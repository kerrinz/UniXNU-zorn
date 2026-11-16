"""Decode the GPU trial checkpoint and its late CPU presenter counters."""

import re
import struct
import zlib

from inspect_ios26_gpu_s2cr_cdc_record import inspect_page as inspect_gpu
from inspect_ios26_lockscreen_touch_cpu_record import inspect_envelope


def inspect_page(page, expected_run_id, before):
    envelope = inspect_envelope(page, expected_run_id, before)
    text = envelope["text"]
    match = re.search(r"; u=([0-9a-f]{6})(?=; gpu=)", text)
    if not match:
        raise ValueError("missing late CPU presenter census")
    census = int(match[1], 16)
    if census & 0x3f0000:
        raise ValueError("reserved UI census bits are set")
    # The original decoder validates the CPU, touch and GPU fields. Recreate
    # its schema after verifying the unmodified page's tag and checksum.
    base = (text[:match.start()] + text[match.end():]).encode("ascii")
    raw = bytearray(4096)
    struct.pack_into("<8s16sII512s", raw, 0, b"HJPAN026", expected_run_id, len(base), 0, base)
    struct.pack_into("<I", raw, 28, zlib.crc32(raw[:544]))
    decoded = inspect_gpu(bytes(raw), expected_run_id, before)
    decoded["late_ui"] = dict(
        springboard_pid_observed=bool(census & 0x800000),
        springboard_exit_observed=bool(census & 0x400000),
        swap_ends_capped_at_255=(census >> 8) & 255,
        pixel_copies_capped_at_255=census & 255,
        sample_seconds_after_pid1=150,
    )
    return decoded

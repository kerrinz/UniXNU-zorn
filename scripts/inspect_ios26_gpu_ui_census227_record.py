"""Decode the explicitly selected nominal45s GPU checkpoint, never a150s sample."""

import re
import struct
import zlib

from inspect_ios26_gpu_ui_census_record import inspect_page as inspect_legacy
from inspect_ios26_lockscreen_touch_cpu_record import inspect_envelope


def inspect_page(page, expected_run_id, before):
    envelope = inspect_envelope(page, expected_run_id, before)
    text = envelope["text"]
    match = re.search(r"; u=([0-9a-f]{6})(?=; gpu=)", text)
    if not match:
        raise ValueError("missing checkpoint schedule census")
    census = int(match[1], 16)
    if census & 0x3f0000 != 0x010000:
        raise ValueError("exact checkpoint45 schedule bit required")
    # Verify the original envelope first, then remove only the versioned bit
    # for the unchanged CPU/touch/GPU decoder. No runtime timestamp is inferred.
    base = (text[:match.start(1)] + f"{census & ~0x010000:06x}" + text[match.end(1):]).encode("ascii")
    raw = bytearray(4096)
    struct.pack_into("<8s16sII512s", raw, 0, b"HJPAN026", expected_run_id, len(base), 0, base)
    struct.pack_into("<I", raw, 28, zlib.crc32(raw[:544]))
    decoded = inspect_legacy(bytes(raw), expected_run_id, before)
    decoded["late_ui"].update(
        sample_seconds_after_pid1=45,
        checkpoint45_selected=True,
        timing_basis="nominal source schedule selected by recorded bit16; not measured elapsed time",
    )
    return decoded

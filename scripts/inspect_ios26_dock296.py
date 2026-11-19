"""Decode a bounded Dock thumbnail and retain the same-frame present ledger."""

import hashlib
import struct
import zlib

from inspect_ios26_gpu_progress236 import MAGIC as PANIC_MAGIC, WIRE_LIMIT
from inspect_ios26_ui_menu274 import UI_MAGIC, inspect_progress as inspect_menu

DOCK_MAGIC = b'K80SH296'
WIDTH, HEIGHT = 104, 48
STRIDE = WIDTH * 4
PIXEL_END = 16 + STRIDE * HEIGHT
IMAGE_BYTES = PIXEL_END + 64
HEADER_BYTES = 68
CHUNK_BYTES = 3072 - HEADER_BYTES


def split_dock(data, tag):
    """Remove Dock packets for the retained menu decoder, validating every chunk."""
    boot = bytes.fromhex(tag)
    if len(boot) != 16 or len(data) > WIRE_LIMIT:
        raise ValueError('Dock capture envelope differs')
    rest = bytearray()
    image = bytearray()
    identity = None
    packets = partial = 0
    at = 0
    while at < len(data):
        tail = data[at:]
        if tail.startswith(DOCK_MAGIC):
            if len(tail) < HEADER_BYTES:
                partial = len(tail)
                break
            offset, size, total, crc, whole_crc, schema, x, y, w, h, header_crc = struct.unpack_from('<11I', tail, 24)
            if tail[8:24] != boot or schema != 296 or zlib.crc32(tail[:64]) != header_crc:
                raise ValueError('Dock boot tag, schema or header CRC differs')
            if total != IMAGE_BYTES or offset != len(image) or not 0 < size == min(CHUNK_BYTES, total - offset):
                raise ValueError('Dock chunk bounds or order differs')
            if x != 0 or y != 3 * h or not WIDTH <= w <= 16384 or not HEIGHT <= h <= 4096:
                raise ValueError('Dock source is outside the expected bottom quarter')
            captured_identity = (whole_crc, x, y, w, h)
            if identity is not None and identity != captured_identity:
                raise ValueError('Dock ROI or image CRC changed during capture')
            identity = captured_identity
            end = HEADER_BYTES + size
            if len(tail) < end:
                partial = len(tail)
                break
            chunk = tail[HEADER_BYTES:end]
            if zlib.crc32(chunk) != crc:
                raise ValueError('Dock chunk CRC differs')
            image.extend(chunk)
            packets += 1
            at += end
            continue
        if DOCK_MAGIC.startswith(tail):
            partial = len(tail)
            break
        if tail.startswith(UI_MAGIC):
            rest.extend(tail[:288])
            at += 288
            continue
        if tail.startswith((b'K80SH265', b'K80SH270')):
            raise ValueError('Legacy screenshot differs from selected Dock transport')
        end = data.find(b'\r\n', at)
        if tail.startswith(PANIC_MAGIC) or end < 0:
            rest.extend(tail)
            break
        rest.extend(data[at:end + 2])
        at = end + 2

    complete = len(image) == IMAGE_BYTES and not partial
    present = None
    if complete:
        if zlib.crc32(image) != identity[0] or image[:16] != b'SHOT' + struct.pack('<3I', WIDTH, HEIGHT, STRIDE):
            raise ValueError('Dock image CRC or pixel layout differs')
        present = struct.unpack_from('<16I', image, PIXEL_END)
        if present[0] != 2 or present[1] < 64 or present[3] not in (1, 2) or present[9] != 1:
            raise ValueError('Dock image lacks a completed present record')
        if not all(0 < value <= 16384 for value in present[13:15]):
            raise ValueError('Dock logical source geometry differs')
    roi = None if identity is None else dict(zip(('x', 'y', 'width', 'height'), identity[1:]))
    return bytes(rest), bytes(image), dict(
        complete=complete, packet_count=packets, partial_packet_bytes=partial,
        width=WIDTH, height=HEIGHT, stride=STRIDE, source_roi=roi,
        payload_sha256=hashlib.sha256(image).hexdigest(), source_present_record=present,
        physical_scanout_proven=False, dock_blur_visually_qualified=False,
    )


def inspect_progress(data, tag, program_tag):
    rest, image, dock = split_dock(data, tag)
    result = inspect_menu(rest, tag, program_tag)
    total = result['wire_nonterminal_frames274'] + dock['packet_count']
    if total > 38:
        raise ValueError('Dock capture exceeded the retained CDC frame budget')
    if dock['partial_packet_bytes']:
        result['transport_frames_valid'] = False
    present = dock['source_present_record']
    scene = result.get('synthetic_menu274') or {}
    before = scene.get('before') or {}
    dock['capture_precedes_or_matches_pre_menu_present'] = bool(
        present and before.get('available', 0) & 1 and present[1] <= before['present_frame']
    )
    dock['completed_GPU_surface_association'] = bool(
        present and present[3] == 2 and present[8] and present[10]
        and present[7] and 0 < present[2] == present[15] <= present[5]
    )
    result.update(dock296=dock, wire_nonterminal_frames296=total)
    return result, image, rest

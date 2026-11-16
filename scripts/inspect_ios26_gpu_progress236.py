"""Validate raw K80 panic transport; retain text as opaque bytes, never symbolize."""
import struct
import zlib
from pathlib import Path
from inspect_ios26_gpu_progress229 import inspect_progress as inspect_previous

MAGIC = b'K80PAN26'
CAPACITY = 0x64000
WIRE_LIMIT = 529408


def decode_packet(data, run_id):
    if not isinstance(run_id, str) or len(run_id) != 32 or bytes.fromhex(run_id).hex() != run_id:
        raise ValueError('panic identity syntax differs')
    if len(data) < 128:
        fixed = MAGIC + struct.pack('<II', 236, 128)
        if data[:min(len(data), len(fixed))] != fixed[:min(len(data), len(fixed))]:
            raise ValueError('partial panic header differs')
        if len(data) > 24 and data[24:min(len(data), 40)] != bytes.fromhex(run_id)[:min(len(data), 40)-24]:
            raise ValueError('partial panic identity differs')
        return dict(packet_complete=False, partial_bytes=len(data)), None
    version, header, total, crc = struct.unpack_from('<4I', data, 8)
    if data[:8] != MAGIC or version != 236 or header != 128 or not 145 <= total <= CAPACITY or not total & 1:
        raise ValueError('panic header bounds differ')
    if data[24:40] != bytes.fromhex(run_id) or any(data[92:128]):
        raise ValueError('panic identity or reserved fields differ')
    cause, flags, rn, required, pn, available, mn, size, index, state, fmt, progress, mode = struct.unpack_from('<13I', data, 40)
    if (cause not in (1, 2, 3) or flags & ~2047 or state > 3 or fmt > 65535 or
            (cause != 2 and fmt) or rn > 4095 or pn > 262144 or mn > 131072 or
            available > 1048576 or size > 1048576 or pn != min(available, 262144) or
            mn != min(size, 131072) or (size and index >= size) or (not size and index) or
            mode != bool(mn) or (state == 2 and required < rn) or
            (state != 2 and (rn or required))):
        raise ValueError('panic section bounds differ')
    expected_flags = ((1 if state == 2 and required > rn else 0) |
                      (2 if state == 3 else 0) | (4 if state == 1 else 0) |
                      (16 if available > pn else 0) | (64 if size > mn else 0) |
                      (128 if mn else 0) | (1024 if state == 0 else 0))
    if flags & ~(8 | 32 | 256 | 512) != expected_flags:
        raise ValueError('panic section flags differ')
    if (available and flags & (8 | 256)) or (size and flags & (32 | 512)):
        raise ValueError('panic unavailable section contains bytes')
    content = 128 + rn + pn + mn
    padding = 1 if content % 2 == 0 else 0
    if total != content + padding + 16 or len(data) > total:
        raise ValueError('panic total length differs')
    meta = dict(packet_complete=False, partial_bytes=len(data), declared_bytes=total,
                reason=cause, flags=flags, reason_state=state, reason_bytes=rn,
                reason_required=required, paniclog_bytes=pn, paniclog_available=available,
                msgbuf_bytes=mn, msgbuf_size=size, msgbuf_index=index,
                format_id=fmt, progress_word=progress,
                reason_truncated=bool(flags & 1), paniclog_truncated=bool(flags & 16),
                msgbuf_truncated=bool(flags & 64), msgbuf_concurrent_snapshot=bool(flags & 128),
                all_boot_history_preserved=False, DMA_quiescence_proven=False,
                root_cause_known=False, raw_text_interpreted=False)
    if len(data) < total:
        return meta, None
    if data[total-16:total-8] != b'K80END26' or struct.unpack_from('<II', data, total-8) != (total, crc):
        raise ValueError('panic completion footer differs')
    if padding and data[content] != 0:
        raise ValueError('panic padding differs')
    check = bytearray(data[:-16])
    check[20:24] = bytes(4)
    if zlib.crc32(check) != crc:
        raise ValueError('panic CRC differs')
    at = 128
    sections = {}
    for name, length in (('reason', rn), ('paniclog', pn), ('msgbuf', mn)):
        sections[name] = data[at:at+length]
        at += length
    meta.update(packet_complete=True, partial_bytes=0, crc32=f'{crc:08x}',
                host_received_exact_packet=True)
    return meta, sections


def inspect_progress(data, run_id, probe_run_id):
    if len(data) > WIRE_LIMIT:
        raise ValueError('CDC data exceeds raw panic budget')
    at = data.find(MAGIC)
    if at < 0:
        at = len(data)
        for length in range(7, 0, -1):
            if data.endswith(MAGIC[:length]):
                at -= length
                break
    normal, packet = data[:at], data[at:]
    result = inspect_previous(normal, run_id, probe_run_id)
    terminal = dict(packet_complete=False, partial_bytes=0, reason=None,
                    root_cause_known=False, raw_text_interpreted=False)
    if packet:
        if (not result['transport_frames_valid'] or result['partial_tail_bytes'] or
                not 0 < result['frame_count'] < 39):
            raise ValueError('panic requires complete prior progress frames')
        terminal, _ = decode_packet(packet, run_id)
    result['terminal236'] = terminal
    return result


def save_panic(data, run_id, output):
    at = data.find(MAGIC)
    if at < 0:
        return []
    metadata, sections = decode_packet(data[at:], run_id)
    if not metadata['packet_complete']:
        return []
    output = Path(output)
    paths = []
    for name, blob in sections.items():
        target = output / ('panic236-' + name + '.txt')
        with target.open('xb') as stream:
            stream.write(blob)
        paths.append(str(target))
    return paths

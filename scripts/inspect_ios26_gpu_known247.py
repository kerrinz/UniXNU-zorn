"""Decode actual known-frame queue completion;never treat SwapWait as a fence."""
from inspect_ios26_gpu_surface246 import decode_surface, inspect_progress as inspect_previous
from inspect_ios26_gpu_progress236 import MAGIC, WIRE_LIMIT


def inspect_progress(data, tag, program_tag):
    if len(data) > WIRE_LIMIT:
        raise ValueError('known247 wire budget exceeded')
    at = data.find(MAGIC)
    normal = data if at < 0 else data[:at]
    terminal = b'' if at < 0 else data[at:]
    output, records = [], []
    for line in normal.splitlines(keepends=True):
        if not line.endswith(b'\r\n'):
            output.append(line)
            continue
        if line.count(b',kp=') != 1 or len(line) > 3072:
            raise ValueError('known247 frame envelope differs')
        head, _, payload = line[:-2].partition(b',kp=')
        record = decode_surface(payload)
        if record['available'] and (not record['frame'] or record['surfaces'] != 1):
            raise ValueError('known247 request identity differs')
        records.append(record)
        output.append(head + b'\r\n')
    result = inspect_previous(b''.join(output) + terminal, tag, program_tag)
    if len(records) != result['frame_count']:
        raise ValueError('known247 record count differs')
    result['known247'] = records
    result['last_known247'] = next((r for r in reversed(records) if r['available']), None)
    result['known_frame_copy_observed'] = any(
        r['available'] and r['lease'] == 2 and r['all_acquires_passed'] and
        r['pixel_copy_returned'] and r['completion_ledger_valid'] and
        bool(r['surface_gpu_access_fence']) for r in records)
    # The fixed probe must separately prove its pixel result and successful
    # frame/SID query. This scalar transport alone cannot attribute pixel writes.
    result['GPU_surface_write_proven'] = False
    result['physical_presentation_proven'] = False
    return result

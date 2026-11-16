"""Decode the actual return value at the map-operation completion boundaries."""
import re

from inspect_ios26_gpu_progress216 import inspect_progress as inspect_base


def inspect_progress(data, tag, program_tag):
    if len(data) > 119808:
        raise ValueError('return capture exceeds byte budget')
    stripped, results = [], []
    for line in data.splitlines(keepends=True):
        if not line.endswith(b'\r\n'):
            stripped.append(line)
            continue
        if len(line) > 3072:
            raise ValueError('return frame exceeds byte budget')
        match = re.search(rb',br=([01])/([0-9a-f]{8})\r\n$', line)
        if not match:
            raise ValueError('missing or malformed native return observation')
        known, raw = int(match[1]), int(match[2], 16)
        if not known and raw:
            raise ValueError('unknown result carries a value')
        results.append(dict(known=bool(known), raw=raw if known else None))
        stripped.append(line[:match.start()] + b'\r\n')
    result = inspect_base(b''.join(stripped), tag, program_tag)
    if len(results) != len(result['frames']):
        raise ValueError('native result frame correspondence differs')
    for frame, value in zip(result['frames'], results):
        if value['known'] and not frame['callback']['point']:
            raise ValueError('native result before a requested source point')
        frame['callback_result'] = value
    points = [frame['callback']['point'] for frame in result['frames']]
    result['callback_dispatch_return_observed'] = any(p >= 1 for p in points)
    result['callback_finish_enter_observed'] = any(p >= 2 for p in points)
    result['callback_operation_release_return_observed'] = any(p >= 4 for p in points)
    result['callback_finish_return_observed'] = any(p >= 5 for p in points)
    result['callback_owner_return_observed'] = any(p >= 6 for p in points)
    result['callback_scope'] = (
        'First observed owned BOmap selector3 only; source points describe '
        'dispatch/finish/unlock/release boundaries. Independent actual-complete-frame '
        'acknowledgments never imply native success or GPU completion.')
    result['callback_return_scope'] = (
        'Actual IOReturn at each source point; unknown is explicit. '
        'Point1=dispatcher returned;2=before finish lock;3=after unlock/before release;'
        '4=release returned;5=finish returned;6=owner returned before done. '
        'A source point or acknowledgment never implies native success.')
    return result

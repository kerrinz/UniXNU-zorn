"""Validate source callout gates separately from native results and GPU completion."""
import re

from inspect_ios26_gpu_progress211 import inspect_progress as inspect_base


def inspect_progress(data, tag, program_tag):
    if len(data) > 119808:
        raise ValueError('callback capture exceeds byte budget')
    stripped = []
    callbacks = []
    for line in data.splitlines(keepends=True):
        if not line.endswith(b'\r\n'):
            stripped.append(line)
            continue
        if len(line) > 3072:
            raise ValueError('callback frame exceeds byte budget')
        match = re.search(rb',bc=(\d+)/(\d+)/(\d+)/(\d+)\r\n$', line)
        if not match:
            raise ValueError('missing or malformed source callback observation')
        selector, point, ack, failed = map(int, match.groups())
        if (point > 6 or ack > point or failed not in (0, point)
                or selector != (3 if point else 0)):
            raise ValueError('callback bounds differ')
        callbacks.append(dict(selector=selector, point=point, ack=ack, failed=failed))
        stripped.append(line[:match.start()] + b'\r\n')
    result = inspect_base(b''.join(stripped), tag, program_tag)
    if len(callbacks) != len(result['frames']):
        raise ValueError('callback frame correspondence differs')
    previous = dict(point=0, ack=0, failed=0)
    for frame, callback in zip(result['frames'], callbacks):
        point, ack, failed = (callback[k] for k in ('point', 'ack', 'failed'))
        if (point < previous['point'] or point > previous['point'] + 1
                or ack < previous['ack'] or ack > previous['ack'] + 1
                or ack > previous['point']):
            raise ValueError('callback source/delivered-frame order differs')
        if point > previous['point'] and ack != point - 1:
            raise ValueError('callback advanced without prior delivery')
        if previous['failed'] and callback != dict(selector=3, **previous):
            raise ValueError('callback resumed after diagnostic failure')
        if point and not (frame['point'] == frame['ack'] == 6):
            raise ValueError('callback before completed publication gate')
        frame['callback'] = callback
        previous = dict(point=point, ack=ack, failed=failed)
    result['callback_observed'] = any(c['point'] for c in callbacks)
    result['callback_dispatch_return_observed'] = any(c['point'] == 6 for c in callbacks)
    result['callback_diagnostic_abort_observed'] = any(c['failed'] for c in callbacks)
    result['callback_scope'] = (
        'First observed owned BOmap selector3 only; point6 means dispatcher returned, '
        'not native success. Independent actual-complete-frame acknowledgments; '
        'no address/register/backtrace/instruction data.')
    return result

"""Validate clientMemoryForType observations without claiming an IOKit mapping."""
import re

from inspect_ios26_gpu_progress217 import inspect_progress as inspect_base


def inspect_progress(data, tag, program_tag):
    if len(data) > 119808:
        raise ValueError('view capture exceeds byte budget')
    stripped, views = [], []
    for line in data.splitlines(keepends=True):
        if len(line) > 3072:
            raise ValueError('view frame exceeds byte budget')
        if not line.endswith(b'\r\n'):
            stripped.append(line)
            continue
        suffix = re.search(rb',bv=(\d+)/([01])/([01])\r\n$', line)
        if not suffix:
            raise ValueError('missing or malformed output-reference state')
        token, known, ready = map(int, suffix.groups())
        if not known and ready:
            raise ValueError('unknown output-reference state carries a value')
        body = line[:suffix.start()] + b'\r\n'
        callback = re.search(rb',bc=(\d+)/(\d+)/(\d+)/(\d+),br=', body)
        if not callback:
            raise ValueError('missing view call-kind')
        kind, point = int(callback[1]), int(callback[2])
        if point > 3 or kind != (256 if point else 0):
            raise ValueError('view call-kind or source point differs')
        if point:
            if not 1 <= token <= 4096 or (point < 3 and ready):
                raise ValueError('view token or early output-reference state differs')
        elif token or known or ready:
            raise ValueError('view state before a claimed source point')
        views.append(dict(token=token, known=bool(known), output_ready=bool(ready)))
        replacement = b',bc=' + (b'3' if point else b'0')
        stripped.append(body[:callback.start()] + replacement + body[callback.end(1):])
    result = inspect_base(b''.join(stripped), tag, program_tag)
    if len(views) != len(result['frames']):
        raise ValueError('view frame correspondence differs')
    claimed_token = None
    results_by_point, states_by_point = {}, {}
    for frame, view in zip(result['frames'], views):
        point = frame['callback']['point']
        frame['callback']['selector'] = 256 if point else 0
        frame['view'] = view
        if point:
            if claimed_token is None:
                claimed_token = view['token']
            elif view['token'] != claimed_token:
                raise ValueError('claimed view token changed')
            value = frame['callback_result']
            if point == 1 and value['known']:
                raise ValueError('view entry cannot carry a work result')
            if value['known'] and value['raw'] and view['output_ready']:
                raise ValueError('native error carries an output reference')
            if value['known']:
                if point in results_by_point and results_by_point[point] != value['raw']:
                    raise ValueError('native result changed at one source point')
                results_by_point[point] = value['raw']
            if view['known']:
                if point in states_by_point and states_by_point[point] != view['output_ready']:
                    raise ValueError('output reference changed at one source point')
                states_by_point[point] = view['output_ready']
    for key in (
        'callback_dispatch_return_observed', 'callback_finish_enter_observed',
        'callback_operation_release_return_observed', 'callback_finish_return_observed',
        'callback_owner_return_observed',
    ):
        result.pop(key, None)
    points = [frame['callback']['point'] for frame in result['frames']]
    result['view_entry_observed'] = any(p >= 1 for p in points)
    result['view_owner_copy_return_observed'] = any(p >= 2 for p in points)
    result['view_serial_unlock_return_observed'] = any(p >= 3 for p in points)
    result['view_token'] = claimed_token
    result['view_output_reference_observed'] = any(
        f['callback']['point'] == 3 and f['view']['known'] and f['view']['output_ready']
        for f in result['frames'])
    result['callback_scope'] = (
        'Diagnostic call-kind256 names clientMemoryForType, not a native GPU ABI '
        'method. First eligible view after completed BoCpuMap13 only, bound to one '
        'client/thread/token. Point1=before owner copy;2=owner copy returned;'
        '3=serial unlock returned. The output flag describes the reference before '
        'the final observation gate; refusal withdraws outputs and retains the reference.')
    result['callback_return_scope'] = (
        'Entry result is unknown; later points carry actual native results. '
        'A prepared reference and a delivered frame do not prove the view callback '
        'or outer IOConnectMapMemory64 returned successfully.')
    return result

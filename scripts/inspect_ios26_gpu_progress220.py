"""Decode the actual next prepared native request after successful BO mapping."""
import re

from inspect_ios26_gpu_progress217 import inspect_progress as inspect_base


def inspect_progress(data, tag, program_tag):
    if len(data) > 119808:
        raise ValueError('next-request capture exceeds byte budget')
    stripped, selectors = [], []
    for line in data.splitlines(keepends=True):
        if not line.endswith(b'\r\n'):
            if len(line) > 3072:
                raise ValueError('partial next-request frame exceeds byte budget')
            stripped.append(line)
            continue
        if len(line) > 3072:
            raise ValueError('next-request frame exceeds byte budget')
        match = re.search(rb',bc=(\d+)/(\d+)/(\d+)/(\d+),br=', line)
        if not match:
            raise ValueError('missing native request identity')
        selector, point = int(match[1]), int(match[2])
        if (point and not 1 <= selector <= 17) or (not point and selector):
            raise ValueError('native request selector outside source ABI')
        selectors.append(selector)
        replacement = b',bc=' + (b'3' if point else b'0')
        stripped.append(line[:match.start()] + replacement + line[match.end(1):])
    result = inspect_base(b''.join(stripped), tag, program_tag)
    if len(selectors) != len(result['frames']):
        raise ValueError('native request frame correspondence differs')
    claimed = None
    for frame, selector in zip(result['frames'], selectors):
        callback = frame['callback']
        callback['selector'] = selector
        if callback['point']:
            if claimed is None:
                claimed = selector
            elif selector != claimed:
                raise ValueError('claimed native request changed')
            if callback['point'] == 1 and frame['callback_result']['known']:
                raise ValueError('request entry cannot carry a work result')
    for key in (
        'callback_dispatch_return_observed', 'callback_finish_enter_observed',
        'callback_operation_release_return_observed', 'callback_finish_return_observed',
        'callback_owner_return_observed',
    ):
        result.pop(key, None)
    points = [frame['callback']['point'] for frame in result['frames']]
    for threshold, name in enumerate((
        'next_run_enter', 'done_enter', 'completion_event_return',
        'serial_unlock_return', 'run_return', 'base_external_return',
    ), 1):
        result['callback_' + name + '_observed'] = any(p >= threshold for p in points)
    result['callback_next_native_method'] = claimed
    result['callback_scope'] = (
        'First prepared owned native request after successful BOmap3; actual '
        'selector remains bound to one client/thread/request. Point1=run entry '
        'before native work;2=done entry;3=completion observation returned;'
        '4=serial unlock returned;5=run returned to action;6=base externalMethod '
        'returned to subclass. These points do not prove subsequent IPC or Metal return.')
    result['callback_return_scope'] = (
        'Point1 has no work result and remains explicitly unknown. Later source '
        'points carry the actual IOReturn when sampled consistently; unknown '
        'snapshots never imply success. No GPU or Metal completion is inferred.')
    return result

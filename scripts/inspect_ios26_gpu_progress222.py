"""Validate source-level mapClientMemory64 observations; no IPC success claim."""
import re
from inspect_ios26_gpu_progress217 import inspect_progress as inspect_base


def inspect_progress(data, tag, program_tag):
    if len(data) > 119808:
        raise ValueError('map capture exceeds byte budget')
    stripped, states = [], []
    for line in data.splitlines(keepends=True):
        if len(line) > 3072:
            raise ValueError('map frame exceeds byte budget')
        if not line.endswith(b'\r\n'):
            stripped.append(line)
            continue
        suffix = re.search(rb',bv=(\d+)/([01])/([01]),bm=([01])/(\d+)\r\n$', line)
        if not suffix:
            raise ValueError('missing or malformed map state')
        token, descriptor_known, descriptor, known, bits = map(int, suffix.groups())
        if (not descriptor_known and descriptor) or (not known and bits):
            raise ValueError('unknown map state carries a value')
        body = line[:suffix.start()] + b'\r\n'
        callback = re.search(rb',bc=(\d+)/(\d+)/(\d+)/(\d+),br=', body)
        if not callback:
            raise ValueError('missing map call-kind')
        kind, point = int(callback[1]), int(callback[2])
        if point > 4 or kind != (257 if point else 0):
            raise ValueError('map call-kind or point differs')
        if point:
            if not 1 <= token <= 4096 or (point == 1 and descriptor):
                raise ValueError('map token or entry descriptor differs')
            allowed = (0,) if point < 3 else (1, 3) if point == 3 else (5, 7, 15)
            if known and bits not in allowed:
                raise ValueError('map state differs from source boundary')
            if known and bits & 2 and descriptor_known and not descriptor:
                raise ValueError('mapping eligibility without a descriptor')
        elif token or descriptor_known or descriptor or known or bits:
            raise ValueError('map state before claim')
        states.append(dict(token=token, descriptor_known=bool(descriptor_known),
                           descriptor_present=bool(descriptor), known=bool(known), bits=bits))
        stripped.append(body[:callback.start()] + b',bc=' + (b'3' if point else b'0') + body[callback.end(1):])
    result = inspect_base(b''.join(stripped), tag, program_tag)
    if len(states) != len(result['frames']):
        raise ValueError('map frame correspondence differs')
    token = None
    native_raw = None
    descriptor_value = None
    can_map = None
    by_point = {}
    for frame, state in zip(result['frames'], states):
        point = frame['callback']['point']
        frame['callback']['selector'] = 257 if point else 0
        frame['mapping'] = state
        if not point:
            continue
        if token is None:
            token = state['token']
        if token != state['token']:
            raise ValueError('claimed map token changed')
        actual = frame['callback_result']
        if point == 1 and actual['known']:
            raise ValueError('map entry carries a callback result')
        if actual['known']:
            if native_raw is not None and native_raw != actual['raw']:
                raise ValueError('callback result changed across map boundaries')
            native_raw = actual['raw']
            if state['known'] and state['bits'] & 2 and actual['raw']:
                raise ValueError('mapping eligibility after callback error')
        if point >= 2 and state['descriptor_known']:
            if descriptor_value is not None and descriptor_value != state['descriptor_present']:
                raise ValueError('returned descriptor presence changed')
            descriptor_value = state['descriptor_present']
        if state['known']:
            if point in by_point and by_point[point] != state['bits']:
                raise ValueError('map state changed at one source point')
            by_point[point] = state['bits']
            if point >= 3:
                value = bool(state['bits'] & 2)
                if can_map is not None and can_map != value:
                    raise ValueError('sharing predicate changed across map boundaries')
                can_map = value
    for key in ('callback_dispatch_return_observed', 'callback_finish_enter_observed',
                'callback_operation_release_return_observed', 'callback_finish_return_observed',
                'callback_owner_return_observed'):
        result.pop(key, None)
    points = [f['callback']['point'] for f in result['frames']]
    result.update(map_token=token, map_entry_observed=any(p >= 1 for p in points),
                  map_view_callback_return_observed=any(p >= 2 for p in points),
                  map_sharing_predicate_observed=any(p >= 3 for p in points),
                  map_block_return_observed=any(p >= 4 for p in points),
                  map_object_presence_observed=any(f['callback']['point'] == 4 and
                      f['mapping']['known'] and bool(f['mapping']['bits'] & 8)
                      for f in result['frames']))
    result['callback_scope'] = ('Diagnostic kind257, not native GPU ABI. First eligible '
        'mapClientMemory64 after successful BoCpuMap13; one client/thread/token. '
        '1=entry;2=clientMemoryForType returned;3=sharing predicate evaluated;'
        '4=original mapping/descriptor-release block returned or skipped. '
        'All waits outside the unchanged fake-frame region; observer refusal holds '
        'unhanded descriptor/map references only. bm bits:1=predicate known,2=eligible,'
        '4=map outcome known,8=map present.')
    result['callback_return_scope'] = ('br is the actual view callback IOReturn, unknown '
        'at entry. bv is returned descriptor presence, not a live pointer after release. '
        'A nonnull map and delivered frame do not prove mapClientMemory64 function '
        'return, subsequent IPC return, user mapping usability or Metal creation.')
    return result

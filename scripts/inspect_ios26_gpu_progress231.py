"""Decode fixed source error categories and bounded atomic progress census only."""
import re
from inspect_ios26_gpu_progress229 import inspect_progress as inspect_previous

CATEGORIES = {0: 'unknown', 1: 'kernel-data-abort-prefix',
              2: 'kernel-instruction-fetch-abort-prefix', 3: 'initproc-exited-prefix',
              4: 'initproc-failed-to-start-prefix', 5: 'GPU-progress-worker-returned-prefix'}


def _partial(line, run_id):
    template = b'K80 TERM ' + run_id.encode('ascii') + b' r=1 c=0 p=777 v=ff\r\n'
    choices = {44: b'123', 48: b'012345', 52: b'01234567', 53: b'01234567',
               54: b'01234567', 58: b'0123456789abcdef', 59: b'0123456789abcdef'}
    return len(line) < 62 and all(byte in choices.get(i, bytes([template[i]]))
                                   for i, byte in enumerate(line))


def inspect_progress(data, run_id, probe_run_id):
    if len(data) > 119808:
        raise ValueError('CDC total including terminal exceeds source budget')
    normal, terminal, partial, ended = [], None, 0, False
    for line in data.splitlines(keepends=True):
        if ended:
            raise ValueError('data follows the one terminal packet')
        if line.startswith(b'K80 TERM '):
            match = re.fullmatch(rb'K80 TERM ([0-9a-f]{32}) r=([123]) c=([0-5]) p=([0-7])([0-7])([0-7]) v=([0-9a-f]{2})\r\n', line)
            if match:
                if match[1] != run_id.encode('ascii'):
                    raise ValueError('terminal identity differs')
                reason, category, requested, acknowledged, state = map(int, match.groups()[1:6])
                result = int(match[7], 16)
                if reason != 2 and category:
                    raise ValueError('non-panic category differs')
                known = (requested, acknowledged, state) != (7, 7, 7)
                if known:
                    if (requested > 6 or acknowledged > requested or state > 5 or
                            (result > 88 if state == 3 else result != 255)):
                        raise ValueError('source census fields differ')
                elif result != 255:
                    raise ValueError('unknown source census has result')
                terminal = dict(reason=reason, category=category,
                                category_source_prefix=CATEGORIES[category],
                                progress_census=(dict(requested=requested, acknowledged=acknowledged,
                                                      state=state, result=result if state == 3 else None)
                                                 if known else None))
            elif not line.endswith(b'\n') and _partial(line, run_id):
                partial = len(line)
            else:
                raise ValueError('terminal source fields syntax differs')
            ended = True
        else:
            normal.append(line)
    result = inspect_previous(b''.join(normal), run_id, probe_run_id)
    if ended and (not result['transport_frames_valid'] or result['partial_tail_bytes'] or result['frame_count'] >= 39):
        raise ValueError('terminal requires prior complete frames within original39frame budget')
    reason = terminal['reason'] if terminal else None
    result['terminal231'] = (terminal or dict(reason=None, category=None, category_source_prefix=None,
                                            progress_census=None)) | dict(
        source_path={1: 'time-limit', 2: 'panic-classified-terminal', 3: 'halt-or-restart'}.get(reason),
        packet_complete=terminal is not None, partial_bytes=partial,
        host_received_exact_packet=terminal is not None, panic_path_source_observed=reason == 2,
        cause_known=False, global_atomic_snapshot_proven=False,
        DMA_completion_or_quiescence_proven=False,
        scope='Fixed source error prefix enum and two equal bounded atomic censuses only. No raw text, numeric error values, addresses, registers or backtrace. Missing/partial packet proves no cause. Source census is not a globally atomic snapshot. All USB resources retained after START; host delivery does not prove device-side completion handling.')
    return result

"""Decode fixed source error categories and bounded atomic progress census only."""
import re
from inspect_ios26_gpu_progress229 import inspect_progress as inspect_previous

import hashlib,json
from pathlib import Path
CATALOG_PATH = Path(__file__).parent / 'data' / 'k80-panic-formats232-f9fd63efaf9448ad923c58b1cfb477f5.json'
CATALOG_SHA256 = 'aaea538132ae8ff3e6d4482e98329eadfce2e31cd30e4fb050da953e60fa0788'
raw_catalog=CATALOG_PATH.read_bytes()
if hashlib.sha256(raw_catalog).hexdigest()!=CATALOG_SHA256:raise ValueError('source format catalog differs')
CATALOG=json.loads(raw_catalog)
FORMATS={row['id']:row for row in CATALOG['entries']}


def _partial(line, run_id):
    template = b'K80 TERM ' + run_id.encode('ascii') + b' r1 f=0000 p777 v=ff\r\n'
    choices = {43:b'123',47:b'0123456789abcdef',48:b'0123456789abcdef',49:b'0123456789abcdef',50:b'0123456789abcdef',53:b'01234567',54:b'01234567',55:b'01234567',59:b'0123456789abcdef',60:b'0123456789abcdef'}
    return len(line) < 63 and all(byte in choices.get(i, bytes([template[i]]))
                                   for i, byte in enumerate(line))


def inspect_progress(data, run_id, probe_run_id):
    if len(data) > 119808:
        raise ValueError('CDC total including terminal exceeds source budget')
    normal, terminal, partial, ended = [], None, 0, False
    for line in data.splitlines(keepends=True):
        if ended:
            raise ValueError('data follows the one terminal packet')
        if line.startswith(b'K80 TERM '):
            match = re.fullmatch(rb'K80 TERM ([0-9a-f]{32}) r([123]) f=([0-9a-f]{4}) p([0-7])([0-7])([0-7]) v=([0-9a-f]{2})\r\n', line)
            if match:
                if match[1] != run_id.encode('ascii'):
                    raise ValueError('terminal identity differs')
                reason=int(match[2]);format_id=int(match[3],16);requested,acknowledged,state=map(int,match.groups()[3:6])
                result = int(match[7], 16)
                if reason != 2 and format_id:
                    raise ValueError('non-panic format ID differs')
                if format_id not in FORMATS and format_id not in (0,65534,65535):raise ValueError('source format ID outside pinned catalog')
                known = (requested, acknowledged, state) != (7, 7, 7)
                if known:
                    if (requested > 6 or acknowledged > requested or state > 5 or
                            (result > 88 if state == 3 else result != 255)):
                        raise ValueError('source census fields differ')
                elif result != 255:
                    raise ValueError('unknown source census has result')
                entry=FORMATS.get(format_id)
                terminal = dict(reason=reason,format_id=format_id,
                                source_template=entry['format'] if entry else None,
                                source_locations=entry['source_locations'][:8] if entry else [],
                                source_locations_total=len(entry['source_locations']) if entry else 0,
                                format_capture_state={0:'not-observed',65534:'unmatched-template',65535:'in-progress'}.get(format_id,'matched-source-template'),
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
    result['terminal232'] = (terminal or dict(reason=None,format_id=None,source_template=None,source_locations=[],source_locations_total=0,format_capture_state=None,
                                            progress_census=None)) | dict(
        source_path={1: 'time-limit', 2: 'panic-classified-terminal', 3: 'halt-or-restart'}.get(reason),
        packet_complete=terminal is not None, partial_bytes=partial,
        host_received_exact_packet=terminal is not None, panic_path_source_observed=reason == 2,
        cause_known=False, global_atomic_snapshot_proven=False,
        DMA_completion_or_quiescence_proven=False,
        scope='Introduced source-format ID (not callsite) and two equal bounded atomic censuses only. Duplicate templates retain multiple possible source locations. No dynamic error arguments are inspected. No raw text, numeric error values, addresses, registers or backtrace. Missing/partial packet proves no cause. Source census is not a globally atomic snapshot. All USB resources retained after START; host delivery does not prove device-side completion handling.')
    return result

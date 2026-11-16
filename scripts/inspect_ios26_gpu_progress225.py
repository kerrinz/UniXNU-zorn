"""Request-correlated native return snapshots; no IPC-return or PAC inference."""
import re
from inspect_ios26_gpu_progress223 import inspect_progress as inspect_base


def inspect_progress(data, tag, program_tag):
    if len(data) > 119808:
        raise ValueError("progress225 stream exceeds source bound")
    stripped, traces = [], []
    for line in data.splitlines(keepends=True):
        if not line.endswith(b'\r\n'):
            stripped.append(line)
            continue
        if len(line) > 3072:
            raise ValueError('progress225 frame exceeds source bound')
        match = re.search(rb',nr=(\d+)/(\d+)/(\d+)/(\d+)/([0-9a-f]{8})/([0-9a-f]{8})/(\d+)/(\d+)\r\n$', line)
        if not match:
            raise ValueError('missing native return225 snapshot')
        values = [int(x, 16 if i in (4, 5) else 10) for i, x in enumerate(match.groups())]
        if any(x > 0xffffffff for x in values):
            raise ValueError('native return225 counter overflow')
        r = dict(zip(('sequence', 'method', 'stage', 'run_seen', 'run_raw', 'external_raw', 'overlaps', 'rejected'), values))
        if (r['stage'] > 3 or r['run_seen'] > 1 or r['method'] > 17 or
                (not r['sequence'] and any(values[1:7])) or
                (r['sequence'] and (not r['method'] or not r['stage'])) or
                (r['stage'] == 1 and (r['run_seen'] or r['run_raw'] or r['external_raw'])) or
                (r['stage'] == 2 and (not r['run_seen'] or r['external_raw'])) or
                (not r['run_seen'] and r['run_raw'])):
            raise ValueError('native return225 state differs')
        traces.append(r)
        stripped.append(line[:match.start()] + b'\r\n')
    result = inspect_base(b''.join(stripped), tag, program_tag)
    prior = identity = None
    for frame, trace in zip(result['frames'], traces):
        app = frame['application']
        current = (app.get('native') or {}).get('unique'), len(app.get('sessions') or [])
        if trace['sequence'] and (not current[0] or not current[1]):
            raise ValueError('native return225 lacks bound native session')
        if frame['snap']:
            if current == identity and prior:
                if (trace['sequence'] < prior['sequence'] or trace['overlaps'] < prior['overlaps'] or
                        trace['rejected'] < prior['rejected']):
                    raise ValueError('native return225 counters regressed')
                if trace['sequence'] == prior['sequence'] and prior['sequence']:
                    if (trace['method'] != prior['method'] or trace['stage'] < prior['stage'] or
                            trace['run_seen'] < prior['run_seen'] or
                            (prior['run_seen'] and trace['run_raw'] != prior['run_raw']) or
                            (prior['stage'] == 3 and trace['external_raw'] != prior['external_raw'])):
                        raise ValueError('native return225 request changed')
            identity, prior = current, trace
        elif any(trace.values()):
            raise ValueError('native return225 present without snapshot')
        frame['native_return225'] = trace
    result['last_native_return225'] = traces[-1] if traces else None
    result['native_return_scope'] = ('stage1: externalMethod entered after selector bounds; stage2: actual run returned; '
        'stage3: base IOUserClient::externalMethod returned. Internal request key is not exported. '
        'Overlaps/rejections/dropped diagnostics prevent an unambiguous request conclusion; '
        'no stage proves subsequent IPC delivery or user-mode continuation.')
    result['full_GPU_qualification'] = False
    result['physical_presentation_proven'] = False
    return result

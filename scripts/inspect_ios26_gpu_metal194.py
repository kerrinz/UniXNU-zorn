"""Decode source-defined v194 Metal reports and sequential native sessions.

Pure host decoder. Program completion and native teardown are separate facts.
"""
import base64
import re
from inspect_ios26_gpu_prepare191 import inspect_prepare


def _fields(raw, bases):
    parts = raw.split(b'/')
    if len(parts) != len(bases):
        raise ValueError('field count differs')
    values = []
    for part, base in zip(parts, bases):
        if not re.fullmatch(rb'[0-9a-f]+' if base == 16 else rb'[0-9]+', part):
            raise ValueError('invalid numeric syntax')
        value = int(part, base)
        if value > 0xffffffffffffffff:
            raise ValueError('numeric overflow')
        values.append(value)
    return values


def inspect_metal(native, encoded, sessions, histories, tag, program, raw_encoded):
    if not re.fullmatch(r'[0-9a-f]{32}', tag):
        raise ValueError('invalid expected program identity')
    keys = ('unique', 'pid', 'flags', 'calls', 'method', 'raw',
            'close_returned', 'close_raw', 'attempts', 'copy_errors',
            'lines', 'bytes', 'dropped')
    n = dict(zip(keys, _fields(native, [16, 10, 16, 10, 10, 16, 10, 16, 10, 10, 10, 10, 10])))
    if (any(n[k] > 0xffffffff for k in keys[1:]) or n['flags'] & ~255 or
            n['calls'] > 65535 or n['close_returned'] > 1 or n['attempts'] > 256 or
            n['copy_errors'] > n['attempts'] or n['lines'] > n['attempts'] or n['bytes'] >= 384):
        raise ValueError('native bounds differ')
    program_unique, program_pid, raw_bytes, raw_dropped = _fields(program, [16, 10, 10, 10])
    if (program_pid > 0xffffffff or raw_bytes >= 384 or raw_dropped > 0xffffffff or
            bool(program_unique) != bool(program_pid) or (program_unique and not n['attempts'])):
        raise ValueError('program observation bounds differ')
    if n['unique'] and program_unique and (n['unique'] != program_unique or n['pid'] != program_pid):
        raise ValueError('native/program task identities differ')
    raw_text = base64.b64decode(raw_encoded, validate=True)
    if len(raw_text) != raw_bytes or base64.b64encode(raw_text) != raw_encoded or (raw_bytes and not program_unique):
        raise ValueError('raw stderr size/identity/base64 differs')
    count, rejected, terminal = _fields(sessions, [10, 10, 10])
    if count > 4 or rejected > 0xffffffff or terminal > 1 or len(histories) != count:
        raise ValueError('session bounds/count differ')
    hk = ('flags', 'calls', 'method', 'raw', 'close_returned', 'close_raw',
          'prepare_stage', 'prepare_raw', 'prepare_detail', 'prepare_events',
          'prepare_failed', 'prepare_mask')
    history = []
    for raw in histories:
        h = dict(zip(hk, _fields(raw, [16, 10, 10, 16, 10, 16, 10, 16, 16, 10, 10, 16])))
        if (any(h[k] > 0xffffffff for k in hk[:-1]) or h['flags'] & ~255 or
                h['calls'] > 65535 or h['close_returned'] > 1 or h['prepare_stage'] >= 64 or
                h['prepare_events'] > 128 or h['prepare_failed'] > 1 or
                bool(h['prepare_raw']) != bool(h['prepare_failed'])):
            raise ValueError('history bounds differ')
        h["preparation"] = inspect_prepare(88, b"/".join(raw.split(b"/")[6:]))
        history.append(h)
    if history and any(n[k] != history[-1][k] for k in hk[:6]):
        raise ValueError('current session/history differs')
    raw = base64.b64decode(encoded, validate=True)
    if len(raw) != n['bytes'] or base64.b64encode(raw) != encoded:
        raise ValueError('output length/base64 differs')
    report = None
    error = None
    if raw:
        prefix = b'ZORN193MTL run=' + tag.encode() + b' '
        if raw.startswith(prefix + b'error=') and re.fullmatch(rb'[\x20-\x7e]+\n', raw):
            error = raw[len(prefix) + 6:-1].decode('ascii')
        else:
            m = re.fullmatch(re.escape(prefix) +
                rb'phase=(\d+) flags=([0-9a-f]+) status=(-?\d+) code=(-?\d+) '
                rb'service=([0-9a-f]+) device=([0-9a-f]+) crc=([0-9a-f]{8}) '
                rb'bad=([0-9a-f]{8}) ticks=(\d+)\n', raw)
            if not m:
                raise ValueError('Metal report syntax/identity differs')
            report = dict(zip(('phase', 'flags', 'status', 'code', 'service', 'device', 'crc', 'first_bad', 'ticks'),
                              [int(x, b) for x, b in zip(m.groups(), [10, 16, 10, 10, 16, 16, 16, 16, 10])]))
            if report['phase'] not in range(1, 12) or report['flags'] & ~1023:
                raise ValueError('Metal report bounds differ')
        if not program_unique or not program_pid or not n['lines']:
            raise ValueError('report lacks native task binding')
    render = bool(report and report['phase'] == 11 and report['flags'] == 1023 and
                  report['status'] == 4 and report['code'] == 0 and report['service'] != 0 and
                  report['service'] == report['device'] and report['crc'] == 0x718ed2ce and
                  report['first_bad'] == 0xffffffff and report['ticks'] and terminal and history and
                  n['unique'] == program_unique and n['pid'] == program_pid and
                  history[-1]['flags'] & 15 == 15 and history[-1]['preparation']['complete'])
    closed = bool(history and history[-1]['flags'] == 255 and all(
        h['close_returned'] and not h['close_raw'] and not h['raw'] and
        h['flags'] in (17, 255) and not h['prepare_failed'] for h in history))
    loss = bool(n['copy_errors'] or n['dropped'] or rejected or raw_dropped)
    reasons = ([] if render else ['Metal-render-not-complete']) + ([] if closed else ['native-teardown-not-complete'])
    if loss:
        reasons.append('diagnostic-loss-or-rejected-session')
    return dict(program_identity=dict(unique=program_unique,pid=program_pid),raw_stderr=raw_text.decode("utf-8",errors="replace"),raw_stderr_dropped=raw_dropped,complete=render and closed and not loss, render_complete=render,
                native_teardown_complete=closed, native=n, sessions=history,
                session_rejected=rejected, report_terminal=terminal, report=report,
                error=error, reasons=reasons)


def inspect_metal_application(stage, publication, native, encoded, tag, known_image, summary, histories, program, raw_encoded):
    """Check publication/envelope before decoding application observations."""
    del known_image  # Existing outer CDC decoder independently validates the kernel probe.
    extra = (native, encoded, summary, program, raw_encoded, *histories)
    if stage not in (87, 88):
        if publication is not None or any(x is not None for x in extra):
            raise ValueError('unexpected Metal application fields')
        return dict(published=False, complete=False, native=None, report=None, reasons=['not-reached'])
    if publication is None:
        raise ValueError('missing application publication')
    pub = int(publication, 16)
    if pub >> 32 != 1 or (stage == 88) != (pub & 0xffffffff == 0):
        raise ValueError('publication stage/raw mismatch')
    if stage == 87:
        if any(x is not None for x in extra):
            raise ValueError('Metal fields before publication')
        return dict(published=False, complete=False, native=None, report=None, reasons=['publication-failed'])
    if any(x is None for x in (native, encoded, summary, program, raw_encoded)):
        raise ValueError('missing Metal application fields')
    count = int(summary.split(b'/')[0])
    if count > 4 or any(x is None for x in histories[:count]) or any(x is not None for x in histories[count:]):
        raise ValueError('non-contiguous session history')
    return dict(published=True, **inspect_metal(native, encoded, summary, histories[:count], tag, program, raw_encoded))

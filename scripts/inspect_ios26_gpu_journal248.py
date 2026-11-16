"""Decode source-defined loss-accounted stderr fragments; retain legacy loss.

The journal is a post-write user-memory sample, not a readback from the fd sink.
Panic bytes remain opaque and are handled only by the existing decoder.
"""
import base64
import hashlib
import re
import zlib
from inspect_ios26_gpu_known247 import inspect_progress as inspect_previous
from inspect_ios26_gpu_progress236 import MAGIC, WIRE_LIMIT

KEYS = ('unique', 'seen_bytes', 'pid', 'reserved', 'published', 'records',
        'pending', 'gaps', 'exited', 'exit_status', 'crc32', 'offset', 'bytes')


def decode_journal(raw, encoded):
    fields = raw.split(b'/')
    if len(fields) != 14 or fields[0] not in (b'0', b'1'):
        raise ValueError('journal248 envelope differs')
    for value, width in zip(fields[1:], (16, 16) + (8,) * 11):
        if not re.fullmatch(rb'[0-9a-f]{%d}' % width, value):
            raise ValueError('journal248 numeric syntax differs')
    r = dict(zip(KEYS, (int(x, 16) for x in fields[1:])))
    r['available'] = int(fields[0])
    blob = base64.b64decode(encoded, validate=True)
    if base64.b64encode(blob) != encoded or len(blob) != r['bytes']:
        raise ValueError('journal248 fragment length/base64 differs')
    if not r['available']:
        if any(r.values()) or blob:
            raise ValueError('journal248 unavailable contains state')
        return r, blob
    if (not r['unique'] or not r['pid'] or not r['seen_bytes'] or
            not 0 <= r['offset'] <= r['published'] <= r['reserved'] <= min(r['seen_bytes'], 65536) or
            r['records'] > 256 or r['pending'] > r['records'] or r['exited'] > 1 or
            r['gaps'] & ~127 or r['bytes'] > 768 or r['offset'] + r['bytes'] > r['published'] or
            (not r['published'] and r['crc32']) or (not r['exited'] and r['exit_status']) or
            bool(r['records']) != bool(r['reserved'])):
        raise ValueError('journal248 bounds differ')
    return r, blob


def inspect_journal(records):
    data, checks = bytearray(), {}
    last = None
    for r, blob in records:
        if not r['available']:
            continue
        if last:
            if ((r['unique'], r['pid']) != (last['unique'], last['pid']) or
                    any(r[k] < last[k] for k in ('seen_bytes', 'reserved', 'published', 'records', 'exited')) or
                    r['gaps'] & last['gaps'] != last['gaps'] or
                    (last['exited'] and r['exit_status'] != last['exit_status'])):
                raise ValueError('journal248 identity/state regressed')
        if r['offset'] != len(data):
            raise ValueError('journal248 stream offset differs')
        data.extend(blob)
        if r['published'] in checks and checks[r['published']] != r['crc32']:
            raise ValueError('journal248 prefix checksum changed')
        checks[r['published']] = r['crc32']
        for size in list(checks):
            if size <= len(data):
                if zlib.crc32(data[:size]) != checks.pop(size):
                    raise ValueError('journal248 prefix checksum differs')
        last = r
    complete = bool(last and last['exited'] and not last['exit_status'] and not last['gaps'] and
                    not last['pending'] and last['seen_bytes'] == last['reserved'] ==
                    last['published'] == len(data) and not checks)
    return dict(complete=complete, last=last, received_bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest(), stderr_base64=base64.b64encode(data).decode(),
                pending_checksum_prefixes=sorted(checks),
                task_detached_exit_observed=bool(last and last['exited']),
                fd_sink_readback=False), bytes(data)


def _same_terminal_report(data, program_tag, report):
    if not report:
        return False
    prefix = re.escape(b'ZORN193MTL run=' + program_tag.encode() + b' ')
    pattern = prefix + (rb'phase=(\d+) flags=([0-9a-f]+) status=(-?\d+) code=(-?\d+) '
                        rb'service=([0-9a-f]+) device=([0-9a-f]+) crc=([0-9a-f]{8}) '
                        rb'bad=([0-9a-f]{8}) ticks=(\d+)')
    keys = ('phase', 'flags', 'status', 'code', 'service', 'device', 'crc', 'first_bad', 'ticks')
    for line in data.splitlines():
        m = re.fullmatch(pattern, line)
        if m and dict(zip(keys, (int(x, b) for x, b in zip(m.groups(), (10,16,10,10,16,16,16,16,10))))) == report:
            return True
    return False


def inspect_progress(data, tag, program_tag):
    if len(data) > WIRE_LIMIT:
        raise ValueError('journal248 wire budget exceeded')
    at = data.find(MAGIC)
    normal, terminal = (data, b'') if at < 0 else (data[:at], data[at:])
    output, records = [], []
    for line in normal.splitlines(keepends=True):
        if not line.endswith(b'\r\n'):
            output.append(line)
            continue
        if len(line) > 3072 or line.count(b',jl=') != 1 or line.count(b',jb=') != 1:
            raise ValueError('journal248 frame envelope differs')
        head, _, rest = line[:-2].partition(b',jl=')
        raw, sep, encoded = rest.partition(b',jb=')
        if not sep:
            raise ValueError('journal248 missing fragment')
        records.append(decode_journal(raw, encoded))
        output.append(head + b'\r\n')
    result = inspect_previous(b''.join(output) + terminal, tag, program_tag)
    if len(records) != result['frame_count']:
        raise ValueError('journal248 record count differs')
    journal, full = inspect_journal(records)
    # Any observed mismatch with native identity rejects the capture. Before
    # native publication, the process may already have written stderr.
    for (record, _), frame in zip(records, result['frames']):
        app = frame.get('application')
        if record['available'] and app:
            identity = app['program_identity']
            if identity['unique'] and (identity['unique'], identity['pid']) != (record['unique'], record['pid']):
                raise ValueError('journal248 native program binding differs')
    app = result.get('last_application')
    bound = bool(app and journal['last'] and app['program_identity'] ==
                 dict(unique=journal['last']['unique'], pid=journal['last']['pid']))
    report_matches = bool(app and _same_terminal_report(full, program_tag, app.get('report')))
    native_clean = bool(app and app['render_complete'] and app['native_teardown_complete'] and
                        not app['native']['copy_errors'] and not app['native']['dropped'] and
                        not app['session_rejected'] and not app.get('error'))
    terminal_meta = result['terminal236']
    transport_clean = bool(result['transport_frames_valid'] and not result['partial_tail_bytes'] and
                           not terminal_meta.get('reason') and not terminal_meta['partial_bytes'])
    result['journal248'] = journal
    result['journal_terminal_report_matches'] = report_matches
    result['lossless_application_complete248'] = bool(journal['complete'] and bound and report_matches and
                                                     native_clean and transport_clean)
    # app.complete and raw_stderr_dropped are deliberately untouched.
    result['GPU_surface_write_proven'] = False
    result['physical_presentation_proven'] = False
    return result

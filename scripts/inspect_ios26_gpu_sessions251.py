"""Check actual metadata connection/refusal/close reports on the full journal."""
import base64
import re
from inspect_ios26_gpu_burst249 import inspect_progress as inspect_previous

# Public IOKit IOReturn.h:iokit_common_err(0x2c5),not an inferred native status.
EXCLUSIVE_ACCESS = 0xe00002c5


def inspect_progress(data, tag, program_tag):
    result = inspect_previous(data, tag, program_tag)
    raw = base64.b64decode(result['journal248']['stderr_base64'], validate=True)
    prefix = b'ZORN251META run=' + program_tag.encode() + b' '
    pattern = re.escape(prefix) + (rb'open0=([0-9a-f]+) open1=([0-9a-f]+) '
                                  rb'busy=([0-9a-f]+) close0=([0-9a-f]+) '
                                  rb'close1=([0-9a-f]+) identity=([01])')
    keys = ('open0', 'open1', 'busy', 'close0', 'close1', 'identity')
    reports = []
    for line in raw.splitlines():
        if not line.startswith(b'ZORN251META '):
            continue
        match = re.fullmatch(pattern, line)
        if not match:
            raise ValueError('sessions251 report syntax/program binding differs')
        report = dict(zip(keys, (int(value, 16) for value in match.groups())))
        if any(value > 0xffffffff for value in report.values()):
            raise ValueError('sessions251 report bounds differ')
        reports.append(report)
    if len(reports) > 1:
        raise ValueError('sessions251 duplicate reports')
    report = reports[0] if reports else None
    complete = bool(report and result['known_burst_complete249'] and
                    result['lossless_application_complete248'] and
                    not any(report[key] for key in ('open0', 'open1', 'close0', 'close1')) and
                    report['busy'] == EXCLUSIVE_ACCESS and report['identity'] == 1)
    result['metadata251'] = report
    result['metadata_session_complete251'] = complete
    # This validates two metadata connections and one refused competing Query,
    # not concurrent native execution or physical output.
    result['multi_native_GPU_sessions_qualified'] = False
    return result

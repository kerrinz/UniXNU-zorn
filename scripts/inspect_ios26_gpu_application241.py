"""Read APP241 source scalars only; never decode native stacks, keys or addresses."""
import re
from inspect_ios26_gpu_progress236 import decode_packet, MAGIC

FIELDS = (
    ('unique', 1, 64), ('pid', 1, 32), ('report_unique', 1, 64), ('report_pid', 1, 32),
    ('sessions', 1, 32), ('rejected', 1, 32), ('dropped', 1, 32), ('flags', 1, 32),
    ('calls', 1, 32), ('method', 1, 32), ('raw', 1, 32), ('close', 2, 32),
    ('prepare', 5, 32), ('mask', 1, 64), ('nr', 8, 32),
)
NUMBER = rb'(0|[1-9][0-9]{0,19})'
PATTERN = re.compile(b'K80 APP241 snapshot=1 ' + b' '.join(
    name.encode() + b'=' + b'/'.join([NUMBER] * count) for name, count, _ in FIELDS
) + b' schema=1')


def inspect_application_packet(data, run_id):
    at = data.find(MAGIC)
    if at < 0:
        raise ValueError('application snapshot needs panic transport')
    meta, sections = decode_packet(data[at:], run_id)
    if not meta['packet_complete'] or sections is None:
        raise ValueError('application snapshot requires complete transport')
    if meta['paniclog_truncated']:
        return dict(available=False, root_cause_known=False, reason='paniclog snapshot truncated')
    candidates = [line for line in sections['paniclog'].split(b'\n')
                  if line.startswith(b'K80 APP241 ')]
    if not candidates:
        return dict(available=False, root_cause_known=False, reason='source line absent')
    if len(candidates) != 1:
        raise ValueError('ambiguous application snapshot')
    if candidates[0] == b'K80 APP241 snapshot=0 schema=1':
        return dict(available=False, root_cause_known=False, reason='original snapshot try-lock unavailable')
    match = PATTERN.fullmatch(candidates[0])
    if not match:
        raise ValueError('application snapshot syntax differs')
    numbers = iter(map(int, match.groups()))
    result = {}
    for name, count, bits in FIELDS:
        values = [next(numbers) for _ in range(count)]
        if any(value >= 1 << bits for value in values):
            raise ValueError('application scalar exceeds source type')
        result[name] = values[0] if count == 1 else values
    if (result['sessions'] > 4 or result['calls'] > 65535 or result['method'] > 17 or
            result['close'][0] > 1 or result['prepare'][0] >= 64 or
            result['prepare'][3] > 128 or result['prepare'][4] > 1 or
            result['nr'][1] > 17 or result['nr'][2] > 3 or result['nr'][3] > 1):
        raise ValueError('application scalar exceeds source bounds')
    return dict(available=True, snapshot=result,
                native_task_matches_reporter=bool(result['sessions'] and result['unique'] and
                    result['pid'] and result['unique'] == result['report_unique'] and
                    result['pid'] == result['report_pid']),
                root_cause_known=False, IPC_delivery_proven=False,
                GPU_completion_proven=False)

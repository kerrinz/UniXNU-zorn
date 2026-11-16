"""Read only explicit SOURCE240/242/242 text from an identity/CRC-checked panic envelope."""
import re
from inspect_ios26_gpu_progress236 import decode_packet, MAGIC

EVENTS = (
    'before-registerService', 'registerService-returned', 'newUserClient-entered',
    'service-admission-entered', 'service-admission-returned', 'client-allocation-entered',
    'initWithTask-entered', 'initWithTask-succeeded', 'client-attach-entered',
    'client-start-entered', 'client-admission-entered', 'client-admission-returned',
    'client-admission-succeeded', 'newUserClient-success-return', 'ensureProcess-entered',
    'prepareApplicationExecution-entered', 'prepareApplicationExecution-returned',
    'client-run-entered', 'external-action-entered', 'externalMethod-entered',
    'close-operation-authorized', 'close-quiesce-returned',
    'close-releaseAll-returned', 'close-ClientStorage-destroyed',
)


def inspect_source_packet(data, run_id):
    at = data.find(MAGIC)
    if at < 0:
        raise ValueError('source snapshot needs a panic packet')
    meta, sections = decode_packet(data[at:], run_id)
    if not meta['packet_complete'] or sections is None:
        raise ValueError('source snapshot requires complete paniclog transport')
    if meta['paniclog_truncated']:
        return dict(available=False, root_cause_known=False, reason='paniclog snapshot truncated')
    # Locate only the literal line emitted by our source. Native binary payload,
    # machine addresses, register values and backtraces are never decoded.
    lines = sections['paniclog'].split(b'\n')
    candidates = [line for line in lines if line.startswith(b'K80 SOURCE240 ')]
    if not candidates:
        return dict(available=False, root_cause_known=False)
    if len(candidates) != 1:
        raise ValueError('ambiguous source snapshot')
    match = re.fullmatch(rb'K80 SOURCE240 events=(0|[1-9][0-9]{0,7}) schema=1', candidates[0])
    if not match:
        raise ValueError('source snapshot syntax differs')
    mask = int(match[1])
    if mask >> len(EVENTS):
        raise ValueError('unknown source milestone bits')
    return dict(available=True, events=mask,
                observed=[name for bit, name in enumerate(EVENTS) if mask & (1 << bit)],
                root_cause_known=False, session_attribution_proven=False,
                globally_ordered=False, missing_events_prove_no_call=False,
                close_bits_scope='latest actual Close entry reset; combine with application snapshot')

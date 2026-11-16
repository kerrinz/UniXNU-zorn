"""Inspect the explicit RELEASE243 source diagnostic; native payload stays opaque."""
import re
from inspect_ios26_gpu_progress236 import decode_packet, MAGIC

# Only phases whose selected public-source writers have been checked.
PHASES = {1: 'freeBo-entered', 2: 'freeBo-pre-unmap', 3: 'freeBo-before-unmap',
          4: 'freeBo-unmap-returned', 30: 'NativeMemory-release-entered',
          31: 'before-descriptor-complete', 32: 'descriptor-complete-returned',
          33: 'before-descriptor-release', 34: 'descriptor-release-returned',
          100: 'releaseAll-call-entry-sentinel'}


def inspect_release_packet(data, run_id):
    at = data.find(MAGIC)
    if at < 0:
        raise ValueError('release source snapshot needs panic transport')
    meta, sections = decode_packet(data[at:], run_id)
    if not meta['packet_complete'] or sections is None:
        raise ValueError('release source snapshot needs complete transport')
    if meta['paniclog_truncated']:
        return dict(available=False, root_cause_known=False, reason='paniclog snapshot truncated')
    lines = [line for line in sections['paniclog'].split(b'\n')
             if line.startswith(b'K80 RELEASE243 ')]
    if not lines:
        return dict(available=False, root_cause_known=False, reason='source line absent')
    if len(lines) != 1:
        raise ValueError('ambiguous release source snapshot')
    match = re.fullmatch(rb'K80 RELEASE243 native=(0|[1-9][0-9]{0,9}) schema=1', lines[0])
    if not match or int(match[1]) > 0xffffffff:
        raise ValueError('release source scalar syntax or size differs')
    value = int(match[1])
    return dict(available=True, native_stage=value, source_phase=PHASES.get(value, 'unknown'),
                globally_shared_best_effort=True, session_attribution_proven=False,
                phase_proves_success=False, DMA_quiescence_proven=False, root_cause_known=False)

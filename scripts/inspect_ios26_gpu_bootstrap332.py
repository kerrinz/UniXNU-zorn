"""Decode K80 v332 evidence emitted before GPU board startup."""
import re

from inspect_ios26_lockscreen_touch_cpu_record import inspect_envelope


def inspect_page(page, expected_run_id, before):
    envelope = inspect_envelope(page, expected_run_id, before)
    match = re.fullmatch(r'K80 GPU early332: root=1; cpu_online=([0-8]); gpu=pending', envelope['text'])
    if not match:
        raise ValueError('Pre-GPU checkpoint text differs')
    return dict(envelope, status='fresh-root-EL0-before-GPU', cpu_online=int(match[1]),
                deferred_CPU_owner_published=None, GPU_board_scheduled_at_checkpoint=False,
                GPU_firmware_or_rendering_proven=False)

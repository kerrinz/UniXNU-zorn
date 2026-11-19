"""Decode the v327 pre-GPU checkpoint, including its bounded owner timeout."""
import re

from inspect_ios26_gpu_early252_record import inspect_page as inspect_ready_page
from inspect_ios26_lockscreen_touch_cpu_record import inspect_envelope


def inspect_page(page, expected_run_id, before):
    envelope = inspect_envelope(page, expected_run_id, before)
    timeout = re.fullmatch(
        r'K80 GPU early252: root=1; deferred=timeout; cpu_online=([0-8]); cpu_samples=pending',
        envelope['text'])
    if timeout is None:
        return inspect_ready_page(page, expected_run_id, before)
    return dict(envelope, status='fresh-root-EL0-deferred-owner-timeout',
                cpu_online=int(timeout[1]), CPU_samples_pending=True,
                deferred_CPU_owner_published=False, deferred_owner_wait_seconds=30,
                can_support_fresh_trial_when_bound_to_actual_capture_and_bundle=False,
                device_execution_proven_by_local_decode=False,
                readback_ack_proven_by_record=False,
                GPU_firmware_or_rendering_proven=False,
                ordinary_GPU_desktop_qualified=False)

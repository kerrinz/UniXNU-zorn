"""Decode the source-defined early checkpoint; CPU samples and GPU remain separate."""
import re
from inspect_ios26_lockscreen_touch_cpu_record import inspect_envelope


def inspect_page(page, expected_run_id, before):
    envelope = inspect_envelope(page, expected_run_id, before)
    match = re.fullmatch(r'K80 GPU early252: root=1; deferred=1; cpu_online=([0-8]); cpu_samples=pending', envelope['text'])
    if not match:
        raise ValueError('early252 checkpoint text differs')
    return dict(envelope, status='fresh-source-defined-root-EL0-early-GPU-checkpoint',
                cpu_online=int(match[1]), CPU_samples_pending=True,
                deferred_CPU_owner_published=True,
                can_support_fresh_trial_when_bound_to_actual_capture_and_bundle=True,
                device_execution_proven_by_local_decode=False,
                readback_ack_proven_by_record=False,
                GPU_firmware_or_rendering_proven=False,
                ordinary_GPU_desktop_qualified=False,
                scope='Source branch after actual registered root and deferred-owner publication,before record readback/CDC/GPU work;bind real capture before any hardware claim')

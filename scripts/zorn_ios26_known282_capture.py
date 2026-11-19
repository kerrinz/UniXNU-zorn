"""Host postprocessing for the new-stack282 known-image trial; no device I/O.

The selected267 program and268 wire schema are unchanged. Reuse their real
decoders, but require the current boot record and bounded Recovery envelope.
Transport success alone never qualifies Metal, client Close, or scanout.
"""
import base64
import hashlib
import json
from pathlib import Path

from inspect_ios26_client_census268 import inspect_progress, save_shot
from inspect_ios26_gpu_early252_record import inspect_page
from inspect_ios26_gpu_progress236 import save_panic


def finish_capture(out, *, tag, program_tag, scope, runner_exit,
                   transport_errors=(), port=None):
    out = Path(out)
    errors = list(transport_errors)
    data = b''
    readable = False
    verdict = dict(transport_frames_valid=False, frames=[], frame_count=0,
                   full_GPU_qualification=False, known_image_complete=False)
    envelope = False
    try:
        data = (out / 'cdc.raw').read_bytes()
        readable = True
    except OSError as error:
        errors.append('CDC raw unavailable: ' + str(error))
    try:
        verdict.update(inspect_progress(data, tag, program_tag))
        verdict['raw_screenshot_file282'] = save_shot(data, tag, out)
        journal = verdict['journal248']
        fragment = base64.b64decode(journal['stderr_base64'], validate=True)
        if hashlib.sha256(fragment).hexdigest() != journal['sha256']:
            raise ValueError('journal248 actual saved bytes hash differs')
        path = out / 'ordinary282-stderr.bin'
        with path.open('xb') as stream:
            stream.write(fragment)
        journal['raw_file'] = str(path)
        verdict['raw_panic_files'] = save_panic(data, tag, out)
        record = inspect_page((out / 'after-log.bin').read_bytes(),
                              bytes.fromhex(tag),
                              (out / 'before-log.bin').read_bytes())
        # Decode/save received logs first, even if the runner never wrote a run
        # receipt. A missing receipt withholds the Recovery grade, not the bytes.
        run = json.loads((out / 'run.json').read_text())
        envelope = bool(record and runner_exit == 0 and
                        run.get('scope') == scope and
                        type(run.get('boot_attempts')) is int and
                        run['boot_attempts'] == 1 and
                        run.get('fastboot_returned_success') is True and
                        run.get('recovery_identity_after', {}).get('family')
                        in ('TWRP', 'OrangeFox'))
    except (OSError, ValueError, KeyError) as error:
        errors.append(str(error))
    verified = bool(verdict['transport_frames_valid'] and envelope and
                    not errors and
                    not verdict.get('terminal236', {}).get('partial_bytes'))
    for name, observed in (
        ('early252_with_recovery_observed', verdict.get('early_launch_observed252')),
        ('serial_shot265_with_recovery_observed', verdict.get('serial_shot265', {}).get('complete')),
        ('kernel_readback266_with_recovery_observed', verdict.get('kernel_known_task_complete266')),
        ('Metal_probe267_with_recovery_observed', verdict.get('Metal_probe267', {}).get('bounded_probe_and_required_lifecycle_complete')),
        ('complete_client_lifecycle268_with_recovery_observed', verdict.get('complete_client_lifecycle268')),
    ):
        verdict[name] = bool(verified and observed)
    verdict.update(
        verified=verified, envelope_valid=envelope, port=port, bytes=len(data),
        raw_wire_readable=readable, runner_exit=runner_exit, errors=errors,
        boot_tag=tag, selected_program_tag=program_tag,
        wire_schema='282boot;268census/267Metal/266kernel-task/265full-SHOT',
        bounded_Metal_and_client_lifecycle_complete282=bool(
            verified and verdict.get('kernel_known_task_complete266') and
            verdict.get('Metal_probe267', {}).get('bounded_probe_and_required_lifecycle_complete') and
            verdict.get('complete_client_lifecycle268')),
        physical_known_image_proven=False,
        GPU_desktop_stability_qualified=False,
        physical_FT3683_functionally_qualified=False,
        full_GPU_qualification=False,
    )
    # Serialize before exclusive creation: malformed keys cannot leave truncated
    # success-looking JSON. Preserve raw/partial bytes even after a failed run.
    text = json.dumps(verdict, indent=2) + '\n'
    with (out / 'cdc-capture.json').open('x') as stream:
        stream.write(text)
    return verdict

"""Postprocess a captured Dock trial and preserve the independent run envelope."""

import base64
import hashlib
import json
from pathlib import Path

from inspect_ios26_dock296 import inspect_progress
from inspect_ios26_gpu_early252_record import inspect_page
from inspect_ios26_scalar_timing287 import inspect as inspect_scalar_timing
from inspect_ios26_ui_menu274 import save_panic


def finish_capture(out, *, tag, program_tag, timing_session, scope, runner_exit,
                   transport_errors=(), port=None):
    out = Path(out)
    errors = list(transport_errors)
    result = dict(transport_frames_valid=False, full_GPU_qualification=False)
    bytes_read = 0
    envelope = False
    try:
        data = (out / 'cdc.raw').read_bytes()
        bytes_read = len(data)
        result, image, remaining = inspect_progress(data, tag, program_tag)
        if result['dock296']['complete']:
            shot = out / 'screen296-dock.bgrx'
            with shot.open('xb') as file:
                file.write(image)
            result['dock296']['raw_path'] = str(shot)
        journal = result['journal248']
        fragment = base64.b64decode(journal['stderr_base64'], validate=True)
        if hashlib.sha256(fragment).hexdigest() != journal['sha256']:
            raise ValueError('Retained journal digest differs')
        journal_path = out / 'ordinary296-stderr.bin'
        with journal_path.open('xb') as file:
            file.write(fragment)
        journal['raw_file'] = str(journal_path)
        result['scalar_timing287'] = inspect_scalar_timing(fragment, timing_session)
        result['raw_panic_files'] = save_panic(remaining, tag, out)
        record = inspect_page((out / 'after-log.bin').read_bytes(), bytes.fromhex(tag),
                              (out / 'before-log.bin').read_bytes())
        run = json.loads((out / 'run.json').read_text())
        envelope = bool(record and runner_exit == 0 and run.get('scope') == scope
                        and type(run.get('boot_attempts')) is int and run['boot_attempts'] == 1
                        and run.get('fastboot_returned_success') is True
                        and run.get('recovery_identity_after', {}).get('family') in ('TWRP', 'OrangeFox'))
    except (OSError, ValueError, KeyError) as error:
        errors.append(str(error))
    verified = bool(result['transport_frames_valid'] and envelope and not errors
                    and not result.get('terminal236', {}).get('partial_bytes'))
    result.update(
        verified=verified, envelope_valid=envelope, errors=errors, bytes=bytes_read,
        port=port, runner_exit=runner_exit, boot_tag=tag, ordinary_timing_session=timing_session,
        dock_capture_with_recovery=bool(verified and result.get('dock296', {}).get('complete')),
        dock_blur_visually_qualified=False, desktop_FPS_qualified=False,
        physical_FT3683_qualified=False, full_GPU_qualification=False,
    )
    receipt = json.dumps(result, indent=2) + '\n'
    with (out / 'cdc-capture.json').open('x') as file:
        file.write(receipt)
    return result

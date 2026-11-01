"""UNAPPLIED host admission proposal. Pure file checks; no USB or native I/O.

Local SHA/nonce/lease files prevent accidental reuse; they are not authentication
or evidence of a firmware handle, GPU ownership, or successful storage I/O.
"""
import hashlib
import json
import os
from pathlib import Path

ROLES = ('boot', 'fd', 'kernel', 'current_start_source', 'current_start_object',
         'FAT', 'menu', 'ADT', 'current_inputs', 'immutable_archive', 'ready',
         'expected', 'owner_approval', 'runner', 'reader', 'firmware_source')
SCOPE = 'single-UEFI-media-qualification-terminal-before-payload'
def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def validate(policy, image, timeout, capture_after, arm_bcb):
    # Explicitly pending template refuses before any device enumeration.
    if (policy.get('version') != 1 or policy.get('scope') != SCOPE or
            policy.get('owner_activation_approved') is not True or
            policy.get('ready') is not True or policy.get('allow_boot') is not True):
        raise ValueError('qualification approval/candidate ready missing; no USB action')
    if (policy.get('serial'), policy.get('product'), policy.get('slot')) != ('92988a43', 'zorn', 'b'):
        raise ValueError('exact K80 identity required')
    if timeout != 600 or capture_after != 0 or not arm_bcb:
        raise ValueError('exact 600s recovery, no screen capture and fresh BCB required')
    required = dict(start_in_recovery=True, bootstrap_allowed=False,
                    terminal_before_payload=True, planned_diagnostic_stop=True,
                    unavailable_preowner_failure_accepted=True,
                    unavailable_nonreturning_IO_accepted=True, inspection_macro=0,
                    gpu_enabled=False, retries=0, log_relative_lba=2291712,
                    log_bytes=4096, watchdog_mode=1)
    if any(type(policy.get(k)) is not type(v) or policy[k] != v for k,v in required.items()):
        raise ValueError('qualification bounds differ')
    pins=policy.get('pins', {})
    if set(pins) != set(ROLES):
        raise ValueError('incomplete candidate input/archive/protection pins')
    for role in ROLES:
        pin=pins[role];path=Path(pin['path'])
        if not path.is_absolute() or not path.is_file() or digest(path) != pin['sha256']:
            raise ValueError('candidate binding changed: '+role)
    if Path(image).resolve() != Path(pins['boot']['path']).resolve():
        raise ValueError('policy boot path differs')
    expected=json.loads(Path(pins['expected']['path']).read_text())
    for key,n in [('nonce',16),('kernel_sha256',32),('input_sha256',32)]:
        raw=bytes.fromhex(expected[key])
        if len(raw)!=n or not any(raw):raise ValueError('invalid expected identity')
    if expected['kernel_sha256'] != pins['kernel']['sha256']:
        raise ValueError('expected identity kernel differs')
    owner=json.loads(Path(pins['owner_approval']['path']).read_text())
    if (owner.get('scope')!=SCOPE or owner.get('approved') is not True or
            owner.get('candidate_boot_sha256')!=pins['boot']['sha256'] or
            owner.get('candidate_nonce')!=expected['nonce'] or
            owner.get('accept_preowner_and_IO_failure_unavailable') is not True):
        raise ValueError('specific new owner activation record missing')
    ready=json.loads(Path(pins['ready']['path']).read_text())
    if (ready.get('allow_boot') is not True or ready.get('sha256')!=pins['boot']['sha256'] or
            ready.get('single_media_qualification') is not True):
        raise ValueError('candidate ready differs')
    lease=Path(policy['one_shot_claim'])
    if not lease.is_absolute() or lease.exists() or not lease.parent.is_dir():
        raise ValueError('one-shot claim unavailable/consumed; no retry')
    return dict(expected_path=pins['expected']['path'],nonce=expected['nonce'],
                boot_sha256=pins['boot']['sha256'],claim=str(lease))

def claim(verified):
    # Claim before the first USB call. Any failure after this is consumed,
    # including failure to find recovery or failure of fastboot boot itself.
    fd=os.open(verified['claim'],os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        raw=(json.dumps(dict(status='consumed-no-repeat',nonce=verified['nonce'],
                            boot_sha256=verified['boot_sha256']))+'\n').encode()
        with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    except BaseException:
        # Never unlink or reset a partial claim.
        raise

def recovered_record(block, expected_path, before):
    # Reuse the actual approved decoder, with exact original identity.
    from zorn_early_failure import decode
    expected=json.loads(Path(expected_path).read_text())
    try:
        if block==before:raise ValueError('unchanged preboot log')
        record=decode(block,expected=expected)
    except (ValueError,KeyError,TypeError) as error:
        return dict(available=False,reason=str(error),native_write_success_proven=False,
                    native_readback_success_proven=False)
    return dict(available=True,record=record,native_write_success_proven=False,
                native_readback_success_proven=False,
                note='fresh record is not the private commit report or a storage/GPU lease')


def validate_build_manifest(build, qualification_selected):
    """Prevent a future ready diagnostic from bypassing the special runner flag."""
    diagnostic = build.get('single_media_qualification') is True
    if diagnostic != bool(qualification_selected):
        raise ValueError('media diagnostic requires its explicit qualification policy')
    if diagnostic and (type(build.get('early_watchdog_mode')) is not int or
                       build['early_watchdog_mode'] != 1 or
                       build.get('native_gpu_enabled') is not False or
                       build.get('terminal_before_payload') is not True):
        raise ValueError('diagnostic build bounds differ; no USB action')

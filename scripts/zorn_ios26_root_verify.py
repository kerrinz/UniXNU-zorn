"""Confirm the already transferred UFS root; never resend image data or boot.

Requires a new explicit post-timeout scope. Reuses the private one-device ADB
server, waits for any old writer to exit, issues a zero-count notrunc/fsync,
then hashes the complete actual32GiB window and rechecks protected metadata.
"""
import argparse
import os
from pathlib import Path
import time
from zorn_ios26_root_install import ROOT, BASE, CURRENT, SERIAL, PART, BYTES, Recovery, sha, load, save

SCOPE = 'K80-existing-UFS-root-zero-data-flush-and-full-readback-v1'


def validate(path, execute=False):
    path = Path(path).resolve()
    if not path.is_relative_to(BASE) or path.is_symlink():
        raise ValueError('fresh existing-root verification scope required')
    d = load(path)
    required = dict(scope=SCOPE, serial=SERIAL, product='zorn', slot='a',
                    timeout_seconds=1800, pending_writer_wait_seconds=300,
                    flush_timeout_seconds=600, image_bytes=BYTES,
                    relative_first_lba=6291712, blocks=8388608,
                    new_image_data_bytes=0, existing_server_only=True,
                    adb_server_port=5039, retries=0, boot_iOS=False,
                    zero_count_partition_flush=True)
    if any(type(d.get(k)) is not type(v) or d[k] != v for k, v in required.items()):
        raise ValueError('existing-root verification limits differ')
    roles = {'owner', 'runner', 'entry', 'core', 'adb', 'host_adb_proof',
             'image', 'prior_failure', 'primary_GPT', 'backup_GPT', 'Data', 'root_manifest'}
    if set(d.get('pins', {})) != roles:
        raise ValueError('incomplete actual readback/protection pins')
    for name, row in d['pins'].items():
        p = Path(row['path'])
        if not p.is_absolute() or p.is_symlink() or not p.is_file() or sha(p) != row['sha256']:
            raise ValueError('changed verification input: ' + name)
    if Path(d['pins']['entry']['path']) != Path(__file__).resolve():
        raise ValueError('maintained verification entry required')
    if Path(d['pins']['runner']['path']) != Path(__file__).with_name('run-zorn-debug.py'):
        raise ValueError('fixed runner required')
    if Path(d['pins']['core']['path']) != Path(__file__).with_name('zorn_ios26_root_install.py'):
        raise ValueError('actual pinned transfer/protection implementation required')
    failure = load(d['pins']['prior_failure']['path'])
    if not failure.get('writes_attempted') or failure.get('installed') is not False:
        raise ValueError('actual incomplete transfer evidence required')
    proof = load(d['pins']['host_adb_proof']['path'])
    if proof.get('adb_sha256') != d['pins']['adb']['sha256'] or proof.get('archive_sha1_matched') is not True:
        raise ValueError('verified independent host tool required')
    owner = load(d['pins']['owner']['path'])
    if execute and (owner.get('allow_zero_data_flush_and_full_readback') is not True or
                    owner.get('serial') != SERIAL or d.get('execution_ready') is not True):
        raise ValueError('actual new post-timeout verification approval required;no USB')
    return d


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ios26-verify-existing-root', type=Path, required=True)
    p.add_argument('--check', action='store_true')
    a = p.parse_args()
    d = validate(a.ios26_verify_existing_root, execute=not a.check)
    if a.check:
        print({'host_inputs_match': True, 'new_image_data_bytes': 0, 'device_calls': 0})
        return
    c = load(CURRENT)
    if any(c.get(k) for k in ('active_run', 'active_build', 'runner_session')):
        raise RuntimeError('another operation is active;no USB')
    if c.get('gpu_discovery', {}).get('latest_persistent_root_installation') != d['pins']['prior_failure']['path']:
        raise RuntimeError('stopped operation differs from reviewed transfer;no USB')
    out = a.ios26_verify_existing_root.resolve().parent/'run'
    out.mkdir(exist_ok=False)
    save(out/'one-shot.claim.json', {'scope': SCOPE, 'consumed_before_first_USB': True,
         'manifest_sha256': sha(a.ios26_verify_existing_root), 'reusable': False}, True)
    c['active_run'] = str(out)
    tmp = CURRENT.with_name('current.root-readback.tmp')
    save(tmp, c, True)
    os.replace(tmp, CURRENT)
    result = {'scope': SCOPE, 'phase': 'identity', 'new_image_data_bytes': 0,
              'flush_returned_success': False, 'complete_readback_matched': False,
              'installed': False, 'iOS_booted': False}
    save(out/'result.json', result)
    try:
        rec = Recovery(d, out)
        status = rec.command(['server-status'])
        (out/'existing-host-server-status.txt').write_bytes(status)
        if d['pins']['adb']['path'].encode() not in status:
            raise RuntimeError('existing server executable not confirmed;no device commands')
        before = rec.protections()
        for name, raw in before.items():
            (out/(name+'.before.bin')).write_bytes(raw)
        until = min(rec.deadline, time.monotonic()+d['pending_writer_wait_seconds'])
        while True:
            processes = rec.command(['shell', 'ps', '-A', '-o', 'PID,ARGS']).decode()
            writers = [line for line in processes.splitlines()
                       if 'dd ' in line and ('of='+PART in line or 'of=/dev/block/sda35' in line)]
            if not writers:
                break
            if time.monotonic() >= until:
                raise RuntimeError('previous actual root writer still present;no flush or readback')
            print('observed existing root writer;waiting without killing or restarting it', flush=True)
            time.sleep(min(5, max(0, until-time.monotonic())))
        result['phase'] = 'zero-data-flush'
        save(out/'result.json', result)
        # Actual Toybox count=0 writes zero input bytes. notrunc keeps all data;
        # fsync confirms the already authorized root writes have been flushed.
        rec.command(['shell', '-T', '-e', 'none',
                     f'dd if=/dev/null of={PART} bs=4096 count=0 conv=notrunc,fsync status=none'],
                    timeout_seconds=d['flush_timeout_seconds'])
        result.update(phase='full-readback', flush_returned_success=True)
        save(out/'result.json', result)
        actual = rec.stream_read(lambda raw: None)
        if actual != {'bytes': BYTES, 'sha256': d['pins']['image']['sha256']}:
            result['actual_readback'] = actual
            raise RuntimeError('actual full root readback differs;no automatic rewrite')
        after = rec.protections()
        for name, raw in after.items():
            (out/(name+'.after.bin')).write_bytes(raw)
        if after != before:
            raise RuntimeError('protected metadata/fences changed;stop')
        result.update(phase='existing-root-flushed-and-full-readback-verified',
                      complete_readback_matched=True, installed=True, readback=actual,
                      protected_metadata_and_fences_unchanged=True)
    except BaseException as e:
        result.update(phase='stopped-no-retry', error=repr(e))
        raise
    finally:
        save(out/'result.json', result)
        c = load(CURRENT)
        if c.get('active_run') == str(out):
            c['active_run'] = None
            c.setdefault('gpu_discovery', {})['latest_existing_root_verification'] = str(out/'result.json')
            c['stop_device_operations'] = not result['installed']
            c['stop_device_reason'] = None if result['installed'] else result.get('error', 'readback incomplete')
            save(tmp, c, True)
            os.replace(tmp, CURRENT)
        print(result, flush=True)


if __name__ == '__main__':
    main()

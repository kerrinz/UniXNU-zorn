"""Fresh Recovery metadata for persistent iOS26 installation; never writes a phone.

Invoked by run-zorn-debug.py. Import, validation and --help have no device I/O.
An exclusive claim is consumed before the first exact-serial USB command.
This scope cannot boot, mount, flash, change slots, or install an image.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-persistent-install26'
CURRENT = ROOT / 'out/zorn/unattended-active/current.json'
SERIAL = '92988a43'
SCOPE = 'K80-existing-server-readonly-recovery-preflight-v3'


def load(p):
    return json.loads(Path(p).read_text())


def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def save_new(p, data):
    with Path(p).open('x') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())


def validate(path):
    path = Path(path).resolve()
    if not path.is_relative_to(BASE) or path.is_symlink():
        raise ValueError('independent installation preflight admission required')
    a = load(path)
    required = dict(scope=SCOPE, serial=SERIAL, product='zorn', slot='a',
                    timeout_seconds=120, device_writes=False, boots=False,
                    retries=0, readonly_preflight_authorized=True,
                    existing_server_only=True, adb_server_port=5039,
                    accepted_recovery='twrp-or-orangefox')
    if any(type(a.get(k)) is not type(v) or a[k] != v for k, v in required.items()):
        raise ValueError('readonly installation scope differs')
    roles = {'runner', 'entry', 'adb', 'owner', 'descriptor', 'primary_GPT',
             'backup_GPT', 'Data', 'root_manifest', 'recovery_identity'}
    if set(a.get('pins', {})) != roles:
        raise ValueError('incomplete preflight inputs')
    for role, row in a['pins'].items():
        p = Path(row['path'])
        if not p.is_absolute() or not p.is_file() or sha(p) != row['sha256']:
            raise ValueError('changed preflight input: ' + role)
        archive = Path(row['archive'])
        if (p.is_symlink() or not archive.is_absolute() or archive.is_symlink() or
                not archive.is_file() or archive.stat().st_ino == p.stat().st_ino or
                sha(archive) != row['sha256']):
            raise ValueError('independent exact preflight archive required: ' + role)
    if Path(a['pins']['runner']['path']) != Path(__file__).with_name('run-zorn-debug.py'):
        raise ValueError('fixed runner required')
    if Path(a['pins']['entry']['path']) != Path(__file__).resolve():
        raise ValueError('maintained preflight entry required')
    if Path(a['pins']['recovery_identity']['path']) != Path(__file__).with_name('zorn_recovery_identity.py'):
        raise ValueError('maintained Recovery identity helper required')
    owner = load(a['pins']['owner']['path'])
    if owner.get('readonly_iOS26_preflight_authorized') is not True or owner.get('serial') != SERIAL:
        raise ValueError('actual current owner instruction required')
    if owner.get('accepted_recovery') != 'twrp-or-orangefox':
        raise ValueError('actual owner interchangeable-Recovery instruction required')
    c = load(CURRENT)
    if c.get('gpu_discovery', {}).get('current_mode') == 'unattended-offline-no-phone':
        raise ValueError('current owner mode is offline/no-phone; no USB')
    if any(c.get(k) for k in ('active_run', 'active_build', 'runner_session', 'stop_device_operations')):
        raise ValueError('device/build already active or stopped; no USB')
    return a


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ios26-install-preflight', type=Path, required=True)
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    a = validate(args.ios26_install_preflight)
    if args.check:
        print(json.dumps({'valid':True,'device_calls':0,'device_writes':False}));return
    out = args.ios26_install_preflight.resolve().parent / 'run'
    out.mkdir(exist_ok=False)
    save_new(out / 'one-shot.claim.json', dict(scope=SCOPE, serial=SERIAL,
             admission_sha256=sha(args.ios26_install_preflight),
             consumed_before_first_USB=True, reusable=False, pid=os.getpid()))
    current = load(CURRENT)
    if any(current.get(k) for k in ('active_run', 'active_build', 'runner_session', 'stop_device_operations')):
        raise RuntimeError('state changed after claim; consumed without USB')
    current['active_run'] = str(out)
    temporary = CURRENT.with_name('current.ios26-install-preflight.tmp')
    save_new(temporary, current)
    os.replace(temporary, CURRENT)
    deadline = time.monotonic() + a['timeout_seconds']
    adb = a['pins']['adb']['path']
    count = 0
    result = dict(scope=SCOPE, device_writes=False, boots=False, status='started',
                  installed=False, OS_or_GPU_executed=False)

    def command(argv):
        nonlocal count
        left = deadline - time.monotonic()
        if left <= 0:
            raise RuntimeError('readonly deadline expired; no more device commands')
        count += 1
        cmd=[adb,'-H','127.0.0.1','-P','5039','-s',SERIAL,*argv]
        save_new(out / f'command-{count:03}.json', dict(arguments=cmd))
        # argv is selected only by the literal operations below, never shell input.
        env=os.environ.copy()
        for key in ('ADB_SERVER_SOCKET','ANDROID_ADB_SERVER_PORT','ANDROID_SERIAL','ADB_TRACE'):env.pop(key,None)
        env['ADB_LIBUSB']='0';env['ADB_MDNS_AUTO_CONNECT']='0'
        c = subprocess.run(cmd, env=env,capture_output=True,timeout=min(15,left))
        (out / f'command-{count:03}.stdout').write_bytes(c.stdout)
        (out / f'command-{count:03}.stderr').write_bytes(c.stderr)
        if c.returncode:
            raise RuntimeError(f'exact Recovery command {count} failed ({c.returncode}); no retry')
        return c.stdout

    def exact(argv, wanted):
        got = command(argv).decode().strip()
        if got != wanted:
            raise RuntimeError('Recovery identity/geometry mismatch: ' + repr(argv))

    def read(name, device, first, blocks):
        if device not in ('/dev/block/sda', '/dev/block/by-name/unixnu') or not 0 < blocks <= 65:
            raise ValueError('bounded read only')
        data = command(['exec-out', f'dd if={device} bs=4096 skip={first} count={blocks} 2>/dev/null'])
        if len(data) != blocks * 4096:
            raise RuntimeError('short bounded metadata read')
        (out / (name + '.bin')).write_bytes(data)
        return data

    try:
        # Both owner-approved recoveries are accepted without changing scope.
        # An Android adbd transport alone still cannot qualify this identity.
        exact(['get-serialno'], SERIAL)
        for key, wanted in [('ro.product.device', 'zorn'), ('ro.boot.slot_suffix', '_a')]:
            exact(['shell', 'getprop', key], wanted)
        from zorn_recovery_identity import PROPERTIES, inspect_recovery
        actual_properties = {key: command(['shell', 'getprop', key]).decode().strip()
                             for key in PROPERTIES}
        result['recovery_identity'] = inspect_recovery(actual_properties)
        exact(['shell', 'readlink', '-f', '/dev/block/by-name/unixnu'], '/dev/block/sda35')
        exact(['shell', 'blockdev', '--getss', '/dev/block/sda'], '4096')
        exact(['shell', 'blockdev', '--getsize64', '/dev/block/by-name/unixnu'], '68719476736')
        mounts = command(['shell', 'cat', '/proc/mounts']).decode()
        if any(line.split()[0] in ('/dev/block/sda35', '/dev/block/by-name/unixnu')
               for line in mounts.splitlines() if line.split()):
            raise RuntimeError('unixnu is mounted; no automatic unmount')
        checks = [('primary_GPT', '/dev/block/sda', 0, 6),
                  ('backup_GPT', '/dev/block/sda', 64049147, 5),
                  ('root_manifest', '/dev/block/by-name/unixnu', 0, 1),
                  ('Data', '/dev/block/by-name/unixnu', 4194304, 65)]
        for name, device, first, blocks in checks:
            if read(name, device, first, blocks) != Path(a['pins'][name]['path']).read_bytes():
                raise RuntimeError('protected GPT/root/Data metadata changed: ' + name)
        read('root-window-before', '/dev/block/by-name/unixnu', 6291711, 1)
        read('root-window-first', '/dev/block/by-name/unixnu', 6291712, 1)
        read('root-window-after', '/dev/block/by-name/unixnu', 14680320, 1)
        read('original-log', '/dev/block/by-name/unixnu', 2291712, 1)
        command(['shell', 'ls', '-l', '/dev/block/by-name'])
        command(['shell', 'cat', '/proc/partitions'])
        command(['shell', 'cat', '/proc/cmdline'])
        command(['shell', 'dd', '--help'])
        result.update(status='Recovery-identity-and-protected-metadata-matched',
                      persistent_boot_target_selected=False,
                      root_window_contents_fully_backed_up=False,
                      installation_ready=False, device_commands=count)
    except Exception as e:
        result.update(status='failed-stopped-no-retry', error=str(e), device_commands=count)
        raise
    finally:
        save_new(out / 'result.json', result)
        current = load(CURRENT)
        if current.get('active_run') == str(out):
            current['active_run'] = None
            current.setdefault('gpu_discovery', {})['latest_persistent_install_preflight'] = str(out / 'result.json')
            save_new(temporary, current)
            os.replace(temporary, CURRENT)
        print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()

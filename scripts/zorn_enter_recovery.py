"""One exact-serial Android/Recovery -> OrangeFox transition, without flashing.

Only the fixed runner invokes this entry. Every execution consumes a fresh
claim before USB. There is at most one adb reboot recovery; the subsequent
120-second wait never retries the reboot, boots iOS, or writes storage.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-persistent-install26'
CURRENT = ROOT/'out/zorn/unattended-active/current.json'
SCOPE = 'K80-exact-existing-server-enter-OrangeFox-no-flash-v2'
SERIAL = '92988a43'


def load(p):
    return json.loads(Path(p).read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save_new(p, d):
    with Path(p).open('x') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())


def validate(path):
    path = Path(path).resolve()
    if not path.is_relative_to(BASE) or path.is_symlink():
        raise ValueError('fresh local exact Recovery-entry admission required')
    d = load(path)
    required = dict(scope=SCOPE, serial=SERIAL, product='zorn', slot='a',
                    timeout_seconds=120, reboot_recovery_max=1,
                    partition_writes=False, boot_iOS=False, reboot_retries=0,
                    existing_server_only=True, adb_server_port=5039)
    if any(type(d.get(k)) is not type(v) or d[k] != v for k, v in required.items()):
        raise ValueError('Recovery entry scope differs')
    if set(d.get('pins', {})) != {'runner', 'entry', 'owner', 'adb'}:
        raise ValueError('missing entry/input pins')
    for name, row in d['pins'].items():
        p = Path(row['path'])
        if not p.is_absolute() or not p.is_file() or sha(p) != row['sha256']:
            raise ValueError('changed Recovery-entry input: ' + name)
        archive = Path(row['archive'])
        if not archive.is_file() or archive.stat().st_ino == p.stat().st_ino or sha(archive) != row['sha256']:
            raise ValueError('independent exact input archive required: ' + name)
    if Path(d['pins']['runner']['path']) != Path(__file__).with_name('run-zorn-debug.py'):
        raise ValueError('fixed runner required')
    if Path(d['pins']['entry']['path']) != Path(__file__).resolve():
        raise ValueError('maintained exact entry required')
    owner = load(d['pins']['owner']['path'])
    if owner.get('adb_reboot_recovery_authorized') is not True or owner.get('serial') != SERIAL:
        raise ValueError('actual owner Recovery-entry approval required')
    c = load(CURRENT)
    if any(c.get(k) for k in ('active_run', 'active_build', 'runner_session', 'stop_device_operations')):
        raise ValueError('another active/stopped operation; no USB')
    return d


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ios26-enter-recovery', type=Path, required=True)
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    d = validate(args.ios26_enter_recovery)
    if args.check:
        print(json.dumps({'valid': True, 'device_calls': 0}))
        return
    out = args.ios26_enter_recovery.resolve().parent/'run'
    out.mkdir(exist_ok=False)
    save_new(out/'one-shot.claim.json', {'scope': SCOPE, 'serial': SERIAL,
             'admission_sha256': sha(args.ios26_enter_recovery),
             'consumed_before_first_USB': True, 'reusable': False})
    c = load(CURRENT)
    if any(c.get(k) for k in ('active_run', 'active_build', 'runner_session', 'stop_device_operations')):
        raise RuntimeError('state changed after claim; consumed with no USB')
    c['active_run'] = str(out)
    tmp = CURRENT.with_name('current.enter-recovery.tmp')
    save_new(tmp, c)
    os.replace(tmp, CURRENT)
    deadline, count = time.monotonic()+120, 0
    result = {'scope': SCOPE, 'status': 'started', 'reboot_requests': 0,
              'partition_writes': False, 'iOS_booted': False}

    def command(argv, transient=False):
        nonlocal count
        left = deadline-time.monotonic()
        if left <= 0:
            raise RuntimeError('Recovery entry timed out; stop device commands')
        count += 1
        cmd = [d['pins']['adb']['path'], '-H', '127.0.0.1', '-P', '5039', '-s', SERIAL, *argv]
        save_new(out/f'command-{count:03}.json', {'arguments': cmd})
        env=os.environ.copy()
        for key in ('ADB_SERVER_SOCKET','ANDROID_ADB_SERVER_PORT','ANDROID_SERIAL','ADB_TRACE'):env.pop(key,None)
        env['ADB_LIBUSB']='0';env['ADB_MDNS_AUTO_CONNECT']='0'
        p = subprocess.run(cmd, env=env, capture_output=True, timeout=min(10, left))
        (out/f'command-{count:03}.stdout').write_bytes(p.stdout)
        (out/f'command-{count:03}.stderr').write_bytes(p.stderr)
        if p.returncode and not transient:
            raise RuntimeError('Recovery-entry command failed; no reboot retry')
        return p.returncode, p.stdout.decode().strip()

    def identity():
        for argv, wanted in [(['get-serialno'], SERIAL),
                             (['shell', 'getprop', 'ro.product.device'], 'zorn'),
                             (['shell', 'getprop', 'ro.boot.slot_suffix'], '_a')]:
            if command(argv)[1] != wanted:
                raise RuntimeError('exact serial/product/slot mismatch; no reboot')

    try:
        identity()
        if command(['shell', 'getprop', 'ro.orangefox.boot'])[1] != '1':
            result['reboot_requests'] = 1
            save_new(out/'reboot-attempt.json', result)
            command(['reboot', 'recovery'])
            print('single adb reboot recovery sent; waiting for actual OrangeFox', flush=True)
            while True:
                if time.monotonic() >= deadline:
                    raise RuntimeError('OrangeFox did not return within120s; no retry or rescue')
                code, state = command(['get-state'], transient=True)
                if code == 0 and state in ('device', 'recovery'):
                    if command(['shell', 'getprop', 'ro.orangefox.boot'])[1] == '1':
                        break
                elif code == 0 and state not in ('offline', ''):
                    raise RuntimeError('unexpected ADB state during Recovery entry')
                time.sleep(min(2, max(0, deadline-time.monotonic())))
        identity()
        if command(['shell', 'getprop', 'ro.orangefox.boot'])[1] != '1':
            raise RuntimeError('OrangeFox identity no longer present')
        result.update(status='verified-OrangeFox-Recovery', device_commands=count,
                      serial=SERIAL, product='zorn', slot='a')
    except BaseException as e:
        result.update(status='failed-stop-device-operations', error=str(e), device_commands=count)
        raise
    finally:
        save_new(out/'result.json', result)
        c = load(CURRENT)
        if c.get('active_run') == str(out):
            c['active_run'] = None
            c.setdefault('gpu_discovery', {})['latest_Recovery_entry'] = str(out/'result.json')
            if result['status'] == 'verified-OrangeFox-Recovery':
                c['device_state'] = 'Actual exact OrangeFox Recovery verified after owner-authorized ADB Recovery entry'
            elif result['reboot_requests']:
                c['stop_device_operations'] = True
                c['stop_device_reason'] = result.get('error')
            save_new(tmp, c)
            os.replace(tmp, CURRENT)
        print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()

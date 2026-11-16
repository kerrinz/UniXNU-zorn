"""One explicitly admitted boot of the installed K80 iOS26 UFS root.

Validation/check-only never accesses USB or creates a claim. Execution needs
new exact approval of the transient kernel/loader carrier (not a RAM OS),
native UFS initialization/read-only root, RAMFS var and bounded Recovery.
There is no flash, install, root/Data write, GPU start or boot retry here.
"""
import argparse
import gzip
import hashlib
import io as bytesio
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import time

from zorn_ios26_installed_root_image import (ROOT, STAGE, ARGS, KERNEL_SHA,
                                           FAT_SHA, FD_SHA, ROOT_SHA)

SCOPE = 'single-K80-ios26-installed-UFS-root300s-bounded-recovery'
SERIAL = '92988a43'
CURRENT = ROOT / 'out/zorn/unattended-active/current.json'
PART = '/dev/block/by-name/unixnu'
EXPECTED = dict(version=1, scope=SCOPE, serial=SERIAL, product='zorn', slot='a',
                os_major=26, donor='iPhone18,1/26.6.2/23G90',
                trial_seconds=300, timeout_seconds=600, retries=0,
                watchdog_mode=1, start_in_recovery=True, bootstrap_allowed=False,
                root_OS_in_RAM=False, root_read_only=True, var_backend='RAMFS',
                GPU_startup=False, native_UFS_initialization=True,
                native_Data_write=False, native_root_write=False,
                boot_partition_writes=False, persistent_boot_entry=False,
                transient_kernel_loader=True)
PROTECTION_ROLES = {'primary_GPT', 'backup_GPT', 'root_manifest', 'Data_header',
                    'Data_metadata', 'root_first_page', 'root_before', 'root_after'}
ROLES = PROTECTION_ROLES | {'boot', 'FAT', 'fd', 'kernel', 'menu', 'ADT',
        'loader', 'manager', 'image_proof', 'installed_result', 'installed_evidence',
        'fixed_builder', 'fixed_runner', 'entry', 'image_entry', 'device_helpers',
        'adb_binary', 'fastboot_binary', 'host_adb_proof'}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def save(path, value, exclusive=False):
    with Path(path).open('x' if exclusive else 'w') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def equal(value, expected):
    return type(value) is type(expected) and value == expected


def validate_bundle(path, spec=None):
    path = Path(path)
    if path.is_symlink() or not path.resolve().is_relative_to(STAGE):
        raise ValueError('independent current root-boot bundle required')
    bundle = load(path)
    expected = dict(EXPECTED, scope=spec['scope']) if spec else EXPECTED
    if any(not equal(bundle.get(k), v) for k, v in expected.items()):
        raise ValueError('exact installed-UFS-root boot scope differs')
    pins = bundle.get('pins', {})
    roles = ROLES | {'trial_core'} if spec else ROLES
    if set(pins) != roles:
        raise ValueError('complete exact input/protection roles required')
    for role, row in pins.items():
        source, archive = Path(row['path']), Path(row['archive'])
        if (not source.is_absolute() or not archive.is_absolute() or source.is_symlink() or
                archive.is_symlink() or not source.is_file() or not archive.is_file() or
                source.stat().st_ino == archive.stat().st_ino or
                sha(source) != row['sha256'] or sha(archive) != row['sha256']):
            raise ValueError('changed/shared source/archive: ' + role)
    fixed = {'entry': Path(spec['entry']) if spec else Path(__file__), 'image_entry': Path(__file__).with_name('zorn_ios26_installed_root_image.py'),
             'fixed_builder': Path(__file__).with_name('build-zorn-debug.py'),
             'fixed_runner': Path(__file__).with_name('run-zorn-debug.py'),
             'device_helpers': Path(__file__).with_name('zorn_gpu_resource_trial.py')}
    if spec:
        fixed['trial_core'] = Path(__file__)
    if any(Path(pins[k]['path']).resolve() != p.resolve() for k, p in fixed.items()):
        raise ValueError('maintained fixed build/run/helper entry required')
    for role, expected in [('kernel', KERNEL_SHA), ('FAT', spec['fat_sha256'] if spec else FAT_SHA), ('fd', FD_SHA)]:
        if pins[role]['sha256'] != expected:
            raise ValueError('current installed-root artifact differs: ' + role)
    if spec and pins['ADT']['sha256'] != spec['adt_sha256']:
        raise ValueError('corrected loader relocation-slot ADT required')
    result = load(pins['installed_result']['path'])
    if (result.get('installed') is not True or
            result.get('readback') != {'bytes': 34359738368, 'sha256': ROOT_SHA} or
            result.get('protected_metadata_and_fences_unchanged') is not True):
        raise ValueError('complete actual UFS root readback required')
    image_proof = load(pins['image_proof']['path'])
    if (image_proof.get('boot', {}).get('sha256') != pins['boot']['sha256'] or
            image_proof.get('root_OS_in_RAM') is not False or
            image_proof.get('root_SHA256') != ROOT_SHA or image_proof.get('boot_args') != ARGS):
        raise ValueError('actual current carrier proof differs')
    if (load(pins['host_adb_proof']['path']).get('adb_sha256') != pins['adb_binary']['sha256'] or
            load(pins['host_adb_proof']['path']).get('archive_sha1_matched') is not True):
        raise ValueError('verified native SDK37 host tool required')
    import tomllib
    menu = tomllib.loads(Path(pins['menu']['path']).read_text())
    if (len(menu.get('entry', [])) != 1 or menu['entry'][0].get('args') != ARGS or
            menu['boot'].get('connect_all') is not False or menu['kits'].get('autoload') is not False):
        raise ValueError('exact bounded root selection required')
    image = Path(pins['boot']['path']).read_bytes()
    size, ramdisk = struct.unpack_from('<II', image, 8)
    if (image[:8] != b'ANDROID!' or struct.unpack_from('<I', image, 40)[0] != 4 or
            ramdisk or len(image) != 4096 + ((size + 4095) & ~4095)):
        raise ValueError('current no-Android-ramdisk carrier required')
    with gzip.GzipFile(fileobj=bytesio.BytesIO(image[4096:4096+size])) as stream:
        raw = stream.read(256 * 1024**2 + 1)
    if (len(raw) > 256 * 1024**2 or raw[56:60] != b'ARM\x64' or
            struct.unpack_from('<QQ', raw, 8) != (0xA7100000, len(raw)) or
            raw[4096:] != Path(pins['fd']['path']).read_bytes() + Path(pins['FAT']['path']).read_bytes()):
        raise ValueError('actual shim/FD/FAT closure differs')
    if bundle.get('allow_boot') is not False:
        raise ValueError('artifact bundle must not impersonate execution admission')
    return bundle


def validate_admission(path, bundle_path, spec=None):
    admission = load(path)
    expected = dict(EXPECTED, scope=spec['scope']) if spec else EXPECTED
    if any(not equal(admission.get(k), v) for k, v in expected.items()):
        raise ValueError('new exact root-boot admission required')
    if admission.get('allow_boot') is not True or admission.get('bundle_sha256') != sha(bundle_path):
        raise ValueError('distinct actual root-boot approval required')
    nonce = admission.get('nonce')
    if nonce != (spec['nonce'] if spec else '21d4dceea4044d06a4492ca94291444b'):
        raise ValueError('current unexecuted terminal artifact identity required')
    # This approval belongs to one canonical trial, not an arbitrary copy of
    # its bundle. Copying an approved manifest must not create a fresh claim.
    base = STAGE / (spec['directory'] if spec else 'k80-installed-root-trial26-20261110')
    claim = Path(admission['claim'])
    if (Path(bundle_path).resolve() != base / 'bundle.json' or
            claim.resolve() != base / 'trial/one-shot.claim.json' or
            claim.is_symlink() or claim.exists() or not claim.parent.is_dir()):
        raise ValueError('canonical one-shot trial absent/consumed;no copied-scope replay')
    bundle = validate_bundle(bundle_path, spec)
    for role in ['owner', 'ready']:
        row = admission[role]
        if sha(row['path']) != row['sha256']:
            raise ValueError('changed actual ' + role)
        value = load(row['path'])
        required = dict(scope=expected['scope'], nonce=nonce, bundle_sha256=sha(bundle_path),
                        boot_sha256=bundle['pins']['boot']['sha256'], allow_boot=True)
        if any(not equal(value.get(k), v) for k, v in required.items()):
            raise ValueError('exact independent ' + role + ' required')
        if role == 'owner' and (value.get('approved') is not True or
                value.get('accept_transient_kernel_loader_with_UFS_root') is not True or
                value.get('accept_console_only_root_observation') is not True):
            raise ValueError('actual owner decision on kernel carrier and observation required')
    current = load(CURRENT)
    if any(current.get(k) for k in ['active_run', 'active_build', 'runner_session', 'stop_device_operations']):
        raise ValueError('another run/build or device-stop state exists')
    return bundle, claim


def run(bundle, claim):
    out, pins = claim.parent, bundle['pins']
    save(claim, {'scope': bundle['scope'], 'status': 'consumed-no-repeat',
                 'boot_sha256': pins['boot']['sha256'], 'before_first_USB': True}, True)
    current = load(CURRENT)
    current['active_run'] = str(out)
    temporary = CURRENT.with_name('current.installed-root-boot.tmp')
    save(temporary, current, True)
    os.replace(temporary, CURRENT)
    from zorn_gpu_resource_trial import Transport, recovery, fresh_bcb, getvar

    class Capture(Transport):
        def __init__(self):
            self.adb, self.fastboot = pins['adb_binary']['path'], pins['fastboot_binary']['path']
            self.deadline, self.sequence = time.monotonic() + 600, 0

        def call(self, *args, binary=False, timeout=20):
            left = self.deadline - time.monotonic()
            if left <= 0:
                raise RuntimeError('overall600s deadline expired;stop device operations')
            self.sequence += 1
            stem = out / f'command-{self.sequence:03d}'
            save(stem.with_suffix('.json'), {'arguments': list(map(str, args))}, True)
            env = os.environ.copy()
            for key in ['ADB_SERVER_SOCKET', 'ANDROID_ADB_SERVER_PORT', 'ANDROID_SERIAL', 'ADB_TRACE']:
                env.pop(key, None)
            env.update(ADB_LIBUSB='0', ADB_MDNS_AUTO_CONNECT='0')
            try:
                p = subprocess.run(list(map(str, args)), env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, timeout=min(timeout, left))
            except subprocess.TimeoutExpired as error:
                stem.with_suffix('.stdout').write_bytes(error.stdout or b'')
                stem.with_suffix('.stderr').write_bytes(error.stderr or b'')
                raise
            stem.with_suffix('.stdout').write_bytes(p.stdout)
            stem.with_suffix('.stderr').write_bytes(p.stderr)
            p.check_returncode()
            return p.stdout if binary else (p.stdout + p.stderr).decode().strip()

        def adb_call(self, *args, **kw):
            return self.call(self.adb, '-H', '127.0.0.1', '-P', '5039', '-s', SERIAL, *args, **kw)

    io = Capture()
    status = {'scope': bundle['scope'], 'status': 'claimed', 'GPU_started': False,
              'root_mount_proven': False, 'desktop_proven': False, 'boot_attempts': 0}
    def record():
        save(out / 'run.json', status)
    def protected():
        state = recovery(io, pins)
        exact = [('Data_metadata', 4194304, 65), ('root_first_page', 6291712, 1),
                 ('root_before', 6291711, 1), ('root_after', 14680320, 1)]
        for name, lba, count in exact:
            state[name] = io.read(PART, lba, count)
            if state[name] != Path(pins[name]['path']).read_bytes():
                raise RuntimeError('protected current root/Data/fence differs: ' + name)
        state['log'] = io.read(PART, 2291712, 1)
        return state
    record()
    try:
        try:
            probe = socket.create_connection(('127.0.0.1', 5039), timeout=0.2)
        except ConnectionRefusedError:
            io.call(io.adb, '-P', '5039', '--one-device', SERIAL, 'start-server')
        else:
            probe.close()
        server = io.adb_call('server-status')
        if io.adb not in server or 'usb_backend: NATIVE' not in server:
            raise RuntimeError('exact existing private native SDK37 server required')
        before = protected()
        for name, data in before.items():
            (out / ('before-' + name + '.bin')).write_bytes(data)
        status['BCB'] = fresh_bcb(io, out)
        if protected() != before:
            raise RuntimeError('protected storage changed before boot')
        status['status'] = 'Recovery-prearmed'
        record()
        io.adb_call('reboot', 'bootloader')
        overall = io.deadline
        io.deadline = min(overall, time.monotonic() + 30)
        while True:
            try:
                product, slot = getvar(io, 'product'), getvar(io, 'current-slot')
            except subprocess.SubprocessError:
                if time.monotonic() >= io.deadline:
                    raise RuntimeError('bootloader unavailable;no bootstrap or retry')
                time.sleep(1)
                continue
            if product != 'zorn' or slot != 'a':
                raise RuntimeError('wrong actual fastboot product/slot;no boot')
            break
        io.deadline = overall
        if sha(pins['boot']['path']) != pins['boot']['sha256']:
            raise RuntimeError('boot image changed after approval')
        status.update(status='single-boot-attempt', boot_attempts=1)
        record()
        started = time.monotonic()
        try:
            output = io.call(io.fastboot, '-s', SERIAL, 'boot', pins['boot']['path'], timeout=60)
            status['fastboot_returned_success'] = True
        except subprocess.SubprocessError as error:
            output = str(error)
            status['fastboot_returned_success'] = False
        (out / 'fastboot.txt').write_text(output + '\n')
        while True:
            try:
                if io.adb_call('shell', 'getprop', 'ro.orangefox.boot', timeout=3) == '1':
                    break
            except subprocess.SubprocessError:
                pass
            if time.monotonic() >= io.deadline:
                raise RuntimeError('no Recovery within600s;STOP,no reboot/flash/retry')
            time.sleep(min(2, max(0, io.deadline - time.monotonic())))
        status['recovery_observed_seconds'] = time.monotonic() - started
        after = protected()
        for name, data in after.items():
            (out / ('after-' + name + '.bin')).write_bytes(data)
        if before != after:
            raise RuntimeError('protected root/Data/GPT/fences/log changed after trial')
        status.update(status='recovered-protected-storage-unchanged-console-result-unqualified',
                      root_mount_proven=False, desktop_proven=False)
    except BaseException as error:
        status.update(status='failed-device-operations-stopped', error=repr(error))
        raise
    finally:
        record()
        current = load(CURRENT)
        if current.get('active_run') == str(out):
            current['active_run'] = None
            current.setdefault('gpu_discovery', {})['latest_installed_root_boot_trial'] = str(out / 'run.json')
            if status['status'].startswith('failed'):
                current.update(stop_device_operations=True, stop_device_reason=status.get('error'))
            save(temporary, current, True)
            os.replace(temporary, CURRENT)
        print(json.dumps(status))


def main(spec=None):
    parser = argparse.ArgumentParser(description=__doc__)
    flag = spec['flag'] if spec else '--ios26-installed-root-trial'
    parser.add_argument(flag, dest='bundle', type=Path, required=True)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--admission', type=Path)
    args = parser.parse_args()
    if args.check_only:
        validate_bundle(args.bundle, spec)
        print(json.dumps({'host_inputs_match': True, 'allow_boot': False, 'claim_created': False,
                          'phone_accessed': False, 'scope': spec['scope'] if spec else SCOPE}))
        return
    if args.admission is None:
        parser.error('new exact owner admission required;no USB')
    bundle, claim = validate_admission(args.admission, args.bundle, spec)
    run(bundle, claim)


if __name__ == '__main__':
    main()

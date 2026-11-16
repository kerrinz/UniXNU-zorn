"""One explicitly admitted boot of the installed K80 iOS26 UFS root.

Validation/check-only never accesses USB or creates a claim. Execution needs
a current exact scoped admission of the transient kernel/loader carrier,
native UFS initialization/read-only root, RAMFS var and bounded Recovery.
Only the original native one-page log may change;root/Data remain read-only.
There is no install,GPU start or boot retry here.
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

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT/'out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90'
ARGS = 'rd=md0 -v keepsyms=1 houji_native_root=1 zorn26_root=1 zorn26_installed_root_trial=1 zorn_wdt=1 zorn26_prearmed_recovery=1 zorn26_trial_seconds=300 zorn26_userland_progress=1'
KERNEL_SHA = 'f8176652b1bfa5b32fe0cccce683ba15512d41017a78b2efd289ca634c3e4620'
FAT_SHA = 'f2eb85bfb2740f8841b98a964a6e8ef3bb8139dc6dbf18b582935bf412fae27e'
FD_SHA = '1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab'
ROOT_SHA = '6e46fbc832239eebd1bd63a4a248845cebd1200af9f5aef5eba4c69af7deb127'
NONCE = '0551535d07db45dca3a495a0d8252969'
DIRECTORY = 'k80-logdirs-boot26-0551535d07db45dca3a495a0d8252969/root-trial-logdirs'

SCOPE = 'single-K80-ios26-RAMFS-logdirs-launchd-CPU300s-v20'
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
                transient_kernel_loader=True, accepted_recovery='twrp-or-orangefox',
                existing_server_only=True, adb_server_port=5039,
                native_log_blocks=1, native_log_absolute_lba=49563392,
                native_log_write=True, native_misc_write=False, CPU_presenter=False,touch_startup=False,CPU_input_dependency_wait_seconds=30,userland_RAM_progress=True,userland_snapshot_seconds=90,native_board_preparation=False,native_RSC_programming=False,native_RSC_IRQ_operations=False)
PROTECTION_ROLES = {'primary_GPT', 'backup_GPT', 'root_manifest', 'Data_header',
                    'Data_metadata', 'root_first_page', 'root_before', 'root_after'}
ROLES = PROTECTION_ROLES | {'boot', 'FAT', 'fd', 'kernel', 'menu', 'ADT',
        'loader', 'manager', 'image_proof', 'installed_result', 'installed_evidence',
        'fixed_builder', 'fixed_runner', 'entry', 'device_helpers', 'recovery_identity', 'record_decoder', 'record_identity', 'record_helpers',
        'adb_binary', 'fastboot_binary', 'host_adb_proof','EL0_link_proof','source_build_proof'}


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


def protected_recovery(io, pins, accepted_recovery):
    from zorn_gpu_resource_trial import recovery

    state = recovery(io, pins, accepted_recovery=accepted_recovery)
    for name, lba, count in [('Data_metadata', 4194304, 65), ('root_first_page', 6291712, 1),
                             ('root_before', 6291711, 1), ('root_after', 14680320, 1)]:
        state[name] = io.read(PART, lba, count)
        if state[name] != Path(pins[name]['path']).read_bytes():
            raise RuntimeError('protected current root/Data/fence differs: ' + name)
    return state


def probe_existing_adb_listener():
    # TCP only. This does not send an ADB protocol request or contact a device.
    try:
        with socket.create_connection(('127.0.0.1', 5039), timeout=0.2):
            pass
    except OSError as error:
        raise RuntimeError('existing private ADB listener unreachable') from error


def require_existing_adb(io):
    probe_existing_adb_listener()
    server = io.adb_call('server-status')
    if io.adb not in server or 'usb_backend: NATIVE' not in server:
        raise RuntimeError('exact existing private native SDK37 server required')


def validate_bundle(path):
    path = Path(path)
    if path.is_symlink() or not path.resolve().is_relative_to(STAGE):
        raise ValueError('independent current root-boot bundle required')
    bundle = load(path)
    expected = EXPECTED
    if any(not equal(bundle.get(k), v) for k, v in expected.items()):
        raise ValueError('exact installed-UFS-root boot scope differs')
    pins = bundle.get('pins', {})
    roles = ROLES
    if set(pins) != roles:
        raise ValueError('complete exact input/protection roles required')
    for role, row in pins.items():
        source, archive = Path(row['path']), Path(row['archive'])
        if (not source.is_absolute() or not archive.is_absolute() or source.is_symlink() or
                archive.is_symlink() or not source.is_file() or not archive.is_file() or
                source.stat().st_ino == archive.stat().st_ino or
                sha(source) != row['sha256'] or sha(archive) != row['sha256']):
            raise ValueError('changed/shared source/archive: ' + role)
    fixed = {'entry': Path(__file__), 'recovery_identity': Path(__file__).with_name('zorn_recovery_identity.py'), 'record_helpers': Path(__file__).with_name('zorn_gpu_ios26_platform_record.py'),
             'fixed_builder': Path(__file__).with_name('build-zorn-debug.py'),
             'fixed_runner': Path(__file__).with_name('run-zorn-debug.py'),
             'device_helpers': Path(__file__).with_name('zorn_gpu_resource_trial.py')}
    if any(Path(pins[k]['path']).resolve() != p.resolve() for k, p in fixed.items()):
        raise ValueError('maintained fixed build/run/helper entry required')
    for role, expected in [('kernel', KERNEL_SHA), ('FAT', FAT_SHA), ('fd', FD_SHA)]:
        if pins[role]['sha256'] != expected:
            raise ValueError('current installed-root artifact differs: ' + role)
    if pins['ADT']['sha256'] != '3ff5fc7e4ffcee66277ace679f5a2d3dbcaa636115facd23210dc52959893302':
        raise ValueError('corrected loader relocation-slot ADT required')
    entry_proof=load(pins['EL0_link_proof']['path'])
    if (entry_proof.get('kernel_sha256')!=KERNEL_SHA or
            entry_proof.get('actual_argument_symbol')!='_rootdev' or
            entry_proof.get('actual_PID1_guard') is not True or
            entry_proof.get('actual_saved_state_64_flavor_guard')!=21 or
            entry_proof.get('actual_EL0_mode_mask_must_be_zero')!=31 or
            entry_proof.get('all_three_failed_guards_skip_record_call') is not True or
            entry_proof.get('registered_root_match_and_source_atomic_once_gate') is not True or
            entry_proof.get('new_transport_initialization_or_binding') is not False):
        raise ValueError('actual PID1/EL0/device-match one-shot source proof differs')
    result=load(pins['installed_result']['path']);installation=load(pins['installed_evidence']['path'])
    if (result.get('scope')!='K80-persistent-iOS26-root-logdirs-delta-v6' or
        result.get('phase')!='root-delta-installed-written-blocks-readback-verified' or
        result.get('installed') is not True or result.get('full_root_readback_performed') is not False or
        result.get('expected_image_sha256')!=ROOT_SHA or result.get('protected_metadata_and_fences_unchanged') is not True or
        installation.get('scope')!=result['scope'] or installation.get('new_root_sha256')!=ROOT_SHA or
        installation.get('relative_first_lba')!=6291712 or installation.get('blocks')!=8388608 or
        installation.get('complete_readback_required') is not False):
        raise ValueError('exact changed-page root installation/protection evidence required')
    for role in ['patch','delta','prior_install_receipt']:
        row=installation['pins'][role]
        if sha(row['path'])!=row['sha256'] or sha(row['archive'])!=row['sha256']:
            raise ValueError('root delta provenance changed: '+role)
    delta=load(installation['pins']['delta']['path']);previous=load(installation['pins']['prior_install_receipt']['path'])
    patch=Path(installation['pins']['patch']['path']).read_bytes();count=len(delta['pages'])
    written=b''.join(patch[i*8192+4096:(i+1)*8192] for i in range(count))
    if (delta['sha256']!=ROOT_SHA or result.get('historical_base_image_sha256')!=delta['source_sha256'] or
        previous.get('installed') is not True or previous.get('readback')!={'bytes':34359738368,'sha256':delta['source_sha256']} or
        result.get('pages_written')!=count or result.get('readback')!={'scope':'written4KiB-root-pages-only','blocks':count,'bytes':count*4096,'sha256':hashlib.sha256(written).hexdigest()}):
        raise ValueError('actual written-page readback and historical base chain differ')
    claim=load(Path(pins['installed_result']['path']).parent/'one-shot.claim.json')
    if claim.get('manifest_sha256')!=sha(pins['installed_evidence']['path']) or claim.get('consumed_before_first_USB') is not True or claim.get('reusable') is not False:
        raise ValueError('root update was not a matching consumed one-shot operation')
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
    if load(pins['record_identity']['path']).get('run_id') != NONCE:
        raise ValueError('fresh native artifact tag differs')
    code=Path(pins['kernel']['path']).read_bytes()
    if struct.unpack_from('<3I',code)!=(0xfeedfacf,0x100000c,0xc0000002):
        raise ValueError('actual arm64e kernel required')
    offset=32;versions=[]
    for _ in range(struct.unpack_from('<I',code,16)[0]):
        cmd,size=struct.unpack_from('<II',code,offset)
        if size<8 or offset+size>len(code):raise ValueError('bad Mach-O command')
        if cmd==0x32:versions.append(struct.unpack_from('<III',code,offset+8))
        offset+=size
    if versions!=[(2,26<<16,27<<16)]:raise ValueError('actual IOS26/SDK27 required')
    fat=Path(pins['FAT']['path']).read_bytes()
    marker=b'ZORNGHWD'+struct.pack('<II',1,0xfffffffe)
    if any(fat[i*512+0x180:i*512+0x190]!=marker for i in [0,6]):
        raise ValueError('both WDT1 markers required')
    if bundle.get('allow_boot') is not False:
        raise ValueError('artifact bundle must not impersonate execution admission')
    return bundle


def validate_admission(path, bundle_path):
    admission = load(path)
    expected = EXPECTED
    if any(not equal(admission.get(k), v) for k, v in expected.items()):
        raise ValueError('new exact root-boot admission required')
    if admission.get('allow_boot') is not True or admission.get('bundle_sha256') != sha(bundle_path):
        raise ValueError('distinct actual root-boot approval required')
    nonce = admission.get('nonce')
    if nonce != NONCE:
        raise ValueError('current unexecuted terminal artifact identity required')
    # This approval belongs to one canonical trial, not an arbitrary copy of
    # its bundle. Copying an approved manifest must not create a fresh claim.
    base = STAGE / DIRECTORY
    claim = Path(admission['claim'])
    if (Path(bundle_path).resolve() != base / 'bundle.json' or
            claim.resolve() != base / 'trial/one-shot.claim.json' or
            claim.is_symlink() or claim.exists() or not claim.parent.is_dir()):
        raise ValueError('canonical one-shot trial absent/consumed;no copied-scope replay')
    bundle = validate_bundle(bundle_path)
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
    if current.get('gpu_discovery', {}).get('current_mode') == 'unattended-offline-no-phone':
        raise ValueError('owner mode is offline/no-phone;no claim or USB')
    if any(current.get(k) for k in ['active_run', 'active_build', 'runner_session', 'stop_device_operations']):
        raise ValueError('another run/build or device-stop state exists')
    return bundle, claim


def run(bundle, claim, *, record_result=None):
    out, pins = claim.parent, bundle['pins']
    current = load(CURRENT)
    if any(current.get(k) for k in ['active_run','active_build','runner_session','stop_device_operations']) or current.get('gpu_discovery',{}).get('current_mode') == 'unattended-offline-no-phone':
        raise ValueError('current mode/run changed;no claim or USB')
    save(claim, {'scope': bundle['scope'], 'status': 'consumed-no-repeat',
                 'boot_sha256': pins['boot']['sha256'], 'before_first_USB': True}, True)
    current = load(CURRENT)
    current['active_run'] = str(out)
    temporary = CURRENT.with_name('current.installed-root-boot.tmp')
    save(temporary, current, True)
    os.replace(temporary, CURRENT)
    from zorn_gpu_resource_trial import Transport, fresh_bcb, getvar

    class Capture(Transport):
        def __init__(self):
            self.adb, self.fastboot = pins['adb_binary']['path'], pins['fastboot_binary']['path']
            # The bundle field already existed; it used to be ignored in favour of a
            # fixed 600s. 1500s is the one reviewed longer value, for the 1080s trial.
            self.deadline_seconds = bundle['timeout_seconds']
            if self.deadline_seconds not in (600, 1500):
                raise ValueError('host deadline must be the reviewed 600s or 1500s value')
            self.deadline, self.sequence = time.monotonic() + self.deadline_seconds, 0

        def execute(self, args, timeout):
            left = self.deadline - time.monotonic()
            if left <= 0:
                raise subprocess.TimeoutExpired(args, timeout)
            env = os.environ.copy()
            for key in ['ADB_SERVER_SOCKET', 'ANDROID_ADB_SERVER_PORT', 'ANDROID_SERIAL', 'ADB_TRACE']:
                env.pop(key, None)
            env.update(ADB_LIBUSB='0', ADB_MDNS_AUTO_CONNECT='0')
            return subprocess.run(list(map(str, args)), env=env, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, timeout=min(timeout, left))

        def call(self, *args, binary=False, timeout=20):
            if time.monotonic() >= self.deadline:
                raise RuntimeError(f'overall {self.deadline_seconds}s deadline expired;stop device operations')
            self.sequence += 1
            stem = out / f'command-{self.sequence:03d}'
            save(stem.with_suffix('.json'), {'arguments': list(map(str, args))}, True)
            try:
                p = self.execute(args, timeout)
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

        def probe_recovery(self):
            from zorn_recovery_identity import PROPERTIES, inspect_recovery

            properties = {}
            for key in PROPERTIES:
                result = self.execute((self.adb, '-H', '127.0.0.1', '-P', '5039', '-s', SERIAL,
                                       'shell', 'getprop', key), 3)
                result.check_returncode()
                properties[key] = (result.stdout + result.stderr).decode().strip()
            return inspect_recovery(properties)

    io = Capture()
    status = {'scope': bundle['scope'], 'status': 'claimed', 'GPU_started': False,
              'root_mount_proven': False, 'desktop_proven': False, 'boot_attempts': 0}
    def record():
        pending = out / 'run.json.pending'
        save(pending, status)
        os.replace(pending, out / 'run.json')
    try:
        record()
        require_existing_adb(io)
        before = protected_recovery(io, pins, bundle['accepted_recovery'])
        for name, data in before.items():
            (out / ('before-' + name + '.bin')).write_bytes(data)
        from zorn_gpu_ios26_platform_record import artifact_tag, record_inspector
        oldlog = io.read(PART,2291712,1)
        (out/'before-log.bin').write_bytes(oldlog)
        if oldlog[:24] == b'HJPAN026'+artifact_tag(bundle):
            raise RuntimeError('same artifact already captured;consumed,no boot')
        status['recovery_identity_before'] = io.recovery_identity
        status['BCB'] = fresh_bcb(io, out)
        if protected_recovery(io, pins, bundle['accepted_recovery']) != before:
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
        status['recovery_poll_attempts'] = 0
        while time.monotonic() < io.deadline:
            status['recovery_poll_attempts'] += 1
            try:
                status['recovery_poll_identity'] = io.probe_recovery()
                break
            except (subprocess.SubprocessError,ValueError):
                pass
            time.sleep(min(2, max(0, io.deadline - time.monotonic())))
        else:
            raise RuntimeError(f'no Recovery within {io.deadline_seconds}s;STOP,no reboot/flash/retry')
        status['recovery_observed_seconds'] = time.monotonic() - started
        after = protected_recovery(io, pins, bundle['accepted_recovery'])
        for name, data in after.items():
            (out / ('after-' + name + '.bin')).write_bytes(data)
        if before != after:
            raise RuntimeError('protected root/Data/GPT/fences changed after trial')
        status['recovery_identity_after']=io.recovery_identity
        newlog=io.read(PART,2291712,1);(out/'after-log.bin').write_bytes(newlog)
        status.update(status='recovered-protected-storage-unchanged-root-unqualified',
                      root_mount_proven=False, desktop_proven=False,PID1_image_activation_proven=False,user_mode_instructions_proven=False,
                      log_changed=newlog!=oldlog,native_writer_readback_success_proven=False)
        try:
            decoded=record_inspector(bundle)(newlog,artifact_tag(bundle),oldlog)
            save(out/'decoded-native-record.json',decoded)
            if record_result is not None:
                status.update(record_result(decoded))
            elif decoded['can_support_fresh_trial_when_bound_to_actual_capture_and_bundle']:
                status.update(status='recovered-fresh-PID1-userland-progression',root_mount_proven=True,PID1_image_activation_proven=True,user_mode_instructions_proven=True,actual_userland_progress=decoded['actual_userland_progress'],syscall_dispatch_return_observed=decoded['actual_userland_progress']['returns']>0,lockscreen_proven=False)
        except ValueError as error:
            status['native_record_refusal']=str(error)

    except BaseException as error:
        status.update(status='failed-device-operations-stopped', error=repr(error))
        raise
    finally:
        try:
            record()
        except OSError as error:
            status['final_archive_error'] = repr(error)
            raise
        finally:
            current = load(CURRENT)
            if current.get('active_run') == str(out):
                current['active_run'] = None
                if 'final_archive_error' not in status:
                    current.setdefault('gpu_discovery', {})['latest_installed_root_boot_trial'] = str(out / 'run.json')
                if status['status'].startswith('failed') or 'final_archive_error' in status:
                    current.update(stop_device_operations=True,
                                   stop_device_reason=status.get('error') or status['final_archive_error'])
                save(temporary, current, True)
                os.replace(temporary, CURRENT)
            print(json.dumps(status))


def finish_recovery():
    """Recover evidence from the last interrupted trial through read-only Recovery."""
    parser = argparse.ArgumentParser(description=finish_recovery.__doc__)
    parser.add_argument('--ios26-finish-recovery', type=Path, required=True)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    ready_path = args.ios26_finish_recovery.resolve()
    current = load(CURRENT)
    gpu = current['gpu_discovery']
    incident_path = Path(gpu['latest_installed_root_boot_trial'])
    trial = incident_path.parent
    out = trial / 'delayed-recovery-read'
    bundle_path = trial.parent / 'bundle.json'
    incident, bundle, ready = load(incident_path), load(bundle_path), load(ready_path)
    if (ready_path != out / 'ready.json' or not trial.resolve().is_relative_to(STAGE)
            or incident_path.name != 'host-archive-failure.json'
            or incident['status'] != 'host-archive-failed-after-one-boot'
            or incident['recovery_visible'] is not True
            or current.get('stop_device_operations') is not True
            or current.get('stop_device_reason') != incident['reason']
            or gpu.get('current_mode') != 'attended-phone-connected'
            or any(current.get(k) for k in ('active_run', 'active_build', 'runner_session'))
            or ready != dict(scope='K80-delayed-Recovery-read-only', serial=SERIAL, product='zorn', slot='a',
                             incident_sha256=sha(incident_path), bundle_sha256=sha(bundle_path),
                             runner_sha256=sha(Path(__file__).with_name('run-zorn-debug.py')),
                             entry_sha256=sha(__file__), timeout_seconds=60, device_writes=False, boots=False)):
        raise ValueError('exact interrupted trial and read-only readiness required')
    for name, role in [('run-zorn-debug.py', 'runner'), (Path(__file__).name, 'entry')]:
        source, archive = Path(__file__).with_name(name), out / name
        if source.samefile(archive) or sha(archive) != ready[role + '_sha256']:
            raise ValueError('missing independent fixed runner input: ' + name)
    claim_path = trial / 'one-shot.claim.json'
    claim = load(claim_path)
    pins = bundle['pins']
    if (claim['scope'] != incident['scope'] or claim['scope'] != bundle['scope']
            or claim['status'] != 'consumed-no-repeat' or claim['before_first_USB'] is not True
            or claim['boot_sha256'] != pins['boot']['sha256']
            or any(bundle.get(k) != v for k, v in dict(serial=SERIAL, product='zorn', slot='a',
                       accepted_recovery='twrp-or-orangefox', adb_server_port=5039).items())
            or any(sha(path) != digest for path, digest in incident['files'].items())):
        raise ValueError('interrupted trial evidence changed')
    for role in PROTECTION_ROLES | {'adb_binary', 'host_adb_proof', 'device_helpers', 'recovery_identity',
                                     'record_helpers', 'record_decoder', 'record_identity'}:
        row = pins[role]
        source, archive = Path(row['path']), Path(row['archive'])
        if source.samefile(archive) or sha(source) != row['sha256'] or sha(archive) != row['sha256']:
            raise ValueError('interrupted trial input changed: ' + role)
    if args.check_only:
        print(json.dumps({'ready': True, 'phone_accessed': False, 'boots': False}))
        return

    from zorn_gpu_resource_trial import Transport
    from zorn_gpu_ios26_platform_record import artifact_tag, record_inspector

    save(out / 'one-shot.claim.json', dict(scope=ready['scope'], ready_sha256=sha(ready_path),
                                         consumed_before_first_USB=True, reusable=False), True)
    io = Transport(adb_server_port=5039)
    io.adb = pins['adb_binary']['path']
    io.deadline = time.monotonic() + ready['timeout_seconds']
    result = dict(scope=ready['scope'], device_writes=False, boots=False)
    try:
        require_existing_adb(io)
        protected = protected_recovery(io, pins, bundle['accepted_recovery'])
        for name, data in protected.items():
            if data != (trial / ('before-' + name + '.bin')).read_bytes():
                raise RuntimeError('pre-trial protected storage differs: ' + name)
        result.update(recovery_identity=io.recovery_identity, protected_storage_unchanged=True)
        page = io.read(PART, 2291712, 1)
        with (out / 'after-log.bin').open('xb') as stream:
            stream.write(page)
        before = (trial / 'before-log.bin').read_bytes()
        result.update(log_changed=page != before, after_log_sha256=hashlib.sha256(page).hexdigest())
        try:
            decoded = record_inspector(bundle)(page, artifact_tag(bundle), before)
        except ValueError as error:
            result['native_record_refusal'] = str(error)
        else:
            save(out / 'decoded-native-record.json', decoded, True)
        result['status'] = 'Recovery-verified-delayed-diagnostic-read'
    except BaseException as error:
        result.update(status='failed-device-operations-remain-stopped', error=repr(error))
        raise
    finally:
        save(out / 'result.json', result, True)
        print(json.dumps(result))
    if load(CURRENT) != current:
        raise RuntimeError('current state changed during delayed Recovery read')
    current.update(stop_device_operations=False, stop_device_reason=None)
    gpu['latest_installed_root_boot_trial'] = str(out / 'result.json')
    pending = CURRENT.with_name('current.delayed-recovery.tmp')
    save(pending, current, True)
    os.replace(pending, CURRENT)


def main(mode="run"):
    parser = argparse.ArgumentParser(description=__doc__)
    flag = '--ios26-logdirs-boot-image' if mode == 'build' else '--ios26-logdirs-boot-trial'
    parser.add_argument(flag, dest='bundle', type=Path, required=True)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--admission', type=Path)
    args = parser.parse_args()
    if mode == 'build' and not args.check_only:
        parser.error('current exact package already built;use --check-only')
    if args.check_only:
        validate_bundle(args.bundle)
        print(json.dumps({'host_inputs_match': True, 'allow_boot': False, 'claim_created': False,
                          'phone_accessed': False, 'scope': SCOPE}))
        return
    if args.admission is None:
        parser.error('new exact owner admission required;no USB')
    bundle, claim = validate_admission(args.admission, args.bundle)
    run(bundle, claim)


if __name__ == '__main__':
    main()

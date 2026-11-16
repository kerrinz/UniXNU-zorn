"""Fixed entry for one exact finite K80 iOS26 FT3683 trial."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import socket
import subprocess
import sys
import time

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'UniXNU-zorn/scripts').is_dir())
SCRIPTS = ROOT / 'UniXNU-zorn/scripts'
CURRENT = ROOT / 'out/zorn/unattended-active/current.json'
BUILDS = ROOT / 'out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90'
REVIEW = BUILDS / 'k80-ft3683-current-root-power26-1f77e414c8c641b4ac1914153cc0c5f3/trial-review'
HOST_SHA = 'd40ffca2561a7947a8582df435fe2ec47ed8c02548554d592423cd2d700f8fd6'
BUILD_INPUTS_SHA = '71eb6647b17115218974c2dd8c51bbcb0e27e6a092490ed44bb4d24daf374841'
TRIAL = REVIEW / 'trial'
SCOPE = 'single-K80-ios26-FT3683-current-root-power-300s-1f77e414'
NONCE = '1f77e414c8c641b4ac1914153cc0c5f3'
WATCHDOG_SECONDS = 300
HISTORICAL_SCOPES = {
    BUILDS / 'k80-ft3683-power-handoff26-4fd550b0b4f141f6908687f32e9ad368/trial-review/reviewed-inputs.json': (
        'ecf979d80bcf8093af08a89985231cc0f527c72eeaf4051f1db6a017251f4f43', 'b4bd6ead1655528301264b61df9487fbd5f4ef71bacc1732e75a226f866b7fd2',
        'single-K80-ios26-FT3683-power-handoff-300s-4fd550b0', '4fd550b0b4f141f6908687f32e9ad368', 300,
    ),
    BUILDS / 'k80-ft3683-capture-result26-066d546e71774b4b8c0a81e6e8d2d918/trial-review/reviewed-inputs.json': (
        'c600309300ab2b8e66d662d28bc449edda27f8c2254c1b8e6a06ffc6cc17f655', '6e5f9553a0be478ba1269fcffc67eb42966aab865ae7d48b05baf0ac69d7af1d',
        'single-K80-ios26-FT3683-capture-result-300s-066d546e', '066d546e71774b4b8c0a81e6e8d2d918', 300,
    ),
    BUILDS / 'k80-ft3683-userland-checkpoint26-443f950ac6a4439b89bd0e112678b02f/trial-review/reviewed-inputs.json': (
        '1849b958a40b4b733ff6f686fbac6012d156bd9fde5714ae91f0ad296faf7e93', '292ff13d18d09b00136c8950cc548034992a7bbe7f886bc64597c2d81d3a835e',
        'single-K80-ios26-FT3683-userland-checkpoint-300s-443f950a', '443f950ac6a4439b89bd0e112678b02f', 300,
    ),
    BUILDS / 'k80-touch-current-display26-5b2e86dbb4e946dfa7016fa635c2c831/trial-review/reviewed-inputs.json': (
        '655165ebbcba94c4a20d2f5c909addc3ddabffff8253a76973633b422652558f', '0f6c9c3ef74e1bef739e6e529fab1f5a831fd88117863113565a821e03fff2ff',
        'single-K80-ios26-FT3683-display-finite64-300s-5b2e86db', '5b2e86dbb4e946dfa7016fa635c2c831', 300,
    ),
    BUILDS / 'k80-touch-installed-lifetime-root26-864de56c132a45c6bc5124c03aedbdf8/trial-review/reviewed-inputs.json': (
        '24be9814019c42241bfd75207921a9d7e9b1fa4fd669ab1dcbf3d2d6e043e0f9',
        '4e8cdeb67d4a11aabdf0b72b1e322804e4ac6b038dc29c57df366c8a708f7d47',
        'single-K80-ios26-FT3683-finite64-90s-864de56c', '864de56c132a45c6bc5124c03aedbdf8', 90,
    ),
    BUILDS / 'k80-touch-hid-client-lifetime-finite26-49f9ffe9a317475789b359fb4f0b5015/trial-review/reviewed-inputs.json': (
        '8c150a148864ff0572aa484f834135cf0e7e6aa8d5f9a6ab5b339ab8719dc513',
        '78628579daa3b3dd86cf6995d7f4a2187ecc6a6b505bc8aea81743ea08114453',
        'single-K80-ios26-FT3683-finite64-90s-49f9ffe9', '49f9ffe9a317475789b359fb4f0b5015', 90,
    ),
    BUILDS / 'k80-touch-worker-finite26-e2b4adfa8c624a5bbdd867b856dde842/trial-review/reviewed-inputs.json': (
        '866e530031620437cc57290ccc3011fc010e70606e2f74d479532467b8f7fead',
        '2751c193032cc6d63902df02c31580a82db0b5a78e3ee3c35941bae4f5450ea1',
        'single-K80-ios26-FT3683-finite64-90s-e2b4adfa', 'e2b4adfa8c624a5bbdd867b856dde842', 90,
    ),
}
SERIAL = '92988a43'
PART = '/dev/block/by-name/unixnu'
LOG_LBA = 2291712

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


def verify_inputs(pins):
    for role, pin in pins.items():
        source, archive = Path(pin['path']), Path(pin['archive'])
        for file in (source, archive):
            if (file.is_symlink() or not file.is_file() or
                    file.stat().st_size != pin['bytes'] or sha(file) != pin['sha256']):
                raise ValueError('changed exact input: ' + role)
        if source.samefile(archive):
            raise ValueError('archive shares source inode: ' + role)


def verify_link_archive(pins, reviewed):
    rows = load(pins['link_inputs']['path'])
    command = load(pins['link_command']['path'])['arguments']
    filelist = Path(pins['link_filelist']['path'])
    proof = load(reviewed['pins']['image_proof']['path'])['link']
    paths = [row['path'] for row in rows]
    ordered = filelist.read_text().splitlines()
    path_set = set(paths)
    ordered.extend(arg for arg in command if arg in path_set)
    if (len(path_set) != proof['inputs'] or ordered != paths or
            command[command.index('-filelist') + 1] != str(filelist) or
            command[command.index('-o') + 1] != proof['kernel']):
        raise ValueError('FT3683 archived link command does not match its input list')
    for row in rows:
        obj = Path(row['path'])
        original = Path(row['replacement'] or row['prior_input'])
        if (obj.parent != filelist.parent / 'inputs' or obj.is_symlink() or
                obj.samefile(original) or obj.stat().st_size != row['bytes'] or
                sha(obj) != row['sha256']):
            raise ValueError('changed or shared link input: ' + obj.name)
    installed = load(pins['installed_evidence']['path'])
    receipt = load(reviewed['pins']['installed_result']['path'])
    if (installed['scope'] != receipt['scope'] or
            installed['new_root_sha256'] != receipt['expected_image_sha256'] or
            installed['relative_first_lba'] != 6291712 or
            installed['blocks'] != 8388608 or installed['complete_readback_required'] is not False):
        raise ValueError('changed-page UFS installation evidence differs')
    return len(rows)


def validate_bundle(path, *, check_only=False):
    if path == REVIEW / 'reviewed-inputs.json':
        selected = HOST_SHA, BUILD_INPUTS_SHA, SCOPE, NONCE, WATCHDOG_SECONDS
    elif check_only and path in HISTORICAL_SCOPES:
        selected = HISTORICAL_SCOPES[path]
    else:
        raise ValueError('canonical FT3683 review required for this mode')

    host_sha, build_inputs_sha, scope, nonce, watchdog_seconds = selected
    host_file = path.parent / 'runner-candidate/host-inputs.json'
    build_inputs_file = path.parent / 'fixed-entry-archive/exact-build-inputs.json'
    if sha(host_file) != host_sha or sha(build_inputs_file) != build_inputs_sha:
        raise ValueError('canonical FT3683 review and exact host-input manifest required')
    host = load(host_file)
    # The historical dispatcher copies are for patch review. A live fixed
    # installation is checked against its own fresh approval before execution.
    verify_inputs({k: v for k, v in host.items() if not k.startswith('fixed_')})
    reviewed = load(path)
    if (reviewed['scope'] != scope or reviewed['record_id'] != nonce or
            reviewed['watchdog_seconds'] != watchdog_seconds or reviewed['host_deadline_seconds'] != 600 or
            reviewed['device_ready'] is not False or reviewed['allow_boot'] is not False):
        raise ValueError('incorrect finite FT3683 scope')
    verify_inputs(reviewed['pins'])
    build_inputs = load(build_inputs_file)
    verify_inputs(build_inputs)
    link_inputs = verify_link_archive(build_inputs, reviewed)
    checker = runpy.run_path(host['checker']['path'])
    checked = checker['check_package'](Path(reviewed['pins']['image_proof']['path']))
    if (checked['record_run_id'] != nonce or
            checked['watchdog_seconds'] != watchdog_seconds or
            checked['boot_sha256'] != reviewed['pins']['boot']['sha256'] or
            checked['kernel_sha256'] != reviewed['pins']['kernel']['sha256']):
        raise ValueError('FT3683 package does not match the reviewed boot and kernel')
    pins = reviewed['pins'] | {k: host[k] for k in ('adb_binary', 'fastboot_binary')}
    bundle = reviewed | {'pins': pins, 'accepted_recovery': 'twrp-or-orangefox',
                         'verified_link_inputs': link_inputs}
    return bundle, checker


def require_device_gate(current, expected_root=None):
    gpu = current.get('gpu_discovery', {})
    if (gpu.get('current_mode') != 'unattended-phone-connected' or
            gpu.get('allow_boot') is not True or
            (expected_root is not None and gpu.get('current_phone_root_expected_sha256') != expected_root) or
            gpu.get('active_admission') != str(TRIAL / 'admission.json') or
            any(current.get(k) for k in ('active_run', 'active_build', 'runner_session', 'stop_device_operations'))):
        raise ValueError('current K80 device admission is closed; no claim or USB')


def validate_admission(path, bundle_path, bundle):
    if (Path(__file__).resolve().parent != SCRIPTS or
            Path(sys.argv[0]).resolve() != SCRIPTS / 'run-zorn-debug.py'):
        raise ValueError('only the maintained fixed runner may execute; candidate is offline')
    expected_root = load(bundle['pins']['installed_result']['path'])['expected_image_sha256']
    require_device_gate(load(CURRENT), expected_root)
    if path != TRIAL / 'admission.json' or TRIAL.resolve() != TRIAL or path.is_symlink():
        raise ValueError('fresh canonical FT3683 admission required')
    claim = TRIAL / 'one-shot.claim.json'
    if claim.exists() or claim.is_symlink():
        raise ValueError('FT3683 claim already consumed')
    binding = dict(scope=SCOPE, nonce=NONCE, bundle_sha256=sha(bundle_path),
                   boot_sha256=bundle['pins']['boot']['sha256'], allow_boot=True)
    expected = binding | dict(serial=SERIAL, product='zorn', slot='a',
                    trial_seconds=WATCHDOG_SECONDS, timeout_seconds=600, watchdog_mode=1,
                    retries=0, bootstrap_allowed=False, GPU_startup=False,
                    accepted_recovery='twrp-or-orangefox', full_root_readback=False,
                    fixed_builder_sha256=sha(SCRIPTS / 'build-zorn-debug.py'),
                    fixed_runner_sha256=sha(SCRIPTS / 'run-zorn-debug.py'),
                    entry_sha256=sha(Path(__file__)), claim=str(claim))
    expected['touch_power_handoff'] = True
    admission = load(path)
    if any(not equal(admission.get(k), v) for k, v in expected.items()):
        raise ValueError('exact scoped FT3683 admission required')
    for role in ('owner', 'ready'):
        actual = TRIAL / (role + '.json')
        row = admission[role]
        if row['path'] != str(actual) or actual.is_symlink() or row['sha256'] != sha(actual):
            raise ValueError('fresh independent FT3683 ' + role + ' required')
        value = load(actual)
        checks = expected | ({'approved': True} if role == 'owner' else {'ready': True})
        if any(not equal(value.get(k), v) for k, v in checks.items()):
            raise ValueError('incorrect FT3683 ' + role)
    return claim


def run(bundle, claim, checker):
    out, pins = claim.parent, bundle['pins']
    current = load(CURRENT)
    expected_root = load(pins['installed_result']['path'])['expected_image_sha256']
    require_device_gate(current, expected_root)
    save(claim, {'scope': bundle['scope'], 'status': 'consumed-no-repeat',
                 'boot_sha256': pins['boot']['sha256'], 'nonce': NONCE,
                 'bundle_sha256': sha(REVIEW / 'reviewed-inputs.json'),
                 'before_first_USB': True}, True)
    current = load(CURRENT)
    require_device_gate(current, expected_root)
    current['active_run'] = str(out)
    temporary = CURRENT.with_name('current.ft3683-trial.tmp')
    save(temporary, current, True)
    os.replace(temporary, CURRENT)
    from zorn_gpu_resource_trial import Transport, recovery, fresh_bcb, getvar

    class Capture(Transport):
        def __init__(self):
            self.adb, self.fastboot = pins['adb_binary']['path'], pins['fastboot_binary']['path']
            self.deadline = time.monotonic() + bundle['host_deadline_seconds']
            self.sequence = 0

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
        state = recovery(io, pins, accepted_recovery=bundle['accepted_recovery'])
        for name, observed in (('Data_before', 'before'), ('Data_after', 'after')):
            if state[observed] != Path(pins[name]['path']).read_bytes():
                raise RuntimeError('protected Data fence differs: ' + name)
        exact = [('Data_metadata', 4194304, 65), ('root_first_page', 6291712, 1),
                 ('root_before', 6291711, 1), ('root_after', 14680320, 1)]
        for name, lba, count in exact:
            state[name] = io.read(PART, lba, count)
            if state[name] != Path(pins[name]['path']).read_bytes():
                raise RuntimeError('protected current root/Data/fence differs: ' + name)
        return state
    record()
    try:
        try:
            probe = socket.create_connection(('127.0.0.1', 5039), timeout=0.2)
        except ConnectionRefusedError:
            raise RuntimeError('existing private server unavailable;no bootstrap')
        else:
            probe.close()
        server = io.adb_call('server-status')
        if io.adb not in server or 'usb_backend: NATIVE' not in server:
            raise RuntimeError('exact existing private native SDK37 server required')
        before = protected()
        for name, data in before.items():
            (out / ('before-' + name + '.bin')).write_bytes(data)
        oldlog = io.read(PART, LOG_LBA, 1)
        (out / 'before-log.bin').write_bytes(oldlog)
        if oldlog[:24] == b'HJPAN026' + bytes.fromhex(NONCE):
            raise RuntimeError('same artifact already captured;consumed,no boot')
        status['recovery_identity_before'] = io.recovery_identity
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
                from zorn_recovery_identity import PROPERTIES, inspect_recovery
                properties={key:io.adb_call('shell','getprop',key,timeout=3) for key in PROPERTIES}
                inspect_recovery(properties)
                break
            except (subprocess.SubprocessError,ValueError):
                pass
            if time.monotonic() >= io.deadline:
                raise RuntimeError('no Recovery within600s;STOP,no reboot/flash/retry')
            time.sleep(min(2, max(0, io.deadline - time.monotonic())))
        status['recovery_observed_seconds'] = time.monotonic() - started
        after = protected()
        for name, data in after.items():
            (out / ('after-' + name + '.bin')).write_bytes(data)
        if before != after:
            raise RuntimeError('protected root/Data/GPT/fences changed after trial')
        status['recovery_identity_after']=io.recovery_identity
        newlog = io.read(PART, LOG_LBA, 1)
        (out / 'after-log.bin').write_bytes(newlog)
        status.update(status='recovered-without-qualified-FT3683-record',
                      log_changed=newlog != oldlog,
                      full_root_readback=False, touch_input_delivery_proven=False)
        try:
            decoded = checker['decode'](newlog, oldlog)
            save(out / 'decoded-touch-record.json', decoded)
            status.update(root_mount_proven=True, PID1_EL0_observed=True)
            if decoded.get('touch_snapshot_available') is False:
                status.update(status='recovered-fresh-userland-without-FT3683-snapshot',
                              actual_userland_progress=decoded['actual_userland_progress'])
            else:
                status.update(status='recovered-fresh-FT3683-snapshot', finite_touch_snapshot=decoded)
        except ValueError as error:
            status['native_record_refusal'] = str(error)

    except BaseException as error:
        status.update(status='failed-device-operations-stopped', error=repr(error))
        raise
    finally:
        record()
        current = load(CURRENT)
        if current.get('active_run') == str(out):
            current['active_run'] = None
            gpu = current.setdefault('gpu_discovery', {})
            gpu['latest_FT3683_trial'] = str(out / 'run.json')
            if gpu.get('active_admission') == str(out / 'admission.json'):
                gpu.update(active_admission=None, allow_boot=False)
            if status['status'].startswith('failed'):
                current.update(stop_device_operations=True, stop_device_reason=status.get('error'))
            save(temporary, current, True)
            os.replace(temporary, CURRENT)
        print(json.dumps(status))


def main(mode='run'):
    parser = argparse.ArgumentParser(description=__doc__)
    selector = '--ios26-ft3683-image' if mode == 'build' else '--ios26-ft3683-trial'
    parser.add_argument(selector, type=Path, required=True, dest='bundle')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--admission', type=Path)
    args = parser.parse_args()
    if args.check_only and args.admission is not None:
        parser.error('check-only accepts no admission')
    if not args.check_only:
        if mode != 'run' or args.admission is None:
            parser.error('an exact new FT3683 admission is required; no claim or USB')
        if Path(__file__).resolve().parent != SCRIPTS:
            parser.error('isolated FT3683 fixed-entry candidate is offline only')
    try:
        if not args.check_only:
            require_device_gate(load(CURRENT))
        bundle, checker = validate_bundle(args.bundle, check_only=args.check_only)
        if args.check_only:
            print(json.dumps(dict(scope=bundle['scope'], boot_sha256=bundle['pins']['boot']['sha256'],
                                  verified_link_inputs=bundle['verified_link_inputs'],
                                  archived_inputs_match=True, allow_boot=False,
                                  claim_created=False, phone_accessed=False)))
            return
        claim = validate_admission(args.admission, args.bundle, bundle)
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))
    run(bundle, claim, checker)

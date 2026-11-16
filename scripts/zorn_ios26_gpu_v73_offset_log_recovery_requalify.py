"""One-shot read-only Recovery requalification with corrected data/log references.

The first requalification attempt incorrectly read unixnu-relative LBA 4194303
as Data_header. The retained Data partition starts at LBA 4194304. This new
scope verifies that preceding guard separately, then verifies the actual Data
header and metadata. The diagnostic log page is checked against the exact last
known device capture (v60), not the different CPU-run log capture. It never
boots or writes the phone.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / 'out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90'
CURRENT = ROOT / 'out/zorn/unattended-active/current.json'
RUNNER = Path(__file__).with_name('run-zorn-debug.py')
IDENTITY_HELPER = Path(__file__).with_name('zorn_recovery_identity.py')
CPU = STAGE / 'k80-cpu-keystore-retag26-b0da41e98417481f979a24106c21f3bc/root-trial-cpu-keystore-retag'
CPU_TRIAL = CPU / 'trial'
CPU_BUNDLE = CPU / 'bundle.json'
INCIDENT = ROOT / 'UniXNU-zorn/docs/evidence/k80-gpu-v73-provider-census-recovery-stop-2026-11-13.json'
V1_OUT = STAGE / 'k80-gpu-v73-recovery-requalify-readonly-20261113-01'
V1_RESULT = V1_OUT / 'result.json'
V73_TRIAL = STAGE / 'k80-gpu-v73-provider-census-20261113/root-trial-provider-census-v73-predevice-004/trial'
V73_PRE_DATA_GUARD = V73_TRIAL / 'command-022.stdout'
V2_OUT = STAGE / 'k80-gpu-v73-offset-recovery-requalify-readonly-20261113-02'
V2_RESULT = V2_OUT / 'result.json'
V60_TRIAL = STAGE / 'k80-native-smmu-readonly-census-v60-06a3d3fbe6124d6e9f1cd2fada451e95/root-trial-native-smmu-readonly-census-v60/trial'
V60_RUN = V60_TRIAL / 'run.json'
V60_LOG = V60_TRIAL / 'after-log.bin'
V60_EVIDENCE = ROOT / 'UniXNU-zorn/docs/evidence/k80-native-SMMU-readonly-bank-stream-census-observed-2026-11-13.json'
OUT = STAGE / 'k80-gpu-v73-offset-log-recovery-requalify-readonly-20261113-03'
SCOPE = 'single-K80-ios26-GPU-v73-corrected-offset-known-log-recovery-requalification-readonly-20261113'
SERIAL = '92988a43'
STOP_REASON = "RuntimeError('protected current root/Data/fence differs: root_first_page')"
ROOT_PART = '/dev/block/by-name/unixnu'
MISC_PART = '/dev/block/by-name/misc'
BASELINE_LOG_LBA = 2291712
TIMEOUT_SECONDS = 90


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def save(path, value, exclusive=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x' if exclusive else 'w') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def file_hashes_match(before, after):
    return before.is_file() and after.is_file() and before.read_bytes() == after.read_bytes()


def state_is_requalifiable(state):
    gpu = state.get('gpu_discovery', {})
    return (state.get('stop_device_operations') is True and
            state.get('stop_device_reason') == STOP_REASON and
            not any(state.get(k) for k in ('active_run', 'active_build', 'active_admission', 'runner_session')) and
            gpu.get('current_mode') != 'unattended-offline-no-phone' and
            gpu.get('allow_boot') is False and not gpu.get('active_admission'))


def expected_inputs():
    cpu_bundle = load(CPU_BUNDLE)
    incident = load(INCIDENT)
    run = load(CPU_TRIAL / 'run.json')
    refs = {
        'primary_GPT': Path(cpu_bundle['pins']['primary_GPT']['path']),
        'backup_GPT': Path(cpu_bundle['pins']['backup_GPT']['path']),
        'root_manifest': Path(cpu_bundle['pins']['root_manifest']['path']),
        'Data_header': Path(cpu_bundle['pins']['Data_header']['path']),
        'Data_metadata': CPU_TRIAL / 'after-Data_metadata.bin',
        'pre_data_guard': V73_PRE_DATA_GUARD,
        'root_first_page': CPU_TRIAL / 'after-root_first_page.bin',
        'root_before': CPU_TRIAL / 'after-root_before.bin',
        'root_after': CPU_TRIAL / 'after-root_after.bin',
        'CPU_before_Data_metadata': CPU_TRIAL / 'before-Data_metadata.bin',
        'CPU_before_root_first_page': CPU_TRIAL / 'before-root_first_page.bin',
        'CPU_before_root_before': CPU_TRIAL / 'before-root_before.bin',
        'CPU_before_root_after': CPU_TRIAL / 'before-root_after.bin',
        'BCB_reference': CPU_TRIAL / 'misc-readback.bin',
        'CPU_native_log_reference': CPU_TRIAL / 'after-log.bin',
        'native_log_reference': V60_LOG,
        'CPU_run': CPU_TRIAL / 'run.json',
        'CPU_bundle': CPU_BUNDLE,
        'v73_stop_incident': INCIDENT,
        'v1_failed_requalification': V1_RESULT,
        'v2_failed_requalification': V2_RESULT,
        'v60_device_run': V60_RUN,
        'v60_device_evidence': V60_EVIDENCE,
        'current_state': CURRENT,
        'adb_binary': Path(cpu_bundle['pins']['adb_binary']['path']),
        'fixed_runner': RUNNER,
        'entry': Path(__file__),
        'recovery_identity_helper': IDENTITY_HELPER,
    }
    return refs, cpu_bundle, incident, run


def verify_historical_evidence():
    refs, cpu_bundle, incident, cpu_run = expected_inputs()
    required_cpu = (
        cpu_run.get('scope') == 'single-K80-ios26-CPU-keystore-retag-300s-b0da41e9' and
        cpu_run.get('status') == 'recovered-fresh-PID1-userland-progression' and
        cpu_run.get('root_mount_proven') is True and cpu_run.get('GPU_started') is False
    )
    if not required_cpu:
        raise ValueError('exact recovered CPU lockscreen-base run required')
    protected = ('Data_metadata', 'root_first_page', 'root_before', 'root_after')
    for name in protected:
        before = CPU_TRIAL / f'before-{name}.bin'
        after = CPU_TRIAL / f'after-{name}.bin'
        if not file_hashes_match(before, after) or not file_hashes_match(refs[name], after):
            raise ValueError('CPU before/after Recovery reference differs: ' + name)
    if not file_hashes_match(CPU_TRIAL / 'before-Data.bin', CPU_TRIAL / 'after-Data.bin'):
        raise ValueError('CPU Data capture changed')
    checks = incident.get('protected_checks', {})
    if (incident.get('status') != 'fixed-runner-stopped-before-boot-on-root-first-page-protection-mismatch' or
            incident.get('execution', {}).get('boot_attempts') != 0 or
            incident.get('execution', {}).get('device_write_commands') != 0 or
            incident.get('execution', {}).get('GPU_started') is not False or
            incident.get('execution', {}).get('touch_started') is not False or
            checks.get('root_first_page_match') is not False or
            checks.get('actual_root_first_page_sha256') != sha(refs['root_first_page']) or
            checks.get('pinned_root_first_page_sha256') == checks.get('actual_root_first_page_sha256')):
        raise ValueError('preserved v73 stop evidence does not match the stale-pin incident')
    v1 = load(V1_RESULT)
    v1_trial = V1_OUT
    if (v1.get('status') != 'failed-read-only-Recovery-check-stop-retained' or
            v1.get('boots') is not False or v1.get('device_writes') is not False or
            v1.get('partition_writes') is not False or v1.get('commands') != 25 or
            v1.get('error') != "RuntimeError('fresh Recovery protection differs from CPU baseline: Data_header')" or
            v1.get('stop_gate_cleared') is not False):
        raise ValueError('exact preserved v1 offset-failure record required')
    current_reads = {
        'command-018.stdout': refs['primary_GPT'],
        'command-019.stdout': refs['backup_GPT'],
        'command-020.stdout': refs['root_manifest'],
        'command-021.stdout': refs['pre_data_guard'],
        'command-022.stdout': refs['Data_metadata'],
        'command-023.stdout': refs['root_first_page'],
        'command-024.stdout': refs['root_before'],
        'command-025.stdout': refs['root_after'],
    }
    for capture, reference in current_reads.items():
        captured = v1_trial / capture
        if not file_hashes_match(captured, reference):
            raise ValueError('v1 Recovery capture differs from corrected reference: ' + capture)
    if (load(v1_trial / 'command-021.json').get('arguments') !=
            ['exec-out', 'dd if=/dev/block/by-name/unixnu bs=4096 skip=4194303 count=1 2>/dev/null'] or
            load(v1_trial / 'command-022.json').get('arguments') !=
            ['exec-out', 'dd if=/dev/block/by-name/unixnu bs=4096 skip=4194304 count=65 2>/dev/null']):
        raise ValueError('v1 page-offset evidence differs from the preserved command record')
    if refs['Data_metadata'].read_bytes()[:4096] != refs['Data_header'].read_bytes():
        raise ValueError('Data_header must be unixnu-relative LBA 4194304')
    v2 = load(V2_RESULT)
    if (v2.get('scope') != 'single-K80-ios26-GPU-v73-corrected-offset-recovery-requalification-readonly-20261113' or
            v2.get('status') != 'failed-read-only-Recovery-check-stop-retained' or
            v2.get('boots') is not False or v2.get('device_writes') is not False or
            v2.get('partition_writes') is not False or v2.get('commands') != 28 or
            v2.get('error') != "RuntimeError('native log page differs from the last actual CPU boot')" or
            v2.get('stop_gate_cleared') is not False):
        raise ValueError('exact preserved v2 diagnostic-log-reference failure required')
    v2_reads = {
        'current-primary_GPT.bin': refs['primary_GPT'],
        'current-backup_GPT.bin': refs['backup_GPT'],
        'current-root_manifest.bin': refs['root_manifest'],
        'current-pre_data_guard.bin': refs['pre_data_guard'],
        'current-Data_header.bin': refs['Data_header'],
        'current-Data_metadata.bin': refs['Data_metadata'],
        'current-root_first_page.bin': refs['root_first_page'],
        'current-root_before.bin': refs['root_before'],
        'current-root_after.bin': refs['root_after'],
    }
    for capture, reference in v2_reads.items():
        if not file_hashes_match(V2_OUT / capture, reference):
            raise ValueError('v2 Recovery protection differs from corrected pin: ' + capture)
    v60_run = load(V60_RUN)
    v60_evidence = load(V60_EVIDENCE)
    v60_log = refs['native_log_reference'].read_bytes()
    if (v60_run.get('scope') != 'single-K80-ios26-native-SMMU-readonly-bank-stream-census90s-v60' or
            v60_run.get('status') != 'recovered-fresh-smmu-readonly-census-record' or
            v60_run.get('log_changed') is not True or
            v60_run.get('native_writer_readback_success_proven') is not False or
            v60_evidence.get('scope') != v60_run.get('scope') or
            v60_evidence.get('native_log_page', {}).get('after', {}).get('sha256') != sha(refs['native_log_reference']) or
            v60_evidence.get('native_log_page', {}).get('native_writer_readback_success_proven') is not False or
            v60_evidence.get('native_log_page', {}).get('decoded_record_status') != 'existing-Hp26-record-byte-envelope-valid' or
            v60_log == refs['CPU_native_log_reference'].read_bytes()):
        raise ValueError('known v60 device log capture does not match its preserved readback evidence')
    v2_bcb = (V2_OUT / 'command-027.stdout').read_bytes()
    bcb_command = v2_bcb[:2048].split(b'\0', 1)[0]
    if (len(v2_bcb) != 4096 or v2_bcb[2048:] != refs['BCB_reference'].read_bytes()[2048:] or
            bcb_command not in (b'', b'boot-recovery')):
        raise ValueError('v2 full BCB page/tail does not match the retained Recovery reference')
    if not file_hashes_match(V2_OUT / 'command-028.stdout', refs['native_log_reference']):
        raise ValueError('v2 log capture is not the known v60 full-page record')
    if (load(V2_OUT / 'command-027.json').get('arguments') !=
            ['exec-out', 'dd if=/dev/block/by-name/misc bs=4096 skip=0 count=1 2>/dev/null'] or
            load(V2_OUT / 'command-028.json').get('arguments') !=
            ['exec-out', 'dd if=/dev/block/by-name/unixnu bs=4096 skip=2291712 count=1 2>/dev/null']):
        raise ValueError('v2 BCB/log full-page capture command identity differs')
    return refs, cpu_bundle, incident, cpu_run


def archive_inputs():
    if OUT.exists() or OUT.is_symlink():
        raise FileExistsError('new one-shot requalification output must not already exist')
    refs, cpu_bundle, incident, cpu_run = verify_historical_evidence()
    archive = OUT / 'archive'
    archive.mkdir(parents=True)
    original_state = load(CURRENT)
    if not state_is_requalifiable(original_state):
        raise ValueError('exact stopped v73 state required; no device access')
    copied = {}
    for role, source in refs.items():
        source = source.resolve(strict=True)
        if source.is_symlink() or not source.is_file():
            raise ValueError('regular pinned input required: ' + role)
        destination = archive / (role + source.suffix)
        shutil.copyfile(source, destination)
        if source.samefile(destination) or sha(source) != sha(destination):
            raise ValueError('independent archive mismatch: ' + role)
        copied[role] = {'path': str(source), 'archive': str(destination), 'sha256': sha(source)}
    ready = {
        'scope': SCOPE,
        'serial': SERIAL,
        'product': 'zorn',
        'slot': 'a',
        'purpose': 'fresh full Recovery protection read with Data_header at Data start LBA 4194304 and the exact known v60 diagnostic log page',
        'timeout_seconds': TIMEOUT_SECONDS,
        'boots': False,
        'device_writes': False,
        'partition_writes': False,
        'bcb_writes': False,
        'native_log_writes': False,
        'current_state_sha256': sha(CURRENT),
        'incident_sha256': sha(INCIDENT),
        'cpu_run_sha256': sha(CPU_TRIAL / 'run.json'),
        'cpu_bundle_sha256': sha(CPU_BUNDLE),
        'inputs': copied,
        'authorization_context': 'The owner authorized unattended operations on this connected K80 iOS26 partition. This exact stage is read-only Recovery verification; no boot or phone write is permitted by the runner.',
    }
    save(OUT / 'ready.json', ready, True)
    save(OUT / 'previous-current-state.json', original_state, True)
    print(json.dumps({'scope': SCOPE, 'ready': str(OUT / 'ready.json'),
                      'inputs': len(copied), 'phone_accessed': False, 'claim_created': False}))


def validate(ready_path):
    ready_path = Path(ready_path)
    if ready_path != OUT / 'ready.json' or ready_path.is_symlink() or not ready_path.is_file():
        raise ValueError('canonical exact one-shot readiness required')
    refs, cpu_bundle, incident, cpu_run = verify_historical_evidence()
    ready = load(ready_path)
    previous_state = load(OUT / 'previous-current-state.json')
    if (not state_is_requalifiable(previous_state) or sha(CURRENT) != ready.get('current_state_sha256') or
            load(CURRENT) != previous_state or ready.get('incident_sha256') != sha(INCIDENT) or
            ready.get('cpu_run_sha256') != sha(CPU_TRIAL / 'run.json') or
            ready.get('cpu_bundle_sha256') != sha(CPU_BUNDLE) or
            ready.get('timeout_seconds') != TIMEOUT_SECONDS or
            any(ready.get(k) is not False for k in ('boots', 'device_writes', 'partition_writes', 'bcb_writes', 'native_log_writes'))):
        raise ValueError('current exact stop/evidence/read-only policy changed')
    if set(ready.get('inputs', {})) != set(refs):
        raise ValueError('complete exact Recovery reference set required')
    if ready['inputs']['current_state']['sha256'] != ready.get('current_state_sha256'):
        raise ValueError('current state is not bound to this read-only scope')
    for role, source in refs.items():
        pin = ready['inputs'][role]
        archive = Path(pin['archive'])
        if (Path(pin['path']) != source or source.is_symlink() or archive.is_symlink() or
                not archive.is_file() or source.samefile(archive) or
                sha(source) != sha(archive) or sha(source) != pin['sha256']):
            raise ValueError('changed/missing exact input: ' + role)
    if (ready_path.parent != OUT or ready.get('scope') != SCOPE or
            ready.get('serial') != SERIAL or ready.get('product') != 'zorn' or ready.get('slot') != 'a' or
            ready.get('purpose') != 'fresh full Recovery protection read with Data_header at Data start LBA 4194304 and the exact known v60 diagnostic log page' or
            set(ready) != {'scope','serial','product','slot','purpose','timeout_seconds','boots','device_writes',
                           'partition_writes','bcb_writes','native_log_writes','current_state_sha256',
                           'incident_sha256','cpu_run_sha256','cpu_bundle_sha256','inputs','authorization_context'}):
        raise ValueError('read-only Recovery scope differs')
    return ready, previous_state, cpu_bundle


class ReadOnlyCapture:
    def __init__(self, adb_path, output):
        self.adb = Path(adb_path)
        self.output = output
        self.deadline = time.monotonic() + TIMEOUT_SECONDS
        self.sequence = 0
        self.recovery_identity = None

    def call(self, *args, binary=False, timeout=15):
        if time.monotonic() >= self.deadline:
            raise TimeoutError('fixed read-only Recovery deadline expired')
        if args == ('server-status',) or args == ('get-serialno',) or args == ('shell','cat','/proc/mounts'):
            pass
        elif len(args) == 3 and args[:2] == ('shell','getprop') and re.fullmatch(r'ro\.[A-Za-z0-9_.]+', args[2]):
            pass
        elif len(args) == 4 and args[:3] == ('shell','readlink','-f') and re.fullmatch(r'/dev/block/[A-Za-z0-9_./-]+', args[3]):
            pass
        elif args in (('shell','blockdev','--getsize64',ROOT_PART),
                      ('shell','blockdev','--getss','/dev/block/sda')):
            pass
        elif len(args) == 2 and args[0] == 'exec-out' and re.fullmatch(
                r'dd if=(/dev/block/sda|/dev/block/by-name/(unixnu|misc)) bs=4096 skip=[0-9]+ count=(?:1|5|6|65) 2>/dev/null', args[1]):
            pass
        else:
            raise ValueError('command outside fixed read-only Recovery allowlist')
        self.sequence += 1
        stem = self.output / f'command-{self.sequence:03d}'
        save(stem.with_suffix('.json'), {'arguments': list(map(str, args)), 'read_only': True}, True)
        env = os.environ.copy()
        for key in ('ADB_SERVER_SOCKET','ANDROID_ADB_SERVER_PORT','ANDROID_SERIAL','ADB_TRACE'):
            env.pop(key, None)
        env.update(ADB_LIBUSB='0', ADB_MDNS_AUTO_CONNECT='0')
        command = [str(self.adb), '-H', '127.0.0.1', '-P', '5039', '-s', SERIAL, *args]
        remaining = max(0.1, self.deadline - time.monotonic())
        result = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 timeout=min(timeout, remaining), check=True)
        stem.with_suffix('.stdout').write_bytes(result.stdout)
        stem.with_suffix('.stderr').write_bytes(result.stderr)
        return result.stdout if binary else (result.stdout + result.stderr).decode().strip()

    def read(self, device, lba, count):
        if device not in ('/dev/block/sda', ROOT_PART, MISC_PART) or lba < 0 or count not in (1,5,6,65):
            raise ValueError('read outside fixed Recovery ranges')
        data = self.call('exec-out', f'dd if={device} bs=4096 skip={lba} count={count} 2>/dev/null', binary=True)
        if len(data) != count * 4096:
            raise RuntimeError('short bounded Recovery read')
        return data

    def identify(self):
        from zorn_recovery_identity import PROPERTIES, inspect_recovery
        checks = [
            (('get-serialno',), SERIAL),
            (('shell','getprop','ro.product.device'), 'zorn'),
            (('shell','getprop','ro.boot.slot_suffix'), '_a'),
            (('shell','readlink','-f',ROOT_PART), '/dev/block/sda35'),
            (('shell','readlink','-f',MISC_PART), '/dev/block/sda11'),
            (('shell','blockdev','--getsize64',ROOT_PART), '68719476736'),
            (('shell','blockdev','--getss','/dev/block/sda'), '4096'),
        ]
        for args, expected in checks:
            if self.call(*args) != expected:
                raise RuntimeError('serial/product/slot/partition geometry differs')
        values = {key: self.call('shell','getprop',key) for key in PROPERTIES}
        self.recovery_identity = inspect_recovery(values)
        mounts = self.call('shell','cat','/proc/mounts')
        if len(mounts) > 65536 or len(mounts.splitlines()) > 256:
            raise RuntimeError('unexpected Recovery mount inventory')
        for line in mounts.splitlines():
            fields = line.split()
            if not fields:
                raise RuntimeError('malformed mount row')
            if fields[0].startswith('/dev/block/') and self.call('shell','readlink','-f',fields[0]) == '/dev/block/sda35':
                raise RuntimeError('unixnu mounted during read-only requalification')

    def protected(self, refs):
        self.identify()
        values = {
            'primary_GPT': self.read('/dev/block/sda', 0, 6),
            'backup_GPT': self.read('/dev/block/sda', 64049147, 5),
            'root_manifest': self.read(ROOT_PART, 0, 1),
            'pre_data_guard': self.read(ROOT_PART, 4194303, 1),
            'Data_header': self.read(ROOT_PART, 4194304, 1),
            'Data_metadata': self.read(ROOT_PART, 4194304, 65),
            'root_first_page': self.read(ROOT_PART, 6291712, 1),
            'root_before': self.read(ROOT_PART, 6291711, 1),
            'root_after': self.read(ROOT_PART, 14680320, 1),
        }
        for name, data in values.items():
            if data != refs[name].read_bytes():
                raise RuntimeError('fresh Recovery protection differs from CPU baseline: ' + name)
        return values


def require_existing_server(io):
    try:
        with socket.create_connection(('127.0.0.1',5039), timeout=0.5):
            pass
    except ConnectionRefusedError:
        raise RuntimeError('existing private ADB server unavailable; no bootstrap') from None
    server = io.call('server-status')
    if str(io.adb) not in server or 'usb_backend: NATIVE' not in server:
        raise RuntimeError('exact existing private SDK37 native ADB server required')


def execute(ready_path):
    if Path(sys.argv[0]).resolve() != RUNNER.resolve():
        raise ValueError('execute through the maintained fixed run-zorn-debug.py entry')
    ready, previous_state, cpu_bundle = validate(ready_path)
    claim = OUT / 'one-shot.claim.json'
    if claim.exists() or claim.is_symlink():
        raise ValueError('one-shot requalification already consumed; no replay')
    save(claim, {'scope': SCOPE, 'status': 'consumed-before-first-USB',
                 'ready_sha256': sha(ready_path), 'boots': False,
                 'device_writes': False, 'reusable': False}, True)
    current = load(CURRENT)
    if current != previous_state:
        raise ValueError('current stop state changed before first USB; no access')
    current['active_run'] = str(OUT)
    pending = CURRENT.with_name('current.gpu-v73-offset-log-requalify.tmp')
    save(pending, current, True)
    os.replace(pending, CURRENT)
    refs = {name: Path(row['path']) for name, row in ready['inputs'].items()}
    io = ReadOnlyCapture(cpu_bundle['pins']['adb_binary']['path'], OUT)
    result = {'scope': SCOPE, 'status': 'claimed-read-only-Recovery-check', 'boots': False,
              'device_writes': False, 'partition_writes': False, 'commands': 0}
    release_committed = False
    try:
        require_existing_server(io)
        before = io.protected(refs)
        for name, data in before.items():
            (OUT / f'current-{name}.bin').write_bytes(data)
        # Read the whole BCB page and one original native log page, then repeat
        # both the full protection set and BCB read before changing host state.
        bcb = io.read(MISC_PART, 0, 1)
        bcb_reference = refs['BCB_reference'].read_bytes()
        command = bcb[:2048].split(b'\0', 1)[0]
        if bcb[2048:] != bcb_reference[2048:] or command not in (b'', b'boot-recovery'):
            raise RuntimeError('full BCB page command/tail differs from accepted Recovery state')
        log = io.read(ROOT_PART, BASELINE_LOG_LBA, 1)
        if log != refs['native_log_reference'].read_bytes():
            raise RuntimeError('native log page differs from the exact known v60 diagnostic record')
        after = io.protected(refs)
        bcb_after = io.read(MISC_PART, 0, 1)
        if before != after or bcb_after != bcb:
            raise RuntimeError('Recovery protection or full BCB page changed during read-only check')
        if load(CURRENT).get('active_run') != str(OUT):
            raise RuntimeError('current active scope changed during read-only check')
        result.update(status='fresh-Recovery-protections-verified',
                      recovery_identity=io.recovery_identity,
                      protected_ranges=len(before), protected_storage_matches_CPU_before_after=True,
                      full_BCB_page_stable=True, BCB_tail_preserved=True,
                      native_log_matches_known_v60_record=True, root_first_page_sha256=sha_bytes(before['root_first_page']),
                      Data_header_lba=4194304, Data_header_sha256=sha_bytes(before['Data_header']),
                      pre_data_guard_lba=4194303, pre_data_guard_sha256=sha_bytes(before['pre_data_guard']),
                      device_writes=0, boots=0, commands=io.sequence)
        save(OUT / 'result.json', result, True)
        current = load(CURRENT)
        if current != {**previous_state, 'active_run': str(OUT)}:
            raise RuntimeError('current state changed before exact stop release')
        current.update(stop_device_operations=False, stop_device_reason=None, active_run=None)
        current.setdefault('gpu_discovery', {})['v73_corrected_offset_log_requalification'] = str(OUT / 'result.json')
        pending = CURRENT.with_name('current.gpu-v73-offset-log-requalify-release.tmp')
        save(pending, current, True)
        os.replace(pending, CURRENT)
        release_committed = True
        result['stop_gate_cleared_after_fresh_readonly_recovery'] = True
        save(OUT / 'result.json', result)
    except BaseException as error:
        if release_committed:
            rollback = load(CURRENT)
            rollback.update(stop_device_operations=True, stop_device_reason=STOP_REASON, active_run=None)
            rollback_pending = CURRENT.with_name('current.gpu-v73-offset-log-requalify-rollback.tmp')
            save(rollback_pending, rollback, True)
            os.replace(rollback_pending, CURRENT)
        result.update(status='failed-read-only-Recovery-check-stop-retained', error=repr(error),
                      commands=io.sequence, stop_gate_cleared=False)
        save(OUT / 'result.json', result)
        raise
    finally:
        current = load(CURRENT)
        if current.get('active_run') == str(OUT):
            current['active_run'] = None
            pending = CURRENT.with_name('current.gpu-v73-offset-log-requalify-finish.tmp')
            save(pending, current, True)
            os.replace(pending, CURRENT)
    print(json.dumps(result))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ios26-gpu-v73-offset-log-recovery-requalify', type=Path)
    parser.add_argument('--prepare-host-only', action='store_true')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if args.prepare_host_only:
        if args.ios26_gpu_v73_offset_log_recovery_requalify is not None:
            parser.error('host preparation does not accept a ready path')
        archive_inputs()
        return
    if args.ios26_gpu_v73_offset_log_recovery_requalify is None:
        parser.error('--ios26-gpu-v73-offset-log-recovery-requalify READY is required')
    if args.check_only:
        ready, _, _ = validate(args.ios26_gpu_v73_offset_log_recovery_requalify)
        print(json.dumps({'scope': ready['scope'], 'host_inputs_match': True,
                          'phone_accessed': False, 'claim_created': False,
                          'boots': False, 'device_writes': False}))
        return
    execute(args.ios26_gpu_v73_offset_log_recovery_requalify)


if __name__ == '__main__':
    main()

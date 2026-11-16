"""Dedicated one-shot unixnu64 resource observation. Import/validation are host-only.

The fixed runner is its only command-line entry. A new exact candidate decision
is required; old installation/slotB claims and attendance never grant execution.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import time
import zlib

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / 'out/zorn/gpu-resource-observation-candidate'
SCOPE = 'single-unixnu64-UEFI-resource-observation-terminal-before-payload'
SERIAL = '92988a43'
PARTITION = '/dev/block/by-name/unixnu'
ROLES = {'boot', 'fd', 'module', 'kernel', 'kernel_plan', 'FAT', 'menu', 'ADT',
         'expected', 'current_start_source', 'current_start_object',
         'current_start_recipe', 'current_start_binding', 'descriptor',
         'firmware_inputs', 'firmware_archive', 'runtime_inputs', 'runtime_archive',
         'primary_GPT', 'backup_GPT', 'root_manifest', 'Data_header',
         'fixed_runner', 'runner', 'reader', 'fd_audit', 'image_audit', 'offline_result'}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def same(value, expected):
    return type(value) is type(expected) and value == expected


def closure(inputs, archives):
    if not isinstance(inputs, dict) or not inputs or set(inputs) != set(archives):
        raise ValueError('incomplete current/archive closure')
    for name, expected in inputs.items():
        path, row = Path(name), archives[name]
        saved = Path(row['path'])
        if (not path.is_absolute() or not saved.is_absolute() or not path.is_file() or
                not saved.is_file() or row['sha256'] != expected or
                path.stat().st_ino == saved.stat().st_ino or
                digest(path) != expected or digest(saved) != expected):
            raise ValueError('changed/shared current/archive input: '+name)


def validate(admission, base=CANDIDATE, current=None):
    """Pure file checks. Returns a claim recipe, never touches USB or a claim."""
    required = dict(version=1, scope=SCOPE, serial=SERIAL, product='zorn', slot='a',
                    storage_profile='unixnu64', timeout_seconds=600,
                    start_in_recovery=True, bootstrap_allowed=False,
                    terminal_before_payload=True, GPU_enabled=False,
                    accepted_preowner_and_nonreturning_IO_unavailable=True,
                    owner_activation_approved=True, allow_boot=True, retries=0,
                    log_relative_lba=2291712, log_blocks=1, watchdog_mode=1,
                    resource_observation_only=True, protocol_locates_max=3, clock_lookups_max=3,
                    gcd_descriptor_calls_max=16, no_clock_vote_rate_reset=True, no_SCM_PAS=True,
                    accept_lookup_bookkeeping_allocation_or_blocking=True)
    if any(not same(admission.get(k), v) for k, v in required.items()):
        raise ValueError('new exact media admission/approval required; no USB action')
    if current is not None and any(current.get(k) for k in ('active_run', 'active_build', 'runner_session')):
        raise ValueError('another build/run is active; no USB action')
    if current is not None and current.get('stop_device_operations'):
        raise ValueError('device operations stopped after an earlier failure')
    base = Path(base).resolve()
    bundle_path = Path(admission['bundle']).resolve()
    if bundle_path != base/'trial-bundle.json' or digest(bundle_path) != admission['bundle_sha256']:
        raise ValueError('candidate bundle changed')
    bundle = load(bundle_path)
    pins = bundle['pins']
    if set(pins) != ROLES or bundle.get('scope') != SCOPE:
        raise ValueError('missing candidate/protection roles')
    for role, pin in pins.items():
        p = Path(pin['path'])
        if not p.is_absolute() or not p.is_file() or digest(p) != pin['sha256']:
            raise ValueError('candidate role changed: '+role)
    image = Path(pins['boot']['path']).resolve()
    if image != base/'image/boot.img' or Path(pins['FAT']['path']).resolve() != image.with_name('payload.img'):
        raise ValueError('exact new media image required')
    expected = load(pins['expected']['path'])
    for key, size in [('nonce', 16), ('kernel_sha256', 32), ('input_sha256', 32)]:
        raw = bytes.fromhex(expected[key])
        if len(raw) != size or not any(raw):
            raise ValueError('invalid new identity')
    if expected['kernel_sha256'] != pins['kernel']['sha256']:
        raise ValueError('identity kernel differs')
    descriptor = load(pins['descriptor']['path'])
    if (descriptor['slot'] != 'a' or descriptor['partition'] != {
            'name': 'unixnu', 'linux_by_name': PARTITION,
            'type_guid': '0fc63daf-8483-4772-8e79-3d69d8477de4',
            'unique_guid': 'b279731f-ccad-4ef5-a8b7-e7440cd08de3',
            'first_lba': 47271680, 'last_lba': 64048895,
            'lba_bytes': 4096, 'bytes': 68719476736} or
            descriptor['log'] != {'relative_lba': 2291712, 'blocks': 1}):
        raise ValueError('unixnu64 partition differs')
    data_header = Path(pins['Data_header']['path']).read_bytes()
    if (len(data_header) != 4096 or data_header[:8] != b'SHNGDATA' or
            struct.unpack_from('<IIQ', data_header, 8) != (1, 64, 2097152) or
            data_header[24:56].hex() != descriptor['Data']['seed_sha256'] or
            struct.unpack_from('<I', data_header, 56)[0] != 1535636492 or
            zlib.crc32(data_header[:60]) != struct.unpack_from('<I', data_header, 60)[0]):
        raise ValueError('installed Data metadata/cookie differs')
    owner = load(admission['owner_approval'])
    if (digest(admission['owner_approval']) != admission['owner_approval_sha256'] or
            not same(owner.get('approved'), True) or owner.get('scope') != SCOPE or
            owner.get('boot_sha256') != pins['boot']['sha256'] or
            owner.get('nonce') != expected['nonce'] or
            owner.get('bundle_sha256') != admission['bundle_sha256'] or
            not same(owner.get('accept_preowner_and_nonreturning_IO_unavailable'), True) or
            not same(owner.get('resource_observation_approved'), True) or
            not same(owner.get('accept_lookup_bookkeeping_allocation_or_blocking'), True)):
        raise ValueError('distinct exact new owner decision required')
    ready = load(admission['ready'])
    if (digest(admission['ready']) != admission['ready_sha256'] or
            not same(ready.get('allow_boot'), True) or ready.get('scope') != SCOPE or
            ready.get('bundle_sha256') != admission['bundle_sha256'] or
            ready.get('boot_sha256') != pins['boot']['sha256'] or
            ready.get('readback_qualified') is not False or
            not same(ready.get('resource_observation_only'), True)):
        raise ValueError('distinct per-trial ready differs')
    if load(pins['kernel_plan']['path'])['candidate_sha256'] != pins['kernel']['sha256']:
        raise ValueError('postlinked kernel differs')
    fd = load(pins['fd_audit']['path'])
    image_audit = load(pins['image_audit']['path'])
    if (fd.get('fd_sha256') != pins['fd']['sha256'] or
            fd.get('module_sha256') != pins['module']['sha256'] or
            fd.get('extracted_module_whole_file_equal') is not True or
            fd.get('actual_compiler_selectors') != dict(inspection=0, media_commit=1, caller=1, driver=1, resource_query=1) or
            type(fd.get("module_entry_rva")) is not int or fd["module_entry_rva"] == 0 or
            fd.get("selected_annotation_only") is not False or
            image_audit.get('boot_sha256') != pins['boot']['sha256'] or
            image_audit.get('kernel_sha256') != pins['kernel']['sha256'] or
            image_audit.get('FD_sha256') != pins['fd']['sha256'] or
            image_audit.get('terminal_before_payload') is not True or
            load(pins['offline_result']['path']).get('offline_complete') is not True):
        raise ValueError('actual candidate FD/image/protection proof differs')
    start = load(pins['current_start_binding']['path'])
    for role, key in [('current_start_source', 'source'), ('current_start_object', 'active_object'),
                      ('current_start_recipe', 'recipe')]:
        if start.get(key) != pins[role]['path'] or start.get(key+'_sha256') != pins[role]['sha256']:
            raise ValueError('currentstart binding differs')
    if start.get('independent_sha256') != pins['current_start_object']['sha256']:
        raise ValueError('independently assembled currentstart differs')
    fw_inputs = load(pins['firmware_inputs']['path'])['inputs']
    fw_archived = load(pins['firmware_archive']['path'])['files']
    fw_map = {row['source']: dict(path=p, sha256=row['sha256']) for p, row in fw_archived.items()}
    if not set(fw_inputs).issubset(fw_map):
        raise ValueError('firmware dependency archive incomplete')
    closure(fw_inputs, {p: fw_map[p] for p in fw_inputs})
    closure(load(pins['runtime_inputs']['path'])['inputs'], load(pins['runtime_archive']['path'])['files'])
    with Path(pins['FAT']['path']).open('rb') as stream:
        sector = stream.read(512)
        backup = int.from_bytes(sector[0x32:0x34], 'little')
        if len(sector) != 512 or sector[510:512] != b'\x55\xaa' or not 1 <= backup < 32:
            raise ValueError('invalid FAT header')
        stream.seek(backup*512)
        other = stream.read(512)
    for sector in (sector, other):
        if (sector[0x180:0x190] != b'ZORNGHWD'+struct.pack('<II', 1, 0xfffffffe) or
                sector[0x190:0x1a0] != b'ZORNTPWR'+struct.pack('<II', 1, 0xfffffffe)):
            raise ValueError('watchdog/touch marker differs')
    claim_path = Path(admission['claim'])
    if (not claim_path.is_absolute() or claim_path.parent.resolve() != base/'trials' or
            claim_path.name != 'one-shot.claim.json' or claim_path.exists()):
        raise ValueError('claim consumed/unavailable; no retry')
    return dict(base=base, image=image, pins=pins, expected=expected,
                claim=claim_path, boot_sha256=pins['boot']['sha256'])


def claim_once(verified):
    fd = os.open(verified['claim'], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    # Never unlink/reset the claim, including after a short write or host failure.
    with os.fdopen(fd, 'w') as stream:
        json.dump(dict(status='consumed-no-repeat', boot_sha256=verified['boot_sha256'],
                       nonce=verified['expected']['nonce']), stream)
        stream.flush()
        os.fsync(stream.fileno())


class Transport:
    def __init__(self, *, adb_server_port=None):
        if adb_server_port is not None and (type(adb_server_port) is not int or adb_server_port != 5039):
            raise ValueError('only the reviewed existing ADB server5039 is selectable')
        self.adb_server_port = adb_server_port
        self.adb = os.environ.get('UNIXNU_ADB', 'adb')
        self.fastboot = os.environ.get('UNIXNU_FASTBOOT', 'fastboot')
        self.deadline = time.monotonic()+180

    def call(self, *args, binary=False, timeout=20):
        remaining = self.deadline-time.monotonic()
        if remaining <= 0:
            raise RuntimeError('bounded deadline reached; stop device operations')
        options = {}
        if self.adb_server_port is not None:
            env = os.environ.copy()
            for key in ('ADB_SERVER_SOCKET', 'ANDROID_ADB_SERVER_PORT', 'ANDROID_SERIAL', 'ADB_TRACE'):
                env.pop(key, None)
            env['ADB_LIBUSB'] = '0'
            env['ADB_MDNS_AUTO_CONNECT'] = '0'
            options['env'] = env
        p = subprocess.run(list(map(str, args)), capture_output=True,
                           timeout=min(timeout, remaining), check=True, **options)
        return p.stdout if binary else (p.stdout+p.stderr).decode().strip()

    def adb_call(self, *args, **kw):
        server = () if self.adb_server_port is None else ('-H', '127.0.0.1', '-P', str(self.adb_server_port))
        return self.call(self.adb, *server, '-s', SERIAL, *args, **kw)

    def read(self, device, lba, count):
        if device not in (PARTITION, '/dev/block/sda', '/dev/block/by-name/misc') or lba < 0 or not 0 < count <= 65:
            raise ValueError('invalid bounded read')
        data = self.adb_call('exec-out', f'dd if={device} bs=4096 skip={lba} count={count} 2>/dev/null', binary=True)
        if len(data) != count*4096:
            raise RuntimeError('short bounded read')
        return data


def recovery(io, pins, *, accepted_recovery=None):
    checks = [(('get-serialno',), SERIAL), (('shell', 'getprop', 'ro.product.device'), 'zorn'),
              (('shell', 'getprop', 'ro.boot.slot_suffix'), '_a'),
              (('shell', 'getprop', 'ro.orangefox.boot'), '1'),
              (('shell', 'readlink', '-f', PARTITION), '/dev/block/sda35'),
              (('shell', 'readlink', '-f', '/dev/block/by-name/misc'), '/dev/block/sda11'),
              (('shell', 'blockdev', '--getsize64', PARTITION), '68719476736'),
              (('shell', 'blockdev', '--getss', '/dev/block/sda'), '4096')]
    if accepted_recovery is not None:
        if accepted_recovery != 'twrp-or-orangefox':
            raise ValueError('unsupported Recovery selection')
        checks = [row for row in checks if row[0] != ('shell', 'getprop', 'ro.orangefox.boot')]
    for args, expected in checks:
        if io.adb_call(*args) != expected:
            raise RuntimeError('exact OrangeFox/serial/product/slot/partition check failed')
    if accepted_recovery is not None:
        from zorn_recovery_identity import PROPERTIES, inspect_recovery
        io.recovery_identity = inspect_recovery({key: io.adb_call('shell', 'getprop', key) for key in PROPERTIES})
    mounts = io.adb_call('shell', 'cat', '/proc/mounts')
    if len(mounts) > 65536 or len(mounts.splitlines()) > 256:
        raise RuntimeError('unexpected mount inventory')
    for line in mounts.splitlines():
        fields = line.split()
        if not fields:
            raise RuntimeError('malformed mount row')
        if fields[0].startswith('/dev/block/'):
            if io.adb_call('shell', 'readlink', '-f', fields[0]) == '/dev/block/sda35':
                raise RuntimeError('unixnu is mounted')
    if io.read('/dev/block/sda', 0, 6) != Path(pins['primary_GPT']['path']).read_bytes():
        raise RuntimeError('primary GPT differs')
    if io.read('/dev/block/sda', 64049147, 5) != Path(pins['backup_GPT']['path']).read_bytes():
        raise RuntimeError('backup GPT differs')
    if io.read(PARTITION, 0, 1) != Path(pins['root_manifest']['path']).read_bytes():
        raise RuntimeError('OS root manifest differs')
    data = io.read(PARTITION, 4194304, 65)
    if data[:4096] != Path(pins['Data_header']['path']).read_bytes():
        raise RuntimeError('retained Data header/cookie differs')
    return dict(Data=data, before=io.read(PARTITION, 4194303, 1),
                after=io.read(PARTITION, 4194304+2097217, 1))


def fresh_bcb(io, out):
    old = io.read('/dev/block/by-name/misc', 0, 1)
    page = bytearray(old)
    page[:864] = bytes(864)
    page[:14] = b'boot-recovery\0'
    page[64:73] = b'recovery\n'
    assert len(page) == 4096 and page[864:] == old[864:]
    (out/'misc-before.bin').write_bytes(old)
    (out/'recovery-bcb.bin').write_bytes(page)
    remote = '/tmp/zorn-gpu-unixnu64-recovery-bcb.bin'
    io.adb_call('push', out/'recovery-bcb.bin', remote)
    if io.adb_call('exec-out', 'cat', remote, binary=True) != page:
        raise RuntimeError('BCB tmpfs mismatch')
    io.adb_call('shell', f'dd if={remote} of=/dev/block/by-name/misc bs=4096 count=1 conv=notrunc')
    back = io.read('/dev/block/by-name/misc', 0, 1)
    (out/'misc-readback.bin').write_bytes(back)
    if back != page:
        raise RuntimeError('BCB full-page readback differs')
    return dict(tail_preserved=True, full_page_readback=True, before=digest(out/'misc-before.bin'),
                prepared=digest(out/'misc-readback.bin'))


def getvar(io, key):
    text = io.call(io.fastboot, '-s', SERIAL, 'getvar', key, timeout=3)
    values = re.findall(r'(?m)^(?:\(bootloader\) )?'+re.escape(key)+r':\s*([^\r\n]+)\s*$', text)
    if len(values) != 1:
        raise RuntimeError('missing/ambiguous fastboot variable: '+key)
    return values[0].strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gpu-resource-observation-trial', type=Path, required=True)
    args = parser.parse_args()
    current_path = ROOT/'out/zorn/unattended-active/current.json'
    verified = validate(load(args.gpu_resource_observation_trial), current=load(current_path))
    out = verified['base']/'trials/run'
    out.mkdir(exist_ok=False)
    claim_once(verified)  # Before any USB/ADB/fastboot, including enumeration.
    manifest = dict(status='preparing', scope=SCOPE, serial=SERIAL, slot='a',
                    boot_sha256=verified['boot_sha256'], allow_boot=False,
                    readback_qualified=False, GPU_executed=False, native_GPU_invoked=False)

    def record():
        (out/'run.json').write_text(json.dumps(manifest, indent=2)+'\n')

    record()
    c = load(current_path)
    c.update(active_run=str(out), active_phase='unixnu64-resource-observation-trial')
    current_path.write_text(json.dumps(c, ensure_ascii=False, indent=2)+'\n')
    if sys.platform == 'darwin' and Path('/usr/bin/caffeinate').is_file():
        subprocess.Popen(['/usr/bin/caffeinate', '-i', '-w', str(os.getpid())],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    io = Transport()
    try:
        before = recovery(io, verified['pins'])
        oldlog = io.read(PARTITION, 2291712, 1)
        (out/'preboot-checkpoints.bin').write_bytes(oldlog)
        manifest['BCB'] = fresh_bcb(io, out)
        if recovery(io, verified['pins']) != before:
            raise RuntimeError('storage changed before reboot')
        io.adb_call('reboot', 'bootloader')
        until = min(io.deadline, time.monotonic()+30)
        while True:
            try:
                if getvar(io, 'product') == 'zorn':
                    break
            except subprocess.SubprocessError:
                pass
            if time.monotonic() >= until:
                raise RuntimeError('no exact fastboot within30s; stop, no bootstrap/retry')
            time.sleep(1)
        if getvar(io, 'current-slot') != 'a' or int(getvar(io, 'partition-size:unixnu'), 16) != 68719476736:
            raise RuntimeError('fastboot slot/partition changed')
        if digest(verified['image']) != verified['boot_sha256']:
            raise RuntimeError('image changed before boot')
        manifest['status'] = 'boot-attempting'
        record()
        started = time.monotonic()
        io.deadline = started+600
        try:
            output = io.call(io.fastboot, '-s', SERIAL, 'boot', verified['image'], timeout=60)
            manifest['fastboot_returned_success'] = True
        except subprocess.SubprocessError as error:
            output = str(error)
            manifest['fastboot_returned_success'] = False
            # An uncertain transport result never authorizes a retry. Wait only
            # for the already armed BCB/independent firmware watchdog recovery.
        (out/'fastboot.txt').write_text(output+'\n')
        while True:
            try:
                if io.adb_call('shell', 'getprop', 'ro.orangefox.boot', timeout=3) == '1':
                    break
            except subprocess.SubprocessError:
                pass
            if time.monotonic() >= io.deadline:
                raise RuntimeError('no Recovery within600s; STOP and notify; no flash/restore')
            time.sleep(min(2, max(0, io.deadline-time.monotonic())))
        manifest['recovery_observed_seconds'] = time.monotonic()-started
        # Finish checks get a separate bounded read-only budget after recovery.
        io.deadline = time.monotonic()+180
        if recovery(io, verified['pins']) != before:
            raise RuntimeError('Data/root/GPT/fences changed after terminal diagnostic')
        newlog = io.read(PARTITION, 2291712, 1)
        (out/'checkpoints.bin').write_bytes(newlog)
        from zorn_early_failure import decode
        try:
            if newlog == oldlog:
                raise ValueError('unchanged/stale preboot record')
            decoded = decode(newlog, expected=verified['expected'])
            manifest['record'] = dict(available=True, decoded=decoded)
        except (ValueError, KeyError, TypeError) as error:
            manifest['record'] = dict(available=False, reason=str(error))
        manifest.update(status='recovered', native_write_SUCCESS_proven=False,
                        native_readback_SUCCESS_proven=False,
                        record_is_not_private_commit_status=True)
    except Exception as error:
        manifest.update(status='failed-stop-device-operations', error=str(error),
                        physical_assistance_may_be_required=True)
        raise
    finally:
        record()
        c = load(current_path)
        c.update(active_run=None, active_phase='unixnu64-resource-observation-'+manifest['status'])
        if manifest['status'] != 'recovered':
            c['stop_device_operations'] = True
        current_path.write_text(json.dumps(c, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(manifest, indent=2))

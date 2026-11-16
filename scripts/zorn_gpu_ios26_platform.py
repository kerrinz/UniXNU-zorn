"""Independent iOS26 K80 platform candidate entry; importing never touches USB.

Host inspection/assembly does not authorize a run. A run additionally requires
new exact owner/ready/admission files and consumes its claim before first USB.
The current platform packet has no persistent kernel terminal writer: recovery
timing or a stale log must never be reported as proof of kernel/GPU execution.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT/'out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90'
SCOPE = 'single-K80-ios26-platform20s-bounded-recovery'
SERIAL = '92988a43'
ROLES = {'boot', 'fd', 'kernel', 'FAT', 'menu', 'ADT', 'loader', 'manager',
         'fixed_builder', 'fixed_runner', 'entry', 'device_helpers', 'packer',
         'shim_source', 'shim_object', 'source_build_proof', 'link_proof',
         'fd_proof', 'payload_proof', 'image_proof', 'primary_GPT',
         'backup_GPT', 'root_manifest', 'Data_header', 'descriptor'}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def exact(value, expected):
    return type(value) is type(expected) and value == expected


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def record_active_run(out, manifest, finished=False):
    """Only called by an actually authorized, already consumed future trial."""
    path = ROOT/'out/zorn/unattended-active/current.json'
    current = load(path)
    if current.get('active_run') not in (None, str(out)) or current.get('runner_session'):
        raise RuntimeError('another device operation became active; consumed, no USB')
    current['active_run'] = None if finished else str(out)
    current.setdefault('gpu_discovery', {})['last_ios26_platform_run'] = str(out/'run.json')
    if finished and manifest['status'].startswith('failed'):
        current['stop_device_operations'] = True
        current['stop_device_reason'] = manifest.get('error', 'iOS26 platform trial failed')
    temporary = path.with_name(path.name+'.ios26-'+str(os.getpid())+'.tmp')
    with temporary.open('x') as stream:
        json.dump(current, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def inspect_bundle(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(STAGE):
        raise ValueError('independent local iOS26 bundle required')
    data = load(path)
    required = dict(version=1, scope=SCOPE, os_major=26, serial=SERIAL,
                    product='zorn', slot='a', donor='iPhone18,1/26.6.2/23G90',
                    kernel_machine='ZORN', CPU_page_bytes=16384,
                    watchdog_mode=1, trial_seconds=20, GPU_startup=False,
                    root_storage_selected=False, target_executed=False)
    if any(not exact(data.get(k), v) for k, v in required.items()):
        raise ValueError('iOS26 platform identity/scope differs; no legacy fallback')
    pins = data.get('pins', {})
    if set(pins) != ROLES:
        raise ValueError('incomplete iOS26 artifact/protection/source roles')
    for role, row in pins.items():
        p, archive = Path(row['path']), Path(row['archive'])
        if (not p.is_absolute() or not archive.is_absolute() or p.is_symlink() or archive.is_symlink()
                or not p.is_file() or not archive.is_file()
                or p.stat().st_ino == archive.stat().st_ino
                or digest(p) != row['sha256'] or digest(archive) != row['sha256']):
            raise ValueError('changed/shared current/archive input: '+role)
    fixed = {'fixed_builder': ROOT/'UniXNU-zorn/scripts/build-zorn-debug.py',
             'fixed_runner': ROOT/'UniXNU-zorn/scripts/run-zorn-debug.py',
             'entry': Path(__file__).resolve(),
             'device_helpers': Path(__file__).with_name('zorn_gpu_resource_trial.py')}
    if any(Path(pins[k]['path']).resolve() != p.resolve() for k, p in fixed.items()):
        raise ValueError('exact maintained fixed entry/helper paths required')
    code = Path(pins['kernel']['path']).read_bytes()
    if struct.unpack_from('<3I', code) != (0xfeedfacf, 0x100000c, 0xc0000002):
        raise ValueError('arm64e.kernel Mach-O required')
    offset, versions = 32, []
    for _ in range(struct.unpack_from('<I', code, 16)[0]):
        cmd, size = struct.unpack_from('<II', code, offset)
        if size < 8 or offset+size > len(code):
            raise ValueError('invalid native Mach-O commands')
        if cmd == 0x32:
            versions.append(struct.unpack_from('<III', code, offset+8))
        offset += size
    if versions != [(2, 26 << 16, 27 << 16)]:
        raise ValueError('actual IOS26/SDK27 build metadata differs')
    image = Path(pins['boot']['path']).read_bytes()
    if image[:8] != b'ANDROID!' or struct.unpack_from('<I', image, 40)[0] != 4:
        raise ValueError('exact Android v4 carrier required')
    size, ramdisk = struct.unpack_from('<II', image, 8)
    if ramdisk or len(image) != 4096+((size+4095)&~4095):
        raise ValueError('no Android ramdisk or appended bytes allowed')
    # Bounded host decompression of the actual packaged carrier, not a device
    # allocation/geometry proof. The original ABL window is 256 MiB.
    from io import BytesIO
    with gzip.GzipFile(fileobj=BytesIO(image[4096:4096+size])) as stream:
        raw = stream.read(256*1024*1024+1)
    if len(raw) > 256*1024*1024:
        raise ValueError('original ABL payload window exceeded')
    fd, fat = Path(pins['fd']['path']).read_bytes(), Path(pins['FAT']['path']).read_bytes()
    if len(fd) != 0x300000 or len(raw) != 4096+len(fd)+len(fat) or raw[4096:] != fd+fat:
        raise ValueError('embedded FD/FAT differs')
    if raw[56:60] != b'ARM\x64' or struct.unpack_from('<QQ', raw, 8) != (0xA7100000, len(raw)):
        raise ValueError('native shim layout differs')
    if fat[0x180:0x190] != b'ZORNGHWD'+struct.pack('<II', 1, 0xfffffffe):
        raise ValueError('source-native WDT1 marker required')
    image_proof = load(pins['image_proof']['path'])
    if image_proof.get('boot', {}).get('sha256') != pins['boot']['sha256']:
        raise ValueError('independent image proof differs')
    payload_proof = load(pins['payload_proof']['path'])
    fd_proof = load(pins['fd_proof']['path'])
    if (payload_proof.get('payload', {}).get('sha256') != pins['FAT']['sha256']
            or fd_proof.get('FD', {}).get('sha256') != pins['fd']['sha256']
            or fd_proof.get('old_DarwinBoot_absent_from_actual_FFS') is not True):
        raise ValueError('actual payload/FD provider proof differs')
    members = {Path(row['path']).name: row['sha256'] for row in payload_proof['files']}
    for role, name in [('kernel', 'kernel.macho'), ('ADT', 'kernel.macho.adt'),
                       ('menu', 'unixnu.toml'), ('loader', 'DarwinBoot26.efi'),
                       ('manager', 'BOOTAA64.EFI')]:
        if members.get(name) != pins[role]['sha256']:
            raise ValueError('actual FAT member binding differs: '+role)
    if data.get('terminal_observer') != 'RAM-console-only-no-persistent-record':
        raise ValueError('current kernel observer contract differs')
    return data


def validate_activation(admission_path, bundle_path):
    admission_path = Path(admission_path)
    if admission_path.is_symlink() or not admission_path.resolve().is_relative_to(STAGE):
        raise ValueError('new independent iOS26 admission path required')
    admission = load(admission_path)
    required = dict(version=1, scope=SCOPE, serial=SERIAL, product='zorn', slot='a',
                    os_major=26, allow_boot=True, owner_activation_approved=True,
                    timeout_seconds=600, start_in_recovery=True,
                    bootstrap_allowed=False, retries=0, watchdog_mode=1,
                    fresh_full_page_BCB_required=True, native_GPU_startup=False,
                    native_storage_write=False, accepted_terminal_unavailable=True,
                    platform_execution_proven_from_recovery_alone=False)
    if any(not exact(admission.get(k), v) for k, v in required.items()):
        raise ValueError('new exact iOS26 owner admission required; no USB action')
    bundle = inspect_bundle(bundle_path)
    if admission.get('bundle_sha256') != digest(bundle_path):
        raise ValueError('new candidate bundle differs')
    nonce = admission.get('nonce', '')
    try:
        raw = bytes.fromhex(nonce)
    except (ValueError, TypeError):
        raise ValueError('fresh nonzero candidate nonce required') from None
    if len(raw) != 16 or not any(raw):
        raise ValueError('fresh nonzero candidate nonce required')
    for kind in ['owner_approval', 'ready']:
        p = Path(admission[kind]['path'])
        if not p.is_file() or p.is_symlink() or digest(p) != admission[kind]['sha256']:
            raise ValueError('exact fresh '+kind+' missing')
        row = load(p)
        expected = dict(scope=SCOPE, nonce=nonce, bundle_sha256=digest(bundle_path),
                        boot_sha256=bundle['pins']['boot']['sha256'], allow_boot=True)
        if any(not exact(row.get(k), v) for k, v in expected.items()):
            raise ValueError('distinct exact '+kind+' required')
        if kind == 'owner_approval' and (row.get('approved') is not True or
                row.get('accepted_terminal_unavailable') is not True):
            raise ValueError('actual separate owner decision/availability contract required')
    claim = Path(admission['claim'])
    expected_claim = STAGE/'k80-fixed-platform-entry26/trials'/nonce/'one-shot.claim.json'
    if (not claim.is_absolute() or claim.resolve() != expected_claim
            or not claim.parent.is_dir() or claim.exists() or claim.is_symlink()):
        raise ValueError('new claim absent/consumed; no retry')
    current = load(ROOT/'out/zorn/unattended-active/current.json')
    if any(current.get(k) for k in ['active_run', 'runner_session', 'stop_device_operations']):
        raise ValueError('another device run/stop state exists')
    return dict(bundle=bundle, claim=claim, nonce=nonce)


def run_trial(verified, out):
    # No Transport, enumeration or any subprocess is constructed before this
    # consumed claim. A local claim is reuse protection, not a hardware lease.
    bundle, claim = verified['bundle'], verified['claim']
    with os.fdopen(os.open(claim, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600), 'w') as stream:
        json.dump(dict(status='consumed-no-repeat', scope=SCOPE, nonce=verified['nonce'],
                       boot_sha256=bundle['pins']['boot']['sha256']), stream)
        stream.flush()
        os.fsync(stream.fileno())
    from zorn_gpu_resource_trial import Transport, recovery, fresh_bcb, getvar
    class CapturingTransport(Transport):
        """Archive actual existing bounded reads, not modeled device results."""
        sequence = 0
        command_sequence = 0
        def call(self, *args, **kwargs):
            self.command_sequence += 1
            stem = out/(f'command-{self.command_sequence:03d}')
            (stem.with_suffix('.json')).write_text(json.dumps(dict(arguments=list(map(str, args)),
                binary=bool(kwargs.get('binary', False))), indent=2)+'\n')
            try:
                value = super().call(*args, **kwargs)
            except subprocess.SubprocessError as error:
                for name in ['stdout', 'stderr']:
                    raw = getattr(error, name, None)
                    if isinstance(raw, bytes):
                        stem.with_suffix('.'+name+'.bin').write_bytes(raw)
                raise
            if isinstance(value, bytes):
                # Save before the existing read helper checks exact length,
                # so a short but successful process output is retained too.
                stem.with_suffix('.output.bin').write_bytes(value)
            else:
                stem.with_suffix('.output.txt').write_text(value)
            return value
        def read(self, device, lba, count):
            raw = super().read(device, lba, count)
            self.sequence += 1
            path = out/(f'read-{self.sequence:03d}-{Path(device).name}-{lba}-{count}.bin')
            path.write_bytes(raw)
            return raw
    io = CapturingTransport()
    manifest = dict(scope=SCOPE, serial=SERIAL, product='zorn', slot='a',
                    boot_sha256=bundle['pins']['boot']['sha256'], status='claimed')
    owned_active_run = False
    def record():
        (out/'run.json').write_text(json.dumps(manifest, indent=2)+'\n')
    record()
    try:
        record_active_run(out, manifest)
        owned_active_run = True
        before = recovery(io, bundle['pins'])
        for name, raw in before.items():
            (out/('before-'+name+'.bin')).write_bytes(raw)
        oldlog = io.read('/dev/block/by-name/unixnu', 2291712, 1)
        (out/'preboot-checkpoints.bin').write_bytes(oldlog)
        manifest['BCB'] = fresh_bcb(io, out)
        record()
        io.adb_call('reboot', 'bootloader')
        io.deadline = time.monotonic()+30
        while True:
            # Wait only for the authorized transition. An observed wrong
            # product/slot is terminal; it is never treated as a transient.
            try:
                product, slot = getvar(io, 'product'), getvar(io, 'current-slot')
            except subprocess.SubprocessError:
                if time.monotonic() >= io.deadline:
                    raise RuntimeError('bootloader unavailable; consumed, no bootstrap/retry')
                time.sleep(1)
                continue
            if product != 'zorn' or slot != 'a':
                raise RuntimeError('exact zorn/slotA required; no boot')
            break
        io.deadline = time.monotonic()+600
        started = time.monotonic()
        try:
            output = io.call(io.fastboot, '-s', SERIAL, 'boot', bundle['pins']['boot']['path'], timeout=60)
            manifest['fastboot_returned_success'] = True
        except subprocess.SubprocessError as error:
            output = str(error)
            manifest['fastboot_returned_success'] = False
        (out/'fastboot.txt').write_text(output+'\n')
        # No reboot/boot retry after an uncertain result. Only observe the
        # already armed Recovery return within the single remaining deadline.
        while True:
            try:
                if io.adb_call('shell', 'getprop', 'ro.orangefox.boot', timeout=3) == '1':
                    break
            except subprocess.SubprocessError:
                pass
            if time.monotonic() >= io.deadline:
                raise RuntimeError('no Recovery within600s; STOP device operations, no recovery flashing')
            time.sleep(min(2, max(0, io.deadline-time.monotonic())))
        manifest['recovery_observed_seconds'] = time.monotonic()-started
        io.deadline = time.monotonic()+180
        after = recovery(io, bundle['pins'])
        for name, raw in after.items():
            (out/('after-'+name+'.bin')).write_bytes(raw)
        if before != after:
            raise RuntimeError('actual GPT/root/Data/fences changed')
        newlog = io.read('/dev/block/by-name/unixnu', 2291712, 1)
        (out/'checkpoints.bin').write_bytes(newlog)
        manifest.update(status='recovered-platform-result-unqualified',
                        log_changed=newlog != oldlog, kernel_record_available=False,
                        platform_entry_proven=False, GPU_execution_proven=False,
                        terminal_observer=bundle['terminal_observer'],
                        note='Current kernel has no persistent terminal writer; timing or old log is not kernel/GPU proof')
    except BaseException as error:
        manifest.update(status='failed-device-operations-stopped', error=str(error))
        for field in ['stdout', 'stderr']:
            raw = getattr(error, field, None)
            if isinstance(raw, bytes):
                (out/('error-'+field+'.bin')).write_bytes(raw)
        raise
    finally:
        record()
        if owned_active_run:
            record_active_run(out, manifest, finished=True)


def main(mode):
    parser = argparse.ArgumentParser(description=__doc__)
    flag = '--ios26-platform-image' if mode == 'build' else '--ios26-platform-trial'
    parser.add_argument(flag, action='store_true', required=True)
    parser.add_argument('--os', choices=['26'], required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--admission', type=Path)
    args = parser.parse_args()
    if mode == 'build' and args.admission:
        parser.error('build mode never accepts device admission')
    if mode == 'run' and not args.check_only and not args.admission:
        parser.error('new exact admission required; no USB action')
    if mode == 'run' and args.admission and not args.check_only:
        verified = validate_activation(args.admission, args.bundle)
        bundle = verified['bundle']
    else:
        bundle = inspect_bundle(args.bundle)
    if args.check_only:
        print(json.dumps(dict(status='actual-iOS26-inputs-verified-host-only',
                              scope=SCOPE, slot='a', allow_boot=False,
                              claim_created=False, device_calls=0,
                              terminal_observer=bundle['terminal_observer'])))
        return
    out = args.output
    if out is None or out.exists() or out.is_symlink() or not out.resolve().is_relative_to(STAGE):
        parser.error('a new independent iOS26 output directory is required')
    out.mkdir()
    if mode == 'build':
        pins = bundle['pins']
        command = [sys.executable, pins['packer']['path'], '--fd', pins['fd']['path'],
                   '--ramdisk', pins['FAT']['path'], '--output', str(out/'boot.img')]
        save(out/'command.json', dict(arguments=command))
        with (out/'package.log').open('wb') as stream:
            subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=True)
        if digest(out/'boot.img') != pins['boot']['sha256']:
            raise RuntimeError('fixed builder output differs from exact reviewed candidate')
        save(out/'result.json', dict(status='independent-image-built-unselected',
                                    boot_sha256=digest(out/'boot.img'), allow_boot=False))
    else:
        run_trial(verified, out)

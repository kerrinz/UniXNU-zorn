"""Independent iOS26 K80 single-page result candidate; importing never touches USB.

Host inspection/assembly does not authorize a run. A run additionally requires
new exact owner/ready/admission files and consumes its claim before first USB.
The new packet may initialize native K80 UFS and write only the original log
page. Fresh captured tag/CRC bytes can qualify its platform milestone; Recovery
timing, stale bytes and compilation never prove kernel or GPU execution.
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
SCOPE = 'single-K80-ios26-root-input-probe20s-v1'
SERIAL = '92988a43'
ROLES = {'boot', 'fd', 'kernel', 'FAT', 'menu', 'ADT', 'loader', 'manager',
         'fixed_builder', 'fixed_runner', 'entry', 'device_helpers', 'packer',
         'shim_source', 'shim_object', 'source_build_proof', 'link_proof',
         'fd_proof', 'payload_proof', 'image_proof', 'primary_GPT',
         'backup_GPT', 'root_manifest', 'Data_header', 'descriptor', 'record_identity', 'record_decoder', 'record_GPT_pins',
         'adb_binary', 'fastboot_binary', 'recovery_identity'}


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
    current.setdefault('gpu_discovery', {})['last_ios26_platform_record_run'] = str(out/'run.json')
    if finished and manifest['status'].startswith('failed'):
        current['stop_device_operations'] = True
        current['stop_device_reason'] = manifest.get('error', 'iOS26 platform trial failed')
    temporary = path.with_name(path.name+'.ios26record-'+str(os.getpid())+'.tmp')
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
                    CPU_root_input_probe=True, root_binding_suppressed=True,
                    root_storage_selected=False, target_executed=False, allow_boot=False,
                    accepted_recovery='twrp-or-orangefox', existing_server_only=True, adb_server_port=5039,
                    native_UFS_initialization=True, native_storage_write=True,
                    native_log_absolute_lba=49563392, native_log_blocks=1,
                    native_misc_write=False, native_Data_write=False, native_root_write=False)
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
             'device_helpers': Path(__file__).with_name('zorn_gpu_resource_trial.py'),
             'recovery_identity': Path(__file__).with_name('zorn_recovery_identity.py')}
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
    if data.get('terminal_observer') != 'native-one-page-Hp26-artifact-record':
        raise ValueError('current native record contract differs')
    proof = load(pins['link_proof']['path'])
    if (proof.get('kernel', {}).get('sha256') != pins['kernel']['sha256'] or
            proof.get('actual_platform_call_after_registration') is not True):
        raise ValueError('actual native platform-result link proof differs')
    if (proof.get('probe_wait_cannot_reach_root_attach_in_final_CFG') is not True or
            proof.get('probe_path_cannot_reach_normal_root_start') is not True or
            proof.get('actual_CPU_result_only_not_root_or_hardware_success') is not True):
        raise ValueError('actual CPU-only observation suppression proof required')
    tag = artifact_tag(data)
    if data.get('artifact_run_id') != tag.hex() or tag not in code:
        raise ValueError('native source artifact tag differs')
    import tomllib
    menu = tomllib.loads(Path(pins['menu']['path']).read_text())
    expected_args = ('rd=md0 -v keepsyms=1 zorn26_platform_trial=1 zorn_wdt=1 '
                     'zorn26_prearmed_recovery=1 zorn26_trial_seconds=20 zorn26_platform_record=1 '
                     'zorn26_root=1 zorn26_root_inputs_probe=1')
    if (len(menu.get('entry', [])) != 1 or menu['entry'][0].get('args') != expected_args or
            menu.get('kits', {}).get('autoload') is not False or menu['boot'].get('connect_all') is not False):
        raise ValueError('exact record-only native startup selection required')
    gpt_pins = load(pins['record_GPT_pins']['path'])
    if len(gpt_pins) != 4 or {x['role'] for x in gpt_pins} != {
            'primary-header', 'primary-entries', 'backup-header', 'backup-entries'}:
        raise ValueError('exact four native GPT byte pins required')
    expected_GPT = {'primary-header': (4096, 4096, 1), 'primary-entries': (8192, 8192, 2),
                    'backup-header': (16384, 4096, 64049151), 'backup-entries': (0, 8192, 64049147)}
    for row in gpt_pins:
        if (row['source_offset'], row['bytes'], row['lba']) != expected_GPT[row['role']]:
            raise ValueError('native GPT slice geometry differs')
        role = 'primary_GPT' if row['role'].startswith('primary') else 'backup_GPT'
        source = Path(pins[role]['path']).read_bytes()
        part = source[row['source_offset']:row['source_offset']+row['bytes']]
        if len(part) != row['bytes'] or hashlib.sha256(part).hexdigest() != row['sha256']:
            raise ValueError('native GPT guard differs from current protection inputs')
    return data


def artifact_tag(bundle):
    identity = load(bundle['pins']['record_identity']['path'])
    try:
        tag = bytes.fromhex(identity['run_id'])
    except (ValueError, TypeError, KeyError):
        raise ValueError('exact native record artifact identity required') from None
    if len(tag) != 16 or not any(tag):
        raise ValueError('nonzero16byte native record identity required')
    return tag


def record_inspector(bundle):
    # Only the exact locally pinned, already reviewed pure decoder is loaded.
    import importlib.util
    row = bundle['pins']['record_decoder']
    if digest(row['path']) != row['sha256']:
        raise ValueError('pinned pure decoder changed during trial')
    spec = importlib.util.spec_from_file_location('zorn26_record_bytes', row['path'])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.inspect_page


def require_device_mode():
    # The latest explicit no-phone mode revokes execution even if an older
    # exact approval/ready pair still exists. Offline inspection is allowed.
    current = load(ROOT/'out/zorn/unattended-active/current.json')
    if current.get('gpu_discovery', {}).get('current_mode') == 'unattended-offline-no-phone':
        raise ValueError('current owner mode is offline/no-phone; no claim or USB action')


def validate_activation(admission_path, bundle_path):
    require_device_mode()
    admission_path = Path(admission_path)
    if admission_path.is_symlink() or not admission_path.resolve().is_relative_to(STAGE):
        raise ValueError('new independent iOS26 admission path required')
    admission = load(admission_path)
    required = dict(version=1, scope=SCOPE, serial=SERIAL, product='zorn', slot='a',
                    os_major=26, allow_boot=True, owner_activation_approved=True,
                    timeout_seconds=600, start_in_recovery=True,
                    accepted_recovery='twrp-or-orangefox', existing_server_only=True, adb_server_port=5039,
                    bootstrap_allowed=False, retries=0, watchdog_mode=1,
                    fresh_full_page_BCB_required=True, native_GPU_startup=False,
                    native_UFS_initialization=True, native_storage_write=True,
                    native_log_absolute_lba=49563392, native_log_blocks=1,
                    native_misc_write=False, native_Data_write=False, native_root_write=False,
                    accepted_native_UFS_and_single_log_write=True, accepted_terminal_unavailable=True,
                    CPU_root_input_probe=True, root_binding_suppressed=True,
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
    if len(raw) != 16 or not any(raw) or raw != artifact_tag(bundle):
        raise ValueError('fresh nonzero candidate nonce required')
    for kind in ['owner_approval', 'ready']:
        p = Path(admission[kind]['path'])
        if not p.is_file() or p.is_symlink() or digest(p) != admission[kind]['sha256']:
            raise ValueError('exact fresh '+kind+' missing')
        row = load(p)
        expected = dict(scope=SCOPE, nonce=nonce, bundle_sha256=digest(bundle_path),
                        boot_sha256=bundle['pins']['boot']['sha256'], allow_boot=True,
                        native_UFS_initialization=True, native_storage_write=True,
                        native_log_absolute_lba=49563392, native_log_blocks=1,
                        native_misc_write=False, native_Data_write=False, native_root_write=False,
                        accepted_native_UFS_and_single_log_write=True)
        if any(not exact(row.get(k), v) for k, v in expected.items()):
            raise ValueError('distinct exact '+kind+' required')
        if kind == 'owner_approval' and (row.get('approved') is not True or
                row.get('accepted_terminal_unavailable') is not True):
            raise ValueError('actual separate owner decision/availability contract required')
    claim = Path(admission['claim'])
    expected_claim = STAGE/'k80-fixed-root-input-probe-entry26/trials'/nonce/'one-shot.claim.json'
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
    require_device_mode()  # Recheck immediately before consuming any execution claim.
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
    overall_deadline = time.monotonic()+600
    io = CapturingTransport(adb_server_port=5039)
    # Actual reviewed executable paths,not a later PATH/environment choice.
    io.adb = bundle['pins']['adb_binary']['path']
    io.fastboot = bundle['pins']['fastboot_binary']['path']
    io.deadline = min(overall_deadline, io.deadline)
    manifest = dict(scope=SCOPE, serial=SERIAL, product='zorn', slot='a',
                    boot_sha256=bundle['pins']['boot']['sha256'], status='claimed')
    owned_active_run = False
    def record():
        (out/'run.json').write_text(json.dumps(manifest, indent=2)+'\n')
    record()
    try:
        record_active_run(out, manifest)
        owned_active_run = True
        before = recovery(io, bundle['pins'], accepted_recovery=bundle['accepted_recovery'])
        manifest['recovery_identity_before'] = io.recovery_identity
        for name, raw in before.items():
            (out/('before-'+name+'.bin')).write_bytes(raw)
        oldlog = io.read('/dev/block/by-name/unixnu', 2291712, 1)
        (out/'preboot-checkpoints.bin').write_bytes(oldlog)
        if oldlog[:24] == b'HJPAN026'+artifact_tag(bundle):
            raise RuntimeError('same native artifact tag already on phone; consumed,no boot/retry')
        if digest(bundle['pins']['boot']['path']) != bundle['pins']['boot']['sha256']:
            raise RuntimeError('reviewed boot image changed; consumed,no boot/retry')
        manifest['BCB'] = fresh_bcb(io, out)
        record()
        io.adb_call('reboot', 'bootloader')
        io.deadline = min(overall_deadline, time.monotonic()+30)
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
        io.deadline = overall_deadline
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
                from zorn_recovery_identity import PROPERTIES, inspect_recovery
                properties = {key: io.adb_call('shell', 'getprop', key, timeout=3) for key in PROPERTIES}
                inspect_recovery(properties)
                break
            except (subprocess.SubprocessError, ValueError):
                pass
            if time.monotonic() >= io.deadline:
                raise RuntimeError('no Recovery within600s; STOP device operations, no recovery flashing')
            time.sleep(min(2, max(0, io.deadline-time.monotonic())))
        manifest['recovery_observed_seconds'] = time.monotonic()-started
        io.deadline = min(overall_deadline, time.monotonic()+180)
        after = recovery(io, bundle['pins'], accepted_recovery=bundle['accepted_recovery'])
        manifest['recovery_identity_after'] = io.recovery_identity
        for name, raw in after.items():
            (out/('after-'+name+'.bin')).write_bytes(raw)
        if before != after:
            raise RuntimeError('actual GPT/root/Data/fences changed')
        newlog = io.read('/dev/block/by-name/unixnu', 2291712, 1)
        (out/'checkpoints.bin').write_bytes(newlog)
        manifest.update(status='recovered-native-record-unavailable-unqualified',
                        log_changed=newlog != oldlog, kernel_record_available=False,
                        platform_entry_proven=False, GPU_execution_proven=False,
                        native_writer_readback_success_proven=False,
                        root_or_desktop_proven=False,
                        terminal_observer=bundle['terminal_observer'])
        try:
            decoded = record_inspector(bundle)(newlog, artifact_tag(bundle), oldlog)
            (out/'decoded-native-record.json').write_text(json.dumps(decoded, indent=2)+'\n')
            manifest['kernel_record_available'] = True
            if decoded['can_support_fresh_trial_when_bound_to_actual_capture_and_bundle']:
                # Only here: actual fixed Transport captured both pages from
                # identified Recovery, all GPT/root/Data/fences matched, and
                # the exact reviewed bundle binds the fresh native tag/CRC.
                manifest.update(status='recovered-native-root-input-observation',
                                platform_entry_proven=True, CPU_root_input_observation=decoded.get('CPU_root_input_observation'))
        except ValueError as error:
            manifest['native_record_refusal'] = str(error)
        manifest['note'] = ('Only the fresh actual CPU-staging observation and record-worker/UFS path are eligible; '
                            'no GPU,root,terminal-reset completion or native readback ACK inferred')
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
    flag = '--ios26-root-input-probe-image' if mode == 'build' else '--ios26-root-input-probe-trial'
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

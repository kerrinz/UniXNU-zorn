"""Fixed281 new-stack known-image trial; package checks never access the phone.

Execution additionally requires the actual271->281 installation receipt, exact
independent bundle archives and fresh owner/ready/admission. No installation,
server bootstrap, retry or recovery flashing is implemented here.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import plistlib
import struct
import tomllib

from zorn_ios26_logdirs_boot_trial import CURRENT, STAGE, load, sha, probe_existing_adb_listener, run
from zorn_ios26_gpu_v268_system_trial import ARGS, PROTECTIONS, record_result

TAG = '36e4614944b04a64bee5499cb2e8338f'
PROBE_TAG = 'ddb9c8640ab544cd85cae684e0fb8f66'
SCOPE = 'single-K80-ios26-gpu-v281-known-image-300s-36e46149'
BASE = STAGE / ('k80-gpu-v281-upstream-known-image-' + TAG)
TRIAL = BASE / 'root-trial'
PACKAGE = BASE / 'boot-package/verified.json'
REVIEW = STAGE / 'k80-known281-root-delta-review-36e46149/review-inputs.json'
BOOT = '1d9e57e149139a53d9fcbdf5dad29cba745b3556b662741e5b0b42ab93204245'
KERNEL = 'd1e3e7ff3f80e44060b0e5a5b0e86169aef39a9dbdb73de09ca1153ee38ef2ee'
ROOT_SHA = 'b87e132bbf509d13ff3475606abef000a1f43478ad4889bdcfbf47eb0db39e8d'
ADT_SHA = '9aaa913f7861164c84cac130f6906f7b155528904ab69e0686a81e5e072bdfc6'
FD_SHA = '1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab'
REVIEW_SHA = '680b0ec4db336248fcdfe402958bb63a22e03f8262d19d3e624bd2efa1c7fe94'
SOURCES = {name: BASE / name for name in (
    'close-source-closure281.json', 'full-build-review.json',
    'full-link/exact-inputs.json', 'source-reuse281.json',
    'retained-upstream-stack-and-probe281.json', 'native-platform-config.json',
    'known-capture-current-host281/result.json', 'known-receiver-current-host281/result.json',
    'known-camera-host281/result.json')}
SOURCES.update({name: Path(__file__).with_name(name) for name in (
    'zorn_ios26_gpu_v281_system_trial.py', 'zorn_ios26_known281_capture.py',
    'zorn_ios26_known281_receiver.py', 'read-zorn-gpu-known281-cdc.py', 'read-zorn-gpu-census268-cdc.py',
    'prepare-ios26-known281-trial.py',
    'check-ios26-known-finalization281.py',
    'check-ios26-known-admission281.py',
    'zorn_ios26_metal_root_delta.py',
    'capture-zorn-video281.py', 'capture-zorn-video268.py',
    'inspect_ios26_client_census268.py', 'inspect_ios26_metal_probe267.py',
    'inspect_ios26_gpu_early252_record.py', 'inspect_ios26_lockscreen_touch_cpu_record.py',
    'inspect_ios26_gpu_progress236.py', 'inspect_ios26_gpu_shot265.py',
    'zorn_ios26_logdirs_boot_trial.py', 'zorn_gpu_resource_trial.py',
    'zorn_ios26_gpu_v268_system_trial.py',
    'zorn_recovery_identity.py', 'run-zorn-debug.py', 'build-zorn-debug.py')})
SOURCES.update(root_install_review=REVIEW,
               root_install_receipt=REVIEW.parent / 'admission/run/result.json',
               root_install_admission=REVIEW.parent / 'admission/admission.json',
               root_install_claim=REVIEW.parent / 'admission/run/one-shot.claim.json')
SOURCES['camera_binary'] = Path('/opt/homebrew/bin/ffmpeg').resolve()
# The shared runner consumes semantic role names, not decoder filenames.
SOURCES.update({role:Path(__file__).with_name(name) for role,name in {
    'record_decoder':'inspect_ios26_gpu_early252_record.py',
    'record_helpers':'zorn_gpu_ios26_platform_record.py',
    'record_envelope':'inspect_ios26_lockscreen_touch_cpu_record.py'}.items()})
ARTIFACTS = {'boot', 'kernel', 'FAT', 'fd', 'ADT', 'loader', 'manager', 'menu', 'package', 'record_identity'}
TOOLS = {'adb_binary', 'fastboot_binary', 'host_adb_proof'}
PROTECTED_HASHES = dict(
    primary_GPT='ebe6365fefb07e8693e5f4e32e3b4e7fc065a73518becd9b0de7e16318ead967',
    backup_GPT='c659f0aecb0f237147a8810adc540f4c26b4d31c467985471bf4179f2cb4c054',
    root_manifest='bc908a6cf66491055077798550660f40128bfe6dce2fdc0db56e6af96511208d',
    Data_header='e4ce50884e09f6d376d428e2e8f7bc05da0448e1afd7a5ba0749cbe92d12f99d',
    Data_metadata='c0e97aa04664934c02336391204760f9e09979a43ce9b86991be2b9b32f2d300',
    root_before='ad7facb2586fc6e966c004d7d1d16b024f5805ff7cb47c7a85dabd8b48892ca7',
    root_after='ad7facb2586fc6e966c004d7d1d16b024f5805ff7cb47c7a85dabd8b48892ca7')
EXPECTED = dict(scope=SCOPE, serial='92988a43', product='zorn', slot='a',
    trial_seconds=300, timeout_seconds=600, retries=0, watchdog_mode=1,
    accepted_recovery='twrp-or-orangefox', existing_server_only=True,
    native_log_absolute_lba=49563392, native_log_blocks=1,
    root_read_only=True, data_read_only=True, transient_boot=True,
    bootstrap_allowed=False, gpu_firmware_start=True, allow_boot=False)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pinned(row):
    p = Path(row['path'])
    require(p.is_absolute() and p.resolve() == p and not p.is_symlink() and
            p.is_file() and sha(p) == row['sha256'], '281 source/check changed: ' + str(p))


def validate_package(proof=None):
    proof = load(PACKAGE) if proof is None else proof
    require(proof['version'] == 281 and proof['run_id'] == TAG and
            proof['artifact_identity']['application_probe_run_id'] == PROBE_TAG,
            '281 boot/program identity differs')
    require(proof['boot']['sha256'] == BOOT and proof['link']['sha256'] == KERNEL and
            proof['root']['sha256'] == ROOT_SHA and proof['pins']['ADT']['sha256'] == ADT_SHA and
            proof['pins']['FD']['sha256'] == FD_SHA, '281 exact tuple differs')
    require(proof['boot_args'] == ARGS and proof['watchdog_seconds'] == 300 and
            proof['recovery_timeout_seconds'] == 600 and proof['retries'] == 0 and
            proof['runtime_roots_read_only'] is True and proof['storage_layout_changed'] is False,
            '281 bounded configuration differs')
    require(proof['ordinary_client'] == 'zorn-metal-probe193' and
            proof['probe_job_disabled'] is False and proof['synthetic_input_enabled'] is False and
            proof['human_input_required'] is False, '281 unattended known-image path differs')
    for row in (proof['boot'], proof['FAT']):
        pinned(row)
    for name in ('kernel', 'ADT', 'FD'):
        pinned(dict(path=proof['pins'][name]['archive'], sha256=proof['pins'][name]['sha256']))
    closure = load(BASE / 'close-source-closure281.json')
    require(closure['passed'] is True and closure['kernel_sha256'] == KERNEL and
            closure['root_sha256'] == ROOT_SHA and closure['boot_tag'] == TAG and
            closure['program_tag'] == PROBE_TAG, '281 current native closure differs')
    for row in closure['checks']:
        pinned(row)
        if Path(row['path']) == BASE / 'root-candidate/layout-and-replay-result.json':
            layout = load(row['path'])
            require(layout['status'] == 'new-known281-root-layout-recomputed-and-local-delta-replay-matched' and
                    layout['candidate_image']['sha256'] == layout['replay_image']['sha256'] == ROOT_SHA and
                    layout['changed_pages'] == 11897 and layout['write_groups'] == 227 and
                    layout['proposed_relative_first_lba'] == 6291712 and layout['layout_change'] is False,
                    '281 exact local replay/layout differs')
        else:
            require(load(row['path']).get('passed') is True, '281 current native check failed: '+row['path'])
    full = load(BASE / 'full-build-review.json')
    require(full['inputs_verified'] == proof['link']['inputs'] == 1398 and
            proof['link']['undefined_symbols'] == 0 and len(full['header_checks']) == 128,
            '281 complete link/header closure differs')
    pinned(proof['link']['exact_inputs'])
    for row in load(BASE / 'full-link/exact-inputs.json'):
        pinned(row)
    for row in full['header_checks']:
        # Compiler dependencies can retain lexical ../ between owned source
        # directories. Compare the actual file, preserving the recorded digest.
        pinned(dict(path=str(Path(row['resolved']).resolve()), sha256=row['sha256']))
    native = load(BASE / 'native-platform-config.json')
    require(native['CPU_page_bytes'] == 16384 and native['macros']['ARM_PGSHIFT'] == '14',
            '281 native CPU16KiB required')
    source = Path(load(BASE / 'candidate.json')['source'])
    projection = load(BASE / 'source-reuse281.json')
    for row in projection['unchanged_from280']:
        pinned(dict(path=str(source / row['file']), sha256=row['sha256']))
    manifest = Path(__file__).resolve().parents[1] / 'patches/gpu/ios26-upstream-known281/source-manifest.json'
    manifest = load(manifest)
    for name in ('closure', 'full_link', 'effective_headers', 'source_projection', 'new_stack_and_probe'):
        pinned(manifest[name])
    for row in manifest['changed_files']:
        pinned(row['candidate'])
    # Newly changed host receivers require their own current-source receipts.
    for name in ('known-capture-current-host281/result.json', 'known-receiver-current-host281/result.json', 'known-camera-host281/result.json'):
        receipt = load(BASE / name)
        require(receipt['passed'] is True and receipt['phone_access'] is False,
                '281 current receiver host check failed')
        for key in ('source', 'receiver', 'postprocessor', 'test_tool', 'retained_serial_transport', 'retained_camera_backend'):
            if key in receipt:
                pinned(receipt[key])
    for row in projection['retained_same_source_tests']:
        pinned(row)
        require(load(row['path'])['passed'] is True, '281 retained same-source check failed')
    pinned(proof['root_result'])
    root = load(proof['root_result']['path'])
    require(root['passed'] is True and root['sha256'] == ROOT_SHA and
            root['signature_verified'] is True and root['filesystem_verified'] is True and
            root['monitored_attributes_preserved'] is True, '281 root composition differs')
    policy = BASE / 'root-policy'
    require((policy / 'NativeAdrenoMetal.clients').read_text() == 'zorn-metal-probe193\n',
            '281 ordinary-client policy differs')
    for name, path in (('System/Library/Extensions/NativeAdrenoMetal.clients', policy / 'NativeAdrenoMetal.clients'),
                       ('System/Library/LaunchDaemons/org.unixnu.zorn.metal-probe193.plist', policy / 'org.unixnu.zorn.metal-probe193.plist')):
        require(root['monitored_after_sha256'][name] == sha(path), '281 composed root policy hash differs')
    job = plistlib.loads((policy / 'org.unixnu.zorn.metal-probe193.plist').read_bytes())
    require(job['RunAtLoad'] is True and job['Disabled'] is False and
            job['KeepAlive'] is False and job['ProgramArguments'] == ['/redwood/sbin/zorn-metal-probe193'],
            '281 bounded probe job differs')
    pinned(proof['root_adt_binding'])
    binding = load(proof['root_adt_binding']['path'])
    require(binding['root_sha256'] == ROOT_SHA and binding['unrelated_bytes_preserved'] is True,
            '281 root/ADT binding differs')
    stack = load(BASE / 'retained-upstream-stack-and-probe281.json')
    for name in ('new_stack', 'new_Turnip', 'Metal_runtime', 'probe_build'):
        pinned(stack[name])
    bundle = load(stack['new_stack']['path'])
    require(bundle['ABI'] == 1 and bundle['CPU_page_bytes'] == 16384 and
            bundle['GPU_page_bytes'] == bundle['signature_page_bytes'] == 4096,
            '281 selected Metal memory/ABI differs')
    for name, digest in bundle['files'].items():
        pinned(dict(path=str(Path(bundle['bundle']) / name), sha256=digest))
    return proof


def validate_installation():
    require(SOURCES['root_install_receipt'].is_file(), '281 root installation/readback absent; no probe/claim')
    require(sha(REVIEW) == REVIEW_SHA, '281 installation review differs')
    receipt = load(SOURCES['root_install_receipt'])
    require(receipt['scope'] == 'K80-persistent-iOS26-known281-36e46149' and
            receipt['installed'] is True and receipt['booted'] is False and
            receipt['protected_metadata_and_fences_unchanged'] is True and
            receipt['phase'] == 'root-delta-installed-written-blocks-readback-verified' and
            receipt['pages_written'] == 11897 and receipt['expected_image_sha256'] == ROOT_SHA and
            receipt['readback'] == dict(scope='written4KiB-root-pages-only', blocks=11897,
                bytes=48730112, sha256='0f4fa912db5f8be69e6dd484b9df0d8cac77fac7ed713ca401ec7d8e31be49bd'),
            '281 actual root installation incomplete/different')
    import zorn_ios26_metal_root_delta as installer
    review = installer.validate_review(REVIEW, installer.INSTALLS[installer.KNOWN281_FLAG])
    admission = load(SOURCES['root_install_admission'])
    required = dict(scope='K80-persistent-iOS26-known281-36e46149', review_sha256=REVIEW_SHA,
        serial='92988a43', product='zorn', slot='a', partition='unixnu',
        relative_first_lba=6291712, old_root_sha256=review['window']['old_root_sha256'],
        new_root_sha256=ROOT_SHA, blocks=8388608, changed_pages=11897, write_groups=227,
        timeout_seconds=600, retries=0, allow_install=True, allow_boot=False,
        full_phone_root_readback=False, layout_change=False,
        entry_sha256=sha(installer.__file__), runner_sha256=sha(Path(__file__).with_name('run-zorn-debug.py')))
    def matches(row, expected):
        return all(type(row.get(k)) is type(v) and row[k] == v for k,v in expected.items())
    require(matches(admission, required), '281 installation admission differs')
    for role, flag in (('owner', 'approved'), ('ready', 'ready')):
        row = admission[role]
        require(Path(row['path']) == SOURCES['root_install_admission'].parent / (role+'.json'),
                '281 installation '+role+' path differs')
        pinned(row)
        require(matches(load(row['path']), dict(required, **{flag:True})),
                '281 installation '+role+' binding differs')
    claim = load(SOURCES['root_install_claim'])
    require(matches(claim, dict(scope=required['scope'],
        admission_sha256=sha(SOURCES['root_install_admission']),
        consumed_before_first_USB=True, reusable=False)), '281 installation claim differs')
    require(receipt.get('last_verified_group') == 226 and
            all(receipt.get(k, {}).get('family') in ('TWRP','OrangeFox') for k in
                ('recovery_identity_before','recovery_identity_after')), '281 installation completion/Recovery differs')
    plan = installer.reviewed_module(review, 'plan_source', 'known281_completed_plan')
    _, parts, retained = plan.load_plan()
    require(receipt.get('last_verified_block') == parts[-1][0], '281 final verified group differs')
    verify_install_readbacks(SOURCES['root_install_receipt'].parent, parts, retained,
                            Path(review['pins']['previous_misc']['path']).read_bytes())
    state = load(CURRENT)
    require(state['gpu_discovery'].get('current_phone_root_expected_sha256') == ROOT_SHA,
            '281 current phone root differs')


def verify_install_readbacks(directory, parts, retained, misc_reference):
    """Verify archived source-defined bytes, not a JSON success flag alone."""
    directory = Path(directory)
    require(len(parts) == 227 and sum(len(new)//4096 for _,_,new in parts) == 11897,
            '281 readback group coverage differs')
    expected_names = {f'delta-{block:07}.{phase}.bin' for block,_,_ in parts for phase in ('before','after')}
    require({p.name for p in directory.glob('delta-*.bin')} == expected_names,
            '281 readback files missing/extra')
    digest = hashlib.sha256()
    for block, old, new in parts:
        for phase, expected in (('before',old), ('after',new)):
            p = directory / f'delta-{block:07}.{phase}.bin'
            require(not p.is_symlink() and p.read_bytes() == expected,
                    '281 archived root '+phase+' differs at '+str(block))
        digest.update(new)
    require(digest.hexdigest() == '0f4fa912db5f8be69e6dd484b9df0d8cac77fac7ed713ca401ec7d8e31be49bd',
            '281 aggregate readback differs')
    prior = directory / 'prior-root-changed-pages.before.bin'
    require(not prior.is_symlink() and prior.read_bytes() == b''.join(raw for _,raw in retained),
            '281 retained parent readback differs')
    hashes = {k:PROTECTED_HASHES[k] for k in ('primary_GPT','backup_GPT','root_manifest')}
    hashes.update(Data=PROTECTED_HASHES['Data_metadata'], before=PROTECTED_HASHES['root_before'],
                  after=PROTECTED_HASHES['root_after'])
    for name in list(hashes)+['log','misc']:
        before, after = (directory / (name+'.'+phase+'.bin') for phase in ('before','after'))
        require(not before.is_symlink() and not after.is_symlink() and before.read_bytes() == after.read_bytes(),
                '281 archived protected '+name+' changed')
        if name in hashes:
            require(sha(before) == hashes[name], '281 protected '+name+' baseline differs')
        else:
            require(before.stat().st_size == 4096, '281 protected log/misc width differs')
    from zorn_ios26_metal_root_delta import inspect_misc_page
    inspect_misc_page((directory / 'misc.before.bin').read_bytes(), misc_reference)


def validate(path):
    require(not path.is_symlink() and path.resolve() == TRIAL / 'bundle.json', '281 canonical bundle required')
    # Refuse an uninstalled candidate before any listener, claim or controller edit.
    validate_installation()
    return validate_bundle_contents(load(path))


def validate_bundle_contents(b):
    """Pure local content check, also usable before publishing a final bundle."""
    require(all(type(b.get(k)) is type(v) and b[k] == v for k, v in EXPECTED.items()),
            '281 exact scope differs')
    pins = b['pins']
    require(set(pins) == ARTIFACTS | PROTECTIONS | TOOLS | SOURCES.keys(), '281 complete role set required')
    for role, row in pins.items():
        pinned(row)
        src, archive = Path(row['path']), Path(row['archive'])
        require(archive.parent == TRIAL / 'archive' and not archive.is_symlink() and
                archive.is_file() and not src.samefile(archive) and sha(archive) == row['sha256'],
                '281 independent archive differs: ' + role)
    require(all(Path(pins[k]['path']) == p for k, p in SOURCES.items()), '281 fixed source paths differ')
    proof = validate_package(load(pins['package']['path']))
    require(Path(pins['package']['path']) == PACKAGE and pins['boot']['sha256'] == BOOT and
            pins['kernel']['sha256'] == KERNEL and pins['ADT']['sha256'] == ADT_SHA and
            pins['fd']['sha256'] == FD_SHA, '281 packaged tuple differs')
    require(all(pins[k]['sha256'] == digest for k,digest in PROTECTED_HASHES.items()),
            '281 protected GPT/17/Data/fences differ')
    with Path(proof['root']['image']).open('rb') as stream:
        expected_first_page = stream.read(4096)
    require(Path(pins['root_first_page']['path']).read_bytes() == expected_first_page,
            '281 local root first-page expectation differs')
    require(pins['adb_binary']['sha256'] == '1811e253b21b12cbfda7201ebaf86c10e7ddcb5c606a7a81f7c82b4c429c2d3b' and
            pins['fastboot_binary']['sha256'] == 'c97aa28970ba9a46023a8ca52a78dd6547c2c1c4133f9715d4fe551e1dfae152',
            '281 fixed SDK37 tool bytes differ')
    for row in proof['FAT_members']:
        role = {'BOOTAA64.EFI':'manager', 'DarwinBoot26.efi':'loader', 'kernel.macho':'kernel',
                'kernel.macho.adt':'ADT', 'unixnu.toml':'menu'}[Path(row['FAT_path']).name]
        require(pins[role]['sha256'] == row['sha256'], '281 FAT member differs: ' + role)
    menu = tomllib.loads(Path(pins['menu']['path']).read_text())
    require(len(menu['entry']) == 1 and menu['entry'][0]['args'] == ARGS and
            not menu['boot']['connect_all'] and not menu['kits']['autoload'], '281 single bounded menu differs')
    raw = Path(pins['boot']['path']).read_bytes()
    require(raw[:8] == b'ANDROID!' and struct.unpack_from('<I', raw, 40)[0] == 4,
            '281 Android v4 carrier required')
    size = struct.unpack_from('<I', raw, 8)[0]
    payload = gzip.decompress(raw[4096:4096+size])
    fat = Path(pins['FAT']['path']).read_bytes()
    require(payload[4096:] == Path(pins['fd']['path']).read_bytes() + fat, '281 complete compressed carrier differs')
    for sector in (0, 6):
        require(fat[sector*512+0x180:sector*512+0x1a0] ==
                b'ZORNGHWD'+struct.pack('<II', 1, 0xfffffffe)+b'ZORNTPWR'+struct.pack('<II', 1, 0xfffffffe),
                '281 WDT/power markers differ')
    require(load(pins['record_identity']['path'])['run_id'] == TAG and
            load(pins['host_adb_proof']['path'])['adb_sha256'] == pins['adb_binary']['sha256'],
            '281 record/tool identity differs')
    # Exercise the actual late-run consumer before any claim/device action.
    from zorn_gpu_ios26_platform_record import artifact_tag, record_inspector
    require(artifact_tag(b) == bytes.fromhex(TAG) and callable(record_inspector(b)),
            '281 shared record consumer interface differs')
    return b


def validate_boot_admission(bundle_path, admission_path):
    require(admission_path == TRIAL / 'admission.json', '281 exact admission required')
    paths = {name:TRIAL/(name+'.json') for name in ('owner','ready','admission')}
    require(all(not p.is_symlink() for p in paths.values()), '281 admission symlink refused')
    return validate_boot_records(bundle_path, load(paths['owner']), load(paths['ready']),
        load(paths['admission']), sha(paths['owner']), sha(paths['ready']))


def validate_boot_records(bundle_path, owner, ready, admission, owner_sha256, ready_sha256):
    """Pure record validation, shared with the producer before publication."""
    binding = dict(scope=SCOPE, nonce=TAG, bundle_sha256=sha(bundle_path), boot_sha256=BOOT, allow_boot=True)
    for name in ('owner', 'ready', 'admission'):
        row = {'owner':owner, 'ready':ready, 'admission':admission}[name]
        require(all(type(row.get(k)) is type(v) and row[k] == v for k,v in binding.items()), '281 fresh '+name+' differs')
        if name != 'admission':
            require({'owner':owner_sha256, 'ready':ready_sha256}[name] == admission[name+'_sha256'], '281 '+name+' changed after admission')
    require(ready.get('host_checks_passed') is True and ready.get('one_boot') is True and
            ready.get('timeout_seconds') == 600 and ready.get('watchdog_seconds') == 300 and
            isinstance(ready.get('hardware_only_pending'), list) and ready['hardware_only_pending'] and
            ready.get('host_checks'), '281 bounded ready/current checks/hardware pending required')
    for row in ready['host_checks']:
        pinned(row)
        require(load(row['path']).get('passed') is True, '281 ready host test failed')
    required_checks = {BASE / n for n in ('known-capture-current-host281/result.json',
        'known-receiver-current-host281/result.json', 'known-camera-host281/result.json',
        'known-trial-readback-host281/result.json', 'known-finalization-current-host281/result.json')}
    require(required_checks <= {Path(row['path']) for row in ready['host_checks']},
            '281 ready must include all current receiver/camera/entry checks')
    entry_check = load(BASE / 'known-trial-readback-host281/result.json')
    pinned(entry_check['source'])
    pinned(entry_check['fixed_runner'])
    pinned(entry_check['test_tool'])
    finalization_check = load(BASE / 'known-finalization-current-host281/result.json')
    pinned(finalization_check['source'])
    pinned(finalization_check['prepare_source'])
    pinned(finalization_check['test_tool'])
    return ready


def require_idle_trial():
    state = load(CURRENT)
    require(state['gpu_discovery'].get('current_mode') == 'unattended-phone-connected' and
            not any(state.get(k) for k in ('active_run','active_admission','active_build','runner_session','stop_device_operations')) and
            not state['gpu_discovery'].get('active_admission'), '281 device busy/stopped/mode differs')
    claim = TRIAL / 'trial/one-shot.claim.json'
    require(not claim.exists() and not claim.is_symlink(), '281 trial consumed; no repeat')
    return claim


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ios26-known281-trial', action='store_true')
    parser.add_argument('--check-package', action='store_true')
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--admission', type=Path)
    args = parser.parse_args()
    if args.check_package:
        require(args.bundle is None and args.admission is None, '281 package-only mode takes no admission')
        validate_package()
        print('281 exact package/source/receiver checks passed; root installation not inferred; no USB/claim')
        return
    require(args.bundle is not None, '281 canonical bundle required')
    bundle = validate(args.bundle)
    if args.check_only:
        print('281 installed-root/bundle checks passed; no USB/claim')
        return
    validate_boot_admission(args.bundle, args.admission)
    claim = require_idle_trial()
    probe_existing_adb_listener()
    run(bundle, claim, record_result=record_result)


if __name__ == '__main__':
    main()

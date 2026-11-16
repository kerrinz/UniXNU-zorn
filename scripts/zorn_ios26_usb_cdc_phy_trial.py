"""Fixed CPU lockscreen continuous FT3683 carrier and Recovery transport binding."""
import argparse
from pathlib import Path
import struct
import tomllib

from zorn_ios26_logdirs_boot_trial import (
    CURRENT, STAGE, load, sha, probe_existing_adb_listener, run,
)

HERE = Path(__file__).resolve().parent
BASE = STAGE / 'k80-usb-cdc-phy26-2201ddb38f024f01850be974f83d3fde'
TRIAL = BASE / 'root-trial'
SCOPE = 'single-K80-ios26-cdc-phy-300s-2201ddb3'
BOOT = '71214b6f02cb7803a261f6155bca8d9716acac1336dda61d4c616f04e5c31d5a'
KERNEL = '6e7197fb2de11d4b7d08e0fdadd26247dc8979c32f3aed9697df7ed41fb86ba9'
ADT_SHA = 'ddd1e39d7af3e6e2117872c6df8275c5d39258d13106e19a4f44c70c6044612e'
TAG = '2201ddb38f024f01850be974f83d3fde'
ROOT_SHA = '227ba639a3f765fce15b1bb6f08ccf53f36872fd0a95bba7bb778f067c34e32e'
SOURCES = {
    'entry': Path(__file__),
    'fixed_builder': HERE / 'build-zorn-debug.py',
    'fixed_runner': HERE / 'run-zorn-debug.py',
    'transport_core': HERE / 'zorn_ios26_logdirs_boot_trial.py',
    'device_helpers': HERE / 'zorn_gpu_resource_trial.py',
    'recovery_identity': HERE / 'zorn_recovery_identity.py',
    'record_helpers': HERE / 'zorn_gpu_ios26_platform_record.py',
    'record_decoder': HERE / 'inspect_ios26_usb_cdc_phy_record.py',
    'wire_capture': HERE / 'read-zorn-usb-cdc-phy.py',
    'record_envelope': HERE / 'inspect_ios26_lockscreen_touch_cpu_record.py',
}
ARTIFACTS = {'boot', 'kernel', 'FAT', 'fd', 'ADT', 'loader', 'manager', 'menu', 'package', 'record_identity'}
PROTECTIONS = {'primary_GPT', 'backup_GPT', 'root_manifest', 'Data_header', 'Data_metadata',
               'root_first_page', 'root_before', 'root_after'}
TOOLS = {'installed_result', 'adb_binary', 'fastboot_binary', 'host_adb_proof'}
EXPECTED = dict(scope=SCOPE, serial='92988a43', product='zorn', slot='a',
                trial_seconds=300, timeout_seconds=600, retries=0, watchdog_mode=1,
                accepted_recovery='twrp-or-orangefox', existing_server_only=True,
                native_log_absolute_lba=49563392, native_log_blocks=1, root_read_only=True,
                data_read_only=True, transient_boot=True, bootstrap_allowed=False,
                gpu_firmware_start=False, allow_boot=False)


def validate(path):
    if path.is_symlink() or path.resolve() != TRIAL / 'bundle.json':
        raise ValueError('canonical CPU touch scope required')
    bundle = load(path)
    if any(type(bundle.get(k)) is not type(v) or bundle[k] != v for k, v in EXPECTED.items()):
        raise ValueError('CPU touch trial settings differ')
    pins = bundle['pins']
    if set(pins) != ARTIFACTS | PROTECTIONS | TOOLS | SOURCES.keys():
        raise ValueError('CPU touch trial inputs incomplete')
    for role, row in pins.items():
        source, archive = Path(row['path']), Path(row['archive'])
        if (not source.is_absolute() or source.is_symlink() or archive.is_symlink()
                or archive.parent != TRIAL / 'archive' or source.samefile(archive)
                or sha(source) != row['sha256'] or sha(archive) != row['sha256']):
            raise ValueError(f'CPU touch input differs: {role}')
    if any(Path(pins[k]['path']).resolve() != p.resolve() for k, p in SOURCES.items()):
        raise ValueError('fixed runner source differs')
    if pins['boot']['sha256'] != BOOT or pins['kernel']['sha256'] != KERNEL:
        raise ValueError('exact CPU touch boot and kernel required')
    proof = load(pins['package']['path'])
    if (proof['boot']['sha256'] != BOOT or proof['root']['sha256'] != ROOT_SHA
            or proof['touch_continuous'] is not True or proof['usb_controller_writes'] is not True or proof['usb_dma_enabled'] is not True
            or proof['cpu_accounting_samples_after_pid1_seconds'] != []
            or proof['no_home_button_adt'] is not True
            or proof['pins']['ADT']['sha256'] != ADT_SHA
            or not proof['WDT1_markers_both_present'] or not proof['actual_file_loader_parser_pass']):
        raise ValueError('carrier proof differs')
    for role, value in {'FAT': proof['FAT']['sha256'], 'fd': proof['pins']['FD']['sha256'],
                        'ADT': proof['pins']['ADT']['sha256']}.items():
        if pins[role]['sha256'] != value:
            raise ValueError(f'carrier input differs: {role}')
    for row in proof['FAT_members']:
        role = {'BOOTAA64.EFI': 'manager', 'DarwinBoot26.efi': 'loader',
                'kernel.macho': 'kernel', 'kernel.macho.adt': 'ADT',
                'unixnu.toml': 'menu'}[Path(row['FAT_path']).name]
        if pins[role]['sha256'] != row['sha256']:
            raise ValueError(f'FAT member differs: {role}')
    menu = tomllib.loads(Path(pins['menu']['path']).read_text())
    if len(menu['entry']) != 1 or menu['entry'][0]['args'] != proof['boot_args']:
        raise ValueError('single CPU touch menu entry required')
    tokens = menu['entry'][0]['args'].split()
    required = {'zorn26_touch=1', 'zorn26_touch_pacing=1', 'zorn26_touch_continuous=1',
                'zorn26_touch_record=1', 'zorn26_cpu_presenter=1', 'zorn_wdt=1',
                'zorn26_prearmed_recovery=1', 'zorn26_trial_seconds=300'}
    if tokens != ['rd=md0', '-v', 'keepsyms=1', 'houji_native_root=1', 'zorn26_root=1', 'zorn26_installed_root_trial=1', 'zorn_wdt=1', 'zorn26_prearmed_recovery=1', 'zorn26_trial_seconds=300', 'zorn26_cpu_presenter=1', 'zorn26_software_accelerator=1', 'sample=0', 'sb_wallpaper=0', 'zorn26_touch=1', 'zorn26_touch_pacing=1', 'zorn26_touch_continuous=1', 'zorn26_touch_record=1', 'zorn26_usb_cdc_tx=1'] or not required.issubset(tokens) or any(arg.startswith(('zorn26_gpu_', 'zorn26_userland_progress',
                                                            'zorn26_touch_limit')) for arg in tokens):
        raise ValueError('exact continuous touch and CPU presenter selection required')
    with Path(pins['FAT']['path']).open('rb') as stream:
        for sector in (0, 6):
            stream.seek(sector * 512 + 0x180)
            mode = struct.pack('<II', 1, 0xfffffffe)
            if stream.read(32) != b'ZORNGHWD' + mode + b'ZORNTPWR' + mode:
                raise ValueError('watchdog or FT3683 power marker differs')
    installed = load(pins['installed_result']['path'])
    if (installed['expected_image_sha256'] != ROOT_SHA or installed['installed'] is not True
            or installed['protected_metadata_and_fences_unchanged'] is not True
            or installed['phase'] != 'root-delta-installed-written-blocks-readback-verified'
            or installed['readback'] != dict(scope='written4KiB-root-pages-only', blocks=66,
                bytes=270336, sha256='16aed0f9d4e71d6d86d54a375e42f4f5bc23e459239b6f7cc07dd58da1346e76')):
        raise ValueError('CPU baseline root delta receipt differs')
    if load(pins['host_adb_proof']['path'])['adb_sha256'] != pins['adb_binary']['sha256']:
        raise ValueError('ADB identity differs')
    if load(pins['record_identity']['path'])['run_id'] != TAG:
        raise ValueError('artifact ID differs')
    return bundle


def record_result(decoded):
    if decoded['tx_status'] is None:
        raise ValueError('missing CDC transmit result')
    return dict(status='recovered-fresh-USB-CDC-transmit',
                usb_preflight=decoded['result'],
                usb_sid40_matches=decoded['stream_matches'],
                usb_tx_status=decoded['tx_status'], usb_cdc_state=decoded['cdc_state'], usb_phy=decoded['phy'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',
                        type=Path, required=True, dest='bundle')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--admission', type=Path)
    args = parser.parse_args()
    bundle = validate(args.bundle)
    if args.check_only:
        print('CDC preflight host inputs verified; no USB or claim')
        return
    if args.admission is None or args.admission.resolve() != TRIAL / 'admission.json':
        parser.error('exact local admission required')
    admission = load(args.admission)
    binding = dict(scope=SCOPE, nonce=TAG, bundle_sha256=sha(args.bundle), boot_sha256=BOOT, allow_boot=True)
    for name in ('owner', 'ready', 'admission'):
        row = admission if name == 'admission' else load(TRIAL / (name + '.json'))
        if any(row.get(k) != v for k, v in binding.items()):
            raise ValueError(f'{name} does not bind the exact CPU touch scope')
        if name != 'admission' and sha(TRIAL / (name + '.json')) != admission[name + '_sha256']:
            raise ValueError(f'{name} changed after admission')
    state = load(CURRENT)
    if state.get('gpu_discovery', {}).get('current_mode') != 'unattended-phone-connected':
        raise ValueError('unattended phone mode required')
    claim = TRIAL / 'trial/one-shot.claim.json'
    if claim.exists() or claim.is_symlink():
        raise ValueError('CPU touch trial already consumed')
    probe_existing_adb_listener()
    run(bundle, claim, record_result=record_result)


if __name__ == '__main__':
    main()

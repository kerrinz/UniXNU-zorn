"""Fixed v94 guarded mapping carrier and Recovery transport binding."""
import argparse
from pathlib import Path
import struct
import tomllib

from zorn_ios26_logdirs_boot_trial import (
    CURRENT, STAGE, load, sha, probe_existing_adb_listener, run,
)

HERE = Path(__file__).resolve().parent
BASE = STAGE / 'k80-gpu-guarded-map-mount-worker-package-v94-20261113'
TRIAL = BASE / 'root-trial'
SCOPE = 'single-K80-ios26-v94-guarded-register-mapping-300s'
BOOT = '5d26fc3df944b31ef5b93667172627902f70004492f99bd3287916a6708bc99d'
KERNEL = '986c3f49bd75be529e3e902ba0b84419ca806aa555b94bf6f0a4584ec5c71c99'
TAG = 'd892d63888654e5995013729fb07a907'
ROOT_SHA = '227ba639a3f765fce15b1bb6f08ccf53f36872fd0a95bba7bb778f067c34e32e'
SOURCES = {
    'entry': Path(__file__),
    'fixed_builder': HERE / 'build-zorn-debug.py',
    'fixed_runner': HERE / 'run-zorn-debug.py',
    'transport_core': HERE / 'zorn_ios26_logdirs_boot_trial.py',
    'device_helpers': HERE / 'zorn_gpu_resource_trial.py',
    'recovery_identity': HERE / 'zorn_recovery_identity.py',
    'record_helpers': HERE / 'zorn_gpu_ios26_platform_record.py',
    'record_decoder': HERE / 'inspect_ios26_guarded_gpu_maps_record.py',
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
        raise ValueError('canonical v94 scope required')
    bundle = load(path)
    if any(type(bundle.get(k)) is not type(v) or bundle[k] != v for k, v in EXPECTED.items()):
        raise ValueError('v94 trial settings differ')
    pins = bundle['pins']
    if set(pins) != ARTIFACTS | PROTECTIONS | TOOLS | SOURCES.keys():
        raise ValueError('v94 trial inputs incomplete')
    for role, row in pins.items():
        source, archive = Path(row['path']), Path(row['archive'])
        if (not source.is_absolute() or source.is_symlink() or archive.is_symlink()
                or archive.parent != TRIAL / 'archive' or source.samefile(archive)
                or sha(source) != row['sha256'] or sha(archive) != row['sha256']):
            raise ValueError(f'v94 input differs: {role}')
    if any(Path(pins[k]['path']).resolve() != p.resolve() for k, p in SOURCES.items()):
        raise ValueError('fixed runner source differs')
    if pins['boot']['sha256'] != BOOT or pins['kernel']['sha256'] != KERNEL:
        raise ValueError('exact v94 boot and kernel required')
    proof = load(pins['package']['path'])['package']
    if (proof['boot']['sha256'] != BOOT or proof['root_image_sha256'] != ROOT_SHA
            or not proof['WDT1_markers_both_present'] or not proof['compressed_payload_closure_verified']):
        raise ValueError('carrier proof differs')
    for role, value in {'FAT': proof['FAT']['sha256'], 'fd': proof['FD_sha256'],
                        'ADT': proof['ADT_sha256']}.items():
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
        raise ValueError('single v94 menu entry required')
    tokens = menu['entry'][0]['args'].split()
    if 'zorn26_gpu_guarded_map_mount_record=1' not in tokens or 'zorn26_gpu_board_record=1' in tokens:
        raise ValueError('exact root mount observation selector required')
    fat = Path(pins['FAT']['path'])
    with fat.open('rb') as stream:
        stream.seek(0x180)
        if stream.read(16) != b'ZORNGHWD' + struct.pack('<II', 1, 0xfffffffe):
            raise ValueError('actual FAT watchdog marker differs')
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
    return dict(status='recovered-fresh-guarded-mapping-record', root_mount_proven=True,
                PID1_image_activation_proven=decoded['pid1_el0'], guarded_register_mapping_complete=
                decoded['guarded_register_mapping_complete'])


def main(mode='run'):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ios26-guarded-gpu-maps-' + ('image' if mode == 'build' else 'trial'),
                        type=Path, required=True, dest='bundle')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--admission', type=Path)
    args = parser.parse_args()
    bundle = validate(args.bundle)
    if args.check_only:
        print('v94 host inputs verified; no USB or claim')
        return
    if mode != 'run' or args.admission is None or args.admission.resolve() != TRIAL / 'admission.json':
        parser.error('exact local admission required')
    admission = load(args.admission)
    binding = dict(scope=SCOPE, nonce=TAG, bundle_sha256=sha(args.bundle), boot_sha256=BOOT, allow_boot=True)
    for name in ('owner', 'ready', 'admission'):
        row = admission if name == 'admission' else load(TRIAL / (name + '.json'))
        if any(row.get(k) != v for k, v in binding.items()):
            raise ValueError(f'{name} does not bind the exact v94 scope')
        if name != 'admission' and sha(TRIAL / (name + '.json')) != admission[name + '_sha256']:
            raise ValueError(f'{name} changed after admission')
    state = load(CURRENT)
    if state.get('gpu_discovery', {}).get('current_mode') != 'unattended-phone-connected':
        raise ValueError('unattended phone mode required')
    claim = TRIAL / 'trial/one-shot.claim.json'
    if claim.exists() or claim.is_symlink():
        raise ValueError('v94 trial already consumed')
    probe_existing_adb_listener()
    run(bundle, claim, record_result=record_result)

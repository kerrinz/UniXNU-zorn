"""Fixed CPU lockscreen continuous FT3683 carrier and Recovery transport binding."""
import argparse
from pathlib import Path
import struct
import tomllib

from zorn_ios26_logdirs_boot_trial import (
    CURRENT, STAGE, load, sha, probe_existing_adb_listener, run,
)

HERE = Path(__file__).resolve().parent
BASE = STAGE / 'k80-gpu-v188-application-trial-864d745159824ae5a059e99c246302c1'
TRIAL = BASE / 'root-trial'
SCOPE = 'single-K80-ios26-gpu-v188-prepare-trace-300s-864d7451'
BOOT = 'f693862ebfb5c7f8f10cb8a760708f90fdee61df3a0542c13e5902e62c3660ab'
KERNEL = '751651bae3caf0319af0b4af8b8506f72c1f07391dee1d0621701f971c2748c6'
ADT_SHA = 'cd54d1c7870b7a9ad223002fd49ebe961c89bb05879122aff73230a0d999c312'
TAG = '864d745159824ae5a059e99c246302c1'
ROOT_SHA = '4d636e89dd1f4b22539e682e00b3d304f9612f71d4d17bfe26b5482e33f04167'
SOURCES = {
    'entry': Path(__file__),
    'preparation_decoder': HERE / 'inspect_ios26_gpu_prepare188.py',
    'application_decoder': HERE / 'inspect_ios26_gpu_application186.py',
    'fixed_builder': HERE / 'build-zorn-debug.py',
    'fixed_runner': HERE / 'run-zorn-debug.py',
    'transport_core': HERE / 'zorn_ios26_logdirs_boot_trial.py',
    'device_helpers': HERE / 'zorn_gpu_resource_trial.py',
    'recovery_identity': HERE / 'zorn_recovery_identity.py',
    'record_helpers': HERE / 'zorn_gpu_ios26_platform_record.py',
    'record_decoder': HERE / 'inspect_ios26_gpu_ui_census_record.py',
    'percore_decoder': HERE / 'inspect_ios26_lockscreen_percore_record.py',
    'cdc_capture': HERE / 'read-zorn-gpu-application188-cdc.py',
    'gpu_base_decoder': HERE / 'inspect_ios26_gpu_s2cr_cdc_record.py',
    'record_envelope': HERE / 'inspect_ios26_lockscreen_touch_cpu_record.py',
}
ARTIFACTS = {'boot', 'kernel', 'FAT', 'fd', 'ADT', 'loader', 'manager', 'menu', 'package', 'record_identity', 'installed_cohort'}
PROTECTIONS = {'primary_GPT', 'backup_GPT', 'root_manifest', 'Data_header', 'Data_metadata',
               'root_first_page', 'root_before', 'root_after'}
TOOLS = {'installed_result', 'adb_binary', 'fastboot_binary', 'host_adb_proof'}
EXPECTED = dict(scope=SCOPE, serial='92988a43', product='zorn', slot='a',
                trial_seconds=300, timeout_seconds=600, retries=0, watchdog_mode=1,
                accepted_recovery='twrp-or-orangefox', existing_server_only=True,
                native_log_absolute_lba=49563392, native_log_blocks=1, root_read_only=True,
                data_read_only=True, transient_boot=True, bootstrap_allowed=False,
                gpu_firmware_start=True, allow_boot=False)


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
            or proof['touch_continuous'] is not True or proof['touch_checkpoint_seconds_after_pid1'] != 150
            or proof['cpu_accounting_samples_after_pid1_seconds'] != [25, 45]
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
    if tokens != ['rd=md0', '-v', 'keepsyms=1', 'houji_native_root=1', 'zorn26_root=1', 'zorn26_installed_root_trial=1', 'zorn_wdt=1', 'zorn26_prearmed_recovery=1', 'zorn26_trial_seconds=300', 'zorn26_cpu_presenter=1', 'zorn26_software_accelerator=1', 'sample=0', 'sb_wallpaper=0', 'zorn26_touch=1', 'zorn26_touch_pacing=1', 'zorn26_touch_continuous=1', 'zorn26_touch_record=1', 'zorn26_gpu_board_stage=1', 'zorn26_owned_clocks=1', 'zorn26_gpu_provider_claim=1', 'zorn26_commanddb_resources=1', 'zorn26_commanddb_resources_only=1', 'zorn26_rsc_managed=1', 'zorn26_clock_prefix=1', 'zorn26_domain_prefix=1', 'zorn26_register_maps=1', 'zorn26_gpu_guarded_maps=1', 'zorn26_gpu_guarded_smmu_id=1', 'zorn26_gpu_guarded_smmu_reserve=1', 'zorn26_gpu_smmu_context_read=1', 'zorn26_gpu_guarded_gmu_clocks=1', 'zorn26_gpu_guarded_cx_timer=1', 'zorn26_gpu_cdc=1', 'zorn26_gpu_cpu_memory_prep=1', 'zorn26_gpu_gmu_context_image=1', 'zorn26_gpu_gmu_direct_seed=1', 'zorn26_gpu_masked_global_irq=1', 'zorn26_smmu_active_faults=1', 'zorn26_gmu_context_irq=1', 'zorn26_gmu_blocked_stream=1', 'zorn26_gmu_program_bank=1', 'zorn26_gmu_observe_reset=1', 'zorn26_gmu_deferred_valid=21'] or not required.issubset(tokens) or any(arg.startswith(('zorn26_userland_progress',
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
            or installed['readback'] != dict(scope='written4KiB-root-pages-only', blocks=92,
                bytes=376832, sha256='9e4b8998c442561c3f8eece54fbced0fa70fd24cd04741b57131fac33a675c34')):
        raise ValueError('CPU baseline root delta receipt differs')
    cohort=load(pins['installed_cohort']['path'])
    if (cohort['package']['sha256']!=pins['package']['sha256'] or
            cohort['root_install_receipt']['sha256']!=pins['installed_result']['sha256'] or
            cohort['boot']['sha256']!=BOOT or cohort['root']['sha256']!=ROOT_SHA or
            cohort['system_booted'] is not False):
        raise ValueError('exact installed root/package cohort differs')
    if proof['application_probe_run_id'] != 'd55c2bab3d6d436386ca54c7b6a74f06':
        raise ValueError('exact retained application program identity differs')
    current=load(CURRENT)
    if current['gpu_discovery'].get('current_phone_root_expected_sha256')!=ROOT_SHA:
        raise ValueError('current root identity differs')
    if load(pins['host_adb_proof']['path'])['adb_sha256'] != pins['adb_binary']['sha256']:
        raise ValueError('ADB identity differs')
    if load(pins['record_identity']['path'])['run_id'] != TAG:
        raise ValueError('artifact ID differs')
    return bundle


def record_result(decoded):
    return dict(status='recovered-fresh-FT3683-percore-snapshot', root_mount_proven=True,
                PID1_image_activation_proven=True, cpu_online=decoded['cpu_online'],
                eight_cpus_available=decoded['cpu_online'] == 8,
                continuous_polling_observed=decoded['continuous_polling_observed'],
                all_eight_executed_work=decoded['all_eight_executed_work'],
                gpu_snapshot=decoded['gpu_snapshot'], context_reads_complete=decoded['context_reads_complete'], gmu_clock_complete=decoded['gmu_clock_complete'], endpoint_reservation_complete=decoded['endpoint_reservation_complete'],
                cx_timer_complete=decoded.get('cx_timer_complete',False), cx_timer_raw=decoded.get('cx_timer_raw'), cx_timer_samples=decoded.get('cx_timer_samples'), cx_timer_assessment=decoded.get('cx_timer_assessment'), gmu_ahb_raw=decoded.get('gmu_ahb_raw'),
                inactive_context=decoded.get('inactive_context'), global_irq=decoded.get('global_irq'), global_fault_control=decoded.get('global_fault_control'), context_fault_irq=decoded.get('context_fault_irq'), blocked_stream=decoded.get('blocked_stream'), bank_programming=decoded.get('bank_programming'), reset_observation=decoded.get('reset_observation'), late_ui=decoded['late_ui'], touch_input_delivery_proven=False, lockscreen_proven=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',
                        type=Path, required=True, dest='bundle')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--admission', type=Path)
    args = parser.parse_args()
    bundle = validate(args.bundle)
    if args.check_only:
        print('CPU touch host inputs verified; no USB or claim')
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

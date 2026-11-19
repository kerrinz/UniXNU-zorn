#!/usr/bin/env python3
"""Seal exact K80 physical-observer inputs for offline review."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import tomllib

import zorn_ios26_gpu_v312_system_trial as retained
from zorn_adb_endpoint import port_number


ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT / 'UniXNU-zorn'
PAGE = 4096
FAT_ROLES = {'BOOTAA64.EFI': 'manager', 'DarwinBoot26.efi': 'loader', 'kernel.macho': 'kernel',
             'kernel.macho.adt': 'ADT', 'unixnu.toml': 'menu'}
PHYSICAL_SCHEMAS = {316: 313, 317: 317, 318: 318, 319: 318, 320: 320, 321: 321, 322: 322,
                    325: 325, 326: 325, 327: 325, 328: 325, 329: 325, 330: 325, 331: 325, 332: 325, 333: 325, 334: 334, 335: 335, 336: 336, 337: 337, 338: 338, 339: 339, 340: 340, 341: 341, 342: 342, 343: 343, 344: 344, 345: 345, 346: 346, 347: 347, 348: 348, 349: 349, 350: 350, 351: 351, 352: 352, 353: 353, 354: 354, 355: 355, 356: 356, 357: 357, 358: 358, 359: 359, 360: 360, 361: 361, 362: 362, 363: 363, 364: 362, 365: 362, 366: 362, 367: 367, 368: 367}
HISTORICAL = (
    'primary_GPT', 'backup_GPT', 'root_manifest', 'Data_header', 'Data_metadata',
    'root_before', 'root_after', 'root_first_page',
    'root_install_review', 'root_install_receipt', 'root_install_admission', 'root_install_claim',
    'root_install_entry', 'root_install_runner', 'adb_binary', 'fastboot_binary',
    'host_adb_proof', 'camera_binary', 'zorn_ios26_logdirs_boot_trial.py',
    'zorn_gpu_resource_trial.py', 'zorn_recovery_identity.py', 'run-zorn-debug.py', 'build-zorn-debug.py',
    'record_decoder', 'record_helpers', 'record_envelope',
)
REVIEW_ONLY = dict(allow_boot=False, ready=False, current_recovery_verified=False,
                   scope_created=False, device_claim_created=False, phone_access=False)


def require(condition, error):
    if not condition:
        raise ValueError(error)


def load(path):
    record = json.loads(path.read_text())
    require(isinstance(record, dict), f'Expected JSON object: {path.name}')
    return record


def pin(path):
    path = Path(path)
    require(not path.is_symlink() and path.is_file(), f'Regular review file required: {path}')
    with path.open('rb') as stream:
        return dict(path=str(path.resolve()), bytes=path.stat().st_size,
                    sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


def checked(path, expected):
    row = pin(path)
    require(row['sha256'] == expected, f'Source/archive pin differs: {path}')
    return row


def source_record(row):
    return checked(row['path'], row['sha256'])


def storage_geometry(source, descriptor, root):
    part, data, log = descriptor['partition'], descriptor['Data'], descriptor['log']
    require(tuple(descriptor.get(key) for key in ('serial', 'product', 'slot')) == ('92988a43', 'zorn', 'a')
            and part['name'] == 'unixnu' and part['lba_bytes'] == PAGE and log['blocks'] == 1
            and descriptor['system']['runtime_readonly'] is True
            and descriptor['native_selection']['Android_userdata_fallback'] is False,
            'Unexpected protected storage identity')
    first, last = part['first_lba'], part['last_lba']
    capacity = (last - first + 1) * PAGE
    data_start = data['relative_first_lba'] * PAGE
    data_end = data_start + data['window_blocks'] * PAGE
    root_start = (data_end + (1 << 20) - 1) & ~((1 << 20) - 1)
    log_start = log['relative_lba'] * PAGE
    require(part['bytes'] == capacity and descriptor['system']['image_bytes'] <= log_start
            and log_start + PAGE < data_start and data_end < root_start
            and root_start + root['bytes'] <= capacity, 'Logical windows overlap or exceed partition')
    actual = {k: int(value) for k, value in re.findall(r'static constexpr uint64_t (\w+)=(\d+)ULL;', source)}
    require(actual == dict(AbsoluteByteStart=first * PAGE + root_start, Bytes=root['bytes'],
                           RelativeByteStart=root_start, PartitionBytes=capacity, DataStart=data_start,
                           DataEnd=data_end, LogStart=log_start), 'Effective native root window differs')
    require(','.join(hex(byte) for byte in bytes.fromhex(root['sha256'])) in source, 'Effective compiled root hash differs')
    return dict(serial=descriptor['serial'], product=descriptor['product'], slot='a',
                partition=part, protected_iPadOS17=descriptor['system'],
                Data=dict(relative_start=data_start, relative_end=data_end, read_only=True),
                root26=dict(relative_lba=root_start // PAGE, bytes=root['bytes'], read_only=True,
                            relative_end=root_start + root['bytes'], reserved_tail=capacity-root_start-root['bytes']),
                native_log=dict(absolute_lba=first+log['relative_lba'], blocks=1),
                Android_userdata_excluded=True, no_layout_change=True)


def retained_root(root, previous):
    row = pin(root['image'])
    require(row['bytes'] == root['bytes'] and row['sha256'] == root['sha256']
            and not (Path(root['image']).stat().st_mode & 0o222), 'Read-only offline root bytes differ')
    with Path(row['path']).open('rb') as stream:
        require(hashlib.sha256(stream.read(PAGE)).hexdigest() == previous['root_first_page']['sha256'],
                'Offline root first page differs from retained baseline')
    return row


def classify(state, host, camera, port, *, human_input_required=True):
    require(host['serial'] == '92988a43' and host['host_registry_only'] is True
            and host['recovery_identity_verified'] is False and camera['adb_or_fastboot_calls'] == 0,
            'Expected passive host evidence for 92988a43')
    reasons = []
    if state.get('stop_device_operations'):
        reasons.append('Persisted Recovery stop')
    if (any(state.get(key) for key in ('active_run', 'active_admission', 'active_build', 'runner_session'))
            or state.get('gpu_discovery', {}).get('active_admission')):
        reasons.append('Another run or admission is recorded')
    if (host.get('adb_server_port') != port or host['preboot_host_transport_admissible'] is not True
            or host.get('selected_executable_matches') is not True):
        reasons.append('Selected ADB endpoint lacks exclusive USB ownership or the reviewed executable')
    reasons.append('Current TWRP/OrangeFox identity, storage protection and BCB are unverified')
    if human_input_required:
        reasons.append('Actual FT3683 gestures require physical input for this candidate')
    return dict(REVIEW_ONLY, status='offline-only', current_stop=state.get('stop_device_operations') is True,
                current_stop_reason=state.get('stop_device_reason'), blockers=reasons, adb_server_port=port,
                USB=host, original_camera_success=camera['return_code'] == 0)


def checked_package(evidence):
    artifact = source_record(evidence['exact_package'])
    package_path = Path(artifact['path'])
    package = load(package_path)
    version = evidence['version']
    idle_budget = 16667 if version in (365, 366) else 8000
    require(type(version) is int and version in PHYSICAL_SCHEMAS and package['version'] == version
            and package['run_id'] == evidence['boot_tag']
            and package['boot']['sha256'] == evidence['boot']['sha256']
            and package['root'] == evidence['root'] and package['boot_args'] == evidence['boot_args']
            and package['physical_observer_wire_schema'] == PHYSICAL_SCHEMAS[version]
            and package['synthetic_input_enabled'] is (version == 342) and package['human_input_required'] is (version < 325)
            and package['root_installation_required'] is False and package['scope_or_claim_created'] is False
            and package['runtime_roots_read_only'] is True
            and (package['watchdog_seconds'], package['recovery_timeout_seconds'], package['retries']) == (300, 600, 0),
            'Unexpected physical observer packaging or watchdog configuration')
    if version == 366:
        require(package.get('early_scanout_cdc') is True, 'Unexpected early scanout CDC policy')
    if version in (364, 365, 366):
        require(package.get('ordinary_present_row_claims') is True, 'Unexpected ordinary row dispatch policy')
        version = 362  # Same display, FT3683 and recovery policy.
    if version in (363, 367, 368):
        require(package.get('touch_apps_smmu_roundtrip') is True and package.get('touch_DMA_submitted') is False,
                'Unexpected FT3683 SMMU round trip policy')
        version = 362
    if version in (343, 344, 345):
        require(package.get('passive_runtime_cadence') is True and package.get('status_ack_only') is True
                and type(package.get('display_command_count')) is int and package['display_command_count'] == 0
                and package.get('emits_ctl_start') is False, 'Unexpected fixed passive cadence policy')
    if version in (344, 345):
        require(package.get('requires_runtime_GPU_frame') is True
                and package.get('requires_qualified_GOP_epoch_to_sample') is False,
                'Hardware recording must not depend on individual GOP attribution')
    if version == 342:
        require(package.get('synthetic_ui_scene') == 'one-k80-swipe' and package.get('physical_sensor_borrowed') is False,
                'Unexpected fixed synthetic swipe policy')
    sources = dict(package=artifact, boot=source_record(package['boot']), FAT=source_record(package['FAT']))
    for name, role in (('FD', 'fd'), ('ADT', 'ADT'), ('kernel', 'kernel')):
        row = package['pins'][name]
        sources[role] = checked(row['archive'], row['sha256'])
    for member in package['FAT_members']:
        role = FAT_ROLES[Path(member['FAT_path']).name]
        row = checked(member['readback'], member['sha256'])
        if role in sources:
            require(sources[role]['sha256'] == row['sha256'], f'FAT binding differs: {role}')
        else:
            sources[role] = row
    require(len(package['FAT_members']) == len(FAT_ROLES)
            and set(FAT_ROLES.values()) <= sources.keys(), 'Incomplete FAT member evidence')
    if version == 345:
        require(package.get('second_scanout_CPU_alias_read_only') is True
                and package.get('second_scanout_memory_bytes_touched') is False
                and package.get('second_scanout_DMA_enabled') is False,
                'Unexpected second scanout access policy')
    if version in (346, 347, 356):
        require(package.get('second_scanout_DMA_enabled') is True
                and package.get('second_scanout_memory_bytes_touched') is True
                and package.get('second_scanout_CPU_alias_read_only') is False
                and package.get('bounded_display_command') is True
                and type(package.get('display_command_count')) is int and package['display_command_count'] == 2
                and package.get('emits_ctl_start') is False, 'Unexpected active second scanout policy')
    if version in (347, 356):
        require(package.get('bounded_display_period_comparison') is True
                and package.get('comparison_autorefresh_frames') == (2 if version == 356 else 4)
                and package.get('restored_autorefresh_frames') == 60,
                'Unexpected active cadence period policy')
    if version in (361, 362):
        abi = source_record(package['touch_geni_kernel_abi'])
        manifest = load(Path(abi['path']))
        require(manifest['passed'] is True and manifest['cpu_subtype'] == 0xc0000002,
                'GENI inventory object was not built for kernel arm64e')
        sources['touch_GENI_kernel_ABI'] = abi
        link_manifest = source_record(package['link']['exact_inputs'])
        link_inputs = json.loads(Path(link_manifest['path']).read_bytes())
        require(isinstance(link_inputs, list), 'Expected GENI kernel link input list')
        sources['touch_GENI_link_inputs'] = link_manifest
        for role in ('new_object', 'known_kernel_c'):
            obj = source_record(manifest[role])
            with Path(obj['path']).open('rb') as stream:
                cpu_header = struct.unpack('<III', stream.read(12))
            require(cpu_header == (0xfeedfacf, 0x0100000c, 0xc0000002)
                    and any(row['path'] == obj['path'] and row['sha256'] == obj['sha256'] for row in link_inputs),
                    'GENI kernel ABI or linked input differs')
            sources['touch_GENI_ABI_' + role] = obj
        sources['touch_GENI_ABI_recipe'] = source_record(manifest['recipe'])
    if version in (360, 361):
        require(package.get('touch_geni_inventory_only') is True, 'Unexpected FT3683 GENI policy')
    if version == 362:
        require(package.get('touch_static_gpii_guard') is True
                and package.get('touch_apps_smmu_probe') is True
                and package.get('touch_gpi_writes') is False,
                'Unexpected FT3683 GPI/SMMU policy')
    if version in (359, 360, 361, 362):
        require(type(package.get('present_queue_slots')) is int and package['present_queue_slots'] == 1
                and package.get('swap_timing_origin') == 'present-entry'
                and all(not arg.startswith('fb_queue=') for arg in package['boot_args'].split()),
                'Unexpected one-slot presentation policy')
    if version in (358, 359, 360, 361, 362):
        require(package.get('hardware_paced_live_scanout') is True, 'Unexpected hardware pacing policy')
    if version in (348, 349, 350, 351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
        require(package.get('second_scanout_DMA_enabled') is True
                and package.get('second_scanout_memory_bytes_touched') is True
                and package.get('second_scanout_CPU_alias_read_only') is False
                and package.get('bounded_display_command') is True
                and package.get('bounded_compositor_scanout') is True
                and package.get('live_scanout_window_us') == (500000 if version in (357, 358, 359, 360, 361, 362) else 1000000)
                and package.get('comparison_autorefresh_frames') == (2 if version in (357, 358, 359, 360, 361, 362) else 4)
                and package.get('restored_autorefresh_frames') == 60
                and type(package.get('display_command_count')) is int
                and package['display_command_count'] == 33
                and package.get('emits_ctl_start') is False, 'Unexpected live compositor policy')
    if version in (349, 350, 351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
        require(package.get('compositor_phase_trace') is True, 'Unexpected per-attempt compositor phase policy')
    if version in (350, 351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
        require(package.get('bounded_writer_reservation') is True, 'Unexpected bounded writer policy')
    if version in (351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
        require(type(package.get('second_scanout_cpu_cache_option')) is int
                and package['second_scanout_cpu_cache_option'] == 0x400, 'Unexpected write-combine mapping policy')
    if version in (352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
        require(package.get('topology_guard_trace') is True, 'Unexpected topology guard policy')
    if version in (353, 354, 355, 357, 358, 359, 360, 361, 362):
        require(type(package.get('bounded_prior_DSI_idle_wait_us')) is int
                and package['bounded_prior_DSI_idle_wait_us'] == idle_budget, 'Unexpected DSI idle wait policy')
    if version in (354, 355, 357, 358, 359, 360, 361, 362):
        require(type(package.get('sampled_compositor_RGB_grid_points')) is int
                and package['sampled_compositor_RGB_grid_points'] == 64, 'Unexpected RGB sampling policy')
    if version in (355, 357, 358, 359, 360, 361, 362):
        require(package.get('bounded_dynamic_scanout_row_claims') is True, 'Unexpected row claim policy')
    if version in (345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362):
        sources['loader_review'] = source_record(package['loader_review'])
        loader = load(Path(sources['loader_review']['path']))
        require(loader['passed'] is True and loader['loader']['sha256'] == sources['loader']['sha256'],
                'The independent EFI loader does not match the selected FAT member')
    menu = tomllib.loads(Path(sources['menu']['path']).read_text())
    require(len(menu['entry']) == 1 and menu['entry'][0]['args'] == package['boot_args']
            and not menu['boot']['connect_all'] and not menu['kits']['autoload'], 'Bounded boot menu differs')
    sources['firmware_closure'] = source_record(package['firmware_input_closure'])
    sources['native_platform_config'] = source_record(package['native_platform_config'])
    sources['effective_header_review'] = source_record(package['effective_header_review'])
    require(load(Path(sources['firmware_closure']['path']))['kernel_sha256'] == sources['kernel']['sha256']
            and load(Path(sources['native_platform_config']['path']))['CPU_page_bytes'] == 16384,
            'Firmware closure or 16 KiB CPU profile differs')
    sources['root_result'] = source_record(package['root_result'])
    sources['root_layout_check'] = source_record(package['root_layout_check'])
    require(load(Path(sources['root_result']['path']))['sha256'] == package['root']['sha256']
            and load(Path(sources['root_layout_check']['path']))['candidate_image']['sha256'] == package['root']['sha256'],
            'Local root result differs from the retained image')
    sources['record_identity'] = pin(package_path.parents[1] / 'artifact-identity.json')
    require(load(Path(sources['record_identity']['path'])) == package['artifact_identity'], 'Exact boot identity differs')
    return package, sources


def seal(output, report, sources):
    output.mkdir()
    archive = output / 'inputs'
    archive.mkdir()
    for role, source in sources.items():
        require(re.fullmatch(r'[A-Za-z0-9_.-]+', role) and '..' not in role, 'Invalid archive role')
        src = Path(source['path'])
        dest = archive / role
        subprocess.run(['/bin/cp', '-c', str(src), str(dest)], check=True)
        require(not src.samefile(dest), 'Independent review archive required')
        frozen = checked(dest, source['sha256'])
        require(frozen['bytes'] == source['bytes'], 'Archive byte count differs')
        source['archive'] = frozen['path']
    report['inputs'] = sources
    (output / 'offline-review.json').write_text(json.dumps(report, indent=2) + '\n')


def prepare(evidence_path, observation, output, adb_port=None):
    state = load(retained.CURRENT)
    evidence = load(evidence_path)
    host = load(observation / 'host-ownership.json')
    camera = load(observation / 'passive-observation.json')
    port = port_number(adb_port if adb_port is not None else host.get('adb_server_port'))
    package, sources = checked_package(evidence)
    report = classify(state, host, camera, port, human_input_required=package['human_input_required'])
    retained.validate_installation()
    old_bundle_path = retained.TRIAL / 'bundle.json'
    previous = load(old_bundle_path)['pins']
    for role in HISTORICAL:
        selected = previous[role]
        frozen = checked(selected['archive'], selected['sha256'])
        sources['retained-' + role] = (frozen if role in ('zorn_ios26_logdirs_boot_trial.py', 'zorn_gpu_resource_trial.py')
                                      else source_record(selected))
    require(load(Path(previous['root_install_receipt']['path']))['expected_image_sha256'] == package['root']['sha256'],
            'v307 receipt differs from physical observer root')
    root = retained_root(package['root'], previous)
    actual = load(Path(sources['effective_header_review']['path']))
    rows = [row for row in actual['header_checks'] if Path(row['resolved']).name == 'ZornRootWindow26.h']
    require(len(rows) == 1, 'Unique effective native root header required')
    row = rows[0]
    source = Path(row['resolved'])
    sources['native_root_window'] = checked(source, row['sha256'])
    descriptor = REPO / 'storage/unixnu64.json'
    other = ROOT / 'uefi-zorn/payload/storage/unixnu64.json'
    require(descriptor.read_bytes() == other.read_bytes(), 'UEFI and kernel protected layouts differ')
    geometry = storage_geometry(source.read_text(), load(descriptor), package['root'])
    sources.update(storage_descriptor=pin(descriptor), artifact_evidence=pin(evidence_path),
                   prior_trial_binding=pin(old_bundle_path), current_host_ownership=pin(observation/'host-ownership.json'),
                   external_camera_attempt=pin(observation/'passive-observation.json'),
                   camera_enumeration=pin(observation/'camera-enumeration.txt'),
                   analyzer=pin(REPO/'scripts/analyze-ios26-ft-capture.py'),
                   physical_wire_decoder=pin(REPO/'scripts/inspect_ios26_ft313.py'),
                   serial_transport=pin(REPO/'scripts/read-zorn-gpu-census268-cdc.py'),
                   ownership_guard=pin(REPO/'scripts/check-zorn-usb-adb-owner.py'),
                   endpoint_source=pin(REPO/'scripts/zorn_adb_endpoint.py'),
                   transport_endpoint_source=pin(REPO/'scripts/zorn_gpu_resource_trial.py'),
                   runner_endpoint_source=pin(REPO/'scripts/zorn_ios26_logdirs_boot_trial.py'))
    version = package['version']
    if version >= 318:
        sources['display_board_inputs'] = source_record(evidence['display_board_inputs'])
    if version >= 320:
        sources['panel_te_board_inputs'] = source_record(evidence['panel_te_board_inputs'])
    if version >= 321:
        sources['scanout_board_inputs'] = source_record(evidence['scanout_board_inputs'])
    if version >= 322:
        sources['display_power_board_inputs'] = source_record(evidence['display_power_board_inputs'])
    if 327 <= version < 332:
        require(package['deferred_owner_timeout_checkpoint'] is True, 'Deferred owner checkpoint missing')
        sources['deferred_owner_decoder'] = pin(REPO/'scripts/inspect_ios26_gpu_deferred327_record.py')
    if version in (332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368):
        require(package['cdc_before_gpu_board'] is True, 'Pre-GPU CDC gate missing')
        sources['deferred_owner_decoder'] = pin(REPO/'scripts/inspect_ios26_gpu_bootstrap332.py')
        sources['pre_gpu_cdc_decoder'] = pin(REPO/'scripts/inspect_ios26_gpu_early252.py')
    if version >= 328:
        require(package['early_console_stage_capture'] is True and camera['return_code'] == 0,
                'Early console observation requires a successful host camera preflight')
        sources['console_camera_preflight'] = source_record(camera['capture'])
    if version >= 329:
        require(package['enlarged_early_panic_text'] is True, 'Early panic text missing')
    if version >= 330:
        require(package['native_platform_watchdog_markers'] is True, 'Native platform watchdog markers missing')
    if version >= 331:
        require(package['gpu_board_after_native_root'] is True, 'GPU worker root prerequisite missing')
    for index, row in enumerate(evidence['host_checks']):
        item = source_record(row)
        require(load(Path(item['path']))['passed'] is True, 'Physical observer host check failed')
        sources[f'v{package["version"]}-host-check-{index+1}'] = item
    report.update(version=package['version'], boot_tag=package['run_id'], root=root, root_layout=geometry,
                  kernel_sha256=sources['kernel']['sha256'], boot_sha256=sources['boot']['sha256'],
                  host_artifacts_checked=True, historic_root_readback_verified=True,
                  watchdog_seconds=300, recovery_timeout_seconds=600, attempts_if_later_admitted=1,
                  retries=0, root_write_required=False, host_observation_utc=host['observed_at_utc'],
                  previous_camera_attempt_utc=camera['utc'],
                  capture=dict(cdc_schema=package['physical_observer_wire_schema'], screenshot_schema=297, screenshots_chunks=7,
                               native_log_blocks=1, raw_terminal_panic=True),
                  expected=['Verify fresh Recovery identity and protected storage before any future run',
                            'Observe firmware/GMU/HFI and real fence completion on the exact kernel',
                            'Bind the startup display resource lease to CDC, then verify return to Recovery'
                            if version >= 325
                            else 'Bind real physical touch and GPU presentation to CDC, then verify return to Recovery'],
                  stop_conditions=['Retain persistent device stop while Recovery is unverified',
                                   'No launch with competing ADB or with an unknown device or disk state',
                                   'No boot retry or device reset if execution, DMA or Recovery is uncertain'])
    seal(output, report, sources)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--host-observation', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--adb-port', type=int, help='select a reviewed loopback port, otherwise use the observed owner')
    args = parser.parse_args()
    report = prepare(args.evidence, args.host_observation, args.out, args.adb_port)
    print(json.dumps({key: report[key] for key in (
        'status', 'version', 'boot_tag', 'adb_server_port', 'allow_boot', 'blockers')}))


if __name__ == '__main__':
    main()

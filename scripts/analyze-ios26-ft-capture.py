#!/usr/bin/env python3
"""Analyze a saved K80 physical-input capture and its independent Recovery evidence."""

import argparse
import base64
import hashlib
import json
from pathlib import Path
import re

from inspect_ios26_ft313 import COST_TOTALS, SAMPLES, WIRE_LIMIT, inspect_progress
from inspect_ios26_gpu_early252_record import inspect_page
from inspect_ios26_gpu_deferred327_record import inspect_page as inspect_deferred_page
from inspect_ios26_gpu_bootstrap332 import inspect_page as inspect_bootstrap_page
from inspect_ios26_gpu_progress236 import save_panic
from inspect_ios26_scalar_timing287 import inspect as inspect_timing
from zorn_recovery_identity import inspect_recovery
from zorn_adb_endpoint import bundle_port, device_arguments


PAGE = 4096
SERIAL = '92988a43'
CONTROL = dict(serial=SERIAL, product='zorn', slot='a', watchdog_mode=1, trial_seconds=300,
               timeout_seconds=600, retries=0, root_read_only=True, data_read_only=True,
               transient_boot=True, bootstrap_allowed=False, existing_server_only=True,
               accepted_recovery='twrp-or-orangefox', native_log_absolute_lba=49563392, native_log_blocks=1)
GPT_AND_ROOT = (
    ('primary_GPT', '/dev/block/sda', 0, 6),
    ('backup_GPT', '/dev/block/sda', 64049147, 5),
    ('root_manifest', '/dev/block/by-name/unixnu', 0, 1),
)
READBACKS = (
    ('Data', 'Data_metadata', 65 * PAGE), ('Data_metadata', 'Data_metadata', 65 * PAGE),
    ('before', None, PAGE), ('after', None, PAGE),
    ('root_first_page', 'root_first_page', PAGE), ('root_before', 'root_before', PAGE),
    ('root_after', 'root_after', PAGE),
)
ARTIFACTS = {
    'BOOTAA64.EFI': 'manager', 'DarwinBoot26.efi': 'loader', 'kernel.macho': 'kernel',
    'kernel.macho.adt': 'ADT', 'unixnu.toml': 'menu',
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def same_fields(value, expected):
    return isinstance(value, dict) and all(type(value.get(key)) is type(item) and value[key] == item
                                           for key, item in expected.items())


def read(path, maximum):
    require(not path.is_symlink() and path.is_file(), f'Regular archived file required: {path.name}')
    with path.open('rb') as stream:
        data = stream.read(maximum + 1)
    require(len(data) <= maximum, f'Archived file exceeds its bound: {path.name}')
    return data


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_record(path):
    value = json.loads(read(path, 2 * 1024 * 1024))
    require(isinstance(value, dict), f'Object required in {path.name}')
    return value


def pinned(path, expected):
    require(path.is_absolute() and not path.is_symlink() and path.is_file(),
            f'Regular pinned file required: {path.name}')
    with path.open('rb') as stream:
        require(hashlib.file_digest(stream, 'sha256').hexdigest() == expected, f'Pin differs: {path.name}')


def load_bundle(bundle_path, package_path, package):
    bundle = json_record(bundle_path)
    require(same_fields(bundle, CONTROL), 'Archived runner scope differs from bounded K80 policy')
    version = package.get('version')
    if version == 366:
        require(bundle.get('early_scanout_cdc') is True, 'Archived early scanout CDC policy differs')
    idle_budget = 16667 if version in (365, 366) else 8000
    if version in (364, 365, 366):
        require(bundle.get('ordinary_present_row_claims') is True, 'Archived ordinary row dispatch policy differs')
        version = 362
    if version in (363, 367, 368):
        require(same_fields(bundle, dict(touch_apps_smmu_roundtrip=True, touch_DMA_submitted=False)),
                'Archived FT3683 SMMU round trip scope differs')
        version = 362
    if version in (343, 344, 345):
        require(same_fields(bundle, dict(passive_runtime_cadence=True, bounded_display_commands=0,
                                         status_ack_only=True, changes_scanout_address=False)),
                'Archived passive cadence scope differs')
    if version == 346:
        require(same_fields(bundle, dict(bounded_display_commands=2, changes_scanout_address=True,
                                        status_ack_only=False, native_root_writes=0)),
                'Archived second-buffer round trip scope differs')
    if version in (347, 356):
        require(same_fields(bundle, dict(bounded_display_commands=2, changes_scanout_address=True,
                                        bounded_display_period_comparison=True, status_ack_only=False,
                                        native_root_writes=0)),
                'Archived static comparison scope differs')
    if version == 356:
        require(same_fields(bundle, dict(comparison_autorefresh_frames=2, restored_autorefresh_frames=60)),
                'Archived 2-TE policy differs')
    if version in (348, 349, 350, 351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
        require(same_fields(bundle, dict(bounded_display_commands=33, changes_scanout_address=True,
                                         bounded_compositor_scanout=True,
                                         live_scanout_window_us=500000 if version in (357, 358, 359, 360, 361, 362) else 1000000,
                                         status_ack_only=False, native_root_writes=0)),
                'Archived live compositor scope differs')
    if version in (357, 358, 359, 360, 361, 362):
        require(same_fields(bundle, dict(comparison_autorefresh_frames=2, restored_autorefresh_frames=60)),
                'Archived live 2-TE policy differs')
    if version in (360, 361):
        require(same_fields(bundle, dict(touch_geni_inventory_only=True)),
                'Archived FT3683 GENI policy differs')
    if version == 362:
        require(same_fields(bundle, dict(touch_static_gpii_guard=True, touch_apps_smmu_probe=True,
                                         touch_gpi_writes=False)),
                'Archived FT3683 GPI/SMMU policy differs')
    if version in (359, 360, 361, 362):
        require(same_fields(bundle, dict(present_queue_slots=1, swap_timing_origin='present-entry')),
                'Archived one-slot presentation policy differs')
    if version in (358, 359, 360, 361, 362):
        require(same_fields(bundle, dict(hardware_paced_live_scanout=True)),
                'Archived hardware pacing policy differs')
    if version in (349, 350, 351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
        require(bundle.get('compositor_phase_trace') is True, 'Archived compositor phase policy differs')
    if version in (350, 351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
        require(bundle.get('bounded_writer_reservation') is True, 'Archived writer admission policy differs')
    if version in (351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
        require(same_fields(bundle, dict(second_scanout_cpu_cache_option=0x400)), 'Archived scanout cache policy differs')
    if version in (352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
        require(bundle.get('topology_guard_trace') is True, 'Archived topology guard policy differs')
    if version in (353, 354, 355, 357, 358, 359, 360, 361, 362):
        require(same_fields(bundle, dict(bounded_prior_DSI_idle_wait_us=idle_budget)), 'Archived DSI idle wait policy differs')
    if version in (354, 355, 357, 358, 359, 360, 361, 362):
        require(same_fields(bundle, dict(sampled_compositor_RGB_grid_points=64)), 'Archived RGB sampling policy differs')
    if version in (355, 357, 358, 359, 360, 361, 362):
        require(bundle.get('bounded_dynamic_scanout_row_claims') is True, 'Archived row claim policy differs')
    if version == 342:
        require(same_fields(bundle, dict(synthetic_ui_scene='one-k80-swipe', physical_sensor_borrowed=False)),
                'Archived synthetic scene scope differs')
    require(isinstance(bundle.get('scope'), str) and bundle['scope'].strip(), 'Missing exact scope')
    pins = bundle['pins']
    expected = {role: row['sha256'] for role, row in
                {'boot': package['boot'], 'FAT': package['FAT'], 'fd': package['pins']['FD']}.items()}
    members = package['FAT_members']
    named = {Path(row['FAT_path']).name: row['sha256'] for row in members}
    require(len(members) == len(ARTIFACTS) and set(named) == set(ARTIFACTS)
            and named['kernel.macho'] == package['pins']['kernel']['sha256']
            and named['kernel.macho.adt'] == package['pins']['ADT']['sha256'], 'Boot package member closure differs')
    expected.update({ARTIFACTS[name]: sha for name, sha in named.items()})
    expected['package'] = digest(read(package_path, 2 * 1024 * 1024))
    for role in (*expected, 'record_identity', 'root_install_receipt', 'adb_binary', 'fastboot_binary',
                 'primary_GPT', 'backup_GPT', 'root_manifest', 'Data_header', 'Data_metadata',
                 'root_first_page', 'root_before', 'root_after'):
        row = pins[role]
        source, archive = Path(row['path']), Path(row['archive'])
        require(row['sha256'] == expected.get(role, row['sha256']), f'Package pin differs: {role}')
        pinned(source, row['sha256'])
        pinned(archive, row['sha256'])
        require(not source.samefile(archive), f'Independent archived bytes required: {role}')
    require(json_record(Path(pins['record_identity']['archive'])) == package['artifact_identity'],
            'Run and package boot identity differ')
    install = json_record(Path(pins['root_install_receipt']['archive']))
    require(same_fields(install, dict(installed=True, expected_image_sha256=package['root']['sha256'],
                                      protected_metadata_and_fences_unchanged=True)),
            'Retained root installation receipt differs')
    root = Path(package['root']['image'])
    require(not root.is_symlink() and root.is_file() and root.stat().st_size == package['root']['bytes'],
            'Retained offline root image differs')
    with root.open('rb') as stream:
        require(digest(stream.read(PAGE)) == pins['root_first_page']['sha256'], 'Retained root first page differs')
    return bundle


def checked_bcb(archive, run):
    old, prepared, echoed = [read(archive / name, PAGE) for name in
                             ('misc-before.bin', 'recovery-bcb.bin', 'misc-readback.bin')]
    require(len(old) == len(prepared) == len(echoed) == PAGE, 'BCB archive page sizes differ')
    want = bytearray(old)
    want[:864] = bytes(864)
    want[:14] = b'boot-recovery\0'
    want[64:73] = b'recovery\n'
    require(prepared == echoed == want and same_fields(
        run.get('BCB'), dict(tail_preserved=True, full_page_readback=True,
                             before=digest(old), prepared=digest(echoed))), 'BCB and preserved tail differ')


def checked_recovery(archive, bundle, package, runner_exit):
    run = json_record(archive / 'run.json')
    claim = json_record(archive / 'one-shot.claim.json')
    scope, pins = bundle['scope'], bundle['pins']
    port = bundle_port(bundle)
    require(same_fields(claim, dict(scope=scope, status='consumed-no-repeat', before_first_USB=True,
                                   boot_sha256=package['boot']['sha256'])), 'Consumed claim differs')
    require(type(runner_exit) is int and runner_exit == 0 and same_fields(
        run, dict(scope=scope, boot_attempts=1, fastboot_returned_success=True)), 'Single runner completion differs')
    require(isinstance(run.get('status'), str) and run['status'].startswith('recovered-'),
            'Runner did not reach recovered state')
    for record in (claim, run):
        require('adb_server_port' not in record or same_fields(record, dict(adb_server_port=port)),
                'Archived ADB endpoint differs from the reviewed bundle')
    elapsed = run.get('recovery_observed_seconds')
    require(type(elapsed) in (int, float) and 0 < elapsed <= bundle['timeout_seconds'],
            'Missing or out-of-bound Recovery return time')
    identities = {}
    for phase in ('before', 'after'):
        recorded = run[f'recovery_identity_{phase}']
        identities[phase] = inspect_recovery(recorded['properties'])
        require(identities[phase]['family'] == recorded['family'], f'Recovery markers differ ({phase})')
    checked_bcb(archive, run)

    commands = {}
    for path in archive.glob('command-*.json'):
        match = re.fullmatch(r'command-(\d{3})\.json', path.name)
        require(match is not None, 'Archived command index differs')
        arguments = json_record(path)['arguments']
        require(isinstance(arguments, list) and all(isinstance(arg, str) for arg in arguments),
                'Malformed recorded command')
        commands[int(match[1])] = (path, arguments)
    boot_prefix = [pins['fastboot_binary']['path'], '-s', SERIAL, 'boot']
    boots = [index for index, (_, args) in commands.items() if args[:4] == boot_prefix]
    require(len(boots) == 1 and commands[boots[0]][1][4:] == [pins['boot']['path']],
            'Archived single fastboot command differs')
    adb = list(device_arguments(pins['adb_binary']['path'], port, SERIAL, 'exec-out'))
    for role, device, lba, count in GPT_AND_ROOT:
        args = adb + [f'dd if={device} bs={PAGE} skip={lba} count={count} 2>/dev/null']
        found = [(index, path) for index, (path, recorded) in commands.items() if recorded == args]
        require(any(index < boots[0] for index, _ in found) and any(index > boots[0] for index, _ in found),
                f'Archived reads around boot missing: {role}')
        for _, path in found:
            data = read(path.with_suffix('.stdout'), count * PAGE)
            require(len(data) == count * PAGE and digest(data) == pins[role]['sha256'],
                    f'Archived protected command output differs: {role}')
    for name, role, size in READBACKS:
        before, after = [read(archive / f'{phase}-{name}.bin', size) for phase in ('before', 'after')]
        require(len(before) == size and before == after, f'Protected pair differs: {name}')
        if role:
            require(digest(before) == pins[role]['sha256'], f'Protected baseline differs: {name}')
        if name == 'Data':
            require(digest(before[:PAGE]) == pins['Data_header']['sha256'], 'Data header differs')
    return dict(identities=identities, duration_seconds=elapsed, protected_pairs=len(READBACKS), adb_server_port=port,
                protected_GPT_and_root_manifest=True, BCB_before_boot_checked=True)


def physical_windows(samples):
    windows = []
    for old, new in zip(samples, samples[1:]):
        earlier, later = old['present'], new['present']
        start, end = earlier['uptime_ms'], later['uptime_ms']
        if end <= start:
            continue
        row = dict(start_uptime_ms=start, end_uptime_ms=end)
        a, b = old['physical'], new['physical']
        if a is not None and b is not None:
            keys = ('polls', 'read_successes', 'decoded', 'accepted', 'downs', 'moves', 'lifts',
                    'forced_releases', 'edge_downs', 'multi_contact_samples')
            row['physical_delta'] = {key: b[key] - a[key] for key in keys}
            row['physical_delta']['new_id_bitmap'] = b['seen_ids'] & ~a['seen_ids']
        if earlier['available'] & later['available'] & 1:
            keys = ('present_frame', 'producer_fence', 'completed_fence')
            deltas = {key: later[key] - earlier[key] for key in keys}
            if all(value >= 0 for value in deltas.values()):
                row['GPU_delta'] = deltas
        old_cost, new_cost = old.get('present_cost'), new.get('present_cost')
        if old_cost is not None and new_cost is not None:
            elapsed = new_cost['uptime_ms'] - old_cost['uptime_ms']
            faults = old_cost['faults'] | new_cost['faults']
            if elapsed > 0 and not faults & 3:
                delta = {key: new_cost[key] - old_cost[key] for key in COST_TOTALS}
                row['present_cost_delta'] = dict(delta, elapsed_ms=elapsed, faults=faults,
                    start_counter_uptime_ms=old_cost['uptime_ms'], end_counter_uptime_ms=new_cost['uptime_ms'],
                    copies_per_second=1000 * delta['copied_frames'] / elapsed)
        old_panel, new_panel = old.get('panel_timing'), new.get('panel_timing')
        if old_panel and new_panel and old_panel['status'] == new_panel['status'] == 7:
            elapsed = new_panel['uptime_ms'] - old_panel['uptime_ms']
            if elapsed > 0:
                row['panel_counter_delta'] = dict(elapsed_ms=elapsed, counts={
                    key: (new_panel[key] - old_panel[key]) & 0xffffffff
                    for key in ('interface_frame_count', 'mdp_frame_count')})
                if old_panel['tear_enable'] & new_panel['tear_enable'] & 1:
                    events = ((new_panel['tear_read_count'] >> 16) - (old_panel['tear_read_count'] >> 16)) & 0xffff
                    # Keep ambiguous resets separate from a small wrap in an
                    # actual display-sized window. Raw snapshots are retained.
                    if elapsed <= 20_000 and events <= elapsed * 240 // 1000 + 2:
                        row['panel_counter_delta']['tear_read_frames'] = events
        windows.append(row)
    return windows


def analyze(package_path, archive, output, *, bundle_path=None, runner_exit=None):
    package = json_record(package_path)
    version = package.get('version')
    early_scanout = version == 366
    if early_scanout:
        require(package.get('early_scanout_cdc') is True, 'Unexpected early scanout CDC package policy')
    idle_budget = 16667 if version in (365, 366) else 8000
    legacy = version in (313, 314, 315)
    schema = package.get('physical_observer_wire_schema', 313 if legacy else None)
    expected_schema = {313: 313, 314: 313, 315: 313, 316: 313, 317: 317, 318: 318, 319: 318, 320: 320, 321: 321,
                       322: 322, 325: 325, 326: 325, 327: 325, 328: 325, 329: 325, 330: 325, 331: 325,
                       332: 325, 333: 325, 334: 334, 335: 335, 336: 336, 337: 337, 338: 338, 339: 339, 340: 340, 341: 341, 342: 342, 343: 343, 344: 344, 345: 345, 346: 346, 347: 347, 348: 348, 349: 349, 350: 350, 351: 351, 352: 352, 353: 353, 354: 354, 355: 355, 356: 356, 357: 357, 358: 358, 359: 359, 360: 360, 361: 361, 362: 362, 363: 363, 364: 362, 365: 362, 366: 362, 367: 367, 368: 367}
    require(type(version) is int and version in expected_schema and type(schema) is int and schema == expected_schema[version]
            and same_fields(package, dict(
        synthetic_input_enabled=version == 342, probe_job_disabled=True, watchdog_seconds=300,
        human_input_required=version < 325, recovery_timeout_seconds=600, root_installation_required=False)),
        'Expected the physical observer package and separate admission')
    if version in (364, 365, 366):
        require(package.get('ordinary_present_row_claims') is True, 'Unexpected ordinary row dispatch policy')
        version = 362  # The packet schema and device recovery policy are inherited.
    if version in (363, 367, 368):
        require(same_fields(package, dict(touch_apps_smmu_roundtrip=True, touch_DMA_submitted=False)),
                'Unexpected FT3683 SMMU round trip package')
        version = 362
    if version in (343, 344, 345):
        require(same_fields(package, dict(passive_runtime_cadence=True, display_command_count=0,
                                          status_ack_only=True, emits_ctl_start=False)),
                'Unexpected passive cadence policy')
    if version in (346, 347, 356):
        require(same_fields(package, dict(second_scanout_DMA_enabled=True, display_command_count=2,
                                         bounded_display_command=True, emits_ctl_start=False,
                                         display_command_writes_new_buffer=True)),
                'Unexpected second scanout round trip package')
    if version in (347, 356):
        require(same_fields(package, dict(bounded_display_period_comparison=True,
                                         comparison_autorefresh_frames=2 if version == 356 else 4,
                                         restored_autorefresh_frames=60)),
                'Unexpected static comparison package')
    if version in (360, 361):
        require(package.get('touch_geni_inventory_only') is True, 'Unexpected FT3683 GENI policy')
    if version == 362:
        require(same_fields(package, dict(touch_static_gpii_guard=True, touch_apps_smmu_probe=True,
                                          touch_gpi_writes=False)),
                'Unexpected FT3683 GPI/SMMU policy')
    if version in (359, 360, 361, 362):
        require(same_fields(package, dict(present_queue_slots=1, swap_timing_origin='present-entry'))
                and all(not arg.startswith('fb_queue=') for arg in package['boot_args'].split()),
                'Unexpected one-slot presentation policy')
    if version in (358, 359, 360, 361, 362):
        require(package.get('hardware_paced_live_scanout') is True, 'Unexpected hardware pacing policy')
    if version in (348, 349, 350, 351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
        require(same_fields(package, dict(second_scanout_DMA_enabled=True, bounded_display_command=True,
                                         display_command_count=33, display_command_writes_new_buffer=True,
                                         emits_ctl_start=False, bounded_compositor_scanout=True,
                                         live_scanout_window_us=500000 if version in (357, 358, 359, 360, 361, 362) else 1000000,
                                         comparison_autorefresh_frames=2 if version in (357, 358, 359, 360, 361, 362) else 4,
                                         restored_autorefresh_frames=60)),
                'Unexpected live compositor scanout package')
    if version in (349, 350, 351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
        require(package.get('compositor_phase_trace') is True, 'Unexpected compositor phase package')
    if version in (350, 351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
        require(package.get('bounded_writer_reservation') is True, 'Unexpected bounded writer package')
    if version in (351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
        require(same_fields(package, dict(second_scanout_cpu_cache_option=0x400)), 'Unexpected scanout cache package')
    if version in (352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
        require(package.get('topology_guard_trace') is True, 'Unexpected topology guard package')
    if version in (353, 354, 355, 357, 358, 359, 360, 361, 362):
        require(same_fields(package, dict(bounded_prior_DSI_idle_wait_us=idle_budget)), 'Unexpected DSI idle wait package')
    if version in (354, 355, 357, 358, 359, 360, 361, 362):
        require(same_fields(package, dict(sampled_compositor_RGB_grid_points=64)), 'Unexpected RGB sampling package')
    if version in (355, 357, 358, 359, 360, 361, 362):
        require(package.get('bounded_dynamic_scanout_row_claims') is True, 'Unexpected row claim package')
    if version == 342:
        require(package.get('synthetic_ui_scene') == 'one-k80-swipe' and package.get('physical_sensor_borrowed') is False,
                'Unexpected synthetic swipe policy')
    identity = package['artifact_identity']
    tag, program = identity['run_id'], identity['application_probe_run_id']
    require(package['run_id'] == tag and all(re.fullmatch('[0-9a-f]{32}', item)
            for item in (tag, program, package['ordinary_timing_session'])), 'Package identity differs')
    require(not output.resolve().is_relative_to(archive.resolve()), 'Use an independent analysis directory')
    output.mkdir()
    report = dict(boot_tag=tag, physical_observer_wire_schema=schema,
                  package_sha256=digest(read(package_path, 2 * 1024 * 1024)),
                  boot_sha256=package['boot']['sha256'], device_access=False,
                  offline_archive_only=True, runner_exit=runner_exit, errors={},
                  serial_capture_complete=False, recovery_archive_verified=False,
                  fresh_native_page_verified=False, physical_FT3683_qualified=False,
                  terminal_panic_observed=False, physical_source_activity_observed=False,
                  physical_contacts_observed=False,
                  liquid_glass_qualified=False, GPU_desktop_qualified=False, full_GPU_qualification=False)
    errors = report['errors']
    try:
        raw = read(archive / 'cdc.raw', WIRE_LIMIT)
        report['CDC'] = dict(bytes=len(raw), sha256=digest(raw))
        serial, pixels = inspect_progress(raw, tag, program, schema, early_scanout=early_scanout)
        if schema in (363, 367) and serial['physical313']:
            report['touch_SMMU_round_trip'] = serial['physical313'][0].get('panel_timing', {}).get(
                'touch_SMMU_round_trip')
        schema = 362 if schema in (363, 367) else schema
        if serial['frame_count']:
            require(serial['checkpoint_precedes_gpu_board'] == (version in (332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362)),
                    'CDC checkpoint sequencing differs from the selected kernel')
            if version in (332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362):
                report['pre_gpu_CDC_frames'] = min(serial['frame_count'], 3)
        report['serial'] = serial
        report['windows'] = physical_windows(serial['physical313'])
        if schema in (325, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362):
            first = next(iter(serial['physical313']), {})
            report['display_register_resource_lease'] = first.get('panel_timing', {}).get(
                'display_register_resource_lease')
            if schema in (334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362):
                report['held_display_clock_state'] = first.get('panel_timing', {}).get('held_display_clock_state')
            if schema in (335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362):
                report['held_DPU'] = first.get('panel_timing', {}).get('held_DPU')
            if schema in (336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362):
                report['display_Apps_SMMU'] = (report['held_DPU'] or {}).get('display_Apps_SMMU')
            if schema in (339, 340, 341, 342):
                report['controlled_display_transfer'] = first.get('panel_timing', {}).get('controlled_display_transfer')
            if schema in (341, 342):
                report['runtime_display_frame'] = first.get('panel_timing', {}).get('runtime_display_frame')
            if schema == 342:
                report['runtime_display_scene'] = first.get('panel_timing', {}).get('runtime_display_scene')
            if schema in (343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362):
                report['runtime_DSI_cadence'] = first.get('panel_timing', {}).get('runtime_DSI_cadence')
            if schema >= 345:
                report['second_scanout_alias'] = first.get('panel_timing', {}).get('second_scanout_alias')
            if schema >= 346:
                report['second_scanout_flip'] = first.get('panel_timing', {}).get('second_scanout_flip')
            if schema in (347, 356):
                report['panel_period_comparison'] = first.get('panel_timing', {}).get('panel_period_comparison')
            if schema in (348, 349, 350, 351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
                report['live_scanout'] = first.get('panel_timing', {}).get('live_scanout')
        if schema in (360, 361) and serial['physical313']:
            report['touch_GENI_inventory'] = serial['physical313'][0].get('panel_timing', {}).get('touch_GENI_inventory')
        if schema == 362 and serial['physical313']:
            report['touch_GPI_routes'] = serial['physical313'][0].get('panel_timing', {}).get('touch_GPI_routes')
        if early_scanout:
            summary = serial['early_scanout_summary']
            report['early_scanout_summary'] = summary
            live = report.get('live_scanout')
            if summary and live:
                fields = ('result', 'retain', 'start_us', 'stop_us', 'attempts', 'completed', 'refused')
                inside = sum(live['start_us'] < f['completed_us'] <= live['stop_us'] for f in live['frames'])
                require(all(summary[key] == live[key] for key in fields)
                        and summary['completed_in_window'] == inside
                        and summary['prior_DSI_idle_wait'] == live['writer_gate']['prior_DSI_idle_wait'],
                        'Early and full scanout CDC records disagree')
        touch = [window['physical_delta'] for window in report['windows'] if 'physical_delta' in window]
        report['physical_source_activity_observed'] = any(window['accepted'] > 0 for window in touch)
        report['physical_contacts_observed'] = any(
            window['downs'] or window['moves'] or window['lifts'] for window in touch)
        terminal = serial['terminal236']
        report['terminal_panic_observed'] = terminal['packet_complete']
        report['serial_capture_complete'] = bool(
            serial['transport_frames_valid'] and serial['manual_observation_completed277']
            and serial['crop297']['complete'] and len(serial['physical313']) == SAMPLES
            and not terminal['partial_bytes'])
        if serial['crop297']['complete']:
            (output / 'screen-ft313.bgrx').write_bytes(pixels)
        # The decoder already checked that a complete terminal packet ends
        # the stream. Restrict export to that byte range even if a crop's
        # pixel data happens to contain the panic magic.
        report['panic_text_files'] = (save_panic(raw[-terminal['declared_bytes']:], tag, output)
                                      if terminal['packet_complete'] else [])
        journal = serial['journal248']
        stderr = base64.b64decode(journal['stderr_base64'], validate=True)
        require(digest(stderr) == journal['sha256'], 'Retained journal digest differs')
        (output / 'ordinary-stderr.bin').write_bytes(stderr)
        report['scalar_timing'] = inspect_timing(stderr, package['ordinary_timing_session'])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors['serial'] = str(exc)

    try:
        decode = (inspect_bootstrap_page if version in (332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362) else
                  inspect_deferred_page if version >= 327 else inspect_page)
        report['native_record'] = decode(read(archive / 'after-log.bin', PAGE), bytes.fromhex(tag),
                                         read(archive / 'before-log.bin', PAGE))
        report['fresh_native_page_verified'] = True
    except (OSError, ValueError, KeyError) as exc:
        errors['native_page'] = str(exc)
    if (report['fresh_native_page_verified'] and report['serial_capture_complete']
            and report['native_record']['deferred_CPU_owner_published'] is False):
        errors['serial'] = 'The deferred-owner timeout cannot start the CDC stream'

    if bundle_path is not None:
        try:
            bundle = load_bundle(bundle_path, package_path, package)
            report['recovery'] = checked_recovery(archive, bundle, package, runner_exit)
            report['recovery_archive_verified'] = True
            report['scope'] = bundle['scope']
            report['synthetic_fixture'] = bundle.get('synthetic_fixture') is True
            report['bundle_sha256'] = digest(read(bundle_path, 2 * 1024 * 1024))
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            errors['recovery'] = str(exc)
    else:
        errors['recovery'] = 'Archived runner bundle was not supplied'
    report['serial_and_recovery_bound'] = bool(not errors and report['serial_capture_complete'] and
                                               report['recovery_archive_verified'] and report['fresh_native_page_verified'])
    if schema in (339, 340, 341, 342):
        report['display_transfer_archive_bound'] = bool(
            not errors and report.get('controlled_display_transfer')
            and report['serial']['transport_frames_valid']
            and report['recovery_archive_verified'] and report['fresh_native_page_verified']
            and not report['terminal_panic_observed'])
    report['planned_observation_with_clean_recovery'] = bool(
        report['serial_and_recovery_bound'] and report['physical_source_activity_observed']
        and not report['terminal_panic_observed'])
    (output / 'analysis.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--runner-exit', type=int)
    args = parser.parse_args()
    result = analyze(args.package, args.capture, args.out, bundle_path=args.bundle, runner_exit=args.runner_exit)
    return 0 if result['planned_observation_with_clean_recovery'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

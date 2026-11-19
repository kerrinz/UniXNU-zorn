#!/usr/bin/env python3
"""Replay original Recovery readbacks and a synthetic physical observer archive."""

import argparse
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

from inspect_ios26_ft313 import COST_END, LAYOUTS, LIVE_TRACE_OFFSET, PANEL_END, PHASE_OFFSET, WRITER_GATE_OFFSET, split_physical
from inspect_ios26_gpu_progress236 import MAGIC as PANIC_MAGIC
from inspect_ios26_scroll309 import HEADER_BYTES, MENU_MAGIC, UI276_BYTES, UI_MAGIC
from zorn_adb_endpoint import bundle_port


def load_tool():
    path = Path(__file__).with_name('analyze-ios26-ft-capture.py')
    spec = importlib.util.spec_from_file_location('physical_archive', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save(path, item):
    path.write_text(json.dumps(item, indent=2) + '\n')


def replay_serial(raw, physical, old_tag, tag, schema):
    before, separator, tail = raw.partition(UI_MAGIC)
    assert separator and UI_MAGIC not in tail
    data = before + tail[UI276_BYTES - len(separator):]
    magic, packet_bytes = LAYOUTS[schema]
    assert len(physical) == packet_bytes and physical.startswith(magic)
    packet = bytearray(physical)
    packet[8:24] = bytes.fromhex(tag)
    struct.pack_into('<I', packet, len(packet) - 8, zlib.crc32(packet[:-8]))
    at = chunks = 0
    output = bytearray()
    while at < len(data):
        tail = data[at:]
        if tail.startswith(MENU_MAGIC):
            length = HEADER_BYTES + struct.unpack_from('<I', tail, 28)[0]
            assert tail[8:24] == bytes.fromhex(old_tag)
            part = bytearray(tail[:length])
            part[8:24] = bytes.fromhex(tag)
            struct.pack_into('<I', part, 64, zlib.crc32(part[:64]))
            chunks += 1
        else:
            length = tail.index(b'\r\n') + 2
            part = tail[:length].replace(old_tag.encode(), tag.encode())
        output += part
        at += length
    assert chunks == 7
    # This is explicitly test-only. Real CDC packets are always captured verbatim.
    return bytes(packet + output)


def panic_fixture(tag):
    reason = b'SYNTHETIC panic text'
    header = bytearray(128)
    header[:8] = PANIC_MAGIC
    header[24:40] = bytes.fromhex(tag)
    body = reason + (b'\0' if len(reason) % 2 == 0 else b'')
    total = len(header) + len(body) + 16
    struct.pack_into('<4I', header, 8, 236, len(header), total, 0)
    struct.pack_into('<13I', header, 40, 1, 0, len(reason), len(reason), 0, 0, 0, 0, 0, 2, 0, 0, 0)
    crc = zlib.crc32(header + body)
    struct.pack_into('<I', header, 20, crc)
    return bytes(header) + body + b'K80END26' + struct.pack('<2I', total, crc)


def build_fixture(tool, temporary, historic_capture, historic_bundle, package_path, package,
                  physical_capture, physical_packet, old_tag):
    archive = temporary / 'SYNTHETIC-trial'
    archive.mkdir()
    input_archive = temporary / 'SYNTHETIC-inputs'
    input_archive.mkdir()
    bundle = dict(historic_bundle, synthetic_fixture=True, scope='SYNTHETIC-FT-ARCHIVE-ONLY',
                  adb_server_port=5511)
    version = package['version']
    idle_budget = 16667 if version in (365, 366) else 8000
    if version == 366:
        bundle['early_scanout_cdc'] = True
    if version in (364, 365, 366):
        bundle['ordinary_present_row_claims'] = True
        version = 362
    if version in (363, 367, 368):
        bundle.update(touch_apps_smmu_roundtrip=True, touch_DMA_submitted=False)
        version = 362
    if version in (343, 344, 345):
        bundle.update(passive_runtime_cadence=True, bounded_display_commands=0,
                      status_ack_only=True, changes_scanout_address=False)
    if version == 346:
        bundle.update(bounded_display_commands=2, changes_scanout_address=True,
                      status_ack_only=False, native_root_writes=0)
    if version in (347, 356):
        bundle.update(bounded_display_commands=2, changes_scanout_address=True,
                      bounded_display_period_comparison=True, status_ack_only=False, native_root_writes=0)
    if version == 356:
        bundle.update(comparison_autorefresh_frames=2, restored_autorefresh_frames=60)
    if version in (348, 349, 350, 351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
        bundle.update(bounded_display_commands=33, changes_scanout_address=True,
                      bounded_compositor_scanout=True,
                      live_scanout_window_us=500000 if version in (357, 358, 359, 360, 361, 362) else 1000000,
                      status_ack_only=False, native_root_writes=0)
    if version in (357, 358, 359, 360, 361, 362):
        bundle.update(comparison_autorefresh_frames=2, restored_autorefresh_frames=60)
    if version in (360, 361):
        bundle['touch_geni_inventory_only'] = True
    if version == 362:
        bundle.update(touch_static_gpii_guard=True, touch_apps_smmu_probe=True, touch_gpi_writes=False)
    if version in (359, 360, 361, 362):
        bundle.update(present_queue_slots=1, swap_timing_origin='present-entry')
    if version in (358, 359, 360, 361, 362):
        bundle['hardware_paced_live_scanout'] = True
    if version in (349, 350, 351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
        bundle['compositor_phase_trace'] = True
    if version in (350, 351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
        bundle['bounded_writer_reservation'] = True
    if version in (351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
        bundle['second_scanout_cpu_cache_option'] = 0x400
    if version in (352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
        bundle['topology_guard_trace'] = True
    if version in (353, 354, 355, 357, 358, 359, 360, 361, 362):
        bundle['bounded_prior_DSI_idle_wait_us'] = idle_budget
    if version in (354, 355, 357, 358, 359, 360, 361, 362):
        bundle['sampled_compositor_RGB_grid_points'] = 64
    if version in (355, 357, 358, 359, 360, 361, 362):
        bundle['bounded_dynamic_scanout_row_claims'] = True
    if version == 342:
        bundle.update(synthetic_ui_scene='one-k80-swipe', physical_sensor_borrowed=False)
    pins = bundle['pins'] = historic_bundle['pins'].copy()
    replacements = {'package': package_path, 'boot': Path(package['boot']['path']),
                    'FAT': Path(package['FAT']['path']), 'fd': Path(package['pins']['FD']['archive']),
                    'record_identity': package_path.parents[1] / 'artifact-identity.json'}
    replacements.update({tool.ARTIFACTS[Path(row['FAT_path']).name]: Path(row['readback'])
                         for row in package['FAT_members']})
    for role, source in replacements.items():
        dest = input_archive / role
        subprocess.run(['/bin/cp', '-c', str(source), str(dest)], check=True)
        pins[role] = dict(path=str(source), archive=str(dest), sha256=tool.digest(source.read_bytes()))
    bundle_path = temporary / 'SYNTHETIC-bundle.json'
    save(bundle_path, bundle)
    run = tool.json_record(historic_capture / 'run.json')
    run.update(scope=bundle['scope'], synthetic_fixture=True, adb_server_port=bundle_port(bundle))
    save(archive / 'run.json', run)
    claim = tool.json_record(historic_capture / 'one-shot.claim.json')
    claim.update(scope=bundle['scope'], boot_sha256=package['boot']['sha256'], synthetic_fixture=True,
                 adb_server_port=bundle_port(bundle))
    save(archive / 'one-shot.claim.json', claim)

    for name in ('misc-before.bin', 'misc-readback.bin', 'recovery-bcb.bin', 'before-log.bin'):
        shutil.copyfile(historic_capture / name, archive / name)
    for name, _, _ in tool.READBACKS:
        for phase in ('before', 'after'):
            file = f'{phase}-{name}.bin'
            shutil.copyfile(historic_capture / file, archive / file)
    for path in sorted(historic_capture.glob('command-*.json')):
        command = tool.json_record(path)
        args = command['arguments']
        prefix = [pins['fastboot_binary']['path'], '-s', tool.SERIAL, 'boot']
        if args[:4] == prefix:
            command['arguments'] = prefix + [pins['boot']['path']]
            save(archive / path.name, command)
        elif len(args) > 8 and args[7] == 'exec-out' and any(
                args[8] == f'dd if={device} bs=4096 skip={lba} count={count} 2>/dev/null'
                for _, device, lba, count in tool.GPT_AND_ROOT):
            assert args[3:5] == ['-P', str(bundle_port(historic_bundle))]
            args[4] = str(bundle_port(bundle))
            save(archive / path.name, command)
            shutil.copyfile(path.with_suffix('.stdout'), archive / path.with_suffix('.stdout').name)

    tag = package['artifact_identity']['run_id']
    raw = replay_serial((physical_capture / 'cdc.raw').read_bytes(), physical_packet.read_bytes(), old_tag, tag,
                        package.get('physical_observer_wire_schema', 313))
    if version in (332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362):
        raw = re.sub(rb',ep=([0-9a-f]+)/',
                     lambda match: b',ep=%x/' % (int(match[1], 16) | 0x40), raw)
    screen = archive / 'cdc.raw'
    screen.write_bytes(raw)
    page = bytearray((historic_capture / 'after-log.bin').read_bytes())
    if version in (332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362):
        text = b'K80 GPU early332: root=1; cpu_online=8; gpu=pending'
        struct.pack_into('<I', page, 24, len(text))
        page[32:544] = text.ljust(512, b'\0')
    page[8:24] = bytes.fromhex(tag)
    page[28:32] = bytes(4)
    struct.pack_into('<I', page, 28, zlib.crc32(page[:544]))
    (archive / 'after-log.bin').write_bytes(page)
    return archive, bundle_path, raw


@contextmanager
def substitute(path, replacement):
    saved = path.read_bytes()
    if replacement is None:
        path.unlink()
    else:
        path.write_bytes(replacement)
    try:
        yield
    finally:
        path.write_bytes(saved)


def fails(call, expected):
    try:
        call()
    except ValueError as exc:
        assert expected in str(exc), exc
    else:
        raise AssertionError(f'Invalid record accepted: {expected}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True, help='physical-observer boot-package/verified.json')
    parser.add_argument('--known-recovery', type=Path, required=True, help='actual v305 root-trial directory')
    parser.add_argument('--stopped-trial', type=Path, required=True, help='actual v312 root-trial directory')
    parser.add_argument('--physical-packet', type=Path, required=True, help='explicitly synthetic host test packet')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    tool = load_tool()
    args.out.mkdir()
    historic_capture = args.known_recovery / 'trial'
    historic_bundle_path = args.known_recovery / 'bundle.json'
    historic_bundle = tool.json_record(historic_bundle_path)
    historic_package_path = Path(historic_bundle['pins']['package']['path'])
    historic_package = tool.json_record(historic_package_path)
    historic_bundle = tool.load_bundle(historic_bundle_path, historic_package_path, historic_package)
    historic_result = tool.checked_recovery(historic_capture, historic_bundle, historic_package, 0)
    assert historic_result['identities']['after']['family'] == 'TWRP' and historic_result['protected_pairs'] == 7

    stopped_capture = args.stopped_trial / 'trial'
    stopped = tool.json_record(args.stopped_trial / 'bundle.json')
    stopped_package = tool.json_record(Path(stopped['pins']['package']['path']))
    fails(lambda: tool.checked_recovery(stopped_capture, stopped, stopped_package, 1), 'Single runner completion differs')
    fails(lambda: tool.checked_recovery(stopped_capture, stopped, stopped_package, 0), 'did not reach recovered state')
    package_path = args.candidate
    package = tool.json_record(package_path)
    schema = package.get('physical_observer_wire_schema', 313)
    old_tag = stopped_package['artifact_identity']['run_id']
    exact = {'archived_v305_success_accepted': True, 'archived_v312_stop_refused': True}
    with tempfile.TemporaryDirectory(dir=args.out, prefix='SYNTHETIC-') as temp:
        temp = Path(temp)
        archive, bundle_path, raw = build_fixture(tool, temp, historic_capture, historic_bundle,
                                                  package_path, package, stopped_capture,
                                                  args.physical_packet, old_tag)
        report = tool.analyze(package_path, archive, temp / 'SYNTHETIC-positive',
                              bundle_path=bundle_path, runner_exit=0)
        assert report['serial_and_recovery_bound'] and report['planned_observation_with_clean_recovery'], report['errors']
        assert report['synthetic_fixture'] and report['physical_source_activity_observed']
        assert report['recovery']['adb_server_port'] == 5511
        assert len(report['windows']) == 8 and report['serial']['crop297']['packet_count'] == 7
        timing_windows = [row['present_cost_delta'] for row in report['windows'] if 'present_cost_delta' in row]
        if schema in (317, 318, 320, 321, 322, 325, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 356):
            assert len(timing_windows) == 6
            assert all(row['copies_per_second'] == 0.1 and row['show_us'] == 100
                       and row['start_counter_uptime_ms'] < row['end_counter_uptime_ms'] for row in timing_windows)
            fails(lambda: split_physical(raw, package['run_id'], 313), 'does not match package schema')
            exact['present_cost_uses_own_clock_and_gap_remains_unmeasured'] = True
        else:
            assert not timing_windows
        panel_windows = [row['panel_counter_delta'] for row in report['windows'] if 'panel_counter_delta' in row]
        if schema in (318, 320, 321, 322, 325, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362):
            assert len(panel_windows) == {342: 5, 348: 0, 349: 0, 350: 0, 351: 0, 352: 0, 353: 0, 354: 0, 355: 0, 357: 0, 358: 0, 359: 0, 360: 0, 361: 0, 362: 0}.get(schema, 6)
            assert all(row['elapsed_ms'] == 10000 and row['tear_read_frames'] == 600 for row in panel_windows)
            exact['panel_counter_wrap_and_gated_sample_gap'] = True
        else:
            assert not panel_windows
        if schema in (320, 321, 322, 325, 334, 335, 336, 337, 338):
            te = report['serial']['physical313'][-1]['panel_timing']['external_TE']
            assert 119.9 < te['steady_sample_hz'] < 120.2
            exact['external_TE_is_bound_to_exact_schema_and_identity'] = True
        if schema in (321, 322, 325, 334):
            early = report['serial']['physical313'][0]['panel_timing']['early_DPU_handoff']
            assert early['status'] == 7 and early['equal_numeric_GOP_addresses'] == ['0']
            exact['early_DPU_handoff_is_bound_to_exact_schema_and_identity'] = True
        if schema in (322, 325, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362):
            resources = report['serial']['physical313'][0]['panel_timing']['display_CommandDB']
            assert resources['all_resolved_distinct'] and len(resources['arc']['mmcx.lvl']['levels']) > 1
            exact['display_resources_are_bound_to_exact_schema_and_identity'] = True
        if schema in (325, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362):
            lease = report['display_register_resource_lease']
            assert lease['result'] == 'returned' and lease['acquire_steps'] == 127 and lease['release_steps'] == 253
            assert not any(lease['gcc_ahb_running'].values())
            exact['startup_lease_kept_separate_from_gcc_readiness'] = True
        if schema in (334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362):
            clock = report['held_display_clock_state']
            assert clock['result'] == 'sampled' and clock['gcc_ahb_before'] == 0x80000003
            assert not clock['gcc_ahb_running_before'] and not clock['gcc_ahb_running_after']
            exact['held_clock_snapshot_keeps_idle_interface_distinct'] = True
        if schema in (335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362):
            dpu = report['held_DPU']
            assert dpu['first_result'] == dpu['second_result'] == 'observed'
            assert dpu['raw_frame_deltas'] == {'intf': 14, 'mdp': 2, 'tear_read': 14}
            expected_pipes = ['0', '1'] if schema in (339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362) else ['0']
            assert dpu['route_status'] == 7 and dpu['equal_numeric_GOP_addresses'] == expected_pipes
            exact['leased_dpu_window_ctls_and_gop_bound'] = True
        if schema in (336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362):
            route = report['display_Apps_SMMU']
            assert route['result'] == 'observed' and route == dpu['display_Apps_SMMU']
            expected_mode = 'context_bypass' if schema in (339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362) else 'stage1_enabled'
            assert [(row['sid'], row['interpretation']) for row in route['streams']] == [
                (0x1c00, expected_mode), (0x1c02, expected_mode)]
            assert route['streams'][0]['slot'] == route['streams'][1]['slot']
            exact['stable_display_streams_are_separate_from_physical_frame_rate'] = True
        if schema in (339, 340, 341, 342):
            sequence = report['controlled_display_transfer']
            assert sequence['sequence'] == 1 and sequence['result'] == 'transfer_observed'
            kickoff_field = 'auto_kickoff_us' if schema in (340, 341, 342) else 'ctl_done_us'
            assert sequence[kickoff_field] <= sequence['dsi_done_us']
            assert report['display_transfer_archive_bound']
        if schema in (341, 342):
            frame = report['runtime_display_frame']
            assert frame['result'] == 'frame_claimed' and frame['producer_fence'] <= frame['surface_fence'] <= frame['retired_fence']
            assert frame['queued_us'] <= frame['copied_us'] <= frame['claimed_us']
            assert frame['submit_to_DSI_observation_max_us'] - frame['submit_to_DSI_observation_min_us'] == 999
            exact['runtime_surface_copy_and_DSI_are_bound'] = True
        if schema == 342:
            scene = report['runtime_display_scene']
            assert scene['result'] == 'gesture_complete' and scene['physical_touch'] is False
            assert scene['contact_returns'] == 17 and scene['lift_raw'] == 0
            assert not report['physical_contacts_observed']
            exact['synthetic_swipe_and_physical_FT3683_kept_independent'] = True
        if schema in (343, 344, 345, 346):
            cadence = report['runtime_DSI_cadence']
            assert cadence['result'] == 'completed' and cadence['interface_advances'] == cadence['fresh_dsi']
            assert cadence['changed_content'] and cadence['unknown_content']
            assert not report['serial']['synthetic_input_enabled']
            exact['passive_DSI_owned_epoch_and_original_scope_bound'] = True
        if schema in (345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362):
            alias = report['second_scanout_alias']
            assert alias['result'] == 'alias_verified' and alias['verified_CPU_pages'] == 1125
            assert alias['firmware'] == 'reserved' and alias['mapped_for_display_DMA'] is False
            exact['second_scanout_is_bound_to_firmware_and_CPU_only'] = True
        if schema in (346, 347, 356):
            flip = report['second_scanout_flip']
            assert flip['result'] == 'restored' and flip['pattern_samples'] == 3
            assert not flip['retain'] and flip['forward_DSI_us'] and flip['restore_DSI_us']
            exact['round_trip_kept_separate_from_CPU_mapping'] = True
        if schema in (347, 356):
            comparison = report['panel_period_comparison']
            assert comparison['result'] == 'compared'
            assert comparison['fresh_dsi'] == (90 if schema == 356 else 45)
            assert comparison['final_config'] == 0x8000003c and not comparison['retain']
            exact['static_cadence_distinct_from_unique_frames'] = True
            if schema == 356:
                packet = bytearray(raw)
                struct.pack_into('<I', packet, PANEL_END - 8 + 16 * 4, 0x80000004)
                boundary = LAYOUTS[schema][1] - 8
                struct.pack_into('<I', packet, boundary, zlib.crc32(packet[:boundary]))
                fails(lambda: split_physical(packet, package['run_id'], schema), 'static cadence observation')
                exact['static_2TE_requires_exact_readback'] = True
        if schema in (348, 349, 350, 351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
            live = report['live_scanout']
            assert live['result'] == 'restored' and live['completed'] == 3 and live['attempts'] == 4
            assert live['frames'][-1]['completed_us'] > live['stop_us']
            assert live['restore_DSI_us'] > 0 and not live['retain']
            assert not panel_windows
            for field, bad, message in ((1, 1, 'bounded compositor'), (5, 33, 'bounded compositor'),
                                        (17, 0, 'bounded compositor'), (18 + 1, 0, 'completion time'),
                                        (18 + 4 * 4, 1, 'Unused compositor-frame')):
                packet = bytearray(raw)
                struct.pack_into('<I', packet, LIVE_TRACE_OFFSET + field * 4, bad)
                boundary = LAYOUTS[schema][1] - 8
                struct.pack_into('<I', packet, boundary, zlib.crc32(packet[:boundary]))
                fails(lambda: split_physical(packet, package['run_id'], schema), message)
            exact['compositor_swap_wire_and_fixed_window_bound_with_tail'] = True
            if schema in (357, 358, 359, 360, 361, 362):
                packet = bytearray(raw)
                struct.pack_into('<I', packet, LIVE_TRACE_OFFSET + 4 * 4, live['start_us'] + 1_000_000)
                boundary = LAYOUTS[schema][1] - 8
                struct.pack_into('<I', packet, boundary, zlib.crc32(packet[:boundary]))
                fails(lambda: split_physical(packet, package['run_id'], schema), 'bounded compositor')
                exact['live_2TE_requires_exact_half_second_window'] = True
        if schema in (349, 350, 351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
            phases = report['live_scanout']['attempt_phases']
            assert len(phases) == 4 and sum(row['completed'] for row in phases) == 3
            assert phases[2]['preflight'] == ['auto_refresh_busy'] and not phases[2]['completed']
            assert phases[1]['durations_us']['CPU_copy_us'] == 3072
            for offset, word, message in (
                    (0, 0, 'does not match DSI frame'),
                    (2 * 16 + 12, (5 | 32) << 16, 'refusal guard differs'),
                    (4 * 16, 1, 'Unused compositor phase'),
                    (4, 0xffff, 'exceed recorded frame latency')):
                packet = bytearray(raw)
                struct.pack_into('<I', packet, PHASE_OFFSET + offset, word)
                boundary = LAYOUTS[schema][1] - 8
                struct.pack_into('<I', packet, boundary, zlib.crc32(packet[:boundary]))
                fails(lambda: split_physical(packet, package['run_id'], schema), message)
            exact['per_attempt_phases_bound_to_real_result_types'] = True
        if schema in (350, 351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
            gate = report['live_scanout']['writer_gate']
            assert gate['result'] == 'admitted' and gate['lock_attempts'] == 17
            assert gate['VIG0_source'] == gate['VIG1_source'] == 0xfc400000
            boundary = LAYOUTS[schema][1] - 8
            writer_cases = [(0, 4), (1, 251), (2, 250001), (3, 0), (5, 0xfd800000)]
            if schema not in (360, 361, 362):
                reserved = 7
                if schema in (353, 354, 355, 357, 358, 359):
                    reserved = 10 + int(schema != 353) + 3 * int(schema not in (353, 354))
                writer_cases.append((reserved, 1))
            for field, invalid in writer_cases:
                packet = bytearray(raw)
                struct.pack_into('<I', packet, WRITER_GATE_OFFSET + field * 4, invalid)
                struct.pack_into('<I', packet, boundary, zlib.crc32(packet[:boundary]))
                fails(lambda: split_physical(packet, package['run_id'], schema), 'writer admission')
            packet = bytearray(raw)
            packet[PHASE_OFFSET:WRITER_GATE_OFFSET] = bytes(WRITER_GATE_OFFSET - PHASE_OFFSET)
            packet[LIVE_TRACE_OFFSET:LIVE_TRACE_OFFSET + 146 * 4] = bytes(146 * 4)
            struct.pack_into('<3I', packet, LIVE_TRACE_OFFSET, 4, 0, 2)
            struct.pack_into('<6I', packet, WRITER_GATE_OFFSET, 4, 120, 250718, 0, 0, 0)
            if schema in (351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
                struct.pack_into('<I', packet, WRITER_GATE_OFFSET + 24, 0)
            struct.pack_into('<I', packet, boundary, zlib.crc32(packet[:boundary]))
            _, _, samples, partial = split_physical(packet, package['run_id'], schema)
            assert not partial and samples[2][0]['live_scanout']['writer_gate']['result'] == 'deadline'
            exact['writer_acquisition_and_timeout_checked'] = True
        if schema in (360, 361):
            inventory = report['touch_GENI_inventory']
            assert inventory['result'] == 'fifo_observed' and inventory['tx_fifo_depth'] == 32
            assert inventory['fifo_width_bits'] == 32
            inventory_start = WRITER_GATE_OFFSET + 14 * 4
            for field, invalid, reason in ((2, 0xffffffff, 'invalid controller value'),
                                           (4, 1, 'disagrees with the actual register words'),
                                           (10, 0x407, 'lacks the inherited clock votes')):
                packet = bytearray(raw)
                struct.pack_into('<I', packet, inventory_start + field * 4, invalid)
                struct.pack_into('<I', packet, boundary, zlib.crc32(packet[:boundary]))
                fails(lambda: split_physical(packet, package['run_id'], schema), reason)
            exact['touch_GENI_inventory_validated_against_raw_register_words'] = True
        if schema == 363:
            lease = report['touch_SMMU_round_trip']
            assert lease['result'] == 'released' and lease['post_sample_unmatched_fault'] is True
            assert lease['gpi_bank'] != lease['qup_bank'] and lease['fault_source'] is None
            exact['touch_smmu_round_trip_bound_to_serial_and_recovery_archive'] = True
        if schema == 367:
            lease = report['touch_SMMU_round_trip']
            assert lease['result'] == 'refused' and lease['gate'] == 'lock_busy'
            assert lease['attach_raw'] is None and lease['idr1'] is None
            exact['touch_smmu_pre_attach_gate_bound_to_serial_and_recovery_archive'] = True
        if schema == 362:
            inventory = report['touch_GPI_routes']
            assert inventory['static_GPII']['unallocated'] is True
            assert inventory['apps_smmu']['streams']['gpi']['route'] == 'stream_bypass'
            assert inventory['apps_smmu']['streams']['qup']['route'] == 'stage1_enabled'
            offset = COST_END - 8 - 44
            for field, invalid, reason in ((3, 13, 'publication state'),
                                           (5, 0x10003, 'stream encoding'),
                                           (9, 0x800000b6, 'matched SMMU entry')):
                packet = bytearray(raw)
                struct.pack_into('<I', packet, offset + field * 4, invalid)
                struct.pack_into('<I', packet, boundary, zlib.crc32(packet[:boundary]))
                fails(lambda: split_physical(packet, package['run_id'], schema), reason)
            exact['touch_GPII_guard_and_SMMU_route_wire_checked'] = True
        if schema in (351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
            assert gate['second_buffer_map_cache_option'] == 0x400
            for bad_cache in (0, 0x100, 0x1400):
                packet = bytearray(raw)
                struct.pack_into('<I', packet, WRITER_GATE_OFFSET + 24, bad_cache)
                struct.pack_into('<I', packet, boundary, zlib.crc32(packet[:boundary]))
                fails(lambda: split_physical(packet, package['run_id'], schema), 'mapping option differs')
            exact['explicit_WCOMB_alias_option_required_after_admission'] = True
        if schema in (352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
            for guard, expected in ((256, ['DSI_lane_state_mismatch']),
                                    (21, ['DPU_version_mismatch', 'CTL_route_mismatch', 'active_VIG_source_mismatch']),
                                    (0, [])):
                packet = bytearray(raw)
                struct.pack_into('<I', packet, PHASE_OFFSET + 2 * 16 + 12, (6 | 32 | (guard << 6)) << 16)
                struct.pack_into('<I', packet, boundary, zlib.crc32(packet[:boundary]))
                if not expected:
                    fails(lambda: split_physical(packet, package['run_id'], schema), 'refusal guard differs')
                    continue
                _, _, samples, partial = split_physical(packet, package['run_id'], schema)
                assert not partial and samples[2][0]['live_scanout']['attempt_phases'][2]['preflight'] == expected
            exact['topology_guard_requires_specific_failures'] = True
        if schema in (353, 354, 355, 357, 358, 359, 360, 361, 362):
            packet = bytearray(raw)
            count_offset = WRITER_GATE_OFFSET + 28
            phase_offset = PHASE_OFFSET + 2 * 16 + 12
            struct.pack_into('<I', packet, phase_offset, (13 | 32) << 16)
            for counts, accepted in (((1, 0, 1300), True), ((5, 0, 1300), False),
                                     ((1, 1, 1300), False), ((0, 0, 0), False)):
                struct.pack_into('<3I', packet, count_offset, *counts)
                struct.pack_into('<I', packet, boundary, zlib.crc32(packet[:boundary]))
                if not accepted:
                    fails(lambda: split_physical(packet, package['run_id'], schema), 'DSI idle wait counts differ')
                    continue
                _, _, samples, partial = split_physical(packet, package['run_id'], schema)
                live = samples[2][0]['live_scanout']
                assert not partial and live['attempt_phases'][2]['status'] == 13
                assert live['writer_gate']['prior_DSI_idle_wait']['max_elapsed_us'] == 1300
            exact['prior_DSI_read_only_wait_trace_checked'] = True
        if schema in (354, 355, 357, 358, 359, 360, 361, 362):
            packet = bytearray(raw)
            mask_offset = WRITER_GATE_OFFSET + 40
            struct.pack_into('<I', packet, mask_offset, 0b101)
            struct.pack_into('<I', packet, boundary, zlib.crc32(packet[:boundary]))
            _, _, samples, partial = split_physical(packet, package['run_id'], schema)
            live = samples[2][0]['live_scanout']
            assert not partial and live['sampled_RGB_grid_points'] == 64
            assert [frame['sampled_RGB_changed'] for frame in live['frames']] == [True, False, True]
            struct.pack_into('<I', packet, mask_offset, 0b1000)
            struct.pack_into('<I', packet, boundary, zlib.crc32(packet[:boundary]))
            fails(lambda: split_physical(packet, package['run_id'], schema), 'mask includes an unconfirmed swap')
            exact['RGB_changes_only_on_confirmed_frames'] = True
        if schema in (355, 357, 358, 359, 360, 361, 362):
            packet = bytearray(raw)
            row_offset = WRITER_GATE_OFFSET + 44
            for counts, accepted in (((3, 5, 123), True), ((1, 8, 123), False), ((0, 0, 1), False)):
                struct.pack_into('<3I', packet, row_offset, *counts)
                struct.pack_into('<I', packet, boundary, zlib.crc32(packet[:boundary]))
                if not accepted:
                    fails(lambda: split_physical(packet, package['run_id'], schema), 'row claim counters differ')
                    continue
                _, _, samples, partial = split_physical(packet, package['run_id'], schema)
                gate = samples[2][0]['live_scanout']['writer_gate']
                assert not partial and gate['dynamic_scanout_rows'] == dict(layers=3, helper_joins=5, max_join_us=123)
            exact['bounded_scanout_row_claim_trace_checked'] = True
        assert not report['physical_FT3683_qualified'] and not report['full_GPU_qualification']
        exact['mixed_observation_and_archive_bound'] = True
        tag = package['artifact_identity']['run_id']
        with substitute(archive / 'cdc.raw', raw + panic_fixture(tag)):
            report = tool.analyze(package_path, archive, temp / 'SYNTHETIC-panic',
                                  bundle_path=bundle_path, runner_exit=0)
            assert report['serial_and_recovery_bound'] and report['terminal_panic_observed'], report['errors']
            assert not report['planned_observation_with_clean_recovery']
            assert Path(report['panic_text_files'][0]).read_bytes() == b'SYNTHETIC panic text'
        exact['complete_panic_kept_separate_from_clean_return'] = True
        freshness = archive / 'after-log.bin'
        with substitute(freshness, (archive / 'before-log.bin').read_bytes()):
            report = tool.analyze(package_path, archive, temp / 'SYNTHETIC-stale-page',
                                  bundle_path=bundle_path, runner_exit=0)
            assert report['serial_capture_complete'] and report['recovery_archive_verified']
            assert not report['serial_and_recovery_bound'] and not report['fresh_native_page_verified']
        exact['stale_native_page_keeps_independent_evidence'] = True
        if 327 <= package['version'] < 332:
            text = b'K80 GPU early252: root=1; deferred=timeout; cpu_online=8; cpu_samples=pending'
            page = bytearray(struct.pack('<8s16sII512s', b'HJPAN026', bytes.fromhex(tag), len(text), 0, text))
            struct.pack_into('<I', page, 28, zlib.crc32(page))
            with substitute(freshness, page.ljust(tool.PAGE, b'\0')):
                report = tool.analyze(package_path, archive, temp / 'SYNTHETIC-inconsistent-stream',
                                      bundle_path=bundle_path, runner_exit=0)
                assert not report['serial_and_recovery_bound']
                assert report['errors']['serial'] == 'The deferred-owner timeout cannot start the CDC stream'
                with substitute(archive / 'cdc.raw', None):
                    report = tool.analyze(package_path, archive, temp / 'SYNTHETIC-timeout-page-only',
                                          bundle_path=bundle_path, runner_exit=0)
                    assert report['fresh_native_page_verified'] and report['recovery_archive_verified']
                    assert report['native_record']['deferred_CPU_owner_published'] is False
                    assert not report['serial_and_recovery_bound'] and not report['full_GPU_qualification']
            exact['timeout_record_survives_missing_stream_and_rejects_inconsistent_stream'] = True
        if package['version'] in (332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362):
            assert report['boot_tag'] == tag
            old_order = re.sub(rb',ep=([0-9a-f]+)/',
                               lambda match: b',ep=%x/' % (int(match[1], 16) & ~0x40), raw)
            with substitute(archive / 'cdc.raw', old_order):
                report = tool.analyze(package_path, archive, temp / 'SYNTHETIC-wrong-gpu-order',
                                      bundle_path=bundle_path, runner_exit=0)
                assert report['fresh_native_page_verified'] and not report['serial_and_recovery_bound']
                assert report['errors']['serial'] == 'CDC checkpoint sequencing differs from the selected kernel'
            exact['pre_gpu_record_bound_to_cdc_order'] = True
        with substitute(archive / 'cdc.raw', raw[:-1]):
            report = tool.analyze(package_path, archive, temp / 'SYNTHETIC-truncated-crop')
            assert not report['serial_capture_complete'] and report['fresh_native_page_verified']
        exact['truncated_screenshot_refused'] = True

        bundle = tool.json_record(bundle_path)
        wrong_port = dict(tool.json_record(archive / 'run.json'), adb_server_port=5512)
        with substitute(archive / 'run.json', json.dumps(wrong_port).encode()):
            fails(lambda: tool.checked_recovery(archive, bundle, package, 0), 'Archived ADB endpoint differs')
        exact['alternate_port_5511_and_mismatch_checked'] = True
        with substitute(archive / 'after-root_first_page.bin', bytes(tool.PAGE)):
            fails(lambda: tool.checked_recovery(archive, bundle, package, 0), 'Protected pair differs')
        with substitute(archive / 'misc-readback.bin', bytes(tool.PAGE)):
            fails(lambda: tool.checked_recovery(archive, bundle, package, 0), 'BCB and preserved tail differ')
        with substitute(archive / 'run.json', json.dumps(
                dict(tool.json_record(archive / 'run.json'), boot_attempts=True)).encode()):
            fails(lambda: tool.checked_recovery(archive, bundle, package, 0), 'Single runner completion differs')
        foreign = dict(tool.json_record(archive / 'run.json'))
        foreign['recovery_identity_after'] = dict(family='TWRP', properties={})
        with substitute(archive / 'run.json', json.dumps(foreign).encode()):
            fails(lambda: tool.checked_recovery(archive, bundle, package, 0), 'Recovery markers required')
        command = max(path for path in archive.glob('command-*.json') if 'skip=64049147' in path.read_text())
        with substitute(command.with_suffix('.stdout'), bytes(5 * tool.PAGE)):
            fails(lambda: tool.checked_recovery(archive, bundle, package, 0), 'Archived protected command output differs')
        boot = next(path for path in archive.glob('command-*.json')
                    if tool.json_record(path)['arguments'][3:4] == ['boot'])
        shutil.copyfile(boot, archive / 'command-999.json')
        try:
            fails(lambda: tool.checked_recovery(archive, bundle, package, 0), 'Archived single fastboot command differs')
        finally:
            (archive / 'command-999.json').unlink()
        with substitute(Path(bundle['pins']['ADT']['archive']), bytes(32)):
            fails(lambda: tool.load_bundle(bundle_path, package_path, package), 'Pin differs')
        fails(lambda: split_physical(raw, old_tag, schema), 'boot identity differs')
        fails(lambda: split_physical(raw + raw[:LAYOUTS[schema][1]], tag, schema), 'Repeated physical FT3683 packet')
        exact.update(unequal_protected_pair_refused=True, damaged_BCB_refused=True, bool_boot_count_refused=True,
                     fake_recovery_family_refused=True, damaged_GPT_readback_refused=True,
                     extra_boot_refused=True, changed_ADT_archive_refused=True, foreign_or_repeated_FT_tag_refused=True)

    inputs = (historic_bundle_path, historic_capture / 'run.json', args.stopped_trial / 'bundle.json',
              stopped_capture / 'run.json', stopped_capture / 'cdc.raw', args.physical_packet, package_path,
              Path(tool.__file__), Path(__file__))
    save(args.out / 'result.json', dict(passed=True, cases=exact, v305_actual_recovery=historic_result,
                                         exact_inputs={str(path): tool.digest(path.read_bytes()) for path in inputs},
                                         phone_access=False, no_new_hardware_qualification=True))
    print('PASS physical observer archive, original Recovery and fail-closed replay')


if __name__ == '__main__':
    main()

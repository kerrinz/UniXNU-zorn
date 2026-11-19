#!/usr/bin/env python3
"""Verify the complete display baseline and separately verify the latest Recovery."""

import argparse
import importlib.util
import json
from pathlib import Path

from inspect_ios26_gpu_bootstrap332 import inspect_page


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_analyzer():
    path = Path(__file__).with_name('analyze-ios26-ft-capture.py')
    spec = importlib.util.spec_from_file_location('physical_archive_analyzer', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify(evidence_path, expected_hash, current, *, baseline):
    tool = load_analyzer()
    tool.pinned(evidence_path, expected_hash)
    evidence = tool.json_record(evidence_path)

    def pinned(row):
        path = Path(row['path'])
        tool.pinned(path, row['sha256'])
        return path

    version = 364 if baseline else 365
    target = dict(serial='92988a43', product='zorn', slot='a')
    require(evidence['version'] == version and evidence['target'] == target
            and evidence['native_root_writes'] == evidence['retries'] == 0
            and evidence['boot_attempts'] == 1 and evidence['watchdog_seconds'] == 300
            and evidence['recovery_timeout_seconds'] == 600
            and evidence['root_payload_changed'] is False,
            'Predecessor target or execution policy differs')
    discovery = current['gpu_discovery']
    require(discovery['current_phone_root_expected_sha256'] == evidence['root_sha256'],
            'Installed root differs from the predecessor')

    run_path = pinned(evidence['recovery']['run'])
    archive = run_path.parent
    require(baseline or str(run_path) == discovery['latest_installed_root_boot_trial'],
            'Latest Recovery does not identify the exact v365 archive')
    require(pinned(evidence['claim']) == archive / 'one-shot.claim.json', 'Consumed claim path differs')
    package_path = pinned(evidence['exact_package'])
    package = tool.json_record(package_path)
    bundle_path = archive.parent / 'bundle.json'
    bundle = tool.load_bundle(bundle_path, package_path, package)
    run = tool.json_record(run_path)
    capture = evidence['capture']
    analysis_path = pinned(capture['analysis'])
    analysis = tool.json_record(analysis_path)
    require(analysis_path.parent.parent == archive.parent and pinned(capture['serial']) == archive / 'cdc.raw'
            and tool.same_fields(analysis, dict(boot_tag=evidence['boot_tag'], scope=evidence['scope'],
                boot_sha256=evidence['boot']['sha256'], package_sha256=evidence['exact_package']['sha256'],
                bundle_sha256=tool.digest(bundle_path.read_bytes()), runner_exit=0,
                recovery_archive_verified=True, fresh_native_page_verified=True, synthetic_fixture=False,
                serial_capture_complete=baseline, serial_and_recovery_bound=baseline,
                terminal_panic_observed=False, errors={})), 'Predecessor CDC or analysis identity differs')
    require(package['version'] == version and package['run_id'] == evidence['boot_tag']
            and package['root']['sha256'] == evidence['root_sha256'] and bundle['scope'] == evidence['scope']
            and run['status'] == 'recovered-fresh-root-EL0-before-GPU' and run['log_changed'] is True
            and pinned(capture['receiver']) == archive / 'serial-receipt.json', 'Predecessor artifact differs')
    receiver = tool.json_record(archive / 'serial-receipt.json')
    require(tool.same_fields(receiver, dict(boot_tag=evidence['boot_tag'], errors=[], receiver_ended=True,
                                           runner_exit=0)), 'Predecessor receiver did not stop cleanly')
    state = tool.checked_recovery(archive, bundle, package, receiver['runner_exit'])
    require(state == analysis['recovery'] and state['identities']['after']['family'] == 'TWRP'
            and state['protected_pairs'] == 7, 'Predecessor protected Recovery differs')
    native = inspect_page(tool.read(archive / 'after-log.bin', tool.PAGE), bytes.fromhex(evidence['boot_tag']),
                          tool.read(archive / 'before-log.bin', tool.PAGE))
    require(native == analysis['native_record'] and native['cpu_online'] == 8,
            'Predecessor native page differs')
    require(analysis['serial']['transport_frames_valid'] is True
            and analysis['serial']['kernel_known_task_complete266'] is True, 'Known task evidence differs')
    if baseline:
        require(analysis['live_scanout']['result'] == 'restored' and not analysis['live_scanout']['retain'],
                'The complete baseline lacks a restored display ownership record')
    else:
        require(evidence['capture_status'] == 'recovered-with-partial-CDC'
                and analysis.get('live_scanout') is None and analysis['serial']['frame_count'] == 30,
                'The latest archive differs from the exact v365 capture shortfall')
    return dict(version=version, run=str(run_path), boot_tag=evidence['boot_tag'],
                terminal_recovery_verified=True, full_CDC=baseline)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--current', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--baseline-sha', required=True)
    parser.add_argument('--latest', type=Path, required=True)
    parser.add_argument('--latest-sha', required=True)
    args = parser.parse_args()
    current = json.loads(args.current.read_text())
    print(json.dumps(dict(baseline=verify(args.baseline, args.baseline_sha, current, baseline=True),
                          latest=verify(args.latest, args.latest_sha, current, baseline=False))))


if __name__ == '__main__':
    main()

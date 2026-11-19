#!/usr/bin/env python3
"""Use the reviewed v318 carrier for one passive K80 panel timing trial."""

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import termios
from threading import Event, Thread
import time
from uuid import uuid4

from zorn_adb_endpoint import port_number
from zorn_ios26_gpu_v268_system_trial import record_result
from zorn_ios26_logdirs_boot_trial import CURRENT, PROTECTION_ROLES, STAGE, load, run, save, sha


SCRIPTS = Path(__file__).resolve().parent
TAG = '40e40ca097bf4cfa85552460cadb77b7'
BOOT = '408c8cb661e66b930e22fe16f373a57d08519f0f76bbf0bc72f46a3d934721e1'
ROOT_SHA = '951d3de636fb50a26886ac6b07e24db5bf3da6a0b58be2706542f28339fca301'
BUILD = STAGE / ('k80-gpu-v318-panel-timing-' + TAG)
REVIEW = BUILD / 'physical-review-with-archived-host/offline-review.json'
REVIEW_SHA = '7d04e615938912582060008225b1c544af07d39ada29e2c8ddc9f9bd099ceeb9'
HOST_TESTS = BUILD / 'panel-timing-archive-host/result.json'
PREVIOUS = SCRIPTS.parent / 'docs/evidence/k80-gpu-v309-settings-second-open-device-2026-11-18.json'
POLICY = dict(serial='92988a43', product='zorn', slot='a', trial_seconds=300, timeout_seconds=600,
              watchdog_mode=1, retries=0, root_read_only=True, data_read_only=True, transient_boot=True,
              bootstrap_allowed=False, existing_server_only=True, accepted_recovery='twrp-or-orangefox',
              native_log_absolute_lba=49563392, native_log_blocks=1, actual_contact_input_required=False,
              display_register_writes=False, native_root_writes=0, device_attempts=1)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pin(path):
    path = Path(path)
    require(path.is_file() and path.resolve() == path, f'Exact regular file required: {path}')
    return dict(path=str(path), sha256=sha(path))


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def checked_review():
    require(pin(REVIEW)['sha256'] == REVIEW_SHA, 'Exact independent v318 review changed')
    review = load(REVIEW)
    require(review['boot_tag'] == TAG and review['boot_sha256'] == BOOT and review['root']['sha256'] == ROOT_SHA
            and review['version'] == 318 and review['status'] == 'offline-only' and review['allow_boot'] is False
            and review['capture']['cdc_schema'] == 318, 'Unexpected v318 offline review')
    sources = review['inputs']
    for name, row in sources.items():
        source, archive = Path(row['path']), Path(row['archive'])
        require(archive == REVIEW.parent / 'inputs' / name and not source.samefile(archive)
                and pin(source)['sha256'] == pin(archive)['sha256'] == row['sha256'],
                f'Independent reviewed bytes differ: {name}')
    require(Path(sources['v318-host-check-3']['path']) == HOST_TESTS and load(HOST_TESTS)['passed'] is True,
            'Exact v318 archive regression required')
    current_tools = {'runner_endpoint_source': 'zorn_ios26_logdirs_boot_trial.py',
                     'transport_endpoint_source': 'zorn_gpu_resource_trial.py',
                     'endpoint_source': 'zorn_adb_endpoint.py', 'analyzer': 'analyze-ios26-ft-capture.py',
                     'physical_wire_decoder': 'inspect_ios26_ft313.py',
                     'ownership_guard': 'check-zorn-usb-adb-owner.py', 'serial_transport': 'read-zorn-gpu-census268-cdc.py',
                     'retained-zorn_recovery_identity.py': 'zorn_recovery_identity.py'}
    require(all(Path(sources[role]['path']) == SCRIPTS / name for role, name in current_tools.items()),
            'Reviewed tools differ from actual invocation')
    original = {'ADT', 'FAT', 'boot', 'fd', 'kernel', 'loader', 'manager', 'menu', 'package', 'record_identity'}
    retained = PROTECTION_ROLES | {'adb_binary', 'fastboot_binary', 'record_decoder', 'root_install_receipt'}
    pins = {role: sources[role] for role in original}
    pins.update({role: sources['retained-' + role] for role in retained})
    require(pins['boot']['sha256'] == BOOT and pins['kernel']['sha256'] == review['kernel_sha256'],
            'Reviewed boot or kernel differs')
    return pins


def checked_current():
    current = load(CURRENT)
    discovery = current['gpu_discovery']
    require(current['stop_device_operations'] is False and not discovery.get('active_admission')
            and not any(current.get(k) for k in ('active_run', 'active_admission', 'active_build', 'runner_session'))
            and discovery['current_mode'] == 'unattended-phone-connected', 'Current device scope is busy or stopped')
    require(discovery['current_phone_root_expected_sha256'] == ROOT_SHA, 'Expected installed root changed')
    previous = load(PREVIOUS)
    run_row = previous['run']
    require(run_row['path'] == discovery['latest_installed_root_boot_trial']
            and pin(run_row['path'])['sha256'] == run_row['sha256']
            and previous['root']['sha256'] == ROOT_SHA and previous['root_writes'] == 0
            and previous['recovery']['identities']['after']['family'] == 'TWRP'
            and previous['recovery']['protected_pairs'] == 7
            and previous['recovery']['protected_GPT_and_root_manifest'] is True,
            'Latest verified Recovery or retained root changed')
    return pin(CURRENT)


def owner_snapshot(pins, port=None):
    args = [sys.executable, '-B', SCRIPTS / 'check-zorn-usb-adb-owner.py', '--preboot',
            '--expected-adb', pins['adb_binary']['path']]
    if port is not None:
        args.extend(('--adb-port', str(port_number(port))))
    host = json.loads(subprocess.check_output(args, timeout=20))
    require(host['preboot_host_transport_admissible'] is True and host['selected_executable_matches'] is True
            and host['host_registry_only'] is True and host['serial'] == POLICY['serial'], 'ADB owner check failed')
    port_number(host['adb_server_port'])
    return host


def binding(out, bundle, current, host):
    require(bundle['scope'] == 'single-K80-ios26-v318-panel-timing-' + out.name[-12:], 'Independent trial scope differs')
    return dict(scope=bundle['scope'], boot_tag=TAG, boot_sha256=BOOT, root_sha256=ROOT_SHA,
                bundle=pin(out/'bundle.json'), sealed_inputs=pin(REVIEW), current=current, entry=pin(Path(__file__).resolve()),
                record_result=pin(SCRIPTS/'zorn_ios26_gpu_v268_system_trial.py'), host_ownership=pin(out/'host-before.json'),
                adb_server_port=port_number(host['adb_server_port']), host_tests=pin(HOST_TESTS))


def prepare(pins, port=None):
    current = checked_current()
    host = owner_snapshot(pins, port)
    out = BUILD / ('passive-panel-trial-' + uuid4().hex[:12])
    out.mkdir()
    bundle = POLICY | dict(scope='single-K80-ios26-v318-panel-timing-' + out.name[-12:],
                            adb_server_port=host['adb_server_port'], pins=pins)
    save(out/'host-before.json', host, True)
    save(out/'bundle.json', bundle, True)
    common = binding(out, bundle, current, host)
    save(out/'owner.json', common | dict(standing_target_authorization=True, allow_boot=True,
         basis='Active goal section 8, only 92988a43 and Android preservation; passive display phase'), True)
    save(out/'ready.json', common | dict(watchdog_seconds=300, recovery_timeout_seconds=600, retries=0,
         physical_contact_required=False, current_recovery_required_before_bcb=True,
         root_writes=0, synthetic_input_enabled=False), True)
    save(out/'admission.json', common | dict(allow_boot=True, owner=pin(out/'owner.json'), ready=pin(out/'ready.json')), True)
    return out


def validate(out, pins):
    require(out.resolve() == out and out.parent == BUILD and out.name.startswith('passive-panel-trial-')
            and not (out/'trial').exists() and not (out/'trial').is_symlink(), 'Fresh exact v318 trial required')
    bundle, host = load(out/'bundle.json'), load(out/'host-before.json')
    current = checked_current()
    require(all(type(bundle.get(key)) is type(value) and bundle[key] == value for key, value in POLICY.items())
            and bundle['pins'] == pins and bundle['adb_server_port'] == host['adb_server_port'], 'Bundle scope changed')
    owner, ready, admission = (load(out/name) for name in ('owner.json', 'ready.json', 'admission.json'))
    common = binding(out, bundle, current, host)
    for record in (owner, ready, admission):
        require(all(record.get(key) == value for key, value in common.items()), 'Exact owner/ready/admission changed')
    require(owner['allow_boot'] is True and owner['standing_target_authorization'] is True
            and admission['allow_boot'] is True and admission['owner'] == pin(out/'owner.json')
            and admission['ready'] == pin(out/'ready.json'), 'Current scoped admission required')
    require(ready['watchdog_seconds'] == 300 and ready['recovery_timeout_seconds'] == 600 and ready['retries'] == 0
            and ready['root_writes'] == 0 and ready['physical_contact_required'] is False
            and ready['current_recovery_required_before_bcb'] is True and ready['synthetic_input_enabled'] is False,
            'Unexpected passive Ready conditions')
    analyzer = load_tool('analyze-ios26-ft-capture')
    package_path = Path(pins['package']['path'])
    analyzer.load_bundle(out/'bundle.json', package_path, load(package_path))
    return bundle, host, analyzer, package_path


def execute(out, bundle, host, analyzer, package_path):
    port = bundle['adb_server_port']
    actual = owner_snapshot(bundle['pins'], port)
    require(actual['adb_server_port'] == port and actual['private_listener_pid'] == host['private_listener_pid'],
            'ADB interface ownership changed before claim')
    archive = out/'trial'
    archive.mkdir()
    save(out/'host-at-execution.json', actual, True)
    transport = load_tool('read-zorn-gpu-census268-cdc')
    stop, polling = Event(), Event()
    serial = dict(errors=[], boot_tag=TAG)

    def receive():
        deadline = time.monotonic() + 610
        identity = 'ZORN26' + TAG[:12].upper()
        try:
            while not stop.is_set() and time.monotonic() < deadline:
                registry = subprocess.check_output(['/usr/sbin/ioreg', '-r', '-n', transport.PRODUCT, '-l', '-w0'],
                                                   text=True, timeout=3)
                candidate = transport.find_port(registry, identity)
                polling.set()
                if candidate:
                    serial['port'] = candidate
                    transport.capture(candidate, archive/'cdc.raw', stop, deadline)
                    break
                stop.wait(0.25)
        except (OSError, ValueError, subprocess.SubprocessError, termios.error) as error:
            serial['errors'].append(repr(error))
        finally:
            polling.set()

    thread = Thread(target=receive, daemon=True)
    thread.start()
    code = 1
    try:
        require(polling.wait(5) and not serial['errors'], 'Serial monitor could not initialize')
        require(checked_current() == load(out/'ready.json')['current'], 'Current target state changed before claim')
        run(bundle, archive/'one-shot.claim.json', record_result=record_result)
        code = 0
    finally:
        stop.set()
        thread.join(5)
        serial.update(receiver_ended=not thread.is_alive(), runner_exit=code)
        save(archive/'serial-receipt.json', serial, True)
    report = analyzer.analyze(package_path, archive, out/'analysis', bundle_path=out/'bundle.json', runner_exit=code)
    print(json.dumps(dict(scope=bundle['scope'], capture_verified=report['serial_and_recovery_bound'],
                          panel_windows=sum('panel_counter_delta' in w for w in report.get('windows', ())),
                          recovery=report.get('recovery'), errors=report['errors'], serial_errors=serial['errors'])))
    return 0 if report['serial_and_recovery_bound'] and not serial['errors'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare', action='store_true')
    mode.add_argument('--check-only', type=Path, metavar='SCOPE_DIRECTORY')
    mode.add_argument('--start', type=Path, metavar='SCOPE_DIRECTORY')
    parser.add_argument('--adb-port', type=int, help='select a current local endpoint during preparation')
    args = parser.parse_args()
    pins = checked_review()
    if args.prepare:
        print(prepare(pins, args.adb_port))
        return 0
    require(args.adb_port is None, 'Prepared ADB port can only be changed before readiness')
    out = args.check_only or args.start
    validated = validate(out, pins)
    if args.check_only:
        print('v318 exact scope, archive, protected root and offline tool inputs checked')
        return 0
    return execute(out, *validated)


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run the macOS ADB ownership checks on frozen host evidence and fixtures."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    tool = Path(__file__).with_name('check-zorn-usb-adb-owner.py')
    spec = importlib.util.spec_from_file_location('zorn_usb_adb_owner', tool)
    owner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owner)
    registry_file = args.archive / 'K80-host-USB-owner.txt'
    listeners_file = args.archive / 'host-listeners.txt'
    registry = registry_file.read_text()
    # The archived lsof output uses its table representation.
    records = []
    for row in listeners_file.read_text().splitlines()[1:]:
        cells = row.split()
        assert cells[0] == 'adb' and cells[-1] == '(LISTEN)'
        records.extend(('p' + cells[1], 'n' + cells[-2]))
    archived = owner.inspect(registry, '\n'.join(records), adb_port=5039)
    assert archived['adb_interface_owner_pids'] == [91506]
    assert archived['default_listener_pid'] == 91506 and archived['private_listener_pid'] == 93135
    assert not archived['preboot_host_transport_admissible']

    private_registry = registry.replace('pid 91506, adb', 'pid 93135, adb')
    private = 'p93135\nn127.0.0.1:5039\n'
    checks = {
        'private_owner_only': (private_registry, private, True, True),
        'competing_default_listener_ipv4': (private_registry, private + 'p91506\nn127.0.0.1:5037\n', True, False),
        'competing_default_listener_ipv6': (private_registry, private + 'p91506\nn[::1]:5037\n', True, False),
        'competing_wildcard_listener': (private_registry, private + 'p91506\nn*:5039\n', True, False),
        'private_binding_not_loopback_ipv4': (private_registry, 'p93135\nn*:5039\n', False, False),
        'two_private_pids': (private_registry, private + 'p91506\nn127.0.0.1:5039\n', False, False),
        'missing_interface_client': (private_registry.replace('IOUserClientCreator', 'OtherProperty'), private, False, False),
    }
    for case, (state, network, exclusive, admitted) in checks.items():
        report = owner.inspect(state, network, adb_port=5039)
        assert report['private_has_exclusive_interface'] == exclusive, case
        assert report['preboot_host_transport_admissible'] == admitted, case
        assert report['host_registry_only'] and not report['recovery_identity_verified'], case
    alternate = 'p93135\ncadb\nn127.0.0.1:5511\n'
    assert owner.inspect(private_registry, alternate)['adb_server_port'] == 5511
    assert owner.inspect(private_registry, alternate, 5511)['preboot_host_transport_admissible']
    assert not owner.inspect(private_registry, alternate, 5512)['preboot_host_transport_admissible']
    competitor = alternate + 'p91506\ncadb\nn127.0.0.1:5512\n'
    assert not owner.inspect(private_registry, competitor, 5511)['preboot_host_transport_admissible']
    assert owner.inspect(private_registry, alternate + 'p42\ncnot-adb\nn127.0.0.1:22\n', 5511)['preboot_host_transport_admissible']
    for state in (registry.replace(owner.SERIAL, '00000000'), registry + '\n' + registry):
        try:
            owner.inspect(state, private)
        except ValueError:
            continue
        raise AssertionError('Wrong or duplicate USB identity accepted')

    pins = [dict(path=str(p.resolve()), sha256=hashlib.sha256(p.read_bytes()).hexdigest())
            for p in (tool, Path(__file__), registry_file, listeners_file)]
    report = dict(passed=True, stored_v312=archived, fixture_cases=list(checks),
                  configurable_port_autodiscovery_and_competition_checked=True,
                  wrong_or_repeated_usb_identity_rejected=True, pins=pins, phone_access=False)
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    print('PASS archived v312 dispute and synthetic preboot ownership cases')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Inspect the K80's macOS USB ADB interface without sending a device command."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

from zorn_adb_endpoint import LOOPBACK, port_number


SERIAL = '92988a43'
NODE = re.compile(r'^(.*?)\+-o (.+) +<class ([^,>]+)')
CREATOR = re.compile(r'"IOUserClientCreator" = "pid (\d+), adb"')


def interface_owners(registry):
    lines = registry.splitlines()
    nodes = [(index, match) for index, line in enumerate(lines) if (match := NODE.match(line))]
    root_serial = f'"USB Serial Number" = "{SERIAL}"'
    if not nodes or nodes[0][1][3] != 'IOUSBHostDevice':
        raise ValueError('USB device root missing from host registry')
    first_child = nodes[1][0] if len(nodes) > 1 else len(lines)
    if (sum(node[3] == 'IOUSBHostDevice' for _, node in nodes) != 1 or
            sum(root_serial in line for line in lines[nodes[0][0] + 1:first_child]) != 1):
        raise ValueError('Exact K80 serial absent or repeated in host registry')
    owners = set()
    in_interface_client = False
    for line in lines:
        node = NODE.match(line)
        if node:
            in_interface_client = node[3] == 'AppleUSBHostInterfaceUserClient' and node[2].strip() == 'adb'
        if in_interface_client:
            creator = CREATOR.search(line)
            if creator:
                owners.add(int(creator[1]))
    return owners


def listeners(records):
    endpoints = {}
    pid = None
    command = None
    for field in records.splitlines():
        if field.startswith('p'):
            pid = int(field[1:])
            command = None
        elif field.startswith('c'):
            command = field[1:]
        elif field.startswith('n'):
            if command not in (None, 'adb'):
                continue
            host, _, port = field[1:].rpartition(':')
            if pid is None or not host or not port.isdecimal():
                raise ValueError('Unexpected endpoint in filtered ADB listener sample')
            endpoints.setdefault((host, port_number(int(port))), set()).add(pid)
    return endpoints


def inspect(registry, lsof, adb_port=None):
    endpoints = listeners(lsof)
    owners = interface_owners(registry)
    if adb_port is None:
        matches = [port for (host, port), pids in endpoints.items()
                   if host == LOOPBACK and len(owners) == 1 and pids == owners]
        adb_port = matches[0] if len(matches) == 1 else None
    else:
        port_number(adb_port)
    private_pids = endpoints.get((LOOPBACK, adb_port), set())
    default_pids = endpoints.get((LOOPBACK, 5037), set())
    private = next(iter(private_pids)) if len(private_pids) == 1 else None
    default = next(iter(default_pids)) if len(default_pids) == 1 else None
    competing = set().union(*(pids for address, pids in endpoints.items()
                              if address != (LOOPBACK, adb_port)))
    exclusive = private is not None and owners == {private}
    return dict(serial=SERIAL, adb_interface_owner_pids=sorted(owners),
                adb_server_port=adb_port,
                default_listener_pid=default, private_listener_pid=private,
                private_has_exclusive_interface=exclusive,
                competing_listener_pids=sorted(competing),
                preboot_host_transport_admissible=exclusive and not competing,
                host_registry_only=True, recovery_identity_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb-port', type=int,
                        help='check this loopback port or discover the unique listener owned by the K80 USB owner')
    parser.add_argument('--expected-adb', type=Path,
                        help='require the selected listener to run these exact executable bytes')
    parser.add_argument('--preboot', action='store_true',
                        help='require exclusive interface ownership and no competing ADB listener')
    args = parser.parse_args()
    registry = subprocess.check_output(
        ['/usr/sbin/ioreg', '-p', 'IOService', '-r', '-n', 'Redmi K80', '-l', '-w0'],
        text=True, timeout=5,
    )
    ports = subprocess.run(
        ['/usr/sbin/lsof', '-nP', '-a', '-c', 'adb', '-iTCP', '-sTCP:LISTEN', '-Fpcn'],
        capture_output=True, text=True, timeout=5, check=False,
    )
    if ports.returncode not in (0, 1) or ports.stderr:
        ports.check_returncode()
        raise RuntimeError(ports.stderr)
    report = inspect(registry, ports.stdout, args.adb_port)
    report['observed_at_utc'] = datetime.now(timezone.utc).isoformat()
    if args.expected_adb:
        pid = report['private_listener_pid']
        expected = args.expected_adb.resolve()
        selected = False
        if pid:
            result = subprocess.run(['/usr/sbin/lsof', '-nP', '-a', '-p', str(pid), '-d', 'txt', '-Fpn'],
                                    capture_output=True, text=True, timeout=5, check=False)
            names = [Path(line[1:]) for line in result.stdout.splitlines()
                     if line.startswith('n') and Path(line[1:]).name == 'adb']
            if result.returncode == 0 and len(names) == 1:
                with names[0].open('rb') as actual, expected.open('rb') as pinned:
                    selected = hashlib.file_digest(actual, 'sha256').digest() == hashlib.file_digest(pinned, 'sha256').digest()
        report['selected_executable_matches'] = selected
        report['preboot_host_transport_admissible'] &= selected
    print(json.dumps(report, indent=2))
    field = 'preboot_host_transport_admissible' if args.preboot else 'private_has_exclusive_interface'
    return 0 if report[field] and report.get('selected_executable_matches', True) else 1


if __name__ == '__main__':
    raise SystemExit(main())

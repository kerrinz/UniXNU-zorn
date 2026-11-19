#!/usr/bin/env python3
"""Exercise the shared runner's endpoint and stopped-state checks with no phone I/O."""

import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

import zorn_ios26_logdirs_boot_trial as runner
import zorn_gpu_resource_trial as transport
from zorn_adb_endpoint import LEGACY_ARCHIVE_PORT, bundle_port, port_number


class FixtureStop(Exception):
    pass


def run_case(folder, selected):
    folder.mkdir()
    current = folder / 'state.json'
    current.write_text('{"gpu_discovery": {}}\n')
    claim = folder / 'claim.SYNTHETIC.json'
    scope = 'SYNTHETIC-adb-endpoint'
    binary = str(folder / 'SYNTHETIC-adb')
    bundle = dict(scope=scope, accepted_recovery='twrp-or-orangefox', timeout_seconds=600,
                  pins=dict(adb_binary=dict(path=binary), fastboot_binary=dict(path='SYNTHETIC-fastboot'),
                            boot=dict(sha256='0' * 64)))
    if selected is not None:
        bundle['adb_server_port'] = selected
    port = LEGACY_ARCHIVE_PORT if selected is None else selected
    expected = [binary, '-H', '127.0.0.1', '-P', str(port), '-s', '92988a43']
    probes, argv = [], []

    def socket_probe(address, timeout):
        assert address == ('127.0.0.1', port) and timeout == 0.2
        probes.append(address)
        return io.BytesIO()

    def fake_command(args, **kwargs):
        assert args[:len(expected)] == expected, args
        assert kwargs['env']['ADB_LIBUSB'] == '0'
        argv.append(args)
        tail = args[len(expected):]
        if tail == ['server-status']:
            reply = f'usb_backend: NATIVE\nbinary_path: {binary}\n'.encode()
        else:
            assert tail[:2] == ['shell', 'getprop']
            reply = {'ro.twrp.boot': b'1\n', 'ro.twrp.version': b'SYNTHETIC-ONLY\n',
                     'ro.orangefox.boot': b'\n'}[tail[2]]
        return subprocess.CompletedProcess(args, 0, reply, b'')

    def synthetic_recovery(capture, pins, recovery_config):
        assert recovery_config == 'twrp-or-orangefox' and pins == bundle['pins']
        assert capture.probe_recovery()['family'] == 'TWRP'
        raise FixtureStop('end of test before any real action')

    with patch.object(runner, 'CURRENT', current), patch.object(runner.socket, 'create_connection', socket_probe), \
            patch.object(runner.subprocess, 'run', fake_command), \
            patch.object(runner, 'protected_recovery', synthetic_recovery), redirect_stdout(io.StringIO()):
        try:
            runner.run(bundle, claim)
        except FixtureStop:
            pass
        else:
            raise AssertionError('Synthetic runner did not stop')
        assert probes == [('127.0.0.1', port)] and len(argv) == 4
        assert json.loads(claim.read_text())['adb_server_port'] == port
        assert json.loads((folder / 'run.json').read_text())['adb_server_port'] == port
        assert json.loads(current.read_text())['stop_device_operations'] is True
        try:
            runner.run(bundle, folder / 'second-claim.SYNTHETIC.json')
        except ValueError as exc:
            assert 'no claim or USB' in str(exc)
        else:
            raise AssertionError('Recorded device stop allowed another run')
        assert not (folder / 'second-claim.SYNTHETIC.json').exists() and len(argv) == 4
    return dict(port=port, actual_runner_commands_checked=len(argv), legacy_archive=selected is None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir()
    for value in (True, False, 0, -1, 65536, '5039', 5511.0, None):
        try:
            port_number(value)
        except ValueError:
            pass
        else:
            raise AssertionError(f'Invalid port accepted: {value!r}')
    assert bundle_port({}) == LEGACY_ARCHIVE_PORT
    assert bundle_port({'adb_server_port': 5037}) == 5037
    with tempfile.TemporaryDirectory(dir=args.out, prefix='SYNTHETIC-') as temporary:
        rows = [run_case(Path(temporary) / str(port), port) for port in (None, 5037, 5511)]
    paths = [Path(__file__), Path(runner.__file__), Path(transport.__file__),
             Path(__file__).with_name('zorn_adb_endpoint.py')]
    (args.out / 'result.json').write_text(json.dumps(dict(
        passed=True, cases=rows, invalid_port_cases=8, device_operations=False,
        exact_sources={str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}),
        indent=2) + '\n')
    print('PASS runtime and Recovery use the reviewed port, with legacy and stopped-state controls')


if __name__ == '__main__':
    main()

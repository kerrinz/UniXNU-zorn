#!/usr/bin/env python3
"""Execute the actual282 receiver through final JSON; device boundaries mocked."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import zorn_ios26_known282_receiver as receiver


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    wire = (args.fixtures / 'SYNTHETIC-retagged268-wire.bin').read_bytes()
    page = (args.fixtures / 'SYNTHETIC-retagged268-page.bin').read_bytes()
    tag = 'b631a4ee28874ebfaa9c4bfdcf2fc3c4'
    program = 'ddb9c8640ab544cd85cae684e0fb8f66'
    checks = []
    class HostThread:
        def __init__(self, target):
            self.target = target
        def start(self):
            self.target()
        def join(self):
            pass
    registry = ('"idVendor" = 4617\n"idProduct" = 1\n'
                '"USB Serial Number" = "ZORN26' + tag[:12].upper() + '"\n'
                '"IOCalloutDevice" = "/dev/cu.usbmodemHOST282"\n')
    assert receiver.find_port(registry, 'ZORN26' + tag[:12].upper())
    assert receiver.find_port(registry, 'ZORN26FOREIGN') is None
    assert receiver.find_port(registry + '"IOCalloutDevice" = "/dev/cu.usbmodemOTHER"\n', 'ZORN26' + tag[:12].upper()) is None
    checks.append('retained real268 port matcher refuses foreign identity/ambiguous ports')
    for case in ['success', 'runner failure', 'runner launch error', 'registry failure',
                 'existing claim', 'bundle rejected']:
        with tempfile.TemporaryDirectory() as temp:
            trial = Path(temp) / 'root-trial'
            out = trial / 'trial'
            out.mkdir(parents=True)
            (out / 'before-log.bin').write_bytes(bytes(4096))
            (out / 'after-log.bin').write_bytes(page)
            if case == 'existing claim':
                (out / 'one-shot.claim.json').write_text('HOST ONLY')
            calls = []
            def validate(path):
                assert path == trial / 'bundle.json'
                calls.append('validate')
                if case == 'bundle rejected':
                    raise ValueError('HOST: uninstalled root/current bundle invalid')
            def capture(port, path, stop, deadline):
                assert port == '/dev/cu.usbmodemHOST282' and path == out / 'cdc.raw'
                calls.append('capture')
                path.write_bytes(wire)
            def run(arguments, **kwargs):
                if arguments[0] == '/usr/sbin/ioreg':
                    assert calls == ['validate']
                    calls.append('registry')
                    return SimpleNamespace(returncode=int(case == 'registry failure'), stdout=registry)
                assert calls == ['validate', 'registry', 'capture']
                assert arguments[2] == str(Path(receiver.__file__).with_name('run-zorn-debug.py'))
                assert arguments[3:] == ['--ios26-known282-trial', '--bundle', str(trial / 'bundle.json'), '--admission', str(trial / 'admission.json')]
                calls.append('runner')
                if case == 'runner launch error':
                    raise OSError('HOST: runner launch failed')
                (out / 'run.json').write_text(json.dumps(dict(
                    scope='HOST-known282', boot_attempts=1, fastboot_returned_success=True,
                    recovery_identity_after=dict(family='TWRP'))))
                return SimpleNamespace(returncode=int(case == 'runner failure'))
            config = SimpleNamespace(TRIAL=trial, TAG=tag, PROBE_TAG=program,
                                     SCOPE='HOST-known282', validate=validate)
            with patch.object(receiver, 'Thread', HostThread), patch.object(receiver, 'capture', capture), patch.object(receiver.subprocess, 'run', run):
                if case in ['existing claim', 'bundle rejected']:
                    try:
                        receiver.run_capture(config)
                    except ValueError:
                        assert calls == ['validate']
                    else:
                        raise AssertionError(case)
                    assert not (out / 'cdc-capture.json').exists()
                else:
                    code = receiver.run_capture(config)
                    report = json.loads((out / 'cdc-capture.json').read_text())
                    assert (code == 0) == (case == 'success')
                    assert report['bounded_Metal_and_client_lifecycle_complete282'] == (case == 'success')
                    assert not report['full_GPU_qualification']
                    if case == 'registry failure':
                        assert calls == ['validate', 'registry']
                    if case == 'runner launch error':
                        assert report['frame_count'] == 31 and report['raw_wire_readable']
                        assert (out / 'screen265.bgrx').is_file()
                        assert (out / 'ordinary282-stderr.bin').is_file()
            checks.append(case + ': actual receiver, exclusive final JSON and listener-first boundary checked')
    def pin(path):
        path = Path(path).resolve()
        return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    result = dict(passed=True, checks=checks, receiver=pin(receiver.__file__),
                  retained_serial_transport=pin(receiver.TRANSPORT_SOURCE),
                  postprocessor=pin(Path(receiver.__file__).with_name('zorn_ios26_known282_capture.py')),
                  test_tool=pin(__file__), wire=pin(args.fixtures / 'SYNTHETIC-retagged268-wire.bin'),
                  thread_registry_serial_and_runner_boundaries_mocked=True,
                  actual_bundle_or_installation_not_validated_by_this_transport_test=True,
                  phone_access=False, hardware_qualified=False)
    (args.out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS282 actual receiver through final JSON; no phone I/O')


if __name__ == '__main__':
    main()

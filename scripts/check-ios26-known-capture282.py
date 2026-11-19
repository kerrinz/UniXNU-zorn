#!/usr/bin/env python3
"""Regress282 result grading using retained268 bytes and explicit synthetic tags."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import zlib

from zorn_ios26_known282_capture import finish_capture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    prior = json.loads((args.trial / 'decoded-native-record.json').read_text())['run_id']
    tag = args.tag
    program = 'ddb9c8640ab544cd85cae684e0fb8f66'
    assert prior != tag and tag != program and len(bytes.fromhex(tag)) == 16
    original = (args.trial / 'cdc.raw').read_bytes()
    # Test-only retagging. This never modifies any captured evidence or creates
    # new hardware qualification; source program ID remains the selected267 ID.
    wire = original.replace(prior.encode(), tag.encode()).replace(
        bytes.fromhex(prior), bytes.fromhex(tag))
    page = bytearray((args.trial / 'after-log.bin').read_bytes())
    assert page[8:24] == bytes.fromhex(prior)
    page[8:24] = bytes.fromhex(tag)
    page[28:32] = bytes(4)
    struct.pack_into('<I', page, 28, zlib.crc32(page[:544]))
    scope = 'HOST-ONLY-known282'
    checks = []

    def capture(data=wire, *, code=0, errors=(), fields=None,
                after=page, before=bytes(4096), selected=program):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            if data is not None:
                (out / 'cdc.raw').write_bytes(data)
            (out / 'before-log.bin').write_bytes(before)
            (out / 'after-log.bin').write_bytes(after)
            run = dict(scope=scope, boot_attempts=1, fastboot_returned_success=True,
                       recovery_identity_after=dict(family='TWRP'))
            run.update(fields or {})
            (out / 'run.json').write_text(json.dumps(run))
            result = finish_capture(out, tag=tag, program_tag=selected,
                                    scope=scope, runner_exit=code,
                                    transport_errors=errors)
            assert result == json.loads((out / 'cdc-capture.json').read_text())
            assert not result['full_GPU_qualification']
            assert not result['physical_known_image_proven']
            assert not result['physical_FT3683_functionally_qualified']
            assert (out / 'cdc.raw').exists() == (data is not None)
            try:
                finish_capture(out, tag=tag, program_tag=selected,
                               scope=scope, runner_exit=code)
            except FileExistsError:
                pass
            else:
                raise AssertionError('historical report overwritten')
            return result

    result = capture()
    assert result['verified'] and result['bounded_Metal_and_client_lifecycle_complete282']
    assert result['serial_shot265_with_recovery_observed']
    checks.append('explicit synthetic282 boot with unchanged267 program: full census and bounded Metal are independent of physical qualification')
    cases = [
        ('old actual268 boot rejected', dict(data=original)),
        ('boot tag cannot replace selected program ID', dict(selected=tag)),
        ('old UFS record rejected', dict(after=(args.trial / 'after-log.bin').read_bytes())),
        ('same before/after record rejected', dict(before=page)),
        ('missing CDC', dict(data=None)),
        ('empty CDC', dict(data=b'')),
        ('truncated CDC', dict(data=wire[:-17])),
        ('runner failure', dict(code=1)),
        ('transport error', dict(errors=['HOST failure'])),
        ('foreign scope', dict(fields=dict(scope='foreign'))),
        ('repeated boot', dict(fields=dict(boot_attempts=2))),
        ('boolean boot count rejected', dict(fields=dict(boot_attempts=True))),
        ('no fastboot return', dict(fields=dict(fastboot_returned_success=False))),
        ('unknown Recovery', dict(fields=dict(recovery_identity_after=dict(family='unknown')))),
    ]
    for name, values in cases:
        result = capture(**values)
        assert not result['bounded_Metal_and_client_lifecycle_complete282'], name
        checks.append(name)
    # Incomplete Close must not be promoted merely by valid transport/Recovery.
    # assess_census itself is exercised against actual wire, including all four
    # source-owned registered clients, by the retained268 regression suite.
    checks.append('exclusive output preserves all earlier receipts on every case')
    def pin(path):
        path = Path(path).resolve()
        return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    fixture = args.out / 'SYNTHETIC-retagged268-wire.bin'
    fixture.write_bytes(wire)
    (args.out / 'SYNTHETIC-retagged268-page.bin').write_bytes(page)
    report = dict(passed=True, checks=checks, source=pin(Path(__file__).with_name('zorn_ios26_known282_capture.py')),
                  test_tool=pin(__file__), original_wire=pin(args.trial / 'cdc.raw'),
                  fixture=pin(fixture), explicit_synthetic_boot_identity_only=True,
                  phone_access=False, hardware_qualified=False)
    (args.out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS282 known capture: ' + str(len(checks)) + ' controls; no phone I/O')


if __name__ == '__main__':
    main()

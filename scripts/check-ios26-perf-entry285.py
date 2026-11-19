#!/usr/bin/env python3
"""Actual285 package/entry negatives; preserve missing-install refusal and state."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import zorn_ios26_gpu_v285_system_trial as t
from zorn_ios26_perf285_receiver import run_capture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    state = t.CURRENT.read_bytes()
    proof = t.validate_package()
    checks = ['actual current full285 package, native inputs, effective headers, new Metal bundle and host receipts revalidated']
    cases = [
        ('old version', lambda d: d.update(version=268)),
        ('boot ID used as program ID', lambda d: d['artifact_identity'].update(application_probe_run_id=t.TAG)),
        ('wrong kernel', lambda d: d['link'].update(sha256='0'*64)),
        ('wrong root', lambda d: d['root'].update(sha256='0'*64)),
        ('wrong ADT', lambda d: d['pins']['ADT'].update(sha256='0'*64)),
        ('wrong FD', lambda d: d['pins']['FD'].update(sha256='0'*64)),
        ('old boot', lambda d: d['boot'].update(sha256='0'*64)),
        ('wrong arguments', lambda d: d.update(boot_args='rd=md0')),
        ('unbounded watchdog', lambda d: d.update(watchdog_seconds=0)),
        ('unbounded Recovery', lambda d: d.update(recovery_timeout_seconds=1500)),
        ('retry', lambda d: d.update(retries=1)),
        ('writable roots', lambda d: d.update(runtime_roots_read_only=False)),
        ('layout change', lambda d: d.update(storage_layout_changed=True)),
        ('human dependency', lambda d: d.update(human_input_required=True)),
        ('synthetic touches', lambda d: d.update(synthetic_input_enabled=True)),
        ('probe incorrectly enabled', lambda d: d.update(probe_job_disabled=False)),
    ]
    for name, change in cases:
        bad = copy.deepcopy(proof)
        change(bad)
        try:
            t.validate_package(bad)
        except ValueError:
            checks.append(name + ' rejected')
        else:
            raise AssertionError(name)
    # This real missing dependency is intentional and must stay a refusal;
    # never generate fake installation success to make an execution test pass.
    if not t.SOURCES['root_install_receipt'].exists():
        def forbidden(*args, **kwargs):
            raise AssertionError('device boundary reached without installed root')
        with patch.object(t, 'probe_existing_adb_listener', forbidden), patch.object(t, 'run', forbidden):
            for action in [lambda: t.validate(t.TRIAL/'bundle.json'), lambda: run_capture(t)]:
                try:
                    action()
                except ValueError as error:
                    assert 'installation/readback absent' in str(error)
                else:
                    raise AssertionError('uninstalled285 root accepted')
        checks.append('actual system and receiver refuse missing285 installation before listener/runner/claim')
    command = [sys.executable, '-B', str(Path(__file__).with_name('run-zorn-debug.py')),
               '--ios26-perf285-trial', '--check-package']
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    (args.out/'runner.stdout').write_text(result.stdout)
    (args.out/'runner.stderr').write_text(result.stderr)
    assert result.returncode == 0 and 'root installation not inferred' in result.stdout
    assert t.CURRENT.read_bytes() == state
    assert not (t.TRIAL/'trial/one-shot.claim.json').exists()
    checks.append('actual maintained runner dispatch check-only passes; controller/claim unchanged')
    def pin(path):
        path = Path(path).resolve()
        return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    report = dict(passed=True, checks=checks, source=pin(t.__file__),
                  fixed_runner=pin(Path(__file__).with_name('run-zorn-debug.py')),
                  test_tool=pin(__file__), package=pin(t.PACKAGE),
                  command=command, actual_current_native_inputs_checked=1399,
                  source_metadata_negatives_not_hardware=True,
                  phone_access=False, new_boot_or_claim=False, full_GPU_qualification=False)
    (args.out/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print('PASS285 actual package/runner and '+str(len(checks))+' host controls; no device access')


if __name__ == '__main__':
    main()

"""Assemble a reviewable host candidate from completed, audited artifacts.

This entry never rebuilds the native kernel, starts a phone or qualifies boot.
GPU invocation, the consumed memory trial and query handoff stay disabled.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def assemble(root, policy):
    for path, expected in policy['inputs'].items():
        if sha(path) != expected:
            raise RuntimeError('Host candidate input changed: ' + path)
    current = json.loads((root / 'out/zorn/unattended-active/current.json').read_text())
    if current.get('active_run') or current.get('runner_session'):
        raise RuntimeError('A device run is active')
    if policy['allow_boot'] is not False or policy['readback_qualified'] is not False:
        raise RuntimeError('This host candidate cannot grant boot permission')
    kernel = Path(policy['kernel'])
    plan = json.loads(Path(policy['kernel_plan']).read_text())
    if sha(kernel) != plan['candidate_sha256']:
        raise RuntimeError('Final postlink kernel digest differs')
    fd = json.loads(Path(policy['fd_audit']).read_text())
    if not fd['extracted_module_whole_file_equal'] or fd['native_GPU_invoked'] or fd['WriteAuthorized']:
        raise RuntimeError('Closed firmware audit required')
    out = Path(policy['output'])
    out.mkdir(exist_ok=True)
    if (out / 'boot.img').exists():
        raise RuntimeError('Completed candidate must be archived before a new assembly')
    baseline = {p: sha(p) for p in policy['baseline_paths']}
    commands = []
    for name, command in policy['commands']:
        with (out / (name + '.log')).open('w') as log:
            result = subprocess.run(command, cwd=root, stdout=log, stderr=subprocess.STDOUT)
        commands.append(dict(name=name, arguments=command, returncode=result.returncode))
        if result.returncode:
            (out / 'failed-command.json').write_text(json.dumps(commands, indent=2) + '\n')
            raise RuntimeError('Host candidate command failed: ' + name)
    if any(sha(p) != value for p, value in baseline.items()):
        raise RuntimeError('Host assembly changed a baseline')
    report = dict(commands=commands, final_kernel_sha256=sha(kernel),
                  fd_sha256=fd['fd_sha256'], boot_sha256=sha(out / 'boot.img'),
                  payload_sha256=sha(out / 'payload.img'),
                  final_ADT_sha256=sha(out / 'payload-with-trustcache.adt'),
                  menu_sha256=sha(out / 'payload-ramdata.toml'),
                  original_baselines=baseline, baselines_unchanged=True,
                  GPU_executed=False, phone_operations=False,
                  native_GPU_invoked=False, WriteAuthorized=0,
                  hardware_qualified=False, allow_boot=False, readback_qualified=False)
    (out / 'assembly-result.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Host candidate assembled:', report['boot_sha256'], 'boot remains disabled')

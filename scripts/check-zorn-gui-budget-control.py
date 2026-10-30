#!/usr/bin/env python3
"""Exercise real budget-reuse guards with a readonly completed archive."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import zorn_gui_budget_control as guard

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--control', type=Path, required=True)
args = p.parse_args()
control_dir = args.control.resolve()
control = json.loads((control_dir / 'inputs.json').read_text())
record = {k: v for k, v in control.items() if k not in
          ('status', 'started', 'phase', 'image', 'sha256', 'inputs', 'completed', 'kernel_reuse')}
record['status'], record['started'], record['phase'] = 'building', 'host-check', 'kernel'
record['gui_hold_seconds'], record['recovery_timeout_seconds'] = (
    (900, 1200) if control['gui_hold_seconds'] == 300 else (300, 600))
proof = guard.verify_control(control_dir, record, ROOT)
rejected = []


def reject(label, operation):
    try:
        operation()
    except RuntimeError:
        rejected.append(label)
    else:
        raise AssertionError('unsafe reuse accepted: ' + label)


for key, value in (
    ('smp_root_publication', 0), ('smp_stop_after_pass', True),
    ('fresh_data', True), ('retained_data', False), ('data_profile', '512m'),
    ('memory_mib', 12288), ('gui_user_stacks', True), ('touch_runtime', False),
    ('brightness_mode', 0), ('source_replay_sha256', '0' * 64),
    ('source_pins_sha256', None), ('gui_hold_seconds', control['gui_hold_seconds']),
    ('recovery_timeout_seconds', 2400), ('disabled_jobs', []),
):
    changed = copy.deepcopy(record)
    changed[key] = value
    reject('profile:' + key, lambda changed=changed: guard.verify_profile(control, changed))

actual_digest = guard.digest
for label, target in (
    ('archive-kernel', control_dir / 'kernel.macho'),
    ('archive-boot', control_dir / 'boot.img'),
    ('archive-plan', control_dir / 'kernel-plan.json'),
    ('native-source', ROOT / 'UniXNU-zorn/native/ufs-read/ZornUfsRead.cpp'),
    ('display-source', ROOT / 'UniXNU-zorn/native/display/ZornDisplayProbe.cpp'),
    ('other-host-source', ROOT / 'uefi-zorn/scripts/make-zorn-payload.py'),
    ('Data-geometry', ROOT / 'out/zorn/data-store8-192/plan.json'),
    ('CPU-object-bytes', ROOT / 'UniXNU/out/zorn/tree/build/armcpu/ArmCpu.o'),
    ('display-ABI-bytes', ROOT / 'UniXNU/out/zorn/tree/build/native-legacy-display/OriginalLegacyFramebufferABI.h'),
):
    def changed_digest(path, target=target):
        return '0' * 64 if Path(path) == target else actual_digest(path)
    with patch.object(guard, 'digest', changed_digest):
        reject(label, lambda: guard.verify_control(control_dir, record, ROOT))

read_text = Path.read_text
for label, target, key in (
    ('actual-CPU-object', ROOT / 'UniXNU/out/zorn/tree/build/armcpu/zorn-smp-build.json', 'object_sha256'),
    ('actual-display-ABI', ROOT / 'UniXNU/out/zorn/tree/build/native-legacy-display/build-report.json', 'generated_abi_sha256'),
):
    def changed_report(path, *a, target=target, key=key, **kw):
        text = read_text(path, *a, **kw)
        if path == target:
            data = json.loads(text)
            assert key in data
            data[key] = '0' * 64
            return json.dumps(data)
        return text
    with patch.object(Path, 'read_text', changed_report):
        reject(label, lambda: guard.verify_control(control_dir, record, ROOT))

result = dict(actual_readonly_control=control['sha256'], actual_kernel=proof['kernel_sha256'],
              source_inputs_verified=proof['inputs_verified'],
              actual_guard_sha256=hashlib.sha256(Path(guard.__file__).read_bytes()).hexdigest(),
              explicit_budget_only_positive_passed=True, rejected=rejected,
              phone_access=False, original_inputs_modified=False)
out = ROOT / 'out/zorn/gui-budget-host-check.json'
out.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))

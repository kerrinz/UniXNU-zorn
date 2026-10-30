"""Verify the narrow, same-kernel GUI observation-budget experiment.

This does not authorize general kernel reuse. The native sources, frozen
components, Data geometry and every non-budget profile field must match.
"""
import hashlib
import json
from pathlib import Path


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_profile(control, record):
    required = dict(serial='92988a43', incremental_patched_tree=True,
                    defconfig='zorn_union_defconfig', data_profile='8g',
                    fresh_data=False, smp_preflight=8, smp_continue=True,
                    smp_stop_after_pass=False, smp_root_publication=1,
                    display_mode=3, brightness_mode=3, memory_mib=8192,
                    gui_watch=True, gui_user_stacks=False,
                    gui_kernel_stacks=False, gui_runnable_kernel_stacks=False,
                    retained_data=True, data_store_mode=2, data_permissions=True,
                    touch_runtime=True, touch_trace=True, touch_fast_poll=True,
                    early_watchdog_mode=1, quiet_gui=True)
    for key, value in required.items():
        if (type(control.get(key)) is not type(value) or type(record.get(key)) is not type(value)
                or control.get(key) != value or record.get(key) != value):
            raise RuntimeError('GUI budget control requires fixed profile: ' + key)
    if not record.get('source_pins_sha256') or not record.get('source_replay_sha256'):
        raise RuntimeError('GUI budget control requires frozen source proof')
    before = (control.get('gui_hold_seconds'), control.get('recovery_timeout_seconds'))
    after = (record.get('gui_hold_seconds'), record.get('recovery_timeout_seconds'))
    if {before, after} != {(300, 600), (900, 1200)}:
        raise RuntimeError('GUI budget control requires opposite 300/600 and 900/1200 budgets')
    ignored = {'status', 'started', 'phase', 'gui_hold_seconds', 'recovery_timeout_seconds'}
    for key, value in record.items():
        if key not in ignored and control.get(key) != value:
            raise RuntimeError('GUI budget control profile differs: ' + key)


def verify_control(control_dir, record, root):
    root, control_dir = Path(root).resolve(), Path(control_dir).resolve()
    core, out = root / 'UniXNU', root / 'out/zorn'
    control = json.loads((control_dir / 'inputs.json').read_text())
    verify_profile(control, record)
    kernel = core / 'out/zorn/kernel/kernel.macho'
    if (control.get('status') != 'ready' or
            control_dir.name != control.get('sha256', '')[:8] or
            digest(control_dir / 'boot.img') != control.get('sha256') or
            digest(control_dir / 'kernel.macho') != control['inputs'].get(str(kernel))):
        raise RuntimeError('GUI budget control archive identity differs')
    # Only kernel-bound generated outputs may resolve to their immutable
    # archive bytes. Every other input must still be current and exact.
    generated = {
        kernel: 'kernel.macho', kernel.with_suffix('.json'): 'kernel-plan.json',
        out / 'smp/start-object-audit.json': 'smp-start-object-audit.json',
        out / 'smp/linked-call-audit.json': 'smp-linked-call-audit.json',
        out / 'payload-ramdata.toml': 'unixnu.toml',
        core / 'out/zorn/tree/build/armcpu/zorn-smp-build.json': 'smp-driver-build.json',
        core / 'out/zorn/tree/build/native-legacy-display/build-report.json': 'display-build-report.json',
        out / 'data-seed-audit.json': 'data-seed-audit.json',
        out / 'data-store-link-audit.json': 'data-store-link-audit.json',
        out / 'gui-hook-audit.json': 'gui-hook-audit.json',
        out / 'touch/runtime-linked-calls.json': 'touch-runtime-linked-calls.json',
        out / 'startup-policy-audit.json': 'startup-policy-audit.json',
        out / 'data-permissions-audit.json': 'data-permissions-audit.json',
    }
    resolved, driver_revision = [], None
    host_driver = root / 'UniXNU-zorn/scripts/build-zorn-debug.py'
    for name, expected in control['inputs'].items():
        path, kind = Path(name), 'current-exact'
        if path in generated:
            path, kind = control_dir / generated[path], 'immutable-generated-exact'
        actual = digest(path)
        if actual != expected:
            if path != host_driver:
                raise RuntimeError('GUI budget control source/input differs: ' + name)
            # Adding this host-only interface necessarily changes the builder.
            # It generates no target code; no native/other script exception.
            driver_revision = dict(path=name, control_sha256=expected, current_sha256=actual)
            kind = 'explicit-host-budget-interface-revision'
        resolved.append(dict(original=name, resolved=str(path), sha256=actual, resolution=kind))
    for name in ('ArmCpu.cpp', 'ZornSmpRuntime.inc', 'ZornSmpPolicy.h'):
        if digest(control_dir / name) != digest(out / 'smp/runtime' / name):
            raise RuntimeError('GUI budget control native source differs: ' + name)
    # Archive timestamps and the previous candidate identity are provenance,
    # not object code. All other actual source/object fingerprint fields stay.
    for archived, current, provenance in (
        ('smp-driver-build.json', core / 'out/zorn/tree/build/armcpu/zorn-smp-build.json',
         {'archive_sha256'}),
        ('display-build-report.json', core / 'out/zorn/tree/build/native-legacy-display/build-report.json',
         {'archive_sha256', 'original_candidate_sha256'}),
    ):
        old, new = json.loads((control_dir / archived).read_text()), json.loads(current.read_text())
        if {k: v for k, v in old.items() if k not in provenance} != {k: v for k, v in new.items() if k not in provenance}:
            raise RuntimeError('GUI budget control actual object/source differs: ' + archived)
        if isinstance(new.get('source_sha256'), dict):
            for name, expected in new['source_sha256'].items():
                if digest(Path(name)) != expected:
                    raise RuntimeError('GUI budget control display source bytes differ: ' + name)
        if archived == 'smp-driver-build.json' and digest(current.parent / 'ArmCpu.o') != new['object_sha256']:
            raise RuntimeError('GUI budget control CPU object bytes differ')
        if archived == 'display-build-report.json' and digest(current.parent / 'OriginalLegacyFramebufferABI.h') != new['generated_abi_sha256']:
            raise RuntimeError('GUI budget control generated display ABI bytes differ')
    plan = control_dir / 'kernel-plan.json'
    if digest(plan) != control['inputs'].get(str(kernel.with_suffix('.json'))):
        raise RuntimeError('GUI budget control requires exact original prelink plan')
    return dict(kind='reused-gui-budget-control', control_boot_sha256=control['sha256'],
                control_manifest_sha256=digest(control_dir / 'inputs.json'),
                kernel_sha256=digest(control_dir / 'kernel.macho'), source_archive=str(control_dir),
                control_budget=[control['gui_hold_seconds'], control['recovery_timeout_seconds']],
                requested_budget=[record['gui_hold_seconds'], record['recovery_timeout_seconds']],
                inputs_verified=len(resolved), host_budget_interface_revision=driver_revision,
                resolved_inputs=resolved)

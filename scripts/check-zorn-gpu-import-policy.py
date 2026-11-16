#!/usr/bin/env python3
"""Read-only symbol-role audit. Never plans rebinding or emits an image.

Reports names/visibility only; numerical symbol values stay inside the existing
reader and are neither serialized nor used to construct an import binding.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
WATCH = ('___ubsan_handle_negate_overflow_minimal',
         '_sysctl_register_oid_early', '_native_pmap_user_mappings')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def export_source(source):
    node = next(n for n in ast.parse(source).body
                if isinstance(n, ast.FunctionDef) and n.name == 'exports')
    return ast.get_source_segment(source, node)


def check_predicate(source):
    body = export_source(source)
    if 'if kind & 0xe0 or not kind & 1 or not kind & 0x0e:' not in body:
        raise ValueError('Exact selected defined-external predicate changed')
    if '0x10' in body:
        raise ValueError('N_PEXT alone must not be treated as non-external')


def audit(root):
    reader = root / 'UniXNU/kits/XnuPrelink/native_prelink.py'
    source = reader.read_text()
    check_predicate(source)
    native = load(reader, 'import_policy_reader')
    names = load(root / 'UniXNU/scripts/xnu_symbols.py', 'import_policy_names')
    base = root / 'out/zorn/dual-system-reinstall-20261101/native-build'
    tree = root / 'UniXNU/out/zorn/tree'
    obj = tree / 'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837'
    plan = json.loads((base / 'kernel.postlink-plan.json').read_text())
    roles = {
        'historical_native': base / 'native-archive/kernel.native.macho',
        'retained_postlink': base / 'prelinked-archive/kernel.prelinked.macho',
        'current_mutable_native': obj / 'mach.development.bcm2837.unstripped.noctf',
        'selected_ubsan_object': obj / 'san/DEVELOPMENT/ubsan_minimal.o',
        'selected_sysctl_object': obj / 'bsd/DEVELOPMENT/kern_newsysctl.o',
        'parent_static_component': root / 'out/zorn/gpu-owned-bitmap-init/bitmap-ubsan-component.o',
    }
    assert sha(roles['historical_native']) == plan['native_sha256']
    assert sha(roles['retained_postlink']) == plan['candidate_sha256']
    records = {}
    for role, path in roles.items():
        data = path.read_bytes()
        # Existing exact reader only. Discard its temporary numeric keys.
        exported = {n for group in native.exports(data, native.macho(data)).values() for n in group}
        globals_ = names.defined_names([path], True)
        all_ = names.defined_names([path], False)
        detail = subprocess.check_output(['xcrun', 'nm', '-m', str(path)], text=True)
        visibility = {}
        for name in WATCH:
            descriptions = []
            for line in detail.splitlines():
                if line.split() and line.split()[-1] == name:
                    # Strip any symbol value, not just a particular address width.
                    marker = line.find('(')
                    descriptions.append(line[marker:].rsplit(name, 1)[0].strip())
            visibility[name] = dict(defined_in_all_names=name in all_,
                                    defined_in_global_names=name in globals_,
                                    selected_prelink_exports_contains=name in exported,
                                    visibility=descriptions)
        records[role] = dict(path=str(path), sha256=sha(path), names=visibility)
    neg = WATCH[0]
    assert records['selected_ubsan_object']['names'][neg]['selected_prelink_exports_contains']
    for role in ['retained_postlink', 'parent_static_component']:
        entry = records[role]['names'][neg]
        assert entry['defined_in_all_names'] and not entry['selected_prelink_exports_contains']
    # Two new policy negative controls, on private source copies only. No
    # executable provider, fake Mach-O, address/handle or hardware-success peer.
    controls = []
    for label, old, new in [
        ('external-filter-erased', 'or not kind & 1 ', ''),
        ('private-external-wrongly-banned', 'if kind & 0xe0 or ', 'if kind & 0x10 or kind & 0xe0 or '),
    ]:
        changed = export_source(source).replace(old, new, 1)
        try:
            check_predicate(changed)
        except ValueError:
            rejected = True
        else:
            raise AssertionError('Policy mutation not refused')
        scope = dict(native.__dict__)
        exec(compile(changed, '<private-policy-negative>', 'exec'), scope)
        role = 'retained_postlink' if label == 'external-filter-erased' else 'selected_ubsan_object'
        data = roles[role].read_bytes()
        wrong = {n for group in scope['exports'](data, native.macho(data)).values() for n in group}
        assert (neg in wrong) == (label == 'external-filter-erased')
        controls.append(dict(name=label, source_guard_refused=rejected,
                             real_artifact_name_semantics_changed=True))
    linked = [Path(n) for n in (obj / 'link.filelist').read_text().splitlines() if n.strip()]
    runtime = roles['selected_ubsan_object']
    assert sum(p.resolve() == runtime.resolve() for p in linked) == 1
    return dict(
        state='native-source-link-and-donor-prelink-policy-bound-offline',
        roles=records, new_policy_negative_controls=controls,
        selected_XNU_link_filelist_UBSan_count=1,
        historical_native_identity_matches_frozen_postlink_plan=True,
        current_mutable_native_is_historical_input=sha(roles['current_mutable_native']) == plan['native_sha256'],
        policy='Native archives share the XNU source link;prelink exports only selects donor pointer-rebinding names;collision name checks are a third role.',
        N_PEXT_with_N_EXT_can_pass_but_localized_nonexternal_does_not=True,
        duplicate_runtime_append_or_private_address_import_not_qualified=True,
        pmap_optional_diagnostic_still_unbound=True,
        no_plan_emit_link_compile_native_provider_phone_or_address_binding=True,
        no_target_component_or_final_kernel_qualification=True,
        allow_boot=False, readback_qualified=False, WriteAuthorized=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(audit(args.root.resolve()), indent=2) + '\n')
    print('Name-only import-role audit passed;2 new policy negatives refused;no image or native execution')


if __name__ == '__main__':
    main()

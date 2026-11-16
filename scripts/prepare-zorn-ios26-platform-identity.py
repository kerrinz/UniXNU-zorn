#!/usr/bin/env python3
"""Add the documented K80 OS26 platform status properties to a local ADT.

No executable inspection, activation-method hook, phone access or image write.
The profile supplies typed public ADT data, not hardware-operation results.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / 'out/zorn/ios26-feasibility-20261107'
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'UniXNU/scripts'))
from unixnu.devicetree import typed_properties
sys.path.insert(0, str(STAGE / 'source/common/boot'))
from ios26_adt import parse, serialize

DOCUMENTED_STATUS = {
    'certificate-production-status': 0,
    'effective-production-status-ap': 0,
    'certificate-security-mode': 1,
    'effective-security-mode-sep': 1,
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def prepare(raw, profile, input_sha256, root_sha256):
    if digest(raw) != input_sha256:
        raise ValueError('actual parent ADT changed')
    if (type(profile.get('format')) is not int or profile['format'] != 1
            or profile.get('donor') != dict(product='iPhone18,1', version='26.6.2', build='23G90')
            or set(profile) != {'format', 'donor', 'chosen'}):
        raise ValueError('exact OS26 phone configuration profile required')
    chosen_profile = profile['chosen']
    if (type(chosen_profile) is not dict or set(chosen_profile) != {'u32'}
            or type(chosen_profile['u32']) is not dict
            or chosen_profile['u32'] != DOCUMENTED_STATUS
            or any(type(x) is not int for x in chosen_profile['u32'].values())):
        raise ValueError('only the four documented u32 status properties are allowed')
    tree = parse(raw)
    if serialize(tree) != raw or tree.get('model') != b'iPhone18,1\0':
        raise ValueError('canonical retained phone identity required')
    if not {b'xiaomi,zorn', b'qcom,sm8650'} <= set((tree.get('compatible') or b'').split(b'\0')):
        raise ValueError('K80 board identity required')
    try:
        expected_root = bytes.fromhex(root_sha256)
    except ValueError as error:
        raise ValueError('invalid root digest') from error
    chosen = tree.child('chosen')
    if len(expected_root) != 32 or chosen.get('zorn26,root-image-sha256') != expected_root:
        raise ValueError('actual root cohort differs')
    added = []
    for name, value in typed_properties(chosen_profile):
        previous = chosen.get(name)
        if previous is not None and previous != value:
            raise ValueError('conflicting existing status property: ' + name)
        if previous is None:
            chosen.set(name, value)
            added.append(name)
    if not added:
        raise ValueError('status already matches; no new candidate needed')
    output = serialize(tree)
    restored = parse(output)
    restored.child('chosen').properties = [item for item in restored.child('chosen').properties
                                            if item[0] not in added]
    if serialize(restored) != raw:
        raise ValueError('unrelated ADT bytes changed')
    return output, dict(added_properties=added, chosen_u32=DOCUMENTED_STATUS,
                        original_ADT_restored_exactly_after_removing_additions=True,
                        existing_root_model_product_buttons_and_hardware_preserved=True,
                        input_sha256=input_sha256, output_sha256=digest(output),
                        root_sha256=root_sha256, native_or_phone_executed=False,
                        runtime_identity_or_activation_success_proven=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['input', 'profile', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--input-sha256', required=True)
    parser.add_argument('--root-sha256', required=True)
    args = parser.parse_args()
    for source in [args.input, args.profile]:
        if source.resolve() != source or not source.is_relative_to(STAGE) or not source.is_file():
            parser.error('ordinary canonical local candidate input required')
    if (args.output.resolve() != args.output or not args.output.is_relative_to(STAGE / 'build')
            or args.output.exists() or args.output.is_symlink()):
        parser.error('new independent local output directory required')
    output, proof = prepare(args.input.read_bytes(), tomllib.loads(args.profile.read_text()),
                            args.input_sha256, args.root_sha256)
    args.output.mkdir()
    (args.output / 'kernel.platform-identity.UNSELECTED.adt').write_bytes(output)
    proof.update(profile_sha256=digest(args.profile.read_bytes()),
                 source_sha256=digest(Path(__file__).read_bytes()),
                 public_reference='https://unixnu.com/zh/guide/mobilegestalt')
    (args.output / 'receipt.json').write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps(proof))


if __name__ == '__main__':
    main()

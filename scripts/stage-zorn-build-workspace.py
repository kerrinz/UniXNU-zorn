#!/usr/bin/env python3
"""Stage an isolated macOS build from explicit local inputs; never access USB.

Requires the prepared SDK/source caches, retained Data inputs, firmware capability
record, and the named ABI / eight-core qualification archives. This is not an
artifact-free bootstrap or an installer for a phone.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

DEVICE = Path(__file__).resolve().parents[1]
ROOT = DEVICE.parent


def run(values, **kwargs):
    return subprocess.run([str(v) for v in values], check=True, **kwargs)


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def copy(source, target):
    if target.exists() or target.is_symlink():
        raise RuntimeError(f'existing destination refused: {target}')
    target.parent.mkdir(parents=True, exist_ok=True)
    # APFS clones are independent on write, including the large readonly image.
    run(['cp', '-cR', source, target])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True, help='new directory only')
    parser.add_argument('--abi-reference', type=Path, required=True, help='ready build archive, including kernel-plan.json')
    parser.add_argument('--mu', type=Path, required=True, help='existing Mu-Silicium dependency')
    parser.add_argument('--xnu-patch-base', help='optional full core commit for a controlled XNU patch baseline')
    parser.add_argument('--source-snapshot', type=Path, help='qualified source capsule within this device repository')
    args = parser.parse_args()
    if args.source_snapshot and args.xnu_patch_base:
        parser.error('choose either a source snapshot or an upstream patch base')
    if args.source_snapshot:
        args.source_snapshot = args.source_snapshot.resolve()
        if not args.source_snapshot.is_relative_to(DEVICE):
            parser.error('source capsule must belong to this device repository')
    if sys.platform != 'darwin':
        parser.error('this prepared SDK / APFS clone recipe requires macOS')
    workspace = args.workspace.resolve()
    if workspace.exists():
        parser.error('workspace already exists; it will not be reset or reused')
    if not (args.mu / 'build_uefi.py').is_file():
        parser.error('--mu is not a Mu-Silicium checkout')
    archive = args.abi_reference.resolve()
    manifest = json.loads((archive / 'inputs.json').read_text())
    hashes = [v for p, v in manifest['inputs'].items()
              if p.endswith('/UniXNU/out/zorn/kernel/kernel.macho')]
    plans = [v for p, v in manifest['inputs'].items()
             if p.endswith('/UniXNU/out/zorn/kernel/kernel.json')]
    if (manifest.get('status') != 'ready' or len(hashes) != 1 or len(plans) != 1
            or digest(archive / 'boot.img') != manifest['sha256']
            or digest(archive / 'kernel.macho') != hashes[0]
            or digest(archive / 'kernel-plan.json') != plans[0]):
        parser.error('ABI reference archive / input hashes differ')
    run(['python3', DEVICE / 'scripts/check-zorn-source-pins.py'])
    required = ['verified-root', 'data-grow8', 'data-store8-192', 'ram-data',
                'smp/runtime', 'original-trustcache', 'cpu-profile',
                'firmware.inputs.json', 'kernel.macho.adt', 'smp/eight-remap-qualified.json']
    for name in required:
        if not (ROOT / 'out/zorn' / name).exists():
            parser.error(f'prepared host input missing: out/zorn/{name}')
    core = workspace / 'UniXNU'
    workspace.mkdir(parents=True)
    state = {'status': 'staging', 'device_operations': False,
             'old_xnu_objects_reused': False, 'abi_reference_boot_sha256': manifest['sha256'],
             'abi_reference_kernel_sha256': hashes[0], 'workspace': str(workspace)}
    record = workspace / 'staging.json'
    record.write_text(json.dumps(state, indent=2) + '\n')
    try:
        run(['git', 'clone', '--quiet', '--shared', '--no-checkout', ROOT / 'UniXNU', core])
        upstream = subprocess.check_output(['git', '-C', str(ROOT / 'UniXNU'), 'remote', 'get-url', 'origin'], text=True).strip()
        run(['git', '-C', core, 'remote', 'set-url', 'origin', upstream])
        revision = subprocess.check_output(['git', '-C', str(ROOT / 'UniXNU'), 'rev-parse', 'HEAD'], text=True).strip()
        run(['git', '-C', core, 'checkout', '--quiet', '--detach', revision])
        overlay = subprocess.check_output(['git', '-C', str(ROOT / 'UniXNU'), 'diff', '--binary'])
        run(['git', '-C', core, 'apply', '-'], input=overlay)
        for name in ('UniXNU-zorn', 'uefi-zorn'):
            copy(ROOT / name, workspace / name)
        pins = json.loads((DEVICE / 'source-pins.json').read_text())
        # Each component gets an independent working tree, not a writable alias
        # to the original. Only its immutable Git object storage is shared.
        for relative, pin in pins['core'].items():
            target = core / relative
            if target.exists():
                target.rmdir()  # only the empty gitlink directory from checkout
            run(['git', 'clone', '--quiet', '--shared', '--no-checkout', ROOT / 'UniXNU' / relative, target])
            upstream = subprocess.check_output(
                ['git', '-C', str(ROOT / 'UniXNU' / relative), 'remote', 'get-url', 'origin'], text=True,
            ).strip()
            run(['git', '-C', target, 'remote', 'set-url', 'origin', upstream])
            run(['git', '-C', target, 'checkout', '--quiet', '--detach', pin['commit']])
            for name, expected in pin['files'].items():
                source = ROOT / 'UniXNU' / relative / name
                if digest(source) != expected:
                    raise RuntimeError(f'component changed during staging: {relative}/{name}')
                destination = target / name
                if not destination.is_file() or digest(destination) != expected:
                    if destination.exists():
                        destination.unlink()
                    copy(source, destination)
        for name in ('feeds', 'ipsw'):
            target = core / 'out' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(ROOT / 'UniXNU/out' / name)
        for patch in (DEVICE / 'patches/zorn').glob('*.patch'):
            shutil.copy2(patch, core / 'patches/xnu' / patch.name)
        for name in required:
            copy(ROOT / 'out/zorn' / name, workspace / 'out/zorn' / name)
        proof = json.loads((ROOT / 'out/zorn/smp/eight-remap-qualified.json').read_text())
        for relative in (proof['run'], proof['archive']):
            copy(ROOT / relative, workspace / relative)
        # Restore the immutable ABI audit input, not any native build objects.
        copy(archive / 'kernel.macho', core / 'out/zorn/kernel/kernel.macho')
        copy(archive / 'kernel-plan.json', core / 'out/zorn/kernel/kernel.json')
        copy(ROOT / 'UniXNU/out/zorn/userdata/userdata-root.img',
             core / 'out/zorn/userdata/userdata-root.img')
        tree = core / 'out/zorn/tree'
        for name in ('fakeroot', 'sources'):
            copy(ROOT / 'UniXNU/out/zorn/tree/.cache' / name, tree / '.cache' / name)
        replay = workspace / 'source-replay'
        command = ['python3', workspace / 'UniXNU-zorn/scripts/check-zorn-patch-series.py',
                   '--core', core, '--reference', ROOT / 'UniXNU/out/zorn/tree/refer/xnu', '--workdir', replay]
        if args.xnu_patch_base:
            command += ['--base-revision', args.xnu_patch_base]
        if args.source_snapshot:
            command += ['--snapshot', workspace / 'UniXNU-zorn' / args.source_snapshot.relative_to(DEVICE)]
        run(command)
        (replay / 'xnu').rename(tree / '.cache/xnu-work')
        copy(replay / 'result.json', core / 'out/zorn/source-replay.json')
        # Reuse public source headers only after checking each Apple Git blob.
        for metadata, folder in (
            ('xnu-driverkit-10063.121.3.json', 'iokit/DriverKit'),
            ('xnu-driverkit-crypto-10063.121.3.json', 'iokit/DriverKit/crypto'),
            ('xnu-trustcache-8796.101.5.json', 'EXTERNAL_HEADERS/TrustCache'),
        ):
            for entry in json.loads((tree / '.cache/sources' / metadata).read_text()):
                if entry['type'] != 'file' or not entry['name'].endswith('.h'):
                    continue
                relative = Path(folder) / entry['name']
                target = tree / '.cache/xnu-work' / relative
                if target.exists():
                    continue
                source = ROOT / 'UniXNU/out/zorn/tree/.cache/xnu-work' / relative
                data = source.read_bytes()
                if hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() != entry['sha']:
                    raise RuntimeError(f'cached Apple public header differs: {relative}')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        mu = workspace.parent / 'Mu-Silicium'
        if mu.exists() or mu.is_symlink():
            if mu.resolve() != args.mu.resolve():
                raise RuntimeError('existing sibling Mu-Silicium differs; not replaced')
        else:
            mu.symlink_to(args.mu.resolve())
        env = dict(os.environ, UNIXNU_SUBMODULE_PINS=str(workspace / 'UniXNU-zorn/source-pins.json'))
        # Assemble from available pinned inputs only; the public CLI otherwise
        # updates all submodules before assembling the tree.
        prepare = '''import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / 'scripts'))
from unixnu import cli, feeds, tree
from unixnu.config import Context
ctx = Context(cli.parser().parse_args(['defconfig', 'zorn_union_defconfig', '-D', sys.argv[2]]))
cli.cmd_defconfig(ctx)
feeds.update_submodules(ctx)
tree.assemble(ctx, feeds.resolve(ctx))
'''
        run(['python3', '-c', prepare, core, workspace / 'UniXNU-zorn'], env=env)
        assert not (tree / 'build/xnu').exists()
        state.update(status='staged-not-built', core_commit=revision, xnu_patch_base=args.xnu_patch_base,
                     source_snapshot=str(args.source_snapshot) if args.source_snapshot else None,
                     source_replay='source-replay/result.json')
        record.write_text(json.dumps(state, indent=2) + '\n')
        print(f'Staged without USB or old XNU objects: {workspace}')
        print('Run the documented full builder from this workspace, including --source-pins, --fd and --ipsw.')
    except Exception as error:
        state.update(status='failed', error=str(error))
        record.write_text(json.dumps(state, indent=2) + '\n')
        raise


if __name__ == '__main__':
    main()

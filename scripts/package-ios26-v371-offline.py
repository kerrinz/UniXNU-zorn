#!/usr/bin/env python3
"""Repack the pinned v371 K80 carrier and run the upstream package verifier."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
from types import SimpleNamespace


DEVICE = Path(__file__).resolve().parents[1]
UPSTREAM_REVISION = '630b85a307f19c8d8a4699d5bfc12f6796b874aa'
PROFILE = 'ios-26.6.2-23G90'
REMOVED = 'zorn26_gpu_provider_claim=1'
PACKER_SHA = 'aca8cbfeff08c4535a5f868b8155939e2bdbf1b397aa09397b50f28cedeebb2d'
SHIM_SHA = '2fea475a9d6a8dbff8f91f4a8018d2155aeadcc20f6cce614e0d35ea625e3dc3'
MENU = 'EFI/UniXNU/unixnu.toml'


def run(*args):
    subprocess.run(args, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verified', required=True, type=Path, help='original v371 boot-package/verified.json')
    parser.add_argument('--upstream', required=True, type=Path, help='checkout at ' + UPSTREAM_REVISION)
    parser.add_argument('--uefi', required=True, type=Path, help='matching uefi-zorn checkout')
    parser.add_argument('--out', required=True, type=Path, help='new output directory')
    args = parser.parse_args()

    upstream = args.upstream.resolve()
    revision = subprocess.check_output(['git', '-C', upstream, 'rev-parse', 'HEAD'], text=True).strip()
    if revision != UPSTREAM_REVISION:
        sys.exit(f'Use UniXNU at {UPSTREAM_REVISION}')
    for path in ('scripts/unixnu', 'unixnu'):
        run('git', '-C', upstream, 'diff', '--quiet', 'HEAD', '--', path)
    sys.path.insert(0, str(upstream / 'scripts'))
    from unixnu import payload, pipeline
    from unixnu.util import sha256_file

    def checked(path, digest):
        if sha256_file(path) != digest:
            sys.exit(f'SHA-256 differs from the pinned v371 input: {path}')
        return path

    evidence = json.loads((DEVICE / 'docs/evidence/k80-ft3683-v371-early-smmu-cdc-offline-2026-11-19.json').read_text())
    original = args.verified.resolve()
    verified_sha = evidence['exact_package']['sha256']
    manifest = json.loads(checked(original, verified_sha).read_text())
    archive = original.parent
    source_fat = checked(archive / Path(manifest['FAT']['path']).name, manifest['FAT']['sha256'])
    fd = checked(archive / 'inputs/firmware.fd', manifest['pins']['FD']['sha256'])
    packer = checked(args.uefi.resolve() / 'scripts/package-zorn-boot.py', PACKER_SHA)
    old_args = manifest['boot_args']
    tokens = old_args.split(' ')
    if old_args != evidence['boot_args'] or tokens.count(REMOVED) != 1:
        sys.exit('The original v371 command line differs from the review')
    tokens.remove(REMOVED)
    short_args = payload.check_args(tokens)
    if len(short_args.encode('ascii')) >= pipeline.MAX_COMMAND_LINE:
        sys.exit('The adjusted command line still exceeds the verifier limit')

    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    ctx = SimpleNamespace(work=out, name='zorn', config_name='zorn_ios26_defconfig', board={})
    files = pipeline.outputs(ctx)
    for path in files.values():
        path.parent.mkdir(exist_ok=True)
    fat = files['payload.img']
    shutil.copyfile(source_fat, fat)
    with tempfile.TemporaryDirectory(dir=out) as temporary:
        scratch = Path(temporary)
        menu = scratch / 'unixnu.toml'
        run('mcopy', '-i', fat, f'::/{MENU}', menu)
        members = {member['FAT_path']: member['sha256'] for member in manifest['FAT_members']}
        old_menu = checked(menu, members.pop(MENU)).read_text()
        original_settings = tomllib.loads(old_menu)
        if len(original_settings['entry']) != 1 or original_settings['entry'][0]['args'] != old_args or old_menu.count(old_args) != 1:
            sys.exit('The original v371 menu differs from its manifest')
        menu.write_text(old_menu.replace(old_args, short_args))
        original_settings['entry'][0]['args'] = short_args
        run('mcopy', '-o', '-i', fat, menu, f'::/{MENU}')
        readback = scratch / 'readback.toml'
        run('mcopy', '-i', fat, f'::/{MENU}', readback)
        if tomllib.loads(readback.read_text()) != original_settings:
            sys.exit('Unexpected change in FAT menu readback')
        for name, (member, sha) in enumerate(members.items()):
            target = scratch / str(name)
            run('mcopy', '-i', fat, f'::/{member}', target)
            checked(target, sha)
            if member == 'EFI/UniXNU/Payloads/kernel.macho':
                shutil.copyfile(target, files['kernel.macho'])

    run(sys.executable, '-B', packer, '--fd', fd, '--ramdisk', fat, '--output', files['boot.img'])
    checked(files['boot.img'].parent / 'shim-scratch/shim.bin', SHIM_SHA)
    report = dict(kernel_args=short_args, input_manifest_sha256=verified_sha,
                  root_sha256=manifest['root']['sha256'], device_ready=False)
    payload.paths(ctx)[2].write_text(json.dumps(report, indent=2) + '\n')
    package = dict(device='zorn', os_profile=PROFILE, configuration=ctx.config_name,
                   upstream_revision=revision, kernel_command_line_bytes=len(short_args),
                   input_manifest_sha256=verified_sha, root_sha256=report['root_sha256'],
                   removed_argument=REMOVED, device_ready=False,
                   outputs={name: dict(bytes=path.stat().st_size, sha256=sha256_file(path)) for name, path in files.items()})
    pending = out / '.package.manifest.pending.json'
    pending.write_text(json.dumps(package, indent=2) + '\n')
    pipeline.verify(ctx, files, pending)
    pending.rename(out / 'package.manifest.json')


if __name__ == '__main__':
    main()

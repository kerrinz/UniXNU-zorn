#!/usr/bin/env python3
"""Build and pack the pinned 23G90 ZORN arm64e source profile for UniXNU release."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import tomllib


DEVICE = Path(__file__).resolve().parents[1]
PROFILE = DEVICE / 'profiles/os/ios-26.6.2-23G90/native-release.json'
REFERENCE = DEVICE / 'docs/evidence/k80-ft3683-v371-early-smmu-cdc-offline-2026-11-19.json'
MENU_PATH = 'EFI/UniXNU/unixnu.toml'
KERNEL_PATH = 'EFI/UniXNU/Payloads/kernel.macho'
OLD_ARGUMENT = 'zorn26_gpu_provider_claim=1'
PACKER_SHA = 'aca8cbfeff08c4535a5f868b8155939e2bdbf1b397aa09397b50f28cedeebb2d'


def read_json(path):
    return json.loads(path.read_bytes())


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def require_hash(path, expected):
    if sha256(path) != expected:
        raise ValueError(f'input digest differs: {path}')
    return path


def tree_digest(tree):
    digest = hashlib.sha256()
    for entry in sorted(tree.rglob('*')):
        if entry.name == '.DS_Store':
            continue
        if entry.is_symlink():
            digest.update(f'L {entry.relative_to(tree)} {entry.readlink()}\n'.encode())
        elif entry.is_file():
            digest.update(f'F {entry.relative_to(tree)} {sha256(entry)}\n'.encode())
    return digest.hexdigest()


def checked(command, *, cwd=None, env=None, log=None):
    if log is None:
        subprocess.run(command, cwd=cwd, env=env, check=True)
        return
    with log.open('wb') as stream:
        result = subprocess.run(command, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        tail = log.read_text(errors='replace').splitlines()[-12:]
        raise ValueError(f'command failed ({result.returncode}), {log}\n' + '\n'.join(tail))


def new_output_paths(arguments, object_file):
    # Archived recipes often repeat -MF. Replace all output arguments before running Clang.
    outputs = {'-o': object_file, '-MF': object_file.with_suffix('.d'),
               '-MJ': object_file.with_suffix('.json')}
    for index, option in enumerate(arguments[:-1]):
        if option in outputs:
            arguments[index + 1] = str(outputs[option])


class NativeBuild:
    def __init__(self, inputs, work, jobs):
        self.plan = read_json(PROFILE)
        if self.plan['schema'] != 1 or jobs < 1:
            raise ValueError('invalid native release plan or job limit')
        self.inputs = inputs
        self.work = work
        self.jobs = jobs
        self.scratch = work / 'kernel/native-build'
        self.source = self.scratch / 'source'
        self.objects = self.scratch / 'obj26'
        self.support = self.scratch / 'kernel-support'
        self.components = self.scratch / 'components'
        self.old = self.plan['recorded_workspace']
        self.base = self.old + '/' + self.plan['base']
        self.transforms = {
            self.old + '/' + self.plan['source']: self.source,
            self.base + '/obj26': self.objects,
            self.base + '/kernel-support': self.support,
            self.old + '/' + self.plan['ho'] + '/kernel-support': self.support,
            self.old: self.inputs,
        }
        self.pattern = re.compile('|'.join(map(re.escape, self.transforms)))

    def rebase(self, text):
        return self.pattern.sub(lambda match: str(self.transforms[match[0]]), text)

    def input_file(self, path):
        path = self.inputs / path
        if not path.resolve().is_relative_to(self.inputs):
            raise ValueError(f'private input leaves its root: {path}')
        return path

    def recipe(self, name):
        return read_json(self.input_file(self.plan['files'][name]))

    def verify_inputs(self):
        if subprocess.check_output(['xcodebuild', '-version'], text=True).splitlines() != [
            'Xcode 27.0', 'Build version 27A266a',
        ]:
            raise ValueError('23G90 requires the recorded Xcode 27.0 (27A266a) SDK/toolchain')
        for path, digest in self.plan['pinned'].items():
            require_hash(self.input_file(path), digest)
        for path, digest in self.plan['trees'].items():
            if tree_digest(self.input_file(path)) != digest:
                raise ValueError(f'private source tree differs: {path}')

    def build_support(self):
        include = self.support / 'include/os'
        include.mkdir(parents=True)
        header = self.recipe('firehose_header')
        command = [self.rebase(arg) for arg in header['arguments']]
        result = subprocess.run(command, capture_output=True)
        if result.returncode != header['returncode'] or hashlib.sha256(result.stdout).hexdigest() != header['sha256']:
            raise ValueError('firehose generated header differs from the recorded source recipe')
        (include / 'firehose_buffer_private.h').write_bytes(result.stdout)
        dispatch = Path(command[-1]).parent.parent
        shutil.copyfile(dispatch / 'src/firehose/firehose_types.defs', include / 'firehose_types.defs')
        for name in ('firehose', 'pthread'):
            for index, recipe in enumerate(self.recipe(name)):
                checked([self.rebase(arg) for arg in recipe['arguments']], cwd=self.support,
                        log=self.support / f'{name}-{index}.log')

    def build_core(self):
        self.source.parent.mkdir(parents=True)
        checked(['/bin/cp', '-cR', self.input_file(self.plan['source']), self.source])
        self.components.mkdir()
        self.build_support()
        recipe = self.recipe('build_command')
        command = [self.rebase(arg) for arg in recipe['arguments']]
        command[command.index('-j4')] = f'-j{self.jobs}'
        for index, arg in enumerate(command):
            key = arg.partition('=')[0]
            if key in ('SYMROOT', 'DSTROOT'):
                command[index] = f'{key}={self.scratch / key.lower()}'
        write_json(self.scratch / 'build-command.json', command)
        env = {**os.environ, 'XNU_AVAILABILITY_PL': self.rebase(recipe['XNU_AVAILABILITY_PL'])}
        checked(command, env=env, log=self.scratch / 'build.log')
        assym = self.objects / 'DEVELOPMENT_ARM64_ZORN/osfmk/DEVELOPMENT/assym.s'
        if not re.search(r'^#define PGSHIFT 14$', assym.read_text(), re.MULTILINE):
            raise ValueError('generated XNU code lacks the 16 KiB ZORN CPU page configuration')

    def compile_component(self, number, old_obj, name):
        recipe = read_json(self.input_file(name))
        args = recipe.get('arguments') or recipe.get('argv') or recipe.get('command')
        if not isinstance(args, list) or '-c' not in args or args.count('-o') != 1:
            raise ValueError(f'not a compile-only recipe: {name}')
        output = self.components / f'{number:04d}-{Path(old_obj).name}'
        args = [self.rebase(arg) for arg in args]
        if '-MF' not in args:
            args.extend(['-MD', '-MF', str(output.with_suffix('.d'))])
        new_output_paths(args, output)
        for index, flag in enumerate(args[:-1]):
            if flag == '-ivfsoverlay':
                overlay = output.with_name(f'{output.name}.{index}.vfs.json')
                overlay.write_text(self.rebase(Path(args[index + 1]).read_text()))
                args[index + 1] = str(overlay)
        directory = self.rebase(recipe.get('directory') or recipe.get('cwd') or self.old)
        write_json(output.with_name(output.name + '.command.json'), {'arguments': args, 'cwd': directory})
        checked(args, cwd=directory, log=output.with_suffix('.log'))
        return output

    def verify_component_headers(self):
        dependencies = tuple(self.components.glob('*.d'))
        if len(dependencies) != len(self.plan['recipes']):
            raise ValueError('a board compile did not record its header dependencies')
        for dep in dependencies:
            contents = dep.read_text().replace('\\\n', ' ').partition(':')[2]
            for name in shlex.split(contents):
                path = Path(name)
                if path.is_relative_to(self.inputs) and not path.is_relative_to(self.scratch):
                    relative = path.relative_to(self.inputs).as_posix()
                    if relative not in self.plan['pinned'] and not any(
                        relative.startswith(tree + '/') for tree in self.plan['trees']
                    ):
                        raise ValueError(f'unpinned private header in {dep.name}: {relative}')

    def link(self):
        base = {}
        for entry in self.recipe('base_objects'):
            base.setdefault(entry['sha256'], []).append(entry['path'])
        rows = self.recipe('link_inputs')

        def rebuild(item):
            number, row = item
            path = row['path']
            local = path.removeprefix(self.old + '/')
            recipe = self.plan['recipes'].get(local)
            if recipe:
                return self.compile_component(number, path, recipe)
            choices = base[row['sha256']]
            basename = re.sub(r'^(\d+[-_])+', '', Path(path).name)
            source = next((guess for guess in choices if Path(guess).name == basename), choices[0])
            if not source.startswith(self.base + '/obj26/'):
                raise ValueError(f'base object lacks a fresh native build path: {source}')
            return Path(self.rebase(source))

        with ThreadPoolExecutor(max_workers=self.jobs) as pool:
            objects = list(pool.map(rebuild, enumerate(rows)))
        self.verify_component_headers()
        if len(set(objects)) != 1400 or any(not p.is_file() or not p.is_relative_to(self.scratch) for p in objects):
            raise ValueError('the full link must consume 1400 fresh local objects')
        replacements = dict(zip((row['path'] for row in rows), objects, strict=True))
        args = self.recipe('link_command')['arguments']
        filelist = self.input_file(self.plan['files']['filelist']).read_text().splitlines()
        direct = [arg for arg in args if arg in replacements]
        if len(filelist) + len(direct) != len(rows) or set(filelist + direct) != replacements.keys():
            raise ValueError('file list and command do not cover the planned full link')
        fresh_list = self.scratch / 'link.filelist'
        fresh_list.write_text(''.join(f'{replacements[path]}\n' for path in filelist))
        args = [str(replacements.get(value, self.rebase(value))) for value in args]
        args[args.index('-filelist') + 1] = str(fresh_list)
        kernel = self.work / 'kernel/kernel.macho'
        args[args.index('-o') + 1] = str(kernel)
        args = [f'-Wl,-map,{self.scratch}/kernel.map' if arg.startswith('-Wl,-map,') else arg for arg in args]
        write_json(self.scratch / 'link-command.json', args)
        checked(args, cwd=self.scratch, log=self.scratch / 'link.log')
        with kernel.open('rb') as stream:
            header = struct.unpack('<IIII', stream.read(16))
        if header != (0xfeedfacf, 0x100000c, 0xc0000002, 2):
            raise ValueError(f'not an arm64e.kernel executable: {header}')
        if subprocess.check_output(['xcrun', 'nm', '-u', kernel]).strip():
            raise ValueError('fresh K80 kernel has unresolved symbols')
        write_json(self.work / 'kernel/native-inputs.json', {
            'profile': 'ios-26.6.2-23G90', 'cpu_page_bytes': 16384, 'objects': len(objects),
            'rebuilt_components': len(self.plan['recipes']), 'native_base_objects': len(objects) - len(self.plan['recipes']),
            'source_plan_sha256': sha256(PROFILE), 'kernel_sha256': sha256(kernel),
            'undefined_symbols': 0, 'device_ready': False,
            'link_objects': {str(p.relative_to(self.scratch)): sha256(p) for p in objects},
        })


def pack(inputs, work, uefi):
    profile = read_json(PROFILE)
    kernel = work / 'kernel/kernel.macho'
    receipt = read_json(work / 'kernel/native-inputs.json')
    require_hash(kernel, receipt['kernel_sha256'])
    v371 = read_json(REFERENCE)
    historical = Path(v371['exact_package']['path']).relative_to(profile['recorded_workspace'])
    verified = require_hash(inputs / historical, v371['exact_package']['sha256'])
    pins = read_json(verified)
    fd = require_hash(verified.parent / 'inputs/firmware.fd', pins['pins']['FD']['sha256'])
    packer = require_hash(uefi / 'scripts/package-zorn-boot.py', PACKER_SHA)
    payload_dir = work / 'payload'
    payload_dir.mkdir()
    fat = payload_dir / 'payload.img'
    menu_dir = verified.parent / 'FAT-readback'
    with tempfile.TemporaryDirectory(dir=payload_dir) as temp:
        temp = Path(temp)
        expected = {}
        checked(['mformat', '-C', '-F', '-c', '1', '-T', '393216', '-v', 'ZORNESP',
                 '-N', '53484e47', '-i', fat, '::'])
        for directory in ('EFI', 'EFI/BOOT', 'EFI/UniXNU', 'EFI/UniXNU/Drivers', 'EFI/UniXNU/Payloads'):
            checked(['mmd', '-i', fat, f'::/{directory}'])
        for member in pins['FAT_members']:
            path = member['FAT_path']
            source = kernel
            if path != KERNEL_PATH:
                source = require_hash(menu_dir / Path(member['readback']).name, member['sha256'])
            if path == MENU_PATH:
                menu = source.read_text()
                original = pins['boot_args']
                args = original.split(' ')
                if menu.count(original) != 1 or args.count(OLD_ARGUMENT) != 1:
                    raise ValueError('recorded K80 boot args do not match the original menu')
                args.remove(OLD_ARGUMENT)
                boot_args = ' '.join(args)
                if len(boot_args.encode('ascii')) >= 1000:
                    raise ValueError('K80 boot args exceed the UniXNU verifier budget')
                source = temp / 'unixnu.toml'
                source.write_text(menu.replace(original, boot_args))
                if tomllib.loads(source.read_text())['entry'][0]['args'] != boot_args:
                    raise ValueError('new FAT menu does not carry the recorded K80 boot args')
            checked(['mcopy', '-i', fat, source, f'::/{path}'])
            expected[path] = sha256(source)
        for index, (path, digest) in enumerate(expected.items()):
            readback = temp / str(index)
            checked(['mcopy', '-i', fat, f'::/{path}', readback])
            require_hash(readback, digest)

    # BootShim and the board DXE consume these markers in the FAT boot code area.
    markers = struct.pack('<8sII8sII', b'ZORNGHWD', 1, 0xfffffffe, b'ZORNTPWR', 1, 0xfffffffe)
    with fat.open('r+b') as volume:
        header = volume.read(512)
        sector_size, _, reserved = struct.unpack_from('<HBH', header, 0x0b)
        backup, = struct.unpack_from('<H', header, 0x32)
        if sector_size != 512 or header[-2:] != b'\x55\xaa' or not 0 < backup < reserved:
            raise ValueError('invalid FAT32 boot record for the K80 handoff markers')
        for offset in (0, backup * sector_size):
            volume.seek(offset + 0x180)
            volume.write(markers)
            volume.seek(offset + 0x1be)
            volume.write(bytes(64))

    boot = work / 'boot/boot.img'
    checked([sys.executable, '-B', packer, '--fd', fd, '--ramdisk', fat, '--output', boot])
    write_json(payload_dir / 'payload.json', {
        'kernel_args': boot_args, 'members': expected, 'fd_sha256': sha256(fd),
        'root_sha256': pins['root']['sha256'], 'parent_manifest_sha256': sha256(verified),
        'native_inputs_sha256': sha256(work / 'kernel/native-inputs.json'), 'device_ready': False,
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('build', 'pack'))
    parser.add_argument('--inputs', required=True, type=Path)
    parser.add_argument('--work', required=True, type=Path)
    parser.add_argument('--uefi', required=True, type=Path)
    parser.add_argument('--jobs', required=True, type=int)
    args = parser.parse_args()
    try:
        if args.stage == 'build':
            native = NativeBuild(args.inputs.resolve(), args.work.resolve(), args.jobs)
            native.verify_inputs()
            native.build_core()
            native.link()
        else:
            pack(args.inputs.resolve(), args.work.resolve(), args.uefi.resolve())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))


if __name__ == '__main__':
    main()

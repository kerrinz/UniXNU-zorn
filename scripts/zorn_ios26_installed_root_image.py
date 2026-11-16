"""Host-only packaging of the matching K80 installed-UFS-root boot candidate.

This entry cannot contact a phone, claim a trial, install a boot entry or boot.
It reuses the reviewed packer; its fastboot-only carrier is not a flash image
policy. The OS image remains on UFS and is never embedded as a RAM root.
"""
import argparse
import gzip
import hashlib
import io
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / 'out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90'
KERNEL_SHA = '0d867627c845212405f5e341bc444fe2e79feeac51b784b64879c9a68f99c266'
FAT_SHA = 'bc580406f0a41c88ad75fd80db4cf6fefe49153e0bd30e9ea9188108cf894b69'
FD_SHA = '1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab'
ROOT_SHA = 'b56dafe874ae86e84929e08317805b6f1d969973c2399b394c3f1de093aea592'
ARGS = ('rd=md0 -v keepsyms=1 houji_native_root=1 zorn26_root=1 '
        'zorn26_installed_root_trial=1 zorn_wdt=1 zorn26_prearmed_recovery=1 '
        'zorn26_trial_seconds=300')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def check_inputs():
    fat_proof = STAGE / 'k80-installed-root-fat26/verified.json'
    kernel_proof = STAGE / 'k80-installed-root-terminal26/verified.json'
    fd_proof = STAGE / 'k80-platform-fd26/verified.json'
    install = STAGE / ('k80-persistent-install26/'
                       'explicit-resend-fa16eca8a2414de48cf9adb82ef6f70f/run/result.json')
    f, k, d, actual = map(load, [fat_proof, kernel_proof, fd_proof, install])
    if (actual.get('installed') is not True or
            actual.get('phase') != 'root-installed-full-readback-verified' or
            actual.get('readback') != {'bytes': 34359738368, 'sha256': ROOT_SHA} or
            actual.get('protected_metadata_and_fences_unchanged') is not True):
        raise ValueError('actual exact installed-root readback evidence missing')
    files = {'FAT': Path(f['FAT']['path']), 'kernel': Path(k['kernel']['output']),
             'fd': Path(d['FD']['path']), 'fat_proof': fat_proof,
             'kernel_proof': kernel_proof, 'fd_proof': fd_proof,
             'installed_readback': install,
             'fixed_builder': Path(__file__).with_name('build-zorn-debug.py'),
             'entry': Path(__file__), 'packer': ROOT / 'uefi-zorn/scripts/package-zorn-boot.py',
             'shim_source': ROOT / 'uefi-zorn/BootShim/BootShim.S'}
    for role, expected in [('FAT', FAT_SHA), ('kernel', KERNEL_SHA), ('fd', FD_SHA)]:
        if files[role].is_symlink() or sha(files[role]) != expected:
            raise ValueError('current input differs: ' + role)
    if (f.get('root_image_sha256') != ROOT_SHA or f.get('root_OS_image_in_FAT') is not False or
            f.get('root_OS_from_UFS') is not True or f.get('boot_args') != ARGS or
            d.get('old_DarwinBoot_absent_from_actual_FFS') is not True or
            k.get('zero_undefined') is not True):
        raise ValueError('current source/link/root selection proofs differ')
    members = f['files']
    expected = {'EFI/BOOT/BOOTAA64.EFI', 'EFI/UniXNU/Drivers/DarwinBoot26.efi',
                'EFI/UniXNU/Payloads/kernel.macho', 'EFI/UniXNU/Payloads/kernel.macho.adt',
                'EFI/UniXNU/unixnu.toml'}
    if len(members) != 5 or {row['FAT_path'] for row in members} != expected:
        raise ValueError('exact five loader/kernel/config files required; no OS image')
    for row in members:
        source, readback = Path(row['source']), Path(row['readback'])
        if sha(source) != row['sha256'] or sha(readback) != row['sha256']:
            raise ValueError('loader member changed: ' + row['FAT_path'])
        files['member_' + source.name] = source
    menu = tomllib.loads(files['member_unixnu.toml'].read_text())
    if (len(menu.get('entry', [])) != 1 or menu['entry'][0].get('args') != ARGS or
            menu['entry'][0].get('ramdisk') or menu['boot'].get('connect_all') is not False or
            menu['kits'].get('autoload') is not False):
        raise ValueError('explicit bounded installed-root selection required')
    code = files['kernel'].read_bytes()
    if struct.unpack_from('<3I', code) != (0xfeedfacf, 0x100000c, 0xc0000002):
        raise ValueError('actual arm64e.kernel required')
    at, versions = 32, []
    for _ in range(struct.unpack_from('<I', code, 16)[0]):
        cmd, size = struct.unpack_from('<II', code, at)
        if size < 8 or at + size > len(code):
            raise ValueError('invalid kernel commands')
        if cmd == 0x32:
            versions.append(struct.unpack_from('<III', code, at + 8))
        at += size
    if versions != [(2, 26 << 16, 27 << 16)]:
        raise ValueError('IOS26 runtime/SDK27 build metadata required')
    return files, members


def prepare_loader_fat(out, files, members):
    """Reuse the existing K80 relocation-slot producer before packaging.

    Hardware ADTs carry nominal DRAM; the actual DarwinBoot parser instead
    consumes zero relocation slots. Only the loader may later fill them from
    a real allocation and secondary trampoline. This prepares no addresses.
    """
    stage = ROOT / 'out/zorn/ios26-feasibility-20261107'
    producer = stage / 'source/os/ios26/boot/prepare_adt.py'
    codec = stage / 'source/common/boot/ios26_adt.py'
    spec = importlib.util.spec_from_file_location('zorn_existing_adt_prepare', producer)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = files['member_kernel.macho.adt'].read_bytes()
    normalized = module.prepare(original)
    old, new = module.parse(original), module.parse(normalized)

    def flatten(node, prefix=''):
        here = prefix + '/' + node.name
        result = {here + '/' + key: (flags, value) for key, flags, value in node.properties}
        for child in node.children:
            result.update(flatten(child, here))
        return result

    before, after = flatten(old), flatten(new)
    delta = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    expected = ['/device-tree/chosen/' + key
                for key in ['dram-base', 'dram-size', 'hakios,secondary-entry']]
    if delta != sorted(expected):
        raise ValueError('loader preparation must change only the three known relocation slots')
    chosen = new.child('chosen')
    if (any(chosen.get(key) != bytes(8) for key in ['dram-base', 'dram-size', 'hakios,secondary-entry']) or
            chosen.get('darwinboot-memory-size') != struct.pack('<Q', 8 * 1024**3) or
            chosen.get('zorn26,root-image-sha256') != bytes.fromhex(ROOT_SHA) or
            module.prepare(normalized) != normalized):
        raise ValueError('existing K80 allocation request/root identity/zero-slot contract differs')
    adt = out / 'kernel.loader-bound.UNSELECTED.adt'
    adt.write_bytes(normalized)
    fat = out / 'loader-bound-files.UNSELECTED.fat'
    subprocess.run(['/bin/cp', '-c', str(files['FAT']), str(fat)], check=True)
    if fat.stat().st_ino == files['FAT'].stat().st_ino:
        raise ValueError('independent mutable FAT inode required')
    command = ['/opt/homebrew/bin/mcopy', '-o', '-i', str(fat), str(adt),
               '::/EFI/UniXNU/Payloads/kernel.macho.adt']
    (out / 'normalize-FAT-command.json').write_text(json.dumps(command, indent=2) + '\n')
    subprocess.run(command, check=True)
    readback = out / 'loader-bound-readback'
    readback.mkdir()
    rows = []
    for index, row in enumerate(members):
        source = adt if row['FAT_path'].endswith('/kernel.macho.adt') else Path(row['source'])
        copied = readback / (str(index) + '-' + source.name)
        subprocess.run(['/opt/homebrew/bin/mcopy', '-i', str(fat),
                        '::/' + row['FAT_path'], str(copied)], check=True)
        if copied.read_bytes() != source.read_bytes():
            raise ValueError('normalized FAT member readback differs: ' + row['FAT_path'])
        rows.append({'FAT_path': row['FAT_path'], 'source': str(source),
                     'sha256': sha(source), 'bytes': source.stat().st_size,
                     'readback': str(copied)})
    proof = {'source_ADT': str(files['member_kernel.macho.adt']),
             'source_ADT_sha256': sha(files['member_kernel.macho.adt']),
             'normalized_ADT': str(adt), 'normalized_ADT_sha256': sha(adt),
             'existing_producer': str(producer), 'existing_producer_sha256': sha(producer),
             'codec': str(codec), 'codec_sha256': sha(codec), 'changed_properties': delta,
             'slots_zero_not_addresses': True, 'allocation_request_8GiB_unchanged': True,
             'root_window_digest_board_and_other_properties_unchanged': True,
             'idempotent': True, 'phone_accessed': False}
    (out / 'loader-binding.json').write_text(json.dumps(proof, indent=2) + '\n')
    updated = dict(files, original_FAT=files['FAT'], original_ADT=files['member_kernel.macho.adt'],
                   FAT=fat, loader_slot_producer=producer, loader_ADT_codec=codec)
    updated['member_kernel.macho.adt'] = adt
    return updated, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ios26-installed-root-image', type=Path, required=True,
                        help='new independent output directory under the iOS26 stage')
    args = parser.parse_args()
    out = args.ios26_installed_root_image
    if out.is_symlink() or not out.resolve().is_relative_to(STAGE) or out.exists():
        raise ValueError('new independent output directory required')
    files, members = check_inputs()
    out.mkdir(parents=True)
    files, members = prepare_loader_fat(out, files, members)
    archive = out / 'inputs'
    archive.mkdir()
    pins = {}
    # Independent inodes: never hard-link mutable source, objects or recipes.
    for role, source in files.items():
        target = archive / (role + '-' + source.name)
        subprocess.run(['/bin/cp', '-c', str(source), str(target)], check=True)
        if (source.stat().st_ino == target.stat().st_ino or sha(source) != sha(target)):
            raise ValueError('independent input archive differs: ' + role)
        pins[role] = {'path': str(source.resolve()), 'archive': str(target.resolve()),
                      'sha256': sha(target)}
    boot = out / 'boot.ZORN26-INSTALLED-UFS-ROOT.UNSELECTED.img'
    command = [sys.executable, str(files['packer']), '--fd', str(files['fd']),
               '--ramdisk', str(files['FAT']), '--output', str(boot)]
    (out / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    with (out / 'pack.stdout').open('wb') as stdout, (out / 'pack.stderr').open('wb') as stderr:
        subprocess.run(command, stdout=stdout, stderr=stderr, check=True)
    image = boot.read_bytes()
    size, ramdisk = struct.unpack_from('<II', image, 8)
    if (image[:8] != b'ANDROID!' or struct.unpack_from('<I', image, 40)[0] != 4 or
            ramdisk or len(image) != 4096 + ((size + 4095) & ~4095)):
        raise ValueError('invalid exact v4/no Android ramdisk carrier')
    with gzip.GzipFile(fileobj=io.BytesIO(image[4096:4096 + size])) as stream:
        raw = stream.read(256 * 1024**2 + 1)
    fd, fat = files['fd'].read_bytes(), files['FAT'].read_bytes()
    shim = (out / 'shim-scratch/shim.bin').read_bytes()
    if (len(raw) > 256 * 1024**2 or raw != shim + fd + fat or len(shim) != 4096 or
            raw[56:60] != b'ARM\x64' or
            struct.unpack_from('<QQ', raw, 8) != (0xA7100000, len(raw))):
        raise ValueError('unpacked current shim/FD/FAT mismatch')
    marker = b'ZORNGHWD' + struct.pack('<II', 1, 0xfffffffe)
    if any(fat[sector * 512 + 0x180:sector * 512 + 0x190] != marker for sector in (0, 6)):
        raise ValueError('both native WDT1 markers required')
    proof = {'status': 'matching-installed-UFS-root-carrier-built-host-only-unselected',
             'boot': {'path': str(boot.resolve()), 'sha256': sha(boot), 'bytes': len(image)},
             'pins': pins, 'FAT_members': members, 'boot_args': ARGS,
             'root_SHA256': ROOT_SHA, 'root_OS_on_UFS': True, 'root_OS_in_RAM': False,
             'loader_slot_binding': str(out / 'loader-binding.json'),
             'FAT_SHA256': sha(files['FAT']), 'ADT_SHA256': sha(files['member_kernel.macho.adt']),
             'kernel_SHA256': KERNEL_SHA, 'Android_ramdisk_bytes': 0,
             'unpacked_shim_FD_FAT_exact': True, 'watchdog_mode': 1,
             'trial_seconds': 300, 'allow_boot': False, 'ready': False,
             'permanent_boot_entry_installed': False, 'phone_accessed': False,
             'pending': ['fresh exact root-boot runner/admission/claim/BCB/Recovery closure',
                         'owner decision for this bounded boot scope; old claims are consumed',
                         'persistent boot-entry policy remains separate from UFS root installation'],
             'observability': 'existing panic text/RAM console only;Recovery timing is not root/GUI proof',
             'iOS26_persistent_Data_complete': False, 'GPU_or_Metal_qualified': False}
    (out / 'verified.json').write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps({k: proof[k] for k in ['status', 'boot', 'root_OS_in_RAM', 'ready']}))


if __name__ == '__main__':
    main()

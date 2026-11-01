"""One protected new-storage installation boot, called by the fixed runner."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
ADB = os.environ.get('UNIXNU_ADB', 'adb')
FASTBOOT = os.environ.get('UNIXNU_FASTBOOT', 'fastboot')
SERIAL = '92988a43'


def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()


def command(*args,timeout=20,binary=False):
    result = subprocess.run(list(map(str,args)),capture_output=True,timeout=timeout,check=True)
    return result.stdout if binary else (result.stdout+result.stderr).decode().strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--unixnu64-install-trial',type=Path,required=True)
    args = parser.parse_args()
    ready_path = args.unixnu64_install_trial.resolve()
    claim = ready_path.with_suffix('.claim.json')
    if claim.exists():
        raise RuntimeError('installation trial already consumed; no USB action')
    ready = json.loads(ready_path.read_text())
    if (ready['serial'] != SERIAL or ready['slot'] != 'a' or
        ready['storage_profile'] != 'unixnu64' or ready['timeout'] != 600 or
        ready['allow_boot'] is not True or ready['GPU_enabled'] is not False):
        raise RuntimeError('new-installation admission differs')
    current_path = ROOT/'out/zorn/unattended-active/current.json'
    current = json.loads(current_path.read_text())
    if current.get('active_run') or current.get('active_build') or current.get('runner_session'):
        raise RuntimeError('another run/build is active')
    base = ROOT/'out/zorn/dual-system-reinstall-20261101'
    image = Path(ready['image']).resolve()
    required = {str(image), str(Path(__file__).resolve()),
                str(Path(__file__).with_name('run-zorn-debug.py').resolve()),
                str(Path(__file__).with_name('read-zorn-log.py').resolve()),
                str(Path(__file__).with_name('install-zorn-unixnu64-data.py').resolve())}
    if not image.is_relative_to(base) or image.name != 'boot.img':
        raise RuntimeError('installation image must belong to this storage workspace')
    if (not required.issubset(ready['inputs']) or set(ready['archive']) != set(ready['inputs']) or
            not isinstance(ready['fresh_Data'], bool) or
            not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', ready['run_directory'])):
        raise RuntimeError('incomplete archive/source closure or invalid run directory; no USB action')
    for path,digest in ready['inputs'].items():
        if sha(path) != digest: raise RuntimeError('trial input changed: '+path)
    for path,row in ready['archive'].items():
        saved = Path(row['path'])
        if (row['sha256'] != ready['inputs'][path] or sha(saved) != row['sha256'] or
                saved.stat().st_ino == Path(path).stat().st_ino):
            raise RuntimeError('immutable input archive changed/shared inode')
    if sha(image) != ready['boot_sha256']: raise RuntimeError('boot digest differs')
    payload = image.with_name('payload.img')
    if str(payload) not in ready['inputs']:
        raise RuntimeError('protected FAT payload is not pinned; no USB action')
    with payload.open('rb') as stream:
        header = stream.read(512)
        backup = int.from_bytes(header[0x32:0x34], 'little')
        if len(header) != 512 or header[510:512] != b'\x55\xaa' or not 1 <= backup < 32:
            raise RuntimeError('invalid protected FAT header')
        stream.seek(backup*512); other = stream.read(512)
    watchdog = b'ZORNGHWD' + (1).to_bytes(4,'little') + (0xfffffffe).to_bytes(4,'little')
    touch = b'ZORNTPWR' + (1).to_bytes(4,'little') + (0xfffffffe).to_bytes(4,'little')
    for sector in (header, other):
        if sector[0x180:0x190] != watchdog:
            raise RuntimeError('independent watchdog mode1 marker missing; no USB action')
        if not ready['fresh_Data'] and sector[0x190:0x1a0] != touch:
            raise RuntimeError('retained touch handoff marker missing; no USB action')
    out = base/ready['run_directory']; out.mkdir(exist_ok=False)
    manifest = dict(serial=SERIAL,product='zorn',slot='a',image=str(image),
        sha256=sha(image),status='preparing',started=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        storage_profile='unixnu64',timeout_seconds=600,GPU_enabled=False,
        fresh_Data=ready['fresh_Data'],owner_scope='new dual-system iOS installation')
    def record(): (out/'run.json').write_text(json.dumps(manifest,indent=2)+'\n')
    record()
    if sys.platform == 'darwin' and Path('/usr/bin/caffeinate').is_file():
        subprocess.Popen(['/usr/bin/caffeinate','-i','-w',str(os.getpid())],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    spec = importlib.util.spec_from_file_location('unixnu64_install',Path(__file__).with_name('install-zorn-unixnu64-data.py'))
    storage = importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
    try:
        # This exact OrangeFox identity is accepted even when adb reports device.
        storage.boundaries()
        before = storage.read(storage.PARTITION,2291712,1)
        (out/'preboot-checkpoints.bin').write_bytes(before)
        misc_command = 'dd if=/dev/block/by-name/misc bs=4096 count=1 2>/dev/null'
        old = command(ADB,'-s',SERIAL,'exec-out',misc_command,binary=True)
        if len(old) != 4096: raise RuntimeError('short misc page')
        page = bytearray(old);page[:864] = bytes(864)
        page[:14] = b'boot-recovery\0';page[64:73] = b'recovery\n'
        if len(page) != 4096 or page[864:] != old[864:]: raise RuntimeError('BCB tail changed')
        (out/'misc-before.bin').write_bytes(old);(out/'recovery-bcb.bin').write_bytes(page)
        remote = '/tmp/unixnu64-recovery-bcb.bin'
        command(ADB,'-s',SERIAL,'push',out/'recovery-bcb.bin',remote)
        if command(ADB,'-s',SERIAL,'exec-out','cat',remote,binary=True) != page:
            raise RuntimeError('BCB tmpfs mismatch')
        command(ADB,'-s',SERIAL,'shell',f'dd if={remote} of=/dev/block/by-name/misc bs=4096 count=1 conv=notrunc')
        back = command(ADB,'-s',SERIAL,'exec-out',misc_command,binary=True)
        if back != page: raise RuntimeError('BCB full-page readback differs')
        (out/'misc-readback.bin').write_bytes(back)
        (out/'bcb.json').write_text(json.dumps(dict(tail_preserved=True,full_page_readback=True,
            before_sha256=hashlib.sha256(old).hexdigest(),after_sha256=hashlib.sha256(back).hexdigest()),indent=2)+'\n')
        command(ADB,'-s',SERIAL,'reboot','bootloader')
        deadline = time.monotonic()+30
        while True:
            try:
                product = command(FASTBOOT,'-s',SERIAL,'getvar','product',timeout=3)
                if 'product: zorn' in product: break
            except subprocess.SubprocessError: pass
            if time.monotonic() >= deadline: raise RuntimeError('no fastboot within30s')
            time.sleep(1)
        if 'current-slot: a' not in command(FASTBOOT,'-s',SERIAL,'getvar','current-slot'):
            raise RuntimeError('slot changed')
        if '0x1000000000' not in command(FASTBOOT,'-s',SERIAL,'getvar','partition-size:unixnu'):
            raise RuntimeError('unixnu partition size changed')
        if sha(image) != ready['boot_sha256']: raise RuntimeError('image changed before boot')
        with claim.open('x') as stream:
            json.dump(dict(status='consumed-no-repeat',boot_sha256=sha(image),run=str(out)),stream)
        manifest['status'] = 'boot-attempting';record()
        current = json.loads(current_path.read_text());current['active_run'] = str(out)
        current['active_phase'] = 'unixnu64-installation-boot'
        current_path.write_text(json.dumps(current,indent=2,ensure_ascii=False)+'\n')
        started = time.monotonic();deadline = started+600
        output = command(FASTBOOT,'-s',SERIAL,'boot',image,timeout=60)
        (out/'fastboot.txt').write_text(output+'\n');manifest['fastboot_accepted'] = True;record()
        while True:
            try:
                fox = command(ADB,'-s',SERIAL,'shell','getprop','ro.orangefox.boot',timeout=3)
                if fox == '1': break
            except subprocess.SubprocessError: pass
            if time.monotonic() >= deadline:
                raise RuntimeError('no Recovery within600s; STOP device operations; physical assistance required')
            time.sleep(2)
        storage.boundaries()
        after = storage.read(storage.PARTITION,2291712,1)
        (out/'checkpoints.bin').write_bytes(after)
        changed = after != before
        manifest.update(status='recovered',elapsed_seconds=time.monotonic()-started,
            kernel_log_changed=changed,kernel_log_sha256=hashlib.sha256(after).hexdigest(),
            completed=time.strftime('%Y-%m-%dT%H:%M:%S%z'))
        if changed:
            result = subprocess.run([sys.executable,str(Path(__file__).with_name('read-zorn-log.py')),
                '--block',str(out/'checkpoints.bin'),'--tail','100'],capture_output=True,text=True,timeout=30)
            (out/'checkpoints.txt').write_text(result.stdout+result.stderr)
            manifest['decoder_returncode'] = result.returncode
        print(json.dumps(manifest,indent=2),flush=True)
    except Exception as error:
        manifest.update(status='failed',error=str(error));raise
    finally:
        record()
        current = json.loads(current_path.read_text());current['active_run'] = None
        current['active_phase'] = 'unixnu64-installation-'+manifest['status']
        current_path.write_text(json.dumps(current,indent=2,ensure_ascii=False)+'\n')

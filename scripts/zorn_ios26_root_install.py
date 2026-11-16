"""Install the exact iOS26 HFSX root into its bounded unixnu UFS window.

The fixed runner is the execution entry. --check is entirely host-side.
This installs storage only: no fastboot boot, boot-partition writes, mounting,
slot changes, Data initialization, reboot, or automatic recovery/retry.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import selectors
import shutil
import socket
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-persistent-install26'
CURRENT = ROOT / 'out/zorn/unattended-active/current.json'
SERIAL = '92988a43'
PART = '/dev/block/by-name/unixnu'
FIRST = 6291712
BLOCKS = 8388608
BYTES = BLOCKS * 4096
RESERVE = 4 * 1024**3
SCOPE = 'K80-persistent-iOS26-current-root-update-v5'


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def save(path, data, exclusive=False):
    with Path(path).open('x' if exclusive else 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())


def validate(path, execute=False):
    path = Path(path).resolve()
    if not path.is_relative_to(BASE) or path.is_symlink():
        raise ValueError('independent exact installation manifest required')
    d = load(path)
    required = dict(scope=SCOPE, serial=SERIAL, product='zorn', slot='a',
                    partition=PART, relative_first_lba=FIRST, blocks=BLOCKS,
                    image_bytes=BYTES, timeout_seconds=3600, retries=0,
                    Android_preserved=True, Recovery_preserved=True,
                    accepted_recovery='twrp-or-orangefox',
                    old_Data_preserved=True, root_in_RAM=False,
                    native_execution=False, boot_partition_writes=False,
                    automatic_boot=False, complete_preimage_required=False,
                    protected_metadata_backup_required=True,
                    target_window_backup='retained-host-image-no-new-phone-backup',
                    adb_server_port=5039, adb_one_device=SERIAL,
                    adb_libusb=False,
                    existing_server_only=True,
                    allow_fresh_private_server_when_absent=False,
                    pending_writer_wait_seconds=0,
                    complete_readback_required=True)
    if any(type(d.get(k)) is not type(v) or d[k] != v for k, v in required.items()):
        raise ValueError('exact bounded persistent root installation scope differs')
    roles = {'image', 'owner', 'descriptor', 'runner', 'entry', 'adb',
             'primary_GPT', 'backup_GPT', 'Data', 'root_manifest',
             'host_adb_proof', 'recovery_identity', 'window_review',
             'retained_prior_image', 'prior_install_receipt'}
    if set(d.get('pins', {})) != roles:
        raise ValueError('missing installation protection/input pins')
    for name, row in d['pins'].items():
        p = Path(row['path'])
        if not p.is_absolute() or p.is_symlink() or not p.is_file() or sha(p) != row['sha256']:
            raise ValueError('changed installation input: ' + name)
        archive = Path(row['archive'])
        if (not archive.is_absolute() or archive.is_symlink() or not archive.is_file() or
                archive.stat().st_ino == p.stat().st_ino or sha(archive) != row['sha256']):
            raise ValueError('changed/shared installation archive: ' + name)
    if Path(d['pins']['entry']['path']) != Path(__file__).resolve():
        raise ValueError('maintained installer required')
    if Path(d['pins']['runner']['path']) != Path(__file__).with_name('run-zorn-debug.py'):
        raise ValueError('fixed runner required')
    if Path(d['pins']['recovery_identity']['path']) != Path(__file__).with_name('zorn_recovery_identity.py'):
        raise ValueError('maintained Recovery identity helper required')
    current = load(CURRENT)
    if (any(current.get(k) for k in ('active_run','active_build','runner_session','stop_device_operations')) or
            current.get('gpu_discovery', {}).get('current_mode') == 'unattended-offline-no-phone'):
        raise ValueError('device operation unavailable; no USB')
    image = Path(d['pins']['image']['path'])
    if image.stat().st_size != BYTES:
        raise ValueError('32GiB exact HFSX image required')
    with image.open('rb') as f:
        f.seek(1024)
        if f.read(2) != b'HX':
            raise ValueError('actual HFSX volume header required')
    descriptor = load(d['pins']['descriptor']['path'])
    if descriptor['partition'] != {
            'name': 'unixnu', 'linux_by_name': PART,
            'type_guid': '0fc63daf-8483-4772-8e79-3d69d8477de4',
            'unique_guid': 'b279731f-ccad-4ef5-a8b7-e7440cd08de3',
            'first_lba': 47271680, 'last_lba': 64048895,
            'lba_bytes': 4096, 'bytes': 68719476736}:
        raise ValueError('protected partition geometry differs')
    if not (4194304 + 2097217 < FIRST and FIRST + BLOCKS <= 16777216):
        raise ValueError('root overlaps protected Data or partition edge')
    owner = load(d['pins']['owner']['path'])
    if (owner.get('current_root_update_authorized') is not True or owner.get('serial') != SERIAL or
            owner.get('image_sha256') != d['pins']['image']['sha256'] or
            owner.get('accepted_recovery') != 'twrp-or-orangefox'):
        raise ValueError('actual current-root instruction required')
    review = load(d['pins']['window_review']['path'])
    expected_window = dict(relative_first_lba=FIRST,blocks=BLOCKS,image_bytes=BYTES,
                           image_sha256=d['pins']['image']['sha256'],partition_unique_guid=descriptor['partition']['unique_guid'])
    if any(type(review.get(k)) is not type(v) or review[k] != v for k,v in expected_window.items()):
        raise ValueError('new-image/window review differs')
    header=review.get('header', {})
    if not header.get('path') or sha(header['path'])!=header.get('sha256'):
        raise ValueError('compiled root-window header changed')
    previous = load(d['pins']['prior_install_receipt']['path'])
    if (previous.get('installed') is not True or
            previous.get('readback') != dict(bytes=BYTES,sha256=d['pins']['retained_prior_image']['sha256'])):
        raise ValueError('retained historical root/readback receipt differs')
    adb_proof = load(d['pins']['host_adb_proof']['path'])
    if (adb_proof.get('archive_sha1_matched') is not True or
            adb_proof.get('adb_sha256') != d['pins']['adb']['sha256'] or
            adb_proof.get('one_device_server_option_present') is not True or
            '37.0.1-' not in adb_proof.get('version_output', '')):
        raise ValueError('independent verified stable native-USB host tool required')
    if execute and d.get('execution_ready') is not True:
        raise ValueError('installation is not ready; no device access')
    return d


class Recovery:
    def __init__(self, d, out):
        self.d, self.out, self.n = d, out, 0
        self.adb = d['pins']['adb']['path']
        self.deadline = time.monotonic() + d['timeout_seconds']

    def wait_completion(self, process, phase):
        while process.poll() is None:
            remaining = self.deadline-time.monotonic()
            if remaining <= 0:
                raise RuntimeError(phase+' overall deadline expired;no further device operations')
            try:
                process.wait(timeout=min(30, remaining))
            except subprocess.TimeoutExpired:
                print('same '+phase+' process remains live;waiting within overall deadline', flush=True)

    def start(self, argv, **kw):
        if time.monotonic() >= self.deadline:
            raise RuntimeError('installation deadline expired; no more device commands')
        self.n += 1
        if self.d.get('existing_server_only'):
            if argv == ['start-server']:
                if not self.d.get('allow_fresh_private_server_when_absent'):
                    raise ValueError('verification cannot start or replace a server')
                args = [self.adb, '-P', '5039', '--one-device', SERIAL, 'start-server']
            else:
                args = [self.adb, '-H', '127.0.0.1', '-P', '5039', '-s', SERIAL, *argv]
            # ADB treats an explicit numeric host as remote:connection failure
            # cannot auto-launch a new daemon. Reuse only the reviewed5039.
        else:
            args = ([self.adb, '-P', '5039', '--one-device', SERIAL, 'start-server']
                    if argv == ['start-server'] else [self.adb, '-P', '5039', '-s', SERIAL, *argv])
        env = os.environ.copy()
        for key in ('ADB_SERVER_SOCKET', 'ANDROID_ADB_SERVER_PORT', 'ANDROID_SERIAL', 'ADB_TRACE'):
            env.pop(key, None)
        env['ADB_LIBUSB'] = '0'
        env['ADB_MDNS_AUTO_CONNECT'] = '0'
        save(self.out / f'command-{self.n:03}.json',
             {'arguments': args, 'environment_override':
              {'ADB_LIBUSB': '0', 'ADB_MDNS_AUTO_CONNECT': '0'},
              'inherited_server_socket_port_serial_trace_removed': True}, True)
        return subprocess.Popen(args, env=env, **kw)

    def command(self, argv, timeout_seconds=20):
        with (self.out / f'capture-{self.n+1:03}.stderr').open('wb') as err:
            p = self.start(argv, stdout=subprocess.PIPE, stderr=err)
            try:
                data, _ = p.communicate(timeout=min(timeout_seconds, max(0.01, self.deadline-time.monotonic())))
            except BaseException:
                p.kill()
                p.wait()
                raise
        (self.out / f'capture-{self.n:03}.stdout').write_bytes(data)
        if p.returncode:
            raise RuntimeError('Recovery metadata command failed; no retry')
        return data

    def read(self, device, first, count):
        if device not in (PART, '/dev/block/sda') or not 0 < count <= 65:
            raise ValueError('invalid protection read')
        data = self.command(['exec-out', f'dd if={device} bs=4096 skip={first} count={count} 2>/dev/null'])
        if len(data) != count * 4096:
            raise RuntimeError('short protection read')
        return data

    def protections(self):
        checks = [(['get-serialno'], SERIAL),
                  (['shell', 'getprop', 'ro.product.device'], 'zorn'),
                  (['shell', 'getprop', 'ro.boot.slot_suffix'], '_a'),
                  (['shell', 'readlink', '-f', PART], '/dev/block/sda35'),
                  (['shell', 'blockdev', '--getss', '/dev/block/sda'], '4096'),
                  (['shell', 'blockdev', '--getsize64', PART], '68719476736')]
        for args, expected in checks:
            if self.command(args).decode().strip() != expected:
                raise RuntimeError('exact target identity/geometry not confirmed; no install')
        from zorn_recovery_identity import PROPERTIES, inspect_recovery
        self.recovery_identity = inspect_recovery({key:self.command(['shell','getprop',key]).decode().strip() for key in PROPERTIES})
        mounts = self.command(['shell', 'cat', '/proc/mounts']).decode()
        if len(mounts)>65536 or len(mounts.splitlines())>256:
            raise RuntimeError('unexpected bounded mount inventory')
        for line in mounts.splitlines():
            fields=line.split()
            if not fields:raise RuntimeError('malformed mount row')
            if fields[0] in (PART,'/dev/block/sda35'):
                raise RuntimeError('unixnu mounted;no automatic unmount')
            if fields[0].startswith('/dev/block/'):
                target=self.command(['shell','readlink','-f',fields[0]]).decode().strip()
                if target=='/dev/block/sda35':raise RuntimeError('unixnu alias mounted;no automatic unmount')
        reads = [('primary_GPT', '/dev/block/sda', 0, 6),
                 ('backup_GPT', '/dev/block/sda', 64049147, 5),
                 ('root_manifest', PART, 0, 1), ('Data', PART, 4194304, 65)]
        state = {}
        for name, device, first, blocks in reads:
            state[name] = self.read(device, first, blocks)
            if state[name] != Path(self.d['pins'][name]['path']).read_bytes():
                raise RuntimeError('protected storage metadata changed: ' + name)
        for name, first in [('before', FIRST-1), ('after', FIRST+BLOCKS), ('log', 2291712)]:
            state[name] = self.read(PART, first, 1)
        return state

    def stream_read(self, consume):
        # Literal, fixed read window. No caller-selected block device or range.
        with (self.out / f'capture-{self.n+1:03}.stderr').open('wb') as err:
            p = self.start(['exec-out', f'dd if={PART} bs=1048576 skip=25770852352 count=34359738368 iflag=skip_bytes,count_bytes status=none 2>/dev/null'],
                           stdout=subprocess.PIPE, stderr=err)
            n, digest, notice = 0, hashlib.sha256(), 1024**3
            try:
                with selectors.DefaultSelector() as poll:
                    poll.register(p.stdout, selectors.EVENT_READ)
                    while True:
                        left = self.deadline - time.monotonic()
                        if left <= 0:
                            raise RuntimeError('root stream deadline expired; no further device operations')
                        if not poll.select(min(30, left)):
                            print('waiting for existing root-read stream;overall deadline retained', flush=True)
                            continue
                        data = os.read(p.stdout.fileno(), 1024**2)
                        if not data:
                            break
                        n += len(data)
                        if n > BYTES:
                            raise RuntimeError('root read exceeded exact window')
                        digest.update(data)
                        consume(data)
                        if n >= notice:
                            print(f'root read {n}/{BYTES}', flush=True)
                            notice += 1024**3
                self.wait_completion(p, 'root-read completion')
                if p.returncode or n != BYTES:
                    raise RuntimeError('short/failed full root read')
            except BaseException:
                p.kill()
                p.wait()
                raise
            finally:
                p.stdout.close()
        return {'bytes': n, 'sha256': digest.hexdigest()}

    def write_image(self, image):
        # shell-v2 raw stdin, no PTY. Actual Toybox advertises count_bytes and
        # seek_bytes, not GNU fullblock. Byte count survives short pipe reads;
        # no sync padding/noerror/sparse conversion may alter the image.
        with (self.out/'write.stdout').open('wb') as out, (self.out/'write.stderr').open('wb') as err:
            p = self.start(['shell', '-T', '-e', 'none', f'dd of={PART} bs=1048576 seek=25770852352 count=34359738368 iflag=count_bytes oflag=seek_bytes conv=notrunc,fsync status=none'],
                           stdin=subprocess.PIPE, stdout=out, stderr=err)
            n, digest, notice = 0, hashlib.sha256(), 1024**3
            try:
                os.set_blocking(p.stdin.fileno(), False)
                with Path(image).open('rb') as src, selectors.DefaultSelector() as poll:
                    poll.register(p.stdin, selectors.EVENT_WRITE)
                    while data := src.read(1024**2):
                        digest.update(data)
                        view = memoryview(data)
                        while view:
                            left = self.deadline-time.monotonic()
                            if left <= 0:
                                raise RuntimeError('root write deadline expired; state unknown, no further device operations')
                            if not poll.select(min(30, left)):
                                print('waiting for existing root-write stream;overall deadline retained', flush=True)
                                continue
                            try:
                                sent = os.write(p.stdin.fileno(), view)
                            except BlockingIOError:
                                continue
                            view = view[sent:]
                            n += sent
                            if n >= notice:
                                print(f'root bytes sent {n}/{BYTES};not yet readback-verified', flush=True)
                                notice += 1024**3
                p.stdin.close()
                # Flush completion shares the agreed overall3600s deadline.
                # A32GiB transfer must not be killed by an unrelated60s cap.
                self.wait_completion(p, 'write/flush completion')
                if p.returncode or n != BYTES or digest.hexdigest() != self.d['pins']['image']['sha256']:
                    raise RuntimeError('root write/source failed; no further device operations')
            except BaseException as e:
                save(self.out/'write-failure.json', {'exception': repr(e),
                     'host_pipe_bytes_sent': n, 'child_status_before_host_termination': p.poll(),
                     'persisted_bytes_unknown': True}, True)
                p.kill()
                p.wait()
                raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ios26-install-root', type=Path, required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    d = validate(args.ios26_install_root, execute=not args.check)
    if args.check:
        print(json.dumps({'scope': SCOPE, 'host_inputs_match': True,
                          'execution_ready': d.get('execution_ready') is True, 'phone_accessed': False}))
        return
    c = load(CURRENT)
    if any(c.get(k) for k in ('active_run', 'active_build', 'runner_session')):
        raise RuntimeError('another active/stopped operation; no USB')
    if c.get('stop_device_operations'):
        raise RuntimeError('stopped-device condition;no USB or automatic retry')
    out = args.ios26_install_root.resolve().parent / 'run'
    out.mkdir(exist_ok=False)
    if shutil.disk_usage(out).free < RESERVE:
        raise RuntimeError('host log/source free-space reserve insufficient; no USB')
    save(out/'one-shot.claim.json', {'scope': SCOPE, 'manifest_sha256': sha(args.ios26_install_root),
                                    'consumed_before_first_USB': True, 'reusable': False}, True)
    c['active_run'] = str(out)
    temporary = CURRENT.with_name('current.ios26-root-install.tmp')
    save(temporary, c, True)
    os.replace(temporary, CURRENT)
    status = {'scope': SCOPE, 'phase': 'identity', 'installed': False,
              'writes_attempted': False, 'booted': False, 'retries': 0}
    save(out/'result.json', status)
    try:
        rec = Recovery(d, out)
        # Host-only port check. Start only if absent;never kill/replace a
        # global or foreign daemon. All later clients disable auto-start.
        try:
            probe = socket.create_connection(('127.0.0.1', 5039), timeout=0.2)
        except ConnectionRefusedError:
            raise RuntimeError('reviewed existing server unavailable;no bootstrap')
        else:
            probe.close()
        server = rec.command(['server-status'])
        (out/'private-host-server-status.txt').write_bytes(server)
        if d['pins']['adb']['path'].encode() not in server:
            raise RuntimeError('existing private server executable differs;no device access')
        before = rec.protections()
        for name, data in before.items():
            (out/(name+'.before.bin')).write_bytes(data)
        wait_until = min(rec.deadline, time.monotonic()+d['pending_writer_wait_seconds'])
        while True:
            processes = rec.command(['shell', 'ps', '-A', '-o', 'PID,ARGS']).decode()
            previous = [line for line in processes.splitlines()
                        if 'dd ' in line and ('of='+PART in line or 'of=/dev/block/sda35' in line)]
            if not previous:
                break
            if time.monotonic() >= wait_until:
                raise RuntimeError('previous actual root writer still present;no concurrent resend')
            print('observed previous root writer;waiting without killing or restarting it', flush=True)
            time.sleep(min(5, max(0, wait_until-time.monotonic())))
        help_text = rec.command(['shell', 'dd', '--help'])
        if not all(x in help_text for x in (b'count_bytes', b'skip_bytes', b'seek_bytes', b'fsync', b'notrunc')):
            raise RuntimeError('actual Recovery dd flags unavailable; no substitute writer')
        # Preserve the already archived historical image/readback and actual
        # GPT/Data/manifest/log/fences;do not create a new phone-OS backup or
        # claim the current whole preimage was re-read. New installed-image
        # full readback remains independent of the write status.
        status.update(phase='protected-metadata-verified', target_preimage='retained-historical-host-image;no fresh-phone-preimage-claim',recovery_identity=rec.recovery_identity)
        save(out/'result.json', status)
        if rec.protections() != before:
            raise RuntimeError('protected state changed before write')
        if sha(d['pins']['image']['path']) != d['pins']['image']['sha256']:
            raise RuntimeError('source image changed after preimage; no write')
        status.update(phase='write-exact-root-window', writes_attempted=True)
        save(out/'result.json', status)
        rec.write_image(d['pins']['image']['path'])
        status['phase'] = 'complete-readback'
        save(out/'result.json', status)
        readback = rec.stream_read(lambda data: None)
        if readback != {'bytes': BYTES, 'sha256': d['pins']['image']['sha256']}:
            raise RuntimeError('full installed root readback mismatch; no retry or boot')
        if rec.protections() != before:
            raise RuntimeError('protected storage/fences changed after install; stop')
        status.update(phase='root-installed-full-readback-verified', installed=True,
                      readback=readback, protected_metadata_and_fences_unchanged=True,
                      persistent_boot_entry_installed=False, system_boot_qualified=False)
    except BaseException as e:
        status.update(phase='stopped-no-retry', error=str(e))
        raise
    finally:
        save(out/'result.json', status)
        c = load(CURRENT)
        if c.get('active_run') == str(out):
            c['active_run'] = None
            c.setdefault('gpu_discovery', {})['latest_persistent_root_installation'] = str(out/'result.json')
            if status['installed']:
                c['stop_device_operations'] = False
                c['stop_device_reason'] = None
            if status['writes_attempted'] and not status['installed']:
                c['stop_device_operations'] = True
                c['stop_device_reason'] = 'Persistent root installation incomplete/unknown; inspect exact evidence before any further I/O'
            save(temporary, c, True)
            os.replace(temporary, CURRENT)
        print(json.dumps(status, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()

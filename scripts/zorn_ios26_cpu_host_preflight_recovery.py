"""One fixed read-only Recovery check after a zero-command host sandbox failure."""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

from zorn_ios26_logdirs_boot_trial import CURRENT, STAGE, load, save, sha, protected_recovery, require_existing_adb
from zorn_gpu_resource_trial import Transport

FLAG = '--ios26-cpu-host-preflight-recovery'
RUNNER = Path(__file__).with_name('run-zorn-debug.py')
BASE = STAGE / 'k80-cpu-crash-delivery26-8749f37cf3bc4059a891ec7576f04473' / 'root-trial-crash-delivery'
TRIAL = BASE / 'trial'
OUT = TRIAL / 'host-preflight-recovery26'
PARENT = STAGE / 'k80-cpu-crash-report26-cfce615b97d340f3aac992a6b38adfff' / 'root-trial-crash-report' / 'trial'
SCOPE = 'K80-8749-zero-command-host-failure-read-only-Recovery'
ROOT = '55cf33b108c209a8fbafcc4ad16f2ac3bb39e0645ee9688c0a34908b0a1fccc5'
FAILURE = "PermissionError(1, 'Operation not permitted')"
PINNED = {'trial/run.json': 'e1e600f2d9aa22a94a7f98ddd5d75e8987c4a71cc670a1e520f8685b97e8004f', 'trial/one-shot.claim.json': '86c2ea24ad27d8a4b6bfcc12efd1f5aa981c81525090fc46b6ce72fae2f27a58', 'bundle.json': '07535c6b1c501c701aa6f23927f43662ba322934c9c58a714d9070a5fd935d8c', 'trial/host-access-check.json': '6c4d3e0eb8f5dbfd788b34657d4255aa744846f0115a459a1936c5de028ab46b'}
POLICY = dict(scope=SCOPE, serial='92988a43', product='zorn', slot='a', timeout_seconds=60,
              boots=False, device_writes=False, bootstrap=False, reuse_failed_claim=False)
SOURCES = ('run-zorn-debug.py', Path(__file__).name, 'zorn_ios26_logdirs_boot_trial.py',
           'zorn_gpu_resource_trial.py', 'zorn_recovery_identity.py')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(path):
    require(path == OUT / 'ready.json' and path.resolve() == path, 'canonical read-only readiness required')
    ready, current = load(path), load(CURRENT)
    gpu = current['gpu_discovery']
    require(current.get('stop_device_operations') is True and current.get('stop_device_reason') == FAILURE
            and not any(current.get(k) for k in ('active_run', 'active_build', 'active_admission', 'runner_session'))
            and gpu.get('current_mode') == 'unattended-phone-connected'
            and gpu.get('current_phone_root_expected_sha256') == ROOT
            and gpu.get('allow_boot') is False and not gpu.get('active_admission'), 'exact stopped host-failure state required')
    for relative, digest in PINNED.items():
        p = BASE / relative
        require(p.resolve() == p and not p.is_symlink() and sha(p) == digest, 'terminal incident changed: ' + relative)
    incident, claim, host = (load(TRIAL / name) for name in ('run.json', 'one-shot.claim.json', 'host-access-check.json'))
    require(incident == dict(scope='single-K80-ios26-CPU-crash-delivery-300s-8749f37c',
                status='failed-device-operations-stopped', GPU_started=False, root_mount_proven=False,
                desktop_proven=False, boot_attempts=0, error=FAILURE)
            and not list(TRIAL.glob('command-*')) and not list(TRIAL.glob('before-*.bin'))
            and claim['status'] == 'consumed-no-repeat' and claim['before_first_USB'] is True
            and host['host_loopback_available_outside_sandbox'] is True
            and host['recorded_transport_commands'] == 0 and host['phone_operations_in_this_check'] is False,
            'not a zero-command host failure; no automatic device recovery')
    require({k:ready.get(k) for k in POLICY} == POLICY and set(ready) == set(POLICY) | {'inputs'}, 'read-only policy differs')
    expected = {name:str(Path(__file__).with_name(name)) for name in SOURCES}
    expected.update({relative:str(BASE / relative) for relative in PINNED})
    for p in sorted(PARENT.glob('after-*.bin')):
        expected['parent-' + p.name] = str(p)
    expected['parent-misc-readback'] = str(PARENT / 'misc-readback.bin')
    require(set(ready['inputs']) == set(expected), 'read-only inputs incomplete')
    for role, source in expected.items():
        pin = ready['inputs'][role];p, q = Path(pin['path']), Path(pin['archive'])
        require(str(p) == source and p.resolve() == p and q.parent == OUT / 'archive'
                and q.resolve() == q and not p.samefile(q) and sha(p) == sha(q) == pin['sha256'], 'read-only input changed: ' + role)
    bundle = load(BASE / 'bundle.json')
    for role in ('primary_GPT', 'backup_GPT', 'root_manifest', 'Data_header', 'Data_metadata',
                 'root_first_page', 'root_before', 'root_after', 'adb_binary', 'host_adb_proof',
                 'device_helpers', 'recovery_identity', 'transport_core'):
        pin = bundle['pins'][role];p, q = Path(pin['path']), Path(pin['archive'])
        require(p.resolve() == p and q.resolve() == q and not p.samefile(q)
                and sha(p) == sha(q) == pin['sha256'], 'protection/reader input changed: ' + role)
    require(not (OUT / 'one-shot.claim.json').exists(), 'read-only claim already consumed')
    return ready, current, bundle


class ReadOnlyCapture(Transport):
    def __init__(self, adb, out):
        super().__init__(adb_server_port=5039)
        self.adb, self.out, self.sequence = adb, out, 0
        self.deadline = time.monotonic() + 60

    def adb_call(self, *args, **kwargs):
        # A hard command allowlist prevents boot, push, writes and daemon bootstrap.
        simple = args in (('server-status',), ('get-serialno',), ('shell', 'cat', '/proc/mounts'))
        prop = len(args) == 3 and args[:2] == ('shell', 'getprop') and re.fullmatch(r'ro\.[a-zA-Z0-9_.]+', args[2])
        link = len(args) == 4 and args[:3] == ('shell', 'readlink', '-f') and re.fullmatch(r'/dev/block/[a-zA-Z0-9_/-]+', args[3])
        block = args in (('shell', 'blockdev', '--getsize64', '/dev/block/by-name/unixnu'),
                         ('shell', 'blockdev', '--getss', '/dev/block/sda'))
        read = len(args) == 2 and args[0] == 'exec-out' and re.fullmatch(
            r'dd if=(/dev/block/by-name/(unixnu|misc)|/dev/block/sda) bs=4096 skip=[0-9]+ count=[0-9]+ 2>/dev/null', args[1])
        require(simple or prop or link or block or read, 'command outside fixed read-only allowlist')
        return super().adb_call(*args, **kwargs)

    def call(self, *args, **kwargs):
        self.sequence += 1
        stem = self.out / ('command-%03d' % self.sequence)
        save(stem.with_suffix('.json'), dict(arguments=list(map(str,args))), True)
        result = super().call(*args, **kwargs)
        stem.with_suffix('.stdout').write_bytes(result if isinstance(result, bytes) else result.encode())
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(FLAG, dest='ready', required=True, type=Path)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    require(Path(sys.argv[0]).resolve() == RUNNER, 'fixed runner required')
    ready, current, bundle = validate(args.ready)
    if args.check_only:
        print(json.dumps(dict(scope=SCOPE, host_inputs_match=True, phone_accessed=False)))
        return
    save(OUT / 'one-shot.claim.json', POLICY | dict(ready_sha256=sha(args.ready), consumed_before_first_USB=True, reusable=False), True)
    io = ReadOnlyCapture(bundle['pins']['adb_binary']['path'], OUT)
    result = POLICY | dict(status='claimed', stop_cleared=False)
    try:
        require_existing_adb(io)
        protected = protected_recovery(io, bundle['pins'], bundle['accepted_recovery'])
        for name, data in protected.items():
            require(data == (PARENT / ('after-' + name + '.bin')).read_bytes(), 'prior actual protection changed: ' + name)
            (OUT / ('current-' + name + '.bin')).write_bytes(data)
        old = io.read('/dev/block/by-name/misc', 0, 1)
        reference = (PARENT / 'misc-readback.bin').read_bytes()
        require(old[2048:] == reference[2048:] and old[:32].split(b'\0', 1)[0] in (b'', b'boot-recovery'), 'BCB command/tail differs')
        (OUT / 'misc.bin').write_bytes(old)
        log = io.read('/dev/block/by-name/unixnu', 2291712, 1)
        require(log == (PARENT / 'after-log.bin').read_bytes(), 'native log changed after last actual boot')
        (OUT / 'log.bin').write_bytes(log)
        require(io.read('/dev/block/by-name/misc', 0, 1) == old, 'BCB changed during read-only check')
        require(load(CURRENT) == current, 'current state changed during read-only check')
        result.update(status='verified-Recovery-protections-unchanged-no-boot', recovery_identity=io.recovery_identity,
                      protected_ranges=len(protected), BCB_full_page_stable=True, BCB_tail_preserved=True,
                      log_unchanged_since_actual_cfce_boot=True, transport_commands=io.sequence)
        save(OUT / 'result.json', result, True) # Durable physical evidence before state change.
        # Clear only this proven pre-USB host failure after fresh physical checks.
        current.update(stop_device_operations=False, stop_device_reason=None)
        current['gpu_discovery']['last_zero_command_host_failure_recovery_check'] = str(OUT / 'result.json')
        temporary = CURRENT.with_name('current.host-preflight-recovery.tmp')
        save(temporary, current, True)
        os.replace(temporary, CURRENT)
        result['stop_cleared'] = True
    except BaseException as error:
        result.update(status='read-only-check-failed-stop-retained', error=repr(error))
        raise
    finally:
        pending = OUT / 'result.json.pending'
        save(pending, result, True)
        os.replace(pending, OUT / 'result.json')
        print(json.dumps(result))

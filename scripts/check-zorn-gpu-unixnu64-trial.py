#!/usr/bin/env python3
"""Pure host admission and transport-double controls; no phone or boot."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import runpy
import struct
import sys
import tempfile
import zlib
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().with_name('zorn_gpu_unixnu64_trial.py')
spec = importlib.util.spec_from_file_location('media_trial', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2)+'\n')


def check():
    calls = []

    def denied(*args, **kw):
        calls.append(args)
        raise AssertionError('No host control may invoke a process or USB')

    with tempfile.TemporaryDirectory(prefix='zorn-media-admission-') as directory, patch.object(m.subprocess, 'run', denied):
        base = Path(directory).resolve()
        (base/'image').mkdir()
        (base/'trials').mkdir()
        files = {}
        for role in m.ROLES:
            p = base/'artifacts'/role
            p.parent.mkdir(exist_ok=True)
            p.write_bytes((role+' synthetic host fixture').encode())
            files[role] = p
        files['boot'] = base/'image/boot.img'
        files['boot'].write_bytes(b'synthetic, not a bootable image')
        files['FAT'] = base/'image/payload.img'
        fat = bytearray(1024)
        fat[0x32:0x34] = (1).to_bytes(2, 'little')
        fat[510:512] = b'\x55\xaa'
        fat[0x180:0x190] = b'ZORNGHWD'+struct.pack('<II', 1, 0xfffffffe)
        fat[0x190:0x1a0] = b'ZORNTPWR'+struct.pack('<II', 1, 0xfffffffe)
        fat[512:] = fat[:512]
        files['FAT'].write_bytes(fat)
        descriptor = SCRIPT.parents[1]/'storage/unixnu64.json'
        files['descriptor'].write_bytes(descriptor.read_bytes())
        header = bytearray(4096);header[:8] = b'SHNGDATA'
        struct.pack_into('<IIQ', header, 8, 1, 64, 2097152)
        header[24:56] = bytes.fromhex(m.load(descriptor)['Data']['seed_sha256'])
        struct.pack_into('<I', header, 56, 1535636492)
        struct.pack_into('<I', header, 60, zlib.crc32(header[:60]))
        files['Data_header'].write_bytes(header)
        write(files['expected'], dict(nonce='11'*16, kernel_sha256=m.digest(files['kernel']), input_sha256='22'*32))
        write(files['kernel_plan'], dict(candidate_sha256=m.digest(files['kernel'])))
        write(files['current_start_binding'], dict(source=str(files['current_start_source']),
            source_sha256=m.digest(files['current_start_source']), active_object=str(files['current_start_object']),
            active_object_sha256=m.digest(files['current_start_object']), recipe=str(files['current_start_recipe']),
            recipe_sha256=m.digest(files['current_start_recipe']), independent_sha256=m.digest(files['current_start_object'])))
        write(files['fd_audit'], dict(fd_sha256=m.digest(files['fd']), module_sha256=m.digest(files['module']),
            extracted_module_whole_file_equal=True, actual_compiler_selectors=dict(inspection=0, media_commit=1, caller=1, driver=1)))
        write(files['image_audit'], dict(boot_sha256=m.digest(files['boot']), kernel_sha256=m.digest(files['kernel']),
            FD_sha256=m.digest(files['fd']), terminal_before_payload=True))
        write(files['offline_result'], dict(offline_complete=True, scope='synthetic host fixture, not verification'))
        source = base/'source.bin'
        saved = base/'independent.bin'
        source.write_bytes(b'synthetic archived source')
        saved.write_bytes(source.read_bytes())
        row = dict(path=str(saved), sha256=m.digest(saved))
        write(files['firmware_inputs'], dict(inputs={str(source): m.digest(source)}))
        write(files['firmware_archive'], dict(files={str(saved): dict(source=str(source), sha256=m.digest(saved))}))
        write(files['runtime_inputs'], dict(inputs={str(source): m.digest(source)}))
        write(files['runtime_archive'], dict(files={str(source): row}))
        bundle_path = base/'trial-bundle.json'
        owner, ready = base/'synthetic-owner.json', base/'synthetic-ready.json'
        admission = dict(version=1, scope=m.SCOPE, serial=m.SERIAL, product='zorn', slot='a',
            storage_profile='unixnu64', timeout_seconds=600, start_in_recovery=True,
            bootstrap_allowed=False, terminal_before_payload=True, GPU_enabled=False,
            accepted_preowner_and_nonreturning_IO_unavailable=True, owner_activation_approved=True,
            allow_boot=True, retries=0, log_relative_lba=2291712, log_blocks=1, watchdog_mode=1,
            bundle=str(bundle_path), owner_approval=str(owner), ready=str(ready),
            claim=str(base/'trials/one-shot.claim.json'))

        def seal():
            pins = {role: dict(path=str(p), sha256=m.digest(p)) for role, p in files.items()}
            write(bundle_path, dict(scope=m.SCOPE, pins=pins))
            admission['bundle_sha256'] = m.digest(bundle_path)
            write(owner, dict(approved=True, scope=m.SCOPE, boot_sha256=m.digest(files['boot']),
                nonce='11'*16, bundle_sha256=admission['bundle_sha256'],
                accept_preowner_and_nonreturning_IO_unavailable=True, host_fixture_only=True))
            write(ready, dict(allow_boot=True, scope=m.SCOPE, bundle_sha256=admission['bundle_sha256'],
                boot_sha256=m.digest(files['boot']), readback_qualified=False, host_fixture_only=True))
            admission['owner_approval_sha256'] = m.digest(owner)
            admission['ready_sha256'] = m.digest(ready)

        seal()
        verified = m.validate(admission, base=base, current={})
        refused = 0

        def reject(a=None, current=None):
            nonlocal refused
            try:
                m.validate(a if a is not None else admission, base=base, current=current or {})
            except (ValueError, KeyError, TypeError):
                refused += 1
            else:
                raise AssertionError('bad admission accepted')

        for key, bad in [('serial', 'f85d4270'), ('slot', 'b'), ('storage_profile', 'userdata'),
                         ('timeout_seconds', 601), ('start_in_recovery', False), ('bootstrap_allowed', True),
                         ('GPU_enabled', True), ('owner_activation_approved', False), ('allow_boot', False),
                         ('terminal_before_payload', False), ('retries', 1), ('log_relative_lba', 5404416),
                         ('log_blocks', 2), ('watchdog_mode', 0), ('version', True),
                         ('accepted_preowner_and_nonreturning_IO_unavailable', False)]:
            a = deepcopy(admission)
            a[key] = bad
            reject(a)
        for key in ['active_run', 'active_build', 'runner_session', 'stop_device_operations']:
            reject(current={key: 'active'})
        for key in ['scope', 'bundle_sha256', 'owner_approval_sha256', 'ready_sha256']:
            a = deepcopy(admission)
            a[key] = 'obsolete'
            reject(a)
        for name, field, bad in [('fd_audit', 'actual_compiler_selectors', dict(inspection=1, media_commit=1, caller=1, driver=1)),
                                 ('image_audit', 'terminal_before_payload', False),
                                 ('current_start_binding', 'independent_sha256', '00'*32),
                                 ('kernel_plan', 'candidate_sha256', '00'*32),
                                 ('offline_result', 'offline_complete', False)]:
            old = files[name].read_bytes()
            d = m.load(files[name]);d[field] = bad;write(files[name], d);seal();reject()
            files[name].write_bytes(old);seal()
        bad = m.load(owner);bad['approved'] = False;write(owner, bad);admission['owner_approval_sha256'] = m.digest(owner);reject();seal()
        bad = m.load(ready);bad['scope'] = 'old-installation';write(ready, bad);admission['ready_sha256'] = m.digest(ready);reject();seal()
        old = saved.read_bytes();saved.write_bytes(b'changed archive');reject();saved.write_bytes(old)
        old = files['runtime_archive'].read_bytes()
        write(files['runtime_archive'], dict(files={str(source): dict(path=str(source), sha256=m.digest(source))}));seal();reject();files['runtime_archive'].write_bytes(old);seal()
        old = files['FAT'].read_bytes();bad = bytearray(old);bad[512+0x180] ^= 1;files['FAT'].write_bytes(bad);seal();reject();files['FAT'].write_bytes(old);seal()
        old = files['Data_header'].read_bytes();bad = bytearray(old);struct.pack_into('<I', bad, 56, 123);struct.pack_into('<I', bad, 60, zlib.crc32(bad[:60]));files['Data_header'].write_bytes(bad);seal();reject();files['Data_header'].write_bytes(old);seal()
        verified = m.validate(admission, base=base, current={})
        m.claim_once(verified)
        reject()
        try:
            m.claim_once(verified)
        except FileExistsError:
            pass
        else:
            raise AssertionError('second claim accepted')
        # Pending actual CLI dispatch must refuse before a process/USB call.
        pending = deepcopy(admission);pending['owner_activation_approved'] = False
        path = base/'pending.json';write(path, pending)
        with patch.object(sys, 'argv', ['run-zorn-debug.py', '--gpu-unixnu64-media-trial', str(path)]):
            try:
                runpy.run_path(str(SCRIPT.with_name('run-zorn-debug.py')), run_name='__main__')
            except ValueError:
                refused += 1
            else:
                raise AssertionError('pending CLI accepted')
        # Read-only Recovery identity and exact BCB tail, using explicit doubles.
        snapshot = dict(primary=b'p'*24576, backup=b'b'*20480, root=b'r'*4096, header=b'h'*4096)
        for role, key in [('primary_GPT', 'primary'), ('backup_GPT', 'backup'), ('root_manifest', 'root'), ('Data_header', 'header')]:
            files[role].write_bytes(snapshot[key])
        pins = {role: dict(path=str(p)) for role, p in files.items()}

        class FakeIO:
            def __init__(self, fault=None):
                self.fault = fault;self.writes = 0;self.misc = bytes(i%251 for i in range(4096));self.tmp = None
            def adb_call(self, *a, **kw):
                key = tuple(a)
                table = {('get-serialno',):m.SERIAL, ('shell','getprop','ro.product.device'):'zorn',
                    ('shell','getprop','ro.boot.slot_suffix'):'_a', ('shell','getprop','ro.orangefox.boot'):'1',
                    ('shell','readlink','-f',m.PARTITION):'/dev/block/sda35',
                    ('shell','readlink','-f','/dev/block/by-name/misc'):'/dev/block/sda11',
                    ('shell','blockdev','--getsize64',m.PARTITION):'68719476736',
                    ('shell','blockdev','--getss','/dev/block/sda'):'4096', ('shell','cat','/proc/mounts'):''}
                if self.fault=='serial' and key==('get-serialno',):return 'f85d4270'
                if self.fault=='fox' and key==('shell','getprop','ro.orangefox.boot'):return '0'
                if self.fault=='slot' and key==('shell','getprop','ro.boot.slot_suffix'):return '_b'
                if self.fault=='mounted' and key==('shell','cat','/proc/mounts'):return '/dev/block/alias /data ext4 rw 0 0'
                if key==('shell','readlink','-f','/dev/block/alias'):return '/dev/block/sda35'
                if key in table:return table[key]
                if a[0]=='push':self.tmp=Path(a[1]).read_bytes();return ''
                if a[:2]==('exec-out','cat'):return self.tmp[:-1] if self.fault=='tmpfs' else self.tmp
                if a[0]=='shell' and a[1].startswith('dd if=/tmp/zorn-gpu-unixnu64-recovery-bcb.bin of=/dev/block/by-name/misc '):
                    self.writes+=1;self.misc=self.tmp;return ''
                raise AssertionError(a)
            def read(self, device, lba, count):
                if device=='/dev/block/by-name/misc':
                    return self.misc[:-1]+b'x' if self.writes and self.fault=='bcb' else self.misc
                if device=='/dev/block/sda':return snapshot['primary'] if lba==0 else snapshot['backup']
                if lba==0:return snapshot['root']
                if lba==4194304:return snapshot['header']+bytes(64*4096)
                return b'f'*4096
        f = FakeIO();state=m.recovery(f, pins);assert len(state['Data'])==65*4096 and not f.writes
        faults = 0
        for fault in ['serial','fox','slot','mounted']:
            f=FakeIO(fault)
            try:m.recovery(f,pins)
            except RuntimeError:faults+=1
            else:raise AssertionError(fault)
            assert not f.writes
        out=base/'BCB-double';out.mkdir();f=FakeIO();old=f.misc;b=m.fresh_bcb(f,out)
        assert b['tail_preserved'] and b['full_page_readback'] and f.writes==1 and f.misc[864:]==old[864:]
        for fault in ['tmpfs','bcb']:
            f=FakeIO(fault)
            try:m.fresh_bcb(f,out)
            except RuntimeError:faults+=1
            else:raise AssertionError(fault)
            assert f.writes==(0 if fault=='tmpfs' else 1)
        class FastbootDouble:
            fastboot='synthetic-fastboot'
            def __init__(self, text):self.text=text
            def call(self, *a, **kw):return self.text
        assert m.getvar(FastbootDouble('product: zorn\nFinished. Total time: 0.1s'), 'product')=='zorn'
        for text in ['wrong-product: zorn', 'product: zorn\nproduct: zorn', 'product:']:
            try:m.getvar(FastbootDouble(text),'product')
            except RuntimeError:faults+=1
            else:raise AssertionError('ambiguous variable accepted')
        # Whole fixed-runner workflow with explicit transport doubles; the
        # synthetic admission above is tested independently, never used to boot.
        flows=[]
        for fault in [None, 'bcb']:
            flow=base/('flow-'+str(fault));(flow/'trials').mkdir(parents=True)
            current=flow/'out/zorn/unattended-active/current.json';write(current,{})
            v=dict(verified,base=flow,claim=flow/'trials/one-shot.claim.json',pins=pins)
            class FlowIO(FakeIO):
                fastboot='synthetic-fastboot'
                def __init__(self):
                    super().__init__(fault);self.deadline=0;self.boots=0
                def adb_call(self,*a,**kw):
                    assert v['claim'].exists(),'USB before claim'
                    if a==('reboot','bootloader'):return ''
                    return super().adb_call(*a,**kw)
                def call(self,*a,**kw):
                    assert v['claim'].exists(),'USB before claim'
                    if a[3]=='boot':self.boots+=1;return 'OKAY'
                    return {'product':'product: zorn','current-slot':'current-slot: a',
                            'partition-size:unixnu':'partition-size:unixnu: 0x1000000000'}[a[-1]]
            io=FlowIO()
            # The fake transport accepts only the explicitly listed commands.
            with patch.object(m,'ROOT',flow),patch.object(m,'validate',return_value=v),patch.object(m,'Transport',return_value=io),patch.object(sys,'platform','host-fixture'),patch.object(sys,'argv',['run-zorn-debug.py','--gpu-unixnu64-media-trial',str(path)]),patch('builtins.print'):
                try:m.main()
                except RuntimeError:
                    assert fault=='bcb'
                else:assert fault is None
            manifest=m.load(flow/'trials/run/run.json')
            assert v['claim'].exists() and m.load(current)['active_run'] is None
            if fault:
                assert manifest['status']=='failed-stop-device-operations' and not io.boots and m.load(current)['stop_device_operations']
            else:
                assert io.boots==1 and manifest['status']=='recovered' and not manifest['record']['available']
                assert not manifest['native_write_SUCCESS_proven'] and not manifest['native_readback_SUCCESS_proven']
            flows.append(dict(fault=fault,boots=io.boots,status=manifest['status']))
        assert not calls
        return dict(admission_refusals=refused, valid_synthetic_admission=1, recovery_BCB_double_faults=faults,
                    independent_claim_refusal=True, processes=0, USB_calls=0,
                    workflow_doubles=flows,synthetic_host_only=True, not_candidate_or_hardware_qualification=True)


if __name__ == '__main__':
    print(json.dumps(check()))

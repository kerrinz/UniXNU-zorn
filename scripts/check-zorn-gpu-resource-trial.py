#!/usr/bin/env python3
"""New resource-scope admission controls only; protected common functions are AST-bound, not rerun."""
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

SCRIPT = Path(__file__).resolve().with_name('zorn_gpu_resource_trial.py')
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
            extracted_module_whole_file_equal=True, actual_compiler_selectors=dict(inspection=0, media_commit=1, caller=1, driver=1, resource_query=1), module_entry_rva=0x2000, selected_annotation_only=False))
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
            resource_observation_only=True,protocol_locates_max=3,clock_lookups_max=3,
            gcd_descriptor_calls_max=16,no_clock_vote_rate_reset=True,no_SCM_PAS=True,
            accept_lookup_bookkeeping_allocation_or_blocking=True,
            bundle=str(bundle_path), owner_approval=str(owner), ready=str(ready),
            claim=str(base/'trials/one-shot.claim.json'))

        def seal():
            pins = {role: dict(path=str(p), sha256=m.digest(p)) for role, p in files.items()}
            write(bundle_path, dict(scope=m.SCOPE, pins=pins))
            admission['bundle_sha256'] = m.digest(bundle_path)
            write(owner, dict(approved=True, scope=m.SCOPE, boot_sha256=m.digest(files['boot']),
                nonce='11'*16, bundle_sha256=admission['bundle_sha256'],
                accept_preowner_and_nonreturning_IO_unavailable=True, resource_observation_approved=True,
                accept_lookup_bookkeeping_allocation_or_blocking=True, host_fixture_only=True))
            write(ready, dict(allow_boot=True, scope=m.SCOPE, bundle_sha256=admission['bundle_sha256'],
                boot_sha256=m.digest(files['boot']), readback_qualified=False, resource_observation_only=True, host_fixture_only=True))
            admission['owner_approval_sha256'] = m.digest(owner)
            admission['ready_sha256'] = m.digest(ready)


        seal()
        verified=m.validate(admission,base=base,current={})
        refused=0
        def reject(a=None):
            nonlocal refused
            try:m.validate(admission if a is None else a,base=base,current={})
            except (ValueError,KeyError,TypeError):refused+=1
            else:raise AssertionError('new resource scope accepted an invalid case')
        old_scopes=['single-unixnu64-UEFI-media-qualification-terminal-before-payload',
                    'single-UEFI-media-qualification-terminal-before-payload']
        for scope in old_scopes:
            a=deepcopy(admission);a['scope']=scope;reject(a)
        for key,bad in [('resource_observation_only',False),('protocol_locates_max',4),
                        ('clock_lookups_max',4),('gcd_descriptor_calls_max',17),
                        ('no_clock_vote_rate_reset',False),('no_SCM_PAS',False),
                        ('accept_lookup_bookkeeping_allocation_or_blocking',False),
                        ('owner_activation_approved',False),('GPU_enabled',True),
                        ('protocol_locates_max',3.0)]:
            a=deepcopy(admission);a[key]=bad;reject(a)
        for field in ['resource_observation_approved','accept_lookup_bookkeeping_allocation_or_blocking']:
            for value in [False,None]:
                seal();d=m.load(owner)
                if value is None:del d[field]
                else:d[field]=value
                write(owner,d);admission['owner_approval_sha256']=m.digest(owner);reject()
        seal();d=m.load(owner);d['scope']=old_scopes[0];write(owner,d);admission['owner_approval_sha256']=m.digest(owner);reject()
        seal();d=m.load(ready);d['resource_observation_only']=False;write(ready,d);admission['ready_sha256']=m.digest(ready);reject()
        for field,value in [('module_entry_rva',0),('module_entry_rva',True),('selected_annotation_only',True),
                            ('actual_compiler_selectors',dict(inspection=0,media_commit=1,caller=1,driver=1)),
                            ('actual_compiler_selectors',dict(inspection=0,media_commit=1,caller=1,driver=1,resource_query=0))]:
            original=files['fd_audit'].read_bytes();d=m.load(files['fd_audit']);d[field]=value;write(files['fd_audit'],d);seal();reject();files['fd_audit'].write_bytes(original)
        seal();verified=m.validate(admission,base=base,current={});m.claim_once(verified);reject()
        try:m.claim_once(verified)
        except FileExistsError:pass
        else:raise AssertionError('claim reused')
        pending=deepcopy(admission);pending['owner_activation_approved']=False
        path=base/'pending.json';write(path,pending)
        with patch.object(sys,'argv',['run-zorn-debug.py','--gpu-resource-observation-trial',str(path)]):
            try:runpy.run_path(str(SCRIPT.with_name('run-zorn-debug.py')),run_name='__main__')
            except ValueError:refused+=1
            else:raise AssertionError('pending new scope reached USB')
        assert not calls
        return dict(new_scope_refusals=refused,valid_synthetic_new_scope=1,
                    old_762a_and57_scopes_refused=True,noentry_annotation_refused_as_operational=True,
                    processes=0,USB_calls=0,no_common_transport_suite_rerun=True,
                    synthetic_host_only=True)

if __name__=='__main__':print(json.dumps(check()))

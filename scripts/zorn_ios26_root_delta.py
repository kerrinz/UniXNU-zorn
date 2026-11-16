"""Apply one exact host-derived HFSX root delta in verified Recovery; never boot."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
from zorn_ios26_root_install import Recovery, ROOT, BASE, CURRENT, SERIAL, PART, FIRST, BLOCKS, BYTES, load, save, sha

SCOPE = 'K80-persistent-iOS26-root-logdirs-delta-v6'
ROLES = {'patch','delta','local_update','prior_install_receipt','owner','ready','root_window_header',
         'window_review','adb','primary_GPT','backup_GPT','Data','root_manifest','host_adb_proof',
         'entry','runner','install_transport','recovery_identity'}


def validate(path, execute=False):
    path=Path(path).resolve()
    if not path.is_relative_to(BASE) or path.is_symlink():raise ValueError('independent fixed-install manifest required')
    d=load(path)
    required=dict(scope=SCOPE,serial=SERIAL,product='zorn',slot='a',partition=PART,
        relative_first_lba=FIRST,blocks=BLOCKS,image_bytes=BYTES,timeout_seconds=3600,
        retries=0,existing_server_only=True,allow_fresh_private_server_when_absent=False,
        complete_readback_required=False,automatic_boot=False,Android_preserved=True,old_Data_preserved=True)
    if any(type(d.get(k)) is not type(v) or d.get(k)!=v for k,v in required.items()):raise ValueError('exact root-delta scope differs')
    if set(d.get('pins',{}))!=ROLES:raise ValueError('exact delta input set required')
    for name,row in d['pins'].items():
        p,a=Path(row['path']),Path(row['archive'])
        if not p.is_absolute() or not a.is_absolute() or p.is_symlink() or a.is_symlink() or not p.is_file() or not a.is_file() or p.stat().st_ino==a.stat().st_ino or sha(p)!=row['sha256'] or sha(a)!=row['sha256']:raise ValueError('changed/shared delta input: '+name)
    fixed={'entry':Path(__file__),'runner':Path(__file__).with_name('run-zorn-debug.py'),
        'install_transport':Path(__file__).with_name('zorn_ios26_root_install.py'),
        'recovery_identity':Path(__file__).with_name('zorn_recovery_identity.py')}
    if any(Path(d['pins'][k]['path']).resolve()!=v.resolve() for k,v in fixed.items()):raise ValueError('maintained fixed entry/transport required')
    delta=load(d['pins']['delta']['path']);prior=load(d['pins']['prior_install_receipt']['path']);local=load(d['pins']['local_update']['path'])
    if (delta.get('status')!='exact-full-root-hashes-and4KiB-delta-derived' or delta.get('bytes')!=BYTES or
        prior.get('installed') is not True or prior.get('readback')!={'bytes':BYTES,'sha256':delta['source_sha256']} or
        local.get('status')!='independent-local-root-template-updated-and-numeric-ownership-filesystem-verified'):
        raise ValueError('actual complete prior readback/host-image delta required')
    if d.get('old_root_sha256')!=delta['source_sha256'] or d.get('new_root_sha256')!=delta['sha256']:raise ValueError('root identities differ')
    pages=delta['pages'];patch=Path(d['pins']['patch']['path']).read_bytes()
    if not 0<len(pages)<=256 or len(patch)!=len(pages)*8192 or delta['changed_blocks']!=len(pages) or delta['changed_bytes']!=len(pages)*4096:raise ValueError('bounded actual delta pages required')
    last=-1
    for i,row in enumerate(pages):
        n=row['image_block']
        if type(n) is not int or not last<n<BLOCKS:raise ValueError('duplicate/out-of-window delta page')
        old,new=patch[i*8192:i*8192+4096],patch[i*8192+4096:(i+1)*8192]
        if hashlib.sha256(old).hexdigest()!=row['old_sha256'] or hashlib.sha256(new).hexdigest()!=row['new_sha256'] or old==new:raise ValueError('actual old/new page data differs')
        last=n
    for role in ('owner','ready'):
        a=load(d['pins'][role]['path'])
        if a.get('scope')!=SCOPE or a.get('serial')!=SERIAL or a.get('new_root_sha256')!=delta['sha256'] or a.get('approved') is not True:raise ValueError('exact standing-owner/ready record required')
    review=load(d['pins']['window_review']['path'])
    if review.get('relative_first_lba')!=FIRST or review.get('blocks')!=BLOCKS or review.get('new_root_sha256')!=delta['sha256']:raise ValueError('exact existing root-window review required')
    header=Path(d['pins']['root_window_header']['path']).read_text()
    literal='static constexpr uint8_t ImageSha256[] = {'+','.join(hex(x) for x in bytes.fromhex(delta['sha256']))+'};'
    if literal not in header:raise ValueError('matching native root identity header required')
    proof=load(d['pins']['host_adb_proof']['path'])
    if proof.get('archive_sha1_matched') is not True or proof.get('adb_sha256')!=d['pins']['adb']['sha256']:raise ValueError('verified existing native host tool required')
    c=load(CURRENT)
    if any(c.get(k) for k in ('active_run','active_build','runner_session','stop_device_operations')) or c.get('gpu_discovery',{}).get('current_mode')=='unattended-offline-no-phone':raise ValueError('device operation unavailable;no USB')
    if execute and d.get('execution_ready') is not True:raise ValueError('delta not execution-ready')
    return d,delta,patch


def groups(pages,patch):
    out=[]
    for i,row in enumerate(pages):
        old,new=patch[i*8192:i*8192+4096],patch[i*8192+4096:(i+1)*8192]
        if out and row['image_block']==out[-1][0]+len(out[-1][1])//4096 and len(out[-1][1])<65*4096:
            n,a,z=out[-1];out[-1]=(n,a+old,z+new)
        else:out.append((row['image_block'],old,new))
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--ios26-root-delta',type=Path,required=True);p.add_argument('--check',action='store_true');a=p.parse_args()
    d,delta,patch=validate(a.ios26_root_delta,not a.check);parts=groups(delta['pages'],patch)
    if a.check:print(json.dumps({'scope':SCOPE,'host_inputs_match':True,'pages':len(delta['pages']),'write_groups':len(parts),'phone_accessed':False}));return
    out=a.ios26_root_delta.resolve().parent/'run';out.mkdir()
    save(out/'one-shot.claim.json',{'scope':SCOPE,'manifest_sha256':sha(a.ios26_root_delta),'consumed_before_first_USB':True,'reusable':False},True)
    c=load(CURRENT);c['active_run']=str(out);save(CURRENT,c)
    status={'scope':SCOPE,'phase':'identity','installed':False,'writes_attempted':False,'retries':0,'booted':False,'pages_written':0}
    save(out/'result.json',status)
    try:
        with socket.create_connection(('127.0.0.1',5039),timeout=.2):pass
        rec=Recovery(d,out);server=rec.command(['server-status'])
        if d['pins']['adb']['path'].encode() not in server:raise RuntimeError('existing server executable differs;no bootstrap')
        before=rec.protections()
        for n,data in before.items():(out/(n+'.before.bin')).write_bytes(data)
        ps=rec.command(['shell','ps','-A','-o','PID,ARGS']).decode()
        if any('dd ' in line and ('of='+PART in line or 'of=/dev/block/sda35' in line) for line in ps.splitlines()):raise RuntimeError('existing root writer present;no concurrent write')
        help_text=rec.command(['shell','dd','--help'])
        if not all(x in help_text for x in (b'count_bytes',b'fsync',b'notrunc')):raise RuntimeError('actual reviewed Recovery dd features unavailable')
        # All actual old blocks must match before the first root write.
        for i,(block,old,new) in enumerate(parts):
            actual=rec.read(PART,FIRST+block,len(old)//4096);(out/f'delta-{i:03}-before.bin').write_bytes(actual)
            if actual!=old:raise RuntimeError('root delta preimage differs;no write')
        if rec.protections()!=before:raise RuntimeError('protected state changed before write')
        status.update(phase='apply-exact-root-delta',writes_attempted=True,recovery_identity_before=rec.recovery_identity);save(out/'result.json',status)
        written_digest=hashlib.sha256()
        for i,(block,old,new) in enumerate(parts):
            args=['shell','-T','-e','none',f'dd of={PART} bs=4096 seek={FIRST+block} count={len(new)} iflag=count_bytes conv=notrunc,fsync status=none']
            with (out/f'write-{i:03}.stdout').open('wb') as stdout,(out/f'write-{i:03}.stderr').open('wb') as stderr:
                child=rec.start(args,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr)
                try:child.communicate(new,timeout=min(30,max(.01,rec.deadline-__import__('time').monotonic())))
                except BaseException:
                    child.kill();child.wait();raise
                if child.returncode:raise RuntimeError('root delta write failed;no retry')
            actual=rec.read(PART,FIRST+block,len(new)//4096);(out/f'delta-{i:03}-after.bin').write_bytes(actual)
            if actual!=new:raise RuntimeError('root delta readback differs;no retry')
            written_digest.update(actual)
            status['pages_written']+=len(new)//4096;save(out/'result.json',status)
        # Owner explicitly waived a full32GiB readback. Only the actual written
        # pages were read above;keep that qualification separate from image identity.
        readback={'scope':'written4KiB-root-pages-only','blocks':status['pages_written'],
            'bytes':status['pages_written']*4096,'sha256':written_digest.hexdigest()}
        after=rec.protections()
        if after!=before:raise RuntimeError('protected metadata/fences changed;stop')
        for n,data in after.items():(out/(n+'.after.bin')).write_bytes(data)
        status.update(phase='root-delta-installed-written-blocks-readback-verified',installed=True,readback=readback,full_root_readback_performed=False,expected_image_sha256=delta['sha256'],historical_base_image_sha256=delta['source_sha256'],protected_metadata_and_fences_unchanged=True,recovery_identity_after=rec.recovery_identity,persistent_boot_entry_installed=False,system_boot_qualified=False)
    except BaseException as e:
        status.update(phase='stopped-no-retry',error=repr(e));raise
    finally:
        save(out/'result.json',status);c=load(CURRENT)
        if c.get('active_run')==str(out):
            c['active_run']=None;c.setdefault('gpu_discovery',{})['latest_root_delta_installation']=str(out/'result.json')
            if status['writes_attempted'] and not status['installed']:c.update(stop_device_operations=True,stop_device_reason='Root delta incomplete/unknown;preserve Recovery,evidence and resources;no automatic retry')
            save(CURRENT,c)
        print(json.dumps(status),flush=True)

if __name__=='__main__':main()

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check exact280 plan and real retained Recovery adapter with explicit local I/O fixtures;no phone."""
import argparse,hashlib,json,os,re,subprocess,sys,time,types
from pathlib import Path

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def module(path,name,text=None):
    m=types.ModuleType(name);m.__file__=str(path);sys.modules[name]=m
    exec(compile(path.read_text() if text is None else text,str(path),'exec'),m.__dict__);return m

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--review-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();D=a.review_dir.resolve();O=a.out.resolve();O.mkdir();plan_path=D/'metal_root_delta_plan.py';text=plan_path.read_text();actual=module(plan_path,'metal_root_delta_plan');base,parts,retained=actual.load_plan();layout=json.loads(actual.paths['layout'].read_text());checks=[]
    cases=[('last-page-outside-root','delta'),('duplicate-page','delta'),('payload-byte-differs','patch'),('unexpected-root-file','composed_root'),('root-already-installed','composed_root'),('ABI2-selected','plugin_result'),('stale-native-identity','native_identity'),('parent-install-not-complete','previous_result'),('wrong-root-header','root_window_header')]
    original=json.loads((D/'plan-inputs.json').read_text())
    for name,role in cases:
        T=O/name;T.mkdir();rows=json.loads(json.dumps(original));src=Path(rows[role]['path']);target=T/src.name;subprocess.run(['/bin/cp','-c',str(src),str(target)],check=True)
        if role=='patch':
            with target.open('r+b') as f:b=f.read(1);f.seek(0);f.write(bytes([b[0]^1]))
        elif role=='root_window_header':
            target.write_text(target.read_text().replace(','.join(hex(x) for x in bytes.fromhex(actual.RESULT_SHA)),','.join(hex(x) for x in bytes.fromhex(actual.BASE_SHA))))
        else:
            data=json.loads(target.read_text())
            if name=='last-page-outside-root':data['pages'][-1]['image_block']=actual.BLOCKS
            elif name=='duplicate-page':data['pages'][1]['image_block']=data['pages'][0]['image_block']
            elif name=='unexpected-root-file':data['monitored_after_sha256']['System/Library/Extensions/NativeAdrenoMetal.clients']='00'*32
            elif name=='root-already-installed':data['root_installed']=True
            elif name=='ABI2-selected':data['ABI']=2
            elif name=='stale-native-identity':data['expected_boot_tag']='00'*16
            elif name=='parent-install-not-complete':data['installed']=False
            target.write_text(json.dumps(data,indent=2)+'\n')
        rows[role]=dict(path=str(target),sha256=sha(target));manifest=T/'plan-inputs.json';manifest.write_text(json.dumps(rows,indent=2)+'\n');changed=re.sub(r"^INPUTS_SHA=.*$","INPUTS_SHA="+repr(sha(manifest)),text,flags=re.M);path=T/'metal_root_delta_plan.py';path.write_text(changed)
        try:module(path,'negative_'+name.replace('-','_')).load_plan()
        except ValueError as e:checks.append(dict(control=name,refused=str(e)))
        else:raise AssertionError(name)
    # The unchanged fixed adapter executes over local reads and a fake child,never ADB/USB/dd.
    sys.modules['metal_root_delta_plan']=actual;adapter=module(actual.paths['recovery_adapter'],'actual_recovery_adapter280')
    from zorn_ios26_root_install import PART
    fd=os.open(base,os.O_RDONLY)
    try:
        for mode in ['success','last-preimage','first-readback']:
            T=O/('adapter-'+mode);T.mkdir();events=[];verified=[]
            class Fake:
                adb=str(actual.paths['previous_adb']);deadline=time.monotonic()+600;recovery_identity={'family':'HOST-FIXTURE-NO-DEVICE'}
                def __init__(self):self.writing=False;self.pages={};self.reads=0;self.write_calls=0
                def command(self,args):
                    if args==['server-status']:return (self.adb+' usb_backend: NATIVE').encode()
                    if args==['shell','ps','-A','-o','PID,ARGS']:return b''
                    assert args==['shell','dd','--help'];return b'count_bytes fsync notrunc'
                def protections(self):return {'explicit-host-protection-fixture':b'unchanged'}
                def read(self,part,block,count):
                    assert part==PART and actual.FIRST<=block and 1<=count<=65 and block+count<=actual.FIRST+actual.BLOCKS;self.reads+=1;n=block-actual.FIRST
                    b=b''.join(self.pages.get(i,os.pread(fd,4096,i*4096)) for i in range(n,n+count))
                    if (mode=='last-preimage' and not self.writing and self.reads>len(retained) and n==parts[-1][0]) or (mode=='first-readback' and self.writing and self.write_calls==1):b=bytes([b[0]^1])+b[1:]
                    return b
                def start(self,args,**kw):
                    assert self.writing and args[:4]==['shell','-T','-e','none'];m=re.fullmatch(r'dd of='+re.escape(PART)+r' bs=4096 seek=(\d+) count=(\d+) iflag=count_bytes conv=notrunc,fsync status=none',args[4]);assert m;n=int(m[1])-actual.FIRST;size=int(m[2]);assert 0<=n<actual.BLOCKS and 0<size<=65*4096 and size%4096==0;self.write_calls+=1;outer=self
                    class Child:
                        returncode=0
                        def communicate(self,data,timeout):
                            assert len(data)==size and 0<timeout<=30
                            for k in range(0,len(data),4096):outer.pages[n+k//4096]=data[k:k+4096]
                        def kill(self):raise AssertionError('unexpected fixture kill')
                        def wait(self):raise AssertionError('unexpected fixture wait')
                    return Child()
            fake=Fake()
            def before(identity):assert fake.reads==len(retained)+len(parts);events.append('before-first-write');fake.writing=True
            def done(i,n,total):verified.append((i,n,total))
            if mode=='success':
                result=adapter.install(fake,T,before,done);assert events==['before-first-write'] and fake.write_calls==len(parts) and len(verified)==len(parts) and result['pages_written']==actual.PAGES and result['readback']['sha256']==layout['local_readback_sha256'];checks.append(dict(control='actual-adapter-complete-local-transport',groups=fake.write_calls,pages=result['pages_written']))
            else:
                try:adapter.install(fake,T,before,done)
                except RuntimeError as e:
                    assert ('preimage differs' if mode=='last-preimage' else 'readback differs') in str(e)
                    assert fake.write_calls==(0 if mode=='last-preimage' else 1) and not verified;checks.append(dict(control='actual-adapter-'+mode,write_calls=fake.write_calls,refused=str(e)))
                else:raise AssertionError(mode)
    finally:os.close(fd)
    # Execute the maintained run's real preclaim branch;all state/admission and
    # socket boundaries here are explicit fixtures. No real socket is opened.
    entry_path=Path(__file__).with_name('zorn_ios26_metal_root_delta.py').resolve()
    entry=module(entry_path,'actual_root_entry280')
    current_before=entry.CURRENT.read_bytes()
    entry.validate_admission=lambda *args: {}
    def unavailable(*args,**kwargs):raise OSError('HOST-FIXTURE existing listener absent')
    original_socket=entry.socket.create_connection;entry.socket.create_connection=unavailable
    target=O/'preclaim-listener-refusal'
    try:
        try:entry.run({},Path('HOST-ADMISSION-FIXTURE'),types.SimpleNamespace(run=target))
        except OSError as e:assert 'HOST-FIXTURE' in str(e)
        else:raise AssertionError('missing listener must refuse')
    finally:entry.socket.create_connection=original_socket
    assert not target.exists() and entry.CURRENT.read_bytes()==current_before
    checks.append(dict(control='actual-fixed-entry-absent-listener-before-claim',claim_created=False,current_state_changed=False))
    result=dict(passed=True,checks=checks,plan=dict(path=str(plan_path),sha256=sha(plan_path)),adapter=dict(path=str(actual.paths['recovery_adapter']),sha256=sha(actual.paths['recovery_adapter'])),test_tool=dict(path=str(Path(__file__).resolve()),sha256=sha(Path(__file__))),boundary='Actual plan/load/apply/Recovery-adapter functions;server identity,protections and child transport are explicit local fixtures,not real Recovery or storage evidence',phone_access=False,claim_created=False,root_installed=False)
    (O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS280 actual plan refusals and unchanged adapter complete/local-failure paths;no phone/claim')
if __name__=='__main__':main()

#!/usr/bin/env python3
"""Run the actual reviewed291 transport adapter against explicit host I/O.

The plan, source pages, delta, protection bytes and apply/readback code are real;
only the USB/process boundary is simulated. No installation receipt is created.
"""
import argparse,hashlib,json,os,re,tempfile,time
from pathlib import Path
import zorn_ios26_metal_root_delta as t

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir()
    scope=t.INSTALLS[t.KNOWN291_FLAG];review=t.validate_review(scope.review,scope)
    plan=t.reviewed_module(review,'plan_source','metal_root_delta_plan');adapter=t.reviewed_module(review,'recovery_adapter','root291_adapter_host')
    source,parts,retained=plan.load_plan();state=t.CURRENT.read_bytes();checks=[]
    class HostRecovery:
        def __init__(self,case):
            self.case=case;self.adb=review['pins']['previous_adb']['path'];self.deadline=time.monotonic()+600;self.recovery_identity=dict(family='TWRP',SYNTHETIC_ONLY=True);self.written={};self.writes=[];self.stage='before';self.calls=[]
        def command(self,args):
            self.calls.append(args)
            if args==['server-status']:return (self.adb+'\nusb_backend: NATIVE\n').encode()
            if args==['shell','ps','-A','-o','PID,ARGS']:return b'PID ARGS\n1 init\n'
            if args==['shell','dd','--help']:return b'count_bytes fsync notrunc'
            raise AssertionError('unexpected host-boundary command:'+str(args))
        def protections(self):
            return {k:Path(review['pins']['previous_'+v]['path']).read_bytes() for k,v in [('primary_GPT','primary_GPT'),('backup_GPT','backup_GPT'),('root_manifest','root_manifest'),('Data','Data'),('before','root_before'),('after','root_after'),('misc','misc')]}
        def read(self,part,block,count):
            assert part=='/dev/block/by-name/unixnu' and plan.FIRST<=block and block+count<=plan.FIRST+plan.BLOCKS and 1<=count<=65
            n=block-plan.FIRST
            with source.open('rb') as stream:data=os.pread(stream.fileno(),count*4096,n*4096)
            buf=bytearray(data)
            for i in range(count):
                if n+i in self.written:buf[i*4096:(i+1)*4096]=self.written[n+i]
            if self.case=='stale prior' and not self.writes and n==retained[0][0]:buf[0]^=1
            if self.case=='failed first readback' and self.writes and n==parts[0][0]:buf[0]^=1
            return bytes(buf)
        def start(self,args,**kwargs):
            assert self.stage=='writing' and args[:4]==['shell','-T','-e','none']
            match=re.fullmatch(r'dd of=/dev/block/by-name/unixnu bs=4096 seek=(\d+) count=(\d+) iflag=count_bytes conv=notrunc,fsync status=none',args[4]);assert match
            block,count=map(int,match.groups());idx=len(self.writes);assert block==plan.FIRST+parts[idx][0] and count==len(parts[idx][2]);parent=self
            class HostProcess:
                returncode=0
                def communicate(self,data,timeout):
                    assert 0<timeout<=30 and data==parts[idx][2]
                    parent.writes.append(block-plan.FIRST)
                    for i in range(len(data)//4096):parent.written[block-plan.FIRST+i]=data[i*4096:(i+1)*4096]
            return HostProcess()
    for case in ['complete','stale prior','failed first readback']:
        # Retained-readback clone must use the same volume as its reviewed source.
        with tempfile.TemporaryDirectory(prefix='HOST-ONLY-root291-',dir=scope.review.parent) as temp:
            io=HostRecovery(case);events=[]
            def before(identity):
                assert identity==io.recovery_identity and not io.writes;io.stage='writing';events.append('before')
            def group(index,block,pages):
                assert index==len(events)-1 and block==parts[index][0] and pages==sum(len(z)//4096 for _,_,z in parts[:index+1]);events.append(block)
            try:result=adapter.install(io,Path(temp),before,group)
            except RuntimeError as error:
                if case=='stale prior':assert not io.writes and 'prior changed page no longer matches' in str(error)
                elif case=='failed first readback':assert io.writes==[parts[0][0]] and 'readback differs' in str(error)
                else:raise
            else:
                assert case=='complete' and len(io.writes)==12 and result['pages_written']==31 and result['readback']['sha256']==json.loads(Path(review['pins']['layout']['path']).read_text())['local_readback_sha256']
                assert len(events)==13 and result['protected_metadata_and_fences_unchanged']
            checks.append(case+':actual reviewed adapter and apply_delta with explicit file-backed host boundary')
    assert t.CURRENT.read_bytes()==state and not scope.run.exists()
    pin=lambda p:dict(path=str(Path(p).resolve()),sha256=t.sha(p))
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,checks=checks,source=pin(t.__file__),runner=pin(t.RUNNER),test_tool=pin(__file__),plan=review['pins']['plan_source'],adapter=review['pins']['recovery_adapter'],review=pin(scope.review),simulated_USB_and_child_process_only=True,production_controller_unchanged=True,no_real_claim_or_installation_receipt=True,phone_access=False),indent=2)+'\n')
    print('PASS291 actual root adapter:31pages/12groups;stale prior and readback failure stop writes;host only')
if __name__=='__main__':main()

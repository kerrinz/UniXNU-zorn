#!/usr/bin/env python3
"""290 receiver/postprocessor on explicitly synthetic retained278 fixtures."""
import argparse,base64,copy,hashlib,json,struct,tempfile,zlib
import zorn_ios26_perf290_capture as post
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import zorn_ios26_gpu_v290_system_trial as t
import zorn_ios26_perf290_receiver as receiver
from zorn_ios26_perf290_capture import finish_capture

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir()
    parent=t.STAGE/'k80-gpu-v278-present-cost-840cdc02db2b41919a8fc2ba68dcccb3';old='840cdc02db2b41919a8fc2ba68dcccb3'
    original=parent/'perf-evidence-host/SYNTHETIC-retagged275-wire-plus-manual278.bin';raw=original.read_bytes();wire=bytearray();at=0
    while at<len(raw):
        tail=raw[at:]
        if tail.startswith(b'K80PF278'):
            n=1248;q=bytearray(tail[:n]);q[8:24]=bytes.fromhex(t.TAG);struct.pack_into('<I',q,1240,zlib.crc32(q[:1240]))
        elif tail.startswith(b'K80SH270'):
            n=68+struct.unpack_from('<I',tail,28)[0];q=bytearray(tail[:n]);q[8:24]=bytes.fromhex(t.TAG);struct.pack_into('<I',q,64,zlib.crc32(q[:64]))
        else:
            n=raw.index(b'\r\n',at)+2-at;q=tail[:n].replace(old.encode(),t.TAG.encode())
        wire.extend(q);at+=n
    wire=bytes(wire);page=bytearray((parent/'early-record-host/SYNTHETIC-native-page.bin').read_bytes());assert page[8:24]==bytes.fromhex(old);page[8:24]=bytes.fromhex(t.TAG);page[28:32]=bytes(4);struct.pack_into('<I',page,28,zlib.crc32(page[:544]))
    (a.out/'SYNTHETIC-wire290.bin').write_bytes(wire);(a.out/'SYNTHETIC-page290.bin').write_bytes(page);checks=[]
    def capture(*,data=wire,code=0,fields=None,missing_run=False):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            if data is not None:(out/'cdc.raw').write_bytes(data)
            (out/'before-log.bin').write_bytes(bytes(4096));(out/'after-log.bin').write_bytes(page)
            run=dict(scope=t.SCOPE,boot_attempts=1,fastboot_returned_success=True,recovery_identity_after=dict(family='TWRP'));run.update(fields or {})
            if not missing_run:(out/'run.json').write_text(json.dumps(run))
            x=finish_capture(out,tag=t.TAG,program_tag=t.PROBE_TAG,scope=t.SCOPE,runner_exit=code)
            assert x==json.loads((out/'cdc-capture.json').read_text()) and not x['full_GPU_qualification']
            if missing_run:assert (out/'ordinary290-stderr.bin').exists() and (out/'screen270-roi.bgrx').exists()
            try:finish_capture(out,tag=t.TAG,program_tag=t.PROBE_TAG,scope=t.SCOPE,runner_exit=code)
            except FileExistsError:pass
            else:raise AssertionError('capture overwritten')
            return x
    x=capture();assert not x['scalar_timing287']['complete'] and not x['scalar_timing287_with_recovery_observed'];assert x['verified'] and x['manual_observation_completed278_with_recovery_observed'] and x['serial_roi270_with_recovery_observed'];checks.append('actual290 capture completes on explicitly synthetic278cost/270ROI/native-page fixture;no hardware qualification')
    for name,kw in [('old boot',dict(data=raw)),('missing raw',dict(data=None)),('truncated',dict(data=wire[:-17])),('runner failure',dict(code=1)),('missing run',dict(missing_run=True)),('bool boot count',dict(fields=dict(boot_attempts=True))),('wrong scope',dict(fields=dict(scope='foreign'))),('two boots',dict(fields=dict(boot_attempts=2))),('no successful boot',dict(fields=dict(fastboot_returned_success=False))),('unknown recovery',dict(fields=dict(recovery_identity_after=dict(family='unknown'))))]:
        x=capture(**kw);assert not x['verified'] and not x['manual_observation_completed278_with_recovery_observed'];checks.append(name+' cannot qualify')
    # Keep the real protocol fixture, substituting only its explicitly synthetic
    # journal payload at the already decoded boundary to test scalar integration.
    original_inspect=post.inspect_progress
    base=original_inspect(wire,t.TAG,t.PROBE_TAG)
    table=b'T pipeline n=3 total=12ms max=8ms\nT library n=1 total=2ms max=2ms\nT function n=2 total=1ms max=1ms\nT compile n=2 total=7ms max=4ms cached=1\nG commit-to-complete n=3 total=9ms max=5ms mean=3000us\nJ scheduled wait n=3 total=1ms max=1ms\nJ completed wait n=3 total=9ms max=5ms t=0\nJ resource wait n=1 total=0ms max=0ms\nJ surface cache n=3 bytes=128 dup=0 us=2 max=1\n'
    def fragment(tag=t.TAG,count=2):
        return b''.join(('ZORN287COUNTERS run=%s sample=%d uptime_us=%d bytes=%d\n'%(tag,i,20000000+i*100000000,len(table))).encode()+table for i in range(count))
    for name,raw_journal,want_complete in [('complete',fragment(),True),('one report',fragment(count=1),False),('foreign boot',fragment(tag='0'*32),False),('partial',fragment()[:-10],False)]:
        v=copy.deepcopy(base);v['journal248'].update(stderr_base64=base64.b64encode(raw_journal).decode(),sha256=hashlib.sha256(raw_journal).hexdigest())
        with patch.object(post,'inspect_progress',return_value=v):
            x=capture()
        assert bool(x.get('scalar_timing287_with_recovery_observed'))==want_complete
        if name=='foreign boot':assert not x['verified'] and x['errors']
        checks.append('actual postprocessor scalar '+name+':synthetic journal boundary;no device evidence')
    rpc_fixture=(t.BASE/'rpc-decoder-host/SYNTHETIC-two-reports.bin').read_bytes().replace(b'a'*32,t.TAG.encode())
    for name,fragment,want in [('actual-schema',rpc_fixture,True),('loss',rpc_fixture.replace(b'NC meta 287 18 0 0 2000000000',b'NC meta 287 18 4 1 2000000000'),False)]:
        v=copy.deepcopy(base);v['journal248'].update(stderr_base64=base64.b64encode(fragment).decode(),sha256=hashlib.sha256(fragment).hexdigest())
        with patch.object(post,'inspect_progress',return_value=v):x=capture()
        assert x['verified'] and x['scalar_timing287_with_recovery_observed'] and x['native_RPC287_with_recovery_observed']==want
        assert x==json.loads(json.dumps(x))
        checks.append('actual postprocessor native RPC '+name+':explicit synthetic journal;no GPU evidence')
    class HostThread:
        def __init__(self,target):self.target=target
        def start(self):self.target()
        def join(self):pass
    registry='"idVendor" = 4617\n"idProduct" = 1\n"USB Serial Number" = "ZORN26'+t.TAG[:12].upper()+'"\n"IOCalloutDevice" = "/dev/cu.usbmodemHOST290"\n'
    assert receiver.find_port(registry,'ZORN26'+t.TAG[:12].upper()) and receiver.find_port(registry,'foreign') is None
    for case in ['success','runner failure','launch error','existing claim','bundle rejected']:
        with tempfile.TemporaryDirectory() as tmp:
            trial=Path(tmp)/'root-trial';out=trial/'trial';out.mkdir(parents=True);calls=[]
            (out/'before-log.bin').write_bytes(bytes(4096));(out/'after-log.bin').write_bytes(page)
            if case=='existing claim':(out/'one-shot.claim.json').write_text('HOST ONLY')
            def validate(path):
                calls.append('validate');assert path==trial/'bundle.json'
                if case=='bundle rejected':raise ValueError('HOST bad bundle')
            def receive(port,path,stop,deadline):
                assert calls==['validate','registry'] and port=='/dev/cu.usbmodemHOST290';calls.append('receive');path.write_bytes(wire)
            def run(args,**kwargs):
                if args[0]=='/usr/sbin/ioreg':assert calls==['validate'];calls.append('registry');return SimpleNamespace(returncode=0,stdout=registry)
                assert calls==['validate','registry','receive'] and args[2]==str(Path(receiver.__file__).with_name('run-zorn-debug.py'))
                assert args[3:]==['--ios26-perf290-trial','--bundle',str(trial/'bundle.json'),'--admission',str(trial/'admission.json')];calls.append('runner')
                if case=='launch error':raise OSError('HOST launch failure')
                (out/'run.json').write_text(json.dumps(dict(scope=t.SCOPE,boot_attempts=1,fastboot_returned_success=True,recovery_identity_after=dict(family='TWRP'))));return SimpleNamespace(returncode=int(case=='runner failure'))
            config=SimpleNamespace(TRIAL=trial,TAG=t.TAG,PROBE_TAG=t.PROBE_TAG,SCOPE=t.SCOPE,validate=validate)
            with patch.object(receiver,'Thread',HostThread),patch.object(receiver,'capture',receive),patch.object(receiver.subprocess,'run',run):
                if case in ['existing claim','bundle rejected']:
                    try:receiver.run_capture(config)
                    except ValueError:assert calls==['validate']
                    else:raise AssertionError(case)
                    assert not (out/'cdc-capture.json').exists()
                else:
                    code=receiver.run_capture(config);x=json.loads((out/'cdc-capture.json').read_text());assert (code==0)==(case=='success') and x['verified']==(case=='success')
            checks.append('actual receiver '+case+':validation then listener then fixed runner;exclusive output')
    pin=lambda p:dict(path=str(Path(p).resolve()),sha256=t.sha(p))
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,checks=checks,source=pin(receiver.__file__),receiver=pin(receiver.__file__),postprocessor=pin(Path(__file__).with_name('zorn_ios26_perf290_capture.py')),retained_serial_transport=pin(receiver.TRANSPORT_SOURCE),test_tool=pin(__file__),explicit_synthetic_fixtures=True,phone_access=False),indent=2)+'\n');print('PASS290 actual postprocessor/receiver controls;no phone')
if __name__=='__main__':main()

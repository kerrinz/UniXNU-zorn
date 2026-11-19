#!/usr/bin/env python3
"""284 receiver/postprocessor on explicitly synthetic retained278 fixtures."""
import argparse,copy,json,struct,tempfile,zlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import zorn_ios26_gpu_v284_system_trial as t
import zorn_ios26_perf284_receiver as receiver
from zorn_ios26_perf284_capture import finish_capture

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
    (a.out/'SYNTHETIC-wire284.bin').write_bytes(wire);(a.out/'SYNTHETIC-page284.bin').write_bytes(page);checks=[]
    def capture(*,data=wire,code=0,fields=None,missing_run=False):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            if data is not None:(out/'cdc.raw').write_bytes(data)
            (out/'before-log.bin').write_bytes(bytes(4096));(out/'after-log.bin').write_bytes(page)
            run=dict(scope=t.SCOPE,boot_attempts=1,fastboot_returned_success=True,recovery_identity_after=dict(family='TWRP'));run.update(fields or {})
            if not missing_run:(out/'run.json').write_text(json.dumps(run))
            x=finish_capture(out,tag=t.TAG,program_tag=t.PROBE_TAG,scope=t.SCOPE,runner_exit=code)
            assert x==json.loads((out/'cdc-capture.json').read_text()) and not x['full_GPU_qualification']
            if missing_run:assert (out/'ordinary284-stderr.bin').exists() and (out/'screen270-roi.bgrx').exists()
            try:finish_capture(out,tag=t.TAG,program_tag=t.PROBE_TAG,scope=t.SCOPE,runner_exit=code)
            except FileExistsError:pass
            else:raise AssertionError('capture overwritten')
            return x
    x=capture();assert x['verified'] and x['manual_observation_completed278_with_recovery_observed'] and x['serial_roi270_with_recovery_observed'];checks.append('actual284 capture completes on explicitly synthetic278cost/270ROI/native-page fixture;no hardware qualification')
    for name,kw in [('old boot',dict(data=raw)),('missing raw',dict(data=None)),('truncated',dict(data=wire[:-17])),('runner failure',dict(code=1)),('missing run',dict(missing_run=True)),('bool boot count',dict(fields=dict(boot_attempts=True))),('wrong scope',dict(fields=dict(scope='foreign'))),('two boots',dict(fields=dict(boot_attempts=2))),('no successful boot',dict(fields=dict(fastboot_returned_success=False))),('unknown recovery',dict(fields=dict(recovery_identity_after=dict(family='unknown'))))]:
        x=capture(**kw);assert not x['verified'] and not x['manual_observation_completed278_with_recovery_observed'];checks.append(name+' cannot qualify')
    class HostThread:
        def __init__(self,target):self.target=target
        def start(self):self.target()
        def join(self):pass
    registry='"idVendor" = 4617\n"idProduct" = 1\n"USB Serial Number" = "ZORN26'+t.TAG[:12].upper()+'"\n"IOCalloutDevice" = "/dev/cu.usbmodemHOST284"\n'
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
                assert calls==['validate','registry'] and port=='/dev/cu.usbmodemHOST284';calls.append('receive');path.write_bytes(wire)
            def run(args,**kwargs):
                if args[0]=='/usr/sbin/ioreg':assert calls==['validate'];calls.append('registry');return SimpleNamespace(returncode=0,stdout=registry)
                assert calls==['validate','registry','receive'] and args[2]==str(Path(receiver.__file__).with_name('run-zorn-debug.py'))
                assert args[3:]==['--ios26-perf284-trial','--bundle',str(trial/'bundle.json'),'--admission',str(trial/'admission.json')];calls.append('runner')
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
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,checks=checks,source=pin(receiver.__file__),receiver=pin(receiver.__file__),postprocessor=pin(Path(__file__).with_name('zorn_ios26_perf284_capture.py')),retained_serial_transport=pin(receiver.TRANSPORT_SOURCE),test_tool=pin(__file__),explicit_synthetic_fixtures=True,phone_access=False),indent=2)+'\n');print('PASS284 actual postprocessor/receiver controls;no phone')
if __name__=='__main__':main()

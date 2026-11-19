#!/usr/bin/env python3
"""Run actual receiver main through final JSON;all OS/phone boundaries explicit."""
import argparse,hashlib,importlib.util,json,tempfile
from pathlib import Path
from types import SimpleNamespace
import zorn_ios26_gpu_v273_system_trial as t
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);B=t.PACKAGE.parent.parent;bundle=t.validate(t.TRIAL/'bundle.json');source=Path(__file__).with_name('read-zorn-gpu-menu273-cdc.py');spec=importlib.util.spec_from_file_location('actual_receiver271',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);assert m.PROBE_TAG==t.PROBE_TAG
    raw=(B/'menu-evidence-host/SYNTHETIC-retagged271-wire-plus-menu273.bin').read_bytes();page=(B/'early-record-host/SYNTHETIC-native-page.bin').read_bytes();checks=[]
    original=dict(trial=t.TRIAL,validate=t.validate,Thread=m.Thread,capture=m.capture,run=m.subprocess.run)
    try:
        for code,existing in [(0,False),(1,False),(0,True)]:
            with tempfile.TemporaryDirectory() as temp:
                trial=Path(temp)/'root-trial';out=trial/'trial';out.mkdir(parents=True);calls=[];discovery=[0]
                t.TRIAL=trial;t.validate=lambda p:bundle
                (out/'before-log.bin').write_bytes(bytes(4096));(out/'after-log.bin').write_bytes(page)
                if existing:(out/'one-shot.claim.json').write_text('HOST-FIXTURE')
                class Thread:
                    def __init__(self,target):self.target=target
                    def start(self):self.target()
                    def join(self):pass
                m.Thread=Thread
                def capture(port,path,stop,deadline):
                    assert port=='/dev/cu.usbmodemHOST271' and path==out/'cdc.raw';calls.append('capture');path.write_bytes(raw)
                m.capture=capture
                def run(args,**kwargs):
                    if args[0]=='/usr/sbin/ioreg':
                        discovery[0]+=1
                        if discovery[0]>1:raise ValueError('host fixture unexpected repeat discovery')
                        identity='ZORN26'+t.TAG[:12].upper();return SimpleNamespace(returncode=0,stdout='"idVendor" = 4617\n"idProduct" = 1\n"USB Serial Number" = "'+identity+'"\n"IOCalloutDevice" = "/dev/cu.usbmodemHOST271"\n')
                    assert calls==['capture'] and args[2]==str(t.SOURCES['fixed_runner']) and args[3]=='--ios26-glass-menu273-trial' and args[-1]==str(trial/'admission.json');calls.append('runner')
                    (out/'run.json').write_text(json.dumps(dict(scope=t.SCOPE,boot_attempts=1,fastboot_returned_success=True,recovery_identity_after=dict(family='TWRP'))));return SimpleNamespace(returncode=code)
                m.subprocess.run=run
                if existing:
                    try:m.main()
                    except ValueError:checks.append('actual existing claim refuses before listener/runner')
                    else:raise AssertionError('existing claim')
                    assert not calls;continue
                result=m.main();receipt=json.loads((out/'cdc-capture.json').read_text());assert result==code and receipt['verified']==(code==0) and not receipt['full_GPU_qualification'] and calls==['capture','runner'];assert receipt['serial_roi270_with_recovery_observed']==(code==0) and receipt['synthetic_menu_dispatch_returned273_with_recovery_observed']==(code==0);checks.append('actual main listener-first,exact maintained runner flag/paths,final JSON writes;runner exit='+str(code))
    finally:
        t.TRIAL=original['trial'];t.validate=original['validate'];m.Thread=original['Thread'];m.capture=original['capture'];m.subprocess.run=original['run']
    pin=lambda p:dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest());result=dict(passed=True,checks=checks,actual_receiver=pin(source),actual_postprocessor=pin(Path(__file__).with_name('zorn_ios26_menu273_capture.py')),test_tool=pin(Path(__file__)),actual_selected_program_tag=t.PROBE_TAG,actual_main_and_find_port_executed=True,thread_serial_IO_registry_and_runner_boundaries_stubbed=True,explicit_synthetic_wire_and_early_page_not_hardware=True,actual_current_bundle_validated_before_mocking=True,phone_access=False,new_boot_or_claim=False);(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS273 actual receiver.main through listener/runner/postprocess/finalJSON and preexisting-claim refusal;no phone')
if __name__=='__main__':main()

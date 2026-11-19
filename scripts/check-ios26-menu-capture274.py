#!/usr/bin/env python3
"""Execute actual274 postprocessing through serialization with explicit fixtures."""
import argparse,hashlib,json,struct,tempfile,zlib
from pathlib import Path
from zorn_ios26_menu274_capture import finish_capture
from inspect_ios26_ui_menu274 import split_menu
from inspect_ios26_ui_roi270 import split_roi
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--daemon-fixture',type=Path,required=True);p.add_argument('--page',type=Path,required=True);p.add_argument('--tag',required=True);p.add_argument('--program-tag',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);raw=a.fixture.read_bytes();scope='HOST-ONLY-explicit274-fixture';checks=[]
    def run(data,*,code=0,errors=(),changed_run=None):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp);(out/'cdc.raw').write_bytes(data);(out/'before-log.bin').write_bytes(bytes(4096));(out/'after-log.bin').write_bytes(a.page.read_bytes());r=dict(scope=scope,boot_attempts=1,fastboot_returned_success=True,recovery_identity_after=dict(family='TWRP'));r.update(changed_run or {});(out/'run.json').write_text(json.dumps(r))
            v=finish_capture(out,tag=a.tag,program_tag=a.program_tag,scope=scope,runner_exit=code,transport_errors=errors,port='HOST-FIXTURE-NO-USB');loaded=json.loads((out/'cdc-capture.json').read_text());assert loaded==v and all(type(k) is str for k in v)
            return v
    r=run(raw);assert r['verified'] and r['serial_roi270_with_recovery_observed'] and r['synthetic_menu_dispatch_returned274_with_recovery_observed'] and not r['full_GPU_qualification'];checks.append('actual postprocessing saves screenshot/journal/JSON with independent string keys;roundtrip exact')
    r=run(a.daemon_fixture.read_bytes());assert r['verified'] and r['synthetic_menu_dispatch_returned274_with_recovery_observed'] and not r['Metal_probe267']['bounded_probe_and_required_lifecycle_complete'] and not r['ordinary_daemon_exit_required274'];checks.append('explicit retagged actual266 live-daemon prefix without probe exit/four closes remains transport-only')
    for label,kwargs in [('runner-failure',dict(code=1)),('transport-error',dict(errors=['explicit read error'])),('foreign-scope',dict(changed_run=dict(scope='foreign'))),('two-boots',dict(changed_run=dict(boot_attempts=2))),('no-fastboot',dict(changed_run=dict(fastboot_returned_success=False))),('unknown-Recovery',dict(changed_run=dict(recovery_identity_after=dict(family='unknown'))))]:
        v=run(raw,**kwargs);assert not v['verified'] and not v['serial_roi270_with_recovery_observed'] and not v['synthetic_menu_dispatch_returned274_with_recovery_observed'];checks.append(label+' cannot qualify with Recovery')
    v=run(raw[:raw.index(b'K80UI274')+287]);assert not v['verified'];checks.append('partial288byteUI refuses transport')
    bad=bytearray(raw);at=raw.index(b'K80UI274');struct.pack_into('<I',bad,at+24,7);struct.pack_into('<I',bad,at+88,3);struct.pack_into('<I',bad,at+280,zlib.crc32(bad[at:at+280]));v=run(bytes(bad));assert v['verified'] and v['serial_roi270_with_recovery_observed'] and not v['synthetic_menu_dispatch_returned274_with_recovery_observed'];checks.append('failed gesture keeps actual complete ROI grade independent')
    v=run(raw.replace(a.tag.encode(),b'0'*32));assert not v['verified'];checks.append('foreign normal boot identity refused')
    v=run(b'');assert not v['verified'];checks.append('empty wire refused')
    pin=lambda p:dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest());result=dict(passed=True,checks=checks,source=pin(Path(__file__).with_name('zorn_ios26_menu274_capture.py')),test_tool=pin(Path(__file__)),explicit_synthetic_fixtures=[pin(a.fixture),pin(a.daemon_fixture),pin(a.page)],postprocessing_includes_real_final_JSON_write=True,phone_access=False,new_boot_or_retry=False,hardware_qualified=False);(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS274 actual host postprocessor through JSON serialization,',len(checks),'controls;no phone')
if __name__=='__main__':main()

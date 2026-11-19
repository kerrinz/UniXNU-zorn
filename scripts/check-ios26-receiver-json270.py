#!/usr/bin/env python3
"""Exercise actual receiver postprocessing THROUGH json.dump,not only a dict."""
import argparse,base64,hashlib,importlib.util,json,struct,tempfile,textwrap,zlib
from pathlib import Path
from types import SimpleNamespace

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--trial',type=Path,required=True);p.add_argument('--old-receiver',type=Path,required=True);p.add_argument('--receiver',type=Path,required=True);p.add_argument('--tag',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    spec=importlib.util.spec_from_file_location('actual_fixed270',a.receiver);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);raw=(a.trial/'trial/cdc.raw').read_bytes();checks=[]
    def execute(source,data,label,expected_failure=False):
        text=source.read_text();part=textwrap.dedent(text[text.index('    run_file = '):text.index('    print(json.dumps')])
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp);report=out/'report.json'
            for n in ['run.json','before-log.bin','after-log.bin']:(out/n).write_bytes((a.trial/'trial'/n).read_bytes())
            path=out/'cdc.raw';path.write_bytes(data);ns=dict(out=out,raw=path,report=report,result=SimpleNamespace(returncode=0),TAG=a.tag,PROBE_TAG=module.PROBE_TAG,json=json,base64=base64,hashlib=hashlib,errors=[],ports=['HOST-REGRESSION-REAL270-BYTES'])
            try:exec(part,ns)
            except TypeError as error:
                assert expected_failure and 'keys must be' in str(error),str(error);checks.append(label+':actual old json.dump tuple-key failure reproduced');return None
            assert not expected_failure,label
            result=json.loads(report.read_text());assert result['verified'] and result['runner_exit']==0 and not result['errors'];assert all(type(k) is str for k in ns['verdict']);checks.append(label+':actual json.dump and JSON roundtrip passed');return result
    execute(a.old_receiver,raw,'original selected receiver',True)
    current=execute(a.receiver,raw,'minimal fixed receiver')
    assert current['serial_roi270_with_recovery_observed'] and current['synthetic_scene_dispatch_returned269_with_recovery_observed'] and not current['full_GPU_qualification']
    # Explicit synthetic UI failure on the same exact real wire. Keep the ROI
    # intact:its source image capture grade must be independent of gesture grade.
    from inspect_ios26_ui_roi270 import ROI_MAGIC
    data=bytearray(raw);at=0;modified=False
    while at<len(data):
        tail=data[at:]
        if tail.startswith(ROI_MAGIC):at+=68+struct.unpack_from('<I',tail,28)[0];continue
        if tail.startswith(b'K80UI269'):
            struct.pack_into('<I',data,at+24,7);struct.pack_into('<I',data,at+24+7*4,0xe00002c0);struct.pack_into('<I',data,at+24+15*4,3);struct.pack_into('<I',data,at+88,zlib.crc32(data[at:at+88]));modified=True;break
        at=data.index(b'\r\n',at)+2
    assert modified
    failed=execute(a.receiver,bytes(data),'explicit synthetic failed gesture with real intact ROI')
    assert failed['serial_roi270_with_recovery_observed'] and not failed['synthetic_scene_dispatch_returned269_with_recovery_observed'];checks.append('ROI and gesture grades serialized as independent string keys')
    pin=lambda p:dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest());result=dict(passed=True,checks=checks,actual_receiver=pin(a.receiver),original_failed_receiver=pin(a.old_receiver),actual_wire=pin(a.trial/'trial/cdc.raw'),actual_module_program_tag=module.PROBE_TAG,postprocessing_includes_real_json_dump=True,original_failure_and_partial_receipt_preserved=True,synthetic_UI_failure_only_for_grade_independence=True,phone_access=False,new_boot_or_retry=False);(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS270 actual receiver finalJSON regression,oldfailure reproduced and independent ROI/gesture grades roundtripped;no boot/retry')
if __name__=='__main__':main()

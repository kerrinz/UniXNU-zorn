#!/usr/bin/env python3
"""Reproduce missing281 decoder role and execute the actual shared consumer."""
import argparse,ast,copy,hashlib,inspect,json
from pathlib import Path
import zorn_ios26_gpu_v281_system_trial as t
from zorn_gpu_ios26_platform_record import artifact_tag,record_inspector


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    old=t.load(t.TRIAL/'bundle.json');run=t.TRIAL/'trial';checks=[]
    try:record_inspector(old)
    except KeyError as e:
        assert e.args==('record_decoder',);checks.append('actual original shared consumer KeyError(record_decoder) reproduced offline')
    else:raise AssertionError('original bundle unexpectedly contains decoder role')
    fixed=copy.deepcopy(old);fixed['pins']['record_decoder']=old['pins']['inspect_ios26_gpu_early252_record.py']
    decoder=record_inspector(fixed);tag=artifact_tag(fixed);assert tag==bytes.fromhex(t.TAG)
    decoded=decoder((run/'after-log.bin').read_bytes(),tag,(run/'before-log.bin').read_bytes())
    result=t.record_result(decoded);assert decoded['cpu_online']==8 and result['root_mount_proven'] and not result['GPU_started']
    checks.append('actual pinned decoder factory,artifact_tag,real captured pages and exact record_result callback complete;not a new run')
    # Protect the imported consumer contract as well as literal main-run roles.
    roles=set()
    for f in (artifact_tag,record_inspector):
        tree=ast.parse(inspect.getsource(f))
        for n in ast.walk(tree):
            if isinstance(n,ast.Subscript) and isinstance(n.value,ast.Subscript) and isinstance(n.value.value,ast.Name) and n.value.value.id=='bundle' and isinstance(n.value.slice,ast.Constant) and n.value.slice.value=='pins' and isinstance(n.slice,ast.Constant):roles.add(n.slice.value)
    assert roles=={'record_identity','record_decoder'} and roles<=t.ARTIFACTS|t.SOURCES.keys()
    assert t.SOURCES['record_decoder']==Path(fixed['pins']['record_decoder']['path'])
    checks.append('shared helper semantic roles are declared in current entry before device activation')
    try:decoder((run/'after-log.bin').read_bytes(),tag,(run/'after-log.bin').read_bytes())
    except ValueError:checks.append('actual shared decoder still refuses stale record')
    else:raise AssertionError('stale record')
    def pin(p):
        p=Path(p).resolve();return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    report=dict(passed=True,checks=checks,source=pin(t.__file__),helper=pin(Path(inspect.getfile(record_inspector))),test_tool=pin(__file__),original_bundle=pin(t.TRIAL/'bundle.json'),actual_after_log=pin(run/'after-log.bin'),actual_before_log=pin(run/'before-log.bin'),decoded_record=decoded,callback_result=result,original_receipts_unchanged=True,phone_access=False,new_boot_or_claim=False,full_GPU_qualification=False)
    (a.out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS281 actual record consumer role regression;original failure reproduced;no device action')


if __name__=='__main__':main()

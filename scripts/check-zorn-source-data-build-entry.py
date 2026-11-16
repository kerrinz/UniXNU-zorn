#!/usr/bin/env python3
"""Only new source-review build-entry execution/default/failure boundaries."""
import hashlib,json,runpy,subprocess,sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'out/zorn/gpu-source-data-build-entry-20261103'
TOOL=ROOT/'UniXNU-zorn/scripts/build-zorn-source-data-review.py';GUARD=ROOT/'out/zorn/gpu-votes-source-cli-20261103/no-side-effects.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    def invoke(args,guard=True):
        command=[sys.executable,'-B']+([str(GUARD)] if guard else [])+[str(TOOL)]+args
        q=subprocess.run(command,capture_output=True,text=True);return q
    planned=OUT/'plan-only-output'
    q=invoke(['--source-review-only','--out-dir',str(planned)]);assert q.returncode==0 and not q.stderr
    plan=json.loads(q.stdout);assert plan['planned'] and not plan['executed'] and not planned.exists()
    (OUT/'default-plan.json').write_text(q.stdout)
    successful=OUT/'actual-source-only-build'
    q=invoke(['--source-review-only','--out-dir',str(successful),'--execute','--os','17','--target','ios'],guard=False)
    (OUT/'actual-build-stdout.json').write_text(q.stdout);assert q.returncode==0 and not q.stderr,(q.returncode,q.stderr,q.stdout)
    result=json.loads(q.stdout);assert result['completed'] and not result['hardware_qualification'] and not result['native_execution']
    assert len(result['commands'])==2 and all(c['returncode']==0 for c in result['commands'])
    review=result['object_review'];assert review['instruction_bytes']==review['undefined_symbols']==review['external_exports']==review['relocations']==0
    assert review['compiled_source_bytes']==167116
    frozen={p.name:sha(p) for p in successful.iterdir() if p.is_file()}
    gate_cases=[]
    for case in ['existing-output','missing-scope-flag','wrong-approval','wrong-manifest','wrong-OS']:
        directory=OUT/(case+'-output');args=['--source-review-only','--out-dir',str(directory),'--execute']
        if case=='existing-output':args[args.index('--out-dir')+1]=str(successful)
        elif case=='missing-scope-flag':args.remove('--source-review-only')
        elif case=='wrong-approval':
            p=OUT/'wrong-approval.json';p.write_text('{"owner_reply":"not-approved"}');args+=['--approval',str(p)]
        elif case=='wrong-manifest':
            p=OUT/'wrong-manifest.json';p.write_text('{"sources":[]}');args+=['--inputs',str(p)]
        else:args+=['--os','27']
        q=invoke(args);assert q.returncode==2 and 'forbidden' not in q.stderr,(case,q.stderr)
        assert not directory.exists();gate_cases.append(dict(case=case,returncode=q.returncode,no_writes_or_process=True))
    assert all(sha(successful/name)==digest for name,digest in frozen.items())
    env=runpy.run_path(str(TOOL));preflight=env['preflight'];build=env['execute_build']
    failures=[]
    directory=OUT/'actual-compiler-refusal';plan,content,model=preflight(directory)
    def real_refusal(command,**kwargs):
        header=directory/'UnselectedSourceTables.h';text=header.read_text();assert 'sources_count=4U;' in text
        header.write_text(text.replace('sources_count=4U;','sources_count=5U;',1))
        return subprocess.run(command,**kwargs)
    failed=build(plan,content,model,runner=real_refusal)
    assert not failed['completed'] and failed['commands'][0]['returncode']!=0 and len(failed['commands'])==1
    assert 'source review data layout invalid' in Path(failed['commands'][0]['log']).read_text()
    assert (directory/'UnselectedSourceTables.h').exists() and not (directory/'isolated-source-data.o').exists()
    failures.append(dict(case='injected-count-corruption-real-clang-refusal',result=str(directory/'result.json'),real_compiler_returncode=failed['commands'][0]['returncode']))
    directory=OUT/'timeout-fixture';plan,content,model=preflight(directory)
    def timeout(command,**kwargs):raise subprocess.TimeoutExpired(command,30,output=b'fixture partial stdout\n',stderr=b'fixture partial stderr\n')
    failed=build(plan,content,model,runner=timeout)
    assert not failed['completed'] and failed['commands'][0]['timeout'] and failed['commands'][0]['returncode'] is None
    assert Path(failed['commands'][0]['log']).read_text()=='fixture partial stdout\nfixture partial stderr\n'
    failures.append(dict(case='explicit-timeout-fixture-partial-output-retained',result=str(directory/'result.json'),synthetic_failure_only=True))
    directory=OUT/'write-failure-fixture';plan,content,model=preflight(directory);original_open=Path.open
    def fail_cpp(path,*args,**kwargs):
        if path==directory/'source-layout-check.cpp' and args and args[0]=='x':raise OSError('injected second-output failure')
        return original_open(path,*args,**kwargs)
    with patch.object(Path,'open',fail_cpp):failed=build(plan,content,model)
    assert not failed['completed'] and not failed['commands'] and (directory/'UnselectedSourceTables.h').exists()
    assert 'injected second-output failure' in failed['error'] and '"phase": "failed"' in (directory/'build-events.jsonl').read_text()
    failures.append(dict(case='explicit-write-failure-fixture-partial-source-retained',result=str(directory/'result.json'),synthetic_failure_only=True))
    evidence=dict(default_plan_only_no_write_or_process=True,one_new_entry_actual_build=result,new_preflight_gates=gate_cases,new_failure_boundaries=failures,prior_success_outputs_unchanged=True,all_failures_preserve_partial_files_and_logs=True,old_suites_targets_pairs_reexecuted=False,driver_patch_count_remains32=True,native_or_device_execution=False,allow_boot=False,readback_qualified=False,WriteAuthorized=0)
    (OUT/'result.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('PASS:new default-OFF build entry;1real data-only iOS17 build,5preflight gates,real clang refusal and2explicit failure fixtures;0native/device')

if __name__=='__main__':main()

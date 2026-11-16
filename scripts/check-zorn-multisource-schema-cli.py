#!/usr/bin/env python3
"""New opt-in schema-diagnostics integration checks only."""
import copy,hashlib,json,runpy,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'out/zorn/gpu-multisource-schema-cli-20261103'
TOOL=ROOT/'UniXNU-zorn/scripts/compare-zorn-gpu-power-sources.py';GUARD=ROOT/'out/zorn/gpu-votes-source-cli-20261103/no-side-effects.py'
MANIFEST=ROOT/'out/zorn/gpu-power-source-compare-20261103/inputs.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    def invoke(p,flag=False,digest=None):
        args=[sys.executable,'-B',str(GUARD),str(TOOL),'--inputs',str(p),'--sha256',digest or sha(p)]
        if flag:args+=['--schema-diagnostics']
        q=subprocess.run(args,capture_output=True,text=True);assert not q.stderr,q.stderr
        d=json.loads(q.stdout);assert not d['generated_policy'] and not d['hardware_qualification'];return q.returncode,d
    old=json.loads((ROOT/'out/zorn/gpu-power-source-compare-20261103/comparison.json').read_text())
    code,plain=invoke(MANIFEST);assert code==0 and plain==old and 'prepare_allowed' not in plain
    code,d=invoke(MANIFEST,True);assert code==2 and d['compared'] and d['source_schemas_compatible'] is False and d['prepare_allowed'] is False
    for source in d['sources']:
        diag=source['schema_diagnostics'];assert not diag['prepare_allowed'] and not diag['pure_source_check']['compatible'] and 'multi-SKU/bin' in diag['pure_source_check']['error']
        assert len([r for r in diag['diagnostics'] if r['issue']=='multi_table_metadata'])==4
        assert len([r for r in diag['diagnostics'] if r['issue']=='cell_pairs_not_opp_children'])==1
    stripped=copy.deepcopy(d);del stripped['source_schemas_compatible'];del stripped['prepare_allowed']
    for source in stripped['sources']:del source['schema_diagnostics']
    assert stripped==plain
    (OUT/'combined-result.json').write_text(json.dumps(d,indent=2)+'\n')
    cases=[]
    code,r=invoke(MANIFEST,True,digest='0'*64);assert code==2 and not r['compared'];cases.append(dict(case='flag-cannot-bypass-manifest-SHA',error=r['error']))
    forged=json.loads(MANIFEST.read_text());forged['sources'][0]['schema_diagnostics']={'pure_source_check':{'compatible':True}}
    p=OUT/'self-signed-diagnostics.json';p.write_text(json.dumps(forged));code,r=invoke(p,True);assert code==2 and not r['compared'];cases.append(dict(case='self-signed-compatibility-rejected',error=r['error']))
    # New pin failure route;the maintained helper is never modified.
    env=runpy.run_path(str(TOOL));fn=env['inspect_inputs'];original_pin=fn.__globals__['DIAGNOSTICS_SHA'];fn.__globals__['DIAGNOSTICS_SHA']='0'*64
    try:
        try:fn(json.loads(MANIFEST.read_text()),True)
        except ValueError as exc:assert 'pinned source diagnostics changed' in str(exc);cases.append(dict(case='pinned-diagnostics-required',error=str(exc)))
        else:raise AssertionError('pin mismatch accepted')
    finally:fn.__globals__['DIAGNOSTICS_SHA']=original_pin
    (OUT/'result.json').write_text(json.dumps(dict(default_output_exactly_matches_prior_comparison=True,opt_in_compared=True,opt_in_source_count=4,opt_in_incompatible_exit=2,all_per_source_pure_refusals_preserved=True,no_prepare_permission=True,new_gate_checks=cases,child_no_write_or_process=True,headers=0,prepare_audit_formatter_executed=False,old_suites_reexecuted=False,driver_patch_count_remains32=True,allow_boot=False,readback_qualified=False,WriteAuthorized=0),indent=2)+'\n')
    print('PASS:opt-in4source diagnostics retain refusal/exit2;default comparison unchanged;3new gate checks;0headers/prepare/native')
if __name__=='__main__':main()

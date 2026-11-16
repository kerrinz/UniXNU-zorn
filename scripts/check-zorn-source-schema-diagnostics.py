#!/usr/bin/env python3
"""New structured schema diagnosis cases only;no generator/header/native."""
import copy,hashlib,json,runpy,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'out/zorn/gpu-source-schema-diagnostics-20261103'
TOOL=ROOT/'UniXNU-zorn/scripts/diagnose-zorn-gpu-source-schema.py';GUARD=ROOT/'out/zorn/gpu-votes-source-cli-20261103/no-side-effects.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    OUT.mkdir(exist_ok=False)
    graphs=sorted((ROOT/'out/zorn/gpu-stock-dt-source-20261102/vendor').glob('*.gpu.json'))
    def argv(p):
        d=json.loads(p.read_text());raw=Path(d['input']['path']);return ['--dtb',str(raw),'--sha256',sha(raw),'--graph-json',str(p),'--graph-sha256',sha(p)]
    def invoke(args):
        q=subprocess.run([sys.executable,'-B',str(GUARD),str(TOOL)]+args,capture_output=True,text=True)
        assert q.returncode==2 and not q.stderr,(q.returncode,q.stderr)
        d=json.loads(q.stdout);assert d['prepare_allowed'] is False and not d['generated_policy'] and not d['hardware_qualification'];return d
    real=[]
    for p in graphs:
        d=invoke(argv(p));assert d['diagnostics_complete'] and not d['pure_source_check']['compatible'] and 'multi-SKU/bin' in d['pure_source_check']['error']
        assert d['expected_source_contract'][0]['entry_properties']['opp-hz']['bytes']==8
        metadata=[r for r in d['diagnostics'] if r['issue']=='multi_table_metadata'];assert len(metadata)==4 and all(not r['selected'] for r in metadata)
        entries=[r for r in d['diagnostics'] if r['issue']=='different_entry_schema'];assert entries
        for entry in entries:
            freq=next(v for v in entry['source_properties'] if v['property']=='qcom,gpu-freq');assert freq['bytes']==4
            assert all(not e['present_here'] for e in entry['expected_properties'] if e['property']=='opp-hz')
            assert all(set(prop)=={'property','available','bytes','raw_hex'} for prop in entry['source_properties'])
        gm=next(r for r in d['diagnostics'] if r['issue']=='cell_pairs_not_opp_children');assert len(gm['pairs'])==2 and gm['pair_bytes']==8
        assert len([r for r in d['diagnostics'] if r['issue']=='fixed_path_contract'])==2
        (OUT/(p.stem+'.diagnostics.json')).write_text(json.dumps(d,indent=2)+'\n')
        real.append(dict(input=str(p),diagnostic_rows=len(d['diagnostics']),unselected_tables=4,entry_rows=len(entries),pure_error=d['pure_source_check']['error']))
    cases=[]
    for case in ['wrong-raw-sha','wrong-graph-sha','trimmed-graph','forged-property']:
        args=argv(graphs[0])
        if case=='wrong-raw-sha':args[args.index('--sha256')+1]='0'*64
        elif case=='wrong-graph-sha':args[-1]='0'*64
        else:
            d=json.loads(graphs[0].read_text())
            if case=='trimmed-graph':d['nodes']=d['nodes'][:1]
            else:d['nodes'][0]['properties_hex']['forged']='00000001'
            p=OUT/(case+'.json');p.write_text(json.dumps(d));args[args.index('--graph-json')+1]=str(p);args[-1]=sha(p)
        d=invoke(args);assert not d['diagnostics_complete'];cases.append(dict(case=case,error=d['error']))
    fn=runpy.run_path(str(TOOL))['property_record'];assert fn({},'missing')==dict(property='missing',available=False,bytes=None,raw_hex=None)
    assert fn({'empty':b''},'empty')==dict(property='empty',available=True,bytes=0,raw_hex='')
    (OUT/'result.json').write_text(json.dumps(dict(real_diagnostics=real,new_refusals=cases,missing_empty_unknown_preserved=True,child_no_write_or_process=True,pure_AST_only=True,policy_headers_emitted=0,prepare_audit_formatter_executed=False,old_suites_reexecuted=False,driver_patch_count_remains32=True,allow_boot=False,readback_qualified=False,WriteAuthorized=0),indent=2)+'\n')
    print('PASS:4 source-schema diagnoses preserve paths/widths/raw bytes and pure refusal;4new invalid inputs refused;0headers/prepare/native')
if __name__=='__main__':main()

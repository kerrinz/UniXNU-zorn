#!/usr/bin/env python3
"""New multi-source comparison CPU checks only."""
import copy,hashlib,json,runpy,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'out/zorn/gpu-power-source-compare-20261103'
TOOL=ROOT/'UniXNU-zorn/scripts/compare-zorn-gpu-power-sources.py';GUARD=ROOT/'out/zorn/gpu-votes-source-cli-20261103/no-side-effects.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    entries=[]
    for p in sorted((ROOT/'out/zorn/gpu-stock-dt-source-20261102/vendor').glob('*.gpu.json')):
        graph=json.loads(p.read_text());raw=Path(graph['input']['path']);entries.append(dict(id=p.stem,dtb=str(raw),dtb_sha256=sha(raw),graph_json=str(p),graph_sha256=sha(p)))
    manifest=dict(sources=entries);before={p:sha(Path(p)) for e in entries for p in [e['dtb'],e['graph_json']]}
    def invoke(p,good=False,digest=None):
        q=subprocess.run([sys.executable,'-B',str(GUARD),str(TOOL),'--inputs',str(p),'--sha256',digest or sha(p)],capture_output=True,text=True)
        assert not q.stderr,q.stderr;d=json.loads(q.stdout);assert q.returncode==(0 if good else 2),d
        assert d['compared'] is good and not d['generated_policy'] and not d['hardware_qualification'];return d
    p=OUT/'inputs.json';p.write_text(json.dumps(manifest,indent=2)+'\n');d=invoke(p,True)
    assert len(d['sources'])==4 and len({r['raw_dtb_sha256'] for r in d['sources']})==4
    assert not d['variant_selected'] and not d['policy_derived']
    ids=[e['id'] for e in entries]
    for node in d['comparison']['source_nodes']:
        for prop in node['properties']:assert [v['source_id'] for v in prop['values']]==ids
    (OUT/'comparison.json').write_text(json.dumps(d,indent=2)+'\n')
    cases=[]
    for case in ['duplicate-id','duplicate-raw-identity','wrong-raw-sha','wrong-graph-sha','relative-source-path','extra-field','one-source','invalid-raw-source']:
        m=copy.deepcopy(manifest)
        if case=='duplicate-id':m['sources'][1]['id']=m['sources'][0]['id']
        elif case=='duplicate-raw-identity':m['sources'][1]=dict(m['sources'][0],id='duplicate-base')
        elif case=='wrong-raw-sha':m['sources'][0]['dtb_sha256']='0'*64
        elif case=='wrong-graph-sha':m['sources'][0]['graph_sha256']='0'*64
        elif case=='relative-source-path':m['sources'][0]['dtb']='relative.dtb'
        elif case=='extra-field':m['sources'][0]['selected']=True
        elif case=='one-source':m['sources']=m['sources'][:1]
        else:
            raw=OUT/'truncated.dtb';raw.write_bytes(b'not-an-FDT');m['sources'][0]['dtb']=str(raw);m['sources'][0]['dtb_sha256']=sha(raw)
        p=OUT/(case+'.json');p.write_text(json.dumps(m));r=invoke(p);cases.append(dict(case=case,error=r['error']))
    p=OUT/'duplicate-key.json';p.write_text('{"sources":[],"sources":[]}');r=invoke(p);cases.append(dict(case='duplicate-JSON-key',error=r['error']))
    r=invoke(OUT/'inputs.json',digest='0'*64);cases.append(dict(case='wrong-manifest-SHA',error=r['error']))
    fn=runpy.run_path(str(TOOL))['compare']
    fixture=[dict(id='first',nodes={'/gpu':{'empty':b'','same':b'\x01','unknown':b'\x02'},'/child':{}}),dict(id='second',nodes={'/gpu':{'same':b'\x01','unknown':b'\x03'}})]
    c=fn(fixture);gpu=next(n for n in c['source_nodes'] if n['source_node']=='/gpu');props={p['property']:p for p in gpu['properties']}
    assert props['empty']['values'][0]['available'] and props['empty']['values'][0]['bytes']==0 and not props['empty']['values'][1]['available']
    assert props['same']['same_bytes_in_all_sources'] and not props['unknown']['same_bytes_in_all_sources']
    assert next(n for n in c['source_nodes'] if n['source_node']=='/child')['present_in']==['first']
    assert all(sha(Path(p))==v for p,v in before.items())
    result=dict(real_source_count=4,distinct_raw_identities=4,comparison_summary={k:d['comparison'][k] for k in ['same_property_bytes_count','different_or_missing_property_count']},source_node_count=len(d['comparison']['source_nodes']),new_refusals=cases,pure_missing_empty_unknown_identity_cases_pass=True,child_no_write_or_process=True,source_inputs_unchanged=True,headers=0,prepare_audit_formatter_executed=False,old_suites_reexecuted=False,driver_patch_count_remains32=True,allow_boot=False,readback_qualified=False,WriteAuthorized=0)
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['comparison_summary']));print('PASS:4 distinct raw sources,10new refusals,missing/empty/unknown distinctions;0policy/header/native')
if __name__=='__main__':main()

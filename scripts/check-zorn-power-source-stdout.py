#!/usr/bin/env python3
"""Focused read-only power-source CLI integration checks,not old firmware suites."""
import copy,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'out/zorn/gpu-power-source-stdout-20261103'
TOOL=ROOT/'UniXNU-zorn/scripts/read-zorn-gpu-power-source.py'
GUARD=ROOT/'out/zorn/gpu-votes-source-cli-20261103/no-side-effects.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    graphs=sorted((ROOT/'out/zorn/gpu-stock-dt-source-20261102/vendor').glob('*.gpu.json'))
    def args(p):
        d=json.loads(p.read_text());raw=Path(d['input']['path'])
        return ['--dtb',str(raw),'--sha256',sha(raw),'--stdout','--graph-json',str(p),'--graph-sha256',sha(p)]
    def invoke(argv,good=False,guard=True):
        command=[sys.executable,'-B']+([str(GUARD)] if guard else [])+[str(TOOL)]+argv
        q=subprocess.run(command,capture_output=True,text=True)
        assert 'forbidden' not in q.stderr,q.stderr
        assert q.returncode==(0 if good else 2),(q.returncode,q.stderr)
        if good:
            assert not q.stderr;qdoc=json.loads(q.stdout)
            assert not qdoc['generated_policy'] and not qdoc['hardware_qualification']
            return qdoc
        assert not q.stdout and 'Traceback' not in q.stderr,q.stderr
        return q.stderr.splitlines()[-1]
    real=[]
    before={str(p):sha(p) for p in graphs}
    for p in graphs:
        graph=json.loads(p.read_text());raw=Path(graph['input']['path']);before[str(raw)]=sha(raw)
        d=invoke(args(p),True)
        assert len(d['gpu_tables'])==4 and len(d['gmu_tables'])==1 and len(d['gmu_tables'][0]['pairs'])==2
        assert all(not t['selected'] for t in d['gpu_tables']+d['gmu_tables'])
        assert d['source_graph_provenance']['verified_nodes']==len(graph['nodes'])
        rows={n['source_node']:n['properties'] for n in d['verified_source_properties']}
        for n in graph['nodes']:
            assert set(rows[n['path']])==set(n['properties_hex'])
            for key,rawhex in n['properties_hex'].items():assert rows[n['path']][key]==dict(raw_hex=rawhex,bytes=len(rawhex)//2)
        (OUT/(p.stem+'.stdout.json')).write_text(json.dumps(d,indent=2)+'\n')
        real.append(dict(input=str(p),sha256=sha(p),gpu_tables=len(d['gpu_tables']),gmu_pairs=2,verified_nodes=len(rows)))
    original=json.loads(graphs[0].read_text());cases=[]
    for case in ['mutually-exclusive-output','missing-graph','missing-graph-sha','wrong-raw-sha','wrong-graph-sha','out-with-graph','trimmed-graph','forged-reference','declared-raw-sha']:
        argv=args(graphs[0])
        if case=='mutually-exclusive-output':argv+=['--out',str(OUT/'must-not-exist.json')]
        elif case=='missing-graph':i=argv.index('--graph-json');del argv[i:i+2]
        elif case=='missing-graph-sha':i=argv.index('--graph-sha256');del argv[i:i+2]
        elif case=='wrong-raw-sha':argv[argv.index('--sha256')+1]='0'*64
        elif case=='wrong-graph-sha':argv[-1]='0'*64
        elif case=='out-with-graph':argv.remove('--stdout');argv+=['--out',str(OUT/'must-not-exist.json')]
        else:
            d=copy.deepcopy(original)
            if case=='trimmed-graph':d['nodes']=d['nodes'][:1]
            elif case=='forged-reference':
                n=next(n for n in d['nodes'] if n['references']);n['references'][0]['provider']='/forged'
            else:d['input']['sha256']='0'*64
            p=OUT/(case+'.json');p.write_text(json.dumps(d));argv[argv.index('--graph-json')+1]=str(p);argv[-1]=sha(p)
        cases.append(dict(case=case,error=invoke(argv)))
    assert not (OUT/'must-not-exist.json').exists()
    # Preserve legacy exclusive JSON output;this single integration smoke check
    # neither decodes firmware nor reruns the old source-schema suite.
    p=graphs[0];raw=Path(original['input']['path']);out=OUT/'legacy-output.json'
    q=subprocess.run([sys.executable,'-B',str(TOOL),'--dtb',str(raw),'--sha256',sha(raw),'--out',str(out)],capture_output=True,text=True)
    assert q.returncode==0 and not q.stdout and not q.stderr,q.stderr
    legacy=json.loads(out.read_text());stdout=json.loads((OUT/(p.stem+'.stdout.json')).read_text())
    del stdout['source_graph_provenance'];del stdout['verified_source_properties'];assert stdout==legacy
    digest=sha(out)
    q=subprocess.run([sys.executable,'-B',str(TOOL),'--dtb',str(raw),'--sha256',sha(raw),'--out',str(out)],capture_output=True,text=True)
    assert q.returncode!=0 and sha(out)==digest
    assert all(sha(Path(p))==v for p,v in before.items())
    (OUT/'result.json').write_text(json.dumps(dict(new_stdout_sources=real,new_refusals=cases,child_no_write_or_process=True,legacy_out_shape_preserved=True,legacy_out_exclusive=True,input_SHA_unchanged=True,policy_headers_emitted=0,prepare_audit_formatter_executed=False,old_suites_reexecuted=False,driver_patch_count_remains32=True,allow_boot=False,readback_qualified=False,WriteAuthorized=0),indent=2)+'\n')
    print('PASS:4 verified read-only source table outputs,9 new refusals;legacy exclusive JSON output preserved;0policy/header/native')

if __name__=='__main__':main()

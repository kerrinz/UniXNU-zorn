#!/usr/bin/env python3
"""Only new source graph roots/closure cases;no generator or native execution."""
import copy
import hashlib
import json
import runpy
import struct
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'out/zorn/gpu-graph-closure-20261103'
TOOL=ROOT/'UniXNU-zorn/scripts/verify-zorn-gpu-reference-source.py'
GUARD=ROOT/'out/zorn/gpu-votes-source-cli-20261103/no-side-effects.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    graphs=sorted((ROOT/'out/zorn/gpu-stock-dt-source-20261102/vendor').glob('*.gpu.json'))
    def invoke(p,expected):
        doc=json.loads(p.read_text());raw=Path(doc['input']['path'])
        q=subprocess.run([sys.executable,'-B',str(GUARD),str(TOOL),'--graph-check-only','--input',str(p),'--input-sha256',sha(p),'--dtb',str(raw),'--dtb-sha256',sha(raw)],capture_output=True,text=True)
        assert not q.stderr,q.stderr
        d=json.loads(q.stdout);assert q.returncode==(0 if expected else 2),d
        assert d['graph_verified'] is expected and not d['generated_policy'] and not d['hardware_qualification'],d
        return d
    real=[]
    for p in graphs:
        d=invoke(p,True);(OUT/(p.stem+'.closure.json')).write_text(json.dumps(d,indent=2)+'\n')
        real.append(dict(input=str(p),json_sha256=sha(p),dtb_sha256=d['raw_dtb_sha256'],closure=d['raw_source_closure']))
    original=json.loads(graphs[0].read_text())
    sys.path.insert(0,str(ROOT/'UniXNU/scripts'))
    from unixnu.devicetree import read_fdt,FdtNode
    raw=read_fdt(Path(original['input']['path']).read_bytes())
    impl=runpy.run_path(str(ROOT/'UniXNU-zorn/scripts/verify-zorn-gpu-source-provenance.py'))
    actual,_=impl['verify'](original,raw);tool=runpy.run_path(str(TOOL))
    # An extra node has honest raw bytes/status/references;only closure must reject it.
    existing={n['path'] for n in original['nodes']};path=next(p for p in actual if p not in existing)
    n=actual[path];extra=dict(path=path,source_enabled=n.enabled(),properties_hex={k:v.hex() for k,v in n.properties.items()},references=tool['raw_references'](actual,[path])[path]['references'])
    cases=[]
    for case in ['missing-root','reordered-roots','duplicate-root','unrelated-root','missing-child','missing-provider','extra-honest-node','forged-resolution','numeric-resolution']:
        d=copy.deepcopy(original)
        if case=='missing-root':d['roots'].pop()
        elif case=='reordered-roots':d['roots'].reverse()
        elif case=='duplicate-root':d['roots'].append(d['roots'][0])
        elif case=='unrelated-root':d['roots'][0]=path
        elif case=='missing-child':
            target=next(n['path'] for n in d['nodes'] if n['path'] not in d['roots'] and any(n['path'].startswith(r+'/') for r in d['roots']));d['nodes']=[n for n in d['nodes'] if n['path']!=target]
        elif case=='missing-provider':
            target=next(ref['provider'] for n in d['nodes'] for ref in n['references'] if 'provider' in ref and ref['provider'] not in d['roots']);d['nodes']=[n for n in d['nodes'] if n['path']!=target]
        elif case=='extra-honest-node':d['nodes'].append(extra)
        elif case=='forged-resolution':d['resolution_complete']=not d['resolution_complete']
        else:d['resolution_complete']=int(d['resolution_complete'])
        p=OUT/(case+'.json');p.write_text(json.dumps(d));r=invoke(p,False);cases.append(dict(case=case,error=r['error']))
    pack=lambda *v:struct.pack('>'+'I'*len(v),*v)
    root=FdtNode('');gpu=FdtNode('gpu',root,dict(compatible=b'qcom,kgsl-3d0\0',status=b'disabled\0',clocks=pack(11,99,42)));provider=FdtNode('provider',root,dict(phandle=pack(11),clocks=pack(11),**{'#clock-cells':pack(0)}));child=FdtNode('child',gpu);gpu.children=[child];root.children=[gpu,provider]
    nodes={'/':root,'/gpu':gpu,'/gpu/child':child,'/provider':provider}
    doc=dict(roots=['/gpu'],nodes=[dict(path=p) for p in nodes if p!='/'],resolution_complete=False)
    result=tool['source_closure'](nodes,doc);assert result['node_count']==3 and not result['resolution_complete']
    pure=[dict(case='disabled-root-child-provider-cycle-unknown-tail',closure=result)]
    gpu.properties['compatible']=b'not-a-gpu\0'
    try:tool['source_closure'](nodes,doc)
    except ValueError as e:pure.append(dict(case='no-supported-root',error=str(e)))
    else:raise AssertionError('no root accepted')
    result=dict(real_source_graphs=real,new_graph_refusals=cases,new_closure_cases=pure,child_no_write_or_process=True,policy_headers_emitted=0,prepare_audit_formatter_executed=False,old_suites_reexecuted=False,driver_patch_count_remains32=True,allow_boot=False,readback_qualified=False,WriteAuthorized=0)
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS:4 real roots/closures,9 forged graph refusals,2 focused cycle/unknown/root cases;0headers/native/device')

if __name__=='__main__':main()

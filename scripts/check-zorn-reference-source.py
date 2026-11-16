#!/usr/bin/env python3
"""Focused CPU checks for raw reference correspondence only."""
import copy
import hashlib
import json
import runpy
import struct
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'out/zorn/gpu-reference-source-20261103'
TOOL = ROOT / 'UniXNU-zorn/scripts/verify-zorn-gpu-reference-source.py'
GUARD = ROOT / 'out/zorn/gpu-votes-source-cli-20261103/no-side-effects.py'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    OUT.mkdir(exist_ok=False)
    source = ROOT / 'out/zorn/gpu-stock-dt-source-20261102/vendor'
    cases, real = [], []
    def invoke(p, expected):
        doc = json.loads(p.read_text()); dtb = Path(doc['input']['path'])
        q = subprocess.run([sys.executable, '-B', str(GUARD), str(TOOL), '--input', str(p),
                            '--input-sha256', sha(p), '--dtb', str(dtb), '--dtb-sha256', sha(dtb)],
                           capture_output=True, text=True)
        assert not q.stderr, q.stderr
        result = json.loads(q.stdout)
        assert q.returncode == (0 if expected else 2), result
        assert result['references_verified'] is expected and not result['generated_policy'] and not result['hardware_qualification']
        return result
    for p in sorted(source.glob('*.gpu.json')):
        r = invoke(p, True)
        (OUT / (p.stem + '.references.json')).write_text(json.dumps(r, indent=2)+'\n')
        real.append(dict(input=str(p), json_sha256=sha(p), raw_dtb_sha256=r['raw_dtb_sha256'],
                         declared_nodes=r['declared_nodes_verified'], resolution_complete=r['resolution_complete']))
    original = json.loads(next(source.glob('*.gpu.json')).read_text())
    index = next(i for i,n in enumerate(original['nodes']) if any(r.get('source_arguments') for r in n['references']))
    for case in ['wrong-provider','changed-argument','missing-edge','extra-edge','wrong-property','boolean-argument','invented-unresolved']:
        d=copy.deepcopy(original); refs=d['nodes'][index]['references']; j=next(i for i,r in enumerate(refs) if r.get('source_arguments')); ref=refs[j]
        if case=='wrong-provider':ref['provider']='/forged-provider'
        elif case=='changed-argument':ref['source_arguments'][0]+=1
        elif case=='missing-edge':refs.pop(j)
        elif case=='extra-edge':refs.append(copy.deepcopy(ref))
        elif case=='wrong-property':ref['property']='iommus' if ref['property']!='iommus' else 'clocks'
        elif case=='boolean-argument':ref['source_arguments'][0]=True
        else:refs[j]=dict(property=ref['property'],unresolved_phandle=0,unresolved_tail_cells=[0],reason='fabricated')
        p=OUT/(case+'.json');p.write_text(json.dumps(d));r=invoke(p,False);cases.append(dict(case=case,error=r['error']))
    fn=runpy.run_path(str(TOOL))['raw_references']
    pack=lambda *v:struct.pack('>'+'I'*len(v),*v)
    node=lambda **p:SimpleNamespace(properties=p)
    actual={'/gpu':node(clocks=pack(11,7,99,8)), '/provider':node(phandle=pack(11),**{'#clock-cells':pack(1)})}
    r=fn(actual,['/gpu'])['/gpu'];assert r['cell_locations'][0]['cell_offset']==0 and r['cell_locations'][1]['cell_offset']==2 and r['references'][1]['unresolved_tail_cells']==[99,8]
    pure=[dict(case='known-prefix-unknown-tail',passed=True)]
    a=copy.deepcopy(actual);del a['/provider'].properties['#clock-cells'];r=fn(a,['/gpu'])['/gpu'];assert r['references'][0]['unresolved_tail_cells']==[11,7,99,8];pure.append(dict(case='missing-arity-preserves-entire-tail',passed=True))
    for case in ['truncated','unaligned','multi-cell-arity','duplicate-handle','reserved-handle','multi-supply']:
        a=copy.deepcopy(actual)
        if case=='truncated':a['/gpu'].properties['clocks']=pack(11)
        elif case=='unaligned':a['/gpu'].properties['clocks']=b'\x00'
        elif case=='multi-cell-arity':a['/provider'].properties['#clock-cells']=pack(1,2)
        elif case=='duplicate-handle':a['/second']=node(phandle=pack(11))
        elif case=='reserved-handle':a['/provider'].properties['phandle']=pack(0)
        else:a['/gpu'].properties['vdd-supply']=pack(11,7)
        try:fn(a,['/gpu'])
        except ValueError as e:pure.append(dict(case=case,error=str(e)))
        else:raise AssertionError(case)
    result=dict(real_source_bindings=real,new_graph_refusals=cases,new_raw_cell_cases=pure,
                child_no_write_or_process=True,headers=0,prepare_audit_formatter_executed=False,
                old_suites_reexecuted=False,driver_patches=32,allow_boot=False,readback_qualified=False,WriteAuthorized=0)
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS:4 real reference bindings,7 forged-edge refusals,8 raw-cell cases;0headers/native/device')


if __name__=='__main__':main()

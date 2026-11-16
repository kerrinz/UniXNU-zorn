#!/usr/bin/env python3
"""Focused offline description-reader tests;no old driver or firmware suite."""
from pathlib import Path
import importlib.util
import json
import hashlib
import subprocess
import sys

R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-commanddb-reservation-20261103'
O.mkdir(exist_ok=False)
script=R/'UniXNU-zorn/scripts/inspect-zorn-commanddb-reservation.py'
spec=importlib.util.spec_from_file_location('reservation_reader',script);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from unixnu.devicetree import FdtNode

def save(name,obj):(O/name).write_text(json.dumps(obj,indent=2)+'\n')
def fixture():
    root=FdtNode('');parent=FdtNode('reserved-memory',parent=root,properties={'#address-cells':(2).to_bytes(4,'big'),'#size-cells':(2).to_bytes(4,'big'),'ranges':b''});root.children=[parent]
    child=FdtNode('aop_cmd_db_region@81c60000',parent=parent,properties={'compatible':b'qcom,cmd-db\0','reg':bytes.fromhex('0000000081c600000000000000020000'),'no-map':b''});parent.children=[child];return root,parent,child

real=[];guard=R/'out/zorn/gpu-votes-source-cli-20261103/no-side-effects.py'
for i,row in enumerate(json.loads((R/'out/zorn/gpu-aop-source-kind-20261103/next-dt-reservation-inputs.json').read_text())['sources']):
    source=Path(row['dtb']);before=hashlib.sha256(source.read_bytes()).hexdigest();assert before==row['sha256']
    p=subprocess.run([sys.executable,'-B',str(guard),str(script),'--input',str(source),'--sha256',before,'--require-commanddb-snapshot'],capture_output=True)
    assert p.returncode==2,(p.returncode,p.stderr);d=json.loads(p.stdout);assert d['description_count']==1 and not d['commanddb_snapshot_usable']
    found=d['descriptions'][0];expected=row['source_matches'][0]
    assert found['properties_hex']==expected['properties_hex'] and found['parent_cell_properties_hex']==expected['parent_cell_properties_hex']
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before
    save('source-'+str(i)+'.json',d);real.append(dict(sha256=before,raw_properties_match=True,static_description_refused_as_snapshot=True,guard_no_write_process=True))

bad=[]
mutations={
 'missing-address-cells':lambda p,n:p.pop('#address-cells'),
 'missing-size-cells':lambda p,n:p.pop('#size-cells'),
 'bad-cell-width':lambda p,n:p.update({'#address-cells':b'\x02'}),
 'unsupported-cell-count':lambda p,n:p.update({'#size-cells':(3).to_bytes(4,'big')}),
 'missing-reg':lambda p,n:n.pop('reg'),
 'partial-reg':lambda p,n:n.update(reg=b'\0'*15),
 'nonboolean-no-map':lambda p,n:n.update({'no-map':b'\0'}),
 'contradictory-reusable':lambda p,n:n.update(reusable=b''),
}
for name,fn in mutations.items():
    root,parent,node=fixture();fn(parent.properties,node.properties)
    try:m.describe(root)
    except ValueError as e:bad.append(dict(case=name,error=str(e)))
    else:raise AssertionError(name)
root,parent,node=fixture();parent.name='soc'
try:m.describe(root)
except ValueError as e:bad.append(dict(case='wrong-parent',error=str(e)))
else:raise AssertionError('wrong-parent')
try:m.inspect_source(Path(json.loads((R/'out/zorn/gpu-aop-source-kind-20261103/next-dt-reservation-inputs.json').read_text())['sources'][0]['dtb']),'0'*64)
except ValueError as e:bad.append(dict(case='wrong-independent-SHA',error=str(e)))
else:raise AssertionError('wrong SHA')
edges=[]
for kind,value in [('absent',None),('nonempty',b'\0'*7)]:
    root,parent,node=fixture()
    if value is None:parent.properties.pop('ranges')
    else:parent.properties['ranges']=value
    node.properties.pop('no-map');node.properties['vendor,unknown']=b'\xff\0';d=m.describe(root);r=d['descriptions'][0]
    assert r['ranges_kind']==('absent-translation-unknown' if value is None else 'nonempty-translation-uninterpreted')
    assert r['properties_hex']['vendor,unknown']=='ff00' and not d['mapping_or_security_or_power_authority']
    edges.append(dict(case=kind+'-ranges-preserved',passed=True))
root,parent,node=fixture();parent.children=[];assert m.describe(root)['description_count']==0;edges.append(dict(case='no-node-not-runtime-absence',passed=True))
save('result.json',dict(real_sources=real,new_refusals=bad,unknown_preservation_edges=edges,scope='reservation source descriptions only',hardware_qualification=False,commanddb_snapshot_usable=False,generated_policy=False,native_execution=False,device_operations=False,old_suite_or_compile_rerun=False))
print('PASS:4 raw-source matches/refused snapshots;10 new refusals;3 unknown-preservation edges;no device/native/compile')

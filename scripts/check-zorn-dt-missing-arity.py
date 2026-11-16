#!/usr/bin/env python3
"""New producer regression only:preserve unresolved cells when arity is absent."""
import copy,json,runpy,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'UniXNU/scripts'))
from unixnu import devicetree as DT
OUT=ROOT/'out/zorn/gpu-reference-source-20261103'

def main():
    source=(ROOT/'UniXNU-zorn/scripts/inspect-zorn-gpu-dt-inputs.py').read_text()
    old=source.replace("                count_key = {'clocks': '#clock-cells', 'power-domains': '#power-domain-cells',\n                             'iommus': '#iommu-cells'}.get(key)\n                if handle not in handles or (count_key and count_key not in handles[handle].properties):", "                if handle not in handles:")
    old=old.replace("                provider = handles[handle]\n                count =", "                provider = handles[handle]\n                count_key = {'clocks': '#clock-cells', 'power-domains': '#power-domain-cells',\n                             'iommus': '#iommu-cells'}.get(key)\n                count =")
    assert old!=source
    (OUT/'inspector-preimage.py.txt').write_text(old)
    prior={'__name__':'not_main','__file__':str(ROOT/'UniXNU-zorn/scripts/inspect-zorn-gpu-dt-inputs.py')};exec(compile(old,'producer-preimage','exec'),prior)
    current=runpy.run_path(str(ROOT/'UniXNU-zorn/scripts/inspect-zorn-gpu-dt-inputs.py'))
    pack=lambda *v:struct.pack('>'+'I'*len(v),*v)
    root=DT.FdtNode('');gpu=DT.FdtNode('gpu',root,dict(compatible=b'qcom,kgsl-3d0\0',clocks=pack(11,7,99,8)));provider=DT.FdtNode('provider',root,dict(phandle=pack(11)));root.children=[gpu,provider]
    saved=DT.read_fdt;cases=[]
    try:
        DT.read_fdt=lambda blob:root
        try:prior['inspect'](b'')
        except DT.Error as e:cases.append(dict(case='previous-missing-arity-error',error=str(e)))
        else:raise AssertionError('previous source unexpectedly accepted')
        r=current['inspect'](b'');ref=r['nodes'][0]['references'][0];assert ref['unresolved_tail_cells']==[11,7,99,8] and not r['resolution_complete'];cases.append(dict(case='missing-arity-preserved',reference=ref))
        provider.properties['#clock-cells']=pack(1,2)
        try:current['inspect'](b'')
        except DT.Error:cases.append(dict(case='malformed-present-arity-still-refused',passed=True))
        else:raise AssertionError('malformed arity accepted')
    finally:DT.read_fdt=saved
    (OUT/'producer-check.json').write_text(json.dumps(dict(new_cases=cases,only_CPU_source_fixture=True,headers=0,native=False),indent=2)+'\n')
    print('PASS:producer missing arity preserved;malformed present arity refused;3new observations only')

if __name__=='__main__':main()

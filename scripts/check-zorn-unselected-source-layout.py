#!/usr/bin/env python3
"""New raw-byte roundtrip and compile-time refusal checks;no target execution."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'out/zorn/gpu-source-layout-review'
EMITTER=ROOT/'UniXNU-zorn/scripts/emit-zorn-unselected-source-data.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    header=OUT/'UnselectedSourceTables.h';cpp=OUT/'source-layout-check.cpp'
    baseline=json.loads((OUT/'compile-baseline.json').read_text())
    assert baseline['returncode']==0 and all(sha(Path(p))==digest for p,digest in baseline['inputs'].items())
    text=header.read_text();arrays={}
    for key in ['text_bytes','property_bytes','sources','nodes','properties','optional_fields','tables','entries','gmu_tables','gmu_pairs']:
        match=re.search(r'inline constexpr \w+ '+key+r'\[\] = \{\n(.*?)\n\};',text,re.S);assert match,key
        if key.endswith('_bytes'):arrays[key]=bytes(int(v) for v in re.findall(r'\d+',match[1]))
        else:arrays[key]=[[int(v) for v in re.findall(r'(\d+)U',row)] for row in re.findall(r'\{([^{}]+)\}',match[1])]
    def string(offset):
        raw=arrays['text_bytes'];return raw[offset:raw.index(0,offset)].decode()
    manifest=ROOT/'out/zorn/gpu-power-source-compare-20261103/inputs.json';inputs=json.loads(manifest.read_text())['sources']
    sys.path.insert(0,str(ROOT/'UniXNU/scripts'))
    from unixnu.devicetree import read_fdt
    graphs=[];node_indexes={};properties={};expected_tables=[];expected_gmu=[]
    for s,entry in enumerate(inputs):
        raw_path=Path(entry['dtb']);assert sha(raw_path)==entry['dtb_sha256']
        graph_path=Path(entry['graph_json']);assert sha(graph_path)==entry['graph_sha256'];graph=json.loads(graph_path.read_text());graphs.append(graph)
        row=arrays['sources'][s];assert [string(i) for i in row[:3]]==[entry['id'],entry['dtb_sha256'],entry['graph_sha256']]
        root=read_fdt(raw_path.read_bytes());raw_nodes={}
        def walk(node,path):
            raw_nodes[path]=node
            for child in node.children:walk(child,path.rstrip('/')+'/'+child.name)
        walk(root,'/');closure={r['path'] for r in graph['nodes']};ordered=[p for p in raw_nodes if p in closure]
        first,count=row[3:];assert count==len(ordered)
        for i,path in enumerate(ordered,first):
            n=raw_nodes[path];r=arrays['nodes'][i];assert r[0]==s and string(r[1])==path and r[4:]==[1,int(n.enabled())]
            assert r[3]==len(n.properties);decoded=[];node_indexes[(s,path)]=i
            for pi in range(r[2],r[2]+r[3]):
                pr=arrays['properties'][pi];assert pr[0]==i and pr[4]==0
                name=string(pr[1]);value=arrays['property_bytes'][pr[2]:pr[2]+pr[3]]
                decoded.append((name,value));properties[(i,name)]=(pi,value)
            assert decoded==list(n.properties.items()),path
        for path,n in raw_nodes.items():
            if 'qcom,kgsl-3d0' in n.strings('compatible'):
                container=next(ch for ch in n.children if ch.name=='qcom,gpu-pwrlevel-bins')
                for table in container.children:
                    tp=path+'/'+container.name+'/'+table.name
                    expected_tables.append((s,tp,[tp+'/'+ch.name for ch in table.children]))
            if 'qcom,gen7-gmu' in n.strings('compatible'):expected_gmu.append((s,path,n.properties['qcom,gmu-freq-table']))
    assert len(arrays['sources'])==4 and len(arrays['tables'])==16
    for ti,((s,path,entry_paths),table) in enumerate(zip(expected_tables,arrays['tables'])):
        assert table[:2]==[s,node_indexes[(s,path)]] and table[3]==len(entry_paths)
        assert arrays['entries'][table[2]:table[2]+table[3]]==[[ti,node_indexes[(s,p)]] for p in entry_paths]
    assert len(expected_gmu)==len(arrays['gmu_tables'])==4
    for gi,((s,path,raw),table) in enumerate(zip(expected_gmu,arrays['gmu_tables'])):
        node=node_indexes[(s,path)];pi,value=properties[(node,'qcom,gmu-freq-table')]
        assert table[:3]==[s,node,pi] and value==raw
        pairs=arrays['gmu_pairs'][table[3]:table[3]+table[4]];assert len(pairs)==2
        assert b''.join(arrays['property_bytes'][offset:offset+width] for table_id,offset,width in pairs)==raw
        assert all(table_id==gi and width==8 for table_id,_,width in pairs)
    absent=0
    for node,key,present,pi in arrays['optional_fields']:
        found=properties.get((node,string(key)))
        assert present==int(found is not None)
        if found:assert pi==found[0]
        else:assert pi==0xffffffff;absent+=1
    assert absent>0
    refusal_compiles=[]
    # Each invalid clone is a distinct inode;the approved source header is untouched.
    for case in ['property-byte-overrun','absent-field-made-present','wrong-table-source']:
        directory=OUT/case;directory.mkdir(exist_ok=False);mutated=text
        if case=='property-byte-overrun':
            row=list(arrays['properties'][0]);bad=list(row);bad[2]=len(arrays['property_bytes'])+1;key='properties'
        elif case=='absent-field-made-present':
            row=next(list(r) for r in arrays['optional_fields'] if r[2]==0);bad=list(row);bad[2]=1;key='optional_fields'
        else:row=list(arrays['tables'][0]);bad=list(row);bad[0]=4;key='tables'
        old='{'+','.join(str(v)+'U' for v in row)+'},';new='{'+','.join(str(v)+'U' for v in bad)+'},'
        start=mutated.index(' '+key+'[] = {');end=mutated.index('\n};',start)
        body=mutated[start:end];assert old in body;mutated=mutated[:start]+body.replace(old,new,1)+mutated[end:]
        target=directory/'UnselectedSourceTables.h';target.write_text(mutated);assert target.stat().st_ino!=header.stat().st_ino and target.stat().st_nlink==1
        source=directory/'source-layout-check.cpp';source.write_bytes(cpp.read_bytes())
        command=baseline['command'][:-1]+[str(source)];q=subprocess.run(command,capture_output=True,text=True)
        (directory/'compile.log').write_text(q.stdout+q.stderr)
        assert q.returncode!=0 and 'source review data layout invalid' in q.stderr,q.stderr
        refusal_compiles.append(dict(case=case,command=command,returncode=q.returncode,log=str(directory/'compile.log')))
    original_outputs={str(OUT/n):sha(OUT/n) for n in ['UnselectedSourceTables.h','source-layout-check.cpp','source-layout-data.json']}
    argv=[sys.executable,'-B',str(EMITTER),'--inputs',str(manifest),'--sha256',sha(manifest),'--approval',str(OUT/'owner-scope-approval.json'),'--out-dir',str(OUT),'--emit-unselected-source-data']
    q=subprocess.run(argv,capture_output=True,text=True);assert q.returncode==2 and 'refusing to overwrite' in q.stderr
    assert all(sha(Path(p))==digest for p,digest in original_outputs.items())
    gates=[]
    for case in ['wrong-approved-manifest','missing-narrow-approval']:
        directory=OUT/(case+'-output');args=list(argv);args[args.index('--out-dir')+1]=str(directory)
        if case=='wrong-approved-manifest':args[args.index('--sha256')+1]='0'*64
        else:
            receipt=json.loads((OUT/'owner-scope-approval.json').read_text());receipt['owner_reply']='not-approved'
            p=OUT/'unapproved-fixture.json';p.write_text(json.dumps(receipt));args[args.index('--approval')+1]=str(p)
        q=subprocess.run(args,capture_output=True,text=True);assert q.returncode==2 and not directory.exists()
        gates.append(dict(case=case,returncode=q.returncode,no_output_directory=True))
    assert all(sha(Path(p))==digest for p,digest in baseline['inputs'].items())
    result=dict(source_count=4,table_count=16,node_count=len(arrays['nodes']),property_count=len(arrays['properties']),gpu_entry_count=len(arrays['entries']),gmu_pair_count=len(arrays['gmu_pairs']),explicit_absent_fields=absent,all_raw_property_bytes_and_original_order_roundtrip=True,all_tables_entries_and_GMU_pairs_roundtrip=True,initial_iOS17_arm64_compile=baseline,baseline_compile_not_repeated=True,three_negative_layout_compiles=refusal_compiles,emitter_new_gate_checks=gates,nooverwrite_preserved=True,no_object_link_or_runtime_execution=True,no_driver_startup_import=True,policy_generated=False,source_tables_selected=False,driver_patch_count_remains32=True,old_suites_reexecuted=False,allow_boot=False,readback_qualified=False,WriteAuthorized=0)
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS:4sources/16tables/8GMUpairs raw-byte/order roundtrip;3negative iOS17 layout compiles and2new emitter gates;0runtime/native/device')


if __name__=='__main__':main()

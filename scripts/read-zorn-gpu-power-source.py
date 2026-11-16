#!/usr/bin/env python3
"""Read unselected raw K80 GPU/GMU table schemas; never emit startup policy."""
import argparse
import hashlib
import importlib.util
import json
import runpy
from pathlib import Path

spec=importlib.util.spec_from_file_location('zorn_overlay_source',Path(__file__).with_name('inspect-zorn-gpu-overlay-inputs.py'))
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
from unixnu.devicetree import Error as SourceError
ROOT=Path(__file__).resolve().parents[2]
GRAPH=Path(__file__).with_name('verify-zorn-gpu-reference-source.py')
GRAPH_SHA='05973a22c22e8b40d83ae37d67890ab4af7d96b5c91a1f73de4992d6f9caa19b'


def scalar(node,key,required=False):
    raw=node.properties.get(key)
    if raw is None:
        if required:
            raise ValueError(node.name+': missing '+key)
        return dict(available=False)
    if len(raw)!=4:
        raise ValueError(node.name+': '+key+' must have exactly one source cell')
    return dict(available=True,bytes=4,raw_hex=raw.hex(),source_u32=int.from_bytes(raw,'big'))


def read(root):
    nodes=helper.index(root);tables=[];gmu=[]
    for path,node in nodes.items():
        if 'qcom,kgsl-3d0' in node.strings('compatible'):
            containers=[n for n in node.children if n.name=='qcom,gpu-pwrlevel-bins']
            if len(containers)!=1:
                raise ValueError('GPU source requires one pwrlevel-bins container')
            container=containers[0]
            if container.scalar('#address-cells')!=1 or container.scalar('#size-cells')!=0:
                raise ValueError('unsupported pwrlevel source cell layout')
            for table in container.children:
                if table.scalar('#address-cells')!=1 or table.scalar('#size-cells')!=0:
                    raise ValueError('unsupported table source cell layout')
                tp=path+'/'+container.name+'/'+table.name
                entries=[];ids=set()
                for entry in table.children:
                    fields={k:scalar(entry,k,k in ('reg','qcom,gpu-freq','qcom,bus-freq'))
                            for k in ('reg','qcom,gpu-freq','qcom,bus-freq','qcom,bus-min','qcom,bus-max','qcom,level','qcom,acd-level')}
                    ident=fields['reg']['source_u32']
                    if ident in ids:
                        raise ValueError(tp+': duplicate source reg index')
                    ids.add(ident)
                    entries.append(dict(source_node=tp+'/'+entry.name,source_enabled=entry.enabled(),fields=fields,
                                        all_properties_hex={k:v.hex() for k,v in entry.properties.items()}))
                if not entries:
                    raise ValueError(tp+': empty pwrlevel source table')
                sku=table.properties.get('qcom,sku-codes')
                if sku is not None and (not sku or len(sku)%4):
                    raise ValueError(tp+': malformed sku source cells')
                initial=scalar(table,'qcom,initial-pwrlevel')
                if initial['available'] and initial['source_u32'] not in ids:
                    raise ValueError(tp+': initial source index refers to absent entry')
                tables.append(dict(source_node=tp,source_enabled=table.enabled(),
                                   speed_bin=scalar(table,'qcom,speed-bin'),
                                   sku_codes=dict(available=sku is not None,raw_hex=sku.hex() if sku is not None else None),
                                   initial_source_index=initial,entries=entries,selected=False))
        if 'qcom,gen7-gmu' in node.strings('compatible'):
            raw=node.properties.get('qcom,gmu-freq-table')
            if raw is None or not raw or len(raw)%8:
                raise ValueError(path+': missing/incomplete GMU source cell pairs')
            # Pinned gen7 consumer reads alternating cells;do not reinterpret them
            # as a measured clock,voltage or selected runtime OPP.
            pairs=[dict(byte_offset=i,raw_hex=raw[i:i+8].hex(),source_cells=node.cells('qcom,gmu-freq-table')[i//4:i//4+2])
                   for i in range(0,len(raw),8)]
            if len({tuple(p['source_cells']) for p in pairs})!=len(pairs):
                raise ValueError(path+': duplicate GMU source pair')
            gmu.append(dict(source_node=path,property='qcom,gmu-freq-table',source_enabled=node.enabled(),
                            cell_bytes=4,pair_bytes=8,pairs=pairs,selected=False))
    if not tables or not gmu:
        raise ValueError('GPU and Gen7 GMU source schemas both required')
    return dict(scope='raw source schema only;not generated policy or hardware capability',gpu_tables=tables,gmu_tables=gmu,
                speed_bin_selected=False,frequency_selected=False,voltage_selected=False,
                boot_variant_selected=False,generated_policy=False,hardware_qualification=False)


def verified_graph(root,raw_sha,source,source_sha):
    """Bind graph JSON to the same raw tree before reading any source tables."""
    sha=lambda raw:hashlib.sha256(raw).hexdigest()
    if sha(GRAPH.read_bytes())!=GRAPH_SHA:
        raise ValueError('pinned graph verifier changed')
    graph=runpy.run_path(str(GRAPH))
    if sha(graph['PROVENANCE'].read_bytes())!=graph['PROVENANCE_SHA']:
        raise ValueError('pinned provenance verifier changed')
    impl=runpy.run_path(str(graph['PROVENANCE']))
    if sha(impl['PARSER'].read_bytes())!=impl['PARSER_SHA']:
        raise ValueError('pinned raw parser changed')
    if len(source)>16*1024*1024 or sha(source)!=source_sha:
        raise ValueError('source graph JSON bound/SHA mismatch')
    doc=json.loads(source,object_pairs_hook=impl['unique'])
    if not isinstance(doc,dict) or not isinstance(doc.get('input'),dict) or doc['input'].get('sha256')!=raw_sha:
        raise ValueError('graph original DTB identity mismatch')
    actual,count=impl['verify'](doc,root)
    expected=graph['raw_references'](actual,[row['path'] for row in doc['nodes']])
    for row in doc['nodes']:
        if json.dumps(row.get('references'),sort_keys=True)!=json.dumps(expected[row['path']]['references'],sort_keys=True):
            raise ValueError('graph references differ from raw source')
    closure=graph['source_closure'](actual,doc)
    return dict(json_sha256=source_sha,raw_dtb_sha256=raw_sha,closure=closure,
                verified_nodes=count,hardware_qualification=False),doc['nodes']


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dtb',type=Path,required=True)
    p.add_argument('--sha256',required=True)
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--out',type=Path);mode.add_argument('--stdout',action='store_true')
    p.add_argument('--graph-json',type=Path);p.add_argument('--graph-sha256');a=p.parse_args()
    if a.stdout and (a.graph_json is None or a.graph_sha256 is None):
        p.error('--stdout requires --graph-json and --graph-sha256')
    if not a.stdout and (a.graph_json is not None or a.graph_sha256 is not None):
        p.error('graph verification arguments require --stdout')
    blob=a.dtb.read_bytes();digest=hashlib.sha256(blob).hexdigest()
    if digest!=a.sha256:
        p.error('source SHA mismatch')
    if a.stdout:
        try:
            root=helper.read_fdt(blob)
            provenance,rows=verified_graph(root,digest,a.graph_json.read_bytes(),a.graph_sha256)
            d=read(root);d['source_graph_provenance']=provenance
            # Preserve every verified property,including unknown properties and
            # empty values,without assigning a runtime interpretation to them.
            d['verified_source_properties']=[dict(source_node=row['path'],properties={
                k:dict(raw_hex=v,bytes=len(v)//2) for k,v in row['properties_hex'].items()}) for row in rows]
        except (ValueError,TypeError,OSError,SourceError) as exc:
            p.error(str(exc))
    else:
        d=read(helper.read_fdt(blob))
    d['input']=dict(path=str(a.dtb.resolve()),sha256=digest)
    if a.stdout:
        print(json.dumps(d,indent=2));return
    with a.out.open('x') as f:
        json.dump(d,f,indent=2);f.write('\n')


if __name__=='__main__':
    main()

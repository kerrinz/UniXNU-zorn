#!/usr/bin/env python3
"""Emit approved,unselected raw source data for isolated compile review only."""
import argparse
import hashlib
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
READER = Path(__file__).with_name('read-zorn-gpu-power-source.py')
READER_SHA = '8e15bbef1f754f2808f5ffeeff76bdd0a707f5d8f77a136cec621f3d7929361b'
APPROVED_MANIFEST_SHA = 'a8b6cb3aa94ca8214e0ba20e9b6ba886de6707f3ddfba60f5a1244912f914e88'
ABSENT = 0xffffffff


def unique(pairs):
    result = {}
    for k, v in pairs:
        if k in result: raise ValueError('duplicate JSON key')
        result[k] = v
    return result


def collect(manifest):
    sha = lambda data: hashlib.sha256(data).hexdigest()
    if sha(READER.read_bytes()) != READER_SHA: raise ValueError('pinned source reader changed')
    reader = runpy.run_path(str(READER))
    from unixnu.devicetree import Error as SourceError
    entries = manifest.get('sources') if isinstance(manifest, dict) else None
    if set(manifest) != {'sources'} or not isinstance(entries, list) or len(entries) != 4:
        raise ValueError('the approved four explicit source inputs are required')
    model = {key: [] for key in ('sources','nodes','properties','optional_fields','tables','entries','gmu_tables','gmu_pairs')}
    text, raw_bytes, ids, digests = bytearray(), bytearray(), set(), set()
    def string(value):
        if '\0' in value: raise ValueError('embedded NUL in source identity')
        offset = len(text); text.extend(value.encode()+b'\0'); return offset
    for source_index, entry in enumerate(entries):
        if set(entry) != {'id','dtb','dtb_sha256','graph_json','graph_sha256'} or any(not isinstance(v,str) or not v for v in entry.values()):
            raise ValueError('invalid explicit source identity')
        label = entry['id']
        if label in ids: raise ValueError('duplicate source id')
        ids.add(label)
        source = Path(entry['dtb']); graph = Path(entry['graph_json'])
        if not source.is_absolute() or not graph.is_absolute(): raise ValueError('source paths must be absolute')
        blob = source.read_bytes(); digest = sha(blob)
        if digest != entry['dtb_sha256'] or digest in digests: raise ValueError('raw source identity mismatch/duplicate')
        digests.add(digest)
        try:
            root = reader['helper'].read_fdt(blob)
            provenance, rows = reader['verified_graph'](root,digest,graph.read_bytes(),entry['graph_sha256'])
            parsed = reader['read'](root)
        except (SourceError,UnicodeError) as exc: raise ValueError('invalid raw source: '+str(exc)) from exc
        if len(parsed['gpu_tables']) != 4 or len(parsed['gmu_tables']) != 1:
            raise ValueError('approved source table shape changed')
        actual = reader['helper'].index(root); closure = {row['path'] for row in rows}
        node_ids, property_ids = {}, {}
        first_node = len(model['nodes'])
        # Follow original raw node/property order,not sorted graph JSON order.
        for path, node in actual.items():
            if path not in closure: continue
            node_id = len(model['nodes']); node_ids[path] = node_id
            first_property = len(model['properties'])
            for name, raw in node.properties.items():
                property_ids[(path,name)] = len(model['properties'])
                model['properties'].append([node_id,string(name),len(raw_bytes),len(raw),0])
                raw_bytes.extend(raw)
            model['nodes'].append([source_index,string(path),first_property,len(node.properties),1,int(node.enabled())])
        model['sources'].append([string(label),string(digest),string(entry['graph_sha256']),first_node,len(node_ids)])
        def optional(path, name):
            prop = property_ids.get((path,name))
            model['optional_fields'].append([node_ids[path],string(name),int(prop is not None),prop if prop is not None else ABSENT])
        for table in parsed['gpu_tables']:
            path = table['source_node']; table_id = len(model['tables']); first_entry = len(model['entries'])
            for name in ('qcom,speed-bin','qcom,sku-codes','qcom,initial-pwrlevel'): optional(path,name)
            for entry_row in table['entries']:
                ep = entry_row['source_node']; model['entries'].append([table_id,node_ids[ep]])
                for name in entry_row['fields']: optional(ep,name)
            model['tables'].append([source_index,node_ids[path],first_entry,len(table['entries'])])
        for table in parsed['gmu_tables']:
            path = table['source_node']; prop_id = property_ids[(path,table['property'])]
            gmu_id = len(model['gmu_tables']); first_pair = len(model['gmu_pairs'])
            raw_offset = model['properties'][prop_id][2]
            for pair in table['pairs']: model['gmu_pairs'].append([gmu_id,raw_offset+pair['byte_offset'],8])
            model['gmu_tables'].append([source_index,node_ids[path],prop_id,first_pair,len(table['pairs'])])
    if any(value < 0 or value > ABSENT for rows in model.values() for row in rows for value in row):
        raise ValueError('source review data exceeds32bit file-index model')
    model['text_bytes'] = list(text); model['property_bytes'] = list(raw_bytes)
    return model


TYPES = {
    'sources': ('Source','u32 id_text, dtb_sha_text, graph_sha_text, first_node, node_count;'),
    'nodes': ('Node','u32 source, path_text, first_property, property_count, status_known, source_enabled;'),
    'properties': ('Property','u32 node, name_text, byte_offset, width_bytes, interpretation_known;'),
    'optional_fields': ('OptionalField','u32 node, name_text, present, property_index;'),
    'tables': ('GpuTable','u32 source, node, first_entry, entry_count;'),
    'entries': ('GpuEntry','u32 table, node;'),
    'gmu_tables': ('GmuTable','u32 source, node, property_index, first_pair, pair_count;'),
    'gmu_pairs': ('GmuPair','u32 table, byte_offset, width_bytes;'),
}


def render(model):
    lines = ['// REVIEW DATA ONLY:all sources/tables unselected;not startup policy or hardware authority.',
             '// Offsets index these source byte arrays,never physical/virtual/IOVA addresses.',
             '#ifndef ZORN_UNSELECTED_SOURCE_REVIEW_H','#define ZORN_UNSELECTED_SOURCE_REVIEW_H',
             'namespace zorn_source_review {','using u8 = unsigned char;','using u32 = unsigned int;',
             'static_assert(sizeof(u8)==1 && sizeof(u32)==4,"source review integer widths");',
             'inline constexpr bool generated_policy=false;','inline constexpr bool any_source_selected=false;',
             'inline constexpr bool hardware_qualification=false;','inline constexpr u32 absent_property=0xffffffffU;']
    for key,(typename,fields) in TYPES.items(): lines.append('struct '+typename+' { '+fields+' };')
    for key in ('text_bytes','property_bytes'):
        values = model[key]
        lines.append('inline constexpr u8 '+key+'[] = {')
        for pos in range(0,len(values),24): lines.append(','.join(str(v) for v in values[pos:pos+24])+',')
        lines.append('};')
        lines.append('inline constexpr u32 '+key+'_count='+str(len(values))+'U;')
    for key,(typename,_) in TYPES.items():
        lines.append('inline constexpr '+typename+' '+key+'[] = {')
        lines.extend('{'+','.join(str(v)+'U' for v in row)+'},' for row in model[key])
        lines.append('};');lines.append('inline constexpr u32 '+key+'_count='+str(len(model[key]))+'U;')
    lines += ['}','#endif','']
    return '\n'.join(lines)


CHECK_CPP = r'''// Compile-only source data layout validation:no main,driver imports or runtime calls.
#include "UnselectedSourceTables.h"
using namespace zorn_source_review;
constexpr bool text_valid(u32 pos) {
    if(pos>=text_bytes_count)return false;
    for(u32 i=pos;i<text_bytes_count;++i)if(text_bytes[i]==0)return true;
    return false;
}
constexpr bool same_text(u32 a,u32 b) {
    while(a<text_bytes_count && b<text_bytes_count) {
        if(text_bytes[a]!=text_bytes[b])return false;
        if(!text_bytes[a])return true;
        ++a;++b;
    }
    return false;
}
constexpr bool span(u32 begin,u32 count,u32 size) {return begin<=size && count<=size-begin;}
constexpr bool source_layout_valid() {
    if(generated_policy || any_source_selected || hardware_qualification)return false;
    if(sources_count!=4 || tables_count!=16 || gmu_tables_count!=4 || gmu_pairs_count!=8)return false;
    for(u32 s=0;s<sources_count;++s) {
        const auto &r=sources[s];
        if(!text_valid(r.id_text)||!text_valid(r.dtb_sha_text)||!text_valid(r.graph_sha_text)||!span(r.first_node,r.node_count,nodes_count))return false;
        for(u32 n=r.first_node;n<r.first_node+r.node_count;++n)if(nodes[n].source!=s)return false;
        u32 table_count=0;for(u32 t=0;t<tables_count;++t)if(tables[t].source==s)++table_count;
        if(table_count!=4)return false;
    }
    for(u32 n=0;n<nodes_count;++n) {
        const auto &r=nodes[n];
        if(r.source>=sources_count||!text_valid(r.path_text)||!span(r.first_property,r.property_count,properties_count)||r.status_known!=1||r.source_enabled>1)return false;
        for(u32 p=r.first_property;p<r.first_property+r.property_count;++p)if(properties[p].node!=n)return false;
    }
    for(u32 p=0;p<properties_count;++p) {
        const auto &r=properties[p];
        if(r.node>=nodes_count||!text_valid(r.name_text)||!span(r.byte_offset,r.width_bytes,property_bytes_count)||r.interpretation_known!=0)return false;
    }
    for(u32 o=0;o<optional_fields_count;++o) {
        const auto &r=optional_fields[o];
        if(r.node>=nodes_count||!text_valid(r.name_text)||r.present>1)return false;
        if(r.present) {
            if(r.property_index>=properties_count||properties[r.property_index].node!=r.node||!same_text(r.name_text,properties[r.property_index].name_text))return false;
        } else {
            if(r.property_index!=absent_property)return false;
            const auto &node=nodes[r.node];
            for(u32 p=node.first_property;p<node.first_property+node.property_count;++p)if(same_text(r.name_text,properties[p].name_text))return false;
        }
    }
    for(u32 t=0;t<tables_count;++t) {
        const auto &r=tables[t];
        if(r.source>=sources_count||r.node>=nodes_count||nodes[r.node].source!=r.source||!r.entry_count||!span(r.first_entry,r.entry_count,entries_count))return false;
        for(u32 e=r.first_entry;e<r.first_entry+r.entry_count;++e)if(entries[e].table!=t)return false;
    }
    for(u32 e=0;e<entries_count;++e)if(entries[e].table>=tables_count||entries[e].node>=nodes_count||nodes[entries[e].node].source!=tables[entries[e].table].source)return false;
    for(u32 t=0;t<gmu_tables_count;++t) {
        const auto &r=gmu_tables[t];
        if(r.source>=sources_count||r.node>=nodes_count||nodes[r.node].source!=r.source||r.property_index>=properties_count||properties[r.property_index].node!=r.node||!span(r.first_pair,r.pair_count,gmu_pairs_count))return false;
        const auto &p=properties[r.property_index];if(r.pair_count!=2||p.width_bytes!=r.pair_count*8)return false;
        for(u32 i=0;i<r.pair_count;++i) {
            const auto &pair=gmu_pairs[r.first_pair+i];
            if(pair.table!=t||pair.width_bytes!=8||pair.byte_offset!=p.byte_offset+i*8||!span(pair.byte_offset,8,property_bytes_count))return false;
        }
    }
    return true;
}
static_assert(sizeof(Source)==20 && alignof(Source)==4,"Source record layout");
static_assert(sizeof(Node)==24 && sizeof(Property)==20 && sizeof(OptionalField)==16,"Node/property record layout");
static_assert(sizeof(GpuTable)==16 && sizeof(GpuEntry)==8 && sizeof(GmuTable)==20 && sizeof(GmuPair)==12,"Table record layout");
static_assert(source_layout_valid(),"source review data layout invalid");
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs',type=Path,required=True);parser.add_argument('--sha256',required=True)
    parser.add_argument('--approval',type=Path,required=True);parser.add_argument('--out-dir',type=Path,required=True)
    parser.add_argument('--emit-unselected-source-data',action='store_true',required=True)
    args=parser.parse_args()
    try:
        receipt=json.loads(args.approval.read_text(),object_pairs_hook=unique)
        if receipt.get('owner_reply')!='允许' or receipt.get('manifest_sha256')!=APPROVED_MANIFEST_SHA or receipt.get('new_device_activation_authorized') is not False or receipt.get('WriteAuthorized')!=0:
            raise ValueError('explicit narrow offline source-layout approval required')
        raw=args.inputs.read_bytes();digest=hashlib.sha256(raw).hexdigest()
        if digest!=args.sha256 or digest!=APPROVED_MANIFEST_SHA:
            raise ValueError('only the approved four-source manifest is allowed')
        model=collect(json.loads(raw,object_pairs_hook=unique))
        header=render(model)
        metadata=dict(scope='unselected raw source data,isolated compile review only',manifest_sha256=digest,
                      reader_sha256=READER_SHA,emitter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      records=model,generated_policy=False,any_source_selected=False,hardware_qualification=False)
        outputs={'UnselectedSourceTables.h':header,'source-layout-check.cpp':CHECK_CPP,
                 'source-layout-data.json':json.dumps(metadata,indent=2)+'\n'}
        if any((args.out_dir/name).exists() for name in outputs):raise ValueError('refusing to overwrite source review output')
        args.out_dir.mkdir(parents=False,exist_ok=True)
        for name,content in outputs.items():
            with (args.out_dir/name).open('x') as f:f.write(content)
    except (ValueError,TypeError,OSError) as exc:parser.error(str(exc))
    print(json.dumps(dict(emitted_source_data_only=True,source_count=4,table_count=16,
                         generated_policy=False,hardware_qualification=False,
                         outputs=[str(args.out_dir/name) for name in outputs])))


if __name__=='__main__':main()

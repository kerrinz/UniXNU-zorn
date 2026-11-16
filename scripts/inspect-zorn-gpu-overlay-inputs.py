#!/usr/bin/env python3
"""Inspect overlay source-to-base relations without applying fixups or selecting a variant."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'UniXNU/scripts'))
from unixnu.devicetree import read_fdt


def index(root):
    out = {}
    def walk(node,path):
        if path in out:
            raise ValueError('ambiguous source path: '+path)
        out[path] = node
        for c in node.children:
            walk(c,path.rstrip('/')+'/'+c.name)
    walk(root,'/')
    return out


def string(raw):
    if not raw.endswith(b'\0') or b'\0' in raw[:-1]:
        raise ValueError('requires exactly one terminated source string')
    return raw[:-1].decode()


def inspect(base,overlay):
    bn,on = index(base),index(overlay)
    handles = {}
    for path,node in bn.items():
        hs=[node.scalar(k) for k in ('phandle','linux,phandle') if k in node.properties]
        if hs:
            if len(set(hs))!=1 or hs[0] in (0,0xffffffff) or hs[0] in handles:
                raise ValueError('ambiguous base phandle: '+path)
            handles[hs[0]]=path
    symbols=bn.get('/__symbols__')
    fixes=[];by_slot={}
    fixnode=on.get('/__fixups__')
    if fixnode:
        for symbol in sorted(fixnode.properties):
            resolved=string(symbols.properties[symbol]) if symbols and symbol in symbols.properties else None
            if resolved and resolved not in bn:
                raise ValueError('base symbol points to absent source node')
            for location in fixnode.strings(symbol):
                path,key,off=location.rsplit(':',2)
                if not off.isdecimal():
                    raise ValueError('invalid fixup offset')
                offset=int(off);node=on.get(path)
                if not node or key not in node.properties or offset%4 or offset+4>len(node.properties[key]):
                    raise ValueError('fixup outside source property: '+location)
                slot=(path,key,offset)
                if slot in by_slot:
                    raise ValueError('ambiguous fixup source slot')
                row=dict(symbol=symbol,overlay_node=path,property=key,byte_offset=offset,
                         source_word_hex=node.properties[key][offset:offset+4].hex(),
                         base_symbol_path=resolved,resolved=resolved is not None)
                fixes.append(row);by_slot[slot]=row
    local_slots=set()
    for source,node in on.items():
        if source.startswith('/__local_fixups__/'):
            path=source[len('/__local_fixups__'):]
            actual=on.get(path)
            for key in node.properties:
                if actual is None or key not in actual.properties:
                    raise ValueError('local fixup points to absent source property')
                for offset in node.cells(key):
                    slot=(path,key,offset)
                    if offset%4 or offset+4>len(actual.properties[key]) or slot in local_slots or slot in by_slot:
                        raise ValueError('invalid/ambiguous local fixup slot')
                    local_slots.add(slot)
    fragments=[]
    for fragment in overlay.children:
        if not fragment.name.startswith('fragment@'):
            continue
        path='/'+fragment.name;props=fragment.properties;target=None;method=None
        if ('target' in props)==('target-path' in props):
            raise ValueError('fragment requires exactly one target representation')
        if 'target-path' in props:
            target=string(props['target-path']);method='source-target-path'
            if not target.startswith('/'):
                raise ValueError('target-path must be absolute')
            if target not in bn:
                target=None
        else:
            value=fragment.scalar('target');fix=by_slot.get((path,'target',0))
            if (path,'target',0) in local_slots:
                target=None;method='overlay-local-fixup-unapplied'
            elif fix:
                target=fix['base_symbol_path'];method='external-symbol-source'
            else:
                target=handles.get(value);method='base-phandle-source'
        body=on.get(path+'/__overlay__')
        if body is None:
            raise ValueError('fragment lacks __overlay__ source')
        source_nodes=[]
        prefix=path+'/__overlay__'
        for source,node in on.items():
            if source==prefix or source.startswith(prefix+'/'):
                suffix=source[len(prefix):]
                relation=(target.rstrip('/')+suffix or '/') if target is not None else None
                source_nodes.append(dict(overlay_node=source,base_relation_path=relation,
                                         properties_hex={k:v.hex() for k,v in sorted(node.properties.items())}))
        fragments.append(dict(source_fragment=path,target_method=method,base_target=target,
                              target_resolved=target is not None,source_nodes=source_nodes))
    return dict(scope='source relations only;no effective merged DT or hardware policy',
                fixups=fixes,fragments=fragments,
                local_fixup_source={p:{k:v.hex() for k,v in n.properties.items()} for p,n in on.items()
                                    if p=='/__local_fixups__' or p.startswith('/__local_fixups__/')},
                overlay_applied=False,boot_variant_selected=False,generated_policy=False,hardware_qualification=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('base','overlay'):
        p.add_argument('--'+name,type=Path,required=True)
        p.add_argument('--'+name+'-sha256',required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();trees=[];inputs={}
    for name in ('base','overlay'):
        path=getattr(a,name);blob=path.read_bytes();digest=hashlib.sha256(blob).hexdigest()
        if digest!=getattr(a,name+'_sha256'):
            p.error(name+' source SHA mismatch')
        trees.append(read_fdt(blob));inputs[name]=dict(path=str(path.resolve()),sha256=digest)
    result=inspect(*trees);result['inputs']=inputs
    with a.out.open('x') as f:
        json.dump(result,f,indent=2);f.write('\n')


if __name__=='__main__':
    main()

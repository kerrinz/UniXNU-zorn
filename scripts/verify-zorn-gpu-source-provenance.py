#!/usr/bin/env python3
"""Verify declared graph property bytes against a separately SHA-pinned saved DTB."""
import argparse,ast,builtins,hashlib,json,re,struct,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2]
PARSER=R/'UniXNU/scripts/unixnu/devicetree.py'
PARSER_SHA='cfda7d9aad326729d1e60bbf2db555c3d1af298d25747377b314dac007e8097d'
CHECKER=R/'out/zorn/gpu-votes-source-identity-20261103/candidate.py'
CHECKER_SHA='7ad80015d140f5ed62bd10ee54923743041fc7d3e769eeb1ce6b4790705e3923'
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def unique(pairs):
    d={}
    for k,v in pairs:
        if k in d:raise ValueError('duplicate JSON key')
        d[k]=v
    return d

def verify(doc,root):
    actual={}
    def visit(n,path):
        if path in actual:raise ValueError('ambiguous raw source path')
        actual[path]=n
        for child in n.children:visit(child,path.rstrip('/')+'/'+child.name)
    visit(root,'/')
    rows=doc.get('nodes') if isinstance(doc,dict) else None
    if not isinstance(rows,list) or not rows:raise ValueError('source node rows required')
    seen=set()
    for row in rows:
        if not isinstance(row,dict):raise ValueError('invalid source row')
        path=row.get('path');props=row.get('properties_hex')
        if not isinstance(path,str) or path not in actual:raise ValueError('declared node absent from raw source')
        if path in seen:raise ValueError('duplicate declared path')
        seen.add(path)
        if not isinstance(props,dict):raise ValueError('source property object required')
        decoded={}
        for k,v in props.items():
            if not isinstance(v,str) or re.fullmatch(r'(?:[0-9a-fA-F]{2})*',v) is None:raise ValueError('invalid raw property hex')
            decoded[k]=bytes.fromhex(v)
        if decoded!=actual[path].properties:raise ValueError('declared property set/bytes differ from raw source: '+path)
        if 'source_enabled' in row and (type(row['source_enabled']) is not bool or row['source_enabled']!=actual[path].enabled()):raise ValueError('declared source status differs from raw source')
    return actual,len(seen)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['input','dtb']:
        p.add_argument('--'+name,type=Path,required=True);p.add_argument('--'+name+'-sha256',required=True)
    a=p.parse_args();result=dict(accepted=False,raw_source_verified=False,generated_policy=False,hardware_qualification=False,
                               scope='declared node properties/status only;JSON reference edges/root selection not attested')
    try:
        src=a.input.read_bytes();raw=a.dtb.read_bytes()
        if sha(src)!=a.input_sha256:raise ValueError('source JSON SHA mismatch')
        if sha(raw)!=a.dtb_sha256:raise ValueError('raw DTB SHA mismatch')
        if len(src)>16*1024*1024:raise ValueError('source JSON reader bound')
        if sha(PARSER.read_bytes())!=PARSER_SHA or sha(CHECKER.read_bytes())!=CHECKER_SHA:raise ValueError('pinned parser/checker changed')
        doc=json.loads(src,object_pairs_hook=unique)
        if isinstance(doc,dict) and isinstance(doc.get('input'),dict) and doc['input'].get('sha256')!=a.dtb_sha256:raise ValueError('declared original SHA differs from supplied raw source')
        sys.path.insert(0,str(R/'UniXNU/scripts'));from unixnu.devicetree import read_fdt,Error
        try:actual,count=verify(doc,read_fdt(raw))
        except (Error,UnicodeError,struct.error) as e:raise ValueError('Invalid raw DTB source: '+str(e)) from e
        result.update(raw_source_verified=True,declared_nodes_verified=count,whole_tree_nodes=len(actual),declared_node_set_complete=count==len(actual),input_json_sha256=sha(src),raw_dtb_sha256=sha(raw),raw_parser_sha256=PARSER_SHA)
        module=ast.parse(CHECKER.read_text());fn=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='validate_source_nodes')
        if fn.decorator_list or fn.args.defaults:raise ValueError('unexpected checker entry metadata')
        env={'__builtins__':{k:getattr(builtins,k) for k in ['ValueError','isinstance','dict','str','bytes','int','set','len','range']}}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'pinned-pure-source-entry','exec'),env)
        # Validate the WHOLE original source tree,not a caller-trimmed JSON subset.
        result['source_schema']=env['validate_source_nodes']({path:n.properties for path,n in actual.items()});result['accepted']=True
    except (ValueError,TypeError,OSError,StopIteration) as e:result['error']=str(e)
    print(json.dumps(result));return 0 if result['accepted'] else 2

if __name__=='__main__':raise SystemExit(main())

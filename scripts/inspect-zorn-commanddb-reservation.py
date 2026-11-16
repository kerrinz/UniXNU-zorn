#!/usr/bin/env python3
"""Read SHA-bound DT reservation descriptions, never memory or a live CommandDB."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'UniXNU/scripts'))
from unixnu.devicetree import read_fdt

MAX_BYTES=4*1024*1024


def one_cell(properties,key):
    raw=properties.get(key)
    if raw is None or len(raw)!=4:
        raise ValueError('explicit single-cell parent '+key+' required')
    n=int.from_bytes(raw,'big')
    if n not in (1,2):raise ValueError('unsupported explicit parent '+key)
    return n


def describe(root):
    rows=[]
    def walk(n,path):
        if 'qcom,cmd-db' in n.strings('compatible'):
            if n.parent is None or path.rsplit('/',1)[0]!='/reserved-memory':
                raise ValueError('CommandDB description requires direct reserved-memory parent')
            parent=n.parent.properties;ac=one_cell(parent,'#address-cells');sc=one_cell(parent,'#size-cells')
            reg=n.properties.get('reg')
            width=4*(ac+sc)
            if reg is None or not reg or len(reg)%width:raise ValueError('reg must contain complete explicit-width tuples')
            for flag in ('no-map','reusable'):
                if flag in n.properties and n.properties[flag]!=b'':raise ValueError(flag+' must be an empty boolean')
            if 'no-map' in n.properties and 'reusable' in n.properties:raise ValueError('contradictory no-map/reusable description')
            ranges=parent.get('ranges')
            # Translation is deliberately unsupported;do not decode nonempty ranges
            # with guessed ancestor cells or turn absent ranges into identity.
            ranges_kind='absent-translation-unknown' if ranges is None else ('empty-source-identity-description' if not ranges else 'nonempty-translation-uninterpreted')
            tuples=[]
            for offset in range(0,len(reg),width):
                raw=reg[offset:offset+width]
                tuples.append(dict(raw_hex=raw.hex(),address_cells_hex=raw[:4*ac].hex(),size_cells_hex=raw[4*ac:].hex(),interpretation='source cells only;no address accessor or mapping grant'))
            rows.append(dict(path=path,properties_hex={k:v.hex() for k,v in n.properties.items()},parent_cell_properties_hex={k:parent[k].hex() for k in ('#address-cells','#size-cells','ranges') if k in parent},address_cell_count=ac,size_cell_count=sc,reg_tuples=tuples,ranges_kind=ranges_kind,no_map_description='present' if 'no-map' in n.properties else 'absent-no-permission-inferred',status_raw_hex=n.properties.get('status',b'').hex(),status_present='status' in n.properties))
        for child in n.children:walk(child,path.rstrip('/')+'/'+child.name)
    walk(root,'/')
    return dict(source_kind='DT-reservation-description',descriptions=rows,description_count=len(rows),variant_selected=False,commanddb_snapshot_usable=False,independently_qualified_expected_version=None,runtime_commanddb_presence='unknown',hardware_qualification=False,mapping_or_security_or_power_authority=False,generated_policy=False,device_operations=False,scope='DT source properties only;no memory bytes,physical accessor,translation execution,coherency or ownership qualification')


def inspect_source(path,expected_sha):
    with path.open('rb') as f:raw=f.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:raise ValueError('DT source byte limit exceeded')
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=expected_sha:raise ValueError('DT source SHA mismatch')
    result=describe(read_fdt(raw));result.update(source_sha256=digest,source_bytes=len(raw));return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--sha256',required=True);p.add_argument('--require-commanddb-snapshot',action='store_true');a=p.parse_args()
    try:
        result=inspect_source(a.input,a.sha256)
        print(json.dumps(result,indent=2));return 2 if a.require_commanddb_snapshot else 0
    except Exception as e:
        print(json.dumps(dict(error=str(e),commanddb_snapshot_usable=False,hardware_qualification=False,device_operations=False)));return 2


if __name__=='__main__':raise SystemExit(main())

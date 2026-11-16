#!/usr/bin/env python3
"""Decode a supplied raw CommandDB file for offline review;never qualify hardware or ownership."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

MAX_FILE_BYTES=4*1024*1024
MAX_REVIEW_ENTRIES=4096
# Output cost counts repeated AUX slices,not only unique input bytes.
MAX_TOTAL_AUX_BYTES=8*1024*1024
HEADER_BYTES=144
MAGIC=bytes.fromhex('db30030c')


def span(at,size,total):
    if at<0 or size<0 or at>total or size>total-at:
        raise ValueError('file extent outside complete supplied bytes')


def decode(raw,expected_bytes,expected_sha):
    if not HEADER_BYTES<=expected_bytes<=MAX_FILE_BYTES:
        raise ValueError('declared file size outside offline reader budget')
    if len(raw)!=expected_bytes:raise ValueError('file length differs from declared complete input size')
    # Freeze mutable caller buffers before the validation/materialization passes.
    raw=bytes(raw)
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=expected_sha:raise ValueError('raw input SHA mismatch')
    if raw.startswith((b'\x7fELF',bytes.fromhex('d00dfeed'))):
        raise ValueError('firmware/DT container is not a raw reservation file')
    if raw[4:8]!=MAGIC:raise ValueError('CommandDB byte-layout magic mismatch')
    rows=[];active=[];stopped=False;total=0
    for i in range(8):
        at=8+16*i;r=raw[at:at+16];slave,head,aux,count=struct.unpack_from('<4H',r)
        is_active=not stopped and slave!=0
        if not stopped and slave==0:stopped=True
        row=dict(index=i,raw_hex=r.hex(),in_linux_search_prefix=is_active)
        if is_active:
            total+=count
            if total>MAX_REVIEW_ENTRIES:raise ValueError('aggregate entry count exceeds offline review budget')
            head+=HEADER_BYTES;aux+=HEADER_BYTES
            span(head,count*24,len(raw));span(aux,0,len(raw))
            row.update(entry_count=count,entry_file_offset=head,aux_file_offset=aux)
            active.append((row,head,aux,count))
        rows.append(row)
    # Preflight ALL AUX extents and total exported bytes before constructing
    # per-entry hex strings.Aliased AUX ranges still incur repeated output cost.
    aux_total=0
    for _,head,aux,count in active:
        for i in range(count):
            size,offset=struct.unpack_from('<2H',raw,head+i*24+20)
            span(aux+offset,size,len(raw))
            if size>MAX_TOTAL_AUX_BYTES-aux_total:
                raise ValueError('aggregate AUX export exceeds offline output budget')
            aux_total+=size
    all_heads=[(head,count*24) for _,head,_,count in active];ids={}
    for row,head,aux,count in active:
        entries=[]
        for i in range(count):
            at=head+i*24;e=raw[at:at+24];size,offset=struct.unpack_from('<2H',e,20);offset+=aux
            span(offset,size,len(raw))
            overlaps=bool(size and any(offset<h+n and h<offset+size for h,n in all_heads if n))
            entries.append(dict(index=i,file_offset=at,raw_hex=e.hex(),resource_id_raw_hex=e[:8].hex(),priority_raw_hex=e[8:16].hex(),resource_address_raw_hex=e[16:20].hex(),aux_file_offset=offset,aux_bytes=size,aux_raw_hex=raw[offset:offset+size].hex(),aux_overlaps_record_table=overlaps))
            ids.setdefault(e[:8].hex(),[]).append([row['index'],i])
        row['entries']=entries
    return dict(decoded=True,scope='offline file layout and raw fields only;no runtime readiness,version,authenticity or mapping qualification',source_kind='caller-declared raw reservation file;capture origin unverified',source_sha256=digest,source_bytes=len(raw),header_raw_hex=raw[:HEADER_BYTES].hex(),observed_version_raw_hex=raw[:4].hex(),rows=rows,entry_count=total,duplicate_resource_ids={k:v for k,v in ids.items() if len(v)>1},review_entry_budget=MAX_REVIEW_ENTRIES,checksum_verified=False,snapshot_qualified=False,expected_version_qualified=False,capture_coherency_qualified=False,runtime_presence='unknown',selected_policy=False,hardware_qualification=False,native_execution=False,device_operations=False)


def read_decode(path,expected_bytes,expected_sha):
    if not HEADER_BYTES<=expected_bytes<=MAX_FILE_BYTES:raise ValueError('declared file size outside offline reader budget')
    with path.open('rb') as f:raw=f.read(expected_bytes+1)
    return decode(raw,expected_bytes,expected_sha)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw-reservation-file',type=Path,required=True)
    p.add_argument('--expected-bytes',type=int,required=True,help='Independently declared complete file size;not a memory-access grant')
    p.add_argument('--source-sha256',required=True)
    a=p.parse_args()
    try:result=read_decode(a.raw_reservation_file,a.expected_bytes,a.source_sha256)
    except (OSError,ValueError) as e:
        print(json.dumps(dict(decoded=False,error=str(e),snapshot_qualified=False,expected_version_qualified=False,hardware_qualification=False,device_operations=False)));return 2
    print(json.dumps(result,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())

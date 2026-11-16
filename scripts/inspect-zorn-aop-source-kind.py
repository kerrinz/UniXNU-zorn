#!/usr/bin/env python3
"""Inspect local static ELF32 file extents;never qualify a live CommandDB snapshot."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

MAX_FILE_BYTES=64*1024*1024
# Repeated/overlapping PH ranges each consume hashing work.
MAX_TOTAL_PAYLOAD_HASH_BYTES=64*1024*1024
MAGIC=bytes.fromhex('db30030c')


def read_bounded_source(path):
    with path.open('rb') as f:raw=f.read(MAX_FILE_BYTES+1)
    if len(raw)>MAX_FILE_BYTES:raise ValueError('local source file reader bound')
    return raw


def extent(offset,size,total):
    return offset<=total and size<=total-offset


def inspect(blob):
    """Known ELF32 little-endian source envelope only;no loading or address output."""
    if len(blob)<52:raise ValueError('truncated ELF32 source header')
    fields=struct.unpack_from('<16sHHIIIIIHHHHHH',blob)
    ident,kind,machine,version,entry,phoff,shoff,flags,ehsize,phsize,phnum,shsize,shnum,shstrings=fields
    if ident[:4]!=b'\x7fELF' or ident[4]!=1 or ident[5]!=1 or ident[6]!=1:
        raise ValueError('ELF32 little-endian source envelope required;no snapshot eligibility inferred')
    if version!=1 or ehsize!=52:raise ValueError('unsupported ELF source header version/size')
    if phnum==0xffff or phnum>4096 or shnum>4096 or shstrings==0xffff:
        raise ValueError('extended/oversized ELF tables are outside this source reader')
    if phnum:
        if phsize!=32 or phoff<ehsize or not extent(phoff,phnum*phsize,len(blob)):
            raise ValueError('invalid source program-table extent')
    elif phoff or phsize not in (0,32):raise ValueError('unexpected empty program-table metadata')
    if shnum:
        if shsize!=40 or shoff<ehsize or not extent(shoff,shnum*shsize,len(blob)) or shstrings>=shnum:
            raise ValueError('invalid source section-table extent/index')
    elif shoff or shstrings or shsize not in (0,40):
        raise ValueError('extended/contradictory empty section metadata unsupported')
    programs=[];program_fields=[];payload_hash_bytes=0
    for i in range(phnum):
        ptype,offset,vaddr,paddr,file_bytes,memory_bytes,pflags,alignment=struct.unpack_from('<8I',blob,phoff+i*phsize)
        if file_bytes and not extent(offset,file_bytes,len(blob)):
            raise ValueError('program file extent outside supplied source')
        # PT_NULL metadata spans in these files contain bytes while memsz is0.
        # Do not apply a PT_LOAD memory-size rule to every program-table row.
        if ptype==1 and file_bytes>memory_bytes:raise ValueError('load source file bytes exceed declared memory bytes')
        if alignment not in (0,1) and alignment&(alignment-1):raise ValueError('non-power-of-two source alignment')
        if file_bytes>MAX_TOTAL_PAYLOAD_HASH_BYTES-payload_hash_bytes:
            raise ValueError('aggregate program payload hashing exceeds offline work budget')
        payload_hash_bytes+=file_bytes
        program_fields.append((ptype,offset,file_bytes,memory_bytes,pflags,alignment))
    # Validate every PH range/work budget before hashing the first payload.
    for i,(ptype,offset,file_bytes,memory_bytes,pflags,alignment) in enumerate(program_fields):
        payload=blob[offset:offset+file_bytes] if file_bytes else b''
        programs.append(dict(index=i,type_raw=ptype,file_offset_raw=offset,file_bytes=file_bytes,
                             declared_memory_bytes=memory_bytes,flags_raw=pflags,alignment_raw=alignment,
                             file_payload_present=file_bytes>0,payload_sha256=hashlib.sha256(payload).hexdigest(),
                             file_extent_verified=file_bytes>0,
                             covers_header_and_program_table=offset==0 and file_bytes>=phoff+phnum*phsize))
    sections=[]
    for i in range(shnum):
        name,stype,sflags,address,offset,size,link,info,alignment,entsize=struct.unpack_from('<10I',blob,shoff+i*shsize)
        backed=stype!=8 and size>0
        if backed and not extent(offset,size,len(blob)):raise ValueError('section file extent outside supplied source')
        sections.append(dict(index=i,type_raw=stype,flags_raw=sflags,file_offset_raw=offset,
                             declared_bytes=size,file_backed=backed,file_extent_verified=backed))
    positions=[];start=0;more=False
    while True:
        at=blob.find(MAGIC,start)
        if at<0:break
        if len(positions)==64:more=True;break
        positions.append(at);start=at+1
    return dict(source_kind='static-ELF32-little-endian-file',container_bounds_verified=True,
                elf_type_raw=kind,elf_machine_raw=machine,elf_flags_raw=flags,
                program_table=dict(file_offset=phoff,entry_bytes=phsize,count=phnum),
                section_table=dict(file_offset=shoff,entry_bytes=shsize,count=shnum),
                programs=programs,sections=sections,literal_cmd_db_magic_file_offsets=positions,
                literal_scan_complete=not more,source_authentication_verified=False,
                commanddb_snapshot_usable=False,independently_qualified_expected_version=None,
                runtime_commanddb_presence='unknown',hardware_qualification=False,
                mapping_or_security_or_power_authority=False,generated_policy=False,device_operations=False,
                reason='static firmware bytes are not a complete coherent platform-owned memory snapshot;literal magic does not qualify version,ownership or live DB presence',
                scope='file envelope/extents only;no load addresses,execution,signature verification or policy adoption')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True)
    p.add_argument('--sha256',required=True);p.add_argument('--require-commanddb-snapshot',action='store_true')
    args=p.parse_args();result=dict(container_bounds_verified=False,commanddb_snapshot_usable=False,
                                  hardware_qualification=False,generated_policy=False,device_operations=False)
    try:
        raw=read_bounded_source(args.input)
        digest=hashlib.sha256(raw).hexdigest()
        if digest!=args.sha256:raise ValueError('local source SHA mismatch')
        result.update(inspect(raw),input=dict(path=str(args.input.resolve()),sha256=digest,bytes=len(raw)))
        if args.require_commanddb_snapshot:
            result['error']='refused:static ELF firmware cannot satisfy the complete coherent CommandDB snapshot/independent-version contract'
            print(json.dumps(result,indent=2));return 2
    except (OSError,ValueError,struct.error) as exc:
        result['error']=str(exc);print(json.dumps(result));return 2
    print(json.dumps(result,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())

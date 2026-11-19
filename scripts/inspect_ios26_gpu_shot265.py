"""Decode bounded source-defined K80 SHOT chunks;CPU pixels are not scanout proof."""
import hashlib,struct,zlib
from pathlib import Path
from inspect_ios26_gpu_pool264 import inspect_progress as inspect_previous
from inspect_ios26_gpu_progress236 import MAGIC,WIRE_LIMIT
SHOT_MAGIC=b'K80SH265'
SHOT_BYTES=16+48*104*4+64

def split_stream(data,tag):
    if len(data)>WIRE_LIMIT:raise ValueError('shot265 wire bound exceeded')
    expected=bytes.fromhex(tag)
    if len(expected)!=16:raise ValueError('shot265 boot tag width differs')
    normal=bytearray();payload=bytearray();packets=0;whole_crc=None;partial=0;at=0
    while at<len(data):
        tail=data[at:]
        if tail.startswith(SHOT_MAGIC):
            if len(tail)<48:partial=len(tail);break
            if tail[8:24]!=expected:raise ValueError('shot265 foreign boot')
            offset,n,total,crc,image_crc,schema=struct.unpack_from('<6I',tail,24)
            if schema!=265 or total!=SHOT_BYTES or offset!=len(payload) or not 0<n<=3024 or n!=min(3024,total-offset):raise ValueError('shot265 chunk bounds/order differ')
            if whole_crc is not None and whole_crc!=image_crc:raise ValueError('shot265 image identity changed')
            whole_crc=image_crc
            if len(tail)<48+n:partial=len(tail);break
            part=tail[48:48+n]
            if zlib.crc32(part)!=crc:raise ValueError('shot265 chunk CRC differs')
            payload.extend(part);packets+=1
            if packets>7:raise ValueError('shot265 chunk count exceeded')
            at+=48+n;continue
        if tail.startswith(MAGIC):normal.extend(tail);break
        if SHOT_MAGIC.startswith(tail):partial=len(tail);break
        end=data.find(b'\r\n',at)
        if end<0:normal.extend(tail);break
        normal.extend(data[at:end+2]);at=end+2
    complete=len(payload)==SHOT_BYTES and not partial
    if complete and zlib.crc32(payload)!=whole_crc:raise ValueError('shot265 full image CRC differs')
    record=None
    if complete:
        if payload[:16]!=b'SHOT'+struct.pack('<3I',48,104,192):raise ValueError('shot265 BGRX layout differs')
        record=list(struct.unpack_from('<16I',payload,16+48*104*4))
        if record[0]!=2 or not record[1] or record[3] not in (1,2) or record[9]!=1:raise ValueError('shot265 completed CPU copy record differs')
        if not all(0<v<=16384 for v in record[13:15]):raise ValueError('shot265 logical geometry differs')
    return bytes(normal),bytes(payload),dict(packet_count=packets,partial_packet_bytes=partial,payload_bytes=len(payload),expected_payload_bytes=SHOT_BYTES,complete=complete,width=48,height=104,stride=192,source_present_record=record,payload_sha256=hashlib.sha256(payload).hexdigest(),physical_scanout_proven=False,GPU_surface_write_proven=False)

def inspect_progress(data,tag,program_tag):
    normal,payload,shot=split_stream(data,tag);result=inspect_previous(normal,tag,program_tag)
    total=result['frame_count']+shot['packet_count']
    if total>38:raise ValueError('shot265 original nonterminal frame budget exceeded')
    if shot['partial_packet_bytes']:result['transport_frames_valid']=False
    result['serial_shot265']=shot;result['wire_nonterminal_frames265']=total
    result['full_GPU_qualification']=False
    return result

def save_shot(data,tag,out):
    _,payload,shot=split_stream(data,tag)
    if not shot['complete']:return None
    path=Path(out)/'screen265.bgrx'
    with path.open('xb') as stream:stream.write(payload)
    return dict(path=str(path),sha256=shot['payload_sha256'],bytes=len(payload),physical_scanout_proven=False)

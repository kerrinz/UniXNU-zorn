"""CRC-bound upper-right CPU thumbnail;never full-screen/GPU-write acceptance."""
import hashlib,struct,zlib
from pathlib import Path
from inspect_ios26_ui_scene269 import inspect_progress as inspect_previous,split_scene,UI_MAGIC
from inspect_ios26_gpu_progress236 import MAGIC,WIRE_LIMIT,save_panic as save_previous_panic
ROI_MAGIC=b'K80SH270'
IMAGE_BYTES=20048

def split_roi(data,tag):
    if len(data)>WIRE_LIMIT:raise ValueError('roi270 wire bound exceeded')
    expected=bytes.fromhex(tag)
    if len(expected)!=16:raise ValueError('roi270 boot tag width differs')
    normal=bytearray();pixels=bytearray();at=0;packets=0;whole=None;roi=None;partial=0
    while at<len(data):
        tail=data[at:]
        if tail.startswith(ROI_MAGIC):
            if len(tail)<68:partial=len(tail);break
            if tail[8:24]!=expected:raise ValueError('roi270 foreign boot')
            offset,n,total,crc,image_crc,schema=struct.unpack_from('<6I',tail,24)
            selected=struct.unpack_from('<4I',tail,48);header_crc=struct.unpack_from('<I',tail,64)[0]
            if zlib.crc32(tail[:64])!=header_crc:raise ValueError('roi270 header CRC differs')
            x,y,w,h=selected
            if schema!=270 or total!=IMAGE_BYTES or offset!=len(pixels) or not 0<n<=3004 or n!=min(3004,total-offset):raise ValueError('roi270 chunk bounds/order differ')
            if y or x!=w or not 48<=w<=8192 or not 104<=h<=8192:raise ValueError('roi270 source quadrant differs')
            if (whole is not None and whole!=image_crc) or (roi is not None and roi!=selected):raise ValueError('roi270 image/ROI identity changed')
            whole=image_crc;roi=selected
            if len(tail)<68+n:partial=len(tail);break
            part=tail[68:68+n]
            if zlib.crc32(part)!=crc:raise ValueError('roi270 chunk CRC differs')
            pixels.extend(part);packets+=1
            if packets>7:raise ValueError('roi270 chunk count exceeded')
            at+=68+n;continue
        if ROI_MAGIC.startswith(tail):partial=len(tail);break
        if tail.startswith(b'K80SH265'):raise ValueError('roi270 selected producer received legacy full-frame packet')
        if tail.startswith(UI_MAGIC):
            if len(tail)<96:normal.extend(tail);break
            normal.extend(tail[:96]);at+=96;continue
        if tail.startswith(MAGIC):normal.extend(tail);break
        end=data.find(b'\r\n',at)
        if end<0:normal.extend(tail);break
        normal.extend(data[at:end+2]);at=end+2
    complete=len(pixels)==IMAGE_BYTES and not partial
    record=None
    if complete:
        if zlib.crc32(pixels)!=whole:raise ValueError('roi270 whole image CRC differs')
        if pixels[:16]!=b'SHOT'+struct.pack('<3I',48,104,192):raise ValueError('roi270 retained BGRX sampler layout differs')
        record=list(struct.unpack_from('<16I',pixels,16+19968))
        if record[0]!=2 or not record[1] or record[3] not in (1,2) or record[9]!=1:raise ValueError('roi270 actual completed CPU copy record differs')
        if not all(0<v<=16384 for v in record[13:15]):raise ValueError('roi270 logical source geometry differs')
    quadrant=None if roi is None else dict(x=roi[0],y=roi[1],width=roi[2],height=roi[3],full_panel_width=roi[2]*2,full_panel_height=roi[3]*2,space='actual retained CPU panel alias pixels;logical present dimensions remain in source record',normalized_x_range=[0.5,1.0],normalized_y_range=[0.0,0.5])
    return bytes(normal),bytes(pixels),dict(complete=complete,packet_count=packets,partial_packet_bytes=partial,payload_bytes=len(pixels),expected_payload_bytes=IMAGE_BYTES,width=48,height=104,stride=192,source_roi=quadrant,source_present_record=record,payload_sha256=hashlib.sha256(pixels).hexdigest(),source_ROI_headers_CRC_checked=True,full_screen_image=False,physical_scanout_proven=False,GPU_surface_write_proven=False)

def inspect_progress(data,tag,program_tag):
    normal,_,roi=split_roi(data,tag);r=inspect_previous(normal,tag,program_tag)
    total=r['wire_nonterminal_frames269']+roi['packet_count']
    if total>38:raise ValueError('roi270 original nonterminal budget exceeded')
    if roi['partial_packet_bytes']:r['transport_frames_valid']=False
    r['serial_roi270']=roi;r['wire_nonterminal_frames270']=total
    r['legacy_full_frame_SHOT265_selected']=False
    r['ROI_image_is_final_UI_acceptance']=False;r['full_GPU_qualification']=False
    return r

def save_shot(data,tag,out):
    _,pixels,roi=split_roi(data,tag)
    if not roi['complete']:return None
    path=Path(out)/'screen270-roi.bgrx'
    with path.open('xb') as f:f.write(pixels)
    return dict(path=str(path),sha256=roi['payload_sha256'],bytes=len(pixels),source_roi=roi['source_roi'],full_screen_image=False,physical_scanout_proven=False)

def save_panic(data,tag,out):
    normal,_,_=split_roi(data,tag);normal,_,_=split_scene(normal,tag)
    return save_previous_panic(normal,tag,out)

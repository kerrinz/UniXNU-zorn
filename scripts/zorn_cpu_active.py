"""Isolated E/20-ZCLA/2 decoder. V1 and production reader remain unchanged."""
import struct
import zlib

def validate(c):
    values=c['counters'];masks=c['masks'];status=c['status'];bounds=c['bounds_ms'];clock=c['clock_mach']
    if len(values)!=32 or len(status)!=16 or len(bounds)!=4 or len(clock)!=4:raise ValueError('shape')
    if any(not 0<=v<=0xffffffff for v in values+bounds+clock):raise ValueError('u32')
    if not 0<=c['tick_interval_ns']<=0xffffffffffffffff or not 0<=c['error']<=65535:raise ValueError('header range')
    if len(masks)!=2 or any(not 0<=v<=255 for v in masks):raise ValueError('mask')
    for i,s in enumerate(status):
        if not 0<=s<=255:raise ValueError('status range')
        present=bool(masks[i//8]&(1<<(i%8)))
        if present!=(s==0):raise ValueError('status/mask')
        if not present and any(values[i*2:i*2+2]):raise ValueError('invalid counter publication')
    if c['error']:return
    if not c['tick_interval_ns'] or masks!=[255,255] or not clock[0] or len(set(clock))!=1:raise ValueError('clock/completeness')
    if bounds!=sorted(bounds) or not 60000<=bounds[0]<=120000 or not 240000<=bounds[2]<=270000:raise ValueError('sample windows')

def encode(block,c):
    validate(c)
    if len(block)!=4096 or block[:8]!=b'ZORNLOGD' or struct.unpack_from('<I',block,1032)[0]!=19:raise ValueError('source')
    ring(block)
    text=[]
    for i in range(84):
        slot=block[16+i*12:28+i*12]
        if slot[11] or any(v>127 for v in slot[:11]):raise ValueError('text')
        text.extend(slot[:11])
    packed=bytearray(809)
    for i,value in enumerate(text):
        bit=i*7;at=bit//8;shift=bit%8;packed[at]|=(value<<shift)&255
        if shift>1:packed[at+1]|=value>>(8-shift)
    body=struct.pack('<4sBBHBBQ4I',b'ZCLA',2,4,c['error'],*c['masks'],c['tick_interval_ns'],*c['bounds_ms'])
    body+=bytes(c['status'])+struct.pack('<4I32I',*c['clock_mach'],*c['counters'])
    assert len(body)==194
    out=bytearray(block);out[:8]=b'ZORNLOGE';out[16:1024]=packed+body+struct.pack('<I',zlib.crc32(block+body))+b'\0'
    struct.pack_into('<I',out,1032,20);return bytes(out)

def ring(block):
    count,pos=struct.unpack_from('<II',block,8)
    if count>84 or pos>=84 or (count<84 and pos!=count):raise ValueError('ring')

def decode(block):
    if len(block)!=4096 or block[:8]!=b'ZORNLOGE' or struct.unpack_from('<I',block,1032)[0]!=20:raise ValueError('envelope')
    ring(block);body=block[825:1019]
    magic,version,width,error,mask0,mask1,ns,*bounds=struct.unpack_from('<4sBBHBBQ4I',body)
    if (magic,version,width)!=(b'ZCLA',2,4) or block[824]&240 or block[1023]:raise ValueError('version/padding')
    c=dict(counters=list(struct.unpack_from('<32I',body,66)),bounds_ms=bounds,tick_interval_ns=ns,
           masks=[mask0,mask1],error=error,status=list(body[34:50]),clock_mach=list(struct.unpack_from('<4I',body,50)))
    validate(c)
    original=bytearray(block);original[:8]=b'ZORNLOGD';struct.pack_into('<I',original,1032,19)
    for i in range(924):
        bit=i*7;at=16+bit//8;shift=bit%8
        original[16+(i//11)*12+i%11]=(int.from_bytes(block[at:at+2],'little')>>shift)&127
    for i in range(84):original[16+i*12+11]=0
    if zlib.crc32(bytes(original)+body)!=struct.unpack_from('<I',block,1019)[0]:raise ValueError('CRC')
    return dict(c,original_block=bytes(original),measurement_available=error==0,
                idle_observed=False,instantaneous_load_proven=False)

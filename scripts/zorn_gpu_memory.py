"""Exact D/v21-GPM1 GPU-memory capture; restores all original D/v18 bytes."""
import struct
import zlib
from zorn_display_progress import SLOTS
PAGES=(19,27,19,37,1,1,16,18)
def decode(block):
    if len(block)!=4096 or block[:8]!=b'ZORNLOGD' or block[1024:1032]!=b'ZORNGUI1' or struct.unpack_from('<II',block,1032)!=(21,3072):
        raise ValueError('not GPU-memory v21')
    view=list(struct.unpack_from('<32Q',block,1104));v=[view[i]>>32 for i in SLOTS]
    if v[14]!=0x314d5047:raise ValueError('GPU-memory payload magic')
    original=bytearray(block);crc_at=1104+31*8+4;struct.pack_into('<I',original,crc_at,0)
    if zlib.crc32(original)!=v[15]:raise ValueError('GPU-memory CRC')
    h=v[0];state=h&15;phase=(h>>4)&15;index=(h>>8)&15;failure=(h>>12)&15;bits=(h>>16)&63;planned=(h>>22)&1;plan_status=(h>>23)&15
    attempted=v[2]&255;backed=(v[2]>>8)&255;described=(v[2]>>16)&255;quarantine=v[2]>>24
    if h>>27 or state not in (2,3) or phase not in range(1,6) or index>8 or failure>5 or plan_status>7 or bits not in (32,36,40,42,44,48) or not v[3] or attempted&(attempted+1) or backed&~attempted or described&~backed or quarantine&~backed:
        raise ValueError('GPU-memory header/masks')
    if state==2 and (failure or v[1] or attempted!=255 or backed!=255 or described!=255 or quarantine or not planned or plan_status):raise ValueError('GPU-memory prepared contradiction')
    if state==3 and (not failure or not v[1]):raise ValueError('GPU-memory failed contradiction')
    if not planned and plan_status:raise ValueError("unattempted plan status")
    snapshots=[]
    for i in range(8):
        pages=(v[12+i//4]>>((i%4)*8))&255;frame=v[4+i];present=bool(pages or frame)
        if present and (pages!=PAGES[i] or not frame or not (backed>>i)&1):raise ValueError('GPU-memory backing shape')
        if (described>>i)&1 and not present:raise ValueError('GPU-memory missing described PA')
        snapshots.append({'index':i,'snapshot_present':present,'description_accepted':bool((described>>i)&1),
                          'physical':frame<<12 if present else None,'bytes':pages*4096 if present else None})
    for i in SLOTS:view[i]&=0xffffffff
    struct.pack_into('<32Q',original,1104,*view);struct.pack_into('<I',original,1032,18)
    return {'original_block':bytes(original),'state':state,'phase':phase,'index':index,'failure_source':failure,
            'status':v[1],'epoch':v[3],'plan_attempted':bool(planned),'plan_status':plan_status if planned else None,
             'original_native_status':v[1] if failure==2 else 0,
            'original_gate_status':v[1] if failure==3 else 0,
            'original_snapshot_status':v[1] if failure==5 or failure==3 and phase==4 else 0,
            'allocation_status':[v[1] if failure==2 and index==i else 0 if (attempted>>i)&1 else 0xe00002d8 for i in range(8)],
            'output_policy_bits':bits,'attempted_mask' :attempted,'backed_mask':backed,'described_mask':described,
            'quarantined_mask':quarantine,'cleanup_status_available':not bool(quarantine),'snapshots':snapshots,
            'available':True,'runtime_complete':False,'physical_is_iova':False,
            'retained_bytes':sum(PAGES[i]*4096 for i in range(8) if (backed>>i)&1)}

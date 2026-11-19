"""One source-defined synthetic-scene result;UI outcome requires visual evidence."""
import struct,zlib
from inspect_ios26_client_census268 import inspect_progress as inspect_previous
from inspect_ios26_gpu_shot265 import SHOT_MAGIC,save_shot as save_previous_shot
from inspect_ios26_gpu_progress236 import MAGIC,WIRE_LIMIT
UI_MAGIC=b'K80UI269'
FIELDS=('phase','thread_raw','flags','ready_polls','subscriber_at_return','contact_dispatch_attempts',
        'contact_dispatch_returns','first_raw','lift_raw','elapsed_ms','x','start_y','end_y','steps','contact_id','outcome')

def split_scene(data,tag):
    if len(data)>WIRE_LIMIT:raise ValueError('ui269 wire bound exceeded')
    expected=bytes.fromhex(tag)
    if len(expected)!=16:raise ValueError('ui269 boot tag width differs')
    previous=bytearray();rows=[];at=0;partial=0
    while at<len(data):
        tail=data[at:]
        if tail.startswith(UI_MAGIC):
            if len(tail)<96:partial=len(tail);break
            packet=tail[:96]
            if packet[8:24]!=expected:raise ValueError('ui269 foreign boot')
            crc,schema=struct.unpack_from('<2I',packet,88)
            if schema!=269 or zlib.crc32(packet[:88])!=crc:raise ValueError('ui269 schema/CRC differs')
            v=struct.unpack_from('<16I',packet,24);r=dict(zip(FIELDS,v))
            if r['phase'] not in (6,7) or r['flags']&~1023 or r['subscriber_at_return']>1 or r['outcome']>3:raise ValueError('ui269 source state differs')
            if r['contact_dispatch_attempts']>17 or r['contact_dispatch_returns']>r['contact_dispatch_attempts'] or r['ready_polls']>120:raise ValueError('ui269 source call bound differs')
            if any(r[k] for k in ('x','start_y','end_y','steps','contact_id')) and v[10:15]!=(16384,32112,8192,16,1):raise ValueError('ui269 gesture plan differs')
            r['probe_exit_and_client_close_readiness_observed']=bool(r['flags']&512)
            r['all_bounded_contact_and_lift_dispatch_calls_returned_successfully']=(r['phase']==6 and r['thread_raw']==0 and r['flags']==1023 and 0<r['ready_polls']<=120 and r['contact_dispatch_attempts']==r['contact_dispatch_returns']==17 and r['first_raw']==r['lift_raw']==r['outcome']==0 and r['elapsed_ms']<=32000 and v[10:15]==(16384,32112,8192,16,1))
            r['event_delivery_or_unlock_proven']=False;r['physical_FT3683_sample']=False
            rows.append(r)
            if len(rows)>1:raise ValueError('ui269 repeated terminal scene packet')
            at+=96;continue
        if UI_MAGIC.startswith(tail):partial=len(tail);break
        if tail.startswith(SHOT_MAGIC):
            # Preserve the complete original packet. The unchanged SHOT parser
            # validates boot identity,chunk CRC,order,full CRC and dimensions.
            if len(tail)<48:previous.extend(tail);break
            n=struct.unpack_from('<I',tail,28)[0]
            if not 0<n<=3024:raise ValueError('ui269 SHOT packet bound differs')
            if len(tail)<48+n:previous.extend(tail);break
            previous.extend(tail[:48+n]);at+=48+n;continue
        if tail.startswith(MAGIC):previous.extend(tail);break
        end=data.find(b'\r\n',at)
        if end<0:previous.extend(tail);break
        previous.extend(data[at:end+2]);at=end+2
    return bytes(previous),rows,partial

def inspect_progress(data,tag,program_tag):
    previous,rows,partial=split_scene(data,tag);r=inspect_previous(previous,tag,program_tag)
    total=r['wire_nonterminal_frames265']+len(rows)
    if total>38 or r['frame_count']>30:raise ValueError('ui269 original frame budget exceeded')
    if partial:r['transport_frames_valid']=False
    r['synthetic_scene269']=rows[0] if rows else None;r['partial_ui_packet269']=partial
    r['synthetic_scene_dispatch_returned269']=bool(rows and rows[0]['all_bounded_contact_and_lift_dispatch_calls_returned_successfully'])
    r['wire_nonterminal_frames269']=total;r['synthetic_unlock_proven269']=False
    r['physical_FT3683_gestures_qualified269']=False;r['full_GPU_qualification']=False
    r['ui269_scope']='One separate virtual iOS26 HID service;bounded normalized swipe and explicit lift. Open subscriber and returned void-dispatch calls do not acknowledge queue admission,delivery,unlock or physical touch.'
    return r

def save_shot(data,tag,out):
    previous,_,_=split_scene(data,tag)
    return save_previous_shot(previous,tag,out)

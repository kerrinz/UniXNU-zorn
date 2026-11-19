"""Short held-contact result and actual CPU progress snapshots;menu needs visuals."""
import struct,zlib
from inspect_ios26_ui_desktop271 import inspect_progress as previous,save_shot271,save_panic as previous_panic
from inspect_ios26_ui_roi270 import ROI_MAGIC
from inspect_ios26_gpu_progress236 import MAGIC,WIRE_LIMIT
UI_MAGIC=b'K80UI273'
FIELDS=('phase','thread_raw','flags','subscriber_polls','subscriber_at_return','swipe_attempts','swipe_returns','swipe_first_raw','swipe_lift_raw','swipe_elapsed_ms','swipe_x','swipe_start_y','swipe_end_y','swipe_steps','identity','swipe_outcome','press_outcome','press_attempts','press_returns','press_first_raw','press_lift_attempted','press_lift_raw','press_elapsed_ms','press_x','press_y','press_reports','press_interval_ms','settle_ms','scene_budget_ms','compact_observer_dropped','before_uptime_ms','after_uptime_ms')
PROGRESS_FIELDS=('available','present_frame','producer_fence','completed_fence','surface_access_fence','surface_id','CF_dropped','backend_sequence','backend_stage','backend_raw','native_client_low32','native_client_flags','compact_dropped','application_calls','application_unique_low32','application_pid')
def split_menu(data,tag):
    if len(data)>WIRE_LIMIT:raise ValueError('menu273 wire bound exceeded')
    boot=bytes.fromhex(tag)
    if len(boot)!=16:raise ValueError('menu273 boot tag width differs')
    rest=bytearray();rows=[];partial=0;at=0
    while at<len(data):
        tail=data[at:]
        if tail.startswith(UI_MAGIC):
            if len(tail)<288:partial=len(tail);break
            p=tail[:288];crc,schema=struct.unpack_from('<2I',p,280)
            if p[8:24]!=boot or schema!=273 or zlib.crc32(p[:280])!=crc:raise ValueError('menu273 boot/schema/CRC differs')
            v=struct.unpack_from('<64I',p,24);r=dict(zip(FIELDS,v[:32]))
            if v[0] not in (6,7) or v[2]&~1023 or v[3]>120 or v[4]>1 or v[5]>17 or v[6]>v[5] or v[15]>3 or v[16]>3 or v[17]>2 or v[18]>v[17] or v[20]>1:raise ValueError('menu273 source call/state bounds differ')
            if any(v[10:15]) and v[10:15]!=(16384,32112,8192,16,1):raise ValueError('menu273 retained swipe differs')
            if any(v[23:29]) and v[23:29]!=(28330,3938,2,400,30000,70000):raise ValueError('menu273 prospective short-hold plan differs')
            snapshots=[]
            for offset in [32,48]:
                q=v[offset:offset+16]
                if q[0]&~7:raise ValueError('menu273 CPU progress availability differs')
                if not q[0]&1 and any(q[1:6]):raise ValueError('menu273 unavailable present has values')
                if not q[0]&2 and any(q[6:12]):raise ValueError('menu273 unavailable CF has values')
                if not q[0]&4 and any(q[12:]):raise ValueError('menu273 unavailable application has values')
                snapshots.append(dict(zip(PROGRESS_FIELDS,q)))
            first,last=snapshots
            returned=bool(v[0]==6 and not v[1] and v[2]==1023 and 0<v[3]<=120 and v[4]==1 and v[5]==v[6]==17 and not v[7] and not v[8] and v[9]<=32000 and v[10:15]==(16384,32112,8192,16,1) and not v[15] and not v[16] and v[17]==v[18]==2 and not v[19] and v[20]==1 and not v[21] and 800<=v[22]<=70000 and v[23:29]==(28330,3938,2,400,30000,70000))
            r.update(before=first,after=last,live_GPU_input_admission_observed=bool(v[2]&512),all_bounded_swipe_short_hold_and_lifts_returned=returned,compact_loss_observed=bool(v[29] and v[29]!=0xffffffff),compact_loss_snapshot_busy=v[29]==0xffffffff,source_surface_fence_advanced=bool(first['available']&1 and last['available']&1 and last['present_frame']>first['present_frame'] and last['completed_fence']>first['completed_fence']),backend_failure_observed=bool(any(s['available']&2 and s['backend_sequence'] for s in snapshots)),CF_diagnostic_loss_observed=bool(any(s['available']&2 and s['CF_dropped'] for s in snapshots)),Liquid_Glass_menu_visual_response_proven=False,stalled_fence_is_not_automatically_GPU_failure=True,physical_FT3683_sample=False)
            rows.append(r)
            if len(rows)>1:raise ValueError('menu273 repeated terminal packet')
            at+=288;continue
        if UI_MAGIC.startswith(tail):partial=len(tail);break
        if tail.startswith((b'K80UI269',b'K80UI271',b'K80UI272')):raise ValueError('menu273 received old scene schema')
        if tail.startswith(ROI_MAGIC):
            if len(tail)<68:rest.extend(tail);break
            n=struct.unpack_from('<I',tail,28)[0]
            if not 0<n<=3004:raise ValueError('menu273 ROI payload bound differs')
            if len(tail)<68+n:rest.extend(tail);break
            rest.extend(tail[:68+n]);at+=68+n;continue
        if tail.startswith(MAGIC):rest.extend(tail);break
        end=data.find(b'\r\n',at)
        if end<0:rest.extend(tail);break
        rest.extend(data[at:end+2]);at=end+2
    return bytes(rest),rows,partial
def inspect_progress(data,tag,program_tag):
    rest,rows,partial=split_menu(data,tag);r=previous(rest,tag,program_tag);total=r['wire_nonterminal_frames271']+len(rows)
    if total>38:raise ValueError('menu273 original frame budget exceeded')
    if partial:r['transport_frames_valid']=False
    r.update(synthetic_menu273=rows[0] if rows else None,partial_ui_packet273=partial,synthetic_menu_dispatch_returned273=bool(rows and rows[0]['all_bounded_swipe_short_hold_and_lifts_returned']),wire_nonterminal_frames273=total,ordinary_probe267_selected=False,Liquid_Glass_menu_functionally_qualified=False,GPU_desktop_stability_qualified=False,full_GPU_qualification=False)
    r['client_census268']['scope']='Actual registered native clients of selected live backboardd;no probe exit or four-query-client requirement.'
    r['menu273_scope']='Prospective800ms hold/release plus actual before/after CPU present/fence/CF snapshots. Time and returned calls do not prove a context-menu recognizer threshold,Liquid Glass correctness,or hang causation.'
    return r
def save_shot273(data,tag,out):
    rest,_,_=split_menu(data,tag);return save_shot271(rest,tag,out)
def save_panic(data,tag,out):
    rest,_,_=split_menu(data,tag);return previous_panic(rest,tag,out)

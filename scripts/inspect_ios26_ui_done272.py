"""New272 Done tap and explicit compact-loss counter;no old scene relabeling."""
import struct,zlib
from inspect_ios26_ui_desktop271 import inspect_progress as previous,save_shot271,save_panic as previous_panic
from inspect_ios26_ui_roi270 import ROI_MAGIC
from inspect_ios26_gpu_progress236 import MAGIC,WIRE_LIMIT
UI_MAGIC=b'K80UI272'
FIELDS=('phase','thread_raw','flags','subscriber_polls','subscriber_at_return','swipe_attempts','swipe_returns','swipe_first_raw','swipe_lift_raw','swipe_elapsed_ms','swipe_x','swipe_start_y','swipe_end_y','swipe_steps','identity','swipe_outcome','press_outcome','press_attempts','press_returns','press_first_raw','press_lift_attempted','press_lift_raw','press_elapsed_ms','press_x','press_y','press_reports','press_interval_ms','settle_ms','scene_budget_ms','compact_observer_dropped','reserved30','reserved31','done_outcome','done_attempts','done_returns','done_first_raw','done_lift_attempted','done_lift_raw','done_elapsed_ms','done_x','done_y','done_reports','done_interval_ms','gap_after_press_ms','done_scene_budget_ms','reserved45','reserved46','reserved47')
def split_done(data,tag):
    if len(data)>WIRE_LIMIT:raise ValueError('done272 wire bound exceeded')
    boot=bytes.fromhex(tag)
    if len(boot)!=16:raise ValueError('done272 boot tag width differs')
    rest=bytearray();rows=[];partial=0;at=0
    while at<len(data):
        tail=data[at:]
        if tail.startswith(UI_MAGIC):
            if len(tail)<224:partial=len(tail);break
            packet=tail[:224];crc,schema=struct.unpack_from('<2I',packet,216)
            if packet[8:24]!=boot or schema!=272 or zlib.crc32(packet[:216])!=crc:raise ValueError('done272 boot/schema/CRC differs')
            v=struct.unpack_from('<48I',packet,24);r=dict(zip(FIELDS,v))
            if v[0] not in (6,7) or v[2]&~1023 or v[3]>120 or v[4]>1 or v[5]>17 or v[6]>v[5] or v[15]>3 or v[16]>3 or v[17]>6 or v[18]>v[17] or v[20]>1 or any(v[30:32]) or v[32]>3 or v[33]>1 or v[34]>v[33] or v[36]>1 or any(v[45:]):raise ValueError('done272 source call/state bounds differ')
            if any(v[10:15]) and v[10:15]!=(16384,32112,8192,16,1):raise ValueError('done272 retained swipe differs')
            if any(v[23:29]) and v[23:29]!=(28330,3938,6,400,30000,70000):raise ValueError('done272 retained Settings hold differs')
            if any(v[39:45]) and v[39:45]!=(28671,1260,1,100,15000,85000):raise ValueError('done272 actual ROI-derived Done plan differs')
            first=bool(not v[1] and v[2]==1023 and 0<v[3]<=120 and v[4]==1 and v[5]==v[6]==17 and not v[7] and not v[8] and v[9]<=32000 and v[10:15]==(16384,32112,8192,16,1) and not v[15] and not v[16] and v[17]==v[18]==6 and not v[19] and v[20]==1 and not v[21] and 2400<=v[22]<=70000 and v[23:29]==(28330,3938,6,400,30000,70000))
            done=bool(v[32]==0 and v[33]==v[34]==1 and not v[35] and v[36]==1 and not v[37] and 100<=v[38]<=85000 and v[39:45]==(28671,1260,1,100,15000,85000))
            r.update(live_GPU_input_admission_observed=bool(v[2]&512),initial_swipe_hold_lifts_returned=first,Done_tap_and_lift_returned=done,all_bounded_scene_calls_returned=bool(v[0]==6 and first and done),compact_loss_observed=bool(v[29] and v[29]!=0xffffffff),compact_loss_snapshot_busy=v[29]==0xffffffff,Done_button_visual_response_proven=False,physical_FT3683_sample=False)
            rows.append(r)
            if len(rows)>1:raise ValueError('done272 repeated terminal packet')
            at+=224;continue
        if UI_MAGIC.startswith(tail):partial=len(tail);break
        if tail.startswith((b'K80UI271',b'K80UI269')):raise ValueError('done272 old scene schema received')
        if tail.startswith(ROI_MAGIC):
            if len(tail)<68:rest.extend(tail);break
            n=struct.unpack_from('<I',tail,28)[0]
            if not 0<n<=3004:raise ValueError('done272 ROI payload bound differs')
            if len(tail)<68+n:rest.extend(tail);break
            rest.extend(tail[:68+n]);at+=68+n;continue
        if tail.startswith(MAGIC):rest.extend(tail);break
        end=data.find(b'\r\n',at)
        if end<0:rest.extend(tail);break
        rest.extend(data[at:end+2]);at=end+2
    return bytes(rest),rows,partial
def inspect_progress(data,tag,program_tag):
    rest,rows,partial=split_done(data,tag);r=previous(rest,tag,program_tag);total=r['wire_nonterminal_frames271']+len(rows)
    if total>38:raise ValueError('done272 original frame budget exceeded')
    if partial:r['transport_frames_valid']=False
    r.update(synthetic_done272=rows[0] if rows else None,partial_ui_packet272=partial,synthetic_done_dispatch_returned272=bool(rows and rows[0]['all_bounded_scene_calls_returned']),wire_nonterminal_frames272=total,ordinary_probe267_selected=False,Done_behavioral_response_qualified=False,GPU_desktop_stability_qualified=False,full_GPU_qualification=False)
    r['client_census268']['scope']='Actual source-owned native client records of the selected live backboardd task;closed clients and active clients reported separately. No probe exit or four-query-client requirement.'
    r['done272_scope']='Actual271ROI-derived virtual Done tap after unchanged swipe/hold;legacy compact telemetry loss explicitly reported,actual CF/backend loss remains a refusal. Visual response requires exact-build image/video evidence.'
    return r
def save_shot272(data,tag,out):
    rest,_,_=split_done(data,tag);return save_shot271(rest,tag,out)
def save_panic(data,tag,out):
    rest,_,_=split_done(data,tag);return previous_panic(rest,tag,out)

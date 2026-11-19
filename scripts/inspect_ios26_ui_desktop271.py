"""Source271 live-GPU UI scene;never reinterpret probe269's readiness flag."""
import struct,zlib
from inspect_ios26_ui_roi270 import inspect_progress as previous,split_roi,ROI_MAGIC,save_shot,save_panic as previous_panic
from inspect_ios26_gpu_progress236 import MAGIC,WIRE_LIMIT
UI_MAGIC=b'K80UI271'
FIELDS=('phase','thread_raw','flags','subscriber_polls','subscriber_at_return','swipe_attempts','swipe_returns','swipe_first_raw','swipe_lift_raw','swipe_elapsed_ms','swipe_x','swipe_start_y','swipe_end_y','swipe_steps','identity','swipe_outcome','press_outcome','press_attempts','press_returns','press_first_raw','press_lift_attempted','press_lift_raw','press_elapsed_ms','press_x','press_y','press_reports','press_interval_ms','settle_ms','scene_budget_ms','reserved29','reserved30','reserved31')
def split_desktop(data,tag):
    if len(data)>WIRE_LIMIT:raise ValueError('desktop271 wire bound exceeded')
    boot=bytes.fromhex(tag)
    if len(boot)!=16:raise ValueError('desktop271 boot tag width differs')
    rest=bytearray();rows=[];partial=0;at=0
    while at<len(data):
        tail=data[at:]
        if tail.startswith(UI_MAGIC):
            if len(tail)<160:partial=len(tail);break
            packet=tail[:160];crc,schema=struct.unpack_from('<2I',packet,152)
            if packet[8:24]!=boot or schema!=271 or zlib.crc32(packet[:152])!=crc:raise ValueError('desktop271 boot/schema/CRC differs')
            v=struct.unpack_from('<32I',packet,24);r=dict(zip(FIELDS,v))
            if v[0] not in (6,7) or v[2]&~1023 or v[3]>120 or v[4]>1 or v[5]>17 or v[6]>v[5] or v[15]>3 or v[16]>3 or v[17]>6 or v[18]>v[17] or v[20]>1 or any(v[29:]):raise ValueError('desktop271 source call/state bounds differ')
            if any(v[10:15]) and v[10:15]!=(16384,32112,8192,16,1):raise ValueError('desktop271 retained swipe plan differs')
            if any(v[23:29]) and v[23:29]!=(28330,3938,6,400,30000,70000):raise ValueError('desktop271 actual ROI-derived press plan differs')
            r['live_backboardd_GPU_surface_admission_observed']=bool(v[2]&512)
            r['all_bounded_swipe_press_and_lift_calls_returned_successfully']=bool(v[0]==6 and not v[1] and v[2]==1023 and 0<v[3]<=120 and v[4]==1 and v[5]==v[6]==17 and not v[7] and not v[8] and v[9]<=32000 and v[10:15]==(16384,32112,8192,16,1) and not v[15] and not v[16] and v[17]==v[18]==6 and not v[19] and v[20]==1 and not v[21] and 2400<=v[22]<=70000 and v[23:29]==(28330,3938,6,400,30000,70000))
            r['Settings_menu_or_UI_response_proven']=False;r['physical_FT3683_sample']=False
            rows.append(r)
            if len(rows)>1:raise ValueError('desktop271 repeated scene packet')
            at+=160;continue
        if UI_MAGIC.startswith(tail):partial=len(tail);break
        if tail.startswith(b'K80UI269'):raise ValueError('desktop271 received old probe-only scene schema')
        if tail.startswith(ROI_MAGIC):
            if len(tail)<68:rest.extend(tail);break
            n=struct.unpack_from('<I',tail,28)[0]
            if not 0<n<=3004:raise ValueError('desktop271 ROI payload bound differs')
            if len(tail)<68+n:rest.extend(tail);break
            rest.extend(tail[:68+n]);at+=68+n;continue
        if tail.startswith(MAGIC):rest.extend(tail);break
        end=data.find(b'\r\n',at)
        if end<0:rest.extend(tail);break
        rest.extend(data[at:end+2]);at=end+2
    return bytes(rest),rows,partial
def inspect_progress(data,tag,program_tag):
    rest,rows,partial=split_desktop(data,tag);r=previous(rest,tag,program_tag)
    total=r['wire_nonterminal_frames270']+len(rows)
    if total>38:raise ValueError('desktop271 original frame budget exceeded')
    if partial:r['transport_frames_valid']=False
    r['synthetic_desktop271']=rows[0] if rows else None;r['partial_ui_packet271']=partial
    r['synthetic_desktop_dispatch_returned271']=bool(rows and rows[0]['all_bounded_swipe_press_and_lift_calls_returned_successfully'])
    r['wire_nonterminal_frames271']=total;r['probe_exit_gate269_selected']=False
    r['Settings_long_press_functionally_qualified']=False;r['GPU_desktop_stability_qualified']=False;r['full_GPU_qualification']=False
    r['desktop271_scope']='Actual live-task/GPU-source-fence admission and returned bounded virtual HID calls;UI response still requires exact-build image/video evidence. No probe exit or physicalFT3683 inference.'
    return r
def save_shot271(data,tag,out):
    rest,_,_=split_desktop(data,tag);return save_shot(rest,tag,out)
def save_panic(data,tag,out):
    rest,_,_=split_desktop(data,tag);return previous_panic(rest,tag,out)

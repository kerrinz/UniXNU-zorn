"""Menu and outside-tap call results with three actual CPU snapshots;UI needs visuals."""
import struct,zlib
from inspect_ios26_ui_desktop271 import inspect_progress as previous,save_shot271,save_panic as previous_panic
from inspect_ios26_ui_roi270 import ROI_MAGIC
from inspect_ios26_gpu_progress236 import MAGIC,WIRE_LIMIT
UI_MAGIC=b'K80UI276'
FIELDS=('phase','thread_raw','flags','subscriber_polls','subscriber_at_return','swipe_attempts','swipe_returns','swipe_first_raw','swipe_lift_raw','swipe_elapsed_ms','swipe_x','swipe_start_y','swipe_end_y','swipe_steps','identity','swipe_outcome','press_outcome','press_attempts','press_returns','press_first_raw','press_lift_attempted','press_lift_raw','press_elapsed_ms','press_x','press_y','press_reports','press_interval_ms','settle_ms','scene_budget_ms','compact_observer_dropped','before_menu_uptime_ms','after_menu_uptime_ms')
PROGRESS_FIELDS=('available','present_frame','producer_fence','completed_fence','surface_access_fence','surface_id','CF_dropped','backend_sequence','backend_stage','backend_raw','native_client_low32','native_client_flags','compact_dropped','application_calls','application_unique_low32','application_pid')


def no_call_recorded(outcome, lift_raw, *fields):
    # Early termination leaves all words zero. A skipped ZornUiScene269::Result
    # retains NoClient and UINT32_MAX, the sentinel for an unattempted lift.
    return not any(fields) and (outcome, lift_raw) in ((0, 0), (1, 0xffffffff))


def split_menu(data,tag):
    if len(data)>WIRE_LIMIT:raise ValueError('menu276 wire bound exceeded')
    boot=bytes.fromhex(tag)
    if len(boot)!=16:raise ValueError('menu276 boot tag width differs')
    rest=bytearray();rows=[];partial=0;at=0
    while at<len(data):
        tail=data[at:]
        if tail.startswith(UI_MAGIC):
            if len(tail)<672:partial=len(tail);break
            p=tail[:672];crc,schema=struct.unpack_from('<2I',p,664)
            if p[8:24]!=boot or schema!=276 or zlib.crc32(p[:664])!=crc:raise ValueError('menu276 boot/schema/CRC differs')
            v=struct.unpack_from('<160I',p,24);r=dict(zip(FIELDS,v[:32]))
            if v[0] not in (6,7) or v[2]&~1023 or v[3]>120 or v[4]>1 or v[5]>17 or v[6]>v[5] or v[15]>3 or v[16]>3 or v[17]>4 or v[18]>v[17] or v[20]>1:raise ValueError('menu276 source call/state bounds differ')
            if any(v[10:15]) and v[10:15]!=(16384,32112,8192,16,1):raise ValueError('menu276 retained swipe differs')
            if any(v[23:29]) and v[23:29]!=(28330,3938,4,400,30000,70000):raise ValueError('menu276 prospective short-hold plan differs')
            snapshots=[]
            for offset in [32,48,80,112,144]:
                q=v[offset:offset+16]
                if q[0]&~7:raise ValueError('menu276 CPU progress availability differs')
                if not q[0]&1 and any(q[1:6]):raise ValueError('menu276 unavailable present has values')
                if not q[0]&2 and any(q[6:12]):raise ValueError('menu276 unavailable CF has values')
                if not q[0]&4 and any(q[12:]):raise ValueError('menu276 unavailable application has values')
                snapshots.append(dict(zip(PROGRESS_FIELDS,q)))
            first,middle,afterDismiss,afterApp,last=snapshots
            returned=bool(v[0] in (6,7) and not v[1] and v[2]==1023 and 0<v[3]<=120 and v[4]==1 and v[5]==v[6]==17 and not v[7] and not v[8] and v[9]<=32000 and v[10:15]==(16384,32112,8192,16,1) and not v[15] and not v[16] and v[17]==v[18]==4 and not v[19] and v[20]==1 and not v[21] and 1600<=v[22]<=70000 and v[23:29]==(28330,3938,4,400,30000,70000))
            d=v[64:80]
            if d[0]>3 or d[1]>1 or d[2]>d[1] or d[4]>1 or d[14]>1 or d[15]:raise ValueError('dismiss276 source call/state bounds differ')
            if any(d[7:12]) and d[7:12]!=(16384,24576,8000,100,10000):raise ValueError('dismiss276 prospective outside-tap plan differs')
            if not d[14] and not no_call_recorded(d[0], d[5], *d[1:5], d[6], *d[12:14]):raise ValueError('dismiss276 unselected tap has call results')
            if not d[14] and any(v[80:96]):raise ValueError('dismiss276 unselected tap has post-tap snapshot')
            dismissed=bool(d[14]==1 and d[0]==0 and d[1]==d[2]==1 and not d[3] and d[4]==1 and not d[5] and 100<=d[6]<=10000 and d[7:12]==(16384,24576,8000,100,10000))
            app=v[96:112];scroll=v[128:144]
            if app[0]>3 or app[1]>1 or app[2]>app[1] or app[4]>1 or app[14]>1 or app[15]:raise ValueError('settings276 app-tap call bounds differ')
            if any(app[7:12]) and app[7:12]!=(28330,3938,5000,100,7000):raise ValueError('settings276 app-tap plan differs')
            if not app[14] and (not no_call_recorded(app[0], app[5], *app[1:5], app[6], *app[12:14]) or any(v[112:128])):raise ValueError('settings276 unselected app tap has calls/snapshot')
            if app[14] and not (d[14] and d[0]==0):raise ValueError('settings276 app tap without completed dismiss')
            appReturned=bool(app[14] and app[0]==0 and app[1]==app[2]==1 and not app[3] and app[4]==1 and not app[5] and 100<=app[6]<=7000 and app[7:12]==(28330,3938,5000,100,7000))
            if scroll[0]>3 or scroll[1]>4 or scroll[2]>17 or scroll[3]>scroll[2] or scroll[5]>1 or scroll[11]>1:raise ValueError('settings276 list-scroll call bounds differ')
            if any(scroll[8:11]+scroll[12:14]) and (scroll[8:11]!=(16384,24576,12288) or scroll[12:14]!=(1000,3000)):raise ValueError('settings276 list-scroll plan differs')
            if not scroll[11] and (not no_call_recorded(scroll[0], scroll[6], *scroll[1:6], scroll[7], *scroll[14:16]) or any(v[144:])):raise ValueError('settings276 unselected scroll has calls/snapshot')
            if scroll[11] and not (app[14] and app[0]==0):raise ValueError('settings276 scroll without completed app tap')
            scrollReturned=bool(scroll[11] and scroll[0]==0 and 0<scroll[1]<=4 and scroll[2]==scroll[3]==17 and not scroll[4] and scroll[5]==1 and not scroll[6] and 1020<=scroll[7]<3000 and scroll[8:11]==(16384,24576,12288) and scroll[12:14]==(1000,3000))
            def advanced(a,b):return bool(a['available']&1 and b['available']&1 and b['present_frame']>a['present_frame'] and b['completed_fence']>a['completed_fence'])
            r.update(before_menu=first,after_menu=middle,after_dismiss=afterDismiss,after_app=afterApp,after_scroll=last,app_tap=dict(zip(('outcome','attempts','returns','first_raw','lift_attempted','lift_raw','elapsed_ms','x','y','gap_ms','hold_ms','budget_ms','before_uptime_ms','after_uptime_ms','selected','reserved'),app)),list_scroll=dict(zip(('outcome','polls','attempts','returns','first_raw','lift_attempted','lift_raw','elapsed_ms','x','start_y','end_y','selected','ready_ms','budget_ms','before_uptime_ms','after_uptime_ms'),scroll)),dismiss=dict(zip(('outcome','attempts','returns','first_raw','lift_attempted','lift_raw','elapsed_ms','x','y','gap_ms','hold_ms','budget_ms','before_uptime_ms','after_uptime_ms','selected','reserved'),d)),live_GPU_input_admission_observed=bool(v[2]&512),all_bounded_swipe_short_hold_and_lifts_returned=returned,all_bounded_outside_tap_and_lift_returned=dismissed,all_bounded_app_tap_and_lift_returned=appReturned,all_bounded_list_scroll_and_lift_returned=scrollReturned,all_bounded_menu_and_dismiss_calls_returned=bool(returned and dismissed),all_bounded_scene_calls_returned=bool(v[0]==6 and returned and dismissed and appReturned and scrollReturned),compact_loss_observed=bool(v[29] and v[29]!=0xffffffff),compact_loss_snapshot_busy=v[29]==0xffffffff,source_surface_fence_advanced=advanced(first,last),source_surface_fence_advanced_after_menu=advanced(first,middle),source_surface_fence_advanced_after_dismiss=advanced(middle,afterDismiss),source_surface_fence_advanced_after_app=advanced(afterDismiss,afterApp),source_surface_fence_advanced_after_scroll=advanced(afterApp,last),backend_failure_observed=bool(any(s['available']&2 and s['backend_sequence'] for s in snapshots)),CF_diagnostic_loss_observed=bool(any(s['available']&2 and s['CF_dropped'] for s in snapshots)),Liquid_Glass_menu_visual_response_proven=False,menu_dismissal_visual_response_proven=False,stalled_fence_is_not_automatically_GPU_failure=True,physical_FT3683_sample=False)
            rows.append(r)
            if len(rows)>1:raise ValueError('menu276 repeated terminal packet')
            at+=672;continue
        if UI_MAGIC.startswith(tail):partial=len(tail);break
        if tail.startswith((b'K80UI269',b'K80UI271',b'K80UI272',b'K80UI273',b'K80UI274',b'K80UI275')):raise ValueError('menu276 received old scene schema')
        if tail.startswith(ROI_MAGIC):
            if len(tail)<68:rest.extend(tail);break
            n=struct.unpack_from('<I',tail,28)[0]
            if not 0<n<=3004:raise ValueError('menu276 ROI payload bound differs')
            if len(tail)<68+n:rest.extend(tail);break
            rest.extend(tail[:68+n]);at+=68+n;continue
        if tail.startswith(MAGIC):rest.extend(tail);break
        end=data.find(b'\r\n',at)
        if end<0:rest.extend(tail);break
        rest.extend(data[at:end+2]);at=end+2
    return bytes(rest),rows,partial
def inspect_progress(data,tag,program_tag):
    rest,rows,partial=split_menu(data,tag);r=previous(rest,tag,program_tag);total=r['wire_nonterminal_frames271']+len(rows)
    if total>38:raise ValueError('menu276 original frame budget exceeded')
    if partial:r['transport_frames_valid']=False
    r.update(synthetic_menu276=rows[0] if rows else None,partial_ui_packet276=partial,synthetic_menu_dispatch_returned276=bool(rows and rows[0]['all_bounded_swipe_short_hold_and_lifts_returned']),synthetic_dismiss_dispatch_returned276=bool(rows and rows[0]['all_bounded_menu_and_dismiss_calls_returned']),synthetic_settings_dispatch_returned276=bool(rows and rows[0]['all_bounded_scene_calls_returned']),wire_nonterminal_frames276=total,ordinary_probe267_selected=False,Liquid_Glass_menu_functionally_qualified=False,GPU_desktop_stability_qualified=False,Settings_navigation_functionally_qualified=False,full_GPU_qualification=False)
    r['client_census268']['scope']='Actual registered native clients of selected live backboardd;no probe exit or four-query-client requirement.'
    r['menu276_scope']='Retained275 menu/dismiss plus prospective Settings100ms tap/12s settle/in-list transformed269 swipe and five actual CPU progress snapshots. Time and returned calls do not prove a context-menu recognizer threshold,Liquid Glass correctness,or hang causation.'
    return r
def save_shot276(data,tag,out):
    rest,_,_=split_menu(data,tag);return save_shot271(rest,tag,out)
def save_panic(data,tag,out):
    rest,_,_=split_menu(data,tag);return previous_panic(rest,tag,out)

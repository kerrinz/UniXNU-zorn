"""Bounded ordinary Metal probe evidence;retain legacy loss and physical limits."""
import base64,re
from inspect_ios26_gpu_kernel266 import inspect_progress as inspect_kernel,save_shot

def _rows(data,prefix,pattern,keys,bases):
    rows=[]
    for line in data.splitlines():
        if not line.startswith(prefix):continue
        m=re.fullmatch(pattern,line)
        if not m:raise ValueError('probe267 source report syntax/identity differs')
        values=[int(v,b) for v,b in zip(m.groups(),bases)]
        if any(v>0xffffffffffffffff or v<-(1<<63) for v in values):raise ValueError('probe267 report overflow')
        rows.append(dict(zip(keys,values)))
    return rows

def assess_probe(result,program_tag):
    if not re.fullmatch('[0-9a-f]{32}',program_tag):raise ValueError('probe267 program identity differs')
    journal=result['journal248'];data=base64.b64decode(journal['stderr_base64'],validate=True);tag=re.escape(program_tag.encode())
    shared=_rows(data,b'ZORN267SHARED ',rb'ZORN267SHARED run='+tag+rb' open0=([0-9a-f]+) open1=([0-9a-f]+) query0=([0-9a-f]+) query1=([0-9a-f]+) close0=([0-9a-f]+) close1=([0-9a-f]+) valid0=([01]) valid1=([01]) equal=([01]) identity=([01])',('open0','open1','query0','query1','close0','close1','valid0','valid1','equal','identity'),(16,)*6+(10,)*4)
    present=_rows(data,b'ZORN249PRESENT ',rb'ZORN249PRESENT run='+tag+rb' submitted=(\d+) completed=(\d+) first=(\d+) last=(\d+) sid=(\d+) close=([0-9a-f]+) ticks=(\d+) numer=(\d+) denom=(\d+)',('submitted','completed','first','last','sid','close','ticks','numer','denom'),(10,)*5+(16,)+(10,)*3)
    reports=[]
    for line in data.splitlines():
        if not line.startswith(b'ZORN193MTL run=') or b' error=' in line:continue
        reports+=_rows(line,b'ZORN193MTL ',rb'ZORN193MTL run='+tag+rb' phase=(\d+) flags=([0-9a-f]+) status=(-?\d+) code=(-?\d+) service=([0-9a-f]+) device=([0-9a-f]+) crc=([0-9a-f]{8}) bad=([0-9a-f]{8}) ticks=(\d+)',('phase','flags','status','code','service','device','crc','bad','ticks'),(10,16,10,10,16,16,16,16,10))
    if any(not 1<=r['phase']<=11 or r['flags']&~1023 for r in reports):raise ValueError('probe267 phase/flags differ')
    if any(b['phase']<a['phase'] or b['flags']&a['flags']!=a['flags'] for a,b in zip(reports,reports[1:])):raise ValueError('probe267 source stages regressed')
    app=result.get('last_application');identity=app.get('program_identity') if app else None;j=journal['last'];kp=result.get('last_known247');terminal=result.get('terminal236',{})
    bound=bool(identity and identity['unique'] and j and (identity['unique'],identity['pid'])==(j['unique'],j['pid']))
    clean_transport=bool(result.get('transport_frames_valid') and not result.get('partial_tail_bytes') and not terminal.get('reason') and not terminal.get('partial_bytes'))
    intact=bool(bound and j and not j['gaps'] and not j['pending'] and j['seen_bytes']==j['reserved']==j['published']==journal['received_bytes'] and not journal['pending_checksum_prefixes'])
    pixels=[r for r in reports if r['phase']==10 and r['flags']==511 and r['status']==4 and r['code']==0 and r['service'] and r['service']==r['device'] and r['crc']==0x718ed2ce and r['bad']==0xffffffff and r['ticks']]
    render=bool(clean_transport and intact and pixels and result.get('kernel_known_task_complete266'))
    query=bool(len(shared)==1 and all(shared[0][k]==0 for k in ('open0','open1','query0','query1','close0','close1')) and all(shared[0][k]==1 for k in ('valid0','valid1','equal','identity')))
    shown=False
    if len(present)==1 and kp:
        p=present[0]
        shown=bool(p['submitted']==p['completed']==120 and 0<p['first']<=p['last']<=0xffffffff and p['sid'] and not p['close'] and p['ticks'] and p['numer'] and p['denom'] and kp['frame']==p['last'] and kp['first_surface_id']==p['sid'] and kp['lease']==2 and kp['all_acquires_passed'] and kp['pixel_copy_returned'] and kp['completion_ledger_valid'] and kp['surface_gpu_access_fence'] and kp['matched_GPU_access_completed'])
    clients=[c for c in result.get('clients261',[]) if c.get('available') and identity and (c['unique'],c['pid'])==(identity['unique'],identity['pid'])]
    closed={c['id'] for c in clients if c['flags']&8 and not c['flags']&16 and c['close_stage']==16 and not c['close_raw'] and not c['failure']['sequence'] and not c['dropped'] and c['calls']}
    no_native_failure=all(not c['failure']['sequence'] and not c['close_raw'] and not c['dropped'] for c in clients)
    lifecycle=bool(render and query and shown and journal['complete'] and app['render_complete'] and app['native_teardown_complete'] and result.get('journal_terminal_report_matches') and app['session_rejected']==2 and not app['native']['copy_errors'] and not app['native']['dropped'] and not app.get('error') and len(closed)>=3 and no_native_failure and not result.get('client_diagnostic_loss261'))
    return dict(shared_queries=shared,present_reports=present,Metal_reports=reports,journal_task_bound=bound,journal_prefix_intact=intact,actual_Metal_device_pipeline_GPU_render_CPU_readback=render,actual_two_shared_member_queries_and_closes=query,known_Metal_surface_CPU_present_copy=shown,observed_closed_native_client_ids=sorted(closed),bounded_probe_and_required_lifecycle_complete=lifecycle,legacy_loss_and_session_rejection_preserved=True,scope='Exact ordinary same-task Metal probe and two additional logical Query/Close members;not cross-task isolation,ordinary desktop GPU correctness,physical scanout or FT3683 contacts',physical_known_image_proven=False,full_GPU_qualification=False)

def inspect_progress(data,tag,program_tag):
    result=inspect_kernel(data,tag,program_tag);result['Metal_probe267']=assess_probe(result,program_tag);result['full_GPU_qualification']=False
    return result

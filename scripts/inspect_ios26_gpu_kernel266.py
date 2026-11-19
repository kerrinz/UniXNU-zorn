"""Actual initial kernel task/readback metadata;never full Metal/scanout acceptance."""
import re
from inspect_ios26_gpu_pool264 import inspect_progress as inspect_normal
from inspect_ios26_gpu_shot265 import split_stream,save_shot
from inspect_ios26_gpu_progress236 import MAGIC,WIRE_LIMIT
INDICES=(0,1,2,3,4,5,6,7,8,9,10,11,12,15,16,17,18,19,20,21,22,23,24,31)
FIELDS=('raw','phase','flags','grant_raw','ring_read','ring_write','fence','completed_fence','native_outstanding','submit_outstanding','VM_poisoned','submit_poisoned','device_references','output_crc','first_bad','expected_bad_byte','actual_bad_byte','table_acquires','table_releases','ring_busy','ring_status','io_raw','task_OOB_flags','task_OOB_raw')

def assess(values,available,frame):
    r=dict(zip(FIELDS,values));r['available']=bool(available)
    if not available:
        if any(values):raise ValueError('kernel266 unavailable record contains state')
    if r['phase']>6 or r['flags']&~127:raise ValueError('kernel266 source phase/flags differ')
    for name in ('VM_poisoned','submit_poisoned'):
        if r[name]>1:raise ValueError('kernel266 source boolean differs')
    checks={
        'completed_worker':frame['state']==3 and frame['smr']==88,
        'actual_snapshot':bool(available),
        'original_task_completed':r['raw']==0 and r['phase']==6 and r['flags']&63==63,
        'grant_returned_success':r['grant_raw']==0,
        'ring_idle_record':r['ring_read']==r['ring_write'] and not(r['ring_status']&~1) and not(r['ring_busy']&(1<<23)),
        'real_fence_completed':r['fence']>0 and r['fence']==r['completed_fence'],
        'no_task_outstanding':r['native_outstanding']==r['submit_outstanding']==0,
        'not_poisoned':r['VM_poisoned']==r['submit_poisoned']==0,
        'unmapped_no_device_references':r['device_references']==0,
        'actual_RGBA_readback':r['output_crc']==0xe843b26a and r['first_bad']==0xffffffff and r['expected_bad_byte']==r['actual_bad_byte']==0,
        'table_lease_balance':r['table_acquires']==r['table_releases'],
        'native_IO_success':r['io_raw']==0,
        'actual_task_OOB_release':r['task_OOB_flags']==127 and r['task_OOB_raw']==0,
    }
    r['task_complete']=all(checks.values());r['checks']=checks
    r['scope']='Initial retained native kernel known-image task only;not a Metal frontend/ordinary surface/physical scanout or long-term stability oracle'
    return r

def inspect_progress(data,tag,program_tag):
    if len(data)>WIRE_LIMIT:raise ValueError('kernel266 wire bound exceeded')
    normal,payload,shot=split_stream(data,tag);at=normal.find(MAGIC);head,terminal=(normal,b'') if at<0 else (normal[:at],normal[at:]);lines=[];observations=[]
    for line in head.splitlines(keepends=True):
        if not line.endswith(b'\r\n'):lines.append(line);continue
        if len(line)>3072 or line.count(b',kt=')!=1:raise ValueError('kernel266 task envelope differs')
        prefix,_,tail=line.partition(b',kt=');raw,sep,rest=tail.partition(b',jl=')
        if not sep:raise ValueError('kernel266 journal separator missing')
        fields=raw.split(b'/')
        if len(fields)!=25 or fields[0] not in (b'0',b'1') or any(not re.fullmatch(rb'[0-9a-f]{8}',v) for v in fields[1:]):raise ValueError('kernel266 task syntax differs')
        observations.append((int(fields[0]),[int(v,16) for v in fields[1:]]));lines.append(prefix+b',jl='+rest)
    result=inspect_normal(b''.join(lines)+terminal,tag,program_tag)
    if len(observations)!=result['frame_count']:raise ValueError('kernel266 task/frame count differs')
    total=result['frame_count']+shot['packet_count']
    if total>38:raise ValueError('kernel266 original nonterminal frame budget exceeded')
    rows=[];frozen=None
    for (available,values),frame in zip(observations,result['frames']):
        if bool(available)!=(frame['state']==3):raise ValueError('kernel266 worker publication availability differs')
        if available:
            if frozen is not None and values!=frozen:raise ValueError('kernel266 single initial task observation changed')
            frozen=values
        rows.append(assess(values,available,frame))
    if shot['partial_packet_bytes']:result['transport_frames_valid']=False
    result['serial_shot265']=shot;result['wire_nonterminal_frames265']=total
    result['kernel_known_task266']=rows
    result['kernel_known_task_complete266']=any(r['task_complete'] for r in rows)
    result['last_kernel_known_task266']=rows[-1] if rows else None
    result['kernel_GPU_write_CPU_readback_proven266']=result['kernel_known_task_complete266']
    result['full_GPU_qualification']=False
    return result

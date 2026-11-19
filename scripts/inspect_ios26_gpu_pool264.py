"""Decode real131072span capacity and cumulative successful VM transaction totals."""
import re
from inspect_ios26_gpu_capacity262 import inspect_progress as inspect_previous
from inspect_ios26_gpu_progress236 import MAGIC,WIRE_LIMIT

def inspect_progress(data,tag,program_tag):
    if len(data)>WIRE_LIMIT:raise ValueError('pool264 wire budget exceeded')
    at=data.find(MAGIC);normal,terminal=(data,b'') if at<0 else (data[:at],data[at:]);lines=[];values=[];totals=[]
    for line in normal.splitlines(keepends=True):
        if not line.endswith(b'\r\n'):lines.append(line);continue
        if len(line)>3072 or line.count(b',rc=')!=1 or line.count(b',vm=')!=1:raise ValueError('pool264 capacity/counter envelope differs')
        head,_,tail=line.partition(b',rc=');raw,sep,tail=tail.partition(b',vm=');counts,sep2,rest=tail.partition(b',jl=')
        if not sep or not sep2 or not re.fullmatch(rb'[0-9a-f]{8}',raw):raise ValueError('pool264 capacity syntax differs')
        if not re.fullmatch(rb'[0-9a-f]{16}(?:/[0-9a-f]{16}){3}',counts):raise ValueError('pool264 VM totals syntax differs')
        value=int(raw,16)
        if value>262144:raise ValueError('pool264 backend capacity bound exceeded')
        count=[int(x,16) for x in counts.split(b'/')]
        if totals and any(a<b for a,b in zip(count,totals[-1])):raise ValueError('pool264 cumulative VM counter regression')
        values.append(value);totals.append(count);lines.append(head+b',jl='+rest)
    result=inspect_previous(b''.join(lines)+terminal,tag,program_tag)
    if len(values)!=result['frame_count']:raise ValueError('pool264 capacity/frame count differs')
    observed=False
    for frame,value in zip(result['frames'],values):
        complete=frame['state']==3 and frame['smr']==88
        if value!=(131072 if complete else 0):raise ValueError('pool264 actual completed runtime capacity differs')
        observed|=complete
    result['runtime_span_capacity264']=values
    result['completed_runtime_131072_observed264']=observed
    result['VM_successful_totals264']=[dict(zip(('map_calls','unmap_calls','mapped_bytes','unmapped_bytes'),v)) for v in totals]
    result['VM_totals264_scope']='Independent cumulative CPU counters of successful map/unmap transactions across native VMs;not one coherent live-range/PTE snapshot,not proof of leaks,quiescence,resource-release authority or physical GPU writes'
    result['full_GPU_qualification']=False
    return result

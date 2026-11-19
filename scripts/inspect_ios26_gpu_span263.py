"""Decode the actual completed Domain capacity observation;not hardware authority."""
import re
from inspect_ios26_gpu_capacity262 import inspect_progress as inspect_previous
from inspect_ios26_gpu_progress236 import MAGIC,WIRE_LIMIT

def inspect_progress(data,tag,program_tag):
    if len(data)>WIRE_LIMIT:raise ValueError('span263 wire budget exceeded')
    at=data.find(MAGIC);normal,terminal=(data,b'') if at<0 else (data[:at],data[at:]);lines=[];values=[]
    for line in normal.splitlines(keepends=True):
        if not line.endswith(b'\r\n'):lines.append(line);continue
        if line.count(b',rc=')!=1:raise ValueError('span263 capacity envelope differs')
        head,_,tail=line.partition(b',rc=');raw,sep,rest=tail.partition(b',jl=')
        if not sep or not re.fullmatch(rb'[0-9a-f]{8}',raw):raise ValueError('span263 capacity syntax differs')
        value=int(raw,16)
        if value>262144:raise ValueError('span263 backend capacity bound exceeded')
        values.append(value);lines.append(head+b',jl='+rest)
    result=inspect_previous(b''.join(lines)+terminal,tag,program_tag)
    if len(values)!=result['frame_count']:raise ValueError('span263 capacity/frame count differs')
    observed=False
    for frame,value in zip(result['frames'],values):
        complete=frame['state']==3 and frame['smr']==88
        if value!=(8192 if complete else 0):raise ValueError('span263 actual completed runtime capacity differs')
        observed|=complete
    result['runtime_span_capacity263']=values
    result['completed_runtime_8192_observed263']=observed
    result['capacity_record263_scope']='Actual Domain CPU observation after worker completion;not a GPU mapping/fence/physical display guarantee'
    result['full_GPU_qualification']=False
    return result

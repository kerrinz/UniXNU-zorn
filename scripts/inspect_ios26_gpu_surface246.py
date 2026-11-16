"""Correlate exact IOSurface backing completion;never infer GPU pixel writes."""
from inspect_ios26_gpu_present245 import decode_present, inspect_progress as inspect_previous
from inspect_ios26_gpu_progress236 import MAGIC, WIRE_LIMIT


def decode_surface(value):
    fields=value.split(b'/')
    if len(fields)!=17:raise ValueError('surface246 field count differs')
    if fields[0]==b'0':
        result=decode_present(value);result['surface_gpu_access_fence']=None;return result
    if fields[1]!=b'00000002':raise ValueError('surface246 schema differs')
    # Validate original fields with245 rules,including exactly eight hex digits
    # for the new fence;the original reserved word is cleared for that decoder.
    if len(fields[-1])!=8 or any(c not in b'0123456789abcdef' for c in fields[-1]):
        raise ValueError('surface246 fence syntax differs')
    fence=int(fields[-1],16);fields[1]=b'00000001';fields[-1]=b'00000000'
    result=decode_present(b'/'.join(fields))
    if fence and (not result['surfaces'] or result['lease']!=2 or fence>result['completed']):
        raise ValueError('surface246 completed backing fence differs')
    result.update(surface_gpu_access_fence=fence,matched_GPU_access_completed=bool(fence),
                  GPU_surface_write_proven=False,GPU_surface_proven=False,physical_scanout_proven=False)
    return result


def inspect_progress(data,tag,program_tag):
    if len(data)>WIRE_LIMIT:raise ValueError('surface246 wire budget exceeded')
    at=data.find(MAGIC);normal=data if at<0 else data[:at];terminal=b'' if at<0 else data[at:]
    output=[];records=[]
    for line in normal.splitlines(keepends=True):
        if not line.endswith(b'\r\n'):
            output.append(line);continue
        if line.count(b',dp=')!=1:raise ValueError('surface246 snapshot missing or duplicate')
        head,_,value=line[:-2].partition(b',dp=');record=decode_surface(value);records.append(record)
        fields=value.split(b'/')
        if fields[0]==b'1':fields[1]=b'00000001';fields[-1]=b'00000000'
        output.append(head+b',dp='+b'/'.join(fields)+b'\r\n')
    result=inspect_previous(b''.join(output)+terminal,tag,program_tag)
    if len(records)!=result['frame_count']:raise ValueError('surface246 frame count differs')
    result.pop('presentation245',None);result.pop('last_presentation245',None)
    result['surface246']=records
    result['last_surface246']=next((x for x in reversed(records) if x['available']),None)
    result['GPU_surface_write_proven']=False
    return result

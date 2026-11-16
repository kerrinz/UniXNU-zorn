"""Decode same-frame presenter scalars;never infer GPU surface provenance."""
import re
from inspect_ios26_gpu_progress236 import inspect_progress as inspect_previous, MAGIC, WIRE_LIMIT


def decode_present(value):
    parts=value.split(b'/')
    if len(parts)!=17 or parts[0] not in (b'0',b'1') or any(not re.fullmatch(rb'[0-9a-f]{8}',p) for p in parts[1:]):
        raise ValueError('presentation245 syntax differs')
    words=[int(x,16) for x in parts[1:]]
    if parts[0]==b'0':
        if any(words):raise ValueError('unavailable presentation has payload')
        return dict(available=False,GPU_surface_proven=False,physical_scanout_proven=False)
    schema,frame,producer,lease,tail,completed,count,sid,acquired,copied,ledger,before,after,width,height,reserved=words
    if schema!=1 or lease not in (1,2) or count>4 or acquired>1 or copied>1 or ledger>1 or reserved or not width or not height:
        raise ValueError('presentation245 fields differ')
    if (not count and sid) or (count and not sid) or (lease==1 and (acquired or ledger or tail or completed)):
        raise ValueError('presentation245 surface/lease differs')
    if ledger and (lease!=2 or not tail or completed!=tail or producer>tail):
        raise ValueError('presentation245 completion ledger differs')
    if ((after-before)&0xffffffff)!=(1 if copied else 0):
        raise ValueError('presentation245 real copy counter differs')
    return dict(available=True,frame=frame,producer_fence=producer,lease=lease,tail=tail,completed=completed,
                surfaces=count,first_surface_id=sid,all_acquires_passed=bool(acquired),pixel_copy_returned=bool(copied),
                completion_ledger_valid=bool(ledger),copy_counter_before=before,copy_counter_after=after,
                width=width,height=height,GPU_surface_proven=False,physical_scanout_proven=False)


def inspect_progress(data,tag,program_tag):
    if len(data)>WIRE_LIMIT:raise ValueError('presentation245 exceeds wire bound')
    at=data.find(MAGIC);normal=data if at<0 else data[:at];terminal=b'' if at<0 else data[at:]
    prefix=b'K80 GPU PROGRESS '+tag.encode()+b' ';stripped=[];records=[]
    for line in normal.splitlines(keepends=True):
        if not line.endswith(b'\r\n'):
            stripped.append(line);continue
        if not line.startswith(prefix) or len(line)>3072 or line.count(b',dp=')!=1:
            raise ValueError('presentation245 frame envelope differs')
        original,_,payload=line[:-2].partition(b',dp=')
        record=decode_present(payload);records.append(record);stripped.append(original+b'\r\n')
    result=inspect_previous(b''.join(stripped)+terminal,tag,program_tag)
    if len(records)!=result['frame_count']:raise ValueError('presentation245 record count differs')
    result['presentation245']=records
    result['last_presentation245']=next((x for x in reversed(records) if x['available']),None)
    result['GPU_surface_proven']=False
    result['physical_presentation_proven']=False
    return result

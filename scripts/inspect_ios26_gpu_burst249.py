"""Validate source-defined repeated known-surface reports;no scanout inference."""
import base64
import re
from inspect_ios26_gpu_journal248 import inspect_progress as inspect_previous


def inspect_progress(data, tag, program_tag):
    result=inspect_previous(data,tag,program_tag)
    raw=base64.b64decode(result['journal248']['stderr_base64'],validate=True)
    reports=[]
    prefix=b'ZORN249PRESENT run='+program_tag.encode()+b' '
    pattern=re.escape(prefix)+(rb'submitted=(\d+) completed=(\d+) first=(\d+) last=(\d+) '
                               rb'sid=(\d+) close=([0-9a-f]+) ticks=(\d+) numer=(\d+) denom=(\d+)')
    keys=('submitted','completed','first','last','sid','close','ticks','numer','denom')
    for line in raw.splitlines():
        if not line.startswith(b'ZORN249PRESENT '):
            continue
        m=re.fullmatch(pattern,line)
        if not m:
            raise ValueError('burst249 report syntax/program binding differs')
        r=dict(zip(keys,(int(v,b) for v,b in zip(m.groups(),(10,10,10,10,10,16,10,10,10)))))
        if (any(r[k]>0xffffffff for k in keys if k!='ticks') or r['ticks']>0xffffffffffffffff or
                not 0<=r['completed']<=r['submitted']<=120 or not r['sid'] or
                not r['numer'] or not r['denom'] or
                (r['submitted'] and (not r['first'] or r['last']<r['first'] or
                                     r['last']-r['first']<r['submitted']-1)) or
                (not r['submitted'] and (r['first'] or r['last']))):
            raise ValueError('burst249 report bounds differ')
        r['elapsed_nanoseconds_reported']=r['ticks']*r['numer']//r['denom']
        reports.append(r)
    if len(reports)>1:
        raise ValueError('burst249 duplicate terminal reports')
    r=reports[0] if reports else None
    known=result.get('last_known247')
    complete=bool(r and result['lossless_application_complete248'] and r['submitted']==120 and
                  r['completed']==120 and not r['close'] and r['ticks'] and known and
                  known['available'] and known['frame']==r['last'] and
                  known['first_surface_id']==r['sid'] and result['known_frame_copy_observed'])
    result['burst249']=r
    result['known_burst_complete249']=complete
    result['physical_presentation_proven']=False
    result['GPU_surface_write_proven']=False
    return result

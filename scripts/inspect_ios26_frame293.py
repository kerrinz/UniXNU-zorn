"""Fixed16-command public-Metal CPU-wall observations;never physicalFPS/GPU cycles."""
import re,statistics
from fractions import Fraction

PREFIX=b'ZORN293FRAME '
PATTERN=rb'ZORN293FRAME run=([0-9a-f]{32}) index=(\d+) begin=(\d+) encoded=(\d+) committed=(\d+) completed=(\d+) checked=(\d+) numer=(\d+) denom=(\d+) crc=([0-9a-f]{8}) status=(\d+)\n'
FIELDS=('index','begin','encoded','committed','completed','checked','numer','denom','crc','status')

def inspect_frames(data,program_tag):
    if not re.fullmatch('[0-9a-f]{32}',program_tag):raise ValueError('frame293 expected program tag differs')
    rows=[];timebase=None
    for line in data.splitlines(keepends=True):
        if not line.startswith(PREFIX):continue
        match=re.fullmatch(PATTERN,line)
        if not match or match[1].decode()!=program_tag:raise ValueError('frame293 report syntax/program differs')
        values=[int(v,16 if name=='crc' else 10) for name,v in zip(FIELDS,match.groups()[1:])];row=dict(zip(FIELDS,values))
        if any(v>0xffffffffffffffff for v in values):raise ValueError('frame293 overflow')
        if row['index']!=len(rows) or row['index']>=16:raise ValueError('frame293 missing/duplicate/out-of-range command')
        if not 0<row['numer']<=0xffffffff or not 0<row['denom']<=0xffffffff:raise ValueError('frame293 timebase bounds differ')
        clock=row['numer'],row['denom']
        if timebase and clock!=timebase:raise ValueError('frame293 timebase changed')
        timebase=clock
        times=[row[k] for k in ('begin','encoded','committed','completed','checked')]
        if not times[0] or times!=sorted(times) or (rows and times[0]<rows[-1]['checked']):raise ValueError('frame293 CPU clock order differs')
        if row['crc']!=0x718ed2ce or row['status']!=4:raise ValueError('frame293 readback/completion failed')
        rows.append(row)
    complete=len(rows)==16
    result=dict(complete=complete,frames=len(rows),rows=rows,program_tag=program_tag,
                fixed_work=dict(commands=16,width=32,height=32,shared_IOSurface_poisoned_before_each_command=True),
                scope='Sequential fixed public-Metal command CPU-wall latency;includes driver/scheduling/cache/CPU-readback work. No physicalFPS, GPU timestamp or pure GPU duration.',
                statistics_qualified=complete,hardware_qualified=False)
    if complete:
        numer,denom=timebase
        def us(ticks):return float(Fraction(ticks*numer,denom*1000))
        phases={'prepare_encode':('begin','encoded'),'commit_call':('encoded','committed'),
                'after_commit_wait':('committed','completed'),'CPU_readback_verify':('completed','checked'),
                'encode_through_completion':('encoded','completed'),'whole_command':('begin','checked')}
        values={k:[us(r[z]-r[a]) for r in rows] for k,(a,z) in phases.items()}
        result['CPU_wall_microseconds']={k:dict(min=min(v),median=statistics.median(v),mean=sum(v)/len(v),max=max(v),sum=sum(v)) for k,v in values.items()}
        result['total_CPU_span_us']=us(rows[-1]['checked']-rows[0]['begin'])
        result['between_command_gap_us']=sum(us(b['begin']-a['checked']) for a,b in zip(rows,rows[1:]))
    return result

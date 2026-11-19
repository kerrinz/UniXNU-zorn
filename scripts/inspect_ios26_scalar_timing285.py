"""Decode bounded upstream scalar tables; never decode code addresses or images."""
import re

HEADER=re.compile(rb'ZORN285COUNTERS run=([0-9a-f]{32}|unbound) sample=([01]) uptime_us=([0-9]+) bytes=([0-9]+)\n')
PREFIX=b'ZORN285COUNTERS '

def inspect(data,tag):
    if not re.fullmatch(r'[0-9a-f]{32}',tag):raise ValueError('285 boot tag width differs')
    if not isinstance(data,bytes) or len(data)>65536:raise ValueError('285 bounded journal differs')
    reports=[];at=0;partial=0
    while True:
        start=data.find(PREFIX,at)
        if start<0:break
        match=HEADER.match(data,start)
        if not match:
            if b'\n' not in data[start:]:partial=len(data)-start;break
            raise ValueError('285 scalar header malformed')
        boot,sample,uptime,size=match.groups();sample,uptime,size=map(int,(sample,uptime,size))
        if boot.decode()!=tag or sample!=len(reports) or not 0<uptime<1<<64 or not 0<size<6144:raise ValueError('285 scalar identity/order/bounds differs')
        if reports and uptime<=reports[-1]['uptime_us']:raise ValueError('285 scalar time regressed')
        end=match.end()+size
        if end>len(data):partial=len(data)-start;break
        body=data[match.end():end]
        if not body.endswith(b'\n') or b'\0' in body or any(len(row)>90 for row in body.splitlines()):raise ValueError('285 scalar row framing differs')
        lines=body.decode('utf-8',errors='replace').splitlines()
        if any(re.match(r'(PU[0-9]|MA[0-9]|WC[0-9]|TB )',line) for line in lines):raise ValueError('285 scalar-only reporter contract differs')
        values={};raw=[]
        patterns=[
            (r'T (pipeline|library|function) n=(\d+) total=(\d+)ms max=(\d+)ms',('count','total_ms','max_ms')),
            (r'T (compile) n=(\d+) total=(\d+)ms max=(\d+)ms cached=(\d+)',('count','total_ms','max_ms','cached')),
            (r'G (commit-to-complete) n=(\d+) total=(\d+)ms max=(\d+)ms mean=(\d+)us',('count','total_ms','max_ms','mean_us')),
            (r'J (scheduled wait|resource wait) n=(\d+) total=(\d+)ms max=(\d+)ms',('count','total_ms','max_ms')),
            (r'J (completed wait) n=(\d+) total=(\d+)ms max=(\d+)ms t=(\d+)',('count','total_ms','max_ms','timeouts')),
            (r'J (surface cache) n=(\d+) bytes=(\d+) dup=(\d+) us=(\d+) max=(\d+)',('count','bytes','duplicates','total_us','max_us')),
        ]
        for line in lines:
            found=False
            for pattern,names in patterns:
                m=re.fullmatch(pattern,line)
                if m:
                    name,*numbers=m.groups()
                    if name in values:raise ValueError('285 repeated scalar row')
                    values[name]=dict(zip(names,map(int,numbers)));found=True;break
            if not found:raw.append(line)
        reports.append(dict(sample=sample,uptime_us=uptime,bytes=size,values=values,other_rows=raw,raw_table=body.decode('utf-8',errors='replace')))
        if len(reports)>2:raise ValueError('285 report count exceeded')
        at=end
    required={'pipeline','library','compile','function','commit-to-complete','scheduled wait','completed wait','resource wait','surface cache'}
    complete=bool(len(reports)==2 and not partial and all(required<=set(r['values']) for r in reports))
    return dict(reports=reports,report_count=len(reports),partial_bytes=partial,complete=complete,source='Actual upstream process counters;two bounded reports,scalar rows only',scope='CPU-clock/aggregate upstream values;not GPU hardware timestamps or physicalFPS. Other rows remain uninterpreted,including possibly truncated histograms.',hardware_or_performance_qualified=False)

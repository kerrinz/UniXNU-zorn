"""Decode bounded upstream scalar tables; never decode code addresses or images."""
import re

HEADER=re.compile(rb'ZORN287COUNTERS run=([0-9a-f]{32}|unbound) sample=([01]) uptime_us=([0-9]+) bytes=([0-9]+)\n')
PREFIX=b'ZORN287COUNTERS '

def inspect_native_rows(lines):
    rows=[line for line in lines if line.startswith('NC ')]
    if not rows:return dict(available=False,complete=False,reason='No native RPC scalar rows')
    if rows==['NC unavailable 287']:return dict(available=False,complete=False,reason='Actual exporter absent or snapshot busy')
    meta=re.fullmatch(r'NC meta (\d+) (\d+) (\d+) (\d+) (\d+)',rows[0])
    if not meta:raise ValueError('287 native metadata malformed')
    schema,bins,flags,dropped,when=map(int,meta.groups())
    if schema!=287 or bins!=18 or flags&~15 or dropped>0xffffffff or not 0<when<1<<63:raise ValueError('287 native metadata bounds differ')
    values={}
    for line in rows[1:]:
        match=re.fullmatch(r'NC (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)',line)
        if not match:raise ValueError('287 native row malformed')
        method,count,total,maximum,errors,timeouts=map(int,match.groups())
        if method>=18 or method in values or max(count,errors,timeouts)>0xffffffff or max(total,maximum)>(2**64-1)//1000:raise ValueError('287 native row bounds/identity differ')
        if maximum>total or (not count and any([total,maximum,errors,timeouts])) or (not flags&2 and errors+timeouts>count):raise ValueError('287 native counts inconsistent')
        values[method]=dict(count=count,total_us=total,max_us=maximum,errors=errors,timeouts=timeouts)
    if set(values)!=set(range(18)):raise ValueError('287 native method coverage differs')
    if values[0]['count'] and not flags&8:raise ValueError('287 unknown method missing fault')
    return dict(available=True,complete=not flags and not dropped,schema=schema,bins=bins,flags=flags,dropped=dropped,snapshot_ns=when,methods={str(k):v for k,v in values.items()},scope='Actual IOKit structure RPC CPU wall time by ABI1 method;excludes service admission/probing and IOConnectMapMemory/UnmapMemory. Error counts exclude ordinary Timeout;original raw results remain in native diagnostics.')

def inspect(data,tag):
    if not re.fullmatch(r'[0-9a-f]{32}',tag):raise ValueError('287 boot tag width differs')
    if not isinstance(data,bytes) or len(data)>65536:raise ValueError('287 bounded journal differs')
    reports=[];at=0;partial=0
    while True:
        start=data.find(PREFIX,at)
        if start<0:break
        match=HEADER.match(data,start)
        if not match:
            if b'\n' not in data[start:]:partial=len(data)-start;break
            raise ValueError('287 scalar header malformed')
        boot,sample,uptime,size=match.groups();sample,uptime,size=map(int,(sample,uptime,size))
        if boot.decode()!=tag or sample!=len(reports) or not 0<uptime<1<<64 or not 0<size<6144:raise ValueError('287 scalar identity/order/bounds differs')
        if reports and uptime<=reports[-1]['uptime_us']:raise ValueError('287 scalar time regressed')
        end=match.end()+size
        if end>len(data):partial=len(data)-start;break
        body=data[match.end():end]
        if not body.endswith(b'\n') or b'\0' in body or any(len(row)>90 for row in body.splitlines()):raise ValueError('287 scalar row framing differs')
        lines=body.decode('utf-8',errors='replace').splitlines()
        if any(re.match(r'(PU[0-9]|MA[0-9]|WC[0-9]|TB )',line) for line in lines):raise ValueError('287 scalar-only reporter contract differs')
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
                    if name in values:raise ValueError('287 repeated scalar row')
                    values[name]=dict(zip(names,map(int,numbers)));found=True;break
            if not found:raw.append(line)
        reports.append(dict(native_RPC287=inspect_native_rows(lines),sample=sample,uptime_us=uptime,bytes=size,values=values,other_rows=raw,raw_table=body.decode('utf-8',errors='replace')))
        if len(reports)>2:raise ValueError('287 report count exceeded')
        at=end
    required={'pipeline','library','compile','function','commit-to-complete','scheduled wait','completed wait','resource wait','surface cache'}
    complete=bool(len(reports)==2 and not partial and all(required<=set(r['values']) for r in reports))
    native_complete=bool(complete and all(r['native_RPC287']['complete'] for r in reports))
    native_window=None
    if native_complete:
        first,last=[r['native_RPC287'] for r in reports]
        if last['snapshot_ns']<=first['snapshot_ns']:raise ValueError('287 native snapshot clock regressed')
        changes={}
        for method in range(18):
            before,after=first['methods'][str(method)],last['methods'][str(method)]
            if after['max_us']<before['max_us']:raise ValueError('287 native maximum regressed')
            delta={k:after[k]-before[k] for k in ['count','total_us','errors','timeouts']}
            if any(v<0 for v in delta.values()):raise ValueError('287 native cumulative value regressed')
            if delta['count']:delta['mean_us_per_new_call']=delta['total_us']/delta['count']
            changes[str(method)]=delta
        native_window=dict(elapsed_ns=last['snapshot_ns']-first['snapshot_ns'],methods=changes,scope='Per-method aggregate differences;CPU wall RPC duration. Maximum remains cumulative,not subtracted. Excludes mapping APIs and service admission;not pureGPU time orFPS.')
    return dict(native_RPC_complete=native_complete,native_RPC_window=native_window,reports=reports,report_count=len(reports),partial_bytes=partial,complete=complete,source='Actual upstream process counters;two bounded reports,scalar rows only',scope='CPU-clock/aggregate upstream values;not GPU hardware timestamps or physicalFPS. Other rows remain uninterpreted,including possibly truncated histograms.',hardware_or_performance_qualified=False)

#!/usr/bin/env python3
"""Exercise scalar/RPC integrity and deltas on explicitly synthetic reports."""
import argparse,copy,hashlib,json
from pathlib import Path
from inspect_ios26_scalar_timing287 import inspect,inspect_native_rows

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir();tag='a'*32
    base=(b'T pipeline n=3 total=12ms max=8ms\nT library n=1 total=2ms max=2ms\n'
          b'T function n=2 total=1ms max=1ms\nT compile n=2 total=7ms max=4ms cached=1\n'
          b'G commit-to-complete n=3 total=9ms max=5ms mean=3000us\n'
          b'J scheduled wait n=3 total=1ms max=1ms\nJ completed wait n=3 total=9ms max=5ms t=0\n'
          b'J resource wait n=1 total=0ms max=0ms\nJ surface cache n=3 bytes=128 dup=0 us=2 max=1\n')
    def rows(sample,flags=0,dropped=0):
        values={i:[0,0,0,0,0] for i in range(18)}
        values[5]=[3+2*sample,9000+6000*sample,4000,0,0]
        values[6]=[3+3*sample,10000+3000*sample,5000,0,1+sample]
        return ['NC meta 287 18 %d %d %d'%(flags,dropped,1000000000*(sample+1))]+[
            'NC %d %d %d %d %d %d'%(i,*values[i]) for i in range(18)]
    def report(sample,native):
        body=base+('\n'.join(native)+'\n').encode() if native else base
        return ('ZORN287COUNTERS run=%s sample=%d uptime_us=%d bytes=%d\n'%(tag,sample,(sample+1)*1000000,len(body))).encode()+body
    wire=report(0,rows(0))+report(1,rows(1));result=inspect(wire,tag)
    assert result==json.loads(json.dumps(result))
    assert result['complete'] and result['native_RPC_complete']
    window=result['native_RPC_window'];assert window['elapsed_ns']==1000000000
    assert window['methods']['5']==dict(count=2,total_us=6000,errors=0,timeouts=0,mean_us_per_new_call=3000)
    assert window['methods']['6']['timeouts']==1 and window['methods']['6']['mean_us_per_new_call']==1000
    checks=['Two complete actual-schema synthetic reports preserve counts/timeouts and compute CPU-wall RPC differences;JSON roundtrip exact']
    for name,native in [('absent',[]),('unavailable',['NC unavailable 287']),('loss',rows(1,4,1)),('clock fault',rows(1,1)),('saturation',rows(1,2))]:
        x=inspect(report(0,rows(0))+report(1,native),tag)
        assert x['complete'] and not x['native_RPC_complete'] and x['native_RPC_window'] is None
        checks.append(name+' does not qualify native RPC window')
    malformed=[]
    v=rows(1);v.pop();malformed.append(('missing method',v))
    v=rows(1);v[-1]=v[-2];malformed.append(('repeated method',v))
    v=rows(1);v[0]=v[0].replace('287 18','287 17');malformed.append(('wrong method coverage',v))
    v=rows(1);v[0]='NC meta 287 18 16 0 2000000000';malformed.append(('unknown flags',v))
    v=rows(1);v[1]='NC 0 1 0 0 0 0';malformed.append(('unknown method without fault',v))
    v=rows(1);v[2]='NC 1 0 10 10 0 0';malformed.append(('empty count with time',v))
    v=rows(1);v[2]='NC 1 1 10 20 0 0';malformed.append(('maximum exceeds total',v))
    v=rows(1);v[2]='NC 1 1 10 10 1 1';malformed.append(('error/timeout exceeds calls',v))
    v=rows(1);v[2]='NC 1 4294967296 10 10 0 0';malformed.append(('count overflow',v))
    v=rows(1);v[0]='NC meta 287 18 0 0 1';malformed.append(('snapshot clock regression',v))
    v=rows(1);v[6]='NC 5 1 100 100 0 0';malformed.append(('cumulative regression',v))
    for name,native in malformed:
        try:inspect(report(0,rows(0))+report(1,native),tag)
        except ValueError:checks.append(name+' refused')
        else:raise AssertionError(name)
    x=inspect(wire[:-10],tag);assert not x['complete'] and not x['native_RPC_complete']
    checks.append('Truncated second report preserves incomplete rather than fabricated counters')
    (a.out/'SYNTHETIC-two-reports.bin').write_bytes(wire)
    pin=lambda p:dict(path=str(Path(p).resolve()),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
    source=Path(__file__).with_name('inspect_ios26_scalar_timing287.py')
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,source=pin(source),test_tool=pin(__file__),checks=checks,fixtures_explicitly_synthetic=True,phone_access=False,performance_measured=False),indent=2)+'\n')
    print('PASS287 native scalar decoder integrity/deltas/partial/loss controls;host only')

if __name__=='__main__':main()

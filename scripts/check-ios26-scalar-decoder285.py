#!/usr/bin/env python3
"""Explicit synthetic scalar-only journal controls; no device evidence generated."""
import argparse,hashlib,json
from pathlib import Path
from inspect_ios26_scalar_timing285 import inspect

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir();tag='a'*32
    rows=['T pipeline n=2 total=30ms max=20ms','T library n=1 total=7ms max=7ms','T compile n=3 total=8ms max=4ms cached=9','T function n=8 total=6ms max=3ms','G commit-to-complete n=30 total=60ms max=7ms mean=2000us','J scheduled wait n=10 total=20ms max=4ms','J completed wait n=12 total=21ms max=6ms t=0','J resource wait n=7 total=10ms max=5ms','J surface cache n=5 bytes=40 dup=2 us=300 max=100','H frame-gpu truncated histogram remains raw']
    body=('\n'.join(rows)+'\n').encode()
    def packet(sample,uptime,content=body,boot=tag):return f'ZORN285COUNTERS run={boot} sample={sample} uptime_us={uptime} bytes={len(content)}\n'.encode()+content
    wire=b'unrelated stderr\n'+packet(0,20000000)+packet(1,120000000);x=inspect(wire,tag);assert x['complete'] and x['report_count']==2 and x['reports'][0]['values']['surface cache']['total_us']==300 and not x['hardware_or_performance_qualified'];checks=['complete two scalar tables with unrelated stderr and uninterpreted truncated histogram']
    bad=[('foreign boot',packet(0,20,boot='b'*32)),('unbound',packet(0,20,boot='unbound')),('starts second',packet(1,20)),('duplicate',packet(0,20)+packet(0,30)),('time regression',packet(0,20)+packet(1,19)),('address attribution',packet(0,20,body+b'WC0 lr=1234\n')),('NUL',packet(0,20,body+b'\0\n')),('missing row delimiter',packet(0,20,body[:-1])),('long row',packet(0,20,b'X'*91+b'\n')),('oversized table',packet(0,20,b'X'*6144)),('third report',wire+packet(1,130000000))]
    for name,data in bad:
        try:inspect(data,tag)
        except ValueError:checks.append(name+' refused')
        else:raise AssertionError(name)
    for data in [b'',packet(0,20),packet(0,20)[:-1],b'ZORN285COUNTERS run=']:
        assert not inspect(data,tag)['complete']
    checks.append('empty/single/partial header/partial table never complete')
    pin=lambda p:dict(path=str(Path(p).resolve()),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,checks=checks,decoder=pin(Path(__file__).with_name('inspect_ios26_scalar_timing285.py')),test_tool=pin(__file__),fixtures_explicit_synthetic=True,phone_access=False),indent=2)+'\n');print('PASS285 scalar decoder identity/order/bounds/partial/attribution controls')
if __name__=='__main__':main()

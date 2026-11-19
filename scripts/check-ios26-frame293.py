#!/usr/bin/env python3
"""Strict frame293 parser regression,using labelled synthetic CPU timestamps only."""
import argparse,copy,hashlib,json
from pathlib import Path
import inspect_ios26_frame293 as t

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir();tag='f'*32
 def line(i,**kw):
  fields=dict(index=i,begin=1000+i*100,encoded=1010+i*100,committed=1020+i*100,completed=1040+i*100,checked=1050+i*100,numer=125,denom=3,crc='718ed2ce',status=4);fields.update(kw)
  return ('ZORN293FRAME run='+tag+' '+' '.join(f'{k}={v}' for k,v in fields.items())+'\n').encode()
 rows=[line(i) for i in range(16)];wire=b'Unrelated actual-program prefix\n'+b''.join(rows);r=t.inspect_frames(wire,tag);assert r['complete'] and r['statistics_qualified'] and not r['hardware_qualified'];assert abs(r['CPU_wall_microseconds']['commit_call']['mean']-10*125/3000)<1e-9;checks=['16 labelled synthetic reports;exact timebase and CPU-wall phase conversion']
 for n in [0,1,15]:
  r=t.inspect_frames(b''.join(rows[:n]),tag);assert not r['complete'] and not r['statistics_qualified'] and 'CPU_wall_microseconds' not in r;checks.append(str(n)+' reports keep statistics unqualified')
 cases=[('foreign identity',wire.replace(tag.encode(),b'e'*32,1)),('duplicate',b''.join(rows[:2]+[rows[1]]+rows[2:])),('missing',b''.join(rows[:3]+rows[4:])),('extra',b''.join(rows+[line(16)])),('truncated',wire[:-1]),('clock backwards',b''.join([line(0,committed=1000)]+rows[1:])),('inter-command overlap',b''.join(rows[:1]+[line(1,begin=1049)]+rows[2:])),('timebase zero',b''.join([line(0,numer=0)]+rows[1:])),('timebase changed',b''.join(rows[:1]+[line(1,numer=126)]+rows[2:])),('overflow',b''.join([line(0,checked=1<<64)]+rows[1:])),('wrong CRC',b''.join([line(0,crc='00000000')]+rows[1:])),('not completed',b''.join([line(0,status=3)]+rows[1:]))]
 for name,data in cases:
  try:t.inspect_frames(data,tag)
  except ValueError:checks.append(name+' refused')
  else:raise AssertionError(name)
 fixture=a.out/'SYNTHETIC-frame293-stderr.bin';fixture.write_bytes(wire);pin=lambda p:dict(path=str(Path(p).resolve()),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest());result=dict(passed=True,checks=checks,source=pin(t.__file__),test_tool=pin(__file__),fixture=pin(fixture),all_positive_reports_synthetic=True,phone_access=False,hardware_qualified=False);(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS293 strict fixed-work frame reports:',len(checks),'CPU fixtures only')
if __name__=='__main__':main()

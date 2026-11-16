#!/usr/bin/env python3
"""Regression of exact261 CF wire decoding;synthetic fixtures never hardware evidence."""
from pathlib import Path
import argparse,hashlib,json,sys
from inspect_ios26_gpu_failure261 import decode_failure,inspect_progress

def main():
 a=argparse.ArgumentParser();a.add_argument('--build',required=True,type=Path);a.add_argument('--out',required=True,type=Path);o=a.parse_args();B=o.build.resolve();O=o.out.resolve();O.mkdir();C=json.loads((B/'candidate.json').read_text());P=Path(C['parent']);PC=json.loads((P/'candidate.json').read_text());pin=lambda p:dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
 def wire(values,available=1):return str(available).encode()+b'/'+b'/'.join(('%0*x'%(16 if i<2 else 8,x)).encode() for i,x in enumerate(values))
 values=[64,10,10,1,4,1,0,0]+[1,80,3,0xe00002c2,17,65,64]+[2,160,23,1,18,5,0]+[0,0]
 good=wire(values);r=decode_failure(good);assert r['failure']['method']==18 and r['failure']['stage']==160
 raw=(P/'early-parser-host/SYNTHETIC-v251-derived.raw').read_bytes().replace(PC['tag'].encode(),C['tag'].encode());data=raw.replace(b',jl=',b',cf='+good+b',jl=');(O/'SYNTHETIC-current261.raw').write_bytes(data);r=inspect_progress(data,C['tag'],C['program_tag']);assert r['source_reject_observed261'] and r['source_backend_error_observed261'] and not r['all_clients_observed261'] and not r['full_GPU_qualification'];assert r['clients261'][0]['failure']['raw_kind']=='ZornSmmuSparse4KStatus' and r['clients261'][0]['failure']['physical_owner_cleanup']
 actual=B/'progress-success-frame-host/zero-frame.bin';r=inspect_progress(actual.read_bytes(),C['tag'],C['program_tag']);assert not r['source_backend_error_observed261'] and not r['full_GPU_qualification']
 cases={'short':good[:-1],'extra':good+b'/00000000','unavailable-with-state':wire(values,0),'uppercase':good.replace(b'e00002c2',b'E00002C2')}
 for name,index,value in [('too-many-records',5,65),('unknown-flags',3,32),('short-id',0,63),('no-task',1,0),('no-pid',2,0),('no-registration',3,0),('bad-stage',16,159),('bad-reason',17,24),('bad-method',19,19),('no-raw',18,0),('orphan-close-failure',3,17),('empty-event-state',15,0)]:
  v=values.copy();v[index]=value;cases[name]=wire(v)
 passed=[]
 for name,broken in cases.items():
  try:decode_failure(broken)
  except ValueError:passed.append(name)
  else:raise AssertionError(name)
 v=values.copy();v[4]=3
 changed=values.copy();changed[13]=66
 for name,broken in [('calls-regression',wire(v).join(data.rsplit(good,1))),('first-event-mutated',data.replace(good,wire(changed),1)),('missing-cf',data.replace(b',cf='+good,b'',1)),('duplicate-cf',data.replace(b',cf='+good,b',cf='+good+b',cf='+good,1))]:
  try:inspect_progress(broken,C['tag'],C['program_tag'])
  except ValueError:passed.append(name)
  else:raise AssertionError(name)
 unavailable=inspect_progress(raw.replace(b',jl=',b',cf='+wire([0]*24,0)+b',jl='),C['tag'],C['program_tag']);assert unavailable['client_diagnostic_loss261'] and not unavailable['full_GPU_qualification']
 for n in [0,1]:assert decode_failure(wire([0]*24,n))['id']==0
 result=dict(passed=True,controls=passed,actual_producer_frame=pin(actual),synthetic_fixture=pin(O/'SYNTHETIC-current261.raw'),parser=pin(Path(__file__).with_name('inspect_ios26_gpu_failure261.py')),tool=pin(Path(__file__)),source_boundary_only=True,phone_access=False,hardware_qualified=False,full_GPU_qualification=False)
 (O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS261 parser actual producer and synthetic mutation controls',len(passed))
if __name__=='__main__':main()

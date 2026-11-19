#!/usr/bin/env python3
"""Run actual portable observer bodies and both frozen program-prefix bindings;no GPU."""
import argparse,hashlib,json,subprocess
from pathlib import Path

def pin(p):return dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
def main():
 p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sanitizer',choices=['address,undefined','thread'],default='address,undefined');a=p.parse_args();B=a.build.resolve();C=json.loads((B/'candidate.json').read_text());S=Path(C['source']);P=Path(json.loads((Path(C['parent'])/'candidate.json').read_text())['source']);O=a.out.resolve();O.mkdir();runs=[]
 for root,current in [(P,False),(S,True)]:
  source=root/'ZornApplicationObservation26.inc';name='current' if current else 'parent'
  cpp=r'''
#include <cassert>
#include <cstdio>
#include <cstring>
#include "ZornApplicationObservation26.h"
#include "OBSERVER"
static void commit(const char*text){assert(zorn26_application_stderr_reserve(10,10));zorn26_application_stderr_commit(10,text,(uint32_t)strlen(text),0);}
int main(){appObservationBind(64,10,10);ZornApplicationObservation26 value{};
 const char fresh[]="ZORN193MTL run=PROGRAM phase=11 flags=0 status=0 code=0 service=0 device=0 crc=00000000 bad=ffffffff ticks=1\n";
 const char old[]="ZORN193MTL run=ddb9c8640ab544cd85cae684e0fb8f66 phase=1 flags=0 status=0 code=0 service=0 device=0 crc=00000000 bad=ffffffff ticks=1\n";
 commit(fresh);assert(zorn26_application_snapshot(&value));assert(value.lines==(CURRENT?1u:0u));assert(value.reportTerminal==(CURRENT?1u:0u));
 commit(old);assert(zorn26_application_snapshot(&value));assert(value.lines==1);assert(value.reportTerminal==(CURRENT?1u:0u));assert(value.rawBytes>0&&!value.copyErrors&&!value.dropped);
 assert(!zorn26_application_stderr_reserve(11,11));assert(zorn26_application_snapshot(&value)&&value.dropped==1&&value.reportUnique==10&&value.reportPid==10);
 puts(CURRENT?"actual293 observer binds new program,refuses old report/foreign task":"actual292 observer binds retained267 program,new293 report is raw context only");return 0;
}
'''.replace('OBSERVER',str(source)).replace('PROGRAM',C['program_tag']).replace('CURRENT','true' if current else 'false');f=O/(name+'.cpp');f.write_text(cpp);cmd=['xcrun','clang++','-std=c++17','-O1','-g','-pthread','-fsanitize='+a.sanitizer,'-I'+str(root),str(f),'-o',str(O/name)];r=subprocess.run(cmd,capture_output=True,text=True);(O/(name+'.compile.stderr')).write_text(r.stderr);assert not r.returncode,r.stderr;r=subprocess.run([str(O/name)],capture_output=True,text=True);(O/(name+'.run.stderr')).write_text(r.stderr);assert not r.returncode,r.stderr;runs.append(dict(source=pin(source),stdout=r.stdout))
 result=dict(passed=True,source=pin(S/'ZornApplicationObservation26.inc'),parent=pin(P/'ZornApplicationObservation26.inc'),test_tool=pin(__file__),sanitizer=a.sanitizer,program_tag=C['program_tag'],actual_portable_observer_bodies_executed=True,parent_and_current_prefixes_tested=True,all_reports_synthetic_CPU_fixtures=True,no_GPU_or_IOKit_boundary_executed=True,runs=runs,phone_access=False,hardware_qualified=False);(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS293 actual old/new program binding and foreign-task refusal;CPU fixtures only')
if __name__=='__main__':main()

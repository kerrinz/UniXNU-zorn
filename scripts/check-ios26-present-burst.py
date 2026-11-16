#!/usr/bin/env python3
"""Host fault controls for the actual bounded userland present/query function."""
from pathlib import Path
import argparse,json,subprocess,hashlib,os
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--source-root',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
p.add_argument('--deadline-seconds',type=int,choices=(8,20),default=8)
a=p.parse_args();S=a.source_root.resolve();O=a.out;O.mkdir()
t=(S/'userland/ZornMetalProbe193.mm').read_text();start=t.index('static bool presentKnown249(')
# Stop at this source function's own closing brace,independent of adjacent helpers.
end=t.index('{',start)+1;depth=1
while depth:
    if t[end]=='{':depth+=1
    elif t[end]=='}':depth-=1
    end+=1
body=t[start:end]
assert t.count('UINT64_C('+str(a.deadline_seconds*1000000000)+')')==2
src=r'''
#include <stdint.h>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <string>
#include "ZornKnownPresent247.h"
using IOSurfaceRef=void*;using io_service_t=unsigned;using io_connect_t=unsigned;using kern_return_t=int;
struct mach_timebase_info_data_t {uint32_t numer,denom;};
constexpr unsigned IO_OBJECT_NULL=0,kIOMainPortDefault=0;constexpr int KERN_SUCCESS=0,kIOReturnNotReady=17;
static constexpr char tag[]="SYNTHETIC";
static constexpr uint64_t test_budget_ns=TEST_BUDGET_NS;
static unsigned mode,opens,releases,closes,submits,queries,sleeps,queryForFrame,phase;
static uint64_t now,frame;static std::string report;
static int mach_timebase_info(mach_timebase_info_data_t *p){p->numer=mode==34?625:1;p->denom=mode==34?12:1;if(mode==27)p->numer=0;if(mode==28)p->denom=0;if(mode==29)p->denom=UINT32_MAX;return mode==26?1:0;}
static uint64_t mach_absolute_time(){return now;}
static uint32_t IOSurfaceGetID(void*){return mode==1?0:55;}
static const char *IOServiceMatching(const char*){return "IOMobileFramebuffer";}
static unsigned IOServiceGetMatchingService(unsigned,const char*){return mode==2?0:7;}
static unsigned mach_task_self(){return 1;}
static int IOServiceOpen(unsigned d,unsigned,unsigned,unsigned *c){assert(d==7);++opens;*c=9;if(mode==32)now+=test_budget_ns+100000000ULL;return mode==3?1:0;}
static int IOObjectRelease(unsigned d){assert(d==7);++releases;return 0;}
static int IOServiceClose(unsigned c){assert(c==9);++closes;return mode==4?1:0;}
static void usleep(unsigned us){assert(us==10000 || us==16667);++sleeps;now+=uint64_t(us)*1000*(mode==34?12:1)/(mode==34?625:1);}
static long write(int fd,const char *text,size_t n){assert(fd==2 && report.empty());report.assign(text,n);return long(n);}
static int IOConnectCallScalarMethod(unsigned c,unsigned sel,const uint64_t *in,unsigned n,uint64_t *out,unsigned *count){assert(c==9);
 if(sel==ZornKnownPresentSubmit247){++submits;queryForFrame=0;assert(n==1 && in[0]==55 && *count==1);frame=10+submits;out[0]=frame;
  if(mode==5)return 1;if(mode==6)out[0]=0;if(mode==7)*count=0;if(mode==8)out[0]=0x100000000ULL;
  if(mode==30 && submits==15)out[0]=frame-1;return 0;}
 assert(sel==ZornKnownPresentQuery247 && n==2 && in[0]==frame && in[1]==55 && *count==16);++queries;++queryForFrame;
 if(mode==9 || (mode==10 && queryForFrame<2) || (mode==33 && queryForFrame<200))return kIOReturnNotReady;
 if(mode==11 || (mode==35 && submits==15))return 2;
 const uint64_t record[16]={2,frame,4,2,4,4,1,55,1,1,1,10,11,1125,2436,4};for(unsigned i=0;i<16;++i)out[i]=record[i];
 if(mode>=12 && mode<=21){unsigned fields[]={0,1,7,3,6,8,9,10,12,15};out[fields[mode-12]]=0;}
 if(mode==22)out[15]=5;if(mode==23)out[2]=5;if(mode==24)out[4]=5;if(mode==25)*count=15;return 0;
}
'''+body+r'''
int main(){
 for(mode=0;mode<=35;++mode){opens=releases=closes=submits=queries=sleeps=queryForFrame=phase=0;now=mode==31?UINT64_MAX-1:100;frame=0;report.clear();
  bool ok=presentKnown249((void*)1);assert(ok==(mode==0 || mode==10 || mode==34));
  if(ok){assert(opens==1 && releases==1 && closes==1 && submits==120);assert(report.find("submitted=120 completed=120 first=11 last=130 sid=55 close=0")!=std::string::npos);assert(queries==(mode==10?240:120));}
  if(mode==1 || mode==26 || mode==27 || mode==28 || mode==29 || mode==31)assert(!opens && !submits && !closes);
  else if(mode==2)assert(!opens && !submits && !closes);
  else if(mode==3)assert(opens==1 && releases==1 && !submits && !closes);
  else assert(opens==1 && releases==1 && closes==1);
  if(mode==9)assert(submits==1 && queries==200 && sleeps==200);
  if(mode>=5 && mode<=8)assert(!queries && submits==1);
  if(mode==30)assert(submits==15 && queries==14);
  if(mode==32)assert(!submits && !queries);
  if(mode==33)assert(submits<120 && now<=test_budget_ns+100000000ULL);
  if(mode==35)assert(submits==15 && queries==15);
 }
 puts("PASS249 actual120-frame queue/query loop:36 controls,real IDs/records,failure stop,close,clock/timebase andconfigured deadline;ASan/UBSan");
}
''';f=O/'actual-burst.cpp';f.write_text(src.replace('TEST_BUDGET_NS',str(a.deadline_seconds*1000000000)+'ULL'));args=['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(S),str(f),'-o',str(O/'check')];p=subprocess.run(args,capture_output=True,text=True);(O/'compile.json').write_text(json.dumps(dict(arguments=args,exit=p.returncode,stderr=p.stderr),indent=2)+'\n');assert not p.returncode,p.stderr;p=subprocess.run([str(O/'check')],capture_output=True,text=True,env=os.environ|{'ASAN_OPTIONS':'symbolize=0','UBSAN_OPTIONS':'symbolize=0:print_stacktrace=0'});(O/'run.json').write_text(json.dumps(dict(exit=p.returncode,stdout=p.stdout,stderr=p.stderr),indent=2)+'\n');assert not p.returncode,p.stderr;(O/'result.json').write_text(json.dumps(dict(passed=True,actual_user_function_extracted=True,ASan_UBSan=True,cases=36,frames=120,maximum_application_seconds_between_calls=a.deadline_seconds,global_hardware_watchdog_still_required=True,source_sha256=hashlib.sha256(t.encode()).hexdigest(),all_hardware_boundaries_stubbed=True,phone_access=False,scope='Actual extracted helper and hardware boundary stubs only;not root or hardware qualification'),indent=2)+'\n');print(p.stdout.strip())

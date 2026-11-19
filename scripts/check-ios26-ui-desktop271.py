#!/usr/bin/env python3
"""Exercise prospective desktop input gate and plan against actual CPU stores."""
import argparse,hashlib,importlib.util,json,os,subprocess
from pathlib import Path
GATE=r'''
#include "ZornClientFailureStore261.h"
#include "ZornDesktopIdentity271.h"
#include "ZornPresentTrace245.h"
#include "ZornApplicationObservation26.h"
#include <cassert>
#include <cstring>
#include <cstdio>
#include <thread>
#include <vector>
#include <atomic>
struct Gate{unsigned failed=0;};
static struct {unsigned state=3,result=88;Gate gate;} zornProgress201;
static Gate zornCallbackGate222;static unsigned known[32],fault;
static ZornClientFailureStore261 clients;static ZornDesktopIdentity271 identity;
static ZornPresentTrace245 present;static ZornApplicationObservation26 app;
extern "C" void zorn26_native_known_image_observation(unsigned (&out)[32]){memcpy(out,known,sizeof(known));}
extern "C" int zorn26_desktop_identity271(uint64_t *u,uint32_t *p){return u&&p&&identity.snapshot(*u,*p);}
extern "C" int zorn26_application_snapshot(ZornApplicationObservation26 *p){*p=app;return fault!=1;}
extern "C" int zorn26_present_snapshot245(uint32_t (&p)[16]){return fault!=2&&present.snapshot(p);}
extern "C" int zorn_failure_snapshot261(uint32_t seq,ZornClientFailure261 *out){assert(seq%3==2);return fault!=3&&clients.snapshot(fault==4?2:seq,*out);}
#include "ZornUiDesktopGate271.inc"
static uint64_t ids[64];
void setup(unsigned count=2,unsigned mode=0){
 fault=0;clients={};identity={};present={};app={};zornProgress201={3,88,{}};zornCallbackGate222={};memset(known,0,sizeof(known));
 known[1]=6;known[2]=63;known[4]=known[5]=101;known[6]=known[7]=2;known[15]=0xe843b26a;known[16]=UINT32_MAX;known[19]=known[20]=2;known[21]=0x71000000;known[22]=1;known[24]=127;
 identity.observe("backboardd",10,20);app.unique=10;app.pid=20;app.flags=15;app.calls=100;
 const uint32_t p[16]={2,64,4,2,4,4,1,4,1,1,1,63,64,1125,2436,4};present.publish(p);
 for(unsigned i=0;i<count;++i){ids[i]=clients.bind(100+i,mode==1&&i==0?11:10,20);assert(ids[i]);
  if(mode!=2){assert(clients.begin(100+i,ids[i],200+i,13,false));clients.end(ids[i],200+i);}
  if(mode==3 || i){assert(clients.begin(100+i,ids[i],200+i,0,true));clients.end(ids[i],200+i);clients.finish(ids[i],0);}
 }
}
int main(){unsigned refused=0;
 for(unsigned count:std::vector<unsigned>{1,2,3,4,32,64}){setup(count);assert(zorn26_ui_desktop_ready271());}
 for(unsigned mode:std::vector<unsigned>{1,2,3}){setup(2,mode);assert(!zorn26_ui_desktop_ready271());++refused;}
 for(unsigned f=1;f<=4;++f){setup();fault=f;assert(!zorn26_ui_desktop_ready271());++refused;}
 for(unsigned i:std::vector<unsigned>{0,1,2,3,4,5,6,7,8,9,10,12,13,14,15}){
  setup();uint32_t p[16];assert(present.snapshot(p));p[i]=0;present.publish(p);assert(!zorn26_ui_desktop_ready271());++refused;
 }
 setup();uint32_t p[16];assert(present.snapshot(p));p[15]=5;present.publish(p);assert(!zorn26_ui_desktop_ready271());++refused;
 setup();identity.observe("backboardd",11,21);assert(!zorn26_ui_desktop_ready271());++refused;
 setup();identity={};identity.observe("backboardd-extra",10,20);identity.observe(nullptr,10,20);identity.observe("backboardd",0,20);assert(!zorn26_ui_desktop_ready271());++refused;
 setup();app.unique=11;assert(!zorn26_ui_desktop_ready271());++refused;
 setup();app.pid=21;assert(!zorn26_ui_desktop_ready271());++refused;
 setup();app.prepareFailed=1;assert(!zorn26_ui_desktop_ready271());++refused;
 setup();app.closeReturned=1;assert(!zorn26_ui_desktop_ready271());++refused;
 setup();app.dropped=1;assert(!zorn26_ui_desktop_ready271());++refused;
 setup();clients.noteClient(100,ids[0],100,7,ZornFailureBackend261,0,0,0);assert(!zorn26_ui_desktop_ready271());++refused;
 setup();clients.noteClient(100,ids[0],10,0xe00002c7,ZornFailureReject261,0,0,0);assert(zorn26_ui_desktop_ready271());
 setup();assert(clients.begin(100,ids[0],200,13,false));assert(zorn26_ui_desktop_ready271());clients.end(ids[0],200);
 setup();assert(!clients.begin(0,ids[0],200,13,false));assert(!zorn26_ui_desktop_ready271());++refused;
 for(unsigned i:std::vector<unsigned>{0,1,2,3,4,6,8,9,10,11,12,15,16,17,18,19,21,22,23,24,31}){
  setup();known[i]^=i==21?(1u<<23):i==22?2u:1u;assert(!zorn26_ui_desktop_ready271());++refused;
 }
 setup();zornProgress201.state=2;assert(!zorn26_ui_desktop_ready271());++refused;
 setup();zornProgress201.result=87;assert(!zorn26_ui_desktop_ready271());++refused;
 setup();zornProgress201.gate.failed=1;assert(!zorn26_ui_desktop_ready271());++refused;
 setup();zornCallbackGate222.failed=1;assert(!zorn26_ui_desktop_ready271());++refused;
 setup();std::atomic<unsigned> success{0};std::vector<std::thread> threads;
 for(unsigned i=0;i<8;++i)threads.emplace_back([&]{for(unsigned j=0;j<200;++j){identity.observe("backboardd",10,20);if(zorn26_ui_desktop_ready271())++success;}});
 for(auto &t:threads)t.join();assert(success>0);assert(zorn26_ui_desktop_ready271());
 printf("PASS271 actual live GPU gate,real identity/Store261/Trace245:refused=%u,CPU SID1/fence0 rejected,1..64clients,closed-only/mismatch/backend/loss/duplicate refused;active Scope and capability reject allowed;concurrent=%u\n",refused,success.load());
}
'''
PLAN=r'''
#include "ZornUiDesktopPlan271.h"
#include "ZornUiDesktopWire271.h"
#include <cassert>
#include <cstdio>
#include <vector>
struct Backend {
 uint64_t now=0;unsigned calls=0,fail=0,loseAfter=0,delayAfter=0;std::vector<ZornContacts::Frame> frames;
 uint64_t nowMs(){return now;}void sleepMs(unsigned ms){assert(ms<=400);now+=ms;}
 bool ready(){return !loseAfter||calls<loseAfter;}
 unsigned send(const ZornContacts::Frame &f){++calls;frames.push_back(f);if(calls==delayAfter)now+=70000;return calls==fail?7:0;}
};
int main(){Backend io;auto s=ZornUiDesktop271::run(io);assert(s.swipe.outcome==ZornUiScene269::Outcome::Complete&&s.press.outcome==ZornUiScene269::Outcome::Complete);
 assert(s.swipe.attempted==17&&s.swipe.liftAttempted&&s.press.attempted==6&&s.press.returned==6&&s.press.liftAttempted&&!s.press.liftRaw);
 assert(io.calls==25&&io.now==33420&&s.press.elapsedMs==2400&&io.frames[17].count==0&&io.frames[24].count==0);
 for(unsigned i=18;i<24;++i){const auto &f=io.frames[i];assert(f.count==1&&f.points[0].x==28330&&f.points[0].y==3938&&f.points[0].id==1);}
 for(unsigned i=1;i<=25;++i){Backend b;b.fail=i;auto r=ZornUiDesktop271::run(b);assert(r.swipe.outcome!=ZornUiScene269::Outcome::Complete||r.press.outcome!=ZornUiScene269::Outcome::Complete);assert(b.frames.back().count==0);assert(b.calls<=(i==18||i==25?i:i+1));}
 for(unsigned i=1;i<=24;++i){Backend b;b.delayAfter=i;auto r=ZornUiDesktop271::run(b);assert(r.swipe.outcome!=ZornUiScene269::Outcome::Complete||r.press.outcome!=ZornUiScene269::Outcome::Complete);assert(b.frames.back().count==0);}
 for(unsigned i=1;i<=23;++i){Backend b;b.loseAfter=i;auto r=ZornUiDesktop271::run(b);assert(b.frames.back().count==0);assert(r.swipe.outcome!=ZornUiScene269::Outcome::Complete||r.press.outcome!=ZornUiScene269::Outcome::Complete);}
 uint8_t tag[16]{};uint32_t words[32]{};char buf[160];assert(!ZornUiDesktopWire271::packet(buf,159,words,tag));assert(ZornUiDesktopWire271::packet(buf,160,words,tag)==160);assert(!memcmp(buf,"K80UI271",8));
 puts("PASS271 actual269swipe reused,actual270ROI Settings coordinates,30s readiness-controlled gap,6held reports/2400ms,two final lifts;every dispatch failure,slow callback or readiness loss stops later contacts;new160byte schema bound");}
'''
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--touch-common',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sanitizer',choices=['address-undefined','thread'],required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    env=os.environ|dict(ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0',TSAN_OPTIONS='symbolize=0:halt_on_error=1');san='address,undefined' if a.sanitizer=='address-undefined' else 'thread';tests=[]
    basefile=Path(__file__).with_name('check-ios26-ui-service269.py');spec=importlib.util.spec_from_file_location('actual_service269_boundaries',basefile);base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
    prefix=base.PREFIX.replace('zorn26_ui_scene_gpu_ready269','zorn26_ui_desktop_ready271')+'\n#include "ZornUiDesktopPlan271.h"\n#define NSEC_PER_SEC 1000000000ULL\nvoid clock_interval_to_deadline(unsigned n,uint64_t scale,uint64_t *out){assert(n==30&&scale==NSEC_PER_SEC);*out=mach_absolute_time()+uint64_t(n)*scale;}\n'
    source=a.source/'ZornUiSceneService269.cpp';body=source.read_text();body=body[body.index('class ZornUiSceneService269 final'):]
    main=base.MAIN.replace('uint32_t out[16]{}','uint32_t out[32]{}').replace('sends==18&&out[9]==1020','sends==25&&out[9]==1020').replace('scheduled269=done269=schedulingReturned269=0;','scheduled269=done269=schedulingReturned269=0;captureDeadline270=0;')
    for old,new in [('zorn26_ui_scene_snapshot269','zorn26_ui_desktop_snapshot271'),('zorn26_ui_scene_schedule269','zorn26_ui_desktop_schedule271'),('zorn26_ui_scene_done269','zorn26_ui_desktop_done271')]:main=main.replace(old,new)
    anchor='assert(zorn26_ui_desktop_done271()&&zorn26_ui_desktop_snapshot271(out));'
    assert main.count(anchor)==1;main=main.replace(anchor,anchor+'assert(!zorn26_ui_desktop_capture_ready271());nowTick+=29999;assert(!zorn26_ui_desktop_capture_ready271());++nowTick;assert(zorn26_ui_desktop_capture_ready271());if(m==0||m==10){assert(out[16]==0&&out[17]==6&&out[18]==6&&out[19]==0&&out[20]==1&&out[21]==0&&out[22]==2400&&out[23]==28330&&out[24]==3938);}if(m==8)assert(nowTick==180000);')
    for name,text in [('gate',GATE),('plan',PLAN),('service',prefix+body+main)]:
        f=a.out/(name+'.cpp');f.write_text(text);exe=a.out/name;args=['xcrun','clang++','-std=c++17','-O1','-g','-pthread','-fno-omit-frame-pointer','-fsanitize='+san,'-I'+str(a.source),'-I'+str(a.touch_common),str(f),'-o',str(exe)]
        r=subprocess.run(args,capture_output=True,env=env,timeout=120);(a.out/(name+'-compile.stderr')).write_bytes(r.stderr);assert not r.returncode,r.stderr.decode()
        r=subprocess.run([str(exe)],capture_output=True,env=env,timeout=120);(a.out/(name+'-run.stdout')).write_bytes(r.stdout);(a.out/(name+'-run.stderr')).write_bytes(r.stderr);assert not r.returncode,r.stderr.decode();print(r.stdout.decode().strip());tests.append(dict(test=name,arguments=args,stdout=r.stdout.decode()))
    pin=lambda p:dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest());result=dict(passed=True,sanitizer=a.sanitizer,sources=[pin(a.source/n) for n in ['ZornDesktopIdentity271.h','ZornUiDesktopGate271.inc','ZornUiDesktopPlan271.h','ZornUiDesktopWire271.h','ZornUiScenePlan269.h','ZornClientFailureStore261.h','ZornClientFailure261.h','ZornPresentTrace245.h','ZornApplicationObservation26.h','ZornUiSceneService269.cpp']],original_IOKit_test_boundaries=pin(basefile),tests=tests,host_CPU_snapshots_and_dispatch_boundaries=True,phone_access=False,hardware_or_Gesture_delivery_qualified=False);(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()

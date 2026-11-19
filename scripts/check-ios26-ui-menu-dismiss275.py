#!/usr/bin/env python3
"""Retained274 menu plan/collector and actual275 post-menu tap/service bodies."""
import argparse,hashlib,importlib.util,json,os,subprocess
from pathlib import Path
PLAN=r'''
#include "ZornUiMenuPlan274.h"
#include "ZornUiMenuWire274.h"
#include <cassert>
#include <cstdio>
#include <vector>
struct Backend{
 uint64_t now=0;unsigned calls=0,fail=0,loseAfter=0,slowSend=0,before=0,beforeCalls=0;bool slowBefore=false;std::vector<ZornContacts::Frame> frames;
 uint64_t nowMs(){return now;}void sleepMs(unsigned n){assert(n<=400);now+=n;}bool ready(){return !loseAfter||calls<loseAfter;}
 void beforeMenu(){++before;beforeCalls=calls;if(slowBefore)now+=70000;}
 unsigned send(const ZornContacts::Frame &f){++calls;frames.push_back(f);if(calls==slowSend)now+=70000;return calls==fail?7:0;}
};
static bool complete(const ZornUiMenu274::Scene &s){return s.swipe.outcome==ZornUiScene269::Outcome::Complete&&s.press.outcome==ZornUiScene269::Outcome::Complete;}
int main(){Backend b;auto s=ZornUiMenu274::run(b);assert(complete(s)&&b.calls==23&&b.now==32620&&b.before==1&&b.beforeCalls==18&&s.press.attempted==4&&s.press.returned==4&&s.press.elapsedMs==1600&&s.press.liftAttempted&&!s.press.liftRaw);
 assert(!b.frames[17].count&&!b.frames[22].count);for(unsigned i=18;i<22;++i)assert(b.frames[i].count==1&&b.frames[i].points[0].x==28330&&b.frames[i].points[0].y==3938);
 for(unsigned i=1;i<=23;++i){Backend x;x.fail=i;auto r=ZornUiMenu274::run(x);assert(!complete(r)&&!x.frames.back().count&&x.calls<=(i==18||i==23?i:i+1));}
 for(unsigned i=1;i<=22;++i){Backend x;x.slowSend=i;auto r=ZornUiMenu274::run(x);assert(!complete(r)&&!x.frames.back().count);}
 for(unsigned i=1;i<=21;++i){Backend x;x.loseAfter=i;auto r=ZornUiMenu274::run(x);assert(!complete(r)&&!x.frames.back().count);}
 Backend slow;slow.slowBefore=true;s=ZornUiMenu274::run(slow);assert(!complete(s)&&slow.calls==18&&s.press.outcome==ZornUiScene269::Outcome::Deadline);
 char wire[288];uint32_t words[64]{};uint8_t tag[16]{};assert(!ZornUiMenuWire274::packet(wire,287,words,tag));assert(ZornUiMenuWire274::packet(wire,288,words,tag)==288&&!memcmp(wire,"K80UI274",8));
 puts("PASS274 actual269swipe and adapted271short hold1600ms/four reports/release;before-menu hook after prior lift;dispatch/slow callback/readiness loss/slow hook refuse later contacts and retain final lift;288byte wire");}
'''
PROGRESS=r'''
#include "ZornClientFailureStore261.h"
#include "ZornPresentTrace245.h"
#include "ZornApplicationObservation26.h"
#include <cassert>
#include <cstring>
#include <cstdio>
static unsigned available=7;static ZornClientFailureStore261 clients;static ZornPresentTrace245 present;static ZornApplicationObservation26 app;
extern "C" int zorn26_present_snapshot245(uint32_t (&out)[16]){return (available&1)&&present.snapshot(out);}
extern "C" int zorn_failure_snapshot261(uint32_t seq,ZornClientFailure261 *out){assert(seq==0);return (available&2)&&clients.snapshot(seq,*out);}
extern "C" int zorn26_application_snapshot(ZornApplicationObservation26 *out){if(!(available&4))return 0;*out=app;return 1;}
#include "ZornUiMenuProgress274.inc"
int main(){const auto id=clients.bind(100,10,20);assert(id==64);assert(clients.begin(100,id,200,13,false));clients.end(id,200);const uint32_t p[16]={2,64,4,2,4,4,1,4,1,1,1,63,64,1125,2436,4};present.publish(p);app.unique=10;app.pid=20;app.calls=123;app.dropped=1;
 for(unsigned mask=0;mask<8;++mask){available=mask;struct {uint32_t before=0x12345678,words[16],after=0x87654321;} guard;memset(guard.words,0xaa,sizeof(guard.words));zorn26_ui_menu_progress274(guard.words);assert(guard.before==0x12345678&&guard.after==0x87654321&&guard.words[0]==mask);
  if(mask&1)assert(guard.words[1]==64&&guard.words[2]==4&&guard.words[3]==4&&guard.words[4]==4&&guard.words[5]==4);else for(unsigned i=1;i<=5;++i)assert(!guard.words[i]);
  if(mask&2)assert(guard.words[10]==64&&!guard.words[6]&&!guard.words[7]);else for(unsigned i=6;i<=11;++i)assert(!guard.words[i]);
  if(mask&4)assert(guard.words[12]==1&&guard.words[13]==123&&guard.words[14]==10&&guard.words[15]==20);else for(unsigned i=12;i<=15;++i)assert(!guard.words[i]);
 }
 available=7;clients.noteClient(100,id,170,0xe00002bd,ZornFailureBackend261,ZornFailureSpanCapacity262,10,20);clients.noteClient(100,id,10,0xe00002c7,ZornFailureReject261,0,0,0);uint32_t out[16];zorn26_ui_menu_progress274(out);assert(out[7]&&out[8]==170&&out[9]==0xe00002bd);assert(!clients.begin(0,id,200,0,false));zorn26_ui_menu_progress274(out);assert(out[6]);
 puts("PASS274 actual Trace245/Store261 collector:8availability masks clear missing values,no overrun,actual first backend failure prioritized over capability reject,CF loss and independent compact drop reported;no GPU operation");}
'''
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--touch-common',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sanitizer',choices=['address-undefined','thread'],required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    basefile=Path(__file__).with_name('check-ios26-ui-service269.py');base=module(basefile,'retained269_boundaries');prefix=base.PREFIX.replace('zorn26_ui_scene_gpu_ready269','zorn26_ui_desktop_ready272')+'\n#include "ZornUiTap275.h"\n'+'\n#include "ZornUiMenuPlan274.h"\nextern "C" uint32_t zorn26_ui_compact_loss272(){return 3;}\nextern "C" void zorn26_ui_menu_progress274(uint32_t (&out)[16]){for(auto &v:out)v=0;out[0]=7;out[1]=uint32_t(nowTick);}\n#define NSEC_PER_SEC 1000000000ULL\nvoid clock_interval_to_deadline(unsigned n,uint64_t unit,uint64_t *out){assert(n==5&&unit==NSEC_PER_SEC);*out=mach_absolute_time()+uint64_t(n)*unit;}\n'
    source=a.source/'ZornUiSceneService269.cpp';body=source.read_text();body=body[body.index('class ZornUiSceneService269 final'):];test=base.MAIN.replace('uint32_t out[16]{}','uint32_t out[96]{}').replace('sends==18&&out[9]==1020','sends==25&&out[9]==1020').replace('scheduled269=done269=schedulingReturned269=0;','scheduled269=done269=schedulingReturned269=0;captureDeadline270=0;')
    for before,after in [('zorn26_ui_scene_snapshot269','zorn26_ui_menu_snapshot275'),('zorn26_ui_scene_schedule269','zorn26_ui_menu_schedule275'),('zorn26_ui_scene_done269','zorn26_ui_menu_done275')]:test=test.replace(before,after)
    anchor='assert(zorn26_ui_menu_done275()&&zorn26_ui_menu_snapshot275(out));';assert test.count(anchor)==1;test=test.replace(anchor,anchor+'assert(!zorn26_ui_menu_capture_ready275());nowTick+=4999;assert(!zorn26_ui_menu_capture_ready275());++nowTick;assert(zorn26_ui_menu_capture_ready275());if(m==0||m==10){assert(out[16]==0&&out[17]==4&&out[18]==4&&out[20]==1&&out[21]==0&&out[22]==1600&&out[25]==4&&out[29]==3&&out[30]==151020&&out[31]==154620&&out[32]==7&&out[33]==151020&&out[48]==7&&out[49]==154620&&out[64]==0&&out[65]==1&&out[66]==1&&out[68]==1&&out[69]==0&&out[70]==100&&out[71]==16384&&out[72]==24576&&out[73]==8000&&out[74]==100&&out[75]==10000&&out[76]==154620&&out[77]==164720&&out[78]==1&&out[79]==0&&out[80]==7&&out[81]==164720);}if(m==8)assert(nowTick==155000);')
    san='address,undefined' if a.sanitizer=='address-undefined' else 'thread';env=os.environ|dict(ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0',TSAN_OPTIONS='symbolize=0:halt_on_error=1');rows=[]
    for name,text in [('plan',PLAN),('progress',PROGRESS),('service',prefix+body+test)]:
        f=a.out/(name+'.cpp');f.write_text(text);exe=a.out/name;args=['xcrun','clang++','-std=c++17','-O1','-g','-pthread','-fno-omit-frame-pointer','-fsanitize='+san,'-I'+str(a.source),'-I'+str(a.touch_common),str(f),'-o',str(exe)];r=subprocess.run(args,capture_output=True,env=env,timeout=120);(a.out/(name+'-compile.stderr')).write_bytes(r.stderr);assert not r.returncode,r.stderr.decode();r=subprocess.run([str(exe)],capture_output=True,env=env,timeout=120);(a.out/(name+'-run.stdout')).write_bytes(r.stdout);(a.out/(name+'-run.stderr')).write_bytes(r.stderr);assert not r.returncode,r.stderr.decode();print(r.stdout.decode().strip());rows.append(dict(test=name,arguments=args,stdout=r.stdout.decode()))
    pin=lambda p:dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest());sources=['ZornUiMenuPlan274.h','ZornUiMenuWire274.h','ZornUiMenuProgress274.inc','ZornUiScenePlan269.h','ZornUiDesktopGate272.inc','ZornDesktopIdentity271.h','ZornClientFailureStore261.h','ZornClientFailure261.h','ZornPresentTrace245.h','ZornApplicationObservation26.h','ZornUiSceneService269.cpp','ZornUiTap275.h','ZornUiMenuWire275.h'];result=dict(passed=True,sanitizer=a.sanitizer,sources=[pin(a.source/n) for n in sources],retained_IOKit_test_base=pin(basefile),tests=rows,before_after_CPU_snapshot_and_time_bodies_executed=True,actual_post_menu_tap_and_after_snapshot_bodies_executed=True,capture_eligibility_boundary_ms=[0,4999,5000],host_boundaries='IOKit/process/time/dispatch explicit;actual plan/worker/collector and CPU stores,not a real context-menu threshold or Liquid Glass result',phone_access=False,hardware_qualified=False);(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()

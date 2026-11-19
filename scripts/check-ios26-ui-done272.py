#!/usr/bin/env python3
"""Actual272 gate/Done plan/worker tests;retain271 source and IOKit boundaries."""
import argparse,hashlib,importlib.util,json,os,subprocess
from pathlib import Path
DONE=r'''
#include "ZornUiDonePlan272.h"
#include "ZornUiDoneWire272.h"
#include <cassert>
#include <cstdio>
#include <vector>
struct Backend {
 uint64_t now=0;unsigned calls=0,readyCalls=0,readyAtDone=0,fail=0,loseAfter=0,delayAfter=0,slowReady=0;std::vector<ZornContacts::Frame> frames;
 uint64_t nowMs(){return now;}void sleepMs(unsigned n){assert(n<=400);now+=n;}
 bool ready(){++readyCalls;if(readyCalls==slowReady)now+=85000;return !loseAfter||calls<loseAfter;}
 unsigned send(const ZornContacts::Frame &f){++calls;frames.push_back(f);if(calls==26)readyAtDone=readyCalls;if(calls==delayAfter)now+=85000;return calls==fail?7:0;}
};
static bool complete(const ZornUiDone272::Scene &s){return s.initial.swipe.outcome==ZornUiScene269::Outcome::Complete&&s.initial.press.outcome==ZornUiScene269::Outcome::Complete&&s.done.outcome==ZornUiScene269::Outcome::Complete;}
int main(){Backend io;auto s=ZornUiDone272::run(io);assert(complete(s));assert(io.calls==27&&io.now==48520&&s.done.attempted==1&&s.done.returned==1&&s.done.liftAttempted==1&&!s.done.liftRaw&&s.done.elapsedMs==100);
 assert(io.frames[17].count==0&&io.frames[24].count==0&&io.frames[26].count==0);const auto &f=io.frames[25];assert(f.count==1&&f.points[0].x==28671&&f.points[0].y==1260&&f.points[0].id==1);
 for(unsigned n=1;n<=27;++n){Backend b;b.fail=n;auto r=ZornUiDone272::run(b);assert(!complete(r));assert(!b.frames.back().count);assert(b.calls<=(n==18||n==25||n==27?n:n+1));}
 for(unsigned n=1;n<=27;++n){Backend b;b.delayAfter=n;auto r=ZornUiDone272::run(b);assert(!complete(r));assert(!b.frames.back().count);}
 for(unsigned n=1;n<=25;++n){Backend b;b.loseAfter=n;auto r=ZornUiDone272::run(b);assert(!complete(r)&&!b.frames.back().count&&b.calls<=25);}
 Backend lostAfterContact;lostAfterContact.loseAfter=26;auto r=ZornUiDone272::run(lostAfterContact);assert(complete(r)&&lostAfterContact.calls==27&&!lostAfterContact.frames.back().count);
 Backend slow;slow.slowReady=io.readyAtDone;r=ZornUiDone272::run(slow);assert(!complete(r)&&slow.calls==25&&r.done.outcome==ZornUiScene269::Outcome::Deadline);
 char out[224];uint32_t words[48]{};uint8_t tag[16]{};assert(!ZornUiDoneWire272::packet(out,223,words,tag));assert(ZornUiDoneWire272::packet(out,224,words,tag)==224&&!memcmp(out,"K80UI272",8));
 puts("PASS272 actual reused271swipe/hold then15s gap/Done tap100ms/final lift;all27dispatch failures/27slow callbacks/25readiness losses stop later contacts;last-contact loss still lifts;slow readiness cannot start expired tap;224byte wire bound");}
'''
def load_module(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--touch-common',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sanitizer',choices=['address-undefined','thread'],required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);basefile=Path(__file__).with_name('check-ios26-ui-desktop271.py');base=load_module(basefile,'retained271_tests')
    gate=base.GATE.replace('ZornUiDesktopGate271.inc','ZornUiDesktopGate272.inc').replace('zorn26_ui_desktop_ready271','zorn26_ui_desktop_ready272')
    before='setup();app.dropped=1;assert(!zorn26_ui_desktop_ready272());++refused;';after='setup();app.dropped=1;assert(zorn26_ui_desktop_ready272()&&zorn26_ui_compact_loss272()==1);fault=1;assert(zorn26_ui_compact_loss272()==UINT32_MAX);fault=0;clients.noteClient(100,ids[0],100,7,ZornFailureBackend261,0,0,0);assert(!zorn26_ui_desktop_ready272());++refused;';assert gate.count(before)==1;gate=gate.replace(before,after)
    service_basefile=Path(__file__).with_name('check-ios26-ui-service269.py');old=load_module(service_basefile,'retained269_IOKit_boundaries');prefix=old.PREFIX.replace('zorn26_ui_scene_gpu_ready269','zorn26_ui_desktop_ready272')+'\n#include "ZornUiDonePlan272.h"\nextern "C" uint32_t zorn26_ui_compact_loss272(){return 3;}\n#define NSEC_PER_SEC 1000000000ULL\nvoid clock_interval_to_deadline(unsigned n,uint64_t unit,uint64_t *out){assert(n==30&&unit==NSEC_PER_SEC);*out=mach_absolute_time()+uint64_t(n)*unit;}\n'
    source=a.source/'ZornUiSceneService269.cpp';body=source.read_text();body=body[body.index('class ZornUiSceneService269 final'):];test=old.MAIN.replace('uint32_t out[16]{}','uint32_t out[48]{}').replace('sends==18&&out[9]==1020','sends==27&&out[9]==1020').replace('scheduled269=done269=schedulingReturned269=0;','scheduled269=done269=schedulingReturned269=0;captureDeadline270=0;')
    for before,after in [('zorn26_ui_scene_snapshot269','zorn26_ui_desktop_snapshot272'),('zorn26_ui_scene_schedule269','zorn26_ui_desktop_schedule272'),('zorn26_ui_scene_done269','zorn26_ui_desktop_done272')]:test=test.replace(before,after)
    anchor='assert(zorn26_ui_desktop_done272()&&zorn26_ui_desktop_snapshot272(out));';assert test.count(anchor)==1;test=test.replace(anchor,anchor+'assert(!zorn26_ui_desktop_capture_ready272());nowTick+=29999;assert(!zorn26_ui_desktop_capture_ready272());++nowTick;assert(zorn26_ui_desktop_capture_ready272());if(m==0||m==10){assert(out[16]==0&&out[17]==6&&out[21]==0&&out[29]==3&&out[32]==0&&out[33]==1&&out[34]==1&&out[35]==0&&out[36]==1&&out[37]==0&&out[38]==100&&out[39]==28671&&out[40]==1260);}if(m==8)assert(nowTick==180000);')
    env=os.environ|dict(ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0',TSAN_OPTIONS='symbolize=0:halt_on_error=1');san='address,undefined' if a.sanitizer=='address-undefined' else 'thread';rows=[]
    for name,text in [('gate',gate),('done',DONE),('service',prefix+body+test)]:
        f=a.out/(name+'.cpp');f.write_text(text);exe=a.out/name;args=['xcrun','clang++','-std=c++17','-O1','-g','-pthread','-fno-omit-frame-pointer','-fsanitize='+san,'-I'+str(a.source),'-I'+str(a.touch_common),str(f),'-o',str(exe)];r=subprocess.run(args,capture_output=True,env=env,timeout=120);(a.out/(name+'-compile.stderr')).write_bytes(r.stderr);assert not r.returncode,r.stderr.decode();r=subprocess.run([str(exe)],capture_output=True,env=env,timeout=120);(a.out/(name+'-run.stdout')).write_bytes(r.stdout);(a.out/(name+'-run.stderr')).write_bytes(r.stderr);assert not r.returncode,r.stderr.decode();print(r.stdout.decode().strip());rows.append(dict(test=name,arguments=args,stdout=r.stdout.decode()))
    pin=lambda p:dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest());sources=['ZornUiDonePlan272.h','ZornUiDoneWire272.h','ZornUiDesktopGate272.inc','ZornUiDesktopPlan271.h','ZornUiScenePlan269.h','ZornDesktopIdentity271.h','ZornClientFailureStore261.h','ZornClientFailure261.h','ZornPresentTrace245.h','ZornApplicationObservation26.h','ZornApplicationObservation26.inc','ZornUiSceneService269.cpp'];result=dict(passed=True,sanitizer=a.sanitizer,sources=[pin(a.source/n) for n in sources],retained_test_bases=[pin(basefile),pin(service_basefile)],tests=rows,compact_telemetry_loss_reported_not_silenced=True,CF_loss_and_backend_failure_still_refused=True,actual_method_bodies_and_CPU_stores=True,IOKit_clock_proc_and_dispatch_boundaries_stubbed=True,phone_access=False,hardware_or_Done_response_qualified=False);(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()

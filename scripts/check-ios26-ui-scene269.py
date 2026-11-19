#!/usr/bin/env python3
"""Exercise the actual bounded synthetic gesture plan and CDC mux;no device IO."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path

TEST=r'''
#include "ZornUiScenePlan269.h"
#include "ZornUiSceneWire269.h"
#include <assert.h>
#include <cstdio>
#include <vector>
#include <thread>
using namespace ZornUiScene269;
struct Backend {
 uint64_t now=0;unsigned readyCalls=0,loseAt=0,readyAfter=0,failAt=0,sends=0;
 uint32_t advanceOnSend=0;bool failLift=false,backwards=false;
 std::vector<ZornContacts::Frame> frames;
 uint64_t nowMs(){return backwards&&sends?0:now;}
 bool ready(){++readyCalls;return now>=readyAfter&&(!loseAt||readyCalls<loseAt);}
 void sleepMs(uint32_t ms){assert(ms<=250);now+=ms;}
 uint32_t send(const ZornContacts::Frame &f){frames.push_back(f);++sends;now+=advanceOnSend;return (failAt==sends||(!f.count&&failLift))?0xe00002c0u:0;}
};
static unsigned controls=0;
void planTests() {
 {Backend b;auto r=run(b);assert(r.outcome==Outcome::Complete&&r.attempted==17&&r.returned==17&&r.liftAttempted&&r.liftRaw==0);assert(b.frames.size()==18&&b.now==1020);for(unsigned i=0;i<=Steps;++i){const auto &f=b.frames[i];assert(f.count==1&&f.points[0].x==X&&f.points[0].id==Identity);assert(f.points[0].y==StartY-uint64_t(StartY-EndY)*i/Steps);if(i)assert(f.points[0].y<b.frames[i-1].points[0].y);}assert(!b.frames.back().count);++controls;}
 {Backend b;b.readyAfter=ReadyMs+1;auto r=run(b);assert(r.outcome==Outcome::NoClient&&b.now==ReadyMs&&r.polls==120&&b.frames.empty()&&!r.liftAttempted);++controls;}
 {Backend b;b.readyAfter=ReadyMs-250;auto r=run(b);assert(r.outcome==Outcome::Complete&&b.now<BudgetMs);++controls;}
 for(unsigned i=1;i<=17;++i){Backend b;b.failAt=i;auto r=run(b);assert(r.outcome==Outcome::Dispatch&&r.attempted==i&&r.returned==i&&r.firstRaw==0xe00002c0u&&r.liftAttempted&&r.liftRaw==0);assert(b.frames.size()==i+1&&!b.frames.back().count);++controls;}
 {Backend b;b.failLift=true;auto r=run(b);assert(r.outcome==Outcome::Dispatch&&r.firstRaw==0xe00002c0u&&r.liftRaw==r.firstRaw);++controls;}
 {Backend b;b.loseAt=5;auto r=run(b);assert(r.outcome==Outcome::NoClient&&r.attempted==3&&r.liftAttempted&&!b.frames.back().count);++controls;}
 {Backend b;b.advanceOnSend=BudgetMs;auto r=run(b);assert(r.outcome==Outcome::Deadline&&r.attempted==1&&r.liftAttempted&&b.frames.size()==2);++controls;}
 {Backend b;b.now=100;b.backwards=true;auto r=run(b);assert(r.outcome==Outcome::Deadline&&r.attempted==1&&r.liftAttempted&&r.elapsedMs==UINT32_MAX);++controls;}
}
struct Shot {enum {Bytes=20048,PacketHeader=48};bool available=true;bool ready()const{return available;}unsigned packet(char *out,unsigned cap,unsigned off,const uint8_t(&)[16])const{if(off>=Bytes||cap<=PacketHeader)return 0;const unsigned n=Bytes-off<cap-PacketHeader?Bytes-off:cap-PacketHeader;out[0]='S';return n+PacketHeader;}};
struct Ui {bool available=true;bool ready()const{return available;}unsigned packet(char *out,unsigned cap,const uint8_t(&tag)[16])const{uint32_t v[16]{};v[0]=6;return ZornUiSceneWire269::packet(out,cap,v,tag);}};
struct Normal {unsigned calls=0;std::vector<unsigned> seen;};
unsigned next(void *p,char *out,unsigned,unsigned completed){auto &n=*static_cast<Normal*>(p);n.seen.push_back(completed);++n.calls;out[0]='N';return 37;}
void muxTests() {
 uint8_t tag[16]{};char out[3072]{};uint32_t v[16]{};v[0]=7;v[7]=0xe00002c0u;
 assert(!ZornUiSceneWire269::packet(nullptr,sizeof(out),v,tag));assert(!ZornUiSceneWire269::packet(out,95,v,tag));
 assert(ZornUiSceneWire269::packet(out,sizeof(out),v,tag)==96);assert(!memcmp(out,"K80UI269",8));uint32_t got=0;memcpy(&got,out+88,4);assert(got==zorn_panic_crc236(reinterpret_cast<uint8_t*>(out),88));++controls;
 for(unsigned delayed:{0u,25u,30u}) {
   Normal n;Shot shot;Ui ui;ZornUiSceneMux269 m;unsigned images=0,uis=0;
   for(unsigned seq=0;seq<38;++seq){ui.available=shot.available=seq>=delayed;const auto size=m.next(&n,out,sizeof(out),seq,next,shot,ui,tag,true);assert(size);if(out[0]=='S')++images;else if(!memcmp(out,"K80UI269",8))++uis;}
   assert(m.wire==38&&m.normal==30&&n.calls==30&&images==7&&uis==1&&m.offset==Shot::Bytes);
   for(unsigned i=0;i<n.seen.size();++i)assert(n.seen[i]==i);
   assert(!m.next(&n,out,sizeof(out),38,next,shot,ui,tag,true));++controls;
 }
 {Normal n;Shot s;Ui u;ZornUiSceneMux269 m;assert(!m.next(&n,out,sizeof(out),1,next,s,u,tag,true)&&!n.calls);assert(m.next(&n,out,sizeof(out),0,next,s,u,tag,false)==37&&n.calls==1&&!m.sentUi&&!m.offset);++controls;}
}
int main(){planTests();muxTests();std::vector<std::thread> threads;for(unsigned i=0;i<8;++i)threads.emplace_back([]{for(unsigned j=0;j<200;++j){Backend b;auto r=run(b);assert(r.outcome==Outcome::Complete&&r.liftAttempted);}});for(auto &t:threads)t.join();printf("PASS %u controls and1600 independent scene executions\n",controls);}
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--touch-common',type=Path,required=True);p.add_argument('--sanitizer',choices=['address-undefined','thread'],required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    f=a.out/'scene-test.cpp';f.write_text(TEST);exe=a.out/'scene-test';san='address,undefined' if a.sanitizer=='address-undefined' else 'thread'
    args=['xcrun','clang++','-std=c++17','-O1','-g','-pthread','-fno-omit-frame-pointer','-fsanitize='+san,'-I'+str(a.source),'-I'+str(a.touch_common),str(f),'-o',str(exe)]
    env=dict(os.environ,ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0',TSAN_OPTIONS='symbolize=0:halt_on_error=1');r=subprocess.run(args,capture_output=True,env=env,timeout=120);(a.out/'compile.stderr').write_bytes(r.stderr);assert not r.returncode,r.stderr.decode(errors='replace')
    r=subprocess.run([str(exe)],capture_output=True,env=env,timeout=120);(a.out/'run.stdout').write_bytes(r.stdout);(a.out/'run.stderr').write_bytes(r.stderr);assert not r.returncode,r.stderr.decode(errors='replace');assert b'PASS ' in r.stdout
    pin=lambda f:dict(path=str(f.resolve()),sha256=hashlib.sha256(f.read_bytes()).hexdigest())
    result=dict(passed=True,sanitizer=a.sanitizer,source=[pin(a.source/n) for n in ['ZornUiScenePlan269.h','ZornUiSceneWire269.h','ZornPanicPacket236.h','ZornCdcStream201.h']],touch_common=pin(a.touch_common/'ZornTouchTypes.h'),arguments=args,test=pin(f),executable=pin(exe),stdout=r.stdout.decode(),sanitizer_environment={k:env[k] for k in ['ASAN_OPTIONS','UBSAN_OPTIONS','TSAN_OPTIONS']},phone_access=False,actual_HID_dispatch_or_delivery_qualified=False)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(r.stdout.decode().strip())
if __name__=='__main__':main()

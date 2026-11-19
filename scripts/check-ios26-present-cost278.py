#!/usr/bin/env python3
"""Execute actual278 presenter timing callsites with explicit GPU/time boundaries."""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
PREFIX=r'''
#define UNIXNU_IOS26 1
#define ZORN_IOS26 1
#include "ZornPresentCost278.h"
#include "ZornPresentTrace245.h"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <thread>
#include <atomic>
#include <climits>
static uint64_t tick=40,houji26Presents=0;static unsigned mode,attempts,held,drops,shows,paceCalls,destructs;
uint64_t mach_absolute_time(){return tick;}
void absolutetime_to_nanoseconds(uint64_t n,uint64_t*out){*out=n*1000;}
using IOLock=int;
#define THREAD_UNINT 0
void IOLockLock(IOLock*){}void IOLockUnlock(IOLock*){}void IOLockWakeup(IOLock*,void*,bool){}void IOLockSleep(IOLock*,void*,int){assert(false);}
void IOSleep(unsigned ms){assert(ms==1&&!held);tick+=1000*ms;}
struct Finished{};
struct MiniIOSurface{unsigned sid=7;};
void MiniIOSurfaceDrop(MiniIOSurface*){assert(!held);++drops;}
void MiniIOSurfaceClearKept(){assert(!held);throw Finished{};}
struct ZornGen7PresentLease26{
 bool ready_;
 explicit ZornGen7PresentLease26(uint32_t f){assert(f==9&&!held);held=1;++attempts;tick+=10;ready_=mode!=2&&(mode!=1||attempts>=3);}
 ~ZornGen7PresentLease26(){assert(held);held=0;++destructs;}
 bool ready(){return ready_;}bool gpu(){return true;}bool failed(){return mode==2;}
};
bool houji26AcquireSurface(MiniIOSurface*){assert(held);tick+=5;return mode!=4;}
extern "C" int zorn_gen7_present_ledger245(uint32_t *a,uint32_t*b){*a=*b=9;return 1;}
uint32_t zorn_surface_fence246(uint32_t){return 9;}
static ZornPresentTrace245 zornPresentTrace245,zornPresentCostTrace278;
struct Known{void complete(const uint32_t(&)[16]){}};static Known zornKnownPresent247;
struct Shot{bool pending(){return false;}template<class...T>void capture(T...){assert(false);}};static Shot zornSerialShot265;
extern "C" bool zorn26_ui_menu_capture_ready278(){return false;}
static unsigned swapWord(const uint8_t*p,unsigned off){unsigned n;memcpy(&n,p+off,4);return n;}
'''
CLASS=r'''
class IOMobileFramebuffer{
public:
 IOLock *fLock=nullptr,*fSwapLock=nullptr;uint8_t fSwap[SWAP_QUEUE][SWAP_SIZE]{};MiniIOSurface*fSwapSurfaces[SWAP_QUEUE][SWAP_LAYERS]{};unsigned fSwapFirst=0,fSwapsWaiting=1;uint32_t fHoujiFence[SWAP_QUEUE]{9};uint64_t fZornQueuedAt278[SWAP_QUEUE]{10};bool fZornPresenterStopped=false;uintptr_t fBase=0;unsigned fPanelWidth=1440,fPanelHeight=3200,fRowBytes=5760,fZornCheckedExtent265=18432000,fWidth=1125,fHeight=2436;
 void presenter();uint64_t paceSwap(uint64_t){assert(!held);++paceCalls;tick+=5;return tick;}
 void show(const uint8_t*,MiniIOSurface**){assert(held);++shows;tick+=20;if(mode!=3)++houji26Presents;fSwapsWaiting=0;}
};
'''
MAIN=r'''
int main(){for(unsigned m=0;m<5;++m){mode=m;tick=40;attempts=held=drops=shows=paceCalls=destructs=0;houji26Presents=0;zornPresentCostTrace278={};IOMobileFramebuffer fb;MiniIOSurface surface;fb.fSwapSurfaces[0][0]=&surface;unsigned id=17;memcpy(fb.fSwap[0]+SWAP_ID,&id,4);
 try{fb.presenter();}catch(Finished&){}uint32_t r[16];assert(zornPresentCostTrace278.snapshot(r));assert(r[0]==278&&r[3]==17&&r[15]==9&&r[5]==30&&r[6]==5&&!r[14]&&!held&&destructs==attempts&&paceCalls==1);
 if(m==1){assert(attempts==3&&r[7]==2030&&r[8]==30&&r[9]==5&&r[10]==20&&r[11]==3&&r[12]==2&&r[1]==1&&r[4]==2&&r[13]==0&&drops==1);}
 else if(m==2||m==4){assert(attempts==1&&r[7]==10&&r[8]==10&&!r[10]&&r[13]==1&&r[4]==3&&!r[1]&&!drops&&fb.fZornPresenterStopped);}
 else{assert(attempts==1&&r[7]==10&&r[8]==10&&r[9]==5&&r[10]==20&&r[11]==1&&!r[12]&&!r[13]&&drops==1&&r[1]==(m==3?0u:1u)&&r[4]==(m==3?4u:2u));}
 }
 ZornPresentClock278 clk;ZornPresentCost278 c;c.measure(ZornPresentCost278::Queue,9,8,clk);assert(c.faults==1&&!c.totals[0]);c.measure(ZornPresentCost278::Show,0,uint64_t(UINT32_MAX)+1,clk);assert(c.totals[5]==UINT32_MAX&&(c.faults&2));c.add(c.frames,UINT32_MAX);c.result(false,true,true);assert(c.frames==UINT32_MAX&&(c.faults&2));uint32_t out[16];c.pack(out,99,1);assert((out[14]&7)==7);
 ZornPresentTrace245 trace;std::atomic<bool>done{false};std::thread writer([&](){for(unsigned n=1;n<=10000;++n){uint32_t q[16];for(auto&v:q)v=n;trace.publish(q);}done.store(true);});unsigned reads=0;while(!done.load()){uint32_t q[16];if(trace.snapshot(q)){for(auto v:q)assert(v==q[0]);++reads;}}writer.join();assert(trace.snapshot(out)&&out[0]==10000);for(auto v:out)assert(v==10000);
 printf("PASS278 actual presenter:ready,2pending retries,terminal/cache refusal,zero-pixel return;queue/beat once,wall vs call wait distinct,lease destructor precedes publish/retirement;clock reversal/saturation faults;10000 atomic publications(%u snapshots);no GPU hardware\n",reads);
}
'''
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sanitizer',choices=['address-undefined','thread'],required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);source=a.source/'MiniIOMobileFramebuffer.cpp';text=source.read_text();start=text.index('void\nIOMobileFramebuffer::presenter(void)');end=text.index('/*\n * dada: the surface shown',start);body=text[start:end];cs=text.index('struct ZornPresentClock278 {');clock=text[cs:text.index('};',cs)+2];defines='\n'.join(l for l in text.splitlines() if l.startswith('#define SWAP_'));f=a.out/'actual-presenter278.cpp';f.write_text(PREFIX+defines+'\n'+clock+'\n'+CLASS+body+MAIN)
 # These checks bind clock publication to real queueing and CPU-copy completion,
 # whose device/allocator functions stay explicit host boundaries in this test.
 assert text.index('fZornQueuedAt278[slot]=mach_absolute_time();')<text.index('fSwapsWaiting++;',text.index('fZornQueuedAt278[slot]=mach_absolute_time();'))
 assert body.index('cost278.result(')>body.index('Drop the issuer gate before sleeping')
 exe=a.out/'actual-presenter278';san='address,undefined' if a.sanitizer=='address-undefined' else 'thread';args=['xcrun','clang++','-std=c++17','-O1','-g','-pthread','-fno-omit-frame-pointer','-fsanitize='+san,'-I'+str(a.source),str(f),'-o',str(exe)];env=os.environ|dict(ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0',TSAN_OPTIONS='symbolize=0:halt_on_error=1');r=subprocess.run(args,capture_output=True,env=env,timeout=120);(a.out/'compile.stderr').write_bytes(r.stderr);assert not r.returncode,r.stderr.decode();r=subprocess.run([str(exe)],capture_output=True,env=env,timeout=120);(a.out/'run.stderr').write_bytes(r.stderr);(a.out/'run.stdout').write_bytes(r.stdout);assert not r.returncode,r.stderr.decode();pin=lambda q:dict(path=str(q.resolve()),sha256=hashlib.sha256(q.read_bytes()).hexdigest());(a.out/'result.json').write_text(json.dumps(dict(passed=True,sources=[pin(source),pin(a.source/'ZornPresentCost278.h'),pin(a.source/'ZornPresentTrace245.h')],sanitizer=a.sanitizer,arguments=args,test_tool=pin(Path(__file__)),actual_presenter_and_clock_bodies_executed=True,clock_GPU_cache_queue_show_boundaries_stubbed=True,stdout=r.stdout.decode(),phone_access=False,performance_measured=False,hardware_qualified=False),indent=2)+'\n');print(r.stdout.decode().strip())
if __name__=='__main__':main()

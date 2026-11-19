#!/usr/bin/env python3
"""Run actual269 service/creator/worker bodies with explicit host IOKit boundaries."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
PREFIX=r'''
#include "ZornUiScenePlan269.h"
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>
#include <string>
#include <vector>
using wait_result_t=int;using thread_t=void*;
#define THREAD_NULL nullptr
#define KERN_SUCCESS 0
#define OSDeclareDefaultStructors(T) public: T()=default;
#define OSDefineMetaClassAndStructors(T,B)
#define OSDynamicCast(T,x) dynamic_cast<T*>(x)
#define OSSafeReleaseNULL(x) do{if(x){(x)->release();(x)=nullptr;}}while(0)
constexpr int kIOReturnNotReady=0xe00002d8,kIOReturnUnsupported=0xe00002c7;
using UInt32=unsigned;
static unsigned mode,starts,deallocs,serviceFrees,sends;static bool normalContext=true,boardValid=true;
extern "C" bool zorn26_ui_scene_gpu_ready269(){return mode!=8;}
static uint64_t nowTick;static void(*pending)(void*,int);static void *pendingContext;
struct Terminated{};
struct OSObject {unsigned refs=1;virtual ~OSObject()=default;void retain(){assert(refs);++refs;}void release(){assert(refs);if(!--refs)delete this;}};
struct OSData:OSObject {std::string bytes;explicit OSData(const char *p):bytes(p){bytes.push_back(0);}const void*getBytesNoCopy(){return bytes.data();}unsigned getLength(){return bytes.size();}};
struct OSString:OSObject {std::string bytes;explicit OSString(const char*p):bytes(p){}static OSString*withCString(const char*p){return new OSString(p);}};
static void *gIODTPlane=(void*)1;
struct IORegistryEntry:OSObject {static IORegistryEntry *fromPath(const char *p,void*){assert(!strcmp(p,"/"));return new IORegistryEntry;}OSObject*copyProperty(const char *p){assert(!strcmp(p,"compatible"));return new OSData(boardValid?"xiaomi,zorn":"foreign,device");}};
struct IOService;static IOService *attachedService;
struct IOService:IORegistryEntry {
 IOService *provider=nullptr;bool registered=false,isScene=false;
 virtual bool init(){isScene=true;return mode!=2;}
 virtual bool attach(IOService *p){assert(!provider);if(mode==3)return false;provider=p;p->retain();retain();attachedService=this;return true;}
 virtual void detach(IOService *p){assert(provider==p);provider=nullptr;p->release();attachedService=nullptr;release();}
 void registerService(){assert(provider);registered=true;}
 virtual bool start(IOService*){return mode!=4;}
 virtual OSString*getTransport(){return nullptr;}virtual OSString*getProduct(){return nullptr;}
 static void*operator new(size_t n)noexcept{return mode==1?nullptr:malloc(n);}static void operator delete(void*p){free(p);}
 ~IOService()override{assert(!provider);if(isScene)++serviceFrees;}
};
struct IODTPlatformExpert:IOService {};
static IODTPlatformExpert platform;
static unsigned lockDepth;
void IOLockLock(void*){assert(!lockDepth);++lockDepth;}void IOLockUnlock(void*){assert(lockDepth==1);--lockDepth;}
struct OSArray{};
struct ZornTouchEventService26:IOService {
 OSArray array;void *_clientLock=(void*)1;OSArray *_clients=&array;bool accepting=false;
 bool acceptingFrames()const{return accepting;}
 bool handleIsOpenLocked(const IOService*)const{assert(lockDepth==1);return mode!=7;}
 bool start(IOService *p)override{
   auto*t=getTransport();auto*n=getProduct();assert(t&&n&&t->bytes=="Virtual"&&n->bytes=="K80 GPU UI scene (synthetic)");t->release();n->release();
   accepting=IOService::start(p);return accepting;
 }
 unsigned submitFrame(const ZornContacts::Frame &f){assert(accepting&&provider&&registered);++sends;assert(f.count<=1);return (mode==5&&f.count)||(mode==6&&!f.count)?0xe00002c0u:0;}
};
bool preemption_enabled(){return normalContext;}bool ml_at_interrupt_context(){return false;}bool ml_get_interrupts_enabled(){return normalContext;}
uint64_t mach_absolute_time(){return nowTick*1000000;}void absolutetime_to_nanoseconds(uint64_t t,uint64_t *out){*out=t;}
void IOSleep(unsigned ms){assert(ms<=120000);nowTick+=ms;if(mode==11)normalContext=false;}
int thread_terminate(void*){throw Terminated{};}void *current_thread(){return (void*)2;}
[[noreturn]]void panic(const char*){abort();}
int kernel_thread_start(void(*fn)(void*,int),void *context,void **handle){++starts;if(mode==9)return 5;pending=fn;pendingContext=context;*handle=mode==10?nullptr:(void*)3;return 0;}
void thread_deallocate(void*p){assert(p==(void*)3);++deallocs;}
'''
MAIN=r'''
void reset(unsigned m){assert(!attachedService&&platform.refs==1);mode=m;normalContext=boardValid=true;nowTick=0;starts=deallocs=serviceFrees=sends=lockDepth=0;pending=nullptr;pendingContext=nullptr;scheduled269=done269=schedulingReturned269=0;for(auto &v:status269)v=0;}
int main(){unsigned controls=0;
for(unsigned m=0;m<=11;++m){reset(m);uint32_t out[16]{};assert(!zorn26_ui_scene_snapshot269(out));zorn26_ui_scene_schedule269(&platform);assert(starts==1);const unsigned refs=platform.refs;zorn26_ui_scene_schedule269(&platform);assert(starts==1&&platform.refs==refs);
 if(m!=9){assert(pending&&platform.refs==2);try{pending(pendingContext,0);}catch(Terminated&){};}
 assert(zorn26_ui_scene_done269()&&zorn26_ui_scene_snapshot269(out));
 if(m==0||m==10){assert(out[0]==6&&out[5]==17&&out[6]==17&&out[7]==0&&out[8]==0&&out[15]==0&&sends==18&&out[9]==1020);assert(out[2]==(m==10?1021u:1023u));assert(attachedService&&attachedService->registered&&platform.refs==2);}
 else{assert(out[0]==7);if(m==8){assert(!sends&&!attachedService&&platform.refs==1&&!(out[2]&512));}if(m==7){assert(!sends&&out[15]==1&&out[9]==30000);}if(m==5){assert(sends==2&&out[5]==1&&out[7]==0xe00002c0u&&out[8]==0);}if(m==6){assert(sends==18&&out[8]==0xe00002c0u);}if(m==9)assert(platform.refs==1&&!pending&&out[1]==5);}
 if(attachedService){auto*s=attachedService;s->retain();s->detach(&platform);s->release();}
 assert(platform.refs==1&&!attachedService&&!lockDepth);assert(deallocs==((m==9||m==10)?0u:1u));++controls;
}
reset(0);normalContext=false;zorn26_ui_scene_schedule269(&platform);assert(!scheduled269&&!starts&&platform.refs==1);++controls;
reset(0);boardValid=false;zorn26_ui_scene_schedule269(&platform);assert(!scheduled269&&!starts&&platform.refs==1);++controls;
reset(0);IOService foreign;zorn26_ui_scene_schedule269(&foreign);assert(!scheduled269&&!starts&&foreign.refs==1);++controls;
printf("PASS actual269 creator/worker/subclass bodies:%u controls,once-only schedule,real board predicate,thread failure/null-handle retention,init/attach/start failures,registered creation-reference release,subscriber timeout,contact/lift failure cleanup\n",controls);
}
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--touch-common',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sanitizer',choices=['address-undefined','thread'],required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    source=a.source/'ZornUiSceneService269.cpp';text=source.read_text();actual=text[text.index('class ZornUiSceneService269 final'):]
    f=a.out/'actual-service.cpp';f.write_text(PREFIX+actual+MAIN);exe=a.out/'actual-service';san='address,undefined' if a.sanitizer=='address-undefined' else 'thread'
    args=['xcrun','clang++','-std=c++17','-O1','-g','-pthread','-fno-omit-frame-pointer','-fsanitize='+san,'-I'+str(a.source),'-I'+str(a.touch_common),str(f),'-o',str(exe)]
    env=os.environ|dict(ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0',TSAN_OPTIONS='symbolize=0:halt_on_error=1');r=subprocess.run(args,capture_output=True,env=env,timeout=120);(a.out/'compile.stderr').write_bytes(r.stderr);assert not r.returncode,r.stderr.decode(errors='replace')
    r=subprocess.run([str(exe)],capture_output=True,env=env,timeout=120);(a.out/'run.stdout').write_bytes(r.stdout);(a.out/'run.stderr').write_bytes(r.stderr);assert not r.returncode,r.stderr.decode(errors='replace')
    pin=lambda f:dict(path=str(f.resolve()),sha256=hashlib.sha256(f.read_bytes()).hexdigest())
    result=dict(passed=True,sanitizer=a.sanitizer,source=pin(source),plan=pin(a.source/'ZornUiScenePlan269.h'),actual_method_bodies_extracted=True,test=pin(f),executable=pin(exe),arguments=args,stdout=r.stdout.decode(),host_boundaries='Explicit IOKit allocations/service-plane references/threads/time/frame dispatch stubs;actual selected base open-close predicate tested separately;native full link verifies real OS26 ABI. No real subscriber queue or unlock evidence.',phone_access=False,actual_HID_dispatch_or_delivery_qualified=False)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(r.stdout.decode().strip())
if __name__=='__main__':main()

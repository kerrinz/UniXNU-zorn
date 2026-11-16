#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,hashlib,os
import argparse
parser=argparse.ArgumentParser(description='Host-only source-defined K80 known-frame queue/identity regression;no USB')
parser.add_argument('--source-root',type=Path,required=True)
parser.add_argument('--out',type=Path,required=True,help='new independent output directory')
args=parser.parse_args();S=args.source_root.resolve();O=args.out.resolve();O.mkdir(parents=True,exist_ok=False)
t=(S/'MiniIOMobileFramebuffer.cpp').read_text();a=t.index('    case ZornKnownPresentSubmit247:');z=t.index('\n#endif',a);cases=t[a:z]
source=r'''
#define KERNEL 1
#define ZORN_IOS26 1
#include "ZornKnownPresent247.h"
#include <cassert>
#include <cstring>
#include <initializer_list>
#include <thread>
#include <atomic>
using IOReturn=int;constexpr int kIOReturnSuccess=0,kIOReturnUnsupported=1,kIOReturnBadArgument=2,kIOReturnNotFound=3,kIOReturnBusy=4,kIOReturnNotReady=5;
static ZornKnownPresent247 zornKnownPresent247;
static unsigned enabled=2,holds,drops,queueCalls;static bool flag=true,exists=true,badSize=false;static int queueRaw;
static bool PE_parse_boot_argn(const char*key,void*p,unsigned){assert(!strcmp(key,"zorn26_software_accelerator"));*(unsigned*)p=enabled;return flag;}
struct MiniIOSurface {struct {uint32_t width=32,height=32,bytesPerRow=128,bytesPerElement=4,planeCount=0,pixelFormat=0x52474241;}info;} surface;
static MiniIOSurface *MiniIOSurfaceCopy(uint32_t){if(!exists)return nullptr;++holds;if(badSize)surface.info.width=31;return &surface;}
static void MiniIOSurfaceDrop(MiniIOSurface*){++drops;}
static uint32_t OSIncrementAtomic(uint32_t *p){auto old=*p;++*p;return old;}
#define FOURCC(a,b,c,d) ((uint32_t)(a)<<24|(uint32_t)(b)<<16|(uint32_t)(c)<<8|(uint32_t)(d))
#define SWAP_SIZE 0x46c
#define SWAP_ID 0x50
#define SWAP_SURFACE(i) (0x54+4*(i))
#define SWAP_SOURCE(i) (0x64+16*(i))
#define SWAP_ENABLED(i) (0xa4+4*(i))
#define SWAP_DEST(i) (0xc4+16*(i))
#define SWAP_LAYERS_SET 0x104
#define SWAP_LAYERS_CLEARED 0x108
static uint32_t get(const uint8_t *p,unsigned at){uint32_t v;memcpy(&v,p+at,4);return v;}
static bool completeInCall=false;
struct Owner {uint32_t fWidth=1125,fHeight=2436,fSwapID=10;
 int present(const uint8_t*p){++queueCalls;assert(get(p,SWAP_SURFACE(0))==55 && get(p,SWAP_ID)==fSwapID && get(p,SWAP_ENABLED(0))==1);assert(get(p,SWAP_SOURCE(0)+8)==32 && get(p,SWAP_SOURCE(0)+12)==32);assert(get(p,SWAP_DEST(0)+8)==fWidth && get(p,SWAP_DEST(0)+12)==fHeight);assert(get(p,SWAP_LAYERS_SET)==1 && get(p,SWAP_LAYERS_CLEARED)==14);
 if(completeInCall){uint32_t record[16]={2,fSwapID,4,2,4,4,1,55,1,1,1,10,11,1125,2436,4};assert(zornKnownPresent247.complete(record));}return queueRaw;}
};
struct Args{const uint64_t *scalarInput;uint64_t *scalarOutput;unsigned scalarInputCount,scalarOutputCount,structureInputSize=0,structureOutputSize=0;};
static int actual(Owner *fOwner,uint32_t selector,Args *args){const uint64_t *in=args->scalarInput;uint64_t *out=args->scalarOutput;switch(selector){
CASES
 default:return 99;}}
static void reset(){enabled=2;flag=exists=true;badSize=completeInCall=false;queueRaw=holds=drops=queueCalls=0;surface={};zornKnownPresent247.armed=0;}
int main(){
 assert(ZornSoftwareSelected247(1)&&ZornSoftwareSelected247(2)&&!ZornSoftwareSelected247(0)&&!ZornSoftwareSelected247(3)&&!ZornKnownPresentMode247(1)&&ZornKnownPresentMode247(2));
 uint64_t in[2]={55,0},out[16];Owner owner;Args a{in,out,1,1};reset();
 for(unsigned i=0;i<4;++i){flag=true;enabled=i==0?0:i==1?1:i==2?3:0xffffffffu;assert(actual(&owner,ZornKnownPresentSubmit247,&a)==kIOReturnUnsupported && !holds && !queueCalls);}reset();
 for(uint64_t invalid:{0ULL,0x100000000ULL}){in[0]=invalid;assert(actual(&owner,ZornKnownPresentSubmit247,&a)==kIOReturnBadArgument && !holds);}in[0]=55;
 exists=false;assert(actual(&owner,ZornKnownPresentSubmit247,&a)==kIOReturnNotFound);exists=true;badSize=true;assert(actual(&owner,ZornKnownPresentSubmit247,&a)==kIOReturnUnsupported && holds==drops);reset();
 queueRaw=17;assert(actual(&owner,ZornKnownPresentSubmit247,&a)==17 && holds==drops && !zornKnownPresent247.armed);reset();
 assert(actual(&owner,ZornKnownPresentSubmit247,&a)==0 && holds==drops && zornKnownPresent247.armed && queueCalls==1);auto frame=out[0];assert(actual(&owner,ZornKnownPresentSubmit247,&a)==kIOReturnBusy && queueCalls==1 && holds==drops);
 uint64_t query[2]={frame,55};Args q{query,out,2,16};assert(actual(&owner,ZornKnownPresentQuery247,&q)==kIOReturnNotReady);
 uint32_t record[16]={2,uint32_t(frame),4,2,4,4,1,55,1,1,1,10,11,1125,2436,4};record[1]++;assert(!zornKnownPresent247.complete(record));record[1]--;record[7]++;assert(!zornKnownPresent247.complete(record));record[7]--;
 zornKnownPresent247.trace.gate=1;assert(!zornKnownPresent247.complete(record) && zornKnownPresent247.armed);zornKnownPresent247.trace.gate=0;
 assert(zornKnownPresent247.complete(record) && !zornKnownPresent247.armed);assert(actual(&owner,ZornKnownPresentQuery247,&q)==0 && out[1]==frame && out[7]==55 && out[15]==4);
 query[0]++;assert(actual(&owner,ZornKnownPresentQuery247,&q)==kIOReturnNotReady);query[0]--;query[1]++;assert(actual(&owner,ZornKnownPresentQuery247,&q)==kIOReturnNotReady);
 reset();completeInCall=true;assert(actual(&owner,ZornKnownPresentSubmit247,&a)==0 && !zornKnownPresent247.armed && holds==drops); // completion can beat present() return
 ZornKnownPresent247 c;assert(!c.arm(0,1)&&!c.arm(1,0)&&c.arm(7,55));c.cancel(8,55);assert(c.armed);c.cancel(7,55);assert(!c.armed);
 std::atomic<bool> done{false};std::thread writer([&]{for(unsigned n=1;n<=100000;++n){assert(c.arm(n,55));uint32_t r[16]={2,n,4,2,4,4,1,55,1,1,1,n,n+1,1125,2436,4};assert(c.complete(r));}done=true;});while(!done){uint32_t r[16];if(c.trace.snapshot(r))assert(r[7]==55 && r[12]==r[11]+1 && r[1]==r[11]);}writer.join();
}
'''.replace('CASES',cases)
f=O/'actual-api.cpp';f.write_text(source);a=['/usr/bin/clang++','-std=c++17','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(S),str(f),'-o',str(O/'check')];p=subprocess.run(a,capture_output=True,text=True);(O/'compile.log').write_text(p.stdout+p.stderr);assert not p.returncode,p.stderr;p=subprocess.run([str(O/'check')],capture_output=True,text=True,env=os.environ|{'ASAN_OPTIONS':'symbolize=0','UBSAN_OPTIONS':'symbolize=0:print_stacktrace=0'});assert not p.returncode,p.stderr
r=dict(passed=True,ASan_UBSan=True,actual_switch_cases_extracted=True,source_sha256=hashlib.sha256(t.encode()).hexdigest(),header_sha256=hashlib.sha256((S/'ZornKnownPresent247.h').read_bytes()).hexdigest(),checks=['disabled config refuses','bounds and shape','real queue raw propagated','one pending request','temporary surface hold/drop balance','actual completion required','foreign frame/SID refused','dropped snapshot retains pending','completion-before-submit-return','cancel only exact token','100000 concurrent snapshots'],boundaries_stubbed=['IOKit','original present queue','surface allocation'],hardware_qualification=False,phone_access=False);(O/'result.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS247 actual known-frame API and ticket lifetime ASan/UBSan')

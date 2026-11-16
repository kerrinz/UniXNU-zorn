#!/usr/bin/env python3
"""Host source regression for IOSurface association;no phone or MMIO access.

Use the exact prepared246 source directory containing MiniIOSurface.cpp and
ZornSurfaceBacking246.h. CPU-page variants are host fixtures,not hardware claims.
"""
from pathlib import Path
import argparse,json,subprocess,hashlib,shutil
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-root',type=Path,required=True)
parser.add_argument('--out',type=Path,required=True,help='new independent output directory')
args=parser.parse_args();S=args.source_root.resolve();O=args.out.resolve();O.mkdir(parents=True,exist_ok=False)
t=(S/'MiniIOSurface.cpp').read_text();a=t.index('extern "C" void *zorn_surface_copy_backing246(');z=t.index('/* How many surfaces there are',a);actual=t[a:z]
prefix=r'''
#include <stdint.h>
#include <cstddef>
#include <cassert>
#include "ZornSurfaceBacking246.h"
#ifndef PAGE_SIZE
#define PAGE_SIZE 16384
#endif
constexpr unsigned MINISURF_TABLE_SIZE=16;
using IOByteCount=uint64_t;
constexpr int kIOMemoryMapperNone=0;
struct Memory{uint64_t base,length,chunk=4096,wrongAt=UINT64_MAX;
 uint64_t getLength()const{return length;}
 uint64_t getPhysicalSegment(uint64_t at,uint64_t*n,int){if(at>=length){*n=0;return 0;}*n=chunk-(at%chunk);if(*n>length-at)*n=length-at;return base+at+(at>=wrongAt?4096:0);}
};
using IOMemoryDescriptor=Memory;
struct MiniIOSurface{unsigned sid,holders;Memory*client,*memory;struct{uint64_t allocSize;}info;bool released=false;void release(){released=true;}};
static MiniIOSurface *gSurfaceTable[MINISURF_TABLE_SIZE];
static uint32_t zornSurfaceFence246[MINISURF_TABLE_SIZE];
static unsigned gSurfaceCount=1;static uint64_t gSurfaceBytes=2*PAGE_SIZE;
static void*gSurfaceLock=(void*)1;static bool busy=false,held=false;
static bool IOLockTryLock(void*){if(busy)return false;assert(!held);held=true;return true;}
static void IOLockUnlock(void*){assert(held);held=false;}
static void surfaceHold(MiniIOSurface*s){assert(held);++s->holders;}
static void IOLockLock(void*){assert(!held&&!busy);held=true;}
'''
# Original lifecycle code,including246 reset,is extracted instead of a release stub.
u=(S/'MiniIOSurface.cpp').read_text()
a=u.index('static void\nsurfaceUnhold(');z=u.index('\n}\n',a)+3
unhold=u[a:z]
a=u.index('void\nMiniIOSurfaceDrop(');z=u.index('\n}\n',a)+3
prefix+=unhold+u[a:z]
main=r'''
static ZornSurfaceBacking246 backing(Memory&m){return {&m,m.length,[](void*p,uint64_t at,uint64_t*pa,uint64_t*n)->bool{*pa=static_cast<Memory*>(p)->getPhysicalSegment(at,n,0);return *pa&&*n;}};}
int main(){
 Memory source{0x100000,2*PAGE_SIZE,4096};auto b=backing(source);unsigned status=99;
 assert(!zorn_surface_copy_backing246(b,&status)&&status==ZornSurfaceNone246);
 Memory storage{source.base-PAGE_SIZE,3*PAGE_SIZE,16384};MiniIOSurface one{1,1,nullptr,&storage,{2*PAGE_SIZE}};gSurfaceTable[1]=&one;
 auto*p=zorn_surface_copy_backing246(b,&status);assert(p==&one&&status==ZornSurfaceMatched246&&one.holders==2);
 zorn_surface_completed246(p,9);assert(zorn_surface_fence246(1)==9);zorn_surface_completed246(p,4);assert(zorn_surface_fence246(1)==9);zorn_surface_completed246(p,0);assert(zorn_surface_fence246(1)==9);zorn_surface_drop246(p);assert(one.holders==1);
 busy=true;assert(!zorn_surface_copy_backing246(b,&status)&&status==ZornSurfaceUnavailable246&&one.holders==1);zorn_surface_completed246(&one,10);busy=false;assert(zorn_surface_fence246(1)==9);
 MiniIOSurface alias{2,1,nullptr,&storage,{2*PAGE_SIZE}};gSurfaceTable[2]=&alias;assert(!zorn_surface_copy_backing246(b,&status)&&status==ZornSurfaceAmbiguous246&&one.holders==1&&alias.holders==1);gSurfaceTable[2]=nullptr;
 storage.wrongAt=PAGE_SIZE+4096;assert(!zorn_surface_copy_backing246(b,&status)&&status==ZornSurfaceNone246);storage.wrongAt=UINT64_MAX;
 Memory wrapped=source;one.client=&wrapped;p=zorn_surface_copy_backing246(b,&status);assert(p==&one);zorn_surface_drop246(p);one.client=nullptr;
 storage.length=PAGE_SIZE;assert(!zorn_surface_copy_backing246(b,&status)&&status==ZornSurfaceNone246);storage.length=3*PAGE_SIZE;
 unsigned budget=0;assert(!ZornSurfaceSameBacking246(b,b,budget));budget=100;Memory wrong=source;wrong.base+=4096;assert(!ZornSurfaceSameBacking246(b,backing(wrong),budget));
 Memory huge{0x100000,40000,1};one.client=&huge;one.info.allocSize=40000;assert(!zorn_surface_copy_backing246(backing(huge),&status)&&status==ZornSurfaceUnavailable246&&one.holders==1);
 Memory overflow{UINT64_MAX-3,8,8};budget=5;assert(!ZornSurfaceSameBacking246(backing(overflow),backing(overflow),budget));
 one.client=nullptr;one.info.allocSize=2*PAGE_SIZE;MiniIOSurface other{1,1,nullptr,&storage,{2*PAGE_SIZE}};zorn_surface_completed246(&other,20);assert(zorn_surface_fence246(1)==9);
 assert(!zorn_surface_copy_backing246(b,nullptr));assert(!held);
 p=zorn_surface_copy_backing246(b,&status);assert(p==&one&&one.holders==2);MiniIOSurfaceDrop(&one);assert(one.holders==1&&gSurfaceTable[1]==&one&&!one.released);zorn_surface_drop246(p);assert(one.holders==0&&one.released&&!gSurfaceTable[1]&&zornSurfaceFence246[1]==0);gSurfaceTable[1]=&other;assert(zorn_surface_fence246(1)==0);
}
''';f=O/'actual-surface.cpp';f.write_text(prefix+actual+main);runs=[]
for size in [4096,16384]:
 args=['/usr/bin/clang++','-std=c++17','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I',str(S),'-DPAGE_SIZE='+str(size),str(f),'-o',str(O/('check'+str(size)))];p=subprocess.run(args,capture_output=True);(O/f'compile{size}.log').write_bytes(p.stdout+p.stderr);assert not p.returncode,p.stderr;p=subprocess.run([str(O/('check'+str(size)))],capture_output=True);(O/f'run{size}.log').write_bytes(p.stdout+p.stderr);assert not p.returncode,p.stderr;runs.append(dict(CPU_page_bytes=size,exit=p.returncode))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();(O/'result.json').write_text(json.dumps(dict(passed=True,actual_kernel_helper_extracted=True,header_sha256=sha(S/'ZornSurfaceBacking246.h'),source_sha256=sha(S/'MiniIOSurface.cpp'),ASan_UBSan=runs,checks=['full extent cross-segment match','retain/drop balance','wrapped memory','ambiguous alias refuses attribution','late page mismatch','busy lookup/completion','same SID foreign live object refuses completion','actual unhold/drop lifetime and SID-reuse fence reset','budget exhaustion','overflow','monotonic nonzero actual fence'],limits='Host descriptor/lock/surface table stubs;no hardware or GPU write proof'),indent=2)+'\n');shutil.copy2(__file__,O/'test.py');print('PASS actual surface helper + full span matcher ASan/UBSan at4K/16K CPU geometry')

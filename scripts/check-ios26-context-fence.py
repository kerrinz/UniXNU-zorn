#!/usr/bin/env python3
"""Test real Ring fence and Submit wait classification;cache/VM release are explicit host boundaries."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess

def extract(t,start):
 a=t.index(start);z=t.index('{',a)+1;depth=1
 while depth:depth+=(t[z]=='{')-(t[z]=='}');z+=1
 return t[a:z]

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--ring-source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sanitizer',choices=['address,undefined','thread'],default='address,undefined');a=p.parse_args();S=a.source_root.resolve();O=a.out.resolve();O.mkdir();ring=a.ring_source.resolve();submit=S/'direct-runtime/ZornGen7DirectSubmit26.cpp';r=ring.read_text();s=submit.read_text()
 methods='\n'.join(extract(r,n) for n in ['NativeAdrenoRingFence NativeAdrenoRing::wait(','NativeAdrenoRingFence NativeAdrenoRing::observeFence('])+'\n'+'\n'.join(extract(s,n) for n in ['IOReturn ZornGen7DirectSubmit26::wait(','IOReturn ZornGen7DirectSubmit26::waitAll('])
 code=r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
using IOReturn=int;constexpr int kIOReturnSuccess=0,kIOReturnNotReady=1,kIOReturnBadArgument=2,kIOReturnTimeout=3;
enum NativeAdrenoRingFence{NativeAdrenoRingFencePoisoned,NativeAdrenoRingFenceArgument,NativeAdrenoRingFenceTimeout,NativeAdrenoRingFenceComplete};
struct NativeAdrenoRingClock{void*cookie;uint64_t(*now_us)(void*);int(*idle)(void*);};
struct Cache {unsigned reads=0;bool fail=false;};
static int acquire(void*p,volatile uint32_t*,unsigned){auto&c=*static_cast<Cache*>(p);++c.reads;return c.fail?1:0;}
class NativeAdrenoRing {public:
 bool attached_=true,poisoned_=false;uint32_t seqno_=2,completed_=0,words[4]{};volatile uint32_t*fence_=words;unsigned fence_bytes_=sizeof(words);Cache hostCache;
 struct{void*cookie;int(*acquire)(void*,volatile uint32_t*,unsigned);}cache_{&hostCache,::acquire};
 void poison(){poisoned_=true;}uint32_t lastSubmitted(){return seqno_;}uint32_t completedFence(){return completed_;}
 NativeAdrenoRingFence wait(uint32_t,const NativeAdrenoRingClock*,uint32_t,uint32_t*);
 NativeAdrenoRingFence observeFence(uint32_t,const NativeAdrenoRingClock*,uint32_t,uint32_t*);
};
struct Vm{unsigned streams_=0;};struct DirectSubmitGateScope{int status=0;explicit DirectSubmitGateScope(unsigned&){};};
static uint32_t zorn_direct_fence_wait[8];
class ZornGen7DirectSubmit26 {public:
 struct Job{bool active=false;uint32_t fence=0,queue=0;};Job jobs_[4];bool attached_=true,poisoned_=false;Vm storage;Vm*vm_=&storage;NativeAdrenoRing hw;NativeAdrenoRing*ring_=&hw;
 struct{unsigned timeouts=0,completed=0;}stats_;unsigned releases=0;IOReturn releaseRaw=0;
 unsigned outstanding(){unsigned n=0;for(auto&j:jobs_)n+=j.active;return n;}
 Job*find(uint32_t f){for(auto&j:jobs_)if(j.active&&j.fence==f)return &j;return nullptr;}
 IOReturn poison(){poisoned_=true;return kIOReturnNotReady;}
 IOReturn release(Job&j){++releases;if(releaseRaw)return releaseRaw;j.active=false;return 0;}
 IOReturn wait(uint32_t,const NativeAdrenoRingClock*,uint32_t,bool*pendingFence=nullptr);
 IOReturn waitAll(const NativeAdrenoRingClock*,uint32_t,bool*pendingFence=nullptr);
};
ACTUAL_METHODS
struct Time{uint64_t ticks=1;unsigned idle=0;};
static uint64_t now(void*p){return static_cast<Time*>(p)->ticks++;}static int idle(void*p){++static_cast<Time*>(p)->idle;return 0;}
int main(){unsigned controls=0;
 {NativeAdrenoRing r;Time t;NativeAdrenoRingClock c{&t,now,idle};uint32_t seen=99;assert(r.wait(1,&c,0,&seen)==NativeAdrenoRingFenceTimeout&&seen==0&&r.hostCache.reads==1&&!t.idle);++controls;r.words[1]=2;assert(r.wait(1,&c,0,&seen)==NativeAdrenoRingFenceComplete&&seen==2&&r.completed_==2&&!t.idle);++controls;}
 {ZornGen7DirectSubmit26 s;s.jobs_[0]={true,1,0};Time t;NativeAdrenoRingClock c{&t,now,idle};bool pending=false;assert(s.waitAll(&c,0,&pending)==kIOReturnTimeout&&pending&&s.releases==0&&s.outstanding()==1&&!t.idle);++controls;
  s.hw.words[1]=2;assert(!s.waitAll(&c,0,&pending)&&!pending&&s.releases==1&&!s.outstanding());++controls;}
 {ZornGen7DirectSubmit26 s;s.jobs_[0]={true,1,0};s.hw.words[1]=1;s.releaseRaw=kIOReturnTimeout;bool pending=true;assert(s.waitAll(nullptr,0,&pending)==kIOReturnTimeout&&!pending&&s.releases==1&&s.outstanding()==1);++controls;}
 {ZornGen7DirectSubmit26 s;s.jobs_[0]={true,1,0};s.hw.hostCache.fail=true;bool pending=true;assert(s.waitAll(nullptr,0,&pending)==kIOReturnNotReady&&!pending&&s.releases==0&&s.poisoned_);++controls;}
 {ZornGen7DirectSubmit26 s;bool pending=false;assert(s.wait(1,nullptr,0,&pending)==kIOReturnTimeout&&pending&&!s.releases);++controls;}
 for(unsigned n=1;n<=4;++n){ZornGen7DirectSubmit26 s;s.hw.seqno_=n;s.hw.words[1]=n;for(unsigned i=0;i<n;++i)s.jobs_[i]={true,i+1,0};bool pending=true;assert(!s.waitAll(nullptr,0,&pending)&&!pending&&s.releases==n&&s.stats_.completed==n&&!s.outstanding());++controls;}
 for(unsigned mode=0;mode<3;++mode){ZornGen7DirectSubmit26 s;s.jobs_[0]={true,1,0};if(mode==0)s.attached_=false;if(mode==1)s.poisoned_=true;if(mode==2)s.hw.words[1]=3;bool pending=true;assert(s.waitAll(nullptr,0,&pending)==kIOReturnNotReady&&!pending&&!s.releases);++controls;}
 std::printf("PASS258 actual Ring zero-budget fence and Submit pending-vs-release-error classification (%u controls);host cache/VM boundary explicit\n",controls);
}
'''.replace('ACTUAL_METHODS',methods)
 f=O/'actual.cpp';f.write_text(code);env=dict(os.environ,ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0',TSAN_OPTIONS='symbolize=0:halt_on_error=1');commands=[]
 for args in [['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-g','-fsanitize='+a.sanitizer,str(f),'-o',str(O/'check')],[str(O/'check')]]:
  v=subprocess.run(args,capture_output=True,text=True,timeout=120,env=env);commands.append(dict(arguments=args,exit=v.returncode,stdout=v.stdout,stderr=v.stderr,symbolization_disabled=True));(O/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');assert not v.returncode,v.stderr[-3000:]
 pin=lambda p:dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest());(O/'result.json').write_text(json.dumps(dict(passed=True,sanitizer=a.sanitizer,actual_sources=[pin(ring),pin(submit),pin(S/'direct-runtime/ZornGen7DirectSubmit26.h')],test_tool=pin(Path(__file__).resolve()),actual_Ring_wait_and_observeFence_compiled=True,actual_Submit_wait_and_waitAll_compiled=True,zero_budget_performs_actual_cache_observation_without_idle_retry=True,completed_fence_release_timeout_is_not_pending_fence=True,source_hardware_cache_and_VM_release_boundaries_are_host_fixtures=True,phone_access=False,hardware_qualified=False,stdout=commands[-1]['stdout']),indent=2)+'\n');print(commands[-1]['stdout'].strip())

if __name__=='__main__':main()

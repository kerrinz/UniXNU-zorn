#!/usr/bin/env python3
"""Compile actual Ring/Submit/VM retirement methods together;memory/SMMU boundaries are explicit host fixtures."""
from pathlib import Path
import argparse,ast,hashlib,json,os,subprocess

def extract(t,start):
 a=t.index(start);z=t.index('{',a)+1;d=1
 while d:d+=(t[z]=='{')-(t[z]=='}');z+=1
 return t[a:z]

def literal(path,name):
 for n in ast.walk(ast.parse(path.read_text())):
  if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id==name for x in n.targets):
   v=n.value
   while isinstance(v,ast.Call) and isinstance(v.func,ast.Attribute):v=v.func.value
   return ast.literal_eval(v)
 raise ValueError(name)

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--coherence-header',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sanitizer',choices=['address,undefined','thread'],default='address,undefined');a=p.parse_args();S=a.source_root.resolve();O=a.out.resolve();O.mkdir();D=Path(__file__).resolve().parent
 paths=[S/'direct-ring/NativeAdrenoRing.cpp',S/'direct-runtime/ZornGen7DirectSubmit26.cpp',S/'direct-runtime/ZornGen7DirectVm26.cpp',a.coherence_header.resolve()];ring,submit,vm,coherence=[f.read_text() for f in paths]
 code=literal(D/'check-ios26-context-fence.py','code').split('int main(){')[0]
 code=code.replace('#include <cstdio>','#include <cstdio>\n#include <cstddef>')
 code=code.replace('kIOReturnTimeout=3;', 'kIOReturnTimeout=3,kIOReturnIOError=4;')
 code=code.replace('struct Cache {', 'static bool routeGateHeld=false;static unsigned begins=0,ends=0,cacheInsideGate=0;\nstruct Cache {')
 code=code.replace('++c.reads;', '++c.reads;if(routeGateHeld)++cacheInsideGate;')
 start=code.index('struct Vm{');end=code.index('static uint32_t zorn_direct_fence_wait',start)
 declarations=r'''
struct ZornGen7DirectVm26Routes {void*cookie;IOReturn(*beginSubmission)(void*);void(*endSubmission)(void*);IOReturn(*fault)(void*);};
static IOReturn begin(void*){assert(!routeGateHeld);routeGateHeld=true;++begins;return 0;}
static void end(void*){assert(routeGateHeld);routeGateHeld=false;++ends;}
static IOReturn fault(void*){return 1;}
static constexpr unsigned ZornGen7DirectVm26MaxObjects=4,ZornSmmuSparse4KWrite=2,ZornSmmuSparse4KIoError=7;
static uint32_t zorn_direct_coherent_skips[4],zorn_direct_io_coherent=0;
ACTUAL_COHERENCE
ACTUAL_COHERENT_MAPPING
struct MemoryFixture {unsigned refs=1,cacheReads=0;bool isImport=false,quarantined=false;IOReturn retireRaw=0,cacheRaw=0;
 IOReturn retireAfterQuiescence(){assert(routeGateHeld);if(retireRaw)return retireRaw;assert(refs);--refs;return 0;}
 unsigned deviceReferences()const{return refs;}
 bool imported()const{return isImport;}size_t bytes()const{return 4096;}
 IOReturn acquireDeviceWrites(size_t at,size_t n){assert(routeGateHeld&&at==0&&n==4096);++cacheReads;return cacheRaw;}
 void quarantine(){quarantined=true;}
};
static unsigned surfaceCalls=0;static uint32_t surfaceFence=0;
static void zorn_surface_completed246(uint64_t surface,uint32_t fence){assert(routeGateHeld&&surface==101);++surfaceCalls;surfaceFence=fence;}
class ZornGen7DirectVm26 {public:
 struct Mapping{uint64_t handle=0;MemoryFixture*memory=nullptr;unsigned jobs=0,permissions=0,writeback=0,shareability=0;uint64_t surface246=0;};
 Mapping records[ZornGen7DirectVm26MaxObjects]{};Mapping*mappings_=records;bool attached_=true,poisoned_=false;unsigned submission_resources_=1;
 ZornGen7DirectVm26Routes routes{this,begin,end,fault};ZornGen7DirectVm26Routes*streams_=&routes;
 struct{unsigned operation=0,quarantine=0;bool complete=true;}result_;
 struct Region{void*arena=nullptr;struct Table{void quarantine(){}}table;Table*tables=&table;struct State{unsigned poisoned=0;}stateBody;State*state=&stateBody;}regions_[2];
 Mapping*find(uint64_t);IOReturn fail(unsigned);IOReturn acquireImported();IOReturn retireJobAfterCompletion(uint64_t);IOReturn retireSubmissionResourcesAfterCompletion();void noteSurfaceCompletion246(uint32_t);
};
ACTUAL_GATE
'''
 declarations=declarations.replace('ACTUAL_COHERENCE',coherence[coherence.index('enum '):coherence.index(';')+1]+'\n'+extract(coherence,'static inline bool NativeAdrenoCoherentMapping(')).replace('ACTUAL_COHERENT_MAPPING',extract(vm,'static bool coherentMapping(')).replace('ACTUAL_GATE',extract(submit,'struct DirectSubmitGateScope {')+';')
 code=code[:start]+declarations+code[end:]
 code=code.replace('struct Job{bool active=false;uint32_t fence=0,queue=0;};','struct Job{bool active=false;uint32_t fence=0,queue=0;size_t count=0;uint64_t handles[4]{};};').replace('Vm storage;Vm*vm_=&storage;', 'ZornGen7DirectVm26 storage;ZornGen7DirectVm26*vm_=&storage;struct Present{bool failed=false;uint32_t retiredFence=0;}presentBody;Present*present_=&presentBody;')
 code=code.replace('unsigned timeouts=0,completed=0;', 'unsigned timeouts=0,completed=0,references_retired=0;')
 old='IOReturn poison(){poisoned_=true;return kIOReturnNotReady;}';assert old in code;code=code.replace(old,'IOReturn poison();')
 old='IOReturn release(Job&j){++releases;if(releaseRaw)return releaseRaw;j.active=false;return 0;}';assert old in code;code=code.replace(old,'IOReturn release(Job&);')
 old='Job*find(uint32_t f){for(auto&j:jobs_)if(j.active&&j.fence==f)return &j;return nullptr;}';assert old in code;code=code.replace(old,'Job*find(uint32_t);')
 methods='\n'.join(extract(ring,n) for n in ['NativeAdrenoRingFence NativeAdrenoRing::wait(','NativeAdrenoRingFence NativeAdrenoRing::observeFence('])+'\n'+'\n'.join(extract(submit,n) for n in ['IOReturn ZornGen7DirectSubmit26::poison(','ZornGen7DirectSubmit26::Job *ZornGen7DirectSubmit26::find(','IOReturn ZornGen7DirectSubmit26::release(','IOReturn ZornGen7DirectSubmit26::wait(','IOReturn ZornGen7DirectSubmit26::waitAll('])+'\n'+'\n'.join(extract(vm,n) for n in ['ZornGen7DirectVm26::Mapping *ZornGen7DirectVm26::find(','IOReturn ZornGen7DirectVm26::fail(','IOReturn ZornGen7DirectVm26::acquireImported(','IOReturn ZornGen7DirectVm26::retireJobAfterCompletion(','IOReturn ZornGen7DirectVm26::retireSubmissionResourcesAfterCompletion(','void ZornGen7DirectVm26::noteSurfaceCompletion246('])
 methods=methods.replace('ZornSmmuSparse4KStatus status','unsigned status')
 code=code.replace('ACTUAL_METHODS',methods)
 if 'zorn_failure_' in methods:
  paths.append(S/'ZornClientFailure261.h')
  code=('#include '+json.dumps(str(paths[-1]))+'\n'
        'extern "C" void zorn_failure_note261(uint32_t,uint32_t,uint32_t,uint32_t,uint32_t,uint32_t) {}\n'+code)
 tests=r'''
struct Fixture {ZornGen7DirectSubmit26 s;MemoryFixture ib,output,readOnly;
 Fixture(){begins=ends=cacheInsideGate=surfaceCalls=0;surfaceFence=0;zorn_direct_io_coherent=0;assert(!routeGateHeld);
  output.isImport=readOnly.isImport=true;s.storage.records[0]={1,&ib,1,0,0,0,0};s.storage.records[1]={2,&output,1,ZornSmmuSparse4KWrite,0,0,101};s.storage.records[2]={3,&readOnly,0,0,0,0,0};s.jobs_[0]={true,1,0,2,{1,2}};}
 ~Fixture(){assert(!routeGateHeld&&begins==ends&&!cacheInsideGate);}
};
int main(){unsigned controls=0;
 {Fixture f;Time time;NativeAdrenoRingClock clock{&time,now,idle};bool pending=false;assert(f.s.waitAll(&clock,0,&pending)==kIOReturnTimeout&&pending&&f.ib.refs==1&&f.output.refs==1&&!f.output.cacheReads&&f.s.storage.submission_resources_==1&&!surfaceCalls&&f.s.outstanding()==1&&begins==1);++controls;
  f.s.hw.words[1]=1;assert(!f.s.waitAll(nullptr,0,&pending)&&!pending&&f.ib.refs==0&&f.output.refs==0&&f.output.cacheReads==1&&!f.readOnly.cacheReads&&f.s.storage.submission_resources_==0&&surfaceCalls==1&&surfaceFence==1&&f.s.present_->retiredFence==1&&!f.s.outstanding()&&!f.s.present_->failed&&f.s.stats_.references_retired==2);++controls;
 }
 {Fixture f;f.s.hw.words[1]=1;f.output.cacheRaw=1;bool pending=true;assert(f.s.waitAll(nullptr,0,&pending)==kIOReturnIOError&&!pending&&f.s.poisoned_&&f.s.storage.poisoned_&&f.s.present_->failed&&f.s.outstanding()==1&&f.s.storage.submission_resources_==1&&!surfaceCalls&&!f.s.present_->retiredFence&&f.ib.quarantined&&f.output.quarantined&&f.readOnly.quarantined);const auto n=begins;assert(f.s.waitAll(nullptr,0,&pending)==kIOReturnNotReady&&!pending&&begins==n);++controls;}
 {Fixture f;f.s.hw.words[1]=1;f.ib.retireRaw=kIOReturnTimeout;bool pending=true;assert(f.s.waitAll(nullptr,0,&pending)==kIOReturnIOError&&!pending&&f.s.poisoned_&&f.s.present_->failed&&f.ib.refs==1&&f.output.refs==0&&f.s.storage.submission_resources_==1&&!f.output.cacheReads&&!surfaceCalls&&f.s.outstanding()==1);++controls;}
 {Fixture f;f.s.hw.words[1]=1;f.s.storage.submission_resources_=0;bool pending=true;assert(f.s.waitAll(nullptr,0,&pending)==kIOReturnIOError&&!pending&&f.s.poisoned_&&!surfaceCalls&&!f.s.present_->retiredFence&&f.s.outstanding()==1);++controls;}
 {Fixture f;f.s.hw.words[1]=1;zorn_direct_io_coherent=2;f.s.storage.records[1].writeback=1;f.s.storage.records[1].shareability=3;bool pending=false;assert(!f.s.waitAll(nullptr,0,&pending)&&!pending&&!f.output.cacheReads&&zorn_direct_coherent_skips[3]&&surfaceCalls==1);zorn_direct_io_coherent=0;++controls;}
 {Fixture f;f.s.hw.words[1]=1;f.s.hw.hostCache.fail=true;bool pending=true;assert(f.s.waitAll(nullptr,0,&pending)==kIOReturnIOError&&!pending&&f.ib.refs==1&&f.output.refs==1&&f.s.storage.submission_resources_==1&&!f.output.cacheReads&&!surfaceCalls);++controls;}
 std::printf("PASS259 actual Ring/Submit gate/wait/release/VM retirement chain controls=%u;fence reads outside gate,import cache and surface ledger ordered;memory/SMMU are explicit fixtures\n",controls);
}
'''
 code+=tests;f=O/'actual.cpp';f.write_text(code);env=dict(os.environ,ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0',TSAN_OPTIONS='symbolize=0:halt_on_error=1');commands=[]
 for args in [['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-g','-fsanitize='+a.sanitizer,str(f),'-o',str(O/'check')],[str(O/'check')]]:
  r=subprocess.run(args,capture_output=True,text=True,timeout=120,env=env);commands.append(dict(arguments=args,exit=r.returncode,stdout=r.stdout,stderr=r.stderr,symbolization_disabled=True));(O/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');assert not r.returncode,r.stderr[-4000:]
 pin=lambda p:dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest());(O/'result.json').write_text(json.dumps(dict(passed=True,sanitizer=a.sanitizer,actual_sources=[pin(f) for f in paths],test_tool=pin(Path(__file__).resolve()),actual_Ring_wait_Submit_gate_wait_release_VM_retirement_compiled=True,real_fence_reads_outside_submission_gate=True,cache_visibility_before_submission_resource_and_surface_completion=True,no_Ring_guard_permission_widening_needed_by_this_source_path=True,memory_cache_and_SMMU_route_callbacks_are_host_fixtures=True,phone_access=False,hardware_qualified=False,stdout=commands[-1]['stdout']),indent=2)+'\n');print(commands[-1]['stdout'].strip())

if __name__=='__main__':main()

#!/usr/bin/env python3
"""Test actual board-session bookkeeping/callbacks;physical boundaries stay explicit fixtures."""
from pathlib import Path
import argparse,json,hashlib,os,subprocess

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--parent-source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sanitizer',choices=['address,undefined','thread'],default='address,undefined');a=p.parse_args();S=a.source_root;O=a.out;O.mkdir();current=(S/'ZornGen7DarwinBoardOwner.cpp').read_text();parent=(a.parent_source/'ZornGen7DarwinBoardOwner.cpp').read_text()
 def extract(t,start):
  begin=t.index(start);end=t.index('{',begin)+1;depth=1
  while depth:
   depth+=(t[end]=='{')-(t[end]=='}');end+=1
  return t[begin:end]
 start=current.index('    struct ApplicationSession {');end=current.index('    bool nativeApplicationWindowHeld(',start);physical_split='    bool nativePhysicalResourcesHeld(' in current
 if physical_split:end=min(end,current.index('    bool nativePhysicalResourcesHeld(',start))
 metadata=current[start:end]
 callbacks='\n'.join(extract(current,'        applicationAuthority.'+name+'=[]')+';' for name in ['acquire','check','release'])
 # Keep every real physical/Ring predicate exactly;the host fixture below tests
 # ownership only,not a fabricated successful GPU,MACF,VM or OOB implementation.
 old=extract(parent,'    bool nativeApplicationWindowHeld(');new=extract(current,'    bool nativeApplicationWindowHeld(')
 old=old.replace('''direct_app_publish_attempted && direct_app_granted && direct_app_identity==&client &&
            direct_app_task==task && task && task!=kernel_task && !direct_client_attempted &&
            direct_app_acquires==direct_app_releases+1 &&''','''direct_app_publish_attempted && applicationSessionHeld(client,task) && !direct_client_attempted &&''')
 if physical_split and '(phase==1 || (direct_physical_held && direct_physical_ring==host_ring))' not in old:
  old=old.replace('direct_app_publish_attempted && applicationSessionHeld(client,task) && !direct_client_attempted &&','direct_app_publish_attempted && applicationSessionHeld(client,task) && !direct_client_attempted &&\n            (phase==1 || (direct_physical_held && direct_physical_ring==host_ring)) &&')
 assert old==new,'physical authority predicate changed outside the explicit ownership expression and physical-owner guard'
 prefix=r'''
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <mutex>
#include <thread>
#include <vector>
#include <new>
using IOReturn=int;using task_t=void*;
constexpr IOReturn kIOReturnSuccess=0,kIOReturnNotReady=1,kIOReturnBadArgument=2,kIOReturnExclusiveAccess=3,kIOReturnNoMemory=4;
static task_t kernel_task=reinterpret_cast<void*>(1);
#define TASK_NULL nullptr
static thread_local task_t callingTask;static thread_local bool normalContext=true;
static task_t current_task(){return callingTask;}static bool normal(){return normalContext;}
struct IOUserClient{};struct IOService{};struct IOMemoryDescriptor{};
struct Gate {std::recursive_mutex mutex;std::atomic<void*> owner{nullptr};};
static void *threadId(){static thread_local int id;return &id;}
static bool IORecursiveLockHaveLock(Gate *g){return g && g->owner.load()==threadId();}
static void IORecursiveLockLock(Gate *g){g->mutex.lock();assert(!g->owner.load());g->owner=threadId();}
static void IORecursiveLockUnlock(Gate *g){assert(IORecursiveLockHaveLock(g));g->owner=nullptr;g->mutex.unlock();}
static std::atomic<unsigned> allocations{},frees{},liveRecords{};static bool allocationFails=false,fixtureCleanup=false;
template<class T> static T* allocate(){if(allocationFails)return nullptr;auto *p=new(std::nothrow)T{};if(p){++allocations;++liveRecords;}return p;}
template<class T> static void dispose(T *p){assert(p);assert(fixtureCleanup || p->phase==T::Phase::Retired);++frees;--liveRecords;delete p;}
#define IONewZero(T,N) allocate<T>()
#define IODelete(P,T,N) dispose<T>(P)
enum class ZornGen7AppOperation26:unsigned {PrepareTables,Map,Submit,Wait,CpuView,Close,OobAcquire,OobRelease,Timestamp};
enum class Stage {CpuReady,Other};
struct ZornGen7HostRing26 {bool binding=true;unsigned calls=0;bool nativeApplicationBinding(IOUserClient&,task_t,unsigned,ZornGen7AppOperation26){++calls;return binding;}};
struct Hfi {uint32_t flags=127,raw=0;void copyKernelTaskOobObservation(uint32_t (&out)[8]){out[0]=flags;out[7]=raw;}};
struct ZornGen7AppAuthority26 {
 void *cookie=nullptr;
 IOReturn (*acquire)(void*,IOUserClient&,task_t,ZornGen7HostRing26&,IOService&,IOMemoryDescriptor&,IOService&,IOMemoryDescriptor&)=nullptr;
 IOReturn (*check)(void*,IOUserClient&,task_t,task_t,ZornGen7AppOperation26)=nullptr;
 IOReturn (*release)(void*,IOUserClient&,task_t)=nullptr;
};
class ZornGen7DarwinBoardOwner {public:struct Storage {
 Gate gate;struct {Gate *startup;}gates{&gate};Stage stage=Stage::CpuReady;
 bool direct_client_attempted=false,physicalHealthy=true;
 unsigned direct_oob_epoch=4;ZornGen7HostRing26 *host_ring=nullptr;
 IOService *native_cx_gpu=nullptr,*native_cx_gmu=nullptr;IOMemoryDescriptor *host_gpu_start_gpu_resource=nullptr,*host_gpu_start_gmu_resource=nullptr;
 Hfi *direct_hfi=nullptr;
 ACTUAL_METADATA
 bool nativeApplicationWindowHeld(IOUserClient &client,task_t task,unsigned phase,ZornGen7AppOperation26 op){
  const bool closing=phase==3 || op==ZornGen7AppOperation26::Close || op==ZornGen7AppOperation26::OobRelease;
  return normal() && physicalHealthy && applicationSessionHeld(client,task) && direct_oob_epoch==6 &&
    (current_task()==task || (closing && current_task()==kernel_task));
 }
};Storage *storage_=nullptr;};
using Storage=ZornGen7DarwinBoardOwner::Storage;
static ZornGen7AppAuthority26 callbacks(ZornGen7DarwinBoardOwner &owner){
 ZornGen7AppAuthority26 applicationAuthority{};applicationAuthority.cookie=&owner;
 ACTUAL_CALLBACKS
 return applicationAuthority;
}
'''.replace('ACTUAL_METADATA',metadata).replace('ACTUAL_CALLBACKS',callbacks)
 tests=r'''
struct Fixture {
 Storage s;ZornGen7DarwinBoardOwner board;ZornGen7HostRing26 ring;IOService gpu,gmu;IOMemoryDescriptor gr,mr;Hfi hfi;IOUserClient a,b;
 task_t ta=reinterpret_cast<void*>(2),tb=reinterpret_cast<void*>(3);ZornGen7AppAuthority26 auth;
 Fixture(){s.host_ring=&ring;s.native_cx_gpu=&gpu;s.native_cx_gmu=&gmu;s.host_gpu_start_gpu_resource=&gr;s.host_gpu_start_gmu_resource=&mr;s.direct_hfi=&hfi;s.direct_app_publish_attempted=true;board.storage_=&s;auth=callbacks(board);callingTask=ta;normalContext=true;}
 IOReturn acquire(IOUserClient &c,task_t task){return auth.acquire(auth.cookie,c,task,ring,gpu,gr,gmu,mr);}
 IOReturn release(IOUserClient &c,task_t task){return auth.release(auth.cookie,c,task);}
 ~Fixture(){assert(!IORecursiveLockHaveLock(&s.gate));fixtureCleanup=true;while(s.direct_app_sessions){auto *r=s.direct_app_sessions;s.direct_app_sessions=r->next;dispose(r);}fixtureCleanup=false;}
};
int main(){unsigned controls=0;
 {Fixture f;Storage::ApplicationSession *out=nullptr;assert(f.s.reserveApplicationSession(f.a,f.ta,out)==kIOReturnBadArgument && !out);++controls;}
 for(unsigned mode=0;mode<5;++mode){Fixture f;Storage::ApplicationSession *out=nullptr;IORecursiveLockLock(&f.s.gate);
  if(mode==0)out=reinterpret_cast<Storage::ApplicationSession*>(1);
  task_t task=mode==1?nullptr:mode==2?kernel_task:mode==3?f.tb:f.ta;
  if(mode==4)f.s.direct_app_acquires=1;
  auto raw=f.s.reserveApplicationSession(f.a,task,out);assert(raw==(mode==4?kIOReturnExclusiveAccess:kIOReturnBadArgument));assert(!f.s.direct_app_sessions);IORecursiveLockUnlock(&f.s.gate);++controls;
 }
 {Fixture f;f.s.direct_app_acquires=f.s.direct_app_releases=UINT32_MAX;assert(f.acquire(f.a,f.ta)==kIOReturnExclusiveAccess && !f.s.direct_app_sessions);++controls;}
 {Fixture f;allocationFails=true;assert(f.acquire(f.a,f.ta)==kIOReturnNoMemory && !f.s.direct_app_active && f.s.direct_oob_epoch==4);allocationFails=false;++controls;}
 for(unsigned failure=0;failure<11;++failure){Fixture f;
  if(failure==0)f.s.stage=Stage::Other;
  if(failure==1)f.s.direct_app_publish_attempted=false;
  if(failure==2)f.s.direct_client_attempted=true;
  if(failure==3)f.s.host_ring=nullptr;
  if(failure==4)f.s.native_cx_gpu=nullptr;
  if(failure==5)f.s.host_gpu_start_gmu_resource=nullptr;
  if(failure==6)f.s.direct_oob_epoch=7;
  if(failure==7)f.ring.binding=false;
  if(failure==8)f.hfi.flags=126;
  if(failure==9)f.hfi.raw=1;
  if(failure==10)f.s.physicalHealthy=false;
  const auto freeBefore=frees.load();assert(f.acquire(f.a,f.ta)==kIOReturnNotReady);auto *record=f.s.direct_app_active;
  assert(record && record->client==&f.a && record->task==f.ta && record->phase==Storage::ApplicationSession::Phase::Failed && frees==freeBefore);
  assert(f.acquire(f.a,f.ta)==kIOReturnExclusiveAccess && f.s.direct_app_active==record);
  assert(f.release(f.a,f.ta)==kIOReturnNotReady && f.s.direct_app_active==record && frees==freeBefore);++controls;
 }
 {Fixture f;assert(f.acquire(f.a,f.ta)==0);auto *first=f.s.direct_app_active;assert(first->generation==1 && first->phase==Storage::ApplicationSession::Phase::Held && f.s.direct_app_acquires==1 && f.s.direct_app_releases==0 && f.s.direct_oob_epoch==6);
  assert(f.auth.check(&f.board,f.a,f.ta,f.ta,ZornGen7AppOperation26::Submit)==0);++controls;
  callingTask=f.tb;assert(f.auth.check(&f.board,f.a,f.ta,f.tb,ZornGen7AppOperation26::Submit)==kIOReturnNotReady && f.s.direct_app_active==first);++controls;
  assert(f.release(f.b,f.tb)==kIOReturnNotReady && f.s.direct_app_active==first);++controls;
  callingTask=f.ta;first->generation=0;assert(f.release(f.a,f.ta)==kIOReturnNotReady && f.s.direct_app_active==first);first->generation=1;++controls;
  callingTask=kernel_task;assert(f.release(f.a,f.ta)==0);assert(!f.s.direct_app_active && !f.s.direct_app_sessions && f.s.direct_app_acquires==f.s.direct_app_releases && f.s.direct_oob_epoch==4);++controls;
  callingTask=f.tb;assert(f.acquire(f.b,f.tb)==0 && f.s.direct_app_active->generation==2);auto *second=f.s.direct_app_active;
  assert(f.release(f.a,f.ta)==kIOReturnNotReady && f.s.direct_app_active==second);assert(f.release(f.b,f.tb)==0 && f.s.direct_app_releases==2);++controls;
 }
 {Fixture f;normalContext=false;assert(f.acquire(f.a,f.ta)==kIOReturnNotReady && !f.s.direct_app_active);normalContext=true;callingTask=kernel_task;assert(f.acquire(f.a,kernel_task)==kIOReturnNotReady && !f.s.direct_app_active);++controls;}
 {Fixture f;assert(f.acquire(f.a,f.ta)==0);const auto freesBefore=frees.load();f.s.physicalHealthy=false;assert(f.release(f.a,f.ta)==kIOReturnNotReady && f.s.direct_app_active && frees==freesBefore);++controls;}
 {Fixture f;constexpr unsigned count=12;IOUserClient clients[count];task_t tasks[count];IOReturn results[count]{};std::atomic<bool> go{false};std::vector<std::thread> threads;
  for(unsigned i=0;i<count;++i){tasks[i]=reinterpret_cast<void*>(uintptr_t(100+i));threads.emplace_back([&,i]{callingTask=tasks[i];while(!go.load())std::this_thread::yield();results[i]=f.acquire(clients[i],tasks[i]);});}
  go=true;for(auto &x:threads)x.join();unsigned winners=0,winner=0;
  for(unsigned i=0;i<count;++i){if(results[i]==0){++winners;winner=i;}else assert(results[i]==kIOReturnExclusiveAccess);}
  assert(winners==1 && f.s.direct_app_acquires==1 && f.s.direct_app_releases==0);callingTask=tasks[winner];assert(f.release(clients[winner],tasks[winner])==0);assert(!f.s.direct_app_sessions);++controls;
 }
 assert(liveRecords==0 && allocations==frees);
 printf("PASS %u actual board record/callback controls,12 concurrent acquisitions,normal retirement balances all fixture allocations;physical/Ring boundaries stubbed\n",controls);
}
'''
 if physical_split:
  prefix=prefix.replace('bool direct_client_attempted=false,physicalHealthy=true;','bool direct_client_attempted=false,physicalHealthy=true,direct_physical_held=false;')
  tests=tests.replace(' assert(liveRecords==0 && allocations==frees);',' {Fixture f;assert(!f.acquire(f.a,f.ta));f.s.direct_physical_held=true;assert(!f.release(f.a,f.ta)&&!f.s.direct_app_sessions&&f.s.direct_oob_epoch==6);++controls;}\n assert(liveRecords==0 && allocations==frees);')
 (O/'actual.cpp').write_text(prefix+tests)
 def run(n,args):
  environment=dict(os.environ);environment.update(TSAN_OPTIONS='symbolize=0',ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0')
  r=subprocess.run(args,capture_output=True,timeout=120,env=environment);(O/(n+'.stdout')).write_bytes(r.stdout);(O/(n+'.stderr')).write_bytes(r.stderr);(O/(n+'.command.json')).write_text(json.dumps(dict(arguments=args,exit=r.returncode,symbolization_disabled=True),indent=2)+'\n');assert not r.returncode,r.stderr.decode(errors='replace')[-4000:];return r.stdout.decode()
 run('compile',['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-pthread','-g','-fsanitize='+a.sanitizer,str(O/'actual.cpp'),'-o',str(O/'check')]);stdout=run('check',[str(O/'check')])
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();(O/'result.json').write_text(json.dumps(dict(passed=True,sanitizer=a.sanitizer,source=dict(path=str(S/'ZornGen7DarwinBoardOwner.cpp'),sha256=sha(S/'ZornGen7DarwinBoardOwner.cpp')),actual_record_helpers_and_three_callbacks_extracted=True,physical_window_predicate_byte_equal_after_explicit_metadata_expression_change=not physical_split,physical_window_predicate_matches_explicit_expected_owner_guard=True,stdout=stdout,scope='CPU metadata/lock/refusal/retirement and actual Board callback flow only;Ring and hardware predicates explicit fixtures,not application GPU authority or device qualification',physical_exclusivity_retained=True,host_failed_fixture_cleanup_not_device_recovery=True),indent=2)+'\n');print(stdout.strip())

if __name__=='__main__':main()

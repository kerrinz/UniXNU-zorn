#!/usr/bin/env python3
"""Exercise actual Ring operation/context flow;SMMU/drain/authority boundaries are explicit host fixtures."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess

def extract(t,start):
 a=t.index(start);b=t.index('{',a)+1;d=1
 while d:d+=(t[b]=='{')-(t[b]=='}');b+=1
 return t[a:b]

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--parent-source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sanitizer',choices=['address,undefined','thread'],default='address,undefined');a=p.parse_args();S=a.source_root.resolve();P=a.parent_source.resolve();O=a.out.resolve();O.mkdir();source=(S/'ZornGen7HostRing26.cpp').read_text();parent=(P/'ZornGen7HostRing26.cpp').read_text()
 names=['bool ZornGen7HostRing26::applicationOperationHeld','bool ZornGen7HostRing26::processExecutionHealthy','bool ZornGen7HostRing26::processConnectionHeld','bool ZornGen7HostRing26::applicationContextTransitionHeld','IOReturn ZornGen7HostRing26::enterApplicationContext','IOReturn ZornGen7HostRing26::leaveApplicationContext','IOReturn ZornGen7HostRing26::beginApplicationOperation','IOReturn ZornGen7HostRing26::finishApplicationOperation','bool ZornGen7HostRing26::processTransitionHeldForDomain','IOReturn ZornGen7HostRing26::transitionProcessTables','IOReturn ZornGen7HostRing26::openApplicationProcess','IOReturn ZornGen7HostRing26::closeApplicationProcess']
 methods='\n'.join(extract(source,n) for n in names)
 assert extract(source,'IOReturn ZornGen7HostRing26::quiesceKernelIo')==extract(parent,'IOReturn ZornGen7HostRing26::quiesceKernelIo')
 for n in ['ZornGen7HostGpuTables26.cpp','ZornGen7SmmuDomain26.cpp','ZornGen7DarwinBoardOwner.cpp','ZornGen7DirectHfi26.cpp','ZornGen7AppExecution26.cpp','direct-runtime/ZornGen7AppIo26.cpp','direct-runtime/ZornGen7DirectVm26.cpp','direct-runtime/ZornGen7DirectSubmit26.cpp']:
  assert (S/n).read_bytes()==(P/n).read_bytes(),n
 begin=extract(source,names[6]);assert begin.index('IOLockLock(s.appSerial)')<begin.index('s.lockIssuer()')<begin.index('checkApplicationExecution(')<begin.index('enterApplicationContext(')
 finish=extract(source,names[7]);assert finish.index('if(!matches)')<finish.index('leaveApplicationContext(')<finish.index('IOLockUnlock(s.appSerial)')<finish.index('execution.release()')
 assert 's.appOperationProcess=nullptr' in extract(source,names[-1])
 match=extract((S/'direct-runtime/ZornGen7AppIo26.cpp').read_text(),'bool ZornGen7AppIoClient26::matchesOwnedSession(')
 prefix=r'''
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <mutex>
#include <thread>
#include <vector>
#include <algorithm>
using IOReturn=int;using task_t=void*;using thread_t=void*;constexpr thread_t THREAD_NULL=nullptr;constexpr task_t TASK_NULL=nullptr;
static task_t kernel_task=reinterpret_cast<void*>(1);static thread_local task_t callerTask=reinterpret_cast<void*>(2);
static thread_t current_thread(){static thread_local int id;return &id;}static task_t current_task(){return callerTask;}
static thread_local bool normalContext=true;static bool normal(){return normalContext;}
constexpr IOReturn kIOReturnSuccess=0,kIOReturnNotReady=1,kIOReturnBadArgument=2,kIOReturnBusy=3,kIOReturnTimeout=4,kIOReturnIOError=5,kIOReturnNotPermitted=6,kIOReturnNoMemory=7,kIOReturnUnsupported=8;
struct OSObject{std::atomic<int>refs{1};void retain(){assert(refs.fetch_add(1)>0);}void release(){assert(refs.fetch_sub(1)>1);}};
struct IOService{};struct IOUserClient:OSObject{IOService*provider=nullptr;IOService*getProvider()const{return provider;}};
struct Lock{std::mutex mutex;std::atomic<thread_t>owner{THREAD_NULL};};
static void IOLockLock(Lock*p){assert(p->owner.load()!=current_thread());p->mutex.lock();p->owner=current_thread();}
static void IOLockUnlock(Lock*p){assert(p->owner.load()==current_thread());p->owner=THREAD_NULL;p->mutex.unlock();}
static bool IORecursiveLockHaveLock(Lock*p){return p&&p->owner.load()==current_thread();}
static constexpr uint64_t NSEC_PER_MSEC=1000000;static void clock_interval_to_deadline(unsigned x,uint64_t y,uint64_t*d){*d=x*y;}
static void zorn26_application_prepare_event(uintptr_t,uint32_t,uint32_t,uint32_t){}static void zorn26_client_close_reset242(){}static void zorn26_client_event240(unsigned){}
enum class ZornGen7AppOperation26:unsigned{PrepareTables,Map,Submit,Wait,CpuView,Close,OobAcquire,OobRelease,Timestamp};
enum class ZornGen7ProcessTableOperation26:unsigned{Prepare,Select,AttachVm,RestoreKernel,DetachVm,RetireDetached,DiscardNeverInstalled};
class ZornGen7HostRing26;class ZornGen7SmmuDomain26;
static thread_local bool*faultAfterOutstanding=nullptr;
struct Queue {unsigned count=0,resets=0;bool poison=false;unsigned outstanding()const{if(faultAfterOutstanding){*faultAfterOutstanding=true;faultAfterOutstanding=nullptr;}return count;}bool poisoned()const{return poison;}void requestContextReset(){++resets;}};
struct ZornGen7ProcessTables26 {
 ZornGen7HostRing26*ringOwner_=nullptr;ZornGen7SmmuDomain26*domain_=nullptr;ZornGen7ProcessTables26*ringNext_=nullptr;IOUserClient*clientOwner_=nullptr;task_t clientTask_=TASK_NULL;
 bool clientOpen_=true,clientClosed_=false,vmAttached_=true,vmDetached_=false,retired=false,asidHeld_=true;
 unsigned asid_=42,liveMappings=3;struct{bool detached=true,poisoned=false;}state_;
 struct Vm{bool pending=false,poison=false;bool hasPendingSubmissionResources()const{return pending;}bool poisoned()const{return poison;}}vm_;
 struct ClientState{Queue submit;}clientState;ClientState*clientState_=&clientState;
};
class ZornGen7SmmuDomain26 {
public:bool fault=false;IOReturn transitionRaw=0;bool partial=false;unsigned transitions=0;std::vector<ZornGen7ProcessTableOperation26>operations;
 bool faulted()const{return fault;}
 IOReturn transitionHostProcessTables(ZornGen7HostRing26&,ZornGen7ProcessTableOperation26,ZornGen7ProcessTables26*&,unsigned,size_t);
};
class ZornGen7AppIoClient26:public IOUserClient {
public:ZornGen7HostRing26*owner_=nullptr;IOService*service_=nullptr;task_t openingTask_=TASK_NULL;
 bool live_=true,attempted_=true,pinned_=true,closing_=false;thread_t closingThread_=THREAD_NULL;IOReturn viewError_=0;void*serial_=reinterpret_cast<void*>(1);void*views_=reinterpret_cast<void*>(1);
 bool matchesOwnedSession(const ZornGen7HostRing26&,const IOService*,task_t,bool)const;
};
#define OSDynamicCast(T,P) static_cast<T*>(P)
class ZornGen7AppExecution26:public OSObject {public:IOUserClient*client_=nullptr;task_t task_=TASK_NULL;};
class ZornGen7HostRing26 {
public:
 Lock issuer,operationMutex,driverGate;IOService service;ZornGen7AppIoClient26 client,foreign;ZornGen7AppExecution26 execution;ZornGen7SmmuDomain26 domain;ZornGen7ProcessTables26 process;
 struct Storage{
  Lock&gate;Lock&issuer;Lock*appSerial=nullptr;thread_t appSerialThread=THREAD_NULL;std::atomic<thread_t>issuerThread{THREAD_NULL};
  ZornGen7AppExecution26*appExecution=nullptr;bool appOperationPending=false,appExecutionPending=false,appOobTransition=false,appOobActive=true,kernelIoActive=false;
  thread_t appOperationThread=THREAD_NULL;ZornGen7AppOperation26 appOperationKind=ZornGen7AppOperation26::PrepareTables;bool appFenceWaitExpired=false;
  ZornGen7ProcessTables26*appOperationProcess=nullptr,*appContextTarget=nullptr;thread_t appContextThread=THREAD_NULL;
  uint32_t stopped=0;struct Irq{bool halt=false;unsigned masks=0;bool halted()const{return halt;}void stopAndMask(){halt=true;++masks;}}irq,gmu;
  ZornGen7SmmuDomain26&domain;bool hfiHalted()const{return false;}void*hfi=nullptr;
  bool applicationIoPublishAttempted=true;IOService*applicationIoService=nullptr;IOService*kernelIoService=nullptr;bool kernelIoAttempted=false;
  IOUserClient*kernelIoConnection=nullptr;bool kernelTaskActive=false,kernelIoClosing=false,kernelIoClosed=false;thread_t kernelTaskThread=THREAD_NULL;
  ZornGen7ProcessTables26*processClients=nullptr,*processSelected=nullptr,*nativeProcessTableLease=nullptr,*kernelProcess=nullptr;bool kernelProcessReady=false,nativeTableLease=false;
  Queue native,runtimeSubmit;uint64_t deadline=0;thread_t processTransitionThread=THREAD_NULL;ZornGen7ProcessTableOperation26 processTransitionOperation=ZornGen7ProcessTableOperation26::Prepare;
  struct{bool busy_valid=true;uint32_t busy=0,status=0,irq=0,hwfault=0,rptr=0,wptr=0;}ring;
  struct{unsigned input_bits=48;}logical;size_t runtimeCapacity=4096;
  ZornGen7ProcessTables26*prepareOutput=nullptr;
  void lockIssuer(){IOLockLock(&issuer);issuerThread=current_thread();}
  void unlockIssuer(){assert(issuerHeld());issuerThread=THREAD_NULL;IOLockUnlock(&issuer);}
  bool issuerHeld()const{return issuerThread.load()==current_thread();}
 }s{driverGate,issuer,nullptr,THREAD_NULL,{},nullptr,false,false,false,true,false,THREAD_NULL,ZornGen7AppOperation26::PrepareTables,false,nullptr,nullptr,THREAD_NULL,0,{},{},domain};
 Storage*storage_=&s;bool healthy=true,physicalHeld=true;IOReturn authorityRaw=0,drainRaw=0,openRaw=0,closeRaw=0;unsigned drains=0,authorityCalls=0;bool authoritySawWholeMutex=false;
 ZornGen7HostRing26(){s.appSerial=&operationMutex;s.appExecution=&execution;s.applicationIoService=&service;client.owner_=this;client.service_=&service;client.provider=&service;client.openingTask_=callerTask;foreign=/*NONCOPY*/foreign;
  execution.client_=&client;execution.task_=callerTask;process.ringOwner_=this;process.domain_=&domain;process.clientOwner_=&client;process.clientTask_=callerTask;s.processClients=&process;}
 bool bootstrapHealthy()const{return healthy&&!__atomic_load_n(&s.stopped,__ATOMIC_ACQUIRE)&&!s.irq.halted()&&!s.gmu.halted()&&!domain.faulted();}
 bool kernelClientExecutionHealthy()const{return false;}
 bool applicationOobHeldForTransport(const ZornGen7AppExecution26&)const{return physicalHeld;}
 IOReturn checkApplicationExecution(IOUserClient&,ZornGen7AppExecution26&,ZornGen7AppOperation26){assert(!s.issuerHeld()&&!IORecursiveLockHaveLock(&s.gate));++authorityCalls;authoritySawWholeMutex=operationMutex.owner.load()==current_thread();return authorityRaw;}
 bool applicationOperationHeld()const;bool processExecutionHealthy()const;bool processConnectionHeld(IOUserClient&)const;
 bool applicationContextTransitionHeld(ZornGen7ProcessTableOperation26)const;
 IOReturn enterApplicationContext(IOUserClient&,ZornGen7AppExecution26&);IOReturn leaveApplicationContext(ZornGen7AppExecution26&,bool);
 IOReturn beginApplicationOperation(IOUserClient&,ZornGen7AppOperation26,ZornGen7AppExecution26*&);IOReturn finishApplicationOperation(ZornGen7AppExecution26&,IOReturn);
 bool processTransitionHeldForDomain(const ZornGen7SmmuDomain26&)const;
 IOReturn transitionProcessTables(IOUserClient&,ZornGen7ProcessTableOperation26,ZornGen7ProcessTables26*&,unsigned,size_t);
 IOReturn openApplicationProcess(IOUserClient&,ZornGen7AppExecution26&,ZornGen7ProcessTables26*&);
 IOReturn closeApplicationProcess(IOUserClient&,ZornGen7AppExecution26&,ZornGen7ProcessTables26*&);
 IOReturn quiesceKernelIo(){assert(s.issuerHeld()&&processExecutionHealthy());++drains;if(drainRaw)return drainRaw;
  for(auto*p=s.processClients;p;p=p->ringNext_)if(p!=s.processSelected&&p->clientState_&&p->clientState_->submit.outstanding())return kIOReturnNotReady;
  s.native.count=0;s.runtimeSubmit.count=0;if(s.processSelected){s.processSelected->clientState.submit.count=0;s.processSelected->vm_.pending=false;}return 0;}
 IOReturn openProcessClient(IOUserClient&c,ZornGen7ProcessTables26&p,task_t task){if(openRaw)return openRaw;p.clientOwner_=&c;p.clientTask_=task;p.clientOpen_=true;p.clientClosed_=false;return 0;}
 IOReturn closeProcessClient(IOUserClient&,ZornGen7ProcessTables26&p){if(closeRaw)return closeRaw;p.clientOpen_=false;p.clientClosed_=true;p.liveMappings=0;p.clientState_=nullptr;return 0;}
 void closing(){client.closing_=true;client.closingThread_=current_thread();}
 void expiry(){s.lockIssuer();s.appFenceWaitExpired=true;s.unlockIssuer();}
 void pendingSelected(){s.processSelected=&process;process.state_.detached=false;s.native.count=1;process.clientState.submit.count=1;process.vm_.pending=true;}
 ~ZornGen7HostRing26(){assert(execution.refs==1&&!operationMutex.owner.load()&&!s.issuerHeld());}
};
ACTUAL_MATCH
ACTUAL_METHODS
IOReturn ZornGen7SmmuDomain26::transitionHostProcessTables(ZornGen7HostRing26&r,ZornGen7ProcessTableOperation26 op,ZornGen7ProcessTables26*&p,unsigned,size_t){
 assert(r.s.issuerHeld()&&r.processTransitionHeldForDomain(*this));++transitions;operations.push_back(op);
 if(transitionRaw){if(partial&&p)p->state_.poisoned=true;return transitionRaw;}
 if(op==ZornGen7ProcessTableOperation26::Prepare){p=r.s.prepareOutput;assert(p);}
 else if(op==ZornGen7ProcessTableOperation26::Select){assert(p&&!r.s.processSelected);p->state_.detached=false;}
 else if(op==ZornGen7ProcessTableOperation26::RestoreKernel){assert(p==r.s.processSelected);p->state_.detached=true;}
 else if(op==ZornGen7ProcessTableOperation26::AttachVm){p->vmAttached_=true;p->vmDetached_=false;}
 else if(op==ZornGen7ProcessTableOperation26::DetachVm){p->vmAttached_=false;p->vmDetached_=true;}
 else if(op==ZornGen7ProcessTableOperation26::RetireDetached){assert(p->state_.detached&&p->vmDetached_&&p->clientClosed_);p->asidHeld_=false;p->retired=true;p=nullptr;}
 return 0;
}
'''.replace('foreign=/*NONCOPY*/foreign;','').replace('ACTUAL_MATCH',match).replace('ACTUAL_METHODS',methods)
 tests=r'''
int main(){unsigned controls=0;
 {ZornGen7HostRing26 f;for(unsigned i=0;i<3;++i){ZornGen7AppExecution26*scope=nullptr;assert(!f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Map,scope)&&scope==&f.execution&&f.s.processSelected==&f.process);assert(f.authoritySawWholeMutex);assert(!f.finishApplicationOperation(*scope,0)&&!f.s.processSelected&&f.process.state_.detached&&f.process.asidHeld_&&f.process.liveMappings==3);}assert(f.domain.transitions==6&&f.drains==6);++controls;}
 {ZornGen7HostRing26 f;f.s.processClients=nullptr;f.s.prepareOutput=&f.process;f.process.clientOwner_=nullptr;f.process.clientTask_=TASK_NULL;f.process.clientOpen_=false;f.process.vmAttached_=false;ZornGen7ProcessTables26*p=nullptr;assert(!f.openApplicationProcess(f.client,f.execution,p)&&p==&f.process&&!f.s.processSelected&&p->state_.detached);assert(f.domain.operations.back()==ZornGen7ProcessTableOperation26::RestoreKernel);++controls;}
 {ZornGen7HostRing26 f;f.closing();auto*p=&f.process;assert(!f.closeApplicationProcess(f.client,f.execution,p)&&!p&&!f.s.processClients&&!f.s.processSelected&&f.process.retired&&!f.process.asidHeld_&&f.process.liveMappings==0);++controls;}
 {ZornGen7HostRing26 f;f.pendingSelected();ZornGen7AppExecution26*scope=nullptr;assert(!f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Wait,scope));f.expiry();assert(f.finishApplicationOperation(*scope,kIOReturnTimeout)==kIOReturnTimeout&&!f.s.stopped&&f.s.processSelected==&f.process&&!f.process.state_.detached&&f.domain.transitions==0);f.s.native.count=0;f.process.clientState.submit.count=0;f.process.vm_.pending=false;scope=nullptr;assert(!f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Wait,scope));assert(!f.finishApplicationOperation(*scope,0)&&!f.s.processSelected&&f.process.state_.detached);++controls;}
 {ZornGen7HostRing26 f;f.pendingSelected();ZornGen7AppExecution26*scope=nullptr;assert(!f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Wait,scope));f.expiry();faultAfterOutstanding=&f.domain.fault;auto raw=f.finishApplicationOperation(*scope,kIOReturnTimeout);
  if(raw!=kIOReturnNotReady||!f.s.stopped||f.s.processSelected!=&f.process||f.process.liveMappings!=3){std::puts("REPRO256 late fault was incorrectly retained as healthy wait expiry");return 73;}++controls;}
 {ZornGen7HostRing26 f;ZornGen7AppExecution26*scope=nullptr;assert(!f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Submit,scope));f.s.native.count=1;f.process.clientState.submit.count=1;assert(!f.finishApplicationOperation(*scope,0)&&!f.s.processSelected&&!f.s.native.count);++controls;}
 for(unsigned mode=0;mode<9;++mode){ZornGen7HostRing26 f;if(mode==0)f.process.clientOwner_=&f.foreign;if(mode==1)f.process.clientTask_=kernel_task;if(mode==2)f.process.clientClosed_=true;if(mode==3)f.process.vmDetached_=true;if(mode==4)f.process.state_.poisoned=true;if(mode==5)f.process.ringOwner_=nullptr;if(mode==6)f.process.domain_=nullptr;if(mode==7)f.process.state_.detached=false;if(mode==8)f.physicalHeld=false;ZornGen7AppExecution26*scope=nullptr;assert(f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Map,scope)&&!scope&&!f.domain.transitions&&f.process.asidHeld_&&f.process.liveMappings==3);++controls;}
 for(IOReturn raw:{kIOReturnIOError,kIOReturnNotReady,kIOReturnNotPermitted,kIOReturnTimeout}){ZornGen7HostRing26 f;ZornGen7AppExecution26*scope=nullptr;assert(!f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Submit,scope));assert(f.finishApplicationOperation(*scope,raw)&&f.s.stopped&&f.s.processSelected==&f.process&&f.domain.transitions==1&&f.process.liveMappings==3);++controls;}
 for(unsigned mode=0;mode<2;++mode){ZornGen7HostRing26 f;ZornGen7AppExecution26*scope=nullptr;assert(!f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Map,scope));if(mode==0)f.drainRaw=kIOReturnTimeout;else{f.domain.transitionRaw=kIOReturnIOError;f.domain.partial=true;}assert(f.finishApplicationOperation(*scope,kIOReturnBadArgument)&&f.s.stopped&&f.s.processSelected==&f.process&&f.process.asidHeld_&&f.process.liveMappings==3);++controls;}
 {ZornGen7HostRing26 f;ZornGen7AppExecution26*scope=nullptr;assert(!f.beginApplicationOperation(f.client,ZornGen7AppOperation26::CpuView,scope));assert(f.finishApplicationOperation(*scope,kIOReturnNoMemory)==kIOReturnNoMemory&&!f.s.stopped&&!f.s.processSelected);++controls;}
 {ZornGen7HostRing26 f;ZornGen7ProcessTables26 other;other.domain_=&f.domain;other.ringOwner_=&f;other.clientOwner_=&f.foreign;other.clientTask_=reinterpret_cast<void*>(3);other.state_.detached=false;f.s.processSelected=&other;ZornGen7AppExecution26*scope=nullptr;assert(f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Map,scope)==kIOReturnBusy&&!scope&&!f.s.stopped&&f.s.processSelected==&other&&!f.domain.transitions);++controls;}
 {ZornGen7HostRing26 f;f.authorityRaw=kIOReturnNotPermitted;ZornGen7AppExecution26*scope=nullptr;assert(f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Submit,scope)==kIOReturnNotPermitted&&!scope&&f.s.stopped&&!f.domain.transitions);++controls;}
 {ZornGen7HostRing26 f;callerTask=reinterpret_cast<void*>(9);ZornGen7AppExecution26*scope=nullptr;assert(f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Map,scope)&&!scope&&!f.domain.transitions&&f.process.liveMappings==3);callerTask=reinterpret_cast<void*>(2);++controls;}
 {ZornGen7HostRing26 f;f.drainRaw=kIOReturnTimeout;ZornGen7AppExecution26*scope=nullptr;assert(f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Map,scope)==kIOReturnTimeout&&!scope&&f.s.stopped&&!f.domain.transitions&&f.process.state_.detached&&f.process.asidHeld_);++controls;}
 {ZornGen7HostRing26 f;f.closing();f.closeRaw=kIOReturnIOError;auto*p=&f.process;assert(f.closeApplicationProcess(f.client,f.execution,p)==kIOReturnIOError&&p==&f.process&&f.s.processSelected==p&&p->liveMappings==3&&p->asidHeld_&&!p->retired&&f.s.stopped);++controls;}
 // Two pre-created contexts exercise the actual switch flow only. The fixture
 // supplies the declared authority owner;real service/Board multiclient
 // admission remains exclusive and is NOT qualified by this control.
 {ZornGen7HostRing26 f;ZornGen7AppIoClient26 second;ZornGen7AppExecution26 execution2;ZornGen7ProcessTables26 process2;
  const auto task2=reinterpret_cast<void*>(3);second.owner_=&f;second.service_=&f.service;second.provider=&f.service;second.openingTask_=task2;execution2.client_=&second;execution2.task_=task2;
  process2.ringOwner_=&f;process2.domain_=&f.domain;process2.clientOwner_=&second;process2.clientTask_=task2;process2.asid_=43;process2.ringNext_=&f.process;f.s.processClients=&process2;
  for(unsigned i=0;i<6;++i){const bool next=i&1;callerTask=next?task2:f.execution.task_;f.s.appExecution=next?&execution2:&f.execution;auto&client=next?second:f.client;auto*expected=next?&process2:&f.process;ZornGen7AppExecution26*scope=nullptr;
   assert(!f.beginApplicationOperation(client,ZornGen7AppOperation26::Map,scope)&&f.s.processSelected==expected);assert(!f.finishApplicationOperation(*scope,0)&&!f.s.processSelected&&expected->state_.detached);}
  assert(f.process.asid_==42&&process2.asid_==43&&f.process.asidHeld_&&process2.asidHeld_&&f.process.liveMappings==3&&process2.liveMappings==3&&execution2.refs==1);callerTask=reinterpret_cast<void*>(2);++controls;
 }
 {ZornGen7HostRing26 f;ZornGen7AppExecution26*scope=nullptr;assert(!f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Map,scope));ZornGen7AppExecution26*recursive=nullptr;assert(f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Map,recursive)==kIOReturnNotReady&&!recursive);IOReturn result=0;std::thread outsider([&]{result=f.finishApplicationOperation(*scope,0);});outsider.join();assert(result==kIOReturnNotReady&&f.s.appOperationPending&&f.execution.refs==2&&!f.s.stopped);assert(!f.finishApplicationOperation(*scope,0));++controls;}
 {ZornGen7HostRing26 f;std::atomic<unsigned>active{0},maximum{0},done{0};std::vector<std::thread>threads;for(unsigned i=0;i<12;++i)threads.emplace_back([&]{for(unsigned n=0;n<4;++n){ZornGen7AppExecution26*scope=nullptr;assert(!f.beginApplicationOperation(f.client,ZornGen7AppOperation26::CpuView,scope));auto a=++active;maximum=std::max(maximum.load(),a);std::this_thread::yield();--active;assert(!f.finishApplicationOperation(*scope,0));++done;}});for(auto&t:threads)t.join();assert(done==48&&maximum==1&&f.domain.transitions==96&&!f.s.processSelected);++controls;}
 std::printf("PASS256 actual operation/context controls=%u;48 concurrent operations serialize;host SMMU/drain/authority boundaries explicit\n",controls);
}
'''
 cpp=O/'hostcheck.cpp';cpp.write_text(prefix+tests);env=dict(os.environ);env.update(TSAN_OPTIONS='symbolize=0',ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0');args=['/usr/bin/clang++','-std=c++17','-O1','-g','-fno-omit-frame-pointer','-fsanitize='+a.sanitizer,str(cpp),'-o',str(O/'hostcheck')];runs=[]
 for cmd in [args,[str(O/'hostcheck')]]:
  z=subprocess.run(cmd,capture_output=True,text=True,timeout=120,env=env);runs.append(dict(arguments=cmd,exit=z.returncode,stdout=z.stdout,stderr=z.stderr,symbolization_disabled=True));(O/'commands.json').write_text(json.dumps(runs,indent=2)+'\n');assert not z.returncode,z.stderr[-5000:]
 pin=lambda p:dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest());result=dict(passed=True,sanitizer=a.sanitizer,source=pin(S/'ZornGen7HostRing26.cpp'),header=pin(S/'ZornGen7HostRing26.h'),test_tool=pin(Path(__file__)),actual_scope_context_transition_methods_compiled=True,actual_client_task_match_method_compiled=True,whole_operation_mutex_includes_foreign_check_context_entry_exit=True,healthy_wait_expiry_preserves_live_selected_context=True,wrong_scope_cannot_unlock_active_owner=True,backend_and_real_drain_source_unchanged=True,MMIO_SMMU_drain_authority_and_client_body_boundaries_are_host_fixtures=True,hardware_qualified=False,phone_access=False,output=runs[-1]['stdout']);(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result['output'],end='')
if __name__=='__main__':main()

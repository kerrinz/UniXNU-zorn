#!/usr/bin/env python3
"""Exercise actual shared-member lookup and Ring operation/context flow;native boundaries are explicit fixtures."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess

def extract(t,start):
 a=t.index(start);b=t.index('{',a)+1;d=1
 while d:d+=(t[b]=='{')-(t[b]=='}');b+=1
 return t[a:b]

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--parent-source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sanitizer',choices=['address,undefined','thread'],default='address,undefined');a=p.parse_args();S=a.source_root.resolve();P=a.parent_source.resolve();O=a.out.resolve();O.mkdir();source=(S/'ZornGen7HostRing26.cpp').read_text();parent=(P/'ZornGen7HostRing26.cpp').read_text()
 names=['bool ZornGen7HostRing26::applicationOperationHeld','bool ZornGen7HostRing26::processExecutionHealthy','bool ZornGen7HostRing26::processConnectionHeld','bool ZornGen7HostRing26::applicationContextTransitionHeld','IOReturn ZornGen7HostRing26::enterApplicationContext','IOReturn ZornGen7HostRing26::leaveApplicationContext','IOReturn ZornGen7HostRing26::beginApplicationOperation','IOReturn ZornGen7HostRing26::finishApplicationOperation','bool ZornGen7HostRing26::processTransitionHeldForDomain','IOReturn ZornGen7HostRing26::transitionProcessTables','IOReturn ZornGen7HostRing26::openApplicationProcess','IOReturn ZornGen7HostRing26::closeApplicationProcess']
 names += ['bool ZornGen7HostRing26::physicalContextIdentity','bool ZornGen7HostRing26::physicalContextHeld','bool ZornGen7HostRing26::nativePhysicalContextBinding','IOReturn ZornGen7HostRing26::restoreCompletedApplicationContext','bool ZornGen7HostRing26::nativeProcessContextHeldForDomain','bool ZornGen7HostRing26::processTransitionArgumentsHeld']
 methods='\n'.join(extract(source,n) for n in names)
 assert 'waitAll(&clock,waitBudgetUs,pendingFence)' in extract(source,'IOReturn ZornGen7HostRing26::quiesceKernelIo')
 for n in ['ZornGen7HostGpuTables26.cpp','ZornGen7DirectHfi26.cpp','direct-runtime/ZornGen7DirectVm26.cpp','direct-runtime/ZornGen7DirectClient26.cpp']:
  assert (S/n).read_bytes()==(P/n).read_bytes(),n
 begin=extract(source,names[6]);assert begin.index('IOLockLock(s.appSerial)')<begin.index('s.lockIssuer()')<begin.index('checkApplicationExecution(')<begin.index('enterApplicationContext(')
 finish=extract(source,names[7]);assert finish.index('if(!matches)')<finish.index('leaveApplicationContext(')<finish.index('IOLockUnlock(s.appSerial)')<finish.index('execution.release()')
 assert 's.appOperationProcess=nullptr' in extract(source,'IOReturn ZornGen7HostRing26::closeApplicationProcess')
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
 IOReturn enterApplicationContext(IOUserClient&,ZornGen7AppExecution26&,bool *pendingFence=nullptr);IOReturn leaveApplicationContext(ZornGen7AppExecution26&,bool);
 IOReturn beginApplicationOperation(IOUserClient&,ZornGen7AppOperation26,ZornGen7AppExecution26*&,bool *pendingFence=nullptr,bool selectContext=true);IOReturn finishApplicationOperation(ZornGen7AppExecution26&,IOReturn);
 bool processTransitionHeldForDomain(const ZornGen7SmmuDomain26&)const;
 IOReturn transitionProcessTables(IOUserClient&,ZornGen7ProcessTableOperation26,ZornGen7ProcessTables26*&,unsigned,size_t);
 IOReturn openApplicationProcess(IOUserClient&,ZornGen7AppExecution26&,ZornGen7ProcessTables26*&);
 IOReturn closeApplicationProcess(IOUserClient&,ZornGen7AppExecution26&,ZornGen7ProcessTables26*&,bool *pendingFence=nullptr);
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

 # Actual257 membership/ownership methods replace no target implementation.
 physical=(S/'ZornGen7PhysicalOob26.h').read_text()
 lease=extract(physical,'    struct Lease {')+';'
 owns=extract(physical,'    bool owns(')
 physicalClass='class ZornGen7PhysicalOob26 {public:\n'+lease+'\nOSObject transport,maps;Lease value;Lease *active_=&value;uint64_t generation_=1;ZornGen7PhysicalOob26(){value.physical=this;value.transport=&transport;value.registerMaps=&maps;value.generation=1;}\n'+owns+'\n};\n'
 prefix=prefix.replace('class ZornGen7AppExecution26:public OSObject {public:',physicalClass+'class ZornGen7AppExecution26:public OSObject {public:ZornGen7HostRing26*ring_=nullptr;OSObject*maps_=nullptr;ZornGen7AppExecution26*ringNext_=nullptr;bool oobMemberHeld_=true,oobMemberReleased_=false;ZornGen7PhysicalOob26::Lease*oob_=nullptr;')
 helpers='\n'.join(extract(source,n) for n in ['    bool appSerialHeld() const','    ZornGen7AppExecution26 *applicationMember(','    bool ownsExecution(','    bool applicationQuiescent() const'])
 prefix=prefix.replace('ZornGen7ProcessTables26*prepareOutput=nullptr;', 'ZornGen7ProcessTables26*prepareOutput=nullptr;ZornGen7AppExecution26*appExecutions=nullptr;ZornGen7PhysicalOob26 physicalOob;OSObject&maps=physicalOob.maps;ZornGen7ProcessTables26::Vm runtimeVm;unsigned nativeTableAcquires=0,nativeTableReleases=0,nativeProcessTableAcquires=0,nativeProcessTableReleases=0;\n'+helpers)
 prefix=prefix.replace('s.appExecution=&execution;s.applicationIoService=', 's.appExecutions=&execution;s.appExecution=nullptr;execution.ring_=this;execution.maps_=&s.maps;execution.oob_=&s.physicalOob.value;s.applicationIoService=')

 # The real Domain change is an argument restriction only;all real MMIO,
 # window/fault/stream/TTBR/TLBSYNC/readback backend remains byte-identical.
 oldDomain=(P/'ZornGen7SmmuDomain26.cpp').read_text()
 expected=oldDomain
 assert (S/'ZornGen7SmmuDomain26.cpp').read_text()==expected
 prefix=prefix.replace('bool clientOpen_=true,clientClosed_=false,vmAttached_=true,vmDetached_=false,retired=false,asidHeld_=true;', 'bool clientOpen_=true,clientClosed_=false,vmAttached_=true,vmDetached_=false,retired=false,asidHeld_=true,submitAttached_=true,clientOpenAttempted_=true;')
 prefix=prefix.replace('class ZornGen7PhysicalOob26 {public:', 'class ZornGen7DirectHfi26:public OSObject{public:bool physicalOobHeld(const ZornGen7HostRing26&)const;};\nclass ZornGen7PhysicalOob26 {public:',1)
 prefix=prefix.replace('OSObject transport,maps;', 'ZornGen7DirectHfi26 transport;OSObject maps;',1)
 prefix=prefix.replace('value.generation=1;', 'value.generation=1;value.owner=&transport;value.attempted=value.requestReturned=value.ackObserved=value.ackCleared=value.gxOn=true;',1)
 forTransport=extract(physical,'    Lease *forTransport(')
 prefix=prefix.replace(owns+'\n};',owns+'\n'+forTransport+'\n};',1)
 prefix=prefix.replace('bool oobMemberHeld_=true,oobMemberReleased_=false;', 'bool oobMemberHeld_=true,oobMemberReleased_=false,pinned_=true;enum class Phase{Held,Failed};Phase phase_=Phase::Held;',1)
 prefix=prefix.replace('ZornGen7AppExecution26*appExecutions=nullptr;',r"""ZornGen7ProcessTables26*physicalContextTarget=nullptr;thread_t physicalContextThread=THREAD_NULL;uint64_t physicalContextGeneration=0;bool physicalContextAuthorized=false,physicalContextRestoring=false;
  struct PhysicalAuthority{void*cookie=nullptr;IOReturn(*physicalContextCheck)(void*,ZornGen7HostRing26&,uint64_t)=nullptr;}physicalAuthority;
  OSObject*physicalAuthorityOwner=reinterpret_cast<OSObject*>(1);bool physicalAuthorityHeld=true,physicalAuthorityPending=false,physicalAuthorityReleasing=false;
  ZornGen7AppExecution26*appExecutions=nullptr;""",1)
 prefix=prefix.replace('OSObject&maps=physicalOob.maps;', 'OSObject&maps=physicalOob.maps;OSObject&hfiOwner=physicalOob.transport;',1)
 prefix=prefix.replace(' Storage*storage_=&s;bool healthy=', ' static IOReturn contextCheck(void*cookie,ZornGen7HostRing26&r,uint64_t generation){assert(cookie==&r&&!r.s.issuerHeld());++r.contextChecks;IOLockLock(&r.driverGate);const bool held=r.contextResources&&r.refuseContextAt!=r.contextChecks&&r.nativePhysicalContextBinding(generation);IOLockUnlock(&r.driverGate);return held?0:kIOReturnNotReady;}\n unsigned contextChecks=0,refuseContextAt=0;bool contextResources=true,pendingOnPoll=false,pollFault=false;\n Storage*storage_=&s;bool healthy=',1)
 prefix=prefix.replace('s.appSerial=&operationMutex;', 's.physicalAuthority.cookie=this;s.physicalAuthority.physicalContextCheck=contextCheck;s.physicalAuthorityOwner=&s.physicalOob.transport;s.appSerial=&operationMutex;',1)
 prefix=prefix.replace(' bool applicationOperationHeld()const;', r""" bool physicalContextIdentity()const;bool physicalContextHeld()const;bool nativePhysicalContextBinding(uint64_t)const;IOReturn restoreCompletedApplicationContext(bool *pendingFence=nullptr);
 bool nativeProcessContextHeldForDomain(const ZornGen7SmmuDomain26&,const ZornGen7ProcessTables26&)const;
 bool processTransitionArgumentsHeld(const ZornGen7SmmuDomain26&,ZornGen7ProcessTableOperation26,const ZornGen7ProcessTables26*)const;
 bool applicationOperationHeld()const;""",1)
 prefix=prefix.replace('IOReturn quiesceKernelIo(){assert', 'IOReturn quiesceKernelIo(uint32_t budget=1000000,bool*pending=nullptr){if(pending)*pending=false;assert',1)
 prefix=prefix.replace('++drains;if(drainRaw)', '++drains;if(budget==0&&pendingOnPoll){if(pending)*pending=true;if(pollFault)domain.fault=true;return kIOReturnTimeout;}if(drainRaw)',1)
 prefix=prefix.replace('ACTUAL_METHODS','ACTUAL_METHODS')
 # Insert the declared physical observation boundary after the complete Root.
 pos=prefix.index('bool ZornGen7AppIoClient26::matchesOwnedSession(')
 prefix=prefix[:pos]+'bool ZornGen7DirectHfi26::physicalOobHeld(const ZornGen7HostRing26&r)const{return r.physicalHeld;}\n'+prefix[pos:]
 prefix=prefix.replace('assert(r.s.issuerHeld()&&r.processTransitionHeldForDomain(*this));', 'assert(r.s.issuerHeld()&&r.processTransitionArgumentsHeld(*this,op,p));if(r.s.physicalContextTarget){assert(op==ZornGen7ProcessTableOperation26::RestoreKernel&&p==r.s.physicalContextTarget);for(auto*q=r.s.processClients;q;q=q->ringNext_)if(q!=p)assert(!r.nativeProcessContextHeldForDomain(*this,*q));}',1)
 tests=r'''
int main(){unsigned controls=0;
 {ZornGen7HostRing26 f;for(unsigned i=0;i<3;++i){ZornGen7AppExecution26*scope=nullptr;assert(!f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Map,scope)&&scope==&f.execution&&f.s.processSelected==&f.process);assert(f.authoritySawWholeMutex);assert(!f.finishApplicationOperation(*scope,0)&&!f.s.processSelected&&f.process.state_.detached&&f.process.asidHeld_&&f.process.liveMappings==3);}assert(f.domain.transitions==6&&f.drains==6);++controls;}
 {ZornGen7HostRing26 f;f.s.processClients=nullptr;f.s.prepareOutput=&f.process;f.process.clientOwner_=nullptr;f.process.clientTask_=TASK_NULL;f.process.clientOpen_=false;f.process.vmAttached_=false;ZornGen7ProcessTables26*p=nullptr;assert(!f.openApplicationProcess(f.client,f.execution,p)&&p==&f.process&&!f.s.processSelected&&p->state_.detached);assert(f.domain.operations.back()==ZornGen7ProcessTableOperation26::RestoreKernel);++controls;}
 {ZornGen7HostRing26 f;f.closing();auto*p=&f.process;assert(!f.closeApplicationProcess(f.client,f.execution,p)&&!p&&!f.s.processClients&&!f.s.processSelected&&f.process.retired&&!f.process.asidHeld_&&f.process.liveMappings==0);++controls;}
 {ZornGen7HostRing26 f;f.pendingSelected();ZornGen7AppExecution26*scope=nullptr;assert(!f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Wait,scope));f.expiry();assert(f.finishApplicationOperation(*scope,kIOReturnTimeout)==kIOReturnTimeout&&!f.s.stopped&&f.s.processSelected==&f.process&&!f.process.state_.detached&&f.domain.transitions==0);f.s.native.count=0;f.process.clientState.submit.count=0;f.process.vm_.pending=false;scope=nullptr;assert(!f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Wait,scope));assert(!f.finishApplicationOperation(*scope,0)&&!f.s.processSelected&&f.process.state_.detached);++controls;}
 {ZornGen7HostRing26 f;f.pendingSelected();ZornGen7AppExecution26*scope=nullptr;assert(!f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Wait,scope));f.expiry();faultAfterOutstanding=&f.domain.fault;auto raw=f.finishApplicationOperation(*scope,kIOReturnTimeout);
  if(raw!=kIOReturnNotReady||!f.s.stopped||f.s.processSelected!=&f.process||f.process.liveMappings!=3){std::puts("REPRO256 late fault was incorrectly retained as healthy wait expiry");return 73;}++controls;}
 {ZornGen7HostRing26 f;ZornGen7AppExecution26*scope=nullptr;assert(!f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Submit,scope));f.s.native.count=1;f.process.clientState.submit.count=1;assert(!f.finishApplicationOperation(*scope,0)&&f.s.processSelected==&f.process&&f.s.native.count==1&&f.process.clientState.submit.count==1&&f.process.liveMappings==3&&!f.s.stopped);++controls;}
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

 tests=tests.replace('execution2.client_=&second;execution2.task_=task2;', 'execution2.client_=&second;execution2.task_=task2;execution2.ring_=&f;execution2.maps_=&f.s.maps;execution2.oob_=&f.s.physicalOob.value;execution2.ringNext_=&f.execution;f.s.appExecutions=&execution2;')
 tests=tests.replace('f.s.appExecution=next?&execution2:&f.execution;', '')
 tests=tests.replace('real service/Board multiclient\n // admission remains exclusive and is NOT qualified by this control.', 'actual service/Board membership has separate source tests;no native\n // hardware admission or physical MMIO is qualified by this control.')

 additional=r"""
 {ZornGen7HostRing26 f;f.s.lockIssuer();ZornGen7AppExecution26*scope=nullptr;assert(f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Map,scope)==kIOReturnNotReady&&!scope);f.s.unlockIssuer();++controls;}
 for(unsigned mode=0;mode<4;++mode){ZornGen7HostRing26 f;ZornGen7HostRing26 foreign;
  if(mode==0)f.execution.ring_=&foreign;if(mode==1)f.execution.maps_=nullptr;if(mode==2)f.s.physicalOob.value.generation=2;if(mode==3)f.s.physicalOob.value.retired=true;
  ZornGen7AppExecution26*scope=nullptr;assert(f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Map,scope)&&!scope&&!f.domain.transitions&&f.process.asidHeld_);++controls;}
"""
 tests=tests.replace(' std::printf("PASS256',additional+'\n std::printf("PASS256')

 concurrent=r"""
 {ZornGen7HostRing26 f;ZornGen7AppIoClient26 second;ZornGen7AppExecution26 execution2;ZornGen7ProcessTables26 process2;const auto task2=reinterpret_cast<void*>(3);
  second.owner_=&f;second.service_=&f.service;second.provider=&f.service;second.openingTask_=task2;execution2.client_=&second;execution2.task_=task2;execution2.ring_=&f;execution2.maps_=&f.s.maps;execution2.oob_=&f.s.physicalOob.value;execution2.ringNext_=&f.execution;f.s.appExecutions=&execution2;
  process2.ringOwner_=&f;process2.domain_=&f.domain;process2.clientOwner_=&second;process2.clientTask_=task2;process2.asid_=43;process2.ringNext_=&f.process;f.s.processClients=&process2;
  std::atomic<unsigned>active{0},maximum{0},done{0};std::vector<std::thread>threads;
  for(unsigned i=0;i<12;++i)threads.emplace_back([&,i]{callerTask=(i&1)?task2:f.execution.task_;auto&client=(i&1)?second:f.client;auto*expected=(i&1)?&process2:&f.process;
   for(unsigned n=0;n<4;++n){ZornGen7AppExecution26*scope=nullptr;assert(!f.beginApplicationOperation(client,ZornGen7AppOperation26::CpuView,scope)&&f.s.processSelected==expected);auto count=++active;maximum=std::max(maximum.load(),count);std::this_thread::yield();--active;assert(!f.finishApplicationOperation(*scope,0));++done;}});
  for(auto&thread:threads)thread.join();assert(done==48&&maximum==1&&f.domain.transitions==96&&!f.s.processSelected&&f.process.asid_==42&&process2.asid_==43&&f.process.liveMappings==3&&process2.liveMappings==3&&execution2.refs==1);++controls;
  f.s.appExecutions=&f.execution;f.s.processClients=&f.process;
 }
"""
 tests=tests.replace(' std::printf("PASS256',concurrent+'\n std::printf("PASS256')

 tests=tests.replace('f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Map,scope)==kIOReturnBusy&&!scope&&!f.s.stopped&&f.s.processSelected==&other&&!f.domain.transitions', 'f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Map,scope)==kIOReturnNotReady&&!scope&&f.s.stopped&&f.s.processSelected==&other&&!f.domain.transitions')
 setup=r"""
struct HandoverFixture {
 ZornGen7HostRing26 f;ZornGen7AppIoClient26 oldClient;ZornGen7AppExecution26 oldOwner;ZornGen7ProcessTables26 oldProcess;
 HandoverFixture(){const auto task=reinterpret_cast<void*>(3);oldClient.owner_=&f;oldClient.service_=&f.service;oldClient.provider=&f.service;oldClient.openingTask_=task;oldOwner.client_=&oldClient;oldOwner.task_=task;oldOwner.ring_=&f;oldOwner.maps_=&f.s.maps;oldOwner.oob_=&f.s.physicalOob.value;oldOwner.ringNext_=&f.execution;f.s.appExecutions=&oldOwner;oldProcess.ringOwner_=&f;oldProcess.domain_=&f.domain;oldProcess.clientOwner_=&oldClient;oldProcess.clientTask_=task;oldProcess.asid_=43;oldProcess.state_.detached=false;oldProcess.ringNext_=&f.process;f.s.processClients=&oldProcess;f.s.processSelected=&oldProcess;}
 ~HandoverFixture(){f.s.appExecutions=&f.execution;f.s.processClients=&f.process;}
};
"""
 prefix+=setup
 additional=r"""
 {HandoverFixture h;auto&f=h.f;f.closing();auto*p=&f.process;assert(!f.closeApplicationProcess(f.client,f.execution,p)&&!p&&h.oldProcess.state_.detached&&h.oldProcess.asidHeld_&&h.oldProcess.liveMappings==3&&!f.s.processSelected&&!f.s.stopped&&f.contextChecks==2&&f.domain.operations.front()==ZornGen7ProcessTableOperation26::RestoreKernel);assert(f.process.retired&&!f.process.asidHeld_);++controls;}
 {HandoverFixture h;auto&f=h.f;f.closing();f.pendingOnPoll=true;f.s.native.count=1;h.oldProcess.clientState.submit.count=1;h.oldProcess.vm_.pending=true;auto*p=&f.process;bool pending=false;assert(f.closeApplicationProcess(f.client,f.execution,p,&pending)==kIOReturnBusy&&pending&&p&&!f.s.stopped&&f.s.processSelected==&h.oldProcess&&!h.oldProcess.state_.detached&&f.domain.transitions==0&&f.process.liveMappings==3);++controls;f.pendingOnPoll=false;assert(!f.closeApplicationProcess(f.client,f.execution,p,&pending)&&!pending&&!p&&!f.s.processSelected&&h.oldProcess.asidHeld_&&h.oldProcess.liveMappings==3);++controls;}
 for(unsigned fail=1;fail<=2;++fail){HandoverFixture h;auto&f=h.f;f.refuseContextAt=fail;f.closing();auto*p=&f.process;assert(f.closeApplicationProcess(f.client,f.execution,p)&&p&&f.s.stopped&&f.s.processSelected==&h.oldProcess&&!f.domain.transitions&&h.oldProcess.asidHeld_&&f.process.liveMappings==3);++controls;}
 {HandoverFixture h;auto&f=h.f;f.closing();f.drainRaw=kIOReturnTimeout;auto*p=&f.process;bool pending=true;assert(f.closeApplicationProcess(f.client,f.execution,p,&pending)==kIOReturnTimeout&&!pending&&p&&f.s.stopped&&f.s.processSelected==&h.oldProcess&&!f.domain.transitions);++controls;}
 {HandoverFixture h;auto&f=h.f;f.closing();f.pendingOnPoll=true;f.pollFault=true;auto*p=&f.process;bool pending=true;assert(f.closeApplicationProcess(f.client,f.execution,p,&pending)!=kIOReturnBusy&&!pending&&p&&f.s.stopped&&f.s.processSelected==&h.oldProcess&&!f.domain.transitions);++controls;}
 for(unsigned fail=0;fail<4;++fail){HandoverFixture h;auto&f=h.f;f.closing();if(fail==0)h.oldOwner.phase_=ZornGen7AppExecution26::Phase::Failed;if(fail==1)h.oldOwner.task_=kernel_task;if(fail==2)h.oldProcess.state_.poisoned=true;if(fail==3)h.oldOwner.oobMemberHeld_=false;auto*p=&f.process;assert(f.closeApplicationProcess(f.client,f.execution,p)&&p&&f.s.stopped&&!f.domain.transitions&&f.contextChecks==0);++controls;}
 {HandoverFixture h;auto&f=h.f;IOLockLock(f.s.appSerial);__atomic_store_n(&f.s.appSerialThread,current_thread(),__ATOMIC_RELEASE);assert(!f.restoreCompletedApplicationContext()&&!f.s.processSelected&&h.oldProcess.state_.detached&&h.oldProcess.asidHeld_&&h.oldProcess.liveMappings==3);__atomic_store_n(&f.s.appSerialThread,THREAD_NULL,__ATOMIC_RELEASE);IOLockUnlock(f.s.appSerial);++controls;}
"""
 additional+='\n for(auto op:{ZornGen7AppOperation26::CpuView,ZornGen7AppOperation26::Timestamp}){\n  ZornGen7HostRing26 f;ZornGen7AppExecution26*scope=nullptr;\n  assert(!f.beginApplicationOperation(f.client,op,scope,nullptr,false)&&scope==&f.execution&&f.authoritySawWholeMutex);\n  assert(!f.s.processSelected&&!f.s.appOperationProcess&&f.process.state_.detached&&!f.drains&&!f.domain.transitions);\n  assert(!f.finishApplicationOperation(*scope,0)&&!f.s.processSelected&&!f.drains&&!f.domain.transitions&&f.process.asidHeld_&&f.process.liveMappings==3);++controls;\n }\n for(auto op:{ZornGen7AppOperation26::Submit,ZornGen7AppOperation26::Wait,ZornGen7AppOperation26::Map,ZornGen7AppOperation26::Close,ZornGen7AppOperation26::PrepareTables}){\n  ZornGen7HostRing26 f;ZornGen7AppExecution26*scope=nullptr;assert(f.beginApplicationOperation(f.client,op,scope,nullptr,false)==kIOReturnBadArgument&&!scope&&!f.authorityCalls&&!f.domain.transitions&&!f.s.stopped);++controls;\n }\n {HandoverFixture h;auto&f=h.f;h.oldProcess.clientState.submit.count=1;h.oldProcess.vm_.pending=true;\n  ZornGen7AppExecution26*scope=nullptr;assert(!f.beginApplicationOperation(f.client,ZornGen7AppOperation26::CpuView,scope,nullptr,false));\n  assert(f.s.processSelected==&h.oldProcess&&!f.drains&&!f.domain.transitions&&!f.s.appOperationProcess);\n  assert(f.finishApplicationOperation(*scope,kIOReturnUnsupported)==kIOReturnUnsupported&&f.s.processSelected==&h.oldProcess&&!f.domain.transitions&&!f.drains&&h.oldProcess.clientState.submit.count==1&&h.oldProcess.vm_.pending&&!f.s.stopped);++controls;\n }\n {ZornGen7HostRing26 f;f.authorityRaw=kIOReturnNotPermitted;ZornGen7AppExecution26*scope=nullptr;\n  assert(f.beginApplicationOperation(f.client,ZornGen7AppOperation26::CpuView,scope,nullptr,false)==kIOReturnNotPermitted&&!scope&&f.s.stopped&&!f.domain.transitions);++controls;\n }\n'
 tests=tests.replace(' std::printf("PASS256',additional+'\n std::printf("PASS256')
 tests=tests.replace('PASS256 actual operation/context', 'PASS290 retained Submit scope plus lifecycle/context controls')
 prefix='#include "'+str(S/'ZornClientFailure261.h')+'"\n'+prefix
 prefix=prefix.replace('IOReturn viewError_=0;', 'IOReturn viewError_=0;uint64_t failureToken261_=1;')
 prefix+=r"""
extern "C" void zorn_failure_note261(uint32_t,uint32_t,uint32_t,uint32_t,uint32_t,uint32_t){}
extern "C" void zorn_failure_target_begin261(uint64_t,ZornClientFailureScope261 *out){*out={0,0,0};}
extern "C" void zorn_failure_target_end261(const ZornClientFailureScope261 *){}
"""
 cpp=O/'hostcheck.cpp';cpp.write_text(prefix+tests);env=dict(os.environ);env.update(TSAN_OPTIONS='symbolize=0',ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0');args=['/usr/bin/clang++','-std=c++17','-O1','-g','-fno-omit-frame-pointer','-fsanitize='+a.sanitizer,str(cpp),'-o',str(O/'hostcheck')];runs=[]
 for cmd in [args,[str(O/'hostcheck')]]:
  z=subprocess.run(cmd,capture_output=True,text=True,timeout=120,env=env);runs.append(dict(arguments=cmd,exit=z.returncode,stdout=z.stdout,stderr=z.stderr,symbolization_disabled=True));(O/'commands.json').write_text(json.dumps(runs,indent=2)+'\n');assert not z.returncode,z.stderr[-5000:]
 pin=lambda p:dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest());result=dict(passed=True,sanitizer=a.sanitizer,source=pin(S/'ZornGen7HostRing26.cpp'),header=pin(S/'ZornGen7HostRing26.h'),test_tool=pin(Path(__file__)),actual_shared_member_lookup_and_physical_identity_owns_methods_compiled=True,actual_scope_context_transition_methods_compiled=True,actual_client_task_match_method_compiled=True,whole_operation_mutex_includes_foreign_check_context_entry_exit=True,healthy_wait_expiry_preserves_live_selected_context=True,wrong_scope_cannot_unlock_active_owner=True,real_SMMU_backend_unchanged_except_argument_restriction=True,actual_pending_fence_output_from_backend_tested_separately=True,successful_Submit_retains_actual_pending_state=True,readonly_scope_and_foreign_pending_context_preserved=True,fixture_source=pin(Path(__file__).with_name('check-ios26-close-context.py')),MMIO_SMMU_drain_authority_and_client_body_boundaries_are_host_fixtures=True,hardware_qualified=False,phone_access=False,output=runs[-1]['stdout']);(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result['output'],end='')
if __name__=='__main__':main()

#!/usr/bin/env python3
"""Exercise actual v303 ZornActiveContextRetain303 + ZornGen7HostRing26 operation/context retention, handover, Close, and fault paths under ASan/UBSan and TSan."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess


def extract(t: str, start: str) -> str:
    a = t.index(start)
    b = t.index('{', a) + 1
    d = 1
    while d:
        d += (t[b] == '{') - (t[b] == '}')
        b += 1
    return t[a:b]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--sanitizer', choices=['asan', 'tsan'], required=True)
    a = p.parse_args()
    S = a.source.resolve()
    O = a.out.resolve()
    O.mkdir(parents=True, exist_ok=False)
    source = (S / 'ZornGen7HostRing26.cpp').read_text()

    names = [
        'bool ZornGen7HostRing26::applicationOperationHeld',
        'bool ZornGen7HostRing26::processExecutionHealthy',
        'bool ZornGen7HostRing26::processConnectionHeld',
        'bool ZornGen7HostRing26::applicationContextTransitionHeld',
        'IOReturn ZornGen7HostRing26::enterApplicationContext',
        'IOReturn ZornGen7HostRing26::leaveApplicationContext',
        'IOReturn ZornGen7HostRing26::beginApplicationOperation',
        'IOReturn ZornGen7HostRing26::finishApplicationOperation',
        'bool ZornGen7HostRing26::processTransitionHeldForDomain',
        'IOReturn ZornGen7HostRing26::transitionProcessTables',
        'IOReturn ZornGen7HostRing26::openApplicationProcess',
        'IOReturn ZornGen7HostRing26::closeApplicationProcess',
        'bool ZornGen7HostRing26::physicalContextIdentity',
        'bool ZornGen7HostRing26::physicalContextHeld',
        'bool ZornGen7HostRing26::nativePhysicalContextBinding',
        'IOReturn ZornGen7HostRing26::restoreCompletedApplicationContext',
        'bool ZornGen7HostRing26::nativeProcessContextHeldForDomain',
        'bool ZornGen7HostRing26::processTransitionArgumentsHeld',
    ]
    methods = '\n'.join(extract(source, n) for n in names)
    match = extract((S / 'direct-runtime/ZornGen7AppIo26.cpp').read_text(),
                    'bool ZornGen7AppIoClient26::matchesOwnedSession(')
    physical = (S / 'ZornGen7PhysicalOob26.h').read_text()
    lease = extract(physical, '    struct Lease {') + ';'
    owns = extract(physical, '    bool owns(')
    for_transport = extract(physical, '    Lease *forTransport(')
    helpers = '\n'.join(extract(source, n) for n in [
        '    bool appSerialHeld() const',
        '    ZornGen7AppExecution26 *applicationMember(',
        '    bool ownsExecution(',
        '    bool applicationQuiescent() const',
    ])

    cpp_code = f'''#include "{S / 'ZornClientFailure261.h'}"
#include "{S / 'ZornActiveContextRetain303.h'}"
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <mutex>
#include <thread>
#include <vector>
#include <algorithm>

using IOReturn=int;using task_t=void*;using thread_t=void*;
constexpr thread_t THREAD_NULL=nullptr;constexpr task_t TASK_NULL=nullptr;
static task_t kernel_task=reinterpret_cast<void*>(1);
static thread_local task_t callerTask=reinterpret_cast<void*>(2);
static thread_t current_thread(){{static thread_local int id;return &id;}}
static task_t current_task(){{return callerTask;}}
static thread_local bool normalContext=true;
static bool normal(){{return normalContext;}}
constexpr IOReturn kIOReturnSuccess=0,kIOReturnNotReady=1,kIOReturnBadArgument=2,kIOReturnBusy=3,
    kIOReturnTimeout=4,kIOReturnIOError=5,kIOReturnNotPermitted=6,kIOReturnNoMemory=7,kIOReturnUnsupported=8;

struct OSObject{{std::atomic<int>refs{{1}};void retain(){{assert(refs.fetch_add(1)>0);}}void release(){{assert(refs.fetch_sub(1)>1);}}}};
struct IOService{{}};
struct IOUserClient:OSObject{{IOService*provider=nullptr;IOService*getProvider()const{{return provider;}}}};
struct Lock{{std::mutex mutex;std::atomic<thread_t>owner{{THREAD_NULL}};}};
static void IOLockLock(Lock*p){{assert(p->owner.load()!=current_thread());p->mutex.lock();p->owner=current_thread();}}
static void IOLockUnlock(Lock*p){{assert(p->owner.load()==current_thread());p->owner=THREAD_NULL;p->mutex.unlock();}}
static bool IORecursiveLockHaveLock(Lock*p){{return p&&p->owner.load()==current_thread();}}
static constexpr uint64_t NSEC_PER_MSEC=1000000;
static void clock_interval_to_deadline(unsigned x,uint64_t y,uint64_t*d){{*d=x*y;}}
static void zorn26_application_prepare_event(uintptr_t,uint32_t,uint32_t,uint32_t){{}}
static void zorn26_client_close_reset242(){{}}
static void zorn26_client_event240(unsigned){{}}
extern "C" void zorn_failure_note261(uint32_t,uint32_t,uint32_t,uint32_t,uint32_t,uint32_t){{}}
extern "C" void zorn_failure_target_begin261(uint64_t,ZornClientFailureScope261 *out){{*out={{0,0,0}};}}
extern "C" void zorn_failure_target_end261(const ZornClientFailureScope261 *){{}}

enum class ZornGen7AppOperation26:unsigned{{PrepareTables,Map,Submit,Wait,CpuView,Close,OobAcquire,OobRelease,Timestamp}};
enum class ZornGen7ProcessTableOperation26:unsigned{{Prepare,Select,AttachVm,RestoreKernel,DetachVm,RetireDetached,DiscardNeverInstalled}};
class ZornGen7HostRing26;class ZornGen7SmmuDomain26;
static thread_local bool*faultAfterOutstanding=nullptr;
struct Queue {{
    unsigned count=0,resets=0;bool poison=false;
    unsigned outstanding()const{{if(faultAfterOutstanding){{*faultAfterOutstanding=true;faultAfterOutstanding=nullptr;}}return count;}}
    bool poisoned()const{{return poison;}}
    void requestContextReset(){{++resets;}}
}};
struct ZornGen7ProcessTables26 {{
    ZornGen7HostRing26*ringOwner_=nullptr;ZornGen7SmmuDomain26*domain_=nullptr;ZornGen7ProcessTables26*ringNext_=nullptr;
    IOUserClient*clientOwner_=nullptr;task_t clientTask_=TASK_NULL;
    bool clientOpen_=true,clientClosed_=false,vmAttached_=true,vmDetached_=false,retired=false,asidHeld_=true,submitAttached_=true,clientOpenAttempted_=true;
    unsigned asid_=42,liveMappings=3;struct{{bool detached=true,poisoned=false;}}state_;
    struct Vm{{bool pending=false,poison=false;bool hasPendingSubmissionResources()const{{return pending;}}bool poisoned()const{{return poison;}}}}vm_;
    struct ClientState{{Queue submit;}}clientState;ClientState*clientState_=&clientState;
}};
class ZornGen7SmmuDomain26 {{
public:
    bool fault=false;IOReturn transitionRaw=0;bool partial=false;unsigned transitions=0;
    std::vector<ZornGen7ProcessTableOperation26>operations;
    bool faulted()const{{if(faultAfterOutstanding){{*faultAfterOutstanding=true;faultAfterOutstanding=nullptr;}}return fault;}}
    IOReturn transitionHostProcessTables(ZornGen7HostRing26&,ZornGen7ProcessTableOperation26,ZornGen7ProcessTables26*&,unsigned,size_t);
}};
class ZornGen7AppIoClient26:public IOUserClient {{
public:
    ZornGen7HostRing26*owner_=nullptr;IOService*service_=nullptr;task_t openingTask_=TASK_NULL;
    bool live_=true,attempted_=true,pinned_=true,closing_=false;thread_t closingThread_=THREAD_NULL;
    IOReturn viewError_=0;uint64_t failureToken261_=1;
    void*serial_=reinterpret_cast<void*>(1);void*views_=reinterpret_cast<void*>(1);
    bool matchesOwnedSession(const ZornGen7HostRing26&,const IOService*,task_t,bool)const;
}};
#define OSDynamicCast(T,P) static_cast<T*>(P)
class ZornGen7DirectHfi26:public OSObject{{public:bool physicalOobHeld(const ZornGen7HostRing26&)const;}};
class ZornGen7PhysicalOob26 {{
public:
{lease}
    ZornGen7DirectHfi26 transport;OSObject maps;Lease value;Lease *active_=&value;uint64_t generation_=1;
    ZornGen7PhysicalOob26(){{
        value.physical=this;value.transport=&transport;value.registerMaps=&maps;value.generation=1;
        value.owner=&transport;value.attempted=value.requestReturned=value.ackObserved=value.ackCleared=value.gxOn=true;
    }}
{owns}
{for_transport}
}};
class ZornGen7AppExecution26:public OSObject {{
public:
    ZornGen7HostRing26*ring_=nullptr;OSObject*maps_=nullptr;ZornGen7AppExecution26*ringNext_=nullptr;
    bool oobMemberHeld_=true,oobMemberReleased_=false,pinned_=true;
    enum class Phase{{Held,Failed}};Phase phase_=Phase::Held;
    ZornGen7PhysicalOob26::Lease*oob_=nullptr;
    IOUserClient*client_=nullptr;task_t task_=TASK_NULL;
}};
class ZornGen7HostRing26 {{
public:
    Lock issuer,operationMutex,driverGate;IOService service;ZornGen7AppIoClient26 client,foreign;
    ZornGen7AppExecution26 execution;ZornGen7SmmuDomain26 domain;ZornGen7ProcessTables26 process;
    struct Storage{{
        Lock&gate;Lock&issuer;Lock*appSerial=nullptr;thread_t appSerialThread=THREAD_NULL;std::atomic<thread_t>issuerThread{{THREAD_NULL}};
        ZornGen7AppExecution26*appExecution=nullptr;bool appOperationPending=false,appExecutionPending=false,appOobTransition=false,appOobActive=true,kernelIoActive=false;
        thread_t appOperationThread=THREAD_NULL;ZornGen7AppOperation26 appOperationKind=ZornGen7AppOperation26::PrepareTables;bool appFenceWaitExpired=false;
        ZornGen7ProcessTables26*appOperationProcess=nullptr,*appContextTarget=nullptr;thread_t appContextThread=THREAD_NULL;
        uint32_t stopped=0;struct Irq{{bool halt=false;unsigned masks=0;bool halted()const{{return halt;}}void stopAndMask(){{halt=true;++masks;}}}}irq,gmu;
        ZornGen7SmmuDomain26&domain;bool hfiHalted()const{{return false;}}void*hfi=nullptr;
        bool applicationIoPublishAttempted=true;IOService*applicationIoService=nullptr;IOService*kernelIoService=nullptr;bool kernelIoAttempted=false;
        IOUserClient*kernelIoConnection=nullptr;bool kernelTaskActive=false,kernelIoClosing=false,kernelIoClosed=false;thread_t kernelTaskThread=THREAD_NULL;
        ZornGen7ProcessTables26*processClients=nullptr,*processSelected=nullptr,*nativeProcessTableLease=nullptr,*kernelProcess=nullptr;bool kernelProcessReady=false,nativeTableLease=false;
        Queue native,runtimeSubmit;uint64_t deadline=0;thread_t processTransitionThread=THREAD_NULL;ZornGen7ProcessTableOperation26 processTransitionOperation=ZornGen7ProcessTableOperation26::Prepare;
        struct{{bool busy_valid=true;uint32_t busy=0,status=0,irq=0,hwfault=0,rptr=0,wptr=0;}}ring;
        struct{{unsigned input_bits=48;}}logical;size_t runtimeCapacity=4096;
        ZornGen7ProcessTables26*prepareOutput=nullptr;
        ZornGen7ProcessTables26*physicalContextTarget=nullptr;thread_t physicalContextThread=THREAD_NULL;uint64_t physicalContextGeneration=0;bool physicalContextAuthorized=false,physicalContextRestoring=false;
        struct PhysicalAuthority{{void*cookie=nullptr;IOReturn(*physicalContextCheck)(void*,ZornGen7HostRing26&,uint64_t)=nullptr;}}physicalAuthority;
        OSObject*physicalAuthorityOwner=reinterpret_cast<OSObject*>(1);bool physicalAuthorityHeld=true,physicalAuthorityPending=false,physicalAuthorityReleasing=false;
        ZornGen7AppExecution26*appExecutions=nullptr;
        ZornGen7PhysicalOob26 physicalOob;OSObject&maps=physicalOob.maps;OSObject&hfiOwner=physicalOob.transport;
        ZornGen7ProcessTables26::Vm runtimeVm;unsigned nativeTableAcquires=0,nativeTableReleases=0,nativeProcessTableAcquires=0,nativeProcessTableReleases=0;
{helpers}
        void lockIssuer(){{IOLockLock(&issuer);issuerThread=current_thread();}}
        void unlockIssuer(){{assert(issuerHeld());issuerThread=THREAD_NULL;IOLockUnlock(&issuer);}}
        bool issuerHeld()const{{return issuerThread.load()==current_thread();}}
    }}s{{driverGate,issuer,nullptr,THREAD_NULL,{{}},nullptr,false,false,false,true,false,THREAD_NULL,ZornGen7AppOperation26::PrepareTables,false,nullptr,nullptr,THREAD_NULL,0,{{}},{{}},domain}};
    static IOReturn contextCheck(void*cookie,ZornGen7HostRing26&r,uint64_t generation){{
        assert(cookie==&r&&!r.s.issuerHeld());++r.contextChecks;IOLockLock(&r.driverGate);
        const bool held=r.contextResources&&r.refuseContextAt!=r.contextChecks&&r.nativePhysicalContextBinding(generation);
        IOLockUnlock(&r.driverGate);return held?0:kIOReturnNotReady;
    }}
    unsigned contextChecks=0,refuseContextAt=0;bool contextResources=true,pendingOnPoll=false,pollFault=false,positiveBudgetExpired=false;uint32_t lastWaitBudget=0;
    Storage*storage_=&s;bool healthy=true,physicalHeld=true;IOReturn authorityRaw=0,drainRaw=0,openRaw=0,closeRaw=0;unsigned drains=0,authorityCalls=0;bool authoritySawWholeMutex=false;
    ZornGen7HostRing26(){{
        s.physicalAuthority.cookie=this;s.physicalAuthority.physicalContextCheck=contextCheck;s.physicalAuthorityOwner=&s.physicalOob.transport;
        s.appSerial=&operationMutex;s.appExecutions=&execution;s.appExecution=nullptr;execution.ring_=this;execution.maps_=&s.maps;execution.oob_=&s.physicalOob.value;
        s.applicationIoService=&service;client.owner_=this;client.service_=&service;client.provider=&service;client.openingTask_=callerTask;
        execution.client_=&client;execution.task_=callerTask;process.ringOwner_=this;process.domain_=&domain;process.clientOwner_=&client;process.clientTask_=callerTask;s.processClients=&process;
    }}
    bool bootstrapHealthy()const{{return healthy&&!__atomic_load_n(&s.stopped,__ATOMIC_ACQUIRE)&&!s.irq.halted()&&!s.gmu.halted()&&!domain.faulted();}}
    bool kernelClientExecutionHealthy()const{{return false;}}
    bool applicationOobHeldForTransport(const ZornGen7AppExecution26&)const{{return physicalHeld;}}
    IOReturn checkApplicationExecution(IOUserClient&,ZornGen7AppExecution26&,ZornGen7AppOperation26){{
        assert(!s.issuerHeld()&&!IORecursiveLockHaveLock(&s.gate));++authorityCalls;authoritySawWholeMutex=operationMutex.owner.load()==current_thread();return authorityRaw;
    }}
    bool physicalContextIdentity()const;bool physicalContextHeld()const;bool nativePhysicalContextBinding(uint64_t)const;
    IOReturn restoreCompletedApplicationContext(bool *pendingFence=nullptr,uint32_t waitBudgetUs=0);
    bool nativeProcessContextHeldForDomain(const ZornGen7SmmuDomain26&,const ZornGen7ProcessTables26&)const;
    bool processTransitionArgumentsHeld(const ZornGen7SmmuDomain26&,ZornGen7ProcessTableOperation26,const ZornGen7ProcessTables26*)const;
    bool applicationOperationHeld()const;bool processExecutionHealthy()const;bool processConnectionHeld(IOUserClient&)const;
    bool applicationContextTransitionHeld(ZornGen7ProcessTableOperation26)const;
    IOReturn enterApplicationContext(IOUserClient&,ZornGen7AppExecution26&,bool *pendingFence=nullptr);
    IOReturn leaveApplicationContext(ZornGen7AppExecution26&,bool);
    IOReturn beginApplicationOperation(IOUserClient&,ZornGen7AppOperation26,ZornGen7AppExecution26*&,bool *pendingFence=nullptr,bool selectContext=true);
    IOReturn finishApplicationOperation(ZornGen7AppExecution26&,IOReturn);
    bool processTransitionHeldForDomain(const ZornGen7SmmuDomain26&)const;
    IOReturn transitionProcessTables(IOUserClient&,ZornGen7ProcessTableOperation26,ZornGen7ProcessTables26*&,unsigned,size_t);
    IOReturn openApplicationProcess(IOUserClient&,ZornGen7AppExecution26&,ZornGen7ProcessTables26*&);
    IOReturn closeApplicationProcess(IOUserClient&,ZornGen7AppExecution26&,ZornGen7ProcessTables26*&,bool *pendingFence=nullptr);
    IOReturn quiesceKernelIo(uint32_t budget=1000000,bool*pending=nullptr){{
        if(pending)*pending=false;assert(s.issuerHeld()&&processExecutionHealthy());++drains;lastWaitBudget=budget;
        if((budget==0&&pendingOnPoll)||(budget&&positiveBudgetExpired)||(pendingOnPoll&&pollFault)){{
            if(pending)*pending=true;if(pollFault)domain.fault=true;return kIOReturnTimeout;
        }}
        if(drainRaw)return drainRaw;
        for(auto*p=s.processClients;p;p=p->ringNext_)if(p!=s.processSelected&&p->clientState_&&p->clientState_->submit.outstanding())return kIOReturnNotReady;
        s.native.count=0;s.runtimeSubmit.count=0;if(s.processSelected){{s.processSelected->clientState.submit.count=0;s.processSelected->vm_.pending=false;}}return 0;
    }}
    IOReturn openProcessClient(IOUserClient&c,ZornGen7ProcessTables26&p,task_t task){{if(openRaw)return openRaw;p.clientOwner_=&c;p.clientTask_=task;p.clientOpen_=true;p.clientClosed_=false;return 0;}}
    IOReturn closeProcessClient(IOUserClient&,ZornGen7ProcessTables26&p){{if(closeRaw)return closeRaw;p.clientOpen_=false;p.clientClosed_=true;p.liveMappings=0;p.clientState_=nullptr;return 0;}}
    void closing(){{client.closing_=true;client.closingThread_=current_thread();}}
    void expiry(){{s.lockIssuer();s.appFenceWaitExpired=true;s.unlockIssuer();}}
    void pendingSelected(){{s.processSelected=&process;process.state_.detached=false;s.native.count=1;process.clientState.submit.count=1;process.vm_.pending=true;}}
    ~ZornGen7HostRing26(){{assert(execution.refs==1&&!operationMutex.owner.load()&&!s.issuerHeld());}}
}};
bool ZornGen7DirectHfi26::physicalOobHeld(const ZornGen7HostRing26&r)const{{return r.physicalHeld;}}
{match}
{methods}
IOReturn ZornGen7SmmuDomain26::transitionHostProcessTables(ZornGen7HostRing26&r,ZornGen7ProcessTableOperation26 op,ZornGen7ProcessTables26*&p,unsigned,size_t){{
    assert(r.s.issuerHeld()&&r.processTransitionArgumentsHeld(*this,op,p));
    if(r.s.physicalContextTarget){{
        assert(op==ZornGen7ProcessTableOperation26::RestoreKernel&&p==r.s.physicalContextTarget);
        for(auto*q=r.s.processClients;q;q=q->ringNext_)if(q!=p)assert(!r.nativeProcessContextHeldForDomain(*this,*q));
    }}
    ++transitions;operations.push_back(op);
    if(transitionRaw){{if(partial&&p)p->state_.poisoned=true;return transitionRaw;}}
    if(op==ZornGen7ProcessTableOperation26::Prepare){{p=r.s.prepareOutput;assert(p);}}
    else if(op==ZornGen7ProcessTableOperation26::Select){{assert(p&&!r.s.processSelected);p->state_.detached=false;}}
    else if(op==ZornGen7ProcessTableOperation26::RestoreKernel){{assert(p==r.s.processSelected);p->state_.detached=true;}}
    else if(op==ZornGen7ProcessTableOperation26::AttachVm){{p->vmAttached_=true;p->vmDetached_=false;}}
    else if(op==ZornGen7ProcessTableOperation26::DetachVm){{p->vmAttached_=false;p->vmDetached_=true;}}
    else if(op==ZornGen7ProcessTableOperation26::RetireDetached){{assert(p->state_.detached&&p->vmDetached_&&p->clientClosed_);p->asidHeld_=false;p->retired=true;p=nullptr;}}
    return 0;
}}

int main() {{
    unsigned controls=0;

    // 1. Single active client (backboardd): 100 full frames of Map -> Map -> Submit -> Wait -> CpuView -> Map(Free)
    //    selects context ONCE (transitions == 1, resets == 1) and NEVER thrashes RestoreKernel/Select!
    {{
        ZornGen7HostRing26 f;
        for(unsigned frame=0;frame<100;++frame){{
            for(auto op:{{ZornGen7AppOperation26::Map,ZornGen7AppOperation26::Map,ZornGen7AppOperation26::Submit,ZornGen7AppOperation26::Wait,ZornGen7AppOperation26::Map}}){{
                ZornGen7AppExecution26*scope=nullptr;
                assert(!f.beginApplicationOperation(f.client,op,scope)&&scope==&f.execution&&f.s.processSelected==&f.process);
                if(op==ZornGen7AppOperation26::Submit){{f.s.native.count=1;f.process.clientState.submit.count=1;}}
                if(op==ZornGen7AppOperation26::Wait){{f.s.native.count=0;f.process.clientState.submit.count=0;}}
                assert(!f.finishApplicationOperation(*scope,0)&&f.s.processSelected==&f.process&&!f.process.state_.detached);
            }}
            ZornGen7AppExecution26*cpuScope=nullptr;
            assert(!f.beginApplicationOperation(f.client,ZornGen7AppOperation26::CpuView,cpuScope,nullptr,false));
            assert(!f.finishApplicationOperation(*cpuScope,0)&&f.s.processSelected==&f.process);
        }}
        assert(f.domain.transitions==1&&f.s.native.resets==1);
        f.closing();auto*p=&f.process;
        assert(!f.closeApplicationProcess(f.client,f.execution,p)&&!p&&!f.s.processSelected&&f.process.retired&&!f.process.asidHeld_);
        assert(f.domain.transitions==4); // 1 Select + RestoreKernel + DetachVm + RetireDetached!
        ++controls;
    }}

    // 2. Late fault after Wait expiry or Map/Submit still stops ring and returns kIOReturnNotReady, retaining mappings!
    {{
        ZornGen7HostRing26 f;f.pendingSelected();
        ZornGen7AppExecution26*scope=nullptr;
        assert(!f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Wait,scope));
        f.expiry();faultAfterOutstanding=&f.domain.fault;
        auto raw=f.finishApplicationOperation(*scope,kIOReturnTimeout);
        assert(raw==kIOReturnNotReady&&f.s.stopped&&f.s.processSelected==&f.process&&f.process.liveMappings==3);
        ++controls;
    }}

    // 3. Non-zero errors (BadArgument / IOError / Timeout without expiry) do NOT retain silently; they RestoreKernel or stop!
    {{
        ZornGen7HostRing26 f;ZornGen7AppExecution26*scope=nullptr;
        assert(!f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Map,scope));
        assert(f.finishApplicationOperation(*scope,kIOReturnBadArgument)==kIOReturnBadArgument&&!f.s.processSelected&&f.process.state_.detached);
        ++controls;
    }}
    for(IOReturn raw:{{kIOReturnIOError,kIOReturnNotReady,kIOReturnNotPermitted,kIOReturnTimeout}}){{
        ZornGen7HostRing26 f;ZornGen7AppExecution26*scope=nullptr;
        assert(!f.beginApplicationOperation(f.client,ZornGen7AppOperation26::Submit,scope));
        assert(f.finishApplicationOperation(*scope,raw)&&f.s.stopped&&f.s.processSelected==&f.process&&f.domain.transitions==1&&f.process.liveMappings==3);
        ++controls;
    }}

    // 4. Multi-client switching (client1 <-> client2) cleanly restores kernel context before selecting the other client!
    {{
        ZornGen7HostRing26 f;ZornGen7AppIoClient26 second;ZornGen7AppExecution26 execution2;ZornGen7ProcessTables26 process2;
        const auto task2=reinterpret_cast<void*>(3);
        second.owner_=&f;second.service_=&f.service;second.provider=&f.service;second.openingTask_=task2;
        execution2.client_=&second;execution2.task_=task2;execution2.ring_=&f;execution2.maps_=&f.s.maps;execution2.oob_=&f.s.physicalOob.value;execution2.ringNext_=&f.execution;f.s.appExecutions=&execution2;
        process2.ringOwner_=&f;process2.domain_=&f.domain;process2.clientOwner_=&second;process2.clientTask_=task2;process2.asid_=43;process2.ringNext_=&f.process;f.s.processClients=&process2;
        for(unsigned i=0;i<6;++i){{
            const bool next=i&1;callerTask=next?task2:f.execution.task_;
            auto&client=next?second:f.client;auto*expected=next?&process2:&f.process;
            ZornGen7AppExecution26*scope=nullptr;
            assert(!f.beginApplicationOperation(client,ZornGen7AppOperation26::Map,scope)&&f.s.processSelected==expected);
            assert(!f.finishApplicationOperation(*scope,0)&&f.s.processSelected==expected&&!expected->state_.detached);
        }}
        // Restore cleanly when finished
        IOLockLock(f.s.appSerial);__atomic_store_n(&f.s.appSerialThread,current_thread(),__ATOMIC_RELEASE);
        assert(!f.restoreCompletedApplicationContext()&&!f.s.processSelected);
        __atomic_store_n(&f.s.appSerialThread,THREAD_NULL,__ATOMIC_RELEASE);IOLockUnlock(f.s.appSerial);
        callerTask=reinterpret_cast<void*>(2);
        f.s.appExecutions=&f.execution;f.s.processClients=&f.process;
        ++controls;
    }}

    // 5. Concurrent multi-thread TSan serialization across retained Map/Submit/Wait and context-free CpuView!
    {{
        ZornGen7HostRing26 f;
        std::atomic<unsigned>active{{0}},maximum{{0}},done{{0}};
        std::vector<std::thread>threads;
        for(unsigned i=0;i<12;++i){{
            threads.emplace_back([&,i]{{
                for(unsigned n=0;n<8;++n){{
                    const bool ctxFree=(n&1)!=0;
                    const auto op=ctxFree?ZornGen7AppOperation26::CpuView:ZornGen7AppOperation26::Map;
                    ZornGen7AppExecution26*scope=nullptr;
                    assert(!f.beginApplicationOperation(f.client,op,scope,nullptr,!ctxFree));
                    auto c=++active;maximum=std::max(maximum.load(),c);std::this_thread::yield();--active;
                    assert(!f.finishApplicationOperation(*scope,0));
                    ++done;
                }}
            }});
        }}
        for(auto&t:threads)t.join();
        assert(done==96&&maximum==1&&f.domain.transitions==1&&f.s.processSelected==&f.process);
        ++controls;
    }}

    std::printf("PASS303 context-retain controls=%u;100 frames=1 Select;handover/Close/fault/TSan verified\\n",controls);
    return 0;
}}
'''
    cpp_path = O / 'fixture.cpp'
    cpp_path.write_text(cpp_code)
    bin_path = O / 'fixture'
    san = ['-fsanitize=address,undefined', '-fno-omit-frame-pointer'] if a.sanitizer == 'asan' else ['-fsanitize=thread']
    cmd = ['xcrun', 'clang++', '-std=c++17', '-O1', '-g', '-pthread', *san, str(cpp_path), '-o', str(bin_path)]
    env = dict(os.environ, ASAN_OPTIONS='symbolize=0', UBSAN_OPTIONS='symbolize=0:halt_on_error=1', TSAN_OPTIONS='symbolize=0')
    subprocess.run(cmd, env=env, check=True)
    res = subprocess.run([str(bin_path)], env=env, capture_output=True, text=True, check=True)
    header = S / 'ZornActiveContextRetain303.h'
    report = dict(
        passed=True,
        sanitizer=a.sanitizer,
        phone_access=False,
        single_client_100_frames_transitions=1,
        multi_client_handover_verified=True,
        close_teardown_verified=True,
        fault_retention_verified=True,
        source_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),
        ring_sha256=hashlib.sha256((S / 'ZornGen7HostRing26.cpp').read_bytes()).hexdigest(),
        output=res.stdout,
    )
    (O / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(res.stdout, end='')


if __name__ == '__main__':
    main()

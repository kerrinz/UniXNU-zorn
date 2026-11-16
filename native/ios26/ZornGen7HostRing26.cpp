#include "ZornClientTrace240.h"
extern "C" volatile uint32_t native_adreno_trace_stage;
/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include "ZornGen7HostRing26.h"
#include "ZornApplicationObservation26.h"
#include "ZornGen7AppExecution26.h"
#include "ZornGen7Present26.h"
#include "ZornGen7TaskAdmission26.h"
#include "ZornGen7ProcessTables26.h"
#include "ZornGen7ZapOwner26.h"
#include "ZornGen7CpBootstrapAuthority26.h"
#include "direct-ring/NativeAdrenoRing.h"
#include "direct-runtime/ZornGen7DirectSubmit26.h"
#include "ZornGen7DirectRuntimeAuthority26.h"
#include "direct-runtime/K80KnownImage26.h"
#include "direct-runtime/ZornGen7DirectClient26.h"
#include "direct-runtime/ZornGen7DirectIo26.h"
#include "direct-runtime/ZornGen7AppIo26.h"
#include <string.h>
extern "C" IOReturn ZornGen7CopyKnownImageToBootConsole26(const uint8_t *,size_t);
#include "ZornGen7InactiveOwner26.h"
#include "ZornGen7RegisterMaps26.h"
#include "ZornGen7GpuIrq26.h"
#include "ZornGen7GmuIrq26.h"
#include "ZornGen7HwschedHfi26.h"
#include "ZornGen7DirectHfi26.h"
#include "ZornGen7SmmuDomain26.h"
#include "ZornGen7HostGpuRegisters26.h"
#include "ZornGen7FirmwareAssets26.h"
#include "GpuCodeMemory.h"
#include "direct-ring/GpuHostRing.h"
#include <IOKit/IOLib.h>
#include <kern/clock.h>
#include <kern/task.h>
#include <kern/task_ref.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
OSDefineMetaClassAndStructors(ZornGen7HostRing26,OSObject)
static unsigned nativeKernelClientObservation[40];
extern "C" void Zorn26RecordKernelClientResult(unsigned raw){nativeKernelClientObservation[0]=raw;}
extern "C" void zorn26_native_kernel_client_observation(unsigned (&out)[40])
{for(unsigned i=0;i<40;++i)out[i]=nativeKernelClientObservation[i];}
static unsigned nativeKnownImageObservation[32];
extern "C" void Zorn26RecordKnownImageResult(unsigned raw){nativeKnownImageObservation[0]=raw;}
extern "C" void zorn26_native_known_image_observation(unsigned (&out)[32])
{for(unsigned i=0;i<32;++i)out[i]=nativeKnownImageObservation[i];}
namespace {
// This root lives for the actual initialized GPU's lifetime,not a connection.
// Registry lock precedes issuer;native operations never acquire the registry
// while holding issuer. It also covers CPU frames BEFORE the first binding,
// so first activation cannot race a legacy token-0 unprotected CPU copy.
IOLock *presentationRegistry=nullptr;
ZornGen7HostRing26 *presentationOwner=nullptr;
thread_t presentationThread=THREAD_NULL;
bool presentationIssuerHeld=false;
IOLock *presentationLock(){
    auto *p=__atomic_load_n(&presentationRegistry,__ATOMIC_ACQUIRE);if(p)return p;
    auto *fresh=IOLockAlloc();if(!fresh)return nullptr;
    IOLock *expected=nullptr;
    if(!__atomic_compare_exchange_n(&presentationRegistry,&expected,fresh,false,__ATOMIC_RELEASE,__ATOMIC_ACQUIRE)){
        IOLockFree(fresh);return expected;
    }
    return fresh;
}
bool normal(){return preemption_enabled() && !ml_at_interrupt_context() && ml_get_interrupts_enabled();}
// Actual external-method calling context,not a guessed process or successful
// handle. Hold it across issuer waits and the complete synchronous import.
struct CallerTaskReference {
    task_t task;
    CallerTaskReference():task(current_task()){if(task)task_reference(task);}
    ~CallerTaskReference(){if(task)task_deallocate(task);}
    CallerTaskReference(const CallerTaskReference &)=delete;
    CallerTaskReference &operator=(const CallerTaskReference &)=delete;
};
}
static uint32_t nativeBootstrapObservation[16];
void Zorn26RecordBootstrapResult(IOReturn raw){nativeBootstrapObservation[0]=uint32_t(raw);}
extern "C" void zorn26_native_bootstrap_observation(uint32_t (&out)[16]){memcpy(out,nativeBootstrapObservation,sizeof(out));}
static uint32_t nativeCpObservation[8];
void Zorn26RecordCpResult(IOReturn raw){nativeCpObservation[0]=uint32_t(raw);}
extern "C" void zorn26_native_cp_observation(uint32_t (&out)[8]){memcpy(out,nativeCpObservation,sizeof(out));}
struct ZornGen7HostRing26::Storage {
    IORecursiveLock &gate;FhgStorage &graph;HoujiFullHostNativeMemory &memory;ZornGen7InactiveOwner26 &parent;
    ZornGen7RegisterMaps26 &maps;ZornGen7GpuIrq26 &irq;ZornGen7GmuIrq26 &gmu;OSObject &hfiOwner;bool (*transportHalted)(const OSObject &);ZornGen7HwschedHfi26 *hfi;
    bool hfiHalted() const{return transportHalted(hfiOwner);}
    ZornGen7SmmuDomain26 &domain;ZornGen7HostGpuRegisters26 &registers;OSObject &authorityOwner;const ZornGen7CpStartAuthority26 authority;
    IOLock *waitGate=nullptr;uint32_t stopped=0,phase=0,irqCandidates=0;bool attempted=false,initialIdle=false;
    FhgGraph logical{};FhgRange poolRange{},recordRange{};hhr_result ring{};
    bool grantReturned=false,publishReturned=false;IOReturn grantRaw=kIOReturnNotReady,publishRaw=kIOReturnNotReady;
    int ioRaw=0;bool ioReturned=false;uint32_t ioAddress=0;bool ioWrite=false;
    void *ringCpu=nullptr;size_t ringOffset=0;uint64_t deadline=0;
    ZornGen7ZapOwner26 *zap=nullptr;OSObject *bootstrapAuthorityOwner=nullptr;ZornGen7CpBootstrapAuthority26 bootstrapAuthority{};
    bool successOobAttempted=false,successOobReturned=false;IOReturn successOobRaw=kIOReturnNotReady;
    bool bootstrapAttempted=false,bootstrapGrantReturned=false,modeIdle=false,contextIdle=false,contextRestored=false,nativeAdopted=false,bootstrapComplete=false;
    IOReturn bootstrapGrantRaw=kIOReturnNotReady,nativeRaw=kIOReturnNotReady,acquireRaw=kIOReturnNotReady;
    IOLock *issuer=nullptr;thread_t issuerThread=THREAD_NULL,kernelClientGrantThread=THREAD_NULL;OSObject *runtimeOwner=nullptr;ZornGen7DirectRuntimeAuthority26 runtimeAuthority{};
    bool kernelTaskAttempted=false,kernelTaskActive=false,kernelTaskGrantReturned=false,kernelTaskComplete=false,imageVerified=false,imageUnmapped=false,taskReleaseAllowed=false;
    IOReturn kernelTaskGrantRaw=kIOReturnNotReady,kernelTaskRaw=kIOReturnNotReady;unsigned kernelPhase=0;
    thread_t kernelTaskThread=THREAD_NULL;
    bool nativeTableLease=false;unsigned nativeTableAcquires=0,nativeTableReleases=0;
    bool consoleImageAttempted=false;
    ZornGen7ProcessTables26 *processSelected=nullptr,*processClients=nullptr,*kernelProcess=nullptr;
    ZornGen7ProcessTables26 *nativeProcessTableLease=nullptr;
    uint32_t nativeProcessTableAcquires=0,nativeProcessTableReleases=0;
    size_t runtimeCapacity=0;bool kernelProcessReady=false,kernelProcessClosing=false;
    thread_t processTransitionThread=THREAD_NULL;
    ZornGen7ProcessTableOperation26 processTransitionOperation=ZornGen7ProcessTableOperation26::Prepare;
    ZornGen7AppExecution26 *appExecution=nullptr;bool appExecutionPending=false;
    IOUserClient *appAuthorityClient=nullptr;task_t appAuthorityTask=TASK_NULL;
    thread_t appAuthorityThread=THREAD_NULL;unsigned appAuthorityPhase=0;
    ZornGen7AppOperation26 appAuthorityOperation=ZornGen7AppOperation26::PrepareTables;
    void setAppAuthorityCall(IOUserClient &client,task_t task,unsigned phase,ZornGen7AppOperation26 op){
        appAuthorityClient=&client;appAuthorityTask=task;appAuthorityPhase=phase;appAuthorityOperation=op;
        __atomic_store_n(&appAuthorityThread,current_thread(),__ATOMIC_RELEASE);
    }
    void clearAppAuthorityCall(){
        __atomic_store_n(&appAuthorityThread,THREAD_NULL,__ATOMIC_RELEASE);
        appAuthorityClient=nullptr;appAuthorityTask=TASK_NULL;appAuthorityPhase=0;
    }
    bool appOobTransition=false,appOobActive=false;thread_t appReleaseIdleThread=THREAD_NULL,appOobThread=THREAD_NULL;
    bool appOperationPending=false;thread_t appOperationThread=THREAD_NULL;
    ZornGen7AppOperation26 appOperationKind=ZornGen7AppOperation26::PrepareTables;
    bool appFenceWaitExpired=false; // Under issuer; set only by a healthy WaitFence expiration.
    NativeAdrenoMemory imageMemory;uint64_t imageIova=0,imageHandle=0;uint32_t imageFence=0;hgki_result imageResult{};
    IOService *kernelIoService=nullptr,*applicationIoService=nullptr;bool applicationIoPublishAttempted=false;
    IOUserClient *kernelIoConnection=nullptr;
    // One real kernel IOUserClient probe. Failed maps/client references remain
    // held here; this is not the userspace Mach mapping registry.
    bool clientProbeAttempted=false;thread_t clientProbeThread=THREAD_NULL;
    IOUserClient *clientProbe=nullptr;IOMemoryMap *clientProbeMap=nullptr;
    uint32_t clientProbePhase=0,clientProbeFlags=0,clientProbeMethod=0;
    IOReturn clientProbeMethodRaw=kIOReturnNotReady,clientProbeUnmapRaw=kIOReturnNotReady,clientProbeCloseRaw=kIOReturnNotReady;
    uint64_t clientProbeHandle=0,clientProbeIova=0;uint32_t clientProbeToken=0,clientProbeFence=0,clientProbeAsid=0;
    hgki_result clientProbeResult{};
    task_t kernelTaskOwner=TASK_NULL; // borrowed through retained actual IOUserClient
    bool kernelIoPublishAttempted=false,kernelIoAttempted=false,kernelIoActive=false,kernelIoGrantReturned=false,kernelIoClosing=false,kernelIoClosed=false,kernelIoReleaseAllowed=false;
    IOReturn kernelIoGrantRaw=kIOReturnNotReady;unsigned kernelIoPhase=0;
    // Atomic presentation view of runtime construction:0not-started,1preparing,2ready,3failed.
    uint32_t presentationRuntimeState=0;
    bool runtimeAttempted=false,runtimeReady=false;ZornGen7DirectVm26 runtimeVm;
    ZornGen7PresentProgress26 presentProgress;
    ZornGen7DirectSubmit26 runtimeSubmit;
    uint32_t firstContext[25]{};NativeAdrenoRing native;uint32_t nativeFence=0,nativeObserved=0;NativeAdrenoRingFence nativeWait=NativeAdrenoRingFenceArgument;
    // Record the actual IOLock owner. This token alone is not a GPU grant.
    void lockIssuer(){IOLockLock(issuer);__atomic_store_n(&issuerThread,current_thread(),__ATOMIC_RELEASE);}
    void unlockIssuer(){__atomic_store_n(&issuerThread,THREAD_NULL,__ATOMIC_RELEASE);IOLockUnlock(issuer);}
    bool issuerHeld() const{return __atomic_load_n(&issuerThread,__ATOMIC_ACQUIRE)==current_thread() && current_thread()!=THREAD_NULL;}
    Storage(IORecursiveLock &g,FhgStorage &f,HoujiFullHostNativeMemory &m,ZornGen7InactiveOwner26 &p,
        ZornGen7RegisterMaps26 &v,ZornGen7GpuIrq26 &i,ZornGen7GmuIrq26 &q,OSObject &h,bool (*halted)(const OSObject &),ZornGen7HwschedHfi26 *legacy,
        ZornGen7SmmuDomain26 &d,ZornGen7HostGpuRegisters26 &r,OSObject &o,const ZornGen7CpStartAuthority26 &a):
        gate(g),graph(f),memory(m),parent(p),maps(v),irq(i),gmu(q),hfiOwner(h),transportHalted(halted),hfi(legacy),domain(d),registers(r),authorityOwner(o),authority(a){}
    static void *operator new(size_t,void *p)noexcept{return p;}
};
IOReturn ZornGen7HostRing26::create(IORecursiveLock &g,FhgStorage &f,HoujiFullHostNativeMemory &m,
    ZornGen7InactiveOwner26 &p,ZornGen7RegisterMaps26 &v,ZornGen7GpuIrq26 &i,ZornGen7GmuIrq26 &q,
    ZornGen7HwschedHfi26 &h,ZornGen7SmmuDomain26 &d,ZornGen7HostGpuRegisters26 &r,OSObject &o,
    const ZornGen7CpStartAuthority26 &a,ZornGen7HostRing26 *&out)
{return createImpl(g,f,m,p,v,i,q,h,[](const OSObject &x){return static_cast<const ZornGen7HwschedHfi26 &>(x).halted();},&h,d,r,o,a,out);}
IOReturn ZornGen7HostRing26::create(IORecursiveLock &g,FhgStorage &f,HoujiFullHostNativeMemory &m,
    ZornGen7InactiveOwner26 &p,ZornGen7RegisterMaps26 &v,ZornGen7GpuIrq26 &i,ZornGen7GmuIrq26 &q,
    ZornGen7DirectHfi26 &h,ZornGen7SmmuDomain26 &d,ZornGen7HostGpuRegisters26 &r,OSObject &o,
    const ZornGen7CpStartAuthority26 &a,ZornGen7HostRing26 *&out)
{return createImpl(g,f,m,p,v,i,q,h,[](const OSObject &x){return static_cast<const ZornGen7DirectHfi26 &>(x).halted();},nullptr,d,r,o,a,out);}
IOReturn ZornGen7HostRing26::createImpl(IORecursiveLock &g,FhgStorage &f,HoujiFullHostNativeMemory &m,
    ZornGen7InactiveOwner26 &p,ZornGen7RegisterMaps26 &v,ZornGen7GpuIrq26 &i,ZornGen7GmuIrq26 &q,
    OSObject &h,bool (*halted)(const OSObject &),ZornGen7HwschedHfi26 *legacy,ZornGen7SmmuDomain26 &d,ZornGen7HostGpuRegisters26 &r,OSObject &o,
    const ZornGen7CpStartAuthority26 &authority,ZornGen7HostRing26 *&out)
{
    if(!halted || halted(h) || out || !normal() || !IORecursiveLockHaveLock(&g) || !authority.acquireExclusiveCpInitialization)return kIOReturnNotReady;
    auto *n=new ZornGen7HostRing26;if(!n)return kIOReturnNoMemory;
    if(!n->init()){n->release();return kIOReturnNoMemory;}n->retain();n->pinned_=true;out=n;
    p.retain();v.retain();i.retain();q.retain();h.retain();d.retain();r.retain();o.retain();
    void *bytes=IOMallocZero(sizeof(Storage));if(!bytes)return kIOReturnNoMemory;
    n->storage_=new(bytes)Storage(g,f,m,p,v,i,q,h,halted,legacy,d,r,o,authority);n->storage_->waitGate=IOLockAlloc();n->storage_->issuer=IOLockAlloc();
    if(!n->storage_->waitGate || !n->storage_->issuer)return kIOReturnNoMemory;
    const auto raw=n->prepare();auto &s=*n->storage_;
    nativeCpObservation[0]=uint32_t(raw);nativeCpObservation[1]=s.phase |
        (s.grantReturned?1u<<8:0u) | (s.publishReturned?1u<<9:0u);
    nativeCpObservation[2]=s.ring.configured;nativeCpObservation[3]=s.ring.enabled;
    nativeCpObservation[4]=s.ring.rptr;nativeCpObservation[5]=s.ring.wptr;
    nativeCpObservation[6]=uint32_t(s.ioRaw);nativeCpObservation[7]=s.ioAddress;return raw;
}
IOReturn ZornGen7HostRing26::prepare()
{
    auto &s=*storage_;if(s.attempted || !normal() || !IORecursiveLockHaveLock(&s.gate))return kIOReturnNotReady;s.attempted=true;
    if(s.irq.halted() || s.gmu.halted() || s.hfiHalted() || s.domain.faulted() || !s.memory.prepared() ||
       fhg_graph(&s.graph,sizeof(s.graph),1,&s.logical,sizeof(s.logical)) || s.logical.graph!=1 ||
       s.logical.input_bits!=32 || s.logical.output_bits!=36 || s.logical.upper_region || s.logical.range_count!=12 ||
       !s.logical.audit_complete || s.logical.build_status || s.logical.audit_status)return kIOReturnNotReady;
    const auto &entry=s.memory.entry(FHG_GPU_POOL_SLOT);const auto &pool=s.memory.bo(FHG_GPU_POOL_SLOT);const auto &code=s.memory.bo(FHG_CODE_SLOT);
    if(!entry.allocated || !entry.validated || !entry.published || entry.status || !entry.nc || !entry.request.normal_nc ||
       !pool.backed() || pool.quarantined() || pool.imported() || pool.readOnly() || !pool.writeCombined() || pool.deviceReferences()!=1 ||
       !pool.mapping() || !pool.descriptor() || pool.bytes()!=0x100000 || pool.ownedBytes()!=0x100000 ||
       pool.descriptor()->getLength()!=pool.ownedBytes() || pool.bytes()!=entry.request.logical_bytes || pool.ownedBytes()!=entry.request.owned_bytes ||
       pool.mapping()!=entry.backing.cpu || pool.spanCount()!=1 || pool.ownedSpanCount()!=1 || pool.spans()[0].offset ||
       pool.ownedSpans()[0].offset || pool.spans()[0].physical!=entry.backing.physical ||
       pool.ownedSpans()[0].physical!=entry.backing.owned_physical || pool.spans()[0].physical!=pool.ownedSpans()[0].physical ||
       pool.spans()[0].bytes!=pool.bytes() || pool.ownedSpans()[0].bytes!=pool.ownedBytes() ||
       !code.descriptor() || !ZornGen7ValidateConfiguredGpuCode26(code) || !s.registers.verifyRecord(code))return kIOReturnNotReady;
    if(fhg_range(&s.graph,sizeof(s.graph),1,8,&s.poolRange,sizeof(s.poolRange)) ||
       s.poolRange.iova!=HHR_RING || s.poolRange.physical!=pool.spans()[0].physical+0xc0000 || s.poolRange.bytes!=0x40000 ||
       s.poolRange.permissions!=(ArmSmmu4KRead|ArmSmmu4KWrite|ArmSmmu4KPrivileged) || s.poolRange.writeback || s.poolRange.shareability!=3 || s.poolRange.reserved ||
       fhg_range(&s.graph,sizeof(s.graph),1,11,&s.recordRange,sizeof(s.recordRange)) || s.recordRange.iova!=HHR_RECORD ||
       s.recordRange.physical!=code.spans()[0].physical+HCC_RECORD_OFFSET || s.recordRange.bytes!=4096 ||
       s.recordRange.permissions!=(ArmSmmu4KRead|ArmSmmu4KWrite|ArmSmmu4KPrivileged) || s.recordRange.writeback || s.recordRange.shareability!=3 || s.recordRange.reserved)return kIOReturnNotReady;
    s.ringOffset=0xc0000;s.ringCpu=static_cast<uint8_t *>(pool.mapping())+s.ringOffset;
    if(!s.maps.bindHostRing(*this,s.parent,s.irq))return kIOReturnNotReady;
    IORecursiveLockUnlock(&s.gate);
    s.grantRaw=s.maps.acquireHostCpWindow(s.authorityOwner,s.authority,*pool.descriptor(),*code.descriptor());s.grantReturned=true;
    IORecursiveLockLock(&s.gate);if(s.grantRaw || s.irq.halted() || s.gmu.halted() || s.hfiHalted() || s.domain.faulted())return s.grantRaw?s.grantRaw:kIOReturnNotReady;
    // All actual CP/IRQ work and waits are outside startup/workloop gates.
    __atomic_store_n(&s.phase,1u,__ATOMIC_RELEASE);IORecursiveLockUnlock(&s.gate);
    const auto raw=runInitialization();
    if(raw){__atomic_store_n(&s.stopped,1u,__ATOMIC_RELEASE);s.irq.stopAndMask();}
    IORecursiveLockLock(&s.gate);s.initialIdle=raw==kIOReturnSuccess;return raw;
}
int ZornGen7HostRing26::guard(void *context)
{
    auto *o=static_cast<ZornGen7HostRing26 *>(context);if(!o || !o->storage_ || !normal())return 1;auto &s=*o->storage_;
    uint64_t now=0;if(s.deadline)clock_get_uptime(&now);
    return (s.appOobActive && !o->applicationOperationHeld() &&
        !(s.appOobTransition && s.appOobThread==current_thread())) ||
        (s.kernelIoActive && !o->kernelClientExecutionHealthy()) || (s.kernelTaskActive && !o->kernelTaskExecutionHealthy()) || (s.deadline && now>s.deadline) || (IORecursiveLockHaveLock(&s.gate) &&
        !(!s.hfi && ((s.kernelTaskThread==current_thread() && s.kernelTaskActive && s.kernelPhase==3 && !s.nativeTableLease) ||
            (s.issuerHeld() && (s.kernelIoActive || o->applicationOperationHeld()) && !s.nativeProcessTableLease &&
             s.domain.nativeProcessSubmissionHeldForRing(*o))))) || !s.grantReturned || s.grantRaw || __atomic_load_n(&s.stopped,__ATOMIC_ACQUIRE) ||
        s.irq.halted() || s.gmu.halted() || s.hfiHalted() || s.domain.faulted();
}
int ZornGen7HostRing26::read(void *context,uint32_t at,uint32_t *out)
{
    if(!out || guard(context) || at<0x3d00000 || (at&3u))return 1;auto &s=*static_cast<ZornGen7HostRing26 *>(context)->storage_;
    uint32_t value=0;s.ioReturned=false;s.ioAddress=at;s.ioWrite=false;s.ioRaw=s.irq.accessRingWord((at-0x3d00000)/4,false,value);s.ioReturned=true;
    if(!s.ioRaw)*out=value;return s.ioRaw;
}
int ZornGen7HostRing26::write(void *context,uint32_t at,uint32_t value)
{
    if(guard(context) || at<0x3d00000 || (at&3u))return 1;auto &s=*static_cast<ZornGen7HostRing26 *>(context)->storage_;
    s.ioReturned=false;s.ioAddress=at;s.ioWrite=true;s.ioRaw=s.irq.accessRingWord((at-0x3d00000)/4,true,value);s.ioReturned=true;return s.ioRaw;
}
int ZornGen7HostRing26::publish(void *context,unsigned at,const uint32_t *words,unsigned count)
{
    if(guard(context) || !words || at || count!=10)return 1;auto &s=*static_cast<ZornGen7HostRing26 *>(context)->storage_;
    const uint32_t expected[]={0x70970001,0x08000000,0x70c80007,0x94b,3,0x20000000,2,HHR_RECORD,0,0x80000000};
    for(unsigned i=0;i<count;++i)if(words[i]!=expected[i])return 1;
    auto *to=static_cast<volatile uint32_t *>(s.ringCpu);for(unsigned i=0;i<HHR_WORDS;++i)if(to[i])return 1;
    for(unsigned i=0;i<count;++i)to[i]=words[i];for(unsigned i=0;i<HHR_WORDS;++i)if(to[i]!=(i<count?words[i]:0))return 1;
    auto &pool=const_cast<NativeAdrenoMemory &>(s.memory.bo(FHG_GPU_POOL_SLOT));
    s.publishRaw=pool.publishForDevice(s.ringOffset,HHR_BYTES,true);s.publishReturned=true;
    __asm__ volatile("dsb sy" ::: "memory");return s.publishRaw || guard(context);
}
int ZornGen7HostRing26::delay(void *context,unsigned us)
{
    if(guard(context) || (us!=10 && us!=100))return 1;auto &s=*static_cast<ZornGen7HostRing26 *>(context)->storage_;
    // The checked native submit may hold the metadata gate for its short
    // fenced-WPTR store. Never sleep waiting for an IRQ while retaining it.
    if(IORecursiveLockHaveLock(&s.gate)){IODelay(us);return guard(context);}
    uint64_t deadline=0;clock_interval_to_deadline(us,NSEC_PER_USEC,&deadline);IOLockLock(s.waitGate);
    if(!__atomic_load_n(&s.stopped,__ATOMIC_ACQUIRE))(void)IOLockSleepDeadline(s.waitGate,&s.irqCandidates,deadline,THREAD_UNINT);
    IOLockUnlock(s.waitGate);return guard(context);
}
int ZornGen7HostRing26::consume(OSObject &object,const NativeAdrenoIrqResult &actual)
{
    auto *o=OSDynamicCast(ZornGen7HostRing26,&object);if(!o || !o->storage_)return 1;auto &s=*o->storage_;
    if(__atomic_load_n(&s.stopped,__ATOMIC_ACQUIRE) || !__atomic_load_n(&s.phase,__ATOMIC_ACQUIRE) ||
       (actual.flags&(NativeAdrenoIrqFatal|NativeAdrenoIrqPreempt)))return 1;
    // Wake the real bounded hardware observation worker. IRQ is never treated
    // as a timestamp value,CP initialization success or permission to retire.
    IOLockLock(s.waitGate);++s.irqCandidates;IOLockWakeup(s.waitGate,&s.irqCandidates,false);IOLockUnlock(s.waitGate);return 0;
}
IOReturn ZornGen7HostRing26::runInitialization()
{
    if(guard(this))return kIOReturnNotReady;auto &s=*storage_;auto &r=s.ring;r.started=1;r.retained=1;
    uint32_t sqe=0;if(read(this,0x3d02020,&sqe) || sqe)return kIOReturnNotReady;
    const uint32_t codeRegs[]={0x3d020c0,0x3d020c4,0x3d02dc0,0x3d02dc4};
    const uint32_t codeWant[]={HCC_IOVA+HCC_SQE_OFFSET,0,HCC_IOVA+HCC_AQE_OFFSET,0};
    for(unsigned i=0;i<4;++i){uint32_t actual=0;if(read(this,codeRegs[i],&actual) || actual!=codeWant[i])return kIOReturnNotReady;}
    // Native1s deadline bounds original10k*100us idle observations as a whole.
    clock_interval_to_deadline(1000,NSEC_PER_MSEC,&s.deadline);
    // Fresh actual CPU ranges only;no synthetic successful backing/addresses.
    const auto &pool=s.memory.bo(FHG_GPU_POOL_SLOT);auto *scratch=static_cast<const volatile uint8_t *>(pool.mapping())+0xc8000;
    for(unsigned i=0;i<4096;++i)if(scratch[i])return kIOReturnNotReady;
    const uint32_t address[]={0x3d02000,0x3d02004,0x3d02008,0x3d02010,0x3d02014,0x3d02a60,0x3d02a64};
    const uint32_t value[]={HHR_RING,0,0x20c,HHR_SCRATCH+0x100,0,HHR_SCRATCH+0x108,0};
    for(unsigned i=0;i<7;++i){uint32_t actual=0;if(write(this,address[i],value[i]) || read(this,address[i],&actual) || actual!=value[i])return kIOReturnIOError;++r.configured;}
    if(read(this,0x3d02018,&r.rptr) || read(this,0x3d0201c,&r.wptr) || r.rptr || r.wptr)return kIOReturnNotReady;
    const uint32_t init[]={0x70970001,0x08000000,0x70c80007,0x94b,3,0x20000000,2,HHR_RECORD,0,0x80000000};
    if(publish(this,0,init,10))return kIOReturnIOError;
    auto raw=s.irq.bindReceiver(*this,consume);if(raw)return raw;
    raw=s.irq.armBoundReceiver();if(raw || guard(this))return raw?raw:kIOReturnNotReady;
    // Attempted BEFORE the enable store;an unknown result never opens retry.
    r.enabled=1;__atomic_store_n(&s.phase,2u,__ATOMIC_RELEASE);
    if(write(this,0x3d02020,1) || read(this,0x3d02020,&r.sqe) || r.sqe!=1)return kIOReturnIOError;
    hhr_io io{};io.cookie=this;io.guard=guard;io.read=read;io.write=write;io.delay=delay;
    r.wptr=10;r.code=hhr_kick(&io,&r);if(r.code || guard(this))return kIOReturnIOError;
    r.code=hhr_idle(&io,&r);if(r.code || guard(this) || r.rptr!=10)return kIOReturnNotReady;
    r.init_idle=1;__atomic_store_n(&s.phase,3u,__ATOMIC_RELEASE);return kIOReturnSuccess;
    // Actual initial idle only. No timestamp fence,normal memory canary,ZAP,
    // mode packet,NativeRing adoption or OOB release is synthesized here.
}
void ZornGen7HostRing26::free(){if(pinned_)return;OSObject::free();}

bool ZornGen7HostRing26::zapWindowHealthy() const
{
    if(!storage_ || !normal())return false;const auto &s=*storage_;
    return s.grantReturned && !s.grantRaw && !__atomic_load_n(&s.stopped,__ATOMIC_ACQUIRE) &&
        s.initialIdle && !s.irq.halted() && !s.gmu.halted() && !s.hfiHalted() && !s.domain.faulted();
}
bool ZornGen7HostRing26::claimInitialIdleForZap()
{
    if(!zapWindowHealthy())return false;auto &s=*storage_;
    if(IORecursiveLockHaveLock(&s.gate) || __atomic_load_n(&s.phase,__ATOMIC_ACQUIRE)!=3)return false;
    __atomic_store_n(&s.phase,4u,__ATOMIC_RELEASE);clock_interval_to_deadline(1000,NSEC_PER_MSEC,&s.deadline);
    uint32_t sqe=0,rptr=0,wptr=0;
    if(read(this,0x3d02020,&sqe) || sqe!=1 || read(this,0x3d02018,&rptr) || rptr!=10 ||
       read(this,0x3d0201c,&wptr) || wptr!=10)return false;
    hhr_io io{};io.cookie=this;io.guard=guard;io.read=read;io.write=write;io.delay=delay;
    if(hhr_idle(&io,&s.ring) || s.ring.rptr!=10 || guard(this))return false;
    s.deadline=0;return true; // Initial polling deadline is not an SMC timeout.
}

bool ZornGen7HostRing26::bootstrapHealthy() const
{
    if(!zapWindowHealthy())return false;const auto &s=*storage_;
    return s.zap && s.zap->authenticatedForRing(*this) && s.bootstrapGrantReturned && !s.bootstrapGrantRaw;
}
IOReturn ZornGen7HostRing26::completeAuthenticatedBootstrap(ZornGen7ZapOwner26 &zap,OSObject &owner,
    const ZornGen7CpBootstrapAuthority26 &authority)
{

    if(!storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;
    auto *direct=OSDynamicCast(ZornGen7DirectHfi26,&s.hfiOwner);
    if(!s.hfi && (!direct || !direct->bootstrapOobHeld()))return kIOReturnNotReady;
    if(!IORecursiveLockHaveLock(&s.gate) || s.bootstrapAttempted || !s.initialIdle ||
       __atomic_load_n(&s.phase,__ATOMIC_ACQUIRE)!=4 || !zap.authenticatedForRing(*this) || !authority.acquireAuthenticatedBootstrap || !authority.authorizeSuccessfulOobRelease)return kIOReturnNotReady;
    s.bootstrapAttempted=true;zap.retain();owner.retain();s.zap=&zap;s.bootstrapAuthorityOwner=&owner;s.bootstrapAuthority=authority;
    IORecursiveLockUnlock(&s.gate);
    s.bootstrapGrantRaw=s.maps.acquireAuthenticatedCpBootstrap(owner,authority,
        *s.memory.bo(FHG_GPU_POOL_SLOT).descriptor(),*s.memory.bo(FHG_CODE_SLOT).descriptor(),zap);s.bootstrapGrantReturned=true;
    IOReturn raw=s.bootstrapGrantRaw;if(!raw)raw=runAuthenticatedBootstrap();
    if(!raw){s.successOobAttempted=true;s.successOobRaw=s.hfi?s.hfi->releaseHostGpuOobAfterBootstrap(*this):direct->releaseHostGpuOobAfterBootstrap(*this);
        s.successOobReturned=true;raw=s.successOobRaw;}
    if(raw){__atomic_store_n(&s.stopped,1u,__ATOMIC_RELEASE);s.irq.stopAndMask();}
    IORecursiveLockLock(&s.gate);s.bootstrapComplete=raw==kIOReturnSuccess;
    nativeBootstrapObservation[0]=uint32_t(raw);nativeBootstrapObservation[1]=s.phase;
    nativeBootstrapObservation[2]=uint32_t(s.bootstrapGrantRaw);
    nativeBootstrapObservation[3]=(s.modeIdle?1u:0u) | (s.contextIdle?2u:0u) | (s.contextRestored?4u:0u) |
        (s.nativeAdopted?8u:0u) | (s.bootstrapComplete?16u:0u) | (s.successOobAttempted?32u:0u) | (s.successOobReturned?64u:0u);
    nativeBootstrapObservation[4]=s.ring.rptr;nativeBootstrapObservation[5]=s.ring.wptr;
    nativeBootstrapObservation[6]=s.ring.writebacks;nativeBootstrapObservation[7]=s.ring.observed[0];nativeBootstrapObservation[8]=s.ring.observed[1];
    nativeBootstrapObservation[9]=uint32_t(s.nativeRaw);nativeBootstrapObservation[10]=s.nativeFence;nativeBootstrapObservation[11]=s.nativeObserved;
    nativeBootstrapObservation[12]=uint32_t(s.nativeWait);nativeBootstrapObservation[13]=uint32_t(s.successOobRaw);
    nativeBootstrapObservation[14]=s.ioAddress;nativeBootstrapObservation[15]=uint32_t(s.ioRaw);return raw;
}
IOReturn ZornGen7HostRing26::publishBootstrap(unsigned at,const uint32_t *words,unsigned count)
{
    if(!bootstrapHealthy() || guard(this) || !words || !count || count>25 || at!=storage_->ring.wptr || at>HHR_WORDS-count)return kIOReturnNotReady;
    auto &s=*storage_;uint32_t expected[25]{};unsigned n=0;
    if(!s.modeIdle && at==10){expected[0]=hhr_pkt7(0x66,1);expected[1]=0;n=2;}
    else if(s.modeIdle && !s.contextIdle && at==12){for(unsigned i=0;i<25;++i)expected[i]=s.firstContext[i];n=25;}
    else if(s.modeIdle && s.contextIdle && s.ring.writebacks<2 && at==12+25+5*s.ring.writebacks){
        expected[0]=hhr_pkt7(0x3d,3);expected[1]=HHR_SCRATCH+4*s.ring.writebacks;expected[2]=0;
        expected[3]=0xc0ffee00u+s.ring.writebacks;expected[4]=hhr_pkt7(0x12,0);n=5;
    }
    if(count!=n)return kIOReturnBadArgument;
    auto *to=static_cast<volatile uint32_t *>(s.ringCpu);
    for(unsigned i=0;i<count;++i)if(words[i]!=expected[i] || to[at+i])return kIOReturnNotReady;
    for(unsigned i=0;i<count;++i)to[at+i]=words[i];for(unsigned i=0;i<count;++i)if(to[at+i]!=words[i])return kIOReturnIOError;
    auto &pool=const_cast<NativeAdrenoMemory &>(s.memory.bo(FHG_GPU_POOL_SLOT));
    s.publishRaw=pool.publishForDevice(s.ringOffset,HHR_BYTES,true);s.publishReturned=true;__asm__ volatile("dsb sy" ::: "memory");return s.publishRaw;
}
IOReturn ZornGen7HostRing26::acquireScratch()
{
    if(!bootstrapHealthy() || guard(this))return kIOReturnNotReady;auto &s=*storage_;
    auto &pool=const_cast<NativeAdrenoMemory &>(s.memory.bo(FHG_GPU_POOL_SLOT));s.acquireRaw=pool.acquireDeviceWrites(0xc8000,4096);
    __asm__ volatile("dsb sy" ::: "memory");return s.acquireRaw;
}
int ZornGen7HostRing26::nativeRead(void *p,uint32_t word,uint32_t *out)
{
    auto &o=*static_cast<ZornGen7HostRing26 *>(p);if(!o.bootstrapHealthy() || word>0xffff)return 1;
    return read(p,0x3d00000+4*word,out);
}
int ZornGen7HostRing26::nativeWrite(void *p,uint32_t word,uint32_t value)
{
    auto &o=*static_cast<ZornGen7HostRing26 *>(p);if(!o.bootstrapHealthy() || guard(p) || word!=0x807)return 1;auto &s=*o.storage_;
    // Same source fenced-WPTR primitive as initial CP;no outer retry. The
    // current value is recorded BEFORE a possibly uncertain store.
    s.ring.wptr=value;hhr_io io{};io.cookie=p;io.guard=guard;io.read=read;io.write=write;io.delay=delay;
    return hhr_kick(&io,&s.ring);
}
int ZornGen7HostRing26::nativeBarrier(void *p)
{
    auto &o=*static_cast<ZornGen7HostRing26 *>(p);if(!o.bootstrapHealthy() || guard(p))return 1;__asm__ volatile("dsb sy" ::: "memory");return 0;
}
int ZornGen7HostRing26::nativePublish(void *p,const volatile uint32_t *words,size_t bytes)
{
    auto &o=*static_cast<ZornGen7HostRing26 *>(p);if(!o.bootstrapHealthy() || guard(p))return 1;auto &s=*o.storage_;
    if(words!=static_cast<volatile uint32_t *>(s.ringCpu) || bytes!=HHR_BYTES)return 1;
    auto &pool=const_cast<NativeAdrenoMemory &>(s.memory.bo(FHG_GPU_POOL_SLOT));s.publishRaw=pool.publishForDevice(s.ringOffset,HHR_BYTES,true);
    __asm__ volatile("dsb sy" ::: "memory");return s.publishRaw?1:0;
}
int ZornGen7HostRing26::nativeAcquire(void *p,volatile uint32_t *words,size_t bytes)
{
    auto &o=*static_cast<ZornGen7HostRing26 *>(p);if(!o.bootstrapHealthy() || guard(p))return 1;auto &s=*o.storage_;
    auto *fence=reinterpret_cast<volatile uint32_t *>(static_cast<uint8_t *>(s.memory.bo(FHG_GPU_POOL_SLOT).mapping())+0xc8100);
    if(words!=fence || bytes!=64)return 1;
    // Fixed actual64B fence lies wholly in this already owned GPU4K page.
    // Native memory maintenance receives that complete logical page;it never
    // broadens to a guessed physical/CPU neighbor or a foreign allocation.
    return o.acquireScratch()?1:0;
}
uint64_t ZornGen7HostRing26::nativeNow(void *)
{
    uint64_t absolute=0,ns=0;clock_get_uptime(&absolute);absolutetime_to_nanoseconds(absolute,&ns);return ns/1000;
}
int ZornGen7HostRing26::nativeIdle(void *p){return delay(p,100);}
IOReturn ZornGen7HostRing26::runAuthenticatedBootstrap()
{
    if(!bootstrapHealthy() || guard(this))return kIOReturnNotReady;auto &s=*storage_;auto &r=s.ring;
    // One actual1s window for fixed mode/canary/fence bring-up only. A raw
    // SCM did not inherit this polling deadline and is never called here.
    clock_interval_to_deadline(1000,NSEC_PER_MSEC,&s.deadline);__atomic_store_n(&s.phase,5u,__ATOMIC_RELEASE);
    uint32_t sqe=0,rptr=0,wptr=0;
    if(read(this,0x3d02020,&sqe) || sqe!=1 || read(this,0x3d02018,&rptr) || rptr!=10 ||
       read(this,0x3d0201c,&wptr) || wptr!=10 || r.wptr!=10)return kIOReturnNotReady;
    hhr_io io{};io.cookie=this;io.guard=guard;io.read=read;io.write=write;io.delay=delay;
    if(hhr_idle(&io,&r) || guard(this))return kIOReturnNotReady;
    const uint32_t mode[]={hhr_pkt7(0x66,1),0};r.post_init_attempted=1;
    auto raw=publishBootstrap(r.wptr,mode,2);if(raw)return raw;r.wptr+=2;
    if(hhr_kick(&io,&r) || hhr_idle(&io,&r) || guard(this) || r.rptr!=12)return kIOReturnNotReady;
    s.modeIdle=true;r.post_init_complete=1;
    // The source first-context prefix is required before normal GPU memory
    // writes,even for the same root. Actual USER/LPAC banks are re-observed;
    // no CP wait holds the domain/startup gate.
    raw=s.domain.buildHostFirstContext(*this,s.firstContext);if(raw)return raw;
    raw=publishBootstrap(r.wptr,s.firstContext,25);if(raw)return raw;r.wptr+=25;
    if(hhr_kick(&io,&r) || hhr_idle(&io,&r) || guard(this) || r.rptr!=r.wptr)return kIOReturnNotReady;
    s.contextIdle=true;raw=s.domain.restoreHostPostCpContext(*this);if(raw || guard(this))return raw?raw:kIOReturnNotReady;s.contextRestored=true;
    const auto &pool=s.memory.bo(FHG_GPU_POOL_SLOT);auto *scratch=reinterpret_cast<const volatile uint32_t *>(static_cast<uint8_t *>(pool.mapping())+0xc8000);
    if(acquireScratch() || scratch[0] || scratch[1])return kIOReturnNotReady;
    // Reuse the retained original two5word canary producers,separate WPTR and
    // idle boundaries. CPU never stores either expected GPU result.
    for(unsigned i=0;i<2;++i){
        const uint32_t expected=0xc0ffee00u+i;
        const uint32_t packet[]={hhr_pkt7(0x3d,3),HHR_SCRATCH+4*i,0,expected,hhr_pkt7(0x12,0)};
        raw=publishBootstrap(r.wptr,packet,5);if(raw)return raw;r.wptr+=5;
        if(hhr_kick(&io,&r) || hhr_idle(&io,&r) || guard(this) || acquireScratch())return kIOReturnNotReady;
        r.observed[i]=scratch[i];if(r.observed[i]!=expected)return kIOReturnIOError;++r.writebacks;
    }
    if(r.wptr!=12+25+2*5 || r.rptr!=r.wptr || !s.contextIdle || !s.contextRestored || r.writebacks!=2)return kIOReturnNotReady;
    NativeAdrenoRingIo nativeIo{this,nativeWrite,nativeRead,nativeBarrier};NativeAdrenoRingCache cache{this,nativePublish,nativeAcquire};
    void *fence=static_cast<uint8_t *>(pool.mapping())+0xc8100;
    s.nativeRaw=s.native.adoptLive(&nativeIo,&cache,s.ringCpu,HHR_BYTES,HHR_RING,fence,64,HHR_SCRATCH+0x100,r.wptr);
    if(s.nativeRaw || guard(this))return s.nativeRaw?s.nativeRaw:kIOReturnNotReady;s.nativeAdopted=true;
    // Genuine current26 NativeRing emits its own timestamp fence for this
    // original one-word WFI producer. No fake fence/IRQ completion or CP_INIT
    // before-auth substitution;no guessed houji expected-pointer51.
    const uint32_t idle=hhr_pkt7(0x12,0);s.nativeRaw=s.native.submit(&idle,1,&s.nativeFence);
    if(s.nativeRaw || !s.nativeFence || s.nativeFence!=s.native.lastSubmitted() || guard(this))return s.nativeRaw?s.nativeRaw:kIOReturnNotReady;
    NativeAdrenoRingClock clock{this,nativeNow,nativeIdle};s.nativeWait=s.native.wait(s.nativeFence,&clock,1000000,&s.nativeObserved);
    if(s.nativeWait!=NativeAdrenoRingFenceComplete || s.nativeObserved!=s.nativeFence || s.native.completedFence()!=s.nativeFence ||
       s.native.outstanding() || s.native.poisoned() || guard(this) || hhr_idle(&io,&r))return kIOReturnNotReady;
    if(s.domain.verifyHostRuntimeContexts() || guard(this))return kIOReturnNotReady;
    __atomic_store_n(&s.phase,6u,__ATOMIC_RELEASE);s.deadline=0;return kIOReturnSuccess;
    // Same live owner retains adopted ring/OOB/resources. No normal user
    // submit/getter,success-only OOB release or render qualification here.
}

bool ZornGen7HostRing26::modeExitIdleForDomain(const ZornGen7SmmuDomain26 &domain) const
{return storage_ && &storage_->domain==&domain && bootstrapHealthy() && storage_->modeIdle && !storage_->contextIdle;}

bool ZornGen7HostRing26::bootstrapReadyForOob(const ZornGen7HwschedHfi26 &hfi) const
{return bootstrapReadyForOobTransport(hfi);}
bool ZornGen7HostRing26::bootstrapReadyForOobTransport(const OSObject &hfi) const
{
    if(!storage_ || !bootstrapHealthy())return false;const auto &s=*storage_;
    return &s.hfiOwner==&hfi && __atomic_load_n(&s.phase,__ATOMIC_ACQUIRE)==6 && s.successOobAttempted && !s.successOobReturned &&
        s.modeIdle && s.contextIdle && s.contextRestored && s.ring.writebacks==2 && s.ring.observed[0]==0xc0ffee00u && s.ring.observed[1]==0xc0ffee01u &&
        s.ring.rptr==s.ring.wptr && s.nativeAdopted && !s.nativeRaw && s.nativeWait==NativeAdrenoRingFenceComplete &&
        s.nativeFence && s.nativeObserved==s.nativeFence && s.native.completedFence()==s.nativeFence &&
        !s.native.outstanding() && !s.native.poisoned();
    // Real retained native producer/observations only,not a supplied fence or
    // retirement/stop claim. OOB release has no firmware acknowledgment here.
}

bool ZornGen7HostRing26::contextIdleForDomain(const ZornGen7SmmuDomain26 &domain) const
{return storage_ && &storage_->domain==&domain && bootstrapHealthy() && storage_->modeIdle && storage_->contextIdle &&
    storage_->ring.rptr==storage_->ring.wptr && !storage_->nativeAdopted && __atomic_load_n(&storage_->phase,__ATOMIC_ACQUIRE)==5;}

bool ZornGen7HostRing26::completedBootstrapForDomain(const ZornGen7SmmuDomain26 &domain) const
{
    if(!storage_ || &storage_->domain!=&domain || !bootstrapHealthy())return false;const auto &s=*storage_;
    return s.bootstrapComplete && s.successOobAttempted && s.successOobReturned && !s.successOobRaw && s.contextRestored &&
        s.nativeAdopted && s.nativeFence && s.nativeObserved==s.nativeFence && s.native.completedFence()==s.nativeFence &&
        !s.native.outstanding() && !s.native.poisoned() && s.ring.rptr==s.ring.wptr;
}

bool ZornGen7HostRing26::nativeKernelTaskBinding(IOMemoryDescriptor &image,unsigned phase) const
{
    if(!storage_ || !normal() || !bootstrapHealthy())return false;const auto &s=*storage_;
    return !s.hfi && s.kernelTaskAttempted && s.kernelTaskThread==current_thread() &&
        phase>=1 && phase<=5 && phase==s.kernelPhase && s.runtimeReady && s.bootstrapComplete &&
        s.nativeAdopted && !s.native.poisoned() && !s.runtimeVm.poisoned() && !s.runtimeSubmit.poisoned() &&
        !s.kernelTaskComplete && !s.kernelIoPublishAttempted && !s.applicationIoPublishAttempted &&
        !s.kernelIoConnection && !s.appExecution && !s.appExecutionPending && !s.processClients && !s.processSelected &&
        !s.appOobActive && !s.appOobTransition && !s.appOperationPending &&
        s.imageMemory.descriptor()==&image && s.imageMemory.mapping() && !s.imageMemory.quarantined() &&
        !s.imageMemory.imported() && !s.imageMemory.readOnly() && s.imageMemory.writeCombined() &&
        s.imageMemory.bytes()==32768 && s.imageMemory.ownedBytes()==NativeAdrenoMemory::backingBudget(32768) &&
        image.getLength()==s.imageMemory.ownedBytes();
}
bool ZornGen7HostRing26::nativeKernelTaskCanRelease(IOMemoryDescriptor &image) const
{
    if(!nativeKernelTaskBinding(image,5))return false;const auto &s=*storage_;
    return s.kernelTaskActive && s.kernelTaskGrantReturned && !s.kernelTaskGrantRaw &&
        !s.nativeTableLease && s.nativeTableAcquires==2 && s.nativeTableReleases==2 &&
        s.imageVerified && s.imageUnmapped && !s.imageMemory.deviceReferences() && s.imageFence &&
        s.native.completedFence()==s.imageFence && !s.native.outstanding() && !s.runtimeSubmit.outstanding() &&
        !s.runtimeVm.hasPendingSubmissionResources() && s.ring.rptr==s.ring.wptr;
}
bool ZornGen7HostRing26::nativeKernelTableLeaseHealthy(const ZornGen7SmmuDomain26 &domain) const
{
    if(!storage_ || &storage_->domain!=&domain || !IORecursiveLockHaveLock(&storage_->gate))return false;
    const auto &s=*storage_;
    return !s.hfi && s.imageMemory.descriptor() && nativeKernelTaskBinding(*s.imageMemory.descriptor(),s.kernelPhase) &&
        (s.kernelPhase==2 || s.kernelPhase==4) && kernelTaskExecutionHealthy() &&
        !s.native.outstanding() && !s.runtimeSubmit.outstanding() && !s.runtimeVm.hasPendingSubmissionResources() &&
        s.ring.rptr==s.ring.wptr && s.ring.busy_valid && !(s.ring.busy&(1u<<23)) &&
        !(s.ring.status&~1u) && !s.ring.irq && !s.ring.hwfault;
}
IOReturn ZornGen7HostRing26::beginNativeKernelTableLease(const ZornGen7SmmuDomain26 &domain)
{
    if(!nativeKernelTableLeaseHealthy(domain))return kIOReturnNotReady;auto &s=*storage_;
    if(s.nativeTableLease || s.nativeTableAcquires!=s.nativeTableReleases ||
       s.nativeTableAcquires!=(s.kernelPhase==2?0u:1u))return kIOReturnNotReady;
    // This same thread retains issuer for the entire bounded image operation.
    // No client/process producer is published. Re-observe the sole live ring,
    // RBBM and GX busy bit23 outside the metadata gate before every mutation.
    IORecursiveLockUnlock(&s.gate);
    hhr_io io{};io.cookie=this;io.guard=guard;io.read=read;io.write=write;io.delay=delay;
    const auto idle=hhr_idle(&io,&s.ring);
    IORecursiveLockLock(&s.gate);
    if(idle || !nativeKernelTableLeaseHealthy(domain))return kIOReturnNotReady;
    s.nativeTableLease=true;++s.nativeTableAcquires;return kIOReturnSuccess;
}
IOReturn ZornGen7HostRing26::endNativeKernelTableLease(const ZornGen7SmmuDomain26 &domain)
{
    if(!nativeKernelTableLeaseHealthy(domain))return kIOReturnNotReady;auto &s=*storage_;
    if(!s.nativeTableLease || s.nativeTableAcquires!=s.nativeTableReleases+1)return kIOReturnNotReady;
    s.nativeTableLease=false;++s.nativeTableReleases;return kIOReturnSuccess;
}

IOReturn ZornGen7HostRing26::prepareDirectRuntime(OSObject &owner,const ZornGen7DirectRuntimeAuthority26 &authority,size_t capacity)
{
    if(!storage_)return kIOReturnNotReady;
    auto *direct=OSDynamicCast(ZornGen7DirectHfi26,&storage_->hfiOwner);
    if(!storage_->hfi && (!direct || !direct->bootstrapOobReleaseReturned()))return kIOReturnNotReady;
    if(!storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;
    if(!IORecursiveLockHaveLock(&s.gate) || s.runtimeAttempted || !completedBootstrapForDomain(s.domain))return kIOReturnNotReady;
    __atomic_store_n(&s.presentationRuntimeState,1u,__ATOMIC_RELEASE);
    const auto bound=bindPresentationOwner();
    if(bound){__atomic_store_n(&s.presentationRuntimeState,3u,__ATOMIC_RELEASE);return bound;}
    s.runtimeAttempted=true;s.runtimeCapacity=capacity;owner.retain();s.runtimeOwner=&owner;s.runtimeAuthority=authority;const auto raw=s.domain.attachHostDirectRuntime(*this,s.runtimeVm,s.runtimeSubmit,s.native,owner,authority,capacity,s.presentProgress);
    __atomic_store_n(&s.runtimeReady,raw==kIOReturnSuccess,__ATOMIC_RELEASE);
    __atomic_store_n(&s.presentationRuntimeState,raw==kIOReturnSuccess?2u:3u,__ATOMIC_RELEASE);return raw;
    // No getter or reconstructed ring. Actual queue execution must gain its
    // runtime IO/wait/gate integration before normal submits are admitted.
}

bool ZornGen7HostRing26::kernelTaskPermissionHeld(const ZornGen7HwschedHfi26 &hfi) const
{return kernelTaskPermissionHeldForTransport(hfi);}
bool ZornGen7HostRing26::kernelTaskPermissionHeld(const ZornGen7DirectHfi26 &hfi) const
{return kernelTaskPermissionHeldForTransport(hfi);}
bool ZornGen7HostRing26::kernelTaskPermissionHeldForTransport(const OSObject &hfi) const
{
    if(!storage_ || !normal())return false;const auto &s=*storage_;
    return &s.hfiOwner==&hfi && s.kernelTaskThread==current_thread() && s.kernelTaskActive && s.runtimeReady && s.kernelTaskGrantReturned && !s.kernelTaskGrantRaw &&
        s.imageMemory.descriptor() && s.runtimeAuthority.checkHeldKernelTask && !__atomic_load_n(&s.stopped,__ATOMIC_ACQUIRE) &&
        !s.irq.halted() && !s.gmu.halted() && !s.hfiHalted() && !s.domain.faulted() &&
        !s.runtimeAuthority.checkHeldKernelTask(s.runtimeAuthority.cookie,*s.imageMemory.descriptor(),s.kernelPhase);
}
bool ZornGen7HostRing26::kernelTaskExecutionHealthy() const
{
    if(!storage_ || !kernelTaskPermissionHeldForTransport(storage_->hfiOwner))return false;
    auto &s=*storage_;if(s.hfi)return s.hfi->kernelTaskOobHeld(*this);
    auto *direct=OSDynamicCast(ZornGen7DirectHfi26,&s.hfiOwner);
    return direct && direct->kernelTaskOobHeld(*this);
}
bool ZornGen7HostRing26::kernelTaskReadyToRelease(const ZornGen7HwschedHfi26 &hfi) const
{return kernelTaskReadyToReleaseForTransport(hfi);}
bool ZornGen7HostRing26::kernelTaskReadyToRelease(const ZornGen7DirectHfi26 &hfi) const
{return kernelTaskReadyToReleaseForTransport(hfi);}
bool ZornGen7HostRing26::kernelTaskReadyToReleaseForTransport(const OSObject &hfi) const
{
    if(!storage_ || !kernelTaskPermissionHeldForTransport(hfi))return false;const auto &s=*storage_;
    return s.taskReleaseAllowed && s.imageVerified && s.imageUnmapped && s.imageFence && s.native.completedFence()==s.imageFence &&
        !s.native.outstanding() && !s.runtimeSubmit.outstanding() && !s.native.poisoned() && !s.runtimeSubmit.poisoned() && s.ring.rptr==s.ring.wptr;
}
IOReturn ZornGen7HostRing26::runKnownImage()
{
    if(!storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;
    if(!IORecursiveLockHaveLock(&s.gate) || !s.runtimeReady || s.kernelTaskAttempted ||
       !s.runtimeAuthority.acquireKernelTask || !s.runtimeAuthority.checkHeldKernelTask || !s.runtimeAuthority.authorizeKernelTaskRelease)return kIOReturnNotReady;
    s.kernelTaskAttempted=true;IORecursiveLockUnlock(&s.gate);s.lockIssuer();
    s.kernelTaskThread=current_thread();
    const auto raw=runKnownImageBody();s.kernelTaskRaw=raw;
    if(raw){__atomic_store_n(&s.stopped,1u,__ATOMIC_RELEASE);s.irq.stopAndMask();}
    s.kernelTaskActive=false;s.kernelTaskComplete=raw==kIOReturnSuccess;recordKnownImage(raw);
    s.kernelTaskThread=THREAD_NULL;s.unlockIssuer();IORecursiveLockLock(&s.gate);return raw;
}
IOReturn ZornGen7HostRing26::runKnownImageBody()
{
    auto &s=*storage_;if(!s.runtimeReady || IORecursiveLockHaveLock(&s.gate) || !bootstrapHealthy())return kIOReturnNotReady;
    s.kernelPhase=1;const size_t budget=NativeAdrenoMemory::backingBudget(32768);if(!budget)return kIOReturnUnsupported;
    auto raw=s.imageMemory.allocate(32768,36,true,budget);if(raw)return raw;
    if(!s.imageMemory.mapping() || !s.imageMemory.descriptor() || s.imageMemory.quarantined() || s.imageMemory.imported() ||
       s.imageMemory.readOnly() || s.imageMemory.bytes()!=32768 || s.imageMemory.ownedBytes()!=budget || s.imageMemory.deviceReferences())return kIOReturnNotReady;
    raw=s.imageMemory.makeWriteCombined();if(raw)return raw;
    s.kernelTaskGrantRaw=s.maps.acquireKernelTaskWindow(*this,s.runtimeAuthority,*s.imageMemory.descriptor());s.kernelTaskGrantReturned=true;
    if(s.kernelTaskGrantRaw)return s.kernelTaskGrantRaw;s.kernelTaskActive=true;
    auto *direct=s.hfi?nullptr:OSDynamicCast(ZornGen7DirectHfi26,&s.hfiOwner);
    if(!s.hfi && !direct)return kIOReturnNotReady;
    raw=s.hfi?s.hfi->acquireKernelTaskOob(*this):direct->acquireKernelTaskOob(*this);if(raw)return raw;
    s.kernelPhase=2;clock_interval_to_deadline(1000,NSEC_PER_MSEC,&s.deadline);
    hhr_io io{};io.cookie=this;io.guard=guard;io.read=read;io.write=write;io.delay=delay;
    if(guard(this) || hhr_idle(&io,&s.ring) || s.native.outstanding() || s.runtimeSubmit.outstanding())return kIOReturnNotReady;
    IORecursiveLockLock(&s.gate);
    raw=s.runtimeVm.findAddress(0,32768,4096,&s.imageIova);
    if(!raw && !k80KnownImageLayout26(s.imageIova))raw=kIOReturnUnsupported;
    if(!raw && !k80KnownImageBuild26(s.imageMemory.mapping(),32768,s.imageIova))raw=kIOReturnNotReady;
    if(!raw)raw=s.runtimeVm.map(&s.imageMemory,0,s.imageIova,ZornSmmuSparse4KRead|ZornSmmuSparse4KWrite,0,3,&s.imageHandle);
    if(!raw)raw=s.runtimeVm.auditLive();IORecursiveLockUnlock(&s.gate);
    if(raw || guard(this) || !s.imageHandle)return raw?raw:kIOReturnNotReady;
    // NativeSubmit takes the actual VM handle/ref under the metadata gate
    // and generates its original IB/fence. The fence wait releases that gate;
    // same-thread phase3 register polling under the gate uses bounded IODelay.
    s.kernelPhase=3;ZornGen7DirectSubmit26Buffer command{s.imageHandle,s.imageIova+4*4096,HGKI_SELECTED_COMMAND_WORDS*4};
    raw=s.runtimeSubmit.submit(&command,1,0,&s.imageFence);if(raw || !s.imageFence)return raw?raw:kIOReturnNotReady;
    NativeAdrenoRingClock clock{this,nativeNow,nativeIdle};raw=s.runtimeSubmit.wait(s.imageFence,&clock,1000000);if(raw || guard(this))return raw?raw:kIOReturnNotReady;
    if(hhr_idle(&io,&s.ring) || s.native.completedFence()!=s.imageFence || s.native.outstanding() || s.runtimeSubmit.outstanding())return kIOReturnNotReady;
    s.kernelPhase=4;raw=s.imageMemory.acquireDeviceWrites(0,32768);if(raw)return raw;__asm__ volatile("dsb sy" ::: "memory");
    if(!k80KnownImageVerify26(s.imageMemory.mapping(),32768,s.imageIova,s.imageResult))return kIOReturnIOError;s.imageVerified=true;
    IORecursiveLockLock(&s.gate);raw=s.runtimeVm.unmap(s.imageHandle);if(!raw)raw=s.runtimeVm.auditLive();IORecursiveLockUnlock(&s.gate);
    if(raw || guard(this) || s.imageMemory.deviceReferences())return raw?raw:kIOReturnNotReady;s.imageUnmapped=true;
    s.kernelPhase=5;raw=s.maps.authorizeKernelTaskRelease(*this,s.runtimeAuthority,*s.imageMemory.descriptor());if(raw)return raw;
    s.taskReleaseAllowed=true;
    raw=s.hfi?s.hfi->releaseKernelTaskOob(*this):direct->releaseKernelTaskOob(*this);if(raw)return raw;
    s.kernelPhase=6;s.deadline=0;return kIOReturnSuccess;
    // Retain this bounded qualification's image/backing/readback on every
    // outcome,as the source HGKI lifetime requires. No BO free/reset/retry.
}


void ZornGen7HostRing26::recordKnownImage(IOReturn raw) const
{
    if(!storage_)return;const auto &s=*storage_;auto *o=nativeKnownImageObservation;
    o[0]=unsigned(raw);o[1]=s.kernelPhase;
    o[2]=(s.kernelTaskAttempted?1u:0u)|(s.kernelTaskGrantReturned?2u:0u)|(s.kernelTaskComplete?4u:0u)|
        (s.imageVerified?8u:0u)|(s.imageUnmapped?16u:0u)|(s.taskReleaseAllowed?32u:0u)|(s.nativeTableLease?64u:0u);
    o[3]=unsigned(s.kernelTaskGrantRaw);o[4]=s.ring.rptr;o[5]=s.ring.wptr;
    o[6]=s.imageFence;o[7]=s.native.completedFence();o[8]=s.native.outstanding();o[9]=s.runtimeSubmit.outstanding();
    o[10]=s.runtimeVm.poisoned();o[11]=s.runtimeSubmit.poisoned();o[12]=s.imageMemory.deviceReferences();
    o[13]=uint32_t(s.imageIova);o[14]=uint32_t(s.imageHandle);o[15]=s.imageResult.output_crc;
    o[16]=s.imageResult.first_bad;o[17]=s.imageResult.expected;o[18]=s.imageResult.actual;
    o[19]=s.nativeTableAcquires;o[20]=s.nativeTableReleases;o[21]=s.ring.busy;o[22]=s.ring.status;
    o[23]=unsigned(s.ioRaw);
    auto *direct=OSDynamicCast(ZornGen7DirectHfi26,&s.hfiOwner);
    if(direct){uint32_t task[8]{};direct->copyKernelTaskOobObservation(task);for(unsigned i=0;i<8;++i)o[24+i]=task[i];}
}

IOReturn ZornGen7HostRing26::copyKnownImageToConsole()
{
    if(!storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(&s.gate))return kIOReturnNotReady;s.lockIssuer();
    auto finish=[&](IOReturn raw){s.unlockIssuer();return raw;};
    if(s.consoleImageAttempted || !s.kernelTaskComplete || s.kernelTaskRaw || !s.imageVerified || !s.imageUnmapped ||
       !s.taskReleaseAllowed || !bootstrapHealthy() || !s.imageFence || s.native.completedFence()!=s.imageFence ||
       s.native.outstanding() || s.runtimeSubmit.outstanding() || s.native.poisoned() || s.runtimeSubmit.poisoned() ||
       s.runtimeVm.poisoned() || s.imageMemory.quarantined() || s.imageMemory.deviceReferences() ||
       !s.imageMemory.mapping() || s.imageMemory.bytes()!=32768 || s.kernelIoPublishAttempted)return finish(kIOReturnNotReady);
    s.consoleImageAttempted=true;
    // The real task already waited/acquired device writes and unmapped this BO.
    // Recheck the retained full image, then copy its actual output; never fill
    // a host-generated colour or mutate the original GPU result.
    hgki_result checked{};
    if(!k80KnownImageVerify26(s.imageMemory.mapping(),32768,s.imageIova,checked))return finish(kIOReturnIOError);
    const auto *rgba=static_cast<const uint8_t *>(s.imageMemory.mapping())+5*4096;
    return finish(ZornGen7CopyKnownImageToBootConsole26(rgba,4096));
    // CPU display failure never changes GPU stop/release/reset policy.
}

bool ZornGen7HostRing26::nativeKernelClientBinding(IOUserClient &client,unsigned phase) const
{
    if(!storage_ || !normal() || current_task()!=kernel_task || !bootstrapHealthy())return false;const auto &s=*storage_;
    if(s.hfi || !s.kernelIoAttempted || !s.kernelIoPublishAttempted || s.kernelIoConnection!=&client ||
       s.kernelTaskOwner!=kernel_task || s.kernelIoClosed || phase!=s.kernelIoPhase ||
       (phase!=1 && phase!=3 && phase!=4) || !s.runtimeReady || !s.runtimeOwner || !s.bootstrapComplete ||
       !s.kernelTaskComplete || s.kernelTaskRaw || s.kernelTaskActive || s.kernelTaskThread!=THREAD_NULL ||
       !s.imageVerified || !s.imageUnmapped || !s.taskReleaseAllowed || !s.imageFence ||
       s.imageMemory.quarantined() || s.imageMemory.deviceReferences() || s.nativeTableLease ||
       s.nativeTableAcquires!=2 || s.nativeTableReleases!=2 || !s.nativeAdopted || s.native.completedFence()<s.imageFence ||
       s.native.poisoned() || s.runtimeVm.poisoned() || s.runtimeSubmit.poisoned() ||
       s.appExecution || s.appExecutionPending || s.applicationIoPublishAttempted ||
       s.appOobActive || s.appOobTransition || s.appOperationPending ||
       ((phase==1)==s.kernelIoClosing))return false;
    const auto grant=__atomic_load_n(&s.kernelClientGrantThread,__ATOMIC_ACQUIRE);
    if(!s.kernelIoGrantReturned){
        // The ring retains this real client before dropping issuer for the
        // foreign board grant. Another open cannot replace this pending owner.
        return phase==1 && !s.kernelIoActive && grant==current_thread() && !s.issuerHeld();
    }
    return grant==THREAD_NULL && s.issuerHeld() && s.kernelIoActive && !s.kernelIoGrantRaw;
}
bool ZornGen7HostRing26::nativeKernelClientCanRelease(IOUserClient &client) const
{
    if(!nativeKernelClientBinding(client,4))return false;const auto &s=*storage_;
    return !s.nativeProcessTableLease && s.nativeProcessTableAcquires==s.nativeProcessTableReleases &&
        s.kernelIoClosing && s.kernelProcessClosing && !s.kernelProcessReady && !s.kernelProcess &&
        !s.processClients && !s.processSelected && s.processTransitionThread==THREAD_NULL &&
        !s.native.outstanding() && !s.runtimeSubmit.outstanding() && !s.runtimeVm.hasPendingSubmissionResources() &&
        s.ring.rptr==s.ring.wptr;
}
bool ZornGen7HostRing26::kernelClientPermissionHeld(const ZornGen7HwschedHfi26 &hfi) const
{return kernelClientPermissionHeldForTransport(hfi);}
bool ZornGen7HostRing26::kernelClientPermissionHeld(const ZornGen7DirectHfi26 &hfi) const
{return kernelClientPermissionHeldForTransport(hfi);}
bool ZornGen7HostRing26::kernelClientPermissionHeldForTransport(const OSObject &hfi) const
{
    if(!storage_ || !normal())return false;const auto &s=*storage_;
    return &s.hfiOwner==&hfi && s.kernelIoActive && s.kernelIoConnection && s.kernelIoGrantReturned && !s.kernelIoGrantRaw &&
        s.runtimeAuthority.checkHeldKernelClient && !__atomic_load_n(&s.stopped,__ATOMIC_ACQUIRE) &&
        !s.irq.halted() && !s.gmu.halted() && !s.hfiHalted() && !s.domain.faulted() &&
        !s.runtimeAuthority.checkHeldKernelClient(s.runtimeAuthority.cookie,*s.kernelIoConnection,s.kernelIoPhase);
}
bool ZornGen7HostRing26::kernelClientExecutionHealthy() const
{
    if(!storage_ || !kernelClientPermissionHeldForTransport(storage_->hfiOwner))return false;auto &s=*storage_;
    if(s.hfi)return s.hfi->kernelClientOobHeld(*this);
    auto *direct=OSDynamicCast(ZornGen7DirectHfi26,&s.hfiOwner);
    return direct && direct->kernelClientOobHeld(*this);
}
bool ZornGen7HostRing26::kernelClientReadyToRelease(const ZornGen7HwschedHfi26 &hfi) const
{return kernelClientReadyToReleaseForTransport(hfi);}
bool ZornGen7HostRing26::kernelClientReadyToRelease(const ZornGen7DirectHfi26 &hfi) const
{return kernelClientReadyToReleaseForTransport(hfi);}
bool ZornGen7HostRing26::kernelClientReadyToReleaseForTransport(const OSObject &hfi) const
{
    if(!storage_ || !kernelClientPermissionHeldForTransport(hfi))return false;const auto &s=*storage_;
    return s.kernelIoReleaseAllowed && s.kernelIoClosing && !s.processClients && !s.processSelected && !s.native.outstanding() &&
        !s.runtimeSubmit.outstanding() && !s.native.poisoned() && !s.runtimeSubmit.poisoned() && s.ring.rptr==s.ring.wptr;
}
IOReturn ZornGen7HostRing26::publishKernelIo()
{
    if(!storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(&s.gate))return kIOReturnNotReady;s.lockIssuer();
    if(!s.kernelTaskComplete || s.applicationIoPublishAttempted || s.kernelIoPublishAttempted || !bootstrapHealthy() ||
       !s.runtimeReady || !s.runtimeOwner || !s.imageVerified || !s.imageUnmapped || !s.taskReleaseAllowed || s.kernelTaskRaw ||
       s.native.poisoned() || s.runtimeVm.poisoned() || s.runtimeSubmit.poisoned() || s.native.outstanding() || s.runtimeSubmit.outstanding() ||
       !s.runtimeAuthority.acquireKernelClient || !s.runtimeAuthority.checkHeldKernelClient || !s.runtimeAuthority.authorizeKernelClientRelease){s.unlockIssuer();return kIOReturnNotReady;}
    s.kernelIoPublishAttempted=true;
    s.unlockIssuer();
    // The service allocates no GPU client state until an admitted connection
    // opens its process tables and the client bound to them.
    return ZornGen7DirectIoService26::createAndPublish(*this,s.kernelIoService);
}

IOReturn ZornGen7HostRing26::runKernelClientProbe()
{
    if(!storage_ || !normal() || current_task()!=kernel_task)return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(&s.gate))return kIOReturnNotReady;s.lockIssuer();
    if(s.hfi || s.clientProbeAttempted || !s.kernelIoPublishAttempted || !s.kernelIoService ||
       s.kernelIoAttempted || s.applicationIoPublishAttempted || !bootstrapHealthy() ||
       !s.kernelTaskComplete || s.kernelTaskRaw || !s.imageVerified || !s.imageUnmapped ||
       !s.runtimeReady || s.nativeProcessTableLease || s.nativeProcessTableAcquires || s.nativeProcessTableReleases){
        s.unlockIssuer();return kIOReturnNotReady;
    }
    s.clientProbeAttempted=true;s.clientProbeThread=current_thread();s.clientProbeFlags=1;s.clientProbePhase=1;
    s.unlockIssuer();
    // Each real external method obtains the existing client's serial/issuer
    // locks itself. No driver lock crosses newUserClient, mapping or close.
    const auto raw=runKernelClientProbeBody();
    s.lockIssuer();
    if(raw){__atomic_store_n(&s.stopped,1u,__ATOMIC_RELEASE);s.irq.stopAndMask();}
    recordKernelClientProbe(raw);s.clientProbeThread=THREAD_NULL;s.unlockIssuer();return raw;
}
IOReturn ZornGen7HostRing26::runKernelClientProbeBody()
{
    auto &s=*storage_;
    if(!normal() || current_task()!=kernel_task || s.clientProbeThread!=current_thread() ||
       !s.clientProbeAttempted || IORecursiveLockHaveLock(&s.gate) || s.issuerHeld() ||
       !s.kernelIoService || s.clientProbe || s.clientProbeMap)return kIOReturnNotReady;
    auto raw=s.kernelIoService->newUserClient(kernel_task,nullptr,0x4147,nullptr,&s.clientProbe);
    s.clientProbeMethodRaw=raw;if(raw || !s.clientProbe)return raw?raw:kIOReturnNotReady;s.clientProbeFlags|=2;
    auto call=[&](uint32_t method,const void *input,uint32_t inputBytes,void *output,uint32_t outputBytes){
        IOExternalMethodArguments args{};args.version=kIOExternalMethodArgumentsCurrentVersion;args.selector=method;
        args.structureInput=input;args.structureInputSize=inputBytes;args.structureOutput=output;args.structureOutputSize=outputBytes;
        s.clientProbeMethod=method;
        auto result=s.clientProbe->callExternalMethod(method,&args);
        if(!result && args.structureOutputSize!=outputBytes)result=kIOReturnOverrun;
        s.clientProbeMethodRaw=result;return result;
    };
    s.clientProbePhase=2;NativeAdrenoAbiParams params{};NativeAdrenoAbiDeviceInfo info{};
    raw=call(NativeAdrenoMethodQuery,nullptr,0,&params,sizeof(params));if(raw)return raw;
    if(params.abi_version!=NativeAdrenoAbiVersion || params.input_bits!=s.logical.input_bits ||
       params.output_bits!=s.logical.output_bits || params.max_bo_bytes<32768)return kIOReturnUnsupported;
    raw=call(NativeAdrenoMethodGetDeviceInfo,nullptr,0,&info,sizeof(info));if(raw)return raw;
    if(!(info.flags&NativeAdrenoDeviceClientIova) || info.va_size<32768 || !k80KnownImageLayout26(info.va_start))
        return kIOReturnUnsupported;
    s.clientProbeIova=info.va_start;
    s.clientProbePhase=3;NativeAdrenoAbiBoAlloc alloc{32768,12,0};NativeAdrenoAbiBoAllocReply allocated{};
    raw=call(NativeAdrenoMethodBoAlloc,&alloc,sizeof(alloc),&allocated,sizeof(allocated));
    if(raw || !allocated.handle)return raw?raw:kIOReturnNotReady;s.clientProbeHandle=allocated.handle;
    s.clientProbePhase=4;NativeAdrenoAbiBoCpuMap cpu{allocated.handle};NativeAdrenoAbiBoCpuMapReply view{};
    raw=call(NativeAdrenoMethodBoCpuMap,&cpu,sizeof(cpu),&view,sizeof(view));if(raw)return raw;
    s.clientProbeToken=view.token;
    if(!view.token || view.reserved || view.bytes!=32768)return kIOReturnNotReady;
    s.clientProbeMap=s.clientProbe->mapClientMemory64(view.token,kernel_task,kIOMapAnywhere|kIOMapWriteCombineCache,0);
    if(!s.clientProbeMap || s.clientProbeMap->getAddressTask()!=kernel_task || s.clientProbeMap->getSize()!=32768 ||
       !s.clientProbeMap->getAddress() || (s.clientProbeMap->getAddress()&4095))return kIOReturnNotReady;
    s.clientProbeFlags|=4;
    void *cpuAddress=reinterpret_cast<void *>(s.clientProbeMap->getAddress());
    if(!k80KnownImageBuild26(cpuAddress,32768,s.clientProbeIova))return kIOReturnNotReady;
    __asm__ volatile("dsb sy" ::: "memory");s.clientProbeFlags|=8;
    s.clientProbePhase=5;NativeAdrenoAbiBoMap map{allocated.handle,s.clientProbeIova,3,0,3,0};NativeAdrenoAbiBoMapReply mapped{};
    raw=call(NativeAdrenoMethodBoMap,&map,sizeof(map),&mapped,sizeof(mapped));if(raw)return raw;
    if(mapped.iova!=s.clientProbeIova)return kIOReturnNotReady;s.clientProbeFlags|=16;
    s.clientProbePhase=6;NativeAdrenoAbiSubmit submit{};NativeAdrenoAbiSubmitReply submitted{};
    submit.buffer_count=1;submit.buffers[0]={allocated.handle,s.clientProbeIova+4*4096,HGKI_SELECTED_COMMAND_WORDS*4};
    raw=call(NativeAdrenoMethodSubmit,&submit,sizeof(submit),&submitted,sizeof(submitted));if(raw)return raw;
    if(!submitted.fence || submitted.fence>UINT32_MAX || submitted.fence<=s.imageFence)return kIOReturnNotReady;
    s.clientProbeFence=uint32_t(submitted.fence);s.clientProbeFlags|=32;
    s.clientProbePhase=7;NativeAdrenoAbiWaitFence wait{submitted.fence,1000000000};
    raw=call(NativeAdrenoMethodWaitFence,&wait,sizeof(wait),nullptr,0);if(raw)return raw;s.clientProbeFlags|=64;
    // The actual client's normal submission retired the BO references. Acquire
    // this owned BO's device writes before reading its real IOKit CPU alias.
    s.clientProbePhase=8;s.lockIssuer();clock_interval_to_deadline(1000,NSEC_PER_MSEC,&s.deadline);
    auto *p=s.kernelProcess;
    if(s.kernelIoConnection!=s.clientProbe || !p || s.processSelected!=p || !p->clientState_ ||
       !p->clientOpen_ || p->clientOwner_!=s.clientProbe || !kernelClientExecutionHealthy())raw=kIOReturnNotReady;
    else {
        s.clientProbeAsid=p->asid_;raw=quiesceKernelIo();
        auto *memory=p->clientState_->client.memoryForToken(view.token);
        if(!raw && (!memory || memory->bytes()!=32768 || memory->quarantined() || memory->imported() ||
           memory->readOnly() || s.native.completedFence()!=s.clientProbeFence ||
           p->vm_.poisoned() || p->clientState_->submit.poisoned() || p->clientState_->submit.outstanding()))
            raw=kIOReturnNotReady;
        if(!raw)raw=memory->acquireDeviceWrites(0,32768);
        if(!raw){__asm__ volatile("dsb sy" ::: "memory");
            if(!k80KnownImageVerify26(cpuAddress,32768,s.clientProbeIova,s.clientProbeResult))raw=kIOReturnIOError;}
    }
    s.deadline=0;s.unlockIssuer();if(raw)return raw;s.clientProbeFlags|=128;
    // mapClientMemory64 returns a caller-owned map. Unlike its Mach wrapper it
    // does not add it to client->mappings. Unmap/release our exact map first;
    // then the real CPU-unmap method drops the client's descriptor and lease.
    s.clientProbePhase=9;s.clientProbeUnmapRaw=s.clientProbeMap->unmap();
    if(s.clientProbeUnmapRaw)return s.clientProbeUnmapRaw;
    s.clientProbeMap->release();s.clientProbeMap=nullptr;cpuAddress=nullptr;
    NativeAdrenoAbiBoCpuUnmap unmap{allocated.handle,view.token,0};
    raw=call(NativeAdrenoMethodBoCpuUnmap,&unmap,sizeof(unmap),nullptr,0);if(raw)return raw;s.clientProbeFlags|=256;
    s.clientProbePhase=10;NativeAdrenoAbiBoFree free{allocated.handle};
    raw=call(NativeAdrenoMethodBoFree,&free,sizeof(free),nullptr,0);if(raw)return raw;s.clientProbeFlags|=512;
    s.clientProbePhase=11;s.clientProbeCloseRaw=s.clientProbe->clientClose();
    if(s.clientProbeCloseRaw)return s.clientProbeCloseRaw;s.clientProbeFlags|=1024;
    s.lockIssuer();
    const bool closed=s.kernelIoClosed && !s.kernelIoActive && !s.kernelIoConnection &&
        !s.kernelProcess && !s.kernelProcessReady && !s.processClients && !s.processSelected &&
        !s.nativeProcessTableLease && s.nativeProcessTableAcquires==2 && s.nativeProcessTableReleases==2 &&
        !s.native.outstanding() && !s.native.poisoned() && !s.runtimeSubmit.outstanding() &&
        !s.runtimeSubmit.poisoned() && !s.runtimeVm.poisoned() && !s.runtimeVm.hasPendingSubmissionResources() &&
        s.native.completedFence()==s.clientProbeFence && s.ring.rptr==s.ring.wptr &&
        !__atomic_load_n(&s.stopped,__ATOMIC_ACQUIRE) && !s.irq.halted() && !s.gmu.halted() &&
        !s.hfiHalted() && !s.domain.faulted();
    s.unlockIssuer();if(!closed)return kIOReturnNotReady;
    s.clientProbe->release();s.clientProbe=nullptr;s.clientProbePhase=12;return kIOReturnSuccess;
    // No failed path closes a client, frees a BO, changes root or retries.
}
void ZornGen7HostRing26::recordKernelClientProbe(IOReturn raw) const
{
    if(!storage_)return;const auto &s=*storage_;auto *o=nativeKernelClientObservation;
    o[0]=unsigned(raw);o[1]=s.clientProbePhase;o[2]=s.clientProbeFlags;o[3]=s.clientProbeMethod;o[4]=unsigned(s.clientProbeMethodRaw);
    o[5]=s.ring.rptr;o[6]=s.ring.wptr;o[7]=s.clientProbeFence;o[8]=s.native.completedFence();o[9]=s.native.outstanding();
    const auto *p=s.kernelProcess;o[10]=p && p->clientState_?p->clientState_->submit.outstanding():0;
    o[11]=s.clientProbeResult.output_crc;o[12]=s.clientProbeResult.first_bad;o[13]=s.clientProbeResult.expected;o[14]=s.clientProbeResult.actual;
    o[15]=uint32_t(s.clientProbeIova);o[16]=uint32_t(s.clientProbeHandle);o[17]=s.clientProbeToken;
    o[18]=s.nativeProcessTableAcquires;o[19]=s.nativeProcessTableReleases;o[20]=s.kernelIoPhase;
    o[21]=(s.kernelProcessReady?1u:0u)|(s.kernelProcessClosing?2u:0u)|(p?4u:0u)|(s.processClients?8u:0u)|
        (s.processSelected?16u:0u)|(s.clientProbeMap?32u:0u)|(s.clientProbe?64u:0u)|(s.kernelIoActive?128u:0u)|(s.kernelIoClosed?256u:0u);
    o[22]=s.ring.busy;o[23]=s.ring.status;
    auto *direct=OSDynamicCast(ZornGen7DirectHfi26,&s.hfiOwner);
    if(direct){uint32_t client[8]{};direct->copyKernelClientOobObservation(client);for(unsigned i=0;i<8;++i)o[24+i]=client[i];}
    o[32]=p?p->vm_.poisoned():0;o[33]=p && p->clientState_?p->clientState_->submit.poisoned():0;
    o[34]=s.clientProbeAsid;o[35]=s.nativeProcessTableLease?1u:0u;
    o[36]=unsigned(s.clientProbeUnmapRaw);o[37]=unsigned(s.clientProbeCloseRaw);
    o[38]=s.native.poisoned();o[39]=s.runtimeVm.poisoned();
}

IOReturn ZornGen7HostRing26::beginKernelIo(IOUserClient &connection,task_t owningTask)
{
    if(!storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(&s.gate))return kIOReturnNotReady;s.lockIssuer();
    if(s.appExecution || s.appExecutionPending || owningTask!=kernel_task || s.kernelIoAttempted || !s.kernelIoPublishAttempted || !s.kernelTaskComplete || !bootstrapHealthy()){s.unlockIssuer();return kIOReturnNotReady;}
    s.kernelIoAttempted=true;connection.retain();s.kernelIoConnection=&connection;s.kernelTaskOwner=owningTask;s.kernelIoPhase=1;
    __atomic_store_n(&s.kernelClientGrantThread,current_thread(),__ATOMIC_RELEASE);s.unlockIssuer();
    // The real callback may acquire its own context. No startup/issuer lock
    // crosses this foreign callout;pending state prevents another session.
    const auto raw=s.maps.acquireKernelClientWindow(*this,s.runtimeAuthority,connection);
    s.lockIssuer();__atomic_store_n(&s.kernelClientGrantThread,THREAD_NULL,__ATOMIC_RELEASE);s.kernelIoGrantRaw=raw;s.kernelIoGrantReturned=true;
    IOReturn result=raw;
    if(!result){
        auto *direct=s.hfi?nullptr:OSDynamicCast(ZornGen7DirectHfi26,&s.hfiOwner);
        if(!s.hfi && !direct)result=kIOReturnNotReady;
        else {s.kernelIoActive=true;result=s.hfi?s.hfi->acquireKernelClientOob(*this):direct->acquireKernelClientOob(*this);}
    }
    if(!result)result=quiesceKernelIo();
    if(result){__atomic_store_n(&s.stopped,1u,__ATOMIC_RELEASE);s.irq.stopAndMask();}
    s.unlockIssuer();
    if(!result)result=initializeKernelProcess(connection);
    return result;
}
IOReturn ZornGen7HostRing26::quiesceKernelIo()
{
    auto &s=*storage_;
    auto observe=[&](uint32_t stage,IOReturn raw,uint32_t detail=0){
        if(s.appExecution && s.appOperationPending && s.appOperationKind==ZornGen7AppOperation26::PrepareTables)
            zorn26_application_prepare_event(reinterpret_cast<uintptr_t>(s.appExecution->client_),stage,uint32_t(raw),detail);
    };
    if(!processExecutionHealthy() || IORecursiveLockHaveLock(&s.gate)){observe(32,kIOReturnNotReady);return kIOReturnNotReady;}
    observe(32,0);
    NativeAdrenoRingClock clock{this,nativeNow,nativeIdle};
    // Only the actually installed process may own outstanding ring work.
    // A different process with unretired jobs is a lifecycle violation,not
    // permission to switch its root or discard references.
    for(auto *p=s.processClients;p;p=p->ringNext_)
        if(p!=s.processSelected && p->clientState_ && (p->clientState_->submit.outstanding() || p->clientState_->submit.poisoned())){observe(33,kIOReturnNotReady);return kIOReturnNotReady;}
    observe(33,0);
    if(s.processSelected && s.processSelected->submitAttached_){
        const auto raw=s.processSelected->clientState_->submit.waitAll(&clock,1000000);observe(34,raw);if(raw)return raw;
    }
    auto raw=s.runtimeSubmit.waitAll(&clock,1000000);observe(35,raw);if(raw)return raw;
    hhr_io io{};io.cookie=this;io.guard=guard;io.read=read;io.write=write;io.delay=delay;
    const auto guarded=guard(this);observe(36,IOReturn(guarded));if(guarded)return kIOReturnNotReady;
    const auto idle=hhr_idle(&io,&s.ring);observe(37,IOReturn(idle));if(idle)return kIOReturnNotReady;
    if(s.native.outstanding() || s.runtimeSubmit.outstanding() ||
       (s.processSelected && s.processSelected->clientState_ && (s.processSelected->clientState_->submit.outstanding() || s.processSelected->clientState_->submit.poisoned()))){
        observe(38,kIOReturnNotReady);return kIOReturnNotReady;}
    observe(38,0);
    return kIOReturnSuccess;
}
IOReturn ZornGen7HostRing26::dispatchKernelIo(IOUserClient &connection,uint32_t method,const void *input,size_t inputBytes,void *output,size_t outputBytes)
{
    if(!storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;
    CallerTaskReference caller;if(caller.task!=kernel_task)return kIOReturnNotPermitted;
    if(IORecursiveLockHaveLock(&s.gate))return kIOReturnNotReady;s.lockIssuer();
    auto *p=s.kernelProcess;
    const bool ready=p && s.kernelProcessReady && !s.kernelProcessClosing &&
        s.kernelIoConnection==&connection && s.kernelTaskOwner==caller.task && !s.kernelIoClosing && !s.kernelIoClosed;
    // Close may win the issuer after this snapshot. Keep the genuine object
    // alive until inner dispatch rechecks all owner/open/selected conditions.
    if(ready)p->retain();s.unlockIssuer();if(!ready)return kIOReturnNotReady;
    const auto raw=dispatchProcessClient(connection,*p,caller.task,method,input,inputBytes,output,outputBytes);
    p->release();return raw;
}
IOReturn ZornGen7HostRing26::kernelIoLeases(IOUserClient &connection,const NativeAdrenoAbiBoCpuUnmap &request,uint32_t &out)
{
    if(!storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;s.lockIssuer();
    auto *p=s.kernelProcess;
    const bool ready=s.kernelIoConnection==&connection && !s.kernelIoClosing && !s.kernelProcessClosing &&
        s.kernelProcessReady && p && p->clientOpen_ && p->clientState_ && kernelClientExecutionHealthy();
    const auto raw=ready?p->clientState_->client.preflightCpuUnmap(&request,&out):kIOReturnNotReady;
    s.unlockIssuer();return raw;
}
IOReturn ZornGen7HostRing26::copyKernelIoView(IOUserClient &connection,uint32_t token,IOMemoryDescriptor *&out)
{
    if(out || !storage_ || !normal())return kIOReturnBadArgument;auto &s=*storage_;
    if(IORecursiveLockHaveLock(&s.gate))return kIOReturnNotReady;s.lockIssuer();auto done=[&](IOReturn raw){s.unlockIssuer();return raw;};
    auto *p=s.kernelProcess;
    if(s.kernelIoConnection!=&connection || s.kernelIoClosing || s.kernelProcessClosing || !s.kernelProcessReady ||
       !p || !p->clientOpen_ || !p->clientState_ || !kernelClientExecutionHealthy())return done(kIOReturnNotReady);
    auto *memory=p->clientState_->client.memoryForToken(token);NativeAdrenoCpuView view{};
    if(!memory || !memory->cpuView(&view) || !view.count || view.count>65536)return done(kIOReturnNotReady);
    auto *ranges=IONewData(IOAddressRange,view.count);if(!ranges)return done(kIOReturnNoMemory);
    for(size_t i=0;i<view.count;++i)ranges[i]={view.spans[i].physical,view.spans[i].bytes};
    auto *descriptor=IOMemoryDescriptor::withAddressRanges(ranges,static_cast<UInt32>(view.count),
        static_cast<IOOptionBits>(kIODirectionInOut)|static_cast<IOOptionBits>(kIOMemoryTypePhysical64),nullptr);
    IODeleteData(ranges,IOAddressRange,view.count);
    if(!descriptor)return done(kIOReturnNoMemory);if(!kernelClientExecutionHealthy()){descriptor->release();return done(kIOReturnNotReady);}
    out=descriptor;return done(kIOReturnSuccess);
}
IOReturn ZornGen7HostRing26::closeKernelIoBase(IOUserClient &connection)
{
    if(!storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(&s.gate))return kIOReturnNotReady;s.lockIssuer();
    if(s.kernelIoConnection!=&connection || s.kernelIoClosing || s.processClients || s.processSelected || !kernelClientExecutionHealthy()){s.unlockIssuer();return kIOReturnNotReady;}
    s.kernelIoClosing=true;s.kernelIoPhase=3;clock_interval_to_deadline(1000,NSEC_PER_MSEC,&s.deadline);
    auto raw=quiesceKernelIo();
    if(!raw){s.kernelIoPhase=4;raw=s.runtimeAuthority.authorizeKernelClientRelease(s.runtimeAuthority.cookie,connection);}
    if(!raw){
        auto *direct=s.hfi?nullptr:OSDynamicCast(ZornGen7DirectHfi26,&s.hfiOwner);
        if(!s.hfi && !direct)raw=kIOReturnNotReady;
        else {s.kernelIoReleaseAllowed=true;raw=s.hfi?s.hfi->releaseKernelClientOob(*this):direct->releaseKernelClientOob(*this);}
    }
    if(raw){__atomic_store_n(&s.stopped,1u,__ATOMIC_RELEASE);s.irq.stopAndMask();}
    else {s.kernelIoClosed=true;s.kernelIoActive=false;s.kernelIoConnection=nullptr;s.kernelTaskOwner=TASK_NULL;}
    s.deadline=0;s.unlockIssuer();if(!raw)connection.release();return raw;
}



bool ZornGen7HostRing26::nativeProcessTableLeaseHealthy(const ZornGen7SmmuDomain26 &domain,
    const ZornGen7ProcessTables26 &p) const
{
    if(!storage_ || !IORecursiveLockHaveLock(&storage_->gate) ||
       !nativeProcessContextHeldForDomain(domain,p))return false;
    const auto &s=*storage_;
    const bool kernel=s.kernelIoActive && p.clientOwner_==s.kernelIoConnection && p.clientTask_==kernel_task;
    const bool app=applicationOperationHeld() && p.clientOwner_==s.appExecution->client_ &&
        p.clientTask_==s.appExecution->task_ &&
        (s.appOperationKind==ZornGen7AppOperation26::Map || s.appOperationKind==ZornGen7AppOperation26::Close);
    if((!kernel && !app) || s.processSelected!=&p || s.processTransitionThread!=THREAD_NULL ||
       !p.vmAttached_ || p.vmDetached_ || p.state_.detached || p.state_.poisoned ||
       !p.clientOpen_ || p.clientClosed_ || !p.submitAttached_ || !p.clientState_ ||
       s.native.outstanding() || s.native.poisoned() || s.runtimeSubmit.outstanding() ||
       s.runtimeSubmit.poisoned() || s.runtimeVm.hasPendingSubmissionResources() ||
       s.ring.rptr!=s.ring.wptr || !s.ring.busy_valid || (s.ring.busy&(1u<<23)) ||
       (s.ring.status&~1u) || s.ring.irq || s.ring.hwfault)return false;
    for(auto *q=s.processClients;q;q=q->ringNext_)
        if(q->vm_.poisoned() || q->vm_.hasPendingSubmissionResources() ||
           (q->clientState_ && (q->clientState_->submit.outstanding() || q->clientState_->submit.poisoned())))return false;
    return true;
}
IOReturn ZornGen7HostRing26::beginNativeProcessTableLease(const ZornGen7SmmuDomain26 &domain,
    ZornGen7ProcessTables26 &p)
{
    if(!nativeProcessTableLeaseHealthy(domain,p))return kIOReturnNotReady;auto &s=*storage_;
    if(s.nativeProcessTableLease || s.nativeProcessTableAcquires!=s.nativeProcessTableReleases ||
       s.nativeProcessTableAcquires==UINT32_MAX)return kIOReturnNotReady;
    // Current issuer spans dispatch/close and excludes every other producer,
    // including presentation. Read the real ring/RBBM/GX outside metadata gate.
    IORecursiveLockUnlock(&s.gate);
    hhr_io io{};io.cookie=this;io.guard=guard;io.read=read;io.write=write;io.delay=delay;
    const auto idle=hhr_idle(&io,&s.ring);
    IORecursiveLockLock(&s.gate);
    if(idle || !nativeProcessTableLeaseHealthy(domain,p))return kIOReturnNotReady;
    s.nativeProcessTableLease=&p;++s.nativeProcessTableAcquires;return kIOReturnSuccess;
}
IOReturn ZornGen7HostRing26::endNativeProcessTableLease(const ZornGen7SmmuDomain26 &domain,
    ZornGen7ProcessTables26 &p)
{
    if(!nativeProcessTableLeaseHealthy(domain,p))return kIOReturnNotReady;auto &s=*storage_;
    if(s.nativeProcessTableLease!=&p || s.nativeProcessTableAcquires!=s.nativeProcessTableReleases+1)
        return kIOReturnNotReady;
    s.nativeProcessTableLease=nullptr;++s.nativeProcessTableReleases;return kIOReturnSuccess;
}

bool ZornGen7HostRing26::nativeProcessContextHeldForDomain(const ZornGen7SmmuDomain26 &domain,
    const ZornGen7ProcessTables26 &p) const
{
    if(!storage_ || !normal())return false;const auto &s=*storage_;
    if(s.hfi || &s.domain!=&domain || !s.issuerHeld() || s.nativeTableLease ||
       p.ringOwner_!=this || p.domain_!=&domain)return false;
    const bool kernel=current_task()==kernel_task && s.kernelIoActive && kernelClientExecutionHealthy() &&
        !s.appExecution && !s.appExecutionPending && !s.appOobActive && !s.appOobTransition && !s.appOperationPending;
    bool app=applicationOperationHeld();
    if(app){
        const bool bound=p.clientOwner_==s.appExecution->client_ && p.clientTask_==s.appExecution->task_;
        // AttachVm precedes client binding; DetachVm follows normal client
        // teardown. Only those exact serialized transitions admit no owner.
        const bool transition=s.processTransitionThread==current_thread() &&
            !p.clientOwner_ && p.clientTask_==TASK_NULL &&
            ((s.appOperationKind==ZornGen7AppOperation26::PrepareTables &&
              s.processTransitionOperation==ZornGen7ProcessTableOperation26::AttachVm && !p.clientOpenAttempted_) ||
             (s.appOperationKind==ZornGen7AppOperation26::Close &&
              s.processTransitionOperation==ZornGen7ProcessTableOperation26::DetachVm &&
              p.clientClosed_ && !p.clientOpen_ && !p.submitAttached_ && !p.clientState_));
        app=bound || transition;
    }
    if(!kernel && !app)return false;
    bool member=false;for(auto *q=s.processClients;q;q=q->ringNext_)if(q==&p)member=true;
    return member && (s.processSelected==&p ||
        s.processTransitionThread==current_thread());
}

void ZornGen7HostRing26::observeApplicationPrepare(uint32_t stage,IOReturn raw,uint32_t detail)
{
    if(!storage_)return;const auto &s=*storage_;
    // Capture failures even after a hardware guard stops the owner. This is
    // the serialized real client's diagnostic identity, never a grant.
    if(s.appExecution && s.appExecution->client_ && s.appOperationPending &&
       s.appOperationKind==ZornGen7AppOperation26::PrepareTables &&
       s.appOperationThread==current_thread() && s.appOperationThread!=THREAD_NULL)
        zorn26_application_prepare_event(reinterpret_cast<uintptr_t>(s.appExecution->client_),stage,uint32_t(raw),detail);
}

bool ZornGen7HostRing26::processTransitionHeldForDomain(const ZornGen7SmmuDomain26 &domain) const
{
    if(!storage_ || !normal())return false;const auto &s=*storage_;
    for(auto *p=s.processClients;p;p=p->ringNext_)
        if(p->vm_.poisoned() || (p->clientState_ && (p->clientState_->submit.outstanding() || p->clientState_->submit.poisoned())))return false;
    if(!s.hfi){
        const bool kernel=current_task()==kernel_task && s.kernelIoActive && kernelClientExecutionHealthy() &&
            !s.appExecution && !s.appExecutionPending && !s.appOobActive && !s.appOobTransition && !s.appOperationPending;
        const bool app=applicationOperationHeld() &&
            ((s.appOperationKind==ZornGen7AppOperation26::PrepareTables &&
              (s.processTransitionOperation==ZornGen7ProcessTableOperation26::Prepare ||
               s.processTransitionOperation==ZornGen7ProcessTableOperation26::Select ||
               s.processTransitionOperation==ZornGen7ProcessTableOperation26::AttachVm)) ||
             (s.appOperationKind==ZornGen7AppOperation26::Close &&
              (s.processTransitionOperation==ZornGen7ProcessTableOperation26::RestoreKernel ||
               s.processTransitionOperation==ZornGen7ProcessTableOperation26::DetachVm ||
               s.processTransitionOperation==ZornGen7ProcessTableOperation26::RetireDetached)));
        if(!s.issuerHeld() || (!kernel && !app) || s.nativeTableLease || s.nativeProcessTableLease ||
           !s.ring.busy_valid || (s.ring.busy&(1u<<23)) || (s.ring.status&~1u) ||
           s.ring.irq || s.ring.hwfault)return false;
    }
    return &s.domain==&domain && s.processTransitionThread==current_thread() &&
        s.processTransitionThread!=THREAD_NULL && processExecutionHealthy() &&
        !s.native.poisoned() && !s.runtimeSubmit.poisoned() && !s.native.outstanding() &&
        !s.runtimeSubmit.outstanding() && s.ring.rptr==s.ring.wptr;
}
IOReturn ZornGen7HostRing26::transitionProcessTables(IOUserClient &connection,
    ZornGen7ProcessTableOperation26 operation,ZornGen7ProcessTables26 *&p,unsigned inputBits,size_t capacity)
{
    if(!storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(&s.gate))return kIOReturnNotReady;
    s.lockIssuer();
    auto observe=[&](uint32_t stage,IOReturn raw,uint32_t detail=0){
        if(s.appExecution && s.appOperationPending && s.appOperationKind==ZornGen7AppOperation26::PrepareTables)
            zorn26_application_prepare_event(reinterpret_cast<uintptr_t>(s.appExecution->client_),stage,uint32_t(raw),detail);
    };

    auto done=[&](IOReturn raw){s.processTransitionThread=THREAD_NULL;s.deadline=0;s.unlockIssuer();return raw;};
    if(!processConnectionHeld(connection) || s.processTransitionThread!=THREAD_NULL){observe(24,kIOReturnNotReady,uint32_t(operation));return done(kIOReturnNotReady);}
    observe(24,0,uint32_t(operation));
    if(operation==ZornGen7ProcessTableOperation26::Prepare){if(p)return done(kIOReturnBadArgument);}
    else if(!p || p->ringOwner_!=this)return done(kIOReturnBadArgument);
    if(operation==ZornGen7ProcessTableOperation26::RestoreKernel && s.processSelected!=p)return done(kIOReturnNotReady);
    ZornGen7ProcessTables26 **membership=&s.processClients;
    if(p){while(*membership && *membership!=p)membership=&(*membership)->ringNext_;
        if(!*membership)return done(kIOReturnNotReady);}
    auto *next=p?p->ringNext_:nullptr;
    // Drain the actual submit jobs/fences,then read the actual hardware idle
    // state under the same issuer as all kernel commands. The existing held
    // execution callback/OOB supplies independent all-master exclusion.
    clock_interval_to_deadline(1000,NSEC_PER_MSEC,&s.deadline);
    auto raw=quiesceKernelIo();observe(25,raw,uint32_t(operation));if(raw)return done(raw);
    s.processTransitionOperation=operation;s.processTransitionThread=current_thread();
    const bool retiring=operation==ZornGen7ProcessTableOperation26::RetireDetached ||
        operation==ZornGen7ProcessTableOperation26::DiscardNeverInstalled;
    auto *previous=p;
    if(retiring)*membership=next;
    raw=s.domain.transitionHostProcessTables(*this,operation,p,inputBits,capacity);observe(26,raw,uint32_t(operation));
    if(retiring && raw && p)*membership=p;
    if(retiring && !p && s.kernelProcess==previous){s.kernelProcess=nullptr;s.kernelProcessReady=false;}
    if(operation==ZornGen7ProcessTableOperation26::Prepare && p){
        p->ringOwner_=this;p->ringNext_=s.processClients;s.processClients=p;
    }
    if(!raw){
        if(operation==ZornGen7ProcessTableOperation26::Select){s.processSelected=p;s.native.requestContextReset();}
        else if(operation==ZornGen7ProcessTableOperation26::RestoreKernel){s.processSelected=nullptr;s.native.requestContextReset();}
        // Retiring nodes were unlinked before the domain could release them.
    }else if(operation!=ZornGen7ProcessTableOperation26::Prepare &&
             operation!=ZornGen7ProcessTableOperation26::DiscardNeverInstalled){
        __atomic_store_n(&s.stopped,1u,__ATOMIC_RELEASE);s.irq.stopAndMask();
    }
    return done(raw);
}

IOReturn ZornGen7HostRing26::openProcessClient(IOUserClient &connection,ZornGen7ProcessTables26 &p,task_t owningTask)
{
    if(!storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(&s.gate))return kIOReturnNotReady;s.lockIssuer();
    auto done=[&](IOReturn raw){s.deadline=0;s.unlockIssuer();return raw;};
    // Each branch requires its actual independent execution owner. A valid
    // task pointer alone never selects or grants the application branch.
    const bool kernel=s.kernelIoConnection==&connection && owningTask==kernel_task &&
        s.kernelTaskOwner==owningTask && kernelClientExecutionHealthy();
    const bool app=applicationOperationHeld() && s.appExecution->client_==&connection &&
        s.appExecution->task_==owningTask && owningTask!=kernel_task;
    if((!kernel && !app) || !processConnectionHeld(connection) || s.processSelected!=&p || p.ringOwner_!=this ||
       p.domain_!=&s.domain || !p.vmAttached_ || p.vmDetached_ || p.state_.detached ||
       p.state_.poisoned || p.clientOpenAttempted_)return done(kIOReturnNotReady);
    clock_interval_to_deadline(1000,NSEC_PER_MSEC,&s.deadline);
    auto raw=quiesceKernelIo();if(raw)return done(raw);
    p.clientOpenAttempted_=true;connection.retain();p.clientOwner_=&connection;
    task_reference(owningTask);p.clientTask_=owningTask;
    using State=ZornGen7ProcessTables26::ClientStorage;
    void *bytes=IOMallocZero(sizeof(State));
    if(!bytes)return done(kIOReturnNoMemory);
    p.clientState_=new(bytes)State;
    IORecursiveLockLock(&s.gate);
    raw=p.clientState_->submit.attach(&p.vm_,&s.native,&s.presentProgress);p.submitAttached_=raw==kIOReturnSuccess;
    if(!raw)raw=p.clientState_->client.open(NativeAdrenoAbiVersion,&p.vm_,&p.clientState_->submit,&s.native,
        p.arena_.config.input_bits,p.arena_.config.output_bits);
    // Both admitted client kinds use the actual isolated process aperture
    // and configured GPU metadata. Kernel qualification also calls GetDeviceInfo.
    // Each client has its own actual submit/VM instance. Queue range0
    // is local to that instance;no cross-client queue-base invention. Its VA
    // window excludes every immutable kernel seed,as prepared and audited.
    if(!raw){
        const uint64_t limit=UINT64_C(1)<<p.arena_.config.input_bits;
        if(!p.clientVaStart_ || !p.clientVaBytes_ || p.clientVaStart_>=limit ||
           p.clientVaBytes_>limit-p.clientVaStart_)raw=kIOReturnNotReady;
        for(size_t i=0;!raw && i<p.count_;++i){const auto &seed=p.ranges_[i];
            if(seed.iova<p.clientVaStart_+p.clientVaBytes_ &&
               p.clientVaStart_<seed.iova+seed.bytes)raw=kIOReturnNotReady;}
        if(!raw)raw=p.clientState_->client.setScope(0,p.clientVaStart_,p.clientVaBytes_);
        if(!raw)raw=s.registers.copyConfiguredDeviceInfo(p.clientState_->info);
        if(!raw){p.clientState_->info.va_start=p.clientVaStart_;p.clientState_->info.va_size=p.clientVaBytes_;
            raw=p.clientState_->client.attachDeviceInfo(&p.clientState_->info);}
    }
    if(!raw && app){
        // Reuse the actual retained high/low/high NativeAdrenoTimer reader.
        // CP register indices are independently present in Gen7 gen7_reg.h;
        // do not import the alternative SM8550 GMU byte-offset geometry.
        if(!raw){const NativeAdrenoTimeIo timerIo{this,nativeRead};
            raw=p.clientState_->timer.attach(&timerIo,NativeAdrenoTimeCp);}
        if(!raw)raw=p.clientState_->client.attachTimer(&p.clientState_->timer);
    }
    p.clientOpen_=raw==kIOReturnSuccess;
    IORecursiveLockUnlock(&s.gate);
    if(raw || !processExecutionHealthy()){
        __atomic_store_n(&s.stopped,1u,__ATOMIC_RELEASE);s.irq.stopAndMask();
        return done(raw?raw:kIOReturnNotReady);
    }
    return done(kIOReturnSuccess);
}
IOReturn ZornGen7HostRing26::dispatchProcessClient(IOUserClient &connection,ZornGen7ProcessTables26 &p,task_t callingTask,
    uint32_t method,const void *input,size_t inputBytes,void *output,size_t outputBytes)
{
    if(!storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;
    if(method<NativeAdrenoMethodQuery || method>NativeAdrenoMethodSubmitBatch ||
       inputBytes!=ZornGen7DirectClient26::inputSize(method) || outputBytes!=ZornGen7DirectClient26::outputSize(method) ||
       (inputBytes && !input) || (outputBytes && !output) || outputBytes>sizeof(NativeAdrenoAbiMetadata))return kIOReturnBadArgument;
    if(IORecursiveLockHaveLock(&s.gate))return kIOReturnNotReady;s.lockIssuer();
    auto done=[&](IOReturn raw){s.deadline=0;s.unlockIssuer();return raw;};
    const bool kernel=s.kernelIoConnection==&connection && callingTask==kernel_task &&
        p.clientTask_==s.kernelTaskOwner && !s.kernelProcessClosing && kernelClientExecutionHealthy();
    const bool app=applicationOperationHeld() && s.appExecution->client_==&connection &&
        p.clientTask_==s.appExecution->task_;
    if(!callingTask || (!kernel && !app) || !processConnectionHeld(connection) || s.processSelected!=&p || p.ringOwner_!=this ||
       p.domain_!=&s.domain || p.clientOwner_!=&connection || !p.clientOpen_ || p.clientClosed_ ||
       !p.vmAttached_ || p.vmDetached_ || p.state_.detached || p.state_.poisoned ||
       !p.submitAttached_ || p.clientState_->submit.poisoned())return done(kIOReturnNotReady);
    clock_interval_to_deadline(1000,NSEC_PER_MSEC,&s.deadline);
    alignas(8) uint8_t reply[sizeof(NativeAdrenoAbiMetadata)]{};
    NativeAdrenoRingClock clock{this,nativeNow,nativeIdle};
    const bool fenceWait=method==NativeAdrenoMethodWaitFence;
    struct FenceWaitClock {
        ZornGen7HostRing26 *owner;
        bool idleRefused=false;
    } wait{this};
    // The ring's Timeout also represents an idle callback refusal. Capture
    // that result only for the public WaitFence call, which may time out normally.
    NativeAdrenoRingClock waitClock{&wait,nativeNow,[](void *context) {
        auto &state=*static_cast<FenceWaitClock *>(context);
        const int raw=nativeIdle(state.owner);
        if(raw)state.idleRefused=true;
        return raw;
    }};
    const bool table=method==NativeAdrenoMethodBoMap || method==NativeAdrenoMethodBoFree;
    auto raw=table?quiesceKernelIo():kIOReturnSuccess;
    if(!raw){
        if(table)IORecursiveLockLock(&s.gate);
        // The address belongs to the task making this external-method call,
        // as in the retained native producer. The real calling task is held
        // across this entire call;its independent execution branch is checked above.
        if(method==NativeAdrenoMethodBoImport){NativeAdrenoAbiBoImport request{};memcpy(&request,input,sizeof(request));
            raw=p.clientState_->client.importBo(&request,callingTask,reinterpret_cast<NativeAdrenoAbiBoAllocReply *>(reply));}
        else raw=p.clientState_->client.dispatch(method,input,inputBytes,reply,outputBytes,fenceWait?&waitClock:&clock);
        if(table)IORecursiveLockUnlock(&s.gate);
    }
    const bool waitExpired=fenceWait && raw==kIOReturnTimeout && !wait.idleRefused && !guard(this);
    if(fenceWait && raw==kIOReturnTimeout && !waitExpired)raw=kIOReturnNotReady;
    const bool uncertain=(raw==kIOReturnTimeout && !waitExpired) ||
        raw==kIOReturnIOError || raw==kIOReturnNotReady || raw==kIOReturnNotPermitted;
    if(uncertain || !processExecutionHealthy() || s.native.poisoned() ||
       p.clientState_->submit.poisoned() || p.vm_.poisoned()){
        __atomic_store_n(&s.stopped,1u,__ATOMIC_RELEASE);s.irq.stopAndMask();
        return done(raw && !waitExpired?raw:kIOReturnNotReady);
    }
    // An elapsed wait budget does not retire work or release its resources.
    if(app && waitExpired)s.appFenceWaitExpired=true;
    if(!raw && outputBytes)memcpy(output,reply,outputBytes);return done(raw);
}
IOReturn ZornGen7HostRing26::closeProcessClient(IOUserClient &connection,ZornGen7ProcessTables26 &p)
{
    if(!storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(&s.gate))return kIOReturnNotReady;s.lockIssuer();
    auto done=[&](IOReturn raw){s.deadline=0;s.unlockIssuer();return raw;};
    if(!processConnectionHeld(connection) || s.processSelected!=&p || p.ringOwner_!=this ||
       p.clientOwner_!=&connection || !p.clientOpen_ || p.clientClosed_ ||
       !p.submitAttached_ || p.state_.poisoned)return done(kIOReturnNotReady);
    clock_interval_to_deadline(1000,NSEC_PER_MSEC,&s.deadline);
    auto raw=quiesceKernelIo();NativeAdrenoRingClock clock{this,nativeNow,nativeIdle};
    zorn26_client_event240(21); // original quiesce returned;raw retains its real result
    if(!raw){
        IORecursiveLockLock(&s.gate);
        // Existing diagnostic scalar,scoped immediately before this real call.
        // This is neither a native return value nor hardware completion.
        native_adreno_trace_stage=100;
        raw=p.clientState_->client.releaseAll(&clock,0);
        zorn26_client_event240(22); // original releaseAll returned;no completion inferred
        if(!raw){p.clientOpen_=false;p.clientClosed_=true;raw=p.clientState_->submit.detach();}
        if(!raw){
            p.submitAttached_=false;
            if(s.appExecution && s.appExecution->client_==&connection)raw=p.clientState_->timer.detach();
        }
        if(!raw){
            auto *state=p.clientState_;
            state->~ClientStorage();IOFree(state,sizeof(ZornGen7ProcessTables26::ClientStorage));p.clientState_=nullptr;
            zorn26_client_event240(23); // only after actual successful detach/destruction/free
        }
        IORecursiveLockUnlock(&s.gate);
    }
    if(raw || !processExecutionHealthy()){
        __atomic_store_n(&s.stopped,1u,__ATOMIC_RELEASE);s.irq.stopAndMask();return done(raw?raw:kIOReturnNotReady);}
    auto task=p.clientTask_;p.clientTask_=TASK_NULL;p.clientOwner_=nullptr;
    done(kIOReturnSuccess);if(task)task_deallocate(task);connection.release();return kIOReturnSuccess;
    // Normal caller now explicitly restores kernel,detaches VM and retires
    // its ASID/pages through the existing private transition sequence. No
    // destructor or failure path automatically switches/frees anything.
}

IOReturn ZornGen7HostRing26::initializeKernelProcess(IOUserClient &connection)
{
    if(!storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;
    ZornGen7ProcessTables26 *p=nullptr;
    auto raw=transitionProcessTables(connection,ZornGen7ProcessTableOperation26::Prepare,p,
        s.logical.input_bits,s.runtimeCapacity);
    s.lockIssuer();s.kernelProcess=p;s.unlockIssuer();
    if(!raw)raw=transitionProcessTables(connection,ZornGen7ProcessTableOperation26::Select,p,0,0);
    if(!raw)raw=transitionProcessTables(connection,ZornGen7ProcessTableOperation26::AttachVm,p,0,s.runtimeCapacity);
    if(!raw)raw=openProcessClient(connection,*p,s.kernelTaskOwner);
    s.lockIssuer();
    if(!raw && kernelClientExecutionHealthy())s.kernelProcessReady=true;
    else {if(!raw)raw=kIOReturnNotReady;__atomic_store_n(&s.stopped,1u,__ATOMIC_RELEASE);s.irq.stopAndMask();}
    s.unlockIssuer();return raw;
    // One actual kernel-only client construction chain,not a successful
    // provider fixture. Any partial remains held;no automatic retry/rollback.
}
IOReturn ZornGen7HostRing26::closeKernelIo(IOUserClient &connection)
{
    if(!storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(&s.gate))return kIOReturnNotReady;s.lockIssuer();
    auto *p=s.kernelProcess;
    if(!p || !s.kernelProcessReady || s.kernelProcessClosing || s.kernelIoConnection!=&connection ||
       s.kernelIoClosing || s.kernelIoClosed || !kernelClientExecutionHealthy()){
        s.unlockIssuer();return kIOReturnNotReady;}
    s.kernelProcessClosing=true;s.unlockIssuer();
    // Normal closure,with actual completion,BO unmap and metadata release.
    // Every later stage runs only after its real predecessor succeeded.
    auto raw=closeProcessClient(connection,*p);
    if(!raw)raw=transitionProcessTables(connection,ZornGen7ProcessTableOperation26::RestoreKernel,p,0,0);
    if(!raw)raw=transitionProcessTables(connection,ZornGen7ProcessTableOperation26::DetachVm,p,0,0);
    if(!raw)raw=transitionProcessTables(connection,ZornGen7ProcessTableOperation26::RetireDetached,p,0,0);
    if(!raw)raw=closeKernelIoBase(connection);
    if(raw){__atomic_store_n(&s.stopped,1u,__ATOMIC_RELEASE);s.irq.stopAndMask();}
    return raw;
    // No automatic context restoration or release on an error. The old
    // execution-window release remains last,after the process list is empty.
}

bool ZornGen7HostRing26::nativeApplicationBinding(IOUserClient &client,task_t task,unsigned phase,
    ZornGen7AppOperation26 operation) const
{
    if(!storage_ || !normal() || !task || task==kernel_task || !bootstrapHealthy())return false;const auto &s=*storage_;
    if(s.hfi || !s.applicationIoPublishAttempted || !s.applicationIoService || s.kernelIoPublishAttempted ||
       s.kernelIoAttempted || s.kernelIoConnection || s.kernelIoActive || s.kernelTaskActive ||
       s.kernelTaskThread!=THREAD_NULL || !s.runtimeReady || !s.runtimeOwner || !s.bootstrapComplete ||
       !s.kernelTaskComplete || s.kernelTaskRaw || !s.imageVerified || !s.imageUnmapped ||
       !s.taskReleaseAllowed || !s.imageFence || s.imageMemory.quarantined() || s.imageMemory.deviceReferences() ||
       s.nativeTableLease || s.nativeTableAcquires!=2 || s.nativeTableReleases!=2 || !s.nativeAdopted ||
       s.native.completedFence()<s.imageFence || s.native.poisoned() || s.runtimeVm.poisoned() ||
       s.runtimeSubmit.poisoned() || !s.appExecutionPending || s.appAuthorityClient!=&client ||
       s.appAuthorityTask!=task || s.appAuthorityPhase!=phase || s.appAuthorityOperation!=operation ||
       __atomic_load_n(&s.appAuthorityThread,__ATOMIC_ACQUIRE)!=current_thread() || s.issuerHeld() ||
       !IORecursiveLockHaveLock(&s.gate))return false;
    // The Board callback owns this exact startup/driver gate while checking
    // its live authority. Foreign-call entry still requires the gate unlocked;
    // issuer and pending caller/task/thread/phase checks above remain required.
    const bool closing=phase==3 || (phase==2 && (operation==ZornGen7AppOperation26::Close || operation==ZornGen7AppOperation26::OobRelease));
    if(current_task()!=task && (!closing || current_task()!=kernel_task))return false;
    auto *actual=OSDynamicCast(ZornGen7AppIoClient26,&client);
    if(!actual || !actual->matchesOwnedSession(*this,s.applicationIoService,task,closing))return false;
    if(phase==1)return !s.appExecution && !s.appOobActive && !s.appOobTransition && !s.appOperationPending &&
        !s.processClients && !s.processSelected && !s.nativeProcessTableLease &&
        !s.native.outstanding() && !s.runtimeSubmit.outstanding();
    auto *execution=s.appExecution;
    if(!execution || execution->client_!=&client || execution->task_!=task)return false;
    if(phase==2){
        if(operation==ZornGen7AppOperation26::OobAcquire || operation==ZornGen7AppOperation26::OobRelease)
            return s.appOobTransition && s.appOobThread==current_thread() && !s.appOperationPending &&
                !s.processClients && !s.processSelected && !s.nativeProcessTableLease &&
                !s.native.outstanding() && !s.runtimeSubmit.outstanding() &&
                (s.appOobActive==(operation==ZornGen7AppOperation26::OobRelease));
        return s.appOperationPending && s.appOperationKind==operation && s.appOperationThread==THREAD_NULL && !s.appOobTransition &&
            s.appOobActive && applicationOobHeldForTransport(*execution) &&
            unsigned(operation)<=unsigned(ZornGen7AppOperation26::Timestamp);
    }
    if(phase!=3)return false;const auto &oob=execution->oob_;
    return !s.appOperationPending && !s.appOobTransition && !s.appOobActive && !s.processClients && !s.processSelected &&
        !s.nativeProcessTableLease && s.nativeProcessTableAcquires==s.nativeProcessTableReleases &&
        !s.native.outstanding() && !s.runtimeSubmit.outstanding() && !s.runtimeVm.hasPendingSubmissionResources() &&
        s.ring.rptr==s.ring.wptr && oob.owner==&s.hfiOwner && oob.attempted && oob.requestReturned &&
        oob.ackObserved && oob.ackCleared && oob.gxOn && oob.releaseAttempted && oob.releaseWriteReturned && !oob.raw;
}

IOReturn ZornGen7HostRing26::prepareApplicationExecution(IOUserClient &client,task_t task,UInt32 openType,
    OSObject &codeOwner,const ZornGen7AppAuthority26 &authority,ZornGen7AppExecution26 *&out)
{
    if(out || !storage_ || !normal() || !task || task==kernel_task || task!=current_task())return kIOReturnBadArgument;
    auto &s=*storage_;if(IORecursiveLockHaveLock(&s.gate))return kIOReturnNotReady;
    CallerTaskReference caller; // actual opening task remains held across policy/foreign calls
    auto *provider=client.getProvider();if(!provider)return kIOReturnNotReady;
    provider->retain();client.retain();
    auto admission=ZornGen7AdmitTaskService26(*provider,task,openType);
    if(!admission)admission=ZornGen7AdmitTaskClient26(client,task,openType);
    client.release();provider->release();if(admission)return admission;
    s.lockIssuer();
    if(s.appExecution || s.appExecutionPending || s.kernelIoConnection ||
       (s.kernelIoAttempted && !s.kernelIoClosed) || s.kernelIoActive || s.processClients ||
       !s.runtimeReady || !s.kernelTaskComplete || !s.imageVerified || !s.imageUnmapped || !s.taskReleaseAllowed ||
       !bootstrapHealthy() || s.native.outstanding() || s.runtimeSubmit.outstanding() ||
       s.native.poisoned() || s.runtimeSubmit.poisoned()){
        s.unlockIssuer();return kIOReturnNotReady;}
    s.appExecutionPending=true;s.setAppAuthorityCall(client,task,1,ZornGen7AppOperation26::PrepareTables);s.unlockIssuer();
    ZornGen7AppExecution26 *p=nullptr;
    const auto raw=s.maps.createApplicationExecution(*this,s.gate,client,task,codeOwner,authority,p);
    s.lockIssuer();s.clearAppAuthorityCall();s.appExecutionPending=false;
    if(p){p->retain();s.appExecution=p;out=p;} // own reference separate from output/self-pin
    if(raw || !bootstrapHealthy()){
        if(p){__atomic_store_n(&s.stopped,1u,__ATOMIC_RELEASE);s.irq.stopAndMask();}
        s.unlockIssuer();return raw?raw:kIOReturnNotReady;}
    s.unlockIssuer();return kIOReturnSuccess;
    // Acquires a distinct permission owner only. Application OOB,VM/service
    // activation and publication still need their actual separate connection.
}
IOReturn ZornGen7HostRing26::checkApplicationExecution(IOUserClient &client,
    ZornGen7AppExecution26 &execution,ZornGen7AppOperation26 operation)
{
    if(!storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(&s.gate))return kIOReturnNotReady;s.lockIssuer();
    if(s.appExecution!=&execution || s.appExecutionPending || !bootstrapHealthy()){
        s.unlockIssuer();return kIOReturnNotReady;}
    s.appExecutionPending=true;s.setAppAuthorityCall(client,execution.task_,2,operation);execution.retain();s.unlockIssuer();
    auto raw=execution.checkCurrent(client,operation);
    s.lockIssuer();s.clearAppAuthorityCall();s.appExecutionPending=false;
    if(raw || !bootstrapHealthy()){
        if(!raw)raw=kIOReturnNotReady;__atomic_store_n(&s.stopped,1u,__ATOMIC_RELEASE);s.irq.stopAndMask();}
    s.unlockIssuer();execution.release();return raw;
}
IOReturn ZornGen7HostRing26::closeApplicationExecution(IOUserClient &client,ZornGen7AppExecution26 *&p)
{
    if(!p || !storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(&s.gate))return kIOReturnNotReady;s.lockIssuer();
    // Actual process/VM retirement and actual OOB clear must precede
    // relinquishing the independent application execution authority.
    if(s.appExecution!=p || s.appExecutionPending || s.appOperationPending || s.appOobTransition || s.appOobActive || s.kernelIoActive || s.processClients ||
       s.native.outstanding() || s.runtimeSubmit.outstanding() || s.native.poisoned() || s.runtimeSubmit.poisoned()){
        s.unlockIssuer();return kIOReturnNotReady;}
    s.appExecutionPending=true;s.setAppAuthorityCall(client,p->task_,3,ZornGen7AppOperation26::Close);s.unlockIssuer();
    const auto raw=p->closeAcquiredSession(client);
    s.lockIssuer();s.clearAppAuthorityCall();s.appExecutionPending=false;
    if(!raw){auto *closed=p;s.appExecution=nullptr;p=nullptr;s.unlockIssuer();
        closed->release();closed->release();return kIOReturnSuccess;}
    __atomic_store_n(&s.stopped,1u,__ATOMIC_RELEASE);s.irq.stopAndMask();s.unlockIssuer();return raw;
}

bool ZornGen7HostRing26::applicationOobPermission(const ZornGen7HwschedHfi26 &hfi,ZornGen7AppExecution26 &execution,bool release)
{return applicationOobPermissionForTransport(hfi,execution,release);}
bool ZornGen7HostRing26::applicationOobReleaseReady(const ZornGen7HwschedHfi26 &hfi,const ZornGen7AppExecution26 &execution) const
{return applicationOobReleaseReadyForTransport(hfi,execution);}
bool ZornGen7HostRing26::applicationOobPermission(const ZornGen7DirectHfi26 &hfi,ZornGen7AppExecution26 &execution,bool release)
{return applicationOobPermissionForTransport(hfi,execution,release);}
bool ZornGen7HostRing26::applicationOobReleaseReady(const ZornGen7DirectHfi26 &hfi,const ZornGen7AppExecution26 &execution) const
{return applicationOobReleaseReadyForTransport(hfi,execution);}
bool ZornGen7HostRing26::applicationOobHeldForTransport(const ZornGen7AppExecution26 &execution) const
{
    if(!storage_)return false;const auto &s=*storage_;
    if(s.hfi)return s.hfi->applicationOobHeld(*this,execution);
    auto *direct=OSDynamicCast(ZornGen7DirectHfi26,&s.hfiOwner);
    return direct && direct->applicationOobHeld(*this,execution);
}
bool ZornGen7HostRing26::applicationOobPermissionForTransport(const OSObject &hfi,
    ZornGen7AppExecution26 &execution,bool release)
{
    if(!storage_ || !normal() || &storage_->hfiOwner!=&hfi || !execution.client_)return false;
    return checkApplicationExecution(*execution.client_,execution,
        release?ZornGen7AppOperation26::OobRelease:ZornGen7AppOperation26::OobAcquire)==kIOReturnSuccess;
}
bool ZornGen7HostRing26::applicationOobReleaseReadyForTransport(const OSObject &hfi,
    const ZornGen7AppExecution26 &execution) const
{
    if(!storage_ || !normal())return false;const auto &s=*storage_;
    return &s.hfiOwner==&hfi && s.appExecution==&execution && s.appOobTransition && s.appOobActive &&
        s.appReleaseIdleThread==current_thread() && !s.processClients && !s.processSelected &&
        !s.native.outstanding() && !s.runtimeSubmit.outstanding() && !s.native.poisoned() &&
        !s.runtimeSubmit.poisoned() && s.ring.rptr==s.ring.wptr;
    // Own-source drain/idle marker only. Real independent all-master/window
    // authority is still checked separately before the actual OOB clear.
}
IOReturn ZornGen7HostRing26::acquireApplicationOob(IOUserClient &client,ZornGen7AppExecution26 &execution)
{
    if(!storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(&s.gate))return kIOReturnNotReady;s.lockIssuer();
    if(s.appExecution!=&execution || execution.client_!=&client || s.appExecutionPending || s.appOperationPending ||
       s.appOobTransition || s.appOobActive || s.kernelIoActive || s.processClients || !bootstrapHealthy()){
        s.unlockIssuer();return kIOReturnNotReady;}
    s.appOobTransition=true;s.appOobThread=current_thread();execution.retain();s.unlockIssuer();
    auto *direct=OSDynamicCast(ZornGen7DirectHfi26,&s.hfiOwner);
    auto raw=s.hfi?s.hfi->acquireApplicationOob(*this,execution):
        (direct?direct->acquireApplicationOob(*this,execution):kIOReturnNotReady);
    s.lockIssuer();s.appOobTransition=false;s.appOobThread=THREAD_NULL;
    if(!raw)s.appOobActive=true;
    if(raw || !bootstrapHealthy()){
        if(!raw)raw=kIOReturnNotReady;__atomic_store_n(&s.stopped,1u,__ATOMIC_RELEASE);s.irq.stopAndMask();}
    s.unlockIssuer();execution.release();return raw;
}
IOReturn ZornGen7HostRing26::releaseApplicationOob(IOUserClient &client,ZornGen7AppExecution26 &execution)
{
    if(!storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(&s.gate))return kIOReturnNotReady;s.lockIssuer();
    if(s.appExecution!=&execution || execution.client_!=&client || s.appExecutionPending || s.appOperationPending || s.appOobTransition ||
       !s.appOobActive || s.kernelIoActive || s.processClients || s.processSelected ||
       s.native.outstanding() || s.runtimeSubmit.outstanding() || s.native.poisoned() || s.runtimeSubmit.poisoned()){
        s.unlockIssuer();return kIOReturnNotReady;}
    s.appOobTransition=true;s.appOobThread=current_thread();execution.retain();s.unlockIssuer();
    struct IdleContext {ZornGen7HostRing26 *ring;ZornGen7AppExecution26 *execution;} context{this,&execution};
    hhr_io io{};io.cookie=&context;
    io.guard=[](void *cookie){auto &c=*static_cast<IdleContext *>(cookie);
        return c.ring->applicationOobPermissionForTransport(c.ring->storage_->hfiOwner,*c.execution,true)?guard(c.ring):1;};
    io.read=[](void *cookie,uint32_t at,uint32_t *value){auto &c=*static_cast<IdleContext *>(cookie);
        if(!c.ring->applicationOobPermissionForTransport(c.ring->storage_->hfiOwner,*c.execution,true))return 1;
        return read(c.ring,at,value);};
    io.delay=[](void *cookie,unsigned us){return delay(static_cast<IdleContext *>(cookie)->ring,us);};
    IOReturn raw=hhr_idle(&io,&s.ring)?kIOReturnNotReady:kIOReturnSuccess;
    if(!raw){s.appReleaseIdleThread=current_thread();auto *direct=OSDynamicCast(ZornGen7DirectHfi26,&s.hfiOwner);
        raw=s.hfi?s.hfi->releaseApplicationOob(*this,execution):
            (direct?direct->releaseApplicationOob(*this,execution):kIOReturnNotReady);}
    s.lockIssuer();s.appReleaseIdleThread=THREAD_NULL;s.appOobTransition=false;s.appOobThread=THREAD_NULL;
    if(!raw && !bootstrapHealthy())raw=kIOReturnNotReady;
    if(!raw)s.appOobActive=false;
    else {__atomic_store_n(&s.stopped,1u,__ATOMIC_RELEASE);s.irq.stopAndMask();}
    s.unlockIssuer();execution.release();return raw;
}

bool ZornGen7HostRing26::applicationOperationHeld() const
{
    if(!storage_ || !normal())return false;const auto &s=*storage_;
    const bool held=s.appExecution && s.appExecution->client_ && s.appOperationPending &&
        s.appOperationThread==current_thread() && s.appOperationThread!=THREAD_NULL &&
        !s.appExecutionPending && !s.appOobTransition && s.appOobActive && !s.kernelIoActive &&
        !__atomic_load_n(&s.stopped,__ATOMIC_ACQUIRE) && !s.irq.halted() && !s.gmu.halted() &&
        !s.hfiHalted() && !s.domain.faulted() && applicationOobHeldForTransport(*s.appExecution);
    if(!held || s.hfi)return held;
    const auto task=s.appExecution->task_;const bool closing=s.appOperationKind==ZornGen7AppOperation26::Close;
    if(!task || task==kernel_task || (current_task()!=task && (!closing || current_task()!=kernel_task)) ||
       unsigned(s.appOperationKind)>unsigned(ZornGen7AppOperation26::Timestamp) ||
       s.appOperationKind==ZornGen7AppOperation26::OobAcquire || s.appOperationKind==ZornGen7AppOperation26::OobRelease ||
       !s.applicationIoPublishAttempted || !s.applicationIoService || s.kernelIoService || s.kernelIoAttempted ||
       s.kernelIoConnection || s.kernelTaskActive || s.kernelTaskThread!=THREAD_NULL)return false;
    auto *actual=OSDynamicCast(ZornGen7AppIoClient26,s.appExecution->client_);
    return actual && actual->matchesOwnedSession(*this,s.applicationIoService,task,closing);
    // Exact serialized operation and real OOB observation accompany the Board
    // grant. Native PM/provider/MMIO/SMMU access guards remain mandatory.
}
bool ZornGen7HostRing26::processExecutionHealthy() const
{return kernelClientExecutionHealthy() || applicationOperationHeld();}
bool ZornGen7HostRing26::processConnectionHeld(IOUserClient &client) const
{
    if(!storage_ || !normal())return false;const auto &s=*storage_;
    return (s.kernelIoConnection==&client && !s.kernelIoClosing && !s.kernelIoClosed && kernelClientExecutionHealthy()) ||
        (applicationOperationHeld() && s.appExecution->client_==&client);
}
IOReturn ZornGen7HostRing26::beginApplicationOperation(IOUserClient &client,
    ZornGen7AppOperation26 operation,ZornGen7AppExecution26 *&scope)
{
    if(scope || !storage_ || !normal())return kIOReturnBadArgument;auto &s=*storage_;
    if(IORecursiveLockHaveLock(&s.gate))return kIOReturnNotReady;s.lockIssuer();
    auto *execution=s.appExecution;
    if(!execution || execution->client_!=&client || s.appOperationPending || s.appExecutionPending ||
       s.appOobTransition || !s.appOobActive || s.kernelIoActive || !bootstrapHealthy()){
        s.unlockIssuer();return kIOReturnNotReady;}
    s.appFenceWaitExpired=false;
    s.appOperationKind=operation;s.appOperationPending=true;execution->retain();s.unlockIssuer();
    // Fresh real whole-operation authorization,with no issuer/domain lock.
    auto raw=checkApplicationExecution(client,*execution,operation);
    if(operation==ZornGen7AppOperation26::PrepareTables)zorn26_application_prepare_event(reinterpret_cast<uintptr_t>(&client),16,uint32_t(raw),0);
    s.lockIssuer();
    if(!raw && s.appExecution==execution && s.appOobActive && !s.appOobTransition &&
       bootstrapHealthy() && applicationOobHeldForTransport(*execution)){
        s.appOperationThread=current_thread();scope=execution;
        s.unlockIssuer();return kIOReturnSuccess;
    }
    if(!raw)raw=kIOReturnNotReady;
    if(operation==ZornGen7AppOperation26::PrepareTables)zorn26_application_prepare_event(reinterpret_cast<uintptr_t>(&client),17,uint32_t(raw),0);
    s.appOperationPending=false;s.appOperationKind=ZornGen7AppOperation26::PrepareTables;
    __atomic_store_n(&s.stopped,1u,__ATOMIC_RELEASE);s.irq.stopAndMask();
    s.unlockIssuer();execution->release();return raw;
}
IOReturn ZornGen7HostRing26::finishApplicationOperation(ZornGen7AppExecution26 &execution,IOReturn raw)
{
    auto &s=*storage_;s.lockIssuer();
    const bool matches=s.appExecution==&execution &&
        s.appOperationThread==current_thread() && s.appOperationPending;
    const bool reportedExpiry=raw==kIOReturnTimeout && s.appFenceWaitExpired;
    const bool waitExpired=reportedExpiry && matches && applicationOperationHeld() && bootstrapHealthy();
    if((!raw && (!matches || !bootstrapHealthy())) || (reportedExpiry && !waitExpired))raw=kIOReturnNotReady;
    s.appOperationThread=THREAD_NULL;s.appOperationPending=false;s.appFenceWaitExpired=false;
    s.appOperationKind=ZornGen7AppOperation26::PrepareTables;
    if((raw==kIOReturnTimeout && !waitExpired) ||
       raw==kIOReturnIOError || raw==kIOReturnNotReady || raw==kIOReturnNotPermitted){
        __atomic_store_n(&s.stopped,1u,__ATOMIC_RELEASE);s.irq.stopAndMask();}
    s.unlockIssuer();execution.release();return raw;
}
IOReturn ZornGen7HostRing26::openApplicationProcess(IOUserClient &client,ZornGen7AppExecution26 &execution,
    ZornGen7ProcessTables26 *&out)
{
    auto observe=[&](uint32_t stage,IOReturn raw){zorn26_application_prepare_event(reinterpret_cast<uintptr_t>(&client),stage,uint32_t(raw),0);};
    observe(1,0);
    if(out || !storage_ || !normal())return kIOReturnBadArgument;
    ZornGen7AppExecution26 *scope=nullptr;
    auto raw=beginApplicationOperation(client,ZornGen7AppOperation26::PrepareTables,scope);observe(2,raw);if(raw)return raw;
    if(scope!=&execution){observe(3,kIOReturnNotReady);return finishApplicationOperation(*scope,kIOReturnNotReady);}
    observe(3,0);
    auto &s=*storage_;s.lockIssuer();const bool empty=!s.processClients && !s.processSelected;s.unlockIssuer();
    observe(4,empty?kIOReturnSuccess:kIOReturnBusy);
    if(!empty)return finishApplicationOperation(*scope,kIOReturnBusy);
    raw=transitionProcessTables(client,ZornGen7ProcessTableOperation26::Prepare,out,s.logical.input_bits,s.runtimeCapacity);observe(5,raw);
    if(!raw){raw=transitionProcessTables(client,ZornGen7ProcessTableOperation26::Select,out,0,0);observe(6,raw);}
    if(!raw){raw=transitionProcessTables(client,ZornGen7ProcessTableOperation26::AttachVm,out,0,s.runtimeCapacity);observe(7,raw);}
    if(!raw){raw=openProcessClient(client,*out,execution.task_);observe(8,raw);}
    if(raw){__atomic_store_n(&s.stopped,1u,__ATOMIC_RELEASE);s.irq.stopAndMask();}
    raw=finishApplicationOperation(*scope,raw);observe(9,raw);return raw;
}
IOReturn ZornGen7HostRing26::dispatchApplicationProcess(IOUserClient &client,ZornGen7AppExecution26 &execution,
    ZornGen7ProcessTables26 &process,uint32_t method,const void *input,size_t inputBytes,void *output,size_t outputBytes)
{
    if(!storage_ || !normal() || outputBytes>sizeof(NativeAdrenoAbiMetadata) || (outputBytes && !output) ||
       method<NativeAdrenoMethodQuery || method>NativeAdrenoMethodSubmitBatch ||
       inputBytes!=ZornGen7DirectClient26::inputSize(method) || outputBytes!=ZornGen7DirectClient26::outputSize(method) ||
       (inputBytes && !input))return kIOReturnBadArgument;
    CallerTaskReference caller;if(!caller.task)return kIOReturnBadArgument;
    auto operation=ZornGen7AppOperation26::CpuView;
    if(method==NativeAdrenoMethodBoMap || method==NativeAdrenoMethodBoFree)operation=ZornGen7AppOperation26::Map;
    else if(method==NativeAdrenoMethodSubmit || method==NativeAdrenoMethodSubmitBatch)operation=ZornGen7AppOperation26::Submit;
    else if(method==NativeAdrenoMethodWaitFence)operation=ZornGen7AppOperation26::Wait;
    else if(method==NativeAdrenoMethodGetTimestamp)operation=ZornGen7AppOperation26::Timestamp;
    ZornGen7AppExecution26 *scope=nullptr;auto raw=beginApplicationOperation(client,operation,scope);if(raw)return raw;
    if(scope!=&execution)return finishApplicationOperation(*scope,kIOReturnNotReady);
    alignas(8) uint8_t reply[sizeof(NativeAdrenoAbiMetadata)]{};
    raw=dispatchProcessClient(client,process,caller.task,method,input,inputBytes,reply,outputBytes);
    raw=finishApplicationOperation(*scope,raw);
    if(!raw && outputBytes)memcpy(output,reply,outputBytes);return raw;
}
IOReturn ZornGen7HostRing26::closeApplicationProcess(IOUserClient &client,ZornGen7AppExecution26 &execution,
    ZornGen7ProcessTables26 *&process)
{
    zorn26_client_close_reset242(); // new scope for this actual Close invocation
    if(!process || !storage_ || !normal())return kIOReturnBadArgument;
    ZornGen7AppExecution26 *scope=nullptr;auto raw=beginApplicationOperation(client,ZornGen7AppOperation26::Close,scope);if(raw)return raw;
    if(scope!=&execution)return finishApplicationOperation(*scope,kIOReturnNotReady);
    zorn26_client_event240(20); // original Close authorization/scope returned successfully
    raw=closeProcessClient(client,*process); // real process fence/BO/client/submit cleanup
    if(!raw)raw=transitionProcessTables(client,ZornGen7ProcessTableOperation26::RestoreKernel,process,0,0);
    if(!raw)raw=transitionProcessTables(client,ZornGen7ProcessTableOperation26::DetachVm,process,0,0);
    if(!raw)raw=transitionProcessTables(client,ZornGen7ProcessTableOperation26::RetireDetached,process,0,0);
    return finishApplicationOperation(*scope,raw);
    // Only complete normal process cleanup permits later actual app OOB
    // clear and independent authority release. No failure rollback/retry.
}

IOReturn ZornGen7HostRing26::applicationIoLeases(IOUserClient &connection,ZornGen7AppExecution26 &execution,
    ZornGen7ProcessTables26 &p,const NativeAdrenoAbiBoCpuUnmap &request,uint32_t &out)
{
    ZornGen7AppExecution26 *scope=nullptr;auto raw=beginApplicationOperation(connection,ZornGen7AppOperation26::CpuView,scope);
    if(raw)return raw;if(scope!=&execution)return finishApplicationOperation(*scope,kIOReturnNotReady);
    auto &s=*storage_;s.lockIssuer();uint32_t leases=0;
    const bool ready=processConnectionHeld(connection) && s.processSelected==&p && p.ringOwner_==this &&
        p.domain_==&s.domain && p.clientOwner_==&connection && p.clientTask_==execution.task_ &&
        p.clientOpen_ && !p.clientClosed_ && p.clientState_ && !p.state_.poisoned;
    raw=ready?p.clientState_->client.preflightCpuUnmap(&request,&leases):kIOReturnNotReady;
    s.unlockIssuer();raw=finishApplicationOperation(*scope,raw);if(!raw)out=leases;return raw;
}
IOReturn ZornGen7HostRing26::copyApplicationIoView(IOUserClient &connection,ZornGen7AppExecution26 &execution,
    ZornGen7ProcessTables26 &p,uint32_t token,IOMemoryDescriptor *&out)
{
    if(out || !token)return kIOReturnBadArgument;
    ZornGen7AppExecution26 *scope=nullptr;auto raw=beginApplicationOperation(connection,ZornGen7AppOperation26::CpuView,scope);
    if(raw)return raw;if(scope!=&execution)return finishApplicationOperation(*scope,kIOReturnNotReady);
    auto &s=*storage_;IOMemoryDescriptor *descriptor=nullptr;
    s.lockIssuer();
    const bool ready=processConnectionHeld(connection) && s.processSelected==&p && p.ringOwner_==this &&
        p.domain_==&s.domain && p.clientOwner_==&connection && p.clientTask_==execution.task_ &&
        p.clientOpen_ && !p.clientClosed_ && p.clientState_ && !p.state_.poisoned;
    if(!ready)raw=kIOReturnNotReady;
    else {
        auto *memory=p.clientState_->client.memoryForToken(token);NativeAdrenoCpuView view{};
        if(!memory || !memory->cpuView(&view) || !view.count || view.count>65536)raw=kIOReturnNotReady;
        else {
            auto *ranges=IONewData(IOAddressRange,view.count);
            if(!ranges)raw=kIOReturnNoMemory;
            else {
                for(size_t i=0;i<view.count;++i)ranges[i]={view.spans[i].physical,view.spans[i].bytes};
                descriptor=IOMemoryDescriptor::withAddressRanges(ranges,static_cast<UInt32>(view.count),
                    static_cast<IOOptionBits>(kIODirectionInOut)|static_cast<IOOptionBits>(kIOMemoryTypePhysical64),nullptr);
                IODeleteData(ranges,IOAddressRange,view.count);if(!descriptor)raw=kIOReturnNoMemory;
            }
        }
    }
    s.unlockIssuer();raw=finishApplicationOperation(*scope,raw);
    if(raw){if(descriptor)descriptor->release();return raw;}out=descriptor;return kIOReturnSuccess;
}

IOReturn ZornGen7HostRing26::publishApplicationIo(OSObject &authorityOwner,const ZornGen7AppAuthority26 &authority)
{
    if(!storage_ || !normal() || !authority.acquire || !authority.check || !authority.release)return kIOReturnBadArgument;
    auto &s=*storage_;if(IORecursiveLockHaveLock(&s.gate))return kIOReturnNotReady;
    s.lockIssuer();
    if(s.applicationIoPublishAttempted || s.kernelIoPublishAttempted || s.kernelIoConnection || s.appExecution ||
       s.appExecutionPending || s.appOobActive || s.appOobTransition || s.appOperationPending || s.processClients || s.processSelected ||
       !s.runtimeReady || !s.kernelTaskComplete || !s.imageVerified || !s.imageUnmapped ||
       !s.taskReleaseAllowed || !bootstrapHealthy() || s.native.outstanding() || s.runtimeSubmit.outstanding() ||
       s.native.poisoned() || s.runtimeSubmit.poisoned()){
        s.unlockIssuer();return kIOReturnNotReady;}
    s.applicationIoPublishAttempted=true;s.unlockIssuer();
    // Real IOService attachment/start/registration must run outside issuer and
    // startup gates. The actual service retains backend code/storage,which is
    // mandatory and NOT a kernel-client callback cast or supplied raw0.
    const auto raw=ZornGen7AppIoService26::createAndPublish(*this,authorityOwner,authority,s.applicationIoService);
    if(raw || !bootstrapHealthy()){
        __atomic_store_n(&s.stopped,1u,__ATOMIC_RELEASE);s.irq.stopAndMask();return raw?raw:kIOReturnNotReady;}
    return kIOReturnSuccess;
    // Publication alone grants no app GPU execution. The service defers its
    // real acquire/OOB/private-VM work until fully admitted first method.
}

// Metadata reads and CPU copying only. The existing submit/wait path is the
// sole producer of retiredFence;the presenter cannot touch MMIO or borrow an
// application's execution authority on its kernel worker thread.
IOReturn ZornGen7HostRing26::bindPresentationOwner()
{
    if(!storage_ || !normal())return kIOReturnNotReady;
    auto *lock=presentationLock();if(!lock)return kIOReturnNoMemory;
    IOLockLock(lock);
    if(presentationOwner && presentationOwner!=this){IOLockUnlock(lock);return kIOReturnExclusiveAccess;}
    if(!presentationOwner){retain();presentationOwner=this;}
    IOLockUnlock(lock);return kIOReturnSuccess;
}
uint32_t ZornGen7HostRing26::capturePresentationFence()
{
    if(!normal())return 0;auto *lock=presentationLock();if(!lock)return 0;
    IOLockLock(lock);uint32_t fence=0;
    if(presentationOwner){auto &s=*presentationOwner->storage_;s.lockIssuer();
        if(__atomic_load_n(&s.runtimeReady,__ATOMIC_ACQUIRE) && !s.presentProgress.failed && !s.native.poisoned())fence=s.native.lastSubmitted();
        s.unlockIssuer();}
    IOLockUnlock(lock);return fence;
}
int ZornGen7HostRing26::beginPresentation(uint32_t producer)
{
    if(!normal())return -1;auto *lock=presentationLock();if(!lock)return -1;
    IOLockLock(lock);
    if(!presentationOwner){
        if(producer){IOLockUnlock(lock);return -1;}
        presentationThread=current_thread();presentationIssuerHeld=false;return 1;
    }
    auto &owner=*presentationOwner;auto &s=*owner.storage_;s.lockIssuer();
    auto refuse=[&](int status){s.unlockIssuer();IOLockUnlock(lock);return status;};
    // Do not inspect still-being-constructed VM/submit state. One release/acquire
    // publication distinguishes an ordinary in-flight construction from failure.
    const uint32_t runtime=__atomic_load_n(&s.presentationRuntimeState,__ATOMIC_ACQUIRE);
    if(runtime!=2u)return refuse(runtime==3u?-1:0);
    if(!owner.bootstrapHealthy() || s.presentProgress.failed || s.native.poisoned() ||
       s.runtimeVm.poisoned() || s.runtimeSubmit.poisoned())return refuse(-1);
    bool pending=s.runtimeSubmit.outstanding() || s.runtimeVm.hasPendingSubmissionResources() ||
        s.appExecutionPending || s.appOperationPending || s.appOobTransition ||
        s.kernelIoClosing || s.kernelProcessClosing;
    for(auto *p=s.processClients;p;p=p->ringNext_){
        if(p->state_.poisoned || p->vm_.poisoned() ||
           (p->clientState_ && p->clientState_->submit.poisoned()))return refuse(-1);
        pending=pending || p->vm_.hasPendingSubmissionResources() ||
            (p->clientState_ && p->clientState_->submit.outstanding());
    }
    if(pending)return refuse(0);
    const uint32_t tail=s.native.lastSubmitted();
    // Actual NativeRing never wraps or reuses issued sequence numbers. The
    // cached wait result and successful job-retirement ledger have genuine
    // fence producers;empty job counts alone are never accepted as completion.
    uint32_t completed=s.native.completedFence();
    if(s.presentProgress.retiredFence>completed)completed=s.presentProgress.retiredFence;
    if(!tail || producer>tail || completed>tail)return refuse(-1);
    if(completed<tail)return refuse(0);
    presentationThread=current_thread();presentationIssuerHeld=true;return 2;
    // Hold registry+actual issuer across cache acquisition and full CPU copy.
    // There is no new hardware wait,poll,clock,reset or app authority operation.
}
void ZornGen7HostRing26::endPresentation()
{
    // RAII releases on the same kernel presenter thread. A mismatched call
    // must not unlock another thread's resource lease.
    if(presentationThread!=current_thread())return;
    presentationThread=THREAD_NULL;
    if(presentationIssuerHeld){presentationIssuerHeld=false;presentationOwner->storage_->unlockIssuer();}
    IOLockUnlock(__atomic_load_n(&presentationRegistry,__ATOMIC_ACQUIRE));
}
extern "C" uint32_t zorn_gen7_present_capture_fence26(void){return ZornGen7HostRing26::capturePresentationFence();}
extern "C" int zorn_gen7_present_begin_frame26(uint32_t fence){return ZornGen7HostRing26::beginPresentation(fence);}
extern "C" void zorn_gen7_present_end26(void){ZornGen7HostRing26::endPresentation();}

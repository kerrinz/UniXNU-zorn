// SPDX-License-Identifier: BSD-2-Clause-Patent
#include "ZornGen7StartupOwner26.h"
#include "ZornGen7CommandDbReadIntent26.h"
#include "ZornGen7RscControllerOwner26.h"
#include "ZornGen7NativeBoardStage26.h"
#include "ZornGen7ClockResources26.h"
#include "ZornGen7ArcNativeInputMetadata26.inc"
#include "ZornGen7StockResources26.h"
#include <IOKit/IOLib.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
#include <string.h>
#include <pexpert/pexpert.h>
OSDefineMetaClassAndStructors(ZornGen7StartupOwner26,OSObject)
namespace {
uint32_t creatorAttempted=0;
bool normal(){return preemption_enabled() && !ml_at_interrupt_context() && ml_get_interrupts_enabled();}
bool actualCallbacks(const ZornGen7StartupInputs26 &i,bool nativeOwnedClocks,bool capturedSource=false){
    unsigned managed=0;
    const bool nativeRsc=PE_parse_boot_argn("zorn26_rsc_managed",&managed,sizeof(managed)) && managed==1;
    return (nativeOwnedClocks || i.clocks.authorizeRetainedReadWriteWindow) && i.registers.admitMap && i.registers.admitAccess && i.registers.observeAccess &&
        i.iccQos.acquireExclusiveProgrammingWindow && i.smmuPm.admitRuntimeUse && i.smmuPm.admitNormalSuspend &&
        i.banks.acquireActualBank && i.atomic.admitAtomicAccess && i.atomic.observeAtomicAccess &&
        i.smmuFaults.authorizeActualGlobalSpi && i.smmuFaults.acquireActualFaultControl && i.smmuFaults.authorizeActualContextSpi &&
        i.streams.acquireActualStream && i.cxTimer.acquireFreshTimerWindow && i.load.acquireResetHeldFirmwareLoad &&
        i.scm.acquireExclusiveCxEpoch && i.gmuStart.acquireColdStartWindow &&
        i.gmuStart.acquireHfiQueueReset && (capturedSource || i.commandDb.authorizeStableWritebackRead) &&
        (nativeRsc || i.rscCold.authorizeRetainedColdController);
    // The native route performs its real CPU-power hold and fresh hardware
    // preparation; selecting it does not manufacture the legacy cold callback.
}
}
struct ZornGen7StartupOwner26::Storage {
    IOService &platform;IORegistryEntry &root;OSObject &foreignOwner,&authorityOwner,&scmOwner;
    const unsigned foreignCount,smmuPollBudget;const uint32_t version,scmEntryBudget;
    HoujiFullHostNativeMemory::Span foreign[HoujiFullHostNativeMemory::MaxForeign]{};uint8_t arcDigest[32]{};
    const ZornGen7ClockWindowAuthority26 clocks;const ZornGen7OperationGuard26 registers;
    const ZornGen7IccQosAuthority26 iccQos;const ZornGen7SmmuRuntimeAuthority26 smmuPm;
    const ZornGen7SmmuBankAuthority26 banks;const ZornGen7AtomicSmmuGuard26 atomic;
    const ZornGen7SmmuFaultIrqAuthority26 smmuFaults;const ZornGen7SmmuColdAuthority26 smmuCold;
    const ZornGen7SmmuStreamAuthority26 streams;const ZornGen7CxTimerAuthority26 cxTimer;
    const ZornGen7GmuLoadAuthority26 load;const ZornGen7ScmAuthority26 scm;
    const ZornGen7GmuIrqAuthority26 gmuIrqs;const ZornGen7GmuStartAuthority26 gmuStart;
    const ZornGen7CommandDbReadAuthority26 commandDb;const ZornGen7RscIrqAuthority26 rscIrqs;
    const ZornGen7RscColdAuthority26 rscCold;
    ZornGen7NativeBoardStage26 *prepared=nullptr;
    IOWorkLoop *loop=nullptr;Status status;bool nativeOwnedClocks=false,commandDbOnly=false,commandDbObservation=false,commandDbCapturedResources=false,fullCapturedResources=false;
    ZornGen7CommandDbReadIntent26 *commandDbReadIntent=nullptr;
    ZornGen7CommandDbWorkerObservation26 commandDbObservationResult;
    ZornGen7CommandDbCapturedStatus26 capturedResult;
    ZornGen7RscControllerOwner26 *rscControllerOwner=nullptr;
    bool rscControllerCreationReturned=false;IOReturn rscControllerCreationRaw=kIOReturnNotReady;
    OSObject *stockOwner=nullptr;ZornGen7OperationGuard26 stockMap{};ZornGen7StockAtomicAccess26 stockAtomic{};
    unsigned stockLockBudget=0;OSObject *gpuStartOwner=nullptr;ZornGen7GpuStartAuthority26 gpuStart{};
    OSObject *gpuMmuOwner=nullptr;ZornGen7GpuMmuAuthority26 gpuMmu{};bool gpuMmuReturned=false,gpuCodeReturned=false,gpuRegistersReturned=false,gpuIrqReturned=false,cpInitReturned=false;IOReturn gpuMmuRaw=kIOReturnNotReady,gpuCodeRaw=kIOReturnNotReady,gpuRegistersRaw=kIOReturnNotReady,gpuIrqRaw=kIOReturnNotReady,cpInitRaw=kIOReturnNotReady;
    OSObject *gpuRegisterOwner=nullptr;ZornGen7GpuRegisterAuthority26 gpuRegisters{};OSObject *gpuIrqOwner=nullptr;ZornGen7GpuIrqAuthority26 gpuIrqs{};OSObject *cpStartOwner=nullptr;ZornGen7CpStartAuthority26 cpStart{};
    OSObject *applicationOwner=nullptr;ZornGen7AppAuthority26 application{};
    bool applicationIoRequested=false,applicationIoReturned=false;IOReturn applicationIoRaw=kIOReturnNotReady;
    OSObject *zapOwner=nullptr;ZornGen7ZapAuthority26 zap{};bool kernelIoRequested=false,kernelIoReturned=false;IOReturn kernelIoRaw=kIOReturnNotReady;
    bool consoleImageRequested=false,consoleImageReturned=false;IOReturn consoleImageRaw=kIOReturnNotReady;
    bool kernelImageRequested=false,kernelImageReturned=false;IOReturn kernelImageRaw=kIOReturnNotReady;
    OSObject *directRuntimeOwner=nullptr;ZornGen7DirectRuntimeAuthority26 directRuntime{};size_t vmSpanBudget=0;bool nativeRuntimeRequested=false,directRuntimeReturned=false;IOReturn directRuntimeRaw=kIOReturnNotReady;
    OSObject *bootstrapOwner=nullptr;ZornGen7CpBootstrapAuthority26 bootstrap{};bool bootstrapReturned=false;IOReturn bootstrapRaw=kIOReturnNotReady;bool zapReturned=false;IOReturn zapRaw=kIOReturnNotReady;
    bool gpuOobReturned=false,gpuTablesReturned=false;IOReturn gpuOobRaw=kIOReturnNotReady,gpuTablesRaw=kIOReturnNotReady;
    ZornGen7StockResources26 *stockResources=nullptr;ZornGen7StockIdentity26 *identity=nullptr;
    bool registryReturned=false,resourcesReturned=false,identityReturned=false,tablesReturned=false,profileReturned=false,clockReturned=false,bandwidthReturned=false;
    IOReturn resourcesRaw=kIOReturnNotReady,identityRaw=kIOReturnNotReady,tablesRaw=kIOReturnNotReady,profileRaw=kIOReturnNotReady,clockRaw=kIOReturnNotReady,bandwidthRaw=kIOReturnNotReady;
    ZornGen7InactiveOwner26 *parent=nullptr;ZornGen7CommandDbRegion26 *commandDbOwner=nullptr;
    ZornGen7RscProvider26 *rsc=nullptr;ZornGen7RscProbe26 *probe=nullptr;ZornGen7RegisterMaps26 *maps=nullptr;
    ZornGen7RegistryStartupResult26 result;
    explicit Storage(const ZornGen7StartupInputs26 &i):platform(i.platform),root(i.root),foreignOwner(i.foreignOwner),
        authorityOwner(i.authorityOwner),scmOwner(i.scmOwner),foreignCount(i.foreignCount),smmuPollBudget(i.smmuPollBudget),
        version(i.commandDbVersion),scmEntryBudget(i.scmEntryBudget),clocks(i.clocks),registers(i.registers),iccQos(i.iccQos),
        smmuPm(i.smmuPm),banks(i.banks),atomic(i.atomic),smmuFaults(i.smmuFaults),smmuCold(i.smmuCold),streams(i.streams),
        cxTimer(i.cxTimer),load(i.load),scm(i.scm),gmuIrqs(i.gmuIrqs),gmuStart(i.gmuStart),commandDb(i.commandDb),rscIrqs(i.rscIrqs),rscCold(i.rscCold){}
    // Inert storage for the terminal observation branch only. Empty function
    // slots cannot authorize or enter any full-startup operation. No full
    // StartupInputs26 object or successful stand-in callback is constructed.
    Storage(IOService &p,IORegistryEntry &r,OSObject &foreign,OSObject &code):
        platform(p),root(r),foreignOwner(foreign),authorityOwner(code),scmOwner(code),
        foreignCount(0),smmuPollBudget(0),version(0),scmEntryBudget(0),clocks{},registers{},iccQos{},
        smmuPm{},banks{},atomic{},smmuFaults{},smmuCold{},streams{},cxTimer{},load{},scm{},
        gmuIrqs{},gmuStart{},commandDb{},rscIrqs{},rscCold{}{}
    static void *operator new(size_t,void *p)noexcept{return p;}
};
IOReturn ZornGen7StartupOwner26::createAndSchedulePreparedCommandDbObservationOnly(IOService &platform,IORegistryEntry &root,
    OSObject &foreignOwner,OSObject &codeOwner,ZornGen7NativeBoardStage26 &prepared,ZornGen7StartupOwner26 *&out)
{return createPreparedCommandDbWorker(platform,root,foreignOwner,codeOwner,prepared,out,false);}
IOReturn ZornGen7StartupOwner26::createAndSchedulePreparedCommandDbCapturedResources(IOService &platform,IORegistryEntry &root,
    OSObject &foreignOwner,OSObject &codeOwner,ZornGen7NativeBoardStage26 &prepared,ZornGen7StartupOwner26 *&out)
{return createPreparedCommandDbWorker(platform,root,foreignOwner,codeOwner,prepared,out,true);}
IOReturn ZornGen7StartupOwner26::createPreparedCommandDbWorker(IOService &platform,IORegistryEntry &root,
    OSObject &foreignOwner,OSObject &codeOwner,ZornGen7NativeBoardStage26 &prepared,ZornGen7StartupOwner26 *&out,bool captured)
{
    if(out || !normal() || !prepared.matchesPreparedInputs(platform,root,nullptr,0,foreignOwner,codeOwner))
        return kIOReturnBadArgument;
    unsigned selected=0,other=0;
    const char *selector=captured?"zorn26_commanddb_resources":"zorn26_commanddb_source_read";
    const char *excluded=captured?"zorn26_commanddb_source_read":"zorn26_commanddb_resources";
    if(!PE_parse_boot_argn(selector,&selected,sizeof(selected)) || selected!=1 ||
       (PE_parse_boot_argn(excluded,&other,sizeof(other)) && other))
        return kIOReturnNotPermitted;
    uint32_t expected=0;
    if(!__atomic_compare_exchange_n(&creatorAttempted,&expected,1u,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))
        return kIOReturnExclusiveAccess;
    auto *p=new ZornGen7StartupOwner26;if(!p)return kIOReturnNoMemory;
    if(!p->init()){p->release();return kIOReturnNoMemory;}
    p->retain();p->pinned_=true;out=p;
    platform.retain();root.retain();foreignOwner.retain();codeOwner.retain();codeOwner.retain();
    p->gate_=IOLockAlloc();if(!p->gate_)return kIOReturnNoMemory;
    void *memory=IOMallocZero(sizeof(Storage));if(!memory)return kIOReturnNoMemory;
    p->storage_=new(memory)Storage(platform,root,foreignOwner,codeOwner);auto &s=*p->storage_;
    s.nativeOwnedClocks=true;s.commandDbOnly=true;s.commandDbObservation=!captured;s.commandDbCapturedResources=captured;s.status.phase=Phase::InputsCopied;
    prepared.retain();s.prepared=&prepared;
    // Pure CommandDB observation needs no completion workloop. The managed
    // RSC continuation borrows and retains this real loop in its Probe and
    // interrupt runtime, just as the full startup creator does below.
    unsigned managed=0;
    if(captured && PE_parse_boot_argn("zorn26_rsc_managed",&managed,sizeof(managed)) && managed==1){
        s.loop=IOWorkLoop::workLoop();if(!s.loop)return kIOReturnNoResources;
    }
    return submitWorker(*p);
}
IOReturn ZornGen7StartupOwner26::createAndSchedulePreparedCommandDbObservation(const ZornGen7StartupInputs26 &i,
    ZornGen7NativeBoardStage26 &prepared,ZornGen7StartupOwner26 *&out)
{return schedule(i,nullptr,nullptr,out,false,false,nullptr,false,true,nullptr,&prepared,true,true);}
IOReturn ZornGen7StartupOwner26::createAndSchedulePreparedCommandDbPrefix(const ZornGen7StartupInputs26 &i,
    ZornGen7NativeBoardStage26 &prepared,ZornGen7StartupOwner26 *&out)
{return schedule(i,nullptr,nullptr,out,false,false,nullptr,false,true,nullptr,&prepared,true);}
IOReturn ZornGen7StartupOwner26::createAndSchedule(const ZornGen7StartupInputs26 &i,ZornGen7StartupOwner26 *&out)
{return schedule(i,nullptr,nullptr,out);}
IOReturn ZornGen7StartupOwner26::createAndScheduleHost(const ZornGen7StartupHostInputs26 &i,ZornGen7StartupOwner26 *&out)
{return schedule(i.startup,&i,nullptr,out);}
IOReturn ZornGen7StartupOwner26::createAndScheduleNativeClockHost(const ZornGen7StartupHostInputs26 &i,ZornGen7StartupOwner26 *&out)
{return schedule(i.startup,&i,nullptr,out,false,false,nullptr,false,true);}
IOReturn ZornGen7StartupOwner26::createAndScheduleAuthenticatedPrefix(const ZornGen7StartupAuthenticatedPrefixInputs26 &i,ZornGen7StartupOwner26 *&out)
{return schedule(i.host.startup,&i.host,nullptr,out,false,false,&i);}
IOReturn ZornGen7StartupOwner26::createAndScheduleApplicationIo(const ZornGen7StartupApplicationInputs26 &i,ZornGen7StartupOwner26 *&out)
{return schedule(i.gpu.host.startup,&i.gpu.host,&i.gpu,out,true,false,nullptr,false,false,&i);}
IOReturn ZornGen7StartupOwner26::createAndScheduleGpuPrefix(const ZornGen7StartupGpuInputs26 &i,ZornGen7StartupOwner26 *&out)
{return schedule(i.host.startup,&i.host,&i,out);}
IOReturn ZornGen7StartupOwner26::schedule(const ZornGen7StartupInputs26 &i,const ZornGen7StartupHostInputs26 *host,
    const ZornGen7StartupGpuInputs26 *gpu,ZornGen7StartupOwner26 *&out,bool kernelImage,bool kernelIo,
    const ZornGen7StartupAuthenticatedPrefixInputs26 *authenticatedPrefix,bool consoleImage,bool nativeOwnedClocks,
    const ZornGen7StartupApplicationInputs26 *application,ZornGen7NativeBoardStage26 *prepared,bool commandDbOnly,bool commandDbObservation)
{
    // Match the existing platform clock-nub reservation selector exactly.
    // The same real private GCC/GPUCC owner must be available to GPU prefix,
    // image/client and application stages,not just the host-only entry.
    // Missing/invalid selectors preserve the legacy external-clock route;
    // the explicitly native-only entry retains its original factory checks.
    if(!nativeOwnedClocks){
        unsigned owned=0;
        nativeOwnedClocks=PE_parse_boot_argn("zorn26_owned_clocks",&owned,sizeof(owned)) && owned==1;
    }
    unsigned capturedSelected=0,capturedOnly=0,observationSelected=0;
    const bool fullCapturedResources=!commandDbOnly &&
        PE_parse_boot_argn("zorn26_commanddb_resources",&capturedSelected,sizeof(capturedSelected)) && capturedSelected==1;
    if(fullCapturedResources && (!prepared || !nativeOwnedClocks ||
       (PE_parse_boot_argn("zorn26_commanddb_resources_only",&capturedOnly,sizeof(capturedOnly)) && capturedOnly) ||
       (PE_parse_boot_argn("zorn26_commanddb_source_read",&observationSelected,sizeof(observationSelected)) && observationSelected)))
        return kIOReturnBadArgument;
    if(commandDbObservation){
        unsigned selected=0;
        if(!commandDbOnly || !PE_parse_boot_argn("zorn26_commanddb_source_read",&selected,sizeof(selected)) || selected!=1)
            return kIOReturnNotPermitted;
    }
    if(commandDbOnly && (!prepared || !nativeOwnedClocks || host || gpu || authenticatedPrefix ||
       application || kernelImage || kernelIo || consoleImage))return kIOReturnBadArgument;
    if(gpu && authenticatedPrefix)return kIOReturnBadArgument;
    if(application && (!gpu || &application->gpu!=gpu || !kernelImage || kernelIo || consoleImage ||
       !application->application.acquire || !application->application.check || !application->application.release))return kIOReturnBadArgument;
    if(consoleImage && (!gpu || !kernelImage || kernelIo))return kIOReturnBadArgument;
    const auto validPrefix=[](const auto &g){
        // GPU cold-start authority is created by the actual retained K80
        // DarwinBoardOwner at the OOB boundary,after its native stages finish.
        // The same owner binds SMMU start and post-CP restore to the actual
        // controller,USER/LPAC reservations,provider claim and zero backing.
        return g.gpuRegisters.acquireExclusiveGpuRegisterConfiguration &&
            g.cpStart.acquireExclusiveCpInitialization &&
            g.zap.acquireExclusiveZapWindow && g.zap.checkHeldZapWindow &&
            g.bootstrap.acquireAuthenticatedBootstrap && g.bootstrap.authorizeSuccessfulOobRelease;
    };
    if(kernelIo && (!kernelImage || !gpu || !gpu->runtime.acquireKernelClient || !gpu->runtime.checkHeldKernelClient || !gpu->runtime.authorizeKernelClientRelease))return kIOReturnBadArgument;
    if(kernelImage && (!gpu || !gpu->runtime.acquireKernelTask || !gpu->runtime.checkHeldKernelTask || !gpu->runtime.authorizeKernelTaskRelease))return kIOReturnBadArgument;
    if((gpu && (!host || !validPrefix(*gpu))) ||
       (authenticatedPrefix && (!host || !validPrefix(*authenticatedPrefix))))return kIOReturnBadArgument;
    if(host && (!host->stockMap.admitMap || !host->stockAtomic.admit || !host->stockAtomic.observe ||
       !host->explicitStockLockPollBudget || host->explicitStockLockPollBudget>1048576))return kIOReturnBadArgument;
    if(gpu && (!gpu->runtime.acquireNativeRuntime || gpu->explicitVmSpanBudget<12 || gpu->explicitVmSpanBudget>262144))return kIOReturnBadArgument;
    if(out || !normal() || (commandDbOnly ? (!commandDbObservation && !i.commandDb.authorizeStableWritebackRead) :
       (!actualCallbacks(i,nativeOwnedClocks,fullCapturedResources) || !i.smmuPollBudget || i.smmuPollBudget>1048576 || !i.scmEntryBudget)) ||
       i.foreignCount>HoujiFullHostNativeMemory::MaxForeign ||
       (i.foreignCount && (!i.foreign || (reinterpret_cast<uintptr_t>(i.foreign)&(alignof(HoujiFullHostNativeMemory::Span)-1u)) ||
        size_t(i.foreignCount)*sizeof(*i.foreign)-1u>UINTPTR_MAX-reinterpret_cast<uintptr_t>(i.foreign))))return kIOReturnBadArgument;
    if(prepared && (!nativeOwnedClocks || !prepared->matchesPreparedInputs(i.platform,i.root,
       i.foreign,i.foreignCount,i.foreignOwner,i.authorityOwner)))return kIOReturnBadArgument;
    uint32_t expected=0;if(!__atomic_compare_exchange_n(&creatorAttempted,&expected,1u,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))return kIOReturnExclusiveAccess;
    auto *p=new ZornGen7StartupOwner26;if(!p)return kIOReturnNoMemory;
    if(!p->init()){p->release();return kIOReturnNoMemory;}
    p->retain();p->pinned_=true;out=p;
    i.platform.retain();i.root.retain();i.foreignOwner.retain();i.authorityOwner.retain();i.scmOwner.retain();
    p->gate_=IOLockAlloc();if(!p->gate_)return kIOReturnNoMemory;
    void *memory=IOMallocZero(sizeof(Storage));if(!memory)return kIOReturnNoMemory;
    p->storage_=new(memory)Storage(i);auto &s=*p->storage_;s.nativeOwnedClocks=nativeOwnedClocks;s.commandDbOnly=commandDbOnly;s.commandDbObservation=commandDbObservation;s.fullCapturedResources=fullCapturedResources;s.status.phase=Phase::Retained;
    memcpy(s.arcDigest,i.arcDigest,32);
    if(prepared){prepared->retain();s.prepared=prepared;}
    if(host){
        host->actualStockAccessOwner.retain();s.stockOwner=&host->actualStockAccessOwner;
        s.stockMap=host->stockMap;s.stockAtomic=host->stockAtomic;s.stockLockBudget=host->explicitStockLockPollBudget;
        s.status.hostContinuationRequested=true;
    }
    if(s.foreignCount){
        memcpy(s.foreign,i.foreign,size_t(s.foreignCount)*sizeof(*s.foreign));
    }
    const auto retainPrefix=[&](const auto &g){
        // Keep the legacy input owner alive for layout/caller compatibility,
        // but do not use its callback. DarwinBoardOwner supplies the real
        // provider/resource-bound start lease at the actual OOB boundary.
        g.actualGpuStartOwner.retain();s.gpuStartOwner=&g.actualGpuStartOwner;s.gpuStart={};
        g.actualGpuMmuOwner.retain();s.gpuMmuOwner=&g.actualGpuMmuOwner;s.gpuMmu=g.gpuMmu;
        g.actualGpuRegisterOwner.retain();s.gpuRegisterOwner=&g.actualGpuRegisterOwner;s.gpuRegisters=g.gpuRegisters;
        g.actualGpuIrqOwner.retain();s.gpuIrqOwner=&g.actualGpuIrqOwner;s.gpuIrqs=g.gpuIrqs;
        g.actualCpStartOwner.retain();s.cpStartOwner=&g.actualCpStartOwner;s.cpStart=g.cpStart;
        g.actualZapOwner.retain();s.zapOwner=&g.actualZapOwner;s.zap=g.zap;
        g.actualBootstrapOwner.retain();s.bootstrapOwner=&g.actualBootstrapOwner;s.bootstrap=g.bootstrap;
        s.status.gpuPrefixRequested=true;
    };
    if(authenticatedPrefix){
        retainPrefix(*authenticatedPrefix);s.status.authenticatedPrefixOnlyRequested=true;
    }
    if(gpu){
        retainPrefix(*gpu);
        gpu->actualDirectRuntimeOwner.retain();s.directRuntimeOwner=&gpu->actualDirectRuntimeOwner;s.directRuntime=gpu->runtime;s.vmSpanBudget=gpu->explicitVmSpanBudget;
        s.nativeRuntimeRequested=true;s.kernelImageRequested=kernelImage;s.kernelIoRequested=kernelIo;
        s.consoleImageRequested=consoleImage;s.status.consoleImageRequested=consoleImage;
    }
    if(application){application->actualApplicationAuthorityOwner.retain();
        s.applicationOwner=&application->actualApplicationAuthorityOwner;s.application=application->application;
        s.applicationIoRequested=true;}
    s.loop=IOWorkLoop::workLoop();if(!s.loop)return kIOReturnNoResources;
    s.status.phase=Phase::InputsCopied;
    return submitWorker(*p);
}
IOReturn ZornGen7StartupOwner26::submitWorker(ZornGen7StartupOwner26 &owner)
{
    auto *p=&owner;auto &s=*p->storage_;
    IOLockLock(p->gate_);s.status.phase=Phase::ThreadSubmitted;IOLockUnlock(p->gate_);
    thread_t thread=THREAD_NULL;
    const kern_return_t raw=kernel_thread_start(worker,p,&thread);
    IOLockLock(p->gate_);s.status.threadCreationRaw=raw;s.status.threadCreationReturned=true;
    s.status.threadHandleReturned=thread!=THREAD_NULL;
    if(raw!=KERN_SUCCESS)s.status.phase=Phase::ThreadCreationFailed;
    IOLockUnlock(p->gate_);
    if(raw!=KERN_SUCCESS)return kIOReturnNoResources;
    if(thread==THREAD_NULL)return kIOReturnNotReady;
    // Release only our documented scheduler thread reference. The genuine
    // running thread,completion loop,graph and authority owners remain held.
    thread_deallocate(thread);return kIOReturnSuccess;
}
void ZornGen7StartupOwner26::worker(void *context,wait_result_t)
{
    auto &owner=*static_cast<ZornGen7StartupOwner26 *>(context);auto &s=*owner.storage_;
    IOLockLock(owner.gate_);s.status.phase=Phase::Running;IOLockUnlock(owner.gate_);
    owner.runOnce();
    // Publish only actual returned CPU results. No readStatus caller sees
    // in-progress writes to private source results or native resource state.
    IOLockLock(owner.gate_);s.status.startupReturned=s.registryReturned;
    s.status.firstQueryReturned=s.result.hostGmuStartReturned;
    if(s.result.hostGmuStartReturned)s.status.firstQueryRaw=s.result.hostGmuStartReturn;
    s.status.stockResourcesReturned=s.resourcesReturned;s.status.stockResourcesRaw=s.resourcesRaw;
    s.status.stockReadReturned=s.identityReturned;s.status.stockReadRaw=s.identityRaw;
    s.status.hostTablesReturned=s.tablesReturned;s.status.hostTablesRaw=s.tablesRaw;
    s.status.hostProfileReturned=s.profileReturned;s.status.hostProfileRaw=s.profileRaw;
    s.status.hostClockReturned=s.clockReturned;s.status.hostClockRaw=s.clockRaw;
    s.status.hostBandwidthReturned=s.bandwidthReturned;s.status.hostBandwidthRaw=s.bandwidthRaw;
    s.status.gpuOobReturned=s.gpuOobReturned;s.status.gpuOobRaw=s.gpuOobRaw;
    s.status.gpuTablesReturned=s.gpuTablesReturned;s.status.gpuTablesRaw=s.gpuTablesRaw;
    s.status.gpuMmuReturned=s.gpuMmuReturned;s.status.gpuMmuRaw=s.gpuMmuRaw;
    s.status.gpuCodeReturned=s.gpuCodeReturned;s.status.gpuCodeRaw=s.gpuCodeRaw;
    s.status.gpuRegistersReturned=s.gpuRegistersReturned;s.status.gpuRegistersRaw=s.gpuRegistersRaw;
    s.status.gpuIrqReturned=s.gpuIrqReturned;s.status.gpuIrqRaw=s.gpuIrqRaw;
    s.status.cpInitReturned=s.cpInitReturned;s.status.cpInitRaw=s.cpInitRaw;
    s.status.zapReturned=s.zapReturned;s.status.zapRaw=s.zapRaw;
    s.status.bootstrapReturned=s.bootstrapReturned;s.status.bootstrapRaw=s.bootstrapRaw;
    s.status.directRuntimeReturned=s.directRuntimeReturned;s.status.directRuntimeRaw=s.directRuntimeRaw;
    s.status.kernelImageReturned=s.kernelImageReturned;s.status.kernelImageRaw=s.kernelImageRaw;
    s.status.kernelIoReturned=s.kernelIoReturned;s.status.kernelIoRaw=s.kernelIoRaw;
    s.status.consoleImageReturned=s.consoleImageReturned;s.status.consoleImageRaw=s.consoleImageRaw;
    s.status.phase=Phase::Returned;IOLockUnlock(owner.gate_);
    // Terminating the CPU worker does not retire any live GPU/DMA object.
    // XNU thread_terminate(current_thread()) terminates itself before return.
    (void)thread_terminate(current_thread());panic("Zorn GPU startup worker termination returned");
}
void ZornGen7StartupOwner26::runOnce()
{
    auto &s=*storage_;
    if(s.commandDbCapturedResources){
        unsigned guardedMaps = 0;
        const bool guardRequested = PE_parse_boot_argn("zorn26_gpu_guarded_maps",
            &guardedMaps, sizeof(guardedMaps));
        if (guardRequested && (guardedMaps != 1 || !s.prepared->gpuProviderClaimsHeld())) {
            s.result.registerMappingsReturn = guardedMaps != 1 ?
                kIOReturnBadArgument : kIOReturnNotOpen;
            s.result.registerMappingsReturned = true;
            return;
        }
        auto &out=s.capturedResult;
        out.source.intentRaw=ZornGen7CommandDbReadIntent26::createForCapturedResources(s.platform,*this,s.commandDbReadIntent);
        out.source.intentReturned=true;
        if (out.source.intentRaw != kIOReturnSuccess || !s.commandDbReadIntent) {
            if (guardRequested) {
                s.result.registerMappingsReturn = out.source.intentRaw != kIOReturnSuccess ?
                    out.source.intentRaw : kIOReturnNotReady;
                s.result.registerMappingsReturned = true;
            }
            return;
        }
        ZornGen7PrepareRegistryPreparedCapturedResourcesInto26(*s.prepared,*this,s.platform,s.root,s.foreign,s.foreignCount,
            s.foreignOwner,s.authorityOwner,*s.commandDbReadIntent,s.parent,s.commandDbOwner,out,s.result);
        out.source.registryReturned=true;s.registryReturned=true;
        unsigned rscRead=0,managed=0;
        const bool nativeRsc=PE_parse_boot_argn("zorn26_rsc_managed",&managed,sizeof(managed)) && managed==1;
        const bool layoutRead=PE_parse_boot_argn("zorn26_rsc_layout_read",&rscRead,sizeof(rscRead)) && rscRead==1;
        if(out.bindingReturned && out.bindingRaw==kIOReturnSuccess && s.parent && (layoutRead || nativeRsc)){
            s.rscControllerCreationRaw=ZornGen7RscControllerOwner26::createAndRead(*s.parent,s.platform,s.root,*this,s.rscControllerOwner);
            s.rscControllerCreationReturned=true;
            unsigned reserve=0;
            if(s.rscControllerCreationRaw==kIOReturnSuccess && s.rscControllerOwner){
                if(nativeRsc){
                    s.result.rscReturn=s.rscControllerOwner->prepareManagedRuntime(*s.parent,*s.loop,s.rsc,s.probe);
                    s.result.rscReturned=true;
                    unsigned clocks=0;
                    if(s.result.rscReturn==kIOReturnSuccess && s.rsc &&
                       PE_parse_boot_argn("zorn26_clock_prefix",&clocks,sizeof(clocks)) && clocks==1){
                        const bool clockReady=ZornGen7PrepareNativeClockPrefixInto26(*s.parent,s.root,*s.rsc,s.authorityOwner,
                            ZornGen7ArcNativeInput26::source_digest,s.result);
                        unsigned domains=0;
                        if(clockReady && PE_parse_boot_argn("zorn26_domain_prefix",&domains,sizeof(domains)) && domains==1){
                            const bool domainReady=ZornGen7PrepareNativeDomainPrefixInto26(*s.parent,s.root,s.authorityOwner,s.result);
                            unsigned maps=0;
                            if(domainReady && PE_parse_boot_argn("zorn26_register_maps",&maps,sizeof(maps)) && maps==1){
                                if (guardRequested) {
                                    ZornGen7OperationGuard26 guard{};
                                    // This parent came from takePreparedPrefixOnce. Its claimant
                                    // must still be the one held by the original board stage.
                                    IOReturn raw = s.parent->prepareRegisterOperationGuard(guard);
                                    if (raw == kIOReturnSuccess)
                                        raw = s.parent->prepareRegisterMappings(s.root, s.authorityOwner,
                                            guard, s.maps);
                                    s.result.registerMappingsReturn = raw;
                                    s.result.registerMappingsReturned = true;
                                    unsigned guardedProbe = 0;
                                    if (raw != kIOReturnSuccess ||
                                        !PE_parse_boot_argn("zorn26_gpu_guarded_smmu_id",
                                            &guardedProbe, sizeof(guardedProbe)) || guardedProbe != 1)
                                        return;
                                    s.result.probePrimary = s.parent->prepareNativeCxPrimary();
                                    s.result.probePrimaryReturned = true;
                                    if (s.result.probePrimary.wait.assessment != ZornGen7CxGdsc::WaitAssessment::Completed ||
                                        s.result.probePrimary.regulator.disposition != ZornGen7ColdBoot::Disposition::Complete)
                                        return;
                                    s.result.nativeSmmuPower = s.parent->resumeNativeSmmuPower(s.result.nativeSmmuPowerProgress);
                                    s.result.nativeSmmuPowerReturned = true;
                                    if (s.result.nativeSmmuPower.disposition != ZornGen7ColdBoot::Disposition::Complete)
                                        return;
                                    s.result.smmuPmReturn = s.parent->prepareNativeHeldSmmuRuntimePm(*s.loop, s.authorityOwner);
                                    s.result.smmuPmReturned = true;
                                    if (s.result.smmuPmReturn != kIOReturnSuccess) return;
                                    s.result.domainProbeReturn = s.parent->probeNativeSmmuCapabilities(
                                        *s.maps, s.authorityOwner, s.result.nativeSmmuProbe);
                                    s.result.domainProbeReturned = true;
                                    unsigned reserveEndpoints = 0;
                                    if (s.result.domainProbeReturn == kIOReturnSuccess &&
                                        PE_parse_boot_argn("zorn26_gpu_guarded_smmu_reserve",
                                            &reserveEndpoints, sizeof(reserveEndpoints)) &&
                                        reserveEndpoints == 1) {
                                        s.result.endpointReservation = s.parent->reserveSmmuEndpoints(
                                            s.root, s.authorityOwner);
                                        s.result.endpointReservationReturned = true;
                                        unsigned contextRead = 0;
                                        if (s.result.endpointReservation.disposition == ZornGen7ColdBoot::Disposition::Complete &&
                                            PE_parse_boot_argn("zorn26_gpu_smmu_context_read", &contextRead, sizeof(contextRead)) &&
                                            contextRead == 1) {
                                            const ZornGen7AtomicSmmuGuard26 probe{};
                                            s.result.contextViewsReturn = s.parent->bindSmmuContextViews(
                                                *s.maps, s.authorityOwner, probe);
                                            s.result.contextViewsReturned = true;
                                            unsigned clockProbe = 0;
                                            if (s.result.contextViewsReturn == kIOReturnSuccess &&
                                                PE_parse_boot_argn("zorn26_gpu_guarded_gmu_clocks", &clockProbe, sizeof(clockProbe)) &&
                                                clockProbe == 1) {
                                                s.result.gmuColdClocksReturn = s.parent->enableNativeHostGmuColdClocks(
                                                    s.authorityOwner, s.result.nativeGmuClockResult);
                                                s.result.gmuColdClocksReturned = true;
                                                unsigned timer = 0;
                                                if (s.result.gmuColdClocksReturn == kIOReturnSuccess &&
                                                    PE_parse_boot_argn("zorn26_gpu_guarded_cx_timer", &timer, sizeof(timer)) &&
                                                    timer == 1) {
                                                    s.result.gmuAhbReturn = s.parent->prepareGmuAhbSource();
                                                    s.result.gmuAhbReturned = true;
                                                    if (s.result.gmuAhbReturn == kIOReturnSuccess) {
                                                        s.result.cxTimerReturn = s.parent->initializeNativeCxTimer(
                                                            s.authorityOwner, s.result.nativeCxTimerResult);
                                                        s.result.cxTimerReturned = true;
                                                        unsigned tables = 0;
                                                        if (s.result.cxTimerReturn == kIOReturnSuccess &&
                                                            PE_parse_boot_argn("zorn26_gpu_gmu_context_image", &tables, sizeof(tables)) &&
                                                            tables == 1) {
                                                            auto &result = s.result;
                                                            result.rootPagesReturn = s.parent->prepareSmmuRootPages();
                                                            result.rootPagesReturned = true;
                                                            if (result.rootPagesReturn == kIOReturnSuccess) {
                                                                result.sparseArenasReturn = s.parent->prepareSmmuSparseArenas();
                                                                result.sparseArenasReturned = true;
                                                            }
                                                            if (result.sparseArenasReturned && result.sparseArenasReturn == kIOReturnSuccess) {
                                                                result.gmuImageReturn = s.parent->prepareGmuContextImage();
                                                                result.gmuImageReturned = true;
                                                                unsigned seed = 0;
                                                                if (result.gmuImageReturn == kIOReturnSuccess &&
                                                                    PE_parse_boot_argn("zorn26_gpu_gmu_direct_seed", &seed, sizeof(seed)) &&
                                                                    seed == 1) {
                                                                    result.gmuFirmwareSeedReturn = s.parent->prepareGmuFirmwareSeed();
                                                                    result.gmuFirmwareSeedReturned = true;
                                                                    if (result.gmuFirmwareSeedReturn == kIOReturnSuccess) {
                                                                        result.gmuFirmwareHoldsReturn = s.parent->holdGmuFirmware();
                                                                        result.gmuFirmwareHoldsReturned = true;
                                                                        unsigned irq = 0;
                                                                        if (result.gmuFirmwareHoldsReturn == kIOReturnSuccess &&
                                                                            PE_parse_boot_argn("zorn26_gpu_masked_global_irq", &irq, sizeof(irq)) &&
                                                                            irq == 1) {
                                                                            result.nativeGlobalSmmuIrqReturn =
                                                                                s.parent->prepareNativeGlobalMaskedSmmuIrq(
                                                                                    s.authorityOwner, result.nativeGlobalSmmuIrq);
                                                                            result.nativeGlobalSmmuIrqReturned = true;
                                                                        }
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                    return;
                                }
                                s.result.registerMappingsReturn=s.parent->prepareNativeCpuRegisterMappings(s.root,s.authorityOwner,s.maps);
                                s.result.registerMappingsReturned=true;
                                unsigned cx=0;
                                if(s.result.registerMappingsReturn==kIOReturnSuccess &&
                                   PE_parse_boot_argn("zorn26_cx_primary",&cx,sizeof(cx)) && cx==1){
                                    s.result.probePrimary=s.parent->prepareNativeCxPrimary();
                                    s.result.probePrimaryReturned=true;
                                    unsigned power=0;
                                    if(s.result.probePrimary.wait.assessment==ZornGen7CxGdsc::WaitAssessment::Completed &&
                                       s.result.probePrimary.regulator.disposition==ZornGen7ColdBoot::Disposition::Complete &&
                                       PE_parse_boot_argn("zorn26_smmu_power",&power,sizeof(power)) && power==1){
                                        s.result.nativeSmmuPower=s.parent->resumeNativeSmmuPower(s.result.nativeSmmuPowerProgress);s.result.nativeSmmuPowerReturned=true;
                                        if(s.result.nativeSmmuPower.disposition==ZornGen7ColdBoot::Disposition::Complete){
                                            s.result.smmuPmReturn=s.parent->prepareNativeHeldSmmuRuntimePm(*s.loop,s.authorityOwner);s.result.smmuPmReturned=true;
                                            unsigned probe=0;
                                            if(s.result.smmuPmReturn==kIOReturnSuccess && PE_parse_boot_argn("zorn26_smmu_probe",&probe,sizeof(probe)) && probe==1){
                                                s.result.domainProbeReturn=s.parent->probeNativeSmmuCapabilities(*s.maps,s.authorityOwner,s.result.nativeSmmuProbe);
                                                s.result.domainProbeReturned=true;
                                                unsigned clocks=0;
                                                if(s.result.domainProbeReturn==kIOReturnSuccess &&
                                                   PE_parse_boot_argn("zorn26_gmu_clocks",&clocks,sizeof(clocks)) && clocks==1){
                                                    s.result.gmuColdClocksReturn=s.parent->enableNativeHostGmuColdClocks(s.authorityOwner,s.result.nativeGmuClockResult);
                                                    s.result.gmuColdClocksReturned=true;
                                                    if(s.result.gmuColdClocksReturn==kIOReturnSuccess){
                                                        s.result.gmuAhbReturn=s.parent->prepareGmuAhbSource();s.result.gmuAhbReturned=true;
                                                        unsigned timer=0;
                                                        if(s.result.gmuAhbReturn==kIOReturnSuccess && PE_parse_boot_argn("zorn26_cx_timer",&timer,sizeof(timer)) && timer==1){
                                                            s.result.cxTimerReturn=s.parent->initializeNativeCxTimer(s.authorityOwner,s.result.nativeCxTimerResult);
                                                            s.result.cxTimerReturned=true;
                                                            unsigned irq=0;
                                                            if(s.result.cxTimerReturn==kIOReturnSuccess && PE_parse_boot_argn("zorn26_smmu_irq_masked",&irq,sizeof(irq)) && irq==1){
                                                                s.result.nativeGlobalSmmuIrqReturn=s.parent->prepareNativeGlobalMaskedSmmuIrq(s.authorityOwner,s.result.nativeGlobalSmmuIrq);
                                                                s.result.nativeGlobalSmmuIrqReturned=true;
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                else if(PE_parse_boot_argn("zorn26_rsc_irq_reserve",&reserve,sizeof(reserve)) && reserve==1)
                    (void)s.rscControllerOwner->reserveMaskedNativeInterrupt();
            }
            // Reservation result lives in the controller's separate typed
            // status. Read completion must not become IRQ/TCS readiness.
        }
        return;
    }
    if(s.commandDbObservation){
        auto &out=s.commandDbObservationResult;
        // Construction and the actual read run on this same real worker.
        // The intent grants no stable-firmware/clock/GPU authority.
        out.intentConstructionRaw=ZornGen7CommandDbReadIntent26::createForExplicitTrial(
            s.platform,*this,s.commandDbReadIntent);out.intentConstructionReturned=true;
        if(out.intentConstructionRaw!=kIOReturnSuccess || !s.commandDbReadIntent)return;
        ZornGen7PrepareRegistryPreparedCommandDbObservationInto26(*s.prepared,*this,s.platform,s.root,
            s.foreign,s.foreignCount,s.foreignOwner,s.authorityOwner,*s.commandDbReadIntent,
            s.parent,s.commandDbOwner,out.observation,s.result);
        out.registryReturned=true;out.registry=s.result;
        if(s.commandDbOwner)out.region=s.commandDbOwner->readResult();
        s.registryReturned=true;return;
    }
    if(s.commandDbOnly){
        ZornGen7PrepareRegistryPreparedCommandDbInto26(*s.prepared,*this,s.platform,s.root,
            s.foreign,s.foreignCount,s.foreignOwner,s.authorityOwner,s.commandDb,s.parent,s.commandDbOwner,s.result);
        s.registryReturned=true;return;
    }
    if(s.stockOwner){
        s.resourcesRaw=ZornGen7StockResources26::create(s.platform,s.root,*s.stockOwner,s.stockResources);s.resourcesReturned=true;
        if(s.resourcesRaw!=kIOReturnSuccess || !s.stockResources)return;
        s.identityRaw=s.stockResources->readIdentity(s.stockMap,s.stockAtomic,s.stockLockBudget,s.identity);s.identityReturned=true;
        if(s.identityRaw!=kIOReturnSuccess || !s.identity)return;
    }
    // Original registry/GMU first-query sequence is retained verbatim. This
    // dedicated worker owns no startup gate or completion workloop dispatch.
    if(s.prepared){
    if(s.fullCapturedResources){
        auto &source=s.capturedResult.source;
        source.intentRaw=ZornGen7CommandDbReadIntent26::createForCapturedResources(s.platform,*this,s.commandDbReadIntent);
        source.intentReturned=true;
        if(source.intentRaw!=kIOReturnSuccess || !s.commandDbReadIntent)return;
    ZornGen7PrepareRegistryStartupPreparedCapturedInto26(*s.prepared,*this,s.platform,s.root,s.foreign,s.foreignCount,s.foreignOwner,s.authorityOwner,
        s.clocks,s.registers,s.iccQos,s.smmuPm,s.banks,s.atomic,s.smmuFaults,s.smmuCold,s.streams,s.smmuPollBudget,
        s.cxTimer,s.load,s.scmOwner,s.scm,s.scmEntryBudget,s.gmuIrqs,s.gmuStart,*s.commandDbReadIntent,s.capturedResult,s.arcDigest,*s.loop,
        s.rscIrqs,s.rscCold,s.parent,s.commandDbOwner,s.rsc,s.probe,s.maps,s.result);
        source.registryReturned=true;
    }else{
    ZornGen7PrepareRegistryStartupPreparedResourcesInto26(*s.prepared,*this,s.platform,s.root,s.foreign,s.foreignCount,s.foreignOwner,s.authorityOwner,
        s.clocks,s.registers,s.iccQos,s.smmuPm,s.banks,s.atomic,s.smmuFaults,s.smmuCold,s.streams,s.smmuPollBudget,
        s.cxTimer,s.load,s.scmOwner,s.scm,s.scmEntryBudget,s.gmuIrqs,s.gmuStart,s.commandDb,s.arcDigest,*s.loop,
        s.rscIrqs,s.rscCold,s.parent,s.commandDbOwner,s.rsc,s.probe,s.maps,s.result);
    }
    }else{
    const auto prepare=s.nativeOwnedClocks?ZornGen7PrepareRegistryStartupNativeClocksInto26:ZornGen7PrepareRegistryStartupInto26;
    prepare(s.platform,s.root,s.foreign,s.foreignCount,s.foreignOwner,s.authorityOwner,
        s.clocks,s.registers,s.iccQos,s.smmuPm,s.banks,s.atomic,s.smmuFaults,s.smmuCold,s.streams,s.smmuPollBudget,
        s.cxTimer,s.load,s.scmOwner,s.scm,s.scmEntryBudget,s.gmuIrqs,s.gmuStart,s.commandDb,s.version,s.arcDigest,*s.loop,
        s.rscIrqs,s.rscCold,s.parent,s.commandDbOwner,s.rsc,s.probe,s.maps,s.result);
    }
    s.registryReturned=true;
    if(!s.stockOwner)return; // Preserved first-query-only candidate.
    if(!s.parent || !s.result.hostGmuStartReturned || s.result.hostGmuStartReturn!=kIOReturnSuccess)return;
    s.tablesRaw=s.identity->prepareHostTables(*s.parent);s.tablesReturned=true;
    if(s.tablesRaw!=kIOReturnSuccess)return;
    s.profileRaw=s.parent->runHostProfile();s.profileReturned=true;
    if(s.profileRaw!=kIOReturnSuccess)return;
    s.clockRaw=s.parent->requestHostDefaultClock();s.clockReturned=true;
    if(s.clockRaw!=kIOReturnSuccess)return;
    s.bandwidthRaw=s.parent->requestHostDefaultBandwidth();s.bandwidthReturned=true;
    if(s.bandwidthRaw!=kIOReturnSuccess || !s.gpuStartOwner)return;
    s.gpuTablesRaw=s.parent->prepareHostGpuTables();s.gpuTablesReturned=true;
    if(s.gpuTablesRaw!=kIOReturnSuccess)return;
    if(!s.gpuMmuOwner)return;
    s.gpuMmuRaw=s.parent->startHostGpuMmu(*s.gpuMmuOwner,s.authorityOwner,s.gpuMmu,s.smmuFaults,s.streams,s.smmuPollBudget);s.gpuMmuReturned=true;
    if(s.gpuMmuRaw!=kIOReturnSuccess)return;
    // GPU-MMU must complete real programming/readbacks before OOB. Neither
    // compiled source nor the returned CPU status proves hardware execution.
    s.gpuOobRaw=s.parent->acquireHostGpuOob(*s.gpuStartOwner,s.gpuStart);s.gpuOobReturned=true;
    if(s.gpuOobRaw!=kIOReturnSuccess)return;
    s.gpuCodeRaw=s.parent->bindHostGpuCode();s.gpuCodeReturned=true;
    if(s.gpuCodeRaw!=kIOReturnSuccess || !s.gpuRegisterOwner)return;
    s.gpuRegistersRaw=s.parent->configureHostGpuRegisters(*s.gpuRegisterOwner,s.gpuRegisters);s.gpuRegistersReturned=true;
    if(s.gpuRegistersRaw!=kIOReturnSuccess || !s.gpuIrqOwner)return;
    s.gpuIrqRaw=s.parent->prepareHostGpuIrq(*s.loop,*s.gpuIrqOwner,s.gpuIrqs);s.gpuIrqReturned=true;
    if(s.gpuIrqRaw!=kIOReturnSuccess || !s.cpStartOwner)return;
    s.cpInitRaw=s.parent->initializeHostCp(*s.cpStartOwner,s.cpStart);s.cpInitReturned=true;
    if(s.cpInitRaw!=kIOReturnSuccess || !s.zapOwner)return;
    s.zapRaw=s.parent->authenticateHostZap(*s.zapOwner,s.zap);s.zapReturned=true;
    if(s.zapRaw!=kIOReturnSuccess || !s.bootstrapOwner)return;
    s.bootstrapRaw=s.parent->completeHostBootstrap(*s.bootstrapOwner,s.bootstrap);s.bootstrapReturned=true;
    if(s.bootstrapRaw!=kIOReturnSuccess)return;
    // The authenticated-prefix entry stops at the original completed bootstrap
    // boundary. It neither constructs a client VM nor substitutes successful
    // runtime/task/client grants. Full runtime/image/IO entries keep their
    // original sequence and require their actual independent runtime owner.
    if(!s.nativeRuntimeRequested || !s.directRuntimeOwner)return;
    s.directRuntimeRaw=s.parent->prepareHostDirectRuntime(*s.directRuntimeOwner,s.directRuntime,s.vmSpanBudget);s.directRuntimeReturned=true;
    if(!s.directRuntimeRaw && s.kernelImageRequested){s.kernelImageRaw=s.parent->runHostKnownImage();s.kernelImageReturned=true;}
    if(s.kernelImageReturned && !s.kernelImageRaw && s.consoleImageRequested){s.consoleImageRaw=s.parent->copyHostKnownImageToConsole();s.consoleImageReturned=true;}
    if(s.kernelImageReturned && !s.kernelImageRaw && s.kernelIoRequested){s.kernelIoRaw=s.parent->publishHostKernelIo();s.kernelIoReturned=true;}
    if(s.kernelImageReturned && !s.kernelImageRaw && s.applicationIoRequested){
        s.applicationIoRaw=s.parent->publishHostApplicationIo(*s.applicationOwner,s.application);s.applicationIoReturned=true;}

    // Actual source-bounded kernel image path;client publication
    // adoption and normal timestamp fence still require their real stages.
    // No reset,release,rollback or retry on failure;the actual source owners
    // retain all resources. Full host profile is not direct CP/GPU execution.
}
ZornGen7StartupOwner26::Status ZornGen7StartupOwner26::readStatus()
{
    if(!storage_ || !gate_ || !normal())return {};
    IOLockLock(gate_);const auto out=storage_->status;IOLockUnlock(gate_);return out;
}
bool ZornGen7StartupOwner26::copyCompletedRscManagedStatus(ZornGen7RscManagedStatus26 &out)
{
    if(!storage_ || !gate_ || !normal())return false;
    IOLockLock(gate_);
    const bool ready=storage_->status.phase==Phase::Returned && storage_->rscControllerOwner &&
        storage_->rscControllerOwner->copyCompletedManagedStatus(out);
    if(ready){
        const auto &r=storage_->result;
        out.arcReturned=r.arcReturned;out.arcRaw=r.arcReturn;
        out.clockNodesReturned=r.clockNodesReturned;out.clockNodesRaw=r.clockNodesReturn;
        out.gccRailsReturned=r.gccRailsReturned;out.gccRailsRaw=r.gccRailsReturn;
        out.gccReturned=r.gccPrefixReturned;out.gccComplete=r.gccPrefix.native_closure_prefix_returned;
        out.gpuccReturned=r.gpuccPrefixReturned;out.gpuccComplete=r.gpuccPrefix.source_prefix_complete;
        out.graphReturned=r.clockGraphReturned;out.graphComplete=r.clockGraph.cpu_graph_complete;
        out.listReturned=r.clockListReturned;
        out.listComplete=r.clockList.assessment==ZornGen7Clock::ClockConsumerListAssessment::ListPublished;
    }
    IOLockUnlock(gate_);return ready;
}
bool ZornGen7StartupOwner26::copyCompletedRscControllerRead(ZornGen7RscControllerStatus26 &out,IOReturn &creationRaw)
{
    if(!storage_ || !gate_ || !normal())return false;
    IOLockLock(gate_);
    if(storage_->status.phase!=Phase::Returned || !storage_->rscControllerCreationReturned){IOLockUnlock(gate_);return false;}
    ZornGen7RscControllerStatus26 actual;
    if(storage_->rscControllerOwner)storage_->rscControllerOwner->copyCompletedStatus(actual);
    out=actual;creationRaw=storage_->rscControllerCreationRaw;IOLockUnlock(gate_);return true;
}
bool ZornGen7StartupOwner26::copyCompletedCommandDbCapturedResources(ZornGen7CommandDbCapturedStatus26 &out)
{
    if(!storage_ || !gate_ || !normal())return false;
    IOLockLock(gate_);
    if((!storage_->commandDbCapturedResources && !storage_->fullCapturedResources) || storage_->status.phase!=Phase::Returned){IOLockUnlock(gate_);return false;}
    out=storage_->capturedResult;IOLockUnlock(gate_);return true;
}
bool ZornGen7StartupOwner26::copyCompletedCommandDbStatus(ZornGen7CommandDbStatus26 &out)
{
    if(!storage_ || !gate_ || !normal())return false;
    IOLockLock(gate_);
    if(!storage_->commandDbObservation || storage_->status.phase!=Phase::Returned){IOLockUnlock(gate_);return false;}
    const auto &s=storage_->commandDbObservationResult;ZornGen7CommandDbStatus26 actual;
    actual.intentReturned=s.intentConstructionReturned;actual.intentRaw=s.intentConstructionRaw;
    actual.registryReturned=s.registryReturned;actual.constructionReturned=s.registry.commandDbConstructionReturned;
    actual.constructionRaw=s.registry.commandDbConstruction;actual.captureReturned=s.registry.commandDbPreparationReturned;
    actual.captureRaw=s.registry.commandDbPreparation;actual.readIntentReturned=s.region.readIntentReturned;
    actual.readIntentRaw=s.region.readIntentReturn;actual.mappingReturned=s.region.mappingReturned;
    actual.mappingAccepted=s.region.mappingAccepted;actual.copyReturned=s.region.copyReturned;
    actual.decoderReturned=s.observation.decoderReturned;actual.headerObserved=s.observation.headerObserved;
    actual.decoderRaw=static_cast<uint32_t>(s.observation.status);actual.observedVersion=s.observation.observedVersion;
    actual.copiedBytes=s.observation.copiedBytes;actual.entryCount=s.observation.entryCount;
    out=actual;IOLockUnlock(gate_);return true;
}
bool ZornGen7StartupOwner26::copyCompletedCommandDbObservation(ZornGen7CommandDbWorkerObservation26 &out)
{
    if(!storage_ || !gate_ || !normal())return false;
    IOLockLock(gate_);
    if(!storage_->commandDbObservation || storage_->status.phase!=Phase::Returned){IOLockUnlock(gate_);return false;}
    out=storage_->commandDbObservationResult;IOLockUnlock(gate_);return true;
}
bool ZornGen7StartupOwner26::copyCompletedResult(ZornGen7RegistryStartupResult26 &out)
{
    if(!storage_ || !gate_ || !normal())return false;
    IOLockLock(gate_);
    const auto &s = *storage_;
    // A guarded preflight can return an actual refusal before touching the registry.
    const bool terminalMappingResult = s.commandDbCapturedResources &&
        s.status.phase == Phase::Returned && s.result.registerMappingsReturned;
    if (!s.status.startupReturned && !terminalMappingResult) {
        IOLockUnlock(gate_);
        return false;
    }
    out = s.result;
    IOLockUnlock(gate_);
    return true;
}
void ZornGen7StartupOwner26::free(){if(pinned_)return;OSObject::free();}

IOReturn ZornGen7StartupOwner26::createAndScheduleConsoleImage(const ZornGen7StartupGpuInputs26 &i,ZornGen7StartupOwner26 *&out)
{return schedule(i.host.startup,&i.host,&i,out,true,false,nullptr,true);}

IOReturn ZornGen7StartupOwner26::createAndScheduleKernelImage(const ZornGen7StartupGpuInputs26 &i,ZornGen7StartupOwner26 *&out)
{return schedule(i.host.startup,&i.host,&i,out,true);}

IOReturn ZornGen7StartupOwner26::createAndScheduleKernelIo(const ZornGen7StartupGpuInputs26 &i,ZornGen7StartupOwner26 *&out)
{return schedule(i.host.startup,&i.host,&i,out,true,true);}

IOReturn ZornGen7StartupOwner26::createAndSchedulePreparedNativeClockHost(const ZornGen7StartupHostInputs26 &i,ZornGen7NativeBoardStage26 &p,ZornGen7StartupOwner26 *&out)
{return schedule(i.startup,&i,nullptr,out,false,false,nullptr,false,true,nullptr,&p);}
IOReturn ZornGen7StartupOwner26::createAndSchedulePreparedAuthenticatedPrefix(const ZornGen7StartupAuthenticatedPrefixInputs26 &i,ZornGen7NativeBoardStage26 &p,ZornGen7StartupOwner26 *&out)
{return schedule(i.host.startup,&i.host,nullptr,out,false,false,&i,false,true,nullptr,&p);}
IOReturn ZornGen7StartupOwner26::createAndSchedulePreparedApplicationIo(const ZornGen7StartupApplicationInputs26 &i,ZornGen7NativeBoardStage26 &p,ZornGen7StartupOwner26 *&out)
{return schedule(i.gpu.host.startup,&i.gpu.host,&i.gpu,out,true,false,nullptr,false,true,&i,&p);}

IOReturn ZornGen7StartupOwner26::createAndSchedulePreparedGpuPrefix(const ZornGen7StartupGpuInputs26 &i,ZornGen7NativeBoardStage26 &p,ZornGen7StartupOwner26 *&out)
{return schedule(i.host.startup,&i.host,&i,out,false,false,nullptr,false,true,nullptr,&p);}
IOReturn ZornGen7StartupOwner26::createAndSchedulePreparedKernelImage(const ZornGen7StartupGpuInputs26 &i,ZornGen7NativeBoardStage26 &p,ZornGen7StartupOwner26 *&out)
{return schedule(i.host.startup,&i.host,&i,out,true,false,nullptr,false,true,nullptr,&p);}
IOReturn ZornGen7StartupOwner26::createAndSchedulePreparedKernelIo(const ZornGen7StartupGpuInputs26 &i,ZornGen7NativeBoardStage26 &p,ZornGen7StartupOwner26 *&out)
{return schedule(i.host.startup,&i.host,&i,out,true,true,nullptr,false,true,nullptr,&p);}
IOReturn ZornGen7StartupOwner26::createAndSchedulePreparedConsoleImage(const ZornGen7StartupGpuInputs26 &i,ZornGen7NativeBoardStage26 &p,ZornGen7StartupOwner26 *&out)
{return schedule(i.host.startup,&i.host,&i,out,true,false,nullptr,true,true,nullptr,&p);}

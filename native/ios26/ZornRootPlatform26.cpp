// SPDX-License-Identifier: BSD-2-Clause-Patent
#include "ZornRootPlatformStart26.h"
#include "ZornGen7PlatformBoardStart26.h"
struct ZornGen7RegistryStartupResult26;
bool ZornGen7CopyCompletedPlatformStartupResult26(ZornGen7StartupOwner26 &,ZornGen7RegistryStartupResult26 &);
#include <kern/thread.h>
#include "ZornUfsRootHook26.h"
#include "ZornRootWindow26.h"
#include "ZornRootStartup26.h"
#include <IOKit/IODeviceTreeSupport.h>
#include <libkern/c++/OSSharedPtr.h>
#include <libkern/c++/OSData.h>
#include <libkern/c++/OSMetaClass.h>
#include <pexpert/pexpert.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
#include "ZornGen7InactiveOwner26.h"
class ZornRootPlatform26 final : public OSObject {
    OSDeclareDefaultStructors(ZornRootPlatform26);
public:
    static bool stage(IOService &);
    bool stageGpuBoard();
    IOReturn scheduleDirect(OSObject &,const ZornGen7StartupGpuInputs26 &,ZornGen7PlatformDirectStage26);
    IOReturn scheduleAuthenticatedPrefix(OSObject &,const ZornGen7StartupAuthenticatedPrefixInputs26 &);
    IOReturn scheduleCommandDb(OSObject &,const ZornGen7StartupInputs26 &);
    IOReturn scheduleCommandDbObservation(OSObject &,const ZornGen7StartupInputs26 &);
    bool copyCommandDbObservation(ZornGen7CommandDbWorkerObservation26 &);
    bool copyCommandDbSubmission(IOReturn &);
    bool copyCommandDbStatus(ZornGen7CommandDbStatus26 &);
    bool copyCapturedCommandDbSubmission(IOReturn &);
    bool copyCapturedCommandDbStatus(ZornGen7CommandDbCapturedStatus26 &);
    bool copyRscManaged(ZornGen7RscManagedStatus26 &);
    bool copyStartupResult(ZornGen7RegistryStartupResult26 &);
    bool copyRscControllerRead(ZornGen7RscControllerStatus26 &,IOReturn &);
    void scheduleBootCommandDbObservation();
    bool copyGpuBoardStatus(ZornGen7PlatformBoardStatus26 &);
    void free() override {if(!pinned_)OSObject::free();}
private:
    bool pinned_=false;
    IOService *platform_=nullptr;
    IORegistryEntry *root_=nullptr;
    ZornRootStartup26 *creator_=nullptr;
    IORecursiveLock *gpuComposition_=nullptr;IOLock *gpuGate_=nullptr;
    ZornGen7NativeBoardStage26 *gpuStage_=nullptr;
    // Self-pinned CPU-only firmware/backing owner; partial failures stay retained.
    ZornGen7InactiveOwner26 *gpuInactiveOwner_=nullptr;
    IORegistryEntry *gpuInputNodes_[4]{};
    // No imported GPU BO interface is exposed by this preparation-only owner.
    uint32_t gpuAttempted_=0,gpuSetupTerminal_=0,gpuContextReady_=0;
    ZornGen7PlatformBoardStatus26 gpuStatus_;
    uint32_t directAttempted_=0;
    bool commandDbCapturedResources_=false;bool commandDbSubmissionReturned_=false;IOReturn commandDbSubmissionRaw_=kIOReturnNotReady;
    OSObject *directInputOwner_=nullptr;
    ZornGen7StartupOwner26 *directStartup_=nullptr;
    IOReturn claimDirectPreparation();
    static void gpuBoardWorker(void *,wait_result_t);
};
OSDefineMetaClassAndStructors(ZornRootPlatform26,OSObject);
namespace {
uint32_t attempted;
ZornRootPlatform26 *retainedRootPlatform;
bool sameClassName(const char (&expected)[40],const OSMetaClass *meta)
{
    const char *actual=meta ? meta->getClassName() : nullptr;
    if(!actual)return false;
    for(size_t i=0;i<sizeof(expected);++i){
        if(expected[i]!=actual[i])return false;
        if(!expected[i])return true;
    }
    return false;
}
bool property(IORegistryEntry &node,const char *key,const uint8_t *expected,size_t bytes)
{
    auto object=node.copyProperty(key);
    auto *data=OSDynamicCast(OSData,object.get());
    if(!data || data->getLength()!=bytes || !data->getBytesNoCopy())return false;
    const auto *actual=static_cast<const uint8_t *>(data->getBytesNoCopy());
    for(size_t i=0;i<bytes;++i)if(actual[i]!=expected[i])return false;
    return true;
}
bool liveProviderMatches(IORegistryEntry &root,const char *path,
    const ZornGen7PlatformBoardStatus26::ProviderObservation &expected,bool claimantOpened)
{
    if(!expected.entryFound || !expected.serviceFound || !expected.parentFound ||
       !expected.entryId || !expected.parentId)return false;
    auto entry=IORegistryEntry::fromPath(path,gIODTPlane,nullptr,nullptr,&root);
    auto *service=OSDynamicCast(IOService,entry.get());
    if(!service || service->getRegistryEntryID()!=expected.entryId)return false;
    auto *parent=service->getProvider();
    const bool expectedOpen=claimantOpened ? true : expected.isOpen;
    return parent && parent->getRegistryEntryID()==expected.parentId &&
        service->isOpen()==expectedOpen && service->isInactive()==expected.isInactive &&
        parent->isOpen()==expected.parentIsOpen && parent->isInactive()==expected.parentIsInactive &&
        sameClassName(expected.className,service->getMetaClass()) &&
        sameClassName(expected.parentClassName,parent->getMetaClass());
}
bool liveGpuGmuParentMatches(IORegistryEntry &root,const ZornGen7PlatformBoardStatus26::Stage &stage)
{
    const auto &gpu=stage.gpuProvider;const auto &gmu=stage.gmuProvider;
    // The optional early owner must have opened both originally-closed base
    // providers. Live identity and ancestry are rechecked after that open;
    // this is still only IOKit client exclusion, not hardware-master stop.
    return stage.gpuGmuShareParentObserved && stage.providerClaimRequested &&
        stage.providerClaimAttempted && stage.providerClaimHeld &&
        stage.providerClaimRaw==kIOReturnSuccess && !gpu.isOpen && !gmu.isOpen &&
        gpu.entryId!=gmu.entryId &&
        gpu.parentId && gpu.parentId==gmu.parentId &&
        liveProviderMatches(root,"arm-io/gpu",gpu,true) &&
        liveProviderMatches(root,"arm-io/gmu",gmu,true);
}
}
bool ZornRootPlatform26::stage(IOService &platform)
{
    using namespace ZornRootWindow26;
    if(!preemption_enabled() || ml_at_interrupt_context() || !ml_get_interrupts_enabled() ||
       IOService::getPlatform()!=&platform || !OSDynamicCast(IODTPlatformExpert,&platform))return false;
    char rd[5]{};
    if(!PE_parse_boot_argn("rd",rd,sizeof(rd)) || rd[0]!='m' || rd[1]!='d' || rd[2]!='0' || rd[3])return false;
    auto root=IORegistryEntry::fromPath("/",gIODTPlane);
    if(!root || !property(*root,"compatible",NativeCompatible,sizeof(NativeCompatible)))return false;
    auto chosen=IORegistryEntry::fromPath("chosen",gIODTPlane,nullptr,nullptr,root.get());
    // These immutable inputs identify the intended exact image/window only.
    // Actual installation/readback provenance is a future runner prerequisite;
    // metadata equality never asserts that the image exists on the phone.
    if(!chosen || !property(*chosen,"zorn26,root-image-sha256",ImageSha256,sizeof(ImageSha256)) ||
       !property(*chosen,"zorn26,root-window",WindowBytes,sizeof(WindowBytes)))return false;
    // BSD creates md slots from these loader properties before its explicit
    // UFS-root hook. Reject a competing RAMDisk before publishing root inputs.
    auto memoryMap=IORegistryEntry::fromPath("memory-map",gIODTPlane,nullptr,nullptr,chosen.get());
    if(memoryMap && (memoryMap->copyProperty("RAMDisk") || memoryMap->copyProperty("RAMDisk1")))return false;
    uint32_t empty=0;
    if(!__atomic_compare_exchange_n(&attempted,&empty,1u,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))return false;
    auto *owner=new ZornRootPlatform26;if(!owner)return false;
    if(!owner->init()){owner->release();return false;}
    owner->retain();owner->pinned_=true;
    platform.retain();owner->platform_=&platform;owner->root_=root.detach();
    __atomic_store_n(&retainedRootPlatform,owner,__ATOMIC_RELEASE);
    // The actual platform creator owns the resource/context lifetime. It
    // stages CPU inputs only;the existing IOFindBSDRoot hook later drives the
    // real single UFS preparation/read-only binder. No second initializer,
    // successful provider stub,Data init,write,reset or cleanup is inserted.
    const IOReturn raw=ZornRootStartup26::create(platform,*owner,owner->creator_);
    if(raw || !owner->creator_)return false;
    const ZornRootStartup26::RootInputs input{MdevIndex,AbsoluteByteStart,Bytes};
    const auto result=owner->creator_->stageFromRegistry(*owner->root_,input,*owner);
    const bool staged=result.phase==ZornRootStartup26::Phase::InputsStaged && result.inputsStaged;
    // Publish only after stageRoot has published the real self-pinned owner.
    // BSD can reach its md branch before this platform creator finishes;the
    // ordinary 100ms filesystem matching wait is not this dependency.
    if(staged) IOService::publishResource(ZORN_UFS_ROOT_INPUTS_STAGED26);
    return staged;
}
bool zorn26_root_platform_start(IOService *platform)
{
    unsigned selected=0,record=0;
    if(!PE_parse_boot_argn("zorn26_root",&selected,sizeof(selected)))return true;
    if(selected!=1 || !platform ||
       (PE_parse_boot_argn("zorn26_platform_record",&record,sizeof(record)) && record))return false;
    return ZornRootPlatform26::stage(*platform);
}

bool ZornRootPlatform26::stageGpuBoard()
{
    unsigned owned=0;
    if(!preemption_enabled() || ml_at_interrupt_context() || !ml_get_interrupts_enabled() ||
       !platform_ || IOService::getPlatform()!=platform_ ||
       !PE_parse_boot_argn("zorn26_owned_clocks",&owned,sizeof(owned)) || owned!=1)return false;
    uint32_t empty=0;
    if(!__atomic_compare_exchange_n(&gpuAttempted_,&empty,1u,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))return false;
    gpuGate_=IOLockAlloc();gpuComposition_=IORecursiveLockAlloc();
    if(!gpuGate_ || !gpuComposition_){
        gpuStatus_.setupRaw=kIOReturnNoMemory;gpuStatus_.setupReturned=true;
        __atomic_store_n(&gpuSetupTerminal_,1u,__ATOMIC_RELEASE);return false;
    }
    __atomic_store_n(&gpuContextReady_,1u,__ATOMIC_RELEASE);
    thread_t thread=THREAD_NULL;
    const auto raw=kernel_thread_start(gpuBoardWorker,this,&thread);
    IOLockLock(gpuGate_);gpuStatus_.threadRaw=raw;gpuStatus_.threadReturned=true;
    gpuStatus_.threadHandleReturned=thread!=THREAD_NULL;
    gpuStatus_.setupRaw=raw!=KERN_SUCCESS?kIOReturnNoResources:thread==THREAD_NULL?kIOReturnNotReady:kIOReturnSuccess;
    gpuStatus_.setupReturned=true;const bool returned=gpuStatus_.setupRaw==kIOReturnSuccess;IOLockUnlock(gpuGate_);
    if(raw==KERN_SUCCESS && thread!=THREAD_NULL)thread_deallocate(thread);return returned;
}
void ZornRootPlatform26::gpuBoardWorker(void *context,wait_result_t)
{
    auto &owner=*static_cast<ZornRootPlatform26 *>(context);
    IORecursiveLockLock(owner.gpuComposition_);
    ZornGen7PlatformBoardStatus26 actual;
    ZornGen7PreparePlatformBoardStage26(*owner.platform_,*owner.root_,owner,*owner.gpuComposition_,
        owner.gpuStage_,owner.gpuInputNodes_,actual);
    IORecursiveLockUnlock(owner.gpuComposition_);
    // This opt-in prefix prepares CPU-owned firmware/backing only. It does
    // not create register maps, SMMU/IRQ leases, GPU permissions or a runtime.
    unsigned cpuMemoryPrep=0;
    actual.cpuMemory.optionPresent=PE_parse_boot_argn("zorn26_gpu_cpu_memory_prep",
        &cpuMemoryPrep,sizeof(cpuMemoryPrep));
    if(actual.cpuMemory.optionPresent){
        actual.cpuMemory.optionValue=cpuMemoryPrep;
        actual.cpuMemory.requested=cpuMemoryPrep==1;
        if(cpuMemoryPrep!=1){
            actual.cpuMemory.admissionRaw=kIOReturnBadArgument;
        }else if(!actual.preparationReturned || actual.preparationRaw!=kIOReturnSuccess ||
                 actual.stage.phase!=ZornGen7BoardPreparedPhase26){
            actual.cpuMemory.admissionRaw=kIOReturnNotReady;
        }else{
            actual.cpuMemory.attempted=true;
            actual.cpuMemory.admissionRaw=kIOReturnSuccess;
            IORecursiveLockLock(owner.gpuComposition_);
            actual.cpuMemory.ownerCreateRaw=ZornGen7InactiveOwner26::create(
                *owner.platform_,owner.gpuInactiveOwner_);
            actual.cpuMemory.ownerCreateReturned=true;
            if(actual.cpuMemory.ownerCreateRaw==kIOReturnSuccess && owner.gpuInactiveOwner_){
                const auto result=owner.gpuInactiveOwner_->prepare(nullptr,0,owner);
                actual.cpuMemory.prepareReturned=true;
                actual.cpuMemory.phase=static_cast<uint32_t>(result.phase);
                actual.cpuMemory.cpuQueryReturned=result.cpuQueryReturned;
                actual.cpuMemory.cpuQueryRaw=result.cpuQueryStatus;
                actual.cpuMemory.cpuPageBytes=result.cpuPageBytes;
                actual.cpuMemory.graphStatusReturned=result.graphStatusReturned;
                actual.cpuMemory.graphStatus=result.graphStatus;
                actual.cpuMemory.firmwarePrepareReturned=result.prepareCodeReturned;
                actual.cpuMemory.firmwarePrepareCode=result.prepareCode;
                actual.cpuMemory.zeroAllocationReturned=result.zeroAllocationReturned;
                actual.cpuMemory.zeroAllocationRaw=result.zeroAllocationStatus;
                actual.cpuMemory.zeroCacheReturned=result.zeroCacheReturned;
                actual.cpuMemory.zeroCacheRaw=result.zeroCacheStatus;
                actual.cpuMemory.zeroPreparedCpuOnly=result.zeroPreparedCpuOnly;
            }
            IORecursiveLockUnlock(owner.gpuComposition_);
        }
    }
    // This second opt-in resolves the actual GPU/GMU paths from the retained
    // native tree, then captures their real descriptors. It makes no map or
    // hardware operation; the separate provider-claim opt-in follows below.
    unsigned providerResourcesPrep=0;
    actual.providerResources.optionPresent=PE_parse_boot_argn(
        "zorn26_gpu_provider_resources_prep",&providerResourcesPrep,sizeof(providerResourcesPrep));
    if(actual.providerResources.optionPresent){
        auto &provider=actual.providerResources;
        provider.optionValue=providerResourcesPrep;
        provider.requested=providerResourcesPrep==1;
        provider.inputNodesPresent=owner.gpuInputNodes_[0] && owner.gpuInputNodes_[1];
        if(providerResourcesPrep!=1){
            provider.admissionRaw=kIOReturnBadArgument;
        }else if(!actual.preparationReturned || actual.preparationRaw!=kIOReturnSuccess ||
                 actual.stage.phase!=ZornGen7BoardPreparedPhase26 ||
                 !actual.cpuMemory.optionPresent || actual.cpuMemory.optionValue!=1 ||
                 !actual.cpuMemory.prepareReturned || !actual.cpuMemory.zeroPreparedCpuOnly ||
                 !owner.gpuInactiveOwner_ || !provider.inputNodesPresent){
            provider.admissionRaw=kIOReturnNotReady;
        }else{
            provider.attempted=true;
            provider.admissionRaw=kIOReturnSuccess;
            IORecursiveLockLock(owner.gpuComposition_);
            const auto prepared=owner.gpuInactiveOwner_->prepareRegistryProviders(*owner.root_);
            provider.prepareReturned=true;
            provider.phase=static_cast<uint32_t>(prepared.phase);
            provider.registryLookupAttempted=prepared.registryLookupAttempted;
            provider.resourceCaptureAttempted=prepared.resourceCaptureAttempted;
            provider.retainedResourceMask=prepared.retainedResourceMask;
            for(unsigned i=0;i<2;++i){
                provider.registryLookupReturned[i]=prepared.registryLookupReturned[i];
                provider.registryNodeFound[i]=prepared.registryNodeFound[i];
                provider.resourceCountReturned[i]=prepared.resourceCountReturned[i];
                provider.resourceCount[i]=prepared.resourceCount[i];
                provider.providerReused[i]=prepared.reusedProvider[i];
                provider.nubAllocated[i]=prepared.nubAllocated[i];
                provider.nubInitReturned[i]=prepared.nubInitReturned[i];
                provider.nubInitialized[i]=prepared.nubInitialized[i];
                provider.nubAttachReturned[i]=prepared.nubAttachReturned[i];
                provider.nubAttached[i]=prepared.nubAttached[i];
                provider.nubResourceReturned[i]=prepared.nubResourceReturned[i];
                provider.nubResourceStatus[i]=prepared.nubResourceStatus[i];
            }
            IORecursiveLockUnlock(owner.gpuComposition_);
        }
    }
    // The next opt-in acquires only the existing base-class provider opens on
    // that exact resolved pair. This does not prove GPU/GMU DMA has stopped.
    unsigned providerClaimsPrep=0;
    actual.providerClaims.optionPresent=PE_parse_boot_argn(
        "zorn26_gpu_provider_claims_prep",&providerClaimsPrep,sizeof(providerClaimsPrep));
    if(actual.providerClaims.optionPresent){
        auto &claims=actual.providerClaims;
        claims.optionValue=providerClaimsPrep;
        claims.requested=providerClaimsPrep==1;
        if(providerClaimsPrep!=1){
            claims.admissionRaw=kIOReturnBadArgument;
        }else if(!owner.gpuInactiveOwner_ || !actual.providerResources.optionPresent ||
                 actual.providerResources.optionValue!=1 ||
                 !actual.providerResources.prepareReturned ||
                 !actual.providerResources.resourceCaptureAttempted ||
                 actual.providerResources.phase!=static_cast<uint32_t>(
                     ZornGen7InactiveOwner26::Phase::ResourcesRetainedCpuOnly) ||
                 actual.providerResources.retainedResourceMask!=15){
            claims.admissionRaw=kIOReturnNotReady;
        }else{
            claims.attempted=true;
            claims.admissionRaw=kIOReturnSuccess;
            IORecursiveLockLock(owner.gpuComposition_);
            claims.claimRaw=owner.gpuInactiveOwner_->prepareGpuProviderClaims();
            claims.callReturned=true;
            claims.claimsHeld=owner.gpuInactiveOwner_->gpuProviderClaimsHeld();
            IORecursiveLockUnlock(owner.gpuComposition_);
        }
    }
    IOLockLock(owner.gpuGate_);owner.gpuStatus_.inputReturned=actual.inputReturned;owner.gpuStatus_.inputRaw=actual.inputRaw;
    owner.gpuStatus_.preparationReturned=actual.preparationReturned;
    if(actual.preparationReturned){owner.gpuStatus_.preparationRaw=actual.preparationRaw;owner.gpuStatus_.stage=actual.stage;}
    owner.gpuStatus_.cpuMemory=actual.cpuMemory;
    owner.gpuStatus_.providerResources=actual.providerResources;
    owner.gpuStatus_.providerClaims=actual.providerClaims;
    owner.gpuStatus_.workerReturned=true;IOLockUnlock(owner.gpuGate_);
    if(actual.preparationReturned && actual.preparationRaw==kIOReturnSuccess && actual.stage.phase==ZornGen7BoardPreparedPhase26)
        IOService::publishResource("ZornGen7NativeBoardStagePrepared26"); // CPU dependency only.
    if(actual.preparationReturned && actual.preparationRaw==kIOReturnSuccess && actual.stage.phase==ZornGen7BoardPreparedPhase26)
        owner.scheduleBootCommandDbObservation();
    (void)thread_terminate(current_thread());panic("K80 GPU board preparation worker termination returned");
}
bool ZornRootPlatform26::copyGpuBoardStatus(ZornGen7PlatformBoardStatus26 &out)
{
    if(!preemption_enabled() || ml_at_interrupt_context() || !ml_get_interrupts_enabled())return false;
    if(__atomic_load_n(&gpuSetupTerminal_,__ATOMIC_ACQUIRE)){out=gpuStatus_;return true;}
    if(!__atomic_load_n(&gpuContextReady_,__ATOMIC_ACQUIRE))return false;
    IOLockLock(gpuGate_);const auto actual=gpuStatus_;IOLockUnlock(gpuGate_);
    if(!actual.setupReturned || (actual.setupRaw==kIOReturnSuccess && !actual.workerReturned))return false;
    out=actual;return true;
}
bool zorn26_gpu_board_platform_start(IOService *platform)
{
    unsigned selected=0;
    if(!PE_parse_boot_argn("zorn26_gpu_board_stage",&selected,sizeof(selected)))return true;
    auto *owner=__atomic_load_n(&retainedRootPlatform,__ATOMIC_ACQUIRE);
    if(selected!=1 || !platform || IOService::getPlatform()!=platform || !owner)return false;
    return owner->stageGpuBoard();
}
bool zorn26_gpu_board_platform_status(ZornGen7PlatformBoardStatus26 &out)
{auto *owner=__atomic_load_n(&retainedRootPlatform,__ATOMIC_ACQUIRE);return owner && owner->copyGpuBoardStatus(out);}

IOReturn ZornRootPlatform26::claimDirectPreparation()
{
    if(!preemption_enabled() || ml_at_interrupt_context() || !ml_get_interrupts_enabled() ||
       !__atomic_load_n(&gpuContextReady_,__ATOMIC_ACQUIRE))return kIOReturnNotReady;
    ZornGen7PlatformBoardStatus26 actual;
    if(!copyGpuBoardStatus(actual) || !actual.workerReturned || !actual.preparationReturned ||
       actual.preparationRaw!=kIOReturnSuccess || actual.stage.phase!=ZornGen7BoardPreparedPhase26 ||
       !gpuStage_ || !ZornGen7PlatformBoardStageGpuProviderClaimsHeld26(*gpuStage_) || !root_ ||
       !liveGpuGmuParentMatches(*root_,actual.stage))return kIOReturnNotReady;
    uint32_t empty=0;
    if(!__atomic_compare_exchange_n(&directAttempted_,&empty,1u,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))return kIOReturnExclusiveAccess;
    return kIOReturnSuccess;
}

IOReturn ZornRootPlatform26::scheduleDirect(OSObject &inputOwner,
    const ZornGen7StartupGpuInputs26 &input,ZornGen7PlatformDirectStage26 stage)
{
    const auto claimed=claimDirectPreparation();
    if(claimed!=kIOReturnSuccess)return claimed;
    // The factory copies inputs while the composition gate is held. Keep
    // the supplied code and callback context alive for the worker.
    IORecursiveLockLock(gpuComposition_);
    inputOwner.retain();directInputOwner_=&inputOwner;
    const auto raw=gpuStage_ ? ZornGen7SchedulePlatformDirect26(*platform_,*root_,*this,
        *gpuComposition_,*gpuStage_,input,stage,directStartup_) : kIOReturnNotReady;
    IORecursiveLockUnlock(gpuComposition_);
    return raw; // Thread-submission status only;never GPU completion.
}
IOReturn zorn26_gpu_platform_schedule_direct(OSObject &inputOwner,
    const ZornGen7StartupGpuInputs26 &input,ZornGen7PlatformDirectStage26 stage)
{
    auto *owner=__atomic_load_n(&retainedRootPlatform,__ATOMIC_ACQUIRE);
    return owner ? owner->scheduleDirect(inputOwner,input,stage) : kIOReturnNotReady;
}

IOReturn ZornRootPlatform26::scheduleAuthenticatedPrefix(OSObject &inputOwner,
    const ZornGen7StartupAuthenticatedPrefixInputs26 &input)
{
    const auto claimed=claimDirectPreparation();
    if(claimed!=kIOReturnSuccess)return claimed;
    IORecursiveLockLock(gpuComposition_);
    inputOwner.retain();directInputOwner_=&inputOwner;
    const auto raw=gpuStage_ ? ZornGen7SchedulePlatformAuthenticatedPrefix26(*platform_,*root_,*this,
        *gpuComposition_,*gpuStage_,input,directStartup_) : kIOReturnNotReady;
    IORecursiveLockUnlock(gpuComposition_);
    return raw;
}

IOReturn zorn26_gpu_platform_schedule_authenticated_prefix(OSObject &inputOwner,
    const ZornGen7StartupAuthenticatedPrefixInputs26 &input)
{
    auto *owner=__atomic_load_n(&retainedRootPlatform,__ATOMIC_ACQUIRE);
    return owner ? owner->scheduleAuthenticatedPrefix(inputOwner,input) : kIOReturnNotReady;
}

IOReturn ZornRootPlatform26::scheduleCommandDb(OSObject &inputOwner,
    const ZornGen7StartupInputs26 &input)
{
    if(!preemption_enabled() || ml_at_interrupt_context() || !ml_get_interrupts_enabled() ||
       !__atomic_load_n(&gpuContextReady_,__ATOMIC_ACQUIRE))return kIOReturnNotReady;
    ZornGen7PlatformBoardStatus26 actual;
    if(!copyGpuBoardStatus(actual) || !actual.workerReturned || !actual.preparationReturned ||
       actual.preparationRaw!=kIOReturnSuccess || actual.stage.phase!=ZornGen7BoardPreparedPhase26)return kIOReturnNotReady;
    uint32_t empty=0;
    if(!__atomic_compare_exchange_n(&directAttempted_,&empty,1u,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))return kIOReturnExclusiveAccess;
    // Same native composition gate protects the preparation handoff. The
    // factory copies inputs before returning;real code/cookies remain owned.
    IORecursiveLockLock(gpuComposition_);
    inputOwner.retain();directInputOwner_=&inputOwner;
    const auto raw=gpuStage_ ? ZornGen7SchedulePlatformCommandDb26(*platform_,*root_,*this,
        *gpuComposition_,*gpuStage_,input,directStartup_) : kIOReturnNotReady;
    IORecursiveLockUnlock(gpuComposition_);
    return raw; // Thread-submission status only;never GPU completion.
}
IOReturn zorn26_gpu_platform_schedule_commanddb(OSObject &inputOwner,const ZornGen7StartupInputs26 &input)
{
    auto *owner=__atomic_load_n(&retainedRootPlatform,__ATOMIC_ACQUIRE);
    return owner ? owner->scheduleCommandDb(inputOwner,input) : kIOReturnNotReady;
}

IOReturn ZornRootPlatform26::scheduleCommandDbObservation(OSObject &inputOwner,
    const ZornGen7StartupInputs26 &input)
{
    if(!preemption_enabled() || ml_at_interrupt_context() || !ml_get_interrupts_enabled() ||
       !__atomic_load_n(&gpuContextReady_,__ATOMIC_ACQUIRE))return kIOReturnNotReady;
    ZornGen7PlatformBoardStatus26 actual;
    if(!copyGpuBoardStatus(actual) || !actual.workerReturned || !actual.preparationReturned ||
       actual.preparationRaw!=kIOReturnSuccess || actual.stage.phase!=ZornGen7BoardPreparedPhase26)return kIOReturnNotReady;
    uint32_t empty=0;
    if(!__atomic_compare_exchange_n(&directAttempted_,&empty,1u,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))return kIOReturnExclusiveAccess;
    // Same native composition gate protects the preparation handoff. The
    // factory copies inputs before returning;real code/cookies remain owned.
    IORecursiveLockLock(gpuComposition_);
    inputOwner.retain();directInputOwner_=&inputOwner;
    const auto raw=gpuStage_ ? ZornGen7SchedulePlatformCommandDbObservation26(*platform_,*root_,*this,
        *gpuComposition_,*gpuStage_,input,directStartup_) : kIOReturnNotReady;
    IORecursiveLockUnlock(gpuComposition_);
    return raw; // Thread-submission status only;never GPU completion.
}

bool ZornRootPlatform26::copyCommandDbObservation(ZornGen7CommandDbWorkerObservation26 &out)
{
    if(!preemption_enabled() || ml_at_interrupt_context() || !ml_get_interrupts_enabled() ||
       !__atomic_load_n(&gpuContextReady_,__ATOMIC_ACQUIRE))return false;
    IORecursiveLockLock(gpuComposition_);
    const bool copied=directStartup_ && ZornGen7CopyCompletedPlatformCommandDbObservation26(*directStartup_,out);
    IORecursiveLockUnlock(gpuComposition_);return copied;
}
IOReturn zorn26_gpu_platform_schedule_commanddb_observation(OSObject &inputOwner,const ZornGen7StartupInputs26 &input)
{
    auto *owner=__atomic_load_n(&retainedRootPlatform,__ATOMIC_ACQUIRE);
    return owner ? owner->scheduleCommandDbObservation(inputOwner,input) : kIOReturnNotReady;
}
bool zorn26_gpu_platform_copy_commanddb_observation(ZornGen7CommandDbWorkerObservation26 &out)
{
    auto *owner=__atomic_load_n(&retainedRootPlatform,__ATOMIC_ACQUIRE);
    return owner && owner->copyCommandDbObservation(out);
}

void ZornRootPlatform26::scheduleBootCommandDbObservation()
{
    unsigned selected=0,captured=0,only=0;
    const bool observation=PE_parse_boot_argn("zorn26_commanddb_source_read",&selected,sizeof(selected)) && selected==1;
    const bool resources=PE_parse_boot_argn("zorn26_commanddb_resources",&captured,sizeof(captured)) && captured==1 &&
        PE_parse_boot_argn("zorn26_commanddb_resources_only",&only,sizeof(only)) && only==1;
    if(!observation && !resources)return;
    // Invoked only by the actual preparation worker after it has published its
    // successful CPU result. No full GPU-input table or authority is invented.
    uint32_t empty=0;IOReturn raw=kIOReturnExclusiveAccess;
    if(observation && resources)raw=kIOReturnBadArgument;
    else if(__atomic_compare_exchange_n(&directAttempted_,&empty,1u,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE)){
        IORecursiveLockLock(gpuComposition_);
        const auto schedule=resources?ZornGen7SchedulePlatformCapturedCommandDb26:ZornGen7SchedulePlatformCommandDbObservationOnly26;
        raw=gpuStage_ ? schedule(*platform_,*root_,*this,*gpuComposition_,*gpuStage_,directStartup_) : kIOReturnNotReady;
        IORecursiveLockUnlock(gpuComposition_);
    }
    IOLockLock(gpuGate_);commandDbCapturedResources_=resources;commandDbSubmissionRaw_=raw;commandDbSubmissionReturned_=true;IOLockUnlock(gpuGate_);
}
bool ZornRootPlatform26::copyCommandDbSubmission(IOReturn &out)
{
    if(!preemption_enabled() || ml_at_interrupt_context() || !ml_get_interrupts_enabled() ||
       !__atomic_load_n(&gpuContextReady_,__ATOMIC_ACQUIRE))return false;
    IOLockLock(gpuGate_);
    if(!commandDbSubmissionReturned_ || commandDbCapturedResources_){IOLockUnlock(gpuGate_);return false;}
    out=commandDbSubmissionRaw_;IOLockUnlock(gpuGate_);return true;
}
bool zorn26_gpu_platform_commanddb_observation_submission(IOReturn &out)
{
    auto *owner=__atomic_load_n(&retainedRootPlatform,__ATOMIC_ACQUIRE);
    return owner && owner->copyCommandDbSubmission(out);
}

bool ZornRootPlatform26::copyCommandDbStatus(ZornGen7CommandDbStatus26 &out)
{
    if(!preemption_enabled() || ml_at_interrupt_context() || !ml_get_interrupts_enabled() ||
       !__atomic_load_n(&gpuContextReady_,__ATOMIC_ACQUIRE))return false;
    IORecursiveLockLock(gpuComposition_);
    const bool copied=directStartup_ && ZornGen7CopyCompletedPlatformCommandDbStatus26(*directStartup_,out);
    IORecursiveLockUnlock(gpuComposition_);return copied;
}
bool zorn26_gpu_platform_commanddb_observation_status(ZornGen7CommandDbStatus26 &out)
{
    auto *owner=__atomic_load_n(&retainedRootPlatform,__ATOMIC_ACQUIRE);
    return owner && owner->copyCommandDbStatus(out);
}

bool ZornRootPlatform26::copyCapturedCommandDbSubmission(IOReturn &out)
{
    if(!preemption_enabled() || ml_at_interrupt_context() || !ml_get_interrupts_enabled() ||
       !__atomic_load_n(&gpuContextReady_,__ATOMIC_ACQUIRE))return false;
    IOLockLock(gpuGate_);
    if(!commandDbSubmissionReturned_ || !commandDbCapturedResources_){IOLockUnlock(gpuGate_);return false;}
    out=commandDbSubmissionRaw_;IOLockUnlock(gpuGate_);return true;
}
bool ZornRootPlatform26::copyCapturedCommandDbStatus(ZornGen7CommandDbCapturedStatus26 &out)
{
    if(!preemption_enabled() || ml_at_interrupt_context() || !ml_get_interrupts_enabled() ||
       !__atomic_load_n(&gpuContextReady_,__ATOMIC_ACQUIRE))return false;
    IORecursiveLockLock(gpuComposition_);
    const bool copied=directStartup_ && ZornGen7CopyCompletedPlatformCapturedCommandDb26(*directStartup_,out);
    IORecursiveLockUnlock(gpuComposition_);return copied;
}
bool zorn26_gpu_platform_captured_commanddb_submission(IOReturn &out)
{auto *owner=__atomic_load_n(&retainedRootPlatform,__ATOMIC_ACQUIRE);return owner && owner->copyCapturedCommandDbSubmission(out);}
bool zorn26_gpu_platform_captured_commanddb_status(ZornGen7CommandDbCapturedStatus26 &out)
{auto *owner=__atomic_load_n(&retainedRootPlatform,__ATOMIC_ACQUIRE);return owner && owner->copyCapturedCommandDbStatus(out);}

bool ZornRootPlatform26::copyRscControllerRead(ZornGen7RscControllerStatus26 &out,IOReturn &raw)
{
    if(!preemption_enabled() || ml_at_interrupt_context() || !ml_get_interrupts_enabled() ||
       !__atomic_load_n(&gpuContextReady_,__ATOMIC_ACQUIRE))return false;
    IORecursiveLockLock(gpuComposition_);
    const bool copied=directStartup_ && ZornGen7CopyCompletedPlatformRscControllerRead26(*directStartup_,out,raw);
    IORecursiveLockUnlock(gpuComposition_);return copied;
}
bool zorn26_gpu_platform_rsc_controller_read_status(ZornGen7RscControllerStatus26 &out,IOReturn &raw)
{auto *owner=__atomic_load_n(&retainedRootPlatform,__ATOMIC_ACQUIRE);return owner && owner->copyRscControllerRead(out,raw);}

bool ZornRootPlatform26::copyRscManaged(ZornGen7RscManagedStatus26 &out)
{
    if(!preemption_enabled() || ml_at_interrupt_context() || !ml_get_interrupts_enabled() ||
       !__atomic_load_n(&gpuContextReady_,__ATOMIC_ACQUIRE))return false;
    IORecursiveLockLock(gpuComposition_);
    const bool copied=directStartup_ && ZornGen7CopyCompletedPlatformRscManaged26(*directStartup_,out);
    IORecursiveLockUnlock(gpuComposition_);return copied;
}
bool zorn26_gpu_platform_rsc_managed_status(ZornGen7RscManagedStatus26 &out)
{auto *owner=__atomic_load_n(&retainedRootPlatform,__ATOMIC_ACQUIRE);return owner && owner->copyRscManaged(out);}

// Diagnostic copy of the existing completed startup result only. No callback,
// provider,reference,resource address or new readiness is exported to userland.
bool ZornRootPlatform26::copyStartupResult(ZornGen7RegistryStartupResult26 &out)
{
    if(!preemption_enabled() || ml_at_interrupt_context() || !ml_get_interrupts_enabled() ||
       !__atomic_load_n(&gpuContextReady_,__ATOMIC_ACQUIRE))return false;
    IORecursiveLockLock(gpuComposition_);
    const bool copied=directStartup_ && ZornGen7CopyCompletedPlatformStartupResult26(*directStartup_,out);
    IORecursiveLockUnlock(gpuComposition_);return copied;
}
extern "C" bool zorn26_gpu_platform_startup_result26(ZornGen7RegistryStartupResult26 &out)
{
    auto *owner=__atomic_load_n(&retainedRootPlatform,__ATOMIC_ACQUIRE);
    return owner && owner->copyStartupResult(out);
}

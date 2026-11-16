// SPDX-License-Identifier: BSD-2-Clause-Patent
#include "ZornGen7RegisterMaps26.h"
#include "ZornGen7NativeSmmuIrqResult26.h"
#include "ZornGen7SmmuRuntimePm26.h"
#include "ZornGen7AppExecution26.h"
#include "ZornGen7CpBootstrapAuthority26.h"
#include "ZornGen7HostRing26.h"
#include "ZornGen7DirectRuntimeAuthority26.h"
#include "ZornGen7HostGpuCode26.h"
#include "ZornGen7HostGpuRegisters26.h"
#include "ZornGen7GpuIrq26.h"
#include "ZornGen7HostRing26.h"
#include "ZornGen7DirectRuntimeAuthority26.h"
#include "GpuGen7Table.h"
#include "ZornGen7AtomicSmmuIo26.h"
#include "ZornGen7Cm3Start26.h"
#include "ZornGen7InactiveOwner26.h"
#include "ZornGen7PlatformMmioInputs26.h"
#include "houji_full_host_runtime.h"
#include <IOKit/IOLib.h>
#include <IOKit/IOKitKeys.h>
#include <IOKit/IOPlatformExpert.h>
#include <libkern/c++/OSSharedPtr.h>
#include <libkern/c++/OSArray.h>
#include <libkern/c++/OSData.h>
#include <kern/task.h>
#include <pexpert/pexpert.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
OSDefineMetaClassAndStructors(ZornGen7RegisterMaps26,OSObject);
namespace {
// Same exact descriptor identity comparisons as the approved parent. These
// numbers supply no access grant and never construct physical descriptors.
constexpr struct {
    uint64_t physical; size_t bytes;
    uint64_t descriptorPhysical; size_t descriptorBytes, offset;
    bool readOnly;
} apertures[] = {
    {0x3d00000, 0x40000, 0x3d00000, 0x40000, 0, false},
    {0x3d68000, 0x37000, 0x3d68000, 0x37000, 0, false},
    {0x3d50000, 0x10000, 0x3d50000, 0x10000, 0, false},
    {0xb280000, 0x10000, 0xb280000, 0x10000, 0, false},
    {0x3da0000, 0x40000, 0x3da0000, 0x40000, 0, false},
    {0x170000, 0x4000, 0x100000, 0x1f4200, 0x70000, true}
};
// Pinned Qualcomm SM8650 Gen7 graphics-kernel source: adreno_gen7_gmu.c and
// gen7_reg.h at OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8650
// commit 453d8875f815bf9dfad9035982861226a4823a6c. Register indices are
// byte-addressed from the K80 Gen7 GPU aperture at 0x03d00000.
constexpr uint32_t kGpuRegisterAperture=0x03d00000u;
constexpr uint32_t kGmuBusyStatusWord=0x23b0cu,kGmuBusyStatus2Word=0x23b0du;
constexpr uint32_t kGbifHaltWord=0x3c45u,kGbifHaltAckWord=0x3c46u;
// gen7_gmu_wait_for_idle passes BIT(30) to gmu_core_timed_poll_check.
// The helper compares (value & mask) to zero, so test only bit 30.
constexpr uint32_t kGmuIdlePollMask=1u<<30,kGbifClientHalt=1u<<0,kGbifArbHalt=1u<<1;
constexpr unsigned kGpuStopPollDelayUs=100u,kGpuStopPollBudget=1000u;
constexpr uint32_t gpuRegisterAddress(uint32_t word){return kGpuRegisterAperture+word*4u;}
static_assert(gpuRegisterAddress(kGmuBusyStatusWord)>=apertures[1].physical &&
    gpuRegisterAddress(kGmuBusyStatusWord)+4<=apertures[1].physical+apertures[1].bytes &&
    gpuRegisterAddress(kGmuBusyStatus2Word)>=apertures[1].physical &&
    gpuRegisterAddress(kGmuBusyStatus2Word)+4<=apertures[1].physical+apertures[1].bytes,
    "Gen7 GMU busy registers are outside the retained K80 GMU aperture");
static_assert(gpuRegisterAddress(kGbifHaltWord)>=apertures[0].physical &&
    gpuRegisterAddress(kGbifHaltWord)+4<=apertures[0].physical+apertures[0].bytes &&
    gpuRegisterAddress(kGbifHaltAckWord)>=apertures[0].physical &&
    gpuRegisterAddress(kGbifHaltAckWord)+4<=apertures[0].physical+apertures[0].bytes,
    "Gen7 GBIF halt registers are outside the retained K80 GPU aperture");
bool nativeContext()
{
    return preemption_enabled() && !ml_at_interrupt_context();
}
void orderedIo()
{
    __asm__ volatile("dsb sy" ::: "memory");
}
}

struct ZornGen7RegisterMaps26::Storage {
    ZornGen7OperationGuard26 guard;bool nativeCpuMappings=false;
    IOService *providers[2]{};IOMemoryDescriptor *resources[4]{};
    // One private real IOKit client for the distinct GPU and GMU providers.
    // Root/epoch lifetime,not per-app ownership. No seizure,matching,PMinit,
    // close-on-failure,or borrowed clock/SMMU provider claim is introduced.
    IOService *claimant=nullptr,*claimParent=nullptr;
    bool providerOpened[2]{};
    ZornGen7PlatformMmioInputs26 *platformInputs=nullptr;
    IOService *platformProviders[2]{};IOMemoryDescriptor *platformResources[2]{};
    IOMemoryMap *maps[6]{};uintptr_t virtualBase[6]{};
    // Owner-held actual GPU property/descriptor and distinct real CX_MISC map.
    OSObject *cxNames=nullptr,*cxResourceProperty=nullptr;
    IOMemoryDescriptor *cxDescriptor=nullptr;IOMemoryMap *cxMap=nullptr;
    uintptr_t cxVirtualBase=0;
    OSObject *cxTimerAuthorityOwner=nullptr;ZornGen7CxTimerAuthority26 cxTimerAuthority{};
    OSObject *cm3AuthorityOwner=nullptr;ZornGen7GmuStartAuthority26 cm3Authority{};
    ZornGen7HostGpuCode26 *gpuCodeOwner=nullptr;ZornGen7HostGpuRegisters26 *gpuRegistersOwner=nullptr;ZornGen7GpuIrq26 *gpuIrqOwner=nullptr;ZornGen7HostRing26 *hostRingOwner=nullptr;
    OSObject *cpAuthorityOwner=nullptr;ZornGen7CpStartAuthority26 cpAuthority{};
    bool kernelTaskGrantAttempted=false,kernelTaskReleaseAttempted=false;int kernelTaskGrantRaw=0,kernelTaskReleaseRaw=0;
    bool oobReleaseGrantAttempted=false,oobReleaseGrantReturned=false;int oobReleaseGrantRaw=0;
    bool bootstrapGrantAttempted=false,bootstrapGrantReturned=false;int bootstrapGrantRaw=0;
    OSObject *bootstrapAuthorityOwner=nullptr;ZornGen7CpBootstrapAuthority26 bootstrapAuthority{};
    bool cpGrantAttempted=false,cpGrantReturned=false;int cpGrantRaw=0;
    OSObject *gpuRegisterAuthorityOwner=nullptr;ZornGen7GpuRegisterAuthority26 gpuRegisterAuthority{};
    bool gpuRegistersGrantAttempted=false,gpuRegistersGrantReturned=false;int gpuRegistersGrantRaw=0;
    OSObject *gpuStartOwner=nullptr;ZornGen7GpuStartAuthority26 gpuStartAuthority{};
    bool gpuWindowAttempted=false,gpuWindowReturned=false;
    bool gpuWindowClaimsHeldBefore=false,gpuWindowClaimsHeldAfter=false,gpuWindowCallbackInvoked=false;
    int gpuWindowRaw=0,gpuWindowCallbackRaw=0;
    bool cm3Attempted=false,cm3AuthorityReturned=false,cm3Returned=false;int cm3AuthorityRaw=0;
    ZornGen7Cm3Native26::Result cm3Result{};
    ZornGen7CxTimer::CounterDomain cxTimerCounter=ZornGen7CxTimer::CounterDomain::Unknown;
    ZornGen7CxTimer::Result cxTimerResult{};
    OSObject *configFaultOwner=nullptr;int (*configClearFault)(OSObject &)=nullptr;
    bool configAttempted=false,configActive=false;
    ZornGen7RegisterConfig::CheckedResult configResult{};
    OSObject *callbackBorrower=nullptr,*smmuBorrower=nullptr;
    OSObject *pdcRscFlagsOwner=nullptr;ZornGen7PdcRsc::CheckedProgram *pdcRscProgram=nullptr;
    ZornGen7PdcRsc::CheckedResult pdcRscResult{};bool pdcRscAttempted=false,pdcRscActive=false;
    bool nativeSmmuCfgAttempted=false,nativeSmmuControlBound=false,nativeSmmuControlCr0Read=false;
    uint32_t nativeSmmuControlCr0=0;
    bool nativeColdSmmuBound=false,nativeColdMatching=false;unsigned nativeColdGroups=0,nativeColdBanks=0;
    size_t nativeColdContextBase=0,nativeColdStride=0;uint32_t nativeColdExpectedCr0=0;
    volatile uint32_t nativeGlobalFaultIoBound=0;
    ZornGen7SmmuRuntimePm26 *nativeProbePm=nullptr;
    IOService *nativeProbeController=nullptr;IORecursiveLock *nativeProbeGate=nullptr;
    IOMemoryDescriptor *nativeProbeDescriptor=nullptr;
    Result result;GpuBusStopResult gpuBusStop{};bool accessBusy=false;
    static void *operator new(size_t,void *p) noexcept{return p;}
};
IOReturn ZornGen7RegisterMaps26::create(ZornGen7InactiveOwner26 &parent,OSObject &codeOwner,
    const ZornGen7OperationGuard26 &guard,ZornGen7RegisterMaps26 *&output,bool nativeSmmu)
{return createImpl(parent,codeOwner,&guard,output,nativeSmmu);}
IOReturn ZornGen7RegisterMaps26::createNativeCpuMappings(ZornGen7InactiveOwner26 &parent,OSObject &codeOwner,
    ZornGen7RegisterMaps26 *&output)
{
    unsigned selected=0;
    if(!PE_parse_boot_argn("zorn26_register_maps",&selected,sizeof(selected)) || selected!=1)return kIOReturnNotPermitted;
    return createImpl(parent,codeOwner,nullptr,output,true);
}
IOReturn ZornGen7RegisterMaps26::createImpl(ZornGen7InactiveOwner26 &parent,OSObject &codeOwner,
    const ZornGen7OperationGuard26 *guard,ZornGen7RegisterMaps26 *&output,bool nativeSmmu)
{
    if(output || !nativeContext() || (guard && (!guard->admitMap || !guard->admitAccess || !guard->observeAccess)))
        return kIOReturnBadArgument;
    auto *owner=new ZornGen7RegisterMaps26;if(!owner)return kIOReturnNoMemory;
    if(!owner->init()){owner->release();return kIOReturnNoMemory;}
    owner->retain();owner->pinned_=true;output=owner;parent.retain();codeOwner.retain();
    owner->parent_=&parent;owner->codeOwner_=&codeOwner;
    void *memory=IOMallocZero(sizeof(Storage));if(!memory)return kIOReturnNoMemory;
    owner->storage_=new(memory) Storage;auto &s=*owner->storage_;s.nativeCpuMappings=nativeSmmu;if(guard)s.guard=*guard;s.result.phase=Phase::Retained;
    owner->gate_=IOLockAlloc();if(!owner->gate_)return kIOReturnNoMemory;
    IOService *preparedClaimant=nullptr,*preparedClaimParent=nullptr;
    if(!parent.borrowForRegisterMappings(*owner,s.providers,s.resources,preparedClaimant,preparedClaimParent))
        return kIOReturnNotReady;
    for(auto *p:s.providers)p->retain();for(auto *p:s.resources)p->retain();
    s.result.borrowAcquired=true;s.result.phase=Phase::Borrowed;
    if(!ml_get_interrupts_enabled())return kIOReturnNotReady;
    // Reuse only the inspected base classes' single-owner handleOpen. A
    // subclass could allow shared opens;never seize it or call it exclusive.
    for(auto *provider:s.providers){
        const auto *meta=provider->getMetaClass();
        if(meta!=IOPlatformDevice::metaClass && meta!=IOService::metaClass)return kIOReturnUnsupported;
        if(provider->isInactive())return kIOReturnNotAttached;
    }
    if(s.providers[0]==s.providers[1])return kIOReturnBadArgument;
    OSSharedPtr<IORegistryEntry> parentEntry(s.providers[0]->copyParentEntry(gIOServicePlane),OSNoRetain);
    auto *common=OSDynamicCast(IOService,parentEntry.get());
    if(!common || s.providers[1]->getProvider()!=common)return kIOReturnNotAttached;
    if(preparedClaimant || preparedClaimParent){
        if(!preparedClaimant || !preparedClaimParent || common!=preparedClaimParent ||
           preparedClaimant->isInactive() || preparedClaimant->getProvider()!=preparedClaimParent)
            return kIOReturnNotAttached;
        preparedClaimParent->retain();s.claimParent=preparedClaimParent;
        preparedClaimant->retain();s.claimant=preparedClaimant;
        for(unsigned i=0;i<2;++i){
            s.providerOpened[i]=s.providers[i]->isOpen(s.claimant);
            if(!s.providerOpened[i])return kIOReturnNotOpen;
        }
        return owner->providerClaimsHeld()?kIOReturnSuccess:kIOReturnNotOpen;
    }
    common->retain();s.claimParent=common; // explicit root/claimant parent lifetime
    s.claimant=new IOService;if(!s.claimant)return kIOReturnNoMemory;
    if(!s.claimant->init())return kIOReturnError;
    if(!s.claimant->attach(s.claimParent))return kIOReturnNotAttached;
    for(unsigned i=0;i<2;++i){
        const bool opened=s.providers[i]->open(s.claimant,0,nullptr);
        s.providerOpened[i]=opened;
        if(!opened)return kIOReturnExclusiveAccess;
        if(!s.providers[i]->isOpen(s.claimant))return kIOReturnNotOpen;
    }
    return owner->providerClaimsHeld()?kIOReturnSuccess:kIOReturnNotOpen;
    // Any partial open and all actual refs stay with the pinned mapping owner.
    // Independent guard callbacks below still decide physical access rights.

}
bool ZornGen7RegisterMaps26::providerClaimsHeld() const
{
    if(!storage_ || !nativeContext() || !ml_get_interrupts_enabled())return false;
    const auto &s=*storage_;
    if(!s.claimant || !s.claimParent || s.claimant->isInactive() || s.claimParent->isInactive() ||
       s.claimant->getProvider()!=s.claimParent)return false;
    for(unsigned i=0;i<2;++i){
        if(!s.providerOpened[i] || !s.providers[i] || s.providers[i]->isInactive() ||
           s.providers[i]->getProvider()!=s.claimParent || !s.providers[i]->isOpen(s.claimant))return false;
    }
    return true; // Source-local software exclusion,never hardware readiness.
}
bool ZornGen7RegisterMaps26::boundAndReadyForGpuStart(ZornGen7InactiveOwner26 &parent) const
{
    if(!storage_ || !gate_ || parent_!=&parent || !providerClaimsHeld())return false;
    IOLockLock(gate_);const auto &s=*storage_;
    const bool ready=s.result.mapsReady && s.result.mapViewAccepted[0] && s.result.mapViewAccepted[1] &&
        s.providers[0] && s.providers[1] && s.resources[0] && s.resources[1];
    IOLockUnlock(gate_);
    return ready && providerClaimsHeld();
}
bool ZornGen7RegisterMaps26::hostGpuStartPairIs(ZornGen7InactiveOwner26 &parent,
    IOService &gpu,IOMemoryDescriptor &gpuResource,IOService &gmu,IOMemoryDescriptor &gmuResource) const
{
    if(!storage_ || !gate_ || parent_!=&parent || &gpu==&gmu || &gpuResource==&gmuResource ||
       !providerClaimsHeld())return false;
    IOLockLock(gate_);const auto &s=*storage_;
    const bool exact=s.result.mapsReady && s.result.mapViewAccepted[0] && s.result.mapViewAccepted[1] &&
        s.providers[0]==&gpu && s.providers[1]==&gmu &&
        s.resources[0]==&gpuResource && s.resources[1]==&gmuResource;
    IOLockUnlock(gate_);
    return exact && providerClaimsHeld();
}
ZornGen7RegisterMaps26::Result ZornGen7RegisterMaps26::capturePlatformInputs(
    ZornGen7PlatformMmioInputs26 &actual)
{
    if (!storage_ || !gate_ || !nativeContext()) return {};
    auto &s = *storage_;
    IOLockLock(gate_);
    if(s.result.platformCaptureAttempted && s.platformInputs!=&actual) {
        Result refused=s.result;refused.platformInputsCaptured=false;
        IOLockUnlock(gate_);return refused;
    }
    if (!s.result.borrowAcquired || s.result.platformCaptureAttempted ||
        s.result.mappingAttempted) {
        Result result = s.result;
        IOLockUnlock(gate_);
        return result;
    }
    s.result.platformCaptureAttempted = true;
    s.result.phase = Phase::PlatformCapture;
    actual.retain();
    s.platformInputs = &actual; // Keep partial inputs even if borrow refuses.
    IOLockUnlock(gate_);
    IOService *providers[2] = {};
    IOMemoryDescriptor *descriptors[2] = {};
    const bool borrowed = actual.borrowForMmio(*this, s.providers,
                                              providers, descriptors);
    if (borrowed) {
        for (auto *provider : providers) provider->retain();
        for (auto *descriptor : descriptors) descriptor->retain();
    }
    IOLockLock(gate_);
    if (borrowed) {
        for (unsigned i = 0; i < 2; ++i) {
            s.platformProviders[i] = providers[i];
            s.platformResources[i] = descriptors[i];
        }
        s.result.platformInputsCaptured = true;
    }
    Result result = s.result;
    IOLockUnlock(gate_);
    return result;
}

ZornGen7RegisterMaps26::Result ZornGen7RegisterMaps26::prepareMappings()
{
    if(!providerClaimsHeld())return readResult();
    if (!storage_ || !gate_ || !nativeContext()) return {};
    auto &s = *storage_;
    IOLockLock(gate_);
    if (s.result.mappingAttempted) {
        Result result = s.result;
        IOLockUnlock(gate_);
        return result;
    }
    s.result.mappingAttempted = true;
    if (!s.result.platformInputsCaptured) {
        Result result = s.result;
        IOLockUnlock(gate_);
        return result;
    }
    s.result.phase = Phase::Mapping;
    IOLockUnlock(gate_);
    for (unsigned slot = 0; slot < 6; ++slot) {
        auto *descriptor = slot < 4 ? s.resources[slot] : s.platformResources[slot - 4];
        const auto &required = apertures[slot];
        IOByteCount contiguous = 0;
        const auto length = descriptor->getLength();
        const auto base = descriptor->getPhysicalSegment(0, &contiguous,
                                                        kIOMemoryMapperNone);
        IOByteCount viewContiguous = 0;
        const auto physical = descriptor->getPhysicalSegment(required.offset,
            &viewContiguous, kIOMemoryMapperNone);
        IOLockLock(gate_);
        s.result.shapeRead[slot] = true;
        const bool shape = length == required.descriptorBytes &&
            base == required.descriptorPhysical && contiguous >= required.descriptorBytes &&
            required.offset <= length && required.bytes <= length - required.offset &&
            physical == required.physical && viewContiguous >= required.bytes;
        if (!shape) s.result.phase = Phase::DescriptorRejected;
        IOLockUnlock(gate_);
        if (!shape) return readResult();

        // Native CPU-only route uses this owner's real single-client provider
        // opens and retained descriptors. It creates no device-access grant;
        // access() still refuses without separately bound real callbacks.
        if(s.guard.admitMap){
            const int permission=s.guard.admitMap(s.guard.cookie,*descriptor,physical,required.bytes);
            IOLockLock(gate_);s.result.mapGuardReturned[slot]=true;s.result.mapGuardStatus[slot]=permission;
            if(permission)s.result.phase=Phase::MapGuardRejected;IOLockUnlock(gate_);
            if(permission)return readResult();
        }
        if(!providerClaimsHeld())return readResult();

        IOMemoryMap *map = descriptor->createMappingInTask(kernel_task, 0,
            kIOMapAnywhere | kIOMapInhibitCache | (required.readOnly ? kIOMapReadOnly : 0),
            required.offset, required.bytes);
        IOLockLock(gate_);
        s.maps[slot] = map; // Retain returned ownership even for rejected view.
        s.result.mapCallReturned[slot] = true;
        s.result.mapObjectReturned[slot] = map != nullptr;
        if (!map) s.result.phase = Phase::MapUnavailable;
        IOLockUnlock(gate_);
        if (!map) return readResult();
        const auto virtualAddress = map->getVirtualAddress();
        const auto mappedLength = map->getLength();
        const auto mappedPhysical = map->getPhysicalAddress();
        const bool accepted = mappedLength == required.bytes &&
            mappedPhysical == physical && virtualAddress &&
            !(virtualAddress & 7U) && required.bytes - 1U <= UINTPTR_MAX - virtualAddress;
        IOLockLock(gate_);
        s.result.mapViewAccepted[slot] = accepted;
        if (accepted) s.virtualBase[slot] = virtualAddress;
        else s.result.phase = Phase::MapViewRejected;
        IOLockUnlock(gate_);
        if (!accepted) return readResult();
    }
    if(!prepareCxMiscMapping())return readResult();
    IOLockLock(gate_);
    s.result.mapsReady = true;
    s.result.phase = Phase::Bound;
    Result result = s.result;
    IOLockUnlock(gate_);
    return result;
}

bool ZornGen7RegisterMaps26::prepareCxMiscMapping()
{
    if(!storage_ || !gate_ || !nativeContext() || !providerClaimsHeld())return false;
    auto &s=*storage_;IOLockLock(gate_);
    if(s.result.cxMappingAttempted || !s.result.borrowAcquired || !s.providers[0]) {
        IOLockUnlock(gate_);return false;
    }
    s.result.cxMappingAttempted=true;IOLockUnlock(gate_);
    // The same retained GPU provider is projected from actual native arm-io
    // ranges. The third named resource has its own descriptor and map even
    // though its first page overlaps the ordinary GMU aperture.
    constexpr char expectedNames[]="kgsl_3d0_reg_memory\0rscc\0cx_misc";
    s.cxNames=s.providers[0]->copyProperty("reg-names");
    auto *names=OSDynamicCast(OSData,s.cxNames);
    if(!names || names->getLength()!=sizeof(expectedNames) || !names->getBytesNoCopy())return false;
    const auto *bytes=static_cast<const uint8_t *>(names->getBytesNoCopy());
    for(size_t i=0;i<sizeof(expectedNames);++i)if(bytes[i]!=uint8_t(expectedNames[i]))return false;
    s.cxResourceProperty=s.providers[0]->copyProperty(gIODeviceMemoryKey);
    auto *array=OSDynamicCast(OSArray,s.cxResourceProperty);
    if(!array || array->getCount()!=3)return false;
    auto *descriptor=OSDynamicCast(IOMemoryDescriptor,array->getObject(2));
    if(!descriptor || descriptor==s.resources[0] || descriptor==s.resources[1] ||
       descriptor==s.resources[2] || descriptor==s.resources[3])return false;
    constexpr uint64_t physical=0x3d9e000;constexpr size_t length=0x2000;
    IOByteCount contiguous=0;
    const auto base=descriptor->getPhysicalSegment(0,&contiguous,kIOMemoryMapperNone);
    if(descriptor->getLength()!=length || base!=physical || contiguous<length)return false;
    descriptor->retain();s.cxDescriptor=descriptor;
    IOLockLock(gate_);s.result.cxDescriptorCaptured=true;IOLockUnlock(gate_);
    if(s.guard.admitMap){
        const int permission=s.guard.admitMap(s.guard.cookie,*descriptor,physical,length);
        IOLockLock(gate_);s.result.cxMapGuardReturned=true;s.result.cxMapGuardStatus=permission;
        if(permission)s.result.phase=Phase::MapGuardRejected;IOLockUnlock(gate_);if(permission)return false;
    }
    if(!providerClaimsHeld())return false;
    auto *map=descriptor->createMappingInTask(kernel_task,0,kIOMapAnywhere|kIOMapInhibitCache,0,length);
    s.cxMap=map;IOLockLock(gate_);s.result.cxMapCallReturned=true;s.result.cxMapObjectReturned=map!=nullptr;
    if(!map)s.result.phase=Phase::MapUnavailable;
    IOLockUnlock(gate_);if(!map)return false;
    const auto address=map->getVirtualAddress();
    const bool accepted=map->getLength()==length && map->getPhysicalAddress()==physical &&
        address && !(address&7u) && length-1<=UINTPTR_MAX-address;
    IOLockLock(gate_);s.result.cxMapViewAccepted=accepted;
    if(accepted)s.cxVirtualBase=address;else s.result.phase=Phase::MapViewRejected;
    IOLockUnlock(gate_);return accepted;
    // No read/write, timer grant, clock result or release follows this map.
    // All partial objects/maps remain retained; no fallback to GMU's mapping.
}

bool ZornGen7RegisterMaps26::matchesGuardMap(IOMemoryDescriptor &descriptor,
    uint64_t physical, size_t bytes)
{
    if (!storage_ || !gate_ || !nativeContext()) return false;
    IOLockLock(gate_);
    const auto &s = *storage_;
    bool matches = false;
    if (s.result.phase == Phase::Mapping && s.result.platformInputsCaptured) {
        for (unsigned slot = 0; slot < 6; ++slot) {
            auto *captured = slot < 4 ? s.resources[slot] : s.platformResources[slot - 4];
            if (captured == &descriptor && apertures[slot].physical == physical &&
                apertures[slot].bytes == bytes && s.result.shapeRead[slot] && !s.maps[slot]) {
                matches = true;
                break;
            }
        }
        if (s.result.cxDescriptorCaptured && s.cxDescriptor == &descriptor &&
            physical == 0x3d9e000 && bytes == 0x2000 && !s.cxMap) matches = true;
    }
    IOLockUnlock(gate_);
    return matches;
}

bool ZornGen7RegisterMaps26::matchesGuardAccess(IOMemoryDescriptor &descriptor,
    uint32_t address, unsigned width, bool write)
{
    if (!storage_ || !gate_ || !nativeContext() ||
        (width != 4 && width != 8) || (address & (width - 1))) return false;
    IOLockLock(gate_);
    const auto &s = *storage_;
    bool matches = false;
    if (s.result.mapsReady && s.accessBusy) {
        for (unsigned slot = 0; slot < 6; ++slot) {
            const auto &range = apertures[slot];
            auto *captured = slot < 4 ? s.resources[slot] : s.platformResources[slot - 4];
            if (captured == &descriptor && s.result.mapViewAccepted[slot] &&
                !(write && range.readOnly) && (width == 4 || slot == 4) &&
                address >= range.physical && address - range.physical <= range.bytes - width) {
                matches = true;
                break;
            }
        }
    }
    IOLockUnlock(gate_);
    return matches;
}

int ZornGen7RegisterMaps26::access(uint32_t address, unsigned width,
    bool write, uint64_t &value)
{
    if (!storage_ || !gate_ || !nativeContext() ||
        (width != 4 && width != 8) || (address & (width - 1U)))
        return FHR_ARGUMENT;
    if(!providerClaimsHeld())return FHR_NOT_AVAILABLE;
    auto &s = *storage_;
    // A real CPU map is not permission to execute an MMIO operation. Native
    // mapping-only construction intentionally leaves these slots absent.
    if(!s.guard.admitAccess || !s.guard.observeAccess)return FHR_NOT_AVAILABLE;
    IOLockLock(gate_);
    if (!s.result.mapsReady || s.accessBusy) {
        const int refusal = s.accessBusy ? FHR_BUSY : FHR_NOT_AVAILABLE;
        IOLockUnlock(gate_);
        return refusal;
    }
    unsigned slot = 0;
    size_t offset = 0;
    for (; slot < 6; ++slot) {
        const auto &range = apertures[slot];
        if (address < range.physical) continue;
        const uint64_t delta = uint64_t(address) - range.physical;
        if (delta <= range.bytes && width <= range.bytes - delta) {
            offset = size_t(delta);
            break;
        }
    }
    if (slot == 6 || (write && apertures[slot].readOnly)) {
        IOLockUnlock(gate_);
        return FHR_NOT_AVAILABLE; // GCC never reaches guard or write primitive.
    }
    s.accessBusy = true; // Mutation reentry refuses; no gate spans callouts.
    s.result.lastAccessGuardReturned = false;
    s.result.lastAccessPrimitiveReturned = false;
    s.result.lastAccessObserverReturned = false;
    auto *descriptor = slot < 4 ? s.resources[slot] : s.platformResources[slot - 4];
    const uintptr_t target = s.virtualBase[slot] + offset;
    IOLockUnlock(gate_);

    const int permission = s.guard.admitAccess(s.guard.cookie, *descriptor,
        address, width, write, write ? value : 0);
    IOLockLock(gate_);
    s.result.lastAccessGuardReturned = true;
    s.result.lastAccessGuardStatus = permission;
    IOLockUnlock(gate_);
    int status = permission;
    if(!status && !providerClaimsHeld())status=FHR_NOT_AVAILABLE;
    if (!status) {
        // Real ordered native primitives. No fault-catching or device errno
        // is invented; a CPU/MMIO fault is not a successful returned read.
        orderedIo();
        if (width == 4) {
            auto *reg = reinterpret_cast<volatile uint32_t *>(target);
            if (write) *reg = uint32_t(value);
            else value = *reg;
        } else {
            auto *reg = reinterpret_cast<volatile uint64_t *>(target);
            if (write) *reg = value;
            else value = *reg;
        }
        orderedIo();
        // Commit this observation before entering foreign code. If it does
        // not return, the actual primitive still returned; observer success
        // remains unknown. No gate spans this actual code-owner callback.
        IOLockLock(gate_);
        s.result.lastAccessPrimitiveReturned = true;
        IOLockUnlock(gate_);
        status = s.guard.observeAccess(s.guard.cookie, *descriptor,
                                       address, width, write, value);
        IOLockLock(gate_);
        s.result.lastAccessObserverStatus = status;
        s.result.lastAccessObserverReturned = true;
        IOLockUnlock(gate_);
        if(!status && !providerClaimsHeld())status=FHR_NOT_AVAILABLE;
    }
    IOLockLock(gate_);
    s.accessBusy = false;
    IOLockUnlock(gate_);
    // Read32/read64 publish output only after this genuine returned status is
    // zero. Post-access refusal does not imply the primitive did not occur.
    return status;
}

IOReturn ZornGen7RegisterMaps26::haltGpuBusForSmmuTableUpdate()
{
    if(!storage_ || !gate_ || !nativeContext())return kIOReturnNotReady;
    auto &s=*storage_;
    IOLockLock(gate_);
    auto &r=s.gpuBusStop;
    // A completed halt/release pair may be acquired again for a later
    // serialized SMMU page-table transaction. Failed or uncertain leases are
    // terminal and cannot be recycled.
    if((r.attempted && r.phase!=GpuBusStopPhase::Released) || !s.result.mapsReady || s.nativeCpuMappings ||
       !s.guard.admitAccess || !s.guard.observeAccess){
        IOLockUnlock(gate_);return kIOReturnNotReady;
    }
    if(r.phase==GpuBusStopPhase::Released)r={};
    r.attempted=true;r.phase=GpuBusStopPhase::WaitingForGmuIdle;
    IOLockUnlock(gate_);

    auto update=[&](auto fn){IOLockLock(gate_);fn(s.gpuBusStop);IOLockUnlock(gate_);};
    auto fail=[&](IOReturn raw){update([](GpuBusStopResult &v){v.phase=GpuBusStopPhase::Failed;});return raw;};
    auto readWord=[&](uint32_t word,uint32_t &value,int &raw){
        uint64_t wide=0;raw=access(gpuRegisterAddress(word),4,false,wide);
        if(!raw)value=uint32_t(wide);return raw?kIOReturnNotPermitted:kIOReturnSuccess;
    };
    auto writeWord=[&](uint32_t word,uint32_t value,int &raw){
        uint64_t wide=value;raw=access(gpuRegisterAddress(word),4,true,wide);
        return raw?kIOReturnNotPermitted:kIOReturnSuccess;
    };

    bool idle=false;
    for(unsigned i=0;i<kGpuStopPollBudget;++i){
        uint32_t status=0;int raw=0;const auto io=readWord(kGmuBusyStatusWord,status,raw);
        update([&](GpuBusStopResult &v){v.idlePolls=i+1;v.idleReadRaw=raw;v.busyStatus=status;});
        if(io)return fail(io);
        if((status&kGmuIdlePollMask)==0){idle=true;break;}
        if(i+1<kGpuStopPollBudget)IODelay(kGpuStopPollDelayUs);
    }
    if(!idle){
        uint32_t status2=0;int raw=0;readWord(kGmuBusyStatus2Word,status2,raw);
        update([&](GpuBusStopResult &v){v.status2ReadAttempted=true;v.status2ReadRaw=raw;v.busyStatus2=status2;});
        return fail(kIOReturnTimeout);
    }
    update([](GpuBusStopResult &v){v.phase=GpuBusStopPhase::GmuIdle;});

    update([](GpuBusStopResult &v){v.phase=GpuBusStopPhase::ClientHaltRequested;v.clientHaltWriteAttempted=true;});
    int raw=0;auto io=writeWord(kGbifHaltWord,kGbifClientHalt,raw);
    update([&](GpuBusStopResult &v){v.clientHaltWriteRaw=raw;v.clientHaltWriteReturned=true;});
    if(io)return fail(io);
    bool clientAcked=false;
    for(unsigned i=0;i<kGpuStopPollBudget;++i){
        uint32_t ack=0;int readRaw=0;io=readWord(kGbifHaltAckWord,ack,readRaw);
        update([&](GpuBusStopResult &v){v.clientAckPolls=i+1;v.clientAckReadAttempted=true;v.clientAckReadRaw=readRaw;v.clientAck=ack;});
        if(io)return fail(io);
        if((ack&kGbifClientHalt)==kGbifClientHalt){clientAcked=true;break;}
        if(i+1<kGpuStopPollBudget)IODelay(kGpuStopPollDelayUs);
    }
    if(!clientAcked)return fail(kIOReturnTimeout);
    update([](GpuBusStopResult &v){v.phase=GpuBusStopPhase::ClientHalted;});

    update([](GpuBusStopResult &v){v.phase=GpuBusStopPhase::ArbHaltRequested;v.arbHaltWriteAttempted=true;});
    io=writeWord(kGbifHaltWord,kGbifArbHalt,raw);
    update([&](GpuBusStopResult &v){v.arbHaltWriteRaw=raw;v.arbHaltWriteReturned=true;});
    if(io)return fail(io);
    bool arbAcked=false;
    for(unsigned i=0;i<kGpuStopPollBudget;++i){
        uint32_t ack=0;int readRaw=0;io=readWord(kGbifHaltAckWord,ack,readRaw);
        update([&](GpuBusStopResult &v){v.arbAckPolls=i+1;v.arbAckReadAttempted=true;v.arbAckReadRaw=readRaw;v.arbAck=ack;});
        if(io)return fail(io);
        if((ack&kGbifArbHalt)==kGbifArbHalt){arbAcked=true;break;}
        if(i+1<kGpuStopPollBudget)IODelay(kGpuStopPollDelayUs);
    }
    if(!arbAcked)return fail(kIOReturnTimeout);
    update([](GpuBusStopResult &v){v.phase=GpuBusStopPhase::Halted;});
    return kIOReturnSuccess;
}

IOReturn ZornGen7RegisterMaps26::releaseGpuBusAfterSmmuTableUpdate()
{
    if(!storage_ || !gate_ || !nativeContext())return kIOReturnNotReady;
    auto &s=*storage_;
    IOLockLock(gate_);
    auto &r=s.gpuBusStop;
    if(!r.attempted || r.phase!=GpuBusStopPhase::Halted || !s.result.mapsReady ||
       s.nativeCpuMappings || !s.guard.admitAccess || !s.guard.observeAccess){
        IOLockUnlock(gate_);return kIOReturnNotReady;
    }
    r.phase=GpuBusStopPhase::ReleaseIdleCheck;
    IOLockUnlock(gate_);
    auto update=[&](auto fn){IOLockLock(gate_);fn(s.gpuBusStop);IOLockUnlock(gate_);};
    auto readWord=[&](uint32_t word,uint32_t &value,int &raw){
        uint64_t wide=0;raw=access(gpuRegisterAddress(word),4,false,wide);
        if(!raw)value=uint32_t(wide);return raw?kIOReturnNotPermitted:kIOReturnSuccess;
    };
    auto writeWord=[&](uint32_t word,uint32_t value,int &raw){
        uint64_t wide=value;raw=access(gpuRegisterAddress(word),4,true,wide);
        return raw?kIOReturnNotPermitted:kIOReturnSuccess;
    };
    bool idle=false;
    for(unsigned i=0;i<kGpuStopPollBudget;++i){
        uint32_t status=0;int raw=0;const auto io=readWord(kGmuBusyStatusWord,status,raw);
        update([&](GpuBusStopResult &v){v.releaseIdlePolls=i+1;v.releaseIdleReadAttempted=true;v.releaseIdleReadRaw=raw;v.releaseBusyStatus=status;});
        if(io){update([](GpuBusStopResult &v){v.phase=GpuBusStopPhase::Failed;});return io;}
        if((status&kGmuIdlePollMask)==0){idle=true;break;}
        if(i+1<kGpuStopPollBudget)IODelay(kGpuStopPollDelayUs);
    }
    if(!idle){update([](GpuBusStopResult &v){v.phase=GpuBusStopPhase::Failed;});return kIOReturnTimeout;}

    update([](GpuBusStopResult &v){v.phase=GpuBusStopPhase::ReleaseRequested;v.releaseWriteAttempted=true;});
    int raw=0;auto releaseRaw=writeWord(kGbifHaltWord,0,raw);
    update([&](GpuBusStopResult &v){v.releaseWriteRaw=raw;v.releaseWriteReturned=true;});
    bool released=!releaseRaw;
    bool ackClear=false;
    IOReturn releaseFailure=releaseRaw;
    if(released){
        for(unsigned i=0;i<kGpuStopPollBudget;++i){
            uint32_t ack=0;int readRaw=0;const auto io=readWord(kGbifHaltAckWord,ack,readRaw);
            update([&](GpuBusStopResult &v){v.releaseAckPolls=i+1;v.releaseAckReadAttempted=true;v.releaseAckReadRaw=readRaw;v.releaseAck=ack;});
            if(io){released=false;releaseFailure=io;break;}
            if((ack&(kGbifClientHalt|kGbifArbHalt))==0){ackClear=true;break;}
            if(i+1<kGpuStopPollBudget)IODelay(kGpuStopPollDelayUs);
        }
        if(!ackClear){released=false;if(!releaseFailure)releaseFailure=kIOReturnTimeout;}
    }
    if(released){update([](GpuBusStopResult &v){v.phase=GpuBusStopPhase::Released;});return kIOReturnSuccess;}

    // A clear write or its observer may have completed before an error was
    // reported. Reassert arbitration halt and verify it before returning.
    update([](GpuBusStopResult &v){v.restoreHaltWriteAttempted=true;});
    const auto restoreRaw=writeWord(kGbifHaltWord,kGbifArbHalt,raw);
    update([&](GpuBusStopResult &v){v.restoreHaltWriteRaw=raw;v.restoreHaltWriteReturned=true;});
    bool restored=!restoreRaw;
    if(restored){
        bool acked=false;
        for(unsigned i=0;i<kGpuStopPollBudget;++i){
            uint32_t ack=0;int readRaw=0;const auto io=readWord(kGbifHaltAckWord,ack,readRaw);
            update([&](GpuBusStopResult &v){v.restoreAckPolls=i+1;v.restoreAckReadAttempted=true;v.restoreAckReadRaw=readRaw;v.restoreAck=ack;});
            if(io){restored=false;break;}
            if((ack&kGbifArbHalt)==kGbifArbHalt){acked=true;break;}
            if(i+1<kGpuStopPollBudget)IODelay(kGpuStopPollDelayUs);
        }
        if(!acked)restored=false;
    }
    update([&](GpuBusStopResult &v){v.phase=restored?GpuBusStopPhase::Halted:GpuBusStopPhase::Failed;});
    return releaseFailure?releaseFailure:kIOReturnNotReady;
}

bool ZornGen7RegisterMaps26::bindCallbackOwner(OSObject &borrower,ZornGen7InactiveOwner26 &parent,
    IOService *const (&providers)[2],IOMemoryDescriptor *const (&resources)[4])
{
    if(!storage_ || !gate_ || !nativeContext() || parent_!=&parent)return false;
    auto &s=*storage_;IOLockLock(gate_);
    auto finish=[&](bool r){IOLockUnlock(gate_);return r;};
    if(!s.result.borrowAcquired || s.callbackBorrower)return finish(false);
    for(size_t i=0;i<2;++i)if(providers[i]!=s.providers[i])return finish(false);
    for(size_t i=0;i<4;++i)if(resources[i]!=s.resources[i])return finish(false);
    borrower.retain();s.callbackBorrower=&borrower;return finish(true);
}
IOReturn ZornGen7RegisterMaps26::bindAtomicSmmuSubview(IOService &controller,IOMemoryDescriptor &descriptor,
    size_t offset,size_t bytes,OSObject &guardOwner,const ZornGen7AtomicSmmuGuard26 &guard,
    ZornGen7AtomicSmmuIo26 *&out,ArmSmmu4KIo &io)
{
    if(!storage_ || !gate_ || !nativeContext() || out)return kIOReturnBadArgument;
    auto &s=*storage_;IOLockLock(gate_);
    const bool ready=s.result.mapsReady && s.platformProviders[0]==&controller &&
        s.platformResources[0]==&descriptor && offset<=apertures[4].bytes &&
        bytes && bytes<=apertures[4].bytes-offset && !(offset&7u);
    const uintptr_t view=ready?s.virtualBase[4]+offset:0;
    IOLockUnlock(gate_);if(!ready)return kIOReturnNotReady;
    // Frozen real mapping and real descriptor only; offset/extent do not
    // grant a bank, ASID, stream, security or normal-stop lease.
    const auto raw=ZornGen7AtomicSmmuIo26::create(*this,guardOwner,descriptor,
        reinterpret_cast<volatile unsigned char *>(view),uint32_t(apertures[4].physical+offset),bytes,guard,out);
    if(raw!=kIOReturnSuccess)return raw;
    return out->bind(io)?kIOReturnSuccess:kIOReturnNotReady;
}
bool ZornGen7RegisterMaps26::bindSmmuIo(OSObject &borrower,IOService &controller,
    IOMemoryDescriptor &descriptor,ArmSmmu4KIo &out)
{
    if(!storage_ || !gate_ || !nativeContext() || out.cookie || out.register_bytes ||
       out.read32 || out.read64 || out.write32 || out.write64 || out.barrier)return false;
    auto &s=*storage_;IOLockLock(gate_);
    if(!s.result.mapsReady || s.smmuBorrower || s.platformProviders[0]!=&controller ||
       s.platformResources[0]!=&descriptor) {IOLockUnlock(gate_);return false;}
    borrower.retain();s.smmuBorrower=&borrower;
    out={this,apertures[4].bytes,smmuRead32,smmuRead64,smmuWrite32,smmuWrite64,smmuBarrier};
    IOLockUnlock(gate_);return true;
}
bool ZornGen7RegisterMaps26::bindNativeSmmuProbeIo(OSObject &borrower,IOService &controller,
    IOMemoryDescriptor &descriptor,ZornGen7SmmuRuntimePm26 &pm,IORecursiveLock &startup,ArmSmmu4KIo &out)
{
    if(!storage_ || !gate_ || !nativeContext() || !providerClaimsHeld() ||
       !pm.nativeHeldFor(controller,startup) || out.cookie || out.register_bytes ||
       out.read32 || out.read64 || out.write32 || out.write64 || out.barrier)return false;
    auto &s=*storage_;IOLockLock(gate_);
    const bool guarded = s.guard.admitAccess && s.guard.observeAccess;
    if((!s.nativeCpuMappings && !guarded) || !s.result.mapsReady || s.accessBusy || s.nativeProbePm ||
       s.smmuBorrower!=&borrower || s.platformProviders[0]!=&controller ||
       s.platformResources[0]!=&descriptor || !s.maps[4] || !s.virtualBase[4]){
        IOLockUnlock(gate_);return false;
    }
    // Reuse the existing cache-inhibited map. This interface has only a
    // read32 callback, with a fixed allowlist for each mapping mode.
    pm.retain();s.nativeProbePm=&pm;s.nativeProbeController=&controller;
    s.nativeProbeDescriptor=&descriptor;s.nativeProbeGate=&startup;
    out={this,apertures[4].bytes,nativeSmmuProbeRead32,nullptr,nullptr,nullptr,nullptr};
    IOLockUnlock(gate_);return true;
}
int ZornGen7RegisterMaps26::nativeSmmuProbeRead32(void *cookie,size_t at,uint32_t *out)
{
    if (!cookie || !out || (reinterpret_cast<uintptr_t>(out) & 3u) || (at & 3u))
        return FHR_ARGUMENT;
    auto *owner=static_cast<ZornGen7RegisterMaps26 *>(cookie);
    if(!owner->storage_ || !owner->gate_ || !nativeContext() || !owner->providerClaimsHeld())return FHR_NOT_AVAILABLE;
    auto &s=*owner->storage_;
    if(!s.nativeProbePm || !s.nativeProbeController || !s.nativeProbeGate ||
       !s.nativeProbePm->nativeHeldFor(*s.nativeProbeController,*s.nativeProbeGate))return FHR_NOT_AVAILABLE;
    const bool identification = at == 0x20u || at == 0x24u || at == 0x28u;
    const bool guarded = s.guard.admitAccess && s.guard.observeAccess;
    // Exact read set used by the native reservation path for 24 streams
    // and 22 context banks. Reservation checks the observed geometry first.
    const bool reservation = at == 0 || at == 0x48u || at == 0x74u ||
        (at >= 0x800u && at < 0x800u + 24u * 4u) ||
        (at >= 0xc00u && at < 0xc00u + 24u * 4u) ||
        (at >= 0x1000u && at < 0x1000u + 22u * 4u) ||
        (at >= 0x1800u && at < 0x1800u + 22u * 4u) ||
        (at >= 0x20000u && at < 0x20000u + 22u * 0x1000u &&
         (at - 0x20000u) % 0x1000u == 0);
    if (!identification && !(guarded && reservation)) return FHR_ARGUMENT;
    // The guarded path uses the same admitted and observed primitive as
    // other guarded reads. The offset and held-PM checks above apply to both paths.
    if (guarded) {
        uint64_t value = 0;
        const int raw = owner->access(static_cast<uint32_t>(apertures[4].physical + at),
                                      4, false, value);
        if (raw) return raw;
        if (!owner->providerClaimsHeld() ||
            !s.nativeProbePm->nativeHeldFor(*s.nativeProbeController, *s.nativeProbeGate))
            return FHR_NOT_AVAILABLE;
        *out = static_cast<uint32_t>(value);
        return 0;
    }
    IOLockLock(owner->gate_);
    if(!s.result.mapsReady || s.accessBusy || !s.nativeCpuMappings ||
       s.platformProviders[0]!=s.nativeProbeController || s.platformResources[0]!=s.nativeProbeDescriptor ||
       !s.maps[4] || at>apertures[4].bytes || 4u>apertures[4].bytes-at){
        IOLockUnlock(owner->gate_);return FHR_NOT_AVAILABLE;
    }
    s.accessBusy=true;s.result.lastAccessGuardReturned=false;
    s.result.lastAccessObserverReturned=false;s.result.lastAccessPrimitiveReturned=false;
    const uintptr_t address=s.virtualBase[4]+at;IOLockUnlock(owner->gate_);
    orderedIo();const uint32_t value=*reinterpret_cast<volatile uint32_t *>(address);orderedIo();
    IOLockLock(owner->gate_);s.result.lastAccessPrimitiveReturned=true;s.accessBusy=false;IOLockUnlock(owner->gate_);
    if(!owner->providerClaimsHeld() || !s.nativeProbePm->nativeHeldFor(*s.nativeProbeController,*s.nativeProbeGate))return FHR_NOT_AVAILABLE;
    *out=value;return 0; // Actual returned read;no external guard/observer result invented.
}
IOReturn ZornGen7RegisterMaps26::probeNativeSmmuConfiguration(IOService &controller,
    IORecursiveLock &startup,ZornGen7NativeSmmuIrqResult26 &out)
{
    if(!storage_ || !gate_ || !nativeContext() || !ml_get_interrupts_enabled() ||
       !IORecursiveLockHaveLock(&startup) || !providerClaimsHeld())return kIOReturnNotReady;
    auto &s=*storage_;
    if(!s.nativeProbePm || s.nativeProbeController!=&controller || s.nativeProbeGate!=&startup ||
       !s.nativeProbePm->nativeHeldFor(controller,startup))return kIOReturnNotReady;
    IOLockLock(gate_);
    const bool guarded = s.guard.admitMap && s.guard.admitAccess && s.guard.observeAccess;
    if((!s.nativeCpuMappings && !guarded) || !s.result.mapsReady || !s.result.cxTimerSeedWritesReturned || s.accessBusy ||
       s.nativeSmmuCfgAttempted || s.platformProviders[0]!=&controller ||
       s.platformResources[0]!=s.nativeProbeDescriptor || !s.maps[4] || !s.virtualBase[4]){
        IOLockUnlock(gate_);return kIOReturnNotReady;
    }
    s.nativeSmmuCfgAttempted=true;s.accessBusy=true;
    // Actual K80 qsmmuv500_adreno_impl.cfg_probe: only the nonsecure sACR
    // cache-lock bit. Preserve every other observed bit. This does not reset
    // a context/stream,clear a fault,enable translation,or acquire secure access.
    auto *acr=reinterpret_cast<volatile uint32_t *>(s.virtualBase[4]+0x10u);
    orderedIo();out.cfg_before=*acr;orderedIo();out.cfg_before_returned=true;
    *acr=out.cfg_before&~(UINT32_C(1)<<26);orderedIo();out.cfg_write_returned=true;
    out.cfg_after=*acr;orderedIo();out.cfg_after_returned=true;
    s.accessBusy=false;IOLockUnlock(gate_);
    if(!providerClaimsHeld() || !s.nativeProbePm->nativeHeldFor(controller,startup))return kIOReturnNotReady;
    // Linux warns when secure SACR denies the clear. Darwin candidate stops
    // this startup attempt instead of claiming successful configuration.
    return (out.cfg_after&(UINT32_C(1)<<26))?kIOReturnNotReady:kIOReturnSuccess;
}
bool ZornGen7RegisterMaps26::bindNativeGlobalSmmuFaultIo(IOService &controller,
    IORecursiveLock &startup,ArmSmmu4KIo &out)
{
    if(!storage_ || !gate_ || !nativeContext() || !IORecursiveLockHaveLock(&startup) || !providerClaimsHeld() ||
       out.cookie || out.read32 || out.read64 || out.write32 || out.write64 || out.barrier || out.register_bytes)return false;
    auto &s=*storage_;
    if(!s.nativeProbePm || s.nativeProbeController!=&controller || s.nativeProbeGate!=&startup ||
       !s.nativeProbePm->nativeHeldFor(controller,startup))return false;
    IOLockLock(gate_);
    const bool guarded = s.guard.admitMap && s.guard.admitAccess && s.guard.observeAccess;
    if((!s.nativeCpuMappings && !guarded) || !s.result.mapsReady || !s.result.cxTimerSeedWritesReturned || s.accessBusy ||
       s.platformProviders[0]!=&controller || s.platformResources[0]!=s.nativeProbeDescriptor ||
       !s.maps[4] || !s.virtualBase[4] || s.nativeGlobalFaultIoBound){IOLockUnlock(gate_);return false;}
    // Same actual PM/reference/map owner survives the handler. Only global
    // GFSR/GFSYNR reads are exposed;no sleeping gate/API is called in IRQ.
    __atomic_store_n(&s.nativeGlobalFaultIoBound,1u,__ATOMIC_RELEASE);
    out={this,apertures[4].bytes,nativeGlobalSmmuFaultRead32,nullptr,nullptr,nullptr,nullptr};
    IOLockUnlock(gate_);return true;
}
int ZornGen7RegisterMaps26::nativeGlobalSmmuFaultRead32(void *cookie,size_t at,uint32_t *out)
{
    if(!cookie || !out || (reinterpret_cast<uintptr_t>(out)&3u) ||
       (at!=0x48u && at!=0x50u && at!=0x54u && at!=0x58u))return FHR_ARGUMENT;
    auto *owner=static_cast<ZornGen7RegisterMaps26 *>(cookie);if(!owner->storage_)return FHR_NOT_AVAILABLE;
    auto &s=*owner->storage_;
    if(!__atomic_load_n(&s.nativeGlobalFaultIoBound,__ATOMIC_ACQUIRE))return FHR_NOT_AVAILABLE;
    orderedIo();const uint32_t actual=*reinterpret_cast<volatile uint32_t *>(s.virtualBase[4]+at);orderedIo();
    *out=actual;return 0; // Actual readonly primitive,not a fabricated guard/observer result.
}
bool ZornGen7RegisterMaps26::bindNativeSmmuControlIo(IOService &controller,IORecursiveLock &startup,ArmSmmu4KIo &out)
{
    if(!storage_ || !gate_ || !nativeContext() || !ml_get_interrupts_enabled() ||
       !IORecursiveLockHaveLock(&startup) || !providerClaimsHeld() || out.cookie || out.register_bytes ||
       out.read32 || out.write32 || out.read64 || out.write64 || out.barrier)return false;
    auto &s=*storage_;
    if(!s.nativeProbePm || s.nativeProbeController!=&controller || s.nativeProbeGate!=&startup ||
       !s.nativeProbePm->nativeHeldFor(controller,startup))return false;
    IOLockLock(gate_);
    const bool guarded = s.guard.admitMap && s.guard.admitAccess && s.guard.observeAccess;
    if(s.nativeSmmuControlBound || !s.nativeSmmuCfgAttempted || !s.nativeGlobalFaultIoBound ||
       (!s.nativeCpuMappings && !guarded) || !s.result.mapsReady || s.accessBusy || !s.maps[4] || !s.virtualBase[4] ||
       s.platformProviders[0]!=&controller || s.platformResources[0]!=s.nativeProbeDescriptor){IOLockUnlock(gate_);return false;}
    s.nativeSmmuControlBound=true;
    out={this,apertures[4].bytes,nativeSmmuControlRead32,nullptr,nativeSmmuControlWrite32,nullptr,nativeSmmuControlBarrier};
    IOLockUnlock(gate_);return true;
}
int ZornGen7RegisterMaps26::nativeSmmuControlAccess(size_t at,bool write,uint32_t &value)
{
    if(!storage_ || !gate_ || !nativeContext() || !ml_get_interrupts_enabled() || !providerClaimsHeld())return FHR_NOT_AVAILABLE;
    auto &s=*storage_;
    if(!s.nativeProbeGate || !IORecursiveLockHaveLock(s.nativeProbeGate) || !s.nativeProbeController || !s.nativeProbePm ||
       !s.nativeProbePm->nativeHeldFor(*s.nativeProbeController,*s.nativeProbeGate))return FHR_NOT_AVAILABLE;
    if(write ? (at!=0 && at!=0x70u) : (at!=0 && at!=0x48u && at!=0x74u))return FHR_ARGUMENT;
    IOLockLock(gate_);
    const bool guarded = s.guard.admitMap && s.guard.admitAccess && s.guard.observeAccess;
    if(!s.nativeSmmuControlBound || s.accessBusy || (!s.nativeCpuMappings && !guarded) || !s.result.mapsReady ||
       s.platformProviders[0]!=s.nativeProbeController || s.platformResources[0]!=s.nativeProbeDescriptor){IOLockUnlock(gate_);return FHR_NOT_AVAILABLE;}
    // Only global fault-enable bits may be added to the actual last CR0 read.
    // Never clear CLIENTPD here or touch context/stream/invalidation registers.
    if(write && ((at==0 && (!s.nativeSmmuControlCr0Read || (s.nativeSmmuControlCr0&1u) ||
       value!=(s.nativeSmmuControlCr0|UINT32_C(0x06)))) || (at==0x70u && value!=UINT32_MAX))){IOLockUnlock(gate_);return FHR_ARGUMENT;}
    s.accessBusy=true;auto *reg=reinterpret_cast<volatile uint32_t *>(s.virtualBase[4]+at);
    orderedIo();if(write)*reg=value;else value=*reg;orderedIo();
    if(!write && at==0){s.nativeSmmuControlCr0=value;s.nativeSmmuControlCr0Read=true;}
    s.accessBusy=false;IOLockUnlock(gate_);return 0; // Real returned MMIO only,no synthetic authority result.
}
int ZornGen7RegisterMaps26::nativeSmmuControlRead32(void *cookie,size_t at,uint32_t *out)
{
    if(!cookie || !out || (reinterpret_cast<uintptr_t>(out)&3u))return FHR_ARGUMENT;
    uint32_t actual=0;const int raw=static_cast<ZornGen7RegisterMaps26 *>(cookie)->nativeSmmuControlAccess(at,false,actual);
    if(!raw)*out=actual;return raw;
}
int ZornGen7RegisterMaps26::nativeSmmuControlWrite32(void *cookie,size_t at,uint32_t value)
{return cookie?static_cast<ZornGen7RegisterMaps26 *>(cookie)->nativeSmmuControlAccess(at,true,value):FHR_ARGUMENT;}
int ZornGen7RegisterMaps26::nativeSmmuControlBarrier(void *cookie)
{
    if(!cookie)return FHR_ARGUMENT;auto *owner=static_cast<ZornGen7RegisterMaps26 *>(cookie);
    if(!owner->storage_ || !nativeContext() || !owner->providerClaimsHeld())return FHR_NOT_AVAILABLE;
    auto &s=*owner->storage_;if(!s.nativeSmmuControlBound || !s.nativeProbeGate || !IORecursiveLockHaveLock(s.nativeProbeGate) ||
       !s.nativeProbePm || !s.nativeProbeController || !s.nativeProbePm->nativeHeldFor(*s.nativeProbeController,*s.nativeProbeGate))return FHR_NOT_AVAILABLE;
    orderedIo();return 0;
}
bool ZornGen7RegisterMaps26::bindNativeColdSmmuIo(IOService &controller,IORecursiveLock &startup,
    unsigned groups,unsigned banks,size_t contextBase,size_t stride,bool matching,uint32_t expectedCr0,ArmSmmu4KIo &out)
{
    // Sole private Domain caller has returned from the independent real whole-
    // controller cold grant before this bind. QTB ACK/IOService open alone
    // must never enter here. Raw geometry is the same live ID probe result.
    if(!storage_ || !gate_ || !nativeContext() || !IORecursiveLockHaveLock(&startup) ||
       !ml_get_interrupts_enabled() || !providerClaimsHeld() || out.cookie || out.register_bytes ||
       out.read32 || out.read64 || out.write32 || out.write64 || out.barrier ||
       !groups || groups>256 || !banks || banks>256 || stride<0x5cu || (stride&(stride-1u)) ||
       contextBase>apertures[4].bytes || banks>(apertures[4].bytes-contextBase)/stride)return false;
    auto &s=*storage_;
    if(!s.nativeProbePm || s.nativeProbeController!=&controller || s.nativeProbeGate!=&startup ||
       !s.nativeProbePm->nativeHeldFor(controller,startup))return false;
    IOLockLock(gate_);
    if(s.nativeColdSmmuBound || !s.nativeSmmuControlBound || s.accessBusy || !s.nativeCpuMappings ||
       !s.result.mapsReady || !s.maps[4] || !s.virtualBase[4] ||
       s.platformProviders[0]!=&controller || s.platformResources[0]!=s.nativeProbeDescriptor){IOLockUnlock(gate_);return false;}
    s.nativeColdGroups=groups;s.nativeColdBanks=banks;s.nativeColdContextBase=contextBase;s.nativeColdStride=stride;
    s.nativeColdMatching=matching;s.nativeColdExpectedCr0=expectedCr0;s.nativeColdSmmuBound=true;
    out={this,apertures[4].bytes,nativeColdSmmuRead32,nullptr,nativeColdSmmuWrite32,nullptr,nativeSmmuControlBarrier};
    IOLockUnlock(gate_);return true;
}
int ZornGen7RegisterMaps26::nativeColdSmmuAccess(size_t at,bool write,uint32_t &value)
{
    if(!storage_ || !gate_ || !nativeContext() || !ml_get_interrupts_enabled() || !providerClaimsHeld() || (at&3u) ||
       at>apertures[4].bytes || 4u>apertures[4].bytes-at)return FHR_NOT_AVAILABLE;
    auto &s=*storage_;
    if(!s.nativeColdSmmuBound || !s.nativeProbeGate || !IORecursiveLockHaveLock(s.nativeProbeGate) ||
       !s.nativeProbeController || !s.nativeProbePm || !s.nativeProbePm->nativeHeldFor(*s.nativeProbeController,*s.nativeProbeGate))return FHR_NOT_AVAILABLE;
    bool allowed=false;
    if(!write)allowed=at==0 || at==0x20 || at==0x24 || at==0x28 || at==0x48 || at==0x74;
    else allowed=(at==0 && value==s.nativeColdExpectedCr0) || at==0x48 ||
        ((at==0x68 || at==0x6c || at==0x70) && value==UINT32_MAX);
    if(at>=0xc00u && at<0xc00u+size_t(s.nativeColdGroups)*4u)allowed=!write || value==0x20300u;
    if(s.nativeColdMatching && at>=0x800u && at<0x800u+size_t(s.nativeColdGroups)*4u)allowed=!write || value==0;
    if(at>=s.nativeColdContextBase){const size_t relative=at-s.nativeColdContextBase;
        if(relative/s.nativeColdStride<s.nativeColdBanks){const size_t word=relative%s.nativeColdStride;
            if(word==0)allowed=!write || value==0;
            if(word==0x58u)allowed=!write || value==0xc00001feu;
        }
    }
    if(!allowed)return FHR_ARGUMENT;
    IOLockLock(gate_);
    if(s.accessBusy || !s.result.mapsReady || !s.nativeCpuMappings ||
       s.platformProviders[0]!=s.nativeProbeController || s.platformResources[0]!=s.nativeProbeDescriptor){IOLockUnlock(gate_);return FHR_NOT_AVAILABLE;}
    s.accessBusy=true;auto *reg=reinterpret_cast<volatile uint32_t *>(s.virtualBase[4]+at);
    orderedIo();if(write)*reg=value;else value=*reg;orderedIo();s.accessBusy=false;IOLockUnlock(gate_);return 0;
}
int ZornGen7RegisterMaps26::nativeColdSmmuRead32(void *cookie,size_t at,uint32_t *out)
{
    if(!cookie || !out || (reinterpret_cast<uintptr_t>(out)&3u))return FHR_ARGUMENT;uint32_t value=0;
    const int raw=static_cast<ZornGen7RegisterMaps26 *>(cookie)->nativeColdSmmuAccess(at,false,value);if(!raw)*out=value;return raw;
}
int ZornGen7RegisterMaps26::nativeColdSmmuWrite32(void *cookie,size_t at,uint32_t value)
{return cookie?static_cast<ZornGen7RegisterMaps26 *>(cookie)->nativeColdSmmuAccess(at,true,value):FHR_ARGUMENT;}
int ZornGen7RegisterMaps26::smmuRead32(void *cookie,size_t at,uint32_t *out)
{
    if(!cookie || !out || (reinterpret_cast<uintptr_t>(out)&3u) ||
       at>apertures[4].bytes || 4u>apertures[4].bytes-at)return FHR_ARGUMENT;
    auto *owner=static_cast<ZornGen7RegisterMaps26 *>(cookie);
    uint64_t value=0;const int raw=owner->access(uint32_t(apertures[4].physical+at),4,false,value);
    if(!raw)*out=uint32_t(value);return raw;
}
int ZornGen7RegisterMaps26::smmuRead64(void *cookie,size_t at,uint64_t *out)
{
    if(!cookie || !out || (reinterpret_cast<uintptr_t>(out)&7u) ||
       at>apertures[4].bytes || 8u>apertures[4].bytes-at)return FHR_ARGUMENT;
    auto *owner=static_cast<ZornGen7RegisterMaps26 *>(cookie);
    uint64_t value=0;const int raw=owner->access(uint32_t(apertures[4].physical+at),8,false,value);
    if(!raw)*out=value;return raw;
}
int ZornGen7RegisterMaps26::smmuWrite32(void *cookie,size_t at,uint32_t value)
{
    if(!cookie || at>apertures[4].bytes || 4u>apertures[4].bytes-at)return FHR_ARGUMENT;
    uint64_t wide=value;return static_cast<ZornGen7RegisterMaps26 *>(cookie)->access(
        uint32_t(apertures[4].physical+at),4,true,wide);
}
int ZornGen7RegisterMaps26::smmuWrite64(void *cookie,size_t at,uint64_t value)
{
    if(!cookie || at>apertures[4].bytes || 8u>apertures[4].bytes-at)return FHR_ARGUMENT;
    return static_cast<ZornGen7RegisterMaps26 *>(cookie)->access(
        uint32_t(apertures[4].physical+at),8,true,value);
}
int ZornGen7RegisterMaps26::smmuBarrier(void *cookie)
{
    if(!cookie || !nativeContext())return FHR_ARGUMENT;
    auto *owner=static_cast<ZornGen7RegisterMaps26 *>(cookie);
    if(!owner->storage_ || !owner->gate_)return FHR_NOT_AVAILABLE;
    IOLockLock(owner->gate_);const auto &s=*owner->storage_;
    const bool ready=s.result.mapsReady && s.smmuBorrower && !s.accessBusy;
    IOLockUnlock(owner->gate_);if(!ready)return FHR_NOT_AVAILABLE;
    orderedIo();return 0; // Genuine CPU ordering; no device observation/result.
}
ZornGen7RegisterMaps26::Result ZornGen7RegisterMaps26::readResult()
{
    if(!storage_ || !gate_ || !nativeContext())return {};
    IOLockLock(gate_);const auto r=storage_->result;IOLockUnlock(gate_);return r;
}
ZornGen7RegisterMaps26::GpuBusStopResult ZornGen7RegisterMaps26::readGpuBusStopResult()
{
    if(!storage_ || !gate_ || !nativeContext())return {};
    IOLockLock(gate_);const auto r=storage_->gpuBusStop;IOLockUnlock(gate_);return r;
}
void ZornGen7RegisterMaps26::free()
{
    if(pinned_)return;OSObject::free();
}


int ZornGen7RegisterMaps26::accessGmuTcmWord(uint32_t word,bool write,uint32_t &value)
{
    // Exact Gen7 regmap word windows, from gen7_reg.h. No CM3 reset release,
    // control register, other device or widened CPU mapping is admitted here.
    constexpr uint32_t itcm=0x1b400,dtcm=0x1c400,tcmWords=0x1000;
    if(!((word>=itcm && word-itcm<tcmWords) || (word>=dtcm && word-dtcm<tcmWords)))
        return FHR_ARGUMENT;
    // kgsl_regmap regions are offset from the actual GPU base resource. The
    // existing maps have already checked both genuine descriptor identities.
    // Compute the physical register and require containment in the GMU map;
    // neither this arithmetic nor containment supplies access authority.
    const uint64_t physical=apertures[0].physical+uint64_t(word)*4u;
    if(physical>UINT32_MAX || physical<apertures[1].physical ||
       physical-apertures[1].physical>apertures[1].bytes ||
       4u>apertures[1].bytes-(physical-apertures[1].physical))return FHR_ARGUMENT;
    uint64_t actual=write?value:0;
    const int raw=access(uint32_t(physical),4,write,actual);
    if(!raw && !write)value=uint32_t(actual);
    return raw;
}

IOReturn ZornGen7RegisterMaps26::initializeNativeFreshCxTimer(IOService &gpu,IOService &gmu,
    IORecursiveLock &startup,OSObject &owner,ZornGen7NativeCxTimerResult26 &out)
{
    if(!storage_ || !gate_ || !nativeContext() || !IORecursiveLockHaveLock(&startup) ||
       !providerClaimsHeld())return kIOReturnNotReady;
    auto &s=*storage_;
    if(!s.nativeProbePm || !s.nativeProbeController || s.nativeProbeGate!=&startup ||
       !s.nativeProbePm->nativeHeldFor(*s.nativeProbeController,startup))return kIOReturnNotReady;
    IOLockLock(gate_);
    const bool guarded = s.guard.admitMap && s.guard.admitAccess && s.guard.observeAccess;
    // The retained guarded carrier has the same CX and GMU descriptors.
    // The startup lock, PM hold, and reset/GX checks below cover the raw timer helper.
    if((!s.nativeCpuMappings && !guarded) || !s.result.mapsReady || !s.result.cxMapViewAccepted ||
       s.providers[0]!=&gpu || s.providers[1]!=&gmu || !s.cxDescriptor || !s.cxMap ||
       !s.cxVirtualBase || !s.maps[1] || !s.virtualBase[1] || s.accessBusy ||
       s.result.cxTimerAttempted || s.cm3Attempted || s.configAttempted){
        IOLockUnlock(gate_);return kIOReturnNotReady;
    }
    s.result.cxTimerAttempted=true;s.accessBusy=true;owner.retain();s.cxTimerAuthorityOwner=&owner;
    IOLockUnlock(gate_);
    auto finish=[&](IOReturn raw){IOLockLock(gate_);s.accessBusy=false;IOLockUnlock(gate_);return raw;};
    // Exact Gen7 source GPU words in the already retained ordinary GMU map.
    // This is CM3-held-reset/GX-off admission for timer seeding only,not a
    // SMMU bank/stream/security lease or proof of outstanding DMA drainage.
    constexpr size_t resetByte=0x1f800u*4u-(0x3d68000u-0x3d00000u);
    constexpr size_t gxByte=0x1f8d0u*4u-(0x3d68000u-0x3d00000u);
    static_assert(resetByte+4u<=0x37000u && gxByte+4u<=0x37000u,"Actual GMU descriptor extent");
    auto read=[&](size_t at){orderedIo();const uint32_t value=*reinterpret_cast<volatile uint32_t *>(s.virtualBase[1]+at);orderedIo();return value;};
    out.reset=read(resetByte);out.reset_read_returned=true;
    out.gx=read(gxByte);out.gx_read_returned=true;
    // Actual source is_on(val) is !(val & (GX_POWER_OFF|GX_CLK_OFF)).
    // Require both off bits for this fresh native cold entry;never reset or
    // halt an inherited running master to make it eligible.
    if(!(out.reset&1u) || (out.gx&3u)!=3u)return finish(kIOReturnNotReady);
    // Explicit Darwin raw-virtual variant. The selected linked ml_get_hwclock
    // is verified as BTI/ISB/MRS CNTVCT/RET with no offset or substitute API.
    // We do not claim Linux selected this domain or that firmware has ACKed it.
    s.cxTimerCounter=ZornGen7CxTimer::CounterDomain::RawVirtualWithoutWorkaround;
    s.cxTimerResult=ZornGen7CxTimer::InitializeFreshGen7_9x(
        reinterpret_cast<volatile void *>(s.cxVirtualBase),0x2000,s.cxTimerCounter);
    out.operation_returned=true;out.assessment=unsigned(s.cxTimerResult.assessment);
    out.samples=s.cxTimerResult.samples_completed;out.seed_available=s.cxTimerResult.seed_available!=0;
    IOLockLock(gate_);s.result.cxTimerOperationReturned=true;
    s.result.cxTimerSeedWritesReturned=s.cxTimerResult.assessment==ZornGen7CxTimer::Assessment::SeedWritesReturned &&
        s.cxTimerResult.samples_completed==16 && s.cxTimerResult.seed_available;
    const bool complete=s.result.cxTimerSeedWritesReturned;IOLockUnlock(gate_);
    if(!complete || !providerClaimsHeld() || !s.nativeProbePm->nativeHeldFor(*s.nativeProbeController,startup))
        return finish(kIOReturnNotReady);
    return finish(kIOReturnSuccess); // Actual writes returned;no timer readback/firmware/GPU readiness claim.
}

IOReturn ZornGen7RegisterMaps26::initializeFreshCxTimer(OSObject &owner,
    const ZornGen7CxTimerAuthority26 &authority)
{
    if(!storage_ || !gate_ || !nativeContext() || !authority.acquireFreshTimerWindow)
        return kIOReturnNotReady;
    auto &s=*storage_;IOLockLock(gate_);
    if(!s.result.mapsReady || !s.result.cxMapViewAccepted || !s.cxDescriptor ||
       !s.cxVirtualBase || s.accessBusy || s.result.cxTimerAttempted) {
        IOLockUnlock(gate_);return kIOReturnNotReady;
    }
    s.result.cxTimerAttempted=true;s.accessBusy=true;
    IOLockUnlock(gate_);
    owner.retain();s.cxTimerAuthorityOwner=&owner;s.cxTimerAuthority=authority;
    // Never hold the sleepable gate across a foreign authority callback or
    // across the raw timer helper. The retained source-specific grant must
    // cover the whole operation; normal per-access callbacks cannot do so.
    const int raw=s.cxTimerAuthority.acquireFreshTimerWindow(s.cxTimerAuthority.cookie,
        *s.providers[0],*s.cxDescriptor,0x3d9e000,0x2000,s.cxTimerCounter);
    IOLockLock(gate_);s.result.cxTimerAuthorityReturned=true;s.result.cxTimerAuthorityStatus=raw;
    IOLockUnlock(gate_);
    if(!raw && s.cxTimerCounter==ZornGen7CxTimer::CounterDomain::RawVirtualWithoutWorkaround) {
        s.cxTimerResult=ZornGen7CxTimer::InitializeFreshGen7_9x(
            reinterpret_cast<volatile void *>(s.cxVirtualBase),0x2000,s.cxTimerCounter);
        IOLockLock(gate_);s.result.cxTimerOperationReturned=true;
        s.result.cxTimerSeedWritesReturned=
            s.cxTimerResult.assessment==ZornGen7CxTimer::Assessment::SeedWritesReturned &&
            s.cxTimerResult.samples_completed==16 && s.cxTimerResult.seed_available;
        IOLockUnlock(gate_);
    }
    IOLockLock(gate_);s.accessBusy=false;const bool returned=s.result.cxTimerSeedWritesReturned;
    IOLockUnlock(gate_);return returned?kIOReturnSuccess:kIOReturnNotReady;
    // Source-returned writes only, not timer readback, global initialized bit,
    // CM3/HFI readiness or permission to retry/free after a partial failure.
}

namespace {
uint32_t nativeCm3Observation;
}
extern "C" uint32_t zorn26_native_cm3_observation()
{
    return __atomic_load_n(&nativeCm3Observation,__ATOMIC_ACQUIRE);
}
IOReturn ZornGen7RegisterMaps26::startHostCm3(OSObject &owner,
    const ZornGen7GmuStartAuthority26 &authority)
{
    if(!storage_ || !gate_ || !nativeContext() || !authority.acquireColdStartWindow)return kIOReturnNotReady;
    auto &s=*storage_;IOLockLock(gate_);
    if(!s.result.mapsReady || !s.result.cxTimerSeedWritesReturned || !s.providers[1] || !s.resources[1] ||
       !s.virtualBase[1] || s.accessBusy || s.cm3Attempted){IOLockUnlock(gate_);return kIOReturnNotReady;}
    s.cm3Attempted=true;owner.retain();s.cm3AuthorityOwner=&owner;s.cm3Authority=authority;
    IOLockUnlock(gate_);
    // Whole-operation authority covers raw native accesses including the AO
    // sample. Ordinary per-access guards can sleep and cannot substitute here.
    s.cm3AuthorityRaw=s.cm3Authority.acquireColdStartWindow(s.cm3Authority.cookie,*s.providers[1],
        *s.resources[1],apertures[1].physical,apertures[1].bytes);s.cm3AuthorityReturned=true;
    // Receiver IRQ/debug access remains possible during BOTH grant acquisition
    // and the normal poll. The real grant,not accessBusy,excludes power/reset/
    // view mutation. Never clear another concurrently active access's flag.
    if(!s.cm3AuthorityRaw){
        s.cm3Result=ZornGen7Cm3Native26::StartFresh(reinterpret_cast<volatile uint8_t *>(s.virtualBase[1]),apertures[1].bytes);
        s.cm3Returned=true;
        constexpr uint32_t resultMask=0x1ffu; // Source CM3 init result mask.
        const uint32_t observation=(1u<<31) | (unsigned(s.cm3Result.releaseAttempted)<<30) |
            (unsigned(s.cm3Result.initValueAvailable)<<29) | (unsigned(s.cm3Result.aoSampled)<<28) |
            (s.cm3Result.lastInitValue&resultMask);
        __atomic_store_n(&nativeCm3Observation,observation,__ATOMIC_RELEASE);
    }
    IOLockLock(gate_);
    const bool observed=s.cm3Returned && s.cm3Result.assessment==ZornGen7Cm3Native26::Assessment::InitializationObserved;
    IOLockUnlock(gate_);return observed?kIOReturnSuccess:kIOReturnNotReady;
    // No source fault snapshot/reset/cleanup/retry on failure. All retained.
}

namespace {
// Exact consumed source words only. FENCE_RANGE_0 is in ordinary K80 GMU:
// (0x3d00000+0x23b11*4)-0x3d68000=0x26c44. No dec0 view or widened map.
bool controlSlot(uint32_t word,unsigned &slot)
{
    constexpr uint32_t gmu[]={0x1f8f1,0x1f8f0,0x1f81c,0x1f801,0x1f985,0x1f984,
        0x23b11,0x1f82d,0x1f9d0,0x1f9ce,0x1f9cf,0x1f9cd,0x1f40f,0x1f400,0x1f401,0x1f841};
    if(word==0x3c45){slot=0;return true;}
    for(uint32_t allowed:gmu)if(word==allowed){slot=1;return true;}
    return false;
}
}
bool ZornGen7RegisterMaps26::controlWordAvailable(uint32_t word)
{
    if(!storage_ || !gate_ || !nativeContext())return false;unsigned slot=0;
    if(!controlSlot(word,slot))return false;
    const uint64_t physical=apertures[0].physical+uint64_t(word)*4u;
    const auto &view=apertures[slot];
    if(physical>UINT32_MAX-3u || physical<view.physical || physical-view.physical>view.bytes ||
       4u>view.bytes-(physical-view.physical))return false;
    IOLockLock(gate_);const bool ready=storage_->result.mapsReady && storage_->result.mapViewAccepted[slot];
    IOLockUnlock(gate_);return ready; // Shape only; access still requires its real independent grant.
}
int ZornGen7RegisterMaps26::accessGen7ControlWord(uint32_t word,bool write,uint32_t &value)
{
    if(!controlWordAvailable(word))return FHR_NOT_AVAILABLE;
    const uint64_t physical=apertures[0].physical+uint64_t(word)*4u;
    uint64_t actual=value;const int raw=access(uint32_t(physical),4,write,actual);
    if(!raw && !write)value=uint32_t(actual);return raw;
}
bool ZornGen7RegisterMaps26::configValid(void *cookie,uint32_t word)
{return cookie && static_cast<ZornGen7RegisterMaps26 *>(cookie)->controlWordAvailable(word);}
int ZornGen7RegisterMaps26::configRead(void *cookie,uint32_t word,uint32_t *value)
{
    if(!cookie || !value)return FHR_ARGUMENT;
    uint32_t actual=0;const int raw=static_cast<ZornGen7RegisterMaps26 *>(cookie)->accessGen7ControlWord(word,false,actual);
    if(!raw)*value=actual;return raw;
}
int ZornGen7RegisterMaps26::configWrite(void *cookie,uint32_t word,uint32_t value)
{return cookie?static_cast<ZornGen7RegisterMaps26 *>(cookie)->accessGen7ControlWord(word,true,value):FHR_ARGUMENT;}
int ZornGen7RegisterMaps26::configClear(void *cookie)
{
    if(!cookie)return FHR_ARGUMENT;auto *owner=static_cast<ZornGen7RegisterMaps26 *>(cookie);
    if(!owner->storage_ || !owner->gate_ || !nativeContext())return FHR_NOT_AVAILABLE;
    auto &s=*owner->storage_;IOLockLock(owner->gate_);
    const bool active=s.configActive && s.configFaultOwner && s.configClearFault;
    IOLockUnlock(owner->gate_);if(!active)return FHR_NOT_AVAILABLE;
    return s.configClearFault(*s.configFaultOwner); // Required real GMU IRQ owner, never a local stand-in.
}
ZornGen7RegisterConfig::CheckedResult ZornGen7RegisterMaps26::configureGen7ControlRegisters(
    const ZornGen7RegisterConfig::Parameters &parameters,OSObject &faultOwner,int (*clear)(OSObject &))
{
    if(!storage_ || !gate_ || !nativeContext() || !clear)return {};
    auto &s=*storage_;IOLockLock(gate_);
    if(!s.result.mapsReady || s.configAttempted){auto result=s.configResult;IOLockUnlock(gate_);return result;}
    s.configAttempted=true;s.configActive=true;IOLockUnlock(gate_);
    faultOwner.retain();s.configFaultOwner=&faultOwner;s.configClearFault=clear;
    const ZornGen7RegisterConfig::CheckedAccess io{this,configValid,configRead,configWrite,configClear};
    const auto result=ZornGen7RegisterConfig::ConfigureChecked(parameters,io);
    IOLockLock(gate_);s.configResult=result;s.configActive=false;IOLockUnlock(gate_);return result;
    // No returned register value is an ACK. Partial stores and real fault-state
    // owner stay retained; this private backend has no qualified startup caller
    // until real HFI/log inputs and GMU IRQ state are connected.
}

int ZornGen7RegisterMaps26::accessGmuIrqWord(uint32_t word,bool write,uint32_t &value)
{
    if(!storage_ || !gate_ || !nativeContext())return FHR_NOT_AVAILABLE;
    constexpr uint32_t allowed[]={0x1f991,0x1f992,0x1f993,0x23b04,0x23b05,0x23b06,0x23b13};
    bool known=false;for(uint32_t at:allowed)known|=at==word;if(!known)return FHR_ARGUMENT;
    const uint64_t physical=apertures[0].physical+uint64_t(word)*4u;
    if(physical>UINT32_MAX-3u || physical<apertures[1].physical ||
       physical-apertures[1].physical>apertures[1].bytes ||
       4u>apertures[1].bytes-(physical-apertures[1].physical))return FHR_ARGUMENT;
    uint64_t actual=value;const int raw=access(uint32_t(physical),4,write,actual);
    if(!raw && !write)value=uint32_t(actual);return raw;
}

int ZornGen7RegisterMaps26::accessGmuHfiWord(uint32_t word,bool write,uint32_t &value)
{
    // Exact common HFI/registered HWSCHED control-init source operations. No SYSRESET/CM3 release.
    if(!storage_ || !gate_ || !nativeContext())return FHR_NOT_AVAILABLE;
    const bool allowed=write?(word==0x1f994 || word==0x1f991 || word==0x1f986):
        (word==0x1f980 || word==0x1f992 || word==0x1f81c || word==0x1f8d0 || word==0x1f996);
    if(!allowed)return FHR_ARGUMENT;
    const uint64_t physical=apertures[0].physical+uint64_t(word)*4u;
    if(physical>UINT32_MAX-3u || physical<apertures[1].physical ||
       physical-apertures[1].physical>apertures[1].bytes ||
       4u>apertures[1].bytes-(physical-apertures[1].physical))return FHR_NOT_AVAILABLE;
    uint64_t actual=value;const int raw=access(uint32_t(physical),4,write,actual);
    if(!raw && !write)value=uint32_t(actual);return raw;
}

namespace {
uint32_t nativePdcRscObservation;
}
extern "C" uint32_t zorn26_native_pdc_rsc_observation()
{
    return __atomic_load_n(&nativePdcRscObservation,__ATOMIC_ACQUIRE);
}
IOReturn ZornGen7RegisterMaps26::loadPdcRsc(OSObject &flagsOwner,volatile uint64_t *flags)
{
    if(!storage_ || !gate_ || !nativeContext() || !flags)return kIOReturnNotReady;
    auto &s=*storage_;IOLockLock(gate_);
    if(!s.result.mapsReady || s.pdcRscAttempted || s.accessBusy){IOLockUnlock(gate_);return kIOReturnNotReady;}
    s.pdcRscAttempted=true;flagsOwner.retain();s.pdcRscFlagsOwner=&flagsOwner;IOLockUnlock(gate_);
    void *memory=IOMallocZero(sizeof(ZornGen7PdcRsc::CheckedProgram));if(!memory)return kIOReturnNoMemory;
    ZornGen7PdcRsc::CheckedInputs inputs{{this,pdcRscValid,pdcRscWrite},flags,ZornGen7PdcRsc::SourceVariant::PinnedGen7_9xNon2xRscc};
    s.pdcRscProgram=new(memory)ZornGen7PdcRsc::CheckedProgram(inputs);
    IOLockLock(gate_);s.pdcRscActive=true;IOLockUnlock(gate_);
    s.pdcRscResult=s.pdcRscProgram->run();IOLockLock(gate_);s.pdcRscActive=false;IOLockUnlock(gate_);
    using A=ZornGen7PdcRsc::CheckedAssessment;
    const auto &result=s.pdcRscResult;
    const uint32_t observed=(1u<<31) | (unsigned(result.native_return_available)<<30) |
        (unsigned(result.assessment)<<24) | (result.register_stores_returned<<16) |
        (uint32_t(result.native_return)&0xffffu);
    __atomic_store_n(&nativePdcRscObservation,observed,__ATOMIC_RELEASE);
    return (s.pdcRscResult.assessment==A::StoresReturnedAndSoftwareMarked ||
        s.pdcRscResult.assessment==A::AlreadyMarkedInActualSharedState)?kIOReturnSuccess:kIOReturnNotReady;
}
bool ZornGen7RegisterMaps26::pdcRscValid(void *cookie,ZornGen7PdcRsc::Region region,uint32_t word)
{
    if(!cookie || !nativeContext())return false;
    auto &o=*static_cast<ZornGen7RegisterMaps26 *>(cookie);if(!o.storage_ || !o.gate_)return false;
    const unsigned slot=region==ZornGen7PdcRsc::Region::Pdc?3u:2u;
    if(region!=ZornGen7PdcRsc::Region::Pdc && region!=ZornGen7PdcRsc::Region::Rscc)return false;
    IOLockLock(o.gate_);const auto &s=*o.storage_;const uint64_t at=uint64_t(word)*4u;
    const bool valid=s.pdcRscActive && s.result.mapsReady && s.virtualBase[slot] &&
        at<=apertures[slot].bytes && 4u<=apertures[slot].bytes-at;
    IOLockUnlock(o.gate_);return valid; // Extent only;actual access still requires guard+observer.
}
int ZornGen7RegisterMaps26::pdcRscWrite(void *cookie,ZornGen7PdcRsc::Region region,uint32_t word,uint32_t value)
{
    if(!pdcRscValid(cookie,region,word))return FHR_ARGUMENT;
    const unsigned slot=region==ZornGen7PdcRsc::Region::Pdc?3u:2u;
    uint64_t actual=value;return static_cast<ZornGen7RegisterMaps26 *>(cookie)->access(
        uint32_t(apertures[slot].physical+uint64_t(word)*4u),4,true,actual);
}

IOReturn ZornGen7RegisterMaps26::acquireHostGpuWindow(OSObject &owner,const ZornGen7GpuStartAuthority26 &authority)
{
    if(!storage_ || !gate_ || !nativeContext() || !ml_get_interrupts_enabled() ||
       !authority.acquireExclusiveGpuStart)return kIOReturnNotReady;
    const bool claimsBefore=providerClaimsHeld();if(!claimsBefore)return kIOReturnNotOpen;
    auto &s=*storage_;IOLockLock(gate_);
    if(!s.result.mapsReady || !s.providers[0] || !s.providers[1] || !s.resources[0] || !s.resources[1] ||
       s.gpuWindowAttempted){IOLockUnlock(gate_);return kIOReturnNotReady;}
    s.gpuWindowAttempted=true;s.gpuWindowClaimsHeldBefore=claimsBefore;
    owner.retain();s.gpuStartOwner=&owner;s.gpuStartAuthority=authority;IOLockUnlock(gate_);
    // Recheck outside the map lock immediately before entering the external
    // whole-operation grant. If it vanished,consume this one-shot attempt and
    // retain the owner because another path may have changed hardware state.
    if(!providerClaimsHeld()){
        IOLockLock(gate_);s.gpuWindowRaw=kIOReturnNotOpen;s.gpuWindowClaimsHeldAfter=false;
        s.gpuWindowReturned=true;IOLockUnlock(gate_);return kIOReturnNotOpen;
    }
    // No map gate or accessBusy flag spans the genuine whole-window grant or
    // poll. Actual IRQ/debug work can still use its serialized checked IO.
    // The external whole-window authority must not silently close or lose the
    // actual GPU/GMU provider claims while it grants this durable start epoch.
    const int raw=s.gpuStartAuthority.acquireExclusiveGpuStart(s.gpuStartAuthority.cookie,*s.providers[0],*s.resources[0],
        *s.providers[1],*s.resources[1]);
    const bool claimsAfter=providerClaimsHeld();
    const int effectiveRaw=raw?raw:(claimsAfter?0:kIOReturnNotOpen);
    IOLockLock(gate_);s.gpuWindowCallbackInvoked=true;s.gpuWindowCallbackRaw=raw;s.gpuWindowRaw=effectiveRaw;
    s.gpuWindowClaimsHeldAfter=claimsAfter;s.gpuWindowReturned=true;IOLockUnlock(gate_);
    if(raw)return kIOReturnNotPermitted;
    return claimsAfter?kIOReturnSuccess:kIOReturnNotOpen;
}

bool ZornGen7RegisterMaps26::bindHostGpuCode(ZornGen7HostGpuCode26 &owner,ZornGen7InactiveOwner26 &parent)
{
    if(!storage_ || !gate_ || !nativeContext() || parent_!=&parent)return false;
    IOLockLock(gate_);auto &s=*storage_;
    const bool ready=s.result.mapsReady && s.gpuWindowReturned && !s.gpuWindowRaw &&
        s.gpuWindowClaimsHeldBefore && s.gpuWindowClaimsHeldAfter && !s.gpuCodeOwner;
    if(ready){owner.retain();s.gpuCodeOwner=&owner;}IOLockUnlock(gate_);return ready;
}
int ZornGen7RegisterMaps26::accessHostGpuCodeWord(uint32_t address,bool write,uint32_t &value)
{
    // Exact reused hcb_run instructions only;SQE_CNTL is read-only here.
    const bool base=address==0x3d020c0 || address==0x3d020c4 || address==0x3d02dc0 || address==0x3d02dc4;
    if(!base && (address!=0x3d02020 || write))return FHR_ARGUMENT;
    if(!storage_ || !gate_ || !nativeContext())return FHR_NOT_AVAILABLE;
    IOLockLock(gate_);const auto &s=*storage_;
    const bool ready=s.result.mapsReady && s.gpuCodeOwner && s.gpuWindowReturned && !s.gpuWindowRaw &&
        s.gpuWindowClaimsHeldBefore && s.gpuWindowClaimsHeldAfter;
    IOLockUnlock(gate_);if(!ready)return FHR_NOT_AVAILABLE;
    uint64_t actual=value;const int raw=access(address,4,write,actual);if(!raw && !write)value=uint32_t(actual);return raw;
}

bool ZornGen7RegisterMaps26::bindHostGpuRegisters(ZornGen7HostGpuRegisters26 &owner,ZornGen7InactiveOwner26 &parent,IOService &gpu)
{
    if(!storage_ || !gate_ || !nativeContext() || parent_!=&parent)return false;auto &s=*storage_;IOLockLock(gate_);
    const bool ready=s.result.mapsReady && s.gpuCodeOwner && s.providers[0]==&gpu &&
        s.gpuWindowReturned && !s.gpuWindowRaw && s.gpuWindowClaimsHeldBefore &&
        s.gpuWindowClaimsHeldAfter && !s.gpuRegistersOwner;
    if(ready){owner.retain();s.gpuRegistersOwner=&owner;}IOLockUnlock(gate_);return ready;
}
IOReturn ZornGen7RegisterMaps26::acquireHostGpuRegisterWindow(OSObject &owner,const ZornGen7GpuRegisterAuthority26 &authority,
    IOMemoryDescriptor &code,const uint32_t (&scache)[2])
{
    if(!storage_ || !gate_ || !nativeContext() || !authority.acquireExclusiveGpuRegisterConfiguration)return kIOReturnNotReady;
    auto &s=*storage_;IOLockLock(gate_);
    if(!s.result.mapsReady || !s.gpuCodeOwner || !s.gpuRegistersOwner || !s.gpuWindowReturned || s.gpuWindowRaw ||
       s.gpuRegistersGrantAttempted){IOLockUnlock(gate_);return kIOReturnNotReady;}
    s.gpuRegistersGrantAttempted=true;owner.retain();s.gpuRegisterAuthorityOwner=&owner;s.gpuRegisterAuthority=authority;IOLockUnlock(gate_);
    const int raw=s.gpuRegisterAuthority.acquireExclusiveGpuRegisterConfiguration(s.gpuRegisterAuthority.cookie,
        *s.providers[0],*s.resources[0],*s.providers[1],*s.resources[1],code,scache,
        ZornGen7GpuRegisterProfile26::DirectHostNoLlccNoLpacNoPreemptUntrustedTsb);
    IOLockLock(gate_);s.gpuRegistersGrantRaw=raw;s.gpuRegistersGrantReturned=true;IOLockUnlock(gate_);
    return raw?kIOReturnNotPermitted:kIOReturnSuccess;
}
int ZornGen7RegisterMaps26::accessHostGpuRegisterWord(uint32_t at,bool write,uint32_t &value)
{
    const bool scache=at==0x3d0f004 || at==0x3d0f008;
    bool allowed=scache && !write;
    if(!write && at==0x3d02020)allowed=true;
    for(const auto &op:h7c_ops)if(op.address==at && (!write || op.kind!=3))allowed=true;
    if(!write)for(const auto &reg:h7c_power_regs)if(reg.address==at)allowed=true;
    if(!allowed || !storage_ || !gate_ || !nativeContext())return FHR_ARGUMENT;
    IOLockLock(gate_);const auto &s=*storage_;
    const bool ready=s.result.mapsReady && s.gpuRegistersOwner && s.gpuWindowReturned && !s.gpuWindowRaw &&
        ((!write && scache) || (s.gpuRegistersGrantReturned && !s.gpuRegistersGrantRaw));
    IOLockUnlock(gate_);if(!ready)return FHR_NOT_AVAILABLE;
    uint64_t actual=value;const int raw=access(at,4,write,actual);if(!raw && !write)value=uint32_t(actual);return raw;
}

bool ZornGen7RegisterMaps26::bindGpuIrq(ZornGen7GpuIrq26 &owner,ZornGen7InactiveOwner26 &parent,IOService &gpu)
{
    if(!storage_ || !gate_ || !nativeContext() || parent_!=&parent)return false;auto &s=*storage_;IOLockLock(gate_);
    const bool ready=s.result.mapsReady && s.providers[0]==&gpu && s.gpuRegistersOwner &&
        s.gpuRegistersGrantReturned && !s.gpuRegistersGrantRaw && !s.gpuIrqOwner;
    if(ready){owner.retain();s.gpuIrqOwner=&owner;}IOLockUnlock(gate_);return ready;
}
int ZornGen7RegisterMaps26::accessGpuIrqWord(uint32_t word,bool write,uint32_t &value)
{
    const bool allowed=write?(word==0x38 || word==0x37 || word==0x1f8c3):
        (word==0x201 || word==0x38 || word==0x823 || word==0x824 || word==0x23b10);
    if(!allowed || !storage_ || !gate_ || !nativeContext())return FHR_ARGUMENT;
    IOLockLock(gate_);const auto &s=*storage_;const bool ready=s.result.mapsReady && s.gpuIrqOwner &&
        s.gpuRegistersGrantReturned && !s.gpuRegistersGrantRaw;IOLockUnlock(gate_);if(!ready)return FHR_NOT_AVAILABLE;
    const uint64_t physical=apertures[0].physical+uint64_t(word)*4u;
    if(physical>UINT32_MAX-3u)return FHR_ARGUMENT;
    uint64_t actual=value;const int raw=access(uint32_t(physical),4,write,actual);if(!raw && !write)value=uint32_t(actual);return raw;
}

bool ZornGen7RegisterMaps26::bindHostRing(ZornGen7HostRing26 &owner,ZornGen7InactiveOwner26 &parent,ZornGen7GpuIrq26 &irq)
{
    if(!storage_ || !gate_ || !nativeContext() || parent_!=&parent)return false;auto &s=*storage_;IOLockLock(gate_);
    const bool ready=s.result.mapsReady && s.gpuIrqOwner==&irq && s.gpuRegistersGrantReturned && !s.gpuRegistersGrantRaw && !s.hostRingOwner;
    if(ready){owner.retain();s.hostRingOwner=&owner;}IOLockUnlock(gate_);return ready;
}
IOReturn ZornGen7RegisterMaps26::acquireHostCpWindow(OSObject &owner,const ZornGen7CpStartAuthority26 &authority,
    IOMemoryDescriptor &pool,IOMemoryDescriptor &code)
{
    if(!storage_ || !gate_ || !nativeContext() || !authority.acquireExclusiveCpInitialization)return kIOReturnNotReady;
    auto &s=*storage_;IOLockLock(gate_);
    if(!s.result.mapsReady || !s.hostRingOwner || !s.gpuIrqOwner || !s.gpuRegistersGrantReturned || s.gpuRegistersGrantRaw || s.cpGrantAttempted){IOLockUnlock(gate_);return kIOReturnNotReady;}
    s.cpGrantAttempted=true;owner.retain();s.cpAuthorityOwner=&owner;s.cpAuthority=authority;IOLockUnlock(gate_);
    const int raw=s.cpAuthority.acquireExclusiveCpInitialization(s.cpAuthority.cookie,*s.providers[0],*s.resources[0],
        *s.providers[1],*s.resources[1],pool,code,ZornGen7CpProfile26::InitialNoDmsBeforeAuthenticatedModeTransition);
    IOLockLock(gate_);s.cpGrantRaw=raw;s.cpGrantReturned=true;IOLockUnlock(gate_);return raw?kIOReturnNotPermitted:kIOReturnSuccess;
}
int ZornGen7RegisterMaps26::accessHostRingWord(uint32_t word,bool write,uint32_t &value)
{
    const bool config=word==0x800 || word==0x801 || word==0x802 || word==0x804 || word==0x805 || word==0xa98 || word==0xa99 || word==0x807 || word==0x808;
    const bool allowed=config || (!write && (word==0x806 || word==0x210 || word==0x201 || word==0x821 || word==0x830 || word==0x831 || word==0xb70 || word==0xb71 || word==0x23b0c || word==0x23b13 || word==0x980 || word==0x981));
    // Exact Gen7 CP_ALWAYS_ON_COUNTER_LO/HI are read-only on this route.
    // Existing access guard remains mandatory;this does not grant a window.
    if(!allowed || !storage_ || !gate_ || !nativeContext())return FHR_ARGUMENT;
    IOLockLock(gate_);const auto &s=*storage_;const bool ready=s.result.mapsReady && s.hostRingOwner && s.gpuIrqOwner && s.cpGrantReturned && !s.cpGrantRaw;
    IOLockUnlock(gate_);if(!ready)return FHR_NOT_AVAILABLE;
    const uint64_t physical=apertures[0].physical+uint64_t(word)*4u;if(physical>UINT32_MAX-3u)return FHR_ARGUMENT;
    uint64_t actual=value;const int raw=access(uint32_t(physical),4,write,actual);if(!raw && !write)value=uint32_t(actual);return raw;
}

IOReturn ZornGen7RegisterMaps26::acquireAuthenticatedCpBootstrap(OSObject &owner,
    const ZornGen7CpBootstrapAuthority26 &authority,IOMemoryDescriptor &pool,IOMemoryDescriptor &code,ZornGen7ZapOwner26 &zap)
{
    if(!storage_ || !gate_ || !nativeContext() || !authority.acquireAuthenticatedBootstrap)return kIOReturnNotReady;
    auto &s=*storage_;IOLockLock(gate_);
    if(!s.result.mapsReady || !s.hostRingOwner || !s.gpuIrqOwner || !s.cpGrantReturned || s.cpGrantRaw || s.bootstrapGrantAttempted){IOLockUnlock(gate_);return kIOReturnNotReady;}
    s.bootstrapGrantAttempted=true;owner.retain();s.bootstrapAuthorityOwner=&owner;s.bootstrapAuthority=authority;IOLockUnlock(gate_);
    const int raw=s.bootstrapAuthority.acquireAuthenticatedBootstrap(s.bootstrapAuthority.cookie,*s.providers[0],*s.resources[0],
        *s.providers[1],*s.resources[1],pool,code,zap);
    IOLockLock(gate_);s.bootstrapGrantRaw=raw;s.bootstrapGrantReturned=true;IOLockUnlock(gate_);return raw?kIOReturnNotPermitted:kIOReturnSuccess;
}

IOReturn ZornGen7RegisterMaps26::authorizeHostOobRelease(ZornGen7HostRing26 &ring)
{
    if(!storage_ || !gate_ || !nativeContext())return kIOReturnNotReady;auto &s=*storage_;IOLockLock(gate_);
    if(s.hostRingOwner!=&ring || !s.result.mapsReady || !s.bootstrapGrantReturned || s.bootstrapGrantRaw ||
       s.oobReleaseGrantAttempted || !s.bootstrapAuthority.authorizeSuccessfulOobRelease){IOLockUnlock(gate_);return kIOReturnNotReady;}
    s.oobReleaseGrantAttempted=true;IOLockUnlock(gate_);
    const int raw=s.bootstrapAuthority.authorizeSuccessfulOobRelease(s.bootstrapAuthority.cookie,*s.providers[0],*s.providers[1],ring);
    IOLockLock(gate_);s.oobReleaseGrantRaw=raw;s.oobReleaseGrantReturned=true;IOLockUnlock(gate_);return raw?kIOReturnNotPermitted:kIOReturnSuccess;
}

IOReturn ZornGen7RegisterMaps26::acquireKernelTaskWindow(ZornGen7HostRing26 &ring,
    const ZornGen7DirectRuntimeAuthority26 &authority,IOMemoryDescriptor &image)
{
    if(!storage_ || !gate_ || !nativeContext() || !authority.acquireKernelTask)return kIOReturnNotReady;auto &s=*storage_;IOLockLock(gate_);
    if(s.hostRingOwner!=&ring || !s.result.mapsReady || !s.bootstrapGrantReturned || s.bootstrapGrantRaw ||
       !s.oobReleaseGrantReturned || s.oobReleaseGrantRaw || s.kernelTaskGrantAttempted){IOLockUnlock(gate_);return kIOReturnNotReady;}
    s.kernelTaskGrantAttempted=true;IOLockUnlock(gate_);
    s.kernelTaskGrantRaw=authority.acquireKernelTask(authority.cookie,*s.providers[0],*s.resources[0],*s.providers[1],*s.resources[1],image);
    return s.kernelTaskGrantRaw?kIOReturnNotPermitted:kIOReturnSuccess;
}
IOReturn ZornGen7RegisterMaps26::authorizeKernelTaskRelease(ZornGen7HostRing26 &ring,
    const ZornGen7DirectRuntimeAuthority26 &authority,IOMemoryDescriptor &image)
{
    if(!storage_ || !gate_ || !nativeContext() || !authority.authorizeKernelTaskRelease)return kIOReturnNotReady;auto &s=*storage_;IOLockLock(gate_);
    if(s.hostRingOwner!=&ring || !s.kernelTaskGrantAttempted || s.kernelTaskGrantRaw || s.kernelTaskReleaseAttempted){IOLockUnlock(gate_);return kIOReturnNotReady;}
    s.kernelTaskReleaseAttempted=true;IOLockUnlock(gate_);
    s.kernelTaskReleaseRaw=authority.authorizeKernelTaskRelease(authority.cookie,*s.providers[0],image);
    return s.kernelTaskReleaseRaw?kIOReturnNotPermitted:kIOReturnSuccess;
}

IOReturn ZornGen7RegisterMaps26::acquireKernelClientWindow(ZornGen7HostRing26 &ring,
    const ZornGen7DirectRuntimeAuthority26 &authority,IOUserClient &client)
{
    if(!storage_ || !gate_ || !nativeContext() || !authority.acquireKernelClient)return kIOReturnNotReady;
    auto &s=*storage_;IOLockLock(gate_);
    const bool ready=s.hostRingOwner==&ring && s.result.mapsReady && s.kernelTaskReleaseAttempted && !s.kernelTaskReleaseRaw;
    IOLockUnlock(gate_);if(!ready)return kIOReturnNotReady;
    return authority.acquireKernelClient(authority.cookie,client,*s.providers[0],*s.resources[0],*s.providers[1],*s.resources[1]);
}

IOReturn ZornGen7RegisterMaps26::createApplicationExecution(ZornGen7HostRing26 &ring,
    IORecursiveLock &driverGate,IOUserClient &client,task_t task,OSObject &codeOwner,
    const ZornGen7AppAuthority26 &authority,ZornGen7AppExecution26 *&out)
{
    if(out || !storage_ || !gate_ || !nativeContext() || IORecursiveLockHaveLock(&driverGate))return kIOReturnNotReady;
    auto &s=*storage_;IOLockLock(gate_);
    const bool ready=s.hostRingOwner==&ring && s.result.mapsReady && s.providers[0] && s.resources[0] &&
        s.providers[1] && s.resources[1];
    IOLockUnlock(gate_);if(!ready)return kIOReturnNotReady;
    // Frozen actual references,not guessed MMIO or an inferred hardware lease.
    // The separate real application authority decides current permission.
    return ZornGen7AppExecution26::create(*this,ring,driverGate,client,task,codeOwner,authority,
        *s.providers[0],*s.resources[0],*s.providers[1],*s.resources[1],out);
}

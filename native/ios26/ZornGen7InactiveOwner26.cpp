// SPDX-License-Identifier: BSD-2-Clause-Patent
#include "ZornGen7RscStageScreen26.h"
#include "ZornGen7InactiveOwner26.h"
#include "ZornGen7RscControllerStatus26.h"
#include <pexpert/pexpert.h>
#include "ZornGen7FirmwareAssets26.h"
#include "ZornGen7RegistryNames26.h"
#include "ZornGen7PreparedRuntime26.h"
#include "ZornGen7DarwinBoardOwner.h"
#include "ZornGen7ArcNodes26.h"
#include "ZornGen7ClockNodes26.h"
#include "ZornGen7CxGdscNodes26.h"
#include "ZornGen7PlatformMmioInputs26.h"
#include "ZornGen7RegisterMaps26.h"
#include "ZornGen7NativeDtEntry26.h"
#include "ZornGen7ClockResources26.h"
#include "ZornGen7CommandDbSnapshot26.h"
#include "ZornGen7CommandDbResources26.h"
#include "ZornGen7RscRuntime26.h"
#include <IOKit/IOLib.h>
#include <machine/machine_routines.h>
#include <kern/sched_prim.h>
#include <IOKit/IOMemoryDescriptor.h>
#include <IOKit/IOKitKeys.h>
#include <IOKit/IODeviceTreeSupport.h>
#include <libkern/c++/OSArray.h>

OSDefineMetaClassAndStructors(ZornGen7InactiveOwner26, OSObject);

struct ZornGen7InactiveOwner26::Storage {
    IORecursiveLock *gate = nullptr;
    IOService *platform = nullptr;
    OSObject *foreignStorage = nullptr;
    bool pinned = false;
    bool attempted = false;
    IOService *resourceProvider[2] = {};
    OSObject *resourceProperty[2] = {};
    IOMemoryDescriptor *resources[4] = {};
    IORegistryEntry *inputNode[2] = {}, *inputParent[2] = {};
    IOPlatformDevice *platformNub[2] = {};
    IORegistryEntry *registryRoot = nullptr, *registryNode[2] = {};
    OSObject *registryResourceProperty[2] = {};
    IOService *resolvedProvider[2] = {};
    bool registryResolutionReady = false;
    IOService *gpuProviderClaimant=nullptr,*gpuProviderClaimParent=nullptr;
    bool gpuProviderClaimAttempted=false,gpuProviderClaimOpened[2]{};
    IOReturn gpuProviderClaimRaw=kIOReturnNotReady;
    bool registerGuardPrepared = false;
    struct RegisterAccess {
        IOMemoryDescriptor *descriptor = nullptr;
        uint32_t address = 0;
        unsigned width = 0;
        bool write = false;
        uint64_t value = 0;
    } pendingRegisterAccess;
    OSObject *runtimeBorrower = nullptr;
    bool firmwareSeedAttempted=false,firmwareSeedReady=false,firmwareHoldsAttempted=false;
    bool nativeGlobalIrqAttempted=false;
    ZornGen7DarwinBoardOwner *clocks = nullptr;
    ZornGen7ArcNodes26 *arcNodes = nullptr;
    bool arcNodesAttempted=false,arcNodesReady=false;
    ZornGen7ClockNodes26 *clockNodes=nullptr;bool clockNodesAttempted=false,clockNodesReady=false;
    bool gpuccPrefixAttempted=false,gpuccPrefixReady=false;
    bool gccRailsAttempted=false,gccRailsReady=false;
    bool gccPrefixAttempted=false,gccPrefixReady=false,clockGraphAttempted=false,clockGraphReady=false;
    bool clockListAttempted=false,clockListReady=false;
    bool gmuIrqAttempted=false,gmuIrqReady=false;
    bool gmuConfigAttempted=false,gmuConfigReady=false;
    bool hostTablesAttempted=false,hostTablesReady=false;
    bool hostHfiAttempted=false,hostHfiReady=false,hostIrqArmAttempted=false,hostIrqArmed=false;
    bool hostStartAttempted=false,hostFirstQueryReady=false;
    bool hostProfileAttempted=false,hostProfileReady=false,hostClockAttempted=false,hostClockReady=false,hostBwAttempted=false,hostBwReady=false,hostOobAttempted=false,hostOobReady=false,hostGpuTablesAttempted=false,hostGpuTablesReady=false,hostGpuMmuAttempted=false,hostGpuMmuReady=false,hostGpuCodeAttempted=false,hostGpuCodeReady=false,hostGpuRegistersAttempted=false,hostGpuRegistersReady=false,hostGpuIrqAttempted=false,hostGpuIrqReady=false,hostCpAttempted=false,hostCpInitIdle=false;
    bool hostZapAttempted=false,hostZapAuthenticated=false,hostBootstrapAttempted=false,hostBootstrapReady=false,hostDirectRuntimeAttempted=false,hostDirectRuntimeReady=false,hostKnownImageAttempted=false,hostKnownImageReady=false;
    bool hwschedIrqArmAttempted=false,hwschedIrqArmed=false;
    bool gmuVersionsAttempted=false,gmuVersionsReady=false;
    bool pdcRscAttempted=false,pdcRscReady=false;
    bool directHfiAttempted=false,directHfiReady=false;
    bool hwschedHfiAttempted=false,hwschedHfiReady=false;
    bool gpuIccInputsAttempted=false,gpuIccInputsReady=false;
    bool gpuIccInitialAttempted=false,gpuIccInitialReady=false,gpuIccQosAttempted=false,gpuIccQosReady=false;
    bool gpuBootstrapBwAttempted=false,gpuBootstrapBwReady=false;
    bool gmuTcmLoadedReady=false,cxSecurityAttempted=false,cxSecurityReady=false;
    bool cxTimerAttempted=false,cxTimerReady=false;
    bool gmuAhbAttempted=false,gmuAhbReady=false;
    bool coldGmuClockAttempted=false,coldGmuClockReady=false;
    bool hubMetadataAttempted=false,hubMetadataReady=false;
    bool ddrMetadataAttempted=false,ddrMetadataReady=false;
    bool coreInputsAttempted=false,coreInputsReady=false;
    bool cxGdscProbeAttempted=false,cxGdscProbeReady=false;
    ZornGen7CxGdscNodes26 *cxGdscNodes=nullptr;bool cxGdscCoreAttempted=false,cxGdscCoreReady=false;
    bool cxCompletionAttempted=false,cxCompletionReady=false;
    ZornGen7PlatformMmioInputs26 *smmuInputs=nullptr;
    IOService *smmuController=nullptr;IOMemoryDescriptor *smmuDescriptor=nullptr;
    bool smmuPowerAttempted=false,smmuPowerReady=false;
    ZornGen7RegisterMaps26 *registerMapBorrower=nullptr;
    bool registerMapsAttempted=false,registerMapsReady=false;
    bool smmuPmAttempted=false,smmuPmReady=false;
    bool clocksReady = false;
    bool clockResourcesAttempted = false;
    bool clockResourcesReady = false;
    ZornGen7ClockResources26 *clockResources = nullptr;
    IORegistryEntry *boardXoNode = nullptr;
    bool boardXoAttempted = false, boardXoReady = false;
    ZornGen7Clock::ClockCoreFactoryResult boardXoResult{};
    bool rscAttempted=false,rscReady=false;
    ZornGen7RscRuntime26 *rsc=nullptr;
    bool commandDbAttempted=false,commandDbReady=false;
    ZornGen7CommandDbSnapshot26 *commandDb=nullptr;
    ZornGen7CommandDbResources26 *commandDbResources=nullptr;
    FhgStorage graph = {};
    HoujiFullHostNativeMemory memory;
    // A real independent PRR zero backing, not an address from a probe record.
    // The retained runtime consumes one 4KiB logical page; native allocation
    // owns and zeroes the complete actual CPU page, including its padding.
    NativeAdrenoMemory zero;
    uint64_t zeroReadPar[4] = {}, zeroAliasPar[4] = {};
    Result result = {};
    static void *operator new(size_t, void *p) noexcept { return p; }
    bool zeroOwned(uint64_t cpuPage, bool nc, bool capture,
                   const HoujiFullHostNativeMemory::Span *foreign, unsigned count);
};

// Actual retained K80 fixed FDT descriptions, restricted to these four
// consumed device apertures. They are identity/extent comparisons only.
// Source: platform-base/gpu-owned/K80GpuResourceProfile.inc. No permission
// or new bus resource is constructed from these numeric descriptions.
static constexpr struct {
    uint64_t physical, bytes;
    unsigned provider;
} zornGen7RequiredMemory26[] = {
    {0x3d00000, 0x40000, 0}, // kgsl_3d0_reg_memory, actual GPU node
    {0x3d68000, 0x37000, 1}, // gmu, actual GMU node
    {0x3d50000, 0x10000, 0}, // rscc, actual GPU node
    {0xb280000, 0x10000, 1}, // gmu_pdc, actual GMU node
};
static_assert(sizeof(zornGen7RequiredMemory26) /
              sizeof(*zornGen7RequiredMemory26) == 4);

bool ZornGen7InactiveOwner26::Storage::zeroOwned(uint64_t cpuPage, bool nc,
    bool capture, const HoujiFullHostNativeMemory::Span *foreign, unsigned count)
{
    // Same native descriptor/PAR contract as the retained external PRR zero
    // producer. This is CPU ownership only; no context/stream/DMA lease.
    if ((cpuPage != 4096 && cpuPage != 16384) || !memory.prepared() ||
        !zero.backed() || zero.quarantined() || zero.imported() ||
        zero.readOnly() || zero.deviceReferences() || zero.writeCombined() != nc ||
        zero.cpuPageBytes() != cpuPage || zero.bytes() != 4096 ||
        zero.ownedBytes() != cpuPage || zero.ownedSpanCount() != 1 ||
        zero.spanCount() != 1 || !zero.descriptor() || !zero.mapping() ||
        zero.descriptor()->getLength() != cpuPage) return false;
    const auto &owned = zero.ownedSpans()[0];
    const auto &logical = zero.spans()[0];
    const uint64_t pa = owned.physical, va = (uintptr_t)zero.mapping();
    if (owned.offset || logical.offset || owned.bytes != cpuPage ||
        logical.bytes != 4096 || logical.physical != pa || !pa ||
        ((pa | va) & (cpuPage - 1)) || va > UINT64_MAX - cpuPage ||
        pa >= (UINT64_C(1) << 36) || cpuPage > (UINT64_C(1) << 36) - pa ||
        !gPhysSize || gPhysBase > UINT64_MAX - gPhysSize || pa < gPhysBase ||
        cpuPage > gPhysSize || pa - gPhysBase > gPhysSize - cpuPage) return false;
    NativeAdrenoCpuView view = {};
    if (!zero.cpuView(&view) || view.spans != zero.ownedSpans() ||
        view.count != 1 || view.bytes != cpuPage) return false;
    auto overlaps = [cpuPage](uint64_t a, uint64_t b, uint64_t bytes) {
        return a < b + bytes && b < a + cpuPage;
    };
    // begin() already validated the complete immutable foreign inventory's
    // extent arithmetic. The graph entries were verified by sealPrepared().
    for (unsigned i = 0; i < count; ++i)
        if (overlaps(pa, foreign[i].pa, foreign[i].bytes) ||
            overlaps(va, foreign[i].va, foreign[i].bytes)) return false;
    for (unsigned i = 0; i < HoujiFullHostNativeMemory::Slots; ++i) {
        const auto &entry = memory.entry(i);
        if (overlaps(pa, entry.backing.physical, entry.request.owned_bytes) ||
            overlaps(va, (uintptr_t)entry.backing.cpu, entry.request.owned_bytes))
            return false;
    }
    for (unsigned row = 0; row < cpuPage / 4096; ++row) {
        const uint64_t offset = uint64_t(row) * 4096;
        const uint64_t probe = va + offset + 0x5a;
        const uint64_t alias = phystokv(pa + offset + 0x5a);
        IOByteCount length = 0;
        uint64_t read = 0, write = 0, ar = 0, aw = 0;
        if (zero.descriptor()->getPhysicalSegment(offset, &length,
                kIOMemoryMapperNone) != pa + offset || length < 4096 || !alias ||
            !houjiFullHostAt(probe, false, &read) ||
            !houjiFullHostAt(probe, true, &write) ||
            !houjiFullHostAt(alias, false, &ar) ||
            !houjiFullHostAt(alias, true, &aw)) return false;
        if ((read & 1) || read != write || (read >> 56) != (nc ? 0x44U : 0xffU) ||
            ((read >> 7) & 3) == 1 ||
            ((read & UINT64_C(0x0000fffffffff000)) | (probe & 4095)) != pa + offset + 0x5a ||
            (ar & 1) || ar != aw || ((ar >> 56) != 0xff && (ar >> 56) != 0x44) ||
            ((ar >> 7) & 3) == 1 ||
            ((ar & UINT64_C(0x0000fffffffff000)) | (alias & 4095)) != pa + offset + 0x5a)
            return false;
        if (!capture && (read != zeroReadPar[row] || ar != zeroAliasPar[row]))
            return false;
        if (capture) { zeroReadPar[row] = read; zeroAliasPar[row] = ar; }
    }
    return true;
}

static bool zornGen7PreparationContext26()
{
    return preemption_enabled() && !ml_at_interrupt_context();
}

IOReturn ZornGen7InactiveOwner26::create(IOService &actualPlatform,
                                      ZornGen7InactiveOwner26 *&output)
{
    if (output || !zornGen7PreparationContext26()) return kIOReturnBadArgument;
    auto *owner = new ZornGen7InactiveOwner26;
    if (!owner) return kIOReturnNoMemory;
    if (!owner->init()) { owner->release(); return kIOReturnNoMemory; }
    void *memory = IOMallocZero(sizeof(Storage));
    if (!memory) { owner->release(); return kIOReturnNoMemory; }
    owner->storage_ = new(memory) Storage;
    auto &s = *owner->storage_;
    // Same existing private-owner contract: self-pin before the first real
    // platform or callback borrow. No teardown/stop claim consumes this pin.
    owner->retain();
    s.pinned = true;
    output = owner;
    actualPlatform.retain();
    s.platform = &actualPlatform;
    s.gate = IORecursiveLockAlloc();
    if (!s.gate) return kIOReturnNoMemory;
    // The same platform owns the existing native CCF/ARC clock object. This
    // constructs only its three CPU gates and private root; no clock, voltage,
    // controller mapping, HWSCHED host or hardware operation is started here.
    const IOReturn clockStatus = ZornGen7DarwinBoardOwner::create(actualPlatform, s.clocks);
    if (clockStatus != kIOReturnSuccess) return clockStatus;
    if (!s.clocks || !s.clocks->borrowCpuGates()) return kIOReturnNotReady;
    s.clocksReady = true;
    return kIOReturnSuccess;
}

ZornGen7InactiveOwner26::Result ZornGen7InactiveOwner26::prepare(
    const HoujiFullHostNativeMemory::Span *actualForeign,
    unsigned actualForeignCount, OSObject &actualForeignStorage)
{
    if (!storage_ || !storage_->gate || !zornGen7PreparationContext26()) return {};
    auto &s = *storage_;
    IORecursiveLockLock(s.gate);
    // Reentry or another call returns the actual retained result. It cannot
    // retry allocation or replace callback storage after a partial failure.
    if (s.attempted) {
        Result result = s.result;
        IORecursiveLockUnlock(s.gate);
        return result;
    }
    s.attempted = true;
    actualForeignStorage.retain();
    s.foreignStorage = &actualForeignStorage;
    auto &result = s.result;
    result.phase = Phase::CpuQuery;
    NativeAdrenoCpuState cpu = {};
    result.cpuQueryStatus = NativeAdrenoQueryCpuPages(&cpu);
    result.cpuQueryReturned = true;
    if (result.cpuQueryStatus) goto retained;
    result.cpuPageBytes = cpu.kernel_page_bytes;
    if ((cpu.kernel_page_bytes != 4096 && cpu.kernel_page_bytes != 16384) ||
        cpu.kernel_map_page_bytes != cpu.kernel_page_bytes) {
        result.phase = Phase::CpuShapeRejected;
        goto retained;
    }
    result.phase = Phase::MemoryBegin;
    if (!s.memory.begin(actualForeign, actualForeignCount)) goto retained;
    {
        // This is the actual CPU query result, not an OS-version page guess.
        // Reference graph VA/OAS/OPP assumptions remain unselected; preparation
        // of CPU bytes is not permission to install that graph on K80 hardware.
        const FhgConfig config = {FHG_ABI_VERSION,
            static_cast<uint32_t>(cpu.kernel_page_bytes), {0, 0}};
        const FhgOps ops = s.memory.callbacks();
        result.phase = Phase::GraphInit;
        result.graphStatus = fhg_init(&s.graph, sizeof(s.graph),
                                     &config, sizeof(config), &ops, sizeof(ops));
        result.graphStatusReturned = true;
        if (result.graphStatus) goto retained;
    }
    result.phase = Phase::GraphPrepare;
    result.graphStatus = ZornGen7PrepareFirmwareAssets26(s.graph, result.prepareCode);
    // The original API leaves out_code unchanged on API rejection.
    result.prepareCodeReturned = result.graphStatus == FHG_OK;
    {
        FhgSummary summary = {};
        if (fhg_summary(&s.graph, sizeof(s.graph), &summary, sizeof(summary)) == FHG_OK) {
            result.graphFailure = summary.first_failure;
            result.graphFailureValid = true;
        }
    }
    if (result.graphStatus || result.prepareCode) goto retained;
    result.phase = Phase::GraphSeal;
    if (!s.memory.sealPrepared(s.graph)) goto retained;
    result.phase = Phase::ZeroAllocate;
    // The existing graph/runtime accepts only <36bit backing. Retaining that
    // allocation restriction here is not selection of K80 hardware OAS/IOVA.
    result.zeroAllocationStatus = s.zero.allocate(4096, 36, true,
        NativeAdrenoMemory::backingBudget(4096), false);
    result.zeroAllocationReturned = true;
    if (result.zeroAllocationStatus ||
        !s.zeroOwned(cpu.kernel_page_bytes, false, true, actualForeign,
                     actualForeignCount)) goto retained;
    result.phase = Phase::ZeroCache;
    result.zeroCacheStatus = s.zero.makeWriteCombined();
    result.zeroCacheReturned = true;
    if (result.zeroCacheStatus ||
        !s.zeroOwned(cpu.kernel_page_bytes, true, true, actualForeign,
                     actualForeignCount)) goto retained;
    result.phase = Phase::ZeroVerify;
    {
        // Only the actual owned descriptor mapping is read; never its WB
        // physical-aperture alias. No caller-supplied zero image or fake PA.
        const auto *bytes = static_cast<const volatile uint8_t *>(s.zero.mapping());
        for (size_t i = 0; i < s.zero.ownedBytes(); ++i)
            if (bytes[i]) goto retained;
    }
    houjiFullHostBarrier();
    if (!s.zeroOwned(cpu.kernel_page_bytes, true, false, actualForeign,
                     actualForeignCount)) goto retained;
    result.zeroPreparedCpuOnly = true;
    result.phase = Phase::PreparedCpuOnly;
    {
        Result returned = result;
        IORecursiveLockUnlock(s.gate);
        return returned;
    }
retained:
    // This quarantine path is unchanged from the genuine native binding.
    // No successful release, hardware stop, reset or retry is synthesized.
    if (s.memory.failure().code) {
        result.nativeFailure = s.memory.failure();
        result.nativeFailureValid = true;
    }
    if (s.zero.backed()) s.zero.quarantine();
    s.memory.retainFailure();
    Result returned = result;
    IORecursiveLockUnlock(s.gate);
    return returned;
}

ZornGen7InactiveOwner26::Result ZornGen7InactiveOwner26::captureDeviceMemory(
    IOService &actualGpuProvider, IOService &actualGmuProvider)
{
    if (!storage_ || !storage_->gate || !zornGen7PreparationContext26()) return {};
    auto &s = *storage_;
    IORecursiveLockLock(s.gate);
    auto &result = s.result;
    const bool localProvidersReturned =
        result.phase == Phase::PlatformNubResources &&
        result.nubResourceReturned[0] && result.nubResourceReturned[1] &&
        !result.nubResourceStatus[0] && !result.nubResourceStatus[1] &&
        &actualGpuProvider == s.platformNub[0] &&
        &actualGmuProvider == s.platformNub[1];
    const bool registryProvidersReturned =
        result.phase == Phase::PlatformNubResources &&
        result.registryLookupAttempted && s.registryResolutionReady &&
        &actualGpuProvider == s.resolvedProvider[0] &&
        &actualGmuProvider == s.resolvedProvider[1];
    if (result.resourceCaptureAttempted ||
        (result.phase != Phase::PreparedCpuOnly && !localProvidersReturned &&
         !registryProvidersReturned)) {
        Result returned = result;
        IORecursiveLockUnlock(s.gate);
        return returned;
    }
    result.resourceCaptureAttempted = true;
    // The object was self-pinned before any borrow. Hold the genuine provider
    // and owned copyProperty reference even if the property/type/range fails.
    actualGpuProvider.retain();
    actualGmuProvider.retain();
    s.resourceProvider[0] = &actualGpuProvider;
    s.resourceProvider[1] = &actualGmuProvider;
    result.phase = Phase::ResourceProperty;
    OSArray *arrays[2] = {};
    // Actual cached K80 topology has separate GPU and GMU nodes. Do not
    // invent one aggregate provider containing both resource lists.
    for (unsigned provider = 0; provider < 2; ++provider) {
        s.resourceProperty[provider] =
            s.resourceProvider[provider]->copyProperty(gIODeviceMemoryKey);
        arrays[provider] = OSDynamicCast(OSArray, s.resourceProperty[provider]);
        if (arrays[provider]) {
            result.resourceCount[provider] = arrays[provider]->getCount();
            result.resourceCountReturned[provider] = true;
        }
    }
    if (arrays[0] && arrays[1]) {
        result.phase = Phase::ResourceDescriptor;
        for (unsigned slot = 0; slot < 4; ++slot) {
            const auto &required = zornGen7RequiredMemory26[slot];
            OSArray *array = arrays[required.provider];
            IOMemoryDescriptor *found = nullptr;
            bool ambiguous = false;
            for (unsigned index = 0;
                 index < result.resourceCount[required.provider]; ++index) {
                // IODeviceMemory::withRange delegates to withAddressRange,
                // so the genuine concrete object can be IOGeneralMemoryDescriptor.
                auto *descriptor = OSDynamicCast(IOMemoryDescriptor,
                                                array->getObject(index));
                if (!descriptor || descriptor->getLength() != required.bytes)
                    continue;
                IOByteCount contiguous = 0;
                const auto physical = descriptor->getPhysicalSegment(0,
                    &contiguous, kIOMemoryMapperNone);
                if (physical != required.physical || contiguous < required.bytes)
                    continue;
                if (found) { ambiguous = true; break; }
                found = descriptor;
            }
            if (!found || ambiguous) break;
            found->retain();
            s.resources[slot] = found;
            result.retainedResourceMask |= 1U << slot;
        }
        if (result.retainedResourceMask == 15)
            result.phase = Phase::ResourcesRetainedCpuOnly;
    }
    // This does not map, validate exclusive ownership, power up or publish.
    // The already prepared zero/graph and any acquired refs stay retained;
    // no automatic rollback, stop, retry or resource replacement is implied.
    Result returned = result;
    IORecursiveLockUnlock(s.gate);
    return returned;
}

ZornGen7InactiveOwner26::Result ZornGen7InactiveOwner26::preparePlatformProviders(
    IORegistryEntry &actualGpuNode, IORegistryEntry &actualGmuNode)
{
    return resolvePlatformProviders(actualGpuNode, actualGmuNode, false);
}

ZornGen7InactiveOwner26::Result ZornGen7InactiveOwner26::resolvePlatformProviders(
    IORegistryEntry &actualGpuNode, IORegistryEntry &actualGmuNode,
    bool allowExistingServices)
{
    if (!storage_ || !storage_->gate || !zornGen7PreparationContext26()) return {};
    auto &s = *storage_;
    IORecursiveLockLock(s.gate);
    auto &result = s.result;
    const bool actualRegistryPair = allowExistingServices &&
        result.phase == Phase::RegistryLookup &&
        result.registryLookupReturned[0] && result.registryLookupReturned[1] &&
        &actualGpuNode == s.registryNode[0] && &actualGmuNode == s.registryNode[1];
    if (result.platformNubAttempted ||
        (result.phase != Phase::PreparedCpuOnly && !actualRegistryPair)) {
        Result returned = result;
        IORecursiveLockUnlock(s.gate);
        return returned;
    }
    result.platformNubAttempted = true;
    result.phase = Phase::PlatformNubInput;
    auto *expert = OSDynamicCast(IODTPlatformExpert, s.platform);
    IORegistryEntry *nodes[2] = {&actualGpuNode, &actualGmuNode};
    IOService *existing[2] = {OSDynamicCast(IOService, nodes[0]),
                              OSDynamicCast(IOService, nodes[1])};
    if(allowExistingServices)for(unsigned i=0;i<2;++i)
        if(ZornGen7NativeDtEntry26::canPromote(*nodes[i]))existing[i]=nullptr;
    if (nodes[0] == nodes[1] ||
        (!allowExistingServices && (existing[0] || existing[1])) ||
        ((!existing[0] || !existing[1]) && !expert)) goto retained_platform;
    // Hold real nodes and ancestry before any raw-node link transfer.
    for (unsigned i = 0; i < 2; ++i) {
        if(!existing[i] && !ZornGen7NativeDtEntry26::canPromote(*nodes[i]))goto retained_platform;
        nodes[i]->retain();
        s.inputNode[i] = nodes[i];
        s.inputParent[i] = nodes[i]->copyParentEntry(gIODTPlane);
        if (!s.inputParent[i]) goto retained_platform;
    }
    for (unsigned i = 0; i < 2; ++i) {
        if (existing[i]) {
            auto *parent = existing[i]->getProvider();
            if (!parent) goto retained_platform;
            result.reusedProvider[i] = true;
            auto *nativeNub = OSDynamicCast(IOPlatformDevice, existing[i]);
            if (nativeNub && expert && parent == expert) {
                s.registryResourceProperty[i] =
                    existing[i]->copyProperty(gIODeviceMemoryKey);
                if (s.registryResourceProperty[i] &&
                    !OSDynamicCast(OSArray, s.registryResourceProperty[i]))
                    goto retained_platform;
                // Invoke only the real same-expert standard producer for
                // an absent property. Never repair incompatible metadata.
                if (!s.registryResourceProperty[i]) {
                    result.phase = Phase::PlatformNubResources;
                    result.nubResourceStatus[i] =
                        nativeNub->IOPlatformDevice::getResources();
                    result.nubResourceReturned[i] = true;
                    if (result.nubResourceStatus[i]) goto retained_platform;
                }
            }
            s.resolvedProvider[i] = existing[i];
            continue;
        }
        result.phase = Phase::PlatformNubAllocate;
        s.platformNub[i] = new IOPlatformDevice;
        if (!s.platformNub[i]) goto retained_platform;
        result.nubAllocated[i] = true;
        result.phase = Phase::PlatformNubInit;
        result.nubInitialized[i] = s.platformNub[i]->init(nodes[i], gIODTPlane);
        result.nubInitReturned[i] = true;
        if (!result.nubInitialized[i]) goto retained_platform;
        result.phase = Phase::PlatformNubAttach;
        result.nubAttached[i] = s.platformNub[i]->attach(expert);
        result.nubAttachReturned[i] = true;
        if (!result.nubAttached[i]) goto retained_platform;
        result.phase = Phase::PlatformNubResources;
        result.nubResourceStatus[i] = s.platformNub[i]->getResources();
        result.nubResourceReturned[i] = true;
        if (result.nubResourceStatus[i]) goto retained_platform;
        s.resolvedProvider[i] = s.platformNub[i];
    }
    result.phase = Phase::PlatformNubResources;
    // This flag admits only this exact resolved pair to the existing capture
    // under the same recursive gate. It never represents hardware readiness.
    s.registryResolutionReady = allowExistingServices;
    (void)captureDeviceMemory(*s.resolvedProvider[0], *s.resolvedProvider[1]);
retained_platform:
    Result returned = result;
    IORecursiveLockUnlock(s.gate);
    return returned;
}

ZornGen7InactiveOwner26::Result ZornGen7InactiveOwner26::prepareRegistryProviders(
    IORegistryEntry &actualNativeDtRoot)
{
    if (!storage_ || !storage_->gate || !zornGen7PreparationContext26()) return {};
    auto &s = *storage_;
    IORecursiveLockLock(s.gate);
    auto &result = s.result;
    if (result.registryLookupAttempted || result.platformNubAttempted ||
        result.resourceCaptureAttempted || result.phase != Phase::PreparedCpuOnly)
        goto retained_registry;
    result.registryLookupAttempted = true;
    result.phase = Phase::RegistryLookup;
    actualNativeDtRoot.retain();
    s.registryRoot = &actualNativeDtRoot;
    for (unsigned i = 0; i < 2; ++i) {
        s.registryNode[i] = IORegistryEntry::fromPath(
            ZornGen7RegistryNames26::Paths[i], gIODTPlane,
            nullptr, nullptr, s.registryRoot);
        result.registryLookupReturned[i] = true;
        result.registryNodeFound[i] = s.registryNode[i] != nullptr;
        if (!s.registryNode[i]) goto retained_registry;
    }
    (void)resolvePlatformProviders(*s.registryNode[0], *s.registryNode[1], true);
retained_registry:
    Result returned = result;
    IORecursiveLockUnlock(s.gate);
    return returned;
}

IOReturn ZornGen7InactiveOwner26::prepareGpuProviderClaims()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26() || !ml_get_interrupts_enabled())
        return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    auto finish=[&](IOReturn raw){s.gpuProviderClaimRaw=raw;IORecursiveLockUnlock(s.gate);return raw;};
    if(s.gpuProviderClaimAttempted)return finish(s.gpuProviderClaimRaw);
    s.gpuProviderClaimAttempted=true;
    if(!s.registryResolutionReady || s.result.phase!=Phase::ResourcesRetainedCpuOnly ||
       !s.result.zeroPreparedCpuOnly || s.result.retainedResourceMask!=15 ||
       !s.registryRoot || !s.resourceProvider[0] || !s.resourceProvider[1] ||
       s.resourceProvider[0]!=s.resolvedProvider[0] || s.resourceProvider[1]!=s.resolvedProvider[1])
        return finish(kIOReturnNotReady);
    IOService *gpu=s.resourceProvider[0],*gmu=s.resourceProvider[1];
    const auto exactBase=[](IOService *provider){
        if(!provider)return false;
        const auto *meta=provider->getMetaClass();
        return meta==IOService::metaClass || meta==IOPlatformDevice::metaClass;
    };
    if(gpu==gmu || !exactBase(gpu) || !exactBase(gmu))return finish(kIOReturnUnsupported);
    if(gpu->isInactive() || gmu->isInactive())return finish(kIOReturnNotAttached);
    // Refuse a known prior client; ordinary base-class open arbitrates a race
    // between this snapshot and the single-owner open below.
    if(gpu->isOpen() || gmu->isOpen())return finish(kIOReturnExclusiveAccess);
    IOService *common=gpu->getProvider();
    if(!common || common->isInactive() || gmu->getProvider()!=common)
        return finish(kIOReturnNotAttached);
    common->retain();s.gpuProviderClaimParent=common;
    s.gpuProviderClaimant=new IOService;
    if(!s.gpuProviderClaimant)return finish(kIOReturnNoMemory);
    if(!s.gpuProviderClaimant->init())return finish(kIOReturnError);
    if(!s.gpuProviderClaimant->attach(common))return finish(kIOReturnNotAttached);
    IOService *providers[2]={gpu,gmu};
    for(unsigned i=0;i<2;++i){
        const bool opened=providers[i]->open(s.gpuProviderClaimant,0,nullptr);
        s.gpuProviderClaimOpened[i]=opened;
        if(!opened)return finish(kIOReturnExclusiveAccess);
        if(!providers[i]->isOpen(s.gpuProviderClaimant))return finish(kIOReturnNotOpen);
    }
    return finish(kIOReturnSuccess);
}

bool ZornGen7InactiveOwner26::gpuProviderClaimsHeld() const
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26() || !ml_get_interrupts_enabled())return false;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    bool held=s.gpuProviderClaimAttempted && s.gpuProviderClaimRaw==kIOReturnSuccess &&
        s.gpuProviderClaimant && s.gpuProviderClaimParent &&
        !s.gpuProviderClaimant->isInactive() && !s.gpuProviderClaimParent->isInactive() &&
        s.gpuProviderClaimant->getProvider()==s.gpuProviderClaimParent;
    for(unsigned i=0;i<2 && held;++i){
        auto *provider=s.resourceProvider[i];
        held=s.gpuProviderClaimOpened[i] && provider && !provider->isInactive() &&
            provider->getProvider()==s.gpuProviderClaimParent && provider->isOpen(s.gpuProviderClaimant);
    }
    IORecursiveLockUnlock(s.gate);return held;
}

IOReturn ZornGen7InactiveOwner26::prepareRegisterOperationGuard(ZornGen7OperationGuard26 &out)
{
    if (out.cookie || out.admitMap || out.admitAccess || out.observeAccess)
        return kIOReturnBadArgument;
    if (!gpuProviderClaimsHeld()) return kIOReturnNotReady;
    auto &s = *storage_;
    IORecursiveLockLock(s.gate);
    const bool ready = s.pinned && s.registryResolutionReady && s.registryRoot &&
        s.result.retainedResourceMask == 15 && !s.registerMapsAttempted && !s.runtimeBorrower;
    if (ready) {
        s.registerGuardPrepared = true;
        out = {this, admitRegisterMap, admitRegisterAccess, observeRegisterAccess};
    }
    IORecursiveLockUnlock(s.gate);
    return ready ? kIOReturnSuccess : kIOReturnNotReady;
}

bool ZornGen7InactiveOwner26::registerGuardReady(bool access) const
{
    // Called with the recursive owner gate held. The retained map object
    // drops its own gate before calling either guard callback.
    const auto &s = *storage_;
    return s.registerGuardPrepared && s.registerMapsAttempted && s.registerMapBorrower &&
        s.smmuPowerReady && (!access || s.registerMapsReady) && gpuProviderClaimsHeld();
}

int ZornGen7InactiveOwner26::admitRegisterMap(void *cookie, IOMemoryDescriptor &descriptor,
    uint64_t physical, size_t bytes)
{
    auto &owner = *static_cast<ZornGen7InactiveOwner26 *>(cookie);
    auto &s = *owner.storage_;
    IORecursiveLockLock(s.gate);
    const bool allowed = owner.registerGuardReady(false) &&
        s.registerMapBorrower->matchesGuardMap(descriptor, physical, bytes);
    IORecursiveLockUnlock(s.gate);
    return allowed ? 0 : FHR_NOT_AVAILABLE;
}

int ZornGen7InactiveOwner26::admitRegisterAccess(void *cookie, IOMemoryDescriptor &descriptor,
    uint32_t address, unsigned width, bool write, uint64_t value)
{
    auto &owner = *static_cast<ZornGen7InactiveOwner26 *>(cookie);
    auto &s = *owner.storage_;
    IORecursiveLockLock(s.gate);
    const bool allowed = !s.pendingRegisterAccess.descriptor &&
        (!write || width != 4 || value <= UINT32_MAX) && owner.registerGuardReady(true) &&
        s.registerMapBorrower->matchesGuardAccess(descriptor, address, width, write);
    if (allowed) s.pendingRegisterAccess = {&descriptor, address, width, write, value};
    IORecursiveLockUnlock(s.gate);
    return allowed ? 0 : FHR_NOT_AVAILABLE;
}

int ZornGen7InactiveOwner26::observeRegisterAccess(void *cookie, IOMemoryDescriptor &descriptor,
    uint32_t address, unsigned width, bool write, uint64_t value)
{
    auto &owner = *static_cast<ZornGen7InactiveOwner26 *>(cookie);
    auto &s = *owner.storage_;
    IORecursiveLockLock(s.gate);
    const auto &pending = s.pendingRegisterAccess;
    const bool matched = pending.descriptor == &descriptor && pending.address == address &&
        pending.width == width && pending.write == write;
    const bool allowed = matched && (!write || pending.value == value) &&
        owner.registerGuardReady(true) &&
        s.registerMapBorrower->matchesGuardAccess(descriptor, address, width, write);
    if (allowed) s.pendingRegisterAccess = {};
    IORecursiveLockUnlock(s.gate);
    return allowed ? 0 : FHR_NOT_AVAILABLE;
}

bool ZornGen7InactiveOwner26::borrowForRegisterMappings(ZornGen7RegisterMaps26 &borrower,
    IOService *(&providers)[2],IOMemoryDescriptor *(&resources)[4],
    IOService *&providerClaimant,IOService *&providerClaimParent)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return false;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    auto finish=[&](bool r){IORecursiveLockUnlock(s.gate);return r;};
    if(providerClaimant || providerClaimParent)return finish(false);
    if(s.registerMapBorrower || !s.smmuPowerReady || !s.clocksReady || !s.clocks ||
       !s.rsc || !s.rsc->forwardAllowed() || s.result.phase!=Phase::ResourcesRetainedCpuOnly ||
       !s.result.zeroPreparedCpuOnly || s.result.retainedResourceMask!=15)return finish(false);
    if(s.gpuProviderClaimAttempted){
        if(s.gpuProviderClaimRaw!=kIOReturnSuccess || !s.gpuProviderClaimant || !s.gpuProviderClaimParent ||
           s.gpuProviderClaimant->isInactive() || s.gpuProviderClaimParent->isInactive() ||
           s.gpuProviderClaimant->getProvider()!=s.gpuProviderClaimParent)return finish(false);
        for(unsigned i=0;i<2;++i)if(!s.gpuProviderClaimOpened[i] || !s.resourceProvider[i] ||
           s.resourceProvider[i]->isInactive() || s.resourceProvider[i]->getProvider()!=s.gpuProviderClaimParent ||
           !s.resourceProvider[i]->isOpen(s.gpuProviderClaimant))return finish(false);
        providerClaimant=s.gpuProviderClaimant;providerClaimParent=s.gpuProviderClaimParent;
    }
    for(auto *p:s.resourceProvider)if(!p)return finish(false);
    for(auto *p:s.resources)if(!p)return finish(false);
    for(auto *p:providers)if(p)return finish(false);
    for(auto *p:resources)if(p)return finish(false);
    borrower.retain();s.registerMapBorrower=&borrower;
    for(size_t i=0;i<2;++i)providers[i]=s.resourceProvider[i];
    for(size_t i=0;i<4;++i)resources[i]=s.resources[i];
    return finish(true);
}
bool ZornGen7InactiveOwner26::borrowForRuntime(
    ZornGen7PreparedRuntime26 &actualBorrower, ZornGen7PreparedObjects26 &output)
{
    if (!storage_ || !storage_->gate || !zornGen7PreparationContext26()) return false;
    auto &s = *storage_;
    IORecursiveLockLock(s.gate);
    if (s.runtimeBorrower || s.firmwareSeedAttempted || !s.clocksReady || !s.clocks || !s.clockResourcesReady || !s.boardXoReady ||
        !s.commandDbReady || !s.rscReady || !s.rsc || !s.rsc->forwardAllowed() || !s.arcNodesReady || !s.clockNodesReady || !s.gccRailsReady || !s.gccPrefixReady || !s.gpuccPrefixReady || !s.clockGraphReady || !s.clockListReady || !s.hubMetadataReady || !s.ddrMetadataReady || !s.coreInputsReady || !s.cxGdscProbeReady || !s.cxGdscCoreReady || !s.cxCompletionReady || !s.smmuPowerReady ||
        s.result.phase != Phase::ResourcesRetainedCpuOnly ||
        !s.result.zeroPreparedCpuOnly || s.result.retainedResourceMask != 15) {
        IORecursiveLockUnlock(s.gate);
        return false;
    }
    ZornGen7PreparedObjects26 actual;
    actual.graph = &s.graph;
    actual.memory = &s.memory;
    actual.zero = &s.zero;
    actual.clocks = s.clocks;
    actual.cpuPageBytes = s.result.cpuPageBytes;
    for (unsigned i = 0; i < 2; ++i) actual.providers[i] = s.resourceProvider[i];
    for (unsigned i = 0; i < 4; ++i) actual.resources[i] = s.resources[i];
    actualBorrower.retain();
    s.runtimeBorrower = &actualBorrower;
    output = actual;
    IORecursiveLockUnlock(s.gate);
    return true;
}

IOReturn ZornGen7InactiveOwner26::prepareClockResources(IORegistryEntry &root,
    OSObject &authorityOwner,const ZornGen7ClockWindowAuthority26 &authority)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clocksReady || !s.clocks || s.clockResourcesAttempted || s.runtimeBorrower ||
       s.registryRoot!=&root || !s.registryResolutionReady) {
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;
    }
    s.clockResourcesAttempted=true;
    IORecursiveLockUnlock(s.gate);
    // No parent gate spans registry, mapping or independent authorization.
    // This owner already self-pins and retains the same platform/root epoch.
    const IOReturn created=ZornGen7ClockResources26::create(*s.platform,root,authorityOwner,
        authority,s.clockResources);
    if(created!=kIOReturnSuccess)return created;
    const IOReturn prepared=s.clockResources->prepareAndBind(*s.clocks);
    IORecursiveLockLock(s.gate);
    s.clockResourcesReady=prepared==kIOReturnSuccess;
    IORecursiveLockUnlock(s.gate);
    return prepared;
}
IOReturn ZornGen7InactiveOwner26::prepareNativeClockResources(IORegistryEntry &root,OSObject &authorityOwner)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clocksReady || !s.clocks || s.clockResourcesAttempted || s.runtimeBorrower ||
       s.registryRoot!=&root || !s.registryResolutionReady) {
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;
    }
    s.clockResourcesAttempted=true;
    IORecursiveLockUnlock(s.gate);
    // No parent gate spans genuine native nub/resource/mapping construction.
    // This owner already self-pins and retains the same platform/root epoch.
    const IOReturn created=ZornGen7ClockResources26::createNativeOwned(*s.platform,root,authorityOwner,s.clockResources);
    if(created!=kIOReturnSuccess)return created;
    const IOReturn prepared=s.clockResources->prepareAndBind(*s.clocks);
    IORecursiveLockLock(s.gate);
    s.clockResourcesReady=prepared==kIOReturnSuccess;
    IORecursiveLockUnlock(s.gate);
    return prepared;
}
ZornGen7Clock::ClockCoreFactoryResult ZornGen7InactiveOwner26::prepareBoardXo()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return {};
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clockResourcesReady || !s.registryResolutionReady || !s.registryRoot ||
       s.runtimeBorrower || s.boardXoAttempted) {
        const auto out=s.boardXoResult;IORecursiveLockUnlock(s.gate);return out;
    }
    s.boardXoAttempted=true;IORecursiveLockUnlock(s.gate);
    s.boardXoNode=IORegistryEntry::fromPath("board-xo",gIODTPlane,nullptr,nullptr,s.registryRoot);
    if(!s.boardXoNode)return {};
    const auto actual=s.clocks->registerBoardXoFromNativeNode(*s.boardXoNode,*this);
    IORecursiveLockLock(s.gate);s.boardXoResult=actual;s.boardXoReady=actual.core_initialized;
    IORecursiveLockUnlock(s.gate);return actual;
}
IOReturn ZornGen7InactiveOwner26::bindCommandDbResources(ZornGen7CommandDbResources26 &reader)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.boardXoReady || !s.registryResolutionReady || s.commandDbAttempted || s.runtimeBorrower){
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;
    }
    s.commandDbAttempted=true;reader.retain();s.commandDbResources=&reader;IORecursiveLockUnlock(s.gate);
    const auto bound=reader.bindToClockOwner(*s.clocks);
    IORecursiveLockLock(s.gate);s.commandDbReady=bound==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return bound;
}
IOReturn ZornGen7InactiveOwner26::prepareCommandDbSnapshot(IOMemoryDescriptor &descriptor,
    uint32_t expectedVersion,OSObject &sourceOwner)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.boardXoReady || !s.registryResolutionReady || s.commandDbAttempted || s.runtimeBorrower) {
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;
    }
    s.commandDbAttempted=true;IORecursiveLockUnlock(s.gate);
    const IOReturn copied=ZornGen7CommandDbSnapshot26::create(*s.platform,descriptor,
        expectedVersion,sourceOwner,s.commandDb);
    if(copied!=kIOReturnSuccess)return copied;
    const IOReturn bound=s.commandDb->bindToClockOwner(*s.clocks);
    IORecursiveLockLock(s.gate);s.commandDbReady=bound==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);
    return bound;
}
void ZornGen7InactiveOwner26::free()
{
    if (storage_ && storage_->pinned) return;
    if (storage_) { IOFree(storage_, sizeof(Storage)); storage_ = nullptr; }
    OSObject::free();
}

IOReturn ZornGen7InactiveOwner26::prepareRscRuntime(const ZornGen7RscInputs26 &inputs)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clocksReady || !s.commandDbReady || !s.clocks || s.rscAttempted || s.runtimeBorrower) {
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;
    }
    s.rscAttempted=true;
    zorn26_rsc_stage_screen(0x0d);
    const IOReturn constructed=ZornGen7RscRuntime26::create(*s.platform,inputs,s.rsc);
    IORecursiveLockUnlock(s.gate);
    zorn26_rsc_stage_screen(0x0e);
    if(constructed!=kIOReturnSuccess || !s.rsc)return constructed;
    unsigned masked=0;
    if(PE_parse_boot_argn("zorn26_rsc_masked_runtime",&masked,sizeof(masked)) && masked==1){
        const auto installed=s.rsc->installDisabled();
        // Full runtime remains unavailable in this explicit construction stage.
        // No enable,clock binding or rscReady publication is implied.
        return installed==kIOReturnSuccess?kIOReturnNotReady:installed;
    }
    const IOReturn enabled=s.rsc->installAndEnable();if(enabled!=kIOReturnSuccess)return enabled;
    zorn26_rsc_stage_screen(0x13);
    const IOReturn bound=s.rsc->bindToClockOwner(*s.clocks);zorn26_rsc_stage_screen(0x14);
    IORecursiveLockLock(s.gate);s.rscReady=bound==kIOReturnSuccess && s.rsc->forwardAllowed();
    IORecursiveLockUnlock(s.gate);return bound;
}

bool ZornGen7InactiveOwner26::copyRscRuntimeInstallStatus(ZornGen7RscInstallStatus26 &out)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return false;
    auto &s=*storage_;IORecursiveLockLock(s.gate);auto *runtime=s.rsc;
    if(runtime)runtime->retain();IORecursiveLockUnlock(s.gate);
    if(!runtime)return false;
    const auto r=runtime->readResult();runtime->release();
    ZornGen7RscInstallStatus26 actual;actual.constructed=r.constructed;
    actual.installationReturned=r.installationReturned;
    actual.installationAssessment=static_cast<uint32_t>(r.installation.assessment);
    actual.installedDisabled=r.installationReturned &&
        r.installation.assessment==ZornGen7Rpmh::BindingAssessment::DisabledSourceInstalled;
    actual.enableReturned=r.enableReturned;actual.forwardAllowed=r.forwardAllowed;
    out=actual;return true;
}
IOReturn ZornGen7InactiveOwner26::prepareArcNodes(IORegistryEntry &root,IOService &rscProvider,
    OSObject &treeOwner,const uint8_t (&digest)[32])
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.rscReady || !s.rsc || !s.rsc->forwardAllowed() || !s.commandDbReady || !s.clocks ||
       s.arcNodesAttempted || s.runtimeBorrower) {IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.arcNodesAttempted=true;IORecursiveLockUnlock(s.gate);
    const IOReturn created=ZornGen7ArcNodes26::create(*s.platform,root,rscProvider,treeOwner,s.arcNodes);
    if(created!=kIOReturnSuccess)return created;
    const IOReturn initialized=s.arcNodes->prepareAndInitialize(*s.clocks,digest);
    IORecursiveLockLock(s.gate);s.arcNodesReady=initialized==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);
    return initialized;
}
IOReturn ZornGen7InactiveOwner26::prepareClockNodes(IORegistryEntry &root,OSObject &treeOwner)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.arcNodesReady || !s.rsc || !s.rsc->forwardAllowed() || s.registryRoot!=&root ||
       s.clockNodesAttempted || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.clockNodesAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto created=ZornGen7ClockNodes26::create(*s.platform,root,treeOwner,s.clockNodes);
    if(created!=kIOReturnSuccess)return created;
    const auto bound=s.clockNodes->prepareAndBind(*s.clocks);
    IORecursiveLockLock(s.gate);s.clockNodesReady=bound==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return bound;
}
IOReturn ZornGen7InactiveOwner26::prepareGccClockRails()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clockNodesReady || !s.arcNodesReady || !s.clocks || !s.rsc || !s.rsc->forwardAllowed() ||
       s.gccRailsAttempted || s.gpuccPrefixAttempted || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.gccRailsAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->constructOwnedGccClockRails();
    IORecursiveLockLock(s.gate);s.gccRailsReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}
ZornGen7Clock::GccGpuPrefixResult ZornGen7InactiveOwner26::prepareGccGpuClockPrefix()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return {};
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.gccRailsReady || !s.clocks || !s.rsc || !s.rsc->forwardAllowed() || s.gccPrefixAttempted ||
       s.gpuccPrefixAttempted || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return {};}
    s.gccPrefixAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto result=s.clocks->prepareGccGpuClockPrefix();
    IORecursiveLockLock(s.gate);s.gccPrefixReady=result.native_closure_prefix_returned;
    IORecursiveLockUnlock(s.gate);return result;
}
ZornGen7Clock::GmuClockGraphResult ZornGen7InactiveOwner26::prepareNativeGmuClockGraph()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return {};
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.gccPrefixReady || !s.gpuccPrefixReady || !s.clocks || !s.rsc || !s.rsc->forwardAllowed() ||
       s.clockGraphAttempted || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return {};}
    s.clockGraphAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto result=s.clocks->constructOwnedNativeGmuClockGraph();
    IORecursiveLockLock(s.gate);s.clockGraphReady=result.cpu_graph_complete;IORecursiveLockUnlock(s.gate);return result;
}
ZornGen7Clock::ClockConsumerListResult ZornGen7InactiveOwner26::prepareNativeGmuClockList()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return {};
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clockGraphReady || !s.clocks || !s.rsc || !s.rsc->forwardAllowed() || s.clockListAttempted ||
       s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return {};}
    s.clockListAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto result=s.clocks->constructOwnedNativeGmuClockList();
    IORecursiveLockLock(s.gate);s.clockListReady=result.assessment==ZornGen7Clock::ClockConsumerListAssessment::ListPublished;
    IORecursiveLockUnlock(s.gate);return result;
}
IOReturn ZornGen7InactiveOwner26::prepareGen79HubMetadata()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clockListReady || !s.clocks || !s.rsc || !s.rsc->forwardAllowed() || s.hubMetadataAttempted ||
       s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.hubMetadataAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->publishOwnedGen79HubMetadata();
    IORecursiveLockLock(s.gate);s.hubMetadataReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}
IOReturn ZornGen7InactiveOwner26::prepareDdrMetadata(IORegistryEntry &root,OSObject &treeOwner)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.hubMetadataReady || s.registryRoot!=&root || !s.clocks || !s.rsc || !s.rsc->forwardAllowed() ||
       s.ddrMetadataAttempted || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.ddrMetadataAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->captureOwnedDdrMetadata(root,treeOwner);
    IORecursiveLockLock(s.gate);s.ddrMetadataReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}
IOReturn ZornGen7InactiveOwner26::prepareGen79CoreInputs()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.ddrMetadataReady || !s.clocks || !s.rsc || !s.rsc->forwardAllowed() || s.coreInputsAttempted ||
       s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.coreInputsAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->constructOwnedGen79CoreInputs();
    IORecursiveLockLock(s.gate);s.coreInputsReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}
ZornGen7CxGdsc::NativeProbeResult ZornGen7InactiveOwner26::prepareCxGdscRegisters()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return {};
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.coreInputsReady || !s.clocks || !s.rsc || !s.rsc->forwardAllowed() ||
       s.cxGdscProbeAttempted || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return {};}
    s.cxGdscProbeAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto result=s.clocks->initializeOwnedCxGdscRegisters();
    IORecursiveLockLock(s.gate);s.cxGdscProbeReady=result.native_prefix_returned;
    IORecursiveLockUnlock(s.gate);return result;
}
IOReturn ZornGen7InactiveOwner26::prepareCxGdscCore(IORegistryEntry &root,OSObject &treeOwner)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.cxGdscProbeReady || !s.clocks || !s.rsc || !s.rsc->forwardAllowed() ||
       s.registryRoot!=&root || !s.resolvedProvider[1] || s.cxGdscCoreAttempted || s.runtimeBorrower) {
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;
    }
    s.cxGdscCoreAttempted=true;IORecursiveLockUnlock(s.gate);
    IOReturn raw=ZornGen7CxGdscNodes26::create(*s.platform,root,*s.resolvedProvider[1],treeOwner,s.cxGdscNodes);
    if(raw==kIOReturnSuccess)raw=s.cxGdscNodes->prepareAndBind(*s.clocks);
    IORecursiveLockLock(s.gate);s.cxGdscCoreReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}
ZornGen7CxGdsc::OwnedCompletionResult ZornGen7InactiveOwner26::prepareCxCompletion()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return {};
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.cxGdscCoreReady || !s.clocks || !s.rsc || !s.rsc->forwardAllowed() ||
       s.cxCompletionAttempted || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return {};}
    s.cxCompletionAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto result=s.clocks->registerOwnedCxCompletion();
    IORecursiveLockLock(s.gate);s.cxCompletionReady=result.registered;IORecursiveLockUnlock(s.gate);return result;
}
IOReturn ZornGen7InactiveOwner26::prepareSmmuPowerResources(IORegistryEntry &root,OSObject &treeOwner)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.cxCompletionReady || !s.clocks || !s.rsc || !s.rsc->forwardAllowed() ||
       s.registryRoot!=&root || s.smmuPowerAttempted || s.runtimeBorrower) {
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;
    }
    s.smmuPowerAttempted=true;IORecursiveLockUnlock(s.gate);
    IOReturn raw=ZornGen7PlatformMmioInputs26::create(*s.platform,root,treeOwner,s.smmuInputs);
    if(raw==kIOReturnSuccess && !s.smmuInputs->borrowForSmmuStartup(*s.platform,root,*this,
        s.resolvedProvider,s.smmuController,s.smmuDescriptor))raw=kIOReturnNotReady;
    if(raw==kIOReturnSuccess)raw=s.clocks->constructOwnedSmmuPower(*s.platform,*s.smmuController,
        *s.smmuDescriptor,*s.smmuInputs);
    IORecursiveLockLock(s.gate);s.smmuPowerReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}
IOReturn ZornGen7InactiveOwner26::prepareRegisterMappings(IORegistryEntry &root,OSObject &owner,
    const ZornGen7OperationGuard26 &guard,ZornGen7RegisterMaps26 *&out,bool nativeSmmu)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26() || out)return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPowerReady || !s.smmuInputs || !s.clocks || s.registryRoot!=&root ||
       s.registerMapsAttempted || s.runtimeBorrower) {IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    if (guard.admitMap == admitRegisterMap || guard.admitAccess == admitRegisterAccess ||
        guard.observeAccess == observeRegisterAccess) {
        if (!s.registerGuardPrepared || guard.cookie != this || guard.admitMap != admitRegisterMap ||
            guard.admitAccess != admitRegisterAccess || guard.observeAccess != observeRegisterAccess) {
            IORecursiveLockUnlock(s.gate);
            return kIOReturnNotPermitted;
        }
    }
    s.registerMapsAttempted=true;IORecursiveLockUnlock(s.gate);
    IOReturn raw=ZornGen7RegisterMaps26::create(*this,owner,guard,out,nativeSmmu);
    if(raw!=kIOReturnSuccess)return raw;
    if(!out->capturePlatformInputs(*s.smmuInputs).platformInputsCaptured)return kIOReturnNotReady;
    if(!out->prepareMappings().mapsReady)return kIOReturnNotReady;
    raw=s.clocks->bindOwnedSmmuGlobalIo(*out);
    IORecursiveLockLock(s.gate);s.registerMapsReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}
IOReturn ZornGen7InactiveOwner26::prepareNativeCpuRegisterMappings(IORegistryEntry &root,OSObject &owner,
    ZornGen7RegisterMaps26 *&out)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26() || out)return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPowerReady || !s.smmuInputs || !s.clocks || s.registryRoot!=&root ||
       s.registerMapsAttempted || s.runtimeBorrower) {IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.registerMapsAttempted=true;IORecursiveLockUnlock(s.gate);
    IOReturn raw=ZornGen7RegisterMaps26::createNativeCpuMappings(*this,owner,out);
    if(raw!=kIOReturnSuccess)return raw;
    if(!out->capturePlatformInputs(*s.smmuInputs).platformInputsCaptured)return kIOReturnNotReady;
    if(!out->prepareMappings().mapsReady)return kIOReturnNotReady;
    raw=s.clocks->bindOwnedSmmuGlobalIo(*out);
    IORecursiveLockLock(s.gate);s.registerMapsReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}
IOReturn ZornGen7InactiveOwner26::prepareSmmuRuntimePm(IOWorkLoop &loop,OSObject &owner,
    const ZornGen7SmmuRuntimeAuthority26 &authority)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.registerMapsReady || !s.clocks || !s.rsc || !s.rsc->usesCompletionWorkloop(loop) ||
       s.smmuPmAttempted || s.runtimeBorrower) {IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.smmuPmAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->constructOwnedSmmuRuntimePm(loop,owner,authority);
    IORecursiveLockLock(s.gate);s.smmuPmReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}
IOReturn ZornGen7InactiveOwner26::probeNativeSmmuCapabilities(ZornGen7RegisterMaps26 &maps,OSObject &owner,
    ZornGen7NativeSmmuProbeResult26 &out,const ZornGen7SmmuBankAuthority26 *authority)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    const bool admitted=s.registerMapsReady && s.registerMapBorrower==&maps && s.smmuPmReady &&
        s.clocks && s.rsc && s.rsc->forwardAllowed() && !s.runtimeBorrower;
    (void)authority;IORecursiveLockUnlock(s.gate);return admitted?s.clocks->probeNativeSmmuCapabilities(maps,owner,out):kIOReturnNotReady;
}
ZornGen7ColdBoot::OperationResult ZornGen7InactiveOwner26::resumeNativeSmmuPower(ZornGen7NativeSmmuPowerProgress26 &progress,const ZornGen7SmmuRuntimeAuthority26 *authority)
{
    using namespace ZornGen7ColdBoot;constexpr OperationResult unavailable{Disposition::Unavailable,StatusDomain::Unavailable,0,0};
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return unavailable;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    const bool admitted=s.registerMapsReady && s.smmuPowerReady && s.clocks && s.rsc && s.rsc->forwardAllowed() && !s.runtimeBorrower;
    (void)authority;IORecursiveLockUnlock(s.gate);if(!admitted)return unavailable;progress.caller_phase=1;return s.clocks->resumeNativeSmmuPower(progress);
}
IOReturn ZornGen7InactiveOwner26::prepareNativeHeldSmmuRuntimePm(IOWorkLoop &loop,OSObject &owner,const ZornGen7SmmuRuntimeAuthority26 *authority)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.registerMapsReady || !s.smmuPowerReady || !s.clocks || !s.rsc || !s.rsc->usesCompletionWorkloop(loop) ||
       s.smmuPmAttempted || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.smmuPmAttempted=true;IORecursiveLockUnlock(s.gate);
    (void)authority;const auto raw=s.clocks->constructNativeHeldSmmuRuntimePm(loop,owner);
    IORecursiveLockLock(s.gate);s.smmuPmReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}
ZornGen7CxGdsc::EnablePrefixResult ZornGen7InactiveOwner26::prepareNativeCxPrimary()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return {};
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    const bool admitted=s.registerMapsReady && s.smmuPowerReady && s.cxCompletionReady &&
        s.clocks && s.rsc && s.rsc->forwardAllowed() && !s.runtimeBorrower;
    IORecursiveLockUnlock(s.gate);
    return admitted?s.clocks->prepareNativeCxPrimary():ZornGen7CxGdsc::EnablePrefixResult{};
}
ZornGen7CxGdsc::EnablePrefixResult ZornGen7InactiveOwner26::prepareCxForDomainProbe()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return {};
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPmReady || !s.clocks || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return {};}
    IORecursiveLockUnlock(s.gate);return s.clocks->prepareCxForDomainProbe();
}
IOReturn ZornGen7InactiveOwner26::probeSmmuDomains(OSObject &owner,const ZornGen7SmmuBankAuthority26 &authority)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPmReady || !s.clocks || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    IORecursiveLockUnlock(s.gate);return s.clocks->probeOwnedSmmuDomains(owner,authority);
}
ZornGen7ColdBoot::OperationResult ZornGen7InactiveOwner26::reserveSmmuEndpoints(IORegistryEntry &root,OSObject &treeOwner)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return {ZornGen7ColdBoot::Disposition::Unavailable,ZornGen7ColdBoot::StatusDomain::Unavailable,0,0};
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPmReady || !s.clocks || s.runtimeBorrower || s.registryRoot!=&root || !s.resourceProvider[1]) {
        IORecursiveLockUnlock(s.gate);return {ZornGen7ColdBoot::Disposition::Unavailable,ZornGen7ColdBoot::StatusDomain::Unavailable,0,0};
    }
    auto *gmu=s.resourceProvider[1];IORecursiveLockUnlock(s.gate);
    return s.clocks->reserveOwnedSmmuEndpoints(root,*gmu,treeOwner);
}
IOReturn ZornGen7InactiveOwner26::bindSmmuContextViews(ZornGen7RegisterMaps26 &maps,
    OSObject &owner,const ZornGen7AtomicSmmuGuard26 &guard)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPmReady || !s.clocks || s.runtimeBorrower || s.registerMapBorrower!=&maps) {
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;
    }
    IORecursiveLockUnlock(s.gate);return s.clocks->bindOwnedSmmuContextViews(maps,owner,guard);
}
IOReturn ZornGen7InactiveOwner26::prepareSmmuRootPages()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPmReady || !s.clocks || s.runtimeBorrower) {
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;
    }
    IORecursiveLockUnlock(s.gate);return s.clocks->prepareOwnedSmmuRootPages();
}
IOReturn ZornGen7InactiveOwner26::prepareSmmuSparseArenas()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPmReady || !s.clocks || s.runtimeBorrower) {
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;
    }
    IORecursiveLockUnlock(s.gate);return s.clocks->prepareOwnedSmmuSparseArenas();
}
IOReturn ZornGen7InactiveOwner26::prepareGmuContextImage()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPmReady || !s.clocks || s.runtimeBorrower) {
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;
    }
    IORecursiveLockUnlock(s.gate);return s.clocks->prepareOwnedGmuContextImage();
}
ZornGen7Clock::OwnedGpuccPrefixResult ZornGen7InactiveOwner26::prepareNativeGpuccPrefix()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return {};
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clockNodesReady || !s.arcNodesReady || !s.gccRailsReady || !s.gccPrefixReady || !s.clocks || !s.rsc || !s.rsc->forwardAllowed() ||
       s.gpuccPrefixAttempted || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return {};}
    s.gpuccPrefixAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto result=s.clocks->prepareNativeGpuccPrefix();
    IORecursiveLockLock(s.gate);s.gpuccPrefixReady=result.source_prefix_complete;
    IORecursiveLockUnlock(s.gate);return result;
}
bool ZornGen7InactiveOwner26::rscPlatformAdmitted(IOService &platform) const
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return false;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    const bool allowed=s.platform==&platform && s.commandDbReady && s.clocksReady &&
        !s.rscAttempted && !s.runtimeBorrower;
    IORecursiveLockUnlock(s.gate);return allowed;
}

bool ZornGen7InactiveOwner26::commandDbPlatformAdmitted(IOService &platform) const
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return false;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    const bool allowed=s.platform==&platform && s.boardXoReady && s.registryResolutionReady &&
        !s.commandDbAttempted && !s.runtimeBorrower;
    IORecursiveLockUnlock(s.gate);return allowed;
}

IOReturn ZornGen7InactiveOwner26::prepareGmuFirmwareSeed()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPmReady || !s.clocks || s.runtimeBorrower || s.firmwareSeedAttempted ||
       !s.memory.prepared() || s.result.phase!=Phase::ResourcesRetainedCpuOnly) {
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;
    }
    // Exclusive immutable native inventory borrow; incompatible reference-FHR
    // borrower is excluded from this point, including partial failure.
    s.firmwareSeedAttempted=true;
    IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->prepareOwnedGmuFirmwareSeed(s.memory,*this);
    IORecursiveLockLock(s.gate);s.firmwareSeedReady=raw==kIOReturnSuccess;
    IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::holdGmuFirmware()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPmReady || !s.clocks || s.runtimeBorrower || !s.firmwareSeedReady ||
       s.firmwareHoldsAttempted || !s.memory.prepared()) {
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;
    }
    s.firmwareHoldsAttempted=true;IORecursiveLockUnlock(s.gate);
    return s.clocks->holdOwnedGmuFirmware(s.memory,*this);
}

IOReturn ZornGen7InactiveOwner26::installGmuFaultIrq(OSObject &owner,
    const ZornGen7SmmuFaultIrqAuthority26 &authority)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPmReady || !s.clocks || s.runtimeBorrower || !s.firmwareSeedReady || !s.firmwareHoldsAttempted) {
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;
    }
    IORecursiveLockUnlock(s.gate);return s.clocks->installOwnedGmuFaultIrq(owner,authority);
}

IOReturn ZornGen7InactiveOwner26::prepareGmuStreamSlot(OSObject &owner,
    const ZornGen7SmmuStreamAuthority26 &authority)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPmReady || !s.clocks || s.runtimeBorrower || !s.firmwareSeedReady || !s.firmwareHoldsAttempted) {
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;
    }
    IORecursiveLockUnlock(s.gate);return s.clocks->prepareOwnedGmuStreamSlot(owner,authority);
}

IOReturn ZornGen7InactiveOwner26::programGmuContext(unsigned budget)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPmReady || !s.clocks || s.runtimeBorrower || !s.firmwareSeedReady || !s.firmwareHoldsAttempted) {
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;
    }
    IORecursiveLockUnlock(s.gate);return s.clocks->programOwnedGmuContext(budget);
}

IOReturn ZornGen7InactiveOwner26::prepareGlobalSmmuFaults(OSObject &owner,
    const ZornGen7SmmuFaultIrqAuthority26 &authority,unsigned budget)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPmReady || !s.clocks || s.runtimeBorrower) {
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;
    }
    IORecursiveLockUnlock(s.gate);return s.clocks->prepareOwnedGlobalSmmuFaults(owner,authority,budget);
}

IOReturn ZornGen7InactiveOwner26::prepareSmmuController(OSObject &owner,
    const ZornGen7SmmuColdAuthority26 &cold,const ZornGen7SmmuFaultIrqAuthority26 &fault,unsigned budget,ZornGen7NativeSmmuIrqResult26 *nativeResult)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPmReady || !s.clocks || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    IORecursiveLockUnlock(s.gate);if(nativeResult)return kIOReturnUnsupported;return s.clocks->prepareOwnedSmmuController(owner,cold,fault,budget);
}

IOReturn ZornGen7InactiveOwner26::activateGmuStream()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPmReady || !s.clocks || s.runtimeBorrower || !s.firmwareSeedReady || !s.firmwareHoldsAttempted) {
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;
    }
    IORecursiveLockUnlock(s.gate);return s.clocks->activateOwnedGmuStream();
}

IOReturn ZornGen7InactiveOwner26::loadGmuTcmAndShadow(OSObject &owner,const ZornGen7GmuLoadAuthority26 &authority)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPmReady || !s.clocks || s.runtimeBorrower || !s.firmwareSeedReady || !s.firmwareHoldsAttempted || !s.coldGmuClockReady || !s.gmuAhbReady || !s.cxTimerReady) {
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;
    }
    IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->loadOwnedGmuTcmAndShadow(owner,authority);
    IORecursiveLockLock(s.gate);s.gmuTcmLoadedReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::enableGmuColdClocks(OSObject &treeOwner)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPmReady || !s.clocks || !s.clockListReady || !s.coreInputsReady || s.runtimeBorrower ||
       !s.firmwareSeedReady || !s.firmwareHoldsAttempted || !s.resourceProvider[0] || !s.resourceProvider[1] ||
       s.coldGmuClockAttempted) {IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.coldGmuClockAttempted=true;
    auto *gpu=s.resourceProvider[0];auto *gmu=s.resourceProvider[1];IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->enableOwnedGmuColdClocks(*gpu,*gmu,treeOwner);
    IORecursiveLockLock(s.gate);s.coldGmuClockReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::enableNativeHostGmuColdClocks(OSObject &treeOwner,
    ZornGen7NativeGmuClockResult26 &out)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPmReady || !s.clocks || !s.clockListReady || !s.coreInputsReady || !s.registerMapsReady ||
       !s.registerMapBorrower || !s.rsc || !s.rsc->forwardAllowed() || s.runtimeBorrower ||
       !s.resourceProvider[0] || !s.resourceProvider[1] || s.coldGmuClockAttempted){
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;
    }
    s.coldGmuClockAttempted=true;
    auto *gpu=s.resourceProvider[0];auto *gmu=s.resourceProvider[1];IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->enableNativeHostGmuColdClocks(*gpu,*gmu,treeOwner,out);
    IORecursiveLockLock(s.gate);s.coldGmuClockReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}
IOReturn ZornGen7InactiveOwner26::enableHostGmuColdClocks(OSObject &treeOwner)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPmReady || !s.clocks || !s.clockListReady || !s.coreInputsReady || s.runtimeBorrower ||
       !s.firmwareSeedReady || !s.firmwareHoldsAttempted || !s.resourceProvider[0] || !s.resourceProvider[1] ||
       s.coldGmuClockAttempted){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.coldGmuClockAttempted=true;
    auto *gpu=s.resourceProvider[0];auto *gmu=s.resourceProvider[1];IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->enableOwnedHostGmuColdClocks(*gpu,*gmu,treeOwner);
    IORecursiveLockLock(s.gate);s.coldGmuClockReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::prepareGmuAhbSource()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPmReady || !s.clocks || !s.coldGmuClockReady || !s.registerMapsReady ||
       !s.registerMapBorrower || s.runtimeBorrower || s.gmuAhbAttempted) {
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;
    }
    s.gmuAhbAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->prepareOwnedGmuAhbSource();
    IORecursiveLockLock(s.gate);s.gmuAhbReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::prepareNativeGlobalMaskedSmmuIrq(OSObject &owner,
    ZornGen7NativeSmmuIrqResult26 &out)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPmReady || !s.clocks || !s.cxTimerReady || !s.registerMapsReady ||
       !s.registerMapBorrower || s.runtimeBorrower || s.nativeGlobalIrqAttempted){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.nativeGlobalIrqAttempted=true;IORecursiveLockUnlock(s.gate);
    return s.clocks->prepareNativeGlobalMaskedSmmuIrq(*s.registerMapBorrower,owner,out);
}

IOReturn ZornGen7InactiveOwner26::initializeNativeCxTimer(OSObject &owner,
    ZornGen7NativeCxTimerResult26 &out)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPmReady || !s.clocks || !s.gmuAhbReady || !s.coldGmuClockReady ||
       !s.registerMapsReady || !s.registerMapBorrower || s.runtimeBorrower ||
       !s.resourceProvider[0] || !s.resourceProvider[1] || s.cxTimerAttempted){
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;
    }
    s.cxTimerAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->initializeNativeCxTimer(*s.registerMapBorrower,*s.resourceProvider[0],
        *s.resourceProvider[1],owner,out);
    IORecursiveLockLock(s.gate);s.cxTimerReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::initializeCxTimer(OSObject &owner,const ZornGen7CxTimerAuthority26 &authority)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPmReady || !s.clocks || !s.gmuAhbReady || !s.coldGmuClockReady ||
       !s.registerMapsReady || !s.registerMapBorrower || s.runtimeBorrower || s.cxTimerAttempted) {
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;
    }
    s.cxTimerAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->initializeOwnedCxTimer(*s.registerMapBorrower,owner,authority);
    IORecursiveLockLock(s.gate);s.cxTimerReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::initializeCxSecurity(OSObject &owner,
    const ZornGen7ScmAuthority26 &authority,uint32_t budget)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.smmuPmReady || !s.clocks || !s.gmuTcmLoadedReady || !s.cxTimerReady || !s.pdcRscReady ||
       s.runtimeBorrower || s.cxSecurityAttempted || !s.registryRoot || !s.resourceProvider[0]) {IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.cxSecurityAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->initializeOwnedCxSecurity(*s.registryRoot,*s.resourceProvider[0],owner,authority,budget);
    IORecursiveLockLock(s.gate);s.cxSecurityReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::prepareGmuIrqs(IOWorkLoop &loop,OSObject &owner,const ZornGen7GmuIrqAuthority26 &authority)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.cxSecurityReady || !s.registerMapsReady || !s.registerMapBorrower ||
       !s.resourceProvider[1] || s.runtimeBorrower || s.gmuIrqAttempted){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.gmuIrqAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->prepareOwnedGmuIrqs(*s.resourceProvider[1],*s.registerMapBorrower,loop,owner,authority);
    IORecursiveLockLock(s.gate);s.gmuIrqReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::configureGmuRegisters()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.gmuIrqReady || !s.cxSecurityReady || !s.gmuTcmLoadedReady ||
       s.runtimeBorrower || s.gmuConfigAttempted){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.gmuConfigAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->configureOwnedGmuRegisters();
    IORecursiveLockLock(s.gate);s.gmuConfigReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::prepareDirectHfi(IOWorkLoop &loop)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.gmuConfigReady || !s.gmuIrqReady || s.runtimeBorrower || s.directHfiAttempted){
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.directHfiAttempted=true;IORecursiveLockUnlock(s.gate);const auto raw=s.clocks->prepareOwnedDirectHfi(loop);
    IORecursiveLockLock(s.gate);s.directHfiReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::prepareGpuIccInputs(OSObject &owner)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.ddrMetadataReady || !s.platform || !s.registryRoot ||
       !s.resourceProvider[0] || s.runtimeBorrower || s.gpuIccInputsAttempted){
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.gpuIccInputsAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->prepareOwnedGpuIccInputs(*s.platform,*s.registryRoot,*s.resourceProvider[0],owner);
    IORecursiveLockLock(s.gate);s.gpuIccInputsReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::initializeGpuIccVotes()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.gpuIccInputsReady || s.runtimeBorrower || s.gpuIccInitialAttempted){
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.gpuIccInitialAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->initializeOwnedGpuIccVotes();
    IORecursiveLockLock(s.gate);s.gpuIccInitialReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::configureGpuIccQos(OSObject &owner,const ZornGen7OperationGuard26 &guard,
    const ZornGen7IccQosAuthority26 &authority)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.gpuIccInitialReady || s.runtimeBorrower || s.gpuIccQosAttempted){
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.gpuIccQosAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->configureOwnedGpuIccQos(owner,guard,authority);
    IORecursiveLockLock(s.gate);s.gpuIccQosReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::configureNativeGpuIccQos(OSObject &owner,const ZornGen7IccQosAuthority26 &authority)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.gpuIccInitialReady || s.runtimeBorrower || s.gpuIccQosAttempted){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.gpuIccQosAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->configureNativeOwnedGpuIccQos(owner,authority);
    IORecursiveLockLock(s.gate);s.gpuIccQosReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}
IOReturn ZornGen7InactiveOwner26::applyGpuBootstrapBandwidth()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.gpuIccQosReady || !s.hostIrqArmed || s.runtimeBorrower || s.gpuBootstrapBwAttempted){
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.gpuBootstrapBwAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->applyOwnedGpuBootstrapBandwidth();
    IORecursiveLockLock(s.gate);s.gpuBootstrapBwReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::prepareHwschedHfi(IOWorkLoop &loop)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.gmuConfigReady || !s.gmuVersionsReady || !s.gmuIrqReady || s.runtimeBorrower || s.hwschedHfiAttempted){
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.hwschedHfiAttempted=true;IORecursiveLockUnlock(s.gate);const auto raw=s.clocks->prepareOwnedHwschedHfi(loop);
    IORecursiveLockLock(s.gate);s.hwschedHfiReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::loadPdcRsc()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.gmuTcmLoadedReady || !s.cxTimerReady || !s.coldGmuClockReady ||
       !s.registerMapsReady || !s.registerMapBorrower || s.pdcRscAttempted || s.cxSecurityAttempted || s.runtimeBorrower){
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;
    }
    s.pdcRscAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->loadOwnedPdcRsc(*s.registerMapBorrower);
    IORecursiveLockLock(s.gate);s.pdcRscReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::readHwschedGmuVersions()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.gmuConfigReady || !s.gmuIrqReady || !s.cxSecurityReady || !s.pdcRscReady ||
       s.runtimeBorrower || s.gmuVersionsAttempted){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.gmuVersionsAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->readOwnedHwschedGmuVersions();
    IORecursiveLockLock(s.gate);s.gmuVersionsReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::armHwschedIrqs()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.gmuVersionsReady || !s.gmuConfigReady || !s.hwschedHfiReady || !s.gpuIccQosReady ||
       s.runtimeBorrower || s.hwschedIrqArmAttempted){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.hwschedIrqArmAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->armOwnedHwschedIrqs();
    IORecursiveLockLock(s.gate);s.hwschedIrqArmed=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::prepareHostHfi(IOWorkLoop &loop)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.gmuConfigReady || !s.gmuVersionsReady || !s.gmuIrqReady || s.runtimeBorrower || s.hostHfiAttempted){
        IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.hostHfiAttempted=true;IORecursiveLockUnlock(s.gate);const auto raw=s.clocks->prepareOwnedHostHfi(loop);
    IORecursiveLockLock(s.gate);s.hostHfiReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::armHostIrqs()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.gmuVersionsReady || !s.gmuConfigReady || !s.hostHfiReady || !s.gpuIccQosReady ||
       s.runtimeBorrower || s.hostIrqArmAttempted){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.hostIrqArmAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->armOwnedHostIrqs();
    IORecursiveLockLock(s.gate);s.hostIrqArmed=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::readHostGmuVersions()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.gmuConfigReady || !s.gmuIrqReady || !s.cxSecurityReady || !s.pdcRscReady ||
       s.runtimeBorrower || s.gmuVersionsAttempted){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.gmuVersionsAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->readOwnedHostGmuVersions();
    IORecursiveLockLock(s.gate);s.gmuVersionsReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::prepareHostTables(const ZornGen7HostTableSelection26 &selection)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.coreInputsReady || !s.commandDbReady || s.runtimeBorrower || s.hostTablesAttempted){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.hostTablesAttempted=true;IORecursiveLockUnlock(s.gate);const auto raw=s.clocks->prepareOwnedHostTables(selection);
    IORecursiveLockLock(s.gate);s.hostTablesReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::startHostGmu(OSObject &owner,const ZornGen7GmuStartAuthority26 &authority)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;if(IORecursiveLockHaveLock(s.gate))return kIOReturnNotReady;
    IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.hostHfiReady || !s.hostIrqArmed || !s.gpuBootstrapBwReady || s.runtimeBorrower || s.hostStartAttempted){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.hostStartAttempted=true;IORecursiveLockUnlock(s.gate);const auto raw=s.clocks->startOwnedHostGmu(owner,authority);
    IORecursiveLockLock(s.gate);s.hostFirstQueryReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::runHostProfile()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;if(IORecursiveLockHaveLock(s.gate))return kIOReturnNotReady;
    IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.hostTablesReady || !s.hostFirstQueryReady || !s.hostIrqArmed ||
       !s.gpuBootstrapBwReady || s.runtimeBorrower || s.hostProfileAttempted){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.hostProfileAttempted=true;IORecursiveLockUnlock(s.gate);
    // The original host engine consumes real prepared K80 tables and the
    // same owner's successful first-query sequence. No gate spans HFI waits.
    const auto raw=s.clocks->runOwnedHostProfile();
    IORecursiveLockLock(s.gate);s.hostProfileReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::requestHostDefaultClock()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;if(IORecursiveLockHaveLock(s.gate))return kIOReturnNotReady;
    IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.resourceProvider[0] || !s.hostProfileReady || s.hostClockAttempted || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.hostClockAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->requestOwnedHostDefaultClock(*s.resourceProvider[0]);
    IORecursiveLockLock(s.gate);s.hostClockReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::requestHostDefaultBandwidth()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;if(IORecursiveLockHaveLock(s.gate))return kIOReturnNotReady;
    IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.hostClockReady || s.hostBwAttempted || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.hostBwAttempted=true;IORecursiveLockUnlock(s.gate);const auto raw=s.clocks->requestOwnedHostDefaultBandwidth();
    IORecursiveLockLock(s.gate);s.hostBwReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::acquireHostGpuOob(OSObject &owner,const ZornGen7GpuStartAuthority26 &authority)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;if(IORecursiveLockHaveLock(s.gate))return kIOReturnNotReady;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.registerMapBorrower || !s.hostBwReady || !s.hostGpuMmuReady || s.hostOobAttempted || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.hostOobAttempted=true;IORecursiveLockUnlock(s.gate);const auto raw=s.clocks->acquireOwnedHostGpuOob(*this,*s.registerMapBorrower,owner,authority);
    IORecursiveLockLock(s.gate);s.hostOobReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

void Zorn26BindPreparedGpuZero(OSObject &,NativeAdrenoMemory &);
IOReturn ZornGen7InactiveOwner26::prepareHostGpuTables()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gate);
    if(!s.clocks || (!s.hostBwReady && !(s.firmwareSeedReady && s.firmwareHoldsAttempted)) || s.hostGpuTablesAttempted || s.hostOobAttempted || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.hostGpuTablesAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->prepareOwnedHostGpuTables(s.graph,s.memory,*this);
    IORecursiveLockLock(s.gate);
    s.hostGpuTablesReady=raw==kIOReturnSuccess;
    if(s.hostGpuTablesReady && s.result.zeroPreparedCpuOnly)
        Zorn26BindPreparedGpuZero(*this,s.zero);
    IORecursiveLockUnlock(s.gate);
    return raw;
}

IOReturn ZornGen7InactiveOwner26::startHostGpuMmu(OSObject &mmuOwner,OSObject &irqStreamOwner,
    const ZornGen7GpuMmuAuthority26 &authority,const ZornGen7SmmuFaultIrqAuthority26 &faults,
    const ZornGen7SmmuStreamAuthority26 &streams,unsigned budget)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;if(IORecursiveLockHaveLock(s.gate))return kIOReturnNotReady;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.registerMapBorrower || !s.hostBwReady || !s.hostGpuTablesReady || !s.result.zeroPreparedCpuOnly ||
       s.hostGpuMmuAttempted || s.hostOobAttempted || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.hostGpuMmuAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->startOwnedHostGpuMmu(s.zero,*this,*s.registerMapBorrower,mmuOwner,irqStreamOwner,authority,faults,streams,budget);
    IORecursiveLockLock(s.gate);s.hostGpuMmuReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::bindHostGpuCode()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;
    IORecursiveLockLock(s.gate);
    const bool direct=s.firmwareSeedReady && s.firmwareHoldsAttempted && s.hostGpuTablesReady;
    if(!s.clocks || !s.registerMapBorrower || (!direct && (!s.hostOobReady || !s.hostGpuMmuReady)) || !s.hostGpuTablesReady || s.hostGpuCodeAttempted || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.hostGpuCodeAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->bindOwnedHostGpuCode(s.graph,s.memory,*this,*s.registerMapBorrower);
    IORecursiveLockLock(s.gate);s.hostGpuCodeReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::configureHostGpuRegisters(OSObject &owner,const ZornGen7GpuRegisterAuthority26 &authority)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;if(IORecursiveLockHaveLock(s.gate))return kIOReturnNotReady;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.registerMapBorrower || !s.registryRoot || !s.resourceProvider[0] || !s.hostGpuCodeReady ||
       ((!s.firmwareSeedReady || !s.firmwareHoldsAttempted) && (!s.hostOobReady || !s.hostGpuMmuReady)) ||
       s.hostGpuRegistersAttempted || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.hostGpuRegistersAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->configureOwnedHostGpuRegisters(s.graph,s.memory,*this,*s.registryRoot,*s.resourceProvider[0],*s.registerMapBorrower,owner,authority);
    IORecursiveLockLock(s.gate);s.hostGpuRegistersReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::prepareHostGpuIrq(IOWorkLoop &loop,OSObject &owner,const ZornGen7GpuIrqAuthority26 &authority)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;if(IORecursiveLockHaveLock(s.gate))return kIOReturnNotReady;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.registerMapBorrower || !s.resourceProvider[0] || !s.hostGpuRegistersReady ||
       (!s.hostOobReady && !(s.firmwareSeedReady && s.firmwareHoldsAttempted)) ||
       s.hostGpuIrqAttempted || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.hostGpuIrqAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->prepareOwnedHostGpuIrq(*s.resourceProvider[0],*this,*s.registerMapBorrower,loop,owner,authority);
    IORecursiveLockLock(s.gate);s.hostGpuIrqReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::initializeHostCp(OSObject &owner,const ZornGen7CpStartAuthority26 &authority)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;if(IORecursiveLockHaveLock(s.gate))return kIOReturnNotReady;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.registerMapBorrower || !s.hostGpuIrqReady || !s.hostGpuRegistersReady ||
       (!s.hostOobReady && !(s.firmwareSeedReady && s.firmwareHoldsAttempted)) ||
       s.hostCpAttempted || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.hostCpAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->initializeOwnedHostCp(s.graph,s.memory,*this,*s.registerMapBorrower,owner,authority);
    IORecursiveLockLock(s.gate);s.hostCpInitIdle=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::authenticateHostZap(OSObject &owner,const ZornGen7ZapAuthority26 &authority)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;if(IORecursiveLockHaveLock(s.gate))return kIOReturnNotReady;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.registryRoot || !s.resourceProvider[0] || !s.hostCpInitIdle || (!s.cxSecurityReady && !(s.firmwareSeedReady && s.firmwareHoldsAttempted)) ||
       (!s.hostOobReady && !(s.firmwareSeedReady && s.firmwareHoldsAttempted)) || s.hostZapAttempted || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.hostZapAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->authenticateOwnedHostZap(*s.registryRoot,*s.resourceProvider[0],*this,owner,authority);
    IORecursiveLockLock(s.gate);s.hostZapAuthenticated=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::completeHostBootstrap(OSObject &owner,const ZornGen7CpBootstrapAuthority26 &authority)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;
    auto &s=*storage_;if(IORecursiveLockHaveLock(s.gate))return kIOReturnNotReady;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.hostZapAuthenticated || (!s.hostOobReady && !(s.firmwareSeedReady && s.firmwareHoldsAttempted)) || s.hostBootstrapAttempted || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.hostBootstrapAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->completeOwnedHostBootstrap(owner,authority);
    IORecursiveLockLock(s.gate);s.hostBootstrapReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::prepareHostDirectRuntime(OSObject &owner,const ZornGen7DirectRuntimeAuthority26 &authority,size_t capacity)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(s.gate))return kIOReturnNotReady;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.hostBootstrapReady || s.hostDirectRuntimeAttempted || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.hostDirectRuntimeAttempted=true;IORecursiveLockUnlock(s.gate);
    const auto raw=s.clocks->prepareOwnedDirectRuntime(owner,authority,capacity);
    IORecursiveLockLock(s.gate);s.hostDirectRuntimeReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::runHostKnownImage()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(s.gate))return kIOReturnNotReady;IORecursiveLockLock(s.gate);
    if(!s.clocks || !s.hostDirectRuntimeReady || s.hostKnownImageAttempted || s.runtimeBorrower){IORecursiveLockUnlock(s.gate);return kIOReturnNotReady;}
    s.hostKnownImageAttempted=true;IORecursiveLockUnlock(s.gate);const auto raw=s.clocks->runOwnedKnownImage();
    IORecursiveLockLock(s.gate);s.hostKnownImageReady=raw==kIOReturnSuccess;IORecursiveLockUnlock(s.gate);return raw;
}

IOReturn ZornGen7InactiveOwner26::copyHostKnownImageToConsole()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(s.gate))return kIOReturnNotReady;IORecursiveLockLock(s.gate);
    auto *board=s.clocks;const bool ready=board && s.hostKnownImageReady && !s.runtimeBorrower;
    IORecursiveLockUnlock(s.gate);return ready?board->copyOwnedKnownImageToConsole():kIOReturnNotReady;
}

IOReturn ZornGen7InactiveOwner26::publishHostKernelIo()
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(s.gate))return kIOReturnNotReady;IORecursiveLockLock(s.gate);
    auto *board=s.clocks;const bool ready=board && s.hostKnownImageReady && !s.runtimeBorrower;IORecursiveLockUnlock(s.gate);
    return ready?board->publishOwnedKernelIo():kIOReturnNotReady;
}

IOReturn ZornGen7InactiveOwner26::publishHostApplicationIo(OSObject &owner,const ZornGen7AppAuthority26 &authority)
{
    if(!storage_ || !storage_->gate || !zornGen7PreparationContext26())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(s.gate))return kIOReturnNotReady;IORecursiveLockLock(s.gate);
    auto *board=s.clocks;const bool ready=board && s.hostKnownImageReady && !s.runtimeBorrower;
    IORecursiveLockUnlock(s.gate);return ready?board->publishOwnedApplicationIo(owner,authority):kIOReturnNotReady;
}

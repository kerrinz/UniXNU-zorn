// SPDX-License-Identifier: GPL-2.0-only
#pragma once
#include "ZornGen7NativeSmmuIrqResult26.h"
#include "ZornGen7QtbFence26.h"
#include "sparse/ArmSmmu4K.h"
#include "ZornGen7NativeSmmuProbeResult26.h"
#include "ZornGen7SmmuRuntimePm26.h"
#include "ZornGen7RegisterConfig.h"
class ZornGen7GmuIrq26;class ZornGen7ProcessTables26;
enum class ZornGen7ProcessTableOperation26 : unsigned;
class ZornGen7DirectHfi26;
class ZornGen7HwschedHfi26;
#include <IOKit/IOMemoryDescriptor.h>
class ZornGen7DarwinBoardOwner;struct FhgStorage;
class HoujiFullHostNativeMemory;class NativeAdrenoMemory;
struct ZornGen7GpuMmuAuthority26;
class ZornGen7RegisterMaps26;
struct ZornGen7AtomicSmmuGuard26;
struct ZornGen7SmmuFaultIrqAuthority26;
struct ZornGen7SmmuStreamAuthority26;
struct ZornGen7GmuLoadAuthority26;
struct ZornGen7SmmuColdAuthority26;
// The actual handoff/lease implementation must establish bank, ASID, stream,
// fault IRQ and security ownership. A fresh CPU bitmap or ID1 is not a lease.
struct ZornGen7SmmuBankAuthority26 {
    void *cookie=nullptr;
    int (*acquireActualBank)(void *,IOService &actualController,IOService &actualConsumer,
        uint16_t bank,uint16_t asid,const uint32_t *actualPackedIds,size_t actualCount)=nullptr;
};
class ZornGen7SmmuDomain26 final : public OSObject {
    OSDeclareDefaultStructors(ZornGen7SmmuDomain26);
public:
    void free() override;
private:
    friend class ZornGen7DarwinBoardOwner;
    friend class ZornGen7HostGpuCode26;
    friend class ZornGen7HostRing26;
    friend class ZornGen7HostGpuRegisters26;
    friend class ZornGen7DirectHfi26;
    friend class ZornGen7HwschedHfi26;
    struct Reservation {
        uint16_t bank=0,asid=0;size_t context_offset=0,context_bytes=0;
        IOService *consumer=nullptr;bool acquired=false;
    };
    static IOReturn createAndProbe(IOService &,ZornGen7SmmuRuntimePm26 &,const ArmSmmu4KIo &,
        IORecursiveLock &,OSObject &actualControllerOwner,OSObject &actualAuthorityOwner,
        const ZornGen7SmmuBankAuthority26 &,ZornGen7SmmuDomain26 *&actualPartialOutput);
    static IOReturn createNativeAndProbe(IOService &,ZornGen7SmmuRuntimePm26 &,const ArmSmmu4KIo &,
        IORecursiveLock &,OSObject &,OSObject &,ZornGen7SmmuDomain26 *&);
    static IOReturn createAndProbeImpl(IOService &,ZornGen7SmmuRuntimePm26 &,const ArmSmmu4KIo &,
        IORecursiveLock &,OSObject &,OSObject &,const ZornGen7SmmuBankAuthority26 *,ZornGen7SmmuDomain26 *&);
    void copyProbeResult(ZornGen7NativeSmmuProbeResult26 &) const;
    IOReturn prepareNativeQtbFence(OSObject &,class ZornGen7IccInputs26 &,unsigned);
    IOReturn resumeNativeQtbAfterColdInit();
    IOReturn prepareNativeColdController(OSObject &,const ZornGen7SmmuColdAuthority26 &,unsigned);
    IOReturn haltNativeQtb(IOService &,IOMemoryDescriptor &,class ZornGen7IccInputs26 &,OSObject &,unsigned,ZornGen7QtbFenceResult26 &);
    IOReturn prepareNativeActiveGlobalFaults(ZornGen7RegisterMaps26 &,ZornGen7NativeSmmuControlResult26 &,unsigned);
    IOReturn prepareNativeGlobalMaskedIrq(ZornGen7RegisterMaps26 &,OSObject &,ZornGen7NativeSmmuIrqResult26 &);
    // Actual source fwspec producer supplies immutable packed IDs and its
    // lifetime. No bank, ASID, provider success or device result is supplied.
    ZornGen7ColdBoot::OperationResult reserveActual(IOService &,const uint32_t *,size_t,
        OSObject &actualFwspecOwner,Reservation &actualEmptyOutput);
    ZornGen7ColdBoot::OperationResult reserveNativeEndpoints(IOService &actualPlatform,
        IORegistryEntry &actualRoot,IOService &actualGmu,OSObject &actualTreeOwner);
    IOReturn bindContextViews(ZornGen7RegisterMaps26 &,IOMemoryDescriptor &,
        OSObject &actualGuardOwner,const ZornGen7AtomicSmmuGuard26 &);
    IOReturn transitionHostProcessTables(class ZornGen7HostRing26 &,ZornGen7ProcessTableOperation26,
        ZornGen7ProcessTables26 *&,unsigned explicitInputBits,size_t explicitSpanBudget);
    IOReturn prepareRootPages();
    IOReturn prepareSparseArenas();
    IOReturn prepareGmuContextImage();
    IOReturn attachHostDirectRuntime(class ZornGen7HostRing26 &,class ZornGen7DirectVm26 &,
        class ZornGen7DirectSubmit26 &,class NativeAdrenoRing &,OSObject &,
        const struct ZornGen7DirectRuntimeAuthority26 &,size_t explicitSpanBudget,struct ZornGen7PresentProgress26 &);
    bool runtimeEndpointBindingsMatch(IOService &,IOService &,IOService &) const;
    static ZornSmmuSparse4KStatus observeDirectRuntime(void *,bool full);
    static ZornSmmuSparse4KStatus faultDirectRuntime(void *);
    static ZornSmmuSparse4KStatus haltDirectRuntime(void *);
    static ZornSmmuSparse4KStatus releaseDirectRuntime(void *);
    static IOReturn beginDirectSubmission(void *);
    static void endDirectSubmission(void *);
    static ZornSmmuSparse4KStatus observeProcessRuntime(void *,bool full);
    static ZornSmmuSparse4KStatus faultProcessRuntime(void *);
    static ZornSmmuSparse4KStatus haltProcessRuntime(void *);
    static ZornSmmuSparse4KStatus releaseProcessRuntime(void *);
    bool nativeProcessSubmissionHeldForRing(const class ZornGen7HostRing26 &) const;
    static IOReturn beginProcessSubmission(void *);
    static void endProcessSubmission(void *);
    IOReturn bindNativePostCpAuthority(OSObject &,const ZornGen7GpuMmuAuthority26 &);
    IOReturn restoreHostPostCpContext(class ZornGen7HostRing26 &);
    // Board-owned, read-only validation for the whole-operation grants. These
    // checks bind the callback request to the exact live reservations and
    // backing already retained by this domain; observations use its guarded
    // SMMU access paths.
    IOReturn verifyHostGpuMmuStartAuthorization(IOService &,IOService &,IOService &,
        const uint16_t (&)[2],const uint16_t (&)[2],const uint32_t (&)[2],
        IOMemoryDescriptor &,uint64_t);
    IOReturn verifyHostGpuPostCpRestoreAuthorization(IOService &,IOService &,
        uint16_t,uint16_t,uint32_t,uint32_t);
    IOReturn verifyHostRuntimeContexts();
    IOReturn buildHostFirstContext(class ZornGen7HostRing26 &,uint32_t (&actualWords)[25]);
    IOReturn prepareHostGpuTables(FhgStorage &,HoujiFullHostNativeMemory &,OSObject &actualAllocatingParent);
    IOReturn startHostGpuMmu(NativeAdrenoMemory &,OSObject &actualAllocatingParent,OSObject &actualMmuAuthorityOwner,OSObject &actualIrqStreamAuthorityOwner,
        ZornGen7IccInputs26 &actualTbuPower,const ZornGen7GpuMmuAuthority26 &,
        const ZornGen7SmmuFaultIrqAuthority26 &,const ZornGen7SmmuStreamAuthority26 &,unsigned explicitPollBudget);
    IOReturn holdGmuFirmware(HoujiFullHostNativeMemory &,OSObject &);
    IOReturn prepareGlobalFaultReporting(OSObject &,const ZornGen7SmmuFaultIrqAuthority26 &,unsigned explicitPollBudget);
    IOReturn prepareControllerAndGlobalFaults(OSObject &,const ZornGen7SmmuColdAuthority26 &,
        const ZornGen7SmmuFaultIrqAuthority26 &,unsigned explicitPollBudget);
    IOReturn installGmuFaultIrq(OSObject &,const ZornGen7SmmuFaultIrqAuthority26 &);
    IOReturn prepareGmuStreamSlot(OSObject &,const ZornGen7SmmuStreamAuthority26 &);
    IOReturn programGmuContext(unsigned explicitPollBudget);
    IOReturn activateGmuStream();
    IOReturn loadGmuTcmAndShadow(OSObject &,const ZornGen7GmuLoadAuthority26 &);
    IOReturn configureGmuRegisters(ZornGen7GmuIrq26 &,uint32_t actualCoreRevision,
        ZornGen7RegisterConfig::KnownState actualBcl);
    IOReturn prepareDirectHfi(ZornGen7GmuIrq26 &,IOWorkLoop &,ZornGen7DirectHfi26 *&);
    IOReturn readActualGmuVersions();
    IOReturn readHwschedGmuVersions(ZornGen7GmuIrq26 &,uint32_t (&actualOutput)[5]);
    IOReturn readHostGmuVersions(ZornGen7GmuIrq26 &,uint32_t (&actualOutput)[5]);
    IOReturn prepareHostHfi(ZornGen7GmuIrq26 &,IOWorkLoop &,ZornGen7HwschedHfi26 *&);
    IOReturn prepareHwschedHfi(ZornGen7GmuIrq26 &,IOWorkLoop &,ZornGen7HwschedHfi26 *&);
    bool faulted() const;
    static void stopForContextFault(void *);
    friend IOReturn ZornGen7SeedFirmwareAssets26(ZornGen7SmmuDomain26 &,
        const HoujiFullHostNativeMemory &,OSObject &);
    IOReturn seedGmuFirmware(const HoujiFullHostNativeMemory &,OSObject &,
        const uint8_t *actualImmutableFirmware,size_t actualBytes);
    IOReturn seedGmuHwschedFirmware(const HoujiFullHostNativeMemory &,OSObject &,const uint8_t *,size_t);
    IOReturn seedGmuFirmwareInternal(const HoujiFullHostNativeMemory &,OSObject &,const uint8_t *,size_t,bool actualHwschedCandidate);
    struct Storage;Storage *storage_=nullptr;bool pinned_=false;
};

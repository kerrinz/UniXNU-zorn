/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#pragma once
#include "ZornGen7CpStartAuthority26.h"
#include <IOKit/IOLocks.h>
#include <mach/mach_types.h>
#include <libkern/c++/OSObject.h>
enum class ZornGen7ProcessTableOperation26 : unsigned;enum class ZornGen7AppOperation26 : unsigned;class ZornGen7ProcessTables26;
struct FhgStorage;struct NativeAdrenoIrqResult;class HoujiFullHostNativeMemory;
class ZornGen7InactiveOwner26;class ZornGen7RegisterMaps26;class ZornGen7GpuIrq26;
class ZornGen7DirectHfi26;class ZornGen7GmuIrq26;class ZornGen7HwschedHfi26;class ZornGen7SmmuDomain26;class ZornGen7HostGpuRegisters26;
// Real retained initial-ring owner,not a packet/BO/provider fixture. First
// phase ends ONLY at actual CP_INIT read-pointer+idle observation. ZAP,
// authenticated mode transition and NativeRing adoption remain separate.
class ZornGen7HostRing26 final : public OSObject {
    OSDeclareDefaultStructors(ZornGen7HostRing26);
public:
    void free() override;
    // CPU-only framebuffer lease;no MMIO,permission acquisition or fabricated fence.
    static uint32_t capturePresentationFence();
    static int beginPresentation(uint32_t);
    static void endPresentation();
private:
    IOReturn bindPresentationOwner();
    friend class ZornGen7HwschedHfi26;friend class ZornGen7DirectHfi26;
    bool bootstrapReadyForOobTransport(const OSObject &) const;
    bool bootstrapReadyForOob(const ZornGen7HwschedHfi26 &) const;
    friend class ZornGen7DarwinBoardOwner;friend class ZornGen7ZapOwner26;friend class ZornGen7SmmuDomain26;
    bool nativeApplicationBinding(class IOUserClient &,task_t,unsigned phase,ZornGen7AppOperation26) const;
    IOReturn prepareApplicationExecution(class IOUserClient &,task_t,UInt32 actualOpenType,OSObject &,
        const struct ZornGen7AppAuthority26 &,class ZornGen7AppExecution26 *&);
    IOReturn checkApplicationExecution(class IOUserClient &,class ZornGen7AppExecution26 &,
        ZornGen7AppOperation26);
    IOReturn closeApplicationExecution(class IOUserClient &,class ZornGen7AppExecution26 *&);
    IOReturn beginApplicationOperation(class IOUserClient &,ZornGen7AppOperation26,class ZornGen7AppExecution26 *&);
    IOReturn finishApplicationOperation(class ZornGen7AppExecution26 &,IOReturn);
    bool applicationOperationHeld() const;
    bool processExecutionHealthy() const;
    bool processConnectionHeld(class IOUserClient &) const;
    IOReturn openApplicationProcess(class IOUserClient &,class ZornGen7AppExecution26 &,ZornGen7ProcessTables26 *&);
    IOReturn dispatchApplicationProcess(class IOUserClient &,class ZornGen7AppExecution26 &,ZornGen7ProcessTables26 &,
        uint32_t,const void *,size_t,void *,size_t);
    IOReturn applicationIoLeases(class IOUserClient &,class ZornGen7AppExecution26 &,ZornGen7ProcessTables26 &,
        const struct NativeAdrenoAbiBoCpuUnmap &,uint32_t &);
    IOReturn copyApplicationIoView(class IOUserClient &,class ZornGen7AppExecution26 &,ZornGen7ProcessTables26 &,
        uint32_t,class IOMemoryDescriptor *&);
    IOReturn closeApplicationProcess(class IOUserClient &,class ZornGen7AppExecution26 &,ZornGen7ProcessTables26 *&);
    IOReturn acquireApplicationOob(class IOUserClient &,class ZornGen7AppExecution26 &);
    IOReturn releaseApplicationOob(class IOUserClient &,class ZornGen7AppExecution26 &);
    bool applicationOobPermission(const ZornGen7DirectHfi26 &,class ZornGen7AppExecution26 &,bool release);
    bool applicationOobReleaseReady(const ZornGen7DirectHfi26 &,const class ZornGen7AppExecution26 &) const;
    bool applicationOobPermissionForTransport(const OSObject &,class ZornGen7AppExecution26 &,bool release);
    bool applicationOobReleaseReadyForTransport(const OSObject &,const class ZornGen7AppExecution26 &) const;
    bool applicationOobHeldForTransport(const class ZornGen7AppExecution26 &) const;
    bool applicationOobPermission(const ZornGen7HwschedHfi26 &,class ZornGen7AppExecution26 &,bool release);
    bool applicationOobReleaseReady(const ZornGen7HwschedHfi26 &,const class ZornGen7AppExecution26 &) const;
    IOReturn runKnownImage();IOReturn runKnownImageBody();
    IOReturn copyKnownImageToConsole();
    friend class ZornGen7DirectIoService26;friend class ZornGen7DirectIoClient26;
    friend class ZornGen7AppIoClient26;
    IOReturn publishKernelIo();
    IOReturn runKernelClientProbe();IOReturn runKernelClientProbeBody();
    void recordKernelClientProbe(IOReturn) const;
    IOReturn publishApplicationIo(OSObject &actualAuthorityOwner,const struct ZornGen7AppAuthority26 &);
    IOReturn beginKernelIo(class IOUserClient &,task_t actualOwningTask);
    IOReturn dispatchKernelIo(class IOUserClient &,uint32_t,const void *,size_t,void *,size_t);
    IOReturn closeKernelIo(class IOUserClient &);
    IOReturn closeKernelIoBase(class IOUserClient &);
    IOReturn initializeKernelProcess(class IOUserClient &);
    IOReturn copyKernelIoView(class IOUserClient &,uint32_t,class IOMemoryDescriptor *&);
    IOReturn kernelIoLeases(class IOUserClient &,const struct NativeAdrenoAbiBoCpuUnmap &,uint32_t &);
    bool nativeKernelClientBinding(class IOUserClient &,unsigned) const;
    bool nativeKernelClientCanRelease(class IOUserClient &) const;
    bool kernelClientPermissionHeld(const ZornGen7HwschedHfi26 &) const;
    bool kernelClientPermissionHeld(const ZornGen7DirectHfi26 &) const;
    bool kernelClientPermissionHeldForTransport(const OSObject &) const;
    bool kernelClientExecutionHealthy() const;
    bool kernelClientReadyToRelease(const ZornGen7HwschedHfi26 &) const;
    bool kernelClientReadyToRelease(const ZornGen7DirectHfi26 &) const;
    bool kernelClientReadyToReleaseForTransport(const OSObject &) const;
    IOReturn quiesceKernelIo();
    bool nativeProcessTableLeaseHealthy(const ZornGen7SmmuDomain26 &,const ZornGen7ProcessTables26 &) const;
    IOReturn beginNativeProcessTableLease(const ZornGen7SmmuDomain26 &,ZornGen7ProcessTables26 &);
    IOReturn endNativeProcessTableLease(const ZornGen7SmmuDomain26 &,ZornGen7ProcessTables26 &);
    bool nativeProcessContextHeldForDomain(const ZornGen7SmmuDomain26 &,const ZornGen7ProcessTables26 &) const;
    // Diagnostic only; no authority or hardware operation.
    void observeApplicationPrepare(uint32_t stage,IOReturn raw,uint32_t detail);
    bool processTransitionHeldForDomain(const ZornGen7SmmuDomain26 &) const;
    IOReturn openProcessClient(class IOUserClient &,ZornGen7ProcessTables26 &,task_t actualOwningTask);
    IOReturn dispatchProcessClient(class IOUserClient &,ZornGen7ProcessTables26 &,task_t actualCallingTask,
        uint32_t,const void *,size_t,void *,size_t);
    IOReturn closeProcessClient(class IOUserClient &,ZornGen7ProcessTables26 &);
    // Existing kernel execution grant only;not a new userspace operation.
    IOReturn transitionProcessTables(class IOUserClient &,ZornGen7ProcessTableOperation26,
        ZornGen7ProcessTables26 *&,unsigned explicitInputBits,size_t explicitSpanBudget);
    bool nativeKernelTaskBinding(class IOMemoryDescriptor &,unsigned) const;
    bool nativeKernelTaskCanRelease(class IOMemoryDescriptor &) const;
    bool nativeKernelTableLeaseHealthy(const ZornGen7SmmuDomain26 &) const;
    IOReturn beginNativeKernelTableLease(const ZornGen7SmmuDomain26 &);
    IOReturn endNativeKernelTableLease(const ZornGen7SmmuDomain26 &);
    void recordKnownImage(IOReturn) const;
    bool kernelTaskPermissionHeld(const ZornGen7HwschedHfi26 &) const;
    bool kernelTaskPermissionHeld(const ZornGen7DirectHfi26 &) const;
    bool kernelTaskPermissionHeldForTransport(const OSObject &) const;
    bool kernelTaskReadyToRelease(const ZornGen7DirectHfi26 &) const;
    bool kernelTaskReadyToReleaseForTransport(const OSObject &) const;
    bool kernelTaskExecutionHealthy() const;bool kernelTaskReadyToRelease(const ZornGen7HwschedHfi26 &) const;
    bool completedBootstrapForDomain(const ZornGen7SmmuDomain26 &) const;
    IOReturn prepareDirectRuntime(OSObject &,const struct ZornGen7DirectRuntimeAuthority26 &,size_t explicitSpanBudget);
    bool contextIdleForDomain(const ZornGen7SmmuDomain26 &) const;
    bool modeExitIdleForDomain(const ZornGen7SmmuDomain26 &) const;
    bool claimInitialIdleForZap();bool zapWindowHealthy() const;
    static IOReturn create(IORecursiveLock &,FhgStorage &,HoujiFullHostNativeMemory &,ZornGen7InactiveOwner26 &,
        ZornGen7RegisterMaps26 &,ZornGen7GpuIrq26 &,ZornGen7GmuIrq26 &,ZornGen7HwschedHfi26 &,
        ZornGen7SmmuDomain26 &,ZornGen7HostGpuRegisters26 &,OSObject &actualAuthorityOwner,
        const ZornGen7CpStartAuthority26 &,ZornGen7HostRing26 *&actualPartialOutput);
    static IOReturn create(IORecursiveLock &,FhgStorage &,HoujiFullHostNativeMemory &,ZornGen7InactiveOwner26 &,
        ZornGen7RegisterMaps26 &,ZornGen7GpuIrq26 &,ZornGen7GmuIrq26 &,ZornGen7DirectHfi26 &,
        ZornGen7SmmuDomain26 &,ZornGen7HostGpuRegisters26 &,OSObject &,
        const ZornGen7CpStartAuthority26 &,ZornGen7HostRing26 *&);
    static IOReturn createImpl(IORecursiveLock &,FhgStorage &,HoujiFullHostNativeMemory &,ZornGen7InactiveOwner26 &,
        ZornGen7RegisterMaps26 &,ZornGen7GpuIrq26 &,ZornGen7GmuIrq26 &,OSObject &,bool (*)(const OSObject &),ZornGen7HwschedHfi26 *,
        ZornGen7SmmuDomain26 &,ZornGen7HostGpuRegisters26 &,OSObject &,
        const ZornGen7CpStartAuthority26 &,ZornGen7HostRing26 *&);
    IOReturn prepare();IOReturn runInitialization();
    IOReturn completeAuthenticatedBootstrap(class ZornGen7ZapOwner26 &,OSObject &,const struct ZornGen7CpBootstrapAuthority26 &);
    IOReturn runAuthenticatedBootstrap();bool bootstrapHealthy() const;
    IOReturn publishBootstrap(unsigned,const uint32_t *,unsigned);IOReturn acquireScratch();
    static int nativeRead(void *,uint32_t,uint32_t *);static int nativeWrite(void *,uint32_t,uint32_t);
    static int nativeBarrier(void *);static int nativePublish(void *,const volatile uint32_t *,size_t);
    static int nativeAcquire(void *,volatile uint32_t *,size_t);static uint64_t nativeNow(void *);static int nativeIdle(void *);
    static int guard(void *);static int read(void *,uint32_t,uint32_t *);static int write(void *,uint32_t,uint32_t);
    static int publish(void *,unsigned,const uint32_t *,unsigned);static int delay(void *,unsigned);
    static int consume(OSObject &,const NativeAdrenoIrqResult &);
    struct Storage;Storage *storage_=nullptr;bool pinned_=false;
};

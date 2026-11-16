// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include <IOKit/IOUserClient.h>
#include <IOKit/IOMemoryDescriptor.h>
#include <IOKit/IOLocks.h>
class ZornGen7HostRing26;class ZornGen7RegisterMaps26;class ZornGen7HwschedHfi26;
enum class ZornGen7AppOperation26 : unsigned { PrepareTables,Map,Submit,Wait,CpuView,Close,OobAcquire,OobRelease,Timestamp };
// Distinct,mandatory real application-session authority. Never populate this
// by casting/copying kernel-client callbacks or supplying a successful stub.
// acquire must hold actual powered GPU/GMU/MMU/IRQ/security and foreign
// exclusion continuously through successful release;check validates the
// current whole declared operation,not merely a past successful acquisition.
// Independent native per-access guards remain mandatory throughout.
// Its actual code/storage owner remains retained through every callback and
// any unknown outcome. Software MACF/task references alone cannot supply it.
struct ZornGen7AppAuthority26 {
    void *cookie=nullptr;
    IOReturn (*acquire)(void *,IOUserClient &,task_t actualOpeningTask,
        ZornGen7HostRing26 &,IOService &actualGpu,IOMemoryDescriptor &actualGpuRegisters,
        IOService &actualGmu,IOMemoryDescriptor &actualGmuRegisters)=nullptr;
    IOReturn (*check)(void *,IOUserClient &,task_t actualOpeningTask,task_t actualCallingTask,
        ZornGen7AppOperation26)=nullptr;
    // Actual provider relinquishes its app execution session only after its
    // real conditions hold. raw0 is not a new reset/power-off/DMA-stop proof.
    IOReturn (*release)(void *,IOUserClient &,task_t actualOpeningTask)=nullptr;
};
class ZornGen7AppExecution26 final : public OSObject {
    OSDeclareDefaultStructors(ZornGen7AppExecution26);
public:
    void free() override;
private:
    friend class ZornGen7RegisterMaps26;friend class ZornGen7HostRing26;friend class ZornGen7HwschedHfi26;friend class ZornGen7DirectHfi26;
    // Per-real-session record. Never reset a failed/consumed attempt or copy
    // a kernel OOB result into a new application's permission window.
    struct OobRecord {
        OSObject *owner=nullptr; // exact retained HWSCHED or DirectHfi transport identity
        bool attempted=false,requestReturned=false,ackObserved=false,ackCleared=false,gxOn=false;
        bool releaseAttempted=false,releaseWriteReturned=false;
        uint32_t ack=0,host=0,gx=0;int raw=0;
    } oob_;
    static IOReturn create(ZornGen7RegisterMaps26 &,ZornGen7HostRing26 &,IORecursiveLock &,
        IOUserClient &,task_t,OSObject &actualAuthorityCodeAndStorage,
        const ZornGen7AppAuthority26 &,IOService &,IOMemoryDescriptor &,IOService &,
        IOMemoryDescriptor &,ZornGen7AppExecution26 *&actualPartialOutput);
    IOReturn checkCurrent(IOUserClient &,ZornGen7AppOperation26);
    IOReturn closeAcquiredSession(IOUserClient &);
    enum class Phase { Retaining,Acquiring,Held,Checking,Closing,Released,Failed };
    IOLock *gate_=nullptr;Phase phase_=Phase::Retaining;bool pinned_=false;
    IORecursiveLock *driverGate_=nullptr;ZornGen7AppAuthority26 authority_{};
    ZornGen7RegisterMaps26 *maps_=nullptr;ZornGen7HostRing26 *ring_=nullptr;
    OSObject *codeOwner_=nullptr;IOUserClient *client_=nullptr;task_t task_=TASK_NULL;
    IOService *gpu_=nullptr,*gmu_=nullptr;IOMemoryDescriptor *gpuRegisters_=nullptr,*gmuRegisters_=nullptr;
    IOReturn last_=kIOReturnNotReady;
};

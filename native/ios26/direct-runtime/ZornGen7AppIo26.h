// SPDX-License-Identifier: MIT
#pragma once
#include <IOKit/IOService.h>
#include "HoujiIOAccelerator26.h"
#include <IOKit/IOUserClient.h>
#include <IOKit/IOLocks.h>
#include "Adreno740/NativeAdrenoABI.h"
#include "ZornGen7AppExecution26.h"
class ZornGen7ProcessTables26;class ZornGen7AppIoClient26;
class ZornGen7HostRing26;
// Use the already linked OS26 source registry base. Do not define a second
// IOAcceleratorES or import the separately qualified OS17 original vtable.
class ZornGen7AppIoService26 final : public IOAcceleratorES {
    OSDeclareDefaultStructors(ZornGen7AppIoService26);
    friend class ZornGen7AppIoClient26;
    ZornGen7HostRing26 *owner_=nullptr;IOLock *clients_=nullptr;
    bool reserved_=false;ZornGen7AppIoClient26 *client_=nullptr;
    void returnClientSlot(ZornGen7AppIoClient26 *actualClient);
    OSObject *authorityOwner_=nullptr;ZornGen7AppAuthority26 authority_{};
public:
    static IOReturn createAndPublish(ZornGen7HostRing26 &,OSObject &actualAuthorityOwner,const ZornGen7AppAuthority26 &,IOService *&);
    IOReturn newUserClient(task_t,void *,UInt32,OSDictionary *,IOUserClient **) override;
    // Own discovery properties are frozen by the actual publisher. Do not
    // inherit the framebuffer base's user-controlled Metal property switch.
    IOReturn setProperties(OSObject *) override;
    void free() override;
};
class ZornGen7AppIoClient26 final : public IOUserClient {
    OSDeclareDefaultStructors(ZornGen7AppIoClient26);
    friend class ZornGen7AppIoService26;friend class ZornGen7HostRing26;
    bool matchesOwnedSession(const ZornGen7HostRing26 &,const IOService *,task_t,bool closing) const;
    thread_t closingThread_=THREAD_NULL;
    ZornGen7HostRing26 *owner_=nullptr;IOLock *serial_=nullptr;
    ZornGen7AppIoService26 *service_=nullptr;
    task_t openingTask_=TASK_NULL;
    OSObject *authorityOwner_=nullptr;ZornGen7AppAuthority26 authority_{};
    ZornGen7AppExecution26 *execution_=nullptr;ZornGen7ProcessTables26 *process_=nullptr;
    bool attempted_=false;IOReturn attemptRaw_=kIOReturnNotReady;
    IOReturn ensureProcess();
    bool live_=false,pinned_=false,closing_=false;IOReturn viewError_=kIOReturnSuccess;
    struct View {IOMemoryDescriptor *descriptor=nullptr;IOMemoryMap *quarantine=nullptr;};
    View *views_=nullptr;static constexpr size_t ViewCount=4096;
    IOReturn dropViews(uint32_t);
    IOReturn run(uint32_t,const void *,size_t,void *,size_t);
    static IOReturn action(OSObject *,void *,IOExternalMethodArguments *);
public:
    IOReturn externalMethod(uint32_t,IOExternalMethodArguments *,IOExternalMethodDispatch *,OSObject *,void *) override;
    IOReturn clientMemoryForType(UInt32,IOOptionBits *,IOMemoryDescriptor **) override;
    IOReturn clientClose() override;
    void free() override;
};

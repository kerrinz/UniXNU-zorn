/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#pragma once
#include "ZornGen7GpuRegisterAuthority26.h"
#include <IOKit/IOLocks.h>
#include <libkern/c++/OSObject.h>
struct FhgStorage;class HoujiFullHostNativeMemory;class ZornGen7InactiveOwner26;class ZornGen7RegisterMaps26;
class ZornGen7DirectHfi26;class ZornGen7HwschedHfi26;class ZornGen7GmuIrq26;class ZornGen7SmmuDomain26;
class ZornGen7HostGpuRegisters26 final : public OSObject {
    OSDeclareDefaultStructors(ZornGen7HostGpuRegisters26);
public:
    void free() override;
private:
    friend class ZornGen7DarwinBoardOwner;friend class ZornGen7HostRing26;
    friend class ZornGen7GpuIrq26;
    bool holdsCompletedIrqPrerequisite(IOService &,ZornGen7InactiveOwner26 &,ZornGen7RegisterMaps26 &) const;
    IOReturn copyConfiguredDeviceInfo(struct NativeAdrenoAbiDeviceInfo &) const;
    bool verifyRecord(const class NativeAdrenoMemory &) const;
    static IOReturn create(IORecursiveLock &,FhgStorage &,HoujiFullHostNativeMemory &,ZornGen7InactiveOwner26 &,
        IORegistryEntry &actualRoot,IOService &actualGpu,ZornGen7RegisterMaps26 &,ZornGen7GmuIrq26 &,
        ZornGen7HwschedHfi26 &,ZornGen7SmmuDomain26 &,OSObject &actualAuthorityOwner,
        const ZornGen7GpuRegisterAuthority26 &,ZornGen7HostGpuRegisters26 *&actualPartialOutput);
    static IOReturn create(IORecursiveLock &,FhgStorage &,HoujiFullHostNativeMemory &,ZornGen7InactiveOwner26 &,
        IORegistryEntry &actualRoot,IOService &actualGpu,ZornGen7RegisterMaps26 &,ZornGen7GmuIrq26 &,
        ZornGen7DirectHfi26 &,ZornGen7SmmuDomain26 &,OSObject &actualAuthorityOwner,
        const ZornGen7GpuRegisterAuthority26 &,ZornGen7HostGpuRegisters26 *&actualPartialOutput);
    static IOReturn createTransport(IORecursiveLock &,FhgStorage &,HoujiFullHostNativeMemory &,ZornGen7InactiveOwner26 &,
        IORegistryEntry &actualRoot,IOService &actualGpu,ZornGen7RegisterMaps26 &,ZornGen7GmuIrq26 &,
        OSObject &,bool (*)(OSObject &),ZornGen7SmmuDomain26 &,OSObject &actualAuthorityOwner,
        const ZornGen7GpuRegisterAuthority26 &,ZornGen7HostGpuRegisters26 *&actualPartialOutput);
    IOReturn run();
    static int guard(void *);static int read(void *,uint32_t,uint32_t *);static int write(void *,uint32_t,uint32_t);
    static int delay(void *,unsigned);static int publish(void *,const uint32_t *,unsigned);
    struct Storage;Storage *storage_=nullptr;bool pinned_=false;
};

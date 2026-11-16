/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#pragma once
#include <IOKit/IOLocks.h>
#include <IOKit/IOReturn.h>
#include <libkern/c++/OSObject.h>
struct FhgStorage;class HoujiFullHostNativeMemory;class ZornGen7RegisterMaps26;
class ZornGen7DirectHfi26;class ZornGen7GmuIrq26;class ZornGen7HwschedHfi26;class ZornGen7SmmuDomain26;class ZornGen7InactiveOwner26;
class ZornGen7HostGpuCode26 final : public OSObject {
    OSDeclareDefaultStructors(ZornGen7HostGpuCode26);
public:
    void free() override;
private:
    friend class ZornGen7DarwinBoardOwner;
    static IOReturn create(IORecursiveLock &,FhgStorage &,HoujiFullHostNativeMemory &,
        ZornGen7InactiveOwner26 &,ZornGen7RegisterMaps26 &,ZornGen7GmuIrq26 &,
        ZornGen7HwschedHfi26 &,ZornGen7SmmuDomain26 &,ZornGen7HostGpuCode26 *&actualPartialOutput);
    static IOReturn create(IORecursiveLock &,FhgStorage &,HoujiFullHostNativeMemory &,
        ZornGen7InactiveOwner26 &,ZornGen7RegisterMaps26 &,ZornGen7GmuIrq26 &,
        ZornGen7DirectHfi26 &,ZornGen7SmmuDomain26 &,ZornGen7HostGpuCode26 *&);
    static IOReturn createTransport(IORecursiveLock &,FhgStorage &,HoujiFullHostNativeMemory &,
        ZornGen7InactiveOwner26 &,ZornGen7RegisterMaps26 &,ZornGen7GmuIrq26 &,
        OSObject &,bool (*)(OSObject &),ZornGen7SmmuDomain26 &,ZornGen7HostGpuCode26 *&);
    IOReturn run();
    static int guard(void *);static int read(void *,uint32_t,uint32_t *);static int write(void *,uint32_t,uint32_t);
    struct Storage;Storage *storage_=nullptr;bool pinned_=false;
};

// SPDX-License-Identifier: GPL-2.0-only
#pragma once
#include <IOKit/IOWorkLoop.h>
#include <IOKit/IOLocks.h>
#include <libkern/c++/OSObject.h>
class NativeAdrenoMemory;
class ZornGen7BootBuffers26;
class ZornGen7SmmuDomain26;
class ZornGen7GmuIrq26;
class ZornGen7RegisterMaps26;
class ZornGen7DarwinBoardOwner;
// Actual pinned Gen7 non-HWSCHED three-queue transport. Source table capacity17,
// active3, rings at848+q*4096. It is neither the public A6xx layout nor a
// legacy4K NativeMemory alias. Prepared/linked is not firmware qualification.
class ZornGen7DirectHfi26 final : public OSObject {
    OSDeclareDefaultStructors(ZornGen7DirectHfi26);
public:
    void free() override;
    bool halted() const;
private:
    friend class ZornGen7BootBuffers26;
    friend class ZornGen7DarwinBoardOwner;
    friend class ZornGen7HostTables26;
    friend class ZornGen7HostRing26;
    IOReturn bindHeldHostGpuOob(OSObject &,IORecursiveLock &,bool (*)(OSObject &,const ZornGen7DirectHfi26 &));
    bool bootstrapOobHeld() const;
    bool bootstrapOobReleaseReturned() const;
    IOReturn releaseHostGpuOobAfterBootstrap(class ZornGen7HostRing26 &);
    IOReturn acquireKernelTaskOob(class ZornGen7HostRing26 &);
    bool kernelTaskOobHeld(const class ZornGen7HostRing26 &) const;
    IOReturn releaseKernelTaskOob(class ZornGen7HostRing26 &);
    void copyKernelTaskOobObservation(uint32_t (&)[8]) const;
    IOReturn acquireKernelClientOob(class ZornGen7HostRing26 &);
    bool kernelClientOobHeld(const class ZornGen7HostRing26 &) const;
    IOReturn releaseKernelClientOob(class ZornGen7HostRing26 &);
    void copyKernelClientOobObservation(uint32_t (&)[8]) const;
    IOReturn acquireApplicationOob(class ZornGen7HostRing26 &,class ZornGen7AppExecution26 &);
    bool applicationOobHeld(const class ZornGen7HostRing26 &,const class ZornGen7AppExecution26 &) const;
    IOReturn releaseApplicationOob(class ZornGen7HostRing26 &,class ZornGen7AppExecution26 &);
    enum class Outcome : uint32_t { Unavailable,Drained,ReturnedAck,NativeAccessFailed,QueueInvalid,
        UnexpectedAck,Timeout,Busy,NoSpace };
    struct Reply {Outcome outcome=Outcome::Unavailable;uint32_t words=0,packet[19]{};};
    static IOReturn createPrepared(NativeAdrenoMemory &,uint32_t actualGmuVa,
        OSObject &actualBufferOwner,ZornGen7SmmuDomain26 &,ZornGen7GmuIrq26 &,
        ZornGen7RegisterMaps26 &,IOWorkLoop &,ZornGen7DirectHfi26 *&actualPartialOutput);
    static int consumeIrq(OSObject &,uint32_t actualIrqStatus);
    IOReturn armBoundReceiver(); // Future startup owner only after bootstrap.
    Reply exchange(unsigned id,const uint32_t *actualPayload,size_t actualWords);
    bool healthy() const;
    void fail();
    // All queue reads/writes below hold this owner's sole-consumer gate;
    // this same instance owns pending request/reply and IRQ debug dispatch.
    bool queue(unsigned,uint32_t &,uint32_t &);
    int read(unsigned,uint32_t (&)[19],uint32_t &);
    Outcome process(unsigned,bool allowActualPending);
    struct Storage;Storage *storage_=nullptr;bool pinned_=false;
};

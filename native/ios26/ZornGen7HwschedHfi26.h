/* SPDX-License-Identifier: GPL-2.0-only */
#pragma once
class ZornGen7AppExecution26;
#include <IOKit/IOWorkLoop.h>
#include <IOKit/IOLocks.h>
#include <libkern/c++/OSObject.h>
class ZornGen7HwschedBuffers26;class ZornGen7SmmuDomain26;class ZornGen7GmuIrq26;
class ZornGen7RegisterMaps26;class ZornGen7DarwinBoardOwner;class ZornGen7HwschedWork26;
struct ZornGen7GmuStartAuthority26;struct ZornGen7GpuStartAuthority26;
// Actual seventeen-queue transport,sole-consumer deferred worker and retained
// per-request pending state. Preparation binds a masked receiver only. It is
// not CM3/HFI readiness,firmware authentication or a successful native service.
class ZornGen7HwschedHfi26 final : public OSObject {
    OSDeclareDefaultStructors(ZornGen7HwschedHfi26);
public:
    bool halted() const;
    void free() override;
private:
    friend class ZornGen7SmmuDomain26;friend class ZornGen7DarwinBoardOwner;
    friend class ZornGen7HwschedWork26;
    friend class ZornGen7HwschedServices26;
    friend class ZornGen7HostTables26;friend class ZornGen7HostRing26;
    IOReturn releaseHostGpuOobAfterBootstrap(class ZornGen7HostRing26 &);
    IOReturn acquireApplicationOob(class ZornGen7HostRing26 &,ZornGen7AppExecution26 &);
    IOReturn releaseApplicationOob(class ZornGen7HostRing26 &,ZornGen7AppExecution26 &);
    bool applicationOobHeld(const class ZornGen7HostRing26 &,const ZornGen7AppExecution26 &) const;
    IOReturn acquireKernelClientOob(class ZornGen7HostRing26 &);
    IOReturn releaseKernelClientOob(class ZornGen7HostRing26 &);
    bool kernelClientOobHeld(const class ZornGen7HostRing26 &) const;
    IOReturn acquireKernelTaskOob(class ZornGen7HostRing26 &);
    IOReturn releaseKernelTaskOob(class ZornGen7HostRing26 &);
    bool kernelTaskOobHeld(const class ZornGen7HostRing26 &) const;
    enum class Outcome : uint32_t {Unavailable,ReturnedAck,QueueRefused,NativeAccessFailed,
        ProtocolRefused,ServiceRefused,Timeout,NativeWaitUnavailable};
    enum class RequestKind : uint32_t {InlineGeneric,InlineStart,AsyncGeneric};
    struct Reply {Outcome outcome=Outcome::Unavailable;uint32_t words=0,packet[19]{};};
    struct Services {
        OSObject *actualOwner=nullptr;
        // Actual synchronous frame borrows. No default successful service or
        // synthetic MEM_ALLOC/counter reply,context/fence retirement is supplied.
        int (*debug)(OSObject &,const uint32_t *,size_t)=nullptr;
        int (*startMemory)(OSObject &,const uint32_t *,size_t)=nullptr;
        int (*startCounters)(OSObject &,const uint32_t *,size_t)=nullptr;
        int (*runtimeMessage)(OSObject &,const uint32_t *,size_t)=nullptr;
    };
    static IOReturn createPrepared(ZornGen7HwschedBuffers26 &,IORecursiveLock &actualDomainGate,
        ZornGen7SmmuDomain26 &,ZornGen7GmuIrq26 &,ZornGen7RegisterMaps26 &,IOWorkLoop &,
        ZornGen7HwschedHfi26 *&actualPartialOutput);
    static IOReturn createHostPrepared(ZornGen7HwschedBuffers26 &,IORecursiveLock &actualDomainGate,
        ZornGen7SmmuDomain26 &,ZornGen7GmuIrq26 &,ZornGen7RegisterMaps26 &,IOWorkLoop &,
        ZornGen7HwschedHfi26 *&actualPartialOutput);
    static IOReturn createPreparedInternal(ZornGen7HwschedBuffers26 &,IORecursiveLock &actualDomainGate,
        ZornGen7SmmuDomain26 &,ZornGen7GmuIrq26 &,ZornGen7RegisterMaps26 &,IOWorkLoop &,
        ZornGen7HwschedHfi26 *&actualPartialOutput,bool actualHostRoute);
    IOReturn runHostProfile(OSObject &actualTablesOwner,const uint32_t (&actualPerf)[58],const uint32_t (&actualBw)[159]);
    IOReturn runHostFirstQuery();
    IOReturn requestHostClock(OSObject &actualSameTablesOwner,uint32_t actualAdjustedPowerLevel);
    IOReturn queryHostAbSupport(OSObject &actualSameTablesOwner,bool &actualReturnedSupport);
    IOReturn requestHostBandwidth(OSObject &actualSameTablesOwner,uint32_t actualEncodedBandwidth);
    IOReturn acquireHostGpuOob(OSObject &actualGpuStartOwner,const ZornGen7GpuStartAuthority26 &);
    IOReturn startHostGmu(OSObject &actualAuthorityOwner,const ZornGen7GmuStartAuthority26 &);
    static int hostHealthy(void *);
    static int hostSend(void *,const uint32_t *,unsigned);
    static int hostReceive(void *,unsigned,uint32_t *,unsigned *);
    static int hostDoorbell(void *);
    static int hostDelay(void *,unsigned);
    IOReturn bindActualServices(const Services &);
    IOReturn armBoundReceiver();
    IOReturn startControl(OSObject &actualQuiescenceOwner,int (*acquireActualQuiescence)(OSObject &,OSObject &));
    Reply exchange(uint32_t *actualStableCommand,size_t actualBytes,RequestKind);
    IOReturn enableAsyncAfterSourceStart();
    bool writeServiceReply(uint32_t *actualReply,size_t actualBytes);
    bool writePrepared(uint32_t *,size_t);
    static int consumeIrq(OSObject &,uint32_t actualStatus);
    bool servicePending();
    bool healthy() const;
    void fail();
    bool drainMessages(bool asynchronous,bool allowStartRequests);
    bool drainDebug();
    bool readFrame(bool debug,uint32_t (&)[256],size_t &actualWords,bool &actualEmpty);
    bool pollMessage(uint32_t timeoutMs,bool checkNmi);
    struct Storage;Storage *storage_=nullptr;bool pinned_=false;
};

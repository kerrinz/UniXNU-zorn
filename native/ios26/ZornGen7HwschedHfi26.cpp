/* SPDX-License-Identifier: GPL-2.0-only */
#include "ZornGen7HwschedHfi26.h"
#include "ZornGen7AppExecution26.h"
#include "ZornGen7HostRing26.h"
#include "ZornGen7HwschedBuffers26.h"
#include "ZornGen7HwschedServices26.h"
#include "ZornGen7HoujiHostProtocol26.h"
#include "ZornGen7HostBandwidthArithmetic26.h"
#include "ZornGen7HfiPending.h"
#include "ZornGen7GmuIrq26.h"
#include "ZornGen7SmmuDomain26.h"
#include "ZornGen7RegisterMaps26.h"
#include <IOKit/IOEventSource.h>
#include <IOKit/IOLib.h>
#include <kern/clock.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
#include <libkern/OSAtomic.h>
#include <string.h>
OSDefineMetaClassAndStructors(ZornGen7HwschedHfi26,OSObject)
namespace {
bool normal(){return preemption_enabled() && !ml_at_interrupt_context();}
constexpr uint32_t MSGQ=1u,DBGQ=4u,RECORD=1u<<19,NOP=1u<<18;
constexpr uint32_t START=10,MEM_ALLOC=20,CNTR_REGISTER=110;
bool span(const void *p,size_t bytes){const uintptr_t a=reinterpret_cast<uintptr_t>(p);return a && !(a&3u) && bytes && a<=UINTPTR_MAX-(bytes-1u);}
}
class ZornGen7HwschedWork26 final : public IOEventSource {
    OSDeclareDefaultStructors(ZornGen7HwschedWork26);
public:
    static ZornGen7HwschedWork26 *create(ZornGen7HwschedHfi26 &owner){
        auto *p=new ZornGen7HwschedWork26;if(!p)return nullptr;
        if(!p->init(&owner,nullptr)){p->release();return nullptr;}
        p->retain();p->pinned_=true;p->receiver_=&owner;owner.retain();return p;
    }
    void kick(){signalWorkAvailable();}
    bool checkForWork() override{return receiver_ && receiver_->servicePending();}
    void free() override{if(pinned_)return;IOEventSource::free();}
private:
    ZornGen7HwschedHfi26 *receiver_=nullptr;bool pinned_=false;
};
OSDefineMetaClassAndStructors(ZornGen7HwschedWork26,IOEventSource)
struct ZornGen7HwschedHfi26::Storage {
    struct Request {
        Request *next=nullptr;uint32_t command[255]{};size_t bytes=0;
        ZornGen7Hfi::Pending pending;
        ZornGen7Hfi::WaitResult wait{};ZornGen7Hfi::DeliveryResult delivery{};
        ZornGen7Hfi::CopyResult copy{};ZornGen7Hfi::InspectAssessment closed=ZornGen7Hfi::InspectAssessment::InputUnavailable;
        Reply reply;bool queued=false,notified=false;
        static void *operator new(size_t,void *p)noexcept{return p;}
    };
    ZornGen7HwschedBuffers26 &buffers;IORecursiveLock &domainGate;ZornGen7SmmuDomain26 &domain;
    ZornGen7GmuIrq26 &irq;ZornGen7RegisterMaps26 &maps;IOWorkLoop &loop;
    IOLock *commandGate=nullptr,*transmitGate=nullptr,*messageGate=nullptr,*debugGate=nullptr;
    IOSimpleLock *pendingLock=nullptr;ZornGen7Hfi::PendingRegistry *pending=nullptr;
    ZornGen7HwschedWork26 *work=nullptr;IOReturn workRaw=kIOReturnNotReady;
    Request *requests=nullptr,*inlineRequest=nullptr;
    uint32_t stopped=0,pendingBits=0,async=0,sequence=0;uint64_t recordMask[3]{};
    uint32_t frame[256]{},debugFrame[256]{};size_t actualWords=0,actualDebugWords=0;
    ZornGen7HwschedServices26 *nativeServices=nullptr;
    struct KernelOob {
        ZornGen7HostRing26 *owner=nullptr;bool attempted=false,requestReturned=false,ackObserved=false,ackCleared=false,gxOn=false;
        bool releaseAttempted=false,releaseWriteReturned=false;uint32_t ack=0,host=0,gx=0;int raw=0;
    } kernelOob,clientOob;
    ZornGen7AppExecution26 *activeApp=nullptr; // actual retained owner until normal clear
    struct HostAttempt {
        OSObject *tablesOwner=nullptr;uint32_t perf[58]{},bw[159]{};
        ZornGen7HoujiHost26::hhb_result bootstrap{},profile{},clock{},abQuery{},bandwidth{};
        unsigned bootstrapCode=0,profileCode=0,clockCode=0;
        bool clockAttempted=false,clockReturned=false,clockAccepted=false;uint32_t clockPayload[3]{};
        bool abQueryAttempted=false,abQueryReturned=false,abQueryAccepted=false,abSupported=false;
        unsigned abQueryCode=0,bandwidthCode=0;bool bandwidthAttempted=false,bandwidthReturned=false,bandwidthAccepted=false;
        uint32_t bandwidthPayload[3]{};
        bool oobReleaseAttempted=false,oobReleaseWriteReturned=false;IOReturn oobReleaseGrantRaw=kIOReturnNotReady;int oobReleaseIoRaw=0;
        bool oobAttempted=false,oobGrantReturned=false,oobRequestReturned=false,oobAckObserved=false,oobClearReturned=false;
        bool oobAckClearObserved=false,gxObservedOn=false,ackValueAvailable=false,gxValueAvailable=false;
        IOReturn oobGrantRaw=kIOReturnNotReady;uint32_t ackBefore=0,hostBefore=0,gxBefore=0,ackValue=0,gxValue=0;
        bool oobPreflightReturned=false;
        bool bootstrapReturned=false,bootstrapAccepted=false,profileAttempted=false,profileReturned=false,accepted=false;
        static void *operator new(size_t,void *p)noexcept{return p;}
    };
    HostAttempt *hostAttempt=nullptr;bool hostRoute=false,hostActive=false,hostQueued=false;
    OSObject *hostStartOwner=nullptr;ZornGen7GmuStartAuthority26 hostStartAuthority{};
    bool hostStartAttempted=false,cm3Returned=false,hostControlReturned=false,hostQueryReturned=false;
    IOReturn cm3Raw=kIOReturnNotReady,hostControlRaw=kIOReturnNotReady,hostQueryRaw=kIOReturnNotReady;
    Services services;bool servicesBound=false,prepared=false,armedAttempted=false;
    bool controlAttempted=false,controlReady=false,startAccepted=false,asyncAttempted=false;
    ZornGen7Hwsched26::QueueResult reset{};uint32_t lastControl=0;
    int lastNativeRaw=0,lastServiceRaw=0;uint32_t nativeReturned=0,serviceReturned=0;
    Storage(ZornGen7HwschedBuffers26 &b,IORecursiveLock &g,ZornGen7SmmuDomain26 &d,
        ZornGen7GmuIrq26 &i,ZornGen7RegisterMaps26 &m,IOWorkLoop &l):buffers(b),domainGate(g),domain(d),irq(i),maps(m),loop(l){}
    int access(uint32_t word,bool write,uint32_t &value){
        __atomic_store_n(&nativeReturned,0u,__ATOMIC_RELAXED);
        const int raw=irq.accessHfiWord(word,write,value);
        __atomic_store_n(&lastNativeRaw,raw,__ATOMIC_RELAXED);
        __atomic_store_n(&nativeReturned,1u,__ATOMIC_RELEASE);return raw;
    }
    int callService(int (*call)(OSObject &,const uint32_t *,size_t),const uint32_t *words,size_t count){
        __atomic_store_n(&serviceReturned,0u,__ATOMIC_RELAXED);
        const int raw=call(*services.actualOwner,words,count);
        __atomic_store_n(&lastServiceRaw,raw,__ATOMIC_RELAXED);
        __atomic_store_n(&serviceReturned,1u,__ATOMIC_RELEASE);return raw;
    }
    static void *operator new(size_t,void *p)noexcept{return p;}
};
IOReturn ZornGen7HwschedHfi26::createPrepared(ZornGen7HwschedBuffers26 &buffers,IORecursiveLock &gate,
    ZornGen7SmmuDomain26 &domain,ZornGen7GmuIrq26 &irq,ZornGen7RegisterMaps26 &maps,IOWorkLoop &loop,
    ZornGen7HwschedHfi26 *&out)
{return createPreparedInternal(buffers,gate,domain,irq,maps,loop,out,false);}
IOReturn ZornGen7HwschedHfi26::createHostPrepared(ZornGen7HwschedBuffers26 &buffers,IORecursiveLock &gate,
    ZornGen7SmmuDomain26 &domain,ZornGen7GmuIrq26 &irq,ZornGen7RegisterMaps26 &maps,IOWorkLoop &loop,
    ZornGen7HwschedHfi26 *&out)
{return createPreparedInternal(buffers,gate,domain,irq,maps,loop,out,true);}
IOReturn ZornGen7HwschedHfi26::createPreparedInternal(ZornGen7HwschedBuffers26 &buffers,IORecursiveLock &gate,
    ZornGen7SmmuDomain26 &domain,ZornGen7GmuIrq26 &irq,ZornGen7RegisterMaps26 &maps,IOWorkLoop &loop,
    ZornGen7HwschedHfi26 *&out,bool hostRoute)
{
    if(out || !normal() || !IORecursiveLockHaveLock(&gate) || loop.onThread() || loop.inGate() || irq.halted() || domain.faulted())return kIOReturnNotReady;
    ZornSmmuSparse4KRange actual[7]{};if(!buffers.copyPreparedRanges(actual))return kIOReturnNotReady;
    auto *p=new ZornGen7HwschedHfi26;if(!p)return kIOReturnNoMemory;
    if(!p->init()){p->release();return kIOReturnNoMemory;}
    p->retain();p->pinned_=true;out=p;buffers.retain();domain.retain();irq.retain();maps.retain();loop.retain();
    void *memory=IOMallocZero(sizeof(Storage));if(!memory)return kIOReturnNoMemory;
    p->storage_=new(memory)Storage(buffers,gate,domain,irq,maps,loop);auto &s=*p->storage_;s.hostRoute=hostRoute;
    s.commandGate=IOLockAlloc();s.transmitGate=IOLockAlloc();s.messageGate=IOLockAlloc();s.debugGate=IOLockAlloc();s.pendingLock=IOSimpleLockAlloc();
    if(!s.commandGate || !s.transmitGate || !s.messageGate || !s.debugGate || !s.pendingLock)return kIOReturnNoMemory;
    void *pending=IOMallocZero(sizeof(ZornGen7Hfi::PendingRegistry));if(!pending)return kIOReturnNoMemory;
    s.pending=::new(pending)ZornGen7Hfi::PendingRegistry(s.pendingLock);
    s.work=ZornGen7HwschedWork26::create(*p);if(!s.work)return kIOReturnNoResources;
    s.work->disable();s.workRaw=loop.addEventSource(s.work);if(s.workRaw!=kIOReturnSuccess)return s.workRaw;
    s.work->enable();if(!s.work->isEnabled())return kIOReturnNotReady;
    const auto raw=irq.bindHwschedReceiver(*p,consumeIrq);
    if(raw!=kIOReturnSuccess){p->fail();return raw;}
    s.prepared=true;
    const auto serviceRaw=ZornGen7HwschedServices26::createAndBind(*p,buffers,gate,s.nativeServices);
    if(serviceRaw!=kIOReturnSuccess){p->fail();return serviceRaw;}
    return kIOReturnSuccess; // Real worker/debug consumer bound;IRQ remains masked.
}
bool ZornGen7HwschedHfi26::halted() const
{return !storage_ || __atomic_load_n(&storage_->stopped,__ATOMIC_ACQUIRE)!=0;}
bool ZornGen7HwschedHfi26::healthy() const
{return storage_ && normal() && !halted() && !storage_->irq.halted() && !storage_->domain.faulted();}
void ZornGen7HwschedHfi26::fail()
{if(!storage_)return;__atomic_store_n(&storage_->stopped,1u,__ATOMIC_RELEASE);storage_->irq.stopAndMask();}
IOReturn ZornGen7HwschedHfi26::bindActualServices(const Services &actual)
{
    if(!healthy() || !actual.actualOwner || !actual.debug)return kIOReturnNotReady;
    auto &s=*storage_;IOLockLock(s.commandGate);
    if(!s.prepared || s.servicesBound || s.armedAttempted){IOLockUnlock(s.commandGate);return kIOReturnNotReady;}
    actual.actualOwner->retain();s.services=actual;s.servicesBound=true;IOLockUnlock(s.commandGate);return kIOReturnSuccess;
}
IOReturn ZornGen7HwschedHfi26::armBoundReceiver()
{
    if(!healthy())return kIOReturnNotReady;auto &s=*storage_;
    if(s.loop.onThread() || s.loop.inGate())return kIOReturnNotReady;
    IOLockLock(s.commandGate);
    if(!s.prepared || !s.servicesBound || !s.services.debug || s.armedAttempted){IOLockUnlock(s.commandGate);return kIOReturnNotReady;}
    s.armedAttempted=true;const auto raw=s.irq.armBoundReceiver();IOLockUnlock(s.commandGate);
    if(raw!=kIOReturnSuccess)fail();return raw;
}
IOReturn ZornGen7HwschedHfi26::startControl(OSObject &owner,int (*acquire)(OSObject &,OSObject &))
{
    if(!healthy() || !acquire)return kIOReturnNotReady;auto &s=*storage_;
    if(s.loop.onThread() || s.loop.inGate() || !s.irq.forwardAllowed())return kIOReturnNotReady;
    IOLockLock(s.commandGate);auto done=[&](IOReturn r){IOLockUnlock(s.commandGate);return r;};
    if(s.controlAttempted)return done(kIOReturnNotReady);s.controlAttempted=true;
    IORecursiveLockLock(&s.domainGate);s.reset=s.buffers.resetBeforeHfiControl(owner,acquire);IORecursiveLockUnlock(&s.domainGate);
    if(s.reset.assessment!=ZornGen7Hwsched26::QueueAssessment::SourceIndicesReset){fail();return done(kIOReturnNotReady);}
    uint32_t one=1;const int initRaw=s.access(0x1f986,true,one);
    if(initRaw){fail();return done(kIOReturnNotReady);}
    uint64_t deadline=0;clock_interval_to_deadline(100,1000000,&deadline);
    int controlRaw=0;
    for(;;){
        controlRaw=s.access(0x1f980,false,s.lastControl);
        if(controlRaw || !healthy()){fail();return done(kIOReturnNotReady);}
        if(s.lastControl&1u)break;
        uint64_t now=0;clock_get_uptime(&now);
        if(now>deadline){controlRaw=s.access(0x1f980,false,s.lastControl);break;}
        delay_for_interval_with_leeway(26,74,1000);__asm__ volatile("yield":::"memory");
    }
    if(controlRaw || !healthy() || !(s.lastControl&1u)){fail();return done(kIOReturnNotReady);}
    s.controlReady=true;return done(kIOReturnSuccess); // Exact init-bit observation,not HFI full start.
}
bool ZornGen7HwschedHfi26::readFrame(bool debug,uint32_t (&out)[256],size_t &words,bool &empty)
{
    words=0;empty=false;if(!healthy())return false;auto &s=*storage_;
    IORecursiveLockLock(&s.domainGate);
    const auto r=s.buffers.readActualFrame(debug?ZornGen7Hwsched26::F2HQueue::Debug:ZornGen7Hwsched26::F2HQueue::Message,out,(debug && !s.hostRoute)?19u*4u:sizeof(out));
    IORecursiveLockUnlock(&s.domainGate);
    if(r.assessment==ZornGen7Hwsched26::ReadAssessment::Empty){empty=true;return true;}
    if(r.assessment!=ZornGen7Hwsched26::ReadAssessment::FrameCopied || !r.words || r.words>255)return false;
    words=r.words;return true;
}
bool ZornGen7HwschedHfi26::drainMessages(bool asynchronous,bool allowStart)
{
    if(!healthy())return false;auto &s=*storage_;IOLockLock(s.messageGate);
    bool more=true;
    for(unsigned i=0;i<256;++i){
        bool empty=false;if(!readFrame(false,s.frame,s.actualWords,empty)){fail();more=false;break;}
        if(empty){more=false;break;}
        const uint32_t header=s.frame[0],id=header&255u,type=(header>>16)&15u;
        if(type==1u){
            const auto delivery=s.pending->deliver(s.frame,s.actualWords);
            if(s.inlineRequest)s.inlineRequest->delivery=delivery;
            if(delivery.assessment!=ZornGen7Hfi::DeliveryAssessment::ActualAckStored){fail();more=false;break;}
            if(!asynchronous){more=false;break;} // Source inline caller consumes exactly one frame.
        }else{
            int (*call)(OSObject &,const uint32_t *,size_t)=nullptr;
            if(!asynchronous && allowStart && id==MEM_ALLOC)call=s.services.startMemory;
            else if(!asynchronous && allowStart && id==CNTR_REGISTER)call=s.services.startCounters;
            else if(asynchronous)call=s.services.runtimeMessage;
            if(!call || !s.services.actualOwner){fail();more=false;break;}
            const int serviceRaw=s.callService(call,s.frame,s.actualWords);
            if(serviceRaw || !healthy()){fail();more=false;break;}
            if(!asynchronous){more=false;break;}
        }
    }
    IOLockUnlock(s.messageGate);
    // Finite native work pass. More actual frames schedule another real pass;
    // this is continuation of queue service,not command resend or recovery.
    return more && healthy();
}
bool ZornGen7HwschedHfi26::drainDebug()
{
    if(!healthy())return false;auto &s=*storage_;IOLockLock(s.debugGate);bool more=true;
    for(unsigned i=0;i<256;++i){
        bool empty=false;if(!readFrame(true,s.debugFrame,s.actualDebugWords,empty)){fail();more=false;break;}
        if(empty){more=false;break;}
        if(!s.services.actualOwner || !s.services.debug){fail();more=false;break;}
        const int serviceRaw=s.callService(s.services.debug,s.debugFrame,s.actualDebugWords);
        if(serviceRaw || !healthy()){fail();more=false;break;}
    }
    IOLockUnlock(s.debugGate);return more && healthy();
}
int ZornGen7HwschedHfi26::consumeIrq(OSObject &object,uint32_t status)
{
    auto *p=OSDynamicCast(ZornGen7HwschedHfi26,&object);if(!p || !p->healthy())return -1;
    auto &s=*p->storage_;uint32_t bits=status&DBGQ;
    if(__atomic_load_n(&s.async,__ATOMIC_ACQUIRE))bits|=status&MSGQ;
    if(bits){__atomic_fetch_or(&s.pendingBits,bits,__ATOMIC_RELEASE);s.work->kick();}
    return 0; // Actual software work notification only,never packet/ACK success.
}
bool ZornGen7HwschedHfi26::servicePending()
{
    if(!healthy())return false;auto &s=*storage_;const uint32_t bits=__atomic_exchange_n(&s.pendingBits,0u,__ATOMIC_ACQ_REL);uint32_t more=0;
    if((bits&MSGQ) && __atomic_load_n(&s.async,__ATOMIC_ACQUIRE) && drainMessages(true,false))more|=MSGQ;
    if((bits&DBGQ) && healthy() && drainDebug())more|=DBGQ;
    if(more)__atomic_fetch_or(&s.pendingBits,more,__ATOMIC_RELEASE);
    return healthy() && __atomic_load_n(&s.pendingBits,__ATOMIC_ACQUIRE)!=0;
}
bool ZornGen7HwschedHfi26::pollMessage(uint32_t ms,bool nmi)
{
    auto &s=*storage_;uint64_t deadline=0;clock_interval_to_deadline(ms,1000000,&deadline);bool last=false;
    for(;;){
        uint32_t status=0;const int statusRaw=s.access(0x1f992,false,status);
        if(statusRaw || !healthy())return false;if(status&MSGQ)return true;if(last)return false;
        uint32_t init=0;
        if(nmi && s.access(0x1f81c,false,init))return false;
        uint64_t now=0;clock_get_uptime(&now);if((init&0xe00u) || now>=deadline){last=true;continue;}
        if(nmi)delay_for_interval_with_leeway(10,90,1000);else delay_for_interval_with_leeway(26,74,1000);
        __asm__ volatile("yield":::"memory");
    }
}
ZornGen7HwschedHfi26::Reply ZornGen7HwschedHfi26::exchange(uint32_t *command,size_t bytes,RequestKind kind)
{
    using namespace ZornGen7Hfi;Reply unavailable;
    if(!healthy() || !span(command,bytes) || bytes<4 || bytes>1020 || (bytes&3u))return unavailable;
    auto &s=*storage_;if(s.loop.onThread() || s.loop.inGate())return unavailable;
    const uint32_t id=command[0]&255u;
    if(id>=156 || id==151 || (kind==RequestKind::InlineStart && id!=START))return unavailable;
    IOLockLock(s.commandGate);auto done=[&](Reply r){IOLockUnlock(s.commandGate);return r;};
    const bool async=__atomic_load_n(&s.async,__ATOMIC_ACQUIRE)!=0;
    if(s.hostRoute || !s.controlReady || !s.irq.forwardAllowed() || (kind==RequestKind::AsyncGeneric)!=async)return done(unavailable);
    void *allocation=IOMallocZero(sizeof(Storage::Request));if(!allocation){fail();return done(unavailable);}
    auto *r=new(allocation)Storage::Request;r->next=s.requests;s.requests=r;r->bytes=bytes;
    memcpy(r->command,command,bytes);OSSynchronizeIO();const uint32_t seq=__atomic_add_fetch(&s.sequence,1u,__ATOMIC_RELAXED);OSSynchronizeIO();
    r->command[0]|=((seq&4095u)<<20)|(uint32_t(bytes/4u)<<8);command[0]=r->command[0];
    if(s.pending->link(r->pending,r->command[0])!=PendingAssessment::Linked){fail();return done(r->reply);}
    if(!async)s.inlineRequest=r;
    const bool sent=writePrepared(r->command,bytes);command[0]=r->command[0];
    if(!sent){r->reply.outcome=Outcome::QueueRefused;fail();return done(r->reply);}r->queued=true;r->notified=true;
    if(async){
        r->wait=s.pending->waitNative(r->pending);
        if(r->wait.assessment==WaitAssessment::DeadlineReachedNeedsFinalDispatch){
            while(drainMessages(true,false)){} // Source final dispatch,not resend or another wait.
        }
        else if(r->wait.assessment!=WaitAssessment::ActualAckTokenConsumed){r->reply.outcome=Outcome::NativeWaitUnavailable;fail();return done(r->reply);}
    }else{
        // START's real MEM_ALLOC/counter replies continue this one sent command;
        // each source poll has its own1000ms budget,with no packet resend.
        for(;;){
            if(!pollMessage(1000,kind!=RequestKind::InlineStart)){r->reply.outcome=Outcome::Timeout;fail();return done(r->reply);}
            uint32_t clear=MSGQ;const int clearRaw=s.access(0x1f991,true,clear);
            if(clearRaw){r->reply.outcome=Outcome::NativeAccessFailed;fail();return done(r->reply);}
            drainMessages(false,kind==RequestKind::InlineStart);if(!healthy())return done(r->reply);
            r->copy=s.pending->copyActualResult(r->pending,r->reply.packet,19);
            if(r->copy.assessment==CopyAssessment::Copied)break;
            if(kind!=RequestKind::InlineStart){r->reply.outcome=Outcome::ProtocolRefused;fail();return done(r->reply);}
        }
    }
    if(r->copy.assessment!=CopyAssessment::Copied)r->copy=s.pending->copyActualResult(r->pending,r->reply.packet,19);
    if(r->copy.assessment!=CopyAssessment::Copied || r->copy.actual_words<3){r->reply.outcome=Outcome::ProtocolRefused;fail();return done(r->reply);}
    r->reply.words=r->copy.actual_words;
    if(async && r->wait.assessment==WaitAssessment::ActualAckTokenConsumed){
        if(s.pending->unlink(r->pending)!=PendingAssessment::Unlinked){fail();return done(r->reply);}
    }else{
        r->closed=s.pending->finishAfterActualFinalDispatch(r->pending,false);
        if(r->closed!=InspectAssessment::ActualTokenPresent){r->reply.outcome=Outcome::Timeout;fail();return done(r->reply);}
    }
    s.inlineRequest=nullptr;r->reply.outcome=Outcome::ReturnedAck;
    if(kind==RequestKind::InlineStart && r->reply.packet[2]!=UINT32_MAX)s.startAccepted=true;
    return done(r->reply); // Actual raw ACK only;each source caller owns its status/result contract.
}
IOReturn ZornGen7HwschedHfi26::enableAsyncAfterSourceStart()
{
    if(!healthy())return kIOReturnNotReady;auto &s=*storage_;IOLockLock(s.commandGate);
    if(s.hostRoute || !s.startAccepted || !s.services.runtimeMessage || s.asyncAttempted || s.inlineRequest){IOLockUnlock(s.commandGate);return kIOReturnNotReady;}
    s.asyncAttempted=true;__atomic_store_n(&s.async,1u,__ATOMIC_RELEASE);
    const auto raw=s.irq.enableHwschedAsync(*this);if(raw!=kIOReturnSuccess)fail();
    IOLockUnlock(s.commandGate);return raw;
}
void ZornGen7HwschedHfi26::free(){if(pinned_)return;OSObject::free();}

// Same real CMDQ producer lock serializes ordinary requests and source service
// replies. It is NEVER held across a native completion wait or MSG dispatch.
bool ZornGen7HwschedHfi26::writePrepared(uint32_t *command,size_t bytes)
{
    if(!healthy() || !span(command,bytes) || bytes<4 || bytes>1020 || (bytes&3u))return false;
    auto &s=*storage_;const uint32_t id=command[0]&255u;if(id>=156)return false;
    IOLockLock(s.transmitGate);
    if(s.recordMask[id/64u]&(uint64_t(1)<<(id%64u)))command[0]|=RECORD;
    IORecursiveLockLock(&s.domainGate);const auto write=s.buffers.writeActualCommand(command,bytes);IORecursiveLockUnlock(&s.domainGate);
    command[0]&=~(RECORD|NOP);OSSynchronizeIO();
    if(write!=ZornGen7Hwsched26::CommandWriteAssessment::WriteIndexPublished){IOLockUnlock(s.transmitGate);return false;}
    uint32_t notify=1;const int notifyRaw=s.access(0x1f994,true,notify);
    const bool ok=!notifyRaw && healthy();IOLockUnlock(s.transmitGate);return ok;
}
bool ZornGen7HwschedHfi26::writeServiceReply(uint32_t *reply,size_t bytes)
{
    if(!healthy() || !storage_->controlReady || !span(reply,bytes) || bytes<4 || bytes>1020 || (bytes&3u) ||
       ((reply[0]>>8)&255u)!=bytes/4u)return false;
    // Actual source ACK producer supplies the received request sequence. This
    // leaf deliberately does not allocate/increment a new request sequence.
    const bool ok=writePrepared(reply,bytes);if(!ok)fail();return ok;
}

// Real houji host-profile transport. Complete private packets/results and
// native owners only;no modeled peer,resource reply or successful callback.
int ZornGen7HwschedHfi26::hostHealthy(void *cookie)
{
    auto *p=static_cast<ZornGen7HwschedHfi26 *>(cookie);
    return p && p->healthy() && p->storage_->hostRoute && p->storage_->hostActive &&
        p->storage_->controlReady && p->storage_->irq.forwardAllowed() &&
        !__atomic_load_n(&p->storage_->async,__ATOMIC_ACQUIRE);
}
int ZornGen7HwschedHfi26::hostSend(void *cookie,const uint32_t *words,unsigned count)
{
    auto *p=static_cast<ZornGen7HwschedHfi26 *>(cookie);
    if(!hostHealthy(cookie) || !words || !count || count>160 || ((words[0]>>8)&255u)!=count)return -1;
    auto &s=*p->storage_;IOLockLock(s.transmitGate);
    if(s.hostQueued){IOLockUnlock(s.transmitGate);return -1;}
    IORecursiveLockLock(&s.domainGate);const auto raw=s.buffers.writeActualCommand(words,size_t(count)*4u);IORecursiveLockUnlock(&s.domainGate);
    const bool ok=raw==ZornGen7Hwsched26::CommandWriteAssessment::WriteIndexPublished;
    if(ok)s.hostQueued=true;IOLockUnlock(s.transmitGate);return ok?0:-1;
}
int ZornGen7HwschedHfi26::hostDoorbell(void *cookie)
{
    auto *p=static_cast<ZornGen7HwschedHfi26 *>(cookie);if(!hostHealthy(cookie))return -1;
    auto &s=*p->storage_;IOLockLock(s.transmitGate);
    if(!s.hostQueued){IOLockUnlock(s.transmitGate);return -1;}
    uint32_t one=1;const int raw=s.access(0x1f994,true,one);
    if(!raw)s.hostQueued=false;IOLockUnlock(s.transmitGate);return raw;
}
int ZornGen7HwschedHfi26::hostReceive(void *cookie,unsigned queue,uint32_t *out,unsigned *count)
{
    auto *p=static_cast<ZornGen7HwschedHfi26 *>(cookie);
    if(!hostHealthy(cookie) || !out || !count || (queue!=1 && queue!=2))return -1;
    auto &s=*p->storage_;IOLock *gate=queue==2?s.debugGate:s.messageGate;IOLockLock(gate);
    auto done=[&](int raw){IOLockUnlock(gate);return raw;};
    size_t words=0;bool empty=false;auto &frame=queue==2?s.debugFrame:s.frame;
    if(!p->readFrame(queue==2,frame,words,empty))return done(-1);
    if(empty){*count=0;return done(1);} // Actual observed GGH_EMPTY only.
    if(!words || words>255)return done(-1);
    if(queue==2 && (!s.services.debug || !s.services.actualOwner || s.callService(s.services.debug,frame,words)))return done(-1);
    for(size_t i=0;i<words;++i)out[i]=frame[i];*count=unsigned(words);return done(0);
}
int ZornGen7HwschedHfi26::hostDelay(void *cookie,unsigned us)
{
    if(!hostHealthy(cookie) || us!=10)return -1;IODelay(us);return hostHealthy(cookie)?0:-1;
}
IOReturn ZornGen7HwschedHfi26::startHostGmu(OSObject &owner,const ZornGen7GmuStartAuthority26 &authority)
{
    if(!healthy() || !authority.acquireColdStartWindow || !authority.acquireHfiQueueReset)return kIOReturnNotReady;
    auto &s=*storage_;
    if(s.loop.onThread() || s.loop.inGate() || IORecursiveLockHaveLock(&s.domainGate))return kIOReturnNotReady;
    IOLockLock(s.commandGate);
    if(!s.hostRoute || !s.prepared || !s.servicesBound || !s.irq.forwardAllowed() || s.hostStartAttempted ||
       s.controlAttempted || s.hostAttempt || s.sequence || s.requests || s.inlineRequest){IOLockUnlock(s.commandGate);return kIOReturnNotReady;}
    s.hostStartAttempted=true;owner.retain();s.hostStartOwner=&owner;s.hostStartAuthority=authority;
    IOLockUnlock(s.commandGate);
    // These seven retained buffers were freshly zeroed/header-initialized and
    // cold-published before stream activation. No old trace reset flag or old
    // native memory layout is reused. The real grant excludes firmware access
    // before release;an allocation or CPU range check cannot prove that alone.
    ZornSmmuSparse4KRange ranges[7]{};IORecursiveLockLock(&s.domainGate);
    const bool ready=s.buffers.copyPreparedRanges(ranges);IORecursiveLockUnlock(&s.domainGate);
    if(!ready){fail();return kIOReturnNotReady;}
    s.cm3Raw=s.maps.startHostCm3(owner,s.hostStartAuthority);s.cm3Returned=true;
    if(s.cm3Raw!=kIOReturnSuccess || !healthy()){fail();return s.cm3Raw==kIOReturnSuccess?kIOReturnNotReady:s.cm3Raw;}
    s.hostControlRaw=startControl(owner,s.hostStartAuthority.acquireHfiQueueReset);s.hostControlReturned=true;
    if(s.hostControlRaw!=kIOReturnSuccess || !healthy()){fail();return s.hostControlRaw==kIOReturnSuccess?kIOReturnNotReady:s.hostControlRaw;}
    s.hostQueryRaw=runHostFirstQuery();s.hostQueryReturned=true;
    if(s.hostQueryRaw!=kIOReturnSuccess || !healthy()){fail();return s.hostQueryRaw==kIOReturnSuccess?kIOReturnNotReady:s.hostQueryRaw;}
    return kIOReturnSuccess; // Actual first property ACK only,not full profile or CP.
}
IOReturn ZornGen7HwschedHfi26::runHostFirstQuery()
{
    using namespace ZornGen7HoujiHost26;
    if(!healthy())return kIOReturnNotReady;auto &s=*storage_;
    if(s.loop.onThread() || s.loop.inGate() || IORecursiveLockHaveLock(&s.domainGate))return kIOReturnNotReady;
    IOLockLock(s.commandGate);auto done=[&](IOReturn raw){s.hostActive=false;IOLockUnlock(s.commandGate);return raw;};
    if(!s.hostRoute || !s.controlReady || !s.irq.forwardAllowed() || s.hostAttempt || s.requests || s.inlineRequest ||
       s.sequence || __atomic_load_n(&s.async,__ATOMIC_ACQUIRE))return done(kIOReturnNotReady);
    void *memory=IOMallocZero(sizeof(Storage::HostAttempt));if(!memory)return done(kIOReturnNoMemory);
    s.hostAttempt=new(memory)Storage::HostAttempt;auto &r=*s.hostAttempt;
    s.hostActive=true;const hhb_io io{this,hostHealthy,hostSend,hostReceive,hostDoorbell,hostDelay,nullptr};
    const uint32_t query[]={125,0}; // HFI_VALUE_GMU_WARMBOOT,not a full capability report.
    // Same-owner sequence1 is consumed by this actual query. No power-bin,
    // PERF/BW table,successful old boot or fabricated ACK is needed as input.
    r.bootstrap.next_sequence=1;r.bootstrapCode=hhb_exchange(&io,&r.bootstrap,0,12,query,2,1,0);r.bootstrapReturned=true;
    s.sequence=r.bootstrap.next_sequence-1u;
    if(r.bootstrapCode || !r.bootstrap.record[0].ack || !r.bootstrap.record[0].status_present ||
       r.bootstrap.record[0].value!=1 || r.bootstrap.record[0].status){fail();return done(kIOReturnNotReady);}
    r.bootstrapAccepted=true;return done(kIOReturnSuccess);
}
IOReturn ZornGen7HwschedHfi26::runHostProfile(OSObject &tablesOwner,
    const uint32_t (&perf)[58],const uint32_t (&bw)[159])
{
    using namespace ZornGen7HoujiHost26;
    if(!healthy())return kIOReturnNotReady;auto &s=*storage_;
    if(s.loop.onThread() || s.loop.inGate() || IORecursiveLockHaveLock(&s.domainGate) ||
       !perf[0] || perf[0]>16 || !perf[1] || perf[1]>4)return kIOReturnNotReady;
    IOLockLock(s.commandGate);auto done=[&](IOReturn raw){s.hostActive=false;IOLockUnlock(s.commandGate);return raw;};
    if(!s.hostRoute || !s.controlReady || !s.irq.forwardAllowed() || !s.hostAttempt || s.requests || s.inlineRequest ||
       __atomic_load_n(&s.async,__ATOMIC_ACQUIRE))return done(kIOReturnNotReady);
    auto &r=*s.hostAttempt;
    if(!r.bootstrapReturned || !r.bootstrapAccepted || r.profileAttempted || r.tablesOwner ||
       s.sequence!=r.bootstrap.next_sequence-1u || r.bootstrap.next_sequence!=2u)return done(kIOReturnNotReady);
    r.profileAttempted=true;tablesOwner.retain();r.tablesOwner=&tablesOwner;
    for(unsigned i=0;i<58;++i)r.perf[i]=perf[i];for(unsigned i=0;i<159;++i)r.bw[i]=bw[i];
    s.hostActive=true;const hhb_io io{this,hostHealthy,hostSend,hostReceive,hostDoorbell,hostDelay,nullptr};
    const uint32_t query[]={125,0},core[]={0};
    // Continue the genuine first-query record in THIS receiver/boot epoch.
    // No resend of sequence1 and no profile attempt after unknown failure.
    r.profile.next_sequence=r.bootstrap.next_sequence;
    const struct {unsigned id,words,query,legacy;const uint32_t *payload;} steps[]={
        {4,58,0,1,r.perf},{3,159,0,1,r.bw},{14,1,0,1,core},{10,0,0,1,nullptr},{12,2,1,0,query}};
    for(unsigned i=0;i<5;++i){
        r.profileCode=hhb_exchange(&io,&r.profile,i,steps[i].id,steps[i].payload,steps[i].words,steps[i].query,steps[i].legacy);
        s.sequence=r.profile.next_sequence-1u;
        if(r.profileCode){r.profileReturned=true;fail();return done(kIOReturnNotReady);}
    }
    r.profileReturned=true;r.accepted=r.profile.completed==5 && !r.profile.resource_count && !r.profile.resource_acks &&
        r.profile.record[4].ack && r.profile.record[4].status_present && r.profile.record[4].value==1 && !r.profile.record[4].status;
    if(!r.accepted){fail();return done(kIOReturnNotReady);}return done(kIOReturnSuccess);
    // Host-profile ACKs only,not CP execution/fence/Metal or K80 qualification.
}

IOReturn ZornGen7HwschedHfi26::requestHostClock(OSObject &tablesOwner,uint32_t level)
{
    using namespace ZornGen7HoujiHost26;
    if(!healthy())return kIOReturnNotReady;auto &s=*storage_;
    if(s.loop.onThread() || s.loop.inGate() || IORecursiveLockHaveLock(&s.domainGate))return kIOReturnNotReady;
    IOLockLock(s.commandGate);auto done=[&](IOReturn raw){s.hostActive=false;IOLockUnlock(s.commandGate);return raw;};
    if(!s.hostRoute || !s.controlReady || !s.irq.forwardAllowed() || !s.hostAttempt || s.requests || s.inlineRequest ||
       __atomic_load_n(&s.async,__ATOMIC_ACQUIRE))return done(kIOReturnNotReady);
    auto &r=*s.hostAttempt;
    if(r.tablesOwner!=&tablesOwner || !r.accepted || !r.profileReturned || r.clockAttempted ||
       !r.abQueryAccepted || r.abQuery.next_sequence<2 || s.sequence!=r.abQuery.next_sequence-1u)return done(kIOReturnNotReady);
    r.clockAttempted=true;const uint32_t count=r.perf[0];
    if(count<2 || count>16 || level>=count-1u)return done(kIOReturnBadArgument);
    // Original gen7_gmu_clock_set -> gen7_gmu_dcvs_set. The source clock
    // caller has INVALID bus/AB sentinels;AB support/channel/DDR values are
    // immaterial to this exact branch. Never import houji's boot OPP/index.
    r.clockPayload[0]=1;r.clockPayload[1]=count-level-1u;r.clockPayload[2]=0xffff00ffu;
    r.clock.next_sequence=r.abQuery.next_sequence;s.hostActive=true;
    const hhb_io io{this,hostHealthy,hostSend,hostReceive,hostDoorbell,hostDelay,nullptr};
    r.clockCode=hhb_exchange(&io,&r.clock,0,30,r.clockPayload,3,0,1);
    s.sequence=r.clock.next_sequence-1u;r.clockReturned=true;
    r.clockAccepted=!r.clockCode && r.clock.completed==1 && r.clock.record[0].ack &&
        !r.clock.record[0].value && (!r.clock.record[0].status_present || !r.clock.record[0].status) &&
        !r.clock.resource_count && !r.clock.resource_acks;
    if(!r.clockAccepted){fail();return done(kIOReturnNotReady);}
    return done(kIOReturnSuccess); // Actual clock ACK only,not observed Hz/AXI/GX.
}

IOReturn ZornGen7HwschedHfi26::queryHostAbSupport(OSObject &tablesOwner,bool &out)
{
    using namespace ZornGen7HoujiHost26;
    if(!healthy())return kIOReturnNotReady;auto &s=*storage_;
    if(s.loop.onThread() || s.loop.inGate() || IORecursiveLockHaveLock(&s.domainGate))return kIOReturnNotReady;
    IOLockLock(s.commandGate);auto done=[&](IOReturn raw){s.hostActive=false;IOLockUnlock(s.commandGate);return raw;};
    if(!s.hostRoute || !s.controlReady || !s.irq.forwardAllowed() || !s.hostAttempt || s.requests || s.inlineRequest ||
       __atomic_load_n(&s.async,__ATOMIC_ACQUIRE))return done(kIOReturnNotReady);
    auto &r=*s.hostAttempt;
    if(r.tablesOwner!=&tablesOwner || !r.accepted || !r.profileReturned || r.abQueryAttempted || r.clockAttempted ||
       r.profile.next_sequence<2 || s.sequence!=r.profile.next_sequence-1u)return done(kIOReturnNotReady);
    r.abQueryAttempted=true;r.abQuery.next_sequence=r.profile.next_sequence;s.hostActive=true;
    const uint32_t query[]={ZornGen7HostBandwidth26::abProperty,0};
    const hhb_io io{this,hostHealthy,hostSend,hostReceive,hostDoorbell,hostDelay,nullptr};
    r.abQueryCode=hhb_exchange(&io,&r.abQuery,0,12,query,2,1,0);
    s.sequence=r.abQuery.next_sequence-1u;r.abQueryReturned=true;
    r.abQueryAccepted=!r.abQueryCode && r.abQuery.completed==1 && r.abQuery.record[0].ack &&
        r.abQuery.record[0].status_present && !r.abQuery.record[0].status && !r.abQuery.resource_count && !r.abQuery.resource_acks;
    if(!r.abQueryAccepted){fail();return done(kIOReturnNotReady);}
    // Original gen7_gmu_first_boot tests actual returned value==1. No missing
    // query,timeout or rejected response is converted into unsupported/zero.
    r.abSupported=r.abQuery.record[0].value==1;out=r.abSupported;return done(kIOReturnSuccess);
}
IOReturn ZornGen7HwschedHfi26::requestHostBandwidth(OSObject &tablesOwner,uint32_t encoded)
{
    using namespace ZornGen7HoujiHost26;
    if(!healthy())return kIOReturnNotReady;auto &s=*storage_;
    if(s.loop.onThread() || s.loop.inGate() || IORecursiveLockHaveLock(&s.domainGate))return kIOReturnNotReady;
    IOLockLock(s.commandGate);auto done=[&](IOReturn raw){s.hostActive=false;IOLockUnlock(s.commandGate);return raw;};
    if(!s.hostRoute || !s.controlReady || !s.irq.forwardAllowed() || !s.hostAttempt || s.requests || s.inlineRequest ||
       __atomic_load_n(&s.async,__ATOMIC_ACQUIRE))return done(kIOReturnNotReady);
    auto &r=*s.hostAttempt;
    if(r.tablesOwner!=&tablesOwner || !r.abQueryAccepted || !r.clockAccepted || r.bandwidthAttempted ||
       r.clock.next_sequence<2 || s.sequence!=r.clock.next_sequence-1u)return done(kIOReturnNotReady);
    r.bandwidthAttempted=true;r.bandwidth.next_sequence=r.clock.next_sequence;s.hostActive=true;
    // Source gpu_bus_set -> dcvs_set has INVALID GPU frequency and this
    // actual source-derived BW/AB word. It never borrows a houji OPP vote.
    r.bandwidthPayload[0]=1;r.bandwidthPayload[1]=0xffu;r.bandwidthPayload[2]=encoded;
    const hhb_io io{this,hostHealthy,hostSend,hostReceive,hostDoorbell,hostDelay,nullptr};
    r.bandwidthCode=hhb_exchange(&io,&r.bandwidth,0,30,r.bandwidthPayload,3,0,1);
    s.sequence=r.bandwidth.next_sequence-1u;r.bandwidthReturned=true;
    r.bandwidthAccepted=!r.bandwidthCode && r.bandwidth.completed==1 && r.bandwidth.record[0].ack &&
        !r.bandwidth.record[0].value && (!r.bandwidth.record[0].status_present || !r.bandwidth.record[0].status) &&
        !r.bandwidth.resource_count && !r.bandwidth.resource_acks;
    if(!r.bandwidthAccepted){fail();return done(kIOReturnNotReady);}return done(kIOReturnSuccess);
}

IOReturn ZornGen7HwschedHfi26::acquireHostGpuOob(OSObject &owner,const ZornGen7GpuStartAuthority26 &authority)
{
    if(!healthy() || !authority.acquireExclusiveGpuStart || !normal() || !ml_get_interrupts_enabled())return kIOReturnNotReady;
    auto &s=*storage_;
    if(s.loop.onThread() || s.loop.inGate() || IORecursiveLockHaveLock(&s.domainGate))return kIOReturnNotReady;
    IOLockLock(s.commandGate);
    if(!s.hostRoute || !s.controlReady || !s.hostAttempt || !s.hostAttempt->bandwidthAccepted ||
       s.hostAttempt->oobAttempted || s.requests || s.inlineRequest || __atomic_load_n(&s.async,__ATOMIC_ACQUIRE)){
        IOLockUnlock(s.commandGate);return kIOReturnNotReady;}
    auto &r=*s.hostAttempt;r.oobAttempted=true;IOLockUnlock(s.commandGate);
    const auto grant=s.maps.acquireHostGpuWindow(owner,authority);
    IOLockLock(s.commandGate);r.oobGrantRaw=grant;r.oobGrantReturned=true;
    auto done=[&](IOReturn raw){s.hostActive=false;IOLockUnlock(s.commandGate);return raw;};
    if(grant!=kIOReturnSuccess || !healthy()){fail();return done(grant==kIOReturnSuccess?kIOReturnNotReady:grant);}
    s.hostActive=true;
    auto read=[&](uint32_t word,uint32_t &value)->bool{return hostHealthy(this) && !s.access(word,false,value);};
    auto write=[&](uint32_t word,uint32_t value)->bool{return hostHealthy(this) && !s.access(word,true,value);};
    constexpr uint32_t request=1u<<30,ack=1u<<31;
    // Same houji direct preflight,using the exact gen7_reg.h native words and
    // checked serialized backend. A stale mailbox is never cleared/reused.
    if(!read(0x1f8d0,r.gxBefore) || !read(0x1f992,r.ackBefore) || !read(0x1f996,r.hostBefore)){
        fail();return done(kIOReturnNotReady);}
    r.oobPreflightReturned=true;
    if((r.ackBefore&ack) || (r.hostBefore&(request|ack))){fail();return done(kIOReturnNotReady);}
    if(!write(0x1f994,request)){fail();return done(kIOReturnNotReady);}r.oobRequestReturned=true;
    auto poll=[&](uint32_t word,uint32_t mask,uint32_t expected,uint32_t &value,bool &available)->bool{
        uint64_t deadline=0;clock_interval_to_deadline(100,1000000,&deadline);
        for(;;){
            if(!read(word,value))return false;available=true;if((value&mask)==expected)return true;
            uint64_t now=0;clock_get_uptime(&now);
            if(now>deadline){if(!read(word,value))return false;return (value&mask)==expected;}
            delay_for_interval_with_leeway(26,74,1000);__asm__ volatile("yield":::"memory");
        }
    };
    if(!poll(0x1f992,ack,ack,r.ackValue,r.ackValueAvailable)){fail();return done(kIOReturnNotReady);}
    r.oobAckObserved=true;
    if(!write(0x1f991,ack)){fail();return done(kIOReturnNotReady);}r.oobClearReturned=true;
    if(!read(0x1f992,r.ackValue) || (r.ackValue&ack)){fail();return done(kIOReturnNotReady);}r.oobAckClearObserved=true;
    if(!poll(0x1f8d0,3u,0u,r.gxValue,r.gxValueAvailable)){fail();return done(kIOReturnNotReady);}
    r.gxObservedOn=true;return done(kIOReturnSuccess);
    // Real handshake and GX status only,not GPU-MMU ownership or CP start.
    // No OOB release,ACK clear after timeout,error reset/cleanup or outer retry.
    // Nonreturning native IO still requires the future trial's watchdog.
}

IOReturn ZornGen7HwschedHfi26::releaseHostGpuOobAfterBootstrap(ZornGen7HostRing26 &ring)
{
    if(!healthy() || !normal() || !ml_get_interrupts_enabled() || !ring.bootstrapReadyForOob(*this))return kIOReturnNotReady;
    auto &s=*storage_;if(s.loop.onThread() || s.loop.inGate() || IORecursiveLockHaveLock(&s.domainGate))return kIOReturnNotReady;
    IOLockLock(s.commandGate);
    if(!s.hostRoute || !s.hostAttempt || s.hostAttempt->oobReleaseAttempted || s.hostActive || s.requests ||
       s.inlineRequest || __atomic_load_n(&s.async,__ATOMIC_ACQUIRE)){IOLockUnlock(s.commandGate);return kIOReturnNotReady;}
    auto &r=*s.hostAttempt;
    if(!r.oobGrantReturned || r.oobGrantRaw || !r.oobRequestReturned || !r.oobAckObserved || !r.oobAckClearObserved || !r.gxObservedOn){IOLockUnlock(s.commandGate);return kIOReturnNotReady;}
    r.oobReleaseAttempted=true;IOLockUnlock(s.commandGate);
    // Independent release permission is acquired outside the command/startup
    // gates. Unknown/refused result never falls through to the clear store.
    r.oobReleaseGrantRaw=s.maps.authorizeHostOobRelease(ring);
    IOLockLock(s.commandGate);auto done=[&](IOReturn raw){s.hostActive=false;IOLockUnlock(s.commandGate);return raw;};
    if(r.oobReleaseGrantRaw || !healthy() || !ring.bootstrapReadyForOob(*this) || s.requests || s.inlineRequest ||
       __atomic_load_n(&s.async,__ATOMIC_ACQUIRE)){fail();return done(r.oobReleaseGrantRaw?r.oobReleaseGrantRaw:kIOReturnNotReady);}
    s.hostActive=true;
    // Exact OEM gen7_gmu_oob_clear: oob_gpu=0 -> BIT(31 - 0*2).
    // This is HOST2GMU_INTR_SET,not the earlier GMU2HOST ACK clear register.
    uint32_t value=1u<<31;r.oobReleaseIoRaw=s.access(0x1f994,true,value);
    r.oobReleaseWriteReturned=!r.oobReleaseIoRaw;
    if(r.oobReleaseIoRaw || !healthy()){fail();return done(kIOReturnNotReady);}
    return done(kIOReturnSuccess);
    // Only the source MMIO write returned. No fabricated release ACK/GX-off,
    // power-down,DMA stop,Native BO retirement,unmap,reset or retry follows.
}

IOReturn ZornGen7HwschedHfi26::acquireKernelTaskOob(ZornGen7HostRing26 &ring)
{
    if(!normal() || !healthy() || !ml_get_interrupts_enabled() || !ring.kernelTaskPermissionHeld(*this))return kIOReturnNotReady;auto &s=*storage_;
    if(s.loop.onThread() || s.loop.inGate() || IORecursiveLockHaveLock(&s.domainGate))return kIOReturnNotReady;
    IOLockLock(s.commandGate);auto done=[&](IOReturn raw){s.hostActive=false;IOLockUnlock(s.commandGate);return raw;};auto &r=s.kernelOob;
    if(!s.hostRoute || !s.hostAttempt || !s.hostAttempt->oobReleaseWriteReturned || r.attempted || s.activeApp || s.hostActive || s.requests ||
       s.inlineRequest || __atomic_load_n(&s.async,__ATOMIC_ACQUIRE)){IOLockUnlock(s.commandGate);return kIOReturnNotReady;}
    r.attempted=true;r.owner=&ring;s.hostActive=true;
    auto read=[&](uint32_t at,uint32_t &v){return healthy() && ring.kernelTaskPermissionHeld(*this) && !s.access(at,false,v);};
    auto write=[&](uint32_t at,uint32_t v){return healthy() && ring.kernelTaskPermissionHeld(*this) && !s.access(at,true,v);};
    constexpr uint32_t request=1u<<30,ack=1u<<31;
    if(!read(0x1f992,r.ack) || !read(0x1f996,r.host) || (r.ack&ack) || (r.host&(request|ack))){fail();return done(kIOReturnNotReady);}
    if(!write(0x1f994,request)){fail();return done(kIOReturnNotReady);}r.requestReturned=true;
    auto poll=[&](uint32_t at,uint32_t mask,uint32_t expected,uint32_t &v){
        uint64_t deadline=0;clock_interval_to_deadline(100,NSEC_PER_MSEC,&deadline);
        for(;;){if(!read(at,v))return false;if((v&mask)==expected)return true;uint64_t now=0;clock_get_uptime(&now);
            if(now>deadline)return read(at,v) && (v&mask)==expected;delay_for_interval_with_leeway(26,74,1000);}
    };
    if(!poll(0x1f992,ack,ack,r.ack)){fail();return done(kIOReturnNotReady);}r.ackObserved=true;
    if(!write(0x1f991,ack) || !read(0x1f992,r.ack) || (r.ack&ack)){fail();return done(kIOReturnNotReady);}r.ackCleared=true;
    if(!poll(0x1f8d0,3u,0u,r.gx)){fail();return done(kIOReturnNotReady);}r.gxOn=true;return done(kIOReturnSuccess);
}
bool ZornGen7HwschedHfi26::kernelTaskOobHeld(const ZornGen7HostRing26 &ring) const
{
    if(!storage_ || !healthy())return false;const auto &r=storage_->kernelOob;
    return r.owner==&ring && r.attempted && r.requestReturned && r.ackObserved && r.ackCleared && r.gxOn && !r.releaseAttempted;
}
IOReturn ZornGen7HwschedHfi26::releaseKernelTaskOob(ZornGen7HostRing26 &ring)
{
    if(!normal() || !healthy() || !kernelTaskOobHeld(ring) || !ring.kernelTaskReadyToRelease(*this))return kIOReturnNotReady;auto &s=*storage_;
    if(s.loop.onThread() || s.loop.inGate() || IORecursiveLockHaveLock(&s.domainGate))return kIOReturnNotReady;
    IOLockLock(s.commandGate);auto &r=s.kernelOob;
    if(s.hostActive || s.requests || s.inlineRequest || __atomic_load_n(&s.async,__ATOMIC_ACQUIRE)){IOLockUnlock(s.commandGate);return kIOReturnNotReady;}
    r.releaseAttempted=true;uint32_t clear=1u<<31;r.raw=s.access(0x1f994,true,clear);r.releaseWriteReturned=!r.raw;
    if(r.raw)fail();IOLockUnlock(s.commandGate);return r.raw?kIOReturnNotReady:kIOReturnSuccess;
    // Only returned source OOB-clear store,no release ACK/GX-off/DMA-stop.
}

IOReturn ZornGen7HwschedHfi26::acquireKernelClientOob(ZornGen7HostRing26 &ring)
{
    if(!normal() || !healthy() || !ml_get_interrupts_enabled() || !ring.kernelClientPermissionHeld(*this))return kIOReturnNotReady;auto &s=*storage_;
    if(s.loop.onThread() || s.loop.inGate() || IORecursiveLockHaveLock(&s.domainGate))return kIOReturnNotReady;
    IOLockLock(s.commandGate);auto done=[&](IOReturn raw){s.hostActive=false;IOLockUnlock(s.commandGate);return raw;};auto &r=s.clientOob;
    if(!s.hostRoute || !s.hostAttempt || !s.hostAttempt->oobReleaseWriteReturned || !s.kernelOob.releaseWriteReturned || r.attempted || s.activeApp || s.hostActive || s.requests ||
       s.inlineRequest || __atomic_load_n(&s.async,__ATOMIC_ACQUIRE)){IOLockUnlock(s.commandGate);return kIOReturnNotReady;}
    r.attempted=true;r.owner=&ring;s.hostActive=true;
    auto read=[&](uint32_t at,uint32_t &v){return healthy() && ring.kernelClientPermissionHeld(*this) && !s.access(at,false,v);};
    auto write=[&](uint32_t at,uint32_t v){return healthy() && ring.kernelClientPermissionHeld(*this) && !s.access(at,true,v);};
    constexpr uint32_t request=1u<<30,ack=1u<<31;
    if(!read(0x1f992,r.ack) || !read(0x1f996,r.host) || (r.ack&ack) || (r.host&(request|ack))){fail();return done(kIOReturnNotReady);}
    if(!write(0x1f994,request)){fail();return done(kIOReturnNotReady);}r.requestReturned=true;
    auto poll=[&](uint32_t at,uint32_t mask,uint32_t expected,uint32_t &v){
        uint64_t deadline=0;clock_interval_to_deadline(100,NSEC_PER_MSEC,&deadline);
        for(;;){if(!read(at,v))return false;if((v&mask)==expected)return true;uint64_t now=0;clock_get_uptime(&now);
            if(now>deadline)return read(at,v) && (v&mask)==expected;delay_for_interval_with_leeway(26,74,1000);}
    };
    if(!poll(0x1f992,ack,ack,r.ack)){fail();return done(kIOReturnNotReady);}r.ackObserved=true;
    if(!write(0x1f991,ack) || !read(0x1f992,r.ack) || (r.ack&ack)){fail();return done(kIOReturnNotReady);}r.ackCleared=true;
    if(!poll(0x1f8d0,3u,0u,r.gx)){fail();return done(kIOReturnNotReady);}r.gxOn=true;return done(kIOReturnSuccess);
}
bool ZornGen7HwschedHfi26::kernelClientOobHeld(const ZornGen7HostRing26 &ring) const
{
    if(!storage_ || !healthy())return false;const auto &r=storage_->clientOob;
    return r.owner==&ring && r.attempted && r.requestReturned && r.ackObserved && r.ackCleared && r.gxOn && !r.releaseAttempted;
}
IOReturn ZornGen7HwschedHfi26::releaseKernelClientOob(ZornGen7HostRing26 &ring)
{
    if(!normal() || !healthy() || !kernelClientOobHeld(ring) || !ring.kernelClientReadyToRelease(*this))return kIOReturnNotReady;auto &s=*storage_;
    if(s.loop.onThread() || s.loop.inGate() || IORecursiveLockHaveLock(&s.domainGate))return kIOReturnNotReady;
    IOLockLock(s.commandGate);auto &r=s.clientOob;
    if(s.hostActive || s.requests || s.inlineRequest || __atomic_load_n(&s.async,__ATOMIC_ACQUIRE)){IOLockUnlock(s.commandGate);return kIOReturnNotReady;}
    r.releaseAttempted=true;uint32_t clear=1u<<31;r.raw=s.access(0x1f994,true,clear);r.releaseWriteReturned=!r.raw;
    if(r.raw)fail();IOLockUnlock(s.commandGate);return r.raw?kIOReturnNotReady:kIOReturnSuccess;
    // Only returned source OOB-clear store,no release ACK/GX-off/DMA-stop.
}

IOReturn ZornGen7HwschedHfi26::acquireApplicationOob(ZornGen7HostRing26 &ring,ZornGen7AppExecution26 &execution)
{
    if(!normal() || !healthy() || !ml_get_interrupts_enabled() ||
       !ring.applicationOobPermission(*this,execution,false))return kIOReturnNotReady;
    auto &s=*storage_;
    if(s.loop.onThread() || s.loop.inGate() || IORecursiveLockHaveLock(&s.domainGate))return kIOReturnNotReady;
    IOLockLock(s.commandGate);auto &r=execution.oob_;
    if(!s.hostRoute || !s.hostAttempt || !s.hostAttempt->oobReleaseWriteReturned ||
       !s.kernelOob.releaseWriteReturned || (s.clientOob.attempted && !s.clientOob.releaseWriteReturned) ||
       r.attempted || s.activeApp || s.hostActive || s.requests || s.inlineRequest ||
       __atomic_load_n(&s.async,__ATOMIC_ACQUIRE)){IOLockUnlock(s.commandGate);return kIOReturnNotReady;}
    r.attempted=true;r.owner=this;execution.retain();s.activeApp=&execution;s.hostActive=true;
    auto done=[&](IOReturn raw){s.hostActive=false;IOLockUnlock(s.commandGate);return raw;};
    auto permission=[&](){
        // The real provider's current check runs outside HFI/issuer/domain
        // locks. hostActive/activeApp prevent a competing command mutation.
        IOLockUnlock(s.commandGate);
        const bool held=ring.applicationOobPermission(*this,execution,false);
        IOLockLock(s.commandGate);
        return held && healthy() && s.hostActive && s.activeApp==&execution &&
            r.owner==this && r.attempted && !r.releaseAttempted;
    };
    auto read=[&](uint32_t at,uint32_t &value){if(!permission())return false;r.raw=s.access(at,false,value);return !r.raw;};
    auto write=[&](uint32_t at,uint32_t value){if(!permission())return false;r.raw=s.access(at,true,value);return !r.raw;};
    // Exact existing direct-host GMU OOB source,not an HWSCHED submission.
    constexpr uint32_t request=1u<<30,ack=1u<<31;
    if(!read(0x1f992,r.ack) || !read(0x1f996,r.host) || (r.ack&ack) || (r.host&(request|ack))){fail();return done(kIOReturnNotReady);}
    if(!write(0x1f994,request)){fail();return done(kIOReturnNotReady);}r.requestReturned=true;
    auto poll=[&](uint32_t at,uint32_t mask,uint32_t expected,uint32_t &value){
        uint64_t deadline=0;clock_interval_to_deadline(100,NSEC_PER_MSEC,&deadline);
        for(;;){if(!read(at,value))return false;if((value&mask)==expected)return true;
            uint64_t now=0;clock_get_uptime(&now);if(now>deadline)return read(at,value) && (value&mask)==expected;
            delay_for_interval_with_leeway(26,74,1000);}
    };
    if(!poll(0x1f992,ack,ack,r.ack)){fail();return done(kIOReturnNotReady);}r.ackObserved=true;
    if(!write(0x1f991,ack) || !read(0x1f992,r.ack) || (r.ack&ack)){fail();return done(kIOReturnNotReady);}r.ackCleared=true;
    if(!poll(0x1f8d0,3u,0u,r.gx)){fail();return done(kIOReturnNotReady);}r.gxOn=true;
    return done(kIOReturnSuccess);
}
bool ZornGen7HwschedHfi26::applicationOobHeld(const ZornGen7HostRing26 &ring,const ZornGen7AppExecution26 &execution) const
{
    if(!storage_ || !healthy())return false;const auto &r=execution.oob_;
    return execution.ring_==&ring && storage_->activeApp==&execution && r.owner==this && r.attempted && r.requestReturned &&
        r.ackObserved && r.ackCleared && r.gxOn && !r.releaseAttempted;
}
IOReturn ZornGen7HwschedHfi26::releaseApplicationOob(ZornGen7HostRing26 &ring,ZornGen7AppExecution26 &execution)
{
    if(!normal() || !healthy() || !applicationOobHeld(ring,execution) ||
       !ring.applicationOobReleaseReady(*this,execution) || !ring.applicationOobPermission(*this,execution,true))
        return kIOReturnNotReady;
    auto &s=*storage_;if(s.loop.onThread() || s.loop.inGate() || IORecursiveLockHaveLock(&s.domainGate))return kIOReturnNotReady;
    IOLockLock(s.commandGate);auto &r=execution.oob_;
    if(s.activeApp!=&execution || r.releaseAttempted || s.hostActive || s.requests || s.inlineRequest ||
       __atomic_load_n(&s.async,__ATOMIC_ACQUIRE)){IOLockUnlock(s.commandGate);return kIOReturnNotReady;}
    r.releaseAttempted=true;s.hostActive=true;
    IOLockUnlock(s.commandGate);const bool held=ring.applicationOobPermission(*this,execution,true);IOLockLock(s.commandGate);
    if(!held || !healthy() || s.activeApp!=&execution || !s.hostActive){fail();s.hostActive=false;IOLockUnlock(s.commandGate);return kIOReturnNotReady;}
    uint32_t clear=1u<<31;r.raw=s.access(0x1f994,true,clear);r.releaseWriteReturned=!r.raw;
    if(r.raw){fail();s.hostActive=false;IOLockUnlock(s.commandGate);return kIOReturnNotReady;}
    s.activeApp=nullptr;s.hostActive=false;IOLockUnlock(s.commandGate);execution.release();
    return kIOReturnSuccess; // returned clear store ONLY,no release ACK/GX-off/DMA-stop proof
}

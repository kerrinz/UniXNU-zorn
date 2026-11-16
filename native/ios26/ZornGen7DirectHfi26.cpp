// SPDX-License-Identifier: GPL-2.0-only
#include "ZornGen7DirectHfi26.h"
#include "ZornGen7GmuIrq26.h"
#include "ZornGen7HostRing26.h"
#include "ZornGen7AppExecution26.h"
#include "ZornGen7SmmuDomain26.h"
#include "ZornGen7RegisterMaps26.h"
#include "Adreno740/NativeAdrenoMemory.h"
#include <IOKit/IOLib.h>
#include <IOKit/IOLocks.h>
#include <IOKit/IOBufferMemoryDescriptor.h>
#include <libkern/OSByteOrder.h>
#include <kern/clock.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
OSDefineMetaClassAndStructors(ZornGen7DirectHfi26,OSObject)
namespace {
bool normal(){return preemption_enabled() && !ml_at_interrupt_context();}
constexpr uint32_t ringWords=1024,tableBytes=840,ringStart=848,activeQueues=3;
constexpr uint32_t recordBit=1u<<19,msgqBit=1u,debugBit=1u<<2;
size_t qheader(unsigned q){return 24u+size_t(q)*48u;}
size_t qdata(unsigned q,uint32_t word){return ringStart+size_t(q)*4096u+size_t(word)*4u;}
void acquire(){__asm__ volatile("dmb oshld":::"memory");}
void publish(){__asm__ volatile("dsb oshst":::"memory");}
void complete(){__asm__ volatile("dmb osh":::"memory");}
}
struct ZornGen7DirectHfi26::Storage {
    IOLock *gate=nullptr;OSObject *bufferOwner=nullptr;
    OSObject *hostOobOwner=nullptr;IORecursiveLock *hostStartup=nullptr;
    bool (*hostOobHeld)(OSObject &,const ZornGen7DirectHfi26 &)=nullptr;
    bool hostReleaseAttempted=false,hostReleaseReturned=false;int hostReleaseIoRaw=0;
    IOReturn hostReleaseGrantRaw=kIOReturnNotReady;
    struct KernelOob {
        ZornGen7HostRing26 *owner=nullptr;
        bool attempted=false,requestReturned=false,ackObserved=false,ackCleared=false,gxOn=false;
        bool releaseAttempted=false,releaseWriteReturned=false;
        uint32_t ack=0,host=0,gx=0,reads=0,writes=0,lastWord=0;int raw=0;
    } kernelOob,clientOob;
    ZornGen7AppExecution26 *activeApp=nullptr; // retained until real OOB clear succeeds
    ZornGen7SmmuDomain26 *domain=nullptr;ZornGen7GmuIrq26 *irq=nullptr;
    ZornGen7RegisterMaps26 *maps=nullptr;IOWorkLoop *loop=nullptr;
    // Frozen native mapping belongs to bufferOwner, whose device holds and
    // immutable objects survive every attempt; no public address/BO accessor.
    volatile void *cpu=nullptr;size_t bytes=0;uint32_t iova=0;
    uint32_t stopped=0;bool prepared=false,armAttempted=false,commandBusy=false,pending=false,ack=false;
    uint32_t sequence=0,sentHeader=0,request[255]{},reply[19]{},replyWords=0;
    uint32_t lastPacket[19]{},lastWords=0;uint64_t errorPackets=0,debugPackets=0,unknownPackets=0;
    int lastNativeRaw=0;bool lastNativeReturned=false;Outcome failure=Outcome::Unavailable;
    static void *operator new(size_t,void *p)noexcept{return p;}
};
IOReturn ZornGen7DirectHfi26::createPrepared(NativeAdrenoMemory &memory,uint32_t va,
    OSObject &buffers,ZornGen7SmmuDomain26 &domain,ZornGen7GmuIrq26 &irq,
    ZornGen7RegisterMaps26 &maps,IOWorkLoop &loop,ZornGen7DirectHfi26 *&out)
{
    if(out || !normal() || loop.onThread() || loop.inGate() || irq.halted() || domain.faulted() ||
       !memory.backed() || memory.quarantined() || memory.imported() || memory.pooled() || memory.readOnly() ||
       !memory.writeCombined() || !memory.deviceReferences() || !memory.mapping() || !memory.descriptor() ||
       memory.bytes()!=16384 || memory.ownedBytes()!=NativeAdrenoMemory::backingBudget(memory.bytes()) ||
       memory.descriptor()->getLength()!=memory.ownedBytes() || !va || (va&4095u) || va>UINT32_MAX-16383u)
        return kIOReturnNotReady;
    const uintptr_t base=reinterpret_cast<uintptr_t>(memory.mapping());
    if((base&4095u) || base>UINTPTR_MAX-16383u)return kIOReturnBadArgument;
    auto *owner=new ZornGen7DirectHfi26;if(!owner)return kIOReturnNoMemory;
    if(!owner->init()){owner->release();return kIOReturnNoMemory;}
    owner->retain();owner->pinned_=true;out=owner;
    buffers.retain();domain.retain();irq.retain();maps.retain();loop.retain();
    void *allocation=IOMallocZero(sizeof(Storage));if(!allocation)return kIOReturnNoMemory;
    owner->storage_=new(allocation)Storage;auto &s=*owner->storage_;
    s.bufferOwner=&buffers;s.domain=&domain;s.irq=&irq;s.maps=&maps;s.loop=&loop;
    s.cpu=memory.mapping();s.bytes=memory.bytes();s.iova=va;s.gate=IOLockAlloc();
    if(!s.gate)return kIOReturnNoMemory;
    // No queue reset or contents rewrite after device publication. Validate the
    // actual previously prepared layout, then retain this exact receiver.
    IOLockLock(s.gate);bool valid=true;
    for(unsigned q=0;q<activeQueues;++q){uint32_t r=0,w=0;if(!owner->queue(q,r,w))valid=false;}
    if(valid)s.prepared=true;IOLockUnlock(s.gate);
    if(!valid){owner->fail();return kIOReturnNotReady;}
    const auto raw=irq.bindReceiver(*owner,consumeIrq);
    if(raw!=kIOReturnSuccess){owner->fail();return raw;}
    return kIOReturnSuccess; // Bound real consumer, still masked/not started.
}
bool ZornGen7DirectHfi26::halted() const
{return !storage_ || __atomic_load_n(&storage_->stopped,__ATOMIC_ACQUIRE)!=0;}
bool ZornGen7DirectHfi26::healthy() const
{return storage_ && normal() && !halted() && !storage_->irq->halted() && !storage_->domain->faulted();}
void ZornGen7DirectHfi26::fail()
{if(!storage_)return;__atomic_store_n(&storage_->stopped,1u,__ATOMIC_RELEASE);storage_->irq->stopAndMask();}
bool ZornGen7DirectHfi26::queue(unsigned q,uint32_t &r,uint32_t &w)
{
    auto &s=*storage_;if(q>=activeQueues || !healthy() || s.bytes!=16384 || !s.cpu)return false;
    acquire();
    if(OSReadLittleInt32(s.cpu,0)!=0 || OSReadLittleInt32(s.cpu,4)!=tableBytes/4 ||
       OSReadLittleInt32(s.cpu,8)!=6 || OSReadLittleInt32(s.cpu,12)!=12 ||
       OSReadLittleInt32(s.cpu,16)!=3 || OSReadLittleInt32(s.cpu,20)!=3)return false;
    const size_t h=qheader(q);const uint32_t priority=q==2?40u:10u;
    if(OSReadLittleInt32(s.cpu,h)!=1 || OSReadLittleInt32(s.cpu,h+4)!=s.iova+ringStart+q*4096u ||
       OSReadLittleInt32(s.cpu,h+8)!=(q|(priority<<8)) || OSReadLittleInt32(s.cpu,h+12)!=ringWords ||
       OSReadLittleInt32(s.cpu,h+16)!=0)return false;
    r=OSReadLittleInt32(s.cpu,h+40);w=OSReadLittleInt32(s.cpu,h+44);acquire();
    return r<ringWords && w<ringWords && !((r|w)&3u);
}
int ZornGen7DirectHfi26::read(unsigned q,uint32_t (&packet)[19],uint32_t &count)
{
    auto &s=*storage_;count=0;uint32_t r=0,w=0;
    if((q!=1 && q!=2) || !queue(q,r,w))return -1;
    if(r==w)return 0; // Real empty observation, no ACK/status supplied.
    const uint32_t header=OSReadLittleInt32(s.cpu,qdata(q,r));
    const uint32_t words=(header>>8)&255u,padded=(words+3u)&~3u,available=(w-r)&1023u;
    if(!words || words>19 || padded>available)return -1;
    for(unsigned i=0;i<19;++i)packet[i]=0;
    for(uint32_t i=0;i<words;++i)packet[i]=OSReadLittleInt32(s.cpu,qdata(q,(r+i)&1023u));
    complete();OSWriteLittleInt32(s.cpu,qheader(q)+40,(r+padded)&1023u);publish();
    count=words;return 1;
}
ZornGen7DirectHfi26::Outcome ZornGen7DirectHfi26::process(unsigned q,bool actualPending)
{
    auto &s=*storage_;
    // Snapshot finite occupied count to bound an IRQ work item even if firmware
    // keeps producing. Later real interrupt/inline polls consume later data.
    uint32_t r=0,w=0;if(!queue(q,r,w))return Outcome::QueueInvalid;
    const uint32_t initial=(w-r)&1023u;uint32_t consumed=0;
    while(consumed<initial) {
        uint32_t packet[19]{},words=0;const int status=read(q,packet,words);
        if(status<0)return Outcome::QueueInvalid;if(!status)break;
        consumed+=(words+3u)&~3u;
        s.lastWords=words;for(unsigned i=0;i<19;++i)s.lastPacket[i]=packet[i];
        if(((packet[0]>>16)&15u)==1) {
            // Source CMP_HFI_ACK_HDR compares the complete returned request
            // header, ignoring only RECORD. No sequence-only success match.
            if(!actualPending || !s.pending || s.ack || words<2 ||
               (packet[1]&~recordBit)!=(s.sentHeader&~recordBit))return Outcome::UnexpectedAck;
            s.replyWords=words;for(unsigned i=0;i<19;++i)s.reply[i]=packet[i];s.ack=true;
        }else switch(packet[0]&255u) {
            case 100:if(words<18)return Outcome::QueueInvalid;++s.errorPackets;break;
            case 101:if(words<4)return Outcome::QueueInvalid;++s.debugPackets;break;
            default:++s.unknownPackets;break; // Original unsupported request: no reply.
        }
    }
    return Outcome::Drained;
}
int ZornGen7DirectHfi26::consumeIrq(OSObject &object,uint32_t status)
{
    auto *owner=OSDynamicCast(ZornGen7DirectHfi26,&object);
    if(!owner || !owner->healthy())return 1;
    auto &s=*owner->storage_;if(!s.prepared)return 1;
    Outcome result=Outcome::Drained;
    // Exact direct gen7_hfi_irq_handler only drains debug here. MSGQ bit0 is
    // masked and belongs to the inline command owner; SIDEMSG bit1 has no
    // direct-source queue consumer. This callback never steals a command ACK.
    if(status&debugBit){IOLockLock(s.gate);result=owner->process(2,false);IOLockUnlock(s.gate);}
    if(result!=Outcome::Drained){s.failure=result;owner->fail();return 1;}
    return 0; // Source handler returned; no command/GPU completion inferred.
}
IOReturn ZornGen7DirectHfi26::armBoundReceiver()
{
    if(!healthy() || storage_->loop->onThread() || storage_->loop->inGate())return kIOReturnNotReady;
    auto &s=*storage_;IOLockLock(s.gate);
    if(!s.prepared || s.armAttempted){IOLockUnlock(s.gate);return kIOReturnNotReady;}
    s.armAttempted=true;IOLockUnlock(s.gate);const auto raw=s.irq->armBoundReceiver();
    if(raw!=kIOReturnSuccess)fail();return raw;
}
ZornGen7DirectHfi26::Reply ZornGen7DirectHfi26::exchange(unsigned id,const uint32_t *payload,size_t words)
{
    Reply result;
    if(!healthy() || storage_->loop->onThread() || storage_->loop->inGate() ||
       id>255 || words>254 || (words && !payload))return result;
    auto &s=*storage_;IOLockLock(s.gate);
    if(!s.prepared || !s.irq->forwardAllowed() || s.commandBusy || s.pending){IOLockUnlock(s.gate);return result;}
    // Only actual observed HFI register-init bit can admit a command. This is
    // not firmware authentication or proof of the chosen submission protocol.
    uint32_t init=0;s.lastNativeRaw=s.irq->accessHfiWord(0x1f980,false,init);s.lastNativeReturned=true;
    if(s.lastNativeRaw || !(init&1u)){IOLockUnlock(s.gate);fail();return result;}
    uint32_t r=0,w=0;if(!queue(0,r,w)){IOLockUnlock(s.gate);fail();result.outcome=Outcome::QueueInvalid;return result;}
    const uint32_t count=uint32_t(words)+1u,padded=(count+3u)&~3u;
    if(((r-w-1u)&1023u)<padded){IOLockUnlock(s.gate);result.outcome=Outcome::NoSpace;return result;}
    ++s.sequence;const uint32_t header=((s.sequence&4095u)<<20)|(count<<8)|id;
    s.request[0]=header;for(size_t i=0;i<words;++i)s.request[i+1]=payload[i];
    s.sentHeader=header;s.pending=true;s.commandBusy=true;s.ack=false;s.replyWords=0;
    for(uint32_t i=0;i<padded;++i)OSWriteLittleInt32(s.cpu,qdata(0,(w+i)&1023u),i<count?s.request[i]:0xfafafafa);
    publish();OSWriteLittleInt32(s.cpu,qheader(0)+44,(w+padded)&1023u);publish();
    uint32_t notify=1;s.lastNativeRaw=s.irq->accessHfiWord(0x1f994,true,notify);s.lastNativeReturned=true;
    const bool notified=s.lastNativeRaw==0;IOLockUnlock(s.gate);
    if(!notified){result.outcome=Outcome::NativeAccessFailed;fail();return result;}
    uint64_t deadline=0;clock_interval_to_deadline(1000,1000000,&deadline);
    // Source HFI_RSP_TIMEOUT=1000ms and 10..100us poll sleep; use actual native
    // clock and minimum10us delay. One publication only; no command retry.
    bool last=false;
    for(;;) {
        if(!healthy()){fail();return result;}
        uint32_t status=0;s.lastNativeReturned=false;const int raw=s.irq->accessHfiWord(0x1f992,false,status);
        s.lastNativeRaw=raw;s.lastNativeReturned=true;
        if(raw){result.outcome=Outcome::NativeAccessFailed;fail();return result;}
        if(status&msgqBit)break;
        if(last){result.outcome=Outcome::Timeout;fail();return result;}
        uint32_t initResult=0;s.lastNativeReturned=false;
        s.lastNativeRaw=s.irq->accessHfiWord(0x1f81c,false,initResult);s.lastNativeReturned=true;
        if(s.lastNativeRaw){
            result.outcome=Outcome::NativeAccessFailed;fail();return result;}
        uint64_t now=0;clock_get_uptime(&now);
        if((initResult&0xe00u) || now>=deadline){last=true;continue;}
        IODelay(10);
    }
    uint32_t clear=msgqBit;s.lastNativeReturned=false;
    s.lastNativeRaw=s.irq->accessHfiWord(0x1f991,true,clear);s.lastNativeReturned=true;
    if(s.lastNativeRaw){
        result.outcome=Outcome::NativeAccessFailed;fail();return result;}
    IOLockLock(s.gate);const Outcome drained=process(1,true);
    if(drained!=Outcome::Drained || !s.ack || s.replyWords<3 || !healthy()){
        s.failure=drained;IOLockUnlock(s.gate);result.outcome=drained==Outcome::Drained?Outcome::UnexpectedAck:drained;fail();return result;}
    result.outcome=Outcome::ReturnedAck;result.words=s.replyWords;
    for(unsigned i=0;i<19;++i)result.packet[i]=s.reply[i];
    s.pending=false;s.commandBusy=false;IOLockUnlock(s.gate);
    // Preserve full actual ACK, including raw value/status. Its command-specific
    // consumer determines success; transport never invents a zero status word.
    return result;
}
void ZornGen7DirectHfi26::free(){if(pinned_)return;OSObject::free();}

IOReturn ZornGen7DirectHfi26::bindHeldHostGpuOob(OSObject &owner,IORecursiveLock &startup,
    bool (*held)(OSObject &,const ZornGen7DirectHfi26 &))
{
    if(!healthy() || !held || !IORecursiveLockHaveLock(&startup) || !ml_get_interrupts_enabled() || !held(owner,*this))return kIOReturnNotReady;
    auto &s=*storage_;IOLockLock(s.gate);
    if(s.hostOobOwner || s.hostReleaseAttempted || s.commandBusy || s.pending){IOLockUnlock(s.gate);return kIOReturnNotReady;}
    owner.retain();s.hostOobOwner=&owner;s.hostStartup=&startup;s.hostOobHeld=held;IOLockUnlock(s.gate);return kIOReturnSuccess;
}
bool ZornGen7DirectHfi26::bootstrapOobHeld() const
{
    if(!healthy())return false;auto &s=*storage_;IOLockLock(s.gate);
    const bool held=s.hostOobOwner && s.hostStartup && s.hostOobHeld && !s.hostReleaseAttempted &&
        !s.commandBusy && !s.pending && s.hostOobHeld(*s.hostOobOwner,*this);
    IOLockUnlock(s.gate);return held;
}
bool ZornGen7DirectHfi26::bootstrapOobReleaseReturned() const
{
    if(!healthy())return false;auto &s=*storage_;IOLockLock(s.gate);
    const bool returned=s.hostReleaseAttempted && !s.hostReleaseGrantRaw && s.hostReleaseReturned && !s.hostReleaseIoRaw;
    IOLockUnlock(s.gate);return returned;
}
IOReturn ZornGen7DirectHfi26::releaseHostGpuOobAfterBootstrap(ZornGen7HostRing26 &ring)
{
    if(!healthy() || !normal() || !ml_get_interrupts_enabled() || !bootstrapOobHeld() ||
       !ring.bootstrapReadyForOobTransport(*this))return kIOReturnNotReady;
    auto &s=*storage_;
    if(s.loop->onThread() || s.loop->inGate() || IORecursiveLockHaveLock(s.hostStartup))return kIOReturnNotReady;
    IOLockLock(s.gate);
    if(s.commandBusy || s.pending || s.hostReleaseAttempted){IOLockUnlock(s.gate);return kIOReturnNotReady;}
    s.hostReleaseAttempted=true;s.commandBusy=true;IOLockUnlock(s.gate);
    // Independent real board authorization occurs outside command/startup locks.
    s.hostReleaseGrantRaw=s.maps->authorizeHostOobRelease(ring);
    IOLockLock(s.gate);IOReturn raw=s.hostReleaseGrantRaw;
    if(!raw && (!healthy() || s.pending || !s.hostOobHeld(*s.hostOobOwner,*this) ||
       !ring.bootstrapReadyForOobTransport(*this)))raw=kIOReturnNotReady;
    if(!raw){uint32_t clear=1u<<31;
        s.hostReleaseIoRaw=s.maps->accessGmuHfiWord(0x1f994,true,clear);
        s.hostReleaseReturned=!s.hostReleaseIoRaw;
        if(s.hostReleaseIoRaw || !healthy())raw=kIOReturnNotReady;
    }
    s.commandBusy=false;IOLockUnlock(s.gate);if(raw)fail();return raw;
    // Source OOB-clear store returned only. No invented ACK/GX-off/DMA-stop,
    // resource retirement,reset,second clear or command retry follows.
}

IOReturn ZornGen7DirectHfi26::acquireKernelTaskOob(ZornGen7HostRing26 &ring)
{
    if(!healthy() || !normal() || !ml_get_interrupts_enabled() ||
       !ring.kernelTaskPermissionHeld(*this) || !bootstrapOobReleaseReturned())return kIOReturnNotReady;
    auto &s=*storage_;
    if(!s.hostStartup || s.loop->onThread() || s.loop->inGate() ||
       IORecursiveLockHaveLock(s.hostStartup))return kIOReturnNotReady;
    IOLockLock(s.gate);auto &r=s.kernelOob;
    if(r.attempted || s.commandBusy || s.pending){IOLockUnlock(s.gate);return kIOReturnNotReady;}
    r.attempted=true;r.owner=&ring;s.commandBusy=true;
    auto done=[&](IOReturn raw){s.commandBusy=false;IOLockUnlock(s.gate);if(raw)fail();return raw;};
    auto access=[&](uint32_t at,bool write,uint32_t &v){
        if(!healthy() || !ring.kernelTaskPermissionHeld(*this))return false;
        r.lastWord=at;if(write)++r.writes;else ++r.reads;
        r.raw=s.maps->accessGmuHfiWord(at,write,v);
        return !r.raw && healthy() && ring.kernelTaskPermissionHeld(*this);
    };
    auto write=[&](uint32_t at,uint32_t v){return access(at,true,v);};
    constexpr uint32_t request=1u<<30,ack=1u<<31;
    if(!access(0x1f992,false,r.ack) || !access(0x1f996,false,r.host) ||
       (r.ack&ack) || (r.host&(request|ack)))return done(kIOReturnNotReady);
    if(!write(0x1f994,request))return done(kIOReturnNotReady);r.requestReturned=true;
    auto poll=[&](uint32_t at,uint32_t mask,uint32_t expected,uint32_t &v){
        uint64_t deadline=0;clock_interval_to_deadline(100,NSEC_PER_MSEC,&deadline);
        for(;;){if(!access(at,false,v))return false;if((v&mask)==expected)return true;
            uint64_t now=0;clock_get_uptime(&now);
            if(now>deadline)return access(at,false,v) && (v&mask)==expected;
            delay_for_interval_with_leeway(26,74,1000);}
    };
    if(!poll(0x1f992,ack,ack,r.ack))return done(kIOReturnNotReady);r.ackObserved=true;
    if(!write(0x1f991,ack) || !access(0x1f992,false,r.ack) || (r.ack&ack))return done(kIOReturnNotReady);
    r.ackCleared=true;
    if(!poll(0x1f8d0,3u,0u,r.gx))return done(kIOReturnNotReady);
    r.gxOn=true;return done(kIOReturnSuccess);
    // Reuses source Gen7 GPU OOB request/ACK/clear/GX checks for a distinct
    // actual image owner. Bootstrap's returned clear is not this task's grant.
}
bool ZornGen7DirectHfi26::kernelTaskOobHeld(const ZornGen7HostRing26 &ring) const
{
    if(!healthy())return false;const auto &r=storage_->kernelOob;
    return r.owner==&ring && r.attempted && r.requestReturned && r.ackObserved &&
        r.ackCleared && r.gxOn && !r.releaseAttempted;
}
IOReturn ZornGen7DirectHfi26::releaseKernelTaskOob(ZornGen7HostRing26 &ring)
{
    if(!healthy() || !normal() || !ml_get_interrupts_enabled() ||
       !kernelTaskOobHeld(ring) || !ring.kernelTaskReadyToRelease(*this))return kIOReturnNotReady;
    auto &s=*storage_;
    if(!s.hostStartup || s.loop->onThread() || s.loop->inGate() ||
       IORecursiveLockHaveLock(s.hostStartup))return kIOReturnNotReady;
    IOLockLock(s.gate);auto &r=s.kernelOob;
    if(s.commandBusy || s.pending || r.releaseAttempted || !ring.kernelTaskReadyToRelease(*this)){
        IOLockUnlock(s.gate);return kIOReturnNotReady;}
    r.releaseAttempted=true;s.commandBusy=true;
    uint32_t clear=1u<<31;r.lastWord=0x1f994;++r.writes;
    r.raw=s.maps->accessGmuHfiWord(r.lastWord,true,clear);r.releaseWriteReturned=!r.raw;
    const bool valid=!r.raw && healthy() && ring.kernelTaskReadyToRelease(*this);
    s.commandBusy=false;IOLockUnlock(s.gate);
    if(!valid)fail();return valid?kIOReturnSuccess:kIOReturnNotReady;
    // Returned source OOB-clear store only; no invented release ACK or DMA stop.
}
void ZornGen7DirectHfi26::copyKernelTaskOobObservation(uint32_t (&out)[8]) const
{
    for(unsigned i=0;i<8;++i)out[i]=0;if(!storage_)return;const auto &r=storage_->kernelOob;
    out[0]=(r.attempted?1u:0u)|(r.requestReturned?2u:0u)|(r.ackObserved?4u:0u)|
        (r.ackCleared?8u:0u)|(r.gxOn?16u:0u)|(r.releaseAttempted?32u:0u)|(r.releaseWriteReturned?64u:0u);
    out[1]=r.ack;out[2]=r.host;out[3]=r.gx;out[4]=r.reads;out[5]=r.writes;
    out[6]=r.lastWord;out[7]=uint32_t(r.raw);
}

IOReturn ZornGen7DirectHfi26::acquireKernelClientOob(ZornGen7HostRing26 &ring)
{
    if(!healthy() || !normal() || !ml_get_interrupts_enabled() ||
       !ring.kernelClientPermissionHeld(*this) || !bootstrapOobReleaseReturned())return kIOReturnNotReady;
    auto &s=*storage_;
    if(!s.hostStartup || s.loop->onThread() || s.loop->inGate() ||
       IORecursiveLockHaveLock(s.hostStartup))return kIOReturnNotReady;
    IOLockLock(s.gate);auto &r=s.clientOob;
    const auto &task=s.kernelOob;
    // A distinct client session follows this same ring's completed image OOB.
    // Another owner or a partial/failed clear cannot transfer this permission.
    if(task.owner!=&ring || !task.attempted || !task.requestReturned || !task.ackObserved ||
       !task.ackCleared || !task.gxOn || !task.releaseAttempted || !task.releaseWriteReturned || task.raw ||
       r.attempted || s.commandBusy || s.pending){IOLockUnlock(s.gate);return kIOReturnNotReady;}
    r.attempted=true;r.owner=&ring;s.commandBusy=true;
    auto done=[&](IOReturn raw){s.commandBusy=false;IOLockUnlock(s.gate);if(raw)fail();return raw;};
    auto access=[&](uint32_t at,bool write,uint32_t &v){
        if(!healthy() || !ring.kernelClientPermissionHeld(*this))return false;
        r.lastWord=at;if(write)++r.writes;else ++r.reads;
        r.raw=s.maps->accessGmuHfiWord(at,write,v);
        return !r.raw && healthy() && ring.kernelClientPermissionHeld(*this);
    };
    auto write=[&](uint32_t at,uint32_t v){return access(at,true,v);};
    constexpr uint32_t request=1u<<30,ack=1u<<31;
    if(!access(0x1f992,false,r.ack) || !access(0x1f996,false,r.host) ||
       (r.ack&ack) || (r.host&(request|ack)))return done(kIOReturnNotReady);
    if(!write(0x1f994,request))return done(kIOReturnNotReady);r.requestReturned=true;
    auto poll=[&](uint32_t at,uint32_t mask,uint32_t expected,uint32_t &v){
        uint64_t deadline=0;clock_interval_to_deadline(100,NSEC_PER_MSEC,&deadline);
        for(;;){if(!access(at,false,v))return false;if((v&mask)==expected)return true;
            uint64_t now=0;clock_get_uptime(&now);
            if(now>deadline)return access(at,false,v) && (v&mask)==expected;
            delay_for_interval_with_leeway(26,74,1000);}
    };
    if(!poll(0x1f992,ack,ack,r.ack))return done(kIOReturnNotReady);r.ackObserved=true;
    if(!write(0x1f991,ack) || !access(0x1f992,false,r.ack) || (r.ack&ack))return done(kIOReturnNotReady);
    r.ackCleared=true;
    if(!poll(0x1f8d0,3u,0u,r.gx))return done(kIOReturnNotReady);
    r.gxOn=true;return done(kIOReturnSuccess);
    // Reuses source Gen7 GPU OOB request/ACK/clear/GX checks for a distinct
    // actual client owner. The image's returned clear is not this client's grant.
}
bool ZornGen7DirectHfi26::kernelClientOobHeld(const ZornGen7HostRing26 &ring) const
{
    if(!healthy())return false;const auto &r=storage_->clientOob;
    return r.owner==&ring && r.attempted && r.requestReturned && r.ackObserved &&
        r.ackCleared && r.gxOn && !r.releaseAttempted;
}
IOReturn ZornGen7DirectHfi26::releaseKernelClientOob(ZornGen7HostRing26 &ring)
{
    if(!healthy() || !normal() || !ml_get_interrupts_enabled() ||
       !kernelClientOobHeld(ring) || !ring.kernelClientReadyToRelease(*this))return kIOReturnNotReady;
    auto &s=*storage_;
    if(!s.hostStartup || s.loop->onThread() || s.loop->inGate() ||
       IORecursiveLockHaveLock(s.hostStartup))return kIOReturnNotReady;
    IOLockLock(s.gate);auto &r=s.clientOob;
    if(s.commandBusy || s.pending || r.releaseAttempted || !ring.kernelClientReadyToRelease(*this)){
        IOLockUnlock(s.gate);return kIOReturnNotReady;}
    r.releaseAttempted=true;s.commandBusy=true;
    uint32_t clear=1u<<31;r.lastWord=0x1f994;++r.writes;
    r.raw=s.maps->accessGmuHfiWord(r.lastWord,true,clear);r.releaseWriteReturned=!r.raw;
    const bool valid=!r.raw && healthy() && ring.kernelClientReadyToRelease(*this);
    s.commandBusy=false;IOLockUnlock(s.gate);
    if(!valid)fail();return valid?kIOReturnSuccess:kIOReturnNotReady;
    // Returned source OOB-clear store only; no invented release ACK or DMA stop.
}
void ZornGen7DirectHfi26::copyKernelClientOobObservation(uint32_t (&out)[8]) const
{
    for(unsigned i=0;i<8;++i)out[i]=0;if(!storage_)return;const auto &r=storage_->clientOob;
    out[0]=(r.attempted?1u:0u)|(r.requestReturned?2u:0u)|(r.ackObserved?4u:0u)|
        (r.ackCleared?8u:0u)|(r.gxOn?16u:0u)|(r.releaseAttempted?32u:0u)|(r.releaseWriteReturned?64u:0u);
    out[1]=r.ack;out[2]=r.host;out[3]=r.gx;out[4]=r.reads;out[5]=r.writes;
    out[6]=r.lastWord;out[7]=uint32_t(r.raw);
}


// The actual per-application owner carries its own fresh request history.
// Reuse the retained Gen7 OOB sequence; never inherit a kernel grant.
IOReturn ZornGen7DirectHfi26::acquireApplicationOob(ZornGen7HostRing26 &ring,ZornGen7AppExecution26 &execution)
{
    if(!normal() || !healthy() || !ml_get_interrupts_enabled() || !bootstrapOobReleaseReturned())return kIOReturnNotReady;
    auto &s=*storage_;
    if(!s.hostStartup || s.loop->onThread() || s.loop->inGate() || IORecursiveLockHaveLock(s.hostStartup) ||
       execution.ring_!=&ring || !ring.applicationOobPermission(*this,execution,false))return kIOReturnNotReady;
    IOLockLock(s.gate);auto &r=execution.oob_;const auto &task=s.kernelOob;
    if(task.owner!=&ring || !task.attempted || !task.requestReturned || !task.ackObserved ||
       !task.ackCleared || !task.gxOn || !task.releaseAttempted || !task.releaseWriteReturned || task.raw ||
       s.clientOob.attempted || r.attempted || s.activeApp || s.commandBusy || s.pending){
        IOLockUnlock(s.gate);return kIOReturnNotReady;}
    r.attempted=true;r.owner=this;execution.retain();s.activeApp=&execution;s.commandBusy=true;
    auto done=[&](IOReturn raw){s.commandBusy=false;IOLockUnlock(s.gate);if(raw)fail();return raw;};
    auto permission=[&](){
        // Real app authority callbacks run with no HFI/issuer/startup lock.
        // commandBusy and activeApp retain the sole transition across reentry.
        IOLockUnlock(s.gate);const bool held=ring.applicationOobPermission(*this,execution,false);IOLockLock(s.gate);
        return held && healthy() && s.commandBusy && s.activeApp==&execution &&
            r.owner==this && r.attempted && !r.releaseAttempted;
    };
    auto read=[&](uint32_t at,uint32_t &v){if(!permission())return false;
        r.raw=s.maps->accessGmuHfiWord(at,false,v);return !r.raw && healthy();};
    auto write=[&](uint32_t at,uint32_t v){if(!permission())return false;
        r.raw=s.maps->accessGmuHfiWord(at,true,v);return !r.raw && healthy();};
    constexpr uint32_t request=1u<<30,ack=1u<<31;
    if(!read(0x1f992,r.ack) || !read(0x1f996,r.host) || (r.ack&ack) || (r.host&(request|ack)))return done(kIOReturnNotReady);
    if(!write(0x1f994,request))return done(kIOReturnNotReady);r.requestReturned=true;
    auto poll=[&](uint32_t at,uint32_t mask,uint32_t expected,uint32_t &v){
        uint64_t deadline=0;clock_interval_to_deadline(100,NSEC_PER_MSEC,&deadline);
        for(;;){if(!read(at,v))return false;if((v&mask)==expected)return true;
            uint64_t now=0;clock_get_uptime(&now);if(now>deadline)return read(at,v) && (v&mask)==expected;
            delay_for_interval_with_leeway(26,74,1000);}
    };
    if(!poll(0x1f992,ack,ack,r.ack))return done(kIOReturnNotReady);r.ackObserved=true;
    if(!write(0x1f991,ack) || !read(0x1f992,r.ack) || (r.ack&ack))return done(kIOReturnNotReady);r.ackCleared=true;
    if(!poll(0x1f8d0,3u,0u,r.gx))return done(kIOReturnNotReady);r.gxOn=true;
    return done(kIOReturnSuccess);
}
bool ZornGen7DirectHfi26::applicationOobHeld(const ZornGen7HostRing26 &ring,const ZornGen7AppExecution26 &execution) const
{
    if(!storage_ || !healthy())return false;const auto &r=execution.oob_;
    return execution.ring_==&ring && storage_->activeApp==&execution && r.owner==this && r.attempted &&
        r.requestReturned && r.ackObserved && r.ackCleared && r.gxOn && !r.releaseAttempted;
}
IOReturn ZornGen7DirectHfi26::releaseApplicationOob(ZornGen7HostRing26 &ring,ZornGen7AppExecution26 &execution)
{
    if(!normal() || !healthy() || !ml_get_interrupts_enabled() || !applicationOobHeld(ring,execution))return kIOReturnNotReady;
    auto &s=*storage_;
    if(!s.hostStartup || s.loop->onThread() || s.loop->inGate() || IORecursiveLockHaveLock(s.hostStartup) ||
       !ring.applicationOobReleaseReady(*this,execution) || !ring.applicationOobPermission(*this,execution,true))return kIOReturnNotReady;
    IOLockLock(s.gate);auto &r=execution.oob_;
    if(s.activeApp!=&execution || r.releaseAttempted || s.commandBusy || s.pending){IOLockUnlock(s.gate);return kIOReturnNotReady;}
    r.releaseAttempted=true;s.commandBusy=true;
    IOLockUnlock(s.gate);const bool held=ring.applicationOobPermission(*this,execution,true);IOLockLock(s.gate);
    if(!held || !healthy() || s.activeApp!=&execution || !s.commandBusy ||
       !ring.applicationOobReleaseReady(*this,execution)){
        s.commandBusy=false;IOLockUnlock(s.gate);fail();return kIOReturnNotReady;}
    uint32_t clear=1u<<31;r.raw=s.maps->accessGmuHfiWord(0x1f994,true,clear);r.releaseWriteReturned=!r.raw;
    if(r.raw || !healthy()) {s.commandBusy=false;IOLockUnlock(s.gate);fail();return kIOReturnNotReady;}
    s.activeApp=nullptr;s.commandBusy=false;IOLockUnlock(s.gate);execution.release();
    return kIOReturnSuccess; // returned clear store only, no DMA-stop or release ACK claim
}

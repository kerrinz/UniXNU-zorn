// SPDX-License-Identifier: GPL-2.0-only
#include "ZornGen7GmuIrq26.h"
#include "ZornGen7RegisterMaps26.h"
#include "ZornGen7ScmOwner26.h"
#include "houji_full_host_runtime.h"
#include <IOKit/IOInterruptEventSource.h>
#include <IOKit/IOInterrupts.h>
#include <IOKit/IOLib.h>
#include <IOKit/IOPlatformExpert.h>
#include <libkern/c++/OSData.h>
#include <libkern/c++/OSSharedPtr.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
extern "C" kern_return_t gic_v3_spi_attach_zorn_gmu_masked(uint32_t,bool,void (*)(void *,uint32_t),void *,ZornGicSpiObservation26 *);
extern "C" kern_return_t gic_v3_spi_set_enabled_checked(uint32_t,void *,bool);
namespace {
bool normal(){return preemption_enabled() && !ml_at_interrupt_context();}
uint32_t little(const uint8_t *p){return uint32_t(p[0])|(uint32_t(p[1])<<8)|(uint32_t(p[2])<<16)|(uint32_t(p[3])<<24);}
IOReturn translate(kern_return_t raw){switch(raw){case KERN_SUCCESS:return kIOReturnSuccess;
case KERN_INVALID_ARGUMENT:return kIOReturnBadArgument;case KERN_NAME_EXISTS:return kIOReturnExclusiveAccess;
case KERN_RESOURCE_SHORTAGE:return kIOReturnNoResources;case KERN_INVALID_NAME:return kIOReturnNotReady;
default:return kIOReturnIOError;}}
uint32_t nativeGmuIrq[2]{};
uint32_t nativeGmuArmed;
constexpr uint32_t hfiMask=(1u<<1)|(1u<<2)|(1u<<15),aoMask=(1u<<0)|(1u<<3)|(1u<<5);
}
extern "C" uint64_t zorn26_native_gmu_irq_observed()
{
    return (uint64_t(__atomic_load_n(&nativeGmuIrq[1],__ATOMIC_ACQUIRE))<<32) |
        __atomic_load_n(&nativeGmuIrq[0],__ATOMIC_ACQUIRE);
}
extern "C" uint32_t zorn26_native_gmu_armed()
{
    return __atomic_load_n(&nativeGmuArmed,__ATOMIC_ACQUIRE);
}
// Real native GIC bridge for this actual GMU provider. Reuses the same checked
// attach/mask implementation as RSC/SMMU; no replacement controller or fake IRQ.
class ZornGen7GmuIrqProvider26 final : public IOService {
    OSDeclareDefaultStructors(ZornGen7GmuIrqProvider26);
public:
    static IOReturn create(IOService &,ZornGen7GmuIrq26 &,OSObject &,
        const ZornGen7GmuIrqAuthority26 &,ZornGen7GmuIrqProvider26 *&,bool nativeGic=false);
    IOReturn registerInterrupt(int,OSObject *,IOInterruptAction,void *) override;
    IOReturn getInterruptType(int,int *) override;
    IOReturn enableInterrupt(int) override;
    IOReturn disableInterrupt(int) override;
    IOReturn unregisterInterrupt(int) override{return kIOReturnUnsupported;}
    IOReturn causeInterrupt(int) override{return kIOReturnUnsupported;}
    bool initiallyMasked() const;
    void free() override{if(pinned_)return;IOService::free();}
private:
    struct Slot {ZornGen7GmuIrqProvider26 *provider=nullptr;unsigned source=0;uint32_t intid=0;
        OSObject *target=nullptr;IOInterruptAction action=nullptr;void *refcon=nullptr;
        uint32_t state=0,maskFailed=0,lastReturned=0,lastEnabled=0,everEnabled=0;
        kern_return_t attachRaw=0,lastRaw=0;int grantRaw=0;bool grantReturned=false;};
    struct Storage {IOService *gmu=nullptr;ZornGen7GmuIrq26 *receiver=nullptr;OSObject *owner=nullptr;
        ZornGen7GmuIrqAuthority26 authority;Slot slots[2];bool prepared=false,nativeGic=false;
        static void *operator new(size_t,void *p)noexcept{return p;}};
    Storage *storage_=nullptr;bool pinned_=false;
    static void deliver(void *,uint32_t);
};
OSDefineMetaClassAndStructors(ZornGen7GmuIrqProvider26,IOService);
OSDefineMetaClassAndStructors(ZornGen7GmuIrq26,OSObject);
IOReturn ZornGen7GmuIrqProvider26::create(IOService &gmu,ZornGen7GmuIrq26 &receiver,OSObject &owner,
    const ZornGen7GmuIrqAuthority26 &authority,ZornGen7GmuIrqProvider26 *&out,bool nativeGic)
{
    if(out || !normal() || (!nativeGic && !authority.authorizeActualSpi))return kIOReturnBadArgument;
    OSSharedPtr<OSObject> no(gmu.copyProperty("interrupt-names"),OSNoRetain),io(gmu.copyProperty("interrupts"),OSNoRetain);
    auto *names=OSDynamicCast(OSData,no.get());auto *data=OSDynamicCast(OSData,io.get());
    constexpr char expected[]="hfi\0gmu";
    if(!names || names->getLength()!=sizeof(expected) || !names->getBytesNoCopy() ||
       !data || data->getLength()!=24 || !data->getBytesNoCopy())return kIOReturnBadArgument;
    auto *nb=static_cast<const uint8_t *>(names->getBytesNoCopy());
    for(size_t i=0;i<sizeof(expected);++i)if(nb[i]!=uint8_t(expected[i]))return kIOReturnUnsupported;
    auto *bytes=static_cast<const uint8_t *>(data->getBytesNoCopy());uint32_t ids[2]{};
    for(unsigned i=0;i<2;++i){const auto *at=bytes+12*i;
        if(little(at)!=0 || little(at+4)!=304u+i || little(at+8)!=4)return kIOReturnUnsupported;
        ids[i]=little(at+4)+32u;}
    auto *p=new ZornGen7GmuIrqProvider26;if(!p)return kIOReturnNoMemory;
    if(!p->init()){p->release();return kIOReturnNoMemory;}
    p->retain();p->pinned_=true;out=p;gmu.retain();receiver.retain();owner.retain();
    void *memory=IOMallocZero(sizeof(Storage));if(!memory)return kIOReturnNoMemory;
    p->storage_=new(memory)Storage;auto &s=*p->storage_;
    s.gmu=&gmu;s.receiver=&receiver;s.owner=&owner;s.authority=authority;s.nativeGic=nativeGic;
    for(unsigned i=0;i<2;++i){s.slots[i].provider=p;s.slots[i].source=i;s.slots[i].intid=ids[i];}
    if(!p->attach(&gmu))return kIOReturnNotAttached;
    s.prepared=true;return kIOReturnSuccess;
}
IOReturn ZornGen7GmuIrqProvider26::getInterruptType(int source,int *type)
{if(!storage_ || !storage_->prepared || source<0 || source>=2 || !type)return kIOReturnBadArgument;
 *type=kIOInterruptTypeLevel;return kIOReturnSuccess;}
IOReturn ZornGen7GmuIrqProvider26::registerInterrupt(int source,OSObject *target,IOInterruptAction action,void *refcon)
{
    if(!storage_ || !storage_->prepared || !normal() || source<0 || source>=2 || !target || !action)
        return kIOReturnBadArgument;
    auto &s=*storage_;auto &slot=s.slots[source];uint32_t expected=0;
    if(!__atomic_compare_exchange_n(&slot.state,&expected,1,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))return kIOReturnExclusiveAccess;
    if(!s.nativeGic) {
        slot.grantRaw=s.authority.authorizeActualSpi(s.authority.cookie,*s.gmu,unsigned(source),slot.intid);
        slot.grantReturned=true;
        if(slot.grantRaw){__atomic_store_n(&slot.state,3u,__ATOMIC_RELEASE);return kIOReturnNotPermitted;}
    }
    target->retain();slot.target=target;slot.action=action;slot.refcon=refcon;
    ZornGicSpiObservation26 observation{};
    slot.attachRaw=gic_v3_spi_attach_zorn_gmu_masked(slot.intid,false,deliver,&slot,&observation);
    const uint32_t report=(1u<<31) | (uint32_t(slot.attachRaw)&255u) |
        ((observation.readMask&127u)<<8) |
        ((observation.route==observation.requestedRoute?1u:0u)<<16) |
        ((observation.configuration&3u)<<17) | ((observation.enabled?1u:0u)<<19) |
        ((observation.priority&255u)<<20);
    __atomic_store_n(&nativeGmuIrq[source],report,__ATOMIC_RELEASE);
    __atomic_store_n(&slot.state,slot.attachRaw==KERN_SUCCESS?2u:3u,__ATOMIC_RELEASE);return translate(slot.attachRaw);
}
void ZornGen7GmuIrqProvider26::deliver(void *context,uint32_t intid)
{
    auto *slot=static_cast<Slot *>(context);if(!slot || slot->intid!=intid || !slot->action)return;
    slot->provider->storage_->receiver->primaryArrived();
    // XNU's real level-trigger primary masks this exact SPI and wakes its workloop.
    slot->action(slot->target,slot->refcon,slot->provider,int(slot->source));
}
IOReturn ZornGen7GmuIrqProvider26::enableInterrupt(int source)
{
    if(!storage_ || source<0 || source>=2)return kIOReturnBadArgument;auto &s=*storage_;auto &slot=s.slots[source];
    if(__atomic_load_n(&slot.state,__ATOMIC_ACQUIRE)!=2 ||
       __atomic_load_n(&slot.maskFailed,__ATOMIC_ACQUIRE) || !s.receiver->forwardAllowed()) {
        // IOInterruptEventSource::enable() discards the provider's return.
        // Latch this refusal so the arm caller stops and masks both sources.
        s.receiver->stopFromProvider();
        return kIOReturnNotReady;
    }
    __atomic_store_n(&slot.everEnabled,1u,__ATOMIC_RELEASE);
    const auto raw=gic_v3_spi_set_enabled_checked(slot.intid,&slot,true);
    __atomic_store_n(&slot.lastRaw,raw,__ATOMIC_RELAXED);__atomic_store_n(&slot.lastEnabled,1u,__ATOMIC_RELAXED);
    __atomic_store_n(&slot.lastReturned,1u,__ATOMIC_RELEASE);
    if(raw!=KERN_SUCCESS)s.receiver->stopFromProvider();
    else __atomic_fetch_or(&nativeGmuArmed,1u<<source,__ATOMIC_RELEASE);
    return translate(raw);
}
IOReturn ZornGen7GmuIrqProvider26::disableInterrupt(int source)
{
    if(!storage_ || source<0 || source>=2)return kIOReturnBadArgument;auto &s=*storage_;auto &slot=s.slots[source];
    if(__atomic_load_n(&slot.state,__ATOMIC_ACQUIRE)!=2 || __atomic_load_n(&slot.maskFailed,__ATOMIC_ACQUIRE))return kIOReturnNotReady;
    if(!__atomic_load_n(&slot.everEnabled,__ATOMIC_ACQUIRE) &&
       __atomic_load_n(&slot.lastReturned,__ATOMIC_ACQUIRE) && !__atomic_load_n(&slot.lastEnabled,__ATOMIC_RELAXED) &&
       __atomic_load_n(&slot.lastRaw,__ATOMIC_RELAXED)==KERN_SUCCESS)return kIOReturnSuccess;
    const auto raw=gic_v3_spi_set_enabled_checked(slot.intid,&slot,false);
    __atomic_store_n(&slot.lastRaw,raw,__ATOMIC_RELAXED);__atomic_store_n(&slot.lastEnabled,0u,__ATOMIC_RELAXED);
    __atomic_store_n(&slot.lastReturned,1u,__ATOMIC_RELEASE);
    if(raw!=KERN_SUCCESS){__atomic_store_n(&slot.maskFailed,1u,__ATOMIC_RELEASE);s.receiver->stopFromProvider();}
    return translate(raw);
}
bool ZornGen7GmuIrqProvider26::initiallyMasked() const
{
    if(!storage_ || !storage_->prepared)return false;
    for(const auto &slot:storage_->slots)if(__atomic_load_n(&slot.everEnabled,__ATOMIC_ACQUIRE) ||
        __atomic_load_n(&slot.state,__ATOMIC_ACQUIRE)!=2 ||
        !__atomic_load_n(&slot.lastReturned,__ATOMIC_ACQUIRE) || __atomic_load_n(&slot.lastEnabled,__ATOMIC_RELAXED) ||
        __atomic_load_n(&slot.lastRaw,__ATOMIC_RELAXED)!=KERN_SUCCESS)return false;
    return true;
}
struct ZornGen7GmuIrq26::Storage {
    IOService *gmu=nullptr;ZornGen7RegisterMaps26 *maps=nullptr;IOWorkLoop *loop=nullptr;
    ZornGen7ScmOwner26 *completedCxOwner=nullptr;
    ZornGen7GmuIrqProvider26 *provider=nullptr;IOInterruptEventSource *events[2]{};
    IOLock *gate=nullptr;IORecursiveLock *ioSerial=nullptr;uint32_t stopped=0,armed=0,primaryCount=0,actions=0,maskAttempted=0;
    volatile int32_t cm3_fault=0; // Actual shared source state, not observed hardware state.
    uint32_t interruptMask=hfiMask;bool hwschedReceiver=false;
    bool prepared=false,configAttempted=false,configRunning=false,faultCleared=false,configured=false,armAttempted=false;
    IOReturn factoryStatus=kIOReturnNotReady,workloopStatus[2]{kIOReturnNotReady,kIOReturnNotReady};
    ZornGen7RegisterConfig::CheckedResult config{};
    uint32_t status[2]{},fenceStatus=0;int readRaw[2]{},ackRaw[2]{},fenceRaw=0,receiverRaw=0;bool statusValid[2]{};
    OSObject *receiver=nullptr;int (*consume)(OSObject &,uint32_t)=nullptr;
    static void *operator new(size_t,void *p)noexcept{return p;}
};
IOReturn ZornGen7GmuIrq26::createDisabled(IOService &gmu,ZornGen7RegisterMaps26 &maps,IOWorkLoop &loop,
    OSObject &authorityOwner,const ZornGen7GmuIrqAuthority26 &authority,ZornGen7GmuIrq26 *&out)
{
    return createDisabledImpl(gmu,maps,loop,authorityOwner,authority,nullptr,out);
}
IOReturn ZornGen7GmuIrq26::createDisabledWithNativeGic(IOService &gmu,ZornGen7RegisterMaps26 &maps,IOWorkLoop &loop,
    OSObject &owner,ZornGen7ScmOwner26 &completedCx,const IORecursiveLock &startup,ZornGen7GmuIrq26 *&out)
{
    if(!normal() || !IORecursiveLockHaveLock(&startup) || !IOService::getPlatform() ||
       gmu.getProvider()!=IOService::getPlatform())return kIOReturnNotReady;
    const ZornGen7GmuIrqAuthority26 noExternalCallback{};
    return createDisabledImpl(gmu,maps,loop,owner,noExternalCallback,&completedCx,out);
}
IOReturn ZornGen7GmuIrq26::createDisabledImpl(IOService &gmu,ZornGen7RegisterMaps26 &maps,IOWorkLoop &loop,
    OSObject &authorityOwner,const ZornGen7GmuIrqAuthority26 &authority,ZornGen7ScmOwner26 *completedCx,
    ZornGen7GmuIrq26 *&out)
{
    if(out || !normal() || loop.onThread() || loop.inGate() ||
       (!completedCx && !authority.authorizeActualSpi) || !maps.readResult().mapsReady)
        return kIOReturnBadArgument;
    auto *owner=new ZornGen7GmuIrq26;if(!owner)return kIOReturnNoMemory;
    if(!owner->init()){owner->release();return kIOReturnNoMemory;}
    owner->retain();owner->pinned_=true;out=owner;gmu.retain();maps.retain();loop.retain();authorityOwner.retain();
    if(completedCx)completedCx->retain();
    void *memory=IOMallocZero(sizeof(Storage));if(!memory)return kIOReturnNoMemory;
    owner->storage_=new(memory)Storage;auto &s=*owner->storage_;s.gmu=&gmu;s.maps=&maps;s.loop=&loop;
    s.completedCxOwner=completedCx;
    s.gate=IOLockAlloc();if(!s.gate)return kIOReturnNoMemory;
    s.ioSerial=IORecursiveLockAlloc();if(!s.ioSerial)return kIOReturnNoMemory;
    s.factoryStatus=ZornGen7GmuIrqProvider26::create(gmu,*owner,authorityOwner,authority,s.provider,completedCx!=nullptr);
    if(s.factoryStatus!=kIOReturnSuccess || !s.provider)return s.factoryStatus;
    for(unsigned i=0;i<2;++i){auto event=IOInterruptEventSource::interruptEventSource(owner,action,s.provider,int(i));
        if(!event)return kIOReturnNoResources;
        s.events[i]=event; // Actual exported OSPtr API returns an owned raw pointer.
        s.events[i]->disable();
        s.workloopStatus[i]=loop.addEventSource(s.events[i]);if(s.workloopStatus[i]!=kIOReturnSuccess)return s.workloopStatus[i];}
    if(owner->halted() || !s.provider->initiallyMasked())return kIOReturnNotReady;
    s.prepared=true;return kIOReturnSuccess;
}
bool ZornGen7GmuIrq26::halted() const{return !storage_ || __atomic_load_n(&storage_->stopped,__ATOMIC_ACQUIRE)!=0;}
bool ZornGen7GmuIrq26::forwardAllowed() const
{return storage_ && __atomic_load_n(&storage_->armed,__ATOMIC_ACQUIRE) && !halted();}
void ZornGen7GmuIrq26::stopFromProvider(){if(storage_)__atomic_store_n(&storage_->stopped,1u,__ATOMIC_RELEASE);}
void ZornGen7GmuIrq26::primaryArrived()
{if(!storage_)return;__atomic_fetch_add(&storage_->primaryCount,1u,__ATOMIC_RELAXED);if(!forwardAllowed())stopFromProvider();}
void ZornGen7GmuIrq26::stopAndMask()
{
    if(!storage_)return;auto &s=*storage_;stopFromProvider();
    if(__atomic_exchange_n(&s.maskAttempted,1u,__ATOMIC_ACQ_REL) || !s.provider)return;
    for(unsigned i=0;i<2;++i)if(s.events[i])s.events[i]->disable();
    // Each failed native mask is latched and cannot be retried by XNU auto-enable.
}
int ZornGen7GmuIrq26::clearFault(OSObject &object)
{
    auto *owner=OSDynamicCast(ZornGen7GmuIrq26,&object);if(!owner || !owner->storage_ || !normal())return FHR_ARGUMENT;
    auto &s=*owner->storage_;IOLockLock(s.gate);
    if(!s.prepared || !s.configRunning || s.faultCleared || owner->halted() ||
       __atomic_load_n(&s.armed,__ATOMIC_ACQUIRE) || __atomic_load_n(&s.primaryCount,__ATOMIC_ACQUIRE) ||
       __atomic_load_n(&s.actions,__ATOMIC_ACQUIRE) || !s.provider->initiallyMasked()){IOLockUnlock(s.gate);return FHR_NOT_AVAILABLE;}
    __atomic_store_n(&s.cm3_fault,0,__ATOMIC_RELAXED);s.faultCleared=true;IOLockUnlock(s.gate);return 0;
}
ZornGen7RegisterConfig::CheckedResult ZornGen7GmuIrq26::configure(const ZornGen7RegisterConfig::Parameters &parameters)
{
    if(!storage_ || !normal())return {};auto &s=*storage_;IOLockLock(s.gate);
    if(!s.prepared || s.configAttempted || halted()){auto result=s.config;IOLockUnlock(s.gate);return result;}
    s.configAttempted=true;s.configRunning=true;IOLockUnlock(s.gate);
    const auto result=s.maps->configureGen7ControlRegisters(parameters,*this,clearFault);
    IOLockLock(s.gate);s.config=result;s.configRunning=false;
    s.configured=result.source.assessment==ZornGen7RegisterConfig::Assessment::StoresReturned && !halted();
    IOLockUnlock(s.gate);if(!s.configured)stopAndMask();return result;
}
IOReturn ZornGen7GmuIrq26::bindReceiver(OSObject &receiver,int (*consume)(OSObject &,uint32_t))
{
    if(!storage_ || !normal() || !consume)return kIOReturnBadArgument;auto &s=*storage_;IOLockLock(s.gate);
    if(!s.prepared || !s.configured || s.receiver || s.armAttempted || halted() || !s.provider->initiallyMasked()){
        IOLockUnlock(s.gate);return kIOReturnNotReady;}
    receiver.retain();s.receiver=&receiver;s.consume=consume;IOLockUnlock(s.gate);return kIOReturnSuccess;
}
IOReturn ZornGen7GmuIrq26::armBoundReceiver()
{
    if(!storage_ || !normal())return kIOReturnBadArgument;auto &s=*storage_;IOLockLock(s.gate);
    if(!s.prepared || !s.configured || !s.receiver || !s.consume || s.armAttempted || halted() ||
       !s.provider->initiallyMasked()){IOLockUnlock(s.gate);return kIOReturnNotReady;}
    s.armAttempted=true;IOLockUnlock(s.gate);
    const uint32_t words[]={0x1f991,0x23b04,0x1f993,0x23b06};uint32_t values[]={UINT32_MAX,UINT32_MAX,~__atomic_load_n(&s.interruptMask,__ATOMIC_ACQUIRE),~aoMask};
    for(unsigned i=0;i<4;++i)if(accessIrqWord(words[i],true,values[i])){stopAndMask();return kIOReturnNotReady;}
    __atomic_store_n(&s.armed,1u,__ATOMIC_RELEASE);
    for(unsigned i=0;i<2;++i){s.events[i]->enable();if(halted()){stopAndMask();return kIOReturnNotReady;}}
    return kIOReturnSuccess; // Provider observes real checked GIC operations; no delivery/HFI ACK claim.
}
void ZornGen7GmuIrq26::action(OSObject *object,IOInterruptEventSource *sender,int count)
{
    auto *owner=OSDynamicCast(ZornGen7GmuIrq26,object);if(!owner || !owner->storage_ || !sender || count<=0)return;
    auto &s=*owner->storage_;for(unsigned i=0;i<2;++i)if(s.events[i]==sender){owner->handle(i);return;}
}
void ZornGen7GmuIrq26::handle(unsigned source)
{
    if(!storage_ || source>=2 || !normal())return;auto &s=*storage_;
    __atomic_fetch_add(&s.actions,1u,__ATOMIC_ACQ_REL);
    auto finish=[&](){__atomic_fetch_sub(&s.actions,1u,__ATOMIC_RELEASE);};
    if(!forwardAllowed()){stopAndMask();finish();return;}
    const uint32_t read=source?0x23b05:0x1f992,clear=source?0x23b04:0x1f991;
    uint32_t status=0;s.readRaw[source]=accessIrqWord(read,false,status);
    if(s.readRaw[source]){stopAndMask();finish();return;}
    s.status[source]=status;s.statusValid[source]=true;
    const uint32_t mask=__atomic_load_n(&s.interruptMask,__ATOMIC_ACQUIRE);
    uint32_t ack=source?status:(s.hwschedReceiver?(status&mask):hfiMask);
    s.ackRaw[source]=accessIrqWord(clear,true,ack);
    if(s.ackRaw[source]){stopAndMask();finish();return;}
    if(!source){
        if(status&(1u<<15)){__atomic_store_n(&s.cm3_fault,1,__ATOMIC_RELAXED);__atomic_thread_fence(__ATOMIC_RELEASE);stopAndMask();}
        if(s.hwschedReceiver){if(!(mask&1u))status&=~1u;status&=0x01ffffffu;if(status&~mask)stopAndMask();}
        else if(status&~hfiMask)stopAndMask();
        if(!halted() && status && s.consume){s.receiverRaw=s.consume(*s.receiver,status);if(s.receiverRaw)stopAndMask();}
    }else if(status){
        if(status&(1u<<3))s.fenceRaw=accessIrqWord(0x23b13,false,s.fenceStatus);
        // Strict retained-failure candidate: actual AO error/unknown status stops.
        // No source watchdog NMI, reset, power transition or recovery is issued.
        stopAndMask();
    }
    finish();
}
void ZornGen7GmuIrq26::free(){if(pinned_)return;OSObject::free();}

int ZornGen7GmuIrq26::accessHfiWord(uint32_t word,bool write,uint32_t &value)
{
    if(!storage_ || !normal() || halted() || !storage_->ioSerial)return FHR_NOT_AVAILABLE;
    auto &s=*storage_;IORecursiveLockLock(s.ioSerial);
    const int raw=halted()?FHR_NOT_AVAILABLE:s.maps->accessGmuHfiWord(word,write,value);
    IORecursiveLockUnlock(s.ioSerial);return raw;
}
int ZornGen7GmuIrq26::accessIrqWord(uint32_t word,bool write,uint32_t &value)
{
    if(!storage_ || !normal() || halted() || !storage_->ioSerial)return FHR_NOT_AVAILABLE;
    auto &s=*storage_;IORecursiveLockLock(s.ioSerial);
    const int raw=halted()?FHR_NOT_AVAILABLE:s.maps->accessGmuIrqWord(word,write,value);
    IORecursiveLockUnlock(s.ioSerial);return raw;
    // Never hold ioSerial across the real HFI consume callback: IRQ work and
    // inline command polling share native I/O serialization without inversion.
}

IOReturn ZornGen7GmuIrq26::bindHwschedReceiver(OSObject &receiver,int (*consume)(OSObject &,uint32_t))
{
    const auto raw=bindReceiver(receiver,consume);if(raw!=kIOReturnSuccess)return raw;
    auto &s=*storage_;IOLockLock(s.gate);s.hwschedReceiver=true;IOLockUnlock(s.gate);return kIOReturnSuccess;
}
IOReturn ZornGen7GmuIrq26::enableHwschedAsync(OSObject &receiver)
{
    if(!storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;IOLockLock(s.gate);
    if(!s.hwschedReceiver || s.receiver!=&receiver || !forwardAllowed() ||
       (__atomic_load_n(&s.interruptMask,__ATOMIC_ACQUIRE)&1u)){IOLockUnlock(s.gate);return kIOReturnNotReady;}
    // Source updates its CPU mask BEFORE the native mask store. A real IRQ
    // may arrive immediately;failure retains this state and stops all forward IO.
    const uint32_t mask=__atomic_load_n(&s.interruptMask,__ATOMIC_RELAXED)|1u;
    __atomic_store_n(&s.interruptMask,mask,__ATOMIC_RELEASE);IOLockUnlock(s.gate);
    uint32_t value=~mask;const int raw=accessIrqWord(0x1f993,true,value);
    if(raw || halted()){stopAndMask();return kIOReturnNotReady;}return kIOReturnSuccess;
}

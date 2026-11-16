// SPDX-License-Identifier: GPL-2.0-only
#include "ZornGen7GpuIrq26.h"
#include "ZornGen7HostGpuRegisters26.h"
#include "ZornGen7InactiveOwner26.h"
#include "ZornGen7RegisterMaps26.h"
#include "houji_full_host_runtime.h"
#include <IOKit/IOInterruptEventSource.h>
#include <IOKit/IOInterrupts.h>
#include <IOKit/IOLib.h>
#include <IOKit/IOPlatformExpert.h>
#include <libkern/c++/OSData.h>
#include <libkern/c++/OSSharedPtr.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
extern "C" kern_return_t gic_v3_spi_attach_zorn_gpu_masked(uint32_t,bool,void (*)(void *,uint32_t),void *,ZornGicSpiObservation26 *);
extern "C" kern_return_t gic_v3_spi_set_enabled_checked(uint32_t,void *,bool);
namespace {
bool normal(){return preemption_enabled() && !ml_at_interrupt_context();}
uint32_t little(const uint8_t *p){return uint32_t(p[0])|(uint32_t(p[1])<<8)|(uint32_t(p[2])<<16)|(uint32_t(p[3])<<24);}
IOReturn translate(kern_return_t raw){switch(raw){case KERN_SUCCESS:return kIOReturnSuccess;
case KERN_INVALID_ARGUMENT:return kIOReturnBadArgument;case KERN_NAME_EXISTS:return kIOReturnExclusiveAccess;
case KERN_RESOURCE_SHORTAGE:return kIOReturnNoResources;case KERN_INVALID_NAME:return kIOReturnNotReady;
default:return kIOReturnIOError;}}

}
// Real native GIC bridge for this actual K80 GPU provider. Reuses the same checked
// attach/mask implementation as RSC/SMMU; no replacement controller or fake IRQ.
class ZornGen7GpuIrqProvider26 final : public IOService {
    OSDeclareDefaultStructors(ZornGen7GpuIrqProvider26);
public:
    static IOReturn create(IOService &,ZornGen7GpuIrq26 &,OSObject &,
        const ZornGen7GpuIrqAuthority26 &,ZornGen7GpuIrqProvider26 *&,bool nativeGic=false);
    IOReturn registerInterrupt(int,OSObject *,IOInterruptAction,void *) override;
    IOReturn getInterruptType(int,int *) override;
    IOReturn enableInterrupt(int) override;
    IOReturn disableInterrupt(int) override;
    IOReturn unregisterInterrupt(int) override{return kIOReturnUnsupported;}
    IOReturn causeInterrupt(int) override{return kIOReturnUnsupported;}
    bool initiallyMasked() const;
    void free() override{if(pinned_)return;IOService::free();}
private:
    struct Slot {ZornGen7GpuIrqProvider26 *provider=nullptr;unsigned source=0;uint32_t intid=0;
        OSObject *target=nullptr;IOInterruptAction action=nullptr;void *refcon=nullptr;
        uint32_t state=0,maskFailed=0,lastReturned=0,lastEnabled=0,everEnabled=0;
        kern_return_t attachRaw=0,lastRaw=0;int grantRaw=0;bool grantReturned=false;};
    struct Storage {IOService *gpu=nullptr;ZornGen7GpuIrq26 *receiver=nullptr;OSObject *owner=nullptr;
        ZornGen7GpuIrqAuthority26 authority;Slot slots[1];bool prepared=false,nativeGic=false;
        static void *operator new(size_t,void *p)noexcept{return p;}};
    Storage *storage_=nullptr;bool pinned_=false;
    static void deliver(void *,uint32_t);
};
OSDefineMetaClassAndStructors(ZornGen7GpuIrqProvider26,IOService);
OSDefineMetaClassAndStructors(ZornGen7GpuIrq26,OSObject);
static uint32_t zornGpuIrqObservation[4];
void Zorn26RecordGpuIrqResult(IOReturn raw){zornGpuIrqObservation[0]=uint32_t(raw);}
extern "C" void zorn26_native_gpu_irq_observation(uint32_t (&out)[4])
{memcpy(out,zornGpuIrqObservation,sizeof(out));}
IOReturn ZornGen7GpuIrqProvider26::create(IOService &gpu,ZornGen7GpuIrq26 &receiver,OSObject &owner,
    const ZornGen7GpuIrqAuthority26 &authority,ZornGen7GpuIrqProvider26 *&out,bool nativeGic)
{
    if(out || !normal() || (!nativeGic && !authority.authorizeActualSpi))return kIOReturnBadArgument;
    OSSharedPtr<OSObject> property(gpu.copyProperty("interrupts"),OSNoRetain),names(gpu.copyProperty("interrupt-names"),OSNoRetain);
    auto *data=OSDynamicCast(OSData,property.get());auto *name=OSDynamicCast(OSData,names.get());
    zornGpuIrqObservation[1]=1;
    zornGpuIrqObservation[2]=((data?data->getLength():65535u)<<16)|(name?name->getLength():65535u);
    zornGpuIrqObservation[3]=(data && data->getLength()>=12 && data->getBytesNoCopy())?
        little(static_cast<const uint8_t *>(data->getBytesNoCopy())+4):0;
    constexpr char expected[]="kgsl_3d0_irq";
    if(!data || data->getLength()!=12 || !data->getBytesNoCopy() || !name ||
       name->getLength()!=sizeof(expected) || !name->getBytesNoCopy())return kIOReturnUnsupported;
    zornGpuIrqObservation[1]=2;
    const auto *nb=static_cast<const uint8_t *>(name->getBytesNoCopy());
    for(size_t i=0;i<sizeof(expected);++i)if(nb[i]!=uint8_t(expected[i]))return kIOReturnUnsupported;
    zornGpuIrqObservation[1]=3;
    const auto *bytes=static_cast<const uint8_t *>(data->getBytesNoCopy());
    if(little(bytes)!=0 || little(bytes+4)!=300u || little(bytes+8)!=4)return kIOReturnUnsupported;
    zornGpuIrqObservation[1]=4;
    const uint32_t ids[]={little(bytes+4)+32u};
    auto *p=new ZornGen7GpuIrqProvider26;if(!p)return kIOReturnNoMemory;
    if(!p->init()){p->release();return kIOReturnNoMemory;}
    p->retain();p->pinned_=true;out=p;gpu.retain();receiver.retain();owner.retain();
    void *memory=IOMallocZero(sizeof(Storage));if(!memory)return kIOReturnNoMemory;
    p->storage_=new(memory)Storage;auto &s=*p->storage_;
    s.gpu=&gpu;s.receiver=&receiver;s.owner=&owner;s.authority=authority;s.nativeGic=nativeGic;
    for(unsigned i=0;i<1;++i){s.slots[i].provider=p;s.slots[i].source=i;s.slots[i].intid=ids[i];}
    if(!p->attach(&gpu))return kIOReturnNotAttached;
    zornGpuIrqObservation[1]=5;
    s.prepared=true;return kIOReturnSuccess;
}
IOReturn ZornGen7GpuIrqProvider26::getInterruptType(int source,int *type)
{if(!storage_ || !storage_->prepared || source<0 || source>=1 || !type)return kIOReturnBadArgument;
 *type=kIOInterruptTypeLevel;return kIOReturnSuccess;}
IOReturn ZornGen7GpuIrqProvider26::registerInterrupt(int source,OSObject *target,IOInterruptAction action,void *refcon)
{
    if(!storage_ || !storage_->prepared || !normal() || source<0 || source>=1 || !target || !action)
        return kIOReturnBadArgument;
    auto &s=*storage_;auto &slot=s.slots[source];uint32_t expected=0;
    if(!__atomic_compare_exchange_n(&slot.state,&expected,1,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))return kIOReturnExclusiveAccess;
    if(!s.nativeGic) {
        slot.grantRaw=s.authority.authorizeActualSpi(s.authority.cookie,*s.gpu,slot.intid);
        slot.grantReturned=true;
        if(slot.grantRaw){__atomic_store_n(&slot.state,3u,__ATOMIC_RELEASE);return kIOReturnNotPermitted;}
    }
    target->retain();slot.target=target;slot.action=action;slot.refcon=refcon;
    ZornGicSpiObservation26 observed{};
    zornGpuIrqObservation[1]=16;
    slot.attachRaw=gic_v3_spi_attach_zorn_gpu_masked(slot.intid,false,deliver,&slot,&observed);
    zornGpuIrqObservation[1]=17;
    zornGpuIrqObservation[2]=uint32_t(slot.attachRaw);
    zornGpuIrqObservation[3]=(observed.readMask<<16) |
        (observed.route==observed.requestedRoute?1u<<15:0u) |
        (observed.configuration<<8) | observed.enabled | (observed.priority<<24);
    __atomic_store_n(&slot.state,slot.attachRaw==KERN_SUCCESS?2u:3u,__ATOMIC_RELEASE);return translate(slot.attachRaw);
}
void ZornGen7GpuIrqProvider26::deliver(void *context,uint32_t intid)
{
    auto *slot=static_cast<Slot *>(context);if(!slot || slot->intid!=intid || !slot->action)return;
    slot->provider->storage_->receiver->primaryArrived();
    // XNU's real level-trigger primary masks this exact SPI and wakes its workloop.
    slot->action(slot->target,slot->refcon,slot->provider,int(slot->source));
}
IOReturn ZornGen7GpuIrqProvider26::enableInterrupt(int source)
{
    if(!storage_ || source<0 || source>=1)return kIOReturnBadArgument;auto &s=*storage_;auto &slot=s.slots[source];
    if(__atomic_load_n(&slot.state,__ATOMIC_ACQUIRE)!=2 || __atomic_load_n(&slot.maskFailed,__ATOMIC_ACQUIRE) ||
       !s.receiver->forwardAllowed())return kIOReturnNotReady;
    __atomic_store_n(&slot.everEnabled,1u,__ATOMIC_RELEASE);
    const auto raw=gic_v3_spi_set_enabled_checked(slot.intid,&slot,true);
    __atomic_store_n(&slot.lastRaw,raw,__ATOMIC_RELAXED);__atomic_store_n(&slot.lastEnabled,1u,__ATOMIC_RELAXED);
    __atomic_store_n(&slot.lastReturned,1u,__ATOMIC_RELEASE);
    if(raw!=KERN_SUCCESS)s.receiver->stopFromProvider();return translate(raw);
}
IOReturn ZornGen7GpuIrqProvider26::disableInterrupt(int source)
{
    if(!storage_ || source<0 || source>=1)return kIOReturnBadArgument;auto &s=*storage_;auto &slot=s.slots[source];
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
bool ZornGen7GpuIrqProvider26::initiallyMasked() const
{
    if(!storage_ || !storage_->prepared)return false;
    for(const auto &slot:storage_->slots)if(__atomic_load_n(&slot.everEnabled,__ATOMIC_ACQUIRE) ||
        __atomic_load_n(&slot.state,__ATOMIC_ACQUIRE)!=2 ||
        !__atomic_load_n(&slot.lastReturned,__ATOMIC_ACQUIRE) || __atomic_load_n(&slot.lastEnabled,__ATOMIC_RELAXED) ||
        __atomic_load_n(&slot.lastRaw,__ATOMIC_RELAXED)!=KERN_SUCCESS)return false;
    return true;
}

struct ZornGen7GpuIrq26::Storage {
    IOService *gpu=nullptr;ZornGen7RegisterMaps26 *maps=nullptr;IOWorkLoop *loop=nullptr;
    ZornGen7HostGpuRegisters26 *completedRegisters=nullptr;
    ZornGen7GpuIrqProvider26 *provider=nullptr;IOInterruptEventSource *event=nullptr;
    IORecursiveLock *ioSerial=nullptr;IOLock *gate=nullptr;NativeAdrenoIrq decoder;
    uint32_t stopped=0,armed=0,primaryCount=0,actions=0,maskAttempted=0;
    bool prepared=false,armAttempted=false,maskProgramReturned=false,decodeReturned=false;
    bool keepalivePossiblyHeld=false,keepaliveSetReturned=false,keepaliveClearReturned=false;
    IOReturn factoryRaw=kIOReturnNotReady,loopRaw=kIOReturnNotReady,attachRaw=kIOReturnNotReady,maskRaw=kIOReturnNotReady,decodeRaw=kIOReturnNotReady;
    uint32_t programmedMask=0,fenceControl=0,pollReads=0;NativeAdrenoIrqResult decoded{};
    int lastIoRaw=0;bool lastIoReturned=false,lastIoWrite=false;uint32_t lastIoWord=0;
    OSObject *receiver=nullptr;int (*consume)(OSObject &,const NativeAdrenoIrqResult &)=nullptr;int consumeRaw=0;bool consumeReturned=false;
    static void *operator new(size_t,void *p)noexcept{return p;}
};
IOReturn ZornGen7GpuIrq26::createDisabled(IOService &gpu,ZornGen7InactiveOwner26 &parent,
    ZornGen7RegisterMaps26 &maps,IOWorkLoop &loop,OSObject &authorityOwner,const ZornGen7GpuIrqAuthority26 &authority,ZornGen7GpuIrq26 *&out)
{
    return createDisabledImpl(gpu,parent,maps,loop,authorityOwner,authority,nullptr,out);
}
IOReturn ZornGen7GpuIrq26::createDisabledWithNativeGic(IOService &gpu,ZornGen7InactiveOwner26 &parent,
    ZornGen7RegisterMaps26 &maps,IOWorkLoop &loop,OSObject &owner,ZornGen7HostGpuRegisters26 &completed,
    ZornGen7GpuIrq26 *&out)
{
    if(!normal() || !IOService::getPlatform() || gpu.getProvider()!=IOService::getPlatform() ||
       !completed.holdsCompletedIrqPrerequisite(gpu,parent,maps))return kIOReturnNotReady;
    const ZornGen7GpuIrqAuthority26 noExternalCallback{};
    return createDisabledImpl(gpu,parent,maps,loop,owner,noExternalCallback,&completed,out);
}
IOReturn ZornGen7GpuIrq26::createDisabledImpl(IOService &gpu,ZornGen7InactiveOwner26 &parent,
    ZornGen7RegisterMaps26 &maps,IOWorkLoop &loop,OSObject &authorityOwner,const ZornGen7GpuIrqAuthority26 &authority,
    ZornGen7HostGpuRegisters26 *completed,ZornGen7GpuIrq26 *&out)
{
    if(out || !normal() || !ml_get_interrupts_enabled() || loop.onThread() || loop.inGate() ||
       (!completed && !authority.authorizeActualSpi) || !maps.readResult().mapsReady)return kIOReturnBadArgument;
    auto *p=new ZornGen7GpuIrq26;if(!p)return kIOReturnNoMemory;
    if(!p->init()){p->release();return kIOReturnNoMemory;}p->retain();p->pinned_=true;out=p;
    gpu.retain();parent.retain();maps.retain();loop.retain();authorityOwner.retain();
    if(completed)completed->retain();
    void *bytes=IOMallocZero(sizeof(Storage));if(!bytes)return kIOReturnNoMemory;p->storage_=new(bytes)Storage;auto &s=*p->storage_;
    s.gpu=&gpu;s.maps=&maps;s.loop=&loop;s.completedRegisters=completed;s.gate=IOLockAlloc();s.ioSerial=IORecursiveLockAlloc();
    if(!s.gate || !s.ioSerial)return kIOReturnNoMemory;
    if(!maps.bindGpuIrq(*p,parent,gpu))return kIOReturnNotReady;
    const NativeAdrenoRingIo io{p,write,read,barrier};s.attachRaw=s.decoder.attach(&io);if(s.attachRaw)return s.attachRaw;
    s.factoryRaw=ZornGen7GpuIrqProvider26::create(gpu,*p,authorityOwner,authority,s.provider,completed!=nullptr);if(s.factoryRaw || !s.provider)return s.factoryRaw?s.factoryRaw:kIOReturnNotReady;
    zornGpuIrqObservation[1]=6;
    s.event=IOInterruptEventSource::interruptEventSource(p,action,s.provider,0);if(!s.event)return kIOReturnNoResources;
    s.event->disable();s.loopRaw=loop.addEventSource(s.event);if(s.loopRaw)return s.loopRaw;
    if(p->halted() || !s.provider->initiallyMasked())return kIOReturnNotReady;
    s.prepared=true;
    zornGpuIrqObservation[1]=1u | (s.provider->initiallyMasked()?2u:0u) | (!p->halted()?4u:0u);
    zornGpuIrqObservation[2]=uint32_t(s.factoryRaw);
    zornGpuIrqObservation[3]=uint32_t(s.loopRaw);
    return kIOReturnSuccess;
}
bool ZornGen7GpuIrq26::halted()const{return !storage_ || __atomic_load_n(&storage_->stopped,__ATOMIC_ACQUIRE)!=0;}
bool ZornGen7GpuIrq26::forwardAllowed()const{return storage_ && __atomic_load_n(&storage_->armed,__ATOMIC_ACQUIRE) && !halted();}
void ZornGen7GpuIrq26::stopFromProvider(){if(storage_)__atomic_store_n(&storage_->stopped,1u,__ATOMIC_RELEASE);}
void ZornGen7GpuIrq26::primaryArrived(){if(!storage_)return;__atomic_fetch_add(&storage_->primaryCount,1u,__ATOMIC_RELAXED);if(!forwardAllowed())stopFromProvider();}
void ZornGen7GpuIrq26::stopAndMask()
{
    if(!storage_)return;auto &s=*storage_;stopFromProvider();
    if(__atomic_exchange_n(&s.maskAttempted,1u,__ATOMIC_ACQ_REL) || !s.event)return;s.event->disable();
    // Controller containment only. No claim that GPU/DMA stopped;no GPU
    // reset,keepalive clear,table removal,resource release or retry follows.
}
int ZornGen7GpuIrq26::access(uint32_t word,bool writing,uint32_t &value)
{
    if(!storage_ || !normal() || halted() || !storage_->ioSerial)return FHR_NOT_AVAILABLE;auto &s=*storage_;
    IORecursiveLockLock(s.ioSerial);s.lastIoReturned=false;s.lastIoWord=word;s.lastIoWrite=writing;
    s.lastIoRaw=halted()?FHR_NOT_AVAILABLE:s.maps->accessGpuIrqWord(word,writing,value);s.lastIoReturned=true;
    const int raw=s.lastIoRaw;IORecursiveLockUnlock(s.ioSerial);return raw;
}
int ZornGen7GpuIrq26::read(void *p,uint32_t word,uint32_t *out)
{if(!p || !out)return FHR_ARGUMENT;uint32_t value=0;const int raw=static_cast<ZornGen7GpuIrq26 *>(p)->access(word,false,value);if(!raw)*out=value;return raw;}
int ZornGen7GpuIrq26::write(void *p,uint32_t word,uint32_t value)
{return p?static_cast<ZornGen7GpuIrq26 *>(p)->access(word,true,value):FHR_ARGUMENT;}
int ZornGen7GpuIrq26::barrier(void *p)
{if(!p || static_cast<ZornGen7GpuIrq26 *>(p)->halted())return FHR_NOT_AVAILABLE;__asm__ volatile("dsb sy" ::: "memory");return 0;}
bool ZornGen7GpuIrq26::acquireKeepalive()
{
    auto &s=*storage_;uint32_t one=1;s.keepalivePossiblyHeld=true;
    const int raw=access(0x1f8c3,true,one);s.keepaliveSetReturned=true;if(raw)return false;
    // Actual bounded source AHB fence poll;ordinary IRQs stay enabled and no
    // map/accessBusy lock spans delay. Exact100 native1us waits,never reset.
    for(unsigned i=0;i<=100;++i){++s.pollReads;if(access(0x23b10,false,s.fenceControl))return false;
        if(!s.fenceControl)return true;if(i==100)break;IODelay(1);}
    return false;
}
bool ZornGen7GpuIrq26::releaseKeepalive()
{
    auto &s=*storage_;if(!s.keepalivePossiblyHeld)return false;uint32_t zero=0;
    const int raw=access(0x1f8c3,true,zero);s.keepaliveClearReturned=true;if(raw)return false;s.keepalivePossiblyHeld=false;return true;
}
IOReturn ZornGen7GpuIrq26::bindReceiver(OSObject &receiver,int (*consume)(OSObject &,const NativeAdrenoIrqResult &))
{
    if(!storage_ || !normal() || !consume)return kIOReturnBadArgument;auto &s=*storage_;IOLockLock(s.gate);
    if(!s.prepared || s.receiver || s.armAttempted || halted() || !s.provider->initiallyMasked()){IOLockUnlock(s.gate);return kIOReturnNotReady;}
    receiver.retain();s.receiver=&receiver;s.consume=consume;IOLockUnlock(s.gate);return kIOReturnSuccess;
}
IOReturn ZornGen7GpuIrq26::armBoundReceiver()
{
    if(!storage_ || !normal() || !ml_get_interrupts_enabled())return kIOReturnNotReady;auto &s=*storage_;IOLockLock(s.gate);
    if(!s.prepared || !s.receiver || !s.consume || s.armAttempted || halted() || !s.provider->initiallyMasked()){IOLockUnlock(s.gate);return kIOReturnNotReady;}
    s.armAttempted=true;IOLockUnlock(s.gate);IORecursiveLockLock(s.ioSerial);
    uint32_t status=0,mask=0;
    if(!acquireKeepalive() || access(0x201,false,status) || access(0x38,false,mask) || status || mask){IORecursiveLockUnlock(s.ioSerial);stopAndMask();return kIOReturnNotReady;}
    s.maskRaw=s.decoder.programMask(&s.programmedMask);s.maskProgramReturned=true;
    if(s.maskRaw || s.decoder.poisoned() || s.programmedMask!=NativeAdrenoIrq::mask() || !releaseKeepalive()){
        IORecursiveLockUnlock(s.ioSerial);stopAndMask();return s.maskRaw?s.maskRaw:kIOReturnNotReady;}
    __atomic_store_n(&s.armed,1u,__ATOMIC_RELEASE);IORecursiveLockUnlock(s.ioSerial);
    s.event->enable();if(halted()){stopAndMask();return kIOReturnNotReady;}return kIOReturnSuccess;
}
void ZornGen7GpuIrq26::action(OSObject *o,IOInterruptEventSource *sender,int count)
{auto *p=OSDynamicCast(ZornGen7GpuIrq26,o);if(p && p->storage_ && sender==p->storage_->event && count>0)p->handle();}
void ZornGen7GpuIrq26::handle()
{
    if(!storage_ || !normal())return;auto &s=*storage_;__atomic_fetch_add(&s.actions,1u,__ATOMIC_ACQ_REL);
    auto finish=[&](){__atomic_fetch_sub(&s.actions,1u,__ATOMIC_RELEASE);};
    if(!forwardAllowed()){stopAndMask();finish();return;}
    IORecursiveLockLock(s.ioSerial);
    if(!acquireKeepalive()){IORecursiveLockUnlock(s.ioSerial);stopAndMask();finish();return;}
    s.decodeReturned=false;s.decodeRaw=s.decoder.handle(&s.decoded);s.decodeReturned=true;
    const bool fatal=s.decodeRaw || s.decoder.poisoned() || (s.decoded.flags&(NativeAdrenoIrqFatal|NativeAdrenoIrqPreempt));
    // Retain keepalive on unknown/error/fatal. No source recovery/reset path.
    if(fatal || !forwardAllowed()){IORecursiveLockUnlock(s.ioSerial);stopAndMask();finish();return;}
    const NativeAdrenoIrqResult actual=s.decoded;IORecursiveLockUnlock(s.ioSerial);
    // Foreign real ring/fence receiver runs outside I/O serialization. A
    // notification alone never marks a fence complete or grants retirement.
    s.consumeReturned=false;s.consumeRaw=s.consume(*s.receiver,actual);s.consumeReturned=true;
    if(s.consumeRaw || !forwardAllowed()){stopAndMask();finish();return;}
    IORecursiveLockLock(s.ioSerial);const bool released=releaseKeepalive();IORecursiveLockUnlock(s.ioSerial);
    if(!released)stopAndMask();finish();
}
void ZornGen7GpuIrq26::free(){if(pinned_)return;OSObject::free();}

int ZornGen7GpuIrq26::accessRingWord(uint32_t word,bool writing,uint32_t &value)
{
    if(!storage_ || !normal() || halted() || !storage_->ioSerial)return FHR_NOT_AVAILABLE;
    auto &s=*storage_;IORecursiveLockLock(s.ioSerial);
    const int raw=halted()?FHR_NOT_AVAILABLE:s.maps->accessHostRingWord(word,writing,value);
    IORecursiveLockUnlock(s.ioSerial);return raw;
}

// SPDX-License-Identifier: GPL-2.0-only
#include "ZornGen7SmmuFaultIrq26.h"
#include <IOKit/IOLib.h>
#include <libkern/c++/OSData.h>
#include <libkern/c++/OSSharedPtr.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
extern "C" kern_return_t gic_v3_spi_attach_masked(uint32_t,bool,void (*)(void *,uint32_t),void *);
extern "C" kern_return_t gic_v3_spi_set_enabled_checked(uint32_t,void *,bool);
extern "C" kern_return_t gic_v3_spi_attach_zorn_gmu_context_masked(uint32_t,bool,
    void (*)(void *,uint32_t),void *,ZornGicSpiObservation26 *);
static unsigned zornGmuIrqReadback;
extern "C" unsigned zorn26_gmu_context_irq_readback()
{
    return __atomic_load_n(&zornGmuIrqReadback,__ATOMIC_ACQUIRE);
}
OSDefineMetaClassAndStructors(ZornGen7SmmuFaultIrq26,OSObject)
namespace {
uint32_t little(const uint8_t *p)
{return uint32_t(p[0])|(uint32_t(p[1])<<8)|(uint32_t(p[2])<<16)|(uint32_t(p[3])<<24);}
bool normal(){return preemption_enabled() && !ml_at_interrupt_context();}
IOReturn translate(kern_return_t raw)
{
    switch(raw) {
    case KERN_SUCCESS:return kIOReturnSuccess;
    case KERN_INVALID_ARGUMENT:return kIOReturnBadArgument;
    case KERN_NAME_EXISTS:return kIOReturnExclusiveAccess;
    case KERN_RESOURCE_SHORTAGE:return kIOReturnNoResources;
    case KERN_INVALID_NAME:return kIOReturnNotReady;
    default:return kIOReturnIOError;
    }
}
}
struct ZornGen7SmmuFaultIrq26::Storage {
    ArmSmmu4KIo io{};uint32_t intid=0;unsigned bank=0,source=0;bool global=false;
    void (*stop)(void *)=nullptr;void *parent=nullptr;
    // Immutable references/callbacks precede registration. Only phase is read
    // concurrently by the startup thread; raw records publish separately after containment.
    volatile uint32_t observation_complete=0;
    volatile uint32_t phase=0; // 1constructing,2registered-masked,3armed,4retained-failure.
    int grantRaw=0;bool grantReturned=false,nativeMaskedOnly=false;
    ZornGicSpiObservation26 gic{};
    kern_return_t attachRaw=0,enableRaw=0,maskRaw=0;
    bool attachReturned=false,enableReturned=false,maskReturned=false;
    int fsrRaw=0;uint32_t fsr=0;bool fsrReturned=false;
    int syndromeRaw[3]{};uint32_t syndrome[3]{};bool syndromeReturned[3]{};
    static void *operator new(size_t,void *p) noexcept{return p;}
};
IOReturn ZornGen7SmmuFaultIrq26::createAndArm(IOService &controller,IOService &consumer,
    Scope scope,unsigned bank,unsigned banks,const ArmSmmu4KIo &io,OSObject &contextOwner,
    OSObject &authorityOwner,const ZornGen7SmmuFaultIrqAuthority26 &authority,
    OSObject &parentOwner,void (*stop)(void *),void *parent,ZornGen7SmmuFaultIrq26 *&out)
{
    const auto raw=createMasked(controller,consumer,scope,bank,banks,io,contextOwner,authorityOwner,
        authority,parentOwner,stop,parent,out);
    if(raw!=kIOReturnSuccess)return raw;return out?out->arm():kIOReturnNotReady;
}
IOReturn ZornGen7SmmuFaultIrq26::createNativeGlobalMasked(IOService &controller,unsigned banks,
    const ArmSmmu4KIo &io,OSObject &mapOwner,OSObject &parentOwner,void (*stop)(void *),
    void *parent,ZornGen7SmmuFaultIrq26 *&out,ZornGen7NativeSmmuIrqResult26 &snapshot)
{
    const auto raw=createMaskedImpl(controller,controller,Scope::Global,0,banks,io,mapOwner,
        parentOwner,nullptr,parentOwner,stop,parent,out);
    if(out && out->storage_){const auto &s=*out->storage_;
        snapshot.attach_returned=s.attachReturned;if(s.attachReturned)snapshot.attach_raw=s.attachRaw;
        snapshot.intid=s.intid;snapshot.source=s.source;snapshot.gic=s.gic;
        snapshot.registered_masked=__atomic_load_n(&s.phase,__ATOMIC_ACQUIRE)==2;
    }
    return raw; // Actual checked GIC registration,not an external grant or fault-control ownership.
}
IOReturn ZornGen7SmmuFaultIrq26::createMasked(IOService &controller,IOService &consumer,
    Scope scope,unsigned bank,unsigned banks,const ArmSmmu4KIo &io,OSObject &contextOwner,
    OSObject &authorityOwner,const ZornGen7SmmuFaultIrqAuthority26 &authority,
    OSObject &parentOwner,void (*stop)(void *),void *parent,ZornGen7SmmuFaultIrq26 *&out)
{return createMaskedImpl(controller,consumer,scope,bank,banks,io,contextOwner,authorityOwner,
    &authority,parentOwner,stop,parent,out);}
IOReturn ZornGen7SmmuFaultIrq26::createMaskedImpl(IOService &controller,IOService &consumer,
    Scope scope,unsigned bank,unsigned banks,const ArmSmmu4KIo &io,OSObject &contextOwner,
    OSObject &authorityOwner,const ZornGen7SmmuFaultIrqAuthority26 *authority,
    OSObject &parentOwner,void (*stop)(void *),void *parent,ZornGen7SmmuFaultIrq26 *&out)
{
    const bool isGlobal=scope==Scope::Global;
    if(out || !normal() || !banks || (!isGlobal && bank>=banks) || !stop || !parent ||
       (authority?(isGlobal?!authority->authorizeActualGlobalSpi:!authority->authorizeActualContextSpi):!isGlobal) ||
       !io.cookie || !io.read32 || io.register_bytes<0x5c)
        return kIOReturnBadArgument;
    OSSharedPtr<OSObject> globals(controller.copyProperty("#global-interrupts"),OSNoRetain);
    OSSharedPtr<OSObject> interrupts(controller.copyProperty("interrupts"),OSNoRetain);
    auto *globalData=OSDynamicCast(OSData,globals.get());auto *irqData=OSDynamicCast(OSData,interrupts.get());
    if(!globalData || globalData->getLength()!=4 || !globalData->getBytesNoCopy() ||
       !irqData || !irqData->getLength() || irqData->getLength()%12 || !irqData->getBytesNoCopy())
        return kIOReturnBadArgument;
    const uint32_t global=little(static_cast<const uint8_t *>(globalData->getBytesNoCopy()));
    const size_t total=irqData->getLength()/12;
    // Exact SMMUv2 admission: no PMU suffix in this source DT path; ignore
    // superfluous context IRQs only after every observed bank has one.
    if(global>=total || banks>total-global || (isGlobal && global!=1))return kIOReturnUnsupported;
    const auto *tuples=static_cast<const uint8_t *>(irqData->getBytesNoCopy());
    const size_t source=isGlobal?0u:size_t(global)+bank;const auto *tuple=tuples+source*12;
    if(source>UINT32_MAX || little(tuple)!=0 || little(tuple+4)>987 || little(tuple+8)!=4)
        return kIOReturnUnsupported;
    auto *owner=new ZornGen7SmmuFaultIrq26;if(!owner)return kIOReturnNoMemory;
    if(!owner->init()){owner->release();return kIOReturnNoMemory;}
    owner->retain();owner->pinned_=true;out=owner;
    controller.retain();consumer.retain();contextOwner.retain();authorityOwner.retain();parentOwner.retain();
    void *memory=IOMallocZero(sizeof(Storage));if(!memory)return kIOReturnNoMemory;
    owner->storage_=new(memory) Storage;auto &s=*owner->storage_;
    s.io=io;s.global=isGlobal;s.bank=bank;s.source=static_cast<unsigned>(source);s.intid=little(tuple+4)+32u;
    s.stop=stop;s.parent=parent;__atomic_store_n(&s.phase,1u,__ATOMIC_RELEASE);
    s.nativeMaskedOnly=authority==nullptr;
    if(authority){
        s.grantRaw=isGlobal?authority->authorizeActualGlobalSpi(authority->cookie,controller,s.source,s.intid):
            authority->authorizeActualContextSpi(authority->cookie,controller,consumer,bank,s.source,s.intid);
        s.grantReturned=true;
        if(s.grantRaw){__atomic_store_n(&s.phase,4u,__ATOMIC_RELEASE);return kIOReturnNotPermitted;}
    }
    // Native masked registration uses the actual GIC reservation operation;
    // grantReturned remains false. It cannot arm or mutate SMMU fault control.
    // Reuse the actual GIC backend, retaining this exact context on partial
    // failure. It checks real registration, configuration and masked state.
    if (!s.global && authority && s.bank == 2 && s.intid == 711) {
        s.attachRaw=gic_v3_spi_attach_zorn_gmu_context_masked(s.intid,false,deliver,owner,&s.gic);
        const bool ds=(s.gic.control&(1u<<6))!=0;
        const bool nonsecure=ds ? (s.gic.group && !s.gic.modifier) : s.gic.priority==0xa0;
        const unsigned observed=s.gic.readMask |
            (unsigned(s.gic.configuration==s.gic.requestedType)<<7) |
            (unsigned(s.gic.route==s.gic.requestedRoute)<<8) |
            (unsigned(!s.gic.enabled)<<9) | (unsigned(nonsecure)<<10) |
            (unsigned(s.attachRaw==KERN_SUCCESS)<<11);
        __atomic_store_n(&zornGmuIrqReadback,observed,__ATOMIC_RELEASE);
    } else if(!s.global && authority && s.bank<2 && s.intid==709+s.bank) {
        s.attachRaw=gic_v3_spi_attach_zorn_gmu_context_masked(s.intid,false,deliver,owner,&s.gic);
    } else {
        s.attachRaw=s.nativeMaskedOnly ?
            gic_v3_spi_attach_smmu_boot_cpu_masked_observed(s.intid,false,deliver,owner,&s.gic) :
            gic_v3_spi_attach_masked(s.intid,false,deliver,owner);
    }
    s.attachReturned=true;
    if(s.attachRaw!=KERN_SUCCESS){__atomic_store_n(&s.phase,4u,__ATOMIC_RELEASE);return translate(s.attachRaw);}
    __atomic_store_n(&s.phase,2u,__ATOMIC_RELEASE);
    return kIOReturnSuccess; // Actual registration is masked;no synthetic IRQ-ready result.
}
IOReturn ZornGen7SmmuFaultIrq26::arm(){return armImpl(false);}
IOReturn ZornGen7SmmuFaultIrq26::armNativeGlobalAfterControl(){return armImpl(true);}
IOReturn ZornGen7SmmuFaultIrq26::armImpl(bool nativeControlReady)
{
    if(!storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;
    if(s.nativeMaskedOnly!=nativeControlReady || (nativeControlReady && !s.global) || __atomic_load_n(&s.phase,__ATOMIC_ACQUIRE)!=2 || s.enableReturned)return kIOReturnNotReady;
    s.enableRaw=gic_v3_spi_set_enabled_checked(s.intid,this,true);s.enableReturned=true;
    if(s.enableRaw!=KERN_SUCCESS){__atomic_store_n(&s.phase,4u,__ATOMIC_RELEASE);return translate(s.enableRaw);}
    uint32_t expected=2;
    // A fault can arrive before enable returns. Never overwrite that failure
    // with a ready flag, even when the enable operation itself returned success.
    if(!__atomic_compare_exchange_n(&s.phase,&expected,3u,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))
        return kIOReturnNotReady;
    return kIOReturnSuccess;
}
void ZornGen7SmmuFaultIrq26::deliver(void *context,uint32_t intid)
{
    auto *owner=static_cast<ZornGen7SmmuFaultIrq26 *>(context);
    if(!owner || !owner->storage_)return;
    auto &s=*owner->storage_;
    if(intid!=s.intid)return;
    owner->observeAndContain();
}
void ZornGen7SmmuFaultIrq26::observeAndContain()
{
    if(!storage_)return;auto &s=*storage_;
    const uint32_t phase=__atomic_load_n(&s.phase,__ATOMIC_ACQUIRE);
    if(phase!=2 && phase!=3)return;
    // The parent's genuine runtime-PM use is held throughout armed lifetime.
    // No sleep, PM resume, client callback, FSR clear, RESUME, reset or retry.
    uint32_t fsr=0;const int raw=s.io.read32(s.io.cookie,s.global?0x48u:0x58u,&fsr);
    // Source global handler treats any nonzero GFSR as a fault; context FSR
    // consumes its exact source fault mask. Do not fabricate common masks.
    if(!raw && (s.global?!fsr:!(fsr&UINT32_C(0xc00001fe))))return;
    uint32_t expected=phase;
    bool recorded=__atomic_compare_exchange_n(&s.phase,&expected,4u,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE);
    // Registration may advance 2->3 on the startup CPU while an IRQ is
    // delivered on the routed CPU. Preserve this already-observed fault
    // across that one transition; do not reread MMIO or replay an operation.
    if(!recorded && phase==2 && expected==3)
        recorded=__atomic_compare_exchange_n(&s.phase,&expected,4u,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE);
    if(!recorded)return;
    s.fsrRaw=raw;s.fsrReturned=true;if(!raw)s.fsr=fsr;
    if(s.global && !raw) {
        for(unsigned i=0;i<3;++i) {
            uint32_t value=0;s.syndromeRaw[i]=s.io.read32(s.io.cookie,0x50u+4u*i,&value);
            s.syndromeReturned[i]=true;
            if(s.syndromeRaw[i])break;
            s.syndrome[i]=value;
        }
    }
    s.stop(s.parent); // Actual native owner's atomic stop latch, no guessed completion.
    s.maskRaw=gic_v3_spi_set_enabled_checked(s.intid,this,false);s.maskReturned=true;
    __atomic_store_n(&s.observation_complete,1u,__ATOMIC_RELEASE);
    // Mask failure is uncertain and remains retained. No second command is
    // issued; a future bounded hardware trial must handle failure to contain it.
}
IOReturn ZornGen7SmmuFaultIrq26::verifyNoFault()
{
    if(!normal() || !ready())return kIOReturnNotReady;
    observeAndContain();return ready()?kIOReturnSuccess:kIOReturnNotReady;
}
bool ZornGen7SmmuFaultIrq26::ready() const
{return storage_ && __atomic_load_n(&storage_->phase,__ATOMIC_ACQUIRE)==3;}
void ZornGen7SmmuFaultIrq26::free(){if(pinned_)return;OSObject::free();}

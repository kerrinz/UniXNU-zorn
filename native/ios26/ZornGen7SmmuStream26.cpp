#include <pexpert/pexpert.h>
// SPDX-License-Identifier: GPL-2.0-only
#include "ZornGen7SmmuStream26.h"
#include <IOKit/IOLib.h>
#include <libkern/c++/OSData.h>
#include <libkern/c++/OSSharedPtr.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
OSDefineMetaClassAndStructors(ZornGen7SmmuStream26,OSObject)
namespace {
uint32_t little(const uint8_t *p)
{return uint32_t(p[0])|(uint32_t(p[1])<<8)|(uint32_t(p[2])<<16)|(uint32_t(p[3])<<24);}
bool normal(){return preemption_enabled() && !ml_at_interrupt_context();}
bool subset(uint32_t request,uint32_t existing)
{return ((existing>>16)&(request>>16))==(request>>16) && !((existing^request)&0xffffu&~(existing>>16));}
bool overlap(uint32_t a,uint32_t b)
{return !((a^b)&0xffffu&~((a>>16)|(b>>16)));}
}
struct ZornGen7SmmuStream26::Storage {
    ArmSmmu4KIo io{};const volatile uint32_t *fault=nullptr;
    struct Slot {uint32_t smr=0,s2cr=0;} snapshot[256]{};
    uint32_t id0=0,cr0=0,requested=0,effective=0,prepared_smr=0,prepared_s2cr=0;
    unsigned bank=0,groups=0,slot=0;bool matching=false,extended=false,existing=false;
    bool stopped=false,blocked=false,actlr_selected=false,has_actlr=false;uint32_t actlr=0;
    bool actlr_attempted=false,actlr_step_complete=false,actlr_write_returned=false,actlr_read_returned=false;
    int actlr_write_raw=0,actlr_read_raw=0;uint32_t actual_actlr=0;
    bool actlr_tlb_returned=false;ZornSmmuSparse4KStatus actlr_tlb_status=ZornSmmuSparse4KArgument;
    ZornSmmuSparse4KProgramResult actlr_tlb{};
    bool activation_attempted=false,activated=false;uint32_t active_smr=0,active_s2cr=0;
    bool grant_returned=false,last_io_returned=false;int grant_raw=0,last_io_raw=0;
    static void *operator new(size_t,void *p) noexcept{return p;}
    bool live() const {return !stopped && fault && !__atomic_load_n(fault,__ATOMIC_ACQUIRE);}
    int read(size_t at,uint32_t &value) {
        last_io_returned=false;
        if(!live())return int(kIOReturnNotReady);
        uint32_t v=0;last_io_raw=io.read32(io.cookie,at,&v);last_io_returned=true;
        if(!last_io_raw)value=v;return last_io_raw;
    }
    int write(size_t at,uint32_t value) {
        last_io_returned=false;
        if(!live())return int(kIOReturnNotReady);
        last_io_raw=io.write32(io.cookie,at,value);last_io_returned=true;return last_io_raw;
    }
    int barrier() {
        last_io_returned=false;
        if(!live())return int(kIOReturnNotReady);
        last_io_raw=io.barrier(io.cookie);last_io_returned=true;return last_io_raw;
    }
    bool valid(const Slot &v) const {return extended?bool(v.s2cr&(1u<<10)):bool(v.smr&(1u<<31));}
    uint32_t packed(const Slot &v) const {return (v.smr&0xffffu)|(((v.smr>>16)&(extended?0xffffu:0x7fffu))<<16);}
};
IOReturn ZornGen7SmmuStream26::prepareBlocked(IOService &controller,IOService &consumer,
    unsigned bank,uint32_t id0,uint32_t request,const uint32_t *others,size_t otherCount,
    bool (&ledger)[256],const ArmSmmu4KIo &io,OSObject &globalOwner,OSObject &authorityOwner,
    const ZornGen7SmmuStreamAuthority26 &authority,OSObject &parent,
    const volatile uint32_t &fault,ZornGen7SmmuStream26 *&out)
{
    if(out || !normal() || bank>255 || (otherCount && !others) || otherCount>2 ||
       !authority.acquireActualStream || !io.cookie || !io.read32 || !io.write32 || !io.barrier)
        return kIOReturnBadArgument;
    // This K80 source has no firmware handoff-SMR list. Preserve any future
    // such input as unsupported until its real pinned-bank policy is ported.
    OSSharedPtr<OSObject> handoff(controller.copyProperty("qcom,handoff-smrs"),OSNoRetain);
    if(handoff)return kIOReturnUnsupported;
    auto *owner=new ZornGen7SmmuStream26;if(!owner)return kIOReturnNoMemory;
    if(!owner->init()){owner->release();return kIOReturnNoMemory;}
    owner->retain();owner->pinned_=true;out=owner;
    controller.retain();consumer.retain();globalOwner.retain();authorityOwner.retain();parent.retain();
    void *memory=IOMallocZero(sizeof(Storage));if(!memory)return kIOReturnNoMemory;
    owner->storage_=new(memory) Storage;auto &s=*owner->storage_;
    s.io=io;s.fault=&fault;s.id0=id0;s.requested=request;s.bank=bank;s.matching=bool(id0&(1u<<27));
    auto refuse=[&](IOReturn raw){s.stopped=true;return raw;};
    uint32_t observed=0;
    if(s.read(0x20,observed))return refuse(kIOReturnIOError);
    if(observed!=id0)return refuse(kIOReturnNotReady);
    if(s.read(0,s.cr0))return refuse(kIOReturnIOError);
    if((s.cr0&(1u<<3)) && !(id0&(1u<<8)))return refuse(kIOReturnUnsupported);
    s.extended=s.matching && bool(s.cr0&(1u<<3));
    // The actual qsmmuv500 group/ACTLR path consumes allocated SMRs.
    // Do not invent an indexing-mode equivalent for this K80 backend.
    if(!s.matching)return refuse(kIOReturnUnsupported);
    const uint32_t sid=request&0xffffu,mask=request>>16;
    const uint32_t sidMask=(id0&(1u<<8))?0xffffu:((1u<<((id0>>9)&15u))-1u);
    if(sid&~sidMask)return refuse(kIOReturnUnsupported);
    // New allocations use the exact unmasked K80 fwspec. No destructive
    // hardware mask probing is performed on an arbitrary supposedly free slot.
    if(mask)return refuse(kIOReturnUnsupported);
    if(s.matching) {
        s.groups=id0&255u;
        if(!s.groups || io.register_bytes<0xc00u+size_t(s.groups)*4u)return refuse(kIOReturnBadArgument);
        int firstFree=-1,match=-1;
        for(unsigned i=0;i<s.groups;++i) {
            auto &v=s.snapshot[i];
            if(s.read(0x800u+i*4u,v.smr) || s.read(0xc00u+i*4u,v.s2cr))return refuse(kIOReturnIOError);
            if(!s.valid(v)){if(!ledger[i] && firstFree<0)firstFree=int(i);continue;}
            const uint32_t actual=s.packed(v);
            if(!overlap(request,actual))continue;
            if(!subset(request,actual) || match>=0 || ledger[i])return refuse(kIOReturnExclusiveAccess);
            match=int(i);
        }
        if(match<0 && firstFree<0)return refuse(kIOReturnNoResources);
        s.existing=match>=0;s.slot=unsigned(s.existing?match:firstFree);
        s.effective=s.existing?s.packed(s.snapshot[s.slot]):request;
        // Native endpoints have separate real domains. A matching firmware
        // group covering another endpoint cannot silently be retargeted here.
        for(size_t i=0;i<otherCount;++i)if(overlap(s.effective,others[i]))return refuse(kIOReturnExclusiveAccess);
        for(unsigned i=0;i<s.groups;++i)if(i!=s.slot && s.valid(s.snapshot[i]) &&
            overlap(s.effective,s.packed(s.snapshot[i])))return refuse(kIOReturnExclusiveAccess);
    }
    ledger[s.slot]=true;const auto before=s.snapshot[s.slot];
    s.grant_raw=authority.acquireActualStream(authority.cookie,controller,consumer,bank,request,
        s.effective,s.slot,s.extended,s.matching?&before.smr:nullptr,before.s2cr,s.existing);s.grant_returned=true;
    if(s.grant_raw)return refuse(kIOReturnNotPermitted);
    // Actual grant must serialize the complete hardware match set. Re-read
    // every captured entry and global matching mode before the first write;
    // snapshots alone are not the grant, nor a substitute for quiescence.
    if(s.read(0,observed))return refuse(kIOReturnIOError);
    if(observed!=s.cr0)return refuse(kIOReturnNotReady);
    const unsigned first=0,last=s.groups;
    for(unsigned i=first;i<last;++i) {
        uint32_t smr=0,s2cr=0;
        if((s.matching && s.read(0x800u+i*4u,smr)) || s.read(0xc00u+i*4u,s2cr))return refuse(kIOReturnIOError);
        if((s.matching && smr!=s.snapshot[i].smr) || s2cr!=s.snapshot[i].s2cr)return refuse(kIOReturnNotReady);
    }
    // Initial owned-slot preparation only: fault instead of translating while
    // its target context is not ready. Existing effective SMR is preserved;
    // new SMR is materialized INVALID. No stream is activated by this method.
    s.prepared_s2cr=(2u<<16)|(3u<<8)|bank|((s.extended && s.existing)?1u<<10:0u);
    s.prepared_smr=s.existing?before.smr:(sid|(mask<<16));
    if(s.write(0xc00u+s.slot*4u,s.prepared_s2cr) || s.barrier())return refuse(kIOReturnIOError);
    if(s.matching && !s.existing && (s.write(0x800u+s.slot*4u,s.prepared_smr) || s.barrier()))return refuse(kIOReturnIOError);
    uint32_t smr=0,s2cr=0;
    if((s.matching && s.read(0x800u+s.slot*4u,smr)) || s.read(0xc00u+s.slot*4u,s2cr))return refuse(kIOReturnIOError);
    if(s2cr!=s.prepared_s2cr || (s.matching && smr!=s.prepared_smr))return refuse(kIOReturnNotReady);
    // Select ACTLR using this actual owned/materialized slot, not the earlier
    // requested-fwspec candidate. No ACTLR or context programming occurs here.
    s.blocked=true;
    const auto raw=owner->selectActualActlr(controller);if(raw!=kIOReturnSuccess)return refuse(raw);
    return s.live()?kIOReturnSuccess:refuse(kIOReturnNotReady);
}
IOReturn ZornGen7SelectActlr(IOService &controller,uint32_t packed,bool &present,uint32_t &value)
{
    present=false;
    value=0;
    OSSharedPtr<OSObject> property(controller.copyProperty("qcom,actlr"),OSNoRetain);
    if(!property)return kIOReturnSuccess;
    auto *data=OSDynamicCast(OSData,property.get());
    if(!data || data->getLength()%12 || (data->getLength() && !data->getBytesNoCopy()))
        return kIOReturnBadArgument;
    const auto *p=static_cast<const uint8_t *>(data->getBytesNoCopy());
    for(size_t at=0;at<data->getLength();at+=12) {
        const uint32_t id=little(p+at),mask=little(p+at+4),candidate=little(p+at+8);
        if(id>0xffffu || mask>0xffffu)return kIOReturnBadArgument;
        if(!subset(packed,id|(mask<<16)))continue;
        if(present && value!=candidate)return kIOReturnBadArgument;
        present=true;
        value=candidate;
    }
    return kIOReturnSuccess;
}

IOReturn ZornGen7SmmuStream26::selectActualActlr(IOService &controller)
{
    auto &s=*storage_;
    if(!s.live() || !s.blocked || s.actlr_selected)return kIOReturnNotReady;
    const auto raw=ZornGen7SelectActlr(controller,s.effective,s.has_actlr,s.actlr);
    if(!raw)s.actlr_selected=true;
    return raw;
}
bool ZornGen7SmmuStream26::ready() const
{return storage_ && storage_->live() && storage_->blocked && storage_->actlr_selected;}
IOReturn ZornGen7SmmuStream26::verifyBlocked()
{
    if(!ready())return kIOReturnNotReady;
    auto &s=*storage_;uint32_t cr0=0,smr=0,s2cr=0;
    if(s.read(0,cr0) || s.read(0x800u+s.slot*4u,smr) || s.read(0xc00u+s.slot*4u,s2cr)) {
        s.stopped=true;return kIOReturnIOError;
    }
    if(cr0!=s.cr0 || smr!=s.prepared_smr || s2cr!=s.prepared_s2cr) {
        s.stopped=true;return kIOReturnNotReady;
    }
    return kIOReturnSuccess;
}
void Zorn26ObserveHostActlr(unsigned bank,uint32_t progress,uint32_t readback);

IOReturn ZornGen7SmmuStream26::applyActlrToDisabledBank(const ArmSmmu4KIo &context,
    const ZornSmmuSparse4KIo &program,size_t contextOffset,unsigned asid,unsigned budget)
{
    if(!normal() || !ready() || !context.cookie || !context.read32 || !context.write32 ||
       !context.barrier || context.register_bytes<8 || !budget || budget>1048576)
        return kIOReturnBadArgument;
    auto &s=*storage_;if(s.actlr_attempted)return kIOReturnNotReady;
    s.actlr_attempted=true;
    auto refuse=[&](IOReturn raw){s.stopped=true;return raw;};
    auto raw=verifyBlocked();if(raw!=kIOReturnSuccess)return refuse(raw);
    uint32_t sctlr=0;s.last_io_returned=false;
    if(!s.live())return refuse(kIOReturnNotReady);
    s.last_io_raw=context.read32(context.cookie,0,&sctlr);s.last_io_returned=true;
    if(s.last_io_raw)return refuse(kIOReturnIOError);
    if(sctlr&1u)return refuse(kIOReturnBusy); // Never disable a live/unproven bank here.
    if(s.has_actlr) {
        if(!s.live())return refuse(kIOReturnNotReady);
        s.actlr_write_raw=context.write32(context.cookie,4,s.actlr);s.actlr_write_returned=true;
        if(s.actlr_write_raw)return refuse(kIOReturnIOError);
        Zorn26ObserveHostActlr(s.bank,1,0);
        if(!s.live())return refuse(kIOReturnNotReady);
        s.last_io_returned=false;s.last_io_raw=context.barrier(context.cookie);s.last_io_returned=true;
        if(s.last_io_raw)return refuse(kIOReturnIOError);
        if(!s.live())return refuse(kIOReturnNotReady);
        s.actlr_read_raw=context.read32(context.cookie,4,&s.actual_actlr);s.actlr_read_returned=true;
        if(s.actlr_read_raw)return refuse(kIOReturnIOError);
        Zorn26ObserveHostActlr(s.bank,3,s.actual_actlr);
        if(s.actual_actlr!=s.actlr)return refuse(kIOReturnNotReady);
        // Pinned qsmmuv500_init_cb requires a bank flush after changing ACTLR.
        // This is initial configuration, with the actual stream still blocked.
        s.actlr_tlb_status=ZornSmmuSparse4KSyncContextTlb(&program,contextOffset,asid,1,budget,&s.actlr_tlb);
        s.actlr_tlb_returned=true;
        if(s.actlr_tlb_status!=ZornSmmuSparse4KSuccess || !s.actlr_tlb.tlb_synchronized)
            return refuse(kIOReturnIOError);
    }
    if(s.has_actlr)Zorn26ObserveHostActlr(s.bank,7,s.actual_actlr);
    // No matching source ACTLR means no write/flush, as upstream. It is never
    // reported as an applied value of zero or a successful hardware write.
    raw=verifyBlocked();if(raw!=kIOReturnSuccess)return refuse(raw);
    s.actlr_step_complete=true;return kIOReturnSuccess;
}
void ZornGen7SmmuStream26::free(){if(pinned_)return;OSObject::free();}

IOReturn ZornGen7SmmuStream26::activatePrepared()
{
    return activatePreparedWithPeer(nullptr);
}

void Zorn26TraceHostStream(unsigned,unsigned,int);
IOReturn ZornGen7SmmuStream26::activatePreparedWithPeer(const ZornGen7SmmuStream26 *peer)
{
    if(storage_)Zorn26TraceHostStream(storage_->bank,3,0);
    if(!normal() || !ready())return kIOReturnNotReady;
    auto &s=*storage_;if(s.activation_attempted || !s.actlr_step_complete)return kIOReturnNotReady;
    s.activation_attempted=true;
    unsigned traceStage=4;
    auto refuse=[&](IOReturn raw){
        Zorn26TraceHostStream(s.bank,traceStage,raw);
        s.stopped=true;
        return raw;
    };
    unsigned deferred=0;
    const bool staged=!peer && !s.existing && !s.extended && s.bank==2 &&
        s.effective==5 && s.prepared_smr==5 &&
        PE_parse_boot_argn("zorn26_gmu_deferred_valid",&deferred,sizeof(deferred)) && (deferred>=1 && deferred<=21);
    auto raw=kIOReturnSuccess;
    if (staged) {
        uint32_t cr0=0,smr=0,s2cr=0;
        if (s.read(0,cr0) || s.read(0x800u+4u*s.slot,smr) || s.read(0xc00u+4u*s.slot,s2cr))
            return refuse(kIOReturnIOError);
        if (cr0!=s.cr0 || smr!=s.prepared_smr || s2cr!=(0x300u|s.bank))
            return refuse(kIOReturnNotReady);
    } else {
        raw=verifyBlocked();if(raw!=kIOReturnSuccess)return refuse(raw);
    }
    Zorn26TraceHostStream(s.bank,5,0);
    traceStage=6;
    // The independently acquired grant must still hold/serialize every
    // effective matching transaction and the hardware stream table. Snapshots
    // only detect drift and cannot create that grant or prove quiescence.
    const Storage *sibling=peer?peer->storage_:nullptr;
    Storage::Slot expectedSibling{};
    if(peer) {
        if(!sibling || !sibling->live() || sibling->fault!=s.fault || sibling->io.cookie!=s.io.cookie ||
           sibling->cr0!=s.cr0 || sibling->groups!=s.groups || sibling->slot>=s.groups ||
           sibling->slot==s.slot || sibling->bank==s.bank || (!sibling->blocked && !sibling->activated))
            return refuse(kIOReturnNotReady);
        // The first owner captured the peer slot before preparation. The second
        // captured the first slot while blocked. Admit only those exact transitions.
        const Storage::Slot prepared{sibling->prepared_smr,sibling->prepared_s2cr};
        const auto before=sibling->activated?prepared:sibling->snapshot[sibling->slot];
        const auto captured=s.snapshot[sibling->slot];
        if(captured.smr!=before.smr || captured.s2cr!=before.s2cr)return refuse(kIOReturnNotReady);
        expectedSibling=sibling->activated?
            Storage::Slot{sibling->active_smr,sibling->active_s2cr}:prepared;
    }
    Zorn26TraceHostStream(s.bank,7,0);
    traceStage=8;
    for(unsigned i=0;i<s.groups;++i) {
        if(i==s.slot)continue;
        uint32_t smr=0,s2cr=0;
        if(s.read(0x800u+i*4u,smr) || s.read(0xc00u+i*4u,s2cr))return refuse(kIOReturnIOError);
        const auto expected=sibling && i==sibling->slot?expectedSibling:s.snapshot[i];
        if(smr!=expected.smr || s2cr!=expected.s2cr)return refuse(kIOReturnNotReady);
    }
    Zorn26TraceHostStream(s.bank,9,0);
    traceStage=10;
    // Exact source S2CR_TYPE_TRANS=0, PRIVCFG_DEFAULT=0, SHCFG_NSH=3,
    // actual owned bank. EXID uses S2CR validity; otherwise SMR bit31.
    // Only the previously granted effective group is ever changed.
    s.active_s2cr=(3u<<8)|s.bank|(s.extended?1u<<10:0u);
    s.active_smr=s.prepared_smr|(s.extended?0u:1u<<31);
    // Context, visibility and fault owners were verified by the domain.
    // S2CR precedes SMR as in arm_smmu_write_sme. New non-EXID SMR remains
    // invalid until the final write; existing and EXID entries may start
    // translating with the S2CR write, so no rollback is attempted on error.
    if(!staged && (s.write(0xc00u+s.slot*4u,s.active_s2cr) || s.barrier()))return refuse(kIOReturnIOError);
    Zorn26TraceHostStream(s.bank,11,0);
    traceStage=12;
    if(s.active_smr!=s.prepared_smr &&
       (s.write(0x800u+s.slot*4u,s.active_smr) || s.barrier()))return refuse(kIOReturnIOError);
    Zorn26TraceHostStream(s.bank,13,0);
    traceStage=14;
    s.blocked=false;s.activated=true;
    raw=verifyActive();if(raw!=kIOReturnSuccess)return refuse(raw);
    Zorn26TraceHostStream(s.bank,15,0);
    return kIOReturnSuccess;
}
IOReturn ZornGen7SmmuStream26::verifyActive()
{
    if(!storage_ || !storage_->live() || !storage_->activated)return kIOReturnNotReady;
    auto &s=*storage_;uint32_t cr0=0,smr=0,s2cr=0;
    if(s.read(0,cr0) || s.read(0x800u+s.slot*4u,smr) || s.read(0xc00u+s.slot*4u,s2cr)) {
        s.stopped=true;return kIOReturnIOError;
    }
    if(cr0!=s.cr0 || smr!=s.active_smr || s2cr!=s.active_s2cr) {
        s.stopped=true;return kIOReturnNotReady;
    }
    return kIOReturnSuccess;
}

IOReturn ZornGen7SmmuStream26::verifyActiveConflicts()
{
    auto raw=verifyActive();if(raw)return raw;auto &s=*storage_;
    for(unsigned i=0;i<s.groups;++i){if(i==s.slot)continue;Storage::Slot actual{};
        if((s.matching && s.read(0x800u+4u*i,actual.smr)) || s.read(0xc00u+4u*i,actual.s2cr)){s.stopped=true;return kIOReturnIOError;}
        if(s.matching && !s.valid(actual))continue;
        if(!(actual.s2cr&(3u<<16)) && (actual.s2cr&255u)==s.bank){s.stopped=true;return kIOReturnExclusiveAccess;}
        if(s.matching && overlap(s.effective,s.packed(actual))){s.stopped=true;return kIOReturnExclusiveAccess;}
    }
    return verifyActive();
}
IOReturn ZornGen7SmmuStream26::faultActiveForRuntime()
{
    // Only this source owner's already granted effective slot. Unknown live
    // state refuses;SMR/SHCFG/PRIVCFG/bank/EXID are never guessed or replaced.
    const auto before=verifyActive();if(before)return before;auto &s=*storage_;
    const uint32_t fault=(s.active_s2cr&~(3u<<16))|(2u<<16);uint32_t observed=0;
    if(s.write(0xc00u+4u*s.slot,fault) || s.barrier() || s.read(0xc00u+4u*s.slot,observed)){
        s.stopped=true;return kIOReturnIOError;}
    s.stopped=true;if(observed!=fault)return kIOReturnNotReady;
    s.activated=false;s.blocked=true;return kIOReturnSuccess;
    // Source containment only,never a DMA-stop,quiescence,reset or release.
}

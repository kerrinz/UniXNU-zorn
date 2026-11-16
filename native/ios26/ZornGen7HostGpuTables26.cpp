/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include "ZornGen7HostGpuTables26.h"
#include "ZornGen7ProcessTables26.h"
#include "ZornCountWindow26.h"
#include "direct-runtime/ZornGen7DirectVm26.h"
#include "ZornGen7SmmuTablePages26.h"
#include <IOKit/IOBufferMemoryDescriptor.h>
#include <kern/cpu_data.h>
// Actual exported kernel globals,as declared by the retained native consumer.
extern unsigned long gPhysBase,gPhysSize;
#include "HoujiFullHostNativeMemory.h"
#include "sparse/ArmSmmu4KLive.h"
#include "ArmSmmu4KProgram.h"
#include <IOKit/IOLib.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
OSDefineMetaClassAndStructors(ZornGen7HostGpuTables26,OSObject)
namespace {
bool normal(){return preemption_enabled() && !ml_at_interrupt_context() && ml_get_interrupts_enabled();}
static_assert(unsigned(ArmSmmu4KRead)==unsigned(ZornSmmuSparse4KRead) &&
    unsigned(ArmSmmu4KWrite)==unsigned(ZornSmmuSparse4KWrite) &&
    unsigned(ArmSmmu4KExecute)==unsigned(ZornSmmuSparse4KExecute) &&
    unsigned(ArmSmmu4KPrivileged)==unsigned(ZornSmmuSparse4KPrivileged),"actual range permission translation");
constexpr unsigned slots[]={FHG_SHARED_SLOT,FHG_LARGE_SLOT,FHG_GPU_POOL_SLOT,FHG_CODE_SLOT};
}
struct ZornGen7HostGpuTables26::Storage {
    IORecursiveLock &gate;FhgStorage &graph;HoujiFullHostNativeMemory &memory;
    const unsigned inputBits,outputBits,physicalBits;
    FhgGraph logical{};FhgRange source[FHG_GPU_RANGES]{};
    ZornSmmuSparse4KRange ranges[FHG_GPU_RANGES]{};
    ZornGen7SmmuTablePages26 *pages[2]{};ZornGen7SmmuTablePages26::PageHandle roots[2]{};
    ZornSmmuSparse4KLiveArena arena[2]{};ZornSmmuSparse4KLiveState state[2]{};
    ZornSmmuSparse4KLiveVisibility visibility[2]{};ZornSmmuSparse4KLiveResult result[2]{};
    ZornSmmuSparse4KContextConfig context[2]{};ZornSmmuSparse4KContextImage image[2]{};
    ZornSmmuSparse4KProgramResult program[2]{},observed[2]{};
    ZornSmmuSparse4KStatus imageStatus[2]{},programStatus[2]{},observeStatus[2]{};
    // One host-table owner per actual domain. Every current/future bank ASID
    // is its cbndx (reserveActual),so exclude the entire probed bank range.
    // Remaining tags are software reservations,not bank/hardware leases.
    uint64_t processAsids[1024]{};unsigned actualBankCount=0;
    ZornGen7ProcessTables26 *selectedProcess=nullptr;
    bool directVmAttempted=false,directVmReady=false;
    bool postCpInspected=false,postCpRestoreNeeded=false,postCpRestoreAttempted=false,postCpRestored=false;
    ZornSmmuSparse4KProgramResult postCpBefore{},postCpAgain{},postCpSync{};
    ZornSmmuSparse4KStatus postCpInspectStatus{},postCpAgainStatus{},postCpSyncStatus{};
    int postCpWriteRaw=0,postCpBarrierRaw=0;
    bool contextAttempted=false,contextReady=false,programAttempted[2]{},programReady[2]{};
    bool attempted=false,ready=false;uint32_t heldMask=0;
    IOReturn publishRaw[4]{},holdRaw[4]{};bool publishReturned[4]{},holdReturned[4]{};
    ZornSmmuSparse4KStatus prepareStatus[2]{},seedStatus[2]{},auditStatus[2]{};
    Storage(IORecursiveLock &g,FhgStorage &f,HoujiFullHostNativeMemory &m,unsigned i,unsigned o,unsigned p):
        gate(g),graph(f),memory(m),inputBits(i),outputBits(o),physicalBits(p){}
    static void *operator new(size_t,void *p)noexcept{return p;}
};
IOReturn ZornGen7HostGpuTables26::create(IORecursiveLock &gate,OSObject &domain,FhgStorage &graph,
    HoujiFullHostNativeMemory &memory,OSObject &parent,unsigned input,unsigned output,unsigned physical,ZornGen7HostGpuTables26 *&out)
{
    if(out || !normal() || !IORecursiveLockHaveLock(&gate))return kIOReturnNotReady;
    auto *p=new ZornGen7HostGpuTables26;if(!p)return kIOReturnNoMemory;
    if(!p->init()){p->release();return kIOReturnNoMemory;}
    p->retain();p->pinned_=true;out=p;domain.retain();parent.retain();
    void *bytes=IOMallocZero(sizeof(Storage));if(!bytes)return kIOReturnNoMemory;
    p->storage_=new(bytes)Storage(gate,graph,memory,input,output,physical);return p->prepare();
}
IOReturn ZornGen7HostGpuTables26::prepare()
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    auto &s=*storage_;if(s.attempted)return kIOReturnNotReady;s.attempted=true;
    if(!s.memory.prepared() || s.memory.count()!=HoujiFullHostNativeMemory::Slots ||
       fhg_graph(&s.graph,sizeof(s.graph),1,&s.logical,sizeof(s.logical)))return kIOReturnNotReady;
    // Read the logical inventory only. Old graph's PA/root/tables/descriptors
    // are never replayed as upstream native objects or hardware capability.
    // Existing direct user/client address ABI is an explicit SOFTWARE budget.
    const auto &g=s.logical;
    if(g.graph!=1 || g.input_bits!=32 || g.output_bits!=36 || g.upper_region ||
       g.range_count!=FHG_GPU_RANGES || !g.audit_complete || g.build_status || g.audit_status ||
       g.input_bits>s.inputBits || g.output_bits>s.outputBits || g.output_bits>s.physicalBits ||
       FHG_LIVE_GPU_APERTURE!=(UINT64_C(1)<<g.input_bits))return kIOReturnUnsupported;
    for(unsigned k=0;k<4;++k){
        const unsigned slot=slots[k];const auto &e=s.memory.entry(slot);const auto &bo=s.memory.bo(slot);
        if(!e.allocated || !e.validated || !e.published || e.status || e.request.slot!=slot || !e.request.normal_nc ||
           !e.nc || !bo.backed() || bo.quarantined() || bo.imported() || bo.readOnly() || !bo.writeCombined() ||
           bo.deviceReferences() || !bo.mapping() || !bo.descriptor() || bo.spanCount()!=1 || bo.ownedSpanCount()!=1 ||
           bo.mapping()!=e.backing.cpu || bo.bytes()!=e.request.logical_bytes || bo.ownedBytes()!=e.request.owned_bytes ||
           bo.descriptor()->getLength()!=bo.ownedBytes() || bo.cpuPageBytes()!=e.request.cpu_page_bytes ||
           bo.spans()[0].offset || bo.spans()[0].physical!=e.backing.physical || bo.spans()[0].bytes!=bo.bytes() ||
           bo.ownedSpans()[0].offset || bo.ownedSpans()[0].physical!=e.backing.owned_physical ||
           bo.ownedSpans()[0].physical!=bo.spans()[0].physical || bo.ownedSpans()[0].bytes!=bo.ownedBytes() ||
           bo.ownedBytes()!=NativeAdrenoMemory::backingBudget(bo.bytes()))return kIOReturnNotReady;
    }
    for(unsigned i=0;i<FHG_GPU_RANGES;++i){
        auto &r=s.source[i];if(fhg_range(&s.graph,sizeof(s.graph),1,i,&r,sizeof(r)))return kIOReturnNotReady;
        if(r.reserved || !r.bytes || ((r.iova|r.physical|r.bytes)&4095u) || r.iova>=FHG_LIVE_GPU_APERTURE ||
           r.bytes>FHG_LIVE_GPU_APERTURE-r.iova || r.physical>=(UINT64_C(1)<<g.output_bits) ||
           r.bytes>(UINT64_C(1)<<g.output_bits)-r.physical)return kIOReturnBadArgument;
        bool found=false;
        for(unsigned slot:slots){const auto &e=s.memory.entry(slot);
            if(r.physical>=e.backing.physical && r.physical-e.backing.physical<=e.request.logical_bytes &&
               r.bytes<=e.request.logical_bytes-(r.physical-e.backing.physical)){if(found)return kIOReturnBadArgument;found=true;}}
        if(!found)return kIOReturnBadArgument;
        s.ranges[i]={r.iova,r.physical,r.bytes,r.permissions,r.writeback,r.shareability};
    }
    for(unsigned i=1;i<FHG_GPU_RANGES;++i){
        const auto value=s.ranges[i];unsigned j=i;
        while(j && s.ranges[j-1].iova>value.iova){s.ranges[j]=s.ranges[j-1];--j;}s.ranges[j]=value;
    }
    for(unsigned k=0;k<4;++k){
        // SAME actual nonconst allocating object under its private native
        // parent gate,as in existing GMU firmware holds. No reconstructed BO.
        auto &bo=const_cast<NativeAdrenoMemory &>(s.memory.bo(slots[k]));
        s.publishRaw[k]=bo.publishForDevice(0,bo.bytes(),true);s.publishReturned[k]=true;
        if(s.publishRaw[k]!=kIOReturnSuccess)return s.publishRaw[k];
        s.holdRaw[k]=bo.holdForDevice();s.holdReturned[k]=true;
        if(bo.deviceReferences())s.heldMask|=1u<<k;
        if(s.holdRaw[k]!=kIOReturnSuccess)return s.holdRaw[k];
        if(bo.deviceReferences()!=1)return kIOReturnNotReady;
    }
    for(unsigned i=0;i<2;++i){
        // Independent actual roots for USER/LPAC;do not modify existing upper
        // endpoint roots or reuse old FHG dense table pages. Logical OAS is
        // checked above against actual probe;it is not a guessed K80 width.
        auto raw=ZornGen7SmmuTablePages26::create(s.gate,*this,g.output_bits,s.pages[i]);if(raw)return raw;
        raw=s.pages[i]->allocate4K(s.roots[i]);if(raw)return raw;
        const auto *provider=s.pages[i]->provider();s.visibility[i]=s.pages[i]->visibility();
        if(!provider || !s.visibility[i].publish_table_page)return kIOReturnNotReady;
        s.arena[i]={{g.input_bits,g.output_bits,s.roots[i].physical,size_t(FHG_LIVE_GPU_APERTURE/4096)},
            0,FHG_LIVE_GPU_APERTURE,0,provider,nullptr,0};
        s.prepareStatus[i]=ZornSmmuSparse4KLivePrepare(&s.arena[i],&s.state[i]);
        if(s.prepareStatus[i]!=ZornSmmuSparse4KSuccess)return kIOReturnIOError;
        s.seedStatus[i]=ZornSmmuSparse4KLiveSeedInactive(&s.arena[i],&s.state[i],&s.visibility[i],s.ranges,FHG_GPU_RANGES,&s.result[i]);
        if(s.seedStatus[i]!=ZornSmmuSparse4KSuccess || !s.result[i].complete)return kIOReturnIOError;
        s.auditStatus[i]=ZornSmmuSparse4KLiveAudit(&s.arena[i],&s.state[i],s.ranges,FHG_GPU_RANGES,&s.result[i]);
        if(s.auditStatus[i]!=ZornSmmuSparse4KSuccess || !s.result[i].complete)return kIOReturnIOError;
    }
    if(s.heldMask!=15u)return kIOReturnNotReady;s.ready=true;return kIOReturnSuccess;
    // Actual CPU table construction and native holds only. No GPU bank,
    // stream,TLB,IRQ,PRR,device execute or successful MMU start is implied.
}
IOReturn ZornGen7HostGpuTables26::prepareContexts(uint32_t id0,uint32_t id2,const uint16_t (&asids)[2],
    bool coherent,const uint32_t (&attributes)[2],unsigned bankCount)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    auto &s=*storage_;if(!s.ready || s.contextAttempted || asids[0]==asids[1] ||
        !bankCount || bankCount>255 || asids[0]>=bankCount || asids[1]>=bankCount)
        return kIOReturnNotReady;
    s.contextAttempted=true;
    for(unsigned i=0;i<2;++i){
        // Fresh OEM software default pfpolicy=0 (static device_3d0;only
        // sysfs mutates it):CFCFG0,HUPCF1. Not a live Android policy query,
        // hardware grant,fault recovery or DMA-stop/completion guarantee.
        s.context[i]={&s.arena[i].config,nullptr,&s.state[i].tables,nullptr,
            id0,id2,asids[i],coherent?1u:0u,0,1,0,attributes[i]};
        s.imageStatus[i]=ZornSmmuSparse4KEncodeContext(&s.context[i],&s.image[i]);
        if(s.imageStatus[i]!=ZornSmmuSparse4KSuccess)return kIOReturnUnsupported;
    }
    // The existing encoder explicitly requests AArch64 TCR2.AS=1 and
    // validates that context format. Do not copy houji's fixed start=16.
    if(!(s.image[0].tcr2&(1u<<4)) || !(s.image[1].tcr2&(1u<<4)))return kIOReturnUnsupported;
    s.actualBankCount=bankCount;
    for(unsigned a=0;a<bankCount;++a)s.processAsids[a>>6]|=UINT64_C(1)<<(a&63);
    s.contextReady=true;return kIOReturnSuccess;
}
namespace {
bool exactImage(const ZornSmmuSparse4KContextImage &a,const ZornSmmuSparse4KContextImage &b)
{
    // Do not inherit sheng/houji readback waivers as K80 observations.
    return a.cbar==b.cbar && a.cba2r==b.cba2r && a.tcr==b.tcr && a.tcr2==b.tcr2 &&
        a.mair0==b.mair0 && a.mair1==b.mair1 && a.sctlr==b.sctlr && !a.reserved_zero &&
        a.ttbr0==b.ttbr0 && a.ttbr1==b.ttbr1;
}

bool nativeHostImage(const ZornSmmuSparse4KContextImage &got,
    const ZornSmmuSparse4KContextImage &want)
{
    // K80 GMU v113 and USER v161 observed these same one-direction bits.
    // The sparse programmer independently validates the encoded context.
    auto normalized=got;
    normalized.tcr2 &= ~(got.tcr2 & ~want.tcr2 & UINT32_C(0x60));
    normalized.sctlr |= want.sctlr & ~got.sctlr & UINT32_C(0x1000);
    return exactImage(normalized,want);
}
}
static uint32_t zornHostContextTrace[2];

extern "C" uint32_t zorn26_host_context_observation(unsigned bank)
{
    return bank<2?__atomic_load_n(&zornHostContextTrace[bank],__ATOMIC_ACQUIRE):0;
}

IOReturn ZornGen7HostGpuTables26::programContext(unsigned i,const ZornSmmuSparse4KIo &io,unsigned bank,
    size_t offset,unsigned budget)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate) || i>=2 || !budget || budget>1048576)return kIOReturnNotReady;
    auto &s=*storage_;if(!s.contextReady || s.programAttempted[i] || s.state[i].poisoned)return kIOReturnNotReady;
    s.programAttempted[i]=true;
    s.auditStatus[i]=ZornSmmuSparse4KLiveAudit(&s.arena[i],&s.state[i],s.ranges,FHG_GPU_RANGES,&s.result[i]);
    if(s.auditStatus[i]!=ZornSmmuSparse4KSuccess || !s.result[i].complete){
        __atomic_store_n(&zornHostContextTrace[i],0x80000000u|uint32_t(s.auditStatus[i]),__ATOMIC_RELEASE);
        return kIOReturnIOError;
    }
    s.programStatus[i]=ZornSmmuSparse4KProgramDisabledContext(&io,bank,&s.context[i],budget,&s.program[i]);
    const auto &r=s.program[i];
    const auto &got=r.readback;
    const auto &want=s.image[i];
    const uint32_t delta=(got.cbar!=want.cbar?1u:0u) | (got.cba2r!=want.cba2r?2u:0u) |
        (got.tcr!=want.tcr?4u:0u) | (got.tcr2!=want.tcr2?8u:0u) |
        (got.mair0!=want.mair0?16u:0u) | (got.mair1!=want.mair1?32u:0u) |
        (got.sctlr!=want.sctlr?64u:0u) | (got.ttbr0!=want.ttbr0?128u:0u) |
        (got.ttbr1!=want.ttbr1?256u:0u);
    const uint32_t trace=0x40000000u | (uint32_t(s.programStatus[i])<<24) |
        (uint32_t(r.phase)<<20) | (r.readback_valid?1u<<19:0u) |
        (r.enabled?1u<<18:0u) | (uint32_t(r.writes)<<12) |
        (got.tcr2&~want.tcr2&0x60u ? 1u<<10:0u) |
        (want.sctlr&~got.sctlr&0x1000u ? 1u<<9:0u) | delta;
    __atomic_store_n(&zornHostContextTrace[i],trace,__ATOMIC_RELEASE);
    if(s.programStatus[i]!=ZornSmmuSparse4KSuccess || !r.enabled || !r.readback_valid ||
       r.context_offset!=offset || !nativeHostImage(r.readback,s.image[i]))return kIOReturnIOError;
    s.state[i].context_offset=offset;s.programReady[i]=true;return kIOReturnSuccess;
}
IOReturn ZornGen7HostGpuTables26::verifyContext(unsigned i,const ZornSmmuSparse4KIo &io,unsigned bank,size_t offset)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate) || i>=2)return kIOReturnNotReady;
    auto &s=*storage_;if(!s.contextReady || !s.programReady[i] || s.state[i].poisoned || s.state[i].context_offset!=offset)return kIOReturnNotReady;
    s.auditStatus[i]=ZornSmmuSparse4KLiveAudit(&s.arena[i],&s.state[i],s.ranges,FHG_GPU_RANGES,&s.result[i]);
    if(s.auditStatus[i]!=ZornSmmuSparse4KSuccess || !s.result[i].complete)return kIOReturnIOError;
    s.observeStatus[i]=ZornSmmuSparse4KObserveOwnedContext(&io,bank,&s.context[i],&s.observed[i]);
    const auto &r=s.observed[i];
    return s.observeStatus[i]==ZornSmmuSparse4KSuccess && r.enabled && r.readback_valid &&
        r.context_offset==offset && nativeHostImage(r.readback,s.image[i])?kIOReturnSuccess:kIOReturnNotReady;
}
bool ZornGen7HostGpuTables26::prepared()const{return storage_ && storage_->ready;}
void ZornGen7HostGpuTables26::free(){if(pinned_)return;OSObject::free();}

IOReturn ZornGen7HostGpuTables26::buildFirstContextWords(uint32_t (&words)[25])
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;auto &s=*storage_;
    if(!s.ready || !s.contextReady || !s.programReady[0] || !s.programReady[1] || s.state[0].poisoned || s.state[1].poisoned ||
       !s.observed[0].enabled || !s.observed[0].readback_valid || !nativeHostImage(s.observed[0].readback,s.image[0]))return kIOReturnNotReady;
    const auto ttbr=s.image[0].ttbr0;const auto root=ttbr&0x0000fffffffff000ULL;
    if(!root || root>=(1ULL<<36) || s.image[0].ttbr1!=(ttbr&0xffff000000000000ULL))return kIOReturnNotReady;
    // Original houji/Linux first-context25word producer,with ONLY the actual
    // programmed USER TTBR0 (including its genuine reserved ASID) substituted.
    // No fixed bank0,ASID0x751,old dense FHG root or caller-selected address.
    auto pkt=[](unsigned op,unsigned count){unsigned a=op,b=count,pa=1,pb=1;
        for(;a;a>>=1)pa^=a&1;for(;b;b>>=1)pb^=b&1;return 0x70000000u|(pa<<23)|(pb<<15)|(op<<16)|count;};
    const uint32_t produced[]={pkt(0x17,1),0x80000001,pkt(0x17,1),0x80000003,pkt(0x1f,1),0xf,
        pkt(0x17,1),0x80000003,pkt(0x46,1),0x26,pkt(0x17,1),0x80000001,
        pkt(0x53,4),uint32_t(ttbr),uint32_t(ttbr>>32),0,0,pkt(0x17,1),0x80000001,
        pkt(0x46,1),0x31,pkt(0x17,1),3,pkt(0x65,1),0x101};
    static_assert(sizeof(produced)==sizeof(words));for(unsigned i=0;i<25;++i)words[i]=produced[i];return kIOReturnSuccess;
}

IOReturn ZornGen7HostGpuTables26::inspectPostCpContext(const ZornSmmuSparse4KIo &io,unsigned bank,size_t offset,
    bool &needed,uint32_t &expected,uint32_t &observed)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;auto &s=*storage_;
    if(!s.contextReady || !s.programReady[0] || s.state[0].poisoned || s.state[0].context_offset!=offset || s.postCpInspected)return kIOReturnNotReady;
    s.postCpInspected=true;s.postCpInspectStatus=ZornSmmuSparse4KObserveOwnedContext(&io,bank,&s.context[0],&s.postCpBefore);
    const auto &r=s.postCpBefore;const auto &want=s.image[0];
    if(s.postCpInspectStatus==ZornSmmuSparse4KSuccess && r.enabled && r.readback_valid && r.context_offset==offset && nativeHostImage(r.readback,want)){
        needed=false;expected=want.tcr;observed=r.readback.tcr;return kIOReturnSuccess;}
    // Source-backed NORMAL first-context effect,not an unknown-hardware
    // readback waiver. All fields except EPD1 retain the same bounded nativeHostImage
    // comparison already qualified on K80;no additional differences are accepted.
    auto normalized=r.readback;normalized.tcr=want.tcr;
    if(s.postCpInspectStatus!=ZornSmmuSparse4KStateMismatch || !r.enabled || !r.readback_valid || r.context_offset!=offset ||
       !(want.tcr&(1u<<23)) || r.readback.tcr!=(want.tcr&~(1u<<23)) ||
       (want.ttbr1&0x0000ffffffffffffULL) || !nativeHostImage(normalized,want))return kIOReturnNotReady;
    s.postCpRestoreNeeded=true;needed=true;expected=want.tcr;observed=r.readback.tcr;return kIOReturnSuccess;
}
IOReturn ZornGen7HostGpuTables26::restorePostCpContext(const ZornSmmuSparse4KIo &io,unsigned bank,size_t offset,unsigned budget)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate) || !budget || budget>1048576)return kIOReturnNotReady;auto &s=*storage_;
    if(!s.postCpInspected || !s.postCpRestoreNeeded || s.postCpRestoreAttempted || !s.programReady[0] ||
       s.state[0].poisoned || s.state[0].context_offset!=offset || !io.write32 || !io.barrier)return kIOReturnNotReady;
    s.postCpRestoreAttempted=true;
    // Re-observe after foreign authorization returned;never overwrite a changed
    // state using a snapshot captured before the unlocked callout.
    s.postCpAgainStatus=ZornSmmuSparse4KObserveOwnedContext(&io,bank,&s.context[0],&s.postCpAgain);
    const auto &r=s.postCpAgain;
    if(s.postCpAgainStatus!=ZornSmmuSparse4KStateMismatch || !r.enabled || !r.readback_valid || r.context_offset!=offset ||
       !exactImage(r.readback,s.postCpBefore.readback))return kIOReturnNotReady;
    s.postCpWriteRaw=io.write32(io.cookie,offset+0x30,s.image[0].tcr);if(s.postCpWriteRaw)return kIOReturnIOError;
    s.postCpBarrierRaw=io.barrier(io.cookie);if(s.postCpBarrierRaw)return kIOReturnIOError;
    s.postCpSyncStatus=ZornSmmuSparse4KSyncContextTlb(&io,offset,s.context[0].asid,1,budget,&s.postCpSync);
    if(s.postCpSyncStatus!=ZornSmmuSparse4KSuccess || !s.postCpSync.tlb_synchronized)return kIOReturnIOError;
    const auto raw=verifyContext(0,io,bank,offset);if(raw)return raw;
    s.postCpRestored=true;return kIOReturnSuccess;
    // Original exact TCR restored,not a newly selected translation policy.
    // No master reset,TTBR/ASID change,map/unmap,release or automatic retry.
}

IOReturn ZornGen7HostGpuTables26::attachDirectVm(ZornGen7DirectVm26 &vm,const ZornSmmuSparse4KIo &io,
    ZornGen7DirectVm26Routes &routes,size_t capacity,unsigned budget)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;auto &s=*storage_;
    if(!s.contextReady || !s.programReady[0] || !s.programReady[1] || s.directVmAttempted ||
       capacity<FHG_GPU_RANGES || capacity>262144 || !budget || budget>1048576 || s.context[0].upper ||
       s.context[0].ttbr0_switched || s.state[0].detached)return kIOReturnNotReady;
    s.directVmAttempted=true;ZornGen7DirectVm26Region lower{s.pages[0],&s.arena[0],&s.state[0]};
    // vm audits these SAME existing boot mappings as seeds;no client handle
    // may unmap them,and no old dense/root/table object is substituted.
    const auto raw=vm.attachSeeded(&io,&s.context[0],&routes,&lower,nullptr,capacity,budget,
        s.ranges,FHG_GPU_RANGES,nullptr,0,false,false);
    s.directVmReady=raw==kIOReturnSuccess;return raw;
}
IOReturn ZornGen7HostGpuTables26::observeRuntimeUser(const ZornSmmuSparse4KIo &io,unsigned bank,size_t offset)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;auto &s=*storage_;
    if(s.selectedProcess || !s.contextReady || !s.programReady[0] || s.state[0].poisoned || s.state[0].context_offset!=offset)return kIOReturnNotReady;
    s.observeStatus[0]=ZornSmmuSparse4KObserveOwnedContext(&io,bank,&s.context[0],&s.observed[0]);const auto &r=s.observed[0];
    return s.observeStatus[0]==ZornSmmuSparse4KSuccess && r.enabled && r.readback_valid && r.context_offset==offset &&
        nativeHostImage(r.readback,s.image[0])?kIOReturnSuccess:kIOReturnNotReady;
    // Context-only K80-qualified image:the VM itself audits its full expanded ranges.
    // Re-auditing just the12 boot ranges after client mapping would be wrong.
}

IOReturn ZornGen7HostGpuTables26::prepareProcessTables(unsigned input,
    ZornGen7ProcessTables26 *&out)
{
    if(out || !storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))
        return kIOReturnNotReady;
    auto &s=*storage_;
    if(!s.ready || !s.contextReady || !s.actualBankCount || s.heldMask!=15u || input<32 || input>48 || input>s.inputBits ||
       input<s.logical.input_bits || s.state[0].poisoned || s.state[1].poisoned)
        return kIOReturnNotReady;
    // Preserve the parent's checked device OAS/cache/permission inputs.
    // The requested IAS is an explicit software aperture,not a hardware fact.
    const uint64_t bytes=UINT64_C(1)<<input;
    if(bytes/4096>SIZE_MAX)return kIOReturnUnsupported;
    const size_t leafBudget=size_t(bytes/4096);
    for(unsigned k=0;k<4;++k){
        const auto &bo=s.memory.bo(slots[k]);
        if(!bo.backed() || bo.quarantined() || !bo.deviceReferences())
            return kIOReturnNotReady;
    }
    for(unsigned i=0;i<FHG_GPU_RANGES;++i){
        const auto &r=s.ranges[i];
        if(!r.bytes || r.iova>=bytes || r.bytes>bytes-r.iova)
            return kIOReturnBadArgument;
    }
    auto *p=new ZornGen7ProcessTables26;
    if(!p)return kIOReturnNoMemory;
    if(!p->init()){p->release();return kIOReturnNoMemory;}
    p->retain();p->pinned_=true;out=p;
    // The real parent holds all shared backing through its existing pin.
    // Retain it before any allocator can return a partial page owner.
    p->parent_=this;retain();
    p->count_=FHG_GPU_RANGES;
    p->ranges_=IONewData(ZornSmmuSparse4KRange,p->count_);
    if(!p->ranges_)return kIOReturnNoMemory;
    for(size_t i=0;i<p->count_;++i)p->ranges_[i]=s.ranges[i];
    auto raw=ZornGen7SmmuTablePages26::create(s.gate,*p,s.logical.output_bits,p->pages_);
    if(raw)return raw;
    raw=p->pages_->authorizeNeverInstalledRetirement(*p);if(raw)return raw;
    ZornGen7SmmuTablePages26::PageHandle root;
    raw=p->pages_->allocate4K(root);if(raw)return raw;
    p->arena_={{input,s.logical.output_bits,root.physical,leafBudget},
        0,bytes,0,p->pages_->provider(),nullptr,0};
    p->visibility_=p->pages_->visibility();
    if(!p->arena_.pages || !p->visibility_.publish_table_page)return kIOReturnNotReady;
    auto status=ZornSmmuSparse4KLivePrepare(&p->arena_,&p->state_);
    if(status!=ZornSmmuSparse4KSuccess)return kIOReturnIOError;
    status=ZornSmmuSparse4KLiveSeedInactive(&p->arena_,&p->state_,&p->visibility_,
        p->ranges_,p->count_,&p->seed_);
    if(status!=ZornSmmuSparse4KSuccess || !p->seed_.complete)return kIOReturnIOError;
    status=ZornSmmuSparse4KLiveAudit(&p->arena_,&p->state_,p->ranges_,p->count_,&p->audit_);
    if(status!=ZornSmmuSparse4KSuccess || !p->audit_.complete)return kIOReturnIOError;
    // The retained houji user window starts above4GiB,which cannot fit
    // this actual32-bit software aperture. Do not enlarge IAS or reuse its
    // geometry. Select a contiguous unoccupied hole from the actual audited
    // immutable kernel seed ledger;exclude the already-invalid null page.
    // Input order is immaterial. Each iteration advances past a real seed
    // boundary,so no speculative VA mapping or additional backing is made.
    ZornCountInterval26 counts[FHG_GPU_RANGES]{};
    if(p->count_!=FHG_GPU_RANGES)return kIOReturnNotReady;
    for(size_t i=0;i<p->count_;++i){const auto &range=p->ranges_[i];
        if(!range.bytes || (range.iova&4095u) || (range.bytes&4095u) ||
           range.iova>=bytes || range.bytes>bytes-range.iova)return kIOReturnBadArgument;
        counts[i]={range.iova/4096,range.bytes/4096};
    }
    uint64_t first=0,length=0;
    // No free client hole must not reject an otherwise valid kernel-only
    // table. The application branch alone requires a nonempty client scope.
    if(ZornLargestCountWindow26(bytes/4096,1,counts,p->count_,first,length)){
        p->clientVaStart_=first*4096;p->clientVaBytes_=length*4096;
    }
    // Reserve only after complete CPU graph construction. No resource is
    // published to hardware;exhaustion retains the real partial table.
    unsigned asid=s.actualBankCount;
    while(asid<65536 && (s.processAsids[asid>>6]&(UINT64_C(1)<<(asid&63))))++asid;
    if(asid==65536)return kIOReturnNoResources;
    auto config=s.context[0];config.lower=&p->arena_.config;
    config.lower_tables=&p->state_.tables;config.asid=asid;config.ttbr0_switched=1;
    ZornSmmuSparse4KContextImage image{};
    if(ZornSmmuSparse4KEncodeContext(&config,&image)!=ZornSmmuSparse4KSuccess)
        return kIOReturnUnsupported;
    // Commit the tag and exact encoded context together,under the actual gate.
    s.processAsids[asid>>6]|=UINT64_C(1)<<(asid&63);
    p->asid_=uint16_t(asid);p->asidHeld_=true;p->context_=config;p->image_=image;
    p->prepared_=true;return kIOReturnSuccess;
}

IOReturn ZornGen7HostGpuTables26::discardProcessTables(ZornGen7ProcessTables26 *&p)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate) ||
       !p || p->parent_!=this || !p->pinned_ || !p->prepared_ || p->everExposed_ ||
       p->state_.poisoned || p->state_.context_offset || p->state_.detached || !p->pages_)
        return kIOReturnNotReady;
    auto &s=*storage_;
    if(!s.contextReady || !p->asidHeld_ || p->asid_<s.actualBankCount ||
       !(s.processAsids[p->asid_>>6]&(UINT64_C(1)<<(p->asid_&63))) ||
       p->context_.asid!=p->asid_ || p->context_.lower!=&p->arena_.config ||
       p->context_.lower_tables!=&p->state_.tables)return kIOReturnNotReady;
    // The current private child has no root getter,installation or client
    // attachment API. Only successfully prepared,never-exported tables qualify.
    auto status=ZornSmmuSparse4KLiveAudit(&p->arena_,&p->state_,p->ranges_,p->count_,&p->audit_);
    if(status!=ZornSmmuSparse4KSuccess || !p->audit_.complete)return kIOReturnNotReady;
    p->prepared_=false;
    const auto raw=p->pages_->retireNeverInstalled(*p);
    if(raw){p->state_.poisoned=1;return raw;}
    p->pages_->release();p->pages_=nullptr;
    // Never installed:there can be no hardware TLB entries for this tag.
    // On any preceding retirement failure the tag stays reserved permanently.
    s.processAsids[p->asid_>>6]&=~(UINT64_C(1)<<(p->asid_&63));
    p->asidHeld_=false;p->asid_=0;p->context_={};p->image_={};
    p->arena_={};p->state_={};p->visibility_={};
    IODeleteData(p->ranges_,ZornSmmuSparse4KRange,p->count_);p->ranges_=nullptr;p->count_=0;
    auto *parent=p->parent_;p->parent_=nullptr;parent->release();
    auto *retired=p;p=nullptr;retired->pinned_=false;retired->release();retired->release();
    return kIOReturnSuccess;
}

// No caller-supplied root/tag and no public address getter. Only the actual
// domain can reach these primitives,after its execution-window/issuer drain.

bool ZornGen7HostGpuTables26::nativeProcessWindow(ZornGen7ProcessTables26 &p,
    ZornGen7ProcessTableOperation26 op,unsigned bank,size_t offset,uint64_t &ttbr0,
    uint16_t &asid,bool &writeRoot,bool &invalidate) const
{
    ttbr0=0;asid=0;writeRoot=false;invalidate=false;
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return false;
    const auto &s=*storage_;
    if(!s.ready || !s.contextReady || !s.directVmReady || !s.programReady[0] ||
       s.state[0].poisoned || s.state[1].poisoned || s.state[0].context_offset!=offset ||
       s.context[0].upper || bank!=s.context[0].asid || p.parent_!=this ||
       !p.prepared_ || !p.pinned_ || !p.pages_ || !p.asidHeld_ || p.state_.poisoned ||
       p.asid_<s.actualBankCount || !(s.processAsids[p.asid_>>6]&(UINT64_C(1)<<(p.asid_&63))) ||
       p.context_.asid!=p.asid_ || p.context_.lower!=&p.arena_.config ||
       p.context_.lower_tables!=&p.state_.tables)return false;
    ZornSmmuSparse4KContextImage actual{};
    if(ZornSmmuSparse4KEncodeContext(&p.context_,&actual)!=ZornSmmuSparse4KSuccess ||
       !exactImage(p.image_,actual))return false;
    actual.ttbr0=s.image[0].ttbr0;actual.ttbr1=s.image[0].ttbr1;
    if(!exactImage(actual,s.image[0]))return false;
    switch(op){
    case ZornGen7ProcessTableOperation26::Select:
        if(s.selectedProcess || (p.everExposed_ &&
           (!p.state_.detached || p.state_.context_offset!=offset)))return false;
        ttbr0=p.image_.ttbr0;asid=p.asid_;writeRoot=true;invalidate=true;return true;
    case ZornGen7ProcessTableOperation26::RestoreKernel:
        if(s.selectedProcess!=&p || !p.everExposed_ || p.state_.detached ||
           p.state_.context_offset!=offset)return false;
        ttbr0=s.image[0].ttbr0;asid=s.context[0].asid;writeRoot=true;invalidate=true;return true;
    case ZornGen7ProcessTableOperation26::RetireDetached:
        if(s.selectedProcess || !p.everExposed_ || !p.state_.detached ||
           p.state_.context_offset!=offset)return false;
        asid=p.asid_;invalidate=true;return true;
    case ZornGen7ProcessTableOperation26::AttachVm:
        return s.selectedProcess==&p && p.everExposed_ && !p.state_.detached &&
            p.state_.context_offset==offset;
    case ZornGen7ProcessTableOperation26::DetachVm:
        return !s.selectedProcess && p.everExposed_ && p.state_.detached &&
            p.state_.context_offset==offset;
    default:return false;
    }
}

IOReturn ZornGen7HostGpuTables26::selectProcessTables(ZornGen7ProcessTables26 &p,
    const ZornSmmuSparse4KIo &io,unsigned bank,size_t offset,unsigned budget)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    auto &s=*storage_;
    if(s.selectedProcess || !s.contextReady || !s.directVmReady || !s.programReady[0] ||
       s.state[0].poisoned || s.state[1].poisoned || p.parent_!=this || !p.prepared_ ||
       !p.pinned_ || !p.asidHeld_ || !p.pages_ || p.state_.poisoned ||
       p.asid_<s.actualBankCount || !(s.processAsids[p.asid_>>6]&(UINT64_C(1)<<(p.asid_&63))) ||
       s.state[0].context_offset!=offset || s.context[0].upper || !budget || budget>1048576 ||
       p.context_.asid!=p.asid_ || p.context_.lower!=&p.arena_.config ||
       p.context_.lower_tables!=&p.state_.tables)return kIOReturnNotReady;
    if(p.everExposed_ && (!p.state_.detached || p.state_.context_offset!=offset))return kIOReturnNotReady;
    // TTBR-only switch must preserve the actual live geometry. Different IAS
    // needs a separately implemented TCR transition,never a silent truncation.
    auto expected=p.image_;expected.ttbr0=s.image[0].ttbr0;expected.ttbr1=s.image[0].ttbr1;
    if(!exactImage(expected,s.image[0]))return kIOReturnUnsupported;
    if(observeRuntimeUser(io,bank,offset))return kIOReturnNotReady;
    ZornSmmuSparse4KStatus status=ZornSmmuSparse4KSuccess;
    if(p.vmAttached_ && !p.vmDetached_){if(p.vm_.auditLive())return kIOReturnNotReady;}
    else {status=ZornSmmuSparse4KLiveAudit(&p.arena_,&p.state_,p.ranges_,p.count_,&p.audit_);
        if(status!=ZornSmmuSparse4KSuccess || !p.audit_.complete)return kIOReturnNotReady;}
    if(!p.everExposed_){const auto raw=p.pages_->sealForContextUse(p);if(raw)return raw;}
    // Revoke never-installed retirement BEFORE any possible write. Publish
    // uncertain ownership first,so every partial write keeps backing and tag.
    p.everExposed_=true;s.selectedProcess=&p;
    p.state_.context_offset=offset;p.state_.detached=0;
    auto fail=[&](){p.state_.poisoned=1;s.state[0].poisoned=1;return kIOReturnIOError;};
    status=ZornSmmuSparse4KWriteContextTtbr0(&io,offset,p.image_.ttbr0,&p.switchWrite_);
    if(status!=ZornSmmuSparse4KSuccess)return fail();
    status=ZornSmmuSparse4KSyncContextTlb(&io,offset,p.asid_,0,budget,&p.switchSync_);
    if(status!=ZornSmmuSparse4KSuccess || !p.switchSync_.tlb_synchronized)return fail();
    status=ZornSmmuSparse4KObserveOwnedContext(&io,bank,&p.context_,&p.switchRead_);
    expected=p.image_;expected.ttbr1=s.image[0].ttbr1;
    if(status!=ZornSmmuSparse4KSuccess || !p.switchRead_.enabled || !p.switchRead_.readback_valid ||
       p.switchRead_.context_offset!=offset || !nativeHostImage(p.switchRead_.readback,expected))return fail();
    return kIOReturnSuccess;
}
IOReturn ZornGen7HostGpuTables26::restoreKernelTables(const ZornSmmuSparse4KIo &io,
    unsigned bank,size_t offset,unsigned budget)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    auto &s=*storage_;auto *p=s.selectedProcess;
    if(!p || p->parent_!=this || !p->everExposed_ || !p->prepared_ || !p->asidHeld_ ||
       p->state_.poisoned || s.state[0].poisoned || s.state[1].poisoned ||
       s.state[0].context_offset!=offset || p->state_.context_offset!=offset || p->state_.detached || !budget || budget>1048576)
        return kIOReturnNotReady;
    auto fail=[&](){p->state_.poisoned=1;s.state[0].poisoned=1;return kIOReturnIOError;};
    auto status=ZornSmmuSparse4KObserveOwnedContext(&io,bank,&p->context_,&p->switchRead_);
    auto expected=p->image_;expected.ttbr1=s.image[0].ttbr1;
    if(status!=ZornSmmuSparse4KSuccess || !p->switchRead_.enabled || !p->switchRead_.readback_valid ||
       !nativeHostImage(p->switchRead_.readback,expected))return fail();
    status=ZornSmmuSparse4KWriteContextTtbr0(&io,offset,s.image[0].ttbr0,&p->restoreWrite_);
    if(status!=ZornSmmuSparse4KSuccess)return fail();
    status=ZornSmmuSparse4KSyncContextTlb(&io,offset,s.context[0].asid,0,budget,&p->restoreSync_);
    if(status!=ZornSmmuSparse4KSuccess || !p->restoreSync_.tlb_synchronized)return fail();
    status=ZornSmmuSparse4KObserveOwnedContext(&io,bank,&s.context[0],&p->restoreRead_);
    if(status!=ZornSmmuSparse4KSuccess || !p->restoreRead_.enabled || !p->restoreRead_.readback_valid ||
       p->restoreRead_.context_offset!=offset || !nativeHostImage(p->restoreRead_.readback,s.image[0]))return fail();
    // Restored root is observed;old process TLB entries still exist until its
    // explicit retirement TLBSYNC. Never return its ASID on root write alone.
    p->state_.detached=1;s.selectedProcess=nullptr;return kIOReturnSuccess;
}
IOReturn ZornGen7HostGpuTables26::retireDetachedProcessTables(ZornGen7ProcessTables26 *&p,
    const ZornSmmuSparse4KIo &io,unsigned bank,size_t offset,unsigned budget)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate) || !p)return kIOReturnNotReady;
    auto &s=*storage_;
    if(s.selectedProcess || !p->everExposed_ || p->parent_!=this || !p->pinned_ || !p->prepared_ ||
       !p->pages_ || !p->asidHeld_ || p->state_.poisoned || !p->state_.detached ||
       (p->vmAttachAttempted_ && !p->vmDetached_) || p->clientOpen_ ||
       (p->clientOpenAttempted_ && !p->clientClosed_) || p->submitAttached_ ||
       (p->clientState_ && (p->clientState_->submit.outstanding() || p->clientState_->submit.poisoned())) ||
       p->state_.context_offset!=offset || !budget || budget>1048576 ||
       p->asid_<s.actualBankCount || !(s.processAsids[p->asid_>>6]&(UINT64_C(1)<<(p->asid_&63))) ||
       observeRuntimeUser(io,bank,offset))return kIOReturnNotReady;
    const auto audit=ZornSmmuSparse4KLiveAudit(&p->arena_,&p->state_,p->ranges_,p->count_,&p->audit_);
    if(audit!=ZornSmmuSparse4KSuccess || !p->audit_.complete)return kIOReturnNotReady;
    p->prepared_=false;
    const auto status=ZornSmmuSparse4KSyncContextTlb(&io,offset,p->asid_,0,budget,&p->retirementSync_);
    if(status!=ZornSmmuSparse4KSuccess || !p->retirementSync_.tlb_synchronized){p->state_.poisoned=1;return kIOReturnIOError;}
    const auto raw=p->pages_->retireAfterContextUse(*p);
    if(raw){p->state_.poisoned=1;return raw;}
    p->pages_->release();p->pages_=nullptr;
    // Actual detached-ASID TLBSYNC and complete real descriptor retirement.
    s.processAsids[p->asid_>>6]&=~(UINT64_C(1)<<(p->asid_&63));
    p->asidHeld_=false;p->asid_=0;p->context_={};p->image_={};
    p->arena_={};p->state_={};p->visibility_={};
    IODeleteData(p->ranges_,ZornSmmuSparse4KRange,p->count_);p->ranges_=nullptr;p->count_=0;
    auto *parent=p->parent_;p->parent_=nullptr;parent->release();
    auto *retired=p;p=nullptr;retired->pinned_=false;retired->release();retired->release();return kIOReturnSuccess;
}

IOReturn ZornGen7HostGpuTables26::attachProcessVm(ZornGen7ProcessTables26 &p,
    const ZornSmmuSparse4KIo &io,size_t capacity,unsigned budget)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    auto &s=*storage_;
    if(s.selectedProcess!=&p || p.parent_!=this || !p.prepared_ || !p.pinned_ ||
       !p.everExposed_ || !p.asidHeld_ || p.state_.poisoned || p.state_.detached ||
       !p.state_.context_offset || !p.domain_ || p.vmAttachAttempted_ ||
       p.routes_.cookie!=&p || !p.routes_.observe || !p.routes_.fault ||
       capacity<p.count_ || capacity>262144 || !budget || budget>1048576)return kIOReturnNotReady;
    p.vmAttachAttempted_=true;
    ZornGen7DirectVm26Region lower{p.pages_,&p.arena_,&p.state_};
    const auto raw=p.vm_.attachSeeded(&io,&p.context_,&p.routes_,&lower,nullptr,
        capacity,budget,p.ranges_,p.count_,nullptr,0,false);
    p.vmAttached_=raw==kIOReturnSuccess;return raw;
}
IOReturn ZornGen7HostGpuTables26::observeProcessTables(ZornGen7ProcessTables26 &p,
    const ZornSmmuSparse4KIo &io,unsigned bank,size_t offset)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    auto &s=*storage_;
    if(p.parent_!=this || !p.prepared_ || !p.everExposed_ || !p.asidHeld_ || !p.pinned_ ||
       p.state_.poisoned || p.state_.context_offset!=offset || s.state[0].poisoned ||
       s.state[1].poisoned)return kIOReturnNotReady;
    if(p.state_.detached){
        if(s.selectedProcess)return kIOReturnNotReady;
        return observeRuntimeUser(io,bank,offset);
    }
    if(s.selectedProcess!=&p)return kIOReturnNotReady;
    const auto status=ZornSmmuSparse4KObserveOwnedContext(&io,bank,&p.context_,&p.switchRead_);
    auto expected=p.image_;expected.ttbr1=s.image[0].ttbr1;
    return status==ZornSmmuSparse4KSuccess && p.switchRead_.enabled && p.switchRead_.readback_valid &&
        p.switchRead_.context_offset==offset && nativeHostImage(p.switchRead_.readback,expected)?
        kIOReturnSuccess:kIOReturnNotReady;
}
IOReturn ZornGen7HostGpuTables26::detachProcessVm(ZornGen7ProcessTables26 &p)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    auto &s=*storage_;
    if(s.selectedProcess || p.parent_!=this || !p.prepared_ || !p.everExposed_ ||
       !p.asidHeld_ || !p.vmAttached_ || p.vmDetached_ || p.state_.poisoned ||
       p.clientOpen_ || (p.clientOpenAttempted_ && !p.clientClosed_) || p.submitAttached_ ||
       (p.clientState_ && (p.clientState_->submit.outstanding() || p.clientState_->submit.poisoned())) ||
       !p.state_.detached || p.vm_.objectCount() || p.vm_.poisoned())return kIOReturnNotReady;
    const auto raw=p.vm_.detachSeeded(p.ranges_,p.count_,nullptr,0);
    if(!raw){p.vmDetached_=true;p.vmAttached_=false;}return raw;
}

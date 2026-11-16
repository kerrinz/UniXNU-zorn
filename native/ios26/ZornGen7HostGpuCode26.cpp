/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include "ZornGen7HostGpuCode26.h"
#include "ZornGen7RegisterMaps26.h"
#include "ZornGen7GmuIrq26.h"
#include "ZornGen7HwschedHfi26.h"
#include "ZornGen7DirectHfi26.h"
#include "ZornGen7SmmuDomain26.h"
#include "ZornGen7InactiveOwner26.h"
#include "ZornGen7FirmwareAssets26.h"
// Original retained houji implementation,not a new CP/packet model.
#include "GpuCodeBind.h"
#include <IOKit/IOLib.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
OSDefineMetaClassAndStructors(ZornGen7HostGpuCode26,OSObject)
static uint32_t zornCodeBindObservation[4];
void Zorn26RecordCodeBindResult(IOReturn raw)
{
    zornCodeBindObservation[0]=uint32_t(raw);
}
extern "C" void zorn26_native_code_bind_observation(uint32_t (&out)[4])
{
    memcpy(out,zornCodeBindObservation,sizeof(out));
}
namespace {bool normal(){return preemption_enabled() && !ml_at_interrupt_context() && ml_get_interrupts_enabled();}}
struct ZornGen7HostGpuCode26::Storage {
    IORecursiveLock &gate;FhgStorage &graph;HoujiFullHostNativeMemory &memory;ZornGen7InactiveOwner26 &parent;
    ZornGen7RegisterMaps26 &maps;ZornGen7GmuIrq26 &irq;OSObject &hfi;bool (*halted)(OSObject &);ZornGen7SmmuDomain26 &domain;
    FhgGraph logical{};FhgRange ranges[3]{};hcb_result binding{};
    bool attempted=false,ready=false,ioReturned=false;int ioRaw=0;uint32_t ioAddress=0;bool ioWrite=false;
    Storage(IORecursiveLock &g,FhgStorage &f,HoujiFullHostNativeMemory &m,ZornGen7InactiveOwner26 &p,
        ZornGen7RegisterMaps26 &v,ZornGen7GmuIrq26 &q,OSObject &h,bool (*check)(OSObject &),ZornGen7SmmuDomain26 &d):
        gate(g),graph(f),memory(m),parent(p),maps(v),irq(q),hfi(h),halted(check),domain(d){}
    static void *operator new(size_t,void *p)noexcept{return p;}
};
IOReturn ZornGen7HostGpuCode26::create(IORecursiveLock &g,FhgStorage &f,HoujiFullHostNativeMemory &m,
    ZornGen7InactiveOwner26 &p,ZornGen7RegisterMaps26 &v,ZornGen7GmuIrq26 &q,ZornGen7HwschedHfi26 &h,
    ZornGen7SmmuDomain26 &d,ZornGen7HostGpuCode26 *&out)
{
    return createTransport(g,f,m,p,v,q,h,[](OSObject &o){
        return static_cast<ZornGen7HwschedHfi26 &>(o).halted();
    },d,out);
}
IOReturn ZornGen7HostGpuCode26::create(IORecursiveLock &g,FhgStorage &f,HoujiFullHostNativeMemory &m,
    ZornGen7InactiveOwner26 &p,ZornGen7RegisterMaps26 &v,ZornGen7GmuIrq26 &q,ZornGen7DirectHfi26 &h,
    ZornGen7SmmuDomain26 &d,ZornGen7HostGpuCode26 *&out)
{
    return createTransport(g,f,m,p,v,q,h,[](OSObject &o){
        return static_cast<ZornGen7DirectHfi26 &>(o).halted();
    },d,out);
}
IOReturn ZornGen7HostGpuCode26::createTransport(IORecursiveLock &g,FhgStorage &f,HoujiFullHostNativeMemory &m,
    ZornGen7InactiveOwner26 &p,ZornGen7RegisterMaps26 &v,ZornGen7GmuIrq26 &q,OSObject &h,bool (*halted)(OSObject &),
    ZornGen7SmmuDomain26 &d,ZornGen7HostGpuCode26 *&out)
{
    if(out || !normal() || !IORecursiveLockHaveLock(&g))return kIOReturnNotReady;
    auto *o=new ZornGen7HostGpuCode26;if(!o)return kIOReturnNoMemory;
    if(!o->init()){o->release();return kIOReturnNoMemory;}o->retain();o->pinned_=true;out=o;
    p.retain();v.retain();q.retain();h.retain();d.retain();
    void *bytes=IOMallocZero(sizeof(Storage));if(!bytes)return kIOReturnNoMemory;
    o->storage_=new(bytes)Storage(g,f,m,p,v,q,h,halted,d);
    const auto raw=o->run();
    zornCodeBindObservation[0]=uint32_t(raw);
    zornCodeBindObservation[1]=o->storage_->ioAddress;
    zornCodeBindObservation[2]=uint32_t(o->storage_->ioRaw);
    zornCodeBindObservation[3]=o->storage_->binding.verified;
    return raw;
}
int ZornGen7HostGpuCode26::guard(void *context)
{
    auto *o=static_cast<ZornGen7HostGpuCode26 *>(context);
    if(!o || !o->storage_ || !normal())return 1;auto &s=*o->storage_;
    return !IORecursiveLockHaveLock(&s.gate) || s.irq.halted() || s.halted(s.hfi) || s.domain.faulted();
}
int ZornGen7HostGpuCode26::read(void *context,uint32_t address,uint32_t *out)
{
    if(!out || guard(context))return 1;auto &s=*static_cast<ZornGen7HostGpuCode26 *>(context)->storage_;
    uint32_t value=0;s.ioReturned=false;s.ioAddress=address;s.ioWrite=false;
    s.ioRaw=s.maps.accessHostGpuCodeWord(address,false,value);s.ioReturned=true;
    if(!s.ioRaw)*out=value;return s.ioRaw;
}
int ZornGen7HostGpuCode26::write(void *context,uint32_t address,uint32_t value)
{
    if(guard(context))return 1;auto &s=*static_cast<ZornGen7HostGpuCode26 *>(context)->storage_;
    s.ioReturned=false;s.ioAddress=address;s.ioWrite=true;
    s.ioRaw=s.maps.accessHostGpuCodeWord(address,true,value);s.ioReturned=true;return s.ioRaw;
}
IOReturn ZornGen7HostGpuCode26::run()
{
    if(guard(this))return kIOReturnNotReady;auto &s=*storage_;if(s.attempted)return kIOReturnNotReady;s.attempted=true;
    if(!s.memory.prepared() || fhg_graph(&s.graph,sizeof(s.graph),1,&s.logical,sizeof(s.logical)) ||
       s.logical.graph!=1 || s.logical.input_bits!=32 || s.logical.output_bits!=36 || s.logical.upper_region ||
       s.logical.range_count!=12 || !s.logical.audit_complete || s.logical.build_status || s.logical.audit_status)return kIOReturnNotReady;
    const auto &entry=s.memory.entry(FHG_CODE_SLOT);const auto &bo=s.memory.bo(FHG_CODE_SLOT);
    if(!entry.allocated || !entry.validated || !entry.published || entry.status || entry.request.slot!=FHG_CODE_SLOT ||
       !entry.request.normal_nc || !entry.nc || !bo.backed() || bo.quarantined() || bo.imported() || bo.readOnly() ||
       !bo.writeCombined() || bo.deviceReferences()!=1 || !bo.mapping() || !bo.descriptor() ||
       bo.mapping()!=entry.backing.cpu || bo.bytes()!=HCC_BYTES || bo.bytes()!=entry.request.logical_bytes ||
       bo.ownedBytes()!=entry.request.owned_bytes || bo.descriptor()->getLength()!=bo.ownedBytes() ||
       bo.cpuPageBytes()!=entry.request.cpu_page_bytes || bo.spanCount()!=1 || bo.ownedSpanCount()!=1 ||
       bo.spans()[0].offset || bo.ownedSpans()[0].offset || bo.spans()[0].bytes!=HCC_BYTES ||
       bo.ownedSpans()[0].bytes!=bo.ownedBytes() || bo.spans()[0].physical!=entry.backing.physical ||
       bo.ownedSpans()[0].physical!=entry.backing.owned_physical || bo.spans()[0].physical!=bo.ownedSpans()[0].physical)return kIOReturnNotReady;
    // These are actual graph logical ranges,not an old root/descriptor replay.
    constexpr uint32_t offsets[]={HCC_SQE_OFFSET,HCC_AQE_OFFSET,HCC_RECORD_OFFSET};
    constexpr uint32_t sizes[]={21*4096,9*4096,4096};
    constexpr uint32_t perms[]={ArmSmmu4KRead|ArmSmmu4KExecute,ArmSmmu4KRead|ArmSmmu4KExecute,
        ArmSmmu4KRead|ArmSmmu4KWrite|ArmSmmu4KPrivileged};
    for(unsigned i=0;i<3;++i){auto &r=s.ranges[i];
        if(fhg_range(&s.graph,sizeof(s.graph),1,9+i,&r,sizeof(r)) || r.reserved ||
           r.iova!=HCC_IOVA+offsets[i] || r.physical!=bo.spans()[0].physical+offsets[i] ||
           r.bytes!=sizes[i] || r.permissions!=perms[i] || r.writeback || r.shareability!=3)return kIOReturnNotReady;
    }
    // Compare actual WC native payload/padding/record bytes with the retained
    // K80 immutable firmware arrays;no caller-supplied code image or fake BO.
    if(!ZornGen7ValidateOwnedGpuCode26(bo) || guard(this) || !s.maps.bindHostGpuCode(*this,s.parent))return kIOReturnNotReady;
    const hcb_io io{this,read,write,guard};const auto result=hcb_run(&io,&s.binding);
    if(result!=HCB_OK || s.binding.verified!=15 || s.binding.control_before || s.binding.control_after || guard(this))return kIOReturnIOError;
    s.ready=true;return kIOReturnSuccess;
    // Still disabled SQE. No RAW/trust/PAS/GPU execution,fence or release.
}
void ZornGen7HostGpuCode26::free(){if(pinned_)return;OSObject::free();}

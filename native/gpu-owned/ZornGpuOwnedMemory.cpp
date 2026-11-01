/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include "ZornGpuOwnedMemory.h"
static bool validSpan(const void *p,size_t bytes,size_t alignment=1)
{return p && bytes && !(uintptr_t(p)%alignment) && uintptr_t(p)<=UINTPTR_MAX-(bytes-1);}
static bool overlap(const void *a,size_t na,const void *b,size_t nb)
{return uintptr_t(a)<=uintptr_t(b)?uintptr_t(b)-uintptr_t(a)<na:uintptr_t(a)-uintptr_t(b)<nb;}
IOReturn ZornGpuOwnedMemory::fail(unsigned source,IOReturn status)
{
    report_.failure_source=source;report_.returned_status=status;
    report_.state=ZGOM_RETAINED_FAILURE;return status;
}
IOReturn ZornGpuOwnedMemory::check(unsigned phase,unsigned index)
{
    report_.phase=phase;report_.index=index;
    const IOReturn status=gate_.check(gate_.cookie,gate_.epoch,this,phase,index);
    if(status!=kIOReturnSuccess)report_.original_gate_status=status;
    return status;
}
void ZornGpuOwnedMemory::observe(unsigned index)
{
    const auto &memory=memory_[index];
    if(memory.backed() || memory.spans() || memory.mapping())report_.backed_mask|=1u<<index;
    if(memory.quarantined()){
        report_.quarantined_mask|=1u<<index;
        report_.cleanup_status_unavailable_mask|=1u<<index;
    }
    report_.retained_bytes=0;
    for(unsigned i=0;i<8;++i)report_.retained_bytes+=(uint32_t)memory_[i].bytes();
}
IOReturn ZornGpuOwnedMemory::snapshotCheck(void *p,uint64_t epoch,const NativeAdrenoMemory *memory)
{
    auto &cookie=*static_cast<SnapshotCookie *>(p);auto &owner=*cookie.owner;
    if(epoch!=owner.gate_.epoch || cookie.index>=8 || memory!=&owner.memory_[cookie.index])return kIOReturnBadArgument;
    return owner.check(ZGOM_GATE_SNAPSHOT,cookie.index);
}
IOReturn ZornGpuOwnedMemory::prepare(const ZornGpuBlob images[ZGP_IMAGES],unsigned bits,
    const ZornGpuPrepareGate *gate)
{
    if(report_.state!=ZGOM_FRESH)return kIOReturnBusy;
    if(!(bits==32 || bits==36 || bits==40 || bits==42 || bits==44 || bits==48) ||
       !validSpan(images,sizeof(ZornGpuBlob)*ZGP_IMAGES,alignof(ZornGpuBlob)) ||
       !validSpan(gate,sizeof(*gate),alignof(ZornGpuPrepareGate)) ||
       overlap(images,sizeof(ZornGpuBlob)*ZGP_IMAGES,this,sizeof(*this)) ||
       overlap(gate,sizeof(*gate),this,sizeof(*this)) || overlap(gate,sizeof(*gate),images,sizeof(ZornGpuBlob)*ZGP_IMAGES) ||
       !gate->epoch || !gate->check)return kIOReturnBadArgument;
    for(unsigned i=0;i<ZGP_IMAGES;++i){
        if(!validSpan(images[i].data,images[i].bytes) ||
           overlap(images[i].data,images[i].bytes,this,sizeof(*this)) ||
           overlap(images[i].data,images[i].bytes,gate,sizeof(*gate)))return kIOReturnBadArgument;
    }
    gate_=*gate;report_.state=ZGOM_PREPARING;report_.epoch=gate_.epoch;
    report_.output_policy_bits=bits;report_.returned_status=kIOReturnNotReady;
    for(unsigned i=0;i<8;++i)report_.allocation_status[i]=kIOReturnNotReady;
    IOReturn status=check(ZGOM_GATE_PLAN,0);
    if(status!=kIOReturnSuccess)return fail(ZGOM_FAILURE_GATE,status);
    const ZornGpuLimits limits{64,16,565248,73728};
    report_.plan_attempted=1;
    const auto planned=ZornGpuBuildFirmwarePlan(images,&limits,&scratch_,&plan_);
    report_.plan_status=planned;
    if(planned!=ZGP_OK)return fail(ZGOM_FAILURE_PLAN,kIOReturnBadArgument);
    if(plan_.backing_count!=8 || plan_.backing_bytes!=565248 || plan_.runtime_complete)
        return fail(ZGOM_FAILURE_SHAPE,kIOReturnNotReady);
    for(unsigned i=0;i<8;++i){
        status=check(ZGOM_GATE_ALLOCATE,i);
        if(status!=kIOReturnSuccess)return fail(ZGOM_FAILURE_GATE,status);
        const size_t bytes=plan_.backings[i].bytes;
        if(!bytes || (bytes&4095) || bytes>565248-report_.allocated_bytes)
            return fail(ZGOM_FAILURE_SHAPE,kIOReturnBadArgument);
        report_.attempted_mask|=1u<<i;
        status=memory_[i].allocate(bytes,bits,true,bytes,false);
        report_.allocation_status[i]=status;
        observe(i);
        if(status!=kIOReturnSuccess){report_.original_native_status=status;return fail(ZGOM_FAILURE_NATIVE,status);}
        report_.allocated_bytes+=(uint32_t)bytes;
        status=check(ZGOM_GATE_AFTER_ALLOCATE,i);
        if(status!=kIOReturnSuccess)return fail(ZGOM_FAILURE_GATE,status);
        SnapshotCookie cookie{this,i};const ZornGpuBackingLease lease{gate_.epoch,&cookie,snapshotCheck};
        status=ZornGpuSnapshotNativeBacking(&memory_[i],bytes,bits,&lease,&report_.snapshots[i]);
        report_.original_snapshot_status=status;
        if(status!=kIOReturnSuccess)return fail(report_.original_gate_status?ZGOM_FAILURE_GATE:ZGOM_FAILURE_SNAPSHOT,status);
        const auto &now=report_.snapshots[i];
        for(unsigned j=0;j<i;++j){
            const auto &previous=report_.snapshots[j];
            if(overlap(now.cpu,size_t(now.bytes),previous.cpu,size_t(previous.bytes)) ||
               (now.physical<previous.physical+previous.bytes && previous.physical<now.physical+now.bytes))
                return fail(ZGOM_FAILURE_SHAPE,kIOReturnBadArgument);
        }
        report_.described_mask|=1u<<i;
    }
    status=check(ZGOM_GATE_FINISH,8);
    if(status!=kIOReturnSuccess)return fail(ZGOM_FAILURE_GATE,status);
    report_.state=ZGOM_CPU_PREPARED;report_.returned_status=kIOReturnSuccess;
    report_.runtime_complete=0;return kIOReturnSuccess;
}

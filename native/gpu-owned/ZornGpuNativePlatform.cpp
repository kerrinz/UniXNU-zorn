/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include "ZornGpuNativePlatform.h"
#include "K80GpuResourceProfile.inc"
static bool span(const void *p,size_t n,size_t alignment=1)
{return p && n && !(uintptr_t(p)%alignment) && uintptr_t(p)<=UINTPTR_MAX-(n-1);}
static bool overlap(const void *a,size_t na,const void *b,size_t nb)
{return uintptr_t(a)<=uintptr_t(b)?uintptr_t(b)-uintptr_t(a)<na:uintptr_t(a)-uintptr_t(b)<nb;}
static bool nameEqual(const char *a,size_t n,const char *b)
{
    size_t i=0;while(i<n && b[i]){if(a[i]!=b[i])return false;++i;}
    return i==n && !b[i];
}
static bool nodeValid(const ZornGpuDtResourceNode *node,const void *out,size_t bytes)
{
    return span(node,sizeof(*node),alignof(ZornGpuDtResourceNode)) &&
        span(node->reg,node->reg_bytes) && span(node->names,node->names_bytes) &&
        node->reg_bytes<=128 && node->names_bytes<=256 &&
        !overlap(node,sizeof(*node),out,bytes) && !overlap(node->reg,node->reg_bytes,out,bytes) &&
        !overlap(node->names,node->names_bytes,out,bytes) &&
        !overlap(node->reg,node->reg_bytes,node->names,node->names_bytes) &&
        !overlap(node,sizeof(*node),node->reg,node->reg_bytes) &&
        !overlap(node,sizeof(*node),node->names,node->names_bytes);
}
static IOReturn parseNode(const ZornGpuDtResourceNode &node,unsigned first,unsigned count,
    ZornGpuResourceDescription &result)
{
    NativeAdrenoWindow windows[NativeAdrenoMaxWindows]{};size_t actual=0;
    IOReturn status=NativeAdrenoBoard::parseReg(node.reg,node.reg_bytes,node.address_cells,
        node.size_cells,windows,NativeAdrenoMaxWindows,&actual);
    if(status!=kIOReturnSuccess)return status;
    if(actual!=count)return kIOReturnBadArgument;
    size_t at=0;uint32_t seen=0;
    for(unsigned n=0;n<count;++n){
        const size_t begin=at;
        while(at<node.names_bytes && node.names[at])++at;
        if(at==node.names_bytes || begin==at)return kIOReturnBadArgument;
        unsigned role=ZGN_RESOURCES;
        for(unsigned i=first;i<first+count;++i)
            if(nameEqual(node.names+begin,at-begin,k80Resources[i].name)){role=i;break;}
        if(role==ZGN_RESOURCES || (seen&(1u<<role)) ||
           windows[n].base!=k80Resources[role].base || windows[n].bytes!=k80Resources[role].bytes)
            return kIOReturnBadArgument;
        seen|=1u<<role;result.resources[role]=windows[n];++at;
    }
    return at==node.names_bytes?kIOReturnSuccess:kIOReturnBadArgument;
}
IOReturn ZornGpuDescribeResources(const ZornGpuDtResourceNode *gpu,
    const ZornGpuDtResourceNode *gmu,ZornGpuResourceDescription *out)
{
    if(!span(out,sizeof(*out),alignof(ZornGpuResourceDescription)) ||
       !nodeValid(gpu,out,sizeof(*out)) || !nodeValid(gmu,out,sizeof(*out)) ||
       overlap(gpu,sizeof(*gpu),gmu,sizeof(*gmu)))return kIOReturnBadArgument;
    const void *gp[]={gpu,gpu->reg,gpu->names},*mp[]={gmu,gmu->reg,gmu->names};
    const size_t gn[]={sizeof(*gpu),gpu->reg_bytes,gpu->names_bytes},mn[]={sizeof(*gmu),gmu->reg_bytes,gmu->names_bytes};
    for(unsigned i=0;i<3;++i)for(unsigned j=0;j<3;++j)
        if(overlap(gp[i],gn[i],mp[j],mn[j]))return kIOReturnBadArgument;
    ZornGpuResourceDescription built{};
    IOReturn status=parseNode(*gpu,0,7,built);if(status!=kIOReturnSuccess)return status;
    status=parseNode(*gmu,7,3,built);if(status!=kIOReturnSuccess)return status;
    for(unsigned i=0;i<ZGN_RESOURCES;++i)for(unsigned j=0;j<ZGN_RESOURCES;++j)
        if(i!=j && built.resources[i].base<built.resources[j].base+built.resources[j].bytes &&
           built.resources[j].base<built.resources[i].base+built.resources[i].bytes)built.overlaps[i]|=1u<<j;
    built.descriptor_valid=1;built.runtime_complete=0;*out=built;return kIOReturnSuccess;
}
IOReturn ZornGpuDescribeRequirements(const ZornGpuResourceDescription *resources,
    const ZornGpuFirmwarePlan *plan,ZornGpuNativeRequirements *out)
{
    if(!span(resources,sizeof(*resources),alignof(ZornGpuResourceDescription)) ||
       !span(plan,sizeof(*plan),alignof(ZornGpuFirmwarePlan)) ||
       !span(out,sizeof(*out),alignof(ZornGpuNativeRequirements)) ||
       overlap(resources,sizeof(*resources),out,sizeof(*out)) || overlap(plan,sizeof(*plan),out,sizeof(*out)) ||
       overlap(resources,sizeof(*resources),plan,sizeof(*plan)))return kIOReturnBadArgument;
    if(resources->descriptor_valid!=1 || resources->runtime_complete)return kIOReturnNotReady;
    for(unsigned i=0;i<ZGN_RESOURCES;++i)
        if(resources->resources[i].base!=k80Resources[i].base || resources->resources[i].bytes!=k80Resources[i].bytes)
            return kIOReturnBadArgument;
    if(plan->runtime_complete || plan->backing_count!=8 || plan->backing_bytes!=565248 ||
       plan->queue_count!=17 || plan->hfi_backing_bytes!=73728 || plan->log_backing_bytes!=65536 ||
       !plan->zap_requires_authentication)return kIOReturnNotReady;
    ZornGpuNativeRequirements built{};built.backing_count=plan->backing_count;
    built.static_backing_bytes=plan->backing_bytes;built.log_bytes=plan->log_backing_bytes;
    built.hfi_bytes=plan->hfi_backing_bytes;built.persistent_requests=plan->persistent_requests;
    uint64_t total=0;
    for(unsigned i=0;i<plan->backing_count;++i){
        const auto &b=plan->backings[i];
        if(!b.bytes || (b.bytes&4095) || b.fixed_iova>1 || b.persistent_requested>1)return kIOReturnBadArgument;
        total+=b.bytes;
        if(b.fixed_iova)++built.pending_fixed_iova;else ++built.pending_dynamic_iova;
    }
    if(total!=plan->backing_bytes)return kIOReturnBadArgument;
    built.missing=ZGN_MISSING_OPERATION_SCOPES|ZGN_MISSING_POWER_CLOCKS|ZGN_MISSING_SMMU_OWNERSHIP|
        ZGN_MISSING_ZAP_AUTH|ZGN_MISSING_BOARD_VOTES|ZGN_MISSING_LIVE_HFI|
        ZGN_MISSING_RUNTIME_ALLOCATIONS|ZGN_MISSING_BACKING_BINDINGS;
    built.runtime_complete=0;*out=built;return kIOReturnSuccess;
}
IOReturn ZornGpuSnapshotNativeBacking(const NativeAdrenoMemory *memory,size_t bytes,
    unsigned bits,const ZornGpuBackingLease *lease,ZornGpuBackingSnapshot *out)
{
    if(!span(memory,sizeof(*memory),alignof(NativeAdrenoMemory)) ||
       !span(lease,sizeof(*lease),alignof(ZornGpuBackingLease)) ||
       !span(out,sizeof(*out),alignof(ZornGpuBackingSnapshot)) ||
       overlap(memory,sizeof(*memory),out,sizeof(*out)) || overlap(lease,sizeof(*lease),out,sizeof(*out)) ||
       overlap(memory,sizeof(*memory),lease,sizeof(*lease)) || !bytes || (bytes&4095) ||
       !(bits==32 || bits==36 || bits==40 || bits==42 || bits==44 || bits==48) ||
       !lease->epoch || !lease->check)return kIOReturnBadArgument;
    IOReturn status=lease->check(lease->cookie,lease->epoch,memory);if(status!=kIOReturnSuccess)return status;
    if(!memory->backed() || memory->imported() || memory->readOnly() || memory->quarantined() ||
       memory->deviceReferences() || memory->bytes()!=bytes || memory->spanCount()!=1 ||
       !span(memory->mapping(),bytes,4096))return kIOReturnNotReady;
    const auto *spans=memory->spans();
    if(!span(spans,sizeof(*spans),alignof(NativeAdrenoPhysicalSpan)) ||
       overlap(out,sizeof(*out),memory->mapping(),bytes) ||
       overlap(out,sizeof(*out),spans,sizeof(*spans)) ||
       overlap(lease,sizeof(*lease),memory->mapping(),bytes) ||
       overlap(lease,sizeof(*lease),spans,sizeof(*spans)))return kIOReturnBadArgument;
    const auto physical=spans[0].physical;const uint64_t limit=UINT64_C(1)<<bits;
    if(spans[0].offset || spans[0].bytes!=bytes || !physical || (physical&4095) ||
       physical>=limit || uint64_t(bytes)>limit-physical)return kIOReturnBadArgument;
    ZornGpuBackingSnapshot built{};built.owner=memory;built.cpu=memory->mapping();
    built.physical=physical;built.bytes=bytes;built.epoch=lease->epoch;built.span_count=1;
    built.device_references=memory->deviceReferences();built.write_combined=memory->writeCombined();
    built.runtime_complete=0;
    status=lease->check(lease->cookie,lease->epoch,memory);if(status!=kIOReturnSuccess)return status;
    *out=built;return kIOReturnSuccess;
}

/* SPDX-License-Identifier: MIT */
#include "ZornGen7DirectVm26.h"
#include "ZornGen7DirectVm26Alias.h"
#include "NativeAdrenoCoherencePolicy.h"
extern "C" volatile uint32_t native_adreno_trace_stage;
extern "C" {int (*zorn_direct_dram_read32)(uint64_t,uint32_t *);int (*zorn_direct_cached_read32)(uint64_t,uint32_t *);
    int (*zorn_direct_line_audit)(uint64_t,size_t,uint32_t *,uint32_t *);}
#include <string.h>
#include <IOKit/IOLib.h>
#include <kern/clock.h>
/* Nonzero only once the board proved the GPU's cacheable inner-shareable accesses coherent with the CPU's caches in both directions (the A740's
 * ADRENO_QUIRK_HAS_CACHED_COHERENT behind the dma-coherent GPU SMMU, which Linux maps with IOMMU_CACHE): a mapping with write-back
 * attributes then needs no CPU cache maintenance. 0 keeps every mapping maintained as before. Counters: maintenance passes skipped for
 * coherent mappings at map, unmap, submission and completion. Mode 2 additionally
 * selects writable imports after same-boot WB render-target proofs. */
extern "C" {volatile uint32_t zorn_direct_io_coherent;volatile uint32_t zorn_direct_coherent_skips[4];}
extern "C" {volatile uint32_t zorn_direct_coherent_import_fallbacks;}
static bool coherentMapping(unsigned writeback,unsigned shareability)
{return NativeAdrenoCoherentMapping(zorn_direct_io_coherent,writeback,shareability);}
/* Houji's CPU presenter does read imported surfaces. Never adopt upstream's
 * importedUntouched shortcut for NC mappings. Only qualified WB/inner-shareable
 * mappings can skip maintenance, at the same map/submit/complete/unmap edges. */
static bool overlap(uint64_t a,uint64_t ab,uint64_t b,uint64_t bb)
{return a<b+bb && b<a+ab;}
/* Mappings of one cache/shareability/privilege class may share pages; only pages shared across classes refuse. */
static unsigned aliasClass(unsigned permissions,unsigned writeback,unsigned shareability)
{return writeback|(shareability<<1)|((permissions&ZornSmmuSparse4KPrivileged)?8u:0u);}
static void reverse(ZornSmmuSparse4KRange *first,ZornSmmuSparse4KRange *last)
{while(first<last && first<--last) {const ZornSmmuSparse4KRange t=*first;*first++=*last;*last=t;}}
IOReturn ZornGen7DirectVm26::bindVisibility(ZornGen7SmmuTablePages26 *owner,ZornSmmuSparse4KLiveVisibility *out)
{
    if(!owner || !out)return kIOReturnBadArgument;const auto actual=owner->visibility();
    if(!actual.cookie || !actual.publish_table_page)return kIOReturnNotReady;*out=actual;return kIOReturnSuccess;
}
bool ZornGen7DirectVm26::validBinding(const ZornGen7DirectVm26Region &r,unsigned upper)
{
    return r.tables && r.arena && r.state && !r.tables->quarantined() && r.tables->provider() &&
        r.arena->pages==r.tables->provider() && r.arena->upper_region==upper &&
        r.tables->provider()->find(r.tables->provider()->cookie,r.arena->config.table_physical) &&
        r.state->prepared && !r.state->poisoned;
}
ZornSmmuSparse4KLiveRegion ZornGen7DirectVm26::region(unsigned upper,ZornSmmuSparse4KLiveArena &view) const
{
    const auto *arena=regions_[upper].arena;
    if(arena) {
        view=*arena;
        // Houji's retained GMU owner hashes the original arena. Scratch is
        // CPU-only call metadata: never rewrite that sealed descriptor, even
        // temporarily. The same table mapping/config/state remain authoritative.
        if(alias_scratch_) {view.alias_scratch=alias_scratch_;view.alias_scratch_entries=capacity_;}
    }
    return {arena?&view:nullptr,regions_[upper].state,
        ranges_+(upper?lower_count_:0),upper?upper_count_:lower_count_};
}
// OS diagnostic time has kernel lifetime and no per-call context. The real
// submission/fence deadlines continue to use their supplied NativeAdrenoRingClock.
extern "C" uint64_t zorn_direct_vm_now_us(void)
{
    uint64_t absolute=0,ns=0;clock_get_uptime(&absolute);absolutetime_to_nanoseconds(absolute,&ns);return ns/1000;
}
/* Board hook and per-phase time of the two table transactions, for the log: [0] map, [1] unmap; each row is count, the phases in order, the slowest call
 * and the bytes mapped (int-134: BoMap averaged 135 ms and the desktop crawled). */
extern "C" {volatile uint64_t zorn_direct_vm_phase_us[2][8];}
extern "C" {uint64_t zorn_direct_vm_phase_max_us[2][6];}
extern "C" {uint64_t zorn_direct_vm_alias_paths[2];} // indexed / pairwise preflight
namespace {
struct PhaseClock {
    uint64_t last=zorn_direct_vm_now_us(),began=last;
    void lap(unsigned row,unsigned slot) {
        const uint64_t now=zorn_direct_vm_now_us(),elapsed=now-last;
        zorn_direct_vm_phase_us[row][slot]+=elapsed;last=now;
        uint64_t old=__atomic_load_n(&zorn_direct_vm_phase_max_us[row][slot],__ATOMIC_RELAXED);
        while(elapsed>old && !__atomic_compare_exchange_n(&zorn_direct_vm_phase_max_us[row][slot],&old,elapsed,false,__ATOMIC_RELAXED,__ATOMIC_RELAXED)){}
    }
    void done(unsigned row,uint64_t bytes) {
        const uint64_t total=zorn_direct_vm_now_us()-began;
        zorn_direct_vm_phase_us[row][0]+=1;zorn_direct_vm_phase_us[row][7]+=bytes;
        if(total>zorn_direct_vm_phase_us[row][6])zorn_direct_vm_phase_us[row][6]=total;
    }
};
}
ZornSmmuSparse4KStatus ZornGen7DirectVm26::observe() const
{
    ZornSmmuSparse4KStatus status=streams_->observe(streams_->cookie,true);if(status)return status;
    ZornSmmuSparse4KLiveArena views[2]{};
    ZornSmmuSparse4KLiveRegion lower=region(0,views[0]),upper=region(1,views[1]);ZornSmmuSparse4KLiveResult audit;
    status=ZornSmmuSparse4KLiveAuditContext(context_,lower.arena?&lower:nullptr,upper.arena?&upper:nullptr,&audit);
    if(status)return status;
    return streams_->observe(streams_->cookie,true);
}
/* Global policy, the context image and the owned routes only. The scan of every other slot for a conflicting route read each
 * SMR/S2CR of the SMMU twice per map and unmap (int-152: 0.75 ms a pass, 1.3 s of the 3.2 s of 807 maps); the periodic route check keeps that conflict scan. */
ZornSmmuSparse4KStatus ZornGen7DirectVm26::observeStreamsOnly() const
{
    return streams_->observe(streams_->cookie,false);
}
/* Every 64th table operation scans the SMMU's routes for a conflict with the owned ones; the ones between read no SMMU register
 * before the table transaction (int-159: a map read the owned routes before and after its transaction, 0.4 ms of its 1.7 ms). The
 * tables are not walked here: attach proved them whole and each transaction proves what it changes (i557u: a whole walk of both
 * regions every 64th operation stalled a map 37 ms). */
ZornSmmuSparse4KStatus ZornGen7DirectVm26::observeCheap()
{
    if(++since_audit_>=64) {
        since_audit_=0;
            return streams_->observe(streams_->cookie,true);
    }
    return ZornSmmuSparse4KSuccess;
}
IOReturn ZornGen7DirectVm26::fail(ZornSmmuSparse4KStatus status)
{
    poisoned_=true;result_.operation=status;result_.complete=false;
    for(size_t i=0;mappings_ && i<ZornGen7DirectVm26MaxObjects;++i)if(mappings_[i].memory)mappings_[i].memory->quarantine();
    for(auto &r:regions_)if(r.arena) {r.tables->quarantine();r.state->poisoned=1;}
    result_.quarantine=streams_->fault(streams_->cookie);
    return kIOReturnIOError;
}
IOReturn ZornGen7DirectVm26::attach(const ZornSmmuSparse4KIo *io,ZornSmmuSparse4KContextConfig *context,
    ZornGen7DirectVm26Routes *streams,const ZornGen7DirectVm26Region *lower,const ZornGen7DirectVm26Region *upper,
    size_t capacity,unsigned budget)
{
    return attachSeeded(io,context,streams,lower,upper,capacity,budget,nullptr,0,nullptr,0);
}
IOReturn ZornGen7DirectVm26::attachSeeded(const ZornSmmuSparse4KIo *io,ZornSmmuSparse4KContextConfig *context,
    ZornGen7DirectVm26Routes *streams,const ZornGen7DirectVm26Region *lower,const ZornGen7DirectVm26Region *upper,
    size_t capacity,unsigned budget,const ZornSmmuSparse4KRange *lower_seeds,size_t lower_count,
    const ZornSmmuSparse4KRange *upper_seeds,size_t upper_count,bool per_page_tlb_invalidation,bool allocate_alias_workspace)
{
    if(attached_ || ranges_ || alias_scratch_ || poisoned_)return kIOReturnBusy;
    if(!io || !context || !streams || !streams->cookie || !streams->observe || !streams->fault ||
        !streams->haltForTableUpdate || !streams->releaseAfterTableUpdate || !streams->beginSubmission || !streams->endSubmission ||
        (!lower && !upper) || !capacity || capacity>262144 ||
        !budget || budget>1048576 || (lower && !validBinding(*lower,0)) || (upper && !validBinding(*upper,1)))
        return kIOReturnBadArgument;
    if(lower_count>capacity || upper_count>capacity-lower_count ||
        (lower_count && (!lower || !lower_seeds)) || (upper_count && (!upper || !upper_seeds)))return kIOReturnBadArgument;
    ZornSmmuSparse4KLiveResult seeded{};
    if((lower && ZornSmmuSparse4KLiveAudit(lower->arena,lower->state,lower_seeds,lower_count,&seeded)) ||
       (upper && ZornSmmuSparse4KLiveAudit(upper->arena,upper->state,upper_seeds,upper_count,&seeded)))return kIOReturnBadArgument;
    capacity_=capacity;
    ranges_=IONewData(ZornSmmuSparse4KRange,capacity);
    mappings_=IONewData(Mapping,ZornGen7DirectVm26MaxObjects);
    if(allocate_alias_workspace)alias_scratch_=IONewData(uint32_t,capacity);
    if(!ranges_ || !mappings_ || (allocate_alias_workspace && !alias_scratch_)) {freeMetadata();return kIOReturnNoMemory;}
    memset(mappings_,0,sizeof(Mapping)*ZornGen7DirectVm26MaxObjects);
    for(size_t i=0;i<lower_count;i++)ranges_[i]=lower_seeds[i];
    for(size_t i=0;i<upper_count;i++)ranges_[lower_count+i]=upper_seeds[i];
    lower_count_=lower_count;upper_count_=upper_count;
    capacity_=capacity;io_=*io;context_=context;streams_=streams;budget_=budget;
    per_page_tlb_invalidation_=per_page_tlb_invalidation;
    if(lower)regions_[0]=*lower;if(upper)regions_[1]=*upper;
    for(unsigned i=0;i<2;++i)if(regions_[i].arena) {
        if(bindVisibility(regions_[i].tables,&visibility_[i])!=kIOReturnSuccess) {
            freeMetadata();return kIOReturnBadArgument;
        }
    }
    attached_=true;
    ZornSmmuSparse4KStatus status=observe();if(status)return fail(status);
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectVm26::enableAliasWorkspace()
{
    if(!attached_ || poisoned_)return kIOReturnNotReady;
    if(alias_scratch_)return kIOReturnSuccess;
    if(objects_)return kIOReturnBusy;
    ZornSmmuSparse4KStatus status=observe();if(status)return fail(status);
    uint32_t *scratch=IONewData(uint32_t,capacity_);
    if(!scratch)return kIOReturnNoMemory;
    alias_scratch_=scratch;
    status=observe();if(status)return fail(status);
    return kIOReturnSuccess;
}
void ZornGen7DirectVm26::freeMetadata()
{
    if(alias_scratch_)IODeleteData(alias_scratch_,uint32_t,capacity_);
    if(mappings_)IODeleteData(mappings_,Mapping,ZornGen7DirectVm26MaxObjects);
    if(ranges_)IODeleteData(ranges_,ZornSmmuSparse4KRange,capacity_);
    alias_scratch_=nullptr;mappings_=nullptr;ranges_=nullptr;
    regions_[0]={};regions_[1]={};
    visibility_[0]={};visibility_[1]={};context_=nullptr;streams_=nullptr;
    capacity_=lower_count_=upper_count_=objects_=0;
}
IOReturn ZornGen7DirectVm26::detach()
{
    if(poisoned_ || objects_ || spanCount() || submission_resources_)return kIOReturnBusy;
    if(!attached_)return kIOReturnNotReady;
    freeMetadata();attached_=false;
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectVm26::findAddress(unsigned upper,size_t bytes,uint64_t alignment,uint64_t *out) const
{
    if(!out)return kIOReturnBadArgument;*out=0;
    if(!attached_ || poisoned_)return kIOReturnNotReady;
    if(upper>1 || !regions_[upper].arena || !bytes || (bytes&4095) || alignment<4096 ||
        (alignment&(alignment-1)))return kIOReturnBadArgument;
    const ZornSmmuSparse4KLiveArena *a=regions_[upper].arena;
    uint64_t offset=0;
    for(size_t i=upper?lower_count_:0;;++i) {
        uint64_t rem=(a->iova+offset)&(alignment-1),padding=rem?alignment-rem:0;
        if(padding>a->bytes-offset)return kIOReturnNoResources;offset+=padding;
        if(bytes>a->bytes-offset)return kIOReturnNoResources;
        if(i==(upper?spanCount():lower_count_) ||
            (ranges_[i].iova-a->iova>=offset && bytes<=ranges_[i].iova-a->iova-offset))
            {*out=a->iova+offset;return kIOReturnSuccess;}
        uint64_t end=ranges_[i].iova-a->iova+ranges_[i].bytes;
        if(end>offset)offset=end;
    }
}
IOReturn ZornGen7DirectVm26::preflight(const NativeAdrenoMemory *memory,unsigned upper,uint64_t iova,
    unsigned permissions,unsigned writeback,unsigned shareability) const
{
    if(!memory || upper>1 || !regions_[upper].arena || !memory->backed() || memory->quarantined() ||
        !memory->bytes() || !memory->spanCount() || !(permissions&ZornSmmuSparse4KRead) || (permissions&~15u) ||
        writeback>1 || (shareability!=2 && shareability!=3))return kIOReturnBadArgument;
    const ZornSmmuSparse4KLiveArena *a=regions_[upper].arena;
    if((iova&4095) || iova<a->iova || iova-a->iova>=a->bytes || memory->bytes()>a->bytes-(iova-a->iova))
        return kIOReturnBadArgument;
    if(objects_>=ZornGen7DirectVm26MaxObjects || memory->spanCount()>capacity_-spanCount())return kIOReturnNoResources;
    for(size_t i=0;i<spanCount();++i) {
        /* Native addresses may end at 2^64; compare offsets in the region. */
        if((i<lower_count_)==!upper && iova<=ranges_[i].iova+(ranges_[i].bytes-1) &&
            ranges_[i].iova<=iova+(memory->bytes()-1))return kIOReturnBusy;
    }
    if(a->config.output_bits<32 || a->config.output_bits>48)return kIOReturnBadArgument;
    uint64_t offset=0,limit=UINT64_C(1)<<a->config.output_bits;
    for(size_t j=0;j<memory->spanCount();++j) {
        const auto &span=memory->spans()[j];
        if(span.offset!=offset || !span.physical || !span.bytes || ((span.physical|span.bytes)&4095) ||
            span.bytes>memory->bytes()-offset || span.physical>=limit || span.bytes>limit-span.physical)
            return kIOReturnBadArgument;
        for(const auto &r:regions_)if(r.arena && r.tables->overlaps(span.physical,span.bytes))return kIOReturnBadArgument;
        offset+=span.bytes;
    }
    if(offset!=memory->bytes())return kIOReturnBadArgument;
    /* Only another cache/shareability/privilege class can conflict. Reuse the
     * arena's caller-owned temporary alias scratch before the table transaction
     * uses it. Index the smaller side and query the other in O(log n); neither
     * the resource spans nor the actual page tables are modified here. */
    const unsigned mine=aliasClass(permissions,writeback,shareability);
    size_t other=0;
    for(size_t i=0;i<spanCount();++i)
        if(aliasClass(ranges_[i].permissions,ranges_[i].writeback,ranges_[i].shareability)!=mine)++other;
    if(!other)return kIOReturnSuccess;
    const bool indexNew=memory->spanCount()<=other;
    const size_t smaller=indexNew?memory->spanCount():other;
    uint32_t *order=alias_scratch_?alias_scratch_:a->alias_scratch;
    const size_t scratch_entries=alias_scratch_?capacity_:a->alias_scratch_entries;
    if(order && smaller<=scratch_entries) {
        __atomic_fetch_add(&zorn_direct_vm_alias_paths[0],1ull,__ATOMIC_RELAXED);
        if(indexNew) {
            for(size_t i=0;i<smaller;++i)order[i]=(uint32_t)i;
            NativeAdrenoPhysicalIndex index(memory->spans(),order,smaller);
            for(size_t i=0;i<spanCount();++i) {
                const auto &r=ranges_[i];
                if(aliasClass(r.permissions,r.writeback,r.shareability)!=mine && index.overlaps(r.physical,r.bytes))return kIOReturnBadArgument;
            }
        } else {
            size_t n=0;
            for(size_t i=0;i<spanCount();++i)
                if(aliasClass(ranges_[i].permissions,ranges_[i].writeback,ranges_[i].shareability)!=mine)order[n++]=(uint32_t)i;
            NativeAdrenoPhysicalIndex index(ranges_,order,n);
            for(size_t j=0;j<memory->spanCount();++j)
                if(index.overlaps(memory->spans()[j].physical,memory->spans()[j].bytes))return kIOReturnBadArgument;
        }
        return kIOReturnSuccess;
    }
    /* Small/unconfigured callers retain the conservative allocation-free path. */
    __atomic_fetch_add(&zorn_direct_vm_alias_paths[1],1ull,__ATOMIC_RELAXED);
    for(size_t i=0;i<spanCount();++i) {
        const ZornSmmuSparse4KRange &r=ranges_[i];
        if(aliasClass(r.permissions,r.writeback,r.shareability)==mine)continue;
        for(size_t j=0;j<memory->spanCount();++j)
            if(overlap(memory->spans()[j].physical,memory->spans()[j].bytes,r.physical,r.bytes))return kIOReturnBadArgument;
    }
    return kIOReturnSuccess;
}
ZornGen7DirectVm26::Mapping *ZornGen7DirectVm26::find(uint64_t handle)
{if(handle && mappings_)for(size_t i=0;i<ZornGen7DirectVm26MaxObjects;++i)if(mappings_[i].handle==handle && mappings_[i].memory)return &mappings_[i];return nullptr;}
/* The n ranges just past the table's end (one mapping's spans, consecutive in IOVA and all in one gap) take their sorted place. */
void ZornGen7DirectVm26::insert(size_t n,unsigned upper)
{
    const size_t count=spanCount();
    size_t at=0;while(at<count && ranges_[at].iova<ranges_[count].iova)++at;
    reverse(ranges_+at,ranges_+count);reverse(ranges_+count,ranges_+count+n);reverse(ranges_+at,ranges_+count+n);
    if(upper)upper_count_+=n;else lower_count_+=n;
}
void ZornGen7DirectVm26::erase(size_t at,size_t n,unsigned upper)
{
    const size_t count=spanCount();
    memmove(ranges_+at,ranges_+at+n,(count-at-n)*sizeof(*ranges_));
    if(upper)upper_count_-=n;else lower_count_-=n;
}
IOReturn ZornGen7DirectVm26::map(NativeAdrenoMemory *memory,unsigned upper,uint64_t iova,
    unsigned permissions,unsigned writeback,unsigned shareability,uint64_t *handle)
{
    if(!handle)return kIOReturnBadArgument;*handle=0;result_={};
    if(!attached_ || poisoned_)return kIOReturnNotReady;
    // A new mapping also changes live page tables. Refuse while any submitted
    // job still owns the VM namespace; the host owner drains and retries.
    if(submission_resources_)return kIOReturnBusy;
    PhaseClock clock;
    IOReturn checked=preflight(memory,upper,iova,permissions,writeback,shareability);if(checked)return checked;
    if(next_handle_==UINT64_MAX)return kIOReturnNoResources;
    clock.lap(0,5); /* Previously omitted preflight; map slot 5 was unused. */
    ZornSmmuSparse4KStatus status=observeCheap();if(status)return fail(status);
    clock.lap(0,1);
    checked=memory->holdForDevice();if(checked)return checked;
    Mapping *record=nullptr;for(size_t i=0;i<ZornGen7DirectVm26MaxObjects;++i)if(!mappings_[i].memory){record=&mappings_[i];break;}
    if(!record) {memory->quarantine();return fail(ZornSmmuSparse4KStateMismatch);}
    *record={memory,0,iova,memory->spanCount(),0,permissions,writeback,shareability,0};++objects_;
    if(coherentMapping(writeback,shareability))zorn_direct_coherent_skips[0]=zorn_direct_coherent_skips[0]+1;
    else {
        checked=memory->publishForDevice(0,memory->bytes(),permissions&ZornSmmuSparse4KWrite,distrust_write_combined_);
        if(checked)return fail(ZornSmmuSparse4KIoError);
    }
    clock.lap(0,2);
    /* Every span in one table transaction, staged in the table's free tail (preflight checked the room). */
    const size_t spans=record->spans;
    ZornSmmuSparse4KRange *changes=ranges_+spanCount();
    for(size_t i=0;i<spans;++i) {
        const auto &span=memory->spans()[i];
        changes[i]={iova+span.offset,span.physical,span.bytes,permissions,writeback,shareability};
    }
    ZornSmmuSparse4KLiveArena views[2]{};
    ZornSmmuSparse4KLiveRegion lower=region(0,views[0]),high=region(1,views[1]);ZornSmmuSparse4KLiveResult update;
    status=streams_->haltForTableUpdate(streams_->cookie);
    if(status)return fail(status);
    status=ZornSmmuSparse4KLiveUpdateContextBatch(&io_,streams_->bank,context_,lower.arena?&lower:nullptr,
        high.arena?&high:nullptr,upper,&visibility_[upper],changes,spans,1,budget_,&update);
    if(status)return fail(status);
    status=streams_->releaseAfterTableUpdate(streams_->cookie);
    if(status)return fail(status);
    clock.lap(0,3);
    insert(spans,upper);record->mapped_spans=spans;result_.completed_spans=spans;
    clock.lap(0,4);clock.done(0,memory->bytes());
    record->handle=next_handle_++;*handle=record->handle;result_.complete=true;return kIOReturnSuccess;
}
IOReturn ZornGen7DirectVm26::unmap(uint64_t handle)
{
    native_adreno_trace_stage=10;
    result_={};if(!attached_ || poisoned_)return kIOReturnNotReady;
    Mapping *record=find(handle);if(!record)return kIOReturnBadArgument;
    if(record->jobs || submission_resources_)return kIOReturnBusy;
    PhaseClock clock;
    ZornSmmuSparse4KStatus status=observeCheap();
    native_adreno_trace_stage=11;
    if(status)return fail(status);
    clock.lap(1,1);
    unsigned upper=regions_[1].arena && record->iova>=regions_[1].arena->iova;
    if(coherentMapping(record->writeback,record->shareability))zorn_direct_coherent_skips[1]=zorn_direct_coherent_skips[1]+1;
    else if(record->permissions&ZornSmmuSparse4KWrite) {
        if(record->memory->acquireDeviceWrites(0,record->memory->bytes())!=kIOReturnSuccess)
            return fail(ZornSmmuSparse4KIoError);
    }
    clock.lap(1,2);
    /* The mapping's spans are consecutive in the table; unmap them in one transaction. */
    const size_t spans=record->spans;
    size_t at=0;while(at<spanCount() && ranges_[at].iova!=record->iova)++at;
    if(spans>spanCount()-at)return fail(ZornSmmuSparse4KStateMismatch);
    for(size_t i=0;i<spans;++i) {
        const auto &span=record->memory->spans()[i];
        const ZornSmmuSparse4KRange &r=ranges_[at+i];
        if(r.iova!=record->iova+span.offset || r.physical!=span.physical || r.bytes!=span.bytes ||
            r.permissions!=record->permissions || r.writeback!=record->writeback || r.shareability!=record->shareability)
            return fail(ZornSmmuSparse4KStateMismatch);
    }
    ZornSmmuSparse4KLiveArena views[2]{};
    ZornSmmuSparse4KLiveRegion lower=region(0,views[0]),high=region(1,views[1]);ZornSmmuSparse4KLiveResult update;
    native_adreno_trace_stage=12;
    status=streams_->haltForTableUpdate(streams_->cookie);
    if(status)return fail(status);
    if(per_page_tlb_invalidation_)
        status=ZornSmmuSparse4KLiveUpdateContextBatch(&io_,streams_->bank,context_,lower.arena?&lower:nullptr,
            high.arena?&high:nullptr,upper,&visibility_[upper],ranges_+at,spans,0,budget_,&update);
    else
        status=ZornSmmuSparse4KLiveUnmapContextBatchAsid(&io_,streams_->bank,context_,lower.arena?&lower:nullptr,
            high.arena?&high:nullptr,upper,&visibility_[upper],ranges_+at,spans,budget_,&update);
    native_adreno_trace_stage=13;
    if(status)return fail(status);
    status=streams_->releaseAfterTableUpdate(streams_->cookie);
    if(status)return fail(status);
    clock.lap(1,3);
    erase(at,spans,upper);record->mapped_spans=0;result_.completed_spans=spans;
    native_adreno_trace_stage=14;
    clock.lap(1,4);
    if(record->memory->retireAfterQuiescence()!=kIOReturnSuccess)return fail(ZornSmmuSparse4KStateMismatch);
    clock.lap(1,5);clock.done(1,record->memory->bytes());
    *record={};--objects_;result_.complete=true;return kIOReturnSuccess;
}
IOReturn ZornGen7DirectVm26::describe(uint64_t handle,uint64_t *iova,size_t *bytes,
    unsigned *permissions) const
{
    if(!iova || !bytes || !permissions)return kIOReturnBadArgument;
    *iova=0;*bytes=0;*permissions=0;
    if(!attached_ || poisoned_)return kIOReturnNotReady;
    for(size_t m=0;mappings_ && m<ZornGen7DirectVm26MaxObjects;++m)if(mappings_[m].handle==handle && mappings_[m].memory) {
        const Mapping &mapping=mappings_[m];
        *iova=mapping.iova;*bytes=mapping.memory->bytes();*permissions=mapping.permissions;
        return mapping.mapped_spans==mapping.spans?kIOReturnSuccess:kIOReturnNotReady;
    }
    return kIOReturnBadArgument;
}
/* Explicit TLBIALL of the bank. Where a table update has observed the bank's image (each region's whole-verification
 * update remembers its register offset), the invalidation alone: the image and faults were observed there and every 64th table
 * operation since (int-159: a submission spent 1.3 ms in the kernel, most of it reading SMMU registers). */
IOReturn ZornGen7DirectVm26::invalidateTlb()
{
    if(!attached_ || poisoned_)return kIOReturnNotReady;
    ZornSmmuSparse4KProgramResult r;
    uint64_t offset=0;
    for(const auto &region:regions_)if(region.state && region.state->context_offset)offset=region.state->context_offset;
    const ZornSmmuSparse4KStatus status=offset?ZornSmmuSparse4KSyncContextTlb(&io_,offset,context_->asid,1,budget_,&r):
        ZornSmmuSparse4KInvalidateAllOwnedContext(&io_,streams_->bank,context_,budget_,&r);
    return status?fail(status):kIOReturnSuccess;
}
IOReturn ZornGen7DirectVm26::publishMapped()
{
    if(!attached_ || poisoned_)return kIOReturnNotReady;
    for(size_t i=0;i<ZornGen7DirectVm26MaxObjects;++i) {
        const Mapping &m=mappings_[i];
        if(!m.memory)continue;
        if(coherentMapping(m.writeback,m.shareability)) {zorn_direct_coherent_skips[2]=zorn_direct_coherent_skips[2]+1;continue;}
        if(m.memory->publishForDevice(0,m.memory->bytes(),true,distrust_write_combined_))return fail(ZornSmmuSparse4KIoError);
    }
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectVm26::acquireImported()
{
    if(!attached_ || poisoned_)return kIOReturnNotReady;
    for(size_t i=0;i<ZornGen7DirectVm26MaxObjects;++i) {
        const Mapping &m=mappings_[i];
        if(!m.memory || !m.memory->imported() || !(m.permissions&ZornSmmuSparse4KWrite))continue;
        if(coherentMapping(m.writeback,m.shareability)) {zorn_direct_coherent_skips[3]=zorn_direct_coherent_skips[3]+1;continue;}
        if(m.memory->acquireDeviceWrites(0,m.memory->bytes()))return fail(ZornSmmuSparse4KIoError);
    }
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectVm26::sampleWord(uint64_t iova,uint32_t *cached,uint32_t *dram) const
{
    if(!cached || !dram)return kIOReturnBadArgument;
    *cached=*dram=~0u;
    if(!attached_ || poisoned_)return kIOReturnNotReady;
    if(iova&3)return kIOReturnBadArgument;
    for(size_t i=0;i<ZornGen7DirectVm26MaxObjects;++i) {
        const Mapping &m=mappings_[i];
        if(!m.memory || iova<m.iova || iova-m.iova>=m.memory->bytes())continue;
        const size_t offset=(size_t)(iova-m.iova);
        if(m.memory->mapping())*cached=static_cast<const volatile uint32_t *>(m.memory->mapping())[offset/4];
        for(size_t j=0;j<m.memory->spanCount();++j) {
            const auto &span=m.memory->spans()[j];
            if(offset<span.offset || offset-span.offset>=span.bytes)continue;
            uint32_t value=0;
            /* DRAM first: the cached reader writes its line back, so read after it DRAM would always agree (int-099). */
            if(zorn_direct_dram_read32 && !zorn_direct_dram_read32(span.physical+(offset-span.offset),&value))*dram=value;
            /* A write-combined BO's own mapping is non-cacheable: read the cacheable alias instead, so a dirty line is still seen. */
            if(zorn_direct_cached_read32 && !zorn_direct_cached_read32(span.physical+(offset-span.offset),&value))*cached=value;
            break;
        }
        return kIOReturnSuccess;
    }
    return kIOReturnBadArgument;
}
IOReturn ZornGen7DirectVm26::reassertWriteCombined(uint32_t *reset) const
{
    if(!reset)return kIOReturnBadArgument;
    if(!attached_ || poisoned_)return kIOReturnNotReady;
    for(size_t i=0;i<ZornGen7DirectVm26MaxObjects;++i) {
        const Mapping &m=mappings_[i];
        if(!m.memory)continue;
        const IOReturn status=m.memory->reassertWriteCombined(reset);
        if(status) {m.memory->quarantine();return status;}
    }
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectVm26::auditRange(uint64_t iova,size_t bytes,uint32_t *lines,uint32_t *dirty,uint32_t *stale) const
{
    if(!lines || !dirty || !stale)return kIOReturnBadArgument;
    if(!attached_ || poisoned_)return kIOReturnNotReady;
    if(!zorn_direct_line_audit)return kIOReturnUnsupported;
    if(!bytes || iova>UINT64_MAX-bytes)return kIOReturnBadArgument;
    for(size_t i=0;i<ZornGen7DirectVm26MaxObjects;++i) {
        const Mapping &m=mappings_[i];
        if(!m.memory || iova<m.iova || iova-m.iova>=m.memory->bytes())continue;
        if(!m.memory->writeCombined())return kIOReturnSuccess;   /* maintained before every submission anyway */
        /* Whole lines; the range is clipped to its BO. */
        size_t at=(size_t)(iova-m.iova)&~(size_t)63;
        const size_t end=(size_t)(iova-m.iova)+bytes>m.memory->bytes()?m.memory->bytes():(size_t)(iova-m.iova)+bytes;
        while(at<end) {
            const NativeAdrenoPhysicalSpan *span=nullptr;
            for(size_t j=0;j<m.memory->spanCount();++j) {
                const auto &s=m.memory->spans()[j];
                if(at>=s.offset && at-s.offset<s.bytes) {span=&s;break;}
            }
            if(!span)return kIOReturnBadArgument;
            const uint64_t physical=span->physical+(at-span->offset);
            size_t chunk=4096-(size_t)(physical&4095);
            if(chunk>span->offset+span->bytes-at)chunk=span->offset+span->bytes-at;
            if(chunk>end-at)chunk=(end-at+63)&~(size_t)63;
            if(zorn_direct_line_audit(physical,chunk,dirty,stale))return kIOReturnIOError;
            *lines+=(uint32_t)(chunk/64);at+=chunk;
        }
        return kIOReturnSuccess;
    }
    return kIOReturnBadArgument;
}
IOReturn ZornGen7DirectVm26::peekWords(uint64_t iova,uint32_t *out,size_t count) const
{
    if(!out || !attached_ || poisoned_)return kIOReturnBadArgument;
    for(size_t k=0;k<count;++k)out[k]=0;
    for(size_t i=0;i<ZornGen7DirectVm26MaxObjects;++i) {
        const Mapping &m=mappings_[i];
        if(!m.memory || !m.memory->mapping() || iova<m.iova || iova-m.iova>=m.memory->bytes())continue;
        const size_t offset=(size_t)(iova-m.iova);
        for(size_t k=0;k<count && offset+4*k+4<=m.memory->bytes();++k)out[k]=static_cast<const volatile uint32_t *>(m.memory->mapping())[offset/4+k];
        return kIOReturnSuccess;
    }
    return kIOReturnBadArgument;
}
// Called only by the serialized submit owner. These count owned submission
// references; no count is a fence, quiescence or a hardware permission.
IOReturn ZornGen7DirectVm26::holdSubmissionResources()
{
    if(!attached_ || poisoned_)return kIOReturnNotReady;
    if(submission_resources_==UINT32_MAX)return kIOReturnNoResources;
    ++submission_resources_;return kIOReturnSuccess;
}
IOReturn ZornGen7DirectVm26::cancelUnpublishedSubmissionResources()
{
    // Only the new reference of a job known not to have reached the ring is
    // cancelled. Older jobs keep their own namespace references unchanged.
    if(!attached_ || poisoned_ || !submission_resources_)return kIOReturnNotReady;
    --submission_resources_;return kIOReturnSuccess;
}
IOReturn ZornGen7DirectVm26::retireSubmissionResourcesAfterCompletion()
{
    // The submit owner first observes this job's real fence, retires its IB
    // references and acquires GPU-written imports. Any failure retains this.
    if(!attached_ || poisoned_ || !submission_resources_)return kIOReturnNotReady;
    --submission_resources_;return kIOReturnSuccess;
}
IOReturn ZornGen7DirectVm26::holdJob(uint64_t handle)
{
    if(!attached_ || poisoned_)return kIOReturnNotReady;
    Mapping *record=find(handle);if(!record)return kIOReturnBadArgument;
    if(record->jobs==UINT32_MAX)return kIOReturnNoResources;
    IOReturn status=record->memory->holdForDevice();if(status)return status;
    ++record->jobs;return kIOReturnSuccess;
}
IOReturn ZornGen7DirectVm26::retireJobAfterCompletion(uint64_t handle)
{
    if(!attached_ || poisoned_)return kIOReturnNotReady;
    Mapping *record=find(handle);if(!record || !record->jobs)return kIOReturnBadArgument;
    IOReturn status=record->memory->retireAfterQuiescence();if(status)return status;
    --record->jobs;return kIOReturnSuccess;
}

IOReturn ZornGen7DirectVm26::detachSeeded(const ZornSmmuSparse4KRange *lower,size_t lower_count,
    const ZornSmmuSparse4KRange *upper,size_t upper_count)
{
    if(!attached_ || poisoned_ || objects_ || submission_resources_)return kIOReturnBusy;
    if(lower_count!=lower_count_ || upper_count!=upper_count_ ||
       (lower_count && !lower) || (upper_count && !upper))return kIOReturnBadArgument;
    auto same=[](const ZornSmmuSparse4KRange &a,const ZornSmmuSparse4KRange &b){
        return a.iova==b.iova && a.physical==b.physical && a.bytes==b.bytes &&
            a.permissions==b.permissions && a.writeback==b.writeback && a.shareability==b.shareability;};
    for(size_t i=0;i<lower_count;++i)if(!same(ranges_[i],lower[i]))return kIOReturnNotReady;
    for(size_t i=0;i<upper_count;++i)if(!same(ranges_[lower_count+i],upper[i]))return kIOReturnNotReady;
    const auto status=observe();if(status)return fail(status);
    // No live Mapping owns a BO reference. Free only CPU mapper metadata;
    // seed backing/table lifetime belongs to the parent and actual creator.
    freeMetadata();attached_=false;return kIOReturnSuccess;
}

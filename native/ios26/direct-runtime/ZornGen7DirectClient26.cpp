/* SPDX-License-Identifier: MIT */
#include "ZornGen7DirectClient26.h"
#include "NativeAdrenoCoherencePolicy.h"
#include "HoujiGpuClientLayout.h"
extern "C" volatile uint32_t native_adreno_trace_stage;
/* 0 keeps user BOs cacheable and maintained before every submission (int-070..097); the board sets it from the sheng-gpu-wc boot argument. */
extern "C" {volatile uint32_t zorn_direct_wc_enabled=1;}
/* BoImport record: [0] calls, [1] refused, [2..5] last refusal (status, stage, bytes, address), [6..9] first refusal. Stages 1..3 are this file's
 * checks, 10..19 NativeAdrenoMemory::importTask's. */
extern "C" {volatile uint64_t zorn_direct_import_diag[10];}
extern "C" volatile uint32_t native_adreno_import_stage;
/* Imports and their release (int-233/234: Core Animation's render thread waited in vm_deallocate for pages a kernel wiring held): [0] imports
 * alive, [1] frees of an import refused, [2] last refusal status; then the 8 newest imports as {address, pid<<40|bytes, handle, state}, state
 * 1 alive, 2 released, 3 free refused. */
extern "C" {volatile uint64_t zorn_direct_import_live[3+8*4];}
extern "C" int proc_selfpid(void);
static unsigned gImportNext;
static void noteImportState(uint64_t handle,uint64_t state)
{
    for(unsigned i=0;i<8;++i)if(zorn_direct_import_live[3+i*4+2]==handle) {zorn_direct_import_live[3+i*4+3]=state;return;}
}
extern "C" volatile uint32_t zorn_direct_io_coherent;
extern "C" volatile uint32_t zorn_direct_coherent_import_fallbacks;
/* Per kernel method: [method][0] calls, [1] calls that returned non-zero, [2] last status, [3] total time (us, 32-bit). Method numbers are the ABI's (1..16). */
extern "C" {volatile uint32_t zorn_direct_method_stats[20][4];volatile uint32_t zorn_direct_map_fail[7][2];}
static void noteImport(IOReturn status,uint32_t stage,uint64_t bytes,uint64_t address)
{
    if(!status)return;
    zorn_direct_import_diag[1]=zorn_direct_import_diag[1]+1;
    zorn_direct_import_diag[2]=(uint32_t)status;zorn_direct_import_diag[3]=stage;zorn_direct_import_diag[4]=bytes;zorn_direct_import_diag[5]=address;
    if(zorn_direct_import_diag[1]==1) {
        zorn_direct_import_diag[6]=(uint32_t)status;zorn_direct_import_diag[7]=stage;zorn_direct_import_diag[8]=bytes;zorn_direct_import_diag[9]=address;
    }
}
#include <IOKit/IOLib.h>
#include <string.h>
extern "C" {volatile uint32_t zorn_direct_window_overflow[NativeAdrenoMaxClients][3];}   /* {count, last size KiB, last end MiB} per client window */
ZornGen7DirectClient26::Entry *ZornGen7DirectClient26::find(uint64_t handle)
{
    const uint32_t index=entries_?index_.find(handle):UINT32_MAX;
    if(index>=entry_count_)return nullptr;
    Entry &entry=entries_[index];
    return entry.used && entry.handle==handle?&entry:nullptr;
}
void ZornGen7DirectClient26::publish(Entry &entry)
{
    entry.used=true;entry.handle=next_handle_++;entry.token=(uint32_t)(&entry-entries_)+1;++live_;
    index_.insert(entry.handle,(uint32_t)(&entry-entries_));
}
void ZornGen7DirectClient26::clear(Entry &entry)
{
    if(entry.used && live_)--live_;
    index_.erase(entry.handle);
    const size_t index=(size_t)(&entry-entries_);if(index<free_hint_)free_hint_=index;
    entry.handle=0;entry.mapped=0;entry.iova=0;entry.used=false;
    entry.mapped_state=false;entry.unreleasable=false;entry.imported=false;entry.metadata_bytes=0;
    entry.token=0;entry.mapping_leases=0;
}
ZornGen7DirectClient26::Entry *ZornGen7DirectClient26::free()
{
    for(size_t i=free_hint_;i<entry_count_;++i)if(!entries_[i].used) {free_hint_=i;return &entries_[i];}
    return nullptr;
}
size_t ZornGen7DirectClient26::liveObjects() const
{
    return live_;
}
bool ZornGen7DirectClient26::mapped(uint64_t handle)
{
    Entry *entry=find(handle);return entry && entry->mapped_state;
}
NativeAdrenoMemory *ZornGen7DirectClient26::memoryOf(uint64_t handle)
{
    Entry *entry=find(handle);return entry && !entry->unreleasable?&entry->memory:nullptr;
}
IOReturn ZornGen7DirectClient26::open(uint32_t abi_version,ZornGen7DirectVm26 *vm,
    ZornGen7DirectSubmit26 *submit,NativeAdrenoRing *ring,uint32_t input_bits,uint32_t output_bits,bool qualified_existing_context)
{
    if(open_ || vm_ || submit_)return kIOReturnBusy;
    if(abi_version!=NativeAdrenoAbiVersion)return kIOReturnUnsupported;
    if(!vm || !submit || !ring || input_bits<31 || input_bits>48 ||
        output_bits<32 || output_bits>48 || vm->poisoned() || submit->poisoned() ||
        ring->poisoned())return kIOReturnBadArgument;
    entries_=IONewData(Entry,ZornGen7DirectClient26MaxObjects);
    if(!entries_)return kIOReturnNoMemory;
    memset(entries_,0,sizeof(Entry)*ZornGen7DirectClient26MaxObjects);
    if(!index_.allocate()) {IODeleteData(entries_,Entry,ZornGen7DirectClient26MaxObjects);return kIOReturnNoMemory;}
    entry_count_=ZornGen7DirectClient26MaxObjects;free_hint_=0;live_=0;
    vm_=vm;submit_=submit;ring_=ring;input_bits_=input_bits;output_bits_=output_bits;
    next_handle_=1;open_=true;
    queues_[0]={0,true};
    /* Each client is a new GPU context for the CP: its first submission clears the BR/BV synchronization state. */
    if(!qualified_existing_context)ring_->requestContextReset();
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectClient26::setScope(uint32_t queue_base,uint64_t window_start,uint64_t window_bytes)
{
    if(!open_)return kIOReturnNotReady;
    if(queue_base%NativeAdrenoAbiMaxQueues || queue_base>UINT32_MAX-NativeAdrenoAbiMaxQueues || (window_start&4095) || (window_bytes&4095) ||
        (window_bytes && (window_start+window_bytes<window_start || window_start+window_bytes>(UINT64_C(1)<<input_bits_))))
        return kIOReturnBadArgument;
    /* A client that owns no range yet has none to drain: its queue_base_ is the default 0, the render server's range, and the render server
     * nearly always has a job in flight, so every other process was refused here with kIOReturnBusy (int-200: WidgetRenderer_Default). */
    if(liveObjects() || ownRangeOutstanding() || submit_->rangeOutstanding(queue_base,NativeAdrenoAbiMaxQueues))return kIOReturnBusy;
    queue_base_=queue_base;scoped_=true;window_start_=window_start;window_bytes_=window_bytes;window_peak_=0;
    return kIOReturnSuccess;
}
bool ZornGen7DirectClient26::ownRangeOutstanding() const
{
    return (scoped_ || used_) && submit_->rangeOutstanding(queue_base_,NativeAdrenoAbiMaxQueues);
}
IOReturn ZornGen7DirectClient26::close()
{
    if(!open_)return kIOReturnNotReady;
    if(liveObjects() || ownRangeOutstanding())return kIOReturnBusy;
    for(size_t i=1;i<NativeAdrenoAbiMaxQueues;++i)if(queues_[i].active)return kIOReturnBusy;
    index_.release();IODeleteData(entries_,Entry,entry_count_);entries_=nullptr;entry_count_=0;free_hint_=live_=0;
    queue_base_=0;scoped_=used_=false;window_start_=window_bytes_=window_peak_=0;
    open_=false;for(auto &queue:queues_)queue=Queue{};vm_=nullptr;submit_=nullptr;ring_=nullptr;timer_=nullptr;status_=nullptr;info_=nullptr;
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectClient26::releaseAll(const NativeAdrenoRingClock *clock,uint32_t timeout_us)
{
    if(!open_)return kIOReturnNotReady;
    if(!clock)return kIOReturnBadArgument;
    IOReturn status=(scoped_ || used_)?submit_->waitRange(queue_base_,NativeAdrenoAbiMaxQueues,clock,timeout_us):kIOReturnSuccess;
    if(status)return status;
    for(size_t index=0;index<entry_count_;++index) {
        Entry &entry=entries_[index];
        if(!entry.used)continue;
        entry.mapping_leases=0;
        NativeAdrenoAbiBoFree request{entry.handle};
        status=freeBo(&request);
        if(status)return status;
    }
    for(size_t i=1;i<NativeAdrenoAbiMaxQueues;++i)queues_[i]=Queue{};
    return close();
}
NativeAdrenoMemory *ZornGen7DirectClient26::memoryForToken(uint32_t token)
{
    if(!open_ || !token || token>entry_count_)return nullptr;
    Entry &entry=entries_[token-1];
    return entry.used && !entry.unreleasable && entry.token==token && entry.mapping_leases?&entry.memory:nullptr;
}
uint32_t ZornGen7DirectClient26::mappingLeases(uint32_t token) const
{
    if(!open_ || !token || token>entry_count_)return 0;
    const Entry &entry=entries_[token-1];
    return entry.used && entry.token==token?entry.mapping_leases:0;
}
IOReturn ZornGen7DirectClient26::query(NativeAdrenoAbiParams *params)
{
    if(!params)return kIOReturnBadArgument;
    *params={};
    if(!open_)return kIOReturnNotReady;
    params->abi_version=NativeAdrenoAbiVersion;
    params->input_bits=input_bits_;params->output_bits=output_bits_;
    params->flags=NativeAdrenoParamsHostImport|NativeAdrenoParamsSubmitBatch;params->max_bo_bytes=UINT64_C(1)<<NativeAdrenoAbiMaxBoBytesShift;
    return kIOReturnSuccess;
}
/* Per client slot (kernel's own client last): [0] live objects now, [1] their peak, [2] refused BoAllocs, [3] last refusal status,
 * [4] bytes of the last refused request, [5] the window's highest mapped end in MiB above its start. Turnip turns any refusal into
 * VK_ERROR_OUT_OF_DEVICE_MEMORY, which its command streams do not check (int-237: backboardd wrote through a NULL stream pointer). */
extern "C" {volatile uint32_t zorn_direct_client_stats[NativeAdrenoMaxClients+1][6];}
static volatile uint32_t *clientStats(uint32_t queue_base,uint64_t window_bytes) {
    const uint32_t slot=window_bytes?queue_base/NativeAdrenoAbiMaxQueues:NativeAdrenoMaxClients;
    return zorn_direct_client_stats[slot<NativeAdrenoMaxClients?slot:NativeAdrenoMaxClients];
}
static void noteLive(uint32_t queue_base,uint64_t window_bytes,size_t live) {
    volatile uint32_t *stats=clientStats(queue_base,window_bytes);
    stats[0]=(uint32_t)live;if(live>stats[1])stats[1]=(uint32_t)live;
}
IOReturn ZornGen7DirectClient26::allocBo(const NativeAdrenoAbiBoAlloc *request,
    NativeAdrenoAbiBoAllocReply *reply)
{
    const IOReturn status=allocBoInner(request,reply);
    if(status && request) {
        volatile uint32_t *stats=clientStats(queue_base_,window_bytes_);
        stats[2]=stats[2]+1;stats[3]=(uint32_t)status;stats[4]=(uint32_t)request->bytes;
    }
    if(entries_)noteLive(queue_base_,window_bytes_,liveObjects());
    return status;
}
IOReturn ZornGen7DirectClient26::allocBoInner(const NativeAdrenoAbiBoAlloc *request,
    NativeAdrenoAbiBoAllocReply *reply)
{
    if(!request || !reply)return kIOReturnBadArgument;reply->handle=0;
    if(!open_)return kIOReturnNotReady;
    const uint64_t limit=UINT64_C(1)<<NativeAdrenoAbiMaxBoBytesShift;
    if(!request->bytes || (request->bytes&4095) || request->bytes>limit ||
        request->align_log2<12 || request->align_log2>24 || request->contiguous>1)
        return kIOReturnBadArgument;
    /* Never wrap to zero or reuse a stale handle within this connection. */
    if(!next_handle_)return kIOReturnNoResources;
    Entry *entry=free();
    if(!entry)return kIOReturnNoResources;
    /* Adreno740 9e21f6a: the pool already supplies contiguous runs. Once it
     * fills, do not scan XNU physical memory for another optional large run
     * under the issuer lock; use scattered pages and the existing SMMU checks.
     * r273's failed 64 MiB searches overlapped its longest completion waits.
     * Explicit contiguity requests and the legacy no-pool path remain intact. */
    IOReturn status=kIOReturnUnsupported;
    const size_t backing_budget=NativeAdrenoMemory::backingBudget((size_t)request->bytes);
    if(!backing_budget)return kIOReturnUnsupported;
    const bool prefer_contiguous=request->contiguous==0 && request->bytes>=ZornGen7DirectClient26ContiguousFirstBytes &&
        !NativeAdrenoMemory::poolBytes();
    if(prefer_contiguous) {
        status=entry->memory.allocate((size_t)request->bytes,output_bits_,true,backing_budget,true);
        if(status && !entry->memory.quarantined() && entry->memory.release()==kIOReturnSuccess)status=kIOReturnUnsupported;
    }
    if(status)
        status=entry->memory.allocate((size_t)request->bytes,output_bits_,request->contiguous!=0,backing_budget,true);
    /* User BOs are write-combined for the CPU, as the GPU maps them non-cacheable: no per-submission cache maintenance.
     * int-147 kept them cacheable under IO coherence and mapped the GPU side write-back: the first Turnip IB executed zeros and the GPU hung
     * (the kernel's cacheable alias read zeros past the first line too). Turnip maps every BO asking kIOMapWriteCombineCache, the user's
     * cache bits replace the kernel's (IOUserClient::mapClientMemory64), and XNU's view machinery changes the page attribute to match, so
     * the aliases disagreed. A coherent own BO needs a client that asks for a write-back view. */
    if(!status && zorn_direct_wc_enabled)status=entry->memory.makeWriteCombined();
    if(status) {
        /* A failed allocation can leave quarantine behind; never reuse it. */
        clear(*entry);
        if(entry->memory.release()!=kIOReturnSuccess) {
            entry->used=true;entry->unreleasable=true;++live_;
        }
        return status==kIOReturnUnsupported?kIOReturnUnsupported:status;
    }
    publish(*entry);
    entry->mapped=0;entry->iova=0;entry->mapped_state=false;
    reply->handle=entry->handle;
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectClient26::importBo(const NativeAdrenoAbiBoImport *request,void *task,
    NativeAdrenoAbiBoAllocReply *reply)
{
    if(!request || !reply)return kIOReturnBadArgument;reply->handle=0;
    if(!open_)return kIOReturnNotReady;
    zorn_direct_import_diag[0]=zorn_direct_import_diag[0]+1;
    const uint64_t limit=UINT64_C(1)<<NativeAdrenoAbiMaxBoBytesShift;
    if(!task || !request->address || ((request->address|request->bytes)&4095) || !request->bytes || request->bytes>limit) {
        noteImport(kIOReturnBadArgument,1,request->bytes,request->address);
        return kIOReturnBadArgument;
    }
    if(!next_handle_) {noteImport(kIOReturnNoResources,2,request->bytes,request->address);return kIOReturnNoResources;}
    Entry *entry=free();
    if(!entry) {noteImport(kIOReturnNoResources,2,request->bytes,request->address);return kIOReturnNoResources;}
    const IOReturn status=entry->memory.importTask(task,request->address,(size_t)request->bytes,output_bits_,(size_t)request->bytes);
    if(status) {
        noteImport(status,native_adreno_import_stage,request->bytes,request->address);
        clear(*entry);
        if(entry->memory.release()!=kIOReturnSuccess) {entry->used=true;entry->unreleasable=true;++live_;}
        return status;
    }
    publish(*entry);
    entry->mapped=0;entry->iova=0;entry->mapped_state=false;entry->imported=true;
    reply->handle=entry->handle;
    zorn_direct_import_live[0]=zorn_direct_import_live[0]+1;
    {
        const unsigned slot=3+(gImportNext++%8)*4;
        zorn_direct_import_live[slot]=request->address;zorn_direct_import_live[slot+1]=(uint64_t)proc_selfpid()<<40|request->bytes;
        zorn_direct_import_live[slot+2]=entry->handle;zorn_direct_import_live[slot+3]=1;
    }
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectClient26::mapBo(const NativeAdrenoAbiBoMap *request,
    NativeAdrenoAbiBoMapReply *reply)
{
    if(!request || !reply)return kIOReturnBadArgument;reply->iova=0;
    if(!open_)return kIOReturnNotReady;
    if(!(request->permissions&1) || (request->permissions&~3u) || request->writeback>1 ||
        (request->shareability!=2 && request->shareability!=3) || request->reserved ||
        (request->iova&4095))return kIOReturnBadArgument;
    Entry *entry=find(request->handle);
    if(!entry || entry->unreleasable)return kIOReturnBadArgument;
    if(entry->mapped_state)return kIOReturnBusy;
    const uint64_t end=request->iova+entry->memory.bytes();
    if(window_bytes_ && (request->iova<window_start_ || end<request->iova || end>window_start_+window_bytes_)) {
        /* Per window: how often a mapping fell outside it, and the last one's size and end (MiB), for the boot log's [gpu windows] row. */
        const uint32_t slot=queue_base_/NativeAdrenoAbiMaxQueues;
        if(slot<NativeAdrenoMaxClients) {
            zorn_direct_window_overflow[slot][0]=zorn_direct_window_overflow[slot][0]+1;
            zorn_direct_window_overflow[slot][1]=uint32_t(entry->memory.bytes()>>10);
            zorn_direct_window_overflow[slot][2]=uint32_t(end>>20);
        }
        return kIOReturnBadArgument;
    }
    uint64_t handle=0;
    /* Memory the owner maps read-only could only be pinned for reading: the GPU gets the read half of what was asked. */
    const unsigned permissions=entry->memory.readOnly()?(request->permissions&~2u):request->permissions;
    /* Imported memory is the owner's cacheable memory (IOSurfaces, no-copy buffers): once the board proved IO coherence, the GPU maps it
     * write-back inner-shareable (Linux's IOMMU_CACHE PTE) and the CPU caches over it need no maintenance. The GPU's own BOs stay
     * non-cacheable: their CPU view is write-combined, and a snoop could find a stale line of the kernel's cacheable alias. */
    /* Mode 1 preserves upstream's read-only selection. The separate mode 2
     * requires this boot's dirty-read/clean-resident proofs plus fixed WB
     * render-target readbacks before the board publishes any user client.
     * Full Vulkan/Metal passes still need a bounded desktop trial. */
    const bool coherent=entry->memory.imported() && NativeAdrenoCoherentImport(zorn_direct_io_coherent,permissions);
    const unsigned refs_before=entry->memory.deviceReferences();
    IOReturn status=vm_->map(&entry->memory,0,request->iova,permissions,
        coherent?1u:request->writeback,coherent?3u:request->shareability,&handle);
    /* An import can alias an existing NC BO. Do not create conflicting PTE
     * cache classes. Retry the caller's NC attributes only after a preflight
     * rejection with no mapping/reference acquired; never replay an I/O error
     * or a partially applied/poisoned transaction. NC keeps maintenance. */
    if(coherent && status==kIOReturnBadArgument && !handle && !request->writeback && !vm_->poisoned() &&
       !entry->memory.quarantined() && entry->memory.deviceReferences()==refs_before){
        status=vm_->map(&entry->memory,0,request->iova,permissions,request->writeback,request->shareability,&handle);
        if(!status)++zorn_direct_coherent_import_fallbacks;
    }
    if(status)return status;
    entry->mapped=handle;entry->iova=request->iova;entry->mapped_state=true;
    if(end>window_peak_)window_peak_=end;
    if(window_bytes_ && window_peak_>window_start_)clientStats(queue_base_,window_bytes_)[5]=(uint32_t)((window_peak_-window_start_)>>20);
    reply->iova=request->iova;
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectClient26::unmapRetainedForTrial(uint64_t handle)
{
    if(!open_ || ownRangeOutstanding())return kIOReturnBusy;
    Entry *e=find(handle);if(!e || !e->mapped_state || e->unreleasable)return kIOReturnBadArgument;
    IOReturn status=vm_->unmap(e->mapped);if(status)return status;
    e->mapped=0;e->mapped_state=false;e->iova=0;return kIOReturnSuccess;
}
static void noteFreeRefused(bool imported,uint64_t handle,IOReturn status)
{
    if(!imported)return;
    zorn_direct_import_live[1]=zorn_direct_import_live[1]+1;zorn_direct_import_live[2]=(uint32_t)status;noteImportState(handle,3);
}
IOReturn ZornGen7DirectClient26::freeBo(const NativeAdrenoAbiBoFree *request)
{
    native_adreno_trace_stage=1;
    if(!request)return kIOReturnBadArgument;
    if(!open_)return kIOReturnNotReady;
    Entry *entry=find(request->handle);
    if(!entry)return kIOReturnBadArgument;
    if(entry->unreleasable) {noteFreeRefused(entry->imported,entry->handle,kIOReturnBusy);return kIOReturnBusy;}
    if(entry->mapping_leases) {noteFreeRefused(entry->imported,entry->handle,kIOReturnBusy);return kIOReturnBusy;}
    native_adreno_trace_stage=2;
    if(entry->mapped_state) {
        /* Completed jobs must not pin the buffer: retire what the CP has passed before the unmap decides. */
        submit_->retireCompleted(); /* a poisoned execbuf refuses and the unmap below stays refused too */
        native_adreno_trace_stage=3;
        const IOReturn unmap=vm_->unmap(entry->mapped);
        native_adreno_trace_stage=4;
        if(unmap) {noteFreeRefused(entry->imported,entry->handle,unmap);return unmap;}
        entry->mapped_state=false;entry->mapped=0;entry->iova=0;
    }
    const IOReturn release=entry->memory.release();
    if(release) {noteFreeRefused(entry->imported,entry->handle,release);return release;}
    if(entry->imported) {zorn_direct_import_live[0]=zorn_direct_import_live[0]-1;noteImportState(entry->handle,2);}
    clear(*entry);
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectClient26::submit(const NativeAdrenoAbiSubmit *request,
    NativeAdrenoAbiSubmitReply *reply,const NativeAdrenoRingClock *clock)
{
    if(!request || !reply)return kIOReturnBadArgument;reply->fence=0;
    if(!request->buffer_count || request->buffer_count>NativeAdrenoAbiMaxBuffers)return kIOReturnBadArgument;
    memcpy(&submit_request_,request,sizeof(*request));
    return submitBatch(&submit_request_,reply,clock);
}
IOReturn ZornGen7DirectClient26::submitBatch(const NativeAdrenoAbiSubmitBatch *request,
    NativeAdrenoAbiSubmitReply *reply,const NativeAdrenoRingClock *clock)
{
    if(!request || !reply)return kIOReturnBadArgument;reply->fence=0;
    if(!open_)return kIOReturnNotReady;
    static_assert(NativeAdrenoAbiMaxBatchBuffers==ZornGen7DirectSubmit26MaxBuffers,"ABI and execbuf batch limits");
    if(!request->buffer_count || request->buffer_count>NativeAdrenoAbiMaxBatchBuffers ||
        request->reserved)return kIOReturnBadArgument;
    if(request->queue>=NativeAdrenoAbiMaxQueues || !queues_[request->queue].active)
        return kIOReturnBadArgument;
    if(request->wait_fence) {
        if(!clock || request->wait_fence>UINT32_MAX)return kIOReturnBadArgument;
        const uint32_t wait_us=request->wait_timeout_ns==0?0:
            (request->wait_timeout_ns>UINT64_C(0xffffffff)*1000u?0xffffffffu:
            (uint32_t)(request->wait_timeout_ns/1000));
        const IOReturn waited=submit_->observeFence((uint32_t)request->wait_fence,clock,wait_us);
        if(waited)return waited;
    }
    ZornGen7DirectSubmit26Buffer *buffers=submit_buffers_;
    for(uint32_t i=0;i<request->buffer_count;++i) {
        const NativeAdrenoAbiSubmitBuffer &wire=request->buffers[i];
        if(!wire.bytes || (wire.bytes&3))return kIOReturnBadArgument;
        Entry *entry=find(wire.handle);
        if(!entry || !entry->mapped_state)return kIOReturnBadArgument;
        buffers[i]={entry->mapped,wire.iova,(size_t)wire.bytes};
    }
    uint32_t fence=0;
    used_=true;
    const IOReturn status=submit_->submit(buffers,request->buffer_count,
        queue_base_+static_cast<uint32_t>(request->queue),&fence);
    if(status)return status;
    reply->fence=fence;
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectClient26::attachTimer(const NativeAdrenoTimer *timer)
{
    if(!open_)return kIOReturnNotReady;
    if(!timer || timer_ )return kIOReturnBadArgument;
    timer_=timer;
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectClient26::timestamp(NativeAdrenoAbiTimestamp *reply)
{
    if(!reply)return kIOReturnBadArgument;*reply={};
    if(!open_)return kIOReturnNotReady;
    if(!timer_)return kIOReturnUnsupported;
    return timer_->read(&reply->ticks);
}
IOReturn ZornGen7DirectClient26::attachDeviceInfo(const NativeAdrenoAbiDeviceInfo *info)
{
    if(!open_)return kIOReturnNotReady;
    if(!info || info_ || info->reserved || !info->chip_id || !info->va_size)return kIOReturnBadArgument;
    info_=info;
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectClient26::deviceInfo(NativeAdrenoAbiDeviceInfo *reply)
{
    if(!reply)return kIOReturnBadArgument;*reply={};
    if(!open_)return kIOReturnNotReady;
    if(!info_)return kIOReturnUnsupported;
    *reply=*info_;
    if(window_bytes_){reply->va_start=window_start_;reply->va_size=window_bytes_;}
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectClient26::attachStatus(const NativeAdrenoStatus *status)
{
    if(!open_)return kIOReturnNotReady;
    if(!status || status_)return kIOReturnBadArgument;
    status_=status;
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectClient26::status(NativeAdrenoAbiStatus *reply)
{
    if(!reply)return kIOReturnBadArgument;*reply={};
    if(!open_)return kIOReturnNotReady;
    if(!status_)return kIOReturnUnsupported;
    const NativeAdrenoStatusCounts counts=status_->counts();
    reply->faults=counts.faults;reply->suspends=counts.suspends;
    return kIOReturnSuccess;
}
size_t ZornGen7DirectClient26::inputSize(uint32_t method)
{
    switch(method) {
    case NativeAdrenoMethodQuery:
    case NativeAdrenoMethodGetTimestamp:
    case NativeAdrenoMethodGetStatus:
    case NativeAdrenoMethodGetDeviceInfo:return 0;
    case NativeAdrenoMethodBoAlloc:return sizeof(NativeAdrenoAbiBoAlloc);
    case NativeAdrenoMethodBoMap:return sizeof(NativeAdrenoAbiBoMap);
    case NativeAdrenoMethodBoImport:return sizeof(NativeAdrenoAbiBoImport);
    case NativeAdrenoMethodBoFree:return sizeof(NativeAdrenoAbiBoFree);
    case NativeAdrenoMethodSubmit:return sizeof(NativeAdrenoAbiSubmit);
    case NativeAdrenoMethodSubmitBatch:return sizeof(NativeAdrenoAbiSubmitBatch);
    case NativeAdrenoMethodSetMetadata:
    case NativeAdrenoMethodGetMetadata:return sizeof(NativeAdrenoAbiMetadata);
    case NativeAdrenoMethodCreateQueue:
    case NativeAdrenoMethodCloseQueue:return sizeof(NativeAdrenoAbiQueue);
    case NativeAdrenoMethodBoCpuMap:return sizeof(NativeAdrenoAbiBoCpuMap);
    case NativeAdrenoMethodBoCpuUnmap:return sizeof(NativeAdrenoAbiBoCpuUnmap);
    case NativeAdrenoMethodWaitFence:return sizeof(NativeAdrenoAbiWaitFence);
    default:return SIZE_MAX;
    }
}
size_t ZornGen7DirectClient26::outputSize(uint32_t method)
{
    switch(method) {
    case NativeAdrenoMethodQuery:return sizeof(NativeAdrenoAbiParams);
    case NativeAdrenoMethodBoAlloc:return sizeof(NativeAdrenoAbiBoAllocReply);
    case NativeAdrenoMethodBoMap:return sizeof(NativeAdrenoAbiBoMapReply);
    case NativeAdrenoMethodBoFree:return 0;
    case NativeAdrenoMethodSubmit:
    case NativeAdrenoMethodSubmitBatch:return sizeof(NativeAdrenoAbiSubmitReply);
    case NativeAdrenoMethodWaitFence:return 0;
    case NativeAdrenoMethodGetTimestamp:return sizeof(NativeAdrenoAbiTimestamp);
    case NativeAdrenoMethodGetStatus:return sizeof(NativeAdrenoAbiStatus);
    case NativeAdrenoMethodGetDeviceInfo:return sizeof(NativeAdrenoAbiDeviceInfo);
    case NativeAdrenoMethodGetMetadata:return sizeof(NativeAdrenoAbiMetadata);
    case NativeAdrenoMethodSetMetadata:return 0;
    case NativeAdrenoMethodCreateQueue:return sizeof(NativeAdrenoAbiQueueReply);
    case NativeAdrenoMethodCloseQueue:return 0;
    case NativeAdrenoMethodBoCpuMap:return sizeof(NativeAdrenoAbiBoCpuMapReply);
    case NativeAdrenoMethodBoCpuUnmap:return 0;
    case NativeAdrenoMethodBoImport:return sizeof(NativeAdrenoAbiBoAllocReply);
    default:return SIZE_MAX;
    }
}
IOReturn ZornGen7DirectClient26::dispatch(uint32_t method,const void *input,
    size_t input_size,void *output,size_t output_size,const NativeAdrenoRingClock *clock)
{
    struct Tally {
        uint32_t method;uint64_t began;IOReturn *result;const NativeAdrenoRingClock *clock;
        Tally(uint32_t m,IOReturn *r,const NativeAdrenoRingClock *c):method(m),began(c && c->now_us?c->now_us(c->cookie):0),result(r),clock(c) {}
        ~Tally() {
            if(method>=20)return;
            const uint64_t now=clock && clock->now_us?clock->now_us(clock->cookie):0;
            zorn_direct_method_stats[method][0]=zorn_direct_method_stats[method][0]+1;
            if(*result)zorn_direct_method_stats[method][1]=zorn_direct_method_stats[method][1]+1;
            zorn_direct_method_stats[method][2]=(uint32_t)*result;
            zorn_direct_method_stats[method][3]=zorn_direct_method_stats[method][3]+(uint32_t)(now-began);
        }
    };
    // VM/submit diagnostic uptime is OS-owned; never retain this call's clock/cookie.
    IOReturn tally_result=kIOReturnSuccess;
    Tally tally(method,&tally_result,clock);
    const size_t expected_in=inputSize(method),expected_out=outputSize(method);
    if(expected_in==SIZE_MAX || expected_out==SIZE_MAX)return kIOReturnUnsupported;
    if(input_size!=expected_in || output_size!=expected_out)return kIOReturnBadArgument;
    if((expected_in && !input) || (expected_out && !output))return kIOReturnBadArgument;
    IOReturn status=kIOReturnSuccess;
    switch(method) {
    case NativeAdrenoMethodQuery: {
        NativeAdrenoAbiParams reply{};
        status=query(&reply);
        if(!status)memcpy(output,&reply,sizeof(reply));
        break;
    }
    case NativeAdrenoMethodBoAlloc: {
        NativeAdrenoAbiBoAlloc request{};
        memcpy(&request,input,sizeof(request));
        NativeAdrenoAbiBoAllocReply reply{};
        status=allocBo(&request,&reply);
        if(!status)memcpy(output,&reply,sizeof(reply));
        break;
    }
    case NativeAdrenoMethodBoImport:
        status=kIOReturnUnsupported;
        break;
    case NativeAdrenoMethodBoMap: {
        NativeAdrenoAbiBoMap request{};
        memcpy(&request,input,sizeof(request));
        NativeAdrenoAbiBoMapReply reply{};
        status=mapBo(&request,&reply);
        if(!status)memcpy(output,&reply,sizeof(reply));
        else {
            /* Why maps fail (int-135: 55 of 191, and the translator answers each as a device out-of-memory): status, count, and what the table
             * held and the failed request asked for the last time. */
            unsigned at=0;while(at<5 && zorn_direct_map_fail[at][0] && zorn_direct_map_fail[at][0]!=(uint32_t)status)++at;
            zorn_direct_map_fail[at][0]=(uint32_t)status;zorn_direct_map_fail[at][1]=zorn_direct_map_fail[at][1]+1;
            zorn_direct_map_fail[5][0]=(uint32_t)vm_->spanCount();zorn_direct_map_fail[5][1]=(uint32_t)vm_->objectCount();
            zorn_direct_map_fail[6][0]=(uint32_t)(request.iova>>12);zorn_direct_map_fail[6][1]=(uint32_t)(request.handle);
        }
        break;
    }
    case NativeAdrenoMethodBoFree: {
        NativeAdrenoAbiBoFree request{};
        memcpy(&request,input,sizeof(request));
        status=freeBo(&request);
        break;
    }
    case NativeAdrenoMethodSubmit: {
        NativeAdrenoAbiSubmit request{};
        memcpy(&request,input,sizeof(request));
        NativeAdrenoAbiSubmitReply reply{};
        status=submit(&request,&reply,clock);
        if(!status)memcpy(output,&reply,sizeof(reply));
        break;
    }
    case NativeAdrenoMethodSubmitBatch: {
        memcpy(&submit_request_,input,sizeof(submit_request_));
        NativeAdrenoAbiSubmitReply reply{};
        status=submitBatch(&submit_request_,&reply,clock);
        if(!status)memcpy(output,&reply,sizeof(reply));
        break;
    }
    case NativeAdrenoMethodWaitFence: {
        NativeAdrenoAbiWaitFence request{};
        memcpy(&request,input,sizeof(request));
        status=waitFence(&request,clock);
        break;
    }
    case NativeAdrenoMethodGetDeviceInfo: {
        NativeAdrenoAbiDeviceInfo reply{};
        status=deviceInfo(&reply);
        if(!status)memcpy(output,&reply,sizeof(reply));
        break;
    }
    case NativeAdrenoMethodGetTimestamp: {
        NativeAdrenoAbiTimestamp reply{};
        status=timestamp(&reply);
        if(!status)memcpy(output,&reply,sizeof(reply));
        break;
    }
    case NativeAdrenoMethodBoCpuMap: {
        NativeAdrenoAbiBoCpuMap request{};
        memcpy(&request,input,sizeof(request));
        NativeAdrenoAbiBoCpuMapReply reply{};
        status=cpuMap(&request,&reply);
        if(!status)memcpy(output,&reply,sizeof(reply));
        break;
    }
    case NativeAdrenoMethodBoCpuUnmap: {
        NativeAdrenoAbiBoCpuUnmap request{};
        memcpy(&request,input,sizeof(request));
        status=cpuUnmap(&request);
        break;
    }
    case NativeAdrenoMethodCreateQueue: {
        NativeAdrenoAbiQueueReply reply{};
        status=createQueue(&reply);
        if(!status)memcpy(output,&reply,sizeof(reply));
        break;
    }
    case NativeAdrenoMethodCloseQueue: {
        NativeAdrenoAbiQueue request{};
        memcpy(&request,input,sizeof(request));
        status=closeQueue(&request);
        break;
    }
    case NativeAdrenoMethodSetMetadata: {
        NativeAdrenoAbiMetadata request{};
        memcpy(&request,input,sizeof(request));
        status=setMetadata(&request);
        break;
    }
    case NativeAdrenoMethodGetMetadata: {
        NativeAdrenoAbiMetadata request{};
        memcpy(&request,input,sizeof(request));
        NativeAdrenoAbiMetadata reply{};
        status=getMetadata(&request,&reply);
        if(!status)memcpy(output,&reply,sizeof(reply));
        break;
    }
    case NativeAdrenoMethodGetStatus: {
        NativeAdrenoAbiStatus reply{};
        status=this->status(&reply);
        if(!status)memcpy(output,&reply,sizeof(reply));
        break;
    }
    default:return kIOReturnUnsupported;
    }
    tally_result=status;
    return status;
}
IOReturn ZornGen7DirectClient26::cpuMap(const NativeAdrenoAbiBoCpuMap *request,
    NativeAdrenoAbiBoCpuMapReply *reply)
{
    if(!request || !reply)return kIOReturnBadArgument;*reply={};
    if(!open_)return kIOReturnNotReady;
    Entry *entry=find(request->handle);
    if(!entry || entry->unreleasable)return kIOReturnBadArgument;
    /* An imported BO is the caller's own memory, already mapped where it came from. */
    if(entry->memory.imported())return kIOReturnUnsupported;
    NativeAdrenoCpuView view{};
    if(!entry->memory.cpuView(&view))return kIOReturnNotReady;
    if(entry->mapping_leases==UINT32_MAX)return kIOReturnNoResources;
    ++entry->mapping_leases;
    reply->token=entry->token;reply->bytes=view.bytes;
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectClient26::cpuUnmap(const NativeAdrenoAbiBoCpuUnmap *request)
{
    if(!request)return kIOReturnBadArgument;
    if(!open_)return kIOReturnNotReady;
    if(request->reserved)return kIOReturnBadArgument;
    Entry *entry=find(request->handle);
    if(!entry || entry->unreleasable || !entry->token)return kIOReturnBadArgument;
    if(request->token!=entry->token)return kIOReturnBadArgument;
    if(!entry->mapping_leases)return kIOReturnBusy;
    --entry->mapping_leases;
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectClient26::createQueue(NativeAdrenoAbiQueueReply *reply)
{
    if(!reply)return kIOReturnBadArgument;
    if(!open_)return kIOReturnNotReady;
    for(size_t i=1;i<NativeAdrenoAbiMaxQueues;++i)if(!queues_[i].active) {
        queues_[i]={static_cast<uint32_t>(i),true};
        reply->queue=i;
        return kIOReturnSuccess;
    }
    return kIOReturnNoResources;
}
IOReturn ZornGen7DirectClient26::closeQueue(const NativeAdrenoAbiQueue *request)
{
    if(!request)return kIOReturnBadArgument;
    if(!open_)return kIOReturnNotReady;
    if(!request->queue || request->queue>=NativeAdrenoAbiMaxQueues)return kIOReturnBadArgument;
    Queue &queue=queues_[request->queue];
    if(!queue.active)return kIOReturnBadArgument;
    /* A queue must be drained by the caller before it disappears. */
    if(submit_->queueOutstanding(queue_base_+static_cast<uint32_t>(request->queue)))
        return kIOReturnBusy;
    queue={};
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectClient26::setMetadata(const NativeAdrenoAbiMetadata *request)
{
    if(!request)return kIOReturnBadArgument;
    if(!open_)return kIOReturnNotReady;
    if(request->reserved || request->bytes>NativeAdrenoAbiMetadataBytes)return kIOReturnBadArgument;
    Entry *entry=find(request->handle);
    if(!entry || entry->unreleasable)return kIOReturnBadArgument;
    if(request->bytes)memcpy(entry->metadata,request->text,request->bytes);
    entry->metadata_bytes=request->bytes;
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectClient26::getMetadata(const NativeAdrenoAbiMetadata *request,
    NativeAdrenoAbiMetadata *reply)
{
    if(!request || !reply)return kIOReturnBadArgument;
    /* Snapshot the request so an in/out alias is still well defined. */
    const uint64_t handle=request->handle;
    const uint32_t asked=request->bytes;
    const uint32_t reserved=request->reserved;
    *reply={};
    if(!open_)return kIOReturnNotReady;
    if(reserved || asked>NativeAdrenoAbiMetadataBytes)return kIOReturnBadArgument;
    Entry *entry=find(handle);
    if(!entry || entry->unreleasable)return kIOReturnBadArgument;
    if(asked<entry->metadata_bytes)return kIOReturnBadArgument;
    reply->handle=entry->handle;reply->bytes=entry->metadata_bytes;
    if(entry->metadata_bytes)memcpy(reply->text,entry->metadata,entry->metadata_bytes);
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectClient26::waitFence(const NativeAdrenoAbiWaitFence *request,
    const NativeAdrenoRingClock *clock)
{
    if(!request || !clock)return kIOReturnBadArgument;
    if(!open_)return kIOReturnNotReady;
    if(!request->fence || request->fence>UINT32_MAX)return kIOReturnBadArgument;
    const uint32_t timeout_us=request->timeout_ns==0?0:
        (request->timeout_ns>UINT64_C(0xffffffff)*1000u?0xffffffffu:
        (uint32_t)(request->timeout_ns/1000));
    return submit_->wait((uint32_t)request->fence,clock,timeout_us);
}

// Non-mutating same-entry check before the IOKit view owner revokes a CPU
// descriptor. Every admission/error condition matches original cpuUnmap;
// the original mutation remains in dispatch after actual VM unmapping.
IOReturn ZornGen7DirectClient26::preflightCpuUnmap(const NativeAdrenoAbiBoCpuUnmap *request,uint32_t *leases)
{
    if(!request || !leases)return kIOReturnBadArgument;
    if(!open_)return kIOReturnNotReady;
    if(request->reserved)return kIOReturnBadArgument;
    Entry *entry=find(request->handle);
    if(!entry || entry->unreleasable || !entry->token)return kIOReturnBadArgument;
    if(request->token!=entry->token)return kIOReturnBadArgument;
    if(!entry->mapping_leases)return kIOReturnBusy;
    *leases=entry->mapping_leases;return kIOReturnSuccess;
}

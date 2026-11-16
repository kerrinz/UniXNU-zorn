/* SPDX-License-Identifier: MIT */
#include "ZornGen7DirectSubmit26.h"
#include "AdrenoPM4.h"
#include <IOKit/IOLib.h>
// Optional board clock: host checks without a published driver collect no
// timings. Observations never change submission, references or cache policy.
extern "C" uint64_t zorn_direct_vm_now_us(void);
extern "C" {volatile uint64_t zorn_direct_submit_cost[12];}
/* Accepted jobs, total IBs, largest batch, jobs with more than 16 IBs. */
extern "C" {volatile uint64_t zorn_direct_submit_batches[4];}
static uint64_t submitDiagNow(void) {return zorn_direct_vm_now_us();}
static void submitDiagRecord(unsigned slot,uint64_t began) {
    if(!began)return;
    const uint64_t end=submitDiagNow();if(end<began)return;
    const uint64_t us=end-began;
    __atomic_fetch_add(&zorn_direct_submit_cost[slot],1ull,__ATOMIC_RELAXED);
    __atomic_fetch_add(&zorn_direct_submit_cost[slot+1],us,__ATOMIC_RELAXED);
    uint64_t peak=__atomic_load_n(&zorn_direct_submit_cost[slot+2],__ATOMIC_RELAXED);
    while(us>peak && !__atomic_compare_exchange_n(&zorn_direct_submit_cost[slot+2],&peak,us,false,__ATOMIC_RELAXED,__ATOMIC_RELAXED)){}
}
struct SubmitDiagScope {unsigned slot;uint64_t began;
    explicit SubmitDiagScope(unsigned s):slot(s),began(submitDiagNow()){}
    ~SubmitDiagScope(){submitDiagRecord(slot,began);}};
struct DirectSubmitGateScope {
    ZornGen7DirectVm26Routes *routes=nullptr;IOReturn status=kIOReturnNotReady;bool held=false;
    explicit DirectSubmitGateScope(ZornGen7DirectVm26Routes *r):routes(r) {
        if(routes && routes->beginSubmission && routes->endSubmission && routes->cookie) {
            status=routes->beginSubmission(routes->cookie);held=status==kIOReturnSuccess;
        }
    }
    ~DirectSubmitGateScope(){if(held)routes->endSubmission(routes->cookie);}
    DirectSubmitGateScope(const DirectSubmitGateScope &)=delete;
    DirectSubmitGateScope &operator=(const DirectSubmitGateScope &)=delete;
};

/* CP_INDIRECT_BUFFER is opcode 0x3f with a 3-word payload: 64-bit GPU address
 * and IB_SIZE in dwords (bits 0..19), exactly as the pinned adreno_pm4.xml
 * domain states and Linux msm_gem_submit.c converts the userspace byte size. */
enum : uint32_t {SubmitIndirectBuffer=0x3f,SubmitIbWords=3,SubmitMaxJobs=8,
    SubmitMaxBuffers=ZornGen7DirectSubmit26MaxBuffers,SubmitMaxIbBytes=0xfffffu*4u,
    SubmitAuditBytes=256u*1024u};   /* IB bytes the write-combine audit compares per submission */
extern "C" {volatile uint32_t zorn_direct_coherence[8];}
/* The submission (1-based count) at which the write-combine audit found a dirty IB line or failed; 0 = never. */
extern "C" {volatile uint32_t zorn_direct_wc_distrusted;}
/* The write-combine audit before each submission while trusted: [0] submissions audited, [1] IB lines compared, [2] dirty lines,
 * [3] stale clean lines, [4] the last audit failure (any failure also ends the trust), [5] pages found back at the default attribute
 * and write-combined again. */
extern "C" {volatile uint32_t zorn_direct_wc_audit[6];}
/* Fence waits: [0] calls, [1] timeouts, [2] the fence of the last timed-out wait, [3] the fence value the GPU had written then, [4] the newest fence handed out,
 * [5] the newest completed, [6] waits for a fence no job holds (observeFence path), [7] the last fence refused as never submitted. */
extern "C" {volatile uint32_t zorn_direct_fence_wait[8];}
/* The IBs of the last submissions: [slot] fence, iova low/high, bytes, then the first 28 dwords of the first IB (read as the kernel maps it). */
extern "C" {volatile uint32_t zorn_direct_ib_log[4][4+28];volatile uint32_t zorn_direct_ib_log_count;}
IOReturn ZornGen7DirectSubmit26::poison()
{
    poisoned_=true;if(present_)present_->failed=true;return kIOReturnIOError;
}
ZornGen7DirectSubmit26::Job *ZornGen7DirectSubmit26::find(uint32_t fence)
{
    if(fence)for(auto &job:jobs_)if(job.active && job.fence==fence)return &job;
    return nullptr;
}
ZornGen7DirectSubmit26::Job *ZornGen7DirectSubmit26::free()
{
    for(auto &job:jobs_)if(!job.active)return &job;
    return nullptr;
}
IOReturn ZornGen7DirectSubmit26::attach(ZornGen7DirectVm26 *vm,NativeAdrenoRing *ring,ZornGen7PresentProgress26 *present)
{
    if(attached_ || poisoned_ || vm_ || ring_)return kIOReturnBusy;
    if(!vm || !ring || !present || present->failed || vm->poisoned() || ring->poisoned())return kIOReturnBadArgument;
    DirectSubmitGateScope gate(vm->streams_);
    if(gate.status)return gate.status;
    vm_=vm;ring_=ring;present_=present;attached_=true;stats_={};
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectSubmit26::release(Job &job)
{
    IOReturn status=kIOReturnSuccess;
    for(size_t i=0;i<job.count;++i) {
        IOReturn retired=vm_->retireJobAfterCompletion(job.handles[i]);
        if(retired)status=retired;else ++stats_.references_retired;
    }
    if(status)return poison();
    if(vm_->acquireImported())return poison();
    if(vm_->retireSubmissionResourcesAfterCompletion())return poison();
    // NativeRing rejects sequence wrap. Publish only this actual retired
    // fence after its GPU result and imported-memory visibility succeeded.
    if(job.fence>present_->retiredFence)present_->retiredFence=job.fence;
    job={};return kIOReturnSuccess;
}
IOReturn ZornGen7DirectSubmit26::detach()
{
    if(poisoned_ || outstanding())return kIOReturnBusy;
    if(!attached_)return kIOReturnNotReady;
    attached_=false;vm_=nullptr;ring_=nullptr;present_=nullptr;return kIOReturnSuccess;
}
bool ZornGen7DirectSubmit26::queueOutstanding(uint32_t queue) const
{
    return rangeOutstanding(queue,1);
}
bool ZornGen7DirectSubmit26::rangeOutstanding(uint32_t first,uint32_t count) const
{
    for(const auto &job:jobs_)if(job.active && job.queue-first<count)return true;
    return false;
}
size_t ZornGen7DirectSubmit26::outstanding() const
{
    size_t count=0;for(const auto &job:jobs_)if(job.active)++count;return count;
}
IOReturn ZornGen7DirectSubmit26::submit(const ZornGen7DirectSubmit26Buffer *buffers,size_t count,
    uint32_t queue,uint32_t *fence)
{
    SubmitDiagScope measured(0);
    if(!fence)return kIOReturnBadArgument;*fence=0;
    if(!attached_ || poisoned_ || !vm_)return kIOReturnNotReady;
    DirectSubmitGateScope gate(vm_->streams_);
    if(gate.status)return gate.status;
    if(!buffers || !count || count>SubmitMaxBuffers)return kIOReturnBadArgument;
    /* Every buffer is validated against the live VM before any reference. */
    uint64_t *handles=scratch_handles_;size_t handle_count=0;
    uint32_t *words=scratch_words_;size_t word_count=0;
    for(size_t i=0;i<count;++i) {
        const ZornGen7DirectSubmit26Buffer &buffer=buffers[i];
        if(!buffer.handle || !buffer.bytes || (buffer.iova&3) || (buffer.bytes&3) || buffer.bytes>SubmitMaxIbBytes)
            return kIOReturnBadArgument;
        uint64_t iova=0;size_t bytes=0;unsigned permissions=0;
        IOReturn status=vm_->describe(buffer.handle,&iova,&bytes,&permissions);
        if(status)return status;
        if(!(permissions&ZornSmmuSparse4KRead) || buffer.iova<iova ||
            buffer.iova-iova>bytes || buffer.bytes>bytes-(buffer.iova-iova))return kIOReturnBadArgument;
        uint32_t header=0;
        if(AdrenoPM4Type7(SubmitIndirectBuffer,SubmitIbWords,&header)!=AdrenoPM4Success)
            return poison();
        words[word_count++]=header;
        words[word_count++]=(uint32_t)buffer.iova;
        words[word_count++]=(uint32_t)(buffer.iova>>32);
        words[word_count++]=(uint32_t)(buffer.bytes/4);
        bool known=false;
        for(size_t j=0;j<handle_count;++j)if(handles[j]==buffer.handle) {known=true;break;}
        if(!known)handles[handle_count++]=buffer.handle;
    }
    IOReturn swept=retireCompleted();
    if(swept)return swept;
    Job *job=free();
    if(!job)return kIOReturnBusy;
    for(size_t i=0;i<handle_count;++i) {
        IOReturn status=vm_->holdJob(handles[i]);
        if(status) {
            while(i) {vm_->retireJobAfterCompletion(handles[--i]);++stats_.references_retired;}
            return status;
        }
        ++stats_.references_held;
    }
    // Retain all mappings, including render targets/textures reached by an
    // IB rather than named as an IB. Each mapping already owns its actual
    // backing reference; unmap cannot release it until every job retires.
    IOReturn resources=vm_->holdSubmissionResources();
    if(resources) {
        for(size_t i=0;i<handle_count;++i) {
            if(vm_->retireJobAfterCompletion(handles[i]))return poison();
            ++stats_.references_retired;
        }
        return resources;
    }
    uint32_t value=0;
    /* int-070: the first IB word as the kernel's cacheable alias and DRAM see it before any maintenance, then DRAM after the CPU
     * caches over every mapped BO are cleaned and invalidated. The board shows the last submission's record on a stall. */
    uint32_t cached=~0u,before=~0u,ignored=0,after=~0u;
    /* Write-combined stores this CPU made before the call (the client's command words) complete before anything below. */
    __asm__ volatile("dsb sy":::"memory");
    /* int-098/099: with write-combined user BOs and no maintenance the CP stopped at the end of the first IB, as in int-065..069 when an
     * IB sat in a CPU cache. While write-combined BOs are trusted, every line of this submission's IBs is compared as a CPU cache and
     * DRAM hold it (bounded). A dirty line means a client view still caches its BOs: maintain every BO from now on, this submission
     * included (the audit already wrote the IB lines back; the rest of the BOs may hold more). */
    if(vm_->writeCombinedTrusted()) {
        /* int-100: the dirty IB page was back at XNU's default (cacheable) attribute. Write-combine every such page again first; the
         * pmap writes its lines back on the way, so the audit below should then find none. */
        uint32_t reset=0;
        IOReturn reasserted;
        {SubmitDiagScope measured(3);reasserted=vm_->reassertWriteCombined(&reset);}
        zorn_direct_wc_audit[5]=zorn_direct_wc_audit[5]+reset;
        if(reasserted) {
            /* Mandatory page-attribute correction failed. Its error is not
             * the optional line-audit hook's Unsupported result. The VM has
             * quarantined the failing BO; preserve every held IB reference
             * and do not publish, invalidate, prepare or kick any GPU work. */
            zorn_direct_wc_audit[4]=reasserted;
            vm_->distrustWriteCombined();
            zorn_direct_wc_distrusted=zorn_direct_coherence[0]+1;
            *job=Job{};++stats_.poisoned_jobs;
            for(size_t i=0;i<handle_count;++i)job->handles[i]=handles[i];
            job->count=handle_count;job->queue=queue;job->active=true;
            (void)poison();return reasserted;
        }
        IOReturn audited=kIOReturnSuccess;
        uint32_t lines=0,dirty=0,stale=0;size_t budget=SubmitAuditBytes;
        /* The re-assertion above is the correction and runs every time; the audit only detects, and found no dirty line in int-141's
         * 133798, so after the first 16 submissions it compares every eighth one's IBs (it cost about 2 ms each). */
        ++audit_tick_;
        const bool audit_now=audit_tick_<=16 || (audit_tick_&7)==1;
        if(!audit_now)budget=0;
        const uint64_t audit_began=audit_now?submitDiagNow():0;
        for(size_t i=0;i<count && budget && !audited;++i) {
            const size_t bytes=buffers[i].bytes<budget?(size_t)buffers[i].bytes:budget;
            audited=vm_->auditRange(buffers[i].iova,bytes,&lines,&dirty,&stale);budget-=bytes;
        }
        submitDiagRecord(9,audit_began);
        if(audit_now && audited!=kIOReturnUnsupported) {   /* no board hook (host): nothing to compare */
            zorn_direct_wc_audit[0]=zorn_direct_wc_audit[0]+1;
            zorn_direct_wc_audit[1]=zorn_direct_wc_audit[1]+lines;
            zorn_direct_wc_audit[2]=zorn_direct_wc_audit[2]+dirty;
            zorn_direct_wc_audit[3]=zorn_direct_wc_audit[3]+stale;
            if(audited)zorn_direct_wc_audit[4]=audited;
        }
        if(dirty || (audited && audited!=kIOReturnUnsupported)) {
            vm_->distrustWriteCombined();
            zorn_direct_wc_distrusted=zorn_direct_coherence[0]+1;
        }
    }
    /* These fresh uncached mappings only record a diagnostic word. Match
     * upstream's 1/64 sampling without weakening houji's periodic line audit
     * or its mandatory per-submit page-attribute/cache maintenance. */
    const bool sample=(stats_.submissions&63)==0;
    if(sample)(void)vm_->sampleWord(buffers[0].iova,&cached,&before);
    IOReturn status;
    {SubmitDiagScope measured(6);status=vm_->publishMapped();}
    if(!status) {
        if(sample)(void)vm_->sampleWord(buffers[0].iova,&ignored,&after);
        zorn_direct_coherence[0]=zorn_direct_coherence[0]+1;
        if(sample){zorn_direct_coherence[1]=cached;zorn_direct_coherence[2]=before;zorn_direct_coherence[3]=after;}
        if(sample && (cached!=before || before!=after)) {
            if(!zorn_direct_coherence[4]) {
                zorn_direct_coherence[5]=cached;zorn_direct_coherence[6]=before;zorn_direct_coherence[7]=after;
            }
            zorn_direct_coherence[4]=zorn_direct_coherence[4]+1;
        }
    }
    /* The active ArmSmmu4KLiveUpdateContextBatch fills invalid leaves only,
     * publishes their table pages, and synchronously invalidates each unmap
     * before releasing its memory. Upper tables stay fixed. A successful
     * unchanged VM therefore needs no TLBIALL at each submission; that would
     * discard useful translations and serialize every frame on device MMIO.
     * Failed table updates still poison the VM and retain their resources. */
    if(status) {
        // Failed mandatory publication may have quarantined a real mapping.
        // Preserve the job and namespace, as on an uncertain ring commit.
        if(vm_->poisoned()) {
            *job=Job{};++stats_.poisoned_jobs;
            for(size_t i=0;i<handle_count;++i)job->handles[i]=handles[i];
            job->count=handle_count;job->queue=queue;job->active=true;
            (void)poison();return status;
        }
        if(vm_->cancelUnpublishedSubmissionResources())return poison();
        for(size_t i=0;i<handle_count;++i) {
            if(vm_->retireJobAfterCompletion(handles[i]))return poison();
            ++stats_.references_retired;
        }
        return status;
    }
    {
        const uint32_t slot=zorn_direct_ib_log_count&3;uint32_t head[28];
        (void)vm_->peekWords(buffers[0].iova,head,28);
        zorn_direct_ib_log[slot][0]=ring_->lastSubmitted()+1;zorn_direct_ib_log[slot][1]=(uint32_t)buffers[0].iova;
        zorn_direct_ib_log[slot][2]=(uint32_t)(buffers[0].iova>>32);zorn_direct_ib_log[slot][3]=(uint32_t)buffers[0].bytes;
        for(unsigned i=0;i<28;++i)zorn_direct_ib_log[slot][4+i]=head[i];
        zorn_direct_ib_log_count=zorn_direct_ib_log_count+1;
    }
    status=ring_->submitFramed(words,word_count,&value);
    if(status) {
        /* A poisoned ring may already have consumed the WPTR write, so the
         * referenced buffers cannot be retired here. */
        if(ring_->poisoned()) {
            *job=Job{};++stats_.poisoned_jobs;
            for(size_t i=0;i<handle_count;++i)job->handles[i]=handles[i];
            job->count=handle_count;job->queue=queue;job->active=true;
            return poison();
        }
        if(vm_->cancelUnpublishedSubmissionResources())return poison();
        while(handle_count) {
            if(vm_->retireJobAfterCompletion(handles[--handle_count]))return poison();
            ++stats_.references_retired;
        }
        return status;
    }
    for(size_t i=0;i<handle_count;++i)job->handles[i]=handles[i];
    job->count=handle_count;job->fence=value;job->queue=queue;job->active=true;
    ++stats_.submissions;
    __atomic_fetch_add(&zorn_direct_submit_batches[0],1ull,__ATOMIC_RELAXED);
    __atomic_fetch_add(&zorn_direct_submit_batches[1],(uint64_t)count,__ATOMIC_RELAXED);
    uint64_t peak=__atomic_load_n(&zorn_direct_submit_batches[2],__ATOMIC_RELAXED);
    while(count>peak && !__atomic_compare_exchange_n(&zorn_direct_submit_batches[2],&peak,(uint64_t)count,false,__ATOMIC_RELAXED,__ATOMIC_RELAXED)){}
    if(count>16)__atomic_fetch_add(&zorn_direct_submit_batches[3],1ull,__ATOMIC_RELAXED);
    if(outstanding()>stats_.peak_jobs)stats_.peak_jobs=outstanding();
    *fence=value;
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectSubmit26::observeFence(uint32_t fence,const NativeAdrenoRingClock *clock,
    uint32_t timeout_us)
{
    if(!attached_ || poisoned_)return kIOReturnNotReady;
    if(!fence)return kIOReturnBadArgument;
    const NativeAdrenoRingFence result=ring_->observeFence(fence,clock,timeout_us,nullptr);
    if(result==NativeAdrenoRingFencePoisoned)return poison();
    if(result==NativeAdrenoRingFenceArgument)return kIOReturnBadArgument;
    if(result==NativeAdrenoRingFenceTimeout)return kIOReturnTimeout;
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectSubmit26::wait(uint32_t fence,const NativeAdrenoRingClock *clock,
    uint32_t timeout_us)
{
    if(!attached_ || poisoned_)return kIOReturnNotReady;
    if(!fence)return kIOReturnBadArgument;
    if(!vm_)return kIOReturnNotReady;
    bool has_job=false;
    {
        DirectSubmitGateScope gate(vm_->streams_);
        if(gate.status)return gate.status;
        has_job=find(fence)!=nullptr;
    }
    uint32_t observed=0;
    zorn_direct_fence_wait[0]=zorn_direct_fence_wait[0]+1;
    if(!has_job) {
        zorn_direct_fence_wait[6]=zorn_direct_fence_wait[6]+1;
        const NativeAdrenoRingFence passed=ring_->observeFence(fence,clock,timeout_us,&observed);
        if(passed==NativeAdrenoRingFencePoisoned)return poison();
        if(passed==NativeAdrenoRingFenceArgument) {zorn_direct_fence_wait[7]=fence;return kIOReturnBadArgument;}
        if(passed==NativeAdrenoRingFenceTimeout) {
            ++stats_.timeouts;
            zorn_direct_fence_wait[1]=zorn_direct_fence_wait[1]+1;zorn_direct_fence_wait[2]=fence;zorn_direct_fence_wait[3]=observed;
            zorn_direct_fence_wait[4]=ring_->lastSubmitted();zorn_direct_fence_wait[5]=ring_->completedFence();
            return kIOReturnTimeout;
        }
        return kIOReturnSuccess;
    }
    const NativeAdrenoRingFence result=ring_->wait(fence,clock,timeout_us,&observed);
    if(result==NativeAdrenoRingFencePoisoned)return poison();
    if(result==NativeAdrenoRingFenceArgument) {zorn_direct_fence_wait[7]=fence;return kIOReturnBadArgument;}
    if(result==NativeAdrenoRingFenceTimeout) {
        ++stats_.timeouts;
        zorn_direct_fence_wait[1]=zorn_direct_fence_wait[1]+1;zorn_direct_fence_wait[2]=fence;zorn_direct_fence_wait[3]=observed;
        zorn_direct_fence_wait[4]=ring_->lastSubmitted();zorn_direct_fence_wait[5]=ring_->completedFence();
        return kIOReturnTimeout;
    }
    if(!vm_)return kIOReturnNotReady;
    DirectSubmitGateScope gate(vm_->streams_);
    if(gate.status)return gate.status;
    Job *job=find(fence);
    if(!job) {
        // A concurrent retire may have released the job after the GPU
        // completed. The observed fence is still a successful wait result.
        return kIOReturnSuccess;
    }
    // A real timestamp fence covers earlier packets on this ordered ring.
    // Turnip signals the last chunk of a batch. Retire its earlier jobs in
    // this queue too, so their references do not keep presentation waiting.
    for(auto &earlier:jobs_) {
        if(!earlier.active || earlier.queue!=job->queue || earlier.fence>=fence)continue;
        const IOReturn status=release(earlier);
        if(status)return status;
        ++stats_.completed;
    }
    IOReturn status=release(*job);
    if(status)return status;
    ++stats_.completed;
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectSubmit26::waitAll(const NativeAdrenoRingClock *clock,uint32_t timeout_us)
{
    if(!attached_ || poisoned_)return kIOReturnNotReady;
    while(outstanding()) {
        Job *oldest=nullptr;
        for(auto &job:jobs_)if(job.active && (!oldest || job.fence-oldest->fence>0x80000000u))oldest=&job;
        const IOReturn status=wait(oldest->fence,clock,timeout_us);
        if(status)return status;
    }
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectSubmit26::waitRange(uint32_t first,uint32_t count,const NativeAdrenoRingClock *clock,uint32_t timeout_us)
{
    if(!attached_ || poisoned_)return kIOReturnNotReady;
    while(rangeOutstanding(first,count)) {
        Job *oldest=nullptr;
        for(auto &job:jobs_)if(job.active && job.queue-first<count && (!oldest || job.fence-oldest->fence>0x80000000u))oldest=&job;
        const IOReturn status=wait(oldest->fence,clock,timeout_us);
        if(status)return status;
    }
    return kIOReturnSuccess;
}
IOReturn ZornGen7DirectSubmit26::retireCompleted()
{
    if(!attached_ || poisoned_ || !vm_)return kIOReturnNotReady;
    DirectSubmitGateScope gate(vm_->streams_);
    if(gate.status)return gate.status;
    for(auto &job:jobs_) {
        if(!job.active)continue;
        const NativeAdrenoRingFence state=ring_->observeFence(job.fence,nullptr,0,nullptr);
        if(state==NativeAdrenoRingFencePoisoned)return poison();
        if(state!=NativeAdrenoRingFenceComplete)continue;
        const IOReturn status=release(job);
        if(status)return status;
        ++stats_.completed;
    }
    return kIOReturnSuccess;
}

/* SPDX-License-Identifier: MIT */
#ifndef ZORN_GEN7_DIRECT_SUBMIT26_H
#define ZORN_GEN7_DIRECT_SUBMIT26_H
#include "../direct-ring/NativeAdrenoRing.h"
#include "ZornGen7DirectVm26.h"
#include "ZornGen7Present26.h"

enum : size_t {ZornGen7DirectSubmit26MaxBuffers=NativeAdrenoRingMaxBuffers};

struct ZornGen7DirectSubmit26Buffer {
    uint64_t handle;
    uint64_t iova;
    size_t bytes;      /* Complete indirect-buffer range in bytes. */
};
/* Coherence samples (int-070): [0] submissions sampled; [1..3] the last one's first IB word through the kernel's cacheable alias,
 * through DRAM before and through DRAM after the CPU cache maintenance of every mapped BO (~0 when unreadable); [4] samples whose
 * three values differ and [5..7] the first such sample. */
extern "C" volatile uint32_t zorn_direct_coherence[8];
/* The write-combine audit (int-100), see ZornGen7DirectSubmit26.cpp, and the submission (1-based) that ended the trust; 0 = never. */
extern "C" volatile uint32_t zorn_direct_wc_audit[6];
extern "C" volatile uint32_t zorn_direct_wc_distrusted;
struct ZornGen7DirectSubmit26Stats {
    uint32_t submissions,completed,timeouts,poisoned_jobs;
    size_t references_held,references_retired,peak_jobs;
};
/* Kernel-side execbuf: turns validated indirect buffers into one ring
 * submission and owns a device reference per distinct IB plus a namespace
 * reference for every mapped backing (including textures/render targets)
 * until the timestamp fence is actually observed and imports acquired. This is not a userspace ABI and not a
 * scheduler: at most eight jobs are outstanding, callers serialize every
 * method, and the ring/VM must already be attached to the same live context.
 * Buffers may be sub-ranges of a live VM mapping but never a different IOVA,
 * unmapped handle, table pool or a range that includes unreadable bytes.
 * A failed ring commit that poisons the ring keeps every reference and the
 * submit object unusable; only an independent reset may reclaim them. */
class ZornGen7DirectSubmit26 final {
    struct Job {
        uint32_t fence=0;
        size_t count=0;
        uint64_t handles[ZornGen7DirectSubmit26MaxBuffers]{};
        uint32_t queue=0;
        bool active=false;
    } jobs_[8];
    ZornGen7DirectVm26 *vm_=nullptr;
    NativeAdrenoRing *ring_=nullptr;
    ZornGen7PresentProgress26 *present_=nullptr; // real retained ring owner storage
    ZornGen7DirectSubmit26Stats stats_{};
    bool attached_=false,poisoned_=false;
    uint32_t audit_tick_=0;   /* submissions since attach; every eighth one audits its IB lines */
    /* All methods are serialized by the issuer. Keep larger batches off the
     * kernel stack, as in the upstream 128-IB submit path. */
    uint64_t scratch_handles_[ZornGen7DirectSubmit26MaxBuffers]{};
    uint32_t scratch_words_[ZornGen7DirectSubmit26MaxBuffers*4]{};
    Job *find(uint32_t fence);
    Job *free();
    IOReturn release(Job &);
    IOReturn poison();
public:
    ZornGen7DirectSubmit26()=default;
    ~ZornGen7DirectSubmit26()=default;
    ZornGen7DirectSubmit26(const ZornGen7DirectSubmit26 &)=delete;
    ZornGen7DirectSubmit26 &operator=(const ZornGen7DirectSubmit26 &)=delete;
    IOReturn attach(ZornGen7DirectVm26 *,NativeAdrenoRing *,ZornGen7PresentProgress26 *);
    /* Refuses while jobs are outstanding or poisoned; the caller must have
     * stopped the GPU and observed every fence before calling this. */
    IOReturn detach();
    /* queue is bookkeeping for one shared ring; it never reorders or isolates
     * submissions and is validated by the caller's open queue set. */
    IOReturn submit(const ZornGen7DirectSubmit26Buffer *,size_t,uint32_t queue,
        uint32_t *fence);
    bool queueOutstanding(uint32_t queue) const;
    /* Queues [first, first+count): whether any of their jobs is outstanding, and a wait for every one of them (oldest first) that
     * leaves other queues' jobs alone. Each client of the shared ring owns one such range. */
    bool rangeOutstanding(uint32_t first,uint32_t count) const;
    IOReturn waitRange(uint32_t first,uint32_t count,const NativeAdrenoRingClock *,uint32_t timeout_us);
    /* Retires (without waiting) every job whose fence the CP has already passed, so completed work never pins buffers or
     * job slots just because nobody called wait(). */
    IOReturn retireCompleted();
    /* Waits for every outstanding job in submission order and retires its references. */
    IOReturn waitAll(const NativeAdrenoRingClock *,uint32_t timeout_us);
    /* Polls the CP timestamp; on completion retires every buffer reference. A fence whose job was already retired (by
     * wait or retireCompleted) is checked against the ring and succeeds once the CP has passed it. */
    IOReturn wait(uint32_t fence,const NativeAdrenoRingClock *,uint32_t timeout_us);
    /* Wait for an earlier fence without touching job references; a timeout
     * leaves every job and reference exactly as they were. */
    IOReturn observeFence(uint32_t fence,const NativeAdrenoRingClock *,uint32_t timeout_us);
    bool poisoned() const {return poisoned_;}
    size_t outstanding() const;
    ZornGen7DirectSubmit26Stats stats() const {return stats_;}
};
#endif

/* SPDX-License-Identifier: MIT */
#ifndef ZORN_GEN7_DIRECT_VM26_H
#define ZORN_GEN7_DIRECT_VM26_H
#include "Adreno740/NativeAdrenoMemory.h"
#include "ZornGen7SmmuTablePages26.h"
#include "sparse/ArmSmmu4KStreams.h"
// Implemented by the same retained native domain,under its actual gate.
// full=true checks the complete effective native match set/conflicts;false
// checks its own unchanged route. Both verify real context/fault/power state.
struct ZornGen7DirectVm26Routes {
    void *cookie;unsigned bank;
    ZornSmmuSparse4KStatus (*observe)(void *,bool full);
    ZornSmmuSparse4KStatus (*fault)(void *);
    // Hardware-backed routes stop and release every GPU bus master around
    // each live SMMU page-table mutation. Both callbacks run under the real
    // owning driver's serialized gate and must fail closed.
    ZornSmmuSparse4KStatus (*haltForTableUpdate)(void *);
    ZornSmmuSparse4KStatus (*releaseAfterTableUpdate)(void *);
    // Submission and fence retirement enter the same owner gate as map/unmap.
    // beginSubmission locks and validates the live route; endSubmission
    // releases exactly that acquisition. Waiting for a GPU fence must happen
    // outside this gate so IRQ/completion delivery can continue.
    IOReturn (*beginSubmission)(void *);
    void (*endSubmission)(void *);
};
struct ZornGen7DirectVm26Region {
    ZornGen7SmmuTablePages26 *tables;
    const ZornSmmuSparse4KLiveArena *arena;
    ZornSmmuSparse4KLiveState *state;
};
struct ZornGen7DirectVm26Result {
    ZornSmmuSparse4KStatus operation,quarantine;
    size_t completed_spans;
    bool complete;
};
/* Kernel-owned BO mapping transactions, not a userspace ABI or GPU scheduler.
 * Attach only under the actual bank/ASID/stream and powered-MMIO lease, with
 * fault IRQ handling installed and empty native4K arenas already active.
 * The real table allocations, context/streams and BO objects remain retained
 * by the owning driver. No implicit destructor cleanup; detach must succeed.
 * Serialize all methods, table updates and submission under the DRIVER gate.
 * ALL masters must stay genuinely quiesced through each map/unmap transaction;
 * hardware-backed routes provide a verified halt/release pair around the
 * actual table update and TLBSYNC.
 * Job counts are lifetime accounting; neither they nor these APIs are fences.
 * Each active region is audited, including the unmodified peer. Partial failure
 * keeps every old/new BO reference, poisons both arenas and attempts to FAULT
 * only the owned streams. Uncertain resources require independent real reset.
 * No VM may be advertised to apps until per-client isolation, submission
 * validation/protection, genuine IRQ fences and reset are implemented. */
/* One table for every client's mappings: 1024 filled up once the render server primed its shaders (int-237: BoMap refused with
 * kIOReturnNoResources at objects=1024, Turnip wrote through a NULL command stream and backboardd crashed). */
enum : size_t {ZornGen7DirectVm26MaxObjects=4096};
/* Board hook for sampleWord(): reads one aligned word of physical memory through a fresh uncached mapping; 0 on success. */
extern "C" int (*zorn_direct_dram_read32)(uint64_t physical,uint32_t *value);
/* The board's reader through the kernel's cacheable physical aperture (null on the host: the BO's own mapping is read). */
extern "C" int (*zorn_direct_cached_read32)(uint64_t physical,uint32_t *value);
/* Board hook for auditRange(): [physical, physical+bytes), whole 64-byte lines inside one page, as the cacheable physical aperture and
 * DRAM (a fresh uncached mapping) read it. A line that differs is cleaned and invalidated and DRAM read again: when DRAM then holds the
 * cached copy the line was dirty (*dirty), when DRAM is unchanged it was a stale clean copy (*stale). 0 on success. */
extern "C" int (*zorn_direct_line_audit)(uint64_t physical,size_t bytes,uint32_t *dirty,uint32_t *stale);
class ZornGen7DirectVm26 final {
    static IOReturn bindVisibility(ZornGen7SmmuTablePages26 *,ZornSmmuSparse4KLiveVisibility *);
    static bool validBinding(const ZornGen7DirectVm26Region &,unsigned);
    struct Mapping {
        NativeAdrenoMemory *memory=nullptr;
        uint64_t handle=0,iova=0;
        size_t spans=0,mapped_spans=0;
        unsigned permissions=0,writeback=0,shareability=0,jobs=0;
    };
    Mapping *mappings_=nullptr;
    ZornGen7DirectVm26Region regions_[2]{};
    ZornSmmuSparse4KLiveVisibility visibility_[2]{};
    ZornSmmuSparse4KIo io_{};
    ZornSmmuSparse4KContextConfig *context_=nullptr;
    ZornGen7DirectVm26Routes *streams_=nullptr;
    ZornSmmuSparse4KRange *ranges_=nullptr;
    // CPU-only workspace shared by serialized preflight and live-table checks.
    // Capacity matches the fixed span budget; no allocation on the map path.
    // A call-local arena view carries it; caller metadata can be sealed by GMU.
    uint32_t *alias_scratch_=nullptr;
    size_t capacity_=0,lower_count_=0,upper_count_=0,objects_=0;
    // IBs name other BOs through GPU addresses, not through the submit ABI's
    // IB list. Each unretired submission therefore pins the entire namespace:
    // existing mapping references keep every backing object alive. An append
    // may add a new mapping; no mapping may leave while any job can use it.
    uint32_t submission_resources_=0;
    friend class ZornGen7DirectSubmit26;
    IOReturn holdSubmissionResources();
    IOReturn cancelUnpublishedSubmissionResources();
    IOReturn retireSubmissionResourcesAfterCompletion();
    unsigned budget_=0;
    uint64_t next_handle_=1;
    bool attached_=false,poisoned_=false,distrust_write_combined_=false;
    bool per_page_tlb_invalidation_=true;
    ZornGen7DirectVm26Result result_{};
    ZornSmmuSparse4KLiveRegion region(unsigned,ZornSmmuSparse4KLiveArena &) const;
    ZornSmmuSparse4KStatus observe() const;
    /* Attach audits every table; each update checks the descriptors it changes.
     * Periodic checks scan routes/context for conflicts without another whole
     * table walk under the issuer lock. auditLive() remains an explicit audit. */
    ZornSmmuSparse4KStatus observeStreamsOnly() const;
    ZornSmmuSparse4KStatus observeCheap();
    unsigned since_audit_=0;
    IOReturn fail(ZornSmmuSparse4KStatus);
    void freeMetadata();
    Mapping *find(uint64_t);
    void insert(size_t,unsigned);
    void erase(size_t,size_t,unsigned);
    IOReturn preflight(const NativeAdrenoMemory *,unsigned,uint64_t,unsigned,unsigned,unsigned) const;
public:
    ZornGen7DirectVm26()=default;
    ~ZornGen7DirectVm26()=default;
    ZornGen7DirectVm26(const ZornGen7DirectVm26 &)=delete;
    ZornGen7DirectVm26 &operator=(const ZornGen7DirectVm26 &)=delete;
    IOReturn attach(const ZornSmmuSparse4KIo *,ZornSmmuSparse4KContextConfig *,ZornGen7DirectVm26Routes *,
        const ZornGen7DirectVm26Region *lower,const ZornGen7DirectVm26Region *upper,
        size_t max_spans,unsigned poll_budget);
    /* Adopt actual prepared boot mappings in the same live arena. The board
     * retains those BOs separately until reset; no client handle can unmap them.
     * Every seed is exact-graph audited before allocation or attachment.
     * Boards with expensive guarded MMIO may choose ASID-wide unmap instead
     * of the per-page optimization. Both wait for TLBSYNC before retirement. */
    IOReturn attachSeeded(const ZornSmmuSparse4KIo *,ZornSmmuSparse4KContextConfig *,ZornGen7DirectVm26Routes *,
        const ZornGen7DirectVm26Region *,const ZornGen7DirectVm26Region *,size_t,unsigned,
        const ZornSmmuSparse4KRange *lower_seeds,size_t lower_count,
        const ZornSmmuSparse4KRange *upper_seeds,size_t upper_count,bool per_page_tlb_invalidation=true,
        bool allocate_alias_workspace=true);
    bool perPageTlbInvalidation() const {return per_page_tlb_invalidation_;}
    /* Serialized owner only, before mapping client objects. Allows the board
     * to retain its boot qualification allocation/order, then enable indexing
     * before publishing the provider. Both table audits and alias checks stay. */
    IOReturn enableAliasWorkspace();
    IOReturn auditLive() const {return attached_ && !poisoned_ && !observe()?kIOReturnSuccess:kIOReturnNotReady;}
    /* Frees CPU metadata only, with no BOs remaining. Never releases roots,
     * disables a bank or returns the platform lease; board lifecycle owns it. */
    IOReturn detach();
    // Private board lifecycle:after all real client mappings/jobs are gone,
    // remove metadata for the exact immutable seed graph,not its mappings.
    // Actual tables/ASID remain retained by their owner until real TLBSYNC.
    IOReturn detachSeeded(const ZornSmmuSparse4KRange *lower_seeds,size_t lower_count,
        const ZornSmmuSparse4KRange *upper_seeds,size_t upper_count);
    IOReturn findAddress(unsigned upper,size_t bytes,uint64_t alignment,uint64_t *iova) const;
    IOReturn map(NativeAdrenoMemory *,unsigned upper,uint64_t iova,
        unsigned permissions,unsigned writeback,unsigned shareability,uint64_t *handle);
    IOReturn unmap(uint64_t handle);
    IOReturn holdJob(uint64_t handle);
    /* Explicit diagnostic/recovery TLBIALL plus TLBSYNC. Ordinary submission
     * relies on the live mapper's invalid-leaf and synchronous-unmap contract. */
    IOReturn invalidateTlb();
    /* Cleans and invalidates the CPU caches over every mapped BO (whole objects; imported ones through their physical pages), so
     * no CPU cache line can hold data the GPU should see or hide what it wrote. Lines are physically tagged, so this also reaches
     * lines a user mapping of the same pages left behind. int-070 runs it before every submission. */
    IOReturn publishMapped();
    /* The submit path saw a CPU-cached word that DRAM did not hold yet in a client's BO: from now on write-combined BOs are maintained
     * like any other (sticky; the safe behaviour of int-070..097). */
    void distrustWriteCombined() {distrust_write_combined_=true;}
    bool writeCombinedTrusted() const {return !distrust_write_combined_;}
    /* After a submission completed: cleans and invalidates the CPU caches over every GPU-writable imported BO, so the owner's mapping
     * (an IOSurface) reads what the GPU wrote, not a line prefetched while the GPU ran. Jobs name only their IBs, so every such BO
     * is covered. int-071: an imported render target read back 672 of 4096 texels stale. */
    IOReturn acquireImported();
    /* Diagnostic, never a proof of coherence: the 32-bit word at a mapped GPU address as the kernel's cacheable alias reads it
     * and, when the board installed zorn_direct_dram_read32, as DRAM reads it through an uncached mapping (else ~0). */
    IOReturn sampleWord(uint64_t iova,uint32_t *cached,uint32_t *dram) const;
    /* Every line of [iova, iova+bytes) that lies in a write-combined BO, through zorn_direct_line_audit: *dirty counts lines a CPU
     * cache held newer than DRAM (a client view that caches after all; each such line is written back by the audit), *stale clean
     * copies, *lines the lines compared. kIOReturnUnsupported without a board hook. int-099 sampled one word and wrote its line back
     * before reading DRAM, so it could never see a dirty line. */
    /* Before a submission while write-combined BOs are trusted: every page of every mapped write-combined BO that XNU set back to the
     * default attribute is write-combined again (and its lines written back); *reset counts the pages. */
    IOReturn reassertWriteCombined(uint32_t *reset) const;
    IOReturn auditRange(uint64_t iova,size_t bytes,uint32_t *lines,uint32_t *dirty,uint32_t *stale) const;
    /* Read-only description of a live mapping; never pins or extends it. */
    IOReturn describe(uint64_t handle,uint64_t *iova,size_t *bytes,unsigned *permissions) const;
    /* Up to `count` dwords of a mapped kernel-owned BO at a GPU address (through the kernel's own mapping), for the board log. */
    IOReturn peekWords(uint64_t iova,uint32_t *out,size_t count) const;
    /* Only a scheduler's actual successful GPU completion may call this.
     * A timeout, interrupt bit alone or CPU-written timestamp is insufficient. */
    IOReturn retireJobAfterCompletion(uint64_t handle);
    bool hasPendingSubmissionResources() const {return submission_resources_!=0;}
    bool poisoned() const {return poisoned_;}
    size_t objectCount() const {return objects_;}
    size_t spanCount() const {return lower_count_+upper_count_;}
    ZornGen7DirectVm26Result lastResult() const {return result_;}
};
#endif

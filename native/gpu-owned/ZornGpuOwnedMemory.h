/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#ifndef ZORN_GPU_OWNED_MEMORY_H
#define ZORN_GPU_OWNED_MEMORY_H
#include "ZornGpuNativePlatform.h"
class ZornGpuOwnedMemory;
enum {ZGOM_FRESH,ZGOM_PREPARING,ZGOM_CPU_PREPARED,ZGOM_RETAINED_FAILURE};
enum {ZGOM_GATE_PLAN=1,ZGOM_GATE_ALLOCATE,ZGOM_GATE_AFTER_ALLOCATE,
      ZGOM_GATE_SNAPSHOT,ZGOM_GATE_FINISH};
enum {ZGOM_FAILURE_NONE,ZGOM_FAILURE_PLAN,ZGOM_FAILURE_NATIVE,ZGOM_FAILURE_GATE,ZGOM_FAILURE_SHAPE,ZGOM_FAILURE_SNAPSHOT};
typedef IOReturn (*ZornGpuPrepareCheck)(void *cookie,uint64_t epoch,
    const ZornGpuOwnedMemory *owner,unsigned phase,unsigned index);
struct ZornGpuPrepareGate {uint64_t epoch;void *cookie;ZornGpuPrepareCheck check;};
struct ZornGpuMemoryReport {
    uint32_t state,phase,index,failure_source,attempted_mask,backed_mask;
    uint32_t described_mask,quarantined_mask,cleanup_status_unavailable_mask;
    uint32_t output_policy_bits,allocated_bytes,retained_bytes,runtime_complete;
    uint64_t epoch;
    IOReturn returned_status,original_native_status,original_gate_status;
    IOReturn original_snapshot_status;
    uint32_t plan_status,plan_attempted;
    IOReturn allocation_status[8];
    ZornGpuBackingSnapshot snapshots[8];
};
/* CPU-only Gen7 static memory provider. No IOService, GPU, MMIO, IOVA map,
 * device reference publication, firmware loading, cache policy change or
 * teardown. Single serialized prepare per persistent object, including any
 * failure. Keep the object alive across ALL outcomes; default destructor does
 * not free backing. There is deliberately no release/reset/retry interface.
 * Private plan/scratch/eight native objects belong in persistent caller-owned
 * storage, not on a kernel stack. CONSTINIT storage can avoid boot initializers.
 * Caller runs a normal thread holding its real stable gate, with no log/UFS/
 * watchdog lock. Future runtime entry must enforce real original SMP gates;
 * callback success is only an assertion, not hardware qualification.
 * The NativeAdrenoMemory provider may internally clean up its own failed
 * unpublished allocation; already acquired objects are NEVER auto-cleaned by
 * this class. A failed provider cleanup leaves its object/quarantine retained;
 * its secondary cleanup error is not exposed by the existing provider API.
 */
class ZornGpuOwnedMemory final {
    NativeAdrenoMemory memory_[8];
    ZornGpuFirmwarePlan scratch_{},plan_{};
    ZornGpuMemoryReport report_{};
    ZornGpuPrepareGate gate_{};
    IOReturn check(unsigned phase,unsigned index);
    IOReturn fail(unsigned source,IOReturn status);
    void observe(unsigned index);
    struct SnapshotCookie {ZornGpuOwnedMemory *owner;unsigned index;};
    static IOReturn snapshotCheck(void *,uint64_t,const NativeAdrenoMemory *);
public:
    ZornGpuOwnedMemory()=default;
    ~ZornGpuOwnedMemory()=default;
    ZornGpuOwnedMemory(const ZornGpuOwnedMemory &)=delete;
    ZornGpuOwnedMemory &operator=(const ZornGpuOwnedMemory &)=delete;
    /* Fixed public firmware-plan SHA guard always runs before allocation.
     * Exactly8allocations/565248B maximum. Explicit width is an allocation
     * policy, not measured SMMU ID2/OAS. All args and object are stable/disjoint.
     * Invalid arguments before first attempt leave object unchanged. Once a
     * gate/plan attempt starts, all failures retain state; duplicate prepare
     * returns Busy without replacing the original report or error.
     * Native allocate already zeroes/cleans its new CPU-owned RAM through its
     * real provider. No SQE/GMU/AQE or ZAP bytes are copied into those buffers.
     * CPU_PREPARED is not runtime/GPU readiness (runtime_complete always0).
     */
    IOReturn prepare(const ZornGpuBlob images[ZGP_IMAGES],unsigned output_policy_bits,
        const ZornGpuPrepareGate *);
    const ZornGpuMemoryReport &report() const {return report_;}
    const ZornGpuFirmwarePlan &requirements() const {return plan_;}
};
#endif

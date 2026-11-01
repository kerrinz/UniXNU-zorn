/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#ifndef ZORN_GPU_NATIVE_PLATFORM_H
#define ZORN_GPU_NATIVE_PLATFORM_H
#include "NativeAdrenoBoard.h"
#include "NativeAdrenoMemory.h"
#include "ZornGpuFirmwarePlan.h"
enum {ZGN_GPU,ZGN_CX_DBGC,ZGN_RSCC,ZGN_CX_MISC,ZGN_QDSS_GFX,ZGN_QDSS_ETR,
      ZGN_QDSS_TMC,ZGN_GMU,ZGN_PDC,ZGN_AO,ZGN_RESOURCES};
struct ZornGpuDtResourceNode {
    const uint8_t *reg;size_t reg_bytes;
    const char *names;size_t names_bytes;
    uint32_t address_cells,size_cells;
};
struct ZornGpuResourceDescription {
    NativeAdrenoWindow resources[ZGN_RESOURCES];
    uint32_t overlaps[ZGN_RESOURCES];
    uint32_t descriptor_valid,runtime_complete;
};
enum {ZGN_MISSING_OPERATION_SCOPES=1,ZGN_MISSING_POWER_CLOCKS=2,
      ZGN_MISSING_SMMU_OWNERSHIP=4,ZGN_MISSING_ZAP_AUTH=8,
      ZGN_MISSING_BOARD_VOTES=16,ZGN_MISSING_LIVE_HFI=32,
      ZGN_MISSING_RUNTIME_ALLOCATIONS=64,ZGN_MISSING_BACKING_BINDINGS=128};
struct ZornGpuNativeRequirements {
    uint32_t backing_count,static_backing_bytes,log_bytes,hfi_bytes;
    uint32_t pending_fixed_iova,pending_dynamic_iova,persistent_requests;
    uint32_t missing,runtime_complete;
};
typedef IOReturn (*ZornGpuBackingLeaseCheck)(void *cookie,uint64_t epoch,
    const NativeAdrenoMemory *owner);
struct ZornGpuBackingLease {
    uint64_t epoch;void *cookie;ZornGpuBackingLeaseCheck check;
};
struct ZornGpuBackingSnapshot {
    const NativeAdrenoMemory *owner;
    void *cpu;uint64_t physical,bytes,epoch;
    uint32_t span_count,device_references,write_combined,runtime_complete;
};
/* Descriptive K80 fixed-profile binding, no IOService / hardware operations.
 * Uses actual common NativeAdrenoBoard parser but on local arrays because its
 * failure may already have filled an earlier element. Unknown/missing/duplicate
 * names, unexpected range/size, bad cells or aliases reject without output.
 * Cached FDT ranges are not mapped, powered or acquired. Parent apertures can
 * overlap: overlap masks retain this instead of claiming exclusive access.
 * Caller owns serialized stable disjoint inputs/output. */
IOReturn ZornGpuDescribeResources(const ZornGpuDtResourceNode *gpu,
    const ZornGpuDtResourceNode *gmu,ZornGpuResourceDescription *);
/* Borrowed input plan must come UNCHANGED from public fixed-SHA
 * ZornGpuBuildFirmwarePlan. This function checks integration shape only and
 * does not reauthenticate firmware. No allocation or hidden reset/release.
 * Returns requirements with all presently unimplemented platform providers
 * explicit, never a runnable ShengGmuConfig; runtime_complete always0. */
IOReturn ZornGpuDescribeRequirements(const ZornGpuResourceDescription *,
    const ZornGpuFirmwarePlan *,ZornGpuNativeRequirements *);
/* Observe an actual NativeAdrenoMemory using public getters, not guessed
 * private offsets or a fabricated PA. No allocate/hold/map/cache/release call.
 * Caller holds real stopped/exclusive/stable backing lease for whole call and
 * keeps object/spans alive. Callback checks that held lease before/after and
 * must return promptly without reentry/mutation; its zero is NOT hardware
 * ownership/quiescence/coherence proof. Retain ownership after any failure.
 * Width is explicit caller policy, NOT observed SMMU ID2/OAS; no default40.
 * Contiguous backing only at this phase. Snapshot unchanged on failure;
 * runtime_complete0 even on success. No IOVA is assigned from PA. */
IOReturn ZornGpuSnapshotNativeBacking(const NativeAdrenoMemory *,size_t expected_bytes,
    unsigned policy_output_bits,const ZornGpuBackingLease *,ZornGpuBackingSnapshot *);
#endif

/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#ifndef ZORN_GPU_STARTUP_PLAN_H
#define ZORN_GPU_STARTUP_PLAN_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
enum {ZG_OK,ZG_INVALID};
enum {ZG_VERSION_UNKNOWN,ZG_VERSION_FILE,ZG_VERSION_LIVE_ASSERTED};
enum {ZG_PERF_TABLE,ZG_BW_TABLE,ZG_HWSCHED,ZG_KPROF,ZG_CORE_START,
      ZG_CONTEXT_QUERY,ZG_PREEMPT,ZG_AQE,ZG_START,ZG_STAGE_COUNT};
enum {ZG_ACK_UNKNOWN,ZG_ACK_ZERO_WORD2,ZG_ACK_V5,ZG_ACK_SENTINEL};
enum {ZG_NEED_LIVE_VERSION=1,ZG_NEED_VERSION_SUPPORT=2,ZG_NEED_BOARD_VOTES=4,
      ZG_NEED_PREEMPT_POLICY=8,ZG_NEED_NEWER_MINOR=16};
typedef struct {uint32_t raw,source;uint64_t epoch;} ZGVersion;
typedef struct {uint32_t supplied,enable,data;} ZGPreemptPolicy;
typedef struct {
    uint32_t stage,id,payload_words,payload[3],ack_contract,query,missing;
    uint32_t packet_ready,runtime_complete;ZGVersion version;
} ZGStartupStep;
/* Pure plans for a nine-step MINIMAL cold-start reference subset. Not the
 * entire OEM startup: optional features, warmboot and board tables unresolved.
 * Version must be explicitly live-observed/epoch-bound by the external caller.
 * This flag is an assertion, NOT hardware evidence; FILE/UNKNOWN never select
 * protocol. Only the pinned Gen7 major2 family is considered. PERF/BW remain
 * unavailable until independent K80 OPP/command-DB provenance is implemented.
 * Preemption is an explicit board policy, not copied from houji's disabled
 * preemption. runtime_complete always0. No transport or hardware calls.
 * Caller serializes and owns stable disjoint arguments/output; errors do not
 * write output. A valid plan may have missing bits and packet_ready0. */
int ZGPlanStartupStep(uint32_t stage,const ZGVersion *,const ZGPreemptPolicy *,ZGStartupStep *);
enum {ZG_ACK_MATCHED_ZERO,ZG_ACK_MATCHED_VALUE,ZG_ACK_MATCHED_SENTINEL,
      ZG_ACK_REJECTED,ZG_ACK_NO_ENTRY,ZG_ACK_TIMEOUT,ZG_ACK_MISMATCH,
      ZG_ACK_MALFORMED,ZG_ACK_CONTRACT_UNAVAILABLE};
typedef struct {
    uint32_t count,raw[19],assessment,has_value,value,status_present,status;
} ZGAckAssessment;
/* Preserves the whole supplied (<=19 words) raw ACK even when semantic status
 * is unavailable/rejected. Does not consume/notify/clear pending or infer queue
 * lifetime. A positive v5 query is data; positive feature_ctrl rc stops startup.
 * Legacy generic uses word2==0 and ignores word3. V5 requires word3 to exist.
 * START uses its actual check_ack_failure sentinel, not generic zero rule.
 * Supplied plan is rederived/checked rather than trusting a mutated contract.
 * expected_header must match this step's size/id/CMD, allowing RECORD bit19.
 * Bounds/alias arguments invalid => output unchanged. Assessment is not a
 * success ACK generator; software fixtures are not firmware evidence. */
int ZGAssessStartupAck(const ZGStartupStep *,uint32_t expected_header,
    const uint32_t *raw,size_t count,ZGAckAssessment *);
enum {ZG_MEM_WIRE=1,ZG_MEM_VERSION=2,ZG_MEM_LENGTH=4,ZG_MEM_FLAGS=8,
      ZG_MEM_KIND=16,ZG_MEM_SIZE=32,ZG_MEM_ALIGNMENT=64,ZG_MEM_RANGE=128,
      ZG_MEM_MMIO_REVIEW=256};
enum {ZG_PATH_UNKNOWN,ZG_PATH_GMU_RAM,ZG_PATH_GPU_GLOBAL,ZG_PATH_HW_FENCE,
      ZG_PATH_MEMSTORE,ZG_PATH_IPC_CORE};
enum {ZG_REQUIRE_GMU_MAP=1,ZG_REQUIRE_GPU_MAP=2,ZG_REQUIRE_SECURE=4,
      ZG_REQUIRE_FIXED_RESOURCE=8,ZG_REQUIRE_PREALLOCATED=16,
      ZG_REQUIRE_HOST_ACCESS=32,ZG_REQUIRE_HOST_INIT=64};
enum {ZG_ACCESS_READ=1,ZG_ACCESS_WRITE=2,ZG_ACCESS_PRIV=4}; /* logical, not PTE bits */
typedef struct {
    uint32_t raw_count,raw[11],version,decoded,issues,path,requirements;
    uint64_t gpu_addr,rounded_size;
    uint32_t flags,kind,host_handle,gmu_handle,gmu_addr,size,align;
    uint32_t va_alignment,size_alignment,format_available,runtime_complete;
    uint32_t gmu_access,gpu_access,gmu_cacheable;
} ZGMemRequirement;
/* One fixed-capacity request requirement, not an allocator/reply/lease.
 * Exact legacy10 words/version0 or current11/version1. OEM copies any positive
 * version as current; this candidate conservatively preserves but refuses
 * unknown positive versions. Raw always retained for a bounded1..11-word input,
 * including wrong-type/truncated/unknown input; issues/decoded distinguish it.
 * Unknown fields never become zero-sized successful memory. align0 legacy is
 * derived from the OEM zero-initialized descriptor, not fabricated wire data.
 * Declared GPU/GMU addresses and both handles remain original requests, NOT
 * owned mappings or host success handles. Positive size/alignment/range checks
 * classify requirements only. Even format_available1 has runtime_complete0.
 * No protocol response, hardware address allocation, MMIO or SMMU selection. */
int ZGPlanMemAlloc(const uint32_t *raw,size_t count,ZGMemRequirement *);
#ifdef __cplusplus
}
#endif
#endif

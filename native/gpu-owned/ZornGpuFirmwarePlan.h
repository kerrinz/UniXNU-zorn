/* SPDX-License-Identifier: MIT */
#ifndef ZORN_GPU_FIRMWARE_PLAN_H
#define ZORN_GPU_FIRMWARE_PLAN_H
#include "AdrenoFirmware.h"
#include <stddef.h>
#include <stdint.h>

enum ZornGpuPlanStatus { ZGP_OK, ZGP_ARGUMENT, ZGP_ALIAS, ZGP_HASH, ZGP_FORMAT,
    ZGP_REQUIREMENT, ZGP_RANGE, ZGP_CAPACITY };
enum ZornGpuImage { ZGP_GMU, ZGP_SQE, ZGP_AQE, ZGP_ZAP, ZGP_IMAGES };
struct ZornGpuBlob { const uint8_t *data; size_t bytes; };
struct ZornGpuLimits { uint32_t blocks, backings, backing_bytes, hfi_bytes; };
struct ZornGpuRequest {
    uint32_t address, bytes, type, region, persistent, backing_index;
};
struct ZornGpuBacking {
    uint32_t iova, bytes, region, fixed_iova, persistent_requested, purpose;
};
struct ZornGpuQueue { uint32_t id, priority, offset, bytes; };
struct ZornGpuFirmwarePlan {
    AdrenoFirmwareBlock blocks[64];
    ZornGpuRequest requests[64];
    ZornGpuBacking backings[16];
    ZornGpuQueue queues[17];
    uint32_t block_count, request_count, backing_count, backing_bytes;
    uint32_t payload_count, persistent_requests;
    uint32_t hfi_table_bytes, hfi_queue_offset, hfi_request_bytes, hfi_backing_bytes;
    uint32_t log_backing_bytes, queue_count, sqe_offset, sqe_bytes, aqe_offset, aqe_bytes;
    uint32_t zap_requires_authentication, runtime_complete;
};
/* Immutable, disjoint file blobs; exclusive disjoint scratch/output. No I/O,
 * allocation, mapping, queue writes, authentication, firmware execution or
 * global state. Output is unchanged on failure; scratch may change. File SHAs
 * identify one stock package, not authenticating firmware or installed state.
 * Backings are requirements, never physical addresses or established leases.
 * Queue facts follow a pinned OEM reference, not a stock wire-ABI attestation.
 * runtime_complete remains zero: further HWSCHED allocations/platform work
 * are outside this firmware-layout subset. */
ZornGpuPlanStatus ZornGpuBuildFirmwarePlan(const ZornGpuBlob images[ZGP_IMAGES],
    const ZornGpuLimits *, ZornGpuFirmwarePlan *scratch, ZornGpuFirmwarePlan *output);
#endif

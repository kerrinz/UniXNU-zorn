/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#ifndef ZORN_GPU_GMU_EXTENT_H
#define ZORN_GPU_GMU_EXTENT_H
#include "ZornGpuStartupPlan.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
 uint64_t requested_bytes,backing_bytes,reservation_bytes,unmapped_tail_bytes;
 uint32_t va_alignment,size_alignment;
} ZGGmuExtent;
/* Pure size-consistency check for a supplied decoded Gen7 request and supplied
 * backing/reservation byte counts. No address selection, allocation, mapping,
 * provider call or hardware eligibility. The counts are caller data, not a
 * native observation. This is only the ordinary GMU RAM/GPU-global import size
 * subset; fixed/secure/preallocated resources need their separate providers.
 * The reservation rounds the BACKING length, not just the original request.
 * Its unbacked tail must remain reserved by a real future VMA owner; it is not
 * a mapped payload range. Valid stable disjoint inputs/output are required.
 * On rejection output is unchanged. No query/HFI/log encoding is defined. */
int ZGCheckGmuExtent(const ZGMemRequirement*,uint64_t backing_bytes,
 uint64_t reservation_bytes,ZGGmuExtent*);
#ifdef __cplusplus
}
#endif
#endif

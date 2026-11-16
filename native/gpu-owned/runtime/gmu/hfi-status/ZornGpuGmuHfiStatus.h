/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#ifndef ZORN_GPU_GMU_HFI_STATUS_H
#define ZORN_GPU_GMU_HFI_STATUS_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Supplied scalars from the reference hwsched domain, never native observations.
 * Bit sets describe source branches, not pending work/completion or permission.
 * No register offsets, clear/mask API, callbacks or packet/queue operations. */
typedef struct {
    uint32_t raw;
    uint32_t supplied_software_mask;
    uint32_t effective_for_reference_branches;
    uint32_t msgq_left_to_inline;
    uint32_t worker_branch_bits;
    uint32_t cm3_fault_branch_bit;
    uint32_t ignored_high_bits_by_reference;
    uint32_t unhandled_by_reference;
    uint32_t without_direct_branch;
} ZGGmuHfiStatus;
enum { ZGHFI_STATUS_OK = 0, ZGHFI_STATUS_INVALID = 1 };
/* Only output shape validation and integer classification. Both arguments must
 * already be caller-supplied CPU data. No output means IRQ_HANDLED/native ready,
 * ACK receipt, retired command/fence, OOB completion or hardware ownership.
 * CM3 handling in this exact source has no auxiliary status read; none is
 * fabricated here. AO fence auxiliary data belongs to the separate AO domain. */
int ZGClassifyGmuHfiStatus(uint32_t raw, uint32_t supplied_software_mask,
                         ZGGmuHfiStatus *out);
#ifdef __cplusplus
}
#endif
#endif

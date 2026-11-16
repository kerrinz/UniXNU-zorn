/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#ifndef ZORN_GPU_GMU_AO_STATUS_H
#define ZORN_GPU_GMU_AO_STATUS_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
enum {ZGAO_OK,ZGAO_INVALID};
typedef struct {
 uint32_t raw,watchdog_bite,ahb_fence_error,host_ahb_bus_error;
 uint32_t unhandled_by_reference,needs_ahb_fence_status;
} ZGGmuAoStatus;
/* Pure classification of a SUPPLIED scalar in the pinned Gen7 GMU AO status
 * domain, not a register read or observation. No interrupt ack/mask, watchdog
 * action, NMI, fence completion, IRQ_HANDLED result or stop/ownership proof.
 * The reference handles bits0/3/5; every other bit stays unhandled here, even
 * named RSCC/DBD bits1/4. AHB-fence error is unrelated to the HW_FENCE Tx/Rx
 * provider or native CP timestamp completion. Its auxiliary status is not
 * fabricated: needs_ahb_fence_status requests separate real observation.
 * Caller supplies a valid stable aligned output; invalid shape leaves it alone.
 * This private CPU struct defines no firmware/query/HFI/log wire encoding. */
int ZGClassifyGmuAoStatus(uint32_t,ZGGmuAoStatus*);
#ifdef __cplusplus
}
#endif
#endif

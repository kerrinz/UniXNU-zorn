// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include <stdint.h>
#include <stdbool.h>
#include <mach/kern_return.h>
// Native-only observations from the actual masked attach. Fields are valid
// only when their readMask bit is set;no additional MMIO read by a getter.
typedef struct ZornGicSpiObservation26 {
    uint32_t readMask,intid,control,requestedType,configuration,enabled,group,modifier,priority;
    uint64_t requestedRoute,route;
} ZornGicSpiObservation26;
#ifdef __cplusplus
extern "C" {
#endif
kern_return_t gic_v3_spi_attach_masked_observed(uint32_t,bool,void (*)(void *,uint32_t),void *,ZornGicSpiObservation26 *);
kern_return_t gic_v3_spi_attach_boot_cpu_masked_observed(uint32_t,bool,void (*)(void *,uint32_t),void *,ZornGicSpiObservation26 *);
kern_return_t gic_v3_spi_attach_smmu_boot_cpu_masked_observed(uint32_t,bool,void (*)(void *,uint32_t),void *,ZornGicSpiObservation26 *);
#ifdef __cplusplus
}
#endif

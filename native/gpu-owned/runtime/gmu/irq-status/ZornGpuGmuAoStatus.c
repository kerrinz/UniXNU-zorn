/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include "ZornGpuGmuAoStatus.h"
#include <stddef.h>
int ZGClassifyGmuAoStatus(uint32_t raw,ZGGmuAoStatus *out){
 if(!out||(uintptr_t)out%_Alignof(ZGGmuAoStatus)||(uintptr_t)out>UINTPTR_MAX-(sizeof(*out)-1))return ZGAO_INVALID;
 const uint32_t watchdog=UINT32_C(1)<<0,fence=UINT32_C(1)<<3,ahb=UINT32_C(1)<<5;
 ZGGmuAoStatus status={raw,!!(raw&watchdog),!!(raw&fence),!!(raw&ahb),raw&~(watchdog|fence|ahb),!!(raw&fence)};
 *out=status;return ZGAO_OK;
}

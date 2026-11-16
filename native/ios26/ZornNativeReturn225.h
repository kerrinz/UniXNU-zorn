// SPDX-License-Identifier: MIT
#pragma once
#include <stdint.h>
// Internal request identity never leaves the kernel; telemetry exports only counters/method/results.
typedef struct {uintptr_t key;uint32_t sequence,method,stage,runSeen,runRaw,externalRaw,overlaps,rejected;} ZornNativeReturn225;
#ifdef __cplusplus
static inline bool zorn_native_return225_event(ZornNativeReturn225 &s,uintptr_t key,uint32_t method,uint32_t stage,uint32_t raw){
 if(!key || !method || method>17 || stage<1 || stage>3){if(s.rejected!=UINT32_MAX)++s.rejected;return false;}
 if(stage==1){
  if(s.sequence==UINT32_MAX){if(s.rejected!=UINT32_MAX)++s.rejected;return false;}
  if(s.sequence && s.stage!=3 && s.overlaps!=UINT32_MAX)++s.overlaps;
  ++s.sequence;s.key=key;s.method=method;s.stage=1;s.runSeen=0;s.runRaw=0;s.externalRaw=0;return true;
 }
 if(!s.sequence || s.key!=key || s.method!=method || s.stage==3 || (stage==2 && s.stage!=1)){
  if(s.rejected!=UINT32_MAX)++s.rejected;return false;
 }
 if(stage==2){s.runSeen=1;s.runRaw=raw;}else s.externalRaw=raw;
 s.stage=stage;return true;
}
#endif

// SPDX-License-Identifier: MIT
#pragma once
#include <stdint.h>
#include "ZornNativeReturn225.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
 uint32_t flags,calls,method,raw,closeReturned,closeRaw;
 uint64_t prepareMask;
 uint32_t prepareStage,prepareRaw,prepareDetail,prepareEvents,prepareFailed;
} ZornApplicationSession193;
typedef struct {
 uint64_t unique;
 uint32_t pid,flags,calls,method,raw,closeReturned,closeRaw;
 uint32_t attempts,copyErrors,lines,bytes,dropped;
 uint64_t prepareMask;
 uint32_t prepareStage,prepareRaw,prepareDetail,prepareEvents,prepareFailed;
 uint32_t sessions,sessionRejected,reportTerminal;
 ZornApplicationSession193 history[4];
 uint64_t reportUnique;
 uint32_t reportPid,rawBytes,rawDropped;
 char rawText[384];
 char text[384];
 ZornNativeReturn225 nativeReturn225;
} ZornApplicationObservation26;
void zorn26_application_native_return225(uintptr_t,uintptr_t,uint32_t,uint32_t,uint32_t);
void zorn26_application_prepare_event(uintptr_t,uint32_t,uint32_t,uint32_t);
int zorn26_application_snapshot(ZornApplicationObservation26 *);
int zorn26_application_stderr_reserve(uint64_t,uint32_t);
void zorn26_application_stderr_commit(uint64_t,const char *,uint32_t,int);
#ifdef __cplusplus
}
#endif

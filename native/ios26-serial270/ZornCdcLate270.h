// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include "ZornCdcStream201.h"
// Selected late diagnostic producer only. Ordinary0 still means end/error.
#define ZORN_CDC_PENDING270 UINT32_MAX
typedef struct {ZornCdcNext201 next;void *context;bool pending;} ZornCdcLate270;
static inline unsigned zorn_cdc_late_next270(void *cookie,char *out,unsigned cap,unsigned completed) {
    ZornCdcLate270 *p=(ZornCdcLate270 *)cookie;
    const unsigned n=p->next(p->context,out,cap,completed);
    if(n==ZORN_CDC_PENDING270){p->pending=true;return 0;}
    return n;
}
// Reuse the original completion/busy/size/frame/byte checks and stream layout.
// Its invalid0 path mutates no stream counters. Only an explicit late Pending
// marker after a genuine first frame may defer the next transfer until ready.
// No frame/point is acknowledged,no USB START and no in-flight buffer reuse.
static inline int zorn_cdc_next270(ZornCdcStream201 *s,bool ready,bool busy,
    unsigned completed,ZornCdcNext201 next,void *context) {
    if(!next)return -1;
    ZornCdcLate270 proxy={next,context,false};
    const int result=zorn_cdc_next201(s,ready,busy,completed,zorn_cdc_late_next270,&proxy);
    return result<0 && proxy.pending && s && s->frames?0:result;
}

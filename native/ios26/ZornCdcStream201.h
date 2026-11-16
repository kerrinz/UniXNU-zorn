// SPDX-License-Identifier: MIT
#pragma once
#include <stdint.h>
#include <stdbool.h>
// Same source-defined ABI in kernel C producer and C++ observer.
typedef unsigned (*ZornCdcNext201)(void *, char *, unsigned, unsigned);
enum { ZornCdcFrame201 = 3072, ZornCdcFrames201 = 39 };
typedef struct { unsigned frames,total,length; char bytes[ZornCdcFrame201]; } ZornCdcStream201;
// Only called by the sole USB consumer. Buffer reuse requires actual completed
// bulk-IN and no endpoint ownership; never overwrite in-flight DMA source data.
static inline int zorn_cdc_next201(ZornCdcStream201 *s, bool ready, bool busy,
                                  unsigned completed, ZornCdcNext201 next, void *context) {
    if(!s || !next || s->frames>ZornCdcFrames201 || completed>s->length)return -1;
    if(s->frames && (!ready || busy || completed!=s->length))return 0;
    if(s->frames==ZornCdcFrames201)return 0;
    const unsigned n=next(context,s->bytes,sizeof(s->bytes),s->frames);
    if(!n || n>sizeof(s->bytes) || n>119808u-s->total)return -1;
    s->length=n;s->total+=n;++s->frames;return 1;
}

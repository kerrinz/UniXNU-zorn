// SPDX-License-Identifier: MIT
#pragma once
#include <stdbool.h>
#include <stdint.h>

typedef struct {
    bool ready,terminal,progress,regs,dma,pa,configured,dtr,failed,setup;
    bool data_busy,notify;
    unsigned completed,length,frames,total;
} ZornCdcTerminalSoftware230;
typedef struct { uint32_t dctl,dsts,endpoints,command,events; } ZornCdcTerminalHardware230;

static inline bool zorn_cdc_terminal_software230(const ZornCdcTerminalSoftware230 *s) {
    return s && s->ready && !s->terminal && s->progress && s->regs && s->dma && s->pa &&
        s->configured && s->dtr && !s->failed && s->setup && !s->data_busy && !s->notify &&
        s->length>0 && s->length<=3072 && s->completed==s->length &&
        s->frames>0 && s->frames<39 && s->total>=s->length && s->total<=119808;
}
static inline bool zorn_cdc_terminal_hardware230(const ZornCdcTerminalHardware230 *h,
                                                uint32_t remaining,uint32_t control) {
    return h && (h->dctl&(1u<<31)) && !(h->dsts&(1u<<22)) && (h->endpoints&(1u<<3)) &&
        !(h->command&(1u<<10)) && h->events==0 &&
        !(remaining&0xffffffu) && !(remaining>>28) && !(control&1u);
}
static inline bool zorn_cdc_terminal_budget230(unsigned frames,unsigned total,unsigned bytes) {
    return frames>0 && frames<39 && bytes>0 && bytes<=63 &&
        total<=119808 && bytes<=119808-total;
}

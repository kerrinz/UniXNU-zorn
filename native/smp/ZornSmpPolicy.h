// SPDX-License-Identifier: BSD-2-Clause-Patent
// K80 affinity/capacity evidence and actual recovery MIDRs are pinned by host.
#pragma once
#include <stdint.h>
namespace ZornSmpPolicy {
static inline uint32_t midr(unsigned id) {
    return id<2?0x410fd801U:id<7?0x410fd811U:0x410fd821U;
}
static inline bool identity(unsigned id,uint64_t observedMidr,uint64_t mpidr) {
    return id<8 && observedMidr==midr(id) && (mpidr&0xffffff)==id*0x100U;
}
static inline bool complete(uint32_t mask,const uint32_t beats[8],
    const uint32_t timers[8],const uint32_t ipis[8],const uint32_t tlb[8]) {
    if(mask!=255)return false;
    for(unsigned i=0;i<8;++i)if(beats[i]!=10 || !timers[i] || !ipis[i] || tlb[i]!=1)return false;
    return true;
}
}

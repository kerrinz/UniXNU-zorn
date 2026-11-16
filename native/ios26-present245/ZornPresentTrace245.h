/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#pragma once
#include <stdint.h>
// Atomic scalar storage only; writer never waits and snapshot never spins.
// Record correlates one presenter call, not proof the surfaces were GPU-produced.
struct ZornPresentTrace245 {
    uint32_t gate=0,sequence=0,dropped=0,words[16]{};
    void publish(const uint32_t (&input)[16]) {
        uint32_t zero=0;
        if(!__atomic_compare_exchange_n(&gate,&zero,1u,false,__ATOMIC_ACQUIRE,__ATOMIC_RELAXED)) {
            __atomic_fetch_add(&dropped,1u,__ATOMIC_RELAXED);return;
        }
        __atomic_fetch_add(&sequence,1u,__ATOMIC_SEQ_CST);
        for(unsigned i=0;i<16;++i)__atomic_store_n(&words[i],input[i],__ATOMIC_SEQ_CST);
        __atomic_fetch_add(&sequence,1u,__ATOMIC_SEQ_CST);
        __atomic_store_n(&gate,0u,__ATOMIC_RELEASE);
    }
    bool snapshot(uint32_t (&out)[16]) const {
        const uint32_t first=__atomic_load_n(&sequence,__ATOMIC_SEQ_CST);
        if(!first || (first&1u))return false;
        uint32_t copy[16];
        for(unsigned i=0;i<16;++i)copy[i]=__atomic_load_n(&words[i],__ATOMIC_SEQ_CST);
        if(first!=__atomic_load_n(&sequence,__ATOMIC_SEQ_CST))return false;
        for(unsigned i=0;i<16;++i)out[i]=copy[i];return true;
    }
};
extern "C" int zorn_gen7_present_ledger245(uint32_t *,uint32_t *);
extern "C" int zorn26_present_snapshot245(uint32_t (&)[16]);

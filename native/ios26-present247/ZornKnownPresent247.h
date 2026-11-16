/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#pragma once
#include <stdint.h>
// Board-owned source-defined API;these are not Apple selectors or wire layouts.
enum : uint32_t {ZornKnownPresentSubmit247=0x5a470101,ZornKnownPresentQuery247=0x5a470102};
// Existing bounded boot profile:1 keeps software compatibility;2 adds only
// the known-frame test API while retaining that same real software path.
inline bool ZornSoftwareSelected247(unsigned mode){return mode==1 || mode==2;}
inline bool ZornKnownPresentMode247(unsigned mode){return mode==2;}
#ifdef KERNEL
#include "ZornPresentTrace245.h"
// No pointers or surface ownership here. Original present queue retains surfaces.
// Only the existing presenter publishes after its real acquire/show sequence.
struct ZornKnownPresent247 {
    uint64_t armed=0;
    ZornPresentTrace245 trace;
    static uint64_t token(uint32_t frame,uint32_t sid){return (uint64_t(frame)<<32)|sid;}
    bool arm(uint32_t frame,uint32_t sid){
        if(!frame || !sid)return false;uint64_t zero=0;
        return __atomic_compare_exchange_n(&armed,&zero,token(frame,sid),false,__ATOMIC_SEQ_CST,__ATOMIC_SEQ_CST);
    }
    void cancel(uint32_t frame,uint32_t sid){
        uint64_t expected=token(frame,sid);
        __atomic_compare_exchange_n(&armed,&expected,0ULL,false,__ATOMIC_SEQ_CST,__ATOMIC_SEQ_CST);
    }
    bool complete(const uint32_t (&record)[16]){
        uint64_t expected=token(record[1],record[7]);
        if(!record[1] || !record[7] || __atomic_load_n(&armed,__ATOMIC_SEQ_CST)!=expected)return false;
        trace.publish(record);uint32_t copy[16];
        if(!trace.snapshot(copy) || copy[1]!=record[1] || copy[7]!=record[7])return false;
        return __atomic_compare_exchange_n(&armed,&expected,0ULL,false,__ATOMIC_SEQ_CST,__ATOMIC_SEQ_CST);
    }
    bool query(uint32_t frame,uint32_t sid,uint32_t (&out)[16])const{
        uint32_t copy[16];if(!frame || !sid || !trace.snapshot(copy) || copy[1]!=frame || copy[7]!=sid)return false;
        for(unsigned i=0;i<16;++i)out[i]=copy[i];return true;
    }
};
extern "C" int zorn26_known_present_snapshot247(uint32_t (&)[16]);
#endif

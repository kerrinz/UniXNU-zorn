// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include <stdint.h>
#include <string.h>

// Read-only diagnostic identity from the actual admitted openingTask proc.
// No task,port,client pointer or reference is retained or granted here.
class ZornDesktopIdentity271 {
    uint32_t gate_=0,pid_=0,conflict_=0;uint64_t unique_=0;
    bool lock(){uint32_t zero=0;return __atomic_compare_exchange_n(&gate_,&zero,1u,false,__ATOMIC_ACQUIRE,__ATOMIC_RELAXED);}
    void unlock(){__atomic_store_n(&gate_,0u,__ATOMIC_RELEASE);}
public:
    void observe(const char *name,uint64_t unique,uint32_t pid){
        if(!name || strcmp(name,"backboardd") || !unique || !pid)return;
        if(!lock())return;
        if(!unique_){unique_=unique;pid_=pid;}
        else if(unique_!=unique || pid_!=pid)conflict_=1;
        unlock();
    }
    bool snapshot(uint64_t &unique,uint32_t &pid){
        if(!lock())return false;
        const bool ok=unique_ && pid_ && !conflict_;
        if(ok){unique=unique_;pid=pid_;}
        unlock();return ok;
    }
};
extern "C" int zorn26_desktop_identity271(uint64_t *,uint32_t *);

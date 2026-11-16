/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#pragma once
#include "ZornApplicationJournal248.h"
#include <string.h>

// Resident CPU-only storage. No allocation, waiting, DMA or user pointers kept.
// Concurrent writers own disjoint reserved ranges; only completed prefix ranges
// are read. Busy/copy/capacity failures remain sticky and prevent completeness.
struct ZornJournalStore248 {
    struct Slot { uint32_t state,start,bytes,error; } slots[ZornJournalSlots248];
    uint8_t data[ZornJournalCapacity248];
    uint64_t unique,seen;
    uint32_t pid,gate,gaps,reserved,published,records,folded,crc;
    uint32_t exit_state,exit_status;
    void lose(unsigned reason){__atomic_fetch_or(&gaps,reason,__ATOMIC_RELAXED);}
    bool lock(){uint32_t zero=0;return __atomic_compare_exchange_n(&gate,&zero,1u,false,__ATOMIC_ACQUIRE,__ATOMIC_RELAXED);}
    void unlock(){__atomic_store_n(&gate,0u,__ATOMIC_RELEASE);}
    bool begin(uint64_t task,uint32_t process,uint64_t expected,unsigned unsupported,ZornJournalTicket248 &ticket){
        ticket={};if(!task || !process || !expected)return false;
        uint64_t bound=__atomic_load_n(&unique,__ATOMIC_ACQUIRE);
        if(bound && bound!=task)return false;
        if(!lock()){lose(ZornJournalBusy248);return false;}
        bound=__atomic_load_n(&unique,__ATOMIC_RELAXED);
        if(bound && (bound!=task || __atomic_load_n(&pid,__ATOMIC_RELAXED)!=process)){unlock();return false;}
        if(!bound){__atomic_store_n(&pid,process,__ATOMIC_RELAXED);__atomic_store_n(&unique,task,__ATOMIC_RELEASE);}
        if(expected>UINT64_MAX-seen){lose(ZornJournalCapacityLost248);unlock();return false;}seen+=expected;
        if(__atomic_load_n(&exit_state,__ATOMIC_ACQUIRE)){lose(ZornJournalLate248);unlock();return false;}
        if(unsupported){lose(ZornJournalUnsupported248);unlock();return false;}
        if(records==ZornJournalSlots248){lose(ZornJournalSlotsLost248);unlock();return false;}
        uint64_t take=expected;
        if(take>ZornJournalWriteLimit248)take=ZornJournalWriteLimit248;
        if(take>ZornJournalCapacity248-reserved)take=ZornJournalCapacity248-reserved;
        if(take!=expected)lose(ZornJournalCapacityLost248);
        if(!take){unlock();return false;}
        auto &s=slots[records];s.start=reserved;s.bytes=uint32_t(take);s.error=0;
        __atomic_store_n(&s.state,1u,__ATOMIC_RELEASE);
        ticket={records+1,uint32_t(take),data+reserved};reserved+=uint32_t(take);++records;
        unlock();return true;
    }
    void finish(uint32_t ticket,unsigned error){
        if(!ticket || ticket>ZornJournalSlots248){lose(ZornJournalBadToken248);return;}
        auto &s=slots[ticket-1];uint32_t writing=1;
        if(!__atomic_compare_exchange_n(&s.state,&writing,2u,false,__ATOMIC_ACQUIRE,__ATOMIC_RELAXED)){
            lose(ZornJournalBadToken248);return;
        }
        s.error=error;__atomic_store_n(&s.state,3u,__ATOMIC_RELEASE);
    }
    void exit(uint64_t task,uint32_t process,uint32_t status){
        if(!task || task!=__atomic_load_n(&unique,__ATOMIC_ACQUIRE) ||
            process!=__atomic_load_n(&pid,__ATOMIC_RELAXED))return;
        uint32_t zero=0;
        if(!__atomic_compare_exchange_n(&exit_state,&zero,1u,false,__ATOMIC_ACQUIRE,__ATOMIC_RELAXED)){
            lose(ZornJournalBadToken248);return;
        }
        __atomic_store_n(&exit_status,status,__ATOMIC_RELAXED);
        __atomic_store_n(&exit_state,2u,__ATOMIC_RELEASE);
    }
    bool snapshot(uint32_t cursor,void *output,uint32_t capacity,ZornJournalSnapshot248 &out){
        if(!output || !capacity || !lock())return false;
        if(!__atomic_load_n(&unique,__ATOMIC_RELAXED)){unlock();return false;}
        while(folded<records && __atomic_load_n(&slots[folded].state,__ATOMIC_ACQUIRE)==3){
            auto &s=slots[folded];if(s.error)lose(ZornJournalCopyLost248);
            uint32_t c=~crc;
            for(uint32_t i=0;i<s.bytes;++i){c^=data[s.start+i];for(unsigned j=0;j<8;++j)c=(c>>1)^((0u-(c&1u))&0xedb88320u);}
            crc=~c;published+=s.bytes;__atomic_store_n(&s.state,4u,__ATOMIC_RELEASE);++folded;
        }
        if(cursor>published){unlock();return false;}
        uint32_t n=published-cursor;if(n>capacity)n=capacity;if(n>ZornJournalChunk248)n=ZornJournalChunk248;
        memcpy(output,data+cursor,n);
        const bool ended=__atomic_load_n(&exit_state,__ATOMIC_ACQUIRE)==2;
        out={__atomic_load_n(&unique,__ATOMIC_RELAXED),seen,__atomic_load_n(&pid,__ATOMIC_RELAXED),
            reserved,published,records,records-folded,__atomic_load_n(&gaps,__ATOMIC_RELAXED),
            ended?1u:0u,ended?__atomic_load_n(&exit_status,__ATOMIC_RELAXED):0u,crc,cursor,n};
        unlock();return true;
    }
};

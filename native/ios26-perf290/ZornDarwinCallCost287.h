/* SPDX-License-Identifier: MIT */
#ifndef ZORN_DARWIN_CALL_COST287_H
#define ZORN_DARWIN_CALL_COST287_H
#include <stdint.h>
#include <stddef.h>
#include <pthread.h>

/* Private userland observation;the96-word287 wire contract is unchanged.
 * Serialize only counter updates/snapshots,never an IOKit call. Unlike the
 * old trylock update gate,ordinary counter contention loses no RPC records.
 * A real mutex failure still invalidates observation;backend results remain
 * unchanged. The actual exporter samples its clock AFTER acquiring the lock.
 */
struct ZornDarwinCallCost287 {
    enum { Schema=287, Methods=18, Words=96 };
    enum Fault { Clock=1, Saturated=2, Lost=4, UnknownMethod=8 };
    struct Row { uint64_t count=0,total=0,maximum=0,errors=0,timeouts=0; };
    pthread_mutex_t gate=PTHREAD_MUTEX_INITIALIZER;
    uint32_t flags=0;
    uint64_t dropped=0;
    Row rows[Methods]{};

    void fault(uint32_t bits) { __atomic_fetch_or(&flags,bits,__ATOMIC_RELAXED); }
    bool take() { return pthread_mutex_lock(&gate)==0; }
    bool unlock() { return pthread_mutex_unlock(&gate)==0; }
    void lost() {
        uint64_t before=__atomic_load_n(&dropped,__ATOMIC_RELAXED);
        while(before<UINT32_MAX && !__atomic_compare_exchange_n(&dropped,&before,before+1,false,__ATOMIC_RELAXED,__ATOMIC_RELAXED)) {}
        fault(Lost|(before==UINT32_MAX?Saturated:0));
    }
    void add(uint64_t &value,uint64_t amount,uint64_t limit) {
        if(amount>limit-value) { value=limit;fault(Saturated); }
        else value+=amount;
    }
    void record(uint32_t method,int64_t began,int64_t ended,bool error,bool timeout) {
        if(!take()) { lost();return; }
        if(method==0 || method>=Methods) { method=0;fault(UnknownMethod); }
        Row &r=rows[method];add(r.count,1,UINT32_MAX);
        if(began<0 || ended<began)fault(Clock);
        else {
            const uint64_t elapsed=uint64_t(ended)-uint64_t(began);
            add(r.total,elapsed,UINT64_MAX);
            if(elapsed>r.maximum)r.maximum=elapsed;
        }
        if(error)add(r.errors,1,UINT32_MAX);
        if(timeout)add(r.timeouts,1,UINT32_MAX);
        if(!unlock())lost();
    }
    void copyLocked(uint64_t *out,int64_t now) {
        out[0]=Schema;out[1]=Methods;
        out[2]=__atomic_load_n(&flags,__ATOMIC_RELAXED);
        out[3]=__atomic_load_n(&dropped,__ATOMIC_RELAXED);
        out[4]=uint64_t(now);out[5]=0;
        for(unsigned i=0;i<Methods;++i) {
            const Row &r=rows[i];const unsigned at=6+5*i;
            out[at]=r.count;out[at+1]=r.total;out[at+2]=r.maximum;
            out[at+3]=r.errors;out[at+4]=r.timeouts;
        }
    }
    bool finishSnapshot() {
        if(unlock())return true;
        lost();return false;
    }
    bool snapshot(uint64_t *out,uint32_t words,int64_t now) {
        if(!out || words!=Words || now<0 || !take())return false;
        copyLocked(out,now);return finishSnapshot();
    }
    bool snapshotWithClock(uint64_t *out,uint32_t words,int64_t (*clock)()) {
        if(!out || words!=Words || !clock || !take())return false;
        const int64_t now=clock();
        if(now<0) { if(!unlock())lost();return false; }
        copyLocked(out,now);return finishSnapshot();
    }
};
static_assert(ZornDarwinCallCost287::Words==6+5*ZornDarwinCallCost287::Methods,"fixed private scalar snapshot");
#endif

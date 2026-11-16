// SPDX-License-Identifier: MIT
#pragma once
// Diagnostic only: actual source execution requests, sole USB consumer acknowledges
// only the point carried by a frame whose complete bulk-IN transfer has returned.
struct ZornProgressGate203 { unsigned requested,acknowledged,failed; };
static inline bool zorn_gate_begin203(ZornProgressGate203 &g,unsigned point) {
    const unsigned old=__atomic_load_n(&g.requested,__ATOMIC_ACQUIRE);
    if(point<1 || point>6 || point!=old+1 ||
       __atomic_load_n(&g.acknowledged,__ATOMIC_ACQUIRE)!=old ||
       __atomic_load_n(&g.failed,__ATOMIC_ACQUIRE))return false;
    __atomic_store_n(&g.requested,point,__ATOMIC_RELEASE);return true;
}
static inline bool zorn_gate_ack203(ZornProgressGate203 &g,unsigned completedPoint) {
    const unsigned old=__atomic_load_n(&g.acknowledged,__ATOMIC_ACQUIRE);
    if(completedPoint>6 || completedPoint<old || completedPoint>old+1 ||
       completedPoint>__atomic_load_n(&g.requested,__ATOMIC_ACQUIRE) ||
       __atomic_load_n(&g.failed,__ATOMIC_ACQUIRE))return false;
    __atomic_store_n(&g.acknowledged,completedPoint,__ATOMIC_RELEASE);return true;
}
template<class Clock,class Sleep>
static bool zorn_gate_wait203(ZornProgressGate203 &g,unsigned point,
                             unsigned long long deadline,Clock now,Sleep sleep) {
    if(!zorn_gate_begin203(g,point))return false;
    while(__atomic_load_n(&g.acknowledged,__ATOMIC_ACQUIRE)!=point){
        if(now()>=deadline){__atomic_store_n(&g.failed,point,__ATOMIC_RELEASE);return false;}
        sleep();
    }
    return true;
}
extern "C" bool zorn26_gpu_diagnostic_gate203(unsigned point);

// SPDX-License-Identifier: BSD-2-Clause-Patent
// Bounded, default-off coordinate evidence. No changes to reports or mapping.
#pragma once
#include "ZornTouchContacts.h"
namespace ZornTouchTrace {
enum : unsigned {Magic=0x3152545a, Capacity=32, Words=108, Bytes=432};
enum : unsigned {Down=1, Move=2, Up=3};
struct Point {uint32_t ms; uint16_t x,y; uint8_t id,phase,contacts,reason;};
static_assert(sizeof(Point)==12, "touch trace point ABI");
struct Recorder {
    Point points[Capacity]={};
    ZornContacts::Frame previous={};
    uint32_t total=0,frames=0,bad=0,lastMs=0,maxGap=0;
    uint32_t recordedMs[20]={};
    uint16_t recordedX[20]={},recordedY[20]={};
    bool initialized=false;
    void add(const ZornContacts::Contact &p,unsigned phase,unsigned count,uint32_t ms,unsigned reason=0) {
        points[total%Capacity]={ms,p.x,p.y,p.id,uint8_t(phase),uint8_t(count),uint8_t(reason)};
        ++total;recordedMs[p.id]=ms;recordedX[p.id]=p.x;recordedY[p.id]=p.y;
    }
    bool sample(const ZornContacts::Frame &frame,uint32_t ms,bool valid=true,unsigned reason=0) {
        if((initialized && ms<lastMs) || frame.count>10 || reason>2)return false;
        unsigned ids=0;
        for(unsigned i=0;i<frame.count;++i) {
            const auto &p=frame.points[i];
            if(p.id>=20 || p.x>32767 || p.y>32767 || (ids&(1u<<p.id)))return false;
            ids|=1u<<p.id;
        }
        if(initialized && ms-lastMs>maxGap)maxGap=ms-lastMs;
        initialized=true;lastMs=ms;++frames;
        if(!valid){++bad;return true;}
        for(unsigned i=0;i<previous.count;++i) {
            const auto &p=previous.points[i];
            if(!(ids&(1u<<p.id)))add(p,Up,frame.count,ms,reason);
        }
        for(unsigned i=0;i<frame.count;++i) {
            const auto &p=frame.points[i];bool found=false;
            for(unsigned j=0;j<previous.count;++j)if(previous.points[j].id==p.id)found=true;
            int dx=int(p.x)-recordedX[p.id],dy=int(p.y)-recordedY[p.id];
            if(!found)add(p,Down,frame.count,ms);
            else if(dx>=512 || dx<=-512 || dy>=512 || dy<=-512 || ms-recordedMs[p.id]>=1000)
                add(p,Move,frame.count,ms);
        }
        previous=frame;return true;
    }
    void release(uint32_t ms,unsigned reason) {
        for(unsigned i=0;i<previous.count;++i)add(previous.points[i],Up,0,ms,reason);
        previous={};lastMs=ms;
    }
    void publish(uint32_t *shared) const {
        // One producer. Every shared word uses atomics, including the payload;
        // the reader never blocks a worker or accepts a torn point sequence.
        __atomic_fetch_add(shared,1,__ATOMIC_ACQ_REL);
        uint32_t header[11]={Magic,total,total<Capacity?total:Capacity,frames,bad,
            lastMs,maxGap,0,0,1,0};
        for(unsigned i=0;i<11;++i)__atomic_store_n(shared+i+1,header[i],__ATOMIC_RELAXED);
        for(unsigned i=0;i<Capacity;++i) {
            const auto &p=points[i];unsigned at=12+i*3;
            __atomic_store_n(shared+at,p.ms,__ATOMIC_RELAXED);
            __atomic_store_n(shared+at+1,uint32_t(p.x)|(uint32_t(p.y)<<16),__ATOMIC_RELAXED);
            __atomic_store_n(shared+at+2,uint32_t(p.id)|(uint32_t(p.phase)<<8)|
                (uint32_t(p.contacts)<<16)|(uint32_t(p.reason)<<24),__ATOMIC_RELAXED);
        }
        __atomic_fetch_add(shared,1,__ATOMIC_RELEASE);
    }
};
static inline bool snapshot(const uint32_t *shared,uint32_t *out) {
    for(unsigned attempt=0;attempt<3;++attempt) {
        uint32_t before=__atomic_load_n(shared,__ATOMIC_ACQUIRE);
        if(!before || (before&1))continue;
        for(unsigned i=1;i<Words;++i)out[i]=__atomic_load_n(shared+i,__ATOMIC_RELAXED);
        // A full barrier also orders payload reads before the second version
        // read on ARM; acquire alone would not establish that direction.
        __atomic_thread_fence(__ATOMIC_SEQ_CST);
        uint32_t after=__atomic_load_n(shared,__ATOMIC_ACQUIRE);
        if(before==after){out[0]=after;return out[1]==Magic && out[10]==1;}
    }
    memset(out,0,Bytes);out[1]=Magic;out[10]=2; // explicitly unavailable, not a fake empty trace
    return false;
}
}

// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include <stdint.h>
// Sole presenter writer;publication uses the existing Trace245 scalar-atomic
// store. Durations are CPU-clock wall time in us,never GPU timestamp queries.
// LeaseWall includes retry sleeps;LeaseCall is a subset,not additive to it.
struct ZornPresentCost278 {
    enum Cost { Queue,Beat,LeaseWall,LeaseCall,Acquire,Show,Costs };
    enum Stage { Pending=1,Presented=2,Terminal=3,NoPixels=4 };
    enum Fault { ClockReversed=1,Saturated=2,PublicationDropped=4 };
    uint32_t frames=0,frame=0,producer=0,stage=0,attempts=0,pending=0,terminals=0,faults=0;
    uint32_t totals[Costs]{};
    void add(uint32_t &v,uint64_t n){if(n>UINT32_MAX-v){v=UINT32_MAX;faults|=Saturated;}else v+=uint32_t(n);}
    template<class Clock> void measure(Cost c,uint64_t began,uint64_t ended,Clock &clock){
        if(ended<began){faults|=ClockReversed;return;}
        add(totals[c],clock.toMicros(ended-began));
    }
    void attempt(){add(attempts,1);stage=Pending;}
    void result(bool failed,bool completed,bool copied){
        if(failed){add(terminals,1);stage=Terminal;}
        else if(!completed){add(pending,1);stage=Pending;}
        else if(copied){add(frames,1);stage=Presented;}
        else stage=NoPixels;
    }
    void pack(uint32_t (&out)[16],uint32_t uptimeMs,uint32_t dropped=0)const{
        out[0]=278;out[1]=frames;out[2]=uptimeMs;out[3]=frame;out[4]=stage;
        for(unsigned i=0;i<Costs;++i)out[5+i]=totals[i];
        out[11]=attempts;out[12]=pending;out[13]=terminals;
        out[14]=faults|(dropped?PublicationDropped:0);out[15]=producer;
    }
};

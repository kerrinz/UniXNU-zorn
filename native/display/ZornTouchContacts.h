// SPDX-License-Identifier: BSD-2-Clause-Patent
// Experimental THP mutual-capacitance tracking. No proprietary algorithm code.
#pragma once
#include "ZornTouchMatrix.h"
namespace ZornContacts {
struct Contact {uint16_t x,y,strength;uint8_t id;};
struct Frame {unsigned count=0;Contact points[10]={};};
static inline int median(int *p,unsigned n) {
    for(unsigned i=1;i<n;++i){int value=p[i];unsigned j=i;while(j && p[j-1]>value){p[j]=p[j-1];--j;}p[j]=value;}
    return p[n/2];
}
struct Detector {
    uint32_t baseline[720]={};unsigned baselines=0;
    int signal[720]={};uint8_t seen[720]={};uint16_t queue[720]={};
    Frame previous={};unsigned noise=0,threshold=0,peak=0;
    bool add(const uint8_t *raw){if(baselines>=8 || !ZornMatrix::addBaseline(raw,baseline))return false;++baselines;return true;}
    bool decode(const uint8_t *raw,Frame &out) {
        out={};if(!raw || raw[0]!=0xa5 || raw[1]!=0x5f || baselines<4)return false;
        // Wire order is RX-major (18 groups of 40 TX samples). The bound
        // 2026-10-29 portrait six-press capture establishes physical top at
        // low TX. Export both axes from the top-left, without changing X.
        int rowNoise[18]={};
        for(unsigned rx=0;rx<18;++rx) {
            int row[40];
            for(unsigned tx=0;tx<40;++tx){unsigned i=rx*40+tx,v=ZornMatrix::big16(raw+64+2*i);if(v>=32768)return false;row[tx]=int(v)-int((baseline[i]+baselines/2)/baselines);signal[i]=row[tx];}
            int common=median(row,40);
            for(unsigned tx=0;tx<40;++tx){int d=signal[rx*40+tx]-common;row[tx]=d<0?-d:d;signal[rx*40+tx]=-d;}
            rowNoise[rx]=median(row,40);
        }
        noise=median(rowNoise,18);if(noise>300)return false;
        threshold=noise*5;if(threshold<80)threshold=80;peak=0;
        memset(seen,0,sizeof(seen));
        for(unsigned origin=0;origin<720;++origin) {
            if(seen[origin] || signal[origin]<=int(threshold))continue;
            unsigned head=0,tail=1,cells=0,top=0;uint64_t weight=0,sx=0,sy=0;queue[0]=origin;seen[origin]=1;
            while(head<tail) {
                unsigned i=queue[head++],rx=i/40,tx=i%40,w=signal[i]-threshold;++cells;
                if(unsigned(signal[i])>top)top=signal[i];weight+=w;sx+=uint64_t(w)*rx;sy+=uint64_t(w)*tx;
                for(int dr=-1;dr<=1;++dr)for(int dc=-1;dc<=1;++dc) {
                    int nr=int(rx)+dr,nc=int(tx)+dc;if(nr<0 || nr>=18 || nc<0 || nc>=40)continue;
                    unsigned j=nr*40+nc;if(!seen[j] && signal[j]>int(threshold)){if(tail>=720)return false;seen[j]=1;queue[tail++]=j;}
                }
            }
            if(top>peak)peak=top;
            if(cells<2 || cells>120 || top<300 || top<threshold*2 || !weight)continue;
            if(out.count>=10)return false;
            unsigned at=out.count++;out.points[at].strength=static_cast<uint16_t>(top);out.points[at].x=static_cast<uint16_t>((sx*32767+weight*17/2)/(weight*17));
            out.points[at].y=static_cast<uint16_t>((sy*32767+weight*39/2)/(weight*39));
        }
        // Match identifiers by nearest location rather than flood-fill order.
        unsigned used=0,assigned=0;
        for(unsigned step=0;step<out.count;++step) {
            uint64_t best=~uint64_t(0);unsigned a=10,b=10;
            for(unsigned i=0;i<out.count;++i)if(!(assigned&(1u<<i)))
                for(unsigned j=0;j<previous.count;++j)if(!(used&(1u<<j))) {
                    int dx=int(out.points[i].x)-previous.points[j].x,dy=int(out.points[i].y)-previous.points[j].y;
                    uint64_t d=uint64_t(int64_t(dx)*dx+int64_t(dy)*dy);if(d<best){best=d;a=i;b=j;}
                }
            if(a==10 || best>uint64_t(12000)*12000)break;
            out.points[a].id=previous.points[b].id;assigned|=1u<<a;used|=1u<<b;
        }
        unsigned ids=0;for(unsigned i=0;i<out.count;++i)if(assigned&(1u<<i))ids|=1u<<out.points[i].id;
        // Do not reuse an identifier that is being lifted in this frame.
        for(unsigned i=0;i<previous.count;++i)ids|=1u<<previous.points[i].id;
        for(unsigned i=0;i<out.count;++i)if(!(assigned&(1u<<i))) {
            unsigned id=0;while(id<20 && (ids&(1u<<id)))++id;if(id>=20)return false;
            out.points[i].id=static_cast<uint8_t>(id);ids|=1u<<id;
        }
        if(!out.count && peak<threshold)for(unsigned i=0;i<720;++i)
            baseline[i]=static_cast<uint32_t>(int(baseline[i])+int(ZornMatrix::big16(raw+64+2*i))-int((baseline[i]+baselines/2)/baselines));
        previous=out;return true;
    }
};
}

// SPDX-License-Identifier: BSD-2-Clause-Patent
// Fixed geometry from the zorn live FDT; raw MC byte order checked from capture.
#pragma once
#include <stdint.h>
#include <string.h>
namespace ZornMatrix {
enum : unsigned {Rows=40,Columns=18,Cells=720,Header=64,MatrixBytes=1440,RecordBytes=3120};
static inline unsigned big16(const uint8_t *p){return unsigned(p[0])*256+p[1];}
static inline bool addBaseline(const uint8_t *raw,uint32_t *sum) {
    if(!raw || !sum || raw[0]!=0xa5 || raw[1]!=0x5f)return false;
    uint32_t total=0;
    for(unsigned i=0;i<Cells;++i){unsigned v=big16(raw+Header+2*i);if(v>=32768)return false;total+=v;}
    if(total<Cells*1000u || total>Cells*30000u)return false;
    for(unsigned i=0;i<Cells;++i)sum[i]+=big16(raw+Header+2*i);
    return true;
}
static inline bool packPair(uint8_t *raw,const uint32_t *sum,unsigned count) {
    if(!raw || !sum || count<4 || count>8)return false;
    memmove(raw+Header+MatrixBytes,raw+Header,MatrixBytes);
    for(unsigned i=0;i<Cells;++i){unsigned v=(sum[i]+count/2)/count;if(v>=32768)return false;raw[Header+i*2]=v>>8;raw[Header+i*2+1]=v;}
    memset(raw+Header+2*MatrixBytes,0,RecordBytes-(Header+2*MatrixBytes));
    memcpy(raw+Header+2*MatrixBytes,"ZORNCAL1",8);
    return true;
}
}

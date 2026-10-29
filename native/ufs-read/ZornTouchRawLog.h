// SPDX-License-Identifier: BSD-2-Clause-Patent
// A touch-only view of the SAME authorized 4 KiB checkpoint block.
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
namespace ZornTouchLog {
enum : unsigned {Slots=64,Metadata=784,Raw=960,Bytes=3120};
static inline uint16_t crc(const uint8_t *p,unsigned bytes) {
    uint16_t c=0xffff;
    for(unsigned i=0;i<bytes;++i){c^=p[i];for(unsigned b=0;b<8;++b)c=(c>>1)^((c&1)?0x8408:0);}
    return c;
}
static inline bool install(void *block,size_t blockBytes,const uint8_t *raw,size_t bytes,unsigned kind=0) {
    if(!block || blockBytes!=4096 || !raw || bytes!=Bytes || kind>1)return false;
    static_assert(16+Slots*12==Metadata && Raw+Bytes<=4096,"touch log ranges");
    uint8_t *p=static_cast<uint8_t *>(block);
    memset(p,0,4096);memcpy(p,"ZORNLOGC",8);memcpy(p+Metadata,kind?"ZORNTCH2":"ZORNTCH1",8);
    const uint32_t n=Bytes,check=crc(raw,Bytes);
    memcpy(p+Metadata+8,&n,4);memcpy(p+Metadata+12,&check,4);memcpy(p+Metadata+16,&kind,4);memcpy(p+Raw,raw,Bytes);
    return true;
}
}

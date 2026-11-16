// SPDX-License-Identifier: MIT
// Raw text framing only. No interpretation of instructions, addresses or stacks.
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
enum {ZornPanicHeader236=128,ZornPanicFooter236=16,ZornPanicReasonCap236=4096,
      ZornPanicLogCap236=262144,ZornPanicMsgCap236=131072,
      ZornPanicOffset236=0x20000,ZornPanicCapacity236=0x64000,ZornCdcDmaBytes236=0x84000,
      ZornPanicWireLimit236=529408};
enum {ZornReasonTruncated236=1u,ZornReasonFormatError236=2u,ZornReasonPending236=4u,
      ZornLogInvalid236=8u,ZornLogTruncated236=16u,ZornMsgInvalid236=32u,
      ZornMsgTruncated236=64u,ZornMsgConcurrent236=128u,ZornLogMissing236=256u,
      ZornMsgMissing236=512u,ZornReasonMissing236=1024u};
typedef struct {
    const char *reason;unsigned reason_bytes,reason_required,reason_state;
    const char *panic;unsigned panic_bytes;
    const char *messages;unsigned message_size,message_index;
    unsigned flags;
} ZornPanicInput236;
static inline void zorn_panic_le236(uint8_t *out,unsigned off,uint32_t value){
    for(unsigned i=0;i<4;++i)out[off+i]=(uint8_t)(value>>(8*i));
}
static inline uint32_t zorn_panic_crc236(const uint8_t *p,unsigned n){
    uint32_t crc=~0u;
    for(unsigned i=0;i<n;++i){crc^=p[i];for(unsigned b=0;b<8;++b)crc=(crc>>1)^(0xedb88320u&(0u-(crc&1u)));}
    return ~crc;
}
static inline unsigned zorn_panic_build236(uint8_t *out,unsigned capacity,const uint8_t tag[16],
    unsigned cause,unsigned format,unsigned progress,const ZornPanicInput236 *in){
    if(!out || !tag || !in || capacity<ZornPanicHeader236+ZornPanicFooter236+1 ||
       cause<1 || cause>3 || format>65535 || (cause!=2 && format) ||
       in->reason_state>3 || in->flags&~(ZornLogInvalid236|ZornMsgInvalid236|ZornLogMissing236|ZornMsgMissing236) ||
       in->panic_bytes>1048576 || in->message_size>1048576 ||
       (in->panic_bytes && !in->panic) || (in->message_size && (!in->messages || in->message_index>=in->message_size)) ||
       (in->reason_state==2 && (!in->reason || in->reason_bytes>=ZornPanicReasonCap236 || in->reason_required<in->reason_bytes)))return 0;
    const unsigned rn=in->reason_state==2?in->reason_bytes:0;
    const unsigned pn=in->panic_bytes>ZornPanicLogCap236?ZornPanicLogCap236:in->panic_bytes;
    const unsigned mn=in->message_size>ZornPanicMsgCap236?ZornPanicMsgCap236:in->message_size;
    const unsigned content=ZornPanicHeader236+rn+pn+mn;
    const unsigned padding=(content&1u)?0u:1u;
    const unsigned total=content+padding+ZornPanicFooter236;
    if(total>capacity || total>ZornPanicCapacity236)return 0;
    unsigned flags=in->flags;
    if(in->reason_state==0)flags|=ZornReasonMissing236;
    if(in->reason_state==1)flags|=ZornReasonPending236;
    if(in->reason_state==3)flags|=ZornReasonFormatError236;
    if(in->reason_state==2 && in->reason_required>rn)flags|=ZornReasonTruncated236;
    if(in->panic_bytes>pn)flags|=ZornLogTruncated236;
    if(in->message_size>mn)flags|=ZornMsgTruncated236;
    if(mn)flags|=ZornMsgConcurrent236; // best-effort ring snapshot; no global lock or history-completeness claim
    for(unsigned i=0;i<ZornPanicHeader236;++i)out[i]=0;
    const char magic[]="K80PAN26";for(unsigned i=0;i<8;++i)out[i]=(uint8_t)magic[i];
    zorn_panic_le236(out,8,236);zorn_panic_le236(out,12,ZornPanicHeader236);zorn_panic_le236(out,16,total);
    for(unsigned i=0;i<16;++i)out[24+i]=tag[i];
    zorn_panic_le236(out,40,cause);zorn_panic_le236(out,44,flags);
    zorn_panic_le236(out,48,rn);zorn_panic_le236(out,52,in->reason_state==2?in->reason_required:0);
    zorn_panic_le236(out,56,pn);zorn_panic_le236(out,60,in->panic_bytes);
    zorn_panic_le236(out,64,mn);zorn_panic_le236(out,68,in->message_size);
    zorn_panic_le236(out,72,in->message_size?in->message_index:0);zorn_panic_le236(out,76,in->reason_state);
    zorn_panic_le236(out,80,format);zorn_panic_le236(out,84,progress);zorn_panic_le236(out,88,mn?1:0);
    unsigned at=ZornPanicHeader236;
    for(unsigned i=0;i<rn;++i)out[at++]=(uint8_t)in->reason[i];
    for(unsigned i=0;i<pn;++i)out[at++]=(uint8_t)in->panic[in->panic_bytes-pn+i];
    unsigned index=mn?(in->message_index+in->message_size-mn)%in->message_size:0;
    for(unsigned i=0;i<mn;++i){out[at++]=(uint8_t)in->messages[index];if(++index==in->message_size)index=0;}
    if(padding)out[at++]=0;
    const uint32_t crc=zorn_panic_crc236(out,at);
    zorn_panic_le236(out,20,crc);
    const char end[]="K80END26";for(unsigned i=0;i<8;++i)out[at+i]=(uint8_t)end[i];
    zorn_panic_le236(out,at+8,total);zorn_panic_le236(out,at+12,crc);
    return total; // always odd, so the bulk IN ends in a short packet for every supported MPS
}
static inline bool zorn_panic_budget236(unsigned frames,unsigned total,unsigned bytes){
    return frames>0 && frames<39 && total<=119808 && bytes>0 && bytes<=ZornPanicCapacity236 &&
        bytes<=ZornPanicWireLimit236-total;
}

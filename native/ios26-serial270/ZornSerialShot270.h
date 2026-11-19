// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include "ZornSerialShot265.h"
#include "ZornUiSceneWire269.h"
#include "ZornCdcLate270.h"

// Reuse265 actual checked sampler,immutable image buffer,payload CRC and packet
// producer. Select the upper-right quadrant for observed home-screen icons;
// the new source-bound ROI header prevents treating it as a full-screen image.
struct ZornSerialRoi270 {
    enum {Bytes=ZornSerialShot265::Bytes,PacketHeader=68};
private:
    ZornSerialShot265 image_;
    uint32_t publication_=0,roi_[4]{};
public:
    bool request(){return image_.request();}
    bool pending()const{return __atomic_load_n(&image_.state,__ATOMIC_ACQUIRE)==1 && __atomic_load_n(&publication_,__ATOMIC_ACQUIRE)==0;}
    bool ready()const{return __atomic_load_n(&publication_,__ATOMIC_ACQUIRE)==2 && image_.ready();}
    bool capture(const volatile uint32_t *base,uint32_t w,uint32_t h,uint32_t stride,
                 size_t available,const uint32_t (&record)[16]) {
        const uintptr_t address=reinterpret_cast<uintptr_t>(base);
        const uint64_t extent=uint64_t(stride)*h;
        if(!base || (address&3u) || (w&1u) || (h&1u) || w<96 || h<208 ||
           w>16384 || h>16384 || (stride&3u) || uint64_t(stride)<uint64_t(w)*4 ||
           !extent || extent>available || extent-1>UINTPTR_MAX-address)return false;
        uint32_t empty=0;
        if(!__atomic_compare_exchange_n(&publication_,&empty,1u,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))return false;
        const uint32_t x=w/2,rows=h/2;const size_t offset=size_t(x)*4;
        roi_[0]=x;roi_[1]=0;roi_[2]=w/2;roi_[3]=rows;
        const bool ok=image_.capture(base+x,w/2,rows,stride,available-offset,record);
        __atomic_store_n(&publication_,ok?2u:0u,__ATOMIC_RELEASE);return ok;
    }
    unsigned packet(char *out,unsigned cap,unsigned offset,const uint8_t (&tag)[16])const {
        if(!out || cap>3072 || cap<=PacketHeader || !ready())return 0;
        // Original48byte header + data,leaving20bytes for ROI and header CRC.
        const unsigned n=image_.packet(out,cap-20,offset,tag);
        if(n<=48)return 0;
        memmove(out+PacketHeader,out+48,n-48);memcpy(out,"K80SH270",8);
        auto *p=reinterpret_cast<uint8_t *>(out);zorn_panic_le236(p,44,270);
        for(unsigned i=0;i<4;++i)zorn_panic_le236(p,48+4*i,roi_[i]);
        zorn_panic_le236(p,64,zorn_panic_crc236(p,64));return n+20;
    }
};

struct ZornSerialMux270 : ZornUiSceneMux269 {
    template<class Shot,class Ui> unsigned next(void *context,char *out,unsigned cap,unsigned completed,
        ZornCdcNext201 normalNext,const Shot &shot,const Ui &ui,const uint8_t (&tag)[16],bool idle) {
        if(normalNext && completed==wire && wire<38 && normal>=30 && idle &&
           ((!sentUi&&!ui.ready()) || (sentUi && offset<shot.Bytes&&!shot.ready())))
            return ZORN_CDC_PENDING270;
        return ZornUiSceneMux269::next(context,out,cap,completed,normalNext,shot,ui,tag,idle);
    }
};

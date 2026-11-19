// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include <stdint.h>
#include <string.h>
#include "ZornPanicPacket236.h"
#include "ZornCdcStream201.h"

// One immutable CPU diagnostic frame; no event-delivery or GPU authority.
struct ZornUiSceneWire269 {
    enum { Words=16, Bytes=96 };
    static unsigned packet(char *out,unsigned cap,const uint32_t (&v)[Words],const uint8_t (&tag)[16]) {
        if(!out || cap<Bytes)return 0;
        auto *p=reinterpret_cast<uint8_t *>(out);
        memcpy(p,"K80UI269",8);memcpy(p+8,tag,16);
        for(unsigned i=0;i<Words;++i)zorn_panic_le236(p,24+4*i,v[i]);
        zorn_panic_le236(p,88,zorn_panic_crc236(p,88));
        zorn_panic_le236(p,92,269);return Bytes;
    }
};
struct ZornUiSceneMux269 {
    unsigned wire=0,normal=0,offset=0;bool previousAux=false,sentUi=false;
    template<class Shot,class Ui> unsigned next(void *context,char *out,unsigned cap,unsigned completed,
        ZornCdcNext201 normalNext,const Shot &shot,const Ui &ui,const uint8_t (&tag)[16],bool idle) {
        if(!normalNext || completed!=wire || wire>=38)return 0;
        // Reserve one of the original38 nonterminal slots for the UI result:
        // 30normal + 7SHOT + 1UI. Special frames never acknowledge GPU gates.
        if(idle && (!previousAux || normal>=30)) {
            if(!sentUi && ui.ready()) {
                const unsigned n=ui.packet(out,cap,tag);
                if(n){sentUi=true;previousAux=true;++wire;return n;}
            }
            if(shot.ready() && offset<shot.Bytes) {
                const unsigned n=shot.packet(out,cap,offset,tag);
                if(n){offset+=n-shot.PacketHeader;previousAux=true;++wire;return n;}
            }
        }
        if(normal>=30)return 0;
        const unsigned n=normalNext(context,out,cap,normal);
        if(n){++normal;++wire;previousAux=false;}return n;
    }
};

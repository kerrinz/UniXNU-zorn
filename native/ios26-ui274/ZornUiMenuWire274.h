// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include "ZornUiSceneWire269.h"
// New schema:32menu result words plus16actual CPU progress words before
// the hold and16after its lift/2s observation gap. No old packet is relabeled.
struct ZornUiMenuWire274 {
    enum { Words=64,Bytes=288 };
    static unsigned packet(char *out,unsigned cap,const uint32_t (&v)[Words],const uint8_t (&tag)[16]){
        if(!out || cap<Bytes)return 0;
        auto *p=reinterpret_cast<uint8_t *>(out);memcpy(p,"K80UI274",8);memcpy(p+8,tag,16);
        for(unsigned i=0;i<Words;++i)zorn_panic_le236(p,24+4*i,v[i]);
        zorn_panic_le236(p,280,zorn_panic_crc236(p,280));zorn_panic_le236(p,284,274);return Bytes;
    }
};

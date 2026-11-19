// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include "ZornUiSceneWire269.h"
// New schema:retained274 menu result/before/after snapshots,then16 words
// for the bounded outside-tap result and16actual CPU progress words after it.
struct ZornUiMenuWire275 {
    enum { Words=96,Bytes=416 };
    static unsigned packet(char *out,unsigned cap,const uint32_t (&v)[Words],const uint8_t (&tag)[16]){
        if(!out || cap<Bytes)return 0;
        auto *p=reinterpret_cast<uint8_t *>(out);memcpy(p,"K80UI275",8);memcpy(p+8,tag,16);
        for(unsigned i=0;i<Words;++i)zorn_panic_le236(p,24+4*i,v[i]);
        zorn_panic_le236(p,408,zorn_panic_crc236(p,408));zorn_panic_le236(p,412,275);return Bytes;
    }
};

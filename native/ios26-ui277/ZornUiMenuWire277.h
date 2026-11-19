// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include "ZornUiSceneWire269.h"
// Manual observation only:7header words,9*(uptime+16real CPU values).
// No synthetic input,frame delivery or UI-success fields.
struct ZornUiMenuWire277 {
    enum { Words=160,Bytes=672 };
    static unsigned packet(char *out,unsigned cap,const uint32_t (&v)[Words],const uint8_t (&tag)[16]){
        if(!out || cap<Bytes)return 0;
        auto *p=reinterpret_cast<uint8_t *>(out);memcpy(p,"K80MN277",8);memcpy(p+8,tag,16);
        for(unsigned i=0;i<Words;++i)zorn_panic_le236(p,24+4*i,v[i]);
        zorn_panic_le236(p,664,zorn_panic_crc236(p,664));zorn_panic_le236(p,668,277);return Bytes;
    }
};

// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include "ZornUiSceneWire269.h"
// Manual observation only:7header words,9*(uptime+16real GPU progress+16real present cost values).
// No synthetic input,frame delivery or UI-success fields.
struct ZornUiMenuWire278 {
    enum { Words=304,Bytes=1248 };
    static unsigned packet(char *out,unsigned cap,const uint32_t (&v)[Words],const uint8_t (&tag)[16]){
        if(!out || cap<Bytes)return 0;
        auto *p=reinterpret_cast<uint8_t *>(out);memcpy(p,"K80PF278",8);memcpy(p+8,tag,16);
        for(unsigned i=0;i<Words;++i)zorn_panic_le236(p,24+4*i,v[i]);
        zorn_panic_le236(p,1240,zorn_panic_crc236(p,1240));zorn_panic_le236(p,1244,278);return Bytes;
    }
};

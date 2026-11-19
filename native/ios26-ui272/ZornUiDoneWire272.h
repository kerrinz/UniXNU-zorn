// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include "ZornUiSceneWire269.h"
// First32 source271 fields plus explicit Done tap result. Word29 now reports
// compact-observer loss (UINT32_MAX=busy),not a native error. New schema only.
struct ZornUiDoneWire272 {
    enum { Words=48,Bytes=224 };
    static unsigned packet(char *out,unsigned cap,const uint32_t (&v)[Words],const uint8_t (&tag)[16]){
        if(!out || cap<Bytes)return 0;
        auto *p=reinterpret_cast<uint8_t *>(out);memcpy(p,"K80UI272",8);memcpy(p+8,tag,16);
        for(unsigned i=0;i<Words;++i)zorn_panic_le236(p,24+4*i,v[i]);
        zorn_panic_le236(p,216,zorn_panic_crc236(p,216));zorn_panic_le236(p,220,272);return Bytes;
    }
};

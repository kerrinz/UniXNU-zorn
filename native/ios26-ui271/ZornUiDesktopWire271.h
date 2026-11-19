// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include "ZornUiSceneWire269.h"
// New schema:flag512 means live backboardd/GPU-surface admission,not269's
// exited probe/four closed clients. No old packet is relabeled as this one.
struct ZornUiDesktopWire271 {
    enum { Words=32,Bytes=160 };
    static unsigned packet(char *out,unsigned cap,const uint32_t (&v)[Words],const uint8_t (&tag)[16]){
        if(!out || cap<Bytes)return 0;
        auto *p=reinterpret_cast<uint8_t *>(out);memcpy(p,"K80UI271",8);memcpy(p+8,tag,16);
        for(unsigned i=0;i<Words;++i)zorn_panic_le236(p,24+4*i,v[i]);
        zorn_panic_le236(p,152,zorn_panic_crc236(p,152));zorn_panic_le236(p,156,271);return Bytes;
    }
};

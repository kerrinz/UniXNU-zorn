// SPDX-License-Identifier: BSD-2-Clause-Patent
// Edge lifetime policy adapted from UniXNU NativeHidInput. Coordinates here
// are the parser's IOFixed0..65536, not the wire report's0..32767.
#pragma once
#include <stdint.h>
namespace ZornEdgePolicy {
enum : uint32_t {TouchChanged=2,FromEdgeTip=0x800};
enum : int32_t {EdgeX=48*65536/1440,EdgeY=96*65536/3200};
struct Tracker {
    bool edge[256];
    bool mark(uint32_t index,uint32_t mask,bool touch,int32_t x,int32_t y) {
        if(index>=256 || x<0 || y<0 || x>65536 || y>65536)return false;
        if((mask&TouchChanged) && touch)
            edge[index]=x<EdgeX || x>65536-EdgeX || y<EdgeY || y>65536-EdgeY;
        bool result=edge[index];
        if(!touch && (mask&TouchChanged))edge[index]=false;
        return result;
    }
};
}

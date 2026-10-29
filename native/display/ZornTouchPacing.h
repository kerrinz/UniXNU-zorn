// SPDX-License-Identifier: BSD-2-Clause-Patent
// Explicit two-profile scheduling only. GPIO bit timing and SPI commands stay unchanged.
#pragma once
namespace ZornTouchPacing {
struct Settings {unsigned cooperateBytes=8,pollMs=100;};
static inline bool select(unsigned mode,Settings &out) {
    if(mode>1)return false;
    out=mode?Settings{32,20}:Settings{8,100};
    return true;
}
}

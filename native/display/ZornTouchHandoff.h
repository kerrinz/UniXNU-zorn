// SPDX-License-Identifier: BSD-2-Clause-Patent
// K80 SM8650 handoff inventory. No register writes or controller commands.
// Addresses checked against live FDT and MiCode gcc/pinctrl-pineapple.
#pragma once
#include <stdint.h>
namespace ZornTouch {
static constexpr unsigned pins[6]={48,49,50,51,161,162};
static constexpr uint32_t clocks[4]={0x1183bc,0x152008,0x1183c8,0x1183cc};
static constexpr uint32_t engine[7]={0xa90068,0xa90064,0xa90040,0xa90258,0xa90800,0xa90804,0xa90e40};
static constexpr uint32_t display[9]={0xae94000,0xae94004,0xae94008,0xae94084,0xae940a8,0xae9415c,0xae942cc,0xae94330,0xae9403c};
struct Snapshot {
    uint32_t clock[4],config[6],io[6],se[7],dsi[9];
    unsigned result,reads;
};
static inline bool allowed(uint32_t address) {
    for(auto a:clocks)if(a==address)return true;
    for(auto a:engine)if(a==address)return true;
    for(auto a:display)if(a==address)return true;
    for(auto pin:pins)if(address==0xf100000+pin*0x1000 || address==0xf100004+pin*0x1000)return true;
    return false;
}
template<class Bus> static unsigned capture(Bus &bus,Snapshot &s) {
    s={};
    auto read=[&](uint32_t address,uint32_t &value) {
        if(!allowed(address)||!bus.read(address,value)){s.result=2;return false;}
        ++s.reads;return true;
    };
    for(unsigned i=0;i<4;++i)if(!read(clocks[i],s.clock[i]))return s.result;
    if(s.clock[0]==0xffffffff || s.clock[1]==0xffffffff)return s.result=3;
    for(unsigned i=0;i<6;++i) {
        if(!read(0xf100000+pins[i]*0x1000,s.config[i]) || !read(0xf100004+pins[i]*0x1000,s.io[i]))return s.result;
        if(s.config[i]==0xffffffff)return s.result=3;
    }
    // Display is already scanning the UEFI framebuffer. Capture the strict
    // brightness handoff gates too, without sending any DSI commands.
    for(unsigned i=0;i<9;++i)if(!read(display[i],s.dsi[i]))return s.result;
    // A halted serial engine must not be read. This is a meaningful probe
    // result, not proof that the touch controller is absent or broken.
    if(s.clock[0]&0x80000000)return s.result=1;
    for(unsigned i=0;i<7;++i)if(!read(engine[i],s.se[i]))return s.result;
    return s.result=0;
}
}

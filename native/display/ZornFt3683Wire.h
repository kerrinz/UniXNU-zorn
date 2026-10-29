// SPDX-License-Identifier: BSD-2-Clause-Patent
// Read-only FT3683-family SPI command framing. No firmware/mode writes.
// Framing independently checked against the published FT3683U SPI source
// and the BSD-2-Clause-Patent nativefocaltechtouch FT8203 transport.
#pragma once
#include <stdint.h>
namespace ZornFt {
static inline bool pinOwned(uint32_t cfg) {
    return cfg!=0xffffffff && (!(cfg&(1u<<11)) || (cfg&(1u<<12)));
}
static inline bool gpiIdle(uint32_t cfg,uint32_t scratch) {
    unsigned state=(cfg>>20)&15;
    return cfg!=0xffffffff && scratch!=0xffffffff &&
        ((scratch&15)!=4 || state==0 || state==1 || state==3);
}
static inline uint32_t gpioConfig(unsigned index,uint32_t original) {
    return (original&~0x3ffu)|(index<4?2u<<6:0)|((index!=0 && index!=5)?1u<<9:0);
}
static inline uint16_t crc(const uint8_t *data,unsigned bytes) {
    uint16_t value=0xffff;
    for(unsigned i=0;i<bytes;++i) {
        value^=data[i];
        for(unsigned bit=0;bit<8;++bit)value=(value>>1)^((value&1)?0x8408:0);
    }
    return value;
}
struct ReadResult {unsigned error,attempts;uint8_t raw[10];};
struct FrameResult {unsigned error,attempts;uint8_t raw[93];};
struct FullFrameResult {unsigned error,attempts;uint8_t raw[3129];};
// Only the 64-byte header and 720 raw mutual-capacitance cells are consumed by
// the experimental tracker. Keep the longer capture command for diagnostics.
struct MatrixFrameResult {unsigned error,attempts;uint8_t raw[1513];};
template<class Bus> static unsigned readMatrixFrame(Bus &bus,MatrixFrameResult &result) {
    result={};static const uint8_t tx[1513]={0x01,0xa0,0x05,0xe0};
    for(unsigned retry=0;retry<3;++retry) {
        ++result.attempts;
        for(auto &v:result.raw)v=0xff;
        if(!bus.transfer(tx,result.raw,1513))result.error=2;
        else if(result.raw[3]&0xa0)result.error=3;
        else if(crc(result.raw+7,1504)!=(result.raw[1511]|uint16_t(result.raw[1512])<<8))result.error=4;
        else result.error=0;
        bus.delay(150);if(!result.error)return 0;
    }
    return result.error;
}
template<class Bus> static unsigned readFullFrame(Bus &bus,FullFrameResult &result) {
    result={};static const uint8_t tx[3129]={0x01,0xa0,0x0c,0x30};
    for(unsigned retry=0;retry<3;++retry) {
        ++result.attempts;
        for(auto &v:result.raw)v=0xff;
        if(!bus.transfer(tx,result.raw,3129))result.error=2;
        else if(result.raw[3]&0xa0)result.error=3;
        else if(crc(result.raw+7,3120)!=(result.raw[3127]|uint16_t(result.raw[3128])<<8))result.error=4;
        else result.error=0;
        bus.delay(150);if(!result.error)return 0;
    }
    return result.error;
}
// FT read-touch command only. Keep raw payload: the K80 layout is not yet qualified.
template<class Bus> static unsigned readFrame(Bus &bus,FrameResult &result) {
    result={};const uint8_t tx[93]={0x01,0xa0,0,84};
    for(unsigned retry=0;retry<3;++retry) {
        ++result.attempts;
        for(auto &v:result.raw)v=0xff;
        if(!bus.transfer(tx,result.raw,93))result.error=2;
        else if(result.raw[3]&0xa0)result.error=3;
        else if(crc(result.raw+7,84)!=(result.raw[91]|uint16_t(result.raw[92])<<8))result.error=4;
        else result.error=0;
        bus.delay(150);if(!result.error)return 0;
    }
    return result.error;
}
template<class Bus> static unsigned readIdentity(Bus &bus,uint8_t reg,uint8_t &value,ReadResult &result) {
    result={};
    if(reg!=0xa3 && reg!=0x9f && reg!=0xa6)return result.error=1;
    const uint8_t tx[10]={reg,0xa0,0,1,0,0,0,0,0,0};
    for(unsigned retry=0;retry<3;++retry) {
        ++result.attempts;
        for(auto &v:result.raw)v=0xff;
        if(!bus.transfer(tx,result.raw,10))result.error=2;
        else if(result.raw[3]&0xa0)result.error=3;
        else if(crc(result.raw+7,1)!=(result.raw[8]|uint16_t(result.raw[9])<<8))result.error=4;
        else {value=result.raw[7];result.error=0;}
        bus.delay(150);
        if(!result.error)return 0;
    }
    return result.error;
}
// Mode0/MSB-first/active-low CS. Only MOSI, clock, CS can be changed by wire I/O.
// Derived from BSD-2-Clause-Patent UniXNU-houji HoujiTouchGpio.h.
template<class Pins> static bool transfer(Pins &pins,const uint8_t *tx,uint8_t *rx,unsigned count) {
    if(!tx || !rx || (count!=10 && count!=93 && count!=1513 && count!=3129))return false;
    pins.set(2,0);pins.set(3,0);pins.delay(1);
    for(unsigned i=0;i<count;++i) {
        uint8_t receive=0;
        for(unsigned bit=0;bit<8;++bit) {
            pins.set(1,(tx[i]>>(7-bit))&1);pins.delay(1);
            pins.set(2,1);pins.delay(1);
            receive=(receive<<1)|(pins.sample()&1);pins.set(2,0);
        }
        rx[i]=receive;
        // Only runtime sessions opt into bounded scheduler yields. CS remains
        // asserted and clock is low; short probes keep their original timing.
        pins.afterByte(i+1);
    }
    pins.delay(1);pins.set(3,1);pins.delay(1);return true;
}
}

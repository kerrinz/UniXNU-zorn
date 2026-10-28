// SPDX-License-Identifier: BSD-2-Clause-Patent
// Board-specific, bounded DSI v2.8 FIFO transport. Register/packet facts from
// MiCode 3f527f3e55ef27f240507ace3181d13900c3ed7f; no Linux code imported.
// Single caller during CPU0 startup, before the framebuffer publishes. This
// is not a general DSI host or an OS brightness-slider implementation.
#pragma once
#include <stdint.h>

namespace ZornBrightness {
enum { Off=0, Registers=1, Read=2, Dim=3, DimProbe=4, Limit=64, Minimum=15, Maximum=16383 };
enum Error { OK=0, Handoff=1, Busy=2, ExistingError=3, Timeout=4,
             TransferError=5, Response=6, Range=7, Mismatch=8 };

template<class Bus> class Panel {
    Bus &bus;
    uint32_t savedDma=0, savedLength=0;
    bool poisoned=false;
    static constexpr uint32_t interruptMasks=0xa222aa02u;
    bool healthy() {
        return !(bus.read(0x110)&(1u<<24)) && !bus.read(0x068) &&
            !(bus.read(0x0c0)&0x111) && !(bus.read(0x0b4)&0x11111) &&
            !(bus.read(0x00c)&0xcccc0480u) && !(bus.read(0x120)&0x10000);
    }
    bool transfer(uint32_t first, uint32_t second) {
        if (poisoned || bus.read(0x008)!=0) { error=Busy; return false; }
        if (!healthy()) { error=ExistingError; return false; }
        // W1C only our DMA/BTA status; preserve interrupt enables and all
        // unrelated pending status. Polling needs no new interrupt enable.
        const uint32_t masks=bus.read(0x110)&interruptMasks;
        bus.write(0x110,masks|0x100001);
        if (bus.read(0x110)&0x100001) { error=ExistingError; return false; }
        bus.write(0x15c,0x30006);
        bus.write(0x17c,first); bus.write(0x17c,second);
        // HS, VC0, unicast, embedded FIFO. Never use a memory DMA address.
        bus.write(0x03c,(savedDma&~0xc4000000u)|0x10000000);
        bus.write(0x04c,8);
        bus.write(0x090,1);
        bool done=false;
        for (unsigned i=0;i<500;++i) {
            interrupt=bus.read(0x110);
            if (interrupt&1) { done=true; break; }
            bus.delay(10);
        }
        ack=bus.read(0x068); timeouts=bus.read(0x0c0);
        if (!done || bus.read(0x008)!=0) {
            // Do not reset/restore a potentially active engine. Recovery
            // watchdog owns the failure; this instance refuses more writes.
            poisoned=true; error=Timeout; return false;
        }
        bool clean=healthy();
        bus.write(0x110,masks|0x100001);
        bus.write(0x15c,0);
        bus.write(0x1ec,1); bus.delay(1); bus.write(0x1ec,0);
        bus.write(0x04c,savedLength); bus.write(0x03c,savedDma);
        if (!clean) { error=TransferError; return false; }
        return true;
    }
public:
    unsigned error=OK;
    uint32_t interrupt=0,ack=0,timeouts=0,response=0,count=0;
    unsigned before=0,after=0,target=0,writes=0,readbacks=0;
    explicit Panel(Bus &b):bus(b) {}
    bool qualify() {
        // Refuse anything beyond the captured zorn command-mode handoff.
        if (bus.read(0)!=0x20080000 || bus.read(4)!=0x1f5 ||
            bus.read(0x084)!=0x80000004 ||
            (bus.read(0x0a8)&0x1f1f)!=0x1f1f || bus.read(0x15c)!=0 ||
            bus.read(0x2cc)!=0 || (bus.read(0x330)&1)!=0) { error=Handoff; return false; }
        if (bus.read(8)!=0) { error=Busy; return false; }
        if (!healthy()) { error=ExistingError; return false; }
        savedDma=bus.read(0x03c); savedLength=bus.read(0x04c);
        if (savedDma!=0x14000000) { error=Handoff; return false; }
        return true;
    }
    bool readLevel(unsigned &level) {
        if (poisoned) return false;
        // Set maximum return length to two; batch with DCS GET_BRIGHTNESS.
        // Headers are little-endian controller words; LAST+BTA only on read.
        bus.write(0x1d4,1); bus.write(0x1d4,0);
        if (bus.read(0x1d4)>>16) { error=Response; return false; }
        if (!transfer(0x00370002,0xa0060052)) return false;
        count=bus.read(0x1d4)>>16; response=bus.read(0x06c);
        // Accept only a two-byte DCS short response on VC0. Preserve and
        // reject extra ACK/error packets instead of dropping them silently.
        if (count!=4 || (response>>24)!=0x22) { error=Response; return false; }
        level=(response>>8)&0xffff;  // O11 inverted DBV: high byte first.
        if (level>Maximum) { error=Range; return false; }
        return true;
    }
    bool run(unsigned mode) {
        if ((mode!=Read && mode!=Dim) || !qualify()) return false;
        if (!readLevel(before)) return false;
        after=before; target=before;
        if (mode==Read) return true;
        // Never brighten an already dim/off panel. No arbitrary caller level.
        if (before<=Limit) return true;
        target=Limit;
        // DCS long write [51, target high, target low], one 0xff padding byte.
        const uint32_t payload=0xff000051u|((target>>8)<<8)|((target&255)<<16);
        ++writes;
        if (!transfer(0xc0390003,payload)) return false;
        // The panel's init/dimming sequence has 120ms timing. Sample up to
        // 150ms after one write; never retransmit it on a mismatch.
        for(unsigned i=0;i<15;++i) {
            bus.delay(10000); ++readbacks;
            if (!readLevel(after)) return false;
            if(after==target) break;
        }
        if (after!=target) { error=Mismatch; return false; }
        return true;
    }
};
}

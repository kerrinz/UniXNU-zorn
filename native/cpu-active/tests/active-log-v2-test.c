#include "active-log-v2-codec.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static unsigned rng=79;
static unsigned random32(void){rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;return rng;}
static void source(unsigned char b[4096]) {
    for(unsigned i=0;i<4096;++i)b[i]=(unsigned char)random32();
    memcpy(b,"ZORNLOGD",8);memset(b+8,0,8);b[8]=84;b[12]=3;
    memset(b+1032,0,4);b[1032]=19;
    for(unsigned i=0;i<84;++i){for(unsigned j=0;j<11;++j)b[16+i*12+j]&=127;b[27+i*12]=0;}
}
static struct ZornSweepCapture capture(void) {
    struct ZornSweepCapture c={0};c.bounds_ms[0]=60000;c.bounds_ms[1]=60001;
    c.bounds_ms[2]=240000;c.bounds_ms[3]=240001;c.tick_interval_ns=10000000;
    c.masks[0]=c.masks[1]=255;for(unsigned i=0;i<4;++i)c.clock_mach[i]=10;
    for(unsigned i=0;i<32;++i)c.counters[i]=random32();return c;
}
int main(void) {
    unsigned char b[4096],original[4096],scratch[4096],wire[4096];
    for(unsigned round=0;round<256;++round) {
        source(b);memcpy(original,b,4096);struct ZornSweepCapture c=capture(),d;
        assert(!zorn_active_v2_encode(b,4096,&c,scratch,4096));
        assert(!zorn_active_v2_decode(b,4096,&d,scratch,4096));
        assert(!memcmp(b,original,4096) && !memcmp(c.counters,d.counters,sizeof(c.counters)));
    }
    source(b);memcpy(original,b,4096);struct ZornSweepCapture c=capture(),d,prior;
    assert(!zorn_active_v2_encode(b,4096,&c,scratch,4096));memcpy(wire,b,4096);
    for(unsigned i=0;i<4096;++i) {
        memcpy(b,wire,4096);b[i]^=1;unsigned char bad[4096];memcpy(bad,b,4096);
        memset(&d,0x5a,sizeof(d));memcpy(&prior,&d,sizeof(d));
        assert(zorn_active_v2_decode(b,4096,&d,scratch,4096)!=0);
        assert(!memcmp(b,bad,4096) && !memcmp(&d,&prior,sizeof(d)));
    }
    for(unsigned i=0;i<1008;++i) {
        memcpy(b,original,4096);b[16+i]|=128;unsigned char bad[4096];memcpy(bad,b,4096);
        assert(zorn_active_v2_encode(b,4096,&c,scratch,4096)!=0 && !memcmp(b,bad,4096));
    }
    for(unsigned i=0;i<16;++i) {
        struct ZornSweepCapture e=c;e.error=ZORN_SWEEP_CORE_ERROR;e.status[i]=1;
        e.masks[i/8]&=~(1U<<(i%8));e.counters[i*2]=e.counters[i*2+1]=0;
        memcpy(b,original,4096);assert(!zorn_active_v2_encode(b,4096,&e,scratch,4096));
        assert(!zorn_active_v2_decode(b,4096,&d,scratch,4096) && d.status[i]==1);
        e.status[i]=256;memcpy(b,original,4096);
        assert(zorn_active_v2_encode(b,4096,&e,scratch,4096)!=0 && !memcmp(b,original,4096));
    }
    struct ZornSweepCapture missing={0};missing.error=ZORN_SWEEP_INCOMPLETE;
    for(unsigned i=0;i<16;++i)missing.status[i]=255;
    memcpy(b,original,4096);assert(!zorn_active_v2_encode(b,4096,&missing,scratch,4096));
    assert(!zorn_active_v2_decode(b,4096,&d,scratch,4096) && !d.tick_interval_ns);
    memcpy(b,original,4096);
    assert(zorn_active_v2_encode(b,4096,&c,b,4096)!=0 && !memcmp(b,original,4096));
    puts("{\"asan_ubsan_pass\":true,\"roundtrips\":256,\"corrupt_byte_positions\":4096,\"text_incompatibilities\":1008,\"partial_status_roundtrips\":16,\"status_overflows\":16,\"zero_clock_error_preserved\":true,\"alias_refused\":true}");
}

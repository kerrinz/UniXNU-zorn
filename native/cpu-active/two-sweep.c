#include "two-sweep.h"
static void zorn_ca_publish(struct ZornSweepState *s) {
    s->phase=2;
    __atomic_store_n(&s->ready,1U,__ATOMIC_RELEASE);
}
static int zorn_ca_enter(struct ZornSweepState *s) {
    uint32_t expected=0;
    // Weak CAS is a single try: spurious failure must not become an LL/SC loop.
    return __atomic_compare_exchange_n(&s->busy,&expected,1U,1,__ATOMIC_ACQUIRE,__ATOMIC_RELAXED);
}
static void zorn_ca_leave(struct ZornSweepState *s) {__atomic_store_n(&s->busy,0U,__ATOMIC_RELEASE);}
void zorn_sweep_init(struct ZornSweepState *s,int enabled) {
    if(!s)return;
    uint8_t *p=(uint8_t *)s;
    for(size_t i=0;i<sizeof(*s);++i)p[i]=0;
    s->enabled=enabled==1;
    for(unsigned i=0;i<16;++i)s->capture.status[i]=255; // explicitly unattempted
}
const struct ZornSweepCapture *zorn_sweep_published(const struct ZornSweepState *s) {
    return s && __atomic_load_n(&s->ready,__ATOMIC_ACQUIRE)?&s->capture:(const struct ZornSweepCapture *)0;
}
static int zorn_ca_hooks_valid(const struct ZornSweepHooks *h) {
    return h && h->preflight_ready && h->read_core && h->clock_info && h->now_ms;
}
static void zorn_ca_sample(struct ZornSweepState *s,unsigned epoch,uint64_t begin,const struct ZornSweepHooks *h) {
    struct ZornSweepCapture *c=&s->capture;
    c->bounds_ms[epoch*2]=begin;c->bounds_ms[epoch*2+1]=begin;
    if(!h->preflight_ready(h->context)){c->error|=ZORN_SWEEP_NOT_READY;return;}
    uint32_t raw0=0,raw1=0;uint64_t ns0=0,ns1=0;
    int clock0=h->clock_info(h->context,&raw0,&ns0);
    c->clock_mach[epoch*2]=raw0;
    if(!clock0 || !raw0 || !ns0)c->error|=ZORN_SWEEP_CLOCK_INVALID;
    if(epoch==0)c->tick_interval_ns=ns0;
    else if(ns0!=c->tick_interval_ns || raw0!=c->clock_mach[0])c->error|=ZORN_SWEEP_CLOCK_CHANGED;
    if(clock0 && raw0 && ns0)for(unsigned id=0;id<8;++id) {
        uint64_t values[2]={0,0};uint32_t result=h->read_core(h->context,id,values);
        c->status[epoch*8+id]=result;
        if(result) {
            c->error|=ZORN_SWEEP_CORE_ERROR;
            if(result>3)c->error|=ZORN_SWEEP_UNKNOWN_STATUS;
            continue;
        }
        uint64_t user=values[0]/raw0,system=values[1]/raw0;
        if(user>UINT32_MAX || system>UINT32_MAX) {
            c->status[epoch*8+id]=3;c->error|=ZORN_SWEEP_TICK_OVERFLOW|ZORN_SWEEP_CORE_ERROR;continue;
        }
        c->counters[epoch*16+id*2]=user;c->counters[epoch*16+id*2+1]=system;
        c->masks[epoch]|=1U<<id;
    }
    int clock1=h->clock_info(h->context,&raw1,&ns1);
    c->clock_mach[epoch*2+1]=raw1;
    if(!clock1 || !raw1 || !ns1)c->error|=ZORN_SWEEP_CLOCK_INVALID;
    if(raw0!=raw1 || ns0!=ns1)c->error|=ZORN_SWEEP_CLOCK_CHANGED;
    uint64_t end=h->now_ms(h->context);c->bounds_ms[epoch*2+1]=end;
    if(end<begin || end>UINT32_MAX)c->error|=ZORN_SWEEP_TIME_INVALID;
    if(!h->preflight_ready(h->context))c->error|=ZORN_SWEEP_NOT_READY;
}
int zorn_sweep_tick(struct ZornSweepState *s,uint64_t now,const struct ZornSweepHooks *h) {
    if(!s || !s->enabled)return ZORN_SWEEP_IDLE;
    if(zorn_sweep_published(s))return ZORN_SWEEP_FINAL;
    if(!zorn_ca_enter(s))return ZORN_SWEEP_BUSY;
    if(zorn_sweep_published(s)){zorn_ca_leave(s);return ZORN_SWEEP_FINAL;}
    if(now==s->last_ms){zorn_ca_leave(s);return ZORN_SWEEP_IDLE;}
    if(now<s->last_ms || now>UINT32_MAX ||
       (s->phase==1 && now<s->capture.bounds_ms[1])) {
        s->capture.error|=ZORN_SWEEP_TIME_INVALID|ZORN_SWEEP_INCOMPLETE;
        s->capture.bounds_ms[s->phase*2]=now;
        s->capture.bounds_ms[s->phase*2+1]=now;
        zorn_ca_publish(s);zorn_ca_leave(s);return ZORN_SWEEP_FINAL;
    }
    s->last_ms=now;
    if(!zorn_ca_hooks_valid(h)) {
        s->capture.error|=ZORN_SWEEP_HOOK_INVALID|ZORN_SWEEP_INCOMPLETE;
        zorn_ca_publish(s);zorn_ca_leave(s);return ZORN_SWEEP_FINAL;
    }
    uint64_t earliest=s->phase?240000:60000,latest=s->phase?270000:120000;
    if(now<earliest){zorn_ca_leave(s);return ZORN_SWEEP_IDLE;}
    unsigned epoch=s->phase;
    if(now>latest) {
        s->capture.error|=epoch?ZORN_SWEEP_LATE_SECOND:ZORN_SWEEP_LATE_FIRST;
        s->capture.bounds_ms[epoch*2]=now;s->capture.bounds_ms[epoch*2+1]=now;
    } else zorn_ca_sample(s,epoch,now,h);
    if(epoch)zorn_ca_publish(s);else s->phase=1;
    zorn_ca_leave(s);return epoch?ZORN_SWEEP_FINAL:ZORN_SWEEP_TAKEN;
}
int zorn_sweep_finish(struct ZornSweepState *s,uint64_t now) {
    if(!s || !s->enabled)return ZORN_SWEEP_IDLE;
    if(zorn_sweep_published(s))return ZORN_SWEEP_FINAL;
    if(!zorn_ca_enter(s))return ZORN_SWEEP_BUSY;
    if(!zorn_sweep_published(s)) {
        s->capture.error|=ZORN_SWEEP_INCOMPLETE;
        if(now<s->last_ms || now>UINT32_MAX ||
           (s->phase==1 && now<s->capture.bounds_ms[1]))s->capture.error|=ZORN_SWEEP_TIME_INVALID;
        zorn_ca_publish(s);
    }
    zorn_ca_leave(s);return ZORN_SWEEP_FINAL;
}

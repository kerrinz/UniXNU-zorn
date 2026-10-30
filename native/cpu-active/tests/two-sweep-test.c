#include "two-sweep.h"
#include <assert.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <sched.h>
struct Fixture {
    unsigned reads,clocks,gates;
    uint32_t status[8],raw[4];
    uint64_t ns[4],end,values[2];
    int gate,bad_clock,block,entered,release;
};
static int gate(void *v){struct Fixture *f=v;f->gates++;return f->gate;}
static uint32_t read_core(void *v,unsigned id,uint64_t out[2]) {
    struct Fixture *f=v;f->reads++;
    if(f->block && id==0) {
        __atomic_store_n(&f->entered,1,__ATOMIC_RELEASE);
        while(!__atomic_load_n(&f->release,__ATOMIC_ACQUIRE))sched_yield(); // injected host hook only
    }
    out[0]=f->values[0]+id*10;out[1]=f->values[1]+id*10;return f->status[id];
}
static int clock_info(void *v,uint32_t *raw,uint64_t *ns) {
    struct Fixture *f=v;unsigned i=f->clocks++;assert(i<4);
    *raw=f->raw[i];*ns=f->ns[i];return !f->bad_clock;
}
static uint64_t now_ms(void *v){return ((struct Fixture *)v)->end;}
static void setup(struct ZornSweepState *s,struct Fixture *f) {
    zorn_sweep_init(s,1);memset(f,0,sizeof(*f));f->gate=1;f->end=60001;
    f->values[0]=100;f->values[1]=200;
    for(unsigned i=0;i<4;++i){f->raw[i]=10;f->ns[i]=10000000;}
}
static struct ZornSweepHooks hooks(struct Fixture *f) {
    return (struct ZornSweepHooks){f,gate,read_core,clock_info,now_ms};
}
static unsigned scenarios;
static void deterministic(void) {
    struct ZornSweepState s;struct Fixture f;struct ZornSweepHooks h;
    setup(&s,&f);h=hooks(&f);s.enabled=0;
    assert(zorn_sweep_tick(&s,60000,&h)==ZORN_SWEEP_IDLE && !f.reads);scenarios++;
    setup(&s,&f);h=hooks(&f);
    assert(zorn_sweep_tick(&s,59999,&h)==ZORN_SWEEP_IDLE && !f.gates);
    assert(zorn_sweep_tick(&s,60000,&h)==ZORN_SWEEP_TAKEN && f.reads==8);
    assert(!zorn_sweep_published(&s));
    assert(zorn_sweep_tick(&s,60001,&h)==ZORN_SWEEP_IDLE && f.reads==8);
    f.end=240001;assert(zorn_sweep_tick(&s,240000,&h)==ZORN_SWEEP_FINAL);
    const struct ZornSweepCapture *c=zorn_sweep_published(&s);
    assert(c && !c->error && c->masks[0]==255 && c->masks[1]==255 && f.reads==16);
    for(unsigned i=0;i<16;++i)assert(!c->status[i]);
    assert(c->counters[0]==10 && c->counters[1]==20 && c->bounds_ms[3]==240001);
    struct ZornSweepCapture saved=*c;
    assert(zorn_sweep_tick(&s,0,0)==ZORN_SWEEP_FINAL);
    assert(zorn_sweep_finish(&s,0)==ZORN_SWEEP_FINAL && !memcmp(c,&saved,sizeof(saved)));scenarios++;
    for(unsigned code=1;code<=4;++code) {
        setup(&s,&f);h=hooks(&f);f.status[3]=code;
        zorn_sweep_tick(&s,60000,&h);zorn_sweep_finish(&s,300000);c=zorn_sweep_published(&s);
        assert(c->status[3]==code && c->masks[0]==247 && !c->counters[6]);
        assert(c->error&ZORN_SWEEP_CORE_ERROR);
        assert(!!(c->error&ZORN_SWEEP_UNKNOWN_STATUS)==(code==4));scenarios++;
    }
    setup(&s,&f);h=hooks(&f);f.gate=0;
    zorn_sweep_tick(&s,60000,&h);zorn_sweep_finish(&s,300000);c=zorn_sweep_published(&s);
    assert(!f.reads && !f.clocks && c->status[0]==255 && c->error&ZORN_SWEEP_NOT_READY);scenarios++;
    setup(&s,&f);h=hooks(&f);f.raw[0]=0;f.ns[0]=0;
    zorn_sweep_tick(&s,60000,&h);zorn_sweep_finish(&s,300000);c=zorn_sweep_published(&s);
    assert(!f.reads && !c->tick_interval_ns && c->error&ZORN_SWEEP_CLOCK_INVALID);scenarios++;
    setup(&s,&f);h=hooks(&f);f.raw[1]=11;
    zorn_sweep_tick(&s,60000,&h);zorn_sweep_finish(&s,300000);c=zorn_sweep_published(&s);
    assert(c->clock_mach[1]==11 && c->error&ZORN_SWEEP_CLOCK_CHANGED);scenarios++;
    setup(&s,&f);h=hooks(&f);f.raw[2]=f.raw[3]=11;
    zorn_sweep_tick(&s,60000,&h);f.end=240001;zorn_sweep_tick(&s,240000,&h);
    assert(zorn_sweep_published(&s)->error&ZORN_SWEEP_CLOCK_CHANGED);scenarios++;
    setup(&s,&f);h=hooks(&f);f.values[0]=((uint64_t)UINT32_MAX+1)*10;
    zorn_sweep_tick(&s,60000,&h);zorn_sweep_finish(&s,300000);c=zorn_sweep_published(&s);
    assert(c->error&ZORN_SWEEP_TICK_OVERFLOW && c->masks[0]==0 && c->status[0]==3);scenarios++;
    setup(&s,&f);h=hooks(&f);f.end=60002;
    zorn_sweep_tick(&s,60000,&h);zorn_sweep_tick(&s,60001,&h);c=zorn_sweep_published(&s);
    assert(c && c->error&ZORN_SWEEP_TIME_INVALID && c->bounds_ms[2]==60001 && f.reads==8);scenarios++;
    setup(&s,&f);h=hooks(&f);f.end=59999;
    zorn_sweep_tick(&s,60000,&h);zorn_sweep_finish(&s,300000);
    assert(zorn_sweep_published(&s)->error&ZORN_SWEEP_TIME_INVALID);scenarios++;
    setup(&s,&f);h=hooks(&f);
    zorn_sweep_tick(&s,120001,&h);zorn_sweep_tick(&s,270001,&h);c=zorn_sweep_published(&s);
    assert(c->error==(ZORN_SWEEP_LATE_FIRST|ZORN_SWEEP_LATE_SECOND) && !f.reads && c->status[15]==255);scenarios++;
    setup(&s,&f);zorn_sweep_finish(&s,300000);c=zorn_sweep_published(&s);
    assert(c->error==ZORN_SWEEP_INCOMPLETE && c->status[0]==255 && !c->tick_interval_ns);scenarios++;
    setup(&s,&f);h=hooks(&f);zorn_sweep_tick(&s,(uint64_t)UINT32_MAX+1,&h);
    c=zorn_sweep_published(&s);assert(c->error&ZORN_SWEEP_TIME_INVALID && c->bounds_ms[0]==(uint64_t)UINT32_MAX+1);scenarios++;
    setup(&s,&f);zorn_sweep_tick(&s,60000,0);assert(zorn_sweep_published(&s)->error&ZORN_SWEEP_HOOK_INVALID);scenarios++;
}
struct Job {struct ZornSweepState *s;struct ZornSweepHooks *h;uint64_t now;};
static void *worker(void *p){struct Job *j=p;zorn_sweep_tick(j->s,j->now,j->h);return 0;}
static void *published_reader(void *p) {
    struct ZornSweepState *s=p;const struct ZornSweepCapture *c;
    while(!(c=zorn_sweep_published(s)))sched_yield(); // host reader, not collector
    assert(!c->error && c->masks[0]==255 && c->masks[1]==255);
    assert(c->bounds_ms[0]==60000 && c->bounds_ms[3]==240001);
    for(unsigned i=0;i<16;++i)assert(c->status[i]==0);
    struct ZornSweepCapture saved=*c;
    for(unsigned i=0;i<1000;++i) {
        assert(zorn_sweep_tick(s,0,0)==ZORN_SWEEP_FINAL);
        assert(!memcmp(c,&saved,sizeof(saved)));
    }
    return 0;
}
static void concurrent(void) {
    for(unsigned round=0;round<100;++round) {
        struct ZornSweepState s;struct Fixture f;setup(&s,&f);struct ZornSweepHooks h=hooks(&f);
        pthread_t threads[8];struct Job j={&s,&h,60000};
        for(unsigned i=0;i<8;++i)assert(!pthread_create(threads+i,0,worker,&j));
        for(unsigned i=0;i<8;++i)assert(!pthread_join(threads[i],0));
        assert(f.reads==8 && !zorn_sweep_published(&s));
        j.now=240000;f.end=240001;
        for(unsigned i=0;i<8;++i)assert(!pthread_create(threads+i,0,worker,&j));
        for(unsigned i=0;i<8;++i)assert(!pthread_join(threads[i],0));
        assert(f.reads==16 && !zorn_sweep_published(&s)->error);
    }
    struct ZornSweepState s;struct Fixture f;setup(&s,&f);f.block=1;
    struct ZornSweepHooks h=hooks(&f);struct Job j={&s,&h,60000};pthread_t thread;
    assert(!pthread_create(&thread,0,worker,&j));
    while(!__atomic_load_n(&f.entered,__ATOMIC_ACQUIRE))sched_yield();
    assert(!zorn_sweep_published(&s));
    assert(zorn_sweep_tick(&s,60000,&h)==ZORN_SWEEP_BUSY);
    assert(zorn_sweep_finish(&s,300000)==ZORN_SWEEP_BUSY);
    __atomic_store_n(&f.release,1,__ATOMIC_RELEASE);assert(!pthread_join(thread,0));
    pthread_t reader;assert(!pthread_create(&reader,0,published_reader,&s));
    f.end=240001;zorn_sweep_tick(&s,240000,&h);
    assert(!pthread_join(reader,0));
    assert(zorn_sweep_published(&s) && f.reads==16);
}
int main(void){deterministic();concurrent();printf("{\"deterministic_scenarios\":%u,\"concurrent_duplicate_rounds\":100,\"blocked_owner_controls\":2,\"ready_only_publication_reader\":true,\"immutable_reader_checks\":1000,\"asan_ubsan_pass\":true}\n",scenarios);}

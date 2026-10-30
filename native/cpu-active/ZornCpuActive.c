#include "ZornCpuActive.h"
#include "two-sweep.h"
#include "active-log-v2-codec.h"
#if defined(ZORN_ACTIVE_INTEGRATION_HOST_TEST)
#include "observer-host-shim.h"
#else
#include <kern/clock.h>
#include <machine/machine_routines.h>
#endif
extern int zorn_active_profile_ready(void);
extern int zorn_active_sampler_ready(void);
extern int zorn_active_read_core(void *,unsigned,uint64_t[2]);
extern int zorn_active_clock_info(void *,uint32_t *,uint64_t *);
static struct ZornSweepState zorn_ca_state;
static uint64_t zorn_ca_epoch;
static uint32_t zorn_ca_configured;
static int zorn_ca_ready(void *context){(void)context;return zorn_active_sampler_ready();}
static uint32_t zorn_ca_read_core(void *context,unsigned id,uint64_t out[2]) {
    return (uint32_t)zorn_active_read_core(context,id,out);
}
static uint64_t zorn_ca_milliseconds(void *context) {
    (void)context;
    uint64_t now=mach_absolute_time();
    mach_timebase_info_data_t info;clock_timebase_info(&info);
    if(now<zorn_ca_epoch || !info.numer || !info.denom)return UINT64_MAX;
    uint64_t delta=now-zorn_ca_epoch;
    if(delta>UINT64_MAX/info.numer)return UINT64_MAX;
    return (delta*info.numer/info.denom)/1000000;
}
static const struct ZornSweepHooks zorn_ca_hooks={0,zorn_ca_ready,zorn_ca_read_core,zorn_active_clock_info,zorn_ca_milliseconds};
void zorn_cpu_active_configure(int zorn_ca_enabled,uint64_t trace_epoch) {
    uint32_t expected=0;
    if(!__atomic_compare_exchange_n(&zorn_ca_configured,&expected,1U,1,__ATOMIC_ACQUIRE,__ATOMIC_RELAXED))return;
    zorn_ca_epoch=trace_epoch;zorn_sweep_init(&zorn_ca_state,zorn_ca_enabled);
    __atomic_store_n(&zorn_ca_configured,2U,__ATOMIC_RELEASE);
}
static int zorn_ca_enabled(void) {
    return __atomic_load_n(&zorn_ca_configured,__ATOMIC_ACQUIRE)==2 && zorn_ca_state.enabled;
}
void zorn_cpu_active_gui_tick(void) {
    if(!zorn_ca_enabled())return;
    (void)zorn_sweep_tick(&zorn_ca_state,zorn_ca_milliseconds(0),&zorn_ca_hooks);
}
void zorn_cpu_active_gui_finish(void) {
    if(!zorn_ca_enabled())return;
    (void)zorn_sweep_finish(&zorn_ca_state,zorn_ca_milliseconds(0));
}
static int zorn_ca_overlap(const void *a,const void *b,size_t n) {
    uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return x<=y?y-x<n:x-y<n;
}
const void *zorn_cpu_active_transport(const void *canonical,size_t bytes,
    uint8_t *wire,uint8_t *scratch) {
    if(!zorn_ca_enabled())return canonical;
    const struct ZornSweepCapture *capture=zorn_sweep_published(&zorn_ca_state);
    if(!capture || !canonical || !wire || !scratch || bytes!=4096 ||
       zorn_ca_overlap(canonical,wire,4096) || zorn_ca_overlap(canonical,scratch,4096) || zorn_ca_overlap(wire,scratch,4096))return canonical;
    const uint8_t *source=canonical;
    for(unsigned i=0;i<4096;++i)wire[i]=source[i];
    if(zorn_active_v2_encode(wire,4096,capture,scratch,4096)!=0)return canonical;
    return wire;
}

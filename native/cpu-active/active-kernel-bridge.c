// Isolated exact-type XNU C bridge; not in any production build.
#if defined(ZORN_BRIDGE_HOST_TEST)
#include "bridge-host-shim.h"
#else
#include <kern/processor.h>
#include <kern/clock.h>
#include <machine/machine_routines.h>
#include <os/atomic_private.h>
#include <stdint.h>
#endif
#if HAS_CLUSTER && USE_APPLEARMSMP
#error "This candidate requires the audited non-AppleSMP fixed-core profile"
#endif
extern int zorn_active_profile_ready(void);
extern int zorn_active_processor_handle(unsigned,processor_t *);
extern int zorn_try_processor_active_accounting(processor_t,uint64_t[2]);

static int zorn_ca_normal_profile(unsigned id) {
    // Actual non-AppleSMP ml_cpu_can_exit is false except during quiesce.
    // Availability count writers use os_atomic; no scheduler-state race/lock.
    return zorn_active_profile_ready() && !ml_cpu_can_exit((int)id,REASON_SYSTEM) &&
        os_atomic_load(&processor_avail_count,relaxed)==8;
}
int zorn_active_read_core(void *unused,unsigned id,uint64_t out[2]) {
    (void)unused;
    if(id>=8 || !out || !zorn_ca_normal_profile(id))return 2;
    processor_t p=PROCESSOR_NULL;
    if(!zorn_active_processor_handle(id,&p) || !p || p->cpu_id!=(int)id)return 2;
    uint64_t pair[2];int status=zorn_try_processor_active_accounting(p,pair);
    if(!zorn_ca_normal_profile(id))return 2;
    if(status)return status;
    out[0]=pair[0];out[1]=pair[1];return 0;
}
int zorn_active_clock_info(void *unused,uint32_t *raw,uint64_t *ns) {
    (void)unused;
    if(!raw || !ns)return 0;
    uint32_t before=os_atomic_load(&hz_tick_interval,relaxed);
    *raw=before;*ns=0;
    if(!zorn_ca_normal_profile(0))return 0;
    mach_timebase_info_data_t a,b;
    clock_timebase_info(&a);
    // Exact existing conversion of one second yields the actual divisor.
    // nanoseconds_to_absolutetime divides by a constant, so zero is safe here.
    uint64_t sec0=0,sec1=0;
    nanoseconds_to_absolutetime(1000000000ULL,&sec0);
    if(!before || !a.numer || !a.denom || !sec0 || sec0>UINT32_MAX)return 0;
    // Both products fit: operands are bounded by UInt32, NSEC_PER_SEC<2^32.
    uint64_t ratio_ns=(uint64_t)before*a.numer/a.denom;
    uint64_t divisor_ns=(uint64_t)before*1000000000ULL/sec0;
    nanoseconds_to_absolutetime(1000000000ULL,&sec1);
    clock_timebase_info(&b);
    uint32_t after=os_atomic_load(&hz_tick_interval,relaxed);
    if(before!=after || a.numer!=b.numer || a.denom!=b.denom || sec0!=sec1 ||
       !ratio_ns || ratio_ns!=divisor_ns || !zorn_ca_normal_profile(0))return 0;
    *ns=ratio_ns;return 1;
}

int zorn_active_sampler_ready(void){return zorn_ca_normal_profile(0);}

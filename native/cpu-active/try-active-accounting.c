// Isolated candidate only; no active XNU source or binary is modified.
#if defined(ZORN_ACCOUNTING_HOST_TEST)
#include "try-active-test-shim.h"
#else
#include <kern/processor.h>
#include <kern/recount.h>
#include <os/atomic_private.h>
#include <stdint.h>
#endif

#if !PRECISE_USER_KERNEL_TIME
#error "This observation requires separately accounted user/kernel time"
#endif

enum { ZORN_ACTIVE_OK=0, ZORN_ACTIVE_BUSY=1, ZORN_ACTIVE_INVALID=2,
       ZORN_ACTIVE_OVERFLOW=3 };

// Caller supplies a live registered processor and private output storage in
// normal thread context. No idle pair, thread/stack or current-running delta.
int zorn_try_processor_active_accounting(processor_t processor,uint64_t out[2])
{
    if (!processor || !out) return ZORN_ACTIVE_INVALID;
    const struct recount_track *track=&processor->pr_recount.rpr_active;
    for (unsigned attempt=0;attempt<3;++attempt) {
        uint32_t before=os_atomic_load(&track->rt_sync,acquire);
        if (before&1) continue;
        uint64_t user=os_atomic_load(&track->rt_usage.ru_metrics[RCT_LVL_USER].rm_time_mach,relaxed);
        uint64_t system=os_atomic_load(&track->rt_usage.ru_metrics[RCT_LVL_KERNEL].rm_time_mach,relaxed);
#if RECOUNT_SECURE_METRICS
        uint64_t secure=os_atomic_load(&track->rt_usage.ru_metrics[RCT_LVL_SECURE].rm_time_mach,relaxed);
#endif
        // Keep all payload loads before final generation validation. The
        // original writer already fences its odd marker and even publication.
        os_atomic_thread_fence(acquire);
        uint32_t after=os_atomic_load(&track->rt_sync,acquire);
        if (before!=after) continue;
#if RECOUNT_SECURE_METRICS
        if (secure>UINT64_MAX-system) return ZORN_ACTIVE_OVERFLOW;
        system+=secure;
#endif
        out[0]=user;
        out[1]=system;
        return ZORN_ACTIVE_OK;
    }
    return ZORN_ACTIVE_BUSY;
}

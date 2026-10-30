// Isolated candidate; no production caller or live processor bridge yet.
#ifndef ZORN_TWO_SWEEP_EXPERIMENT_H
#define ZORN_TWO_SWEEP_EXPERIMENT_H
#include <stdint.h>
#include <stddef.h>
enum {
    ZORN_SWEEP_LATE_FIRST=1,ZORN_SWEEP_LATE_SECOND=2,ZORN_SWEEP_NOT_READY=4,
    ZORN_SWEEP_CLOCK_INVALID=8,ZORN_SWEEP_CLOCK_CHANGED=16,ZORN_SWEEP_TIME_INVALID=32,
    ZORN_SWEEP_CORE_ERROR=64,ZORN_SWEEP_TICK_OVERFLOW=128,ZORN_SWEEP_INCOMPLETE=256,
    ZORN_SWEEP_HOOK_INVALID=512,ZORN_SWEEP_UNKNOWN_STATUS=1024
};
enum { ZORN_SWEEP_IDLE=0,ZORN_SWEEP_TAKEN=1,ZORN_SWEEP_FINAL=2,ZORN_SWEEP_BUSY=3 };
struct ZornSweepCapture {
    uint64_t counters[32],bounds_ms[4],tick_interval_ns;
    uint32_t masks[2],error,status[16];
    uint64_t clock_mach[4]; // before/after each sweep; range checked by transport
};
struct ZornSweepState {
    uint32_t busy,ready,enabled,phase;
    uint64_t last_ms;
    struct ZornSweepCapture capture;
};
struct ZornSweepHooks {
    void *context;
    int (*preflight_ready)(void *);
    uint32_t (*read_core)(void *,unsigned,uint64_t active_mach[2]);
    int (*clock_info)(void *,uint32_t *mach_per_tick,uint64_t *ns_per_tick);
    uint64_t (*now_ms)(void *);
};
// Initialize exactly once before publication; never reset a visible state.
void zorn_sweep_init(struct ZornSweepState *,int enabled);
int zorn_sweep_tick(struct ZornSweepState *,uint64_t now_ms,const struct ZornSweepHooks *);
int zorn_sweep_finish(struct ZornSweepState *,uint64_t now_ms);
const struct ZornSweepCapture *zorn_sweep_published(const struct ZornSweepState *);
#endif

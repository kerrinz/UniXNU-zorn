// Optional diagnostic only. Configuration precedes any GUI reader.
#ifndef ZORN_CPU_ACTIVE_H
#define ZORN_CPU_ACTIVE_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
void zorn_cpu_active_configure(int enabled,uint64_t trace_epoch);
void zorn_cpu_active_gui_tick(void);
void zorn_cpu_active_gui_finish(void);
// Caller exclusively owns stable canonical log, wire and scratch until the
// downstream synchronous4096B write completes; all three pages are disjoint.
// Returns canonical unchanged when disabled/unpublished/incompatible.
const void *zorn_cpu_active_transport(const void *canonical,size_t bytes,
    uint8_t *wire,uint8_t *scratch);
#ifdef __cplusplus
}
#endif
#endif

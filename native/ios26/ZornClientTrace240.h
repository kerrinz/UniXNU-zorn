// SPDX-License-Identifier: MIT
#pragma once
#include <stdint.h>
// Source milestones only. No pointers, PID guesses, instruction or stack data.
// Concurrent snapshots are not global ordering or proof of a culprit call.
enum { ZornClientTraceEvents240=24 };
#ifdef __cplusplus
extern "C" {
#endif
void zorn26_client_event240(unsigned);
void zorn26_client_close_reset242(void);
uint32_t zorn26_client_snapshot240(void);
#ifdef __cplusplus
}
#endif

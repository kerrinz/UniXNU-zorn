// SPDX-License-Identifier: BSD-2-Clause-Patent
// Non-RAM-Data profiles expose no marker filesystem operations or seed ABI.
#include <stdint.h>
#include <sys/errno.h>
volatile unsigned zorn_data_marker_state;
volatile int zorn_data_marker_error;
volatile uint64_t zorn_data_marker_cookie;
int zorn_boot_data_marker_existing(void *process, uint64_t scratch)
{
    (void)process;(void)scratch;
    zorn_data_marker_error=ENOTSUP;zorn_data_marker_state=3;
    return ENOTSUP;
}
int zorn_boot_data_marker(void *process, uint64_t scratch)
{
    return zorn_boot_data_marker_existing(process,scratch);
}

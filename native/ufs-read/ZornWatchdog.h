// SPDX-License-Identifier: BSD-2-Clause-Patent
// Gunyah watchdog ABI used by this phone's qcom,gh-watchdog node.
// Interface reference: zorn-kernel/drivers/virt/gunyah/gh_virt_wdt.c.
// This implementation uses SMC calls only; no guessed physical watchdog MMIO.
#pragma once

struct ZornSmcResult {
    uint64_t status;
    uint64_t flags;
    uint64_t elapsed;
};

static ZornSmcResult zorn_wdt_call(uint32_t function, uint32_t arg1, uint32_t arg2)
{
    register uint64_t x0 __asm__("x0") = function;
    register uint64_t x1 __asm__("x1") = arg1;
    register uint64_t x2 __asm__("x2") = arg2;
    register uint64_t x3 __asm__("x3") = 0;
    __asm__ volatile("smc #0" : "+r"(x0), "+r"(x1), "+r"(x2), "+r"(x3)
                     :: "x4", "x5", "x6", "x7", "x8", "x9", "x10", "x11",
                        "x12", "x13", "x14", "x15", "x16", "x17", "cc", "memory");
    return { x0, x1, x2 };
}

static void zorn_wdt_number(char tag, uint64_t value)
{
    static const char digits[] = "0123456789ABCDEF";
    char word[10] = {};
    word[0] = tag;
    for (unsigned i = 0; i < 8; i++) {
        word[1 + i] = digits[(value >> (28 - 4 * i)) & 15];
    }
    zorn_log_append(word);
}

static void zorn_watchdog_start(void)
{
    gLogBusy = 1;
    zorn_log_append("WPROBE");
    ZornSmcResult status = zorn_wdt_call(0x86000006U, 0, 0);
    zorn_wdt_number('S', status.status);
    if (status.status != 0) {
        zorn_log_append("WUNSUP");
        zorn_checkpoint_reset();
        gLogBusy = 0;
        return;
    }
    zorn_log_append(status.flags & 1 ? "WON" : "WOFF");
    if (!zorn_set_recovery_bcb()) {
        gLogBusy = 0;
        zorn_ufs_stop("WBCN");
    }
    zorn_log_append("WBCB");
    if (status.flags & 1) {
        status = zorn_wdt_call(0x86000005U, 2, 0);
        zorn_wdt_number('D', status.status);
        if (status.status != 0) {
            zorn_log_append("WDISERR");
            zorn_checkpoint_reset();
            gLogBusy = 0;
            return;
        }
    }
    // The ABI takes absolute bark/bite deadlines as 16-bit milliseconds.
    uint32_t bark = gWatchdogMode == 2 ? 5000 : 45000;
    uint32_t bite = gWatchdogMode == 2 ? 7000 : 55000;
    status = zorn_wdt_call(0x86000008U, bark, bite);
    zorn_wdt_number('T', status.status);
    if (status.status != 0) {
        zorn_log_append("WTIMERR");
        zorn_checkpoint_reset();
        gLogBusy = 0;
        return;
    }
    status = zorn_wdt_call(0x86000007U, 0, 0);
    zorn_wdt_number('P', status.status);
    if (status.status != 0) {
        zorn_log_append("WPETERR");
        zorn_checkpoint_reset();
        gLogBusy = 0;
        return;
    }
    status = zorn_wdt_call(0x86000005U, 3, 0);
    zorn_wdt_number('E', status.status);
    if (status.status != 0) {
        zorn_log_append("WENERR");
        zorn_checkpoint_reset();
        gLogBusy = 0;
        return;
    }
    gWatchdogArmed = true;
    status = zorn_wdt_call(0x86000006U, 0, 0);
    if (status.status != 0 || !(status.flags & 1)) {
        zorn_log_append("WNOTON");
        zorn_checkpoint_reset();
        gLogBusy = 0;
        return;
    }
    zorn_log_append("WARM");
    if (gWatchdogMode == 2) {
        // Deliberately stop CPU progress to verify recovery without an IRQ,
        // a scheduled kernel worker, or a successful checkpoint return.
        zorn_log_append("WTEST");
        __asm__ volatile("msr daifset, #15" ::: "memory");
        for (;;) {
            __asm__ volatile("wfe" ::: "memory");
        }
    }
    gLogBusy = 0;
}

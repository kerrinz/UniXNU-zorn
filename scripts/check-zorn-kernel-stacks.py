#!/usr/bin/env python3
"""Execute the actual opt-in kernel-stack helper under bounded host stubs.

Checks rejection of SMP/default runnable targets and invalid/wrapped/cyclic stacks,
plus the separately enabled CPU0 non-current runnable context path,
the real 16-frame cap, balanced preemption, and no target/stack mutation.
This is not hardware qualification of a physical nofault copy.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
TREE = ROOT / "UniXNU/out/zorn/tree/.cache/xnu-work"
source = (TREE / "osfmk/kern/exception.c").read_text()
begin = source.index("static __attribute__((noinline)) int\nzorn_gui_sample_kernel_stack(")
end = source.index("/* Opt-in user stack sampling", begin)
helper = source[begin:end]
state_header = (TREE / "osfmk/mach/arm/thread_status.h").read_text()
state = re.search(r"struct arm_kernel_saved_state \{.*?\} __attribute__\(\(aligned\(16\)\)\);", state_header, re.S).group()
program = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <mach/kern_return.h>
#include "ZornGuiLog.h"
typedef uintptr_t vm_offset_t;
typedef uintptr_t vm_size_t;
@@STATE@@
typedef struct arm_kernel_saved_state arm_kernel_saved_state_t;
struct fake_thread {
    unsigned state;
    void (*continuation)(void);
    uint64_t kernel_stack;
    struct {void *kstackptr;} machine;
};
typedef struct fake_thread *thread_t;
#define THREAD_NULL ((thread_t)0)
#define TH_WAIT 1U
#define TH_RUN 4U
#define TH_TERMINATE 16U
#define VM_MIN_KERNEL_ADDRESS 0xffffffe000000000ULL
#define VM_MAX_KERNEL_ADDRESS 0xfffffffbffffffffULL
static unsigned processor_count = 1, depth, copies, fail_after = 1000, records;
static unsigned runnable_requested;
static bool PE_parse_boot_argn(const char *name, void *value, unsigned bytes) {
    assert(depth == 0 && !strcmp(name, "zorn_gui_krun") && bytes == sizeof(unsigned));
    memcpy(value, &runnable_requested, bytes); return runnable_requested != 0;
}
static uint64_t kernel_stack_size = 16384;
static const uint64_t base = 0xfffffff010000000ULL;
static unsigned char memory[16384], before_memory[16384];
static struct fake_thread observer;
static struct ZornGuiUserStack recorded;
static thread_t current_thread(void) {return &observer;}
static void disable_preemption(void) {assert(depth == 0); ++depth;}
static void enable_preemption(void) {assert(depth == 1); --depth;}
static vm_size_t ml_nofault_copy(vm_offset_t src, vm_offset_t dst, vm_size_t bytes) {
    assert(depth == 1);
    if (copies++ >= fail_after) return 0;
    assert(src >= base && bytes <= sizeof(memory) && src - base <= sizeof(memory) - bytes);
    memcpy((void *)dst, memory + src - base, bytes);
    return bytes;
}
void zorn_ufs_gui_stack(const char *name, const struct ZornGuiUserStack *stack) {
    assert(depth == 0 && !strcmp(name, "SpringBoard"));
    recorded = *stack; ++records;
}
@@HELPER@@
static struct fake_thread target;
static void setup(void) {
    memset(memory, 0, sizeof(memory)); memset(&recorded, 0, sizeof(recorded));
    processor_count = 1; depth = copies = records = 0; fail_after = 1000; runnable_requested = 0;
    kernel_stack_size = sizeof(memory);
    target = (struct fake_thread){TH_WAIT, NULL, base, {(void *)(base + 16000)}};
    arm_kernel_saved_state_t ss = {.fp = base + 256, .lr = 0xfffffff007001000ULL};
    memcpy(memory + 16000, &ss, sizeof(ss));
    uint64_t pair[2] = {base + 288, 0xfffffff007002000ULL};
    memcpy(memory + 256, pair, sizeof(pair));
    pair[0] = 0; pair[1] = 0xfffffff007003000ULL;
    memcpy(memory + 288, pair, sizeof(pair));
}
static void sample_expect(unsigned expected) {
    struct fake_thread before = target; memcpy(before_memory, memory, sizeof(memory));
    assert(zorn_gui_sample_kernel_stack("SpringBoard", 5, &target) == (int)expected);
    assert(!depth && records == expected);
    assert(!memcmp(&target, &before, sizeof(target)) && !memcmp(memory, before_memory, sizeof(memory)));
    if (expected) assert(recorded.pid == 5 && (recorded.error & ZORN_GUI_STACK_KERNEL));
}
#define sample() sample_expect(1)
int main(void) {
    setup(); sample(); assert(recorded.count == 3 && recorded.error == ZORN_GUI_STACK_KERNEL && copies == 3);
    setup(); processor_count = 2; sample(); assert(!recorded.count && !copies && (recorded.error & ~ZORN_GUI_STACK_KERNEL) == KERN_NOT_SUPPORTED);
    setup(); target.state |= TH_RUN; sample_expect(0); assert(!recorded.count && !copies);
    setup(); target.state |= TH_TERMINATE; sample(); assert(!recorded.count && !copies);
    setup(); target.continuation = (void (*)(void))0xfffffff007004000ULL; sample_expect(0); assert(!records && !copies);
    setup(); target.machine.kstackptr = (void *)(base - 16); sample(); assert(!recorded.count && !copies && (recorded.error & ~ZORN_GUI_STACK_KERNEL) == KERN_INVALID_ADDRESS);
    setup(); target.machine.kstackptr = (void *)(base + sizeof(memory) - 16); sample(); assert(!recorded.count && !copies);
    setup(); arm_kernel_saved_state_t ss; memcpy(&ss, memory + 16000, sizeof(ss)); ss.fp += 8; memcpy(memory + 16000, &ss, sizeof(ss)); sample(); assert(recorded.count == 1 && copies == 1 && (recorded.error & ~ZORN_GUI_STACK_KERNEL) == KERN_INVALID_ADDRESS);
    setup(); fail_after = 1; sample(); assert(recorded.count == 1 && copies == 2 && (recorded.error & ~ZORN_GUI_STACK_KERNEL) == KERN_INVALID_ADDRESS);
    setup(); uint64_t pair[2] = {base + 256, 0xfffffff007005000ULL}; memcpy(memory + 256, pair, sizeof(pair)); sample(); assert(recorded.count == 2 && copies == 2 && (recorded.error & ~ZORN_GUI_STACK_KERNEL) == KERN_INVALID_ADDRESS);
    setup(); for (unsigned i = 0; i < 20; ++i) {pair[0] = base + 256 + (i + 1) * 32; pair[1] = 0xfffffff007006000ULL + i * 16; memcpy(memory + 256 + i * 32, pair, sizeof(pair));} sample(); assert(recorded.count == 16 && copies == 16 && recorded.error == ZORN_GUI_STACK_KERNEL);
    setup(); memcpy(&ss, memory + 16000, sizeof(ss)); ss.pc_was_in_userspace = 1; memcpy(memory + 16000, &ss, sizeof(ss)); sample(); assert(!recorded.count && copies == 1);
    setup(); runnable_requested = 1; target.state = TH_RUN; sample(); assert(recorded.count == 3 && copies == 3 && recorded.error == ZORN_GUI_STACK_KERNEL);
    setup(); runnable_requested = 1; target.state = TH_WAIT | TH_RUN; sample(); assert(recorded.count == 3 && copies == 3);
    setup(); runnable_requested = 2; target.state = TH_RUN; sample_expect(0); assert(!copies);
    setup(); runnable_requested = 1; target.state = TH_RUN; processor_count = 2; sample(); assert(!copies && (recorded.error & ~ZORN_GUI_STACK_KERNEL) == KERN_NOT_SUPPORTED);
    setup(); runnable_requested = 1; target.state = TH_RUN; target.continuation = (void (*)(void))0xfffffff007004000ULL; sample_expect(0); assert(!copies);
    setup(); runnable_requested = 1; target.state = TH_RUN | TH_TERMINATE; sample(); assert(!copies && !recorded.count);
    setup(); runnable_requested = 1; assert(zorn_gui_sample_kernel_stack("SpringBoard", 5, &observer) == 1); assert(!copies && !depth && records == 1 && !recorded.count);
    setup(); runnable_requested = 1; assert(zorn_gui_sample_kernel_stack("SpringBoard", 5, THREAD_NULL) == 1); assert(!copies && !depth && records == 1 && !recorded.count);
    puts("20 actual-helper controls passed; no target mutation; balanced preemption");
}
'''.replace("@@STATE@@", state).replace("@@HELPER@@", helper)
with tempfile.TemporaryDirectory(prefix="zorn-kernel-stack-") as directory:
    path = Path(directory)
    (path / "check.c").write_text(program)
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-I",
                    str(ROOT / "UniXNU-zorn/native/ufs-read"), str(path / "check.c"),
                    "-o", str(path / "check")], check=True)
    print(subprocess.check_output([str(path / "check")], text=True).strip())
report = {"actual_helper_sha256": hashlib.sha256(helper.encode()).hexdigest(),
          "source_state_declaration_sha256": hashlib.sha256(state.encode()).hexdigest(),
          "host_controls": 20, "target_and_stack_unchanged": True,
          "preemption_balanced_before_record": True, "frame_limit": 16,
          "smp_and_default_runnable_kernel_reads_refused": True,
          "explicit_cpu0_noncurrent_runnable_path_exercised": True,
          "current_terminating_and_missing_targets_refused": True,
          "continuation_and_default_runnable_prefer_user_frames": True,
          "physical_nofault_copy_hardware_qualified": False}
(ROOT / "out/zorn/kernel-stack-host-checks.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))

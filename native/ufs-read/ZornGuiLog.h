// zorn diagnostic ABI. All fields are little-endian; no user memory pointers
// are dereferenced by the persistence layer. Keep the XNU sys header identical.
#ifndef ZORN_GUI_LOG_H
#define ZORN_GUI_LOG_H
#include <sys/types.h>

#define ZORN_GUI_LOG_SLOTS 92
#define ZORN_GUI_LOG_OFFSET (16 + 12 * ZORN_GUI_LOG_SLOTS)
#define ZORN_GUI_STACK_FRAMES 16
#define ZORN_GUI_STACK_KERNEL 0x80000000U

/* A retained kernel stack is wired. Limit reads to its exact allocation. */
static inline int zorn_gui_kernel_frame_valid(uint64_t base, uint64_t size,
    uint64_t fp)
{
    return size >= 16 && size - 1 <= ~((uint64_t)0) - base &&
        fp >= base && fp - base <= size - 16 && !(fp & 15);
}

/* Only sample aligned frame records in the captured thread's user stack.
 * Subtraction keeps untrusted pointer arithmetic from wrapping. */
static inline int zorn_gui_stack_frame_valid(uint64_t sp, uint64_t fp,
    uint64_t minimum, uint64_t maximum)
{
    return maximum >= 16 && sp >= minimum && sp < maximum &&
        fp >= sp && fp - sp < 1024 * 1024 && !(fp & 15) &&
        fp >= minimum && fp <= maximum - 16;
}

struct ZornGuiThread {
    uint64_t pc, lr, sp, fp, wait, continuation;
    uint32_t state, reserved;
};
struct ZornGuiProcess {
    char name[16];
    uint32_t pid, tick;
    uint64_t slide, header;
    uint32_t count, truncated;
    struct ZornGuiThread threads[4];
};
struct ZornGuiExitRecord {
    uint32_t sequence;
    int32_t pid, status;
    uint32_t reasonNamespace;
    uint64_t reasonCode;
    char name[24];
};
struct ZornGuiExitDetail {
    uint64_t pc, lr, far, slide, header;
    uint32_t esr, cpsr, fixups;
    char reason[92];
};
struct ZornGuiIpcRecord {
    uint32_t sequence;
    int32_t pid, message, receiver;
    uint32_t bits;
};
struct ZornGuiQueryRecord {
    uint32_t sequence;
    int32_t pid, status;
    uint32_t outputPresent;
    char provider[40];
};
struct ZornGuiUserStack {
    uint32_t pid, tick, count, error;
    uint64_t frames[ZORN_GUI_STACK_FRAMES];
};
struct ZornGuiFooter {
    char magic[8];
    uint32_t version, bytes, tick, stage, pid, sequence;
    uint64_t ms;
    uint32_t freePages, activePages, inactivePages, wiredPages;
    uint64_t ram[3], display[32];
    struct ZornGuiProcess processes[3];
    struct ZornGuiExitRecord exits[4];
    struct ZornGuiExitDetail exitDetails[4];
    // Actual kernel values, independent of potentially wrapped console text.
    uint64_t configuration[8];
    // Four fixed library/cache paths: errno and vnode type for each.
    uint32_t paths[8];
    struct ZornGuiIpcRecord ipc[3][2];
    char receiverNames[3][2][16];
    struct ZornGuiQueryRecord queries[3];
    uint64_t keystore[6];
    uint64_t startupPolicy[3];
    struct ZornGuiUserStack stacks[3];
    uint64_t dataPermissions[3];
    // errno/support bits, block bytes, total/available blocks, actual UUID.
    uint64_t dataSpace[6];
};

#ifdef __cplusplus
static_assert(sizeof(ZornGuiThread) == 56 && sizeof(ZornGuiProcess) == 272, "GUI process ABI");
static_assert(sizeof(ZornGuiExitRecord) == 48 && sizeof(ZornGuiExitDetail) == 144 && sizeof(ZornGuiIpcRecord) == 20 && sizeof(ZornGuiQueryRecord) == 56 && sizeof(ZornGuiUserStack) == 144 && sizeof(ZornGuiFooter) == 2976, "GUI footer ABI");
extern "C" {
#else
_Static_assert(sizeof(struct ZornGuiThread) == 56 && sizeof(struct ZornGuiProcess) == 272, "GUI process ABI");
_Static_assert(sizeof(struct ZornGuiExitRecord) == 48 && sizeof(struct ZornGuiExitDetail) == 144 && sizeof(struct ZornGuiIpcRecord) == 20 && sizeof(struct ZornGuiQueryRecord) == 56 && sizeof(struct ZornGuiUserStack) == 144 && sizeof(struct ZornGuiFooter) == 2976, "GUI footer ABI");
#endif
void zorn_ufs_gui_stage(unsigned tick, unsigned stage, int pid);
void zorn_ufs_gui_process(const struct ZornGuiProcess *process);
void zorn_ufs_gui_stack(const char *name, const struct ZornGuiUserStack *stack);
void zorn_ufs_gui_paths(const uint32_t paths[8]);
void zorn_ufs_gui_data_space(const uint64_t values[6]);
int zorn_ufs_boot_policy_allowed(void);
void zorn_ufs_gui_ipc(int pid, const char *name, int32_t message, int receiver, uint32_t bits, const char *receiverName);
void zorn_ufs_gui_iokit(int pid, const char *name, const char *provider, int status, unsigned outputPresent);
struct task;
void zorn_gui_exit_regs(struct task *task, struct ZornGuiExitDetail *detail);
int zorn_ufs_gui_enabled(void);
int zorn_ufs_gui_exit_wanted(int pid, const char *name);
void zorn_ufs_gui_hold_tick(void);
void zorn_ufs_gui_flush(void);
void zorn_ufs_exit_report(int pid, const char *name, int status, uint32_t reasonNamespace,
                        uint64_t reasonCode, const struct ZornGuiExitDetail *detail);
#ifdef __cplusplus
}
#endif
#endif

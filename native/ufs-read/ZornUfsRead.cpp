// UFS probe for zorn. Same pineapple host and stream as houji's GPT reader:
// ufshc@1d84000, apps_smmu stream 0x60. Reads the primary GPT. One FUA WRITE
// of a diagnostic block 4 MiB past the flashed root image. No SYNCHRONIZE CACHE.
// Configurable checkpoints set misc's recovery BCB and use PSCI SYSTEM_RESET.
// The optional Gunyah watchdog provides independent timeout recovery. The OS
// transfer callback stays read-only; logs remain in one existing userdata block.
#define IOKIT_ENABLE_SHARED_PTR
#include <IOKit/IOLib.h>
#include <IOKit/IOBufferMemoryDescriptor.h>
#include <IOKit/IODeviceMemory.h>
#include <IOKit/IOMemoryDescriptor.h>
#include <kern/clock.h>
#include <kern/task.h>
#include <machine/machine_routines.h>
#include <libkern/libkern.h>
#include <sys/errno.h>
#include <sys/types.h>
#include <stdarg.h>
#include <pexpert/pexpert.h>
#include "GccUfs.h"
#include "RootDiagnostics.h"
#include "TransferPoll.h"
#include "GiuliaSmmuTakeover.h"
#include "HoujiGptCheck.h"
#include "ZornSha256.h"
#include "ZornVerifiedRoot.h"
#include "ZornGuiLog.h"
#include "../cpu-active/ZornCpuActive.h"
#include "../display/ZornTouchTrace.h"
#include "../display/ZornDisplayProgress.h"
#include "ZornTraceStages.h"

// Exact native XNU globals from the pinned osfmk/vm/vm_page.h. Diagnostic
// snapshots only; these counters never select memory allocation or policy.
extern "C" {
#if defined(ZORN_SMP_PREFLIGHT) && ZORN_SMP_PREFLIGHT
int zorn_armcpu_preflight(void);
int zorn_armcpu_runtime(char *,unsigned);
extern volatile unsigned zorn_smp_preflight_active;
#endif
extern unsigned int vm_page_free_count, vm_page_active_count;
extern unsigned int vm_page_inactive_count, vm_page_wire_count;
extern uint32_t cs_text_fixup_applied;
extern uint32_t cs_text_fixup_parsed;
extern uint64_t dyld_flags;
extern volatile uint64_t native_owner_cache_dyld_flags;
extern volatile int native_owner_cache_stage;
extern volatile uint64_t native_owner_cache_actual_mount_flags;
#if defined(ZORN_VERIFIED_ROOT) && ZORN_VERIFIED_ROOT
extern volatile unsigned zorn_data_permissions_stage, zorn_data_permissions_checked, zorn_data_permissions_total;
extern volatile unsigned zorn_data_permissions_root_uid, zorn_data_permissions_root_gid;
extern volatile int zorn_data_permissions_status;
extern volatile unsigned zorn_data_marker_state;
extern volatile int zorn_data_marker_error;
extern volatile uint64_t zorn_data_marker_cookie;
#endif
#if defined(ZORN_DISPLAY) && ZORN_DISPLAY
extern volatile uint64_t zorn_display_stats[32];
extern volatile uint64_t zorn_touch_runtime_stats[12];
#if defined(ZORN_TOUCH_RUNTIME_ENABLED) && ZORN_TOUCH_RUNTIME_ENABLED
extern volatile uint32_t zorn_touch_edge_stats[8];
uint32_t zorn_touch_trace_words[108];
#endif
void zorn_brightness_checkpoint(void);
extern volatile uint32_t zorn_aks_stage, zorn_aks_opens, zorn_aks_calls, zorn_aks_refused, zorn_aks_last_selector;
extern volatile int32_t zorn_aks_status, zorn_aks_last_result;
extern volatile uint32_t zorn_hid_stage, zorn_hid_resource;
extern volatile int32_t zorn_hid_family_status, zorn_hid_event_status;
#endif
#if defined(ZORN_RAM_DATA) && ZORN_RAM_DATA
extern volatile uint64_t native_ram_block_reads, native_ram_block_writes, native_ram_block_failures;
extern volatile uint32_t native_data_persist_state, native_data_persist_header, native_data_persist_gpt, native_data_persist_gpt_after;
extern volatile uint64_t native_data_persist_present, native_data_persist_writes, native_data_persist_errors, native_data_persist_loaded;
extern volatile int native_owner_data_probe_stage, native_owner_data_probe_status;
unsigned native_ufs_store_mode(void);
#endif
}

extern "C" void zorn_say(const char *);
extern "C" int zorn_os_root_pending;
extern "C" dev_t mdevadd_ops(int devid, uint64_t bytes,
    int (*transfer)(void *arg, uint64_t offset, void *data, size_t bytes, int iswrite), void *arg);
extern "C" int zorn_os_transfer(void *arg, uint64_t offset, void *data, size_t bytes, int iswrite);

static UfsRootDiagnostics gRootDiagnostic;

static void zorn_ufs_stop(const char *word)
{
	zorn_say(word);
	__asm__ volatile("msr daifset, #15" ::: "memory");
	for (;;) {
		__asm__ volatile("wfe" ::: "memory");
	}
}

extern "C" int zorn_os_root_pending = 0;
extern "C" int zorn_os_xfers = 0;
extern "C" int zorn_os_ckbad = 0;
extern "C" int zorn_os_sbok = 0;
extern "C" uint32_t zorn_os_seen_bs = 0;
extern "C" uint64_t zorn_os_seen_blocks = 0;
extern "C" uint64_t zorn_os_first_off = 0;
extern "C" uint64_t zorn_os_first_len = 0;

extern "C" void zorn_os_note_bs(uint32_t bs)
{
	zorn_os_seen_bs = bs;
}

extern "C" void zorn_os_note_blocks(uint64_t blocks)
{
	zorn_os_seen_blocks = blocks;
}

extern "C" void zorn_os_hold(const char *word)
{
	zorn_ufs_stop(word);
}

extern "C" void zorn_os_hold_tagged(int tag, int err)
{
	char word[9];
	static const char hex[] = "0123456789ABCDEF";
	unsigned value = static_cast<unsigned>(err);
	word[0] = static_cast<char>(tag);
	for (int nibble = 0; nibble < 7; nibble++) {
		word[1 + nibble] = hex[(value >> (24 - nibble * 4)) & 0xF];
	}
	word[8] = 0;
	zorn_os_hold(word);
}

extern "C" void zorn_os_hold_errno(int err)
{
	zorn_os_hold_tagged('E', err);
}

static bool zorn_nx_checksum_ok(const uint8_t *block)
{
	uint64_t sum1 = 0;
	uint64_t sum2 = 0;
	for (unsigned word = 2; word < 1024; word++) {
		uint32_t value;
		memcpy(&value, block + word * 4, sizeof(value));
		sum1 += value;
		sum2 += sum1;
	}
	sum1 %= 0xFFFFFFFFULL;
	sum2 %= 0xFFFFFFFFULL;
	uint32_t low = ~static_cast<uint32_t>((sum1 + sum2) % 0xFFFFFFFFULL);
	uint32_t high = ~static_cast<uint32_t>((static_cast<uint64_t>(low) + sum1) % 0xFFFFFFFFULL);
	uint64_t got = (static_cast<uint64_t>(high) << 32) | low;
	uint64_t stored;
	memcpy(&stored, block, sizeof(stored));
	return got == stored;
}

static uint32_t read32(uintptr_t base, unsigned offset)
{
	return *reinterpret_cast<volatile uint32_t *>(base + offset);
}

static void write32(uintptr_t base, unsigned offset, uint32_t value)
{
	*reinterpret_cast<volatile uint32_t *>(base + offset) = value;
}

static uintptr_t mapPhys(uint64_t phys, uint64_t length, OSSharedPtr<IOMemoryMap> &keep)
{
	OSSharedPtr<IODeviceMemory> memory = IODeviceMemory::withRange(phys, length);
	if (!memory) {
		return 0;
	}
	keep = memory->map(kIOMapAnywhere | kIOMapInhibitCache);
	return keep ? static_cast<uintptr_t>(keep->getVirtualAddress()) : 0;
}

static const char *smmuBypassStream(uint16_t stream, OSSharedPtr<IOMemoryMap> &keep, uint32_t *report,
    uint64_t dma, uint64_t bytes, uintptr_t host)
{
	if ((read32(host, 0x60) & 1) || read32(host, 0x58) || read32(host, 0x78)) {
		return "USMM";
	}
	uintptr_t smmu = mapPhys(0x15000000ULL, 0xd0000, keep);
	if (!smmu) {
		return "USMM";
	}
	GiuliaSmmuPlan selection = planGiuliaSmmu(stream, dma, bytes, [smmu](unsigned offset) {
		return read32(smmu, offset);
	});
	const UfsSmmuPlan &plan = selection.target;
	gRootDiagnostic.smmuId1 = read32(smmu, 0x24);
	gRootDiagnostic.smmuId2 = read32(smmu, 0x28);
	gRootDiagnostic.smmuSlot = plan.slot;
	if (plan.error) {
		gRootDiagnostic.smr = plan.smr;
		gRootDiagnostic.s2cr = plan.s2cr;
		return "USMM";
	}
	unsigned bank = plan.bank, index = plan.slot;
	uintptr_t cb = smmu + (plan.pages + bank) * 4096;
	const char *failure = configureGiuliaSmmu(selection, stream, true,
	    [smmu](unsigned offset) {
		return read32(smmu, offset);
	},
	    [smmu](unsigned offset, uint32_t value) {
		write32(smmu, offset, value);
		__asm__ volatile("dsb sy" ::: "memory");
	});
	gRootDiagnostic.smr = read32(smmu, 0x800 + 4 * index);
	gRootDiagnostic.s2cr = read32(smmu, 0xc00 + 4 * index);
	gRootDiagnostic.cbar = read32(smmu, 0x1000 + 4 * bank);
	gRootDiagnostic.sctlr = read32(cb, 0x0);
	gRootDiagnostic.cba2r = read32(smmu, 0x1800 + 4 * bank);
	if (failure) {
		return "USMM";
	}
	report[0] = index | (bank << 16);
	report[1] = gRootDiagnostic.cbar;
	report[2] = gRootDiagnostic.sctlr;
	return nullptr;
}

namespace {
#include "RootTransportLayout.h"

struct UfsHost {
	OSSharedPtr<IOMemoryMap> hcMap, smmuMap;
	uintptr_t hc = 0;
	OSSharedPtr<IOBufferMemoryDescriptor> dma;
	uint8_t *virt = nullptr;
	uint64_t phys = 0;
	IOLock *lock = nullptr;
	bool ready = false;
	bool poisoned = false;
	uintptr_t smmu = 0, cb = 0;
};
static UfsHost gHost;
#include "ZornDataStorePolicy.h"
static unsigned gZornDataMode;
static bool gZornDataOpened;
static bool gLogEnabled = false;
static bool gLogArmed = false;
static uint64_t gTraceEpoch;
static uint64_t gCopyTraceOwner;
static unsigned gCopyTraceCount;
static bool gRecoveryArmed = false;
static bool gLogOnly = false;
static bool gWatchdogArmed = false;
static int gWatchdogMode = 0;
static unsigned gHashBudgetSeconds;
static uint64_t gHashLastPetMs, gHashLastLogBytes;
static char gHashFile[96];
static uint32_t gLogLba = 0;
static uint32_t gMiscLba = 0;
static uint32_t gLogBlocks = 0;
static int gLogBusy = 0;
static bool gTouchRawLog;
#include "ZornTouchRawLog.h"
static int gReturnAfterTent = 0;
static char gRecoveryCheckpoint[9] = "IRET";
static unsigned gCheckpointSkip;
static unsigned gCheckpointSeen;
static bool gCompactTrace;
static uint64_t gLogWriteAttempts, gLogWriteSuccesses, gTraceSuppressed, gStage2Suppressed;
static uint64_t gLogWriteNanoseconds;
static uint64_t gOsReadBlocks, gOsReadErrors, gOsReadNanoseconds;
static bool gServiceTrace;
static bool gGuiWatch;
static bool gQuietGui;
static bool gLaunchServicesWatch;
static bool gGuiKernelStacks;
static unsigned gGuiServiceThread;
static uint64_t gStartupPolicy[3] = {~0ULL, ~0ULL, 0};
static unsigned gGuiHoldSeconds;
using ZornGuiExit = ZornGuiExitRecord;
static ZornGuiExit gGuiExits[4];
static ZornGuiExitDetail gGuiExitDetails[4];
static unsigned gGuiExitSequence;
static int gGuiExitBusy;
static ZornGuiFooter gGuiDiagnostics;
static int gGuiDiagnosticsBusy;
using ZornGuiIpc = ZornGuiIpcRecord;
static ZornGuiIpc gGuiIpc[3][2];
static char gGuiReceiverNames[3][2][16];
static ZornGuiQueryRecord gGuiQueries[3];
static unsigned gGuiQuerySequence;
static unsigned gGuiIpcNext[3], gGuiIpcSequence;
static int gGuiIpcBusy;
static unsigned gExecBudgetSeconds;
static uint64_t gExecLastObservationMs;
static void zorn_service_progress(void);
static void zorn_checkpoint_reset(void);
static void zorn_checkpoint_reset_owned(void);
static void zorn_watchdog_start(void);
struct ZornLogBlock {
	char magic[8];
	uint32_t count;
	uint32_t next;
	char word[340][12];
};
static_assert(sizeof(ZornLogBlock) == 4096, "log must fit one UFS block");
static ZornLogBlock gLogBlock;
// Owned by the existing gLogBusy writer until synchronous transport returns.
alignas(64) static uint8_t gCpuActiveWire[4096],gCpuActiveScratch[4096];
struct ZornMacFailure {
	char policy[12];
	uint32_t error;
};
static ZornMacFailure gMacFailures[8];
static unsigned gMacFailureReady[8];
static unsigned gMacFailureCount;
static uint32_t gTrustCacheMask;
static IOReturn (*gZornWriteLog)(const void *) = nullptr;

extern "C" void zorn_show_words(const char *text);

static void zorn_log_put(const char *text)
{
	unsigned capacity = gTouchRawLog ? ZornTouchLog::Slots : gGuiWatch ? ZORN_GUI_LOG_SLOTS : 340;
	char *slot = gLogBlock.word[gLogBlock.next];
	gLogBlock.next = (gLogBlock.next + 1) % capacity;
	if (gLogBlock.count < capacity) {
		gLogBlock.count++;
	}
	for (int i = 0; i < 12; i++) {
		slot[i] = 0;
	}
	for (int i = 0; i < 11 && text[i] != '\0'; i++) {
		slot[i] = text[i];
	}
}

extern "C" void zorn_ufs_gui_stage(unsigned tick, unsigned stage, int pid)
{
	if (!gGuiWatch || !__sync_bool_compare_and_swap(&gGuiDiagnosticsBusy, 0, 1)) return;
	if (tick) gGuiDiagnostics.tick = tick;
	gGuiDiagnostics.stage = stage;
	gGuiDiagnostics.pid = static_cast<uint32_t>(pid);
	++gGuiDiagnostics.sequence;
	__sync_lock_release(&gGuiDiagnosticsBusy);
}

extern "C" int zorn_ufs_gui_enabled(void) { return gGuiWatch && gLogArmed; }
extern "C" int zorn_ufs_boot_policy_allowed(void)
{
#if defined(ZORN_RAM_DATA) && ZORN_RAM_DATA
	return gGuiWatch && gLogArmed && gWatchdogArmed && native_owner_data_probe_stage == 7 &&
	    native_owner_data_probe_status == 0 && (native_ufs_store_mode() <= 1 ||
	    (native_ufs_store_mode() == 2 && gZornDataOpened && native_data_persist_state == 2 &&
	    native_data_persist_header == 0 && native_data_persist_gpt == 0 && native_data_persist_gpt_after == 0));
#else
	return 0;
#endif
}
extern "C" void zorn_ufs_boot_policy_result(int error, int uid, int gid, unsigned mode, uint64_t bytes)
{
	gStartupPolicy[1] = static_cast<uint32_t>(gid) | (static_cast<uint64_t>(mode) << 32);
	gStartupPolicy[2] = bytes;
	gStartupPolicy[0] = static_cast<uint32_t>(error) | (static_cast<uint64_t>(static_cast<uint32_t>(uid)) << 32);
}

extern "C" void zorn_ufs_gui_ipc(int pid, const char *name, int32_t message, int receiver, uint32_t bits, const char *receiverName)
{
	if (!gGuiWatch || !gLogArmed || !name) return;
	int index = !strcmp(name, gLaunchServicesWatch ? "lsd" : "launchd") ? 0 : !strcmp(name, "SpringBoard") ? 1 : !strcmp(name, "backboardd") ? 2 : -1;
	if (index < 0 || !__sync_bool_compare_and_swap(&gGuiIpcBusy, 0, 1)) return;
	unsigned slot = gGuiIpcNext[index]++ % 2;
	ZornGuiIpc &event = gGuiIpc[index][slot];
	event = { ++gGuiIpcSequence, pid, message, receiver, bits };
	strlcpy(gGuiReceiverNames[index][slot], receiverName ? receiverName : "", sizeof(gGuiReceiverNames[index][slot]));
	__sync_lock_release(&gGuiIpcBusy);
}

extern "C" void zorn_ufs_gui_iokit(int pid, const char *name, const char *provider, int status, unsigned outputPresent)
{
	if (!gGuiWatch || !gLogArmed || !name) return;
	int index = !strcmp(name, gLaunchServicesWatch ? "lsd" : "launchd") ? 0 : !strcmp(name, "SpringBoard") ? 1 : !strcmp(name, "backboardd") ? 2 : -1;
	if (index < 0 || !__sync_bool_compare_and_swap(&gGuiIpcBusy, 0, 1)) return;
	ZornGuiQueryRecord &event = gGuiQueries[index];
	event.sequence = ++gGuiQuerySequence; event.pid = pid; event.status = status;
	event.outputPresent = outputPresent ? 1 : 0;
	strlcpy(event.provider, provider ? provider : "", sizeof(event.provider));
	__sync_lock_release(&gGuiIpcBusy);
}

extern "C" void zorn_ufs_gui_process(const ZornGuiProcess *process)
{
	if (!gGuiWatch || !process || process->count > 4) return;
	unsigned index;
	if (process->pid == 1 || (gLaunchServicesWatch && !strcmp(process->name, "lsd"))) index = 0;
	else if (!strncmp(process->name, "SpringBoard", sizeof(process->name))) index = 1;
	else if (!strncmp(process->name, "backboardd", sizeof(process->name))) index = 2;
	else return;
	if (!__sync_bool_compare_and_swap(&gGuiDiagnosticsBusy, 0, 1)) return;
	gGuiDiagnostics.processes[index] = *process;
	gGuiDiagnostics.processes[index].tick = gGuiDiagnostics.tick;
	++gGuiDiagnostics.sequence;
	__sync_lock_release(&gGuiDiagnosticsBusy);
}

extern "C" void zorn_ufs_gui_stack(const char *name, const ZornGuiUserStack *stack)
{
	if (!gGuiWatch || !name || !stack || !stack->pid || stack->count > ZORN_GUI_STACK_FRAMES) return;
	unsigned index = (!strcmp(name, "launchd") || (gLaunchServicesWatch && !strcmp(name, "lsd"))) ? 0 : !strcmp(name, "SpringBoard") ? 1 : !strcmp(name, "backboardd") ? 2 : 3;
	if (index == 3 || !__sync_bool_compare_and_swap(&gGuiDiagnosticsBusy, 0, 1)) return;
	if (gGuiDiagnostics.processes[index].pid == stack->pid) {
		gGuiDiagnostics.stacks[index] = *stack;
		gGuiDiagnostics.stacks[index].tick = gGuiDiagnostics.tick;
		++gGuiDiagnostics.sequence;
	}
	__sync_lock_release(&gGuiDiagnosticsBusy);
}

extern "C" void zorn_ufs_gui_paths(const uint32_t paths[8])
{
	if (!gGuiWatch || !paths || !__sync_bool_compare_and_swap(&gGuiDiagnosticsBusy, 0, 1)) return;
	memcpy(gGuiDiagnostics.paths, paths, sizeof(gGuiDiagnostics.paths));
	++gGuiDiagnostics.sequence;
	__sync_lock_release(&gGuiDiagnosticsBusy);
}

extern "C" void zorn_ufs_gui_data_space(const uint64_t values[6])
{
	if (!gGuiWatch || !values || !__sync_bool_compare_and_swap(&gGuiDiagnosticsBusy, 0, 1)) return;
	memcpy(gGuiDiagnostics.dataSpace, values, sizeof(gGuiDiagnostics.dataSpace));
	++gGuiDiagnostics.sequence;
	__sync_lock_release(&gGuiDiagnosticsBusy);
}

static void zorn_gui_fill_footer(void)
{
	if (gTouchRawLog) return;
	if (!gGuiWatch || !__sync_bool_compare_and_swap(&gGuiDiagnosticsBusy, 0, 1)) return;
	ZornGuiFooter snapshot = gGuiDiagnostics;
	__sync_lock_release(&gGuiDiagnosticsBusy);
	memcpy(snapshot.magic, "ZORNGUI1", 8);
	// v17 uses the unused high halves of six UInt32 sensor words for event
	// dispatch counters. Same 3072-byte footer and single 4KiB log block as v16.
	snapshot.version = 17; snapshot.bytes = sizeof(snapshot);
#if defined(ZORN_VERIFIED_ROOT) && ZORN_VERIFIED_ROOT
	snapshot.dataPermissions[0] = static_cast<uint32_t>(zorn_data_permissions_status) | (static_cast<uint64_t>(zorn_data_permissions_stage) << 32);
	snapshot.dataPermissions[1] = zorn_data_permissions_checked | (static_cast<uint64_t>(zorn_data_permissions_total) << 32);
	snapshot.dataPermissions[2] = zorn_data_permissions_root_uid | (static_cast<uint64_t>(zorn_data_permissions_root_gid) << 32);
#endif
	memcpy(snapshot.startupPolicy, gStartupPolicy, sizeof(gStartupPolicy));
	snapshot.configuration[0] = dyld_flags;
	snapshot.configuration[1] = native_owner_cache_dyld_flags;
	snapshot.configuration[2] = cs_text_fixup_parsed;
	snapshot.configuration[3] = cs_text_fixup_applied;
	snapshot.configuration[4] = gGuiHoldSeconds;
	snapshot.configuration[5] = gWatchdogMode;
	snapshot.configuration[6] = native_owner_cache_stage;
	snapshot.configuration[7] = native_owner_cache_actual_mount_flags;
	uint64_t ns = 0;
	absolutetime_to_nanoseconds(mach_absolute_time() - gTraceEpoch, &ns);
	snapshot.ms = ns / 1000000;
	snapshot.freePages = vm_page_free_count; snapshot.activePages = vm_page_active_count;
	snapshot.inactivePages = vm_page_inactive_count; snapshot.wiredPages = vm_page_wire_count;
#if defined(ZORN_RAM_DATA) && ZORN_RAM_DATA
	snapshot.ram[0] = native_ram_block_reads; snapshot.ram[1] = native_ram_block_writes;
	snapshot.ram[2] = native_ram_block_failures;
#endif
#if defined(ZORN_DISPLAY) && ZORN_DISPLAY
	for (unsigned i = 0; i < 32; ++i) snapshot.display[i] = zorn_display_stats[i];
	for (unsigned i = 0; i < 12; ++i) snapshot.touch[i] = zorn_touch_runtime_stats[i];
#if defined(ZORN_TOUCH_RUNTIME_ENABLED) && ZORN_TOUCH_RUNTIME_ENABLED
	unsigned trace = 0, userStacks = 0;
	PE_parse_boot_argn("zorn_touch_trace", &trace, sizeof(trace));
	PE_parse_boot_argn("zorn_gui_stack", &userStacks, sizeof(userStacks));
	if (trace == 1 && userStacks == 0 && !gGuiKernelStacks) {
		// v18 explicitly replaces unused stack records. It cannot coexist
		// with stack samplers, and never changes the authorized 4KiB extent.
		uint32_t words[ZornTouchTrace::Words];
		ZornTouchTrace::snapshot(zorn_touch_trace_words, words);
		static_assert(sizeof(words) == sizeof(snapshot.stacks), "trace/stack union ABI");
		memcpy(snapshot.stacks, words, sizeof(words));
		snapshot.version = 18;
	}
	// v19 preserves every v18 field and the text-ring capacity. Overlay only
	// when all original/new values fit; otherwise leave the entire v18 image.
	if (snapshot.version == 18 && zorn_display_progress_overlay(snapshot.display))
		snapshot.version = 19;
	for (unsigned i = 0; i < 6; ++i)
		snapshot.touch[i + 1] = (snapshot.touch[i + 1] & 0xffffffffULL) |
		    (static_cast<uint64_t>(__atomic_load_n(&zorn_touch_edge_stats[i], __ATOMIC_RELAXED)) << 32);
#endif
	snapshot.keystore[0] = zorn_aks_stage;
	snapshot.keystore[1] = static_cast<uint32_t>(zorn_aks_status);
	snapshot.keystore[2] = zorn_aks_opens;
	snapshot.keystore[3] = zorn_aks_calls;
	snapshot.keystore[4] = zorn_aks_refused;
	snapshot.keystore[5] = (static_cast<uint64_t>(zorn_aks_last_selector) << 32) | static_cast<uint32_t>(zorn_aks_last_result);
#endif
	if (__sync_bool_compare_and_swap(&gGuiExitBusy, 0, 1)) {
		memcpy(snapshot.exits, gGuiExits, sizeof(snapshot.exits));
		memcpy(snapshot.exitDetails, gGuiExitDetails, sizeof(snapshot.exitDetails));
		__sync_lock_release(&gGuiExitBusy);
	}
	if (__sync_bool_compare_and_swap(&gGuiIpcBusy, 0, 1)) {
		memcpy(snapshot.ipc, gGuiIpc, sizeof(snapshot.ipc));
		memcpy(snapshot.receiverNames, gGuiReceiverNames, sizeof(snapshot.receiverNames));
		memcpy(snapshot.queries, gGuiQueries, sizeof(snapshot.queries));
		__sync_lock_release(&gGuiIpcBusy);
	}
	static_assert(ZORN_GUI_LOG_OFFSET + sizeof(snapshot) <= sizeof(gLogBlock), "GUI log bounds");
	memcpy(reinterpret_cast<uint8_t *>(&gLogBlock) + ZORN_GUI_LOG_OFFSET, &snapshot, sizeof(snapshot));
}

static void zorn_log_append(const char *text)
{
	zorn_log_put(text);
	(void)gZornWriteLog(&gLogBlock);
}

// Original Image4 may start before the UFS logger. Keep bounded observations
// in BSS, then commit them to the same authorized log block once it is ready.
// No service result, gate state or original executable is changed here.
struct ZornImage4Event {

	uint64_t pc, value;
	unsigned kind;
	bool early;
	char name[48];
	volatile unsigned ready;
};
static ZornImage4Event gImage4Events[64];
static volatile unsigned gImage4EventCount;
static unsigned gImage4Flushed;
static bool gImage4Replayed;

static void zorn_image4_flush(bool replay = false)
{
	if (!gLogArmed || __atomic_load_n(&gLogBusy, __ATOMIC_RELAXED) || !gZornWriteLog) return;
	if (!__sync_bool_compare_and_swap(&gLogBusy, 0, 1)) return;
	if (replay && !gImage4Replayed) {
		gImage4Replayed = true;
		gImage4Flushed = 0;
	}
	while (gImage4Flushed < 64 &&
	    __atomic_load_n(&gImage4Events[gImage4Flushed].ready, __ATOMIC_ACQUIRE)) {
		const ZornImage4Event &event = gImage4Events[gImage4Flushed++];
		char word[12];
		zorn_log_put(event.early ? "I4EARLY" : "I4EVENT");
		snprintf(word, sizeof(word), "I4K%08X", event.kind);
		zorn_log_put(word);
		snprintf(word, sizeof(word), "I4P%08X", static_cast<uint32_t>(event.pc));
		zorn_log_put(word);
		snprintf(word, sizeof(word), "I4H%08X", static_cast<uint32_t>(event.value >> 32));
		zorn_log_put(word);
		snprintf(word, sizeof(word), "I4L%08X", static_cast<uint32_t>(event.value));
		zorn_log_put(word);
		if (event.name[0]) {
			zorn_log_put("I4NBEGIN");
			for (unsigned pos = 0; pos < 47 && event.name[pos];) {
				char chunk[12] = {};
				for (unsigned i = 0; i < 11 && pos < 47 && event.name[pos]; i++, pos++)
					chunk[i] = event.name[pos];
				zorn_log_put(chunk);
			}
			zorn_log_put("I4NEND");
		}
		(void)gZornWriteLog(&gLogBlock);
	}
	__sync_lock_release(&gLogBusy);
}

extern "C" void zorn_ufs_image4_event(unsigned kind, uint64_t pc, uint64_t value, const char *name)
{
	unsigned index = __atomic_fetch_add(&gImage4EventCount, 1, __ATOMIC_RELAXED);
	if (index >= 64) return;
	ZornImage4Event &event = gImage4Events[index];
	event.pc = pc;
	event.value = value;
	event.kind = kind;
	event.early = !gLogArmed;
	if (name) {
		for (unsigned i = 0; i < 47 && name[i]; i++) {
			unsigned char c = name[i];
			event.name[i] = c >= 32 && c <= 126 ? static_cast<char>(c) : '?';
		}
	}
	__atomic_store_n(&event.ready, 1, __ATOMIC_RELEASE);
	// Replay the early service history at the first ignition gate observation;
	// normal syscall tracing may have wrapped the 4 KiB ring since UFS startup.
	zorn_image4_flush(kind == 9);
}

extern "C" void zorn_ufs_log_text(const char *text)
{
	if (!gLogArmed || __atomic_load_n(&gLogBusy, __ATOMIC_RELAXED) || !gZornWriteLog || !text) {
		return;
	}
	if (!__sync_bool_compare_and_swap(&gLogBusy, 0, 1)) return;
	unsigned macCount = __atomic_load_n(&gMacFailureCount, __ATOMIC_ACQUIRE);
	for (unsigned f = 0; f < macCount && f < 8; f++) {
		if (!__atomic_load_n(&gMacFailureReady[f], __ATOMIC_ACQUIRE)) continue;
		static const char hex[] = "0123456789ABCDEF";
		char number[10] = {};
		number[0] = 'E';
		for (unsigned i = 0; i < 8; i++) {
			number[i + 1] = hex[(gMacFailures[f].error >> (28 - i * 4)) & 15];
		}
		zorn_log_put("MACFAIL");
		zorn_log_put(gMacFailures[f].policy);
		zorn_log_put(number);
	}
	zorn_log_put("PANICBEGIN");
	for (unsigned pos = 0; pos < 255 && text[pos] != '\0';) {
		char chunk[12] = {};
		for (unsigned i = 0; i < 11 && pos < 255 && text[pos] != '\0'; i++, pos++) {
			unsigned char c = text[pos];
			chunk[i] = (c >= 32 && c <= 126) ? static_cast<char>(c) : ' ';
		}
		zorn_log_put(chunk);
	}
	zorn_log_put("PANICEND");
	(void)gZornWriteLog(&gLogBlock);
	__sync_lock_release(&gLogBusy);
}

// Retain the last eight original printf messages during one owner mount.
// Capturing under filesystem/console locks only touches this fixed BSS array;
// persistent transport writes happen after mount() has returned.
static unsigned gMountCaptureActive, gMountCaptureCount;
static int gMountCaptureBusy;
static char gMountMessages[8][256];

extern "C" void zorn_ufs_mount_printf(const char *format, va_list arguments)
{
	if (!format || !__atomic_load_n(&gMountCaptureActive, __ATOMIC_ACQUIRE)) return;
	if (!__sync_bool_compare_and_swap(&gMountCaptureBusy, 0, 1)) return;
	if (!__atomic_load_n(&gMountCaptureActive, __ATOMIC_ACQUIRE)) {
		__sync_lock_release(&gMountCaptureBusy); return;
	}
	unsigned sequence = __atomic_fetch_add(&gMountCaptureCount, 1, __ATOMIC_RELAXED);
	vsnprintf(gMountMessages[sequence % 8], sizeof(gMountMessages[0]), format, arguments);
	__sync_lock_release(&gMountCaptureBusy);
}

extern "C" void zorn_ufs_mount_capture(int start)
{
	if (start) {
		if (!__sync_bool_compare_and_swap(&gMountCaptureBusy, 0, 1)) return;
		gMountCaptureCount = 0;
		bzero(gMountMessages, sizeof(gMountMessages));
		__atomic_store_n(&gMountCaptureActive, 1, __ATOMIC_RELEASE);
		__sync_lock_release(&gMountCaptureBusy);
		return;
	}
	__atomic_store_n(&gMountCaptureActive, 0, __ATOMIC_RELEASE);
	if (!gLogArmed || !gZornWriteLog || !__sync_bool_compare_and_swap(&gMountCaptureBusy, 0, 1)) return;
	if (!__sync_bool_compare_and_swap(&gLogBusy, 0, 1)) {
		__sync_lock_release(&gMountCaptureBusy); return;
	}
	unsigned count = gMountCaptureCount;
	char number[12];
	snprintf(number, sizeof(number), "APC%08X", count);
	zorn_log_put(number);
	for (unsigned index = count > 8 ? count - 8 : 0; index < count; ++index) {
		zorn_log_put("APBEGIN");
		const char *text = gMountMessages[index % 8];
		for (unsigned pos = 0; pos < 255 && text[pos];) {
			char chunk[12] = {};
			for (unsigned i = 0; i < 11 && pos < 255 && text[pos]; ++i, ++pos) {
				unsigned char c = text[pos];
				chunk[i] = c >= 32 && c <= 126 ? static_cast<char>(c) : ' ';
			}
			zorn_log_put(chunk);
		}
		zorn_log_put("APEND");
	}
	(void)gZornWriteLog(&gLogBlock);
	__sync_lock_release(&gLogBusy);
	__sync_lock_release(&gMountCaptureBusy);
}

extern "C" void zorn_ufs_note_mac_failure(const char *policy, int error)
{
	if (error == 0) return;
	unsigned index = __atomic_fetch_add(&gMacFailureCount, 1, __ATOMIC_RELAXED);
	if (index >= 8) return;
	ZornMacFailure &failure = gMacFailures[index];
	const char *name = policy ? policy : "UNKNOWN";
	for (unsigned i = 0; i < 11 && name[i] != '\0'; i++) {
		unsigned char c = name[i];
		failure.policy[i] = (c >= 32 && c <= 126) ? static_cast<char>(c) : '?';
	}
	failure.error = static_cast<uint32_t>(error);
	__atomic_store_n(&gMacFailureReady[index], 1, __ATOMIC_RELEASE);
}

extern "C" void zorn_arm_return_after_tent(void)
{
	// Arm the selected checkpoint only after parse_machfile has returned.
	gReturnAfterTent = 1;
}

extern "C" void zorn_ufs_note_trust_cache(unsigned index)
{
	if (index < 32) {
		__atomic_fetch_or(&gTrustCacheMask, 1U << index, __ATOMIC_RELAXED);
	}
}

extern "C" void zorn_ufs_log_word(const char *text)
{
#if defined(ZORN_SMP_PREFLIGHT) && ZORN_SMP_PREFLIGHT
	// Pre-root eight-core diagnostics use the bounded SMP recorder only.
	// Do not issue persistence I/O from legacy tracing inside VM locks.
	if(__atomic_load_n(&zorn_smp_preflight_active,__ATOMIC_ACQUIRE))return;
#endif
	if (!gLogArmed || __atomic_load_n(&gLogBusy, __ATOMIC_RELAXED) || !gZornWriteLog || !text || text[0] == '\0') {
		return;
	}
	if (gCompactTrace && strcmp(text, gRecoveryCheckpoint) != 0) {
		static bool ioSeen[ZORN_TRACE_STAGE_COUNT];
		int stage = zorn_trace_stage_index(text);
		if (stage >= 0) {
			if (__atomic_exchange_n(&ioSeen[stage], true, __ATOMIC_RELAXED)) {
				__atomic_fetch_add(&gTraceSuppressed, 1, __ATOMIC_RELAXED);
				if (text[0] == 'L' && text[2] == '2' && !text[3] &&
				    (text[1] == 'C' || text[1] == 'D' || text[1] == 'V' || text[1] == 'W'))
					__atomic_fetch_add(&gStage2Suppressed, 1, __ATOMIC_RELAXED);
				return;
			}
		}
		bool bareAddress = strlen(text) == 8;
		for (unsigned i = 0; bareAddress && i < 8; ++i)
			bareAddress = (text[i] >= '0' && text[i] <= '9') || (text[i] >= 'A' && text[i] <= 'F');
		static unsigned bareAddresses;
		if (bareAddress && __atomic_fetch_add(&bareAddresses, 1, __ATOMIC_RELAXED) >= 8) return;
		static const char *const noise[] = {
			"TZAL", "TZOK", "EAT1", "EMAP", "EMOK", "ESET", "EIBG", "EINH", "EIRT",
			"ESTR", "ESTS", "ESTE", "EOBJ", "TLNK", "TENT", "TSIZ", "SAVR",
			"INMR", "I4KR", "IRET", "VMRT", "TCHK", "TALK", "TALC", "TLCK", "TLOC", "TLOK",
			"LRDE", "LRDK", "LROK", "LRDS", "LRSH", "LRUE", "LRUY"
		};
		for (unsigned i = 0; i < sizeof(noise) / sizeof(noise[0]); i++) {
			if (strcmp(text, noise[i]) == 0) {
				return;
			}
		}
		if (text[0] == 'C' && text[1] >= '0' && text[1] <= '9') {
			return;
		}
	}
	if (!__sync_bool_compare_and_swap(&gLogBusy, 0, 1)) return;
	zorn_log_append(text);
	bool reset = false;
	if (gReturnAfterTent && strcmp(text, gRecoveryCheckpoint) == 0) {
		gCheckpointSeen++;
		if (gCheckpointSkip != 0) {
			gCheckpointSkip--;
		} else {
			gReturnAfterTent = 0;
			reset = true;
		}
	}
	if (reset) zorn_checkpoint_reset_owned();
	__sync_lock_release(&gLogBusy);
}

extern "C" int zorn_ufs_trace_only(const char *text)
{
	if (!gLogArmed || !gLogOnly) {
		return 0;
	}
	zorn_ufs_log_word(text);
	return 1;
}

extern "C" int zorn_ufs_log_ready(void)
{
	// A transient writer is not an initialization failure: it may be
	// preempted while bsd_init reaches the one-time display probe.
	return gLogArmed && gWatchdogArmed;
}

extern "C" int zorn_ufs_display_summary(unsigned stage, unsigned error, unsigned size, int mayWait)
{
	if (!gLogArmed || !gZornWriteLog) return 0;
	bool acquired = false;
	for (unsigned attempt = 0; attempt < 1000; ++attempt) {
		if (__sync_bool_compare_and_swap(&gLogBusy, 0, 1)) { acquired = true; break; }
		if (!mayWait || ml_at_interrupt_context() || !ml_get_interrupts_enabled()) break;
		IOSleep(1);
	}
	if (!acquired) return 0;
	char word[12];
	snprintf(word, sizeof(word), "DSS%08X", stage); zorn_log_put(word);
	snprintf(word, sizeof(word), "DSE%08X", error); zorn_log_put(word);
	snprintf(word, sizeof(word), "DSZ%08X", size); zorn_log_put(word);
	zorn_log_put("DSPDONE");
	(void)gZornWriteLog(&gLogBlock);
	// Lifecycle completion must not disappear behind a preempted observer.
	// This is the same selected/skip policy as ordinary checkpoint logging.
	if (gReturnAfterTent && !strcmp(gRecoveryCheckpoint, "DSPDONE")) {
		gCheckpointSeen++;
		if (gCheckpointSkip) --gCheckpointSkip;
		else { gReturnAfterTent = 0; zorn_checkpoint_reset_owned(); }
	}
	__sync_lock_release(&gLogBusy);
	return 1;
}

// Brightness experiments must not fall through into userland because an
// unrelated observer was preempted while owning the diagnostic writer.
extern "C" int zorn_ufs_brightness_finish(const char *text, unsigned mode, int ok)
{
	if (!gLogArmed || !gZornWriteLog || !gWatchdogArmed || !text || mode<1 || mode>4) return 0;
	bool acquired=false;
	for (unsigned attempt=0; attempt<1000; ++attempt) {
		if (__sync_bool_compare_and_swap(&gLogBusy,0,1)) { acquired=true; break; }
		if (ml_at_interrupt_context() || !ml_get_interrupts_enabled()) break;
		IOSleep(1);
	}
	if (!acquired) return 0;
	zorn_log_put("UFD00000000"); zorn_log_put("USRBEGIN");
	const size_t length=strnlen(text,256);
	for (size_t pos=0;pos<length;) {
		char chunk[12]={};
		for(unsigned i=0;i<11 && pos<length;++i,++pos)
			chunk[i]=(text[pos]>=32 && text[pos]<=126)?text[pos]:' ';
		zorn_log_put(chunk);
	}
	zorn_log_put("USREND");
	zorn_log_put(ok?"BLSNAP":"BLFAIL");
	(void)gZornWriteLog(&gLogBlock);
	if (mode!=3 || !ok) {
		gReturnAfterTent=0;
		zorn_checkpoint_reset_owned();
		// PSCI is expected not to return. A failed recovery is not permission
		// to continue startup with an unqualified panel transaction.
		panic("zorn brightness recovery returned unexpectedly");
	}
	__sync_lock_release(&gLogBusy);
	return 1;
}

// Short read-only touch handoff: commit the complete bounded inventory and
// return directly to the prearmed recovery, without entering userland.
extern "C" int zorn_ufs_touch_probe_finish(const char *text)
{
	if (!gLogArmed || !gZornWriteLog || !gWatchdogArmed || !text || strnlen(text,512)>=512) return 0;
	bool acquired=false;
	for(unsigned attempt=0;attempt<1000;++attempt) {
		if(__sync_bool_compare_and_swap(&gLogBusy,0,1)){acquired=true;break;}
		if(ml_at_interrupt_context() || !ml_get_interrupts_enabled())break;
		IOSleep(1);
	}
	if(!acquired)return 0;
	zorn_log_put("UFD00000000");zorn_log_put("USRBEGIN");
	for(size_t pos=0;text[pos];) {
		char chunk[12]={};
		for(unsigned i=0;i<11 && text[pos];++i,++pos)chunk[i]=(text[pos]>=32 && text[pos]<=126)?text[pos]:' ';
		zorn_log_put(chunk);
	}
	zorn_log_put("USREND");zorn_log_put("TOUCHRO");
	(void)gZornWriteLog(&gLogBlock);gReturnAfterTent=0;zorn_checkpoint_reset_owned();
	panic("zorn touch handoff recovery returned unexpectedly");
}

// Replace only the diagnostic block's in-memory layout, after acquisition and
// GPIO restoration. GUI startup never runs in this explicit short probe mode.
extern "C" int zorn_ufs_touch_raw_finish(const char *text,const uint8_t *raw,unsigned bytes)
{
	unsigned mode=0;
	if(!PE_parse_boot_argn("zorn_touch",&mode,sizeof(mode)) || (mode!=4 && mode!=5) || !gGuiWatch ||
	    !gLogArmed || !gZornWriteLog || !gWatchdogArmed || !text || strnlen(text,512)>=512)return 0;
	if(bytes!=ZornTouchLog::Bytes)return zorn_ufs_touch_probe_finish(text);
	if(!__sync_bool_compare_and_swap(&gLogBusy,0,1))return 0;
	if(!ZornTouchLog::install(&gLogBlock,sizeof(gLogBlock),raw,bytes,mode==5?1:0)){__sync_lock_release(&gLogBusy);return 0;}
	gTouchRawLog=true;
	zorn_log_put("USRBEGIN");
	for(size_t pos=0;text[pos];) {
		char chunk[12]={};
		for(unsigned i=0;i<11 && text[pos];++i,++pos)chunk[i]=(text[pos]>=32 && text[pos]<=126)?text[pos]:' ';
		zorn_log_put(chunk);
	}
	zorn_log_put("USREND");zorn_log_put("TOUCHRAW");
	(void)gZornWriteLog(&gLogBlock);gReturnAfterTent=0;zorn_checkpoint_reset_owned();
	panic("zorn touch raw recovery returned unexpectedly");
}

static void zorn_trace_time(void)
{
	if (!gLogArmed || __atomic_load_n(&gLogBusy, __ATOMIC_RELAXED)) {
		return;
	}
	uint64_t ns = 0;
	absolutetime_to_nanoseconds(mach_absolute_time() - gTraceEpoch, &ns);
	char word[12];
	snprintf(word, sizeof(word), "TIM%08X", static_cast<uint32_t>(ns / 1000000));
	zorn_ufs_log_word(word);
}

extern "C" void zorn_ufs_copy_scope(uint64_t owner, uint64_t address, int enabled)
{
	if (!enabled) {
		if (gCopyTraceOwner == owner) gCopyTraceOwner = 0;
		return;
	}
	if (!gLogArmed) return;
	gCopyTraceOwner = owner;
	gCopyTraceCount = 0;
	if (gCompactTrace) return;
	zorn_trace_time();
	char word[12];
	snprintf(word, sizeof(word), "CPH%08X", static_cast<uint32_t>(address >> 32));
	zorn_ufs_log_word(word);
	snprintf(word, sizeof(word), "CPL%08X", static_cast<uint32_t>(address));
	zorn_ufs_log_word(word);
}

extern "C" void zorn_ufs_copy_stage(const char *stage, uint64_t owner)
{
	if (gCompactTrace) return;
	if (!gLogArmed || __atomic_load_n(&gLogBusy, __ATOMIC_RELAXED) || owner != gCopyTraceOwner || gCopyTraceCount++ >= 48) return;
	zorn_trace_time();
	zorn_ufs_log_word(stage);
}

extern "C" void zorn_ufs_copy_abort(uint64_t owner, uint64_t pc, uint64_t far,
    uint32_t esr, int recovery)
{
	if (!gLogArmed || __atomic_load_n(&gLogBusy, __ATOMIC_RELAXED) || owner != gCopyTraceOwner || gCopyTraceCount++ >= 48) return;
	zorn_trace_time();
	char word[12];
	snprintf(word, sizeof(word), "KPC%08X", static_cast<uint32_t>(pc));
	zorn_ufs_log_word(word);
	snprintf(word, sizeof(word), "KFH%08X", static_cast<uint32_t>(far >> 32));
	zorn_ufs_log_word(word);
	snprintf(word, sizeof(word), "KFL%08X", static_cast<uint32_t>(far));
	zorn_ufs_log_word(word);
	snprintf(word, sizeof(word), "KES%08X", esr);
	zorn_ufs_log_word(word);
	zorn_ufs_log_word(recovery ? "KREC" : "KNOREC");
}

extern "C" void zorn_ufs_thread_stage(const char *stage, uint64_t caller)
{
	static unsigned count;
	unsigned limit = gCompactTrace ? 24 : 256;
	bool selected = stage && !strcmp(stage, gRecoveryCheckpoint);
	if (!gLogArmed || __atomic_load_n(&gLogBusy, __ATOMIC_RELAXED) || (!selected && count++ >= limit)) {
		return;
	}
	zorn_trace_time();
	char word[12];
	snprintf(word, sizeof(word), "TCR%08X", static_cast<uint32_t>(caller));
	zorn_ufs_log_word(word);
	zorn_ufs_log_word(stage);
}

extern "C" void zorn_ufs_note_amfi_call(uint64_t pc, int finished)
{
	zorn_trace_time();
	char word[12];
	snprintf(word, sizeof(word), "ACB%08X", static_cast<uint32_t>(pc));
	zorn_ufs_log_word(word);
	zorn_ufs_log_word(finished ? "AMFIRET" : "AMFICALL");
}

extern "C" void zorn_ufs_note_pmgr_lookup(uint64_t pc, unsigned event)
{
	zorn_trace_time();
	char word[12];
	snprintf(word, sizeof(word), "PWM%08X", static_cast<uint32_t>(pc));
	zorn_ufs_log_word(word);
	zorn_ufs_log_word(event == 0 ? "PMWAIT" : event == 1 ? "PMFOUND" : "PMNONE");
}

extern "C" void zorn_ufs_note_user_svc(uint64_t pc, uint32_t trap)
{
	zorn_trace_time();
	char word[12];
	snprintf(word, sizeof(word), "UHI%08X", static_cast<uint32_t>(pc >> 32));
	zorn_ufs_log_word(word);
	snprintf(word, sizeof(word), "ULO%08X", static_cast<uint32_t>(pc));
	zorn_ufs_log_word(word);
	snprintf(word, sizeof(word), "SVC%08X", trap);
	zorn_ufs_log_word(word);
	zorn_ufs_log_word("USVC");
}

extern "C" void zorn_ufs_note_user_return(uint32_t trap, uint64_t result, uint32_t cpsr)
{
	zorn_trace_time();
	char word[12];
	snprintf(word, sizeof(word), "RET%08X", trap);
	zorn_ufs_log_word(word);
	snprintf(word, sizeof(word), "RHI%08X", static_cast<uint32_t>(result >> 32));
	zorn_ufs_log_word(word);
	snprintf(word, sizeof(word), "RLO%08X", static_cast<uint32_t>(result));
	zorn_ufs_log_word(word);
	snprintf(word, sizeof(word), "CPS%08X", cpsr);
	zorn_ufs_log_word(word);
	zorn_ufs_log_word("URET");
}

extern "C" void zorn_ufs_user_output(unsigned fd, const char *text, size_t length)
{
	if (!gLogArmed || __atomic_load_n(&gLogBusy, __ATOMIC_RELAXED) || !gZornWriteLog || !text || !length) return;
	zorn_trace_time();
	if (!__sync_bool_compare_and_swap(&gLogBusy, 0, 1)) return;
	char word[12];
	snprintf(word, sizeof(word), "UFD%08X", fd);
	zorn_log_put(word);
	zorn_log_put("USRBEGIN");
	if (length > 256) length = 256;
	for (size_t pos = 0; pos < length;) {
		char chunk[12] = {};
		for (unsigned i = 0; i < 11 && pos < length; i++, pos++) {
			unsigned char c = text[pos];
			chunk[i] = c >= 32 && c <= 126 ? static_cast<char>(c) : ' ';
		}
		zorn_log_put(chunk);
	}
	zorn_log_put("USREND");
	(void)gZornWriteLog(&gLogBlock);
	__sync_lock_release(&gLogBusy);
	zorn_ufs_log_word("UCON");
}

static bool zorn_text_has(const char *text, const char *needle)
{
	size_t size = strlen(needle);
	for (; *text; ++text) if (!strncmp(text, needle, size)) return true;
	return false;
}

extern "C" void zorn_ufs_capture_write(uint64_t fd, uint64_t address, uint64_t length)
{
	static unsigned count;
	if (gQuietGui) return;
	if (!gLogArmed || __atomic_load_n(&gLogBusy, __ATOMIC_RELAXED) || !length || (!gServiceTrace && count++ >= 4096)) return;
	char text[257] = {};
	size_t bytes = length < sizeof(text) - 1 ? static_cast<size_t>(length) : sizeof(text) - 1;
	if (copyin(address, text, bytes) == 0) {
		if (gServiceTrace || count > 512) {
			unsigned printable = 0;
			for (size_t i = 0; i < bytes; ++i) {
				unsigned char c = text[i];
				if ((c >= 32 && c <= 126) || c == '\n' || c == '\r' || c == '\t') ++printable;
			}
			if (printable * 10 < bytes * 9) return;
		}
		if (gServiceTrace) {
			// Keep useful service evidence past the old 4096-write window.
			// This filters observation only; it never changes write(2).
			static unsigned personaReports;
			if ((zorn_text_has(text, "kpersona_find_by_type()") || zorn_text_has(text, "Unable to find persona")) &&
			    personaReports++ >= 2) return;
			if ((zorn_text_has(text, "<Notice>") || zorn_text_has(text, "<Debug>")) &&
			    !zorn_text_has(text, "service state: running") && !zorn_text_has(text, "SpringBoard") &&
			    !zorn_text_has(text, "backboardd") && !zorn_text_has(text, "WindowServer")) return;
		}
		zorn_ufs_user_output(static_cast<unsigned>(fd), text, bytes);
	} else {
		if (count > 512) return;
		char word[12];
		snprintf(word, sizeof(word), "UFD%08X", static_cast<unsigned>(fd));
		zorn_ufs_log_word(word);
		zorn_ufs_log_word("UCOPYERR");
	}
}

extern "C" void zorn_ufs_exec_report(int pid, const char *path, int error, int returned)
{
	if (!gServiceTrace || !path) return;
	if (returned && !error) zorn_service_progress();
	if (gQuietGui) return;
	char text[176];
	int size = snprintf(text, sizeof(text), "EXEC %s pid=%d error=%d path=%.112s ",
	    returned ? "ACTIVATE_RETURN" : "BEGIN", pid, error, path);
	if (size > 0) zorn_ufs_user_output(0, text,
	    static_cast<size_t>(size) < sizeof(text) ? static_cast<size_t>(size) : sizeof(text) - 1);
}

extern "C" int zorn_ufs_gui_exit_wanted(int pid, const char *name)
{
	if (!gGuiWatch || !gLogArmed || !name) return 0;
	if (gLaunchServicesWatch && !strcmp(name, "lsd")) return 1;
	return pid == 1 || !strcmp(name, "SpringBoard") || !strcmp(name, "backboardd") ||
	    !strcmp(name, "launchd") || !strcmp(name, "watchdogd") ||
	    !strcmp(name, "liveactivitiesd") || !strcmp(name, "chronod") ||
	    !strcmp(name, "usermanagerd") || !strcmp(name, "runningboardd");
}

extern "C" void zorn_ufs_exit_report(int pid, const char *name, int status, uint32_t reasonNamespace, uint64_t reasonCode, const ZornGuiExitDetail *detail)
{
	if (!zorn_ufs_gui_exit_wanted(pid, name)) return;
	if (!__sync_bool_compare_and_swap(&gGuiExitBusy, 0, 1)) return;
	unsigned sequence = ++gGuiExitSequence;
	ZornGuiExit &event = gGuiExits[(sequence - 1) % 4];
	event = {};
	event.sequence = sequence; event.pid = pid; event.status = status;
	event.reasonNamespace = reasonNamespace; event.reasonCode = reasonCode;
	strlcpy(event.name, name, sizeof(event.name));
	gGuiExitDetails[(sequence - 1) % 4] = detail ? *detail : ZornGuiExitDetail{};
	gGuiExitDetails[(sequence - 1) % 4].fixups = cs_text_fixup_applied;
	__sync_lock_release(&gGuiExitBusy);
}

extern "C" void zorn_ufs_capture_sysctl(uint64_t address, uint64_t length, uint64_t newLength)
{
	static unsigned count;
	if (!gLogArmed || __atomic_load_n(&gLogBusy, __ATOMIC_RELAXED) || count++ >= 128) return;
	uint32_t name[12] = {};
	unsigned entries = length < 12 ? static_cast<unsigned>(length) : 12;
	bool valid = entries && copyin(address, name, entries * sizeof(name[0])) == 0;
	zorn_trace_time();
	if (!__sync_bool_compare_and_swap(&gLogBusy, 0, 1)) return;
	zorn_log_put("SCBEGIN");
	char word[12];
	snprintf(word, sizeof(word), "SCN%08X", static_cast<uint32_t>(length));
	zorn_log_put(word);
	snprintf(word, sizeof(word), "SCL%08X", static_cast<uint32_t>(newLength));
	zorn_log_put(word);
	if (valid) {
		for (unsigned i = 0; i < entries; i++) {
			snprintf(word, sizeof(word), "MIB%08X", name[i]);
			zorn_log_put(word);
		}
	} else {
		zorn_log_put("SCBAD");
	}
	zorn_log_put("SCEND");
	(void)gZornWriteLog(&gLogBlock);
	__sync_lock_release(&gLogBusy);
}

extern "C" void zorn_ufs_sysctl_point(const char *name, uint64_t handler, unsigned phase)
{
	static unsigned count;
	if (!gLogArmed || __atomic_load_n(&gLogBusy, __ATOMIC_RELAXED) || !name || count++ >= 512) return;
	zorn_trace_time();
	if (!__sync_bool_compare_and_swap(&gLogBusy, 0, 1)) return;
	zorn_log_put("SCTBEGIN");
	for (unsigned pos = 0; pos < 95 && name[pos];) {
		char chunk[12] = {};
		for (unsigned i = 0; i < 11 && pos < 95 && name[pos]; i++, pos++) {
			unsigned char c = name[pos];
			chunk[i] = c >= 32 && c <= 126 ? static_cast<char>(c) : ' ';
		}
		zorn_log_put(chunk);
	}
	zorn_log_put("SCTEND");
	char word[12];
	snprintf(word, sizeof(word), "SCH%08X", static_cast<uint32_t>(handler));
	zorn_log_put(word);
	snprintf(word, sizeof(word), "SCP%08X", phase);
	zorn_log_put(word);
	(void)gZornWriteLog(&gLogBlock);
	__sync_lock_release(&gLogBusy);
	const char *stages[] = { "SCMAC", "SCMACD", "SCCALL", "SCRET" };
	if (phase < 4) zorn_ufs_log_word(stages[phase]);
}

static IOReturn recordTransport(IOReturn result, uint32_t ocs)
{
	gRootDiagnostic.result = static_cast<uint32_t>(result);
	gRootDiagnostic.ocs = ocs;
	if (result != kIOReturnSuccess && gHost.hc) {
		gRootDiagnostic.hcs = read32(gHost.hc, 0x30);
		gRootDiagnostic.hce = read32(gHost.hc, 0x34);
		gRootDiagnostic.doorbell = read32(gHost.hc, 0x58);
		gRootDiagnostic.interrupt = read32(gHost.hc, 0x20);
		gRootDiagnostic.runStop = read32(gHost.hc, 0x60);
	}
	return result;
}

static void cacheCivac(const void *start, size_t length)
{
	uintptr_t address = reinterpret_cast<uintptr_t>(start) & ~uintptr_t(63);
	uintptr_t end = reinterpret_cast<uintptr_t>(start) + length;
	for (; address < end; address += 64) {
		__asm__ volatile("dc civac, %0" :: "r"(address) : "memory");
	}
	__asm__ volatile("dsb sy" ::: "memory");
}

static void cacheInvalidate(const void *start, size_t length)
{
	__asm__ volatile("dsb sy" ::: "memory");
	uintptr_t address = reinterpret_cast<uintptr_t>(start);
	for (uintptr_t end = address + length; address < end; address += 64) {
		__asm__ volatile("dc ivac, %0" :: "r"(address) : "memory");
	}
	__asm__ volatile("dsb sy" ::: "memory");
}

static void hostWrite(unsigned offset, uint32_t value)
{
	__asm__ volatile("dsb sy" ::: "memory");
	write32(gHost.hc, offset, value);
	__asm__ volatile("dsb sy" ::: "memory");
}

#include "RootQueue.h"
#include "RootCommands.h"
#include "ZornDataStore.h"

static IOReturn zorn_write_log4k(const void *source)
{
	if (source != &gLogBlock) return kIOReturnBadArgument;
	__atomic_fetch_add(&gLogWriteAttempts, 1, __ATOMIC_RELAXED);
	zorn_gui_fill_footer();
	uint64_t started = gGuiWatch ? mach_absolute_time() : 0;
	const void *transport=zorn_cpu_active_transport(source,sizeof(gLogBlock),gCpuActiveWire,gCpuActiveScratch);
	IOReturn result = hostWriteLog4k(transport);
	if (gGuiWatch) {
		uint64_t elapsed = 0;
		absolutetime_to_nanoseconds(mach_absolute_time() - started, &elapsed);
		__atomic_fetch_add(&gLogWriteNanoseconds, elapsed, __ATOMIC_RELAXED);
	}
	if (result == kIOReturnSuccess) __atomic_fetch_add(&gLogWriteSuccesses, 1, __ATOMIC_RELAXED);
	return result;
}

static bool hostBringUp(const char **why)
{
	zorn_say("UMAP");
	gHost.hc = mapPhys(UFS_HC_BASE, UFS_HC_SIZE, gHost.hcMap);
	if (!gHost.hc) {
		*why = "UMAP";
		return false;
	}
	gRootDiagnostic.cap = read32(gHost.hc, 0x00);
	gRootDiagnostic.version = read32(gHost.hc, 0x08);
	gRootDiagnostic.hcs = read32(gHost.hc, 0x30);
	gRootDiagnostic.hce = read32(gHost.hc, 0x34);

	zorn_say("UDMA");
	gHost.dma = IOBufferMemoryDescriptor::inTaskWithOptions(
	    kernel_task, static_cast<IOOptionBits>(kIODirectionInOut) | static_cast<IOOptionBits>(kIOMemoryPhysicallyContiguous) |
	    static_cast<IOOptionBits>(kIOMemoryMapperNone),
	    kDmaBytes, 4096);
	gHost.lock = IOLockAlloc();
	if (!gHost.dma || !gHost.lock) {
		*why = "UDMA";
		return false;
	}
	gHost.virt = static_cast<uint8_t *>(gHost.dma->getBytesNoCopy());
	IOByteCount contiguous = 0;
	gHost.phys = gHost.dma->getPhysicalSegment(0, &contiguous, kIOMemoryMapperNone);
	gRootDiagnostic.dma = gHost.phys;
	gRootDiagnostic.contiguous = contiguous;
	if (!gHost.virt || !gHost.phys || (gHost.phys & 4095) || contiguous < kDmaBytes ||
	    (!(read32(gHost.hc, 0) & 0x01000000) && gHost.phys + kDmaBytes > 0x100000000ULL)) {
		*why = "UDMA";
		return false;
	}
	bzero(gHost.virt, kDmaBytes);
	cacheCivac(gHost.virt, kDmaBytes);

	zorn_say("UQUE");
	if (!hostStopQueue(why)) {
		*why = "UQUE";
		return false;
	}
	uint32_t report[3] = { 0, 0, 0 };
	zorn_say("USMM");
	const char *smmu = smmuBypassStream(0x60, gHost.smmuMap, report, gHost.phys, kDmaBytes, gHost.hc);
	if (smmu) {
		*why = smmu;
		return false;
	}
	gHost.smmu = gHost.smmuMap->getVirtualAddress();
	uint32_t idr1 = read32(gHost.smmu, 0x24);
	gHost.cb = gHost.smmu + ((1U << (((idr1 >> 28) & 7) + 1)) + (report[0] >> 16)) * 4096;
	if (!hostStartQueue(why)) {
		*why = "UQUE";
		return false;
	}

	zorn_say("UNOP");
	if (hostNop() != kIOReturnSuccess) {
		*why = "UNOP";
		return false;
	}
	uint32_t power = 0;
	zorn_say("UPWR");
	if (hostQueryRead(0x03, 0x02, &power) != kIOReturnSuccess) {
		*why = "UPWR";
		return false;
	}
	gRootDiagnostic.power = power;
	if ((power & 0xff) != 0x11) {
		zorn_say("UWAK");
		uint8_t ssu[6] = { 0x1b, 0, 0, 0, 0x10, 0 };
		uint32_t scsi = 0;
		if (hostScsi(0xd0, ssu, 6, false, 0, 500000, &scsi) != kIOReturnSuccess) {
			*why = "UWAK";
			return false;
		}
		IODelay(50000);
	}
	zorn_say("ULUN");
	for (unsigned attempt = 0; attempt < 20; attempt++) {
		uint8_t tur[6] = { 0, 0, 0, 0, 0, 0 };
		uint32_t scsi = 0;
		if (hostScsi(0, tur, 6, false, 0, 200000, &scsi) == kIOReturnSuccess) {
			gHost.ready = true;
			return true;
		}
		if (gHost.poisoned) {
			break;
		}
		IODelay(10000);
	}
	*why = "ULUN";
	return false;
}

static const char *gptWord(const uint8_t *header, unsigned headerBytes, const uint8_t *entries, unsigned entryBytes, uint32_t used)
{
	if (!header || !entries || headerBytes != 4096 || used > entryBytes) {
		return "USZ";
	}
	static const uint8_t magic[8] = { 'E', 'F', 'I', ' ', 'P', 'A', 'R', 'T' };
	for (unsigned i = 0; i < 8; i++) {
		if (header[i] != magic[i]) {
			return "USIG";
		}
	}
	if (houjiLe64(header + 24) != 1 || houjiLe64(header + 72) != 2) {
		return "ULBA";
	}
	if (houjiLe32(header + 12) != 92 || houjiLe32(header + 84) != 128) {
		return "USZ";
	}
	if (houjiCrc32(header, 92, true) != houjiLe32(header + 16)) {
		return "UCRC";
	}
	if (houjiCrc32(entries, used) != houjiLe32(header + 88)) {
		return "UENT";
	}
	return nullptr;
}

static IOLock *gZornOsLock;
static uint8_t gZornOsBounce[4096];
static uint64_t gZornOsAbs;
static uint64_t gZornOsBytes;
static uint64_t gZornSystemOsAbs;
static uint64_t gZornSystemOsBytes;
static uint64_t gZornOsWindowAbs;
static uint64_t gZornOsWindowBytes;
static dev_t gZornDevices[2] = {static_cast<dev_t>(-1), static_cast<dev_t>(-1)};

extern "C" dev_t zorn_ufs_window_device(unsigned index)
{
	return index < 2 ? gZornDevices[index] : static_cast<dev_t>(-1);
}

extern "C" uint64_t zorn_ufs_window_bytes(unsigned index)
{
	return index == 1 ? gZornSystemOsBytes : index == 0 ? gZornOsBytes : 0;
}

extern "C" int zorn_ufs_window_healthy(unsigned index)
{
	return index < 2 && gZornDevices[index] != static_cast<dev_t>(-1) && gHost.ready && !gHost.poisoned;
}

static int zorn_os_read(uint64_t abs, void *dst, size_t bytes)
{
	uint8_t *out = static_cast<uint8_t *>(dst);
	while (bytes) {
		uint32_t skip = static_cast<uint32_t>(abs & 4095U);
		uint32_t room = 4096U - skip;
		uint32_t take = bytes < room ? static_cast<uint32_t>(bytes) : room;
		uint64_t started = gGuiWatch ? mach_absolute_time() : 0;
		IOReturn result = hostRead4k(0, abs / 4096U, 1, gZornOsBounce);
		if (gGuiWatch) {
			uint64_t elapsed = 0;
			absolutetime_to_nanoseconds(mach_absolute_time() - started, &elapsed);
			__atomic_fetch_add(&gOsReadBlocks, 1, __ATOMIC_RELAXED);
			__atomic_fetch_add(&gOsReadNanoseconds, elapsed, __ATOMIC_RELAXED);
			if (result != kIOReturnSuccess)
				__atomic_fetch_add(&gOsReadErrors, 1, __ATOMIC_RELAXED);
		}
		if (result != kIOReturnSuccess) {
			return EIO;
		}
#if ZORN_VERIFIED_ROOT
		uint64_t block = abs & ~uint64_t(4095);
		unsigned index;
		uint64_t logical, valid;
		if (block >= gZornOsWindowAbs && block - gZornOsWindowAbs < gZornOsWindowBytes) {
			index = 0; logical = block - gZornOsWindowAbs; valid = gZornOsWindowBytes - logical;
		} else if (block >= gZornSystemOsAbs && block - gZornSystemOsAbs < gZornSystemOsBytes) {
			index = 1; logical = block - gZornSystemOsAbs; valid = gZornSystemOsBytes - logical;
		} else return EAUTH;
		if (valid > 4096) valid = 4096;
		if (skip > valid || take > valid - skip ||
		    zorn_verified_block(index, logical, gZornOsBounce, static_cast<size_t>(valid))) return EAUTH;
#endif
		memcpy(out, gZornOsBounce + skip, take);
		out += take;
		abs += take;
		bytes -= take;
	}
	return 0;
}

extern "C" int zorn_os_transfer(void *, uint64_t offset, void *data, size_t bytes, int iswrite)
{
	if (iswrite) {
		return EROFS;
	}
	if ((!data && bytes) || offset > gZornOsBytes || bytes > gZornOsBytes - offset || !gZornOsLock) {
		return EINVAL;
	}
	IOLockLock(gZornOsLock);
	int error = zorn_os_read(gZornOsAbs + offset, data, bytes);
	IOLockUnlock(gZornOsLock);
	if (error == 0) {
		if (zorn_os_xfers == 0) {
			zorn_os_first_off = offset;
			zorn_os_first_len = bytes;
		}
		zorn_os_xfers++;
		if (offset == 0 && bytes >= 4096 && data) {
			if (zorn_nx_checksum_ok(static_cast<const uint8_t *>(data))) {
				zorn_os_sbok = 1;
			} else {
				zorn_os_ckbad = 1;
			}
		}
	}
	return error;
}

extern "C" int zorn_systemos_transfer(void *, uint64_t offset, void *data, size_t bytes, int iswrite)
{
	if (iswrite) return EROFS;
	if ((!data && bytes) || !gZornSystemOsBytes || offset > gZornSystemOsBytes ||
	    bytes > gZornSystemOsBytes - offset || !gZornOsLock) return EINVAL;
	// Both md devices share the same bounce buffer and UFS command queue.
	IOLockLock(gZornOsLock);
	int error = zorn_os_read(gZornSystemOsAbs + offset, data, bytes);
	IOLockUnlock(gZornOsLock);
	static unsigned traced;
	if (__atomic_fetch_add(&traced, 1, __ATOMIC_RELAXED) < 12) {
		char word[12];
		snprintf(word, sizeof(word), "SRO%08X", static_cast<uint32_t>(offset));
		zorn_say(word);
		snprintf(word, sizeof(word), "SRL%08X", static_cast<uint32_t>(bytes));
		zorn_say(word);
		snprintf(word, sizeof(word), "SRE%08X", static_cast<uint32_t>(error));
		zorn_say(word);
	}
	return error;
}

extern "C" void zorn_os_fail(int err)
{
	if (zorn_os_ckbad) {
		zorn_os_hold("CKBAD");
	}
	if (zorn_os_xfers == 0) {
		zorn_os_hold("NORD");
	}
	if ((err & 0xff) != 0x5c) {
		zorn_os_hold_tagged('A', err);
	}
	if (!zorn_os_sbok) {
		if (zorn_os_first_off == 0) {
			zorn_os_hold_tagged('L', static_cast<int>(zorn_os_first_len));
		}
		zorn_os_hold_tagged('O', static_cast<int>(zorn_os_first_off));
	}
	if (zorn_os_seen_bs == 0 || zorn_os_seen_blocks == 0) {
		zorn_os_hold("NOBS");
	}
	uint64_t device_bytes = zorn_os_seen_blocks * zorn_os_seen_bs;
	if (device_bytes < gZornOsBytes) {
		zorn_os_hold("SMALL");
	}
	if (device_bytes > gZornOsBytes) {
		zorn_os_hold("BIG");
	}
	if (zorn_os_seen_bs != 4096) {
		zorn_os_hold_tagged('B', static_cast<int>(zorn_os_seen_bs));
	}
	zorn_os_hold("SAME");
}

static void zorn_ufs_publish_os(uint64_t start, const uint8_t *page)
{
	if (houjiLe32(page + 8) != 1) {
		zorn_ufs_stop("SHNGMS");
	}
	uint32_t count = houjiLe32(page + 12);
	if (count == 0 || count > 8) {
		zorn_ufs_stop("SHNGMS");
	}
	ZornSha256 sha;
	zornShaInit(&sha);
	zornShaUpdate(&sha, page, 4064);
	uint8_t digest[32];
	zornShaFinal(&sha, digest);
	if (memcmp(digest, page + 4064, 32) != 0) {
		zorn_ufs_stop("SHNGMS");
	}
	const uint8_t *os = nullptr;
	for (uint32_t index = 0; index < count; index++) {
		const uint8_t *entry = page + 24 + 128 * index;
		if (entry[0] == 'O' && entry[1] == 'S' && entry[2] == 0) {
			os = entry;
			break;
		}
	}
	if (!os) {
		zorn_ufs_stop("OSNAME");
	}
	uint64_t window = houjiLe64(os + 32);
	uint64_t window_bytes = houjiLe64(os + 40);
	if ((window & 4095) || window / 4096 > 0xffffffffULL - start) {
		zorn_ufs_stop("OSGPT");
	}
	gZornOsWindowAbs = start * 4096ULL + window;
	gZornOsWindowBytes = window_bytes;
#if ZORN_VERIFIED_ROOT
	if (window != 1048576ULL || !zorn_verified_open(0, window_bytes)) zorn_ufs_stop("VR0NO");
#endif
	static uint8_t disk[4096];
	if (hostRead4k(0, static_cast<uint32_t>(start + window / 4096), 1, disk) != kIOReturnSuccess) {
		zorn_ufs_stop("OSGPT");
	}
#if ZORN_VERIFIED_ROOT
	if (zorn_verified_block(0, 0, disk, sizeof(disk))) zorn_ufs_stop("VR0GPT");
#endif
	static const uint8_t gpt[8] = { 'E', 'F', 'I', ' ', 'P', 'A', 'R', 'T' };
	for (unsigned i = 0; i < 8; i++) {
		if (disk[512 + i] != gpt[i]) {
			zorn_ufs_stop("OSGPT");
		}
	}
	if (houjiLe32(disk + 524) != 92 || houjiLe64(disk + 584) != 2 || houjiLe32(disk + 596) != 128) {
		zorn_ufs_stop("OSGPT");
	}
	const uint8_t *part = disk + 1024;
	bool empty = true;
	for (unsigned i = 0; i < 16; i++) {
		if (part[i] != 0) {
			empty = false;
		}
	}
	if (empty) {
		zorn_ufs_stop("OSGPT");
	}
	uint64_t first = houjiLe64(part + 32);
	uint64_t last = houjiLe64(part + 40);
	if (first < 34 || last < first || (last - first + 1) > (0xffffffffffffffffULL / 512)) {
		zorn_ufs_stop("OSGPT");
	}
	uint64_t bytes = (last - first + 1) * 512;
	uint64_t into = first * 512;
	if ((bytes & 4095) || bytes == 0 || into > window_bytes || bytes > window_bytes - into) {
		zorn_ufs_stop("OSGPT");
	}
	gZornOsAbs = start * 4096ULL + window + into;
	gZornOsBytes = bytes;
	static uint8_t nx[4096];
	if (zorn_os_read(gZornOsAbs, nx, sizeof(nx)) != 0 ||
	    nx[32] != 'N' || nx[33] != 'X' || nx[34] != 'S' || nx[35] != 'B' || houjiLe32(nx + 36) != 4096) {
		zorn_ufs_stop("NXNO");
	}
	if (!zorn_nx_checksum_ok(nx)) {
		zorn_ufs_stop("CKBAD");
	}
	uint64_t blocks = houjiLe64(nx + 40);
	if (blocks > (0xffffffffffffffffULL / 4096) || blocks * 4096 != bytes) {
		zorn_ufs_stop("NXNO");
	}
	gZornOsLock = IOLockAlloc();
	if (!gZornOsLock) {
		zorn_ufs_stop("MDNO");
	}
	gZornDevices[0] = mdevadd_ops(0, bytes, zorn_os_transfer, nullptr);
	if (gZornDevices[0] == static_cast<dev_t>(-1)) {
		zorn_ufs_stop("MDNO");
	}
	zorn_os_root_pending = 1;
	zorn_say("MD0");
}

static void zorn_ufs_publish_systemos(uint64_t start, uint64_t end, const uint8_t *page)
{
	// In this pinned IPSW SystemOS is a raw APFS container, unlike the OS
	// member's inner 512-byte-sector GPT. Never apply OS's GPT offset to it.
	const uint8_t *systemos = nullptr;
	uint32_t count = houjiLe32(page + 12);
	for (uint32_t index = 0; index < count; index++) {
		const uint8_t *entry = page + 24 + 128 * index;
		if (memcmp(entry, "SystemOS\0", 9) == 0) {
			if (systemos) zorn_ufs_stop("SYSDUP");
			systemos = entry;
		}
	}
	if (!systemos) zorn_ufs_stop("SYSNAME");
	uint64_t offset = houjiLe64(systemos + 32);
	uint64_t bytes = houjiLe64(systemos + 40);
	if (offset != 6079643648ULL || bytes != 3303014400ULL || end < start ||
	    (offset & 4095) || (bytes & 4095) ||
	    offset / 4096 > end - start || bytes / 4096 > end - start + 1 - offset / 4096 ||
	    start + offset / 4096 + bytes / 4096 - 1 > 0xffffffffULL) zorn_ufs_stop("SYSBND");
	gZornSystemOsAbs = start * 4096ULL + offset;
	gZornSystemOsBytes = bytes;
#if ZORN_VERIFIED_ROOT
	if (!zorn_verified_open(1, bytes)) zorn_ufs_stop("VR1NO");
#endif
	static uint8_t nx[4096], returned[4096];
	if (hostRead4k(0, static_cast<uint32_t>(start + offset / 4096), 1, nx) != kIOReturnSuccess)
		zorn_ufs_stop("SYSREAD");
#if ZORN_VERIFIED_ROOT
	if (zorn_verified_block(1, 0, nx, sizeof(nx))) zorn_ufs_stop("VR1NX");
#endif
	if (memcmp(nx + 32, "NXSB", 4) || houjiLe32(nx + 36) != 4096 ||
	    houjiLe64(nx + 40) != bytes / 4096 || !zorn_nx_checksum_ok(nx)) zorn_ufs_stop("SYSNX");
	// Identity pin for this metadata block only. This is not full-volume
	// owner authentication; per-block VerifiedRoot policy is a separate step.
	static const uint8_t expected[32] = {
		0x55,0x78,0x02,0x85,0x7a,0x9d,0xbf,0x40,0x1a,0xf6,0x4d,0x4e,0xa2,0x8f,0x83,0xb1,
		0x6a,0x55,0x6a,0x75,0x64,0x2c,0x16,0x44,0xad,0xed,0x53,0x66,0x57,0x75,0x77,0x26
	};
	ZornSha256 sha;
	uint8_t digest[32];
	zornShaInit(&sha); zornShaUpdate(&sha, nx, sizeof(nx)); zornShaFinal(&sha, digest);
	if (memcmp(digest, expected, sizeof(digest))) zorn_ufs_stop("SYSHASH");
	if (zorn_systemos_transfer(nullptr, 0, returned, sizeof(returned), 0) ||
	    memcmp(returned, nx, sizeof(nx))) zorn_ufs_stop("SYSCOPY");
	zorn_say("SYSREAD");
	if (zorn_systemos_transfer(nullptr, 0, returned, sizeof(returned), 1) != EROFS)
		zorn_ufs_stop("SYSRW");
	zorn_say("SYSRO");
	if (zorn_systemos_transfer(nullptr, bytes, returned, 1, 0) != EINVAL)
		zorn_ufs_stop("SYSOOB");
	zorn_say("SYSBND");
	dev_t device = mdevadd_ops(1, bytes, zorn_systemos_transfer, nullptr);
	if (device == static_cast<dev_t>(-1)) zorn_ufs_stop("SYSMD");
	gZornDevices[1] = device;
	char word[12];
	snprintf(word, sizeof(word), "SDV%08X", static_cast<uint32_t>(device));
	zorn_say(word);
	zorn_say("SYSOK");
}

// The flashed SHNGROOT image is 9382658048 bytes. The log block is 4 MiB after it.
static const uint64_t kZornImageBlocks = 9382658048ULL / 4096ULL;
static const uint64_t kZornLogGuard = 1024ULL;

static bool zorn_ufs_show_saved_log(uint64_t start, uint64_t end)
{
	if (end < start || end - start < kZornImageBlocks + kZornLogGuard ||
	    start + kZornImageBlocks + kZornLogGuard > 0xffffffffULL) {
		return false;
	}
	uint32_t lba = static_cast<uint32_t>(start + kZornImageBlocks + kZornLogGuard);
	static uint8_t block[4096];
	if (hostRead4k(0, lba, 1, block) != kIOReturnSuccess) {
		return false;
	}
	static const char magic[] = { 'Z', 'O', 'R', 'N', 'L', 'O', 'G', '1' };
	for (unsigned i = 0; i < 8; i++) {
		if (i == 7 ? (block[i] != '1' && block[i] != '2' && block[i] != '3') :
		    block[i] != static_cast<uint8_t>(magic[i])) {
			zorn_say("NOLOG");
			return false;
		}
	}
	uint32_t count = block[8] | (uint32_t(block[9]) << 8) |
	    (uint32_t(block[10]) << 16) | (uint32_t(block[11]) << 24);
	bool v2 = block[7] != '1';
	uint32_t capacity = block[7] == '3' ? ZORN_GUI_LOG_SLOTS : (v2 ? 340 : 510);
	uint32_t width = v2 ? 12 : 8;
	uint32_t next = v2 ? houjiLe32(block + 12) : 0;
	if (count > capacity || next >= capacity) {
		return false;
	}
	static char text[4200];
	unsigned n = 0;
	for (uint32_t i = 0; i < count && n + 1 < sizeof(text); i++) {
		if (i != 0 && n + 1 < sizeof(text)) {
			text[n++] = ' ';
		}
		uint32_t index = v2 && count == capacity ? (next + i) % capacity : i;
		const uint8_t *slot = block + 16 + index * width;
		for (unsigned c = 0; c < width - 1 && slot[c] != 0 && n + 1 < sizeof(text); c++) {
			text[n++] = static_cast<char>(slot[c]);
		}
	}
	text[n] = '\0';
	const char *show = text;
	if (n > 1500) {
		show = text + (n - 1500);
	}
	zorn_show_words(show);
	return true;
}

static void zorn_ufs_arm_log(uint64_t start, uint64_t end)
{
	if (end < start || end - start < kZornImageBlocks + kZornLogGuard ||
	    start + kZornImageBlocks + kZornLogGuard > 0xffffffffULL) {
		zorn_say("WRNO");
		return;
	}
	gLogLba = static_cast<uint32_t>(start + kZornImageBlocks + kZornLogGuard);
	gLogBlocks = 1;
	int logOnly = 0;
	PE_parse_boot_argn("zorn_log_only", &logOnly, sizeof(logOnly));
	gLogOnly = logOnly == 1;
	PE_parse_boot_argn("zorn_wdt", &gWatchdogMode, sizeof(gWatchdogMode));
	int hashBudget = 0;
	PE_parse_boot_argn("zorn_hash_budget", &hashBudget, sizeof(hashBudget));
	gHashBudgetSeconds = hashBudget > 0 && hashBudget <= 120 ? static_cast<unsigned>(hashBudget) : 0;
	int compact = 0;
	PE_parse_boot_argn("zorn_trace_compact", &compact, sizeof(compact));
	gCompactTrace = compact == 1;
	int serviceTrace = 0;
	PE_parse_boot_argn("zorn_service_trace", &serviceTrace, sizeof(serviceTrace));
	gServiceTrace = serviceTrace == 1;
	int guiWatch = 0;
	PE_parse_boot_argn("zorn_gui_watch", &guiWatch, sizeof(guiWatch));
	gGuiWatch = guiWatch == 1;
	int kernelStacks = 0;
	PE_parse_boot_argn("zorn_gui_kstack", &kernelStacks, sizeof(kernelStacks));
	gGuiKernelStacks = gGuiWatch && kernelStacks == 1;
#if defined(ZORN_DISPLAY) && ZORN_DISPLAY
	unsigned displayProgress = 0, progressTrace = 0, progressStacks = 0;
	PE_parse_boot_argn("zorn_display_progress", &displayProgress, sizeof(displayProgress));
	PE_parse_boot_argn("zorn_touch_trace", &progressTrace, sizeof(progressTrace));
	PE_parse_boot_argn("zorn_gui_stack", &progressStacks, sizeof(progressStacks));
	zorn_display_progress_configure(gGuiWatch && displayProgress == 1 && progressTrace == 1 &&
	    !progressStacks && !gGuiKernelStacks ? 1 : 0);
#endif
	gGuiDiagnostics.dataSpace[0] = 0xffffffffU;
	int quietGui = 0;
	PE_parse_boot_argn("zorn_gui_quiet", &quietGui, sizeof(quietGui));
	gQuietGui = gGuiWatch && quietGui == 1;
	int guiService = 0;
	PE_parse_boot_argn("zorn_gui_service", &guiService, sizeof(guiService));
	gLaunchServicesWatch = gGuiWatch && guiService == 1;
	unsigned guiServiceThread = 0;
	PE_parse_boot_argn("zorn_gui_service_thread", &guiServiceThread, sizeof(guiServiceThread));
	gGuiServiceThread = gLaunchServicesWatch && guiServiceThread <= 63 ? guiServiceThread : 0;
	int guiHold = 0;
	PE_parse_boot_argn("zorn_gui_hold", &guiHold, sizeof(guiHold));
	gGuiHoldSeconds = gGuiWatch && guiHold >= 30 && guiHold <= 1800 ? static_cast<unsigned>(guiHold) : 0;
	int execBudget = 0;
	PE_parse_boot_argn("zorn_exec_budget", &execBudget, sizeof(execBudget));
	gExecBudgetSeconds = execBudget > 0 && execBudget <= 180 ? static_cast<unsigned>(execBudget) : 0;
	int skip = 0;
	PE_parse_boot_argn("zorn_checkpoint_skip", &skip, sizeof(skip));
	if (skip >= 0 && skip <= 1024) {
		gCheckpointSkip = static_cast<unsigned>(skip);
	}
	int earlyCheckpoint = 0;
	PE_parse_boot_argn("zorn_checkpoint_early", &earlyCheckpoint, sizeof(earlyCheckpoint));
	if (earlyCheckpoint == 1) {
		gReturnAfterTent = 1;
	}
	char checkpoint[9] = {};
	if (PE_parse_boot_argn("zorn_checkpoint", checkpoint, sizeof(checkpoint))) {
		checkpoint[8] = '\0';
		bool valid = checkpoint[0] != '\0' && strlen(checkpoint) <= 7;
		for (unsigned i = 0; checkpoint[i] != '\0'; i++) {
			if (!((checkpoint[i] >= 'A' && checkpoint[i] <= 'Z') ||
			    (checkpoint[i] >= '0' && checkpoint[i] <= '9'))) {
				valid = false;
			}
		}
		if (valid) {
			memcpy(gRecoveryCheckpoint, checkpoint, sizeof(checkpoint));
		}
	}
	gZornWriteLog = zorn_write_log4k;
	for (unsigned i = 0; i < sizeof(gLogBlock); i++) {
		reinterpret_cast<uint8_t *>(&gLogBlock)[i] = 0;
	}
	static const char magic[] = { 'Z', 'O', 'R', 'N', 'L', 'O', 'G', '2' };
	for (unsigned i = 0; i < 8; i++) {
		gLogBlock.magic[i] = magic[i];
	}
	if (gGuiWatch) gLogBlock.magic[7] = 'D';
	zorn_say("WRGO");
	gLogEnabled = true;
	gTraceEpoch = mach_absolute_time();
	unsigned cpuActive=0,cpuProgress=0,cpuTrace=0,cpuUserStack=0,cpuKernelStack=0;
	PE_parse_boot_argn("zorn_cpu_active",&cpuActive,sizeof(cpuActive));
	PE_parse_boot_argn("zorn_display_progress",&cpuProgress,sizeof(cpuProgress));
	PE_parse_boot_argn("zorn_touch_trace",&cpuTrace,sizeof(cpuTrace));
	PE_parse_boot_argn("zorn_gui_stack",&cpuUserStack,sizeof(cpuUserStack));
	PE_parse_boot_argn("zorn_gui_kstack",&cpuKernelStack,sizeof(cpuKernelStack));

	unsigned cpuCores=0,cpuSmp=0,cpuContinue=0,cpuPublish=0,cpuStop=0,cpuStore=0,cpuRetained=0,cpuBrightness=0,cpuTouch=0;
	PE_parse_boot_argn("cpus",&cpuCores,sizeof(cpuCores));
	PE_parse_boot_argn("zorn_smp_preflight",&cpuSmp,sizeof(cpuSmp));
	PE_parse_boot_argn("zorn_smp_continue",&cpuContinue,sizeof(cpuContinue));
	PE_parse_boot_argn("zorn_smp_root_publish",&cpuPublish,sizeof(cpuPublish));
	PE_parse_boot_argn("zorn_smp_stop",&cpuStop,sizeof(cpuStop));
	PE_parse_boot_argn("zorn_data_store",&cpuStore,sizeof(cpuStore));
	PE_parse_boot_argn("zorn_data_retained",&cpuRetained,sizeof(cpuRetained));
	PE_parse_boot_argn("zorn_brightness",&cpuBrightness,sizeof(cpuBrightness));
	PE_parse_boot_argn("zorn_touch",&cpuTouch,sizeof(cpuTouch));
	bool cpuFixedProfile=false;
#if defined(ZORN_SMP_PREFLIGHT) && ZORN_SMP_PREFLIGHT && defined(ZORN_DATA_8G) && ZORN_DATA_8G && defined(ZORN_RAM_DATA) && ZORN_RAM_DATA && defined(ZORN_TOUCH_RUNTIME_ENABLED) && ZORN_TOUCH_RUNTIME_ENABLED
	cpuFixedProfile=cpuCores==8 && cpuSmp==8 && cpuContinue==1 && cpuPublish==1 && !cpuStop &&
	    cpuStore==2 && cpuRetained==1 && cpuBrightness==3 && cpuTouch==6;
#endif
	zorn_cpu_active_configure(cpuFixedProfile && cpuActive==1 && cpuProgress==1 && cpuTrace==1 &&
	    !cpuUserStack && !cpuKernelStack && gGuiWatch && gGuiHoldSeconds==300 &&
	    gWatchdogMode==1 ? 1 : 0,gTraceEpoch);

	if (!__sync_bool_compare_and_swap(&gLogBusy, 0, 1)) return;
	gLogArmed = true;
	if (zorn_write_log4k(&gLogBlock) != kIOReturnSuccess) {
		gLogArmed = false;
		gLogEnabled = false;
		__sync_lock_release(&gLogBusy);
		zorn_say("WRNO");
		return;
	}
	static uint8_t check[4096];
	if (hostRead4k(0, gLogLba, 1, check) != kIOReturnSuccess ||
	    memcmp(check, &gLogBlock, sizeof(gLogBlock)) != 0) {
		gLogArmed = false;
		gLogEnabled = false;
		__sync_lock_release(&gLogBusy);
		zorn_say("WRNO");
		return;
	}
	__sync_lock_release(&gLogBusy);
	zorn_say("WROK");
	char trustStatus[12];
	snprintf(trustStatus, sizeof(trustStatus), "TC%08X", gTrustCacheMask);
	zorn_ufs_log_word(trustStatus);
	if (gWatchdogMode == 1 || gWatchdogMode == 2) {
		zorn_watchdog_start();
	}
	zorn_image4_flush();
}

static const uint8_t *gptNamed(const uint8_t *entries, uint32_t count, uint32_t size, const char *name)
{
	for (uint32_t index = 0; index < count; index++) {
		const uint8_t *entry = entries + index * size;
		bool match = true;
		unsigned i = 0;
		for (; name[i] != '\0'; i++) {
			if (entry[56 + i * 2] != static_cast<uint8_t>(name[i]) || entry[57 + i * 2] != 0) {
				match = false;
				break;
			}
		}
		if (match && entry[56 + i * 2] == 0 && entry[57 + i * 2] == 0) {
			return entry;
		}
	}
	return nullptr;
}

static void zorn_psci_reset(void)
{
	__asm__ volatile("dsb sy" ::: "memory");
	register uint64_t x0 __asm__("x0") = 0x84000009ULL;
	register uint64_t x1 __asm__("x1") = 0;
	register uint64_t x2 __asm__("x2") = 0;
	register uint64_t x3 __asm__("x3") = 0;
	__asm__ volatile("smc #0" : "+r"(x0), "+r"(x1), "+r"(x2), "+r"(x3)
	                 :: "x4", "x5", "x6", "x7", "x8", "x9", "x10", "x11", "x12",
	                    "x13", "x14", "x15", "x16", "x17", "cc", "memory");
}

static bool zorn_set_recovery_bcb(void)
{
	if (gMiscLba == 0 || gMiscLba == gLogLba) {
		return false;
	}
	static uint8_t page[4096];
	static uint8_t back[4096];
	if (hostTryRead4k(0, gMiscLba, 1, page) != kIOReturnSuccess) {
		return false;
	}
	for (unsigned i = 0; i < 864; i++) {
		page[i] = 0;
	}
	static const char command[] = "boot-recovery";
	static const char args[] = "recovery\n";
	for (unsigned i = 0; i < sizeof(command); i++) {
		page[i] = static_cast<uint8_t>(command[i]);
	}
	for (unsigned i = 0; i < sizeof(args); i++) {
		page[64 + i] = static_cast<uint8_t>(args[i]);
	}
	gRecoveryArmed = true;
	IOReturn wrote = hostWriteMisc4k(page);
	gRecoveryArmed = false;
	if (wrote != kIOReturnSuccess) {
		return false;
	}
	if (hostTryRead4k(0, gMiscLba, 1, back) != kIOReturnSuccess ||
	    memcmp(page, back, sizeof(page)) != 0) {
		return false;
	}
	return true;
}

#include "ZornWatchdog.h"

extern "C" void zorn_ufs_gui_hold_tick(void)
{
	// Explicit bounded observation window, distinct from exec progress.
	// The scheduled observer must reach this call; an unscheduled kernel
	// still loses its pet, and no call after the hard deadline pets it.
	if (!gGuiHoldSeconds || !gLogArmed || !gWatchdogArmed || gWatchdogMode != 1) return;
	uint64_t ns = 0;
	absolutetime_to_nanoseconds(mach_absolute_time() - gTraceEpoch, &ns);
	if (ns >= static_cast<uint64_t>(gGuiHoldSeconds) * 1000000000ULL) return;
	uint64_t result = zorn_wdt_call(0x86000007U, 0, 0).status;
	zorn_ufs_log_word(result ? "GHOLDERR" : "GHOLDOK");
}

extern "C" void zorn_ufs_gui_flush(void)
{
	// Called once by the scheduled observer after its final BSS stage update.
	// Never pet an expired watchdog. No task, vnode or preemption lock is held.
	if (!gGuiWatch || !gLogArmed || !gZornWriteLog) return;
	for (unsigned attempt = 0; attempt < 3; ++attempt) {
		if (__sync_bool_compare_and_swap(&gLogBusy, 0, 1)) {
			zorn_log_put("GUIEND");
			IOReturn result = gZornWriteLog(&gLogBlock);
			__sync_lock_release(&gLogBusy);
			if (result == kIOReturnSuccess) return;
		}
		if (attempt != 2) IOSleep(10);
	}
}

extern "C" void zorn_ufs_runtime_snapshot(void)
{
	if (!gLogArmed || __atomic_load_n(&gLogBusy, __ATOMIC_RELAXED)) return;
	uint64_t ns = 0;
	absolutetime_to_nanoseconds(mach_absolute_time() - gTraceEpoch, &ns);
	uint64_t ms = ns / 1000000;
	char text[224];
	int count = snprintf(text, sizeof(text), "MEM ms=%llu free=%u active=%u inactive=%u wired=%u pages fixups=%u parsed=%u hold=%u ",
	    ms, vm_page_free_count, vm_page_active_count, vm_page_inactive_count, vm_page_wire_count,
	    cs_text_fixup_applied, cs_text_fixup_parsed, gGuiHoldSeconds);
	if (count > 0) zorn_ufs_user_output(0, text, static_cast<size_t>(count) < sizeof(text) ? static_cast<size_t>(count) : sizeof(text) - 1);
#if defined(ZORN_RAM_DATA) && ZORN_RAM_DATA
	count = snprintf(text, sizeof(text), "RAMDATA reads=%llu writes=%llu errors=%llu ",
	    native_ram_block_reads, native_ram_block_writes, native_ram_block_failures);
	if (count > 0) zorn_ufs_user_output(0, text, static_cast<size_t>(count) < sizeof(text) ? static_cast<size_t>(count) : sizeof(text) - 1);
#endif
#if defined(ZORN_DISPLAY) && ZORN_DISPLAY
	count = snprintf(text, sizeof(text), "DISPLAY stage=%llu error=%08x registered=%llu clients=%llu accepted=%llu rejected=%llu transfers=%llu status=%08x bytes=%llu pixels=%llu ",
	    zorn_display_stats[0], static_cast<unsigned>(zorn_display_stats[1]), zorn_display_stats[6],
	    zorn_display_stats[8], zorn_display_stats[23], zorn_display_stats[24], zorn_display_stats[29],
	    static_cast<unsigned>(zorn_display_stats[30]), zorn_display_stats[31], zorn_display_stats[26]);
	if (count > 0) zorn_ufs_user_output(0, text, static_cast<size_t>(count) < sizeof(text) ? static_cast<size_t>(count) : sizeof(text) - 1);
#endif
	ZornGuiExit exits[4] = {};
	if (gGuiWatch && __sync_bool_compare_and_swap(&gGuiExitBusy, 0, 1)) {
		memcpy(exits, gGuiExits, sizeof(exits));
		__sync_lock_release(&gGuiExitBusy);
	}
	for (const ZornGuiExit &event : exits) {
		if (!event.sequence) continue;
		count = snprintf(text, sizeof(text), "GUI EXIT #%u %s[%d] status=%x namespace=%u code=%llx ",
		    event.sequence, event.name, event.pid, event.status, event.reasonNamespace, event.reasonCode);
		if (count > 0) zorn_ufs_user_output(0, text, static_cast<size_t>(count) < sizeof(text) ? static_cast<size_t>(count) : sizeof(text) - 1);
	}
	ZornGuiIpc ipc[3][2] = {};
	if (gGuiWatch && __sync_bool_compare_and_swap(&gGuiIpcBusy, 0, 1)) {
		memcpy(ipc, gGuiIpc, sizeof(ipc));
		__sync_lock_release(&gGuiIpcBusy);
	}
	static const char *names[] = { "launchd", "SpringBoard", "backboardd" };
	for (unsigned i = 0; i < 3; ++i) for (const ZornGuiIpc &event : ipc[i]) {
		if (!event.sequence) continue;
		count = snprintf(text, sizeof(text), "IPC_ATTEMPT #%u %s[%d] msg=%d receiver=%d bits=%x ",
		    event.sequence, i == 0 && gLaunchServicesWatch ? "lsd" : names[i], event.pid, event.message, event.receiver, event.bits);
		if (count > 0) zorn_ufs_user_output(0, text, static_cast<size_t>(count) < sizeof(text) ? static_cast<size_t>(count) : sizeof(text) - 1);
	}
#if defined(ZORN_DISPLAY) && ZORN_DISPLAY
	count = snprintf(text, sizeof(text), "AKS stage=%u status=%x opens=%u calls=%u refused=%u last=%u result=%x ",
	    zorn_aks_stage, static_cast<unsigned>(zorn_aks_status), zorn_aks_opens, zorn_aks_calls,
	    zorn_aks_refused, zorn_aks_last_selector, static_cast<unsigned>(zorn_aks_last_result));
	if (count > 0) zorn_ufs_user_output(0, text, static_cast<size_t>(count) < sizeof(text) ? static_cast<size_t>(count) : sizeof(text) - 1);
	count = snprintf(text, sizeof(text), "HID stage=%u family=%x event=%x resource=%u ",
	    zorn_hid_stage, static_cast<unsigned>(zorn_hid_family_status), static_cast<unsigned>(zorn_hid_event_status), zorn_hid_resource);
	if (count > 0) zorn_ufs_user_output(0, text, static_cast<size_t>(count) < sizeof(text) ? static_cast<size_t>(count) : sizeof(text) - 1);
#endif
	count = snprintf(text, sizeof(text), "LOGIO writes=%llu ok=%llu dedup=%llu stage2=%llu ",
	    __atomic_load_n(&gLogWriteAttempts, __ATOMIC_RELAXED),
	    __atomic_load_n(&gLogWriteSuccesses, __ATOMIC_RELAXED),
	    __atomic_load_n(&gTraceSuppressed, __ATOMIC_RELAXED),
	    __atomic_load_n(&gStage2Suppressed, __ATOMIC_RELAXED));
	if (count > 0) zorn_ufs_user_output(0, text, static_cast<size_t>(count) < sizeof(text) ? static_cast<size_t>(count) : sizeof(text) - 1);
	count = snprintf(text, sizeof(text), "UFSIO blocks=%llu errors=%llu read_us=%llu log_us=%llu ",
	    __atomic_load_n(&gOsReadBlocks, __ATOMIC_RELAXED),
	    __atomic_load_n(&gOsReadErrors, __ATOMIC_RELAXED),
	    __atomic_load_n(&gOsReadNanoseconds, __ATOMIC_RELAXED) / 1000,
	    __atomic_load_n(&gLogWriteNanoseconds, __ATOMIC_RELAXED) / 1000);
	if (count > 0) zorn_ufs_user_output(0, text, static_cast<size_t>(count) < sizeof(text) ? static_cast<size_t>(count) : sizeof(text) - 1);
#if defined(ZORN_RAM_DATA) && ZORN_RAM_DATA
	if (gZornDataMode) {
		count = snprintf(text, sizeof(text), "DSTORE mode=%u open=%u state=%u header=%u gpt=%u/%u present=%llu writes=%llu loaded=%llu errors=%llu ",
		    gZornDataMode, gZornDataOpened ? 1U : 0U, native_data_persist_state, native_data_persist_header,
		    native_data_persist_gpt, native_data_persist_gpt_after, native_data_persist_present,
		    native_data_persist_writes, native_data_persist_loaded, native_data_persist_errors);
		if (count > 0) zorn_ufs_user_output(0, text, static_cast<size_t>(count) < sizeof(text) ? static_cast<size_t>(count) : sizeof(text) - 1);
		count = snprintf(text, sizeof(text), "DKEEP state=%u error=%d cookie=%llx ",
		    zorn_data_marker_state, zorn_data_marker_error, zorn_data_marker_cookie);
		if (count > 0) zorn_ufs_user_output(0, text, static_cast<size_t>(count) < sizeof(text) ? static_cast<size_t>(count) : sizeof(text) - 1);
	}
#endif
#if defined(ZORN_DISPLAY) && ZORN_DISPLAY
	zorn_brightness_checkpoint();
#endif
#if defined(ZORN_SMP_PREFLIGHT) && ZORN_SMP_PREFLIGHT
	count=zorn_armcpu_runtime(text,sizeof(text));
	if(count>0 && unsigned(count)<sizeof(text))zorn_ufs_user_output(0,text,unsigned(count));
#endif
}

static void zorn_service_progress(void)
{
	if (!gLogArmed || __atomic_load_n(&gLogBusy, __ATOMIC_RELAXED) || !gExecBudgetSeconds) return;
	uint64_t ns = 0;
	absolutetime_to_nanoseconds(mach_absolute_time() - gTraceEpoch, &ns);
	uint64_t ms = ns / 1000000;
	if (ms - gExecLastObservationMs < 10000) return;
	gExecLastObservationMs = ms;
	zorn_ufs_runtime_snapshot();
	// A separate explicit budget permits pets only after actual successful
	// exec image activation, never from a timer or console output. A hang
	// still bites in 55 seconds; even repeated exec progress stops at 180 s.
	if (gWatchdogArmed && gWatchdogMode == 1 && ms < static_cast<uint64_t>(gExecBudgetSeconds) * 1000) {
		uint64_t result = zorn_wdt_call(0x86000007U, 0, 0).status;
		zorn_ufs_log_word(result ? "EPETERR" : "EPET");
	}
}

static void zorn_hash_name(void)
{
	zorn_log_put("HFBEGIN");
	for (unsigned pos = 0; pos < sizeof(gHashFile) - 1 && gHashFile[pos];) {
		char chunk[12] = {};
		for (unsigned i = 0; i < 11 && pos < sizeof(gHashFile) - 1 && gHashFile[pos]; ++i, ++pos) {
			unsigned char c = gHashFile[pos];
			chunk[i] = c >= 32 && c <= 126 ? static_cast<char>(c) : ' ';
		}
		zorn_log_put(chunk);
	}
	zorn_log_put("HFEND");
}

extern "C" void zorn_ufs_hash_file(const char *name, uint64_t limit)
{
	if (!gLogArmed || __atomic_load_n(&gLogBusy, __ATOMIC_RELAXED) || !gZornWriteLog) return;
	if (!__sync_bool_compare_and_swap(&gLogBusy, 0, 1)) return;
	strlcpy(gHashFile, name ? name : "unknown", sizeof(gHashFile));
	gHashLastLogBytes = 0;
	zorn_hash_name();
	char word[12];
	snprintf(word, sizeof(word), "HL%08X", static_cast<uint32_t>(limit));
	zorn_log_put(word);
	(void)gZornWriteLog(&gLogBlock);
	__sync_lock_release(&gLogBusy);
}

extern "C" void zorn_ufs_hash_progress(uint64_t completed, uint64_t limit)
{
	uint64_t ns = 0;
	absolutetime_to_nanoseconds(mach_absolute_time() - gTraceEpoch, &ns);
	uint64_t elapsedMs = ns / 1000000;
	bool pet = gWatchdogArmed && gWatchdogMode == 1 && gHashBudgetSeconds && completed &&
	    elapsedMs < static_cast<uint64_t>(gHashBudgetSeconds) * 1000 && elapsedMs - gHashLastPetMs >= 10000;
	uint64_t petStatus = 0;
	if (pet) {
		petStatus = zorn_wdt_call(0x86000007U, 0, 0).status;
		if (!petStatus) gHashLastPetMs = elapsedMs;
	}
	if ((!pet && completed != limit && completed - gHashLastLogBytes < 32 * 1024 * 1024) ||
	    !gLogArmed || __atomic_load_n(&gLogBusy, __ATOMIC_RELAXED) || !gZornWriteLog) return;
	if (!__sync_bool_compare_and_swap(&gLogBusy, 0, 1)) return;
	gHashLastLogBytes = completed;
	zorn_hash_name();
	char word[12];
	snprintf(word, sizeof(word), "TIM%08X", static_cast<uint32_t>(elapsedMs)); zorn_log_put(word);
	snprintf(word, sizeof(word), "HG%08X", static_cast<uint32_t>(completed)); zorn_log_put(word);
	snprintf(word, sizeof(word), "HL%08X", static_cast<uint32_t>(limit)); zorn_log_put(word);
	if (pet) zorn_log_put(petStatus ? "HPETERR" : "HPET");
	(void)gZornWriteLog(&gLogBlock);
	__sync_lock_release(&gLogBusy);
}

extern "C" void zorn_ufs_hash_result(int error)
{
	char word[12];
	snprintf(word, sizeof(word), "HRE%08X", static_cast<uint32_t>(error));
	zorn_say(word);
}

extern "C" void zorn_ufs_data_result(int stage, int error, int readonly, dev_t device)
{
	char word[12];
	snprintf(word, sizeof(word), "DST%08X", static_cast<unsigned>(stage)); zorn_say(word);
	snprintf(word, sizeof(word), "DRE%08X", static_cast<unsigned>(error)); zorn_say(word);
	snprintf(word, sizeof(word), "DRO%08X", static_cast<unsigned>(readonly)); zorn_say(word);
	snprintf(word, sizeof(word), "DDV%08X", static_cast<unsigned>(device)); zorn_say(word);
#if defined(ZORN_RAM_DATA) && ZORN_RAM_DATA
	snprintf(word, sizeof(word), "DPT%08X", static_cast<unsigned>(native_owner_data_probe_stage)); zorn_say(word);
	snprintf(word, sizeof(word), "DPE%08X", static_cast<unsigned>(native_owner_data_probe_status)); zorn_say(word);
	snprintf(word, sizeof(word), "DRD%08X", static_cast<unsigned>(native_ram_block_reads)); zorn_say(word);
	snprintf(word, sizeof(word), "DWR%08X", static_cast<unsigned>(native_ram_block_writes)); zorn_say(word);
	snprintf(word, sizeof(word), "DER%08X", static_cast<unsigned>(native_ram_block_failures)); zorn_say(word);
	if(gZornDataMode) {
		char text[224];
		int count=snprintf(text,sizeof(text),"DSTORE mode=%u open=%u state=%u header=%u gpt=%u/%u present=%llu writes=%llu loaded=%llu errors=%llu ",
		    gZornDataMode,gZornDataOpened?1U:0U,native_data_persist_state,native_data_persist_header,
		    native_data_persist_gpt,native_data_persist_gpt_after,native_data_persist_present,
		    native_data_persist_writes,native_data_persist_loaded,native_data_persist_errors);
		if(count>0 && unsigned(count)<sizeof(text))zorn_ufs_user_output(0,text,unsigned(count));
	}
#endif
	zorn_say(!error && stage == 4 && !readonly ? "DATAOK" : "DATAFAIL");
}

static void zorn_checkpoint_reset_owned(void)
{
	zorn_log_append("RSET");
	char trustStatus[12];
	snprintf(trustStatus, sizeof(trustStatus), "TC%08X", gTrustCacheMask);
	zorn_log_append(trustStatus);
	snprintf(trustStatus, sizeof(trustStatus), "HIT%08X", gCheckpointSeen);
	zorn_log_append(trustStatus);
	bool wrote = zorn_set_recovery_bcb();
	zorn_log_append(wrote ? "BCBK" : "BCBN");
	if (wrote) {
		bool stoppedWatchdog=false;
		if (gWatchdogArmed) {
			ZornSmcResult stopped=zorn_wdt_call(0x86000005U,2,0);
			stoppedWatchdog=stopped.status==0;
			zorn_log_append(stoppedWatchdog?"WSTOP":"WSTERR");
		}
		zorn_psci_reset();
		if(stoppedWatchdog) {
			(void)zorn_wdt_call(0x86000007U,0,0);
			ZornSmcResult enabled=zorn_wdt_call(0x86000005U,3,0);
			zorn_log_append(enabled.status==0?"WREARM":"WREFAIL");
		}
		zorn_log_append("PSRT");
	}
}

static void zorn_checkpoint_reset(void)
{
	// Never steal an in-flight block or release another CPU's ownership.
	// The independent watchdog remains the fallback if the writer is busy.
	if (!__sync_bool_compare_and_swap(&gLogBusy, 0, 1)) return;
	zorn_checkpoint_reset_owned();
	__sync_lock_release(&gLogBusy);
}

extern "C" void zorn_ufs_smp_record(const char *text,unsigned length,int final)
{
	unsigned mode=0;
	if(!PE_parse_boot_argn("zorn_smp_preflight",&mode,sizeof(mode)) || mode!=8 ||
	   !gLogArmed || !gWatchdogArmed || !gZornWriteLog || !text || !length || length>3000)
		panic("zorn SMP log bounds/readiness");
	bool acquired=false;
	for(unsigned attempt=0;attempt<(final?40U:1U);++attempt) {
		if(__sync_bool_compare_and_swap(&gLogBusy,0,1)){acquired=true;break;}
		if(final)IOSleep(5);
	}
	if(!acquired){if(final)panic("zorn SMP final log busy");return;}
	// One complete, bounded snapshot; never combine halves from two samples.
	gLogBlock.count=0;gLogBlock.next=0;
	zorn_log_put("UFD00000000");zorn_log_put("USRBEGIN");
	for(unsigned pos=0;pos<length;) {
		char word[12]={};
		for(unsigned n=0;n<11 && pos<length;++n,++pos)word[n]=(text[pos]>=32 && text[pos]<=126)?text[pos]:' ';
		zorn_log_put(word);
	}
	zorn_log_put("USREND");zorn_log_put(final?"SMPFINAL":"SMPSAMPLE");
	(void)gZornWriteLog(&gLogBlock);
	if(final){zorn_checkpoint_reset_owned();panic("zorn SMP reset returned");}
	__sync_lock_release(&gLogBusy);
}

extern "C" void zorn_ufs_read_gpt(void)
{
	zorn_say("UFS0");
	const char *why = "UFS0";
	if (!hostBringUp(&why)) {
		zorn_ufs_stop(why);
	}
	static uint8_t header[4096];
	static uint8_t entries[32768];
	zorn_say("URD1");
	if (hostRead4k(0, 1, 1, header) != kIOReturnSuccess) {
		zorn_ufs_stop("URD1");
	}
	uint32_t count = houjiLe32(header + 80);
	uint32_t size = houjiLe32(header + 84);
	if (houjiLe64(header + 72) != 2 || size != 128 || count == 0 || count > 256) {
		zorn_ufs_stop(houjiLe64(header + 72) == 2 ? "UENT" : "ULBA");
	}
	uint32_t bytes = count * size;
	uint32_t blocks = bytes / 4096;
	if (bytes != blocks * 4096 || blocks > 8) {
		zorn_ufs_stop("UENT");
	}
	zorn_say("URD2");
	if (hostRead4k(0, 2, blocks, entries) != kIOReturnSuccess) {
		zorn_ufs_stop("URD2");
	}
	why = gptWord(header, sizeof(header), entries, sizeof(entries), bytes);
	if (why) {
		zorn_ufs_stop(why);
	}
	const uint8_t *userdata = gptNamed(entries, count, size, "userdata");
	const uint8_t *misc = gptNamed(entries, count, size, "misc");
	if (!userdata) {
		zorn_ufs_stop("UNAME");
	}
	if (misc) {
		uint64_t miscStart = houjiLe64(misc + 32);
		if (miscStart != 0 && miscStart <= 0xffffffffULL) {
			gMiscLba = static_cast<uint32_t>(miscStart);
		}
	}
	uint64_t start = houjiLe64(userdata + 32);
	uint64_t end = houjiLe64(userdata + 40);
	if (start == 0 || start > 0xffffffffULL || end < start) {
		zorn_ufs_stop("UDAT");
	}
	static uint8_t page[4096];
	zorn_say("UDAT");
	if (hostRead4k(0, static_cast<uint32_t>(start), 1, page) != kIOReturnSuccess) {
		zorn_ufs_stop("UDAT");
	}
	uint32_t at0 = houjiLe32(page);
	uint32_t at400 = houjiLe32(page + 0x400);
	uint16_t ext4 = static_cast<uint16_t>(page[0x438] | (page[0x439] << 8));
	if (at0 == 0xF2F52010U || at400 == 0xF2F52010U) {
		zorn_ufs_stop("UF2FS");
	}
	if (ext4 == 0xEF53) {
		zorn_ufs_stop("UEXT4");
	}
	if (page[32] == 'N' && page[33] == 'X' && page[34] == 'S' && page[35] == 'B') {
		zorn_ufs_stop("UNXSB");
	}
	if (page[1024] == 'H' && page[1025] == '+' ) {
		zorn_ufs_stop("UHFS");
	}
	if (page[1024] == 'H' && page[1025] == 'X') {
		zorn_ufs_stop("UHFSX");
	}
	if (houjiLe32(page + 1024) == 0xE0F5E1E2U) {
		zorn_ufs_stop("UERFS");
	}
	if (page[0] == 'h' && page[1] == 's' && page[2] == 'q' && page[3] == 's') {
		zorn_ufs_stop("USQSH");
	}
	for (unsigned i = 0; i + 4 <= sizeof(page); i += 4) {
		if (houjiLe32(page + i) == 0xF2F52010U) {
			zorn_ufs_stop("UF2FS");
		}
	}
	unsigned at = 0;
	while (at < sizeof(page) && page[at] == 0) {
		at++;
	}
	if (at >= sizeof(page)) {
		zorn_ufs_stop("UEMPT");
	}
	static const uint8_t rootMagic[8] = { 'S', 'H', 'N', 'G', 'R', 'O', 'O', 'T' };
	bool root = true;
	for (unsigned i = 0; i < 8; i++) {
		if (page[i] != rootMagic[i]) {
			root = false;
			break;
		}
	}
	if (root) {
		zorn_ufs_arm_log(start, end);
#if defined(ZORN_SMP_PREFLIGHT) && ZORN_SMP_PREFLIGHT
		unsigned continueSmp=0;PE_parse_boot_argn("zorn_smp_continue",&continueSmp,sizeof(continueSmp));
		int smpOk=zorn_armcpu_preflight();
		if(!smpOk || continueSmp!=1)panic("zorn SMP preflight returned before root publication");
		zorn_ufs_log_word("SMP8GO");
#endif
#if defined(ZORN_RAM_DATA) && ZORN_RAM_DATA
		unsigned storeMode = 0, reset = 0;
		PE_parse_boot_argn("zorn_data_store", &storeMode, sizeof(storeMode));
		PE_parse_boot_argn("sheng-data-reset", &reset, sizeof(reset));
		if (storeMode && (storeMode > 2 || reset || !zornDataGeometry(start, end, houjiLe64(page + 16), gLogLba)))
			zorn_ufs_stop("DBOUNDS");
		gZornDataMode = storeMode;
		gZornDataHeaderCrc = houjiLe32(header + 16); gZornDataEntriesCrc = houjiLe32(header + 88);
		gZornDataEntryBytes = bytes; gZornDataBackupLba = houjiLe64(header + 32);
		memcpy(gZornDataDiskGuid, header + 56, 16); gZornDataGeometryReady = true;
#endif
		zorn_ufs_publish_os(start, page);
		zorn_ufs_publish_systemos(start, end, page);
		return;
	}
	zorn_ufs_stop("NOSHNG");
}
}

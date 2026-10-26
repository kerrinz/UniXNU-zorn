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
#include <libkern/libkern.h>
#include <sys/errno.h>
#include <sys/types.h>
#include <pexpert/pexpert.h>
#include "GccUfs.h"
#include "RootDiagnostics.h"
#include "TransferPoll.h"
#include "GiuliaSmmuTakeover.h"
#include "HoujiGptCheck.h"
#include "ZornSha256.h"

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
static bool gLogEnabled = false;
static bool gLogArmed = false;
static uint64_t gTraceEpoch;
static uint64_t gCopyTraceOwner;
static unsigned gCopyTraceCount;
static bool gRecoveryArmed = false;
static bool gLogOnly = false;
static bool gWatchdogArmed = false;
static int gWatchdogMode = 0;
static uint32_t gLogLba = 0;
static uint32_t gMiscLba = 0;
static uint32_t gLogBlocks = 0;
static int gLogBusy = 0;
static int gReturnAfterTent = 0;
static char gRecoveryCheckpoint[9] = "IRET";
static unsigned gCheckpointSkip;
static unsigned gCheckpointSeen;
static bool gCompactTrace;
static void zorn_checkpoint_reset(void);
static void zorn_watchdog_start(void);
struct ZornLogBlock {
	char magic[8];
	uint32_t count;
	uint32_t next;
	char word[340][12];
};
static_assert(sizeof(ZornLogBlock) == 4096, "log must fit one UFS block");
static ZornLogBlock gLogBlock;
struct ZornMacFailure {
	char policy[12];
	uint32_t error;
};
static ZornMacFailure gMacFailures[8];
static unsigned gMacFailureCount;
static uint32_t gTrustCacheMask;
static IOReturn (*gZornWriteLog)(const void *) = nullptr;

extern "C" void zorn_show_words(const char *text);

static void zorn_log_put(const char *text)
{
	char *slot = gLogBlock.word[gLogBlock.next];
	gLogBlock.next = (gLogBlock.next + 1) % 340;
	if (gLogBlock.count < 340) {
		gLogBlock.count++;
	}
	for (int i = 0; i < 12; i++) {
		slot[i] = 0;
	}
	for (int i = 0; i < 11 && text[i] != '\0'; i++) {
		slot[i] = text[i];
	}
}

static void zorn_log_append(const char *text)
{
	zorn_log_put(text);
	(void)gZornWriteLog(&gLogBlock);
}

extern "C" void zorn_ufs_log_text(const char *text)
{
	if (!gLogArmed || gLogBusy || !gZornWriteLog || !text) {
		return;
	}
	gLogBusy = 1;
	for (unsigned f = 0; f < gMacFailureCount; f++) {
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
	gLogBusy = 0;
}

extern "C" void zorn_ufs_note_mac_failure(const char *policy, int error)
{
	if (error == 0 || gMacFailureCount >= 8) {
		return;
	}
	ZornMacFailure &failure = gMacFailures[gMacFailureCount++];
	const char *name = policy ? policy : "UNKNOWN";
	for (unsigned i = 0; i < 11 && name[i] != '\0'; i++) {
		unsigned char c = name[i];
		failure.policy[i] = (c >= 32 && c <= 126) ? static_cast<char>(c) : '?';
	}
	failure.error = static_cast<uint32_t>(error);
}

extern "C" void zorn_arm_return_after_tent(void)
{
	// Arm the selected checkpoint only after parse_machfile has returned.
	gReturnAfterTent = 1;
}

extern "C" void zorn_ufs_note_trust_cache(unsigned index)
{
	if (index < 32) {
		gTrustCacheMask |= 1U << index;
	}
}

extern "C" void zorn_ufs_log_word(const char *text)
{
	if (!gLogArmed || gLogBusy || !gZornWriteLog || !text || text[0] == '\0') {
		return;
	}
	if (gCompactTrace && strcmp(text, gRecoveryCheckpoint) != 0) {
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
	gLogBusy = 1;
	zorn_log_append(text);
	gLogBusy = 0;
	if (gReturnAfterTent && strcmp(text, gRecoveryCheckpoint) == 0) {
		gCheckpointSeen++;
		if (gCheckpointSkip != 0) {
			gCheckpointSkip--;
			return;
		}
		gReturnAfterTent = 0;
		zorn_checkpoint_reset();
	}
}

extern "C" int zorn_ufs_trace_only(const char *text)
{
	if (!gLogArmed || !gLogOnly) {
		return 0;
	}
	zorn_ufs_log_word(text);
	return 1;
}

static void zorn_trace_time(void)
{
	if (!gLogArmed || gLogBusy) {
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
	zorn_trace_time();
	char word[12];
	snprintf(word, sizeof(word), "CPH%08X", static_cast<uint32_t>(address >> 32));
	zorn_ufs_log_word(word);
	snprintf(word, sizeof(word), "CPL%08X", static_cast<uint32_t>(address));
	zorn_ufs_log_word(word);
}

extern "C" void zorn_ufs_copy_stage(const char *stage, uint64_t owner)
{
	if (!gLogArmed || gLogBusy || owner != gCopyTraceOwner || gCopyTraceCount++ >= 48) return;
	zorn_trace_time();
	zorn_ufs_log_word(stage);
}

extern "C" void zorn_ufs_copy_abort(uint64_t owner, uint64_t pc, uint64_t far,
    uint32_t esr, int recovery)
{
	if (!gLogArmed || gLogBusy || owner != gCopyTraceOwner || gCopyTraceCount++ >= 48) return;
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
	if (!gLogArmed || gLogBusy || count++ >= 256) {
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
	if (!gLogArmed || gLogBusy || !gZornWriteLog || !text || !length) return;
	zorn_trace_time();
	gLogBusy = 1;
	char word[12];
	snprintf(word, sizeof(word), "UFD%08X", fd);
	zorn_log_put(word);
	zorn_log_put("USRBEGIN");
	if (length > 128) length = 128;
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
	gLogBusy = 0;
	zorn_ufs_log_word("UCON");
}

extern "C" void zorn_ufs_capture_write(uint64_t fd, uint64_t address, uint64_t length)
{
	static unsigned count;
	if (!gLogArmed || gLogBusy || !length || count++ >= 64) return;
	char text[128];
	size_t bytes = length < sizeof(text) ? static_cast<size_t>(length) : sizeof(text);
	if (copyin(address, text, bytes) == 0) {
		zorn_ufs_user_output(static_cast<unsigned>(fd), text, bytes);
	} else {
		char word[12];
		snprintf(word, sizeof(word), "UFD%08X", static_cast<unsigned>(fd));
		zorn_ufs_log_word(word);
		zorn_ufs_log_word("UCOPYERR");
	}
}

extern "C" void zorn_ufs_capture_sysctl(uint64_t address, uint64_t length, uint64_t newLength)
{
	static unsigned count;
	if (!gLogArmed || gLogBusy || count++ >= 32) return;
	uint32_t name[12] = {};
	unsigned entries = length < 12 ? static_cast<unsigned>(length) : 12;
	bool valid = entries && copyin(address, name, entries * sizeof(name[0])) == 0;
	zorn_trace_time();
	gLogBusy = 1;
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
	gLogBusy = 0;
}

extern "C" void zorn_ufs_sysctl_point(const char *name, uint64_t handler, unsigned phase)
{
	static unsigned count;
	if (!gLogArmed || gLogBusy || !name || count++ >= 128) return;
	zorn_trace_time();
	gLogBusy = 1;
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
	gLogBusy = 0;
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

static int zorn_os_read(uint64_t abs, void *dst, size_t bytes)
{
	uint8_t *out = static_cast<uint8_t *>(dst);
	while (bytes) {
		uint32_t skip = static_cast<uint32_t>(abs & 4095U);
		uint32_t room = 4096U - skip;
		uint32_t take = bytes < room ? static_cast<uint32_t>(bytes) : room;
		if (hostRead4k(0, abs / 4096U, 1, gZornOsBounce) != kIOReturnSuccess) {
			return EIO;
		}
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
	static uint8_t disk[4096];
	if (hostRead4k(0, static_cast<uint32_t>(start + window / 4096), 1, disk) != kIOReturnSuccess) {
		zorn_ufs_stop("OSGPT");
	}
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
	if (mdevadd_ops(0, bytes, zorn_os_transfer, nullptr) == static_cast<dev_t>(-1)) {
		zorn_ufs_stop("MDNO");
	}
	zorn_os_root_pending = 1;
	zorn_say("MD0");
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
		if (i == 7 ? (block[i] != '1' && block[i] != '2') :
		    block[i] != static_cast<uint8_t>(magic[i])) {
			zorn_say("NOLOG");
			return false;
		}
	}
	uint32_t count = block[8] | (uint32_t(block[9]) << 8) |
	    (uint32_t(block[10]) << 16) | (uint32_t(block[11]) << 24);
	bool v2 = block[7] == '2';
	uint32_t capacity = v2 ? 340 : 510;
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
	int compact = 0;
	PE_parse_boot_argn("zorn_trace_compact", &compact, sizeof(compact));
	gCompactTrace = compact == 1;
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
	gZornWriteLog = hostWriteLog4k;
	for (unsigned i = 0; i < sizeof(gLogBlock); i++) {
		reinterpret_cast<uint8_t *>(&gLogBlock)[i] = 0;
	}
	static const char magic[] = { 'Z', 'O', 'R', 'N', 'L', 'O', 'G', '2' };
	for (unsigned i = 0; i < 8; i++) {
		gLogBlock.magic[i] = magic[i];
	}
	zorn_say("WRGO");
	gLogEnabled = true;
	gTraceEpoch = mach_absolute_time();
	gLogArmed = true;
	if (hostWriteLog4k(&gLogBlock) != kIOReturnSuccess) {
		gLogArmed = false;
		gLogEnabled = false;
		zorn_say("WRNO");
		return;
	}
	static uint8_t check[4096];
	if (hostRead4k(0, gLogLba, 1, check) != kIOReturnSuccess ||
	    memcmp(check, &gLogBlock, sizeof(gLogBlock)) != 0) {
		gLogArmed = false;
		gLogEnabled = false;
		zorn_say("WRNO");
		return;
	}
	zorn_say("WROK");
	char trustStatus[12];
	snprintf(trustStatus, sizeof(trustStatus), "TC%08X", gTrustCacheMask);
	zorn_ufs_log_word(trustStatus);
	if (gWatchdogMode == 1 || gWatchdogMode == 2) {
		zorn_watchdog_start();
	}
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

static void zorn_checkpoint_reset(void)
{
	gLogBusy = 1;
	if (gWatchdogArmed) {
		ZornSmcResult stopped = zorn_wdt_call(0x86000005U, 2, 0);
		zorn_log_append(stopped.status == 0 ? "WSTOP" : "WSTERR");
		gWatchdogArmed = false;
	}
	zorn_log_append("RSET");
	char trustStatus[12];
	snprintf(trustStatus, sizeof(trustStatus), "TC%08X", gTrustCacheMask);
	zorn_log_append(trustStatus);
	snprintf(trustStatus, sizeof(trustStatus), "HIT%08X", gCheckpointSeen);
	zorn_log_append(trustStatus);
	bool wrote = zorn_set_recovery_bcb();
	zorn_log_append(wrote ? "BCBK" : "BCBN");
	if (wrote) {
		zorn_psci_reset();
		zorn_log_append("PSRT");
	}
	gLogBusy = 0;
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
		zorn_ufs_publish_os(start, page);
		zorn_ufs_arm_log(start, end);
		return;
	}
	zorn_ufs_stop("NOSHNG");
}
}

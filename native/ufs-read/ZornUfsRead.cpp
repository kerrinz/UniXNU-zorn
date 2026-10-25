// Read-only UFS probe for zorn. Same pineapple host and stream as houji's
// GPT reader: ufshc@1d84000, apps_smmu stream 0x60. NOP, power query, wake,
// TEST UNIT READY, then READ of the primary GPT. No WRITE, no log commit.
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
	const uint8_t *userdata = nullptr;
	for (uint32_t index = 0; index < count; index++) {
		const uint8_t *entry = entries + index * size;
		static const char name[] = "userdata";
		bool match = true;
		for (unsigned i = 0; name[i]; i++) {
			if (entry[56 + i * 2] != static_cast<uint8_t>(name[i]) || entry[57 + i * 2] != 0) {
				match = false;
				break;
			}
		}
		if (match && entry[56 + 16] == 0 && entry[57 + 16] == 0) {
			userdata = entry;
			break;
		}
	}
	if (!userdata) {
		zorn_ufs_stop("UNAME");
	}
	uint64_t start = houjiLe64(userdata + 32);
	if (start == 0 || start > 0xffffffffULL) {
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
		return;
	}
	zorn_ufs_stop("NOSHNG");
}
}

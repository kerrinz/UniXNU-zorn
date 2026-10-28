// SPDX-License-Identifier: BSD-2-Clause-Patent
// Included after the existing root command implementation. No independent DMA
// queue or controller ownership; all traffic uses gHost.lock and its poison rule.
static IOReturn zornDataWrite(uint64_t rel, uint32_t blocks, const void *src)
{
    if (!gZornDataOpened || gZornDataMode != 2 || !gHost.ready || gHost.poisoned ||
        !src || !zornDataRange(rel, blocks)) return kIOReturnNotPermitted;
    uint32_t lba = static_cast<uint32_t>(kZornDataFirst + rel);
    IOLockLock(gHost.lock);
    IOReturn result = kIOReturnNotReady;
    // Do not touch the shared DMA allocation after a previous poisoned command.
    if (gHost.ready && !gHost.poisoned) {
        memcpy(gHost.virt + kDataOffset, src, blocks * 4096U);
        uint8_t cdb[10] = {0x2a, 8, uint8_t(lba >> 24), uint8_t(lba >> 16), uint8_t(lba >> 8),
                          uint8_t(lba), 0, uint8_t(blocks >> 8), uint8_t(blocks), 0};
        uint32_t scsi = 0;
        result = hostScsiDir(0, cdb, 10, 1, blocks * 4096U, 2000000, &scsi);
    }
    IOLockUnlock(gHost.lock);
    return result;
}

#if defined(ZORN_RAM_DATA) && ZORN_RAM_DATA
extern "C" {
extern const uint8_t zorn_data_expected_seed[32];
}
static uint32_t gZornDataHeaderCrc, gZornDataEntriesCrc, gZornDataEntryBytes;
static uint64_t gZornDataBackupLba;
static uint8_t gZornDataDiskGuid[16];
static bool gZornDataGeometryReady;

extern "C" unsigned zorn_data_store_mode(void)
{
    if (!gZornDataGeometryReady) return 0;
    return gZornDataMode;
}

static uint8_t gZornDataGptBuffer[4096 + 32768];
static int gZornDataGptBusy;
static unsigned zorn_data_store_gpt_check_inner(void)
{
    if (!gZornDataGeometryReady || !gHost.ready || gHost.poisoned) return 1;
    uint8_t *header = gZornDataGptBuffer, *entries = gZornDataGptBuffer + 4096;
    if (hostRead4k(0, 1, 1, header) != kIOReturnSuccess ||
        houjiLe32(header + 16) != gZornDataHeaderCrc || houjiCrc32(header, 92, true) != gZornDataHeaderCrc ||
        memcmp(header + 56, gZornDataDiskGuid, 16) || houjiLe64(header + 32) != gZornDataBackupLba ||
        houjiLe64(header + 72) != 2 || houjiLe32(header + 84) != 128 ||
        houjiLe32(header + 80) * 128ULL != gZornDataEntryBytes) return 2;
    uint32_t blocks = gZornDataEntryBytes / 4096;
    if (!blocks || blocks > 8 || hostRead4k(0, 2, blocks, entries) != kIOReturnSuccess ||
        houjiCrc32(entries, gZornDataEntryBytes) != gZornDataEntriesCrc) return 3;
    if (hostRead4k(0, gZornDataBackupLba, 1, header) != kIOReturnSuccess ||
        houjiLe64(header + 24) != gZornDataBackupLba || houjiLe64(header + 32) != 1 ||
        memcmp(header + 56, gZornDataDiskGuid, 16) || houjiLe32(header + 84) != 128 ||
        houjiLe32(header + 80) * 128ULL != gZornDataEntryBytes ||
        houjiCrc32(header, 92, true) != houjiLe32(header + 16) ||
        houjiLe32(header + 88) != gZornDataEntriesCrc) return 4;
    uint64_t at = houjiLe64(header + 72);
    if (at < 2 || at >= gZornDataBackupLba || blocks > gZornDataBackupLba - at ||
        hostRead4k(0, at, blocks, entries) != kIOReturnSuccess ||
        houjiCrc32(entries, gZornDataEntryBytes) != gZornDataEntriesCrc) return 5;
    return 0;
}
extern "C" unsigned zorn_data_store_gpt_check(void)
{
    if (!__sync_bool_compare_and_swap(&gZornDataGptBusy, 0, 1)) return 6;
    unsigned result = zorn_data_store_gpt_check_inner();
    __sync_lock_release(&gZornDataGptBusy);
    return result;
}

extern "C" int zorn_data_store_open(uint64_t blocks, uint64_t *first, const char **why)
{
    if (first) *first = 0;
    const char *reason = "off or unverified geometry";
    bool ok = false;
    if (gZornDataMode && gZornDataGeometryReady && !gZornDataOpened && blocks == kZornDataWindowBlocks &&
        zorn_data_store_gpt_check() == 0) {
        uint8_t header[4096];
        reason = "overlay header absent/damaged/wrong seed; explicit host preparation required";
        if (hostRead4k(0, kZornDataFirst, 1, header) == kIOReturnSuccess &&
            !memcmp(header, "SHNGDATA", 8) && houjiLe32(header + 8) == 1 &&
            houjiLe32(header + 12) == 64 && houjiLe64(header + 16) == kZornDataPages &&
            !memcmp(header + 24, zorn_data_expected_seed, 32) && houjiLe32(header + 56) &&
            houjiCrc32(header, 60) == houjiLe32(header + 60)) {
            gZornDataOpened = true;
            if (first) *first = kZornDataFirst;
            reason = "verified exact reserved Data overlay"; ok = true;
        }
    }
    if (why) *why = reason;
    return ok;
}

extern "C" int zorn_data_store_read(uint64_t rel, uint32_t blocks, void *dst)
{
    if (!gZornDataOpened || !dst || !blocks || rel >= kZornDataWindowBlocks ||
        blocks > kZornDataWindowBlocks - rel) return 0;
    while (blocks) {
        uint32_t n = blocks > 32 ? 32 : blocks;
        if (hostRead4k(0, kZornDataFirst + rel, n, dst) != kIOReturnSuccess) return 0;
        rel += n; blocks -= n; dst = static_cast<uint8_t *>(dst) + n * 4096ULL;
    }
    return 1;
}
extern "C" int zorn_data_store_write(uint64_t rel, uint32_t blocks, const void *src)
{
    if (!gZornDataOpened || gZornDataMode != 2 || !src || !blocks || rel >= kZornDataWindowBlocks ||
        blocks > kZornDataWindowBlocks - rel) return 0;
    while (blocks) {
        uint32_t n = blocks > 32 ? 32 : blocks;
        if (zornDataWrite(rel, n, src) != kIOReturnSuccess) return 0;
        rel += n; blocks -= n; src = static_cast<const uint8_t *>(src) + n * 4096ULL;
    }
    return 1;
}
extern "C" int zorn_data_store_sync(void)
{
    if (!gZornDataOpened || gZornDataMode != 2 || !gHost.ready || gHost.poisoned) return 0;
    IOLockLock(gHost.lock);
    uint8_t cdb[10] = {0x35}; uint32_t scsi = 0;
    IOReturn result = hostScsiDir(0, cdb, 10, 0, 0, 2000000, &scsi);
    IOLockUnlock(gHost.lock);
    return result == kIOReturnSuccess;
}
#endif

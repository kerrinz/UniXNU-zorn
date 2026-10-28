// SPDX-License-Identifier: BSD-2-Clause-Patent
// Real readonly IOBlockStorageDevice over the existing verified UFS window.
// Original IOStorageFamily/APFS publish the media, UUID and BSD device nodes.
#include "ZornVerifiedRoot.h"
#include <IOKit/IOService.h>
#include <IOKit/IOBSD.h>
#include <IOKit/IOLib.h>
#include <IOKit/storage/IOBlockStorageDevice.h>
#include <libkern/c++/OSNumber.h>
#include <libkern/c++/OSString.h>
#include <libkern/c++/OSIterator.h>
#include <mach/kmod.h>
#include <sys/errno.h>
#include <sys/param.h>

extern "C" {
extern kmod_info_t g_kernel_kmod_info;
kern_return_t OSKextLoadKextWithIdentifier(const char *);
void zorn_storage_static_init(void) __asm__("__GLOBAL__sub_I_ZornUfsBlock.cpp");
int zorn_systemos_transfer(void *, uint64_t, void *, size_t, int);
void zorn_say(const char *);
volatile unsigned zorn_storage_stage;
volatile uint64_t zorn_storage_reads, zorn_storage_failures;
}

class ZornUfsBlock : public IOBlockStorageDevice {
    OSDeclareDefaultStructors(ZornUfsBlock)
    uint64_t bytes = 0;
    uint8_t *bounce = nullptr;
    IOLock *lock = nullptr;
    bool online = false;
public:
    bool configure() {
        bytes = zorn_ufs_window_bytes(1);
        if (!zorn_verified_window_ready(1) || bytes != 3303014400ULL) return false;
        lock = IOLockAlloc();
        bounce = static_cast<uint8_t *>(IOMalloc(4096));
        return lock && bounce;
    }
    bool start(IOService *provider) override {
        if (!bytes || !lock || !bounce || !IOBlockStorageDevice::start(provider)) return false;
        online = true;
        return true;
    }
    void free() override {
        if (bounce) { IOFree(bounce, 4096); bounce = nullptr; }
        if (lock) { IOLockFree(lock); lock = nullptr; }
        IOBlockStorageDevice::free();
    }
    IOReturn doEjectMedia() override { return kIOReturnUnsupported; }
    IOReturn doFormatMedia(UInt64) override { return kIOReturnNotWritable; }
    UInt32 doGetFormatCapacities(UInt64 *, UInt32) const override { return 0; }
    char *getVendorString() override { return const_cast<char *>("Zorn"); }
    char *getProductString() override { return const_cast<char *>("Verified UFS SystemOS"); }
    char *getRevisionString() override { return const_cast<char *>("1.0"); }
    char *getAdditionalDeviceInfoString() override {
        return const_cast<char *>("Readonly authenticated userdata window on SM8650 UFS");
    }
    IOReturn reportBlockSize(UInt64 *value) override { *value = 512; return kIOReturnSuccess; }
    IOReturn reportEjectability(bool *value) override { *value = false; return kIOReturnSuccess; }
    IOReturn reportMaxValidBlock(UInt64 *value) override { *value = bytes / 512 - 1; return kIOReturnSuccess; }
    IOReturn reportMediaState(bool *present, bool *changed) override {
        *present = online && zorn_verified_window_ready(1);
        if (changed) *changed = false;
        return kIOReturnSuccess;
    }
    IOReturn reportRemovability(bool *value) override { *value = false; return kIOReturnSuccess; }
    IOReturn reportWriteProtection(bool *value) override { *value = true; return kIOReturnSuccess; }
    IOReturn doSynchronizeCache() override { return online ? kIOReturnSuccess : kIOReturnNotReady; }
    IOReturn doSynchronize(UInt64, UInt64, IOOptionBits) override { return doSynchronizeCache(); }
    IOReturn getWriteCacheState(bool *value) override { *value = false; return kIOReturnSuccess; }
    IOReturn setWriteCacheState(bool) override { return kIOReturnUnsupported; }
    IOReturn doAsyncReadWrite(IOMemoryDescriptor *, UInt64, UInt64,
                            IOStorageAttributes *, IOStorageCompletion *) override;
};
OSDefineMetaClassAndStructors(ZornUfsBlock, IOBlockStorageDevice)
static_assert(sizeof(IOBlockStorageDevice) == 0x90, "Original storage class size");
static_assert(sizeof(IOService) == 0x88, "Source IOService class size");

IOReturn ZornUfsBlock::doAsyncReadWrite(IOMemoryDescriptor *buffer, UInt64 block, UInt64 count,
                                     IOStorageAttributes *, IOStorageCompletion *completion)
{
    if (!buffer || !completion || !completion->action || !count || block >= bytes / 512 ||
        count > bytes / 512 - block || buffer->getLength() < count * 512) return kIOReturnBadArgument;
    if (buffer->getDirection() != kIODirectionIn) return kIOReturnNotWritable;
    if (!online || !zorn_verified_window_ready(1)) return kIOReturnNotReady;
    uint64_t done = 0, length = count * 512;
    IOReturn status = kIOReturnSuccess;
    IOLockLock(lock);
    while (done < length) {
        size_t chunk = static_cast<size_t>(length - done > 4096 ? 4096 : length - done);
        int error = zorn_systemos_transfer(nullptr, block * 512 + done, bounce, chunk, 0);
        if (error) {
            status = error == EAUTH ? kIOReturnNotPrivileged : kIOReturnIOError;
            break;
        }
        if (buffer->writeBytes(done, bounce, chunk) != chunk) { status = kIOReturnIOError; break; }
        done += chunk;
        __atomic_fetch_add(&zorn_storage_reads, 1, __ATOMIC_RELAXED);
    }
    IOLockUnlock(lock);
    if (status != kIOReturnSuccess) __atomic_fetch_add(&zorn_storage_failures, 1, __ATOMIC_RELAXED);
    completion->action(completion->target, completion->parameter, status, done);
    return kIOReturnSuccess;
}

static ZornUfsBlock *gBlock;
static bool gAttempted;

static bool publish()
{
    if (gBlock) return zorn_verified_window_ready(1);
    if (gAttempted || !zorn_verified_window_ready(1)) return false;
    gAttempted = true;
    zorn_storage_stage = 1; zorn_say("SBLOAD");
    if (OSKextLoadKextWithIdentifier("com.apple.iokit.IOStorageFamily")) return false;
    const OSMetaClass *parent = &IOBlockStorageDevice::gMetaClass;
    if (parent->getClassSize() != 0x90 || parent->getSuperClass() != &IOService::gMetaClass ||
        IOService::gMetaClass.getClassSize() != 0x88) { zorn_say("SBABI"); return false; }
    zorn_storage_stage = 2; zorn_say("SBMETA");
    void *handle = OSMetaClass::preModLoad(g_kernel_kmod_info.name);
    if (!handle) return false;
    zorn_storage_static_init();
    if (OSMetaClass::postModLoad(handle)) return false;
    zorn_storage_stage = 3; zorn_say("SBREG");
    IOService *provider = IOService::getResourceService();
    ZornUfsBlock *block = new ZornUfsBlock;
    if (!provider || !block) { OSSafeReleaseNULL(block); return false; }
    if (!block->init(nullptr) || !block->configure()) { block->release(); return false; }
    block->setName("ZornUfsSystemOS");
    // These describe this real provider. UUID/roles/BSD identity are never set here.
    block->setProperty("ZornUfsControllerBase", 0x1d84000ULL, 64);
    block->setProperty("ZornUfsStreamID", 0x60ULL, 32);
    block->setProperty("ZornUfsWindowBytes", zorn_ufs_window_bytes(1), 64);
    if (!block->attach(provider)) { block->release(); return false; }
    zorn_storage_stage = 4; zorn_say("SBATT");
    if (!block->start(provider)) { block->detach(provider); block->release(); return false; }
    gBlock = block;
    zorn_storage_stage = 5; zorn_say("SBSTART");
    block->registerService(kIOServiceSynchronous);
    zorn_storage_stage = 6; zorn_say("SBPUB");
    return true;
}

static bool ourMedia(IORegistryEntry *media)
{
    IORegistryIterator *parents = IORegistryIterator::iterateOver(
        media, gIOServicePlane, kIORegistryIterateRecursively | kIORegistryIterateParents);
    if (!parents) return false;
    bool found = false;
    for (unsigned depth = 0; depth < 128; ++depth) {
        IORegistryEntry *entry = parents->getNextObject();
        if (!entry) break;
        if (entry == gBlock) { found = true; break; }
    }
    parents->release();
    return found;
}

static bool find(const char *uuid, dev_t *device, char *path, size_t capacity)
{
    if (!gBlock || !zorn_verified_window_ready(1) || !uuid || strlen(uuid) != 36) return false;
    OSDictionary *matching = IOService::serviceMatching("IOMedia");
    OSDictionary *properties = OSDictionary::withCapacity(1);
    OSString *wanted = OSString::withCString(uuid);
    OSIterator *iterator = nullptr;
    unsigned matches = 0;
    dev_t selected = NODEV;
    char bsdPath[64] = {};
    if (matching && properties && wanted && properties->setObject("UUID", wanted) &&
        matching->setObject("IOPropertyMatch", properties)) iterator = IOService::getMatchingServices(matching);
    if (iterator) {
        for (unsigned count = 0; count < 64; ++count) {
            IORegistryEntry *media = OSDynamicCast(IORegistryEntry, iterator->getNextObject());
            if (!media) break;
            if (!ourMedia(media)) continue;
            OSNumber *major = OSDynamicCast(OSNumber, media->getProperty(kIOBSDMajorKey));
            OSNumber *minor = OSDynamicCast(OSNumber, media->getProperty(kIOBSDMinorKey));
            OSString *name = OSDynamicCast(OSString, media->getProperty(kIOBSDNameKey));
            if (!major || !minor || !name || !name->getLength() || name->getLength() > 50) continue;
            if (major->unsigned64BitValue() > 255 || minor->unsigned64BitValue() > 0xffffff) continue;
            ++matches;
            selected = static_cast<dev_t>((major->unsigned32BitValue() << 24) | minor->unsigned32BitValue());
            snprintf(bsdPath, sizeof(bsdPath), "/dev/%s", name->getCStringNoCopy());
        }
    }
    OSSafeReleaseNULL(iterator); OSSafeReleaseNULL(wanted);
    OSSafeReleaseNULL(properties); OSSafeReleaseNULL(matching);
    if (matches != 1 || selected == NODEV || !zorn_verified_window_ready(1)) return false;
    if (device) *device = selected;
    if (path) {
        if (strlen(bsdPath) + 1 > capacity) return false;
        strlcpy(path, bsdPath, capacity);
    }
    return true;
}

extern "C" int zorn_systemos_iokit_device(const char *uuid, dev_t *device, char *path, size_t capacity)
{
    if (!device || !path || !publish()) return 0;
    for (unsigned attempt = 0; attempt < 100; ++attempt) {
        if (find(uuid, device, path, capacity)) {
            zorn_storage_stage = 7; zorn_say("SBMEDIA");
            return 1;
        }
        IOSleep(20);
    }
    zorn_say("SBNOFS");
    return 0;
}

extern "C" int zorn_systemos_iokit_matches(dev_t device, const char *uuid)
{
    dev_t observed = NODEV;
    return find(uuid, &observed, nullptr, 0) && observed == device;
}

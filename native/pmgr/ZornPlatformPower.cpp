// SPDX-License-Identifier: MIT
// Adapted from UniXNU-sheng 0e1f6e52638137db15905db8d775ad73757f39fa
// package/ShengPlatformPower.cpp. Board-side original PMGR ABI qualification. Default off. Modes: 1 releases
// unpublished objects, 2 publishes the original nub, 3 tests power refusal.
// No clocks, sleep, reset or secondary-CPU success is advertised.
#include "OriginalPMGRABI.h"
#include <IOKit/IOLib.h>
#include <IOKit/IOPlatformExpert.h>
#include <libkern/c++/OSSymbol.h>
#include <mach/kmod.h>
#include <pexpert/pexpert.h>

extern "C" {
extern kmod_info_t g_kernel_kmod_info;
kern_return_t OSKextLoadKextWithIdentifier(const char *);
void zorn_pmgr_static_init(void) __asm__("__GLOBAL__sub_I_ZornPlatformPower.cpp");
IOService *zorn_original_pmgr_nub_create(IORegistryEntry *, ApplePMGR *);
uint32_t zorn_original_pmgr_nub_read(IOService *);
void zorn_original_pmgr_nub_write(IOService *, uint64_t);
// stage,status,parent-size,own-size,provider,nub,bound-provider,read-before,
// read-after,own-before,own-after,nub-before,nub-after,attached,registered,mode.
volatile uint64_t zorn_pmgr_observation[16];
void zorn_say(const char *);
__attribute__((noinline)) void zorn_pmgr_checkpoint(void)
{
  char word[12];
  snprintf(word, sizeof(word), "PMS%08X", (unsigned)zorn_pmgr_observation[0]);
  zorn_say(word);
  snprintf(word, sizeof(word), "PME%08X", (unsigned)zorn_pmgr_observation[1]);
  zorn_say(word);
  if (!zorn_pmgr_observation[1]) {
    snprintf(word, sizeof(word), "PMR%08X", (unsigned)zorn_pmgr_observation[8]);
    zorn_say(word);
    zorn_say(zorn_pmgr_observation[0] == 5 ? "PMOK2" : "PMOK1");
  }
}
}

__attribute__((noreturn)) static void unavailable(unsigned slot)
{
  zorn_pmgr_observation[0] = 0x100 + slot;
  zorn_pmgr_observation[1] = static_cast<uint32_t>(kIOReturnUnsupported);
  zorn_pmgr_checkpoint();
  panic("ZornPlatformPower: unimplemented operation %u", slot);
}

class ZornPlatformPower : public ApplePMGR {
  OSDeclareDefaultStructors(ZornPlatformPower)
public:
  void enableCPUCore(unsigned, uint64_t) override { unavailable(168); }
  void enableCPUCore(unsigned) override { unavailable(169); }
  void disableCPUCore(unsigned) override { unavailable(170); }
  void enableCPUCluster(unsigned) override { unavailable(171); }
  void disableCPUCluster(unsigned) override { unavailable(172); }
  void initCPUIdle(ml_processor_info_t *) override { unavailable(173); }
  void enterCPUIdle(UInt64 *) override { unavailable(174); }
  void exitCPUIdle(UInt64 *) override { unavailable(175); }
  void updateCPUIdle(UInt64 *) override { unavailable(176); }
#include "GuardedPMGRSlots.inc"
};
OSDefineMetaClassWithInit(ZornPlatformPower, ApplePMGR, )
OSMetaClassConstructorInit(ZornPlatformPower, ApplePMGR, )
OSDefineBasicStructors(ZornPlatformPower, ApplePMGR)
// The original object's storage exceeds kalloc_type's 16 KiB size limit.
// Use XNU's existing zeroed, size-aware OSObject heap allocation pair.
void *ZornPlatformPower::operator new(size_t size) { return OSObject::operator new(size); }
void ZornPlatformPower::operator delete(void *memory, size_t size)
{
  OSObject::operator delete(memory, size);
}
static_assert(sizeof(ZornPlatformPower) == 0x4b8a8, "Exact original provider storage");

static const OSMetaClass *lookup(const char *text)
{
  const OSSymbol *name = OSSymbol::withCString(text);
  const OSMetaClass *meta = name ? OSMetaClass::getMetaClassWithName(name) : nullptr;
  OSSafeReleaseNULL(name);
  return meta;
}

extern "C" void zorn_pmgr_run(void)
{
  unsigned mode = 0;
  if (!PE_parse_boot_argn("zorn_pmgr", &mode, sizeof(mode)) || !mode) return;
  zorn_pmgr_observation[15] = mode;
  zorn_pmgr_observation[1] = static_cast<uint32_t>(kIOReturnError);
  if (mode > 3 || zorn_pmgr_observation[0]) { zorn_pmgr_checkpoint(); return; }
  zorn_pmgr_observation[0] = 1;
  zorn_say("PMLOAD");
  kern_return_t result = OSKextLoadKextWithIdentifier("com.apple.driver.ApplePMGR");
  if (result) { zorn_pmgr_observation[1] = static_cast<uint32_t>(result); zorn_pmgr_checkpoint(); return; }
  zorn_say("PMMETA");
  const OSMetaClass *parent = lookup("ApplePMGR"), *nubMeta = lookup("ApplePMGRNub");
  if (!parent || parent != &ApplePMGR::gMetaClass || parent->getClassSize() != 0x4b8a8 ||
      !nubMeta || nubMeta->getClassSize() != 0x740) { zorn_pmgr_checkpoint(); return; }
  zorn_pmgr_observation[2] = parent->getClassSize();
  zorn_say("PMREG");
  void *handle = OSMetaClass::preModLoad(g_kernel_kmod_info.name);
  if (!handle) { zorn_pmgr_checkpoint(); return; }
  zorn_pmgr_static_init();
  result = OSMetaClass::postModLoad(handle);
  if (result) { zorn_pmgr_observation[1] = static_cast<uint32_t>(result); zorn_pmgr_checkpoint(); return; }
  zorn_pmgr_observation[9] = ZornPlatformPower::gMetaClass.getInstanceCount();
  zorn_pmgr_observation[11] = nubMeta->getInstanceCount();
  zorn_say("PMNEW");
  ZornPlatformPower *provider = new ZornPlatformPower;
  IORegistryEntry *description = new IORegistryEntry;
  IOService *nub = nullptr;
  do {
    if (!provider || !description || !provider->init() || !description->init()) break;
    zorn_pmgr_observation[0] = 2;
    zorn_pmgr_observation[3] = provider->getMetaClass()->getClassSize();
    zorn_pmgr_observation[4] = reinterpret_cast<uintptr_t>(provider);
    // Empty resource description: no Apple register map or device capabilities.
    description->setName("zorn-platform-power");
    zorn_say("PMNUB");
    nub = zorn_original_pmgr_nub_create(description, provider);
    zorn_pmgr_observation[5] = reinterpret_cast<uintptr_t>(nub);
    if (!nub || nub->getMetaClass() != nubMeta || !provider->metaCast("ApplePMGR")) break;
    uintptr_t bound = 0;
    memcpy(&bound, reinterpret_cast<const char *>(nub) + 0x88, sizeof(bound));
    zorn_pmgr_observation[6] = bound;
    if (bound != reinterpret_cast<uintptr_t>(provider)) break;
    zorn_pmgr_observation[0] = 3;
    zorn_say("PMREAD");
    uint32_t value = zorn_original_pmgr_nub_read(nub);
    zorn_pmgr_observation[7] = value;
    zorn_original_pmgr_nub_write(nub, uint64_t(value | 4));
    zorn_pmgr_observation[8] = zorn_original_pmgr_nub_read(nub);
    zorn_pmgr_observation[13] = nub->getProvider() != nullptr || provider->getProvider() != nullptr;
    zorn_pmgr_observation[14] = (nub->getState() | provider->getState()) & kIOServiceRegisteredState;
    if (value != 0xffffffff || zorn_pmgr_observation[8] != 0xffffffff ||
        zorn_pmgr_observation[13] || zorn_pmgr_observation[14]) break;
    if (mode == 3) provider->disableCPUCore(1);
    if (mode == 2) {
      zorn_say("PMATT");
      IOService *platform = IOService::getPlatform();
      if (!platform || !provider->attach(platform)) break;
      if (!provider->start(platform)) { provider->detach(platform); break; }
      if (!nub->attach(provider)) {
        provider->stop(platform); provider->detach(platform); break;
      }
      if (!nub->start(provider)) {
        nub->detach(provider); provider->stop(platform); provider->detach(platform); break;
      }
      zorn_say("PMPUB");
      provider->registerService(kIOServiceSynchronous);
      nub->registerService(kIOServiceSynchronous);
      zorn_pmgr_observation[0] = 5;
      zorn_pmgr_observation[13] = nub->getProvider() == provider && provider->getProvider() == platform;
      zorn_pmgr_observation[14] = (nub->getState() & provider->getState()) & kIOServiceRegisteredState;
      zorn_say("PMMATCH");
      auto matching = IOService::serviceMatching("ApplePMGRNub");
      IOService *matched = matching ? IOService::waitForMatchingService(matching, 1000000) : nullptr;
      OSSafeReleaseNULL(matching);
      // Check actual service discovery and genuine type identity, then retain
      // both live objects. The registry and original nub refer to this provider.
      if (matched != nub || matched->getMetaClass() != nubMeta ||
          !zorn_pmgr_observation[13] || !zorn_pmgr_observation[14]) {
        zorn_pmgr_checkpoint();
        panic("ZornPlatformPower: original nub publication failed");
      }
      zorn_pmgr_observation[10] = ZornPlatformPower::gMetaClass.getInstanceCount();
      zorn_pmgr_observation[12] = nubMeta->getInstanceCount();
      zorn_pmgr_observation[1] = kIOReturnSuccess;
      OSSafeReleaseNULL(matched);
      OSSafeReleaseNULL(description);
      zorn_pmgr_checkpoint();
      return;
    }
    zorn_pmgr_observation[1] = kIOReturnSuccess;
  } while (false);
  OSSafeReleaseNULL(nub);
  OSSafeReleaseNULL(description);
  OSSafeReleaseNULL(provider);
  zorn_pmgr_observation[10] = ZornPlatformPower::gMetaClass.getInstanceCount();
  zorn_pmgr_observation[12] = nubMeta->getInstanceCount();
  if (zorn_pmgr_observation[9] != zorn_pmgr_observation[10] ||
      zorn_pmgr_observation[11] != zorn_pmgr_observation[12]) zorn_pmgr_observation[1] = static_cast<uint32_t>(kIOReturnError);
  zorn_pmgr_observation[0] = 4;
  zorn_pmgr_checkpoint();
}

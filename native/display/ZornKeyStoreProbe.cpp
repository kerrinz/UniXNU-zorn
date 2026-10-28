// SPDX-License-Identifier: BSD-2-Clause-Patent
// Board lifecycle for upstream AppleKeyStoreState on volatile, unprotected Data.
// No keys, passcodes, persistent keybags or SEP operations are supplied.
#include <IOKit/IOService.h>
#include <IOKit/IODeviceTreeSupport.h>
#include <libkern/c++/OSData.h>
#include <libkern/c++/OSSymbol.h>
#include <pexpert/pexpert.h>
#include <mach/kmod.h>

extern kmod_info_t g_kernel_kmod_info;
extern "C" {
void zorn_say(const char *);
void native_keyevents_static_init(void) __asm__("__GLOBAL__sub_I_NativeKeyStoreEvents.cpp");
IOService *native_keyevents_allocate(void);
volatile uint32_t zorn_aks_stage, zorn_aks_opens, zorn_aks_calls, zorn_aks_refused;
volatile uint32_t zorn_aks_last_selector;
volatile int32_t zorn_aks_status;
volatile int32_t zorn_aks_last_result;
}
static bool enabled, attempted;
static void report(const char *tag, uint32_t value) {
    char text[16];
    snprintf(text, sizeof(text), "%s%08X", tag, value);
    zorn_say(text);
}
extern "C" bool native_aks_state_enabled(void) { return enabled; }
extern "C" uint32_t native_aks_lock_state(void) { return 0; }
extern "C" void native_keyevents_open_refused(void) {
    __atomic_add_fetch(&zorn_aks_refused, 1, __ATOMIC_RELAXED);
}
extern "C" void native_aks_opened(void) {
    uint32_t count=__atomic_add_fetch(&zorn_aks_opens, 1, __ATOMIC_RELAXED);
    if(count<=4)report("AKO", count);
}
extern "C" void native_aks_call(uint32_t selector, int32_t result) {
    zorn_aks_last_selector=selector;zorn_aks_last_result=result;
    uint32_t count=__atomic_add_fetch(&zorn_aks_calls, 1, __ATOMIC_RELAXED);
    // Bounded diagnostics only; preserve the upstream answer unchanged.
    if(count<=16) {report("AKC",selector);report("AKE",(uint32_t)result);}
}
extern "C" void zorn_keystore_state_probe(void) {
    unsigned requested=0, state=0, original=0;
    if(attempted || !PE_parse_boot_argn("offline-key-events",&requested,sizeof(requested)) || requested!=1)return;
    attempted=true;zorn_aks_stage=1;zorn_aks_status=kIOReturnNotPermitted;
    PE_parse_boot_argn("sheng-aks",&state,sizeof(state));
    PE_parse_boot_argn("offline-keystore",&original,sizeof(original));
    IORegistryEntry *chosen=IORegistryEntry::fromPath("/chosen",gIODTPlane);
    OSData *property=chosen?OSDynamicCast(OSData,chosen->getProperty("ephemeral-storage")):nullptr;
    uint32_t ephemeral=0;
    if(property && property->getLength()==sizeof(ephemeral))memcpy(&ephemeral,property->getBytesNoCopy(),sizeof(ephemeral));
    OSSafeReleaseNULL(chosen);
    if(ephemeral!=1 || state!=1 || original) {report("AKR",(uint32_t)zorn_aks_status);return;}
    const OSSymbol *name=OSSymbol::withCString("AppleKeyStore");
    bool absent=name && !OSMetaClass::getMetaClassWithName(name);
    OSSafeReleaseNULL(name);
    IOService *provider=IOService::getResourceService();
    if(!absent || !provider) {report("AKR",(uint32_t)zorn_aks_status);return;}
    void *handle=OSMetaClass::preModLoad(g_kernel_kmod_info.name);
    if(!handle)return;
    native_keyevents_static_init();
    zorn_aks_status=OSMetaClass::postModLoad(handle);
    if(zorn_aks_status) {report("AKR",(uint32_t)zorn_aks_status);return;}
    zorn_aks_stage=2;enabled=true;
    IOService *service=native_keyevents_allocate();
    bool initialized=service && service->init();
    bool attached=initialized && service->attach(provider);
    bool started=attached && service->start(provider);
    if(!started) {
        enabled=false;
        if(attached)service->detach(provider);
        OSSafeReleaseNULL(service);
        zorn_aks_status=kIOReturnError;report("AKR",(uint32_t)zorn_aks_status);return;
    }
    // Retain the published service for this boot; the original implementation
    // rejects all unsupported key/data-protection selectors.
    zorn_aks_status=kIOReturnSuccess;zorn_aks_stage=3;zorn_say("AKSOK");
}

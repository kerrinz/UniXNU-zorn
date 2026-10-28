// SPDX-License-Identifier: BSD-2-Clause-Patent
// Load the unchanged OS-profile HID families and observe their real resource.
// No input device, touch report, button event or hardware driver is created.
#include <IOKit/IOService.h>
#include <libkern/c++/OSKext.h>
#include <pexpert/pexpert.h>
extern "C" {
kern_return_t OSKextLoadKextWithIdentifier(const char *);
void zorn_say(const char *);
volatile uint32_t zorn_hid_stage, zorn_hid_resource;
volatile int32_t zorn_hid_family_status=-1, zorn_hid_event_status=-1;
}
static void result(const char *tag,uint32_t value) {
    char text[16];snprintf(text,sizeof(text),"%s%08X",tag,value);zorn_say(text);
}
extern "C" void zorn_hid_services_probe(void) {
    unsigned enabled=0;
    if(zorn_hid_stage || !PE_parse_boot_argn("zorn_hid_family",&enabled,sizeof(enabled)) || enabled!=1)return;
    zorn_hid_stage=1;
    zorn_hid_family_status=OSKextLoadKextWithIdentifier("com.apple.iokit.IOHIDFamily");
    result("HDF",static_cast<uint32_t>(zorn_hid_family_status));
    if(!zorn_hid_family_status) {
        zorn_hid_event_status=OSKext::loadKextWithIdentifier("com.apple.iokit.IOHIDEventDriver",
            true,false,kOSKextExcludeNone,kOSKextExcludeNone,nullptr);
        result("HDE",static_cast<uint32_t>(zorn_hid_event_status));
        zorn_hid_stage=2;
        OSDictionary *match=IOService::serviceMatching("IOHIDResource");
        IOService *resource=match?IOService::waitForMatchingService(match,5000000000ULL):nullptr;
        zorn_hid_resource=resource!=nullptr;
        OSSafeReleaseNULL(resource);OSSafeReleaseNULL(match);
    }
    zorn_hid_stage=3;result("HDR",zorn_hid_resource);
}

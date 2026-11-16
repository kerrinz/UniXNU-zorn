/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#ifndef ZORN_GPU_TABLE_VISIBILITY_H
#define ZORN_GPU_TABLE_VISIBILITY_H
#include "NativeAdrenoMemory.h"
#include "ArmSmmu4KLive.h"
/* Persistent native-kernel context, not an EFI object or a hardware lease.
 * Caller owns a stable native descriptor/table pool and its REAL device ref,
 * and serializes pool/VM/context operations. Both context and memory must
 * outlive every possible returned callback. No close/reset/rebind/release API.
 * Default OFF. Selected target annotation is never a production activation. */
class ZornGpuTableVisibility final {
public:
 enum {Ok,Invalid,Busy,Disabled,Retained};
 enum {NoError,Off,Arguments,Backing,Range,Changed,Reentry,CounterLimit};
 struct Report {
  uint32_t bind_attempted,bound,callback_attempts,native_attempts;
  uint32_t native_status_available,native_status_attempt;
  IOReturn last_native_status,first_native_error;
  uint32_t first_native_error_available,first_adapter_error,failed,runtime_complete;
 };
 ZornGpuTableVisibility()=default;
 ~ZornGpuTableVisibility()=default;
 ZornGpuTableVisibility(const ZornGpuTableVisibility&)=delete;
 ZornGpuTableVisibility& operator=(const ZornGpuTableVisibility&)=delete;
 bool selectedMode() const; /* compiled software configuration only */
 int bind(NativeAdrenoMemory*,ArmSmmu4KLiveVisibility*);
 int snapshot(Report*);
private:
 NativeAdrenoMemory *memory_=nullptr;
 uintptr_t base_=0;size_t bytes_=0;
 Report report_{};
 uint32_t busy_=0,failed_=0,reentry_=0;
 bool enter();void leave();
 bool disjoint(const void*,size_t) const;
 bool stable() const;
 int reject(uint32_t);
 int publish(volatile uint64_t*,size_t);
 static int thunk(void*,volatile uint64_t*,size_t);
 static_assert(__is_same(decltype(&thunk),decltype(ArmSmmu4KLiveVisibility::publish_table_page)),"real callback ABI");
 static_assert(sizeof(IOReturn)==4,"native raw IOReturn width");
};
#endif

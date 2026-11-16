/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#ifndef ZORN_GPU_TABLE_PREPARATION_H
#define ZORN_GPU_TABLE_PREPARATION_H
#include "ZornGpuTableVisibility.h"
#include "NativeAdrenoSmmuMemory.h"
/* Persistent native-only source composition. Caller retains actual inactive
 * table allocation, arena and state under its real exclusive lifetime gate.
 * Geometry is forwarded, never selected or treated as hardware rights. The
 * returned callback references the persistent member, never a stack context. */
class ZornGpuTablePreparation final {
public:
 enum {Ok,Invalid,Busy,Disabled,ModeMismatch,Retained,PrepareFailure,BindFailure,PrepareOutputInvalid};
 struct Geometry {unsigned input_bits,output_bits;uint64_t iova,bytes;unsigned upper;size_t leaf_budget;};
 struct Report {
  uint32_t attempted,publisher_mode_available,publisher_mode_selected;
  uint32_t native_attempted,native_status_available;IOReturn native_return;
  uint32_t bind_attempted,bind_result_available;int32_t bind_result;
  uint32_t adapter_error,retained,callback_exported,runtime_complete;
  uint32_t legacy_callback_observed,legacy_callback_present;
 };
 ZornGpuTablePreparation()=default;
 ~ZornGpuTablePreparation()=default;
 ZornGpuTablePreparation(const ZornGpuTablePreparation&)=delete;
 ZornGpuTablePreparation& operator=(const ZornGpuTablePreparation&)=delete;
 int prepare(NativeAdrenoMemory*,const Geometry*,ArmSmmu4KLiveArena*,ArmSmmu4KLiveState*,ArmSmmu4KLiveVisibility*);
 int snapshot(Report*);
 int snapshotPublisher(ZornGpuTableVisibility::Report*);
private:
 ZornGpuTableVisibility publisher_;
 ArmSmmu4KLiveVisibility legacy_{}; /* Never returned to a caller. */
 Report report_{};uint32_t busy_=0;
 bool enter();void leave();
 bool disjoint(const void*,size_t) const;
 static bool separate(const void*,size_t,const void*,size_t);
 static bool zeroState(const ArmSmmu4KLiveState*);
 void retain(NativeAdrenoMemory*,ArmSmmu4KLiveState*,uint32_t);
};
#endif

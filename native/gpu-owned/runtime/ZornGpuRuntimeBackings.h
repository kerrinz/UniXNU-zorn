/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#ifndef ZORN_GPU_RUNTIME_BACKINGS_H
#define ZORN_GPU_RUNTIME_BACKINGS_H
#include "NativeAdrenoMemory.h"
#include "ZornGpuStartupPlan.h"
static_assert(sizeof(IOReturn)==4,"preserve native IOReturn width");
/* Caller owns persistent storage and valid stable argument objects. These are
 * local reservations, not hardware allocation attempts or ownership tokens.
 * All32 native objects stay private; CPU prepare is default OFF.
 * CPU metadata does not authorize any GPU/GMU mapping or runtime use. */
class ZornGpuRuntimeBackings final {
public:
 enum {Ok,Invalid,Busy,Full,Conflict,Retained,Disabled,NativeFailure,BackingInvalid};
 struct CpuPolicy {uint32_t kind,output_bits,contiguous,reserved;uint64_t per_allocation_budget,total_budget;};
 struct CpuReport {uint32_t attempted,native_status_available;IOReturn native_status;uint32_t backed,cpu_prepared,quarantined,cleanup_status_available;};
 static int checkCpuPolicy(const ZGMemRequirement*,const CpuPolicy*);
 int prepareCpu(uint32_t,const CpuPolicy*);
 int copyCpuReport(uint32_t,CpuReport*);
 struct Summary {
  uint32_t entries,reserved,retained,unknown;
  uint32_t native_attempted,allocated,native_status_available,runtime_complete;
  uint64_t reserved_cpu_bytes;
 };
 struct Failure {int64_t adapter_error;uint32_t available,native_status_available;};
 ZornGpuRuntimeBackings()=default;
 ~ZornGpuRuntimeBackings()=default;
 ZornGpuRuntimeBackings(const ZornGpuRuntimeBackings&)=delete;
 ZornGpuRuntimeBackings& operator=(const ZornGpuRuntimeBackings&)=delete;
 int reserve(const ZGMemRequirement*,uint32_t*);
 int retainFailure(uint32_t,int64_t adapter_error);
 int snapshot(Summary*);
 int copyFailure(uint32_t,Failure*);
private:
 struct Slot {ZGMemRequirement requirement{};int64_t error=0;uint32_t failed=0,adapter_available=0;};
 NativeAdrenoMemory memory_[32];
 Slot slots_[32];
 CpuReport cpu_[32]{};
 uint64_t attempted_bytes_=0;
 uint32_t count_=0,busy_=0;
 bool enter();void leave();
 bool disjoint(const void*,size_t) const;
};
#endif

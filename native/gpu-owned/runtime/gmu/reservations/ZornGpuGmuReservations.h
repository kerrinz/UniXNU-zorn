/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#ifndef ZORN_GPU_GMU_RESERVATIONS_H
#define ZORN_GPU_GMU_RESERVATIONS_H
#include "NativeAdrenoMemory.h"
#include "ZornGpuGmuExtent.h"
/* Persistent CPU bookkeeping of ranges supplied by a future real GMU owner.
 * It cannot create/retain a native reference or prove the supplied reservation.
 * Caller must actually own/retain valid stable native descriptors and serialize
 * their lifetime for the entire ledger lifetime. One ledger conservatively
 * compares all supplied ranges; it neither establishes nor switches a domain.
 * No native method, allocator, VM map, address selection/export or HFI reply.
 * A local index identifies only metadata. Never interpret it as a device handle.
 * Full rounded reservation, including unbacked tail, stays recorded on failure.
 * No reset/release/retirement interface or implicit destructor cleanup. */
class ZornGpuGmuReservations final {
public:
 enum {Ok,Invalid,Busy,Conflict,Full,Retained};
 struct Reservation {uint64_t supplied_start,backing_bytes,reservation_bytes;};
 struct Summary {
  uint32_t entries,recorded,metadata_retained,native_status_unknown;
  uint32_t native_attempted,native_status_available,mapping_complete,runtime_complete;
 };
 struct Failure {int64_t adapter_error;uint32_t available,native_status_available;};
 ZornGpuGmuReservations()=default;
 ~ZornGpuGmuReservations()=default;
 ZornGpuGmuReservations(const ZornGpuGmuReservations&)=delete;
 ZornGpuGmuReservations& operator=(const ZornGpuGmuReservations&)=delete;
 int remember(const ZGMemRequirement*,NativeAdrenoMemory*,const Reservation*,uint32_t *local_index);
 int retainFailure(uint32_t local_index,int64_t adapter_error);
 int snapshot(Summary*);
 int copyFailure(uint32_t local_index,Failure*);
private:
 struct Entry {
  NativeAdrenoMemory *borrowed=nullptr;
  ZGMemRequirement request{};Reservation reservation{};ZGGmuExtent extent{};
  int64_t first_adapter_error=0;uint32_t failed=0;
 };
 Entry entries_[32];uint32_t count_=0,busy_=0;
 bool enter();void leave();
 static bool separate(const void*,size_t,const void*,size_t);
 bool disjoint(const void*,size_t) const;
 bool clearOfBorrowed(const void*,size_t) const;
 static bool overlap(const Reservation&,const Reservation&);
};
#endif

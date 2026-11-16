/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include "ZornGpuGmuReservations.h"
#include <string.h>
bool ZornGpuGmuReservations::enter(){uint32_t zero=0;return __atomic_compare_exchange_n(&busy_,&zero,1,false,__ATOMIC_ACQUIRE,__ATOMIC_RELAXED);}
void ZornGpuGmuReservations::leave(){__atomic_store_n(&busy_,0,__ATOMIC_RELEASE);}
bool ZornGpuGmuReservations::separate(const void *p,size_t n,const void *q,size_t m){
 uintptr_t a=(uintptr_t)p,b=(uintptr_t)q;
 return p&&q&&n&&m&&a<=UINTPTR_MAX-(n-1)&&b<=UINTPTR_MAX-(m-1)&&(a>b?a-b>=m:b-a>=n);
}
bool ZornGpuGmuReservations::disjoint(const void *p,size_t n) const{return separate(p,n,this,sizeof(*this));}
bool ZornGpuGmuReservations::clearOfBorrowed(const void *p,size_t n) const {
 for(uint32_t i=0;i<count_;++i)if(!separate(p,n,entries_[i].borrowed,sizeof(NativeAdrenoMemory)))return false;
 return true;
}
bool ZornGpuGmuReservations::overlap(const Reservation &a,const Reservation &b){
 // Supplied starts are GMU-space scalars, NEVER compared to CPU pointers.
 // Both intervals have already passed overflow/extent validation.
 return a.supplied_start<=b.supplied_start?
  b.supplied_start-a.supplied_start<a.reservation_bytes:
  a.supplied_start-b.supplied_start<b.reservation_bytes;
}
int ZornGpuGmuReservations::remember(const ZGMemRequirement *request,NativeAdrenoMemory *memory,
 const Reservation *reservation,uint32_t *index){
 const void *args[]={request,memory,reservation,index};
 const size_t sizes[]={sizeof(*request),sizeof(*memory),sizeof(*reservation),sizeof(*index)};
 const size_t aligns[]={alignof(ZGMemRequirement),alignof(NativeAdrenoMemory),alignof(Reservation),alignof(uint32_t)};
 for(unsigned i=0;i<4;++i){
  if(!disjoint(args[i],sizes[i])||(uintptr_t)args[i]%aligns[i])return Invalid;
  for(unsigned j=0;j<i;++j)if(!separate(args[i],sizes[i],args[j],sizes[j]))return Invalid;
 }
 if(!enter())return Busy;
 if(!clearOfBorrowed(request,sizeof(*request))||!clearOfBorrowed(reservation,sizeof(*reservation))||!clearOfBorrowed(index,sizeof(*index))){leave();return Invalid;}
 ZGGmuExtent extent{};
 if(ZGCheckGmuExtent(request,reservation->backing_bytes,reservation->reservation_bytes,&extent)!=ZG_OK){leave();return Invalid;}
 const uint64_t start=reservation->supplied_start,limit=UINT64_C(0x100000000);
 if(!start||start>=limit||(start&(extent.va_alignment-1))||extent.reservation_bytes>limit-start||
  (request->gmu_addr&&start!=request->gmu_addr)){leave();return Invalid;}
 for(uint32_t i=0;i<count_;++i){auto &old=entries_[i];
  if(old.request.kind==request->kind&&old.request.gmu_handle==request->gmu_handle){
   if(old.borrowed!=memory||old.request.raw_count!=request->raw_count||
    memcmp(old.request.raw+1,request->raw+1,(request->raw_count-1)*4)||
    memcmp(&old.reservation,reservation,sizeof(*reservation))){leave();return Conflict;}
   if(old.failed){leave();return Retained;}
   *index=i;leave();return Ok;
  }
  if(old.borrowed==memory||!separate(memory,sizeof(*memory),old.borrowed,sizeof(*memory))||
   overlap(old.reservation,*reservation)){leave();return Conflict;}
 }
 if(count_==32){leave();return Full;}
 uint32_t slot=count_;auto &entry=entries_[slot];entry.borrowed=memory;
 entry.request=*request;entry.reservation=*reservation;entry.extent=extent;++count_;
 *index=slot;leave();return Ok;
}
int ZornGpuGmuReservations::retainFailure(uint32_t index,int64_t error){
 if(!error)return Invalid;
 if(!enter())return Busy;
 if(index>=count_){leave();return Invalid;}
 auto &entry=entries_[index];if(entry.failed){leave();return Retained;}
 entry.first_adapter_error=error;entry.failed=1;leave();return Ok;
}
int ZornGpuGmuReservations::snapshot(Summary *out){
 if(!disjoint(out,sizeof(*out))||(uintptr_t)out%alignof(Summary))return Invalid;
 if(!enter())return Busy;
 if(!clearOfBorrowed(out,sizeof(*out))){leave();return Invalid;}
 Summary s{};s.entries=count_;
 for(uint32_t i=0;i<count_;++i){uint32_t bit=UINT32_C(1)<<i;s.recorded|=bit;s.native_status_unknown|=bit;if(entries_[i].failed)s.metadata_retained|=bit;}
 *out=s;leave();return Ok;
}
int ZornGpuGmuReservations::copyFailure(uint32_t index,Failure *out){
 if(!disjoint(out,sizeof(*out))||(uintptr_t)out%alignof(Failure))return Invalid;
 if(!enter())return Busy;
 if(index>=count_||!clearOfBorrowed(out,sizeof(*out))){leave();return Invalid;}
 Failure failure{};failure.adapter_error=entries_[index].first_adapter_error;failure.available=entries_[index].failed;
 *out=failure;leave();return Ok;
}

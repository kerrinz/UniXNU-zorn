/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include "ZornGpuTableVisibility.h"
#ifndef ZORN_NATIVE_VISIBILITY_COMPILE_ONLY
#define ZORN_NATIVE_VISIBILITY_COMPILE_ONLY 0
#endif
#if ZORN_NATIVE_VISIBILITY_COMPILE_ONLY != 0 && ZORN_NATIVE_VISIBILITY_COMPILE_ONLY != 1
#error Invalid visibility selector
#endif
bool ZornGpuTableVisibility::enter(){uint32_t zero=0;return __atomic_compare_exchange_n(&busy_,&zero,1,false,__ATOMIC_ACQUIRE,__ATOMIC_RELAXED);}
void ZornGpuTableVisibility::leave(){__atomic_store_n(&busy_,0,__ATOMIC_RELEASE);}
bool ZornGpuTableVisibility::disjoint(const void *p,size_t n) const {
 uintptr_t a=(uintptr_t)p,b=(uintptr_t)this;
 return p&&n&&a<=UINTPTR_MAX-(n-1)&&b<=UINTPTR_MAX-(sizeof(*this)-1)&&
  (a>b?a-b>=sizeof(*this):b-a>=n);
}
bool ZornGpuTableVisibility::stable() const {
 return memory_&&!memory_->quarantined()&&memory_->deviceReferences()&&
  memory_->descriptor()&&!memory_->imported()&&!memory_->writeCombined()&&
  (uintptr_t)memory_->mapping()==base_&&memory_->bytes()==bytes_&&
  memory_->spanCount()==1&&memory_->spans()&&memory_->spans()[0].offset==0&&
  memory_->spans()[0].bytes==bytes_;
}
int ZornGpuTableVisibility::reject(uint32_t error){
 if(!report_.first_adapter_error)report_.first_adapter_error=error;
 __atomic_store_n(&failed_,1,__ATOMIC_RELEASE);return 1;
}
int ZornGpuTableVisibility::bind(NativeAdrenoMemory *memory,ArmSmmu4KLiveVisibility *out){
 if(!enter())return Busy;
 if(report_.bind_attempted){leave();return Retained;}
 report_.bind_attempted=1;
#if !ZORN_NATIVE_VISIBILITY_COMPILE_ONLY
 (void)memory;(void)out;reject(Off);leave();return Disabled;
#else
 if(!disjoint(memory,sizeof(*memory))||!disjoint(out,sizeof(*out))||
    (uintptr_t)memory%alignof(NativeAdrenoMemory)||(uintptr_t)out%alignof(ArmSmmu4KLiveVisibility)){
  reject(Arguments);leave();return Invalid;
 }
 uintptr_t m=(uintptr_t)memory,v=(uintptr_t)out;
 if((m>v?m-v<sizeof(*out):v-m<sizeof(*memory))||out->cookie||out->publish_table_page){reject(Arguments);leave();return Invalid;}
 memory_=memory;base_=(uintptr_t)memory_->mapping();bytes_=memory_->bytes();
 if(!base_||(base_&4095)||!bytes_||(bytes_&4095)||base_>UINTPTR_MAX-(bytes_-1)||!disjoint((void*)base_,bytes_)||!stable()){
  reject(Backing);leave();return Invalid;
 }
 // Visibility metadata and the native object must not live in writable tables.
 const uintptr_t metadata[]={m,v};const size_t lengths[]={sizeof(*memory),sizeof(*out)};
 for(unsigned i=0;i<2;++i)if(metadata[i]>=base_?metadata[i]-base_<bytes_:base_-metadata[i]<lengths[i]){
  reject(Arguments);leave();return Invalid;
 }
 report_.bound=1;*out={this,thunk};leave();return Ok;
#endif
}
int ZornGpuTableVisibility::thunk(void *cookie,volatile uint64_t *page,size_t bytes){
 if(!cookie)return 1;
 return static_cast<ZornGpuTableVisibility*>(cookie)->publish(page,bytes);
}
int ZornGpuTableVisibility::publish(volatile uint64_t *page,size_t bytes){
#if !ZORN_NATIVE_VISIBILITY_COMPILE_ONLY
 (void)page;(void)bytes;return 1;
#else
 if(!enter()){
  __atomic_store_n(&reentry_,1,__ATOMIC_RELEASE);
  __atomic_store_n(&failed_,1,__ATOMIC_RELEASE);return 1;
 }
 if(__atomic_load_n(&failed_,__ATOMIC_ACQUIRE)){leave();return 1;}
 if(!report_.bound||!stable()){reject(Backing);leave();return 1;}
 if(report_.callback_attempts==UINT32_MAX){reject(CounterLimit);leave();return 1;}
 ++report_.callback_attempts;
 uintptr_t p=(uintptr_t)page;
 if(!page||bytes!=4096||(p&4095)||p<base_||p-base_>bytes_||bytes>bytes_-(p-base_)){
  reject(Range);memory_->quarantine();leave();return 1;
 }
 ++report_.native_attempts;
 IOReturn native=memory_->publishForDevice((size_t)(p-base_),bytes,false,false);
 // Preserve the REAL native result before any adapter/post-call decision.
 report_.last_native_status=native;report_.native_status_available=1;
 report_.native_status_attempt=report_.callback_attempts;
 if(native!=kIOReturnSuccess){
  if(!report_.first_native_error_available){report_.first_native_error=native;report_.first_native_error_available=1;}
  __atomic_store_n(&failed_,1,__ATOMIC_RELEASE);memory_->quarantine();leave();return 1;
 }
 if(!stable()){reject(Changed);memory_->quarantine();leave();return 1;}
 if(__atomic_load_n(&reentry_,__ATOMIC_ACQUIRE)||__atomic_load_n(&failed_,__ATOMIC_ACQUIRE)){
  reject(Reentry);memory_->quarantine();leave();return 1;
 }
 leave();return 0;
#endif
}
int ZornGpuTableVisibility::snapshot(Report *out){
 if(!disjoint(out,sizeof(*out))||(uintptr_t)out%alignof(Report))return Invalid;
 if(!enter())return Busy;
 Report r=report_;r.failed=__atomic_load_n(&failed_,__ATOMIC_ACQUIRE);
 if(__atomic_load_n(&reentry_,__ATOMIC_ACQUIRE)&&!r.first_adapter_error)r.first_adapter_error=Reentry;
 *out=r;leave();return Ok;
}

__attribute__((noinline)) bool ZornGpuTableVisibility::selectedMode() const {return ZORN_NATIVE_VISIBILITY_COMPILE_ONLY!=0;}

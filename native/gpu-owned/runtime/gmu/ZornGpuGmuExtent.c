/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include "ZornGpuGmuExtent.h"
#include <string.h>
static int separate(const void *p,size_t n,const void *q,size_t m){
 uintptr_t a=(uintptr_t)p,b=(uintptr_t)q;
 return p&&q&&n&&m&&a<=UINTPTR_MAX-(n-1)&&b<=UINTPTR_MAX-(m-1)&&
  (a>b?a-b>=m:b-a>=n);
}
int ZGCheckGmuExtent(const ZGMemRequirement *request,uint64_t backing,
 uint64_t reservation,ZGGmuExtent *out){
 if(!separate(request,sizeof(*request),out,sizeof(*out))||
  (uintptr_t)request%_Alignof(ZGMemRequirement)||(uintptr_t)out%_Alignof(ZGGmuExtent))return ZG_INVALID;
 ZGMemRequirement q={0};
 if(request->raw_count>11||ZGPlanMemAlloc(request->raw,request->raw_count,&q)!=ZG_OK||
  !q.format_available||q.runtime_complete||memcmp(&q,request,sizeof(q)))return ZG_INVALID;
 if(!(q.requirements&ZG_REQUIRE_GMU_MAP)||
  (q.path!=ZG_PATH_GMU_RAM&&q.path!=ZG_PATH_GPU_GLOBAL)||
  (q.requirements&(ZG_REQUIRE_SECURE|ZG_REQUIRE_FIXED_RESOURCE|ZG_REQUIRE_PREALLOCATED)))return ZG_INVALID;
 if(!backing||(backing&4095)||backing<q.size||backing>UINT32_MAX)return ZG_INVALID;
 uint64_t rounded=(backing+q.size_alignment-1)&~((uint64_t)q.size_alignment-1);
 if(rounded>UINT32_MAX||reservation!=rounded)return ZG_INVALID;
 ZGGmuExtent extent={q.size,backing,reservation,reservation-backing,q.va_alignment,q.size_alignment};
 *out=extent;return ZG_OK;
}

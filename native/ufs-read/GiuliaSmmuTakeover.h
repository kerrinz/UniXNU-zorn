// SPDX-License-Identifier: BSD-2-Clause-Patent
#include "SmmuTakeover.h"
struct GiuliaSmmuPlan {
  UfsSmmuPlan target;
  bool retarget = false;
  uint32_t oldSmr = 0, oldS2cr = 0;
};

template<class Read>
static GiuliaSmmuPlan planGiuliaSmmu(uint16_t sid, uint64_t dma, uint64_t bytes, Read read) {
  GiuliaSmmuPlan result;
  result.target = planUfsSmmu(sid,dma,bytes,read);
  if (!result.target.error) return result;
  unsigned count=read(0x20)&255, slot=0xffffffffU, matches=0;
  if (!count || count>128) return result;
  for(unsigned i=0;i<count;++i) {
    uint32_t smr=read(0x800+4*i), mask=(smr>>16)&0x7fff;
    if ((smr&0x80000000U) && !((smr^sid)&0xffff&~mask)) {
      if (mask || ++matches != 1) {result.target.error="ambiguous UFS stream";return result;}
      slot=i;
    }
  }
  if (matches != 1) return result;
  uint32_t oldSmr=read(0x800+4*slot), oldRoute=read(0xc00+4*slot), idr1=read(0x24);
  unsigned pages=1U<<(((idr1>>28)&7)+1), oldBank=oldRoute&255;
  if (((oldRoute>>16)&3)!=0 || oldBank>=(idr1&255)) return result;
  // Plan a separate unused context, keeping the firmware context untouched.
  // Only this exact SID is hidden during planning; all other streams stay visible.
  auto planningRead=[&](unsigned at) {
    if (at==0x800+4*slot) return uint32_t(0);
    if (at==(pages+oldBank)*4096) return read(at)|1U;
    return read(at);
  };
  UfsSmmuPlan target=planUfsSmmu(sid,dma,bytes,planningRead);
  if (target.error || target.reuse || target.bank==oldBank) return result;
  target.slot=slot;
  result.target=target;result.retarget=true;result.oldSmr=oldSmr;result.oldS2cr=oldRoute;
  return result;
}

template<class Read,class Write>
static const char *configureGiuliaSmmu(const GiuliaSmmuPlan &p,uint16_t sid,
                                     bool quiescent,Read read,Write write) {
  if (!quiescent) return "UFS queue not stopped";
  if (p.target.error) return p.target.error;
  if (p.retarget && (read(0x800+4*p.target.slot)!=p.oldSmr ||
                     read(0xc00+4*p.target.slot)!=p.oldS2cr))
    return "UFS stream changed since planning";
  return configureUfsSmmu(p.target,sid,read,write);
}

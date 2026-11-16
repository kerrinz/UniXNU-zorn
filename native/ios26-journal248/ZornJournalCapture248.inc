/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include "ZornApplicationJournal248.h"
static int zorn26_journal_process248(proc_t p,int fd){
 if(!p || fd!=2)return 0;
 const char *name=proc_best_name(p);
 static const char expected[]="zorn-metal-probe193";
 return name && !strncmp(name,expected,sizeof(expected));
}
// Observe the actually returned prefix after the original write. User memory
// is sampled here, not retained; concurrent user mutation is outside this log
// evidence. No result, descriptor, permission or native error is changed.
static void zorn26_journal_capture248(proc_t p,int fd,const ZornJournalVector248 *v,
 unsigned count,user_ssize_t written,int error,int flags,unsigned unsupported){
 if(!zorn26_journal_process248(p,fd) || written<=0)return;
 ZornJournalTicket248 t={0,0,0};
 if(!zorn26_journal_begin248(proc_uniqueid(p),(uint32_t)proc_pid(p),(uint64_t)written,
   unsupported || error || flags || !v || !count || count>ZornJournalVectors248,&t))return;
 uint32_t at=0;unsigned failed=0;
 for(unsigned i=0;i<count && at<t.bytes;++i){
  uint64_t n=v[i].bytes;if(n>t.bytes-at)n=t.bytes-at;
  if(!n)continue;
  if(v[i].address>UINT64_MAX-n || copyin((user_addr_t)v[i].address,(char *)t.target+at,(size_t)n)){
   failed=1;break;
  }
  at+=(uint32_t)n;
 }
 if(at!=t.bytes)failed=1;
 zorn26_journal_finish248(t.index,failed);
}

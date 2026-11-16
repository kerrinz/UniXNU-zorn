/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include "ZornJournalStore248.h"
#include <cassert>
#include <atomic>
#include <thread>
#include <vector>
#include <cstring>
#include <cstdio>
#include <cerrno>
using user_addr_t=uint64_t;using user_ssize_t=int64_t;
struct Process {const char *name;uint64_t unique;uint32_t pid;};using proc_t=Process *;
const char *proc_best_name(proc_t p){return p->name;}
uint64_t proc_uniqueid(proc_t p){return p->unique;}
uint32_t proc_pid(proc_t p){return p->pid;}
static uintptr_t base;static size_t span;static bool copy_fault;
static int copyin(user_addr_t a,void *out,size_t n){
 if(copy_fault || a<base || n>span || a-base>span-n)return EFAULT;
 memcpy(out,reinterpret_cast<void *>(uintptr_t(a)),n);return 0;
}
static ZornJournalStore248 store{};
extern "C" int zorn26_journal_begin248(uint64_t u,uint32_t p,uint64_t n,unsigned bad,ZornJournalTicket248 *t){return t && store.begin(u,p,n,bad,*t);}
extern "C" void zorn26_journal_finish248(uint32_t t,unsigned e){store.finish(t,e);}
extern "C" void zorn26_journal_exit248(uint64_t u,uint32_t p,uint32_t s){store.exit(u,p,s);}
extern "C" int zorn26_journal_snapshot248(uint32_t a,void *v,uint32_t n,ZornJournalSnapshot248 *o){return o && store.snapshot(a,v,n,*o);}
#include "ZornJournalCapture248.inc"
static uint8_t out[ZornJournalCapacity248];
static ZornJournalSnapshot248 snap(uint32_t at=0){ZornJournalSnapshot248 s{};assert(store.snapshot(at,out,sizeof(out),s));return s;}
static void reset(){store={};copy_fault=false;}
static uint32_t crc(const uint8_t *v,size_t n){uint32_t c=~0u;for(size_t i=0;i<n;++i){c^=v[i];for(unsigned j=0;j<8;++j)c=(c>>1)^((0u-(c&1u))&0xedb88320u);}return ~c;}
static void add(const char *text){ZornJournalTicket248 t{};assert(store.begin(42,7,strlen(text),0,t));memcpy(t.target,text,t.bytes);store.finish(t.index,0);}
int main(){
 reset();ZornJournalSnapshot248 empty{};assert(!store.snapshot(0,out,sizeof(out),empty));
 // Out-of-order completion cannot publish bytes belonging to an unfinished writer.
 ZornJournalTicket248 a{},b{};assert(store.begin(42,7,3,0,a));assert(store.begin(42,7,6,0,b));
 memcpy(a.target,"abc",3);memcpy(b.target,"defghi",6);store.finish(b.index,0);auto s=snap();assert(!s.published && s.pending==2);
 store.exit(43,7,0);store.exit(42,8,0);assert(!snap().exited);store.exit(42,7,0);assert(snap().pending==2);
 store.finish(a.index,0);s=snap();assert(s.published==9 && s.seen_bytes==9 && !s.pending && s.exited && !s.exit_status && !s.gaps);
 assert(!memcmp(out,"abcdefghi",9) && s.crc32==crc(out,9));assert(snap(5).bytes==4);assert(!memcmp(out,"fghi",4));
 assert(!store.begin(43,9,1,0,a));assert(!snap().gaps);assert(!store.begin(42,7,1,0,a));assert(snap().gaps&ZornJournalLate248);
 reset();add("123456789");assert(snap().crc32==0xcbf43926);store.exit(42,7,9<<8);assert(snap().exit_status==9u<<8);
 // Both the per-write and total bounds report loss instead of wrapping/overwriting.
 reset();assert(store.begin(42,7,16385,0,a));assert(a.bytes==16384);memset(a.target,0x41,a.bytes);store.finish(a.index,0);assert(snap().gaps&ZornJournalCapacityLost248);
 for(int i=0;i<3;++i){assert(store.begin(42,7,16384,0,a));memset(a.target,0x42,a.bytes);store.finish(a.index,0);}assert(!store.begin(42,7,1,0,a));s=snap();assert(s.reserved==65536 && s.published==65536 && s.seen_bytes==65538);
 reset();for(unsigned i=0;i<ZornJournalSlots248;++i)add("a");assert(!store.begin(42,7,1,0,a));assert(snap().gaps&ZornJournalSlotsLost248);
 reset();assert(!store.begin(42,7,10,1,a));s=snap();assert(s.seen_bytes==10 && !s.published && (s.gaps&ZornJournalUnsupported248));
 reset();assert(store.begin(42,7,4,0,a));store.finish(a.index,1);assert(snap().gaps&ZornJournalCopyLost248);store.finish(a.index,0);assert(snap().gaps&ZornJournalBadToken248);
 reset();add("a");store.gate=1;assert(!store.begin(42,7,1,0,a));assert(!store.snapshot(0,out,sizeof(out),s));store.gate=0;assert(snap().gaps&ZornJournalBusy248);
 reset();add("a");store.exit(42,7,0);store.exit(42,7,0);assert(snap().gaps&ZornJournalBadToken248);
 // Capture the actual write prefix, with normalized vectors, faults and overflow.
 Process p{"zorn-metal-probe193",42,7},other{"unrelated",42,7};char input[]="abcdefghi";base=(uintptr_t)input;span=9;
 ZornJournalVector248 v[]={{base,3},{base+3,0},{base+3,6}};
 reset();zorn26_journal_capture248(&p,2,v,3,7,0,0,0);s=snap();assert(s.bytes==7 && !memcmp(out,"abcdefg",7) && !s.gaps);
 reset();zorn26_journal_capture248(&other,2,v,3,7,0,0,0);assert(!store.unique);zorn26_journal_capture248(&p,1,v,3,7,0,0,0);assert(!store.unique);
 reset();zorn26_journal_capture248(&p,2,v,3,0,0,0,0);assert(!store.unique);
 reset();copy_fault=true;zorn26_journal_capture248(&p,2,v,3,7,0,0,0);assert(snap().gaps&ZornJournalCopyLost248);
 reset();ZornJournalVector248 overflow{UINT64_MAX-2,5};zorn26_journal_capture248(&p,2,&overflow,1,5,0,0,0);assert(snap().gaps&ZornJournalCopyLost248);
 reset();zorn26_journal_capture248(&p,2,v,1,7,0,0,0);assert(snap().gaps&ZornJournalCopyLost248);
 for(unsigned reason=0;reason<3;++reason){reset();zorn26_journal_capture248(&p,2,v,3,7,reason==0?EFAULT:0,reason==1?1:0,reason==2);s=snap();assert(s.seen_bytes==7 && !s.reserved && (s.gaps&ZornJournalUnsupported248));}
 // A failed observer reservation is visible. Contention never blocks completion.
 reset();std::atomic<unsigned> done{0};std::atomic<bool> go{false};
 std::vector<std::thread> writers;for(unsigned j=0;j<4;++j)writers.emplace_back([&,j](){while(!go.load())std::this_thread::yield();for(unsigned k=0;k<32;++k){ZornJournalTicket248 t{};if(store.begin(42,7,16,0,t)){memset(t.target,int(j+1),t.bytes);store.finish(t.index,0);}}++done;});
 go=true;while(done.load()!=4){ZornJournalSnapshot248 x{};uint8_t local[768];if(store.snapshot(0,local,sizeof(local),x))assert(x.published<=x.reserved);}
 for(auto &w:writers)w.join();store.exit(42,7,0);s=snap();assert(s.pending==0 && s.exited && s.published==s.reserved);
 std::vector<uint8_t> all;uint32_t at=0;do{s=snap(at);all.insert(all.end(),out,out+s.bytes);at+=s.bytes;}while(at<s.published);assert(crc(all.data(),all.size())==s.crc32);
 printf("journal248: ordered publication, CRC, bounds, capture, exit and concurrency passed\n");
}

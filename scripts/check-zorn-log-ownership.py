#!/usr/bin/env python3
"""Stress the actual log/MAC functions with eight simultaneous host producers."""
from pathlib import Path
import hashlib,json,re,subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'out/zorn/smp';OUT.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/'UniXNU-zorn/native/ufs-read/ZornUfsRead.cpp'
text=SOURCE.read_text()
def function(marker):
    start=text.index(marker);brace=text.index('{',start);end=brace+1;depth=1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[start:end]
names=['static void zorn_log_put(const char *text)',
       'extern "C" void zorn_ufs_log_word(const char *text)',
       'extern "C" void zorn_ufs_user_output(unsigned fd, const char *text, size_t length)',
       'extern "C" void zorn_ufs_note_mac_failure(const char *policy, int error)',
       'static void zorn_checkpoint_reset(void)\n{']
functions=[function(n) for n in names]
def audit_ownership(source):
    if re.search(r'^\s+gLogBusy\s*=',source,re.M):
        raise ValueError('non-atomic ownership store remains')
audit_ownership(text)
watchdog=SOURCE.with_name("ZornWatchdog.h")
audit_ownership(watchdog.read_text())
try:
    audit_ownership((OUT/'ZornUfsRead.pre-atomic.cpp').read_text())
except ValueError:
    pass
else:
    raise AssertionError('old plain-store source was not rejected')
source=r'''
#include <cassert>
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <thread>
#include <vector>
#include "ZornGuiLog.h"
#include "ZornTouchRawLog.h"
struct Log {char magic[8];unsigned count,next;char word[340][12];};
static Log gLogBlock;
static bool gGuiWatch=true,gTouchRawLog=false,gLogArmed=true,gCompactTrace=false;
static int gLogBusy;
static unsigned gTraceSuppressed,gStage2Suppressed,gCheckpointSeen,gCheckpointSkip;
static bool gReturnAfterTent;
static char gRecoveryCheckpoint[12]="RESET";
static std::atomic<unsigned> inWrite{0},writes{0},resets{0};
static constexpr unsigned ZORN_TRACE_STAGE_COUNT=1;
static int zorn_trace_stage_index(const char *){return -1;}
struct ZornMacFailure {char policy[12];unsigned error;};
struct Guarded {uint64_t before;ZornMacFailure failures[8];uint64_t after;};
static Guarded guarded={0x0123456789abcdef,{},0xfedcba9876543210};
#define gMacFailures guarded.failures
static unsigned gMacFailureCount,gMacFailureReady[8];
static void zorn_checkpoint_reset_owned(){assert(gLogBusy==1);++resets;}
static void zorn_checkpoint_reset(void);
@WRITER@
static int backend(const void *p){
 assert(p==&gLogBlock && gLogBusy==1 && inWrite.fetch_add(1)==0);
 std::this_thread::yield();
 assert(gLogBlock.count<=ZORN_GUI_LOG_SLOTS && gLogBlock.next<ZORN_GUI_LOG_SLOTS);
 auto bytes=reinterpret_cast<const unsigned char *>(&gLogBlock);
 for(unsigned i=ZORN_GUI_LOG_OFFSET;i<4096;++i)assert(bytes[i]==0xa5);
 ++writes;assert(inWrite.fetch_sub(1)==1);return 0;
}
static int (*gZornWriteLog)(const void *)=backend;
static void zorn_log_append(const char *s){zorn_log_put(s);(void)backend(&gLogBlock);}
extern "C" void zorn_ufs_log_word(const char *);
static void zorn_trace_time(){zorn_ufs_log_word("TIM00000001");}
@FUNCTIONS@
int main(){
 memset(reinterpret_cast<unsigned char *>(&gLogBlock)+ZORN_GUI_LOG_OFFSET,0xa5,4096-ZORN_GUI_LOG_OFFSET);
 std::atomic<unsigned> ready{0};std::atomic<bool> go{false};std::vector<std::thread> workers;
 for(unsigned id=0;id<8;++id)workers.emplace_back([&,id]{
  ++ready;while(!go.load())std::this_thread::yield();
  for(unsigned n=0;n<2500;++n){
   if(id&1)zorn_ufs_user_output(id,"physical-test",13);
   else zorn_ufs_log_word("WORKER");
  }
  for(unsigned n=0;n<64;++n)zorn_ufs_note_mac_failure("TEST",id+1);
 });
 while(ready.load()!=8)std::this_thread::yield();go=true;
 for(auto &w:workers)w.join();
 assert(writes>0 && !inWrite && !gLogBusy);
 assert(gMacFailureCount==512 && guarded.before==0x0123456789abcdef && guarded.after==0xfedcba9876543210);
 for(unsigned i=0;i<8;++i)assert(gMacFailureReady[i]==1 && !strcmp(gMacFailures[i].policy,"TEST") && gMacFailures[i].error>=1 && gMacFailures[i].error<=8);
 __sync_bool_compare_and_swap(&gLogBusy,0,1);zorn_checkpoint_reset();assert(!resets && gLogBusy==1);
 __sync_lock_release(&gLogBusy);zorn_checkpoint_reset();assert(resets==1&&!gLogBusy);
 gReturnAfterTent=true;gCheckpointSkip=3;
 for(unsigned i=0;i<12;++i)zorn_ufs_log_word("RESET");
 assert(resets==2 && gCheckpointSeen==4 && !gCheckpointSkip && !gReturnAfterTent && !gLogBusy);
 printf("eight producers: %u whole-block writes; bounded MAC slots; reset ownership preserved\n",writes.load());
}
'''.replace('@WRITER@',functions[0]).replace('@FUNCTIONS@','\n'.join(functions[1:]))
(OUT/'log-ownership-check.cpp').write_text(source)
command=['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-O1','-fsanitize=address,undefined','-I',str(SOURCE.parent),str(OUT/'log-ownership-check.cpp'),'-o',str(OUT/'log-ownership-check')]
subprocess.run(command,check=True)
subprocess.run([str(OUT/'log-ownership-check')],check=True)
result=dict(source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),watchdog_sha256=hashlib.sha256(watchdog.read_bytes()).hexdigest(),actual_functions=[n.split('(')[0] for n in names],host_producers=8,iterations_each=2500,asan_ubsan=True,no_simultaneous_block_writers=True,footer_preserved=True,mac_reservations=512,mac_slots_bounded=8,reset_never_steals_ownership=True,old_plain_store_baseline_rejected=True,hardware_qualified=False)
(OUT/'log-ownership-host-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

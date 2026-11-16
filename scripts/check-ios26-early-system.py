#!/usr/bin/env python3
"""Exercise actual early-launch source; XNU/hardware boundaries are explicit fixtures."""
from pathlib import Path
import argparse,json,hashlib,subprocess

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sanitizer',choices=['address,undefined','thread'],default='address,undefined');a=p.parse_args();S=a.source_root;O=a.out;O.mkdir()
 u=(S/'ZornUfsOwner26.cpp').read_text();m=(S/'MiniIOMobileFramebuffer.cpp').read_text();domain=(S/'ZornGen7SmmuDomain26.cpp').read_text()
 def extract(t,name):
  begin=t.index(name);end=t.index('{',begin)+1;depth=1
  while depth:
   depth+=(t[end]=='{')-(t[end]=='}');end+=1
  return t[begin:end]
 names=['static unsigned zorn_early_mode252()', 'static void zorn_cpu_publish252(', 'static void zorn_gpu_early_worker252(', 'static void zorn_gpu_early_schedule252(']
 actual='\n'.join(extract(u,n) for n in names)
 actual+='\nstatic unsigned append252(char *line,unsigned cap,unsigned size){\n'+extract(u,'    if(size>=2 && zorn_early_mode252()==1)')+'\nreturn size;\n}\n'
 selection=extract((S/'ZornJournalCapture248.inc').read_text(),'static int zorn26_journal_process248(')
 prefix=r'''
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
#include <thread>
#include "ZornGpuEarly252.h"
using natural_t=unsigned;using wait_result_t=int;using thread_t=void*;
constexpr thread_t THREAD_NULL=nullptr;constexpr int KERN_SUCCESS=0,NSEC_PER_SEC=1;
static std::map<std::string,unsigned> args;
static int PE_parse_boot_argn(const char *key,void *out,int bytes){assert(bytes==sizeof(unsigned));auto it=args.find(key);if(it==args.end())return 0;memcpy(out,&it->second,sizeof(unsigned));return 1;}
static unsigned zornEarlyFlags252,zornCpuDone252,zornCpuMask252,zornCpuOnline252,zornCpuUser252,zornCpuSystem252;
static uint64_t zornEarlyTicks252;
static unsigned processor_avail_count=8;
static bool normal=true,interrupt=false,enabledInterrupt=true;
static bool preemption_enabled(){return normal;}static bool ml_at_interrupt_context(){return interrupt;}static bool ml_get_interrupts_enabled(){return enabledInterrupt;}
static uint64_t ticks=1,readyAt=1;static unsigned sleepCalls,readyCalls,cdcCalls,writeCalls,deallocCalls,spawnCalls;
static uint64_t mach_absolute_time(){return ticks;}
static void clock_interval_to_deadline(unsigned n,unsigned unit,uint64_t *out){*out=ticks+n*unit;}
static void IOSleep(unsigned n){assert(n==10);++sleepCalls;++ticks;}
static bool zorn26_gmu_deferred_ready252(){++readyCalls;return ticks>=readyAt;}
struct ZornUfsOwner26{enum class Phase {RootRegistered,Other};Phase phase=Phase::RootRegistered;unsigned refs=1;void retain(){++refs;}void release(){assert(refs>1);--refs;}struct Status{Phase phase;};Status readStatus(){return {phase};}};
struct Hjt26Reason{struct {char text[256];}record;};
constexpr unsigned kZornPlatformRecordTrial=1;
static void hjt26_capture(Hjt26Reason *r,const char *text,unsigned kind){assert(kind==1);strcpy(r->record.text,text);assert(strstr(text,"cpu_samples=pending"));}
static unsigned writeRaw=0;static bool writeReturned=true,readbackReturned=true,readbackMatched=true;
namespace ZornUfsCore26{struct PlatformRecordObservation{bool writeReturned=false,readbackReturned=false,readbackMatched=false;};static unsigned persistPlatformRecordOnce(decltype(Hjt26Reason::record)&,PlatformRecordObservation &o){++writeCalls;o={::writeReturned,::readbackReturned,::readbackMatched};return writeRaw;}}
static void zorn_gpu_progress_cdc201(ZornUfsOwner26*){++cdcCalls;}
struct End{};static thread_t current_thread(){return reinterpret_cast<void*>(1);}static int thread_terminate(thread_t){throw End{};}static void panic(const char*){assert(false);}
static int spawnRaw=0;static bool spawnHandle=true;static void (*scheduled)(void*,wait_result_t);static void *scheduledContext;
static int kernel_thread_start(void(*f)(void*,wait_result_t),void *c,thread_t *out){++spawnCalls;scheduled=f;scheduledContext=c;*out=spawnHandle?reinterpret_cast<void*>(2):nullptr;return spawnRaw;}
static void thread_deallocate(thread_t t){assert(t);++deallocCalls;}
using proc_t=const char*;static const char *proc_best_name(proc_t p){return p;}
'''
 suffix=r'''
static void defaults(){args={{"-g0",1},{"zorn26_gpu_cdc",1},{"zorn26_prearmed_recovery",1},{"zorn_wdt",1},{"zorn26_installed_root_trial",1},{"zorn26_touch",1},{"zorn26_touch_continuous",1},{"zorn26_trial_seconds",300},{"zorn26_software_accelerator",2}};}
static void reset(){defaults();zornEarlyFlags252=0;zornEarlyTicks252=0;zornCpuDone252=0;normal=true;interrupt=false;enabledInterrupt=true;ticks=readyAt=1;sleepCalls=readyCalls=cdcCalls=writeCalls=deallocCalls=spawnCalls=0;writeRaw=0;writeReturned=readbackReturned=readbackMatched=true;spawnRaw=0;spawnHandle=true;scheduled=nullptr;scheduledContext=nullptr;}
static void runWorker(ZornUfsOwner26 &o){try{zorn_gpu_early_worker252(&o,0);assert(false);}catch(const End&){};}
int main(){
 reset();assert(zorn_early_mode252()==1);unsigned controls=1;
 const auto good=args;
 for(const auto &kv:good){defaults();args.erase(kv.first);assert(zorn_early_mode252()==(kv.first=="-g0"?0u:2u));++controls;defaults();args[kv.first]=0;assert(zorn_early_mode252()==2);++controls;}
 defaults();args["-g45"]=0;assert(zorn_early_mode252()==2);++controls;
 reset();ZornUfsOwner26 o;zorn_gpu_early_schedule252(&o);assert(spawnCalls==1 && deallocCalls==1 && o.refs==2 && zornEarlyFlags252==3);zorn_gpu_early_schedule252(&o);assert(spawnCalls==1);++controls;
 readyAt=7;runWorker(o);assert(readyCalls==7 && sleepCalls==6 && writeCalls==1 && cdcCalls==1 && o.refs==1 && zornEarlyFlags252==63 && zornEarlyTicks252==7);++controls;
 reset();ZornUfsOwner26 failed;spawnRaw=1;zorn_gpu_early_schedule252(&failed);assert(spawnCalls==1 && failed.refs==1 && !deallocCalls && (zornEarlyFlags252&0x80000000));zorn_gpu_early_schedule252(&failed);assert(spawnCalls==1);++controls;
 reset();ZornUfsOwner26 unknown;spawnHandle=false;zorn_gpu_early_schedule252(&unknown);assert(spawnCalls==1 && unknown.refs==2 && !deallocCalls && (zornEarlyFlags252&0x80000000));zorn_gpu_early_schedule252(&unknown);assert(spawnCalls==1);++controls;
 // Fixture releases only the retained host reference; no device cleanup claim.
 unknown.release();
 for(unsigned failure=0;failure<10;++failure){
  reset();ZornUfsOwner26 x;x.retain();
  if(failure==0)readyAt=100;
  if(failure==1)x.phase=ZornUfsOwner26::Phase::Other;
  if(failure==2)writeRaw=1;
  if(failure==3)writeReturned=false;
  if(failure==4)readbackReturned=false;
  if(failure==5)readbackMatched=false;
  if(failure==6)normal=false;
  if(failure==7)interrupt=true;
  if(failure==8)enabledInterrupt=false;
  if(failure==9)args["zorn_wdt"]=0;
  runWorker(x);assert(cdcCalls==0 && x.refs==1 && (zornEarlyFlags252&0x80000000));
  if(failure==0)assert(ticks==31 && sleepCalls==30 && readyCalls==30 && !writeCalls);
  if(failure>=6)assert(!readyCalls && !writeCalls);
  ++controls;
 }
 for(unsigned cycle=0;cycle<100;++cycle){
  reset();natural_t user[8]={1,0,3,0,5,0,7,0},system[8]={0,2,0,4,0,6,0,8};
  std::thread writer([&]{zorn_cpu_publish252(0xff,8,user,system);});
  while(!__atomic_load_n(&zornCpuDone252,__ATOMIC_ACQUIRE))std::this_thread::yield();
  assert(__atomic_load_n(&zornCpuMask252,__ATOMIC_RELAXED)==255 && __atomic_load_n(&zornCpuOnline252,__ATOMIC_RELAXED)==8);
  assert(__atomic_load_n(&zornCpuUser252,__ATOMIC_RELAXED)==0x55 && __atomic_load_n(&zornCpuSystem252,__ATOMIC_RELAXED)==0xaa);writer.join();
 }
 ++controls;reset();natural_t all[8]={1,1,1,1,1,1,1,1};zorn_cpu_publish252(0x33,7,all,all);assert(zornCpuMask252==0x33 && zornCpuUser252==0x33 && zornCpuSystem252==0x33 && zornCpuOnline252==7);++controls;
 reset();zornEarlyFlags252=63;zornEarlyTicks252=10;zorn_cpu_publish252(255,8,all,all);
 for(unsigned cap=7;cap<200;++cap){
  char line[256];memset(line,0xcc,sizeof(line));memcpy(line,"frame\r\n",7);
  const auto n=append252(line,cap,7);assert(static_cast<unsigned char>(line[cap])==0xcc);
  if(n){assert(n<cap && strlen(line)==n);assert(strstr(line,",ep=3f/a/1/ff/8/ff/ff\r\n"));}
 }
 ++controls;
 assert(!zorn26_journal_process248(nullptr,2) && !zorn26_journal_process248("backboardd",1));
 assert(zorn26_journal_process248("backboardd",2) && !zorn26_journal_process248("backboarddX",2) && !zorn26_journal_process248("zorn-metal-probe193",2));++controls;
 printf("PASS %u actual early-launch controls;100 CPU atomic publication races;explicit XNU/hardware fixtures\n",controls);
}
'''
 source=prefix+actual+'\n'+selection+suffix;(O/'check.cpp').write_text(source)
 checks=[
  ('retained original three completed pre-GPU transfers and deferred call', 'completedFrames>=3' in u and 'const unsigned actual=zorn26_gmu_validate_smr_after_checkpoint();' in u),
  ('EL0 validates actual RootRegistered device before early scheduling',u.index('actual.root.device!=static_cast<dev_t>(actualMountedDevice)')<u.index('if(zorn_early_mode252()==1)zorn_gpu_early_schedule252(owner);')),
  ('original25s/45s CPU sampling precedes independent publication',u.index('IOSleep(25000);',u.index('static void zorn_touch_checkpoint_worker26'))<u.index('IOSleep(20000);',u.index('static void zorn_touch_checkpoint_worker26'))<u.index('zorn_cpu_publish252(valid,online,user,system);')),
  ('malformed selection refused before scheduling',u.index('if(zorn_early_mode252()==2)return;')<u.index('if(zorn_early_mode252()==1)zorn_gpu_early_schedule252(owner);')),
  ('placeholder suppressed only with explicit early option','const bool submitted=early==0 && publishAccelerator(&provider,false);' in m),
  ('nonconsuming real deferred-owner observation','return __atomic_load_n(&zornGmuDeferredOwner,__ATOMIC_ACQUIRE)!=nullptr;' in domain),
 ]
 assert all(ok for _,ok in checks),checks
 def run(n,args):
  r=subprocess.run(args,capture_output=True,timeout=120);(O/(n+'.stdout')).write_bytes(r.stdout);(O/(n+'.stderr')).write_bytes(r.stderr);(O/(n+'.command.json')).write_text(json.dumps(dict(arguments=args,exit=r.returncode),indent=2)+'\n');assert r.returncode==0,r.stderr.decode(errors='replace')[-4000:];return r.stdout.decode()
 run('compile',['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-pthread','-g','-fsanitize='+a.sanitizer,'-I',str(S),str(O/'check.cpp'),'-o',str(O/'check')]);stdout=run('check',[str(O/'check')])
 pin=lambda f:dict(path=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest())
 (O/'result.json').write_text(json.dumps(dict(passed=True,sanitizer=a.sanitizer,checks=[n for n,_ in checks],stdout=stdout,actual_functions=names,source=[pin(S/n) for n in ['ZornGpuEarly252.h','ZornUfsOwner26.cpp','MiniIOMobileFramebuffer.cpp','ZornGen7SmmuDomain26.cpp','ZornJournalCapture248.inc']],scope='actual source control/lifecycle/atomics with explicit host XNU,thread,persistence,CDC fixtures;not hardware qualification'),indent=2)+'\n');print(stdout.strip())

if __name__=='__main__':main()

#!/usr/bin/env python3
"""Actual CPU snapshot scheduling;no GPU execution or lifetime qualification."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess
p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--parent-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sanitizer',choices=['address,undefined','thread'],default='address,undefined');a=p.parse_args();S=a.source_root.resolve();P=a.parent_root.resolve();O=a.out.resolve();O.mkdir();current=S/'ZornClientFailureStore261.h';old=P/'ZornClientFailureStore261.h';(O/'legacy-store.h').write_text(old.read_text().replace('class ZornClientFailureStore261 {','class LegacyStore {'))
code=r'''
#include <cassert>
#include <cstdint>
#include <set>
#include <vector>
#include <cstdio>
#include "ZornClientFailureStore261.h"
#include "legacy-store.h"
template<class T> static std::vector<uint64_t> fill(T&s,unsigned n,bool failure,bool rejection){
 std::vector<uint64_t> ids;
 for(unsigned i=0;i<n;++i){auto id=s.bind(i+1,10,10);assert(id);ids.push_back(id);assert(s.begin(i+1,id,100+i,1,false));
  if(rejection&&i==0)s.noteThread(100+i,10,0xe00002c7u,ZornFailureReject261,0,0,0);
  if(failure&&i+1==n)s.noteThread(100+i,121,0xe00002cau,ZornFailureBackend261,15,0,0);
  s.end(id,100+i);assert(s.begin(i+1,id,100+i,18,true));s.end(id,100+i);s.finish(id,failure&&i+1==n?0xe00002cau:0);
 }return ids;
}
int main(){
 {LegacyStore old;auto ids=fill(old,4,false,true);std::set<uint64_t> seen;for(unsigned f=0;f<128;++f){ZornClientFailure261 r{};assert(old.snapshot(f,r));seen.insert(r.id);}assert(seen.size()==1&&*seen.begin()==ids[0]);}
 unsigned cases=0;
 for(unsigned count:{1u,2u,3u,4u,6u,9u,16u,63u,64u})for(unsigned mode=0;mode<4;++mode){
  ZornClientFailureStore261 s;const bool failure=mode&1,rejection=mode&2;auto ids=fill(s,count,failure,rejection);std::set<uint64_t> census,all;
  for(unsigned f=0;f<3*count+3;++f){ZornClientFailure261 r{};assert(s.snapshot(f,r));assert(r.id&&r.records==count&&!r.recycled&&!r.dropped);assert((r.flags&ZornFailureClosed261)&&!(r.flags&ZornFailureScope261)&&r.closeStage==16);
   all.insert(r.id);if(f%3==2){assert(r.id==ids[(f/3)%count]);census.insert(r.id);}
   if(f%3==0&&failure)assert(r.failure.sequence&&r.failure.raw==0xe00002cau);
   if(f%3==1&&rejection)assert(r.reject.sequence&&r.reject.raw==0xe00002c7u);
   if(r.id==ids.back()&&failure)assert(r.flags&ZornFailureCloseFailed261);else assert(!(r.flags&ZornFailureCloseFailed261));
  }assert(census.size()==count&&all.size()==count);++cases;
 }
 puts("PASS268 legacy sticky-reject starvation reproduced;all1..64clients reached,priority failure/reject snapshots and raw failed-close status retained,modulo3/6/9/63 aliasing excluded");
}
''';f=O/'actual-scheduling.cpp';f.write_text(code);env=os.environ|dict(ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0',TSAN_OPTIONS='symbolize=0:halt_on_error=1');commands=[]
for args in [['/usr/bin/clang++','-std=c++17','-O1','-fsanitize='+a.sanitizer,'-I'+str(S),str(f),'-o',str(O/'check')],[str(O/'check')]]:
 r=subprocess.run(args,capture_output=True,text=True,timeout=120,env=env);commands.append(dict(arguments=args,exit=r.returncode,stdout=r.stdout,stderr=r.stderr));(O/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');assert not r.returncode,r.stderr
pin=lambda p:dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest());(O/'result.json').write_text(json.dumps(dict(passed=True,sanitizer=a.sanitizer,test_tool=pin(Path(__file__).resolve()),actual_current_header=pin(current),actual_parent_header=pin(old),legacy_starvation_reproduced=True,all_clients_nonstarving_census=True,failure_and_reject_reserved_slots_preserved=True,failed_close_retained=True,scope='Actual CPU store only;not GPU emulation or hardware/client-lifetime acceptance',phone_access=False,commands=commands),indent=2)+'\n');print(r.stdout.strip())

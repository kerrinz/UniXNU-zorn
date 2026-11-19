from pathlib import Path
import json,subprocess,os,hashlib
import argparse
p=argparse.ArgumentParser();p.add_argument('--source-root',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();S=a.source_root.resolve();O=a.out.resolve();O.mkdir();ufs=(S/'ZornUfsOwner26.cpp').read_text();a=ufs.index('extern "C" unsigned zorn26_cdc_interval262(');z=ufs.index('\n}',a)+2;period=ufs[a:z];cdc=(S/'ZornUsbCdc26.c').read_text();a=cdc.index('            const unsigned interval262=');z=cdc.index('            if(next && stream.frames<38',a);clamp=cdc[a:z];limit='clock_interval_to_deadline(next?285:120,NSEC_PER_SEC,&deadline);';assert cdc.count(limit)==1;step='clock_interval_to_deadline(interval262,NSEC_PER_SEC,&next_frame);';assert cdc.count(step)==1
prefix=r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include "ZornProgressGate203.h"
#include "ZornCdcStream201.h"
#include "ZornPanicPacket236.h"
struct Progress {unsigned state=0,result=0;ZornProgressGate203 gate{};};
static Progress zornProgress201;static ZornProgressGate203 zornCallbackGate222;
static uint64_t nowTick;
constexpr uint64_t NSEC_PER_SEC=1000000000ULL;
static void clock_interval_to_deadline(unsigned seconds,uint64_t scale,uint64_t *out){assert(scale==NSEC_PER_SEC);*out=nowTick+uint64_t(seconds)*1000;}
'''
wrappers='''
static unsigned expedite(void *context,uint64_t &next_frame){bool next=true;
'''+clamp+'''return interval262;}
static uint64_t duration(bool next){uint64_t deadline=0;
'''+limit+'''return deadline-nowTick;}
static uint64_t schedule(unsigned interval262){uint64_t next_frame=0;
'''+step+'''return next_frame;}
'''
main=r'''
static unsigned calls;
static unsigned producer(void *,char *bytes,unsigned cap,unsigned completed){assert(completed==calls++);memset(bytes,'x',cap);return cap;}
int main(){
 auto &p=zornProgress201;assert(zorn26_cdc_interval262(nullptr)==3);assert(zorn26_cdc_interval262((void*)1)==3);
 p.state=2;p.result=88;p.gate={6,6,0};assert(zorn26_cdc_interval262(&p)==3);
 p.state=3;p.result=87;assert(zorn26_cdc_interval262(&p)==3);
 p.result=88;assert(zorn26_cdc_interval262(&p)==9);
 p.gate.acknowledged=5;assert(zorn26_cdc_interval262(&p)==3);p.gate.acknowledged=6;
 p.gate.failed=1;assert(zorn26_cdc_interval262(&p)==3);p.gate.failed=0;
 zornCallbackGate222={1,0,0};assert(zorn26_cdc_interval262(&p)==3);zornCallbackGate222={0,0,1};assert(zorn26_cdc_interval262(&p)==3);zornCallbackGate222={};
 assert(duration(false)==120000&&duration(true)==285000&&duration(true)<300000);
 uint64_t next_frame=9000;nowTick=1;zornCallbackGate222={1,0,0};assert(expedite(&p,next_frame)==3&&next_frame==3001);
 nowTick=3001;next_frame=schedule(expedite(&p,next_frame));assert(next_frame==6001);
 nowTick=6001;zornCallbackGate222.acknowledged=1;assert(zorn26_cdc_interval262(&p)==9);assert(nowTick-1<10000); // both delivered observations before unchanged10s gate budget
 next_frame=6001;assert(expedite(&p,next_frame)==9&&next_frame==6001); // do not delay an already earlier transfer
 ZornCdcStream201 stream{};for(unsigned i=0;i<39;++i){assert(zorn_cdc_next201(&stream,true,false,stream.length,producer,nullptr)==1);const unsigned old=calls;assert(zorn_cdc_next201(&stream,true,true,stream.length,producer,nullptr)==0&&calls==old);}
 assert(stream.frames==39&&stream.total==119808&&calls==39);assert(zorn_cdc_next201(&stream,true,false,stream.length,producer,nullptr)==0);
 assert(!zorn_panic_budget236(stream.frames,stream.total,ZornPanicCapacity236));assert(zorn_panic_budget236(38,38*3072,ZornPanicCapacity236));assert(stream.total+ZornPanicCapacity236==ZornPanicWireLimit236);
 puts("PASS262 actual owner cadence and USB deadline snippets:unknown/startup/failure/pending stay3s,completed idle9s,new gate expedites,legacy120s/progress285s,original39-total-frame/529408B;262 caps normal frames38 to reserve the terminal frame");
}
'''
f=O/'actual-cadence.cpp';f.write_text(prefix+period+wrappers+main);args=['/usr/bin/clang++','-std=c++17','-O1','-fsanitize=address,undefined','-I'+str(S),str(f),'-o',str(O/'check')];r=subprocess.run(args,capture_output=True);(O/'compile.json').write_text(json.dumps(dict(arguments=args,exit=r.returncode,stderr=r.stderr.decode()),indent=2)+'\n');assert r.returncode==0,r.stderr.decode();r=subprocess.run([str(O/'check')],capture_output=True,env=os.environ|{'ASAN_OPTIONS':'symbolize=0','UBSAN_OPTIONS':'symbolize=0:print_stacktrace=0'});assert not r.returncode,r.stderr.decode();pin=lambda p:dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest());(O/'result.json').write_text(json.dumps(dict(passed=True,actual_sources=[pin(S/n) for n in ['ZornUfsOwner26.cpp','ZornUsbCdc26.c','ZornCdcStream201.h','ZornProgressGate203.h','ZornPanicPacket236.h']],tool=pin(Path(__file__)),XNU_clock_owner_and_DMA_are_explicit_host_boundaries=True,ASan_UBSan=True,original_byte_and_frame_and_panic_budgets_preserved=True,normal_frame_cap=38,total_frame_cap_with_terminal=39,terminal_refusal_at39_normal_frames_tested=True,real_device_timing_or_USB_qualified=False,phone_access=False,stdout=r.stdout.decode()),indent=2)+'\n');print(r.stdout.decode())

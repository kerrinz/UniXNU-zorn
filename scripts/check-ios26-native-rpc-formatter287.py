#!/usr/bin/env python3
"""Compile the actual frontend row formatter and native block on host fixtures."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from inspect_ios26_scalar_timing287 import inspect_native_rows

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir();source=a.source/'NativeBridgeMetalFrontend.mm';text=source.read_text()
    start=text.index('extern "C" size_t native_bridge_metal_telemetry(char *out,size_t size) {')
    r=text.index(' auto row=',start);end=text.index(' auto ms=',r);row=text[r:end]
    b=text.index(' {\n  uint64_t nc[ZornDarwinCallCost287::Words]',start);end=text.index(' row("N no-copy',b);block=text[b:end]
    prefix=r'''
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <cassert>
#include "ZornDarwinCallCost287.h"
static unsigned mode;
static bool sample(uint64_t *out,uint32_t words) {
 assert(words==96);ZornDarwinCallCost287 actual;
 if(mode==2){actual.flags=actual.Saturated;for(unsigned i=1;i<18;++i)actual.rows[i]={UINT32_MAX,UINT64_MAX,UINT64_MAX,0,0};}
 if(mode==3){actual.flags=actual.Lost;actual.dropped=1;}
 return actual.snapshot(out,words,1000);
}
int main(int argc,char **argv) {
 assert(argc==2);mode=unsigned(atoi(argv[1]));
 bool (*callCost287)(uint64_t *,uint32_t)=mode?sample:nullptr;
 using ull=unsigned long long;char bytes[6144];char *out=bytes;size_t size=sizeof bytes,at=0;out[0]=0;
'''
    suffix='\n assert(at<sizeof bytes);assert(fwrite(out,1,at,stdout)==at);return 0;\n}\n'
    generated=a.out/'actual-rpc-formatter.cpp';generated.write_text(prefix+row+block+suffix)
    exe=a.out/'actual-rpc-formatter';args=['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(a.source),str(generated),'-o',str(exe)]
    env=os.environ|dict(ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0')
    build=subprocess.run(args,capture_output=True,env=env,timeout=120);(a.out/'compile.stderr').write_bytes(build.stderr);assert not build.returncode,build.stderr.decode()
    checks=[]
    for mode in range(4):
        r=subprocess.run([str(exe),str(mode)],capture_output=True,env=env,timeout=30);assert not r.returncode,r.stderr.decode();(a.out/(str(mode)+'.SYNTHETIC.txt')).write_bytes(r.stdout)
        lines=r.stdout.decode().splitlines();assert all(len(s)<=90 for s in lines)
        decoded=inspect_native_rows(lines)
        assert decoded['available']==bool(mode) and decoded['complete']==(mode==1)
        if mode==2:assert decoded['methods']['17']['count']==0xffffffff and decoded['methods']['17']['total_us']==(2**64-1)//1000
        if mode==3:assert decoded['flags']==4 and decoded['dropped']==1
        checks.append(['Absent export is unavailable,not zero success','Complete fixed18-method scalar snapshot roundtrips','Saturated maximum counters fit actual90-column rows and remain unqualified','Observation loss remains explicit'][mode])
    pin=lambda p:dict(path=str(Path(p).resolve()),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,source=pin(source),header=pin(a.source/'ZornDarwinCallCost287.h'),decoder=pin(Path(__file__).with_name('inspect_ios26_scalar_timing287.py')),test_tool=pin(__file__),checks=checks,arguments=args,actual_frontend_formatter_and_RPC_block_executed=True,export_and_counter_values_explicit_host_fixtures=True,phone_access=False,performance_measured=False),indent=2)+'\n')
    print('PASS287 actual frontend formatter/private scalar wire;ASan/UBSan;host only')

if __name__=='__main__':main()

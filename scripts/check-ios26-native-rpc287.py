#!/usr/bin/env python3
"""Execute the actual selected Turnip call and counter with explicit host I/O."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path

PREFIX=r'''
#include <IOKit/IOReturn.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <assert.h>
#include <atomic>
#include <thread>
#include <vector>
#include "NativeAdrenoABI.h"
static int64_t host_now=100;
static int64_t os_time_get_nano(){host_now+=10;return host_now;}
static unsigned calls=0;static kern_return_t answer=0;
static uint32_t last_connection,last_selector;
static std::vector<uint8_t> last_input;
static size_t last_output_capacity=0;
static kern_return_t host_call(uint32_t connection,uint32_t selector,
 const void *input,size_t bytes,void *output,size_t *output_bytes) {
 ++calls;last_connection=connection;last_selector=selector;
 last_input.clear();if(bytes)last_input.assign((const uint8_t*)input,(const uint8_t*)input+bytes);
 last_output_capacity=output_bytes?*output_bytes:0;
 if(output_bytes){assert(output);memset(output,0x5a,*output_bytes);*output_bytes=0;}
 return answer;
}
#define IOConnectCallStructMethod host_call
#define DW_TUNNEL_MAGIC 0x4e544e4cu
static struct {uint32_t conn=19;bool tunnel=false;uint32_t selector=7;} dw;
'''

MAIN=r'''
int main() {
 static_assert(sizeof(NativeAdrenoAbiSubmit)==416 && sizeof(NativeAdrenoAbiSubmitBatch)==3104,"actual ABI1");
 uint64_t out[96]={};uint8_t data[32],reply[16];memset(data,0xa6,sizeof data);
 assert(dw_call(NativeAdrenoMethodBoMap,data,sizeof data,reply,sizeof reply)==0);
 assert(calls==1 && last_connection==19 && last_selector==NativeAdrenoMethodBoMap);
 assert(last_input==std::vector<uint8_t>(data,data+sizeof data) && last_output_capacity==sizeof reply);
 for(auto b:reply)assert(b==0x5a);
 dw.tunnel=true;
 for(kern_return_t raw:{kern_return_t(0),kern_return_t(kIOReturnTimeout),kern_return_t(kIOReturnNoResources)}) {
  answer=raw;assert(dw_call(NativeAdrenoMethodWaitFence,data,sizeof data,nullptr,0)==raw);
  assert(last_selector==7 && last_input.size()==8+sizeof data && last_output_capacity==0);
  uint32_t h[2];memcpy(h,last_input.data(),8);
  assert(h[0]==DW_TUNNEL_MAGIC && h[1]==NativeAdrenoMethodWaitFence);
  assert(!memcmp(last_input.data()+8,data,sizeof data));
 }
 const unsigned before=calls;
 assert(dw_call(NativeAdrenoMethodSubmitBatch,data,sizeof(NativeAdrenoAbiSubmitBatch)+1,nullptr,0)==kern_return_t(kIOReturnBadArgument));
 assert(calls==before);
 assert(tu_darwin_call_cost287(out,96));assert(out[0]==287 && out[1]==18 && out[2]==0 && out[3]==0 && out[4]>0 && out[5]==0);
 auto row=[&](unsigned n){return out+6+5*n;};
 assert(row(3)[0]==1 && row(3)[1]==10 && row(3)[2]==10 && row(3)[3]==0 && row(3)[4]==0);
 assert(row(6)[0]==3 && row(6)[1]==30 && row(6)[2]==10 && row(6)[3]==1 && row(6)[4]==1);
 assert(row(17)[0]==1 && row(17)[3]==1 && row(17)[4]==0);
 memset(out,0xcc,sizeof out);uint64_t preserved[96];memcpy(preserved,out,sizeof out);
 assert(!tu_darwin_call_cost287(out,95) && !tu_darwin_call_cost287(nullptr,96));
 assert(!memcmp(out,preserved,sizeof out));
 ZornDarwinCallCost287 clock;clock.record(5,100,50,false,false);
 assert(clock.snapshot(out,96,200) && out[2]==clock.Clock && row(5)[0]==1 && row(5)[1]==0);
 assert(!clock.snapshot(out,96,-1));
 ZornDarwinCallCost287 saturation;saturation.rows[5]={UINT32_MAX,UINT64_MAX-5,0,UINT32_MAX,UINT32_MAX};
 saturation.record(5,0,10,true,true);assert(saturation.snapshot(out,96,200));
 assert(out[2]&saturation.Saturated);assert(row(5)[0]==UINT32_MAX && row(5)[1]==UINT64_MAX && row(5)[3]==UINT32_MAX && row(5)[4]==UINT32_MAX);
 ZornDarwinCallCost287 unknown;unknown.record(18,0,10,false,false);assert(unknown.snapshot(out,96,200));assert(out[2]&unknown.UnknownMethod);assert(row(0)[0]==1);
 ZornDarwinCallCost287 busy;assert(busy.take());busy.record(6,0,10,false,false);
 assert(!busy.snapshot(out,96,200));busy.unlock();assert(busy.snapshot(out,96,200));assert(out[2]==busy.Lost && out[3]==1 && row(6)[0]==0);
 ZornDarwinCallCost287 concurrent;std::vector<std::thread> threads;
 for(unsigned i=0;i<8;++i)threads.emplace_back([&](){for(unsigned n=0;n<10000;++n)concurrent.record(5,0,100,false,false);});
 for(auto &t:threads)t.join();assert(concurrent.snapshot(out,96,200));
 assert(row(5)[0]+out[3]==80000 && row(5)[1]==row(5)[0]*100);
 assert((out[2]&concurrent.Lost)!=0 || out[3]==0);
 assert(!out[3] || (out[2]&concurrent.Lost));
 return 0;
}
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesa',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--sanitizer',choices=['address,undefined','thread'],required=True)
    a=p.parse_args();a.out.mkdir();source=a.mesa/'src/freedreno/vulkan/tu_knl_darwin.cc'
    text=source.read_text();start=text.index('#include "ZornDarwinCallCost287.h"')
    end=text.index('\n/* Finds an admitted selector:',start)
    actual=text[start:end];assert actual.count('IOConnectCallStructMethod(')==2
    f=a.out/'actual-native-call.cpp';f.write_text(PREFIX+actual+MAIN)
    executable=a.out/'actual-native-call'
    args=['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-g','-pthread',
          '-fsanitize='+a.sanitizer,'-I'+str(a.mesa/'k80-abi280'),str(f),'-o',str(executable)]
    env=os.environ|dict(ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0',TSAN_OPTIONS='symbolize=0:halt_on_error=1')
    for name,command in [('compile',args),('run',[str(executable)])]:
        result=subprocess.run(command,capture_output=True,env=env,timeout=120)
        (a.out/(name+'.stdout')).write_bytes(result.stdout);(a.out/(name+'.stderr')).write_bytes(result.stderr)
        assert not result.returncode,(name,result.stderr.decode(errors='replace')[-4000:])
    pin=lambda p:dict(path=str(Path(p).resolve()),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
    result=dict(passed=True,source=pin(source),header=pin(a.mesa/'k80-abi280/ZornDarwinCallCost287.h'),ABI=pin(a.mesa/'k80-abi280/NativeAdrenoABI.h'),test_tool=pin(__file__),sanitizer=a.sanitizer,arguments=args,
        checks=['Actual direct/tunnel input and output bytes,selector,one real boundary call and raw return preserved',
                'Success/timeout/error separate;oversized tunnel rejects before boundary',
                'Actual ABI1 sizes and96-word schema;bad snapshot bounds preserve output',
                'Reversed clock,saturation,unknown method and forced contention remain explicit',
                '80000 concurrent records account for observed calls plus explicit loss'],
        fake_clock_and_IOKit_boundary_only=True,production_RPC_and_counter_executed=True,phone_access=False,hardware_or_performance_qualified=False)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS287 actual native call/counter: '+a.sanitizer+';host boundaries only')

if __name__=='__main__':main()

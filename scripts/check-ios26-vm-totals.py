from pathlib import Path
import argparse,json,subprocess,hashlib,os
p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sanitizer',choices=['address,undefined','thread'],default='address,undefined');args=p.parse_args();S=args.source_root.resolve();O=args.out.resolve();pin=lambda p:dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest());save=lambda p,d:Path(p).write_text(json.dumps(d,indent=2)+'\n')
# Compile the actual cumulative getter and PhaseClock.done;clock and threading are CPU fixtures.
source=(S/'direct-runtime/ZornGen7DirectVm26.cpp').read_text();a=source.index('extern "C" void zorn26_vm_completed_totals264');z=source.index('\n}',a)+2;getter=source[a:z];a=source.index('struct PhaseClock {');z=source.index('\n};',a)+3;clock=source[a:z]
prefix='''#include <cstdint>
#include <cassert>
#include <thread>
#include <atomic>
#include <cstdio>
volatile uint64_t zorn_direct_vm_phase_us[2][8]{};
uint64_t zorn_direct_vm_phase_max_us[2][6]{};
uint64_t zorn_direct_vm_now_us(){return 0;} // explicit clock fixture;no maximum-field updates during this counter-only race
'''
main='''int main(){zorn26_vm_completed_totals264(nullptr);uint64_t out[4]{};zorn26_vm_completed_totals264(out);for(auto v:out)assert(!v);
 std::atomic<unsigned> finished{0};std::thread workers[4];for(unsigned i=0;i<4;++i)workers[i]=std::thread([&,i]{for(unsigned n=0;n<10000;++n){PhaseClock c;c.done(i&1,16384);}++finished;});
 uint64_t previous[4]{};while(finished.load()<4){zorn26_vm_completed_totals264(out);for(unsigned i=0;i<4;++i){assert(out[i]>=previous[i]);previous[i]=out[i];}}
 for(auto &w:workers)w.join();zorn26_vm_completed_totals264(out);assert(out[0]==20000&&out[1]==20000&&out[2]==327680000&&out[3]==327680000);puts("PASS264 actual successful map/unmap atomic counters and getter;40000CPU updates,not a live-PTE or hardware oracle");}
'''
def run(san):
 o=O;o.mkdir();f=o/'actual-counters.cpp';f.write_text(prefix+getter+'\n'+clock+'\n'+main);a=['/usr/bin/clang++','-std=c++17','-O1','-pthread','-fsanitize='+san,str(f),'-o',str(o/'check')];r=subprocess.run(a,capture_output=True,text=True);save(o/'compile.json',dict(arguments=a,exit=r.returncode,stderr=r.stderr));assert not r.returncode,r.stderr;r=subprocess.run([str(o/'check')],capture_output=True,text=True,env=os.environ|{'ASAN_OPTIONS':'symbolize=0','UBSAN_OPTIONS':'symbolize=0:print_stacktrace=0','TSAN_OPTIONS':'symbolize=0:halt_on_error=1'});assert not r.returncode,r.stderr;save(o/'result.json',dict(passed=True,tool=pin(__file__),actual_source=pin(S/'direct-runtime/ZornGen7DirectVm26.cpp'),actual_done_and_getter_extracted=True,sanitizer=san,independent_cumulative_fields_not_coherent_range_snapshot=True,clock_is_explicit_zero_host_fixture=True,hardware_qualified=False,stdout=r.stdout));return r.stdout
print(run(args.sanitizer))

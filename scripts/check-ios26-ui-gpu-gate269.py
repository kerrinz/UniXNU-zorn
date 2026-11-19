#!/usr/bin/env python3
"""Run actual synthetic-scene admission with the real CPU client/journal stores."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
TEST=r'''
#include "ZornClientFailureStore261.h"
#include "ZornJournalStore248.h"
#include <cassert>
#include <cstring>
#include <cstdio>
#include <thread>
#include <vector>
#include <atomic>
struct Gate{unsigned failed=0;};
static struct {unsigned state=3,result=88;Gate gate;} zornProgress201;
static Gate zornCallbackGate222;
static unsigned known[32],fault=0;static ZornClientFailureStore261 clients;static ZornJournalStore248 journal;
extern "C" void zorn26_native_known_image_observation(unsigned (&out)[32]){memcpy(out,known,sizeof(known));}
extern "C" int zorn26_journal_snapshot248(uint32_t at,void *buf,uint32_t cap,ZornJournalSnapshot248 *out){assert(at==0&&buf&&cap==1&&out);return journal.snapshot(at,buf,cap,*out);}
extern "C" int zorn_failure_snapshot261(uint32_t seq,ZornClientFailure261 *out){assert(seq>=2&&seq<=11&&seq%3==2);return clients.snapshot(fault==1?2:seq,*out);}
#include "ZornUiSceneGpuGate269.inc"
void setup(unsigned fixture=0){fault=0;clients={};journal={};zornProgress201={3,88,{}};zornCallbackGate222={};memset(known,0,sizeof(known));known[1]=6;known[2]=63;known[4]=known[5]=101;known[6]=known[7]=2;known[15]=0xe843b26a;known[16]=UINT32_MAX;known[19]=known[20]=2;known[21]=0x71000000;known[22]=1;known[24]=127;
 unsigned count=fixture==1?3:fixture==2?5:4;
 for(unsigned i=0;i<count;++i){uintptr_t owner=100+i,current=200+i;auto id=clients.bind(owner,fixture==3&&i==2?11:10,10);assert(id);if(!(fixture==4&&i==2)){assert(clients.begin(owner,id,current,0,false));clients.end(id,current);}if(fixture==5&&i==2){assert(clients.begin(owner,id,current,0,false));continue;}if(fixture==6&&i==2)clients.noteClient(owner,id,100,7,ZornFailureBackend261,0,0,0);if(fixture==7&&i==2)clients.noteClient(owner,id,10,0xe00002c7,ZornFailureReject261,0,0,0);if(!(fixture==8&&i==2)){assert(clients.begin(owner,id,current,0,true));clients.end(id,current);clients.finish(id,fixture==9&&i==2?7:0);}}
 if(fixture==10){assert(!clients.begin(0,1,123,0,false));}
 ZornJournalTicket248 ticket{};assert(journal.begin(10,10,16,0,ticket));memset(ticket.target,'x',ticket.bytes);if(fixture!=11)journal.finish(ticket.index,0);if(fixture!=12)journal.exit(10,10,fixture==13?7:0);if(fixture==14)journal.lose(ZornJournalCopyLost248);
}
int main(){setup();assert(zorn26_ui_scene_gpu_ready269());unsigned refused=0;
 for(unsigned f=1;f<=14;++f){setup(f);const bool ok=zorn26_ui_scene_gpu_ready269();if(f==7)assert(ok);else{assert(!ok);++refused;}}
 for(auto pair:std::vector<std::pair<unsigned,unsigned>>{{0,1},{1,5},{2,62},{3,1},{4,100},{6,0},{7,1},{8,1},{9,1},{10,1},{11,1},{12,1},{15,0},{16,0},{17,1},{18,1},{19,1},{21,0x71800000},{22,3},{23,1},{24,126},{31,1}}){setup();known[pair.first]=pair.second;assert(!zorn26_ui_scene_gpu_ready269());++refused;}
 setup();zornProgress201.state=2;assert(!zorn26_ui_scene_gpu_ready269());++refused;
 setup();zornProgress201.result=87;assert(!zorn26_ui_scene_gpu_ready269());++refused;
 setup();zornProgress201.gate.failed=1;assert(!zorn26_ui_scene_gpu_ready269());++refused;
 setup();zornCallbackGate222.failed=1;assert(!zorn26_ui_scene_gpu_ready269());++refused;
 setup();fault=1;assert(!zorn26_ui_scene_gpu_ready269());++refused;
 setup();std::atomic<unsigned> complete{0};std::vector<std::thread> threads;for(unsigned i=0;i<8;++i)threads.emplace_back([&]{for(unsigned j=0;j<200;++j)if(zorn26_ui_scene_gpu_ready269())++complete;});for(auto &t:threads)t.join();assert(complete>0);assert(zorn26_ui_scene_gpu_ready269());
 puts("PASS actual269 source admission with real Store261/Journal248:closed4task-bound clients and detached exit,sticky capability reject allowed;initial-task/journal/close/failure/loss/pending/duplicate checks;1600concurrent CPU snapshots may conservatively refuse busy locks");printf("refused=%u completed_concurrent=%u;no DMA stop or hardware authority\n",refused,complete.load());}
'''
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sanitizer',choices=['address-undefined','thread'],required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);f=a.out/'actual-gate.cpp';f.write_text(TEST);exe=a.out/'actual-gate';san='address,undefined' if a.sanitizer=='address-undefined' else 'thread';args=['xcrun','clang++','-std=c++17','-O1','-g','-pthread','-fno-omit-frame-pointer','-fsanitize='+san,'-I'+str(a.source),str(f),'-o',str(exe)];env=os.environ|dict(ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0',TSAN_OPTIONS='symbolize=0:halt_on_error=1')
    r=subprocess.run(args,capture_output=True,env=env,timeout=120);(a.out/'compile.stderr').write_bytes(r.stderr);assert not r.returncode,r.stderr.decode();r=subprocess.run([str(exe)],capture_output=True,env=env,timeout=120);(a.out/'run.stdout').write_bytes(r.stdout);(a.out/'run.stderr').write_bytes(r.stderr);assert not r.returncode,r.stderr.decode();pin=lambda f:dict(path=str(f.resolve()),sha256=hashlib.sha256(f.read_bytes()).hexdigest());result=dict(passed=True,sanitizer=a.sanitizer,sources=[pin(a.source/n) for n in ['ZornUiSceneGpuGate269.inc','ZornClientFailureStore261.h','ZornClientFailure261.h','ZornJournalStore248.h','ZornApplicationJournal248.h']],test=pin(f),executable=pin(exe),arguments=args,stdout=r.stdout.decode(),boundaries='CPU diagnostic snapshot fixture only;actual Store261 and Journal248 locking/latches/snapshots and source UI admission. No new GPU operation or resource release.',phone_access=False,actual_HID_dispatch_or_delivery_qualified=False);(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(r.stdout.decode().strip())
if __name__=='__main__':main()

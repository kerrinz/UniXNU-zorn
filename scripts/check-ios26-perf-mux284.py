#!/usr/bin/env python3
"""Reproduce late-cost starvation on283 and exercise the actual284 mux fix."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path

TEST=r'''
#include "ZornSerialShot270.h"
#include "ZornUiMenuWire278.h"
#include <cassert>
#include <cstdio>
#include <vector>
static unsigned calls;
unsigned normal(void*,char*,unsigned,unsigned){++calls;return 2;}
struct Ui {
 bool available=false;uint32_t words[304]{};
 bool ready()const{return available;}
 unsigned packet(char*out,unsigned cap,const uint8_t(&tag)[16])const{return ZornUiMenuWire278::packet(out,cap,words,tag);}
};
int main(){
 ZornSerialMux270 m;m.normal=m.wire=30;ZornSerialRoi270 shot;Ui ui;
 char out[3072]{};uint8_t tag[16]{};assert(shot.request());
 assert(m.next(nullptr,out,sizeof(out),30,normal,shot,ui,tag,true)==ZORN_CDC_PENDING270);
 assert(!m.sentUi&&m.wire==30&&!m.offset&&!calls);
 ui.available=true;
 const unsigned n=m.next(nullptr,out,sizeof(out),30,normal,shot,ui,tag,true);
 if(n==ZORN_CDC_PENDING270){puts("reproduced:completed cost blocked by unavailable ROI");return 42;}
 assert(n==1248&&!memcmp(out,"K80PF278",8)&&m.sentUi&&m.wire==31&&!m.offset&&!calls);
 auto saved=m;
 for(unsigned i=0;i<100;++i){
  assert(m.next(nullptr,out,sizeof(out),31,normal,shot,ui,tag,true)==ZORN_CDC_PENDING270);
  assert(m.wire==saved.wire&&m.normal==saved.normal&&m.offset==saved.offset&&m.sentUi==saved.sentUi&&!calls);
 }
 // Preserve the original missing-ROI wait after the independent cost frame.
 constexpr unsigned W=384,H=832;std::vector<uint32_t> pixels(W*H,0xff00ff00);
 uint32_t record[16]={2,64,4,2,4,4,1,3,1,1,1,63,64,1125,2436,4};
 assert(shot.capture(pixels.data(),W,H,W*4,pixels.size()*4,record));
 unsigned chunks=0;
 while(m.offset<shot.Bytes){
  unsigned size=m.next(nullptr,out,sizeof(out),m.wire,normal,shot,ui,tag,true);
  assert(size>shot.PacketHeader&&size<=3072&&!memcmp(out,"K80SH270",8));++chunks;
 }
 assert(chunks==7&&m.wire==38&&m.normal==30&&!calls);
 assert(!m.next(nullptr,out,sizeof(out),m.wire,normal,shot,ui,tag,true));
 ZornSerialMux270 small;small.normal=small.wire=30;
 assert(!small.next(nullptr,out,1247,30,normal,ZornSerialRoi270{},ui,tag,true));
 assert(!small.sentUi&&small.wire==30&&!calls);
 assert(!small.next(nullptr,out,sizeof(out),29,normal,shot,ui,tag,true));
 puts("PASS independent completed cost;100 missing-ROI waits;7real ROI chunks;38frame cap;small-buffer and stale-completion refusal");
}
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--legacy',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sanitizer',choices=['address,undefined','thread'],required=True);a=p.parse_args();a.out.mkdir();runs=[]
    env=os.environ|dict(ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0',TSAN_OPTIONS='symbolize=0:halt_on_error=1')
    for name,source,expected in [('legacy',a.legacy,42),('current',a.source,0)]:
        f=a.out/(name+'.cpp');f.write_text(TEST);exe=a.out/name;args=['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-g','-pthread','-fsanitize='+a.sanitizer,'-I'+str(source),str(f),'-o',str(exe)]
        build=subprocess.run(args,env=env,capture_output=True,timeout=120);(a.out/(name+'.compile.stderr')).write_bytes(build.stderr);assert build.returncode==0,build.stderr.decode()
        run=subprocess.run([str(exe)],env=env,capture_output=True,timeout=60);(a.out/(name+'.stdout')).write_bytes(run.stdout);(a.out/(name+'.stderr')).write_bytes(run.stderr);assert run.returncode==expected,run.stderr.decode();runs.append(dict(arguments=args,exit=run.returncode,header_sha256=hashlib.sha256((source/'ZornSerialShot270.h').read_bytes()).hexdigest()))
    pin=lambda p:dict(path=str(Path(p).resolve()),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,checks=runs,test_tool=pin(__file__),sanitizer=a.sanitizer,legacy_starvation_reproduced=True,actual_header_and_packet_producers_used=True,performance_improvement_proven=False,phone_access=False),indent=2)+'\n');print('PASS284 actual late-cost starvation and independent delivery: '+a.sanitizer)
if __name__=='__main__':main()

#!/usr/bin/env python3
"""Exercise the actual bounded DSI transport against a deterministic register bus."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out/zorn/brightness"
HEADER = ROOT / "UniXNU-zorn/native/display/ZornDsiBrightness.h"
SOURCE = r'''
#include <cassert>
#include <map>
#include <vector>
#include <utility>
#include "ZornDsiBrightness.h"
struct Bus {
 std::map<unsigned,uint32_t> r;
 std::vector<std::pair<unsigned,uint32_t>> writes;
 std::vector<uint32_t> fifo;
 unsigned level=4096, delays=0, dimCommands=0;
 bool timeout=false,badResponse=false,badReadback=false;
 Bus() { r={{0,0x20080000},{4,0x1f5},{0x84,0x80000004},
    {0xa8,0x1f1f},{0x3c,0x14000000},{0x4c,4},{0x110,0x500},
    {0x0c,0x11111210},{0xb4,0x88888},{0x120,0x2343},{0x330,0x33531000}}; }
 uint32_t read(unsigned a) { return r[a]; }
 void delay(unsigned us) { delays+=us; }
 void write(unsigned a,uint32_t v) {
   // No clock, PHY, controller reset, memory-DMA pointer or unrelated writes.
   assert(a==0x110 || a==0x15c || a==0x17c || a==0x3c || a==0x4c ||
          a==0x90 || a==0x1ec || a==0x1d4);
   writes.emplace_back(a,v);
   if(a==0x110) { assert((v&0xa222aa02)==0);r[a]&=~v;return; }
   r[a]=v;
   if(a==0x1d4 && v==1)r[a]=0;
   if(a==0x15c && v==0x30006)fifo.clear();
   if(a==0x17c)fifo.push_back(v);
   if(a==0x90) {
     assert(v==1 && fifo.size()==2 && r[0x4c]==8 && r[0x3c]==0x10000000);
     if(timeout)return;
     if(fifo[0]==0x00370002) {
       assert(fifo[1]==0xa0060052);
       r[0x1d4]=(badResponse?8:4)<<16;
       r[0x6c]=0x22000000|((badReadback && dimCommands?level+1:level)<<8);
     } else {
       assert(fifo[0]==0xc0390003 && fifo[1]==0xff400051);
       ++dimCommands; level=64;
     }
     r[0x110]|=1;
   }
 }
};
int main() {
 using namespace ZornBrightness;
 {Bus b;Panel<Bus> p(b);assert(p.run(Read));assert(p.before==4096 && !p.writes && !b.dimCommands);
  assert(b.r[0x3c]==0x14000000 && b.r[0x4c]==4 && b.r[0x110]==0x500 && !b.r[0x15c]);}
 {Bus b;Panel<Bus> p(b);assert(p.run(Dim));assert(p.before==4096 && p.after==64 && p.target==64 && p.writes==1 && b.dimCommands==1);}
 for(unsigned v:{0u,15u,32u,64u}) {Bus b;b.level=v;Panel<Bus> p(b);assert(p.run(Dim));assert(p.after==v && b.dimCommands==0);}
 for(unsigned a:{0u,4u,0x84u,0xa8u,0x15cu,0x2ccu,0x330u,0x3cu}) {
   Bus b;b.r[a]^=1;Panel<Bus> p(b);assert(!p.run(Dim));assert(p.error==Handoff && b.writes.empty());
 }
 {Bus b;b.r[8]=4;Panel<Bus> p(b);assert(!p.run(Dim));assert(p.error==Busy && b.writes.empty());}
 for(unsigned a:{0x68u,0xc0u}) {Bus b;b.r[a]=1;Panel<Bus> p(b);assert(!p.run(Dim));assert(b.writes.empty());}
 {Bus b;b.timeout=true;Panel<Bus> p(b);assert(!p.run(Dim));assert(p.error==Timeout && b.delays==5000 && !b.dimCommands);
  assert(b.writes.back().first==0x90);}
 {Bus b;b.badResponse=true;Panel<Bus> p(b);assert(!p.run(Dim));assert(p.error==Response && !b.dimCommands);}
 {Bus b;b.level=0xffff;Panel<Bus> p(b);assert(!p.run(Dim));assert(p.error==Range && !b.dimCommands);}
 {Bus b;b.badReadback=true;Panel<Bus> p(b);assert(!p.run(Dim));assert(p.error==Mismatch && b.dimCommands==1);}
}
'''

OUT.mkdir(parents=True, exist_ok=True)
source = OUT / "transport-host-check.cpp"
binary = OUT / "transport-host-check"
source.write_text(SOURCE)
subprocess.run(["clang++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                "-I", str(HEADER.parent), str(source), "-o", str(binary)], check=True)
subprocess.run([str(binary)], check=True)
report = dict(passed=True, hardware_qualified=False,
              header_sha256=hashlib.sha256(HEADER.read_bytes()).hexdigest(),
              checks=["exact handoff and active lanes; zero writes on refusal",
                      "DCS 52 two-byte response, count/type/range checked",
                      "DCS 51 high-byte-first fixed 64; never brighten",
                      "transfer timeout <=5ms; no unsafe reset on timeout",
                      "only whitelisted FIFO/status registers; no IRQ enable",
                      "configuration restored; unrelated pending status preserved",
                      "readback mismatch/error refuses success"])
(OUT / "host-check.json").write_text(json.dumps(report, indent=2)+"\n")
print(json.dumps(report))

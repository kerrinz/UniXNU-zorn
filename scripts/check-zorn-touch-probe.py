#!/usr/bin/env python3
"""Fault-inject actual read-only K80 handoff logic; not a hardware qualification."""
from pathlib import Path
import hashlib
import json
import subprocess
ROOT = Path(__file__).resolve().parents[2]
HEADER = ROOT / "UniXNU-zorn/native/display/ZornTouchHandoff.h"
OUT = ROOT / "out/zorn/touch"
OUT.mkdir(parents=True, exist_ok=True)
source = r'''
#include <cassert>
#include "ZornTouchHandoff.h"
struct Bus {
 unsigned n=0,se=0,fail=0;bool halt=false,foreign=false;
 bool read(uint32_t pa,uint32_t &v) {
  assert(ZornTouch::allowed(pa));if(++n==fail)return false;
  if(pa>=0xa90000&&pa<0xa94000)++se;
  v=pa==0x1183bc?(foreign?0xffffffff:halt?0x80000000:0):0;return true;
 }
};
int main() {
 ZornTouch::Snapshot s;Bus b;
 assert(!ZornTouch::allowed(0));assert(!ZornTouch::allowed(0xf16c000));
 assert(!ZornTouch::allowed(0xa90070));assert(!ZornTouch::allowed(0xae9417c));
 assert(!ZornTouch::capture(b,s)&&b.n==32&&b.se==7&&s.reads==32);
 b={};b.halt=true;assert(ZornTouch::capture(b,s)==1&&b.n==25&&b.se==0);
 b={};b.foreign=true;assert(ZornTouch::capture(b,s)==3&&b.se==0);
 for(unsigned i=1;i<=32;++i){b={};b.fail=i;assert(ZornTouch::capture(b,s)==2&&b.n==i&&s.reads==i-1);}
}
'''
(OUT / "probe-check.cpp").write_text(source)
subprocess.run(["clang++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-O1",
                "-fsanitize=address,undefined", "-I", str(HEADER.parent),
                str(OUT / "probe-check.cpp"), "-o", str(OUT / "probe-check")], check=True, timeout=60)
subprocess.run([str(OUT / "probe-check")], check=True, timeout=30)
result = dict(passed=True, cases=35, source_sha256=hashlib.sha256(HEADER.read_bytes()).hexdigest(),
              readonly_callback_only=True, halted_engine_never_read=True, hardware_qualified=False)
(OUT / "handoff-host-check.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))

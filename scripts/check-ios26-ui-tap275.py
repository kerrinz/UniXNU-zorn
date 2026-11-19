#!/usr/bin/env python3
"""Exercise the parameterized Done272 tap path before any new device scope."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
CODE=r'''
#include "ZornUiTap275.h"
#include <cassert>
#include <vector>
#include <cstdio>
struct Backend {
 uint64_t now=0;unsigned sends=0,polls=0,fail=0,slowSend=0,losePoll=0,slowPoll=0;bool rollback=false;
 std::vector<ZornContacts::Frame> frames;
 uint64_t nowMs(){return now;}void sleepMs(unsigned n){assert(n<=250);now+=n;}
 bool ready(){++polls;if(polls==slowPoll)now+=10000;return polls!=losePoll;}
 unsigned send(const ZornContacts::Frame &f){frames.push_back(f);++sends;if(sends==slowSend)now+=10000;if(rollback&&sends==2)now=0;return sends==fail?7:0;}
};
int main(){const ZornUiTap275::Config c{16384,24576,8000,100,10000};Backend b;auto r=ZornUiTap275::run(b,c);assert(r.outcome==ZornUiScene269::Outcome::Complete&&b.now==8100&&b.sends==2&&b.polls==33&&r.attempted==1&&r.returned==1&&r.liftAttempted==1&&!r.firstRaw&&!r.liftRaw&&r.elapsedMs==100);
 const auto &f=b.frames[0];assert(f.count==1&&f.points[0].x==c.x&&f.points[0].y==c.y&&f.points[0].id==1&&f.points[0].strength==1&&!b.frames[1].count);
 for(unsigned p=1;p<=33;++p){Backend x;x.losePoll=p;r=ZornUiTap275::run(x,c);assert(r.outcome==ZornUiScene269::Outcome::NoClient&&!x.sends&&!r.attempted&&!r.liftAttempted);}
 for(unsigned p=1;p<=33;++p){Backend x;x.slowPoll=p;r=ZornUiTap275::run(x,c);assert(r.outcome==ZornUiScene269::Outcome::Deadline&&!x.sends&&!r.liftAttempted);}
 for(unsigned n=1;n<=2;++n){Backend x;x.fail=n;r=ZornUiTap275::run(x,c);assert(r.outcome==ZornUiScene269::Outcome::Dispatch&&x.sends==2&&!x.frames.back().count&&r.firstRaw==7&&r.liftAttempted==1);}
 for(unsigned n=1;n<=2;++n){Backend x;x.slowSend=n;r=ZornUiTap275::run(x,c);assert(r.outcome==ZornUiScene269::Outcome::Deadline&&x.sends==2&&!x.frames.back().count&&r.liftAttempted==1);}
 for(auto bad:std::vector<ZornUiTap275::Config>{{32768,0,0,100,1000},{0,32768,0,100,1000},{0,0,0,0,1000},{0,0,1000,100,1000},{0,0,900,100,1000},{0,0,0,1,0}}){Backend x;r=ZornUiTap275::run(x,bad);assert(r.outcome!=ZornUiScene269::Outcome::Complete&&!x.sends&&!x.polls);}
 Backend rollback;rollback.now=100;rollback.rollback=true;r=ZornUiTap275::run(rollback,c);assert(r.elapsedMs==UINT32_MAX&&r.outcome==ZornUiScene269::Outcome::Deadline&&rollback.sends==2);
 puts("PASS275 actual tap source:8000ms ready-checked gap/100ms contact/lift;33 readiness failures/33 slow predicates refuse touchdown;dispatch/slow callbacks still lift;6 invalid configs refuse before callback;clock reversal saturates and fails. No actual menu dismissal.");}
'''
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--touch-common',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);f=a.out/'tap.cpp';f.write_text(CODE);env=os.environ|dict(ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0',TSAN_OPTIONS='symbolize=0:halt_on_error=1');rows=[]
    for san in ['address,undefined','thread']:
        exe=a.out/san.replace(',','-');args=['xcrun','clang++','-std=c++17','-O1','-g','-fno-omit-frame-pointer','-fsanitize='+san,'-I'+str(a.source),'-I'+str(a.touch_common),str(f),'-o',str(exe)];r=subprocess.run(args,capture_output=True,env=env,timeout=120);(a.out/(exe.name+'-compile.stderr')).write_bytes(r.stderr);assert not r.returncode,r.stderr.decode();r=subprocess.run([str(exe)],capture_output=True,env=env,timeout=120);(a.out/(exe.name+'-run.stderr')).write_bytes(r.stderr);assert not r.returncode,r.stderr.decode();print(r.stdout.decode().strip());rows.append(dict(sanitizer=san,arguments=args,stdout=r.stdout.decode()))
    pin=lambda q:dict(path=str(q.resolve()),sha256=hashlib.sha256(q.read_bytes()).hexdigest());(a.out/'result.json').write_text(json.dumps(dict(passed=True,sources=[pin(a.source/n) for n in ['ZornUiTap275.h','ZornUiScenePlan269.h']],test_tool=pin(Path(__file__)),retained_tap_source=pin(Path(__file__).parents[1]/'native/ios26-ui272/ZornUiDonePlan272.h'),tests=rows,phone_access=False,integrated_service_or_kernel_built=False,menu_dismissal_qualified=False),indent=2)+'\n')
if __name__=='__main__':main()

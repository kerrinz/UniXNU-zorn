#!/usr/bin/env python3
"""Test actual backboardd filters;retain248 loss/copy/CRC/concurrency controls."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
PREFIX=r'''
#include "ZornApplicationObservation26.h"
#include <cassert>
#include <cstring>
#include <cerrno>
#include <cstdint>
using user_addr_t=uint64_t;using user_size_t=uint64_t;using user_ssize_t=int64_t;
struct Process{const char *name;uint64_t unique;unsigned pid;};using proc_t=Process*;
const char *proc_best_name(proc_t p){return p->name;}uint64_t proc_uniqueid(proc_t p){return p->unique;}unsigned proc_pid(proc_t p){return p->pid;}
static unsigned reserved,committed;static uint64_t base;static char bytes[512];static bool fault,refuse;
extern "C" int zorn26_application_stderr_reserve(uint64_t u,uint32_t p){assert(u==10&&p==20);++reserved;return !refuse;}
extern "C" void zorn26_application_stderr_commit(uint64_t u,const char *p,uint32_t n,int e){assert(u==10&&n<=383);assert(e==EFAULT||(!e&&!memcmp(p,bytes,n)));++committed;}
int copyin(user_addr_t p,void *out,size_t n){if(fault||p!=base||n>sizeof(bytes))return EFAULT;memcpy(out,bytes,n);return 0;}
'''
MAIN=r'''
int main(){Process p{"backboardd",10,20},old{"zorn-metal-probe193",10,20},prefix{"backboardd-extra",10,20},none{nullptr,10,20};base=reinterpret_cast<uintptr_t>(bytes);memset(bytes,'X',sizeof(bytes));
 zorn26_application_capture_stderr(&p,2,base,512,512,0,0);assert(reserved==1&&committed==1);
 for(auto *other:{&old,&prefix,&none,static_cast<proc_t>(nullptr)})zorn26_application_capture_stderr(other,2,base,9,9,0,0);
 zorn26_application_capture_stderr(&p,1,base,9,9,0,0);zorn26_application_capture_stderr(&p,2,base,9,9,1,0);zorn26_application_capture_stderr(&p,2,base,9,9,0,1);zorn26_application_capture_stderr(&p,2,base,9,8,0,0);zorn26_application_capture_stderr(&p,2,base,0,0,0,0);assert(reserved==1&&committed==1);
 fault=true;zorn26_application_capture_stderr(&p,2,base,9,9,0,0);assert(reserved==2&&committed==2);fault=false;
 zorn26_application_capture_stderr(&p,2,UINT64_MAX-1,9,9,0,0);assert(reserved==3&&committed==3);
 refuse=true;zorn26_application_capture_stderr(&p,2,base,9,9,0,0);assert(reserved==4&&committed==3);
}
'''
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);original=Path(__file__).parents[1]/'native/ios26-journal248/hostcheck.cpp'
    journal=original.read_text().replace('Process p{"zorn-metal-probe193",42,7},other{"unrelated",42,7}','Process p{"backboardd",42,7},other{"zorn-metal-probe193",42,7}');assert journal!=original.read_text()
    capture=(a.source/'ZornApplicationStderr26.inc').read_text().split('#include "ZornJournalCapture248.inc"')[0];tests=[];env=os.environ|dict(ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0',TSAN_OPTIONS='symbolize=0:halt_on_error=1')
    for name,text in [('journal',journal),('stderr',PREFIX+'\n#include <initializer_list>\n'+capture+MAIN)]:
        f=a.out/(name+'.cpp');f.write_text(text)
        for san in ['address,undefined','thread']:
            exe=a.out/(name+'-'+san.replace(',','-'));args=['xcrun','clang++','-std=c++17','-O1','-pthread','-g','-fsanitize='+san,'-I'+str(a.source),str(f),'-o',str(exe)];r=subprocess.run(args,capture_output=True,env=env,timeout=120);(a.out/(exe.name+'-compile.stderr')).write_bytes(r.stderr);assert not r.returncode,r.stderr.decode();r=subprocess.run([str(exe)],capture_output=True,env=env,timeout=120);(a.out/(exe.name+'-run.stderr')).write_bytes(r.stderr);assert not r.returncode,r.stderr.decode();tests.append(dict(test=name,sanitizer=san,arguments=args,stdout=r.stdout.decode()))
    pin=lambda p:dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest());(a.out/'result.json').write_text(json.dumps(dict(passed=True,sources=[pin(a.source/n) for n in ['ZornApplicationStderr26.inc','ZornJournalCapture248.inc','ZornJournalStore248.h','ZornApplicationJournal248.h']],retained_journal_test_base=pin(original),tests=tests,actual_selected_process='backboardd',disabled_probe_process_explicitly_rejected=True,copyin_and_process_boundaries_stubbed=True,daemon_exit_not_required_or_fabricated=True,phone_access=False),indent=2)+'\n');print('PASS271 actual backboardd stderr/journal filters,disabled probe refused,prefix/copy fault/bounds/loss/CRC/concurrency;ASan/UBSan/TSan')
if __name__=='__main__':main()

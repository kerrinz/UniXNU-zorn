#!/usr/bin/env python3
"""Compile actual syscall diagnostic filters;contrast291 and bind292 to the actual267 probe."""
import argparse,hashlib,importlib.util,json,subprocess
from pathlib import Path

def pin(p):return dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--parent-source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sanitizer',choices=['address,undefined','thread'],default='address,undefined');a=p.parse_args();S=a.source_root.resolve();P=a.parent_source.resolve();O=a.out.resolve();O.mkdir()
 spec=importlib.util.spec_from_file_location('scope291',Path(__file__).with_name('check-ios26-handover-scope291.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 bodies=[]
 for root,suffix in [(P,'_parent'),(S,'')]:
  one=m.extract((root/'ZornApplicationStderr26.inc').read_text(),'static void zorn26_application_capture_stderr(');two=m.extract((root/'ZornJournalCapture248.inc').read_text(),'static int zorn26_journal_process248(')
  bodies.append(one.replace('zorn26_application_capture_stderr(', 'zorn26_application_capture_stderr'+suffix+'(')+two.replace('zorn26_journal_process248(', 'zorn26_journal_process248'+suffix+'('))
 prefix=r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cerrno>
struct Process{const char*name;uint64_t unique;int pid;};using proc_t=Process*;using user_addr_t=uint64_t;using user_size_t=uint64_t;using user_ssize_t=int64_t;
static const char*proc_best_name(proc_t p){return p->name;}static uint64_t proc_uniqueid(proc_t p){return p->unique;}static int proc_pid(proc_t p){return p->pid;}
static unsigned reserves=0,commits=0;static bool permit=true;static uint64_t seenUnique=0;static uint32_t seenPid=0,seenBytes=0;static int seenError=0;static char seenText[384];
// Explicit host boundaries for the original kernel copyin and diagnostic buffers.
static int copyin(user_addr_t a,char*out,size_t n){memcpy(out,reinterpret_cast<const void*>(a),n);return 0;}
static bool zorn26_application_stderr_reserve(uint64_t u,uint32_t p){++reserves;seenUnique=u;seenPid=p;return permit;}
static void zorn26_application_stderr_commit(uint64_t u,const char*t,uint32_t n,int e){assert(u==seenUnique&&n<384);++commits;seenBytes=n;seenError=e;if(!e)memcpy(seenText,t,n);}
'''
 tests=r'''
int main(){unsigned controls=0;Process probe{"zorn-metal-probe193",10,10},desktop{"backboardd",11,11};char line[]="ZORN193MTL run=host-only\n";auto address=reinterpret_cast<user_addr_t>(line);
 assert(!zorn26_journal_process248_parent(&probe,2)&&zorn26_journal_process248_parent(&desktop,2));
 assert(zorn26_journal_process248(&probe,2)&&!zorn26_journal_process248(&desktop,2));
 zorn26_application_capture_stderr_parent(&probe,2,address,sizeof(line)-1,sizeof(line)-1,0,0);assert(!reserves&&!commits);
 zorn26_application_capture_stderr_parent(&desktop,2,address,sizeof(line)-1,sizeof(line)-1,0,0);assert(reserves==1&&commits==1&&seenUnique==11&&seenPid==11);reserves=commits=0;++controls;
 zorn26_application_capture_stderr(&desktop,2,address,sizeof(line)-1,sizeof(line)-1,0,0);assert(!reserves&&!commits);
 zorn26_application_capture_stderr(&probe,2,address,sizeof(line)-1,sizeof(line)-1,0,0);assert(reserves==1&&commits==1&&seenUnique==10&&seenPid==10&&seenBytes==sizeof(line)-1&&!seenError&&!memcmp(line,seenText,sizeof(line)-1));++controls;
 for(auto name:{"zorn-metal-probe193-extra","zorn-metal-probe19","backboardd","",static_cast<const char*>(nullptr)}){Process p{name,20,20};auto before=reserves;assert(!zorn26_journal_process248(&p,2));zorn26_application_capture_stderr(&p,2,address,sizeof(line)-1,sizeof(line)-1,0,0);assert(reserves==before);++controls;}
 for(unsigned fault=0;fault<7;++fault){int fd=2,error=0,flags=0;user_size_t requested=sizeof(line)-1;user_ssize_t written=requested;proc_t task=&probe;
  if(fault==0)fd=1;if(fault==1)error=1;if(fault==2)flags=1;if(fault==3)written=0;if(fault==4)written=-1;if(fault==5)--written;if(fault==6)task=nullptr;
  auto before=reserves;zorn26_application_capture_stderr(task,fd,address,requested,written,error,flags);assert(reserves==before);++controls;
 }
 assert(!zorn26_journal_process248(&probe,1)&&!zorn26_journal_process248(nullptr,2));++controls;
 permit=false;auto before=commits;zorn26_application_capture_stderr(&probe,2,address,sizeof(line)-1,sizeof(line)-1,0,0);assert(commits==before);permit=true;++controls;
 char large[512];memset(large,'x',sizeof(large));zorn26_application_capture_stderr(&probe,2,reinterpret_cast<user_addr_t>(large),512,512,0,0);assert(seenBytes==383&&!seenError);++controls;
 zorn26_application_capture_stderr(&probe,2,UINT64_MAX-1,12,12,0,0);assert(seenError==EFAULT);++controls;
 printf("PASS292 actual stderr/journal selection:%u controls;291 mismatch reproduced;exact267 probe identity selected;copyin and storage are explicit host boundaries\n",controls);return 0;
}
'''
 prefix='#include <initializer_list>\n'+prefix;cpp=prefix+'\n'.join(bodies)+tests;(O/'actual-filters.cpp').write_text(cpp);cmd=['xcrun','clang++','-std=c++17','-O1','-g','-fno-omit-frame-pointer','-fsanitize='+a.sanitizer,str(O/'actual-filters.cpp'),'-o',str(O/'actual-filters')];r=subprocess.run(cmd,capture_output=True,text=True);(O/'compile.stderr').write_text(r.stderr);assert not r.returncode,r.stderr;r=subprocess.run([str(O/'actual-filters')],capture_output=True,text=True);(O/'run.stderr').write_text(r.stderr);assert not r.returncode,r.stderr
 result=dict(passed=True,source_files=[pin(S/n) for n in ['ZornApplicationStderr26.inc','ZornJournalCapture248.inc']],parent_files=[pin(P/n) for n in ['ZornApplicationStderr26.inc','ZornJournalCapture248.inc']],test_tool=pin(__file__),sanitizer=a.sanitizer,actual_functions_compiled=True,parent_desktop_filter_mismatch_reproduced=True,exact_probe_full_name_required=True,original_syscall_and_native_GPU_results_unmodified=True,copyin_and_diagnostic_storage_explicit_host_boundaries=True,phone_access=False,hardware_qualified=False,stdout=r.stdout);(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(r.stdout)
if __name__=='__main__':main()

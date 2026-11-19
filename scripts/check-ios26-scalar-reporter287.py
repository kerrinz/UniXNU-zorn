#!/usr/bin/env python3
"""Execute actual287 bounded reporter/creator with explicit host boundaries."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path

PREFIX=r'''
#include <atomic>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <pthread.h>
#include <sys/uio.h>
#include <time.h>
#include <string>
#include <vector>
static bool enabled,published,failCreate,shortWrite;static unsigned creates,detaches,tables;
static size_t tableBytes=6143;static std::string tag(32,'a');
static std::vector<unsigned> delays;static std::vector<std::string> writes;
static void *(*entry)(void*);
static char *host_getenv(const char *key){
 if(!strcmp(key,"NATIVE_METAL_TIMING"))return enabled?const_cast<char*>("1"):nullptr;
 assert(!strcmp(key,"NATIVE_METAL_BOOT_SESSION"));return tag.empty()?nullptr:tag.data();
}
static unsigned host_sleep(unsigned s){delays.push_back(s);return 0;}
static uint64_t host_now(clockid_t){uint64_t seconds=0;for(auto n:delays)seconds+=n;return seconds*1000000000ULL;}
extern "C" size_t native_bridge_metal_telemetry(char *out,size_t cap){assert(cap==6144);++tables;memset(out,'C',tableBytes<cap?tableBytes:cap);return tableBytes;}
static ssize_t host_writev(int fd,const struct iovec *parts,int n){
 assert(fd==2&&n==2&&parts[0].iov_len<160&&parts[1].iov_len<6144);
 std::string value(static_cast<char*>(parts[0].iov_base),parts[0].iov_len);
 assert(value.find("ZORN287COUNTERS run=")==0&&value.find(" bytes="+std::to_string(parts[1].iov_len)+"\n")!=std::string::npos);
 value.append(static_cast<char*>(parts[1].iov_base),parts[1].iov_len);writes.push_back(value);
 return shortWrite?ssize_t(value.size()-1):ssize_t(value.size());
}
static int host_create(pthread_t *out,const pthread_attr_t*,void *(*f)(void*),void *arg){assert(published&&!arg);++creates;entry=f;if(failCreate)return 11;*out=reinterpret_cast<pthread_t>(uintptr_t(1));return 0;}
static int host_detach(pthread_t t){assert(reinterpret_cast<uintptr_t>(t)==1);++detaches;return 0;}
#define getenv host_getenv
#define sleep host_sleep
#define clock_gettime_nsec_np host_now
#define writev host_writev
#define pthread_create host_create
#define pthread_detach host_detach
'''
MAIN=r'''
int main(int argc,char**argv){
 assert(argc==2);const std::string mode=argv[1];
 if(mode=="disabled"){installTimingReport();assert(!creates&&!detaches);return 0;}
 enabled=published=true;failCreate=mode=="create-fails";
 installTimingReport();installTimingReport();assert(creates==1&&detaches==unsigned(!failCreate));
 if(failCreate){assert(writes.empty());return 0;}
 shortWrite=mode=="short-write";if(mode=="oversized-prefix")tag.assign(300,'a');
 if(mode=="unbound")tag.clear();if(mode=="oversized-table")tableBytes=6144;
 assert(entry==reportTiming&&entry(nullptr)==nullptr);
 if(mode=="oversized-prefix"||mode=="oversized-table"){assert(writes.empty()&&tables==1&&delays.size()==1);return 0;}
 assert(writes.size()==(shortWrite?1u:2u)&&tables==writes.size());
 assert(delays[0]==20);if(!shortWrite){assert(delays.size()==2&&delays[1]==40);assert(writes[1].find("sample=1 uptime_us=60000000")!=std::string::npos);}
 if(mode=="unbound")assert(writes[0].find("run=unbound ")!=std::string::npos);
 size_t bytes=0;for(auto &s:writes)bytes+=s.size();assert(bytes<=2*(159+6143));
 printf("PASS actual reporter %s:reports=%zu,total=%zu\n",mode.c_str(),writes.size(),bytes);
}
'''

def function(text,name):
    a=text.index(name);at=text.index('{',a);depth=0
    for i in range(at,len(text)):
        if text[i]=='{':depth+=1
        elif text[i]=='}':
            depth-=1
            if not depth:return text[a:i+1]
    raise AssertionError(name)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sanitizer',choices=['address,undefined','thread'],required=True);a=p.parse_args();a.out.mkdir()
    source=a.source/'NativeBridgeMetalFrontend.mm';text=source.read_text();report=function(text,'static void *reportTiming(void *)');creator=function(text,'static void installTimingReport()');open_body=function(text,'extern "C" id native_bridge_metal_open(');telemetry=function(text,'extern "C" size_t native_bridge_metal_telemetry(char *out,size_t size) {')
    assert '__attribute__((constructor)) static void installTimingReport' not in text
    assert open_body.index('gDevice=nmb_device_open(')<open_body.index('gDeviceObject=[cls new];')<open_body.index('if(gDeviceObject)installTimingReport();')
    assert all(s not in telemetry for s in ['dladdr(','lateUseFrame(','nmb_allocation_sites(','gWaitCallers','gUnalignedCaller'])
    assert all(s in telemetry for s in ['T pipeline','T compile','G commit-to-complete','J completed wait','J resource wait','TH '])
    f=a.out/'actual-reporter.cpp';f.write_text(PREFIX+report+'\n'+creator+'\n'+MAIN);exe=a.out/'actual-reporter';args=['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-g','-pthread','-fsanitize='+a.sanitizer,str(f),'-o',str(exe)]
    env=os.environ|dict(ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0',TSAN_OPTIONS='symbolize=0:halt_on_error=1');build=subprocess.run(args,capture_output=True,env=env,timeout=120);(a.out/'compile.stderr').write_bytes(build.stderr);assert build.returncode==0,build.stderr.decode();checks=[]
    for mode in ['disabled','normal','create-fails','short-write','oversized-prefix','unbound','oversized-table']:
        r=subprocess.run([str(exe),mode],capture_output=True,env=env,timeout=30);(a.out/(mode+'.stdout')).write_bytes(r.stdout);(a.out/(mode+'.stderr')).write_bytes(r.stderr);assert r.returncode==0,(mode,r.stderr.decode());checks.append(mode)
    pin=lambda p:dict(path=str(Path(p).resolve()),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,checks=checks,source=pin(source),test_tool=pin(__file__),actual_reporter_and_creator_executed=True,upstream_counter_bodies_retained=True,external_telemetry_thread_clock_and_IO_boundaries_stubbed=True,counters_only_reporter_has_no_stack_address_attribution=True,publication_precedes_worker=True,sanitizer=a.sanitizer,arguments=args,phone_access=False,performance_measured=False),indent=2)+'\n');print('PASS287 actual bounded scalar reporter/creator;no GPU or phone: '+a.sanitizer)
if __name__=='__main__':main()

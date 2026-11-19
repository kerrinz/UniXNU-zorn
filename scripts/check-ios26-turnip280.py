#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise actual selected Turnip wire/BO-finish bodies; IOKit and reaping are explicit host fixtures."""
import argparse, hashlib, json, os, subprocess
from pathlib import Path

def function(text, name):
    start = text.index('\n' + name + '(') + 1
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--abi-dir', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); a.out.mkdir(parents=True)
    source = a.source.read_text()
    prelude = r'''
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <pthread.h>
#include <sched.h>
#include "ZornAdrenoAbiV1Selection279.h"
#define MIN2(a,b) ((a)<(b)?(a):(b))
#define TU_RMV(...) ((void)0)
#define DW_TUNNEL_MAGIC 0x4e544e4cu
using kern_return_t=int;using VkResult=int;
constexpr int KERN_SUCCESS=0,kIOReturnBadArgument=1,kIOReturnBusy=2,VK_SUCCESS=0,VK_ERROR_DEVICE_LOST=-4;
struct tu_bo{uint32_t gem_handle,refcnt;uint64_t darwin_handle,iova,size,darwin_alloc_size;void*map;uint32_t darwin_token;bool darwin_read_only;};
struct darwin_retired_bo{uint64_t handle,iova,size;void*mapping;uint32_t token,fence;bool cacheable,read_only;};
struct darwin_retire_state{pthread_mutex_t lock;darwin_retired_bo*entries;unsigned capacity,head,count;VkResult failure;uint64_t enqueued;};
struct tu_device{pthread_rwlock_t dma_bo_lock;void*darwin_retire;int vk;};
struct tu_queue{tu_device*device;};
static struct{unsigned conn=0,selector=9,inflight_count=0;bool tunnel=false;uint32_t inflight[8]={},last_fence=77;NativeAdrenoAbiParams params={};pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;}dw;
static unsigned calls,expected_count,waits,busy_left;static int call_error;static bool expected_batch;
static int IOConnectCallStructMethod(unsigned,unsigned method,const void*data,size_t size,void*out,size_t*outsize){
 ++calls;if(dw.tunnel){assert(method==dw.selector&&size>=8);auto h=(const uint32_t*)data;assert(h[0]==DW_TUNNEL_MAGIC);method=h[1];data=(const char*)data+8;size-=8;}
 assert(method==(expected_batch?NativeAdrenoMethodSubmitBatch:NativeAdrenoMethodSubmit));
 assert(size==(expected_batch?sizeof(NativeAdrenoAbiSubmitBatch):sizeof(NativeAdrenoAbiSubmit)));
 NativeAdrenoAbiSubmitBatch req={};memcpy(&req,data,size);assert(req.buffer_count==expected_count&&req.queue==0);
 for(unsigned i=0;i<expected_count;i++)assert(req.buffers[i].iova==0x100000ull+i*4096);
 if(busy_left){--busy_left;return kIOReturnBusy;}if(call_error)return call_error;
 assert(out&&outsize&&*outsize==sizeof(NativeAdrenoAbiSubmitReply));((NativeAdrenoAbiSubmitReply*)out)->fence=123;return 0;
}
static uint64_t tu_trace_clock_ns(){static uint64_t n;n+=1000;return n;}
static int vk_device_set_lost(int*vk,const char*,...){*vk=1;return VK_ERROR_DEVICE_LOST;}
static int dw_wait_fence_locked_free(tu_device*,uint32_t f,uint64_t){assert(f==55);++waits;return 0;}
static void u_rwlock_rdlock(pthread_rwlock_t*p){assert(!pthread_rwlock_rdlock(p));}
static void u_rwlock_rdunlock(pthread_rwlock_t*p){assert(!pthread_rwlock_unlock(p));}
static bool p_atomic_dec_zero(uint32_t*p){return __atomic_sub_fetch(p,1,__ATOMIC_SEQ_CST)==0;}
static void tu_debug_bos_del(tu_device*,tu_bo*){}static void tu_dump_bo_del(tu_device*,tu_bo*){}
static tu_bo*reuse_slot;static unsigned reap_calls,reuse_at;static bool fail_alloc;
static int darwin_reap_locked(tu_device*,darwin_retire_state*){
 ++reap_calls;if(reuse_slot&&reap_calls==reuse_at){assert(!reuse_slot->gem_handle);reuse_slot->gem_handle=99;reuse_slot->iova=0x999000;reuse_slot->refcnt=1;}return 0;
}
static void*fixture_calloc(size_t n,size_t z){return fail_alloc?nullptr:std::calloc(n,z);}
'''
    record_start = source.index('struct tu_darwin_submit_rec {')
    record_end = source.index('\n};', record_start) + 3
    code = prelude + '\n' + source[record_start:record_end] + '\n'
    code += 'static kern_return_t\n' + function(source, 'dw_call') + '\n'
    code += 'static VkResult\n' + function(source, 'darwin_submit_chunk') + '\n'
    code += 'static bool\n' + function(source, 'tu_darwin_set_priority') + '\n'
    code += 'static bool\n' + function(source, 'tu_darwin_note') + '\n'
    code += '#define calloc fixture_calloc\nstatic void\n' + function(source, 'darwin_bo_finish') + '\n#undef calloc\n'
    code += r'''
int main(){
 tu_device dev={};assert(!pthread_rwlock_init(&dev.dma_bo_lock,nullptr));tu_queue queue={&dev};
 NativeAdrenoAbiSubmitBuffer entries[128]={};for(unsigned i=0;i<128;i++)entries[i].iova=0x100000ull+i*4096;
 for(bool tunnel:{false,true})for(bool batch:{false,true}){
  dw.tunnel=tunnel;dw.params.flags=batch?NativeAdrenoParamsSubmitBatch:0;expected_batch=batch;
  for(unsigned n:{1u,batch?128u:16u}){expected_count=n;uint32_t fence=0;tu_darwin_submit_rec rec={};assert(!darwin_submit_chunk(&queue,entries,n,&fence,&rec)&&fence==123);}
  unsigned before=calls;uint32_t fence=0;tu_darwin_submit_rec rec={};assert(darwin_submit_chunk(&queue,entries,batch?129:17,&fence,&rec)==VK_ERROR_DEVICE_LOST&&calls==before);assert(darwin_submit_chunk(&queue,entries,0,&fence,&rec)==VK_ERROR_DEVICE_LOST&&calls==before);
 }
 dw.tunnel=false;dw.params.flags=NativeAdrenoParamsSubmitBatch;expected_batch=true;expected_count=128;dw.inflight_count=1;dw.inflight[0]=55;busy_left=1;uint32_t fence=0;tu_darwin_submit_rec rec={};assert(!darwin_submit_chunk(&queue,entries,128,&fence,&rec)&&waits==1&&rec.busy==1&&fence==123);
 call_error=9;assert(darwin_submit_chunk(&queue,entries,128,&fence,&rec)==VK_ERROR_DEVICE_LOST);call_error=0;
 unsigned before=calls;assert(!tu_darwin_set_priority(0,2)&&!tu_darwin_note(1,nullptr,0)&&calls==before);
 for(unsigned reuse:{0u,1u,2u}){
  darwin_retire_state retire={};assert(!pthread_mutex_init(&retire.lock,nullptr));dev.darwin_retire=&retire;
  tu_bo bo={11,1,11,0x11000,8192,8192,(void*)0x4000,7,true};reuse_slot=reuse?&bo:nullptr;reuse_at=reuse;reap_calls=0;darwin_bo_finish(&dev,&bo);
  assert(retire.count==1&&retire.enqueued==1&&retire.entries[0].handle==11&&retire.entries[0].iova==0x11000&&retire.entries[0].token==7&&retire.entries[0].fence==77);
  assert(reuse?(bo.gem_handle==99&&bo.iova==0x999000):!bo.gem_handle);free(retire.entries);pthread_mutex_destroy(&retire.lock);
 }
 darwin_retire_state retire={};assert(!pthread_mutex_init(&retire.lock,nullptr));dev.darwin_retire=&retire;reuse_slot=nullptr;tu_bo retained={12,2,12,0x12000,4096,0,nullptr,0,false};darwin_bo_finish(&dev,&retained);assert(retained.refcnt==1&&retained.gem_handle==12&&!retire.count);
 retained.refcnt=1;fail_alloc=true;dev.vk=0;darwin_bo_finish(&dev,&retained);assert(retire.failure==VK_ERROR_DEVICE_LOST&&dev.vk&&!retire.count&&!retire.entries);fail_alloc=false;
 pthread_mutex_destroy(&retire.lock);pthread_rwlock_destroy(&dev.dma_bo_lock);
 puts("PASS280 actual v1 direct/tunnel 16/128 wire lengths, refusal/busy/failure, no v2 dispatch;actual BO-finish early slot reuse and failed retirement recording. IOKit/reaping/allocation are fixtures;no GPU.");
}
'''
    code = code.replace('#include <cassert>', '#include <cassert>\n#include <initializer_list>')
    cpp = a.out/'actual.cpp'; cpp.write_text(code)
    env = dict(os.environ, ASAN_OPTIONS='symbolize=0', UBSAN_OPTIONS='symbolize=0:print_stacktrace=0')
    results=[]
    for cmd in [['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(a.abi_dir.resolve()),str(cpp),'-o',str(a.out/'check')],[str((a.out/'check').resolve())]]:
        r=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=60)
        results.append(dict(command=cmd,exit=r.returncode,stdout=r.stdout,stderr=r.stderr))
        (a.out/'commands.json').write_text(json.dumps(results,indent=2)+'\n')
        assert r.returncode==0,r.stderr[-3500:]
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,test_tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),actual_source=str(a.source.resolve()),source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),fixture_boundaries=['IOKit struct call','fence wait','reap callback','allocation failure'],real_hardware=False,stdout=results[-1]['stdout']),indent=2)+'\n')
    print(results[-1]['stdout'].strip())

if __name__=='__main__':main()

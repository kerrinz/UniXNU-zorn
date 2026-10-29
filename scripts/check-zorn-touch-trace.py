#!/usr/bin/env python3
"""Exercise the real trace producer, bounded snapshot and v18 binary decoder."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'out/zorn/touch'
OUT.mkdir(parents=True, exist_ok=True)
HEADER = ROOT / 'UniXNU-zorn/native/display/ZornTouchTrace.h'
spec = importlib.util.spec_from_file_location('trace_reader', Path(__file__).with_name('read-zorn-log.py'))
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
program = r'''
#include <cassert>
#include <atomic>
#include <cstddef>
#include <cstdio>
#include <thread>
#include "ZornTouchTrace.h"
#include "ZornGuiLog.h"
using namespace ZornTouchTrace;
static ZornContacts::Frame finger(unsigned x,unsigned y,unsigned id=0) {
    ZornContacts::Frame f={};f.count=1;f.points[0]={uint16_t(x),uint16_t(y),900,uint8_t(id)};return f;
}
int main(int argc,char **argv) {
    assert(argc==2 && Bytes==sizeof(((ZornGuiFooter *)nullptr)->stacks));
    assert(offsetof(ZornGuiFooter,stacks)==2472 && sizeof(ZornGuiFooter)==3072);
    Recorder r;uint32_t shared[Words]={},copy[Words]={};
    assert(!snapshot(shared,copy) && copy[10]==2);
    assert(r.sample(finger(8192,24575),100));
    assert(r.sample(finger(8250,24550),400));assert(r.total==1);
    assert(r.sample(finger(8250,24550),1100));assert(r.total==2);
    assert(r.sample(finger(16384,16384),1400));assert(r.total==3);
    assert(r.sample({},1600));assert(r.total==4);
    assert(r.points[0].phase==Down && r.points[1].phase==Move && r.points[3].phase==Up);
    assert(!r.sample(finger(1,1),1500));
    assert(!r.sample(finger(32768,1),1700));assert(!r.sample(finger(1,1,20),1700));
    auto duplicate=finger(1,1);duplicate.count=2;duplicate.points[1]=duplicate.points[0];
    assert(!r.sample(duplicate,1700));
    assert(r.sample(finger(24575,8192),1800));
    assert(r.sample({},1900,false));assert(r.bad==1 && r.previous.count==1);
    r.release(2000,1);assert(r.points[5].reason==1 && r.previous.count==0);
    r.publish(shared);assert(snapshot(shared,copy));assert(copy[2]==6 && copy[3]==6);
    assert(copy[4]==7 && copy[5]==1 && copy[7]==700);
    __atomic_fetch_add(shared,1,__ATOMIC_RELEASE);
    assert(!snapshot(shared,copy) && copy[10]==2); // no spin on a preempted writer
    __atomic_fetch_add(shared,1,__ATOMIC_RELEASE);
    unsigned char block[4096]={};memcpy(block,"ZORNLOGD",8);
    auto *footer=reinterpret_cast<ZornGuiFooter *>(block+1024);
    memcpy(footer->magic,"ZORNGUI1",8);footer->version=18;footer->bytes=sizeof(*footer);
    assert(snapshot(shared,copy));memcpy(footer->stacks,copy,sizeof(copy));
    FILE *file=fopen(argv[1],"wb");assert(file && fwrite(block,1,sizeof(block),file)==sizeof(block));fclose(file);
    // Ring rollover is chronological, and cannot overwrite another footer field.
    for(unsigned i=0;i<1000;++i){assert(r.sample(finger((i&1)?1000:30000,16000),2100+i*100));r.publish(shared);}
    assert(snapshot(shared,copy) && copy[2]>1000 && copy[3]==Capacity);
    // Concurrent producer/reader: atomic payload words plus a bounded seqlock.
    std::atomic<bool> done{false};unsigned accepted=0;
    std::thread writer([&]{for(unsigned i=0;i<20000;++i){assert(r.sample(finger(i%32768,i%32768),102100+i*10));r.publish(shared);}done=true;});
    do {
        if(snapshot(shared,copy)){
            ++accepted;assert(!(copy[0]&1) && copy[1]==Magic && copy[3]==Capacity && copy[10]==1);
            assert(copy[5]<=copy[4]);
            for(unsigned i=0;i<Capacity;++i)assert(copy[12+i*3]<=copy[6]);
        } else assert(copy[10]==2);
    } while(!done.load());
    writer.join();assert(accepted>0);
    assert(snapshot(shared,copy));
    file=fopen((std::string(argv[1])+".wrapped").c_str(),"wb");
    assert(file && fwrite(copy,1,sizeof(copy),file)==sizeof(copy));fclose(file);
}
'''
# std::string is used only by the host fixture writer.
program = program.replace('#include <thread>', '#include <thread>\n#include <string>')
source, binary, fixture = OUT/'trace-check.cpp', OUT/'trace-check', OUT/'trace-check.bin'
source.write_text(program)
subprocess.run(['xcrun','clang++','-std=c++17','-O1','-Wall','-Wextra','-Werror',
                '-fsanitize=address,undefined','-I',str(HEADER.parent),
                '-I',str(ROOT/'UniXNU-zorn/native/ufs-read'),str(source),'-o',str(binary)],check=True)
subprocess.run([str(binary),str(fixture)],check=True)
block=fixture.read_bytes();state=reader.gui_state(block);trace=state['touch_trace']
assert state['user_stacks']==[] and state['kernel_stacks']==[]
assert [(p['phase'],p['x'],p['y']) for p in trace['records']] == [
    ('down',8192,24575),('move',8250,24550),('move',16384,16384),('up',16384,16384),
    ('down',24575,8192),('up',24575,8192)]
assert trace['bad_samples']==1 and trace['records'][-1]['release_reason']=='invalid-frames'
wrapped=reader.touch_trace(Path(str(fixture)+'.wrapped').read_bytes())
assert len(wrapped['records'])==32 and wrapped['overwritten_records']>1000
assert all(a['ms']<=b['ms'] for a,b in zip(wrapped['records'],wrapped['records'][1:]))
offset=1024+2472
controls=[(4,0),(0,3),(12,33),(20,100),(28,3000),(40,3),(44,1),
          (48,999999),(52,32768),(56,20),(56,4<<8),(56,1<<8),(56,(1<<24)|(1<<16)|(1<<8))]
for at,value in controls:
    bad=bytearray(block);struct.pack_into('<I',bad,offset+at,value)
    try:reader.gui_state(bytes(bad))
    except ValueError:pass
    else:raise AssertionError(('corrupt trace accepted',at,value))
unavailable=bytearray(block);unavailable[offset:offset+432]=bytes(432)
struct.pack_into('<I',unavailable,offset+4,0x3152545a);struct.pack_into('<I',unavailable,offset+40,2)
assert reader.gui_state(bytes(unavailable))['touch_trace']['status']=='snapshot-unavailable'
# Defaults have no USB side effects; unsafe combinations must fail in parsing.
for entry in (ROOT/'UniXNU-zorn/scripts/build-zorn-debug.py',ROOT/'uefi-zorn/scripts/make-zorn-payload.py'):
    failed=subprocess.run(['python3',str(entry),'--touch-trace'],capture_output=True,text=True)
    assert failed.returncode==2 and '--touch-trace requires' in failed.stderr
result={'passed':True,'header_sha256':hashlib.sha256(HEADER.read_bytes()).hexdigest(),
        'reader_sha256':hashlib.sha256(Path(reader.__file__).read_bytes()).hexdigest(),
        'cpp_asan_ubsan':True,'concurrent_atomic_publication':True,'bounded_busy_snapshot':True,
        'invalid_frames_release_and_ring_wrap':True,'cpp_to_python_v18_roundtrip':True,
        'corruption_controls':len(controls),'cli_rejection_controls':2,
        'same_4096_byte_log':True,'replaces_only_unused_stack_slots':True,'hardware_qualified':False}
(OUT/'trace-host-check.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))

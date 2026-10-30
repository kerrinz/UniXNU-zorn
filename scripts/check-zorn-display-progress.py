#!/usr/bin/env python3
"""Exercise the real measurement helper under concurrency and ABI boundaries."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HEADER = ROOT / 'UniXNU-zorn/native/display/ZornDisplayProgress.h'
DECODER = ROOT / 'UniXNU-zorn/scripts/zorn_display_progress.py'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'out/zorn/display-progress/host-check.json')
    args = parser.parse_args()
    harness = r'''
#include "ZornDisplayProgress.h"
#include "ZornGuiLog.h"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <thread>
#include <atomic>
using namespace ZornDisplayProgress;
int main(int argc, char **argv) {
    assert(argc == 2);
    State state{};
    std::atomic<unsigned> done{0};
    std::thread workers[8];
    for (unsigned n=0;n<8;++n) workers[n]=std::thread([&,n] {
        for (unsigned i=0;i<25000;++i) observe(state,(i+n)%Events,1000+i);
        vsync(state,777,1);done.fetch_add(1);
    });
    while(done.load()!=8) {uint64_t v[Words];snapshot(state,50000,v);}
    for(auto &worker:workers)worker.join();
    uint64_t expected[Events]={};
    for(unsigned n=0;n<8;++n)for(unsigned i=0;i<25000;++i)++expected[(i+n)%Events];
    uint64_t values[Words];snapshot(state,50000,values);
    for(unsigned i=0;i<Events;++i)assert(values[i*2]==expected[i]);
    assert(values[Unknown]==8);
    State mapping{};
    for(unsigned i=0;i<6;++i)vsync(mapping,i,10+i);
    uint64_t map[Words];snapshot(mapping,100,map);
    assert(!map[0]);for(unsigned i=Armed;i<Events;++i)assert(map[i*2]==1);

    uint64_t original[32];
    for(unsigned i=0;i<32;++i)original[i]=0xffff000000000000ULL+i;
    for(unsigned i=0;i<Words;++i)original[Slots[i]]=i+1;
    uint64_t encoded[32];memcpy(encoded,original,sizeof(encoded));
    assert(encode(encoded,values));
    for(unsigned i=0;i<Words;++i)assert(uint32_t(encoded[Slots[i]])==original[Slots[i]]);
    for(unsigned bad=0;bad<Words;++bad) {
        uint64_t src[32],before[32];memcpy(src,original,sizeof(src));
        src[Slots[bad]]|=1ULL<<32;memcpy(before,src,sizeof(src));
        assert(!encode(src,values));assert(!memcmp(src,before,sizeof(src)));
        uint64_t tooLarge[Words];memcpy(tooLarge,values,sizeof(values));tooLarge[bad]=1ULL<<32;
        memcpy(src,original,sizeof(src));assert(!encode(src,tooLarge));assert(!memcmp(src,original,sizeof(src)));
    }
    uint64_t edge[Words];for(auto &v:edge)v=0xffffffffULL;
    uint64_t edgeDisplay[32]={};assert(encode(edgeDisplay,edge));
    for(unsigned i=0;i<Words;++i)assert(edgeDisplay[Slots[i]]>>32==0xffffffffULL);
    // The 4KiB block stays full-size, all original offsets and every byte
    // except the sixteen explicitly overlaid high halves stay unchanged.
    alignas(8) unsigned char block[4096],before[4096];memset(block,0xa5,sizeof(block));
    static_assert(ZORN_GUI_LOG_OFFSET==1024 && sizeof(ZornGuiFooter)==3072,"existing ABI");
    static_assert(ZORN_GUI_LOG_OFFSET+sizeof(ZornGuiFooter)==4096,"authorized log extent");
    auto *footer=reinterpret_cast<ZornGuiFooter *>(block+ZORN_GUI_LOG_OFFSET);
    memcpy(footer->display,original,sizeof(original));memcpy(before,block,sizeof(block));
    assert(encode(footer->display,values));
    for(unsigned i=0;i<4096;++i) {
        bool allowed=false;
        for(unsigned n=0;n<Words;++n) {
            unsigned at=ZORN_GUI_LOG_OFFSET+80+Slots[n]*8+4;
            if(i>=at && i<at+4)allowed=true;
        }
        if(!allowed)assert(block[i]==before[i]);
    }
    FILE *f=fopen(argv[1],"wb");assert(f);
    assert(fwrite(original,sizeof(original),1,f)==1);
    assert(fwrite(encoded,sizeof(encoded),1,f)==1);
    assert(fwrite(values,sizeof(values),1,f)==1);assert(!fclose(f));
}
'''
    with tempfile.TemporaryDirectory(prefix='zorn-display-progress-') as directory:
        work = Path(directory)
        cpp = work / 'check.cpp'; cpp.write_text(harness)
        binary = work / 'check'; sample = work / 'sample.bin'
        command = ['xcrun','clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror',
                   '-I',str(HEADER.parent),'-I',str(ROOT/'UniXNU-zorn/native/ufs-read'),
                   str(cpp),'-o',str(binary)]
        subprocess.run(command,check=True)
        subprocess.run([str(binary),str(sample)],check=True,timeout=30)
        original = struct.unpack('<32Q',sample.read_bytes()[:256])
        encoded = struct.unpack('<32Q',sample.read_bytes()[256:512])
        values = struct.unpack('<16Q',sample.read_bytes()[512:])
        spec = importlib.util.spec_from_file_location('display_progress',DECODER)
        module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        decoded, progress = module.decode(encoded)
        assert decoded == list(original)
        assert progress['unknown_events'] == 8 and not progress['receipt_confirmed']
        assert [progress['events'][name]['count'] for name in module.EVENTS] == list(values[::2][:7])
        # Keep concurrent/stale observations explicit; do not reject or turn
        # them into a coherent timeline, negative age or userspace receipt.
        overlap = list(encoded)
        overlap[module.SLOTS[1]] = (overlap[module.SLOTS[1]] & 0xffffffff) | (60000<<32)
        _, p = module.decode(overlap)
        assert p['events']['retired']['sample_overlapped'] and p['events']['retired']['age_ms'] is None
        for invalid in [list(encoded[:-1]),[1<<64]*32,[-1]*32,[True]*32]:
            try: module.decode(invalid)
            except ValueError: pass
            else: raise AssertionError('invalid display input accepted')
        reader_path = ROOT/'UniXNU-zorn/scripts/read-zorn-log.py'
        spec = importlib.util.spec_from_file_location('progress_reader',reader_path)
        reader = importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
        # A self-contained valid v18 fixture: no private phone-log or host
        # workspace dependency in the build's qualification checks.
        fixture = bytearray(4096)
        struct.pack_into('<8s2I',fixture,0,b'ZORNLOGD',84,17)
        for index in range(84):
            word=f'D{index:03}'.encode()
            fixture[16+12*index:16+12*index+len(word)]=word
        struct.pack_into('<8s6IQ',fixture,1024,b'ZORNGUI1',18,3072,1,12,0,1,15000)
        struct.pack_into('<32Q',fixture,1104,*original)
        trace=[0]*108;trace[0]=2;trace[1]=0x3152545a;trace[10]=1
        struct.pack_into('<108I',fixture,1024+2472,*trace)
        struct.pack_into('<Q',fixture,1024+2928,0xffffffff)
        raw = bytes(fixture)
        old = reader.gui_state(raw)
        assert struct.unpack_from('<I',raw,1032)[0] == 18
        amended = bytearray(raw)
        original_display = struct.unpack_from('<32Q',raw,1104)
        modified = list(original_display)
        for index, slot in enumerate(module.SLOTS):
            assert not modified[slot] >> 32
            modified[slot] |= values[index] << 32
        struct.pack_into('<32Q',amended,1104,*modified)
        struct.pack_into('<I',amended,1032,19)
        new = reader.gui_state(bytes(amended))
        assert new.pop('display_progress') == progress
        assert new == old and reader.decode(bytes(amended)) == reader.decode(raw)
        struct.pack_into('<I',amended,1032,20)
        try: reader.gui_state(bytes(amended))
        except ValueError: pass
        else: raise AssertionError('unknown GUI version accepted')
        target = work/'target.cpp'
        target.write_text('#include "ZornDisplayProgress.h"\nextern "C" void probe(ZornDisplayProgress::State *s,unsigned e,uint64_t t){ZornDisplayProgress::observe(*s,e,t);}\nextern "C" bool pack(uint64_t *d,const uint64_t *v){return ZornDisplayProgress::encode(d,v);}\n')
        sdk = subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
        obj = work/'target.o'
        subprocess.run(['xcrun','clang++','-target','arm64-apple-ios17.0','-isysroot',sdk,
            '-std=c++17','-O2','-ffreestanding','-fno-exceptions','-fno-rtti','-mgeneral-regs-only',
            '-I',str(HEADER.parent),'-c',str(target),'-o',str(obj)],check=True)
        unresolved = subprocess.check_output(['xcrun','nm','-u',str(obj)],text=True).strip()
        assert not unresolved, unresolved
        disassembly = subprocess.check_output(['xcrun','llvm-objdump','-d',str(obj)],text=True)
        assert 'ldxr' in disassembly and 'stxr' in disassembly
        args.output.parent.mkdir(parents=True,exist_ok=True)
        (args.output.parent/'arm64-helper-disassembly.txt').write_text(disassembly)
        probe_source = (ROOT/'UniXNU-zorn/native/display/ZornDisplayProbe.cpp').read_text()
        begin = probe_source.index('#include "ZornDisplayProgress.h"')
        end = probe_source.index('static bool videoValid',begin)
        actual = probe_source[begin:end]
        for signature in ['extern "C" void native_legacy_retirement_observed(',
                          'extern "C" void native_legacy_vsync_observed(']:
            start = probe_source.index(signature)
            at = probe_source.index('{',start)+1;depth=1
            while depth:
                depth += (probe_source[at]=='{')-(probe_source[at]=='}');at+=1
            actual += probe_source[start:at]+'\n'
        hooks = work/'hooks.cpp'
        hooks.write_text(r'''
#include <cstdint>
#include <cassert>
#include <cstring>
struct IOService {};
static unsigned clockCalls;
static uint64_t nowMs=1234;
static uint64_t mach_absolute_time(){++clockCalls;return nowMs*1000000;}
static void absolutetime_to_nanoseconds(uint64_t t,uint64_t *out){*out=t;}
static void zorn_say(const char *){}
static void number(const char *,uint64_t){}
@ACTUAL@
int main(){
    uint64_t d[32]={};native_legacy_retirement_observed(nullptr);native_legacy_vsync_observed(1,60);
    assert(clockCalls==0 && !zorn_display_progress_overlay(d));
    zorn_display_progress_configure(1);native_legacy_retirement_observed(nullptr);
    for(unsigned i=0;i<6;++i)native_legacy_vsync_observed(i,60);
    assert(clockCalls==7);assert(zorn_display_progress_overlay(d));
    for(unsigned i=0;i<7;++i){assert(d[ZornDisplayProgress::Slots[2*i]]>>32==1);assert(d[ZornDisplayProgress::Slots[2*i+1]]>>32==1234);}
    zorn_display_progress_configure(1);uint64_t again[32]={};assert(zorn_display_progress_overlay(again));
    assert(!memcmp(d,again,sizeof d));zorn_display_progress_configure(2);
    unsigned prior=clockCalls;native_legacy_retirement_observed(nullptr);native_legacy_vsync_observed(1,60);
    assert(clockCalls==prior && !zorn_display_progress_overlay(again));
}
'''.replace('@ACTUAL@',actual))
        hook_binary=work/'hooks'
        subprocess.run(['xcrun','clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror',
            '-I',str(HEADER.parent),str(hooks),'-o',str(hook_binary)],check=True)
        subprocess.run([str(hook_binary)],check=True,timeout=10)
    result = dict(header_sha256=hashlib.sha256(HEADER.read_bytes()).hexdigest(),
        decoder_sha256=hashlib.sha256(DECODER.read_bytes()).hexdigest(),
        actual_8_thread_callbacks=200000,exact_quiescent_event_counts=True,
        unknown_backend_events_preserved=True,all_16_original_high_half_negative_cases=True,
        all_16_new_value_overflow_negative_cases=True,uint32_max_boundary_roundtrip=True,
        original_display_words_roundtrip_exact=True,unmodified_bytes_outside_64_overlay_bytes=True,
        log_bytes=4096,footer_bytes=3072,text_slots=84,touch_trace_bytes_preserved=432,
        additional_text_bytes=0,arm64_general_registers_only_compile=True,
        arm64_no_undefined_atomic_or_other_helpers=True,independent_word_times_declared=True,
        reader_integrated=True,actual_v18_v19_reader_roundtrip=True,
        actual_legacy_text_and_touch_trace_preserved=True,unknown_v20_rejected=True,
        observer_hooks_runtime_qualified=False,payload_switch_runtime_qualified=False,
        actual_observer_bodies_host_checked=True,disabled_observers_make_no_clock_calls=True,
        repeated_enable_preserves_counts=True,
        hardware_qualified=False,phone_operations=False,
        scope='Actual helpers/observer bodies and v18/v19 reader with self-contained fixtures; target timing overhead, final kernel wiring, runtime log and GUI repair remain unqualified.')
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__': main()

#!/usr/bin/env python3
"""Cross-check actual C++ log layout/ring writer against the host binary decoder."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
root=Path(__file__).resolve().parents[2];out=root/'out/zorn/touch'
header=root/'UniXNU-zorn/native/ufs-read/ZornTouchRawLog.h';source=(header.parent/'ZornUfsRead.cpp').read_text()
writer=source[source.index('static void zorn_log_put(const char *text)'):source.index('\nextern "C" void zorn_ufs_gui_stage')]
assert 'if (gTouchRawLog) return;' in source[source.index('static void zorn_gui_fill_footer'):source.index('static void zorn_log_append')]
test=r'''
#include <cassert>
#include <cstdio>
#include <cstring>
#include "ZornTouchRawLog.h"
#include "ZornGuiLog.h"
struct Block {char magic[8];uint32_t count,next;char word[340][12];};
static Block gLogBlock;
static bool gTouchRawLog=true,gGuiWatch=true;
'''+writer+r'''
int main(int argc,char **argv) {
 assert(argc==2);uint8_t raw[3120];for(unsigned i=0;i<3120;++i)raw[i]=(i*13)^0x5a;
 assert(!ZornTouchLog::install(&gLogBlock,4095,raw,sizeof(raw)));
 assert(!ZornTouchLog::install(&gLogBlock,4096,raw,sizeof(raw)-1));
 assert(!ZornTouchLog::install(&gLogBlock,4096,nullptr,sizeof(raw)));
 struct {uint64_t before;uint8_t block[4096];uint64_t after;} guarded={};guarded.before=0x0123456789abcdef;guarded.after=0xfedcba9876543210;
 assert(ZornTouchLog::install(guarded.block,4096,raw,sizeof(raw)));
 assert(guarded.before==0x0123456789abcdef && guarded.after==0xfedcba9876543210);
 memcpy(&gLogBlock,guarded.block,4096);
 for(unsigned i=0;i<1000;++i){char text[12];snprintf(text,sizeof(text),"S%08u",i);zorn_log_put(text);}
 assert(gLogBlock.count==64 && gLogBlock.next==1000%64);
 assert(!memcmp(reinterpret_cast<uint8_t *>(&gLogBlock)+960,raw,sizeof(raw)));
 FILE *file=fopen(argv[1],"wb");assert(file);assert(fwrite(&gLogBlock,1,4096,file)==4096);assert(!fclose(file));
 // GUI text wrapping must preserve all 3072 footer bytes, including touch state.
 memset(&gLogBlock,0,sizeof(gLogBlock));gTouchRawLog=false;
 uint8_t *footer=reinterpret_cast<uint8_t *>(&gLogBlock)+ZORN_GUI_LOG_OFFSET;
 uint8_t saved[sizeof(ZornGuiFooter)];
 for(unsigned i=0;i<sizeof(saved);++i)saved[i]=(i*7)^0x9d;
 memcpy(footer,saved,sizeof(saved));
 for(unsigned i=0;i<1000;++i)zorn_log_put("GUIWRAP");
 assert(gLogBlock.count==ZORN_GUI_LOG_SLOTS && gLogBlock.next==1000%ZORN_GUI_LOG_SLOTS);
 assert(!memcmp(footer,saved,sizeof(saved)));
}
'''
(out/'raw-log-check.cpp').write_text(test)
subprocess.run(['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-O1','-fsanitize=address,undefined','-I',str(header.parent),str(out/'raw-log-check.cpp'),'-o',str(out/'raw-log-check')],check=True)
subprocess.run([str(out/'raw-log-check'),str(out/'raw-log-check.bin')],check=True)
spec=importlib.util.spec_from_file_location('zorn_log',root/'UniXNU-zorn/scripts/read-zorn-log.py');reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
block=(out/'raw-log-check.bin').read_bytes();raw=bytes(((i*13)^0x5a)&255 for i in range(3120))
assert reader.touch_raw(block)==raw and reader.gui_state(block) is None
assert reader.decode(block)==['S%08d'%i for i in range(936,1000)]
mutations=[(784,1),(792,1),(796,1),(798,1),(960,1),(2500,1),(4079,1)]
for offset,value in mutations:
 bad=bytearray(block);bad[offset]^=value
 try:reader.touch_raw(bad)
 except ValueError:pass
 else:raise AssertionError('corrupted payload/metadata accepted '+str(offset))
r={'passed':True,'cpp_header_sha256':hashlib.sha256(header.read_bytes()).hexdigest(),'actual_ring_writer_wraps':1000,'raw_bytes':3120,'cpp_asan_ubsan':True,'host_decoder_matches_cpp':True,'corruption_cases':len(mutations),'gui_footer_preserved_across_1000_wraps':True,'same_existing_log_block':True,'hardware_qualified':False}
(out/'raw-log-host-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))

#!/usr/bin/env python3
"""Test the new unselected C file decoder;never compile selected startup or execute a target object."""
from pathlib import Path
import argparse,json,hashlib,subprocess,struct
R=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();O=a.out.resolve();O.mkdir(exist_ok=False)
B=R/'UniXNU-zorn/native/gpu-owned/source-review';clang=Path('/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
fixture=R/'out/zorn/gpu-commanddb-input-acquisition-20261103/synthetic.bin';(O/'synthetic-input.bin').write_bytes(fixture.read_bytes())
harness=r'''#include "ZornCommandDbFile.h"
#include <stdio.h>
#include <string.h>
static union {max_align_t align;unsigned char bytes[100000];} storage;
static ZornCommandDbFileEntry entries[4],saved_entries[4];
static ZornCommandDbFileSummary summary,saved_summary;
static void w16(size_t at,unsigned v){storage.bytes[at]=(unsigned char)v;storage.bytes[at+1]=(unsigned char)(v>>8);}
static void reset(void){memset(storage.bytes,0,sizeof(storage.bytes));storage.bytes[0]=0x78;storage.bytes[1]=0x56;storage.bytes[2]=0x34;storage.bytes[3]=0x12;storage.bytes[4]=0xdb;storage.bytes[5]=0x30;storage.bytes[6]=3;storage.bytes[7]=12;w16(8,9);w16(12,48);w16(14,2);memcpy(storage.bytes+144,"raw-id!!",8);memcpy(storage.bytes+168,"raw-id!!",8);w16(164,3);storage.bytes[192]=0xff;storage.bytes[193]=0;storage.bytes[194]=65;}
static void poison_outputs(void){memset(entries,0xa5,sizeof(entries));memset(&summary,0x5a,sizeof(summary));memcpy(saved_entries,entries,sizeof(entries));memcpy(&saved_summary,&summary,sizeof(summary));}
static int unchanged(void){return !memcmp(entries,saved_entries,sizeof(entries))&&!memcmp(&summary,&saved_summary,sizeof(summary));}
static int check(const char *name,ZornCommandDbFileStatus want,const unsigned char *data,size_t bytes,size_t capacity){poison_outputs();ZornCommandDbFileStatus got=ZornCommandDbDecodeFile(data,bytes,entries,capacity,&summary);int same=unchanged();printf("%s status=%d expected=%d unchanged=%d\n",name,(int)got,(int)want,same);return got==want&&same;}
int main(void){int ok=1;reset();
 poison_outputs();ZornCommandDbFileStatus s=ZornCommandDbDecodeFile(storage.bytes,256,entries,4,&summary);
 ok&=s==ZCDF_OK&&summary.entry_count==2&&summary.searched_rows==1&&summary.source_bytes==256;
 ok&=!summary.snapshot_qualified&&!summary.expected_version_qualified&&!summary.hardware_qualified;
 ok&=!memcmp(summary.header_raw,storage.bytes,144)&&!memcmp(entries[0].raw,storage.bytes+144,24);
 ok&=!memcmp(entries[1].raw,storage.bytes+168,24)&&entries[0].aux_file_offset==192&&entries[0].aux_bytes==3;
 printf("raw-two-records-and-no-qualification=%d\n",ok);
 reset();w16(40,5);w16(42,65535);w16(46,65535);s=ZornCommandDbDecodeFile(storage.bytes,256,entries,4,&summary);ok&=s==ZCDF_OK&&summary.entry_count==2&&!memcmp(summary.header_raw,storage.bytes,144);
 reset();w16(12,0);w16(164,4);s=ZornCommandDbDecodeFile(storage.bytes,256,entries,4,&summary);ok&=s==ZCDF_OK&&entries[0].aux_overlaps_record_table;
 reset();w16(8,0);s=ZornCommandDbDecodeFile(storage.bytes,256,0,0,&summary);ok&=s==ZCDF_OK&&summary.entry_count==0;
 reset();ok&=check("short-file",ZCDF_ARGUMENT,storage.bytes,143,4);
 ok&=check("file-budget",ZCDF_ARGUMENT,storage.bytes,ZCDF_MAX_FILE_BYTES+1u,4);
 ok&=check("capacity-budget",ZCDF_ARGUMENT,storage.bytes,256,ZCDF_MAX_ENTRIES+1u);
 ok&=check("null-input",ZCDF_ARGUMENT,0,256,4);
 ok&=check("capacity",ZCDF_CAPACITY,storage.bytes,256,1);
 reset();storage.bytes[4]=0;ok&=check("magic",ZCDF_FORMAT,storage.bytes,256,4);
 reset();memcpy(storage.bytes,"\x7f""ELF",4);ok&=check("ELF",ZCDF_FORMAT,storage.bytes,256,4);
 reset();storage.bytes[0]=0xd0;storage.bytes[1]=0x0d;storage.bytes[2]=0xfe;storage.bytes[3]=0xed;ok&=check("DTB",ZCDF_FORMAT,storage.bytes,256,4);
 reset();w16(10,65535);ok&=check("record-extent",ZCDF_RANGE,storage.bytes,256,4);
 reset();w16(12,65535);ok&=check("aux-base",ZCDF_RANGE,storage.bytes,256,4);
 reset();w16(188,65);ok&=check("late-aux-extent",ZCDF_RANGE,storage.bytes,256,4);
 reset();w16(14,4097);ok&=check("row-budget",ZCDF_BUDGET,storage.bytes,sizeof(storage.bytes),4);
 reset();w16(14,3000);w16(24,10);w16(30,3000);ok&=check("aggregate-budget",ZCDF_BUDGET,storage.bytes,sizeof(storage.bytes),4);
 reset();poison_outputs();unsigned char before[256];memcpy(before,storage.bytes,256);s=ZornCommandDbDecodeFile(storage.bytes,256,entries,4,(ZornCommandDbFileSummary *)(void *)storage.bytes);ok&=s==ZCDF_ALIAS&&unchanged()&&!memcmp(before,storage.bytes,256);
 reset();poison_outputs();s=ZornCommandDbDecodeFile(storage.bytes,256,(ZornCommandDbFileEntry *)(void *)storage.bytes,4,&summary);ok&=s==ZCDF_ALIAS&&unchanged();
 reset();poison_outputs();s=ZornCommandDbDecodeFile(storage.bytes,256,entries,4,(ZornCommandDbFileSummary *)(void *)entries);ok&=s==ZCDF_ALIAS&&unchanged();
 reset();poison_outputs();s=ZornCommandDbDecodeFile(storage.bytes,256,0,1,&summary);ok&=s==ZCDF_ARGUMENT&&unchanged();
 printf("PASS=%d valid=4 refusals=17 no-native-or-target-execution\n",ok);return ok?0:1;}
'''
(O/'harness.c').write_text(harness);events=[]
def run(cmd):
 p=subprocess.run([str(x) for x in cmd],capture_output=True);i=len(events);(O/f'{i}.stdout.raw').write_bytes(p.stdout);(O/f'{i}.stderr.raw').write_bytes(p.stderr);events.append(dict(command=[str(x) for x in cmd],returncode=p.returncode,stdout_sha256=hashlib.sha256(p.stdout).hexdigest(),stderr_sha256=hashlib.sha256(p.stderr).hexdigest()));save(O/'events.json',events)
 if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace') or p.stdout.decode(errors='replace'))
 return p.stdout.decode()
flags=['-std=c11','-Wall','-Wextra','-Werror','-Wconversion','-Wsign-conversion','-I',B]
run([clang,*flags,'-isysroot','/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk','-O1','-g','-fsanitize=address,undefined',B/'ZornCommandDbFile.c',O/'harness.c','-o',O/'host-check'])
output=run([O/'host-check'])
run([clang,*flags,'-ffreestanding','-fno-builtin','--target=arm64-apple-ios17.0.0','-O2','-c',B/'ZornCommandDbFile.c','-o',O/'ios17-file-decoder.o'])
raw=(O/'ios17-file-decoder.o').read_bytes();assert struct.unpack_from('<I',raw)[0]==0xfeedfacf;at=32;version=None
for _ in range(struct.unpack_from('<I',raw,16)[0]):
 cmd,size=struct.unpack_from('<II',raw,at)
 if cmd==0x32:platform,version=struct.unpack_from('<II',raw,at+8);assert platform==2
 at+=size
assert version==17<<16
save(O/'result.json',dict(scope='unselected freestanding C file-layout core;not full driver/native provider/startup build',sources={str(p):sha(p) for p in [B/'ZornCommandDbFile.c',B/'ZornCommandDbFile.h',Path(__file__).resolve()]},new_valid_cases=4,new_refusal_cases=17,failure_outputs_unchanged=True,ASan_UBSan_pass=True,ios17_arm64_object_build_pass=True,object_minimum_OS='17.0',target_object_executed=False,compiler_sha256=sha(clang),host_output=output,old_suites_rerun=False,component_or_runtime_caller_selected=False,generated_board_policy=False,snapshot_or_version_qualified=False,device_operations=False))
print(output+'PASS:unselected iOS17 ARM64 file-core object;no startup integration')

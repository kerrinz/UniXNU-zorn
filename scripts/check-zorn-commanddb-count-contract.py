#!/usr/bin/env python3
"""Conditional pure-host count-contract audit;NOT a generated K80 consumer build."""
from pathlib import Path
import hashlib,json,difflib,subprocess,argparse
R=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();O=args.out.resolve();O.mkdir(exist_ok=False)
B=R/'out/zorn/gpu-catalog-service-dependencies/sm8550-primary/kits/Sm8550Platform'
PINS={'ShengGmuCommandDb.c':'4defdbd000cd0cbe6c05836ab994c4903638c12878a845d9afde29b074b39e71','ShengGmuCommandDb.h':'f32b2417d08ee3ffc3bff5c6d58f70cb3e65e449f723d7f70e5d89fc5d5f50c2','ShengGmuVotes.h':'6051d0ef5196899fecf1a73b99c9ccd019e1665719b921c6083eaffbd20b2741'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
for name,digest in PINS.items():assert sha(B/name)==digest; (O/name).write_bytes((B/name).read_bytes())
original=(B/'ShengGmuCommandDb.c').read_text();candidate=original.replace('unsigned rows=0;','unsigned rows=0,total_entries=0;').replace('        if(!id)break;','        if(!id)break;\n        /* Bound total scan work before any record scan, including unused names. */\n        if(count>4096u-total_entries)return ShengGmuDbCorrupt;\n        total_entries+=count;')
assert candidate!=original and candidate.count('4096u-total_entries')==1
(O/'candidate.c').write_text(candidate)
(O/'commanddb-total-count.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),candidate.splitlines(True),fromfile='a/kits/Sm8550Platform/ShengGmuCommandDb.c',tofile='b/kits/Sm8550Platform/ShengGmuCommandDb.c')))
# Isolated host fixture declarations use the exact primary field declarations.
# This does not supply generated target inputs or assert an ABI for Darwin.
fixture=O/'host-fixture';fixture.mkdir()
(O/'ShengGmuVotes.h').rename(O/'primary-ShengGmuVotes.h')
votes=(B/'ShengGmuVotes.h').read_text();start=votes.index('typedef struct {const uint8_t *data;size_t bytes;}');end=votes.index('/* Build only CPU-side')
(O/'ShengGmuVotes.h').write_text('/* HOST FIXTURE ONLY: exact source field declarations,no native ABI. */\n#include <stddef.h>\n#include <stdint.h>\n'+votes[start:end])
# A test-only byte count chosen independently of any DT reservation. It is not
# a generated production header,not source policy,and never placed on build paths.
(O/'ShengGmuCommandDbSource.h').write_text('/* SYNTHETIC HOST FIXTURE ONLY;not K80 geometry. */\n#define SHENG_GMU_COMMAND_DB_BYTES 100000u\n')
harness=r'''#include <stdio.h>
#include <string.h>
#include "ShengGmuCommandDb.h"
ShengGmuDbStatus OriginalInputs(const uint8_t *,size_t,uint32_t,ShengGmuVoteInputs *);
ShengGmuDbStatus FixedInputs(const uint8_t *,size_t,uint32_t,ShengGmuVoteInputs *);
static unsigned char data[100000];
static void w16(size_t at,unsigned v){data[at]=(unsigned char)v;data[at+1]=(unsigned char)(v>>8);}
static void w32(size_t at,unsigned v){w16(at,v);w16(at+2,v>>16);}
static int run(const char *name,unsigned a,unsigned b,int mode,int oldwant,int newwant){
 memset(data,0,sizeof(data));w32(0,0x11223344u);w32(4,0x0c0330dbu);
 w16(8,3);w16(14,a);
 if(b){w16(24,5);w16(30,b);}
 uint32_t expected=0x11223344u;
 if(mode==1)expected=0;
 if(mode==2)expected++;
 if(mode==3)w32(4,0);
 ShengGmuVoteInputs before,oldout,newout;memset(&before,0xa5,sizeof(before));
 memcpy(&oldout,&before,sizeof(before));memcpy(&newout,&before,sizeof(before));
 int old=OriginalInputs(data,sizeof(data),expected,&oldout),fixed=FixedInputs(data,sizeof(data),expected,&newout);
 int same=!memcmp(&before,&oldout,sizeof(before))&&!memcmp(&before,&newout,sizeof(before));
 printf("%s old=%d fixed=%d out_unchanged=%d\n",name,old,fixed,same);
 return old==oldwant&&fixed==newwant&&same&&old!=ShengGmuDbSuccess&&fixed!=ShengGmuDbSuccess;
}
int main(void){int ok=1;
 ok&=run("single4097",4097,0,0,ShengGmuDbMissing,ShengGmuDbCorrupt);
 ok&=run("total4097",2048,2049,0,ShengGmuDbMissing,ShengGmuDbCorrupt);
 ok&=run("single4096",4096,0,0,ShengGmuDbMissing,ShengGmuDbMissing);
 ok&=run("total4096",2048,2048,0,ShengGmuDbMissing,ShengGmuDbMissing);
 ok&=run("zero-count",0,0,0,ShengGmuDbMissing,ShengGmuDbMissing);
 ok&=run("zero-expected",1,0,1,ShengGmuDbArgument,ShengGmuDbArgument);
 ok&=run("version-mismatch",1,0,2,ShengGmuDbVersion,ShengGmuDbVersion);
 ok&=run("magic-mismatch",1,0,3,ShengGmuDbCorrupt,ShengGmuDbCorrupt);
 return ok?0:1;}
'''
(O/'harness.c').write_text(harness)
clang=Path('/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang');events=[]
def run(cmd):
 p=subprocess.run([str(x) for x in cmd],capture_output=True);idx=len(events);(O/f'command-{idx}.stdout.raw').write_bytes(p.stdout);(O/f'command-{idx}.stderr.raw').write_bytes(p.stderr);events.append(dict(command=[str(x) for x in cmd],returncode=p.returncode,stdout_sha256=hashlib.sha256(p.stdout).hexdigest(),stderr_sha256=hashlib.sha256(p.stderr).hexdigest()));save(O/'events.json',events)
 if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace') or p.stdout.decode(errors='replace'))
 return p.stdout.decode()
flags=['-isysroot','/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk','-std=c11','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined']
run([clang,*flags,'-DShengGmuCommandDbInputs=OriginalInputs','-c',O/'ShengGmuCommandDb.c','-o',fixture/'original.o'])
run([clang,*flags,'-DShengGmuCommandDbInputs=FixedInputs','-c',O/'candidate.c','-o',fixture/'fixed.o'])
run([clang,*flags,O/'harness.c',fixture/'original.o',fixture/'fixed.o','-o',fixture/'count-check'])
output=run([fixture/'count-check'])
for name,digest in PINS.items():assert sha(B/name)==digest
save(O/'result.json',dict(scope='conditional source algorithm count audit under synthetic100000-byte host fixture;not generated target build or actual DB',primary_sources=PINS,compiler_sha256=sha(clang),output=output,over_limit_cases_reproduced=2,other_failure_boundaries_preserved=6,out_unchanged_all8=True,address_undefined_sanitizers_pass=True,fixture_expected_word='synthetic test token only;not independently qualified platform version',generated_target_header_available=False,actual_snapshot_available=False,source_patch_state='independent UNAPPLIED;not selected or composed with32driverpatches',production_source_unchanged=True,native_driver_or_device_execution=False,hardware_qualification=False,generated_runtime_policy=False))
print(output+'PASS:conditional pure-host count repair;no generated target/GPU qualification')

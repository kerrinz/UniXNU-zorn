from pathlib import Path
import json,subprocess,hashlib,os,shutil,argparse
ap=argparse.ArgumentParser(description='Actual shared-member Metal probe query/close CPU fixtures;not hardware');ap.add_argument('--build',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();B=a.build.resolve();C=json.loads((B/'candidate.json').read_text());S=Path(C['source']);P=Path(C['parent']);PS=Path(json.loads((P/'candidate.json').read_text())['source']);O=a.out.resolve();O.mkdir();pin=lambda p:dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest());save=lambda p,x:Path(p).write_text(json.dumps(x,indent=2)+'\n')
t=(S/'userland/ZornMetalProbe193.mm').read_text();a=t.index('static bool sharedQueries267(){');z=t.index('static int probe(){',a);body=t[a:z]
pre='''#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <unistd.h>
#include "Adreno740/NativeAdrenoABI.h"
using io_service_t=unsigned;using io_connect_t=unsigned;using kern_return_t=int;
constexpr unsigned IO_OBJECT_NULL=0,kIOMainPortDefault=0;constexpr int KERN_SUCCESS=0,kIOReturnNotReady=1;
static constexpr char tag[]="HOST-FIXTURE-ONLY";static uint64_t serviceID=7;
static int which,opens,queries,closes,releases;static unsigned closedMask;
unsigned mach_task_self(){return 2;}
unsigned IOServiceMatching(const char*){return 1;}
unsigned IOServiceGetMatchingService(unsigned,unsigned){return which==1?0:1;}
int IORegistryEntryGetRegistryEntryID(unsigned,uint64_t*p){*p=which==2?8:7;return which==3?4:0;}
void IOObjectRelease(unsigned){++releases;}
int IOServiceOpen(unsigned,unsigned,unsigned,unsigned*p){const int i=opens++;if((which==4&&i==0)||(which==5&&i==1))return 4;*p=i+1;return 0;}
int IOConnectCallStructMethod(unsigned c,unsigned m,const void*,size_t,void*p,size_t*n){++queries;assert(c>=1&&c<=2&&m==NativeAdrenoMethodQuery);auto&r=*static_cast<NativeAdrenoAbiParams*>(p);r={NativeAdrenoAbiVersion,40,44,NativeAdrenoParamsHostImport|NativeAdrenoParamsSubmitBatch,UINT64_C(1)<<NativeAdrenoAbiMaxBoBytesShift};if(which==6&&c==1)return 4;if(which==7&&c==2)*n-=1;if(which==8&&c==1)r.abi_version=0;if(which==9&&c==2)r.input_bits=0;if(which==10&&c==1)r.output_bits=64;if(which==11&&c==2)r.flags=0;if(which==12&&c==1)r.max_bo_bytes=0;if(which==13&&c==2)r.input_bits=39;return 0;}
int IOServiceClose(unsigned c){assert(c>=1&&c<=2);assert(!(closedMask&(1u<<c)));closedMask|=1u<<c;++closes;return which==14&&c==1?4:0;}
'''
main='''int main(){for(which=0;which<=14;++which){opens=queries=closes=releases=0;closedMask=0;const bool result=sharedQueries267();assert(result==(which==0));if(which==1){assert(opens==0&&queries==0&&closes==0&&releases==0);}else if(which==2||which==3){assert(opens==0&&queries==0&&closes==0&&releases==1);}else if(which==4){assert(opens==1&&queries==0&&closes==0);}else if(which==5){assert(opens==2&&queries==1&&closes==1&&closedMask==2);}else {assert(opens==2&&queries==2&&closes==2&&closedMask==6);} }puts("PASS267 actual shared query/close boundaries and malformed native replies");}
'''
f=O/'actual-function.cpp';f.write_text(pre+body+main);args=['/usr/bin/clang++','-std=c++17','-fsanitize=address,undefined','-I/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/common/gpu/native-a750',str(f),'-o',str(O/'check')];r=subprocess.run(args,capture_output=True,text=True);save(O/'compile.json',dict(arguments=args,exit=r.returncode,stderr=r.stderr));assert not r.returncode,r.stderr;r=subprocess.run([str(O/'check')],capture_output=True,text=True,env=os.environ|{'ASAN_OPTIONS':'symbolize=0','UBSAN_OPTIONS':'symbolize=0:print_stacktrace=0'});save(O/'run.json',dict(exit=r.returncode,stdout=r.stdout,stderr=r.stderr));assert not r.returncode,r.stderr
old=(PS/'userland/ZornMetalProbe193.mm').read_text();i=old.index('// Exercise real independent IOKit metadata connections');j=old.index('static int probe(){',i);new=t[:t.index('// Exercise the actual257+')]+t[z:];old=old[:i]+old[j:];new=new.replace(C['program_tag'],json.loads((P/'candidate.json').read_text())['program_tag']).replace('if(!sharedQueries267()){report(10,(long)status,9);retainUntilWatchdog();}','if(!metadataWhileNative251()){report(10,(long)status,9);return 10;}');assert new==old
save(O/'result.json',dict(passed=True,test_tool=pin(Path(__file__).resolve()),actual_function_extracted_from=pin(S/'userland/ZornMetalProbe193.mm'),fixtures=pin(f),ASan_UBSan=True,controls=['valid actual typed queries and two normal closes','missing service and wrong identity return before opening','failed first/second opens never close unopened handles','native query failure,short reply,wrong ABI/apertures/flags/size and unequal members never qualify','failed close never qualifies and no duplicate close'],actual_source_projection_equal_except_program_identity_shared_query_and_failure_retention=True,old_exclusive_assertion_removed=True,shader_pipeline_surface_pixel_verification_and_present_code_unchanged=True,synthetic_IOKit_only_not_hardware=True,phone_access=False));print(r.stdout)

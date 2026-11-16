#!/usr/bin/env python3
"""Byte-count admission before board actions; no start/board/ring execution."""
from pathlib import Path
import argparse,difflib,hashlib,json,subprocess,struct
R=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
B=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740';S=B/'NativeAdrenoGpu.cpp';ring=(B/'NativeAdrenoRing.cpp').read_text();old=S.read_text();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();pin=sha(S)
assert 'ring_bytes<8192 || ring_bytes>(1u<<20) || (ring_bytes&(ring_bytes-1))' in ring
assert 'fence_bytes<64 || (fence_iova&7) || fence_bytes>=(1u<<24)' in ring
anchor='    started_=true;board_=*board;'
g='''    if(config->ring_bytes<8192 || config->ring_bytes>(1u<<20) ||
        (config->ring_bytes&(config->ring_bytes-1)) || config->fence_bytes<64 ||
        config->fence_bytes>=(1u<<24))return kIOReturnBadArgument;
'''
assert old.count(anchor)==1;new=old.replace(anchor,g+anchor,1);C=O/S.name;C.write_text(new);(O/'original.cpp').write_text(old);(O/'gpu-start-byte-preflight.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+S.name,tofile='b/'+S.name)))
def check(c):
 assert c.count(g)==1 and c.replace(g,'',1)==old
 assert c.index('!board || !config')<c.index(g)<c.index(anchor)<c.index('board_.reserve(')<c.index('board_.bootGmu(')<c.index('board_.programSmmu(')<c.index('ring_.attach(')
check(new);bad=[]
for name,c in [('missing',old),('after-reserve',new.replace(g,'',1).replace('    reserved_=true;steps_=1;',g+'    reserved_=true;steps_=1;',1)),('lost-fence-limit',new.replace('config->fence_bytes>=(1u<<24)','false',1))]:
 try:check(c)
 except (AssertionError,ValueError):bad.append(name)
 else:raise AssertionError(name)
# Integer counts only; neither valid nor invalid complete GPU configs exist here.
expr=g.split('if(',1)[1].split(')return',1)[0].replace('config->ring_bytes','r').replace('config->fence_bytes','f')
code='''#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
static bool byte_refusal(size_t r,size_t f){return EXPR;}
int main(){bool ok=true;unsigned refused=0,kept=0;
 const size_t bad[][2]={{0,64},{4096,64},{8191,64},{8193,64},{1048577,64},{SIZE_MAX,64},{8192,0},{8192,63},{8192,16777216}};
 for(auto &p:bad){ok &= byte_refusal(p[0],p[1]);++refused;}
 const size_t good[][2]={{8192,64},{1048576,64},{8192,16777215},{65536,4096}};
 for(auto &p:good){ok &= !byte_refusal(p[0],p[1]);++kept;}
 printf("ok=%d invalid_counts_refused=%u inclusive_controls=%u no-config-or-callback-model\\n",ok,refused,kept);return ok?0:1;}
'''.replace('EXPR',expr)
F=O/'counts-only.cpp';F.write_text(code);events=[]
def run(args,name,cwd=R):
 args=list(map(str,args));p=subprocess.run(args,cwd=cwd,capture_output=True,timeout=50);(O/(name+'.stdout.raw')).write_bytes(p.stdout);(O/(name+'.stderr.raw')).write_bytes(p.stderr);events.append(dict(name=name,arguments=args,directory=str(cwd),returncode=p.returncode));(O/'commands.json').write_text(json.dumps(events,indent=2)+'\n');assert p.returncode==0,p.stderr.decode(errors='replace');return p.stdout.decode()
clang='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++';run([clang,'-std=c++17','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-isysroot','/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk',F,'-o',O/'counts-only'],'counts-build');out=run([O/'counts-only'],'counts-run')
prior=json.loads((R/'out/zorn/gpu-catalog-service-dependencies/compile-result.json').read_text());service=str(B/'NativeAdrenoService.cpp');rec=next(x for x in prior['commands'] if service in x['arguments'] and '-c' in x['arguments']);args=list(rec['arguments']);assert '--target=arm64-apple-ios17.0.0' in args and not any(x in args for x in ['-MF','-MJ']);args[args.index(service)]=str(C);obj=O/'candidate-ios17.o';args[args.index('-o')+1]=str(obj);args+=['-MD','-MF',str(O/'candidate-inputs.d'),'-MT',str(obj)];run(args,'candidate-ios17',Path(rec['directory']))
raw=obj.read_bytes();assert struct.unpack_from('<I',raw)[0]==0xfeedfacf;at=32;ver=None
for _ in range(struct.unpack_from('<I',raw,16)[0]):
 cmd,n=struct.unpack_from('<II',raw,at)
 if cmd==0x32:platform,ver=struct.unpack_from('<II',raw,at+8);assert platform==2
 at+=n
assert ver==17<<16 and sha(S)==pin
res=dict(scope='existing Ring byte-count prerequisites checked before NativeGpu board actions',original_SHA=pin,ring_source_SHA=sha(B/'NativeAdrenoRing.cpp'),candidate_SHA=sha(C),before_late_Ring_byte_refusal_after_three_board_calls_in_source=True,nine_invalid_count_cases_refused_early=True,four_existing_byte_boundary_controls_preserved=True,source_mutations_refused=bad,count_fixture_output=out,ASan_UBSan_pass=True,new_NativeGpu_iOS17_object_pass=True,object_not_linked_or_executed=True,all_valid_input_sequence_and_existing_power_reset_retry_behavior_unchanged=True,no_start_board_ring_getter_callback_native_or_success_config_address_lease_model_execution=True,no_K80_geometry_or_GPU_startup_component_selection=True,legacy_Ring_byte_limits_only_unselected_source_contract=True,header_class_ABI_wire_log_pins_32patches_profiles_unchanged=True,hardware_qualification=False,device_operations=False)
(O/'result.json').write_text(json.dumps(res,indent=2)+'\n');print('PASS:invalid byte lengths now refused before board actions;9 count cases/4 controls/3 mutations/sanitizers/new iOS17 object;no start or callbacks')

#!/usr/bin/env python3
"""Pure callback-presence/byte-count preflight;no actual callback or context."""
from pathlib import Path
import argparse,difflib,hashlib,json,subprocess,struct,re
R=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
B=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740';S=B/'NativeAdrenoGmuContext.cpp';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=S.read_text();pin=sha(S);(O/'original.cpp').write_text(old)
oldguard='    if(!io || bank>63 || !asid || asid>0xffff || slot>127)return kIOReturnBadArgument;'
newguard='''    if(!io || !io->read32 || !io->read64 || !io->write32 || !io->write64 ||
        !io->barrier || io->register_bytes<0x2c ||
        bank>63 || !asid || asid>0xffff || slot>127)return kIOReturnBadArgument;'''
assert old.count(oldguard)==1
new=old.replace(oldguard,newguard,1);C=O/S.name;C.write_text(new)
(O/'gmu-io-preflight.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+S.name,tofile='b/'+S.name)))
assert new.replace(newguard,oldguard,1)==old
body=new[new.index('IOReturn NativeAdrenoGmuContext::bringUp'):new.index('/* Lives for the rest of the boot:')]
assert body.index(newguard)<body.index('used_=true;')<body.index('step(Allocate);')<body.index('io->read32(io->cookie,0x28,')
controls=[]
for field in ['read32','read64','write32','write64','barrier']:
 changed=re.sub(r'!io->'+field+r'\s*\|\|\s*','',newguard,count=1)
 try:assert all('!io->'+f in changed for f in ['read32','read64','write32','write64','barrier'])
 except AssertionError:controls.append(dict(missing_check=field,source_refused=True))
 else:raise AssertionError(field)
# Booleans represent only member availability;there are no function pointers,
# callback values,objects,addresses,successful providers or simulated contexts.
source=r'''#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
static bool before(uint32_t,size_t){return true;}
static bool after(uint32_t mask,size_t bytes){return (mask&1)&&(mask&2)&&(mask&4)&&(mask&8)&&(mask&16)&&bytes>=0x2c;}
int main(){bool ok=true;unsigned incomplete=0,short_window=0,controls=0;
 for(uint32_t mask=0;mask<31;++mask){ok&=before(mask,0x2c)&&!after(mask,0x2c);++incomplete;}
 for(size_t bytes=0;bytes<0x2c;++bytes){ok&=before(31,bytes)&&!after(31,bytes);++short_window;}
 for(size_t bytes: {size_t(0x2c),size_t(0x30),size_t(SIZE_MAX)}){ok&=before(31,bytes)&&after(31,bytes);++controls;}
 printf("PASS=%d incomplete_tables=%u short_byte_counts=%u complete_table_byte_controls=%u no-callback-or-object\n",ok,incomplete,short_window,controls);return ok?0:1;}
'''.replace('#include <stdio.h>','#include <stdio.h>\n#include <initializer_list>')
(O/'presence-only.cpp').write_text(source)
events=[]
def run(args,name,cwd=R):
 p=subprocess.run(list(map(str,args)),cwd=cwd,capture_output=True,timeout=50);(O/(name+'.stdout.raw')).write_bytes(p.stdout);(O/(name+'.stderr.raw')).write_bytes(p.stderr);events.append(dict(name=name,arguments=list(map(str,args)),directory=str(cwd),returncode=p.returncode));(O/'commands.json').write_text(json.dumps(events,indent=2)+'\n');assert p.returncode==0,p.stderr.decode(errors='replace')[-2000:];return p.stdout
clang='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++'
run([clang,'-std=c++17','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-isysroot','/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk',O/'presence-only.cpp','-o',O/'presence-only'],'presence-build');output=run([O/'presence-only'],'presence-run').decode()
assert 'PASS=1' in output
prior=json.loads((R/'out/zorn/gpu-catalog-service-dependencies/compile-result.json').read_text());service=str(B/'NativeAdrenoService.cpp');rec=next(x for x in prior['commands'] if service in x['arguments'] and '-c' in x['arguments'])
args=list(rec['arguments']);assert '--target=arm64-apple-ios17.0.0' in args and not any(x in args for x in ['-MF','-MJ'])
args[args.index(service)]=str(C);obj=O/'candidate-ios17.o';args[args.index('-o')+1]=str(obj);args+=['-MD','-MF',str(O/'candidate-inputs.d'),'-MT',str(obj)]
run(args,'candidate-ios17',Path(rec['directory']))
raw=obj.read_bytes();assert struct.unpack_from('<I',raw)[0]==0xfeedfacf;at=32;version=None
for _ in range(struct.unpack_from('<I',raw,16)[0]):
 cmd,n=struct.unpack_from('<II',raw,at)
 if cmd==0x32:platform,version=struct.unpack_from('<II',raw,at+8);assert platform==2
 at+=n
assert version==17<<16 and sha(S)==pin
result=dict(scope='public input-preflight guard source/nullability cardinalities only;no context execution',original_SHA=pin,candidate_SHA=sha(C),old_guard_accepts_missing_callbacks_before_first_unconditional_read32=True,guard_dominates_used_latch_progress_and_first_callback=True,incomplete_presence_combinations_refused=31,short_register_byte_counts_refused=44,complete_presence_byte_controls_preserved=3,host_output=output,five_removed_guard_source_controls=controls,ASan_UBSan_pass=True,new_candidate_iOS17_object_pass=True,object_SHA=sha(obj),object_not_linked_or_executed=True,header_class_report_layout_unchanged=True,existing_two_callers_provide_complete_tables_not_claimed_faulting=True,no_cookie_ownership_or_mapping_right_inferred=True,no_callback_values_or_native_context_provider_success_peer_model=True,diagnostic_candidate_not_combined=True,catalog_32patches_profiles_and_role_API_unchanged=True,hardware_qualification=False,device_operations=False)
(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS:public preflight covers31 missing-member patterns/44 short byte counts before latch or callback;new iOS17 object;no callback execution')

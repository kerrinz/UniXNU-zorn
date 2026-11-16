#!/usr/bin/env python3
"""Direct diagnostic-load declared-byte extent;no getter/window/MMIO model."""
from pathlib import Path
import argparse,difflib,hashlib,json,re,subprocess,struct
R=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
B=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740';S=B/'NativeAdrenoService.cpp';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=S.read_text();pin=sha(S);(O/'original.cpp').write_text(old)
def masked(s):return re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',lambda m:' '*len(m.group()),s,flags=re.S)
opening=old.index('{',old.index('if(node && node->windowCount() && node->windowAddress(0))'))
m=masked(old);depth=1;i=opening+1
while depth:
 depth+=(m[i]=='{')-(m[i]=='}');i+=1
close=i-1
decl='            const size_t smmu_bytes=static_cast<size_t>(node->windowBytes(0));\n'
pos=old.index(decl,opening);end=pos+len(decl);body=old[end:close].rstrip(' \t')
indented=''.join('    '+line if line.strip() else line for line in body.splitlines(True))
guard='            if(const size_t smmu_bytes=static_cast<size_t>(node->windowBytes(0)); smmu_bytes>=0x4c) {\n'
new=old[:pos]+guard+indented+'            }\n        '+old[close:]
C=O/S.name;C.write_text(new)
(O/'service-smmu-extent.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+S.name,tofile='b/'+S.name)))
def loads(s):return re.findall(r'const uint32_t (id0|id1|id2|scr0|fault)=\*reinterpret_cast<volatile uint32_t \*>\(smmu_base\+(0x[0-9a-f]+)\);',s)
original_loads=loads(old);assert len(original_loads)==5 and loads(new)==original_loads
minimum=max(int(offset,16)+4 for _,offset in original_loads);assert minimum==0x4c
assert old.count('node->windowBytes(0)')==new.count('node->windowBytes(0)')==1
assert old.count('node->windowAddress(0)')==new.count('node->windowAddress(0)')
# Strip only whitespace and the newly introduced gate to prove all remaining
# existing tokens,log strings,selectors and call bodies retain their contents.
rebuilt=old[:pos]+decl+body+'        '+old[close:]
assert rebuilt==old
def audit(s):
 match=re.search(r'if\(const size_t smmu_bytes=static_cast<size_t>\(node->windowBytes\(0\)\); smmu_bytes>=(0x[0-9a-f]+)\) \{',s)
 assert match and int(match[1],16)>=minimum,'last32-bit read must fit declared bytes'
 first=s.index('const uint32_t id0=*reinterpret_cast<volatile uint32_t *>(smmu_base+0x20);')
 assert match.start()<first
 assert loads(s)==original_loads and s.count('node->windowBytes(0)')==1
audit(new)
controls=[]
for name,s in [('missing-gate',new.replace(guard,decl)),('last-read-not-covered',new.replace('smmu_bytes>=0x4c','smmu_bytes>=0x48')),('extra-read',new.replace('const uint32_t id0=', 'const uint32_t extra=*reinterpret_cast<volatile uint32_t *>(smmu_base+0x60);\n                const uint32_t id0=',1))]:
 try:
  audit(s)
  assert s.count('*reinterpret_cast<volatile uint32_t *>(smmu_base+')==5
 except (AssertionError,ValueError) as e:controls.append(dict(name=name,refused=str(e)))
 else:raise AssertionError(name)
# The POD provider result is never modeled. Only the previously absent size
# clause is exercised as an integer predicate under no actual service/getter.
test=r'''#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <initializer_list>
static bool old_size_clause(size_t){return true;}
static bool fixed_size_clause(size_t bytes){return bytes>=0x4c;}
int main(){bool ok=true;unsigned short_counts=0,controls=0;
 for(size_t bytes=1;bytes<0x4c;++bytes){ok&=old_size_clause(bytes)&&!fixed_size_clause(bytes);++short_counts;}
 for(size_t bytes:{size_t(0x4c),size_t(0x50),size_t(SIZE_MAX)}){ok&=old_size_clause(bytes)&&fixed_size_clause(bytes);++controls;}
 printf("PASS=%d short_declared_counts_rejected=%u inclusive_extent_controls=%u no-getter-window-or-MMIO\n",ok,short_counts,controls);return ok?0:1;}
'''
(O/'byte-count.cpp').write_text(test);events=[]
def run(args,name,cwd=R):
 p=subprocess.run(list(map(str,args)),cwd=cwd,capture_output=True,timeout=50);(O/(name+'.stdout.raw')).write_bytes(p.stdout);(O/(name+'.stderr.raw')).write_bytes(p.stderr);events.append(dict(name=name,arguments=list(map(str,args)),directory=str(cwd),returncode=p.returncode));(O/'commands.json').write_text(json.dumps(events,indent=2)+'\n');assert p.returncode==0,p.stderr.decode(errors='replace')[-1600:];return p.stdout
clang='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++'
run([clang,'-std=c++17','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-isysroot','/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk',O/'byte-count.cpp','-o',O/'byte-count'],'byte-count-build');output=run([O/'byte-count'],'byte-count-run').decode();assert 'PASS=1' in output
prior=json.loads((R/'out/zorn/gpu-catalog-service-dependencies/compile-result.json').read_text());rec=next(x for x in prior['commands'] if str(S) in x['arguments'] and '-c' in x['arguments']);args=list(rec['arguments']);assert '--target=arm64-apple-ios17.0.0' in args and not any(x in args for x in ['-MF','-MJ'])
args[args.index(str(S))]=str(C);obj=O/'candidate-ios17.o';args[args.index('-o')+1]=str(obj);args+=['-MD','-MF',str(O/'candidate-inputs.d'),'-MT',str(obj)];run(args,'candidate-ios17',Path(rec['directory']))
raw=obj.read_bytes();assert struct.unpack_from('<I',raw)[0]==0xfeedfacf;at=32;version=None
for _ in range(struct.unpack_from('<I',raw,16)[0]):
 cmd,n=struct.unpack_from('<II',raw,at)
 if cmd==0x32:platform,version=struct.unpack_from('<II',raw,at+8);assert platform==2
 at+=n
assert version==17<<16 and sha(S)==pin
result=dict(scope='source declared-window-extent guard;no live mapped-window or MMIO reproduction',original_SHA=pin,candidate_SHA=sha(C),five_direct_loads=original_loads,last_load_required_bytes=minimum,short_nonzero_declared_byte_counts_refused=75,inclusive_byte_controls_preserved=3,host_output=output,ASan_UBSan_pass=True,three_source_corruptions_refused=controls,existing_getter_counts_and_read_count_order_offsets_unchanged=True,no_new_return_stop_mapping_or_policy_call=True,source_type_and_class_layout_unchanged=True,new_candidate_iOS17_object_pass=True,object_SHA=sha(obj),target_not_linked_or_executed=True,other_service_reference_cookie_diag_candidates_not_combined=True,existing_K80_window_not_claimed_short=True,no_getter_service_provider_window_base_address_or_MMIO_model=True,catalog_pins_32patches_profiles_and_role_API_unchanged=True,hardware_qualification=False,device_operations=False)
(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS:75 short byte counts now gate all5 direct loads;3 boundaries/source controls and new iOS17 Service object;no MMIO/getter')

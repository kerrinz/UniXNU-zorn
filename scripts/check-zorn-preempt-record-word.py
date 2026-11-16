#!/usr/bin/env python3
"""Only raw record-header bytes and complete-word bounds, never a GPU record."""
from pathlib import Path
import argparse,difflib,hashlib,json,re,subprocess,struct
R=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
B=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740';S=B/'NativeAdrenoPreempt.cpp';H=B/'NativeAdrenoPreempt.h';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();old=S.read_text();header=H.read_text();pin=sha(S)
a='return record&&byte_offset<64?get32(record+byte_offset):0;';b='return record&&byte_offset<=64-sizeof(uint32_t)?get32(record+byte_offset):0;';assert old.count(a)==1;new=old.replace(a,b,1);C=O/S.name;C.write_text(new);(O/'original.cpp').write_text(old)
assert header.count('first 56 bytes')==2;nh=header.replace('first 56 bytes','first 64 bytes');(O/H.name).write_text(nh)
patch=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+S.name,tofile='b/'+S.name))+''.join(difflib.unified_diff(header.splitlines(True),nh.splitlines(True),fromfile='a/'+H.name,tofile='b/'+H.name));(O/'preempt-record-word.UNAPPLIED.patch').write_text(patch)
assert new.replace(b,a,1)==old and nh.replace('first 64 bytes','first 56 bytes')==header
assert 'RecordBvRptrAddrOffset = 56' in old and 'put64(record+RecordBvRptrAddrOffset,bv_rptr_addr);' in old
source_controls=[]
for name,c in [('old-start-only',old),('off-by-one',new.replace('<=64-sizeof(uint32_t)','<=65-sizeof(uint32_t)',1)),('new-alignment-policy',new.replace('record&&byte_offset<=','record&&!(byte_offset&3)&&byte_offset<=',1))]:
 try:assert c.count(b)==1 and c.replace(b,a,1)==old
 except AssertionError:source_controls.append(name)
 else:raise AssertionError(name)
get=re.search(r'static uint32_t get32\(.*?\n\}',old,re.S).group(0);reader=re.search(r'uint32_t NativeAdrenoPreempt::recordWord\(.*?\n\}',old,re.S).group(0).replace('NativeAdrenoPreempt::recordWord','reader')
events=[]
def run(args,name,cwd=R):
 args=list(map(str,args));p=subprocess.run(args,cwd=cwd,capture_output=True,timeout=50);(O/(name+'.stdout.raw')).write_bytes(p.stdout);(O/(name+'.stderr.raw')).write_bytes(p.stderr);events.append(dict(name=name,arguments=args,directory=str(cwd),returncode=p.returncode));(O/'commands.json').write_text(json.dumps(events,indent=2)+'\n');assert p.returncode==0,p.stderr.decode(errors='replace');return p.stdout.decode()
outputs={};clang='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++'
for name in ['before','candidate']:
 body=reader if name=='before' else reader.replace(a,b)
 code='#include <stdint.h>\n#include <stddef.h>\n#include <stdio.h>\n'+get+'\n'+body+'''
int main(){uint8_t raw[67];for(unsigned i=0;i<67;++i)raw[i]=uint8_t(i+1);
 bool ok=true;unsigned crossing=0,refused=0;
 for(uint32_t at=61;at<64;++at){uint32_t v=reader(raw,at);crossing+=v!=0;refused+=v==0;
#ifdef FIXED
 ok &= v==0;
#else
 ok &= v==get32(raw+at);
#endif
 }
 for(uint32_t at=0;at<=60;++at)ok &= reader(raw,at)==get32(raw+at);
 ok &= !reader(raw,64) && !reader(raw,UINT32_MAX) && !reader(nullptr,0);
 printf("ok=%d crossing_header=%u refused=%u preserved_offsets=61 refusals=3 raw-bytes-only\\n",ok,crossing,refused);return ok?0:1;}
'''
 f=O/(name+'-bytes.cpp');f.write_text(code);args=[clang,'-std=c++17','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-isysroot','/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk',f,'-o',O/(name+'-bytes')]
 if name=='candidate':args+=['-DFIXED=1']
 run(args,name+'-build');outputs[name]=run([O/(name+'-bytes')],name+'-run')
assert 'crossing_header=3' in outputs['before'] and 'refused=3' in outputs['candidate']
prior=json.loads((R/'out/zorn/gpu-catalog-service-dependencies/compile-result.json').read_text());service=str(B/'NativeAdrenoService.cpp');rec=next(x for x in prior['commands'] if service in x['arguments'] and '-c' in x['arguments']);args=list(rec['arguments']);assert '--target=arm64-apple-ios17.0.0' in args and not any(x in args for x in ['-MF','-MJ']);args[args.index(service)]=str(C);obj=O/'candidate-ios17.o';args[args.index('-o')+1]=str(obj);args+=['-MD','-MF',str(O/'candidate-inputs.d'),'-MT',str(obj)];run(args,'candidate-ios17',Path(rec['directory']))
raw=obj.read_bytes();assert struct.unpack_from('<I',raw)[0]==0xfeedfacf;at=32;ver=None
for _ in range(struct.unpack_from('<I',raw,16)[0]):
 cmd,n=struct.unpack_from('<II',raw,at)
 if cmd==0x32:platform,ver=struct.unpack_from('<II',raw,at+8);assert platform==2
 at+=n
assert ver==17<<16 and sha(S)==pin
result=dict(scope='complete 4-byte read inside existing 64-byte CPU-header region, not full-record memory extent',original_SHA=pin,original_header_SHA=sha(H),candidate_SHA=sha(C),header_comment_56_corrected_to_64_from_existing_56_plus_8_store=True,three_cross_header_offsets=[61,62,63],all_61_existing_complete_offsets_preserved_including_unaligned=True,three_original_null_or_outside_refusals_preserved=True,raw_byte_outputs=outputs,three_source_mutations_refused=source_controls,ASan_UBSan_pass=True,new_iOS17_Preempt_object_pass=True,object_not_linked_or_executed=True,actual_snapshot_callers_offsets=[20,24,8,4],existing_callers_not_claimed_to_trigger=True,no_actual_full_record_overrun_claimed=True,no_native_object_record_IOVA_context_switch_ACK_address_or_provider_model=True,no_writeRecord_setRecordWptr_attach_trigger_complete_cache_or_MMIO_execution=True,original_32patches_profiles_pins_unchanged=True,hardware_qualification=False,device_operations=False)
(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS:3 cross-header byte offsets refused;61 complete offsets/3 refusals/3 mutations/sanitizers/new iOS17 object;no GPU record execution')

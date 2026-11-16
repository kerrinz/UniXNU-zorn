#!/usr/bin/env python3
"""Same missing-I/O-table gap in the distinct GPU context;source/compile only."""
from pathlib import Path
import argparse,difflib,hashlib,json,subprocess,re,struct
R=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
B=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740';S=B/'NativeAdrenoGpuContext.cpp';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=S.read_text();pin=sha(S);(O/'original.cpp').write_text(old)
before='    if(!io || !slots || !sids || bank>63 || !asid || asid>0xffff || slots[0]>127 || slots[1]>127 ||'
after='''    if(!io || !io->read32 || !io->read64 || !io->write32 || !io->write64 ||
        !io->barrier || io->register_bytes<0x2c ||
        !slots || !sids || bank>63 || !asid || asid>0xffff || slots[0]>127 || slots[1]>127 ||'''
assert old.count(before)==1
new=old.replace(before,after,1);C=O/S.name;C.write_text(new)
(O/'gpu-context-io-preflight.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+S.name,tofile='b/'+S.name)))
assert new.replace(after,before,1)==old
body=new[new.index('IOReturn NativeAdrenoGpuContext::bringUp'):]
assert body.index(after)<body.index('used_=true;kernel_asid_=asid;')<body.index('step(Allocate);')<body.index('io->read32(io->cookie,0x28,')
controls=[]
for field in ['read32','read64','write32','write64','barrier']:
 changed=re.sub(r'!io->'+field+r'\s*\|\|\s*','',after,count=1)
 assert '!io->'+field not in changed
 controls.append(dict(missing_check=field,source_refused=True))
prior=json.loads((R/'out/zorn/gpu-catalog-service-dependencies/compile-result.json').read_text());service=str(B/'NativeAdrenoService.cpp');rec=next(x for x in prior['commands'] if service in x['arguments'] and '-c' in x['arguments']);args=list(rec['arguments'])
assert '--target=arm64-apple-ios17.0.0' in args and not any(x in args for x in ['-MF','-MJ'])
args[args.index(service)]=str(C);obj=O/'candidate-ios17.o';args[args.index('-o')+1]=str(obj);args+=['-MD','-MF',str(O/'candidate-inputs.d'),'-MT',str(obj)]
p=subprocess.run(args,cwd=rec['directory'],capture_output=True,timeout=50);(O/'candidate.stdout.raw').write_bytes(p.stdout);(O/'candidate.stderr.raw').write_bytes(p.stderr);(O/'commands.json').write_text(json.dumps([dict(name='gpu-context-ios17',arguments=args,directory=rec['directory'],returncode=p.returncode)],indent=2)+'\n');assert p.returncode==0,p.stderr.decode(errors='replace')[-2000:]
raw=obj.read_bytes();assert struct.unpack_from('<I',raw)[0]==0xfeedfacf;at=32;version=None
for _ in range(struct.unpack_from('<I',raw,16)[0]):
 cmd,n=struct.unpack_from('<II',raw,at)
 if cmd==0x32:platform,version=struct.unpack_from('<II',raw,at+8);assert platform==2
 at+=n
assert version==17<<16 and sha(S)==pin
result=dict(scope='second distinct public context same pre-callback argument gap;source/compile only',original_SHA=pin,candidate_SHA=sha(C),five_missing_member_source_controls=controls,guard_before_used_kernel_asid_progress_and_first_read=True,only_initial_IO_completeness_guard_changed=True,slot_sid_bank_and_asid_rules_unchanged=True,header_class_and_report_layout_unchanged=True,new_candidate_iOS17_object_pass=True,object_SHA=sha(obj),object_not_linked_or_executed=True,shared_presence_arithmetic_contract_checked_once_in_GMU_review_not_repeated=True,no_native_context_callback_allocator_provider_or_route_model=True,original_catalog_pins_profiles_and_role_API_unchanged=True,hardware_qualification=False,device_operations=False)
(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS:distinct GPU public preflight now dominates state/progress/first callback;5 source controls/new iOS17 object;no native execution')

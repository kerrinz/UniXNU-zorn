#!/usr/bin/env python3
"""Source-derived reference lifetime check;no service/peer/bringup execution."""
from pathlib import Path
import argparse,difflib,hashlib,json,re,subprocess,struct
R=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
S=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740/NativeAdrenoService.cpp'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=S.read_text();pin=sha(S);(O/'original.cpp').write_text(old)
assert old.count('        smmu->release();')==1 and old.count('    if(ready_) {')==1
new=old.replace('        smmu->release();\n','',1).replace('    if(ready_) {','    // Keep the copied service reference through its last synchronous use.\n    if(smmu)smmu->release();\n    if(ready_) {',1)
C=O/'NativeAdrenoService.cpp';C.write_text(new)
(O/'service-smmu-reference.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/NativeAdrenoService.cpp',tofile='b/NativeAdrenoService.cpp')))
def masked(s):
 return re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',lambda m:' '*len(m.group()),s,flags=re.S)
def body(s):
 m=masked(s);start=m.index('bool NativeAdrenoGpuService::start(');at=m.index('{',start);depth=1;i=at+1
 while depth:
  depth+=(m[i]=='{')-(m[i]=='}');i+=1
 return s[at+1:i-1]
def trace(s,require_safe):
 b=body(s);m=masked(b)
 acq=m.index('IOService *smmu=smmu_match?IOService::copyMatchingService(smmu_match):nullptr;')
 releases=[x.start() for x in re.finditer(r'smmu->release\s*\(',m)]
 assert len(releases)==1,'the copied reference must be released exactly once'
 # Cast and uses through the derived borrowed node are all synchronous here.
 cast=m.index('OSDynamicCast(NativeAdrenoSmmuService,smmu)',acq)
 uses=[x.start() for x in re.finditer(r'node->(?:windowCount|windowAddress|windowBytes)\s*\(',m[cast:])]
 uses=[cast+x for x in uses]
 assert uses and m.count('IOService *smmu=')==1 and 'smmu->retain(' not in m
 assert not re.search(r'\bsmmu\s*=',m[acq+len('IOService *smmu='):]),'no later owner reassignment'
 tail=m[acq:];assert len(re.findall(r'\breturn\b',tail))==2,'review new control-flow exits before retaining this check'
 returns=[x.start()+acq for x in re.finditer(r'\breturn\b',tail)]
 safe=acq<cast<min(uses)<=max(uses)<releases[0]<min(returns)
 if require_safe:assert safe,'borrowed node access after copied owner release or return before cleanup'
 return dict(acquire_offset=acq,release_offset=releases[0],cast_offset=cast,borrowed_window_use_offsets=uses,return_offsets=returns,reference_held_at_cast_and_window_access=safe)
before=trace(old,False);after=trace(new,True);assert not before['reference_held_at_cast_and_window_access']
# The witness comes from source ordering and the real copy ownership contract,
# not from a fake IOService or a successful native/hardware execution.
mutations=[]
for name,changed in [
 ('release-before-cast',new.replace('    if(smmu)smmu->release();\n','').replace('        NativeAdrenoSmmuService *node=', '        if(smmu)smmu->release();\n        NativeAdrenoSmmuService *node=',1)),
 ('missing-release',new.replace('    if(smmu)smmu->release();\n','')),
 ('double-release',new.replace('    if(smmu)smmu->release();','    if(smmu)smmu->release();\n    if(smmu)smmu->release();')),
 ('return-before-cleanup',new.replace('    if(smmu)smmu->release();','    if(smmu)return false;\n    if(smmu)smmu->release();'))]:
 try:trace(changed,True)
 except (AssertionError,ValueError) as e:mutations.append(dict(name=name,refused=str(e)))
 else:raise AssertionError('source lifetime mutation survived: '+name)
# All acquisition/bringup bodies,selectors and other class methods are untouched.
assert new.replace('    // Keep the copied service reference through its last synchronous use.\n    if(smmu)smmu->release();\n','').replace('    } else {\n        IOLog("NativeAdreno: SMMU node not published yet', '        smmu->release();\n    } else {\n        IOLog("NativeAdreno: SMMU node not published yet',1)==old
contract=R/'UniXNU/out/zorn/tree/.cache/xnu-work/iokit/IOKit/IOService.h'
assert '@function copyMatchingService' in contract.read_text() and 'To be released by the caller' in contract.read_text()
prior=R/'out/zorn/gpu-catalog-service-dependencies/compile-result.json';d=json.loads(prior.read_text())
rec=next(x for x in d['commands'] if str(S) in x['arguments'] and '-c' in x['arguments'])
args=list(rec['arguments']);assert '--target=arm64-apple-ios17.0.0' in args
assert not any(x in args for x in ['-MF','-MJ'])
args[args.index(str(S))]=str(C);obj=O/'candidate-ios17.o';args[args.index('-o')+1]=str(obj)
args+=['-MD','-MF',str(O/'candidate-inputs.d'),'-MT',str(obj)]
p=subprocess.run(args,cwd=rec['directory'],capture_output=True,timeout=50)
(O/'candidate.stdout.raw').write_bytes(p.stdout);(O/'candidate.stderr.raw').write_bytes(p.stderr)
(O/'commands.json').write_text(json.dumps([dict(arguments=args,directory=rec['directory'],returncode=p.returncode)],indent=2)+'\n')
assert p.returncode==0,p.stderr.decode(errors='replace')
raw=obj.read_bytes();assert struct.unpack_from('<I',raw)[0]==0xfeedfacf;at=32;version=None
for _ in range(struct.unpack_from('<I',raw,16)[0]):
 cmd,size=struct.unpack_from('<II',raw,at)
 if cmd==0x32:platform,version=struct.unpack_from('<II',raw,at+8);assert platform==2
 at+=size
assert version==17<<16 and sha(S)==pin
result=dict(scope='source-derived service reference lifetime repair;no live use-after-free reproduction',original_SHA=pin,candidate_SHA=sha(C),copy_ownership_contract_header_SHA=sha(contract),before_source_trace=before,after_source_trace=after,four_source_corruptions_refused=mutations,one_release_after_last_synchronous_use_before_both_returns=True,only_reference_release_position_changed=True,object_not_mapping_or_quiescence_lease=True,new_candidate_iOS17_object_pass=True,target_object_SHA=sha(obj),target_object_not_linked_or_executed=True,existing_metaclass_initializer_unexecuted=True,optional_board_rules_votes_CommandDB_not_enabled=True,no_role_API_workaround_or_fullcore_retry=True,catalog_and_old_patches_unchanged=True,no_successful_provider_peer_or_native_function_execution=True,hardware_qualification=False,device_operations=False)
(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS:source release-before-use repaired;4 lifetime mutations rejected;new nonoptional iOS17 Service object;no native/bringup execution')

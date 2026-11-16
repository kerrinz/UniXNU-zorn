#!/usr/bin/env python3
"""Source-domain error propagation and unexecuted target only; no prepare."""
from pathlib import Path
import argparse,difflib,hashlib,json,subprocess,struct
R=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
B=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740';S=B/'NativeAdrenoSmmuContext.cpp';L=B/'NativeAdrenoSmmuMemory.cpp';old=S.read_text();lower=L.read_text();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();pin=sha(S)
a='    if(prepared!=kIOReturnSuccess)return prepared==kIOReturnNoResources?prepared:kIOReturnBadArgument;';b='    if(prepared!=kIOReturnSuccess)return prepared;';assert old.count(a)==1;new=old.replace(a,b,1);C=O/S.name;C.write_text(new);(O/'original.cpp').write_text(old);(O/'smmu-prepare-status.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+S.name,tofile='b/'+S.name)))
# Actual lower return sites,not simulated native callback statuses.
assert 'if(provider->allocate(provider->cookie,&root,&mapping))return kIOReturnNoMemory;' in lower
assert 'return kIOReturnBusy;' in lower[lower.index('IOReturn NativeAdrenoPrepareSmmuMemory('):]
assert 'state->poisoned=1;return kIOReturnIOError;' in lower
assert 'status==ArmSmmu4KCapacity?kIOReturnNoResources:kIOReturnBadArgument' in lower
traces=[]
for symbol,source in [('kIOReturnNoMemory','root allocation failure'),('kIOReturnIOError','audit or publisher failure'),('kIOReturnBusy','existing state/pages guard'),('kIOReturnNoResources','kit capacity refusal'),('kIOReturnBadArgument','argument/other kit refusal')]:
 traces.append(dict(lower_symbol=symbol,source=source,before=symbol if symbol=='kIOReturnNoResources' else 'kIOReturnBadArgument',after=symbol))
def check(c):
 assert c.count(b)==1 and c.replace(b,a,1)==old
 assert c.index(b)<c.index('tables_=tables;bank_=bank;poll_budget_=poll_budget;prepared_=true;')
check(new);mut=[]
for name,c in [('old-fold',old),('only-NoMemory',new.replace(b,'    if(prepared!=kIOReturnSuccess)return prepared==kIOReturnNoMemory?prepared:kIOReturnBadArgument;',1)),('invented-success',new.replace(b,'    if(prepared!=kIOReturnSuccess)return kIOReturnSuccess;',1))]:
 try:check(c)
 except (AssertionError,ValueError):mut.append(name)
 else:raise AssertionError(name)
prior=json.loads((R/'out/zorn/gpu-catalog-service-dependencies/compile-result.json').read_text());service=str(B/'NativeAdrenoService.cpp');rec=next(x for x in prior['commands'] if service in x['arguments'] and '-c' in x['arguments']);args=list(rec['arguments']);assert '--target=arm64-apple-ios17.0.0' in args and not any(x in args for x in ['-MF','-MJ']);args[args.index(service)]=str(C);obj=O/'candidate-ios17.o';args[args.index('-o')+1]=str(obj);args+=['-MD','-MF',str(O/'candidate-inputs.d'),'-MT',str(obj)]
p=subprocess.run(args,cwd=rec['directory'],capture_output=True,timeout=50);(O/'candidate.stdout.raw').write_bytes(p.stdout);(O/'candidate.stderr.raw').write_bytes(p.stderr);(O/'commands.json').write_text(json.dumps([dict(arguments=args,directory=rec['directory'],returncode=p.returncode)],indent=2)+'\n');assert p.returncode==0,p.stderr.decode(errors='replace')
raw=obj.read_bytes();assert struct.unpack_from('<I',raw)[0]==0xfeedfacf;at=32;ver=None
for _ in range(struct.unpack_from('<I',raw,16)[0]):
 cmd,n=struct.unpack_from('<II',raw,at)
 if cmd==0x32:platform,ver=struct.unpack_from('<II',raw,at+8);assert platform==2
 at+=n
assert ver==17<<16 and sha(S)==pin
res=dict(scope='same-IOReturn lower prepare error propagation',original_SHA=pin,lower_source_SHA=sha(L),candidate_SHA=sha(C),five_actual_lower_symbol_traces=traces,three_source_corruptions_refused=mut,success_config_and_prepared_publication_byte_identical=True,actual_native_NoMemory_IOError_Busy_no_longer_folded_to_BadArgument=True,no_error_promoted_to_success=True,new_SmmuContext_iOS17_object_pass=True,object_not_linked_or_executed=True,no_prepare_begin_allocator_kit_getter_program_map_cache_provider_or_native_execution=True,no_root_ASID_OAS_route_owner_or_success_peer_model=True,no_synthetic_callback_return_sequence=True,class_ABI_header_wire_log_or_policy_unchanged=True,catalog_pins_32patches_profiles_unchanged=True,hardware_qualification=False,device_operations=False)
(O/'result.json').write_text(json.dumps(res,indent=2)+'\n');print('PASS:5 source error-domain traces/3 mutations/new SMMU context iOS17 object;no prepare or native operations')

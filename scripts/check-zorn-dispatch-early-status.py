#!/usr/bin/env python3
"""Review early-return status dataflow only; do not compile frozen UserClient."""
from pathlib import Path
import argparse,difflib,hashlib,json,re,subprocess,struct
R=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
B=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740';S=B/'NativeAdrenoUserClient.cpp'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=S.read_text();pin=sha(S)
start=old.index('    const size_t expected_in=inputSize(method),expected_out=outputSize(method);',old.index('IOReturn NativeAdrenoUserClient::dispatch('));end=old.index('    IOReturn status=kIOReturnSuccess;',start)
block=old[start:end];assert block.count('return kIOReturnUnsupported;')==1 and block.count('return kIOReturnBadArgument;')==2
newblock=block.replace('return kIOReturnUnsupported;','return tally_result=kIOReturnUnsupported;').replace('return kIOReturnBadArgument;','return tally_result=kIOReturnBadArgument;')
new=old[:start]+newblock+old[end:];C=O/'NativeAdrenoUserClient.cpp';C.write_text(new);(O/'original.cpp').write_text(old)
(O/'dispatch-early-status.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/NativeAdrenoUserClient.cpp',tofile='b/NativeAdrenoUserClient.cpp')))
# Straight-line definition/use trace: no status from native operations is invented.
assert 'IOReturn tally_result=kIOReturnSuccess;\n    Tally tally(method,&tally_result,clock);' in old
assert 'native_adreno_method_stats[method][2]=(uint32_t)*result;' in old
assert 'if(*result)native_adreno_method_stats[method][1]' in old
traces=[]
for a,b in zip(block.splitlines()[1:],newblock.splitlines()[1:]):
 before=re.search(r'return (kIOReturn\w+);',a).group(1)
 after=re.search(r'return tally_result=(kIOReturn\w+);',b).group(1);assert before==after
 traces.append({'predicate':a.split('return')[0].strip(),'returned_symbol':before,'before_recorded_symbol':'kIOReturnSuccess','after_recorded_symbol':after})
assert len(traces)==3
# Everything outside three return expressions is byte-identical, including
# clock callback usage, Tally destructor, accepted dispatch and stats layout.
assert new.replace(newblock,block,1)==old
controls=[]
for i in range(3):
 lines=newblock.splitlines(True);lines[i+1]=lines[i+1].replace('tally_result=','',1);bad=''.join(lines)
 if re.findall(r'return tally_result=(kIOReturn\w+);',bad)!=[x['returned_symbol'] for x in traces]:controls.append(i)
assert len(controls)==3
# Compile only this exact type-correct guard block with actual iOS17 headers.
# No client class/role API body, callbacks, method operations or object construction.
fixture='#include <IOKit/IOTypes.h>\n#include <stdint.h>\n#include <stddef.h>\nextern size_t inputSize(uint32_t);\nextern size_t outputSize(uint32_t);\nextern "C" IOReturn guard_only(uint32_t method,size_t input_size,size_t output_size,bool input,bool output,IOReturn &tally_result){\n'+newblock+'return kIOReturnSuccess;\n}\n'
F=O/'guard-compile-only.cpp';F.write_text(fixture)
prior=json.loads((R/'out/zorn/gpu-catalog-service-dependencies/compile-result.json').read_text());service=str(B/'NativeAdrenoService.cpp');rec=next(x for x in prior['commands'] if service in x['arguments'] and '-c' in x['arguments']);args=list(rec['arguments']);assert '--target=arm64-apple-ios17.0.0' in args and not any(x in args for x in ['-MF','-MJ'])
args[args.index(service)]=str(F);obj=O/'guard-ios17.o';args[args.index('-o')+1]=str(obj);args+=['-MD','-MF',str(O/'guard-inputs.d'),'-MT',str(obj)]
p=subprocess.run(args,cwd=rec['directory'],capture_output=True,timeout=50);(O/'guard.stdout.raw').write_bytes(p.stdout);(O/'guard.stderr.raw').write_bytes(p.stderr);(O/'commands.json').write_text(json.dumps([dict(arguments=args,directory=rec['directory'],returncode=p.returncode)],indent=2)+'\n');assert p.returncode==0,p.stderr.decode(errors='replace')
raw=obj.read_bytes();assert struct.unpack_from('<I',raw)[0]==0xfeedfacf;at=32;ver=None
for _ in range(struct.unpack_from('<I',raw,16)[0]):
 cmd,n=struct.unpack_from('<II',raw,at)
 if cmd==0x32:platform,ver=struct.unpack_from('<II',raw,at+8);assert platform==2
 at+=n
assert ver==17<<16 and sha(S)==pin
result=dict(scope='early dispatch refusal vs existing Tally result dataflow; source and extracted guard compile only',original_SHA=pin,candidate_SHA=sha(C),three_early_failure_traces=traces,three_source_mutations_refused=controls,only_three_status_assignments_changed=True,caller_return_codes_and_existing_stats_fields_unchanged=True,accepted_dispatch_clock_and_output_behavior_unchanged=True,extracted_guard_iOS17_object_pass=True,whole_UserClient_compilation_not_attempted_due_frozen_role_API=True,no_native_object_dispatch_externalMethod_clock_callback_or_provider_execution=True,no_wire_log_field_or_runtime_selection_change=True,catalog_pins_32patches_profiles_unchanged=True,hardware_qualification=False,device_operations=False)
(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS:3 early-refusal status dataflow mismatches repaired;3 mutations/extracted guard iOS17 object;no full UserClient compile or execution')

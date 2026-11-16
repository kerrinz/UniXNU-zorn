#!/usr/bin/env python3
"""CP public callback presence/argument classification, source+compile only."""
from pathlib import Path
import argparse,difflib,hashlib,json,subprocess,struct
R=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
B=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740';S=B/'NativeAdrenoCpInit.cpp';old=S.read_text();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();pin=sha(S)
a='    if(config->sqe_base_programmed) {'
g='    if(config->sqe_base_programmed && !io->read32)return kIOReturnBadArgument;\n'
assert old.count(a)==1 and old.count('if(!io->read32 || io->read32(')==1
new=old.replace(a,g+a,1).replace('if(!io->read32 || io->read32(','if(io->read32(',1)
C=O/S.name;C.write_text(new);(O/'original.cpp').write_text(old)
(O/'cp-read-preflight.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+S.name,tofile='b/'+S.name)))
def check(c):
 assert c.count(g)==1 and 'if(!io->read32 || io->read32(' not in c
 inverse=c.replace(g,'',1).replace('if(io->read32(io->cookie,CpSqeInstrBase,','if(!io->read32 || io->read32(io->cookie,CpSqeInstrBase,',1);assert inverse==old
 assert c.index('!config ||')<c.index(g)<c.index(a)<c.index('io->read32(io->cookie,CpSqeInstrBase,')
 assert c.index(g)<c.index('io->write32(io->cookie,CpSqeInstrBase,')
check(new);mut=[]
for name,c in [('removed',new.replace(g,'',1)),('unconditional-read-requirement',new.replace('if(config->sqe_base_programmed && !io->read32)','if(!io->read32)',1)),('still-poisons-invalid-argument',new.replace(g,g.replace('kIOReturnBadArgument','poison()'),1))]:
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
res=dict(scope='missing read32 in public already-programmed mode is argument refusal,not hardware failure',original_SHA=pin,candidate_SHA=sha(C),source_before='nonzero sqe_base_programmed and missing read32 short-circuits before callbacks but calls poison();next call NotReady',source_after='same missing member rejected BadArgument before any callback,not poisoning;no internal retry added',write_mode_read32_requirement_not_added=True,nonnull_callback_failure_and_readback_mismatch_still_poison=True,all_valid_calls_order_payloads_parameters_and_fence_behavior_unchanged=True,source_corruptions_refused=mut,new_CpInit_iOS17_object_pass=True,object_not_linked_or_executed=True,known_retained_Service_and_NativeGpu_callers_mode_zero=True,known_callers_or_K80_failure_not_claimed=True,no_run_poison_ring_getter_callback_allocator_readback_native_or_success_peer_execution=True,no_CP_ME_INIT_firmware_pwrup_or_K80_parameter_generation_selection=True,layout_ABI_wire_logs_pins_32patches_profiles_unchanged=True,hardware_qualification=False,device_operations=False)
(O/'result.json').write_text(json.dumps(res,indent=2)+'\n');print('PASS:missing read member classified before poison;3 source controls/new iOS17 CP object;no run or callbacks')

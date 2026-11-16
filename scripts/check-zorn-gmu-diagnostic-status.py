#!/usr/bin/env python3
"""Source-only diagnostic return preservation;callbacks are never executed."""
from pathlib import Path
import argparse,difflib,hashlib,json,re,subprocess,struct
R=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
B=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740';S=B/'NativeAdrenoGmuContext.cpp';H=B/'NativeAdrenoGmuContext.h';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=S.read_text();oldh=H.read_text();(O/'original.cpp').write_text(old);(O/'original.h').write_text(oldh)
calls=[('32','0x800+4*slot','smr'),('32','0xc00+4*slot','s2cr'),('32','page+4*bank','cbar'),('32','size_t(program->context_offset)','sctlr'),('64','size_t(program->context_offset)+0x20','ttbr0')]
new=old
for i,(width,offset,field) in enumerate(calls):
 line=f'    io->read{width}(io->cookie,{offset},&r->{field});'
 replacement=f'''    r->diagnostic_attempted_mask|=1u<<{i};
    const int status{i}=io->read{width}(io->cookie,{offset},&r->{field});
    r->diagnostic_status[{i}]=status{i};
    r->diagnostic_returned_mask|=1u<<{i};
    if(!status{i})r->diagnostic_zero_mask|=1u<<{i};'''
 assert new.count(line)==1;new=new.replace(line,replacement,1)
needle='    uint32_t mismatch;\n};'
fields='''    uint32_t mismatch;
    /* Best-effort diagnostic callback returns,independent of primary status
     * and program_readback_valid. A zero status without a returned bit is
     * unknown,not success. Raw int returns are not underlying IOKit/EFI errors.
     * Bits/status order:SMR,S2CR,CBAR,SCTLR,TTBR0. No wire/log ABI is added. */
    uint32_t diagnostic_attempted_mask,diagnostic_returned_mask,diagnostic_zero_mask;
    int32_t diagnostic_status[5];
};'''
assert oldh.count(needle)==1;newh=oldh.replace(needle,fields,1)
new=new.replace('static void readBack(', 'static_assert(sizeof(int)==sizeof(int32_t),"preserve callback int width");\n\nstatic void readBack(',1)
C=O/S.name;CH=O/H.name;C.write_text(new);CH.write_text(newh)
patch=''
for name,before,after in [(S.name,old,new),(H.name,oldh,newh)]:patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(O/'gmu-diagnostic-status.UNAPPLIED.patch').write_text(patch)
def helper(s):return s[s.index('static void readBack('):s.index('IOReturn NativeAdrenoGmuContext::bringUp')]
def audit(s):
 b=helper(s)
 assert b.count('io->read32(')==4 and b.count('io->read64(')==1
 assert 'if(!program->context_offset || !program->id1)return;' in b
 previous=-1
 for i,(width,offset,field) in enumerate(calls):
  attempted=b.index(f'r->diagnostic_attempted_mask|=1u<<{i};')
  call=b.index(f'const int status{i}=io->read{width}(io->cookie,{offset},&r->{field});')
  capture=b.index(f'r->diagnostic_status[{i}]=status{i};')
  returned=b.index(f'r->diagnostic_returned_mask|=1u<<{i};')
  zero=b.index(f'if(!status{i})r->diagnostic_zero_mask|=1u<<{i};')
  assert previous<attempted<call<capture<returned<zero
  previous=zero
 assert 'report->status' not in b and 'ready_' not in b and 'return status' not in b
audit(new)
controls=[]
for name,s in [('lost-raw-return',new.replace('r->diagnostic_status[3]=status3;','r->diagnostic_status[3]=0;')),
 ('false-zero',new.replace('if(!status1)r->diagnostic_zero_mask','if(true)r->diagnostic_zero_mask')),
 ('lost-return-availability',new.replace('r->diagnostic_returned_mask|=1u<<4;','')),
 ('extra-MMIO',new.replace('const int status0=io->read32','io->read32(io->cookie,0x800+4*slot,&r->smr);\n    const int status0=io->read32'))]:
 try:audit(s)
 except (AssertionError,ValueError) as e:controls.append(dict(name=name,refused=str(e)))
 else:raise AssertionError(name)
assert old[old.index('IOReturn NativeAdrenoGmuContext::bringUp'):]==new[new.index('IOReturn NativeAdrenoGmuContext::bringUp'):]
assert old.count('io->read32(io->cookie,')==new.count('io->read32(io->cookie,')
assert old.count('io->read64(io->cookie,')==new.count('io->read64(io->cookie,')
service=B/'NativeAdrenoService.cpp';(O/service.name).write_bytes(service.read_bytes())
layout=O/'report-layout.cpp';layout.write_text('#include "NativeAdrenoGmuContext.h"\nstatic_assert(sizeof(NativeAdrenoGmuContextReport)==176);\nstatic_assert(sizeof(NativeAdrenoGmuContextReport::diagnostic_status)==20);\nconstinit NativeAdrenoGmuContextReport review_report{};\n')
prior=json.loads((R/'out/zorn/gpu-catalog-service-dependencies/compile-result.json').read_text());rec=next(x for x in prior['commands'] if str(service) in x['arguments'] and '-c' in x['arguments']);events=[];objects={}
for label,source in [('context',C),('caller',O/service.name),('report-layout',layout)]:
 args=list(rec['arguments']);assert '--target=arm64-apple-ios17.0.0' in args and not any(x in args for x in ['-MF','-MJ'])
 args[args.index(str(service))]=str(source);obj=O/(label+'-ios17.o');args[args.index('-o')+1]=str(obj);args+=['-I'+str(O),'-MD','-MF',str(O/(label+'-inputs.d')),'-MT',str(obj)]
 p=subprocess.run(args,cwd=rec['directory'],capture_output=True,timeout=50);(O/(label+'.stdout.raw')).write_bytes(p.stdout);(O/(label+'.stderr.raw')).write_bytes(p.stderr);events.append(dict(name=label,arguments=args,directory=rec['directory'],returncode=p.returncode));(O/'commands.json').write_text(json.dumps(events,indent=2)+'\n');assert p.returncode==0,p.stderr.decode(errors='replace')
 raw=obj.read_bytes();assert struct.unpack_from('<I',raw)[0]==0xfeedfacf;at=32;version=None
 for _ in range(struct.unpack_from('<I',raw,16)[0]):
  cmd,n=struct.unpack_from('<II',raw,at)
  if cmd==0x32:platform,version=struct.unpack_from('<II',raw,at+8);assert platform==2
  at+=n
 assert version==17<<16 and str(CH) in (O/(label+'-inputs.d')).read_text()
 objects[label]=dict(SHA256=sha(obj),minimum_OS='17.0',candidate_header_used=True,executed=False)
caller_log=(O/'caller.stdout.raw').read_text();i=caller_log.index('struct NativeAdrenoGmuContextReport\n');j=caller_log.index('[sizeof=',i);assert caller_log[j:].startswith('[sizeof=176,')
assert sha(S)==hashlib.sha256(old.encode()).hexdigest() and sha(H)==hashlib.sha256(oldh.encode()).hexdigest()
result=dict(scope='source diagnostic callback-return loss repair;no callback behavior test or native observation',original_CPP_SHA=sha(S),original_header_SHA=sha(H),candidate_CPP_SHA=sha(C),candidate_header_SHA=sha(CH),before_five_callback_returns_discarded=True,after_five_raw_int_returns_with_attempted_returned_zero_masks=True,four_source_corruptions_refused=controls,callback_count_order_offsets_unchanged=True,primary_bringUp_body_status_and_ready_unchanged=True,diagnostic_failure_not_promoted_to_startup_failure=True,historical_report_bytes=144,candidate_report_bytes=176,report_ABI_requires_consistent_caller_rebuild=True,new_iOS17_objects=objects,no_wire_log_carrier_or_field_expansion=True,no_callback_readBack_bringUp_service_native_or_MMIO_execution=True,no_synthetic_return_values_or_success_peer=True,catalog_old_patches_and_profiles_unchanged=True,hardware_qualification=False,device_operations=False)
(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS:5 diagnostic returns source-preserved with explicit unknown masks;4 source controls;context/caller/report iOS17 objects;no callback execution')

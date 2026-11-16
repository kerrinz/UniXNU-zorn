#!/usr/bin/env python3
"""Static IRQ partial-result dataflow and unexecuted iOS17 objects only."""
from pathlib import Path
import argparse,difflib,hashlib,json,subprocess,struct
R=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
B=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740';S=B/'NativeAdrenoIrq.cpp';H=B/'NativeAdrenoIrq.h';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();old=S.read_text();hdr=H.read_text();pin=sha(S)
nh=hdr.replace('struct NativeAdrenoIrqResult {','enum NativeAdrenoIrqValid {\n    NativeAdrenoIrqStatusValid=1u<<0,NativeAdrenoIrqCpStatusValid=1u<<1,\n    NativeAdrenoIrqProtectValid=1u<<2,NativeAdrenoIrqDecoded=1u<<3\n};\nstruct NativeAdrenoIrqResult {',1).replace('uint32_t flags, status, unknown, cp_status, protect_status;','uint32_t flags, status, unknown, cp_status, protect_status;\n    /* Only marked raw fields are available; Decoded marks flags/unknown.\n     * Clear/barrier failure preserves earlier reads, not an ACK or stop proof. */\n    uint32_t valid_fields;',1)
nh=nh.replace('Acknowledgement precedes decoding so\n     * an error reported here cannot be hidden by a later clear failure.','Successfully read raw fields remain available even if acknowledgement or\n     * decoding later fails; valid_fields distinguishes absence from zero.')
new=old.replace('    /* Linux acknowledges the whole read status before decoding it. */','    result->status=status;result->valid_fields|=NativeAdrenoIrqStatusValid;\n    /* Linux acknowledges the whole read status before decoding it. */',1)
new=new.replace('        if(cp_status&kCpErrors) {','        result->cp_status=cp_status;result->valid_fields|=NativeAdrenoIrqCpStatusValid;\n        if(cp_status&kCpErrors) {',1)
new=new.replace('            flags|=NativeAdrenoIrqCpError;','            result->protect_status=protect;result->valid_fields|=NativeAdrenoIrqProtectValid;\n            flags|=NativeAdrenoIrqCpError;',1)
new=new.replace('    result->cp_status=cp_status;result->protect_status=protect;','    result->cp_status=cp_status;result->protect_status=protect;\n    result->valid_fields|=NativeAdrenoIrqDecoded;',1)
C=O/S.name;C.write_text(new);(O/H.name).write_text(nh);(O/'original.cpp').write_text(old);(O/'original.h').write_text(hdr)
adds=['    result->status=status;result->valid_fields|=NativeAdrenoIrqStatusValid;\n','        result->cp_status=cp_status;result->valid_fields|=NativeAdrenoIrqCpStatusValid;\n','            result->protect_status=protect;result->valid_fields|=NativeAdrenoIrqProtectValid;\n','    result->valid_fields|=NativeAdrenoIrqDecoded;\n']
def check(c):
 inverse=c
 for text in adds:assert inverse.count(text)==1;inverse=inverse.replace(text,'',1)
 assert inverse==old
 assert c.index('if(io_.read32(io_.cookie,IrqRbbmStatus,&status))return poison();')<c.index(adds[0])<c.index('if(io_.write32(io_.cookie,IrqRbbmClear,status))return poison();')
 assert c.index('if(io_.read32(io_.cookie,IrqCpStatus,&cp_status))return poison();')<c.index(adds[1])<c.index('if(io_.read32(io_.cookie,IrqCpProtect,&protect))return poison();')<c.index(adds[2])<c.index(adds[3])
check(new);refused=[]
for i in range(4):
 try:check(new.replace(adds[i],'',1))
 except (AssertionError,ValueError):refused.append(i)
 else:raise AssertionError(i)
(O/'irq-partial-result.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+S.name,tofile='b/'+S.name))+''.join(difflib.unified_diff(hdr.splitlines(True),nh.splitlines(True),fromfile='a/'+H.name,tofile='b/'+H.name)))
events=[]
def run(args,name,cwd):
 args=list(map(str,args));p=subprocess.run(args,cwd=cwd,capture_output=True,timeout=50);(O/(name+'.stdout.raw')).write_bytes(p.stdout);(O/(name+'.stderr.raw')).write_bytes(p.stderr);events.append(dict(name=name,arguments=args,directory=str(cwd),returncode=p.returncode));(O/'commands.json').write_text(json.dumps(events,indent=2)+'\n');assert p.returncode==0,p.stderr.decode(errors='replace')
prior=json.loads((R/'out/zorn/gpu-catalog-service-dependencies/compile-result.json').read_text());service=str(B/'NativeAdrenoService.cpp');rec=next(x for x in prior['commands'] if service in x['arguments'] and '-c' in x['arguments'])
F=O/'result-layout.cpp';F.write_text('#include "NativeAdrenoIrq.h"\n#include <stddef.h>\nstatic_assert(sizeof(NativeAdrenoIrqResult)==24);\nstatic_assert(offsetof(NativeAdrenoIrqResult,valid_fields)==20);\nstatic_assert(NativeAdrenoIrqDecoded==8);\nstatic_assert(__is_trivially_copyable(NativeAdrenoIrqResult));\n')
for source,name in [(C,'candidate'),(F,'layout')]:
 args=list(rec['arguments']);assert '--target=arm64-apple-ios17.0.0' in args and not any(x in args for x in ['-MF','-MJ']);args[args.index(service)]=str(source);obj=O/(name+'-ios17.o');args[args.index('-o')+1]=str(obj);args+=['-MD','-MF',str(O/(name+'-inputs.d')),'-MT',str(obj)];run(args,name+'-ios17',Path(rec['directory']))
 raw=obj.read_bytes();assert struct.unpack_from('<I',raw)[0]==0xfeedfacf;at=32;ver=None
 for _ in range(struct.unpack_from('<I',raw,16)[0]):
  cmd,n=struct.unpack_from('<II',raw,at)
  if cmd==0x32:platform,ver=struct.unpack_from('<II',raw,at+8);assert platform==2
  at+=n
 assert ver==17<<16
assert sha(S)==pin
result=dict(scope='partial raw IRQ result availability,source/compile only',original_SHA=pin,original_header_SHA=sha(H),candidate_SHA=sha(C),before_status_read_lost_on_clear_or_barrier_failure=True,before_cp_status_lost_on_protect_failure=True,after_only_successfully_returned_read_fields_published=True,availability_zero_is_unknown_not_zero_status_or_ACK=True,decode_marker_only_at_original_success_end=True,callback_order_primary_returns_poison_and_mask_unchanged=True,source_corruptions_refused=refused,report_bytes_before=20,report_bytes_after=24,consistent_future_consumers_rebuild_required=True,changed_Irq_and_POD_layout_iOS17_objects_pass=True,no_host_callback_readback_IRQ_or_native_execution=True,no_synthetic_success_peer_or_return_value_model=True,no_wire_log_mask_route_owner_or_runtime_selection_change=True,preallocated_GMU_IRQ_HFI_domains_not_combined=True,programMask_existing_optional_output_review_no_new_fix=True,hardware_qualification=False,device_operations=False)
(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS:partial-read source dataflow/4 mutations/new IRQ+POD iOS17 objects;no callback/readback/IRQ/native execution')

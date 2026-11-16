#!/usr/bin/env python3
"""Persistent cookie storage source repair;never constructs a native peer."""
from pathlib import Path
import argparse,difflib,hashlib,json,re,subprocess,struct
R=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
B=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740';S=B/'NativeAdrenoService.cpp'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=S.read_text();pin=sha(S);(O/'original.cpp').write_text(old)
definition='''struct NativeAdrenoSmmuWindow {
    volatile uint8_t *base;
    size_t bytes;
};
'''
member='    NativeAdrenoSmmuWindow smmu_window_{};   /* retained I/O cookie storage;not a mapping lease */\n'
assert old.count(definition)==1
new=old.replace(definition,'',1).replace('class NativeAdrenoGpuService : public IOService {',definition+'class NativeAdrenoGpuService : public IOService {',1)
anchor='    NativeAdrenoGpuWindow ring_window_{};   /* the ring keeps a pointer to it: it must outlive start() */\n'
assert new.count(anchor)==1;new=new.replace(anchor,anchor+member,1)
assert new.count('NativeAdrenoSmmuWindow window{smmu_base,smmu_bytes};')==1
new=new.replace('NativeAdrenoSmmuWindow window{smmu_base,smmu_bytes};','smmu_window_={smmu_base,smmu_bytes};',1).replace('ArmSmmu4KIo smmu_io{&window,smmu_bytes,','ArmSmmu4KIo smmu_io{&smmu_window_,smmu_bytes,',1)
C=O/'NativeAdrenoService.cpp';C.write_text(new)
(O/'service-smmu-cookie.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/NativeAdrenoService.cpp',tofile='b/NativeAdrenoService.cpp')))
context=(B/'NativeAdrenoGmuContext.cpp').read_text();smmu=(B/'NativeAdrenoSmmuContext.cpp').read_text();vm=(B/'NativeAdrenoVm.cpp').read_text()
assert 'status=smmu_.program(io);' in context and 'status=vm_.attach(io,' in context
assert 'io_=*io;programmed_=true;' in smmu and 'io_=*io;context_=context;' in vm
assert 'ArmSmmu4KObserveOwnedContext(&io_' in smmu and 'ArmSmmu4KSyncContextTlb(&io_' in vm
# Source witness: consumers retain a copied io whose cookie is a pointer,not a
# deep copy of the automatic window. No context/VM/allocator runs in this check.
assert 'NativeAdrenoSmmuWindow window{smmu_base,smmu_bytes};' in old
assert 'ArmSmmu4KIo smmu_io{&window,' in old
assert new.index(definition)<new.index('class NativeAdrenoGpuService : public IOService')
def audit(s):
 start=s.index('class NativeAdrenoGpuService : public IOService');end=s.index('\n};',start)
 assert member.strip() in s[start:end],'cookie must be an owned service member'
 assert 'NativeAdrenoSmmuWindow window{' not in s,'no automatic cookie owner'
 assert 'smmu_window_={smmu_base,smmu_bytes};' in s,'same supplied descriptor fields'
 assert 'ArmSmmu4KIo smmu_io{&smmu_window_,smmu_bytes,' in s,'copied io must point at persistent window'
 assert s.index('smmu_window_={smmu_base,smmu_bytes};')<s.index('gmu_ctx_.bringUp(&smmu_io,'),'initialize before borrowing'
audit(new)
mutations=[]
for name,changed in [
 ('automatic-owner-restored',new.replace('smmu_window_={smmu_base,smmu_bytes};','NativeAdrenoSmmuWindow window{smmu_base,smmu_bytes};').replace('smmu_io{&smmu_window_,','smmu_io{&window,')),
 ('null-cookie',new.replace('smmu_io{&smmu_window_,','smmu_io{nullptr,')),
 ('member-removed',new.replace(member,'')),
 ('borrow-before-initialize',new.replace('                smmu_window_={smmu_base,smmu_bytes};\n','').replace('IOReturn status=gmu_ctx_.bringUp(&smmu_io,bank,asid,slot,uint16_t(sid),nullptr,&report);','IOReturn status=gmu_ctx_.bringUp(&smmu_io,bank,asid,slot,uint16_t(sid),nullptr,&report);\n                smmu_window_={smmu_base,smmu_bytes};'))]:
 try:audit(changed)
 except (AssertionError,ValueError) as e:mutations.append(dict(name=name,refused=str(e)))
 else:raise AssertionError(name)
# Reversing precisely the storage edits must reconstruct the complete original.
back=new.replace(member,'').replace(definition,'',1).replace('static int smmu_read32(',definition+'static int smmu_read32(',1).replace('smmu_window_={smmu_base,smmu_bytes};','NativeAdrenoSmmuWindow window{smmu_base,smmu_bytes};',1).replace('ArmSmmu4KIo smmu_io{&smmu_window_,','ArmSmmu4KIo smmu_io{&window,',1)
assert back==old
prior=json.loads((R/'out/zorn/gpu-catalog-service-dependencies/compile-result.json').read_text());rec=next(x for x in prior['commands'] if str(S) in x['arguments'] and '-c' in x['arguments'])
args=list(rec['arguments']);assert '--target=arm64-apple-ios17.0.0' in args and not any(x in args for x in ['-MF','-MJ'])
args[args.index(str(S))]=str(C);obj=O/'candidate-ios17.o';args[args.index('-o')+1]=str(obj);args+=['-MD','-MF',str(O/'candidate-inputs.d'),'-MT',str(obj)]
p=subprocess.run(args,cwd=rec['directory'],capture_output=True,timeout=50);(O/'candidate.stdout.raw').write_bytes(p.stdout);(O/'candidate.stderr.raw').write_bytes(p.stderr)
(O/'commands.json').write_text(json.dumps([dict(arguments=args,directory=rec['directory'],returncode=p.returncode)],indent=2)+'\n');assert p.returncode==0,p.stderr.decode(errors='replace')
log=p.stdout.decode();start=log.index('class NativeAdrenoGpuService\n');end=log.index('*** Dumping',start);layout=log[start:end]
size=re.search(r'\[sizeof=(\d+), dsize=(\d+), align=(\d+)',layout);assert size and int(size[1])==3208 and int(size[3])==8
assert re.search(r'3192\s*\|\s+struct NativeAdrenoSmmuWindow smmu_window_',layout)
(O/'service-layout.txt').write_text(layout)
raw=obj.read_bytes();assert struct.unpack_from('<I',raw)[0]==0xfeedfacf;at=32;version=None
for _ in range(struct.unpack_from('<I',raw,16)[0]):
 cmd,n=struct.unpack_from('<II',raw,at)
 if cmd==0x32:platform,version=struct.unpack_from('<II',raw,at+8);assert platform==2
 at+=n
assert version==17<<16 and sha(S)==pin
result=dict(scope='source/data-layout evidence of persistent service SMMU cookie repair;no native execution',sources={str(p):sha(p) for p in [S,B/'NativeAdrenoGmuContext.cpp',B/'NativeAdrenoSmmuContext.cpp',B/'NativeAdrenoSmmuContext.h',B/'NativeAdrenoVm.cpp',B/'NativeAdrenoVm.h']},original_SHA=pin,candidate_SHA=sha(C),source_witness='automatic window address copied through ArmSmmu4KIo into persistent smmu_.io_ and vm_.io_',old_GPU_CP_cookie_patches_not_composed=True,previous_smmu_service_reference_patch_not_composed=True,only_typed_cookie_storage_changed=True,four_new_source_corruptions_refused=mutations,candidate_iOS17_object_pass=True,original_historical_Service_bytes=3192,candidate_Service_bytes=3208,new_member_offset=3192,new_member_bytes=16,private_layout_requires_consistent_rebuild=True,object_SHA=sha(obj),target_object_not_linked_or_executed=True,metaclass_initializer_unexecuted=True,catalog_and_profiles_unchanged=True,role_API_and_fullcore_unchanged=True,no_native_object_or_success_peer_or_address_model=True,mapping_ownership_and_quiescence_not_solved=True,hardware_qualification=False,device_operations=False)
(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS:automatic SMMU cookie source lifetime repaired;4 source refusals;real iOS17 Service layout3192->3208;no native execution')

#!/usr/bin/env python3
"""Preserve returned cache IOReturn in private storage;never invoke a callback."""
from pathlib import Path
import argparse,difflib,hashlib,json,re,subprocess,struct
R=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
B=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740';S=B/'NativeAdrenoService.cpp';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=S.read_text();pin=sha(S);(O/'original.cpp').write_text(old)
before='    struct RingCache {NativeAdrenoMemory *ring;NativeAdrenoMemory *fence;};'
after='''    struct RingCache {
        NativeAdrenoMemory *ring;NativeAdrenoMemory *fence;
        /* First actual returned native failures only. Availability0 is unknown,
         * not native SUCCESS,no-attempt,coherency or device-completion proof. */
        IOReturn first_publish_error=0,first_acquire_error=0;
        uint32_t publish_error_available=0,acquire_error_available=0;
        static_assert(sizeof(IOReturn)==4,"preserve actual native status width");
    };'''
assert old.count(before)==1;new=old.replace(before,after,1)
changes=[]
for name,member,method,error,avail,args in [
 ('ring_publish','ring','publishForDevice','first_publish_error','publish_error_available','0,bytes,false'),
 ('fence_acquire','fence','acquireDeviceWrites','first_acquire_error','acquire_error_available','0,bytes')]:
 a=f'    return cache && cache->{member} && cache->{member}->{method}({args})==kIOReturnSuccess?0:1;'
 b=f'''    if(!cache || !cache->{member})return 1;
    const IOReturn native=cache->{member}->{method}({args});
    if(native!=kIOReturnSuccess && !cache->{avail}) {{
        cache->{error}=native;cache->{avail}=1;
    }}
    return native==kIOReturnSuccess?0:1;'''
 assert new.count(a)==1;new=new.replace(a,b,1);changes.append((a,b))
C=O/S.name;C.write_text(new)
(O/'service-cache-native-status.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+S.name,tofile='b/'+S.name)))
back=new.replace(after,before,1)
for a,b in changes:back=back.replace(b,a,1)
assert back==old
def body(s,name):
 a=s.index('int NativeAdrenoGpuService::'+name+'(');b=s.index('\n}',a);return s[a:b]
def audit(s):
 for name,member,method,error,avail,args in [
  ('ring_publish','ring','publishForDevice','first_publish_error','publish_error_available','0,bytes,false'),
  ('fence_acquire','fence','acquireDeviceWrites','first_acquire_error','acquire_error_available','0,bytes')]:
  b=body(s,name);gate=b.index(f'if(!cache || !cache->{member})return 1;')
  call=b.index(f'const IOReturn native=cache->{member}->{method}({args});')
  first=b.index(f'if(native!=kIOReturnSuccess && !cache->{avail})')
  capture=b.index(f'cache->{error}=native;cache->{avail}=1;')
  folded=b.index('return native==kIOReturnSuccess?0:1;')
  assert gate<call<first<capture<folded and b.count('cache->'+member+'->'+method+'(')==1
  assert 'return native;' not in b
audit(new);controls=[]
for name,s in [('zero-publish-error',new.replace('cache->first_publish_error=native;','cache->first_publish_error=0;')),
 ('lost-acquire-error',new.replace('cache->first_acquire_error=native;','cache->first_acquire_error=0;')),
 ('overwrite-first-publish',new.replace('native!=kIOReturnSuccess && !cache->publish_error_available','native!=kIOReturnSuccess')),
 ('changed-callback-ABI',new.replace('return native==kIOReturnSuccess?0:1;','return native;',1))]:
 try:audit(s)
 except (AssertionError,ValueError) as e:controls.append(dict(name=name,refused=str(e)))
 else:raise AssertionError(name)
assert new.count('publishForDevice(')==old.count('publishForDevice(') and new.count('acquireDeviceWrites(')==old.count('acquireDeviceWrites(')
prior=json.loads((R/'out/zorn/gpu-catalog-service-dependencies/compile-result.json').read_text());rec=next(x for x in prior['commands'] if str(S) in x['arguments'] and '-c' in x['arguments']);args=list(rec['arguments'])
assert '--target=arm64-apple-ios17.0.0' in args and not any(x in args for x in ['-MF','-MJ'])
args[args.index(str(S))]=str(C);obj=O/'candidate-ios17.o';args[args.index('-o')+1]=str(obj);args+=['-MD','-MF',str(O/'candidate-inputs.d'),'-MT',str(obj)]
p=subprocess.run(args,cwd=rec['directory'],capture_output=True,timeout=50);(O/'candidate.stdout.raw').write_bytes(p.stdout);(O/'candidate.stderr.raw').write_bytes(p.stderr);(O/'commands.json').write_text(json.dumps([dict(name='candidate-ios17',arguments=args,directory=rec['directory'],returncode=p.returncode)],indent=2)+'\n');assert p.returncode==0,p.stderr.decode(errors='replace')[-2000:]
log=p.stdout.decode();i=log.index('class NativeAdrenoGpuService\n');j=log.index('[sizeof=',i);assert log[j:].startswith('[sizeof=3208,')
start=log.index('struct NativeAdrenoGpuService::RingCache\n');end=log.index('*** Dumping',start);cache=log[start:end]
assert '[sizeof=32,' in cache
for at,name in [(16,'first_publish_error'),(20,'first_acquire_error'),(24,'publish_error_available'),(28,'acquire_error_available')]:assert re.search(r'\b'+str(at)+r'\s*\|.*\b'+name+r'\b',cache)
(O/'cache-layout.txt').write_text(cache)
raw=obj.read_bytes();assert struct.unpack_from('<I',raw)[0]==0xfeedfacf;at=32;version=None
for _ in range(struct.unpack_from('<I',raw,16)[0]):
 cmd,n=struct.unpack_from('<II',raw,at)
 if cmd==0x32:platform,version=struct.unpack_from('<II',raw,at+8);assert platform==2
 at+=n
assert version==17<<16 and sha(S)==pin
# Compare symbol dependencies of the changed object with the sealed original;
# metadata inspection does not rebuild/re-execute that old object.
imports={}
for label,path in [('candidate',obj),('sealed-original',R/'out/zorn/gpu-catalog-service-dependencies/catalog-service-original.o')]:
 q=subprocess.run(['/usr/bin/nm','-u',str(path)],capture_output=True);assert q.returncode==0;(O/(label+'-imports.raw')).write_bytes(q.stdout);imports[label]=[line.split()[-1] for line in q.stdout.decode().splitlines() if line.split()]
native=lambda symbols:{x for x in symbols if 'NativeAdrenoMemory' in x}
assert native(imports['candidate'])==native(imports['sealed-original'])
result=dict(scope='private Service first actual native cache-failure storage;source/data-layout only',original_SHA=pin,candidate_SHA=sha(C),before_native_status_folded_to_callback_boolean=True,actual_return_assigned_as_IOReturn_before_folding=True,four_source_corruptions_refused=controls,first_failure_sticky_publish_acquire_channels_separate=True,availability_zero_not_success_or_no_attempt=True,callback_result_0_1_and_native_call_counts_unchanged=True,new_getter_accessor_wire_log_or_owner_API=False,historical_RingCache_bytes=16,candidate_RingCache_bytes=32,historical_Service_bytes=3192,candidate_Service_bytes=3208,native_IOReturn_bytes=4,future_owner_rebuild_required=True,new_candidate_iOS17_Service_object_pass=True,object_SHA=sha(obj),native_memory_import_set_matches_sealed_original=True,object_not_linked_or_executed=True,no_cache_callback_native_provider_or_success_peer_return_value_execution=True,existing_metaclass_initializer_unexecuted=True,old_Ring_VM_Service_candidates_not_combined=True,catalog_pins_32patches_profiles_role_API_unchanged=True,hardware_qualification=False,device_operations=False)
(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS:private raw IOReturn first-failure channels preserve0/1 callback ABI;4 source controls,new iOS17 Service/cache32B layout;no callbacks/native')

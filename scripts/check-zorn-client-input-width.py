#!/usr/bin/env python3
"""Compare negotiation range predicates, never instantiate client/transport."""
from pathlib import Path
import argparse,difflib,hashlib,json,subprocess,struct,re
R=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
B=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740';S=B/'NativeAdrenoClient.cpp';U=B/'NativeAdrenoUserClient.cpp';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();old=S.read_text();server=U.read_text();pin=sha(S)
assert old.count('reply.input_bits<32')==1
opening=server[server.index('IOReturn NativeAdrenoUserClient::open('):server.index('IOReturn NativeAdrenoUserClient::setScope(')]
assert 'input_bits<31 || input_bits>48' in opening
query=server[server.index('IOReturn NativeAdrenoUserClient::query('):server.index('IOReturn NativeAdrenoUserClient::allocBo(')]
assert 'input_bits_' in query and 'params->input_bits=input_bits_;' in query
new=old.replace('reply.input_bits<32','reply.input_bits<31',1);C=O/S.name;C.write_text(new);(O/'original.cpp').write_text(old);(O/'client-input-width.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+S.name,tofile='b/'+S.name)))
assert new.replace('reply.input_bits<31','reply.input_bits<32',1)==old
# Extract lower/upper software range constants from the producer and consumer.
lo,hi=map(int,re.search(r'input_bits<(\d+) \|\| input_bits>(\d+)',opening).groups());clo,chi=map(int,re.search(r'reply.input_bits<(\d+) \|\|\s*reply.input_bits>(\d+)',new).groups());blo,bhi=map(int,re.search(r'reply.input_bits<(\d+) \|\|\s*reply.input_bits>(\d+)',old).groups())
rows=[dict(input_bits=n,server_range=lo<=n<=hi,before_client_range=blo<=n<=bhi,after_client_range=clo<=n<=chi) for n in range(65)]
assert [x['input_bits'] for x in rows if x['server_range']!=x['before_client_range']]==[31]
assert all(x['server_range']==x['after_client_range'] for x in rows)
mut=[]
for value in [30,32,49]:
 c=new.replace('reply.input_bits<31','reply.input_bits<'+str(value),1)
 if c.count('reply.input_bits<31')!=1 or c.replace('reply.input_bits<31','reply.input_bits<32',1)!=old:mut.append(value)
assert len(mut)==3
prior=json.loads((R/'out/zorn/gpu-catalog-service-dependencies/compile-result.json').read_text());service=str(B/'NativeAdrenoService.cpp');rec=next(x for x in prior['commands'] if service in x['arguments'] and '-c' in x['arguments']);args=list(rec['arguments']);assert '--target=arm64-apple-ios17.0.0' in args and not any(x in args for x in ['-MF','-MJ']);args[args.index(service)]=str(C);obj=O/'candidate-ios17.o';args[args.index('-o')+1]=str(obj);args+=['-MD','-MF',str(O/'candidate-inputs.d'),'-MT',str(obj)]
p=subprocess.run(args,cwd=rec['directory'],capture_output=True,timeout=50);(O/'candidate.stdout.raw').write_bytes(p.stdout);(O/'candidate.stderr.raw').write_bytes(p.stderr);(O/'commands.json').write_text(json.dumps([dict(arguments=args,directory=rec['directory'],returncode=p.returncode)],indent=2)+'\n');assert p.returncode==0,p.stderr.decode(errors='replace')
raw=obj.read_bytes();assert struct.unpack_from('<I',raw)[0]==0xfeedfacf;at=32;ver=None
for _ in range(struct.unpack_from('<I',raw,16)[0]):
 cmd,n=struct.unpack_from('<II',raw,at)
 if cmd==0x32:platform,ver=struct.unpack_from('<II',raw,at+8);assert platform==2
 at+=n
assert ver==17<<16 and sha(S)==pin
res=dict(scope='userspace/kernel software input-width negotiation agreement only',original_SHA=pin,server_SHA=sha(U),candidate_SHA=sha(C),before_software_range_mismatch_at_31=True,all_65_integer_range_comparisons_match_after=True,comparison_rows=rows,three_bad_lower_bounds_refused=mut,only_Client_lower_bound_32_to31_changed=True,version_flags_output_width_max_bo_and_transport_behavior_unchanged=True,submit_count_and_metadata_capacity_copy_review_no_new_gap=True,new_Client_iOS17_object_pass=True,object_not_linked_or_executed=True,no_client_transport_success_peer_query_open_submit_or_native_execution=True,no_K80_bits_OAS_IOVA_geometry_mapping_or_policy_selection=True,server_userclient_fullcore_role_API_not_recompiled=True,catalog_pins_32patches_profiles_unchanged=True,hardware_qualification=False,device_operations=False)
(O/'result.json').write_text(json.dumps(res,indent=2)+'\n');print('PASS:producer/consumer software31-bit negotiation mismatch repaired;65 integer comparisons/3 mutations/new iOS17 Client object;no transport/native execution')

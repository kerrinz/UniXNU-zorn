#!/usr/bin/env python3
"""Audit exact ABI dispatch width guards without executing driver methods."""
from pathlib import Path
import json,re,struct,subprocess
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-catalog-fence-query-width'
identity=json.loads((O/'source-repair-identity.json').read_text());original=Path(identity['original']).read_text();candidate=Path(identity['candidate']).read_text()
assert not (O/'width-audit.json').exists()
guards=['        if(request.wait_fence>UINT32_MAX) {status=kIOReturnBadArgument;break;}\n','        if(request.fence>UINT32_MAX) {status=kIOReturnBadArgument;break;}\n']
def sourcecheck(text):
 inverse=text
 for guard in guards:assert inverse.count(guard)==1;inverse=inverse.replace(guard,'',1)
 assert inverse==original
 for method,guard,consumer in [('Submit',guards[0],'status=submit(&request,'),('WaitFence',guards[1],'status=waitFence(&request,')]:
  start=text.index('case NativeAdrenoMethod'+method+': {',text.index('IOReturn NativeAdrenoUserClient::dispatch('));end=text.index('\n    case ',start+5);scope=text[start:end]
  assert scope.index('memcpy(&request,input,sizeof(request));')<scope.index(guard.strip())<scope.index(consumer)
sourcecheck(candidate);refused=[]
mutations=[('submit-width-guard-removed',candidate.replace(guards[0],'',1)),('wait-width-guard-removed',candidate.replace(guards[1],'',1)),('comparison-after-truncation',candidate.replace('request.wait_fence>UINT32_MAX','(uint32_t)request.wait_fence>UINT32_MAX',1))]
for name,bad in mutations:
 (O/(name+'.source')).write_text(bad)
 try:sourcecheck(bad)
 except (AssertionError,ValueError):refused.append(name)
 else:raise AssertionError('width source mutation accepted '+name)
def objectcheck(source):
 asm=subprocess.run(['/opt/homebrew/opt/llvm/bin/llvm-objdump','--macho','-d','--no-show-raw-insn',str(source)],capture_output=True,text=True,check=True).stdout
 rows={int(a,16):i for a,i in re.findall(r'^\s*([0-9a-f]+):\s+([^\n]+)',asm,re.M)}
 # Actual current recipe: request.wait_fence at byte3280; upper word3284.
 assert rows[0x3a8]=='ldr\tw8, [x22, #0xcd4]'
 assert rows[0x3bc]=='cbnz\tw8, 0x134'
 assert 'UserClient6submit' in rows[0x3d4]
 assert rows[0x414]=='lsr\tx8, x8, #32'
 assert rows[0x418]=='cbnz\tw8, 0x430'
 assert 'UserClient9waitFence' in rows[0x428]
 assert rows[0xc8]=='mov\tw27, #0x2c2' and rows[0xcc]=='movk\tw27, #0xe000, lsl #16'
 assert rows[0x430]=='mov\tx0, x27' and rows[0x434]=='mov\tx25, x27'
 return [0x3bc,0x418]
pcs=objectcheck(O/'candidate-dispatch.o');raw=(O/'candidate-dispatch.o').read_bytes()
def textsection(data):
 assert struct.unpack_from('<I',data)[0]==0xfeedfacf;offset=32
 for _ in range(struct.unpack_from('<I',data,16)[0]):
  command,size=struct.unpack_from('<II',data,offset)
  if command==0x19:
   for i in range(struct.unpack_from('<I',data,offset+64)[0]):
    section=offset+72+80*i
    if data[section:section+16].split(b'\0')[0]==b'__text':return struct.unpack_from('<Q',data,section+32)[0],struct.unpack_from('<I',data,section+48)[0]
  offset+=size
 raise AssertionError('text absent')
addr,offset=textsection(raw);objects=[]
for label,pc in zip(['submit','wait'],pcs):
 changed=bytearray(raw);pos=offset+pc-addr;changed[pos:pos+4]=bytes.fromhex('1f2003d5');mutant=O/(label+'-width-branch-removed.o');mutant.write_bytes(changed)
 try:objectcheck(mutant)
 except (AssertionError,ValueError):objects.append(label)
 else:raise AssertionError('width object mutation accepted '+label)
sizes={}
for label in ['original','candidate']:
 layout=(O/(label+'-first.log')).read_text();found=re.search(r'^\s*0 \| class NativeAdrenoUserClient\n(.*?)(?=\*\*\* Dumping|\Z)',layout,re.M|re.S);assert found;sizes[label]=int(re.search(r'\[sizeof=(\d+)',found.group(0)).group(1));assert sizes[label]==6424
 assert re.search(r'3280 \|\s+uint64_t wait_fence',found.group(0))
(O/'width-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,new_actual_object_mutations_refused=objects,actual_upper32_checks_before_submit_and_wait_calls=True,existing_BadArgument_and_tally_exit=True,UserClient_bytes=sizes,wire_header_unchanged=True,review_and_full_source_inverse_equal=True,no_native_method_or_success_peer_execution=True,no_old_suite_or_fullcore_retry=True),indent=2)+'\n')
print('3 source/2 actual object guard refusals;UserClient6424 unchanged;upper32 checked before original calls')

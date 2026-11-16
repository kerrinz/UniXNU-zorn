#!/usr/bin/env python3
"""Offline view owner-before-growth audit;no descriptor/map/allocator calls."""
from pathlib import Path
import json,re,struct,subprocess
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-catalog-view-growth-owner'
assert not (O/'view-growth-audit.json').exists()
identity=json.loads((O/'source-repair-identity.json').read_text());original=Path(identity['original']).read_text();candidate=Path(identity['candidate']).read_text();old=identity['old'];new=identity['new'];anchor=identity['anchor']
def sourcecheck(text):
 assert text.count(new)==1 and text.count(old)==0
 inverse=text.replace(anchor+new,anchor,1).replace('    View *v=viewSlot(type);\n',old+'    View *v=viewSlot(type);\n',1);assert inverse==original
 start=text.index('IOReturn AGXDeviceUserClient::clientMemoryForType(');end=text.index('\n/* Fence waits',start);scope=text[start:end]
 assert scope.index('IOLockLock(g.lock);')<scope.index('View *v=viewSlot(type);')<scope.index('if(v && v->descriptor && v->token==type)')<scope.index(anchor.strip())<scope.index(new.strip())<scope.index('if(backing && backing->system()')
sourcecheck(candidate);refused=[]
mutants=[('growth-before-owner-restored',original),('growth-not-gated-by-backing',candidate.replace('if(backing && !growViews(type))','if(!growViews(type))',1)),('post-growth-slot-reload-removed',candidate.replace('    v=viewSlot(type);\n','',1))]
for name,bad in mutants:
 assert bad!=candidate;(O/(name+'.source')).write_text(bad)
 try:sourcecheck(bad)
 except (AssertionError,ValueError):refused.append(name)
 else:raise AssertionError('view source mutation accepted '+name)
def objectcheck(source):
 asm=subprocess.run(['/opt/homebrew/opt/llvm/bin/llvm-objdump','--macho','-d','--no-show-raw-insn',str(source)],capture_output=True,text=True,check=True).stdout
 start=asm.index('__ZN19AGXDeviceUserClient19clientMemoryForType');tail=asm[start:];end=re.search(r'\n__[^\n]*:\n',tail);scope=tail[:end.start()] if end else tail;rows={int(a,16):i for a,i in re.findall(r'^\s*([0-9a-f]+):\s+([^\n]+)',scope,re.M)}
 assert 'memoryForToken' in rows[0x1d1c] and rows[0x1d24]=='cbz\tx0, 0x1e04'
 assert '_IOMallocTypeVarImpl' in rows[0x1d88]
 assert rows[0x1e94]=='stp\tx20, x27, [x9, #0x108]'
 assert rows[0x1e9c]=='ldr\tx12, [x9, #0x108]'
 assert scope.index('memoryForToken')<scope.index('_IOMallocTypeVarImpl')
 return [0x1d24,0x1e9c]
pcs=objectcheck(O/'NativePublish.o');raw=(O/'NativePublish.o').read_bytes()
def textsection(data):
 assert struct.unpack_from('<I',data)[0]==0xfeedfacf;at=32
 for _ in range(struct.unpack_from('<I',data,16)[0]):
  command,size=struct.unpack_from('<II',data,at)
  if command==0x19:
   for i in range(struct.unpack_from('<I',data,at+64)[0]):
    p=at+72+80*i
    if data[p:p+16].split(b'\0')[0]==b'__text':return struct.unpack_from('<Q',data,p+32)[0],struct.unpack_from('<I',data,p+48)[0]
  at+=size
 raise AssertionError('text absent')
addr,offset=textsection(raw);objects=[]
for label,pc in zip(['missing-backing-gate','missing-post-grow-slot-reload'],pcs):
 data=bytearray(raw);pos=offset+pc-addr;data[pos:pos+4]=bytes.fromhex('1f2003d5');mutant=O/(label+'.o');mutant.write_bytes(data)
 try:objectcheck(mutant)
 except (AssertionError,ValueError):objects.append(label)
 else:raise AssertionError('view object mutation accepted '+label)
layout=(O/'candidate-first.log').read_text();found=re.search(r'^\s*0 \| class AGXDeviceUserClient\n(.*?)(?=\*\*\* Dumping|\Z)',layout,re.M|re.S);assert found;size=int(re.search(r'\[sizeof=(\d+)',found.group(0)).group(1));assert size==280
result=dict(new_source_mutations_refused=refused,new_actual_object_mutations_refused=objects,owner_lookup_and_null_gate_precede_actual_directory_allocation=True,actual_slot_reload_after_directory_publication=True,AGXDeviceUserClient_bytes_unchanged=size,cached_hit_special_types_refcounts_options_and_cleanup_outside_move_inverse_equal=True,no_native_descriptor_allocator_map_or_success_peer_execution=True,no_old_suite_or_fullcore_target_reexecution=True)
(O/'view-growth-audit.json').write_text(json.dumps(result,indent=2)+'\n');print('3 source/2 actual object refusals;backing gate then grow/reload;class280 unchanged,no API execution')

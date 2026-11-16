#!/usr/bin/env python3
"""Offline active-job completion owner audit;no allocator/fence/native peer execution."""
from pathlib import Path
import json,re,shutil,struct,subprocess
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-catalog-fence-ring-owner';identity=json.loads((O/'source-repair-identity.json').read_text())
assert not (O/'active-job-ring-audit.json').exists();original=Path(identity['original']).read_text();candidate=Path(identity['candidate']).read_text()
def sourcecheck(text):
 assert text.count(identity['new'])==1
 assert text.replace(identity['new'],identity['old'],1)==original
 start=text.index('IOReturn NativeAdrenoSubmit::retireCompleted()');end=text.index('\nbool NativeAdrenoSubmit::madeProgress()',start);scoped=text[start:end]
 assert scoped.index('if(!job.active)continue;')<scoped.index('r=ring(job.ring)')<scoped.index('r->observeFence')<scoped.index('release(job)')
 assert 'ringOfFence' not in scoped
sourcecheck(candidate);refused=[]
for label,substitution in [('cache-lookup-restored','ringOfFence(job.fence)'),('forced-ring-zero','ring(0)'),('fence-used-as-index','ring(uint32_t(job.fence))')]:
 bad=candidate.replace('r=ring(job.ring)','r='+substitution,1);assert bad!=candidate;(O/(label+'.source')).write_text(bad)
 try:sourcecheck(bad)
 except (AssertionError,ValueError):refused.append(label)
 else:raise AssertionError('owner source mutation accepted '+label)
review=O/'source-review';review.mkdir();shutil.copyfile(Path(identity['original']),review/'NativeAdrenoSubmit.cpp')
for label,extra in [('check',['--check']),('apply',[])]:
 result=subprocess.run(['git','apply',*extra,str(O/'active-job-completion-ring.UNAPPLIED.patch')],cwd=review,capture_output=True,text=True);(O/('review-'+label+'.log')).write_text(result.stdout+result.stderr);assert result.returncode==0
assert (review/'NativeAdrenoSubmit.cpp').read_bytes()==Path(identity['candidate']).read_bytes()
def objectcheck(source):
 asm=subprocess.run(['/opt/homebrew/opt/llvm/bin/llvm-objdump','--macho','-d','--no-show-raw-insn',str(source)],capture_output=True,text=True,check=True).stdout
 found=re.search(r'^__ZN[^\n]*retireCompleted[^\n]*:\n',asm,re.M);assert found;tail=asm[found.end():];end=re.search(r'^__[^\n]*:\n',tail,re.M);scoped=tail[:end.start()] if end else tail
 load=re.search(r'^\s*([0-9a-f]+):\s+ldrb\s+w8, \[x21, #0xc50\]',scoped,re.M);assert load
 assert scoped.index(load.group(0))<scoped.index('NativeAdrenoRing12observeFence')<scoped.index('NativeAdrenoSubmit7release')
 assert re.search(r'ldr\s+w9, \[x20, #0x70\]',scoped) and re.search(r'csel\s+x8, x10, x25, hi',scoped)
 assert 'ringOfFence' not in scoped
 return int(load.group(1),16)
pc=objectcheck(O/'NativeSubmit.o');raw=(O/'NativeSubmit.o').read_bytes()
def textsection(data):
 assert struct.unpack_from('<I',data)[0]==0xfeedfacf;offset=32
 for _ in range(struct.unpack_from('<I',data,16)[0]):
  command,size=struct.unpack_from('<II',data,offset)
  if command==0x19:
   for index in range(struct.unpack_from('<I',data,offset+64)[0]):
    section=offset+72+80*index
    if data[section:section+16].split(b'\0')[0]==b'__text':return struct.unpack_from('<Q',data,section+32)[0],struct.unpack_from('<I',data,section+48)[0]
  offset+=size
 raise AssertionError('text section absent')
address,file_offset=textsection(raw);position=file_offset+pc-address;assert raw[position:position+4]!=bytes.fromhex('1f2003d5');changed=bytearray(raw);changed[position:position+4]=bytes.fromhex('1f2003d5');mutant=O/'missing-job-ring-load.o';mutant.write_bytes(changed)
try:objectcheck(mutant)
except (AssertionError,ValueError):object_refused=True
else:raise AssertionError('actual job-ring-load removal accepted')
layout=(O/'candidate-first.log').read_text();sizes={}
for name in ['NativeAdrenoSubmit','NativeAdrenoSubmit::Job']:
 found=re.search(r'^\s*0 \| (?:class|struct) '+re.escape(name)+r'\n(.*?)(?=\*\*\* Dumping|\Z)',layout,re.M|re.S);assert found;sizes[name]=int(re.search(r'\[sizeof=(\d+)',found.group(0)).group(1))
assert sizes=={'NativeAdrenoSubmit':3672,'NativeAdrenoSubmit::Job':3168}
result=dict(new_source_mutations_refused=refused,new_actual_object_mutations_refused=1,actual_Job_ring_byte3152_loaded_before_observe_and_release=True,actual_existing_ring_helper_range_and_fallback_preserved=True,independent_original_review_apply_inverse_equal=True,actual_layouts_unchanged=sizes,no_header_public_stats_return_or_wire_change=True,no_native_allocator_fence_job_or_success_peer_execution=True,no_old_suite_or_target_reexecution=True)
(O/'active-job-ring-audit.json').write_text(json.dumps(result,indent=2)+'\n');print('3source/1actual object Job.ring load refusal;review/inverse exact;Submit3672/Job3168 unchanged,no native APIs')

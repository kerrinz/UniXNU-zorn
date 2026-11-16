#!/usr/bin/env python3
"""Audit isolated process-VM ownership source and actual objects,without running native APIs."""
from pathlib import Path
import hashlib,json,re,shutil,struct,subprocess
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-catalog-process-vm-owner';N=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740';D=O/'candidate-source'
ident=json.loads((O/'source-repair-identity.json').read_text());assert not (O/'process-owner-audit.json').exists()
def sourcecheck(files):
 for name in ['NativeAdrenoGpuContext.cpp','NativeAdrenoGpuContext.h']:
  s=files[name]
  for old,new in reversed(ident[name]['changes']):assert s.count(new)==1;s=s.replace(new,old,1)
  assert s==(N/name).read_text()
 c=files['NativeAdrenoGpuContext.cpp'];start=c.index('IOReturn NativeAdrenoGpuContext::createVm(')
 assert c.index('p->owner_next_=process_vms_;process_vms_=p;',start)<c.index('NativeAdrenoPrepareSmmuMemory(',start)
 assert c.count('unlinkProcessOwner(p);delete p;')==2
 assert 'if(*link)*link=p->owner_next_;' in c
files={n:(D/n).read_text() for n in ['NativeAdrenoGpuContext.cpp','NativeAdrenoGpuContext.h']};sourcecheck(files);refused=[]
mutants=[
 ('missing-root-before-prepare','NativeAdrenoGpuContext.cpp','    p->owner_next_=process_vms_;process_vms_=p;',''),
 ('drop-prefix-on-unlink','NativeAdrenoGpuContext.cpp','if(*link)*link=p->owner_next_;','if(*link)process_vms_=p->owner_next_;'),
 ('clean-delete-still-linked','NativeAdrenoGpuContext.cpp','{unlinkProcessOwner(p);delete p;return status;}','{delete p;return status;}'),
 ('destroy-delete-still-linked','NativeAdrenoGpuContext.cpp','    unlinkProcessOwner(p);delete p;','    delete p;'),
 ('withdraw-on-failed-create','NativeAdrenoGpuContext.cpp','        return status;\n    }\n    native_adreno_table_switches[7]=0;','        unlinkProcessOwner(p);return status;\n    }\n    native_adreno_table_switches[7]=0;')]
for label,name,a,b in mutants:
 assert files[name].count(a)==1;bad=dict(files);bad[name]=bad[name].replace(a,b,1);(O/(label+'.source')).write_text(bad[name])
 try:sourcecheck(bad)
 except (AssertionError,ValueError):refused.append(label)
 else:raise AssertionError('source mutation accepted '+label)
review=O/'source-review';review.mkdir()
for n in files:shutil.copyfile(N/n,review/n)
for name,extra in [('check',['--check']),('apply',[])]:
 p=subprocess.run(['git','apply',*extra,str(O/'process-vm-owner-registry.UNAPPLIED.patch')],cwd=review,capture_output=True,text=True);(O/('review-'+name+'.log')).write_text(p.stdout+p.stderr);assert p.returncode==0
for n in files:assert (review/n).read_bytes()==(D/n).read_bytes()
def cut(s,name):
 m=re.search(r'^__ZN[^\n]*'+name+r'[^\n]*:\n',s,re.M);assert m,name;b=s[m.end():];end=re.search(r'^__[^\n]*:\n',b,re.M);return b[:end.start()] if end else b
def objectcheck(p):
 a=subprocess.run(['/opt/homebrew/opt/llvm/bin/llvm-objdump','--macho','-d','--no-show-raw-insn',str(p)],capture_output=True,text=True,check=True).stdout
 c=cut(a,'createVm');d=cut(a,'destroyVm');h=cut(a,'unlinkProcessOwner')
 assert re.search(r'str\s+x8, \[x19, #0x3f0\]',c)
 root=re.search(r'^\s*([0-9a-f]+):\s+str\s+x19, \[x23, #0x2918\]',c,re.M);assert root
 assert c.index(root.group(0))<c.index('NativeAdrenoPrepareSmmuMemory')
 assert re.search(r'ldr\s+x9, \[x19, #0x3f0\]',c) and re.search(r'str\s+x9, \[x8\]',c)
 unlink=re.search(r'^\s*([0-9a-f]+):\s+str\s+x9, \[x8\]',d,re.M);assert unlink
 assert re.search(r'ldr\s+x9, \[x0, #0x3f0\]',d) and '__ZdlPvm' in d
 assert d.index(unlink.group(0))<d.index('__ZdlPvm')
 assert 'str\tx9, [x8]' in h
 return dict(root=int(root.group(1),16),unlink=int(unlink.group(1),16))
offsets=objectcheck(O/'candidate-GpuContext.o')
def textsection(data):
 assert struct.unpack_from('<I',data)[0]==0xfeedfacf;off=32
 for _ in range(struct.unpack_from('<I',data,16)[0]):
  cmd,size=struct.unpack_from('<II',data,off)
  if cmd==0x19:
   for j in range(struct.unpack_from('<I',data,off+64)[0]):
    p=off+72+80*j
    if data[p:p+16].split(b'\0')[0]==b'__text':return struct.unpack_from('<Q',data,p+32)[0],struct.unpack_from('<I',data,p+48)[0]
  off+=size
 raise AssertionError('text absent')
raw=(O/'candidate-GpuContext.o').read_bytes();addr,offset=textsection(raw);object_refused=[]
for label,pc in offsets.items():
 pos=offset+pc-addr;assert raw[pos:pos+4]!=bytes.fromhex('1f2003d5');bad=bytearray(raw);bad[pos:pos+4]=bytes.fromhex('1f2003d5');p=O/('missing-'+label+'.o');p.write_bytes(bad)
 try:objectcheck(p)
 except (AssertionError,ValueError):object_refused.append(label)
 else:raise AssertionError('actual owner store mutation accepted '+label)
layouts={}
for label in ['original-GpuContext','candidate-GpuContext','affected-Publish']:
 s=(O/(label+'-first.log')).read_text();v={}
 for name in ['NativeAdrenoProcessVm','NativeAdrenoGpuContext','AGXDeviceUserClient']:
  m=re.search(r'^\s*0 \| class '+name+r'\n(.*?)(?=\*\*\* Dumping|\Z)',s,re.M|re.S)
  if m:
   b=m.group(0);v[name]=dict(size=int(re.search(r'\[sizeof=(\d+)',b).group(1)),fields=re.findall(r'^\s*(\d+) \|.*?(owner_next_|process_vms_|kernel_asid_)\s*$',b,re.M))
 layouts[label]=v
assert layouts['original-GpuContext']['NativeAdrenoProcessVm']['size']==1008 and layouts['candidate-GpuContext']['NativeAdrenoProcessVm']['size']==1016
assert layouts['original-GpuContext']['NativeAdrenoGpuContext']['size']==10520 and layouts['candidate-GpuContext']['NativeAdrenoGpuContext']['size']==10528
assert layouts['candidate-GpuContext']=={k:v for k,v in layouts['affected-Publish'].items() if k!='AGXDeviceUserClient'}
assert layouts['affected-Publish']['AGXDeviceUserClient']['size']==280
(O/'actual-layouts.json').write_text(json.dumps(layouts,indent=2)+'\n')
v=dict(new_source_mutations_refused=refused,new_actual_object_mutations_refused=object_refused,independent_original_review_apply_inverse_equal=True,actual_owner_link_before_prepare_and_unlink_before_both_deletes=True,actual_new_layouts_and_coherent_consumer=layouts,original_ASID_status_cleanup_code_unchanged=True,no_native_API_or_success_owner_peer_or_old_suite_execution=True)
(O/'process-owner-audit.json').write_text(json.dumps(v,indent=2)+'\n');print('5source/2actual object owner-store refusals;review/inverse exact;actual layouts Process1008->1016/Gpu10520->10528/Publish280')

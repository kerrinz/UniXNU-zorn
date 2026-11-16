#!/usr/bin/env python3
"""Check actual native preprocessing of record/panic identity,including a stale-VFS negative control."""
from pathlib import Path
import argparse,copy,hashlib,json,re,subprocess

def main():
 p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();B=a.build.resolve();O=a.out.resolve();O.mkdir();load=lambda p:json.loads(Path(p).read_text());pin=lambda p:dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest());save=lambda p,d:Path(p).write_text(json.dumps(d,indent=2)+'\n');C=load(B/'candidate.json');S=Path(C['source']);V=load(B/'native-vfs.json');M={r['name']:Path(r['external-contents']) for r in V['roots'] if 'external-contents' in r};H={'ZornPlatformRecordIdentity26.h':'kZornPlatformRecordTrial','ZornPlatformTrialIdentity26.h':'kZornPlatformTrial'}
 def declarations(text):
  result={}
  for name in H.values():
   patterns=re.findall(r'\b'+name+r'\s*\[\s*16\s*\]\s*=\s*\{([^}]+)\}',text)
   if patterns:result[name]=[bytes(int(x.strip(),0) for x in v.split(',') if x.strip()).hex() for v in patterns]
  return result
 units={};headers=[]
 for dep in sorted((B/'native-compile').glob('*.deps')):
  for token in dep.read_text().replace('\\\n',' ').split():
   n=Path(token).name
   if n not in H:continue
   target=M.get(token,Path(token));assert target.resolve()==(S/'record-identity'/n).resolve(),(dep,token,target)
   values=declarations(target.read_text());assert values=={H[n]:[C['tag']]},values
   units.setdefault(dep.name.removesuffix('.deps'),set()).add(H[n]);headers.append(dict(unit=dep.name,alias=token,resolved=pin(target)))
 assert units and set().union(*units.values())==set(H.values())
 def preprocess(unit,vfs,outname):
  recipe=load(B/'native-compile'/(unit+'.command.json'));args=recipe['arguments'];new=[];i=0
  while i<len(args):
   x=args[i]
   if x in ['-o','-MF','-MJ','-MT']:i+=2;continue
   if x in ['-c','-MD','-MMD','-MP']:i+=1;continue
   new.append(str(vfs) if x==str(B/'native-vfs.json') else x);i+=1
  new+=['-E','-P'];r=subprocess.run(new,cwd=recipe['directory'],capture_output=True,text=True,timeout=120);save(O/(outname+'.json'),dict(arguments=new,directory=recipe['directory'],exit=r.returncode,stderr=r.stderr,preprocessed_source_sha256=hashlib.sha256(r.stdout.encode()).hexdigest(),declarations=declarations(r.stdout)));assert not r.returncode,r.stderr[-3000:];return declarations(r.stdout)
 positive=[]
 for unit,names in units.items():
  values=preprocess(unit,B/'native-vfs.json','current-'+unit)
  assert all(values.get(n)==[C['tag']] for n in names),(unit,values)
  positive.append(dict(unit=unit,identities=values,actual_object=pin(B/'native-compile'/unit),recipe=pin(B/'native-compile'/(unit+'.command.json'))))
 old=load(B/'identity-header-inputs260.json');negative=copy.deepcopy(V);back={r['alias']:r['before']['path'] for r in old['aliases']}
 for row in negative['roots']:
  if row['name'] in back:row['external-contents']=back[row['name']]
 save(O/'stale-vfs.json',negative);refused=[]
 for unit,names in units.items():
  values=preprocess(unit,O/'stale-vfs.json','stale-'+unit);assert any(values.get(n)!=[C['tag']] for n in names),(unit,values)
  refused.append(dict(unit=unit,stale_declarations=values,expected_boot_tag=C['tag']))
 assert load(B/'artifact-identity.json')['run_id']==C['tag'];assert C['tag'] in (S/'ZornUfsOwner26.cpp').read_text();assert 'ZORN26'+C['tag'][:12].upper() in (S/'ZornUsbCdc26.c').read_text()
 save(O/'result.json',dict(passed=True,scope='Actual native compiler preprocessed source identity;no instruction inspection or device access',expected_boot_tag=C['tag'],headers=headers,current_preprocessing=positive,stale_parent_VFS_refused=refused,kernel=pin(C['kernel']),artifact_identity=pin(B/'artifact-identity.json'),actual_native_VFS=pin(B/'native-vfs.json'),test_tool=pin(Path(__file__).resolve()),phone_access=False,hardware_qualified=False,no_disassembly_or_reverse_engineering=True));print('PASS260 actual record/panic preprocessing matches kernel/UFS/CDC boot tag;stale parent VFS refused',len(positive))

if __name__=='__main__':main()

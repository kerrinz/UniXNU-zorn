#!/usr/bin/env python3
"""Compare native backend source tokens after removing261 diagnostic-only expressions."""
from pathlib import Path
import argparse,hashlib,json,re

def unwrap(t):
 key='zorn_failure_return261('
 while key in t:
  a=t.index(key);z=a+len(key);depth=1;start=z;args=[]
  while depth:
   c=t[z]
   if c=='(':depth+=1
   elif c==')':depth-=1
   elif c==',' and depth==1:args.append(t[start:z]);start=z+1
   z+=1
  args.append(t[start:z-1]);assert len(args)==6 or 4<=len(args)<=6,args
  t=t[:a]+args[1]+t[z:]
 return t

def project(t):
 t=t.replace('#include "ZornClientFailure261.h"\n','');t=unwrap(t)
 t=t.replace('    ZornClientFailureScope261 failureOwner261{};bool failureOwnerSet261=false;\n','')
 t=t.replace('        if(failureOwnerSet261)zorn_failure_target_end261(&failureOwner261);\n','')
 t=re.sub(r'    auto \*failureClient261=OSDynamicCast\(ZornGen7AppIoClient26,target->clientOwner_\);\n    zorn_failure_target_begin261\([^;]+;\n    failureOwnerSet261=true;','',t)

 key='if(raw)zorn_failure_note261('
 while key in t:
  a=t.index(key);z=a+len(key);depth=1
  while depth:depth+=(t[z]=='(')-(t[z]==')');z+=1
  assert t[z]==';';t=t[:a]+t[z+1:]
 t=t.replace('''const auto cacheRaw=m.memory->acquireDeviceWrites(0,m.memory->bytes());
        if(cacheRaw){zorn_failure_note261(ZornFailureVmCache261,uint32_t(cacheRaw),ZornFailureBackend261,ZornFailureCache261,uint32_t(i),0);return fail(ZornSmmuSparse4KIoError);}''','if(m.memory->acquireDeviceWrites(0,m.memory->bytes()))return fail(ZornSmmuSparse4KIoError);')
 t=re.sub(r'if\(!raw\)\{raw=(transitionProcessTables\([^;]+\));\}',r'if(!raw)raw=\1;',t)
 return t

def tokens(t):
 pattern=r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|\s+|[A-Za-z_][A-Za-z0-9_]*|0[xX][0-9a-fA-F]+|[0-9]+|[^\s]'
 return [m[0] for m in re.finditer(pattern,t) if not m[0].isspace() and not m[0].startswith('//') and not m[0].startswith('/*')]

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--parent-source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();S=a.source_root.resolve();P=a.parent_source.resolve();O=a.out.resolve();O.mkdir();pin=lambda p:dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest());rows=[]
 for n in ['direct-runtime/ZornGen7DirectClient26.cpp','direct-runtime/ZornGen7DirectSubmit26.cpp','direct-runtime/ZornGen7DirectVm26.cpp','ZornGen7HostRing26.cpp','ZornGen7SmmuDomain26.cpp']:
  original=(P/n).read_text();current=(S/n).read_text();normalized=project(current);old,new=tokens(original),tokens(normalized)
  if old!=new:
   i=next((i for i,(x,y) in enumerate(zip(old,new)) if x!=y),min(len(old),len(new)));raise AssertionError((n,i,old[max(0,i-12):i+20],new[max(0,i-12):i+20]))
  rows.append(dict(file=n,parent=pin(P/n),current=pin(S/n),diagnostic_removed_native_tokens_identical=True,tokens=len(old)))
 same=[]
 for n in ['ZornGen7HostGpuTables26.cpp','ZornGen7DarwinBoardOwner.cpp','ZornGen7AppExecution26.cpp','ZornGen7PhysicalOob26.h','ZornGen7DirectHfi26.cpp','direct-ring/NativeAdrenoRing.cpp','direct-ring/NativeAdrenoRing.h']:
  assert (S/n).read_bytes()==(P/n).read_bytes(),n;same.append(dict(file=n,sha256=pin(S/n)['sha256']))
 result=dict(passed=True,scope='Source token projection of diagnostic expressions only;not machine code equivalence or hardware qualification',native_source_checks=rows,unchanged_native_backends=same,test_tool=pin(Path(__file__).resolve()),no_backend_return_guard_lifetime_or_call_count_change_in_projected_source=True,phone_access=False,hardware_qualified=False);(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS261 original native backend tokens preserved after removing CPU observation expressions;Board/HFI/Ring byte-equal,actual SMMU return tokens preserved')

if __name__=='__main__':main()

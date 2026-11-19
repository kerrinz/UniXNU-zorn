#!/usr/bin/env python3
"""Reproduce missing context-free membership checks in the actual parent source.

Explicit host native-dispatch boundary only;no device or exploitation claim.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,subprocess

def pin(p):return dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--parent-source',type=Path,required=True);p.add_argument('--dispatch-fixture',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sanitizer',choices=['address,undefined','thread'],default='address,undefined');a=p.parse_args();S=a.source_root.resolve();P=a.parent_source.resolve();F=a.dispatch_fixture.resolve();O=a.out.resolve();O.mkdir()
 spec=importlib.util.spec_from_file_location('scope288',Path(__file__).with_name('check-ios26-readonly-operation288.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 r=json.loads((F/'result.json').read_text());assert r['passed'] and pin(S/'ZornGen7HostRing26.cpp')==r['source'];cpp=(F/'hostcheck.cpp').read_text();source=(S/'ZornGen7HostRing26.cpp').read_text();parent=(P/'ZornGen7HostRing26.cpp').read_text()
 for name in ['IOReturn ZornGen7HostRing26::beginApplicationOperation','IOReturn ZornGen7HostRing26::finishApplicationOperation']:assert m.extract(source,name)==m.extract(parent,name)
 tests=r'''
int main(){unsigned cases=0;
 for(unsigned fault=0;fault<4;++fault){ZornGen7HostRing26 f;ZornGen7ProcessTables26 duplicate=f.process;
  if(fault==0)f.s.processClients=nullptr;
  if(fault==1){f.process.ringNext_=&duplicate;duplicate.ringNext_=nullptr;}
  if(fault==2)f.process.vm_.poison=true;
  if(fault==3){f.s.processClients=&duplicate;duplicate.ringNext_=nullptr;}
  uint8_t out[sizeof(NativeAdrenoAbiParams)];std::memset(out,0xcc,sizeof(out));
  const auto raw=f.dispatchApplicationProcess(f.client,f.execution,f.process,1,nullptr,0,out,sizeof(out));
  assert(f.process.clientState.client.calls==EXPECTED_CALLS);
  if(!EXPECTED_CALLS){assert(raw==kIOReturnNotReady);for(auto b:out)assert(b==0xcc);}
  assert(!f.domain.transitions&&!f.drains);++cases;
 }
 {ZornGen7HostRing26 f;ZornGen7AppExecution26*scope=nullptr;assert(!f.beginApplicationOperation(f.client,ZornGen7AppOperation26::CpuView,scope,nullptr,false));uint8_t out[sizeof(NativeAdrenoAbiParams)];
  const auto raw=f.dispatchProcessClient(f.client,f.process,reinterpret_cast<void*>(3),1,nullptr,0,out,sizeof(out));assert(f.process.clientState.client.calls==EXPECTED_CALLS);if(!EXPECTED_CALLS)assert(raw==kIOReturnNotReady);f.finishApplicationOperation(*scope,raw);++cases;
 }
 std::printf("actual source process-identity cases=%u native boundary expected calls=%u;no hardware\n",cases,EXPECTED_CALLS);
}
'''
 base=cpp[:cpp.index('int main(){')];runs=[];env=dict(os.environ,TSAN_OPTIONS='symbolize=0',ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0')
 for version,expected in [('parent288',1),('current289',0)]:
  body=base
  if expected:
   body=body.replace(m.extract(source,'static bool nativeContextFreeMethod289'),m.extract(parent,'static bool nativeReadOnlyQuery288'))
   for name in ['IOReturn ZornGen7HostRing26::dispatchApplicationProcess','IOReturn ZornGen7HostRing26::dispatchProcessClient']:body=body.replace(m.extract(source,name),m.extract(parent,name))
  C=O/(version+'.cpp');C.write_text(body+tests.replace('EXPECTED_CALLS',str(expected)));binary=O/version
  for cmd in [['/usr/bin/clang++','-std=c++17','-O1','-g','-fno-omit-frame-pointer','-fsanitize='+a.sanitizer,str(C),'-o',str(binary)],[str(binary)]]:
   q=subprocess.run(cmd,capture_output=True,text=True,timeout=120,env=env);runs.append(dict(arguments=cmd,exit=q.returncode,stdout=q.stdout,stderr=q.stderr));(O/'commands.json').write_text(json.dumps(runs,indent=2)+'\n');assert not q.returncode,q.stderr[-5000:]
 result=dict(passed=True,sanitizer=a.sanitizer,source=pin(S/'ZornGen7HostRing26.cpp'),parent=pin(P/'ZornGen7HostRing26.cpp'),test_tool=pin(Path(__file__).resolve()),actual_fixture=pin(F/'hostcheck.cpp'),parent_actual_dispatch_reaches_host_backend_for_unlisted_duplicate_poisoned_and_mismatched_calling_task=True,current_actual_dispatch_refuses_before_host_backend=True,scope_lifecycle_bodies_identical_to_parent=True,hardware_failure_or_untrusted_pointer_reachability_not_inferred=True,native_GPU_MMIO_backend_is_explicit_host_boundary=True,phone_access=False,hardware_qualified=False);(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS289 actual parent counterexamples reproduced;current dispatch refuses five identity violations before native boundary;host only')
if __name__=='__main__':main()

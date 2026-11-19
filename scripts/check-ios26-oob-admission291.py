#!/usr/bin/env python3
"""Execute actual291 OOB admission and serial scope with explicit hardware boundaries."""
import argparse,hashlib,importlib.util,json,subprocess
from pathlib import Path

def pin(p):return dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',required=True,type=Path);p.add_argument('--fixture',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--sanitizer',choices=['address,undefined','thread'],default='address,undefined');a=p.parse_args();S=a.source_root.resolve();F=a.fixture.resolve();O=a.out.resolve();O.mkdir()
 spec=importlib.util.spec_from_file_location('scope291',Path(__file__).with_name('check-ios26-handover-scope291.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 receipt=json.loads((F/'result.json').read_text());assert receipt['passed'] and receipt['source']==pin(S/'ZornGen7HostRing26.cpp')
 cpp=(F/'hostcheck.cpp').read_text();src=(S/'ZornGen7HostRing26.cpp').read_text()
 def replace(x,y):
  nonlocal cpp
  assert cpp.count(x)==1,x;cpp=cpp.replace(x,y)
 # The fake transport/power grant is deliberately visible;it is not a source backend or hardware qualification.
 replace('class ZornGen7HostRing26 {',r'''
struct FixtureLegacyHfi{int acquireApplicationOob(ZornGen7HostRing26&,ZornGen7AppExecution26&){assert(false);return 1;}};
class ZornGen7HostRing26 {''')
 replace('void*hfi=nullptr;', 'FixtureLegacyHfi*hfi=nullptr;')
 replace('bool applicationOperationHeld()const;', 'IOReturn acquireApplicationOob(IOUserClient&,ZornGen7AppExecution26&);bool applicationOperationHeld()const;')
 replace('thread_t appOperationThread=THREAD_NULL;', 'thread_t appOobThread=THREAD_NULL;thread_t appOperationThread=THREAD_NULL;')
 replace('class ZornGen7DirectHfi26:public OSObject{public:bool physicalOobHeld(const ZornGen7HostRing26&)const;};','class ZornGen7DirectHfi26:public OSObject{public:bool physicalOobHeld(const ZornGen7HostRing26&)const;int acquirePhysicalOob(ZornGen7HostRing26&){return 0;}};')
 # Keep aggregate initialization layout unchanged by putting the extra field at the end.
 cpp=cpp.replace('thread_t appOobThread=THREAD_NULL;thread_t appOperationThread=THREAD_NULL;', 'thread_t appOperationThread=THREAD_NULL;')
 replace('  void lockIssuer(){', '  thread_t appOobThread=THREAD_NULL;\n'+m.extract(src,'    struct AppSerialScope {')+';\n  void lockIssuer(){')
 replace('int main(){unsigned controls=0;',m.extract(src,'IOReturn ZornGen7HostRing26::acquireApplicationOob')+r'''
int main(){unsigned controls=0;
 for(unsigned fault=0;fault<12;++fault){HandoverFixture h;auto&f=h.f;f.execution.oobMemberHeld_=false;h.oldProcess.clientState.submit.count=1;h.oldProcess.vm_.pending=true;
  auto task=callerTask;
  if(fault==0)callerTask=reinterpret_cast<void*>(9);
  if(fault==1)f.execution.task_=kernel_task;
  if(fault==2)f.execution.task_=TASK_NULL;
  if(fault==3)f.client.openingTask_=reinterpret_cast<void*>(9);
  if(fault==4)f.client.closing_=true;
  if(fault==5)f.client.provider=nullptr;
  if(fault==6)f.execution.client_=&f.foreign;
  if(fault==7)f.execution.oobMemberReleased_=true;
  if(fault==8)f.s.appExecutionPending=true;
  if(fault==9)f.s.appOperationPending=true;
  if(fault==10)f.s.appOobTransition=true;
  if(fault==11)f.healthy=false;
  auto raw=f.acquireApplicationOob(f.client,f.execution);callerTask=task;
  assert(raw&&!f.drains&&!f.contextChecks&&!f.domain.transitions&&!f.authorityCalls&&!f.execution.oobMemberHeld_);
  assert(f.s.processSelected==&h.oldProcess&&h.oldProcess.clientState.submit.count==1&&h.oldProcess.vm_.pending&&h.oldProcess.asidHeld_&&h.oldProcess.liveMappings==3);
  assert(!f.s.appOobTransition&&!f.s.appSerialThread||fault==10);++controls;
 }
 {HandoverFixture h;auto&f=h.f;f.execution.oobMemberHeld_=false;h.oldProcess.clientState.submit.count=1;h.oldProcess.vm_.pending=true;

  assert(!f.acquireApplicationOob(f.client,f.execution));
  assert(f.lastWaitBudget==1000000&&f.drains==1&&!f.s.processSelected&&h.oldProcess.state_.detached&&!h.oldProcess.vm_.pending&&!h.oldProcess.clientState.submit.count);
  assert(f.execution.oobMemberHeld_&&f.authorityCalls==1&&!f.s.appOobTransition&&f.s.appOobThread==THREAD_NULL&&f.execution.refs==1&&!f.s.stopped);
  assert(h.oldProcess.asidHeld_&&h.oldProcess.liveMappings==3);++controls;
 }
 {HandoverFixture h;auto&f=h.f;f.execution.oobMemberHeld_=false;h.oldProcess.clientState.submit.count=1;h.oldProcess.vm_.pending=true;f.positiveBudgetExpired=true;
  assert(f.acquireApplicationOob(f.client,f.execution)==kIOReturnTimeout);
  assert(f.lastWaitBudget==1000000&&f.s.stopped&&f.s.irq.halted()&&f.s.processSelected==&h.oldProcess&&h.oldProcess.clientState.submit.count==1&&h.oldProcess.vm_.pending&&h.oldProcess.asidHeld_);
  assert(!f.execution.oobMemberHeld_&&!f.authorityCalls&&!f.domain.transitions&&f.execution.refs==1);++controls;
 }
 printf("PASS291 actual OOB admission/serial scope/foreign drain:controls=%u;wrong caller never drains;expiry retains old owner;physical grant and MMIO remain explicit host boundaries\\n",controls);return 0;
}
#if 0
int retained_parent_main(){unsigned controls=0;''')
 cpp+='\n#endif\n';(O/'actual-oob.cpp').write_text(cpp)
 command=['xcrun','clang++','-std=c++17','-O1','-g','-pthread','-fno-omit-frame-pointer','-fsanitize='+a.sanitizer,str(O/'actual-oob.cpp'),'-o',str(O/'actual-oob')];r=subprocess.run(command,capture_output=True,text=True);(O/'compile.stderr').write_text(r.stderr);assert not r.returncode,r.stderr[-4000:]
 r=subprocess.run([str(O/'actual-oob')],capture_output=True,text=True);(O/'run.stdout').write_text(r.stdout);(O/'run.stderr').write_text(r.stderr);assert not r.returncode,r.stderr
 result=dict(passed=True,source=pin(S/'ZornGen7HostRing26.cpp'),fixture=pin(F/'result.json'),test_tool=pin(__file__),sanitizer=a.sanitizer,actual_OOB_admission_and_AppSerialScope_bodies_executed=True,actual_matchesOwnedSession_and_foreign_restore_bodies_executed=True,wrong_task_or_session_refused_before_foreign_drain=True,positive_expiry_retains_inflight_old_resources=True,physical_power_MMIO_native_drain_boundaries_explicit=True,hardware_qualified=False,phone_access=False,stdout=r.stdout);(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(r.stdout)
if __name__=='__main__':main()

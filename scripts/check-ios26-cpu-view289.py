#!/usr/bin/env python3
"""Execute actual scalar-query dispatch with the retained scope/lifecycle fixture."""
import argparse,hashlib,importlib.util,json,os,subprocess
from pathlib import Path

def pin(p):
 return dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--scope-fixture',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sanitizer',choices=['address,undefined','thread'],default='address,undefined');a=p.parse_args()
 S=a.source_root.resolve();F=a.scope_fixture.resolve();O=a.out.resolve();O.mkdir()
 spec=importlib.util.spec_from_file_location('scope288',Path(__file__).with_name('check-ios26-readonly-operation288.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 prior=json.loads((F/'result.json').read_text());assert prior['passed']
 for k in ['source','header','test_tool']:assert pin(Path(prior[k]['path']))==prior[k],k
 cpp=(F/'hostcheck.cpp').read_text();src=(S/'ZornGen7HostRing26.cpp').read_text();direct=(S/'direct-runtime/ZornGen7DirectClient26.cpp').read_text()
 def replace(old,new):
  nonlocal cpp
  assert cpp.count(old)==1,old;cpp=cpp.replace(old,new,1)
 prefix='#include "'+str(S/'userland/NativeAdrenoABI.h')+'"\n#include <cstring>\n#include <functional>\n'
 cpp=prefix+cpp
 replace('struct ZornGen7ProcessTables26 {',r'''
struct NativeAdrenoCpuSpan{uint64_t physical,bytes;};
struct NativeAdrenoCpuView{NativeAdrenoCpuSpan*spans;size_t count;uint64_t bytes;};
struct IOAddressRange{uint64_t address,length;};using UInt32=uint32_t;using IOOptionBits=uint32_t;
constexpr uint32_t kIODirectionInOut=1,kIOMemoryTypePhysical64=2;
static bool failRanges=false,failDescriptor=false;static unsigned descriptorLive=0;
template<class T>static T*newRanges(size_t n){return failRanges?nullptr:new T[n];}
#define IONewData(T,N) newRanges<T>(N)
#define IODeleteData(P,T,N) delete[] P
struct IOMemoryDescriptor{unsigned refs=1;std::vector<IOAddressRange>ranges;
 static IOMemoryDescriptor*withAddressRanges(IOAddressRange*p,UInt32 n,IOOptionBits flags,void*task){assert(flags==3&&!task);if(failDescriptor)return nullptr;auto*out=new IOMemoryDescriptor;out->ranges.assign(p,p+n);++descriptorLive;return out;}
 void release(){assert(refs==1&&descriptorLive);--descriptorLive;delete this;}
};
struct FixtureCpuMemory{NativeAdrenoCpuSpan spans[2]{{0x40000000,16384},{0x50000000,16384}};size_t count=2;bool valid=true;std::function<void()>duringView;
 bool cpuView(NativeAdrenoCpuView*out){if(duringView)duringView();if(!valid)return false;*out={spans,count,32768};return true;}
};
struct ZornGen7ProcessTables26 {''')
 replace('struct ZornGen7ProcessTables26 {',r'''
// Explicit host boundary: actual native dispatcher/MMIO is NOT simulated hardware.
struct NativeAdrenoRingClock{void*cookie;uint64_t(*now_us)(void*);int(*idle)(void*);};
static std::function<void(uint32_t)> backendCheck;
struct FixtureNativeClient {
 unsigned calls=0;int raw=0;uint32_t last=0;FixtureCpuMemory cpuMemory;unsigned preflights=0,memoryLookups=0;uint32_t leases=2;
 int preflightCpuUnmap(const NativeAdrenoAbiBoCpuUnmap*in,uint32_t*out){++preflights;if(in->reserved||in->token!=1||!in->handle)return kIOReturnBadArgument;if(raw)return raw;*out=leases;return 0;}
 FixtureCpuMemory*memoryForToken(uint32_t token){++memoryLookups;return token==1?&cpuMemory:nullptr;}

 int dispatch(uint32_t m,const void*,size_t,void*out,size_t n,const NativeAdrenoRingClock*){++calls;last=m;if(backendCheck)backendCheck(m);if(!raw&&n)std::memset(out,0x5a,n);return raw;}
 int importBo(const NativeAdrenoAbiBoImport*in,task_t task,NativeAdrenoAbiBoAllocReply*out){assert(in&&task==current_task());return dispatch(NativeAdrenoMethodBoImport,in,sizeof(*in),out,sizeof(*out),nullptr);}
};
struct CallerTaskReference{task_t task=current_task();};
class ZornGen7DirectClient26{public:static size_t inputSize(uint32_t);static size_t outputSize(uint32_t);};
struct ZornGen7ProcessTables26 {''')
 replace('struct ClientState{Queue submit;}', 'struct ClientState{Queue submit;FixtureNativeClient client;}')
 replace('ZornGen7ProcessTables26*prepareOutput=nullptr;', 'ZornGen7ProcessTables26*prepareOutput=nullptr;bool kernelProcessClosing=false;task_t kernelTaskOwner=TASK_NULL;')
 replace(' bool applicationOperationHeld()const;',r'''
 static uint64_t nativeNow(void*){return 1;}static int nativeIdle(void*){return 0;}
 static int guard(void*p){return static_cast<ZornGen7HostRing26*>(p)->bootstrapHealthy()?0:1;}
 IOReturn dispatchApplicationProcess(IOUserClient&,ZornGen7AppExecution26&,ZornGen7ProcessTables26&,uint32_t,const void*,size_t,void*,size_t);
 IOReturn dispatchProcessClient(IOUserClient&,ZornGen7ProcessTables26&,task_t,uint32_t,const void*,size_t,void*,size_t);
 bool applicationProcessIdentity289(IOUserClient&,const ZornGen7AppExecution26&,const ZornGen7ProcessTables26&)const;
 IOReturn copyApplicationIoView(IOUserClient&,ZornGen7AppExecution26&,ZornGen7ProcessTables26&,uint32_t,IOMemoryDescriptor*&);
 IOReturn applicationIoLeases(IOUserClient&,ZornGen7AppExecution26&,ZornGen7ProcessTables26&,const NativeAdrenoAbiBoCpuUnmap&,uint32_t&);
 bool applicationOperationHeld()const;''')
 replace('static bool IORecursiveLockHaveLock(', 'static void IORecursiveLockLock(Lock*p){IOLockLock(p);}static void IORecursiveLockUnlock(Lock*p){IOLockUnlock(p);}\nstatic bool IORecursiveLockHaveLock(')
 bodies='\n'.join(m.extract(src,n) for n in ['static bool nativeContextFreeMethod289','IOReturn ZornGen7HostRing26::dispatchApplicationProcess','IOReturn ZornGen7HostRing26::dispatchProcessClient','bool ZornGen7HostRing26::applicationProcessIdentity289','IOReturn ZornGen7HostRing26::copyApplicationIoView','IOReturn ZornGen7HostRing26::applicationIoLeases'])
 bodies+='\n'+'\n'.join(m.extract(direct,n) for n in ['size_t ZornGen7DirectClient26::inputSize','size_t ZornGen7DirectClient26::outputSize'])
 replace('int main(){unsigned controls=0;',bodies+'\nint main(){unsigned controls=0;')
 tests=r'''
 auto call=[](ZornGen7HostRing26&f,uint32_t method,void*out){
  alignas(8) uint8_t input[sizeof(NativeAdrenoAbiSubmitBatch)]{};
  return f.dispatchApplicationProcess(f.client,f.execution,f.process,method,input,ZornGen7DirectClient26::inputSize(method),out,ZornGen7DirectClient26::outputSize(method));
 };
 for(uint32_t method=1;method<=17;++method){
  ZornGen7HostRing26 f;alignas(8) uint8_t out[sizeof(NativeAdrenoAbiMetadata)];std::memset(out,0xcc,sizeof(out));
  const bool readonly=method==1||method==7||method==8||method==13||method==14||method==15;
  backendCheck=[&](uint32_t seen){assert(seen==method&&f.s.issuerHeld()&&f.applicationOperationHeld()&&f.authoritySawWholeMutex);assert(readonly?(!f.s.processSelected&&f.process.state_.detached):(f.s.processSelected==&f.process&&!f.process.state_.detached));};
  assert(!call(f,method,out));backendCheck=nullptr;
  assert(f.process.clientState.client.calls==1&&f.process.clientState.client.last==method&&!f.s.processSelected&&!f.s.stopped&&f.process.liveMappings==3&&f.process.asidHeld_);
  assert(f.domain.transitions==(readonly?0u:2u));
  if(readonly)assert(!f.drains&&!f.contextChecks);
  for(size_t j=0;j<sizeof(out);++j)assert(out[j]==(j<ZornGen7DirectClient26::outputSize(method)?0x5a:0xcc));++controls;
 }
 {ZornGen7HostRing26 f;f.process.clientState.client.raw=kIOReturnUnsupported;uint8_t out[sizeof(NativeAdrenoAbiStatus)];std::memset(out,0xcc,sizeof(out));
  assert(call(f,NativeAdrenoMethodGetStatus,out)==kIOReturnUnsupported&&f.process.clientState.client.calls==1&&!f.s.stopped&&!f.domain.transitions&&!f.drains);for(auto b:out)assert(b==0xcc);++controls;}
 {HandoverFixture h;auto&f=h.f;h.oldProcess.clientState.submit.count=1;h.oldProcess.vm_.pending=true;
  uint8_t out[sizeof(NativeAdrenoAbiTimestamp)];assert(!call(f,NativeAdrenoMethodGetTimestamp,out));
  assert(f.s.processSelected==&h.oldProcess&&h.oldProcess.clientState.submit.count==1&&h.oldProcess.vm_.pending&&!h.oldProcess.state_.detached&&h.oldProcess.asidHeld_&&!f.s.stopped&&!f.drains&&!f.domain.transitions);++controls;}
 for(unsigned fault=0;fault<12;++fault){ZornGen7HostRing26 f;uint8_t out[sizeof(NativeAdrenoAbiParams)];std::memset(out,0xcc,sizeof(out));
  if(fault==0)f.process.ringOwner_=nullptr;if(fault==1)f.process.domain_=nullptr;
  if(fault==2)f.process.clientOwner_=&f.foreign;if(fault==3)f.process.clientTask_=kernel_task;
  if(fault==4)f.process.clientOpen_=false;if(fault==5)f.process.clientClosed_=true;
  if(fault==6)f.process.vmAttached_=false;if(fault==7)f.process.vmDetached_=true;
  if(fault==8)f.process.state_.poisoned=true;if(fault==9)f.process.clientState_=nullptr;
  if(fault==10)f.process.clientState.submit.poison=true;if(fault==11)f.client.openingTask_=kernel_task;
  assert(call(f,NativeAdrenoMethodQuery,out)&&!f.process.clientState.client.calls&&!f.domain.transitions&&!f.drains);for(auto b:out)assert(b==0xcc);++controls;
 }
 for(unsigned fault=0;fault<6;++fault){ZornGen7HostRing26 f;uint8_t out[sizeof(NativeAdrenoAbiParams)];std::memset(out,0xcc,sizeof(out));uint32_t method=1;size_t in=0,n=sizeof(out);const void*input=nullptr;void*output=out;
  if(fault==0)method=0;if(fault==1)method=18;if(fault==2)in=1;if(fault==3)n--;
  if(fault==4)output=nullptr;if(fault==5){callerTask=TASK_NULL;}
  assert(f.dispatchApplicationProcess(f.client,f.execution,f.process,method,input,in,output,n)==kIOReturnBadArgument&&!f.authorityCalls&&!f.process.clientState.client.calls);callerTask=reinterpret_cast<void*>(2);for(auto b:out)assert(b==0xcc);++controls;
 }
 {ZornGen7HostRing26 f;uint8_t out[sizeof(NativeAdrenoAbiParams)];f.authorityRaw=kIOReturnNotPermitted;
  assert(call(f,1,out)==kIOReturnNotPermitted&&!f.process.clientState.client.calls&&!f.domain.transitions);++controls;}
 {ZornGen7HostRing26 f;uint8_t out[sizeof(NativeAdrenoAbiParams)];
  assert(f.dispatchProcessClient(f.client,f.process,current_task(),1,nullptr,0,out,sizeof(out))==kIOReturnNotReady&&!f.process.clientState.client.calls);++controls;}
'''
 tests+='\n for(unsigned fault=0;fault<4;++fault){ZornGen7HostRing26 f;ZornGen7ProcessTables26 duplicate=f.process;uint8_t out[sizeof(NativeAdrenoAbiParams)];std::memset(out,0xcc,sizeof(out));\n  if(fault==0)f.s.processClients=nullptr;\n  if(fault==1){f.process.ringNext_=&duplicate;duplicate.ringNext_=nullptr;}\n  if(fault==2)f.process.vm_.poison=true;\n  if(fault==3){f.s.processClients=&duplicate;duplicate.ringNext_=nullptr;}\n  assert(call(f,1,out)&&!f.process.clientState.client.calls&&!f.domain.transitions&&!f.drains);for(auto b:out)assert(b==0xcc);++controls;\n }\n {ZornGen7HostRing26 f;ZornGen7AppExecution26*scope=nullptr;assert(!f.beginApplicationOperation(f.client,ZornGen7AppOperation26::CpuView,scope,nullptr,false));uint8_t out[sizeof(NativeAdrenoAbiParams)];\n  assert(f.dispatchProcessClient(f.client,f.process,reinterpret_cast<void*>(3),1,nullptr,0,out,sizeof(out))==kIOReturnNotReady&&!f.process.clientState.client.calls);assert(f.finishApplicationOperation(*scope,kIOReturnNotReady));++controls;}\n for(unsigned foreign=0;foreign<2;++foreign){HandoverFixture h;auto&f=h.f;if(!foreign){f.s.processSelected=nullptr;h.oldProcess.state_.detached=true;}else{h.oldProcess.clientState.submit.count=1;h.oldProcess.vm_.pending=true;}\n  NativeAdrenoAbiBoCpuUnmap request{};request.handle=1;request.token=1;uint32_t leases=123;\n  assert(!f.applicationIoLeases(f.client,f.execution,f.process,request,leases)&&leases==2&&f.process.clientState.client.preflights==1&&!f.domain.transitions&&!f.drains&&f.authoritySawWholeMutex);\n  IOMemoryDescriptor*out=nullptr;assert(!f.copyApplicationIoView(f.client,f.execution,f.process,1,out)&&out&&descriptorLive==1);\n  assert(out->ranges.size()==2&&out->ranges[0].address==0x40000000&&out->ranges[1].address==0x50000000&&out->ranges[0].length==16384&&!f.domain.transitions&&!f.drains);\n  if(foreign)assert(f.s.processSelected==&h.oldProcess&&h.oldProcess.clientState.submit.count==1&&h.oldProcess.vm_.pending);\n  out->release();assert(!descriptorLive);++controls;\n }\n for(unsigned fault=0;fault<9;++fault){ZornGen7HostRing26 f;auto&native=f.process.clientState.client;IOMemoryDescriptor*out=nullptr;\n  if(fault==0)f.s.processClients=nullptr;if(fault==1)f.process.vm_.poison=true;\n  if(fault==2)native.cpuMemory.valid=false;if(fault==3)native.cpuMemory.count=0;\n  if(fault==4)native.cpuMemory.count=65537;if(fault==5)failRanges=true;\n  if(fault==6)failDescriptor=true;if(fault==7)native.cpuMemory.duringView=[&]{f.healthy=false;};\n  if(fault==8)f.process.clientState_=nullptr;\n  assert(f.copyApplicationIoView(f.client,f.execution,f.process,1,out)&&!out&&!descriptorLive&&!f.domain.transitions&&!f.drains);failRanges=failDescriptor=false;++controls;\n }\n for(unsigned fault=0;fault<5;++fault){ZornGen7HostRing26 f;NativeAdrenoAbiBoCpuUnmap request{};request.handle=1;request.token=1;uint32_t leases=123;\n  if(fault==0)request.reserved=1;if(fault==1)request.token=2;if(fault==2)request.handle=0;\n  if(fault==3)f.s.processClients=nullptr;if(fault==4)f.process.vm_.poison=true;\n  assert(f.applicationIoLeases(f.client,f.execution,f.process,request,leases)&&leases==123&&!f.domain.transitions&&!f.drains);++controls;\n }\n {ZornGen7HostRing26 f;IOMemoryDescriptor*out=nullptr;assert(f.copyApplicationIoView(f.client,f.execution,f.process,0,out)==kIOReturnBadArgument&&!f.authorityCalls);out=reinterpret_cast<IOMemoryDescriptor*>(1);assert(f.copyApplicationIoView(f.client,f.execution,f.process,1,out)==kIOReturnBadArgument&&!f.authorityCalls);++controls;}\n'
 replace(' std::printf("PASS288',tests+'\n std::printf("PASS288')
 cpp=cpp.replace('PASS288 actual read-only scope plus retained lifecycle/context controls','PASS289 actual context-free dispatch/CPU-view/token/lease plus retained lifecycle/context controls')
 C=O/'hostcheck.cpp';C.write_text(cpp);env=dict(os.environ,TSAN_OPTIONS='symbolize=0',ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0');runs=[]
 for cmd in [['/usr/bin/clang++','-std=c++17','-O1','-g','-fno-omit-frame-pointer','-fsanitize='+a.sanitizer,str(C),'-o',str(O/'hostcheck')],[str(O/'hostcheck')]]:
  r=subprocess.run(cmd,capture_output=True,text=True,timeout=120,env=env);runs.append(dict(arguments=cmd,exit=r.returncode,stdout=r.stdout,stderr=r.stderr));(O/'commands.json').write_text(json.dumps(runs,indent=2)+'\n');assert not r.returncode,r.stderr[-6000:]
 result=dict(passed=True,sanitizer=a.sanitizer,test_tool=pin(Path(__file__).resolve()),source=pin(S/'ZornGen7HostRing26.cpp'),header=pin(S/'ZornGen7HostRing26.h'),ABI=pin(S/'userland/NativeAdrenoABI.h'),scope_fixture=pin(F/'hostcheck.cpp'),scope_result=pin(F/'result.json'),actual_dispatch_application_and_process_bodies_compiled=True,actual_input_output_sizes_compiled=True,all_17_methods_context_selection_and_raw_result_tested=True,actual_CPU_view_and_preflight_bodies_compiled=True,CPU_memory_descriptor_and_native_client_are_explicit_host_boundaries=True,exact_process_membership_duplicate_and_poison_refusals_tested=True,foreign_pending_context_preserved=True,task_ownership_poison_pointer_authority_refusals_tested=True,native_dispatch_MMIO_SMMU_clock_boundaries_are_explicit_host_fixtures=True,hardware_qualified=False,phone_access=False,output=runs[-1]['stdout']);(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result['output'],end='')

if __name__=='__main__':main()

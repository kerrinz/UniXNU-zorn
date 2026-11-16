#!/usr/bin/env python3
"""Test actual shared service and Board member lifetime; Ring/MMIO are explicit boundaries."""
from pathlib import Path
import argparse,ast,hashlib,json,os,subprocess

def extract(t,start):
 a=t.index(start);z=t.index('{',a)+1;d=1
 while d:d+=(t[z]=='{')-(t[z]=='}');z+=1
 return t[a:z]

def literal(path,name):
 tree=ast.parse(path.read_text())
 for n in ast.walk(tree):
  if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id==name for x in n.targets):
   value=n.value
   while isinstance(value,ast.Call) and isinstance(value.func,ast.Attribute):value=value.func.value
   return ast.literal_eval(value)
 raise ValueError(name)

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--parent-source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--kind',choices=['board','service'],required=True);p.add_argument('--sanitizer',choices=['address,undefined','thread'],default='address,undefined');a=p.parse_args();S=a.source_root.resolve();P=a.parent_source.resolve();O=a.out.resolve();O.mkdir();D=Path(__file__).resolve().parent
 if a.kind=='board':
  source=S/'ZornGen7DarwinBoardOwner.cpp';text=source.read_text();old=(P/source.name).read_text()
  for name in ['    bool nativePhysicalResourcesHeld(','    bool nativeApplicationWindowHeld(']:assert extract(text,name)==extract(old,name)
  metadata=text[text.index('    struct ApplicationSession {'):text.index('    bool nativePhysicalResourcesHeld(')]
  callbacks='\n'.join(extract(text,'        applicationAuthority.'+n+'=[]')+';' for n in ['acquire','check','release'])
  prefix=literal(D/'check-ios26-board-sessions.py','prefix').replace('ACTUAL_METADATA',metadata).replace('ACTUAL_CALLBACKS',callbacks)
  prefix=prefix.replace('bool direct_client_attempted=false,physicalHealthy=true;','bool direct_client_attempted=false,physicalHealthy=true,direct_physical_held=false;ZornGen7HostRing26 *direct_physical_ring=nullptr;')
  fixture=literal(D/'check-ios26-board-sessions.py','tests').split('int main(){')[0]
  tests=r'''
int main(){unsigned controls=0;
 {Fixture f;Storage::ApplicationSession*out=nullptr;assert(f.s.reserveApplicationSession(f.a,f.ta,out)==kIOReturnBadArgument&&!out);++controls;}
 {Fixture f;assert(!f.acquire(f.a,f.ta));auto *first=f.s.direct_app_sessions;assert(first&&first->generation==1&&!f.s.direct_app_active&&first->phase==Storage::ApplicationSession::Phase::Held);
  f.s.direct_physical_held=true;f.s.direct_physical_ring=&f.ring;callingTask=f.tb;assert(!f.acquire(f.b,f.tb));auto*second=f.s.direct_app_sessions;assert(second!=first&&second->next==first&&second->generation==2&&f.s.direct_app_acquires==2);++controls;
  assert(f.auth.check(&f.board,f.a,f.ta,f.tb,ZornGen7AppOperation26::Submit)==kIOReturnNotReady);++controls;
  callingTask=f.ta;assert(!f.auth.check(&f.board,f.a,f.ta,f.ta,ZornGen7AppOperation26::Submit));assert(!f.release(f.a,f.ta));assert(f.s.direct_app_sessions==second&&!second->next&&f.s.direct_app_releases==1&&f.s.direct_oob_epoch==6);++controls;
  callingTask=f.tb;assert(!f.auth.check(&f.board,f.b,f.tb,f.tb,ZornGen7AppOperation26::Submit));assert(!f.release(f.b,f.tb));assert(!f.s.direct_app_sessions&&f.s.direct_app_releases==2&&f.s.direct_oob_epoch==6);++controls;
 }
 for(unsigned failure=0;failure<11;++failure){Fixture f;
  if(failure==0)f.s.stage=Stage::Other;if(failure==1)f.s.direct_app_publish_attempted=false;if(failure==2)f.s.direct_client_attempted=true;if(failure==3)f.s.host_ring=nullptr;if(failure==4)f.s.native_cx_gpu=nullptr;if(failure==5)f.s.host_gpu_start_gmu_resource=nullptr;if(failure==6)f.s.direct_oob_epoch=7;if(failure==7)f.ring.binding=false;if(failure==8)f.hfi.flags=126;if(failure==9)f.hfi.raw=1;if(failure==10)f.s.physicalHealthy=false;
  const auto old=frees.load();assert(f.acquire(f.a,f.ta)==kIOReturnNotReady);auto *r=f.s.direct_app_sessions;assert(r&&r->client==&f.a&&r->task==f.ta&&r->phase==Storage::ApplicationSession::Phase::Failed&&!f.s.direct_app_active&&frees==old);
  assert(f.acquire(f.a,f.ta)==kIOReturnExclusiveAccess&&f.s.direct_app_sessions==r);assert(f.release(f.a,f.ta)==kIOReturnNotReady&&frees==old);++controls;
 }
 {Fixture f;allocationFails=true;assert(f.acquire(f.a,f.ta)==kIOReturnNoMemory&&!f.s.direct_app_sessions);allocationFails=false;++controls;}
 {Fixture f;f.s.direct_app_acquires=f.s.direct_app_releases=UINT32_MAX;assert(f.acquire(f.a,f.ta)==kIOReturnExclusiveAccess&&!f.s.direct_app_sessions);++controls;}
 {Fixture f;assert(!f.acquire(f.a,f.ta));f.s.direct_physical_held=true;f.s.direct_physical_ring=&f.ring;callingTask=f.tb;assert(!f.acquire(f.b,f.tb));auto*second=f.s.direct_app_sessions;second->generation=0;assert(f.release(f.b,f.tb)==kIOReturnNotReady);second->generation=2;assert(!f.release(f.b,f.tb));callingTask=kernel_task;assert(!f.release(f.a,f.ta));++controls;}
 {Fixture f;assert(!f.acquire(f.a,f.ta));callingTask=f.tb;assert(f.acquire(f.b,f.tb)==kIOReturnNotReady);assert(f.s.direct_app_sessions->phase==Storage::ApplicationSession::Phase::Failed&&f.s.direct_app_acquires==1);++controls;}
 {Fixture f;assert(!f.acquire(f.a,f.ta));f.s.direct_physical_held=true;f.s.direct_physical_ring=&f.ring;constexpr unsigned count=12;IOUserClient clients[count];task_t tasks[count];IOReturn results[count]{};std::atomic<bool>go{false};std::vector<std::thread>threads;
  for(unsigned i=0;i<count;++i){tasks[i]=reinterpret_cast<void*>(uintptr_t(100+i));threads.emplace_back([&,i]{callingTask=tasks[i];while(!go.load())std::this_thread::yield();results[i]=f.acquire(clients[i],tasks[i]);});}go=true;for(auto&x:threads)x.join();for(auto raw:results)assert(!raw);assert(f.s.direct_app_acquires==13);++controls;
  for(unsigned i=0;i<count;++i){callingTask=tasks[i];assert(!f.release(clients[i],tasks[i]));}callingTask=f.ta;assert(!f.release(f.a,f.ta)&&!f.s.direct_app_sessions&&f.s.direct_app_releases==13);++controls;
 }
 {Fixture f;constexpr unsigned count=65;IOUserClient clients[count];callingTask=f.ta;for(unsigned i=0;i<64;++i){assert(!f.acquire(clients[i],f.ta));f.s.direct_physical_held=true;f.s.direct_physical_ring=&f.ring;}assert(f.acquire(clients[64],f.ta)==kIOReturnExclusiveAccess&&f.s.direct_app_acquires==64);for(unsigned i=0;i<64;++i)assert(!f.release(clients[i],f.ta));assert(!f.s.direct_app_sessions);++controls;}
 assert(liveRecords==0&&allocations==frees);printf("PASS257 Board actual members,distinct tasks,non-head retirement,12 concurrent joins,64-member bound,failed retention;physical/Ring boundaries explicit (%u controls)\n",controls);
}
'''
  code=prefix+fixture+tests;actual=[source];scope='Actual Board record helpers and three callbacks;full physical predicate byte-equal to256;Ring/MMIO predicates explicit fixtures'
 else:
  source=S/'direct-runtime/ZornGen7AppIo26.cpp';text=source.read_text();header=S/'direct-runtime/ZornGen7AppIo26.h';h='\n'.join(x for x in header.read_text().splitlines() if not x.startswith('#include') and x!='#pragma once')
  names=['IOReturn ZornGen7AppIoService26::newUserClient','IOReturn ZornGen7AppIoService26::reserveNativeClient','void ZornGen7AppIoService26::returnClientSlot','bool ZornGen7AppIoClient26::matchesOwnedSession','IOReturn ZornGen7AppIoClient26::ensureProcess','IOReturn ZornGen7AppIoClient26::dropViews','IOReturn ZornGen7AppIoClient26::clientClose','void ZornGen7AppIoClient26::free']
  prefix=literal(D/'check-ios26-lazy-session.py','prefix').replace('kIOReturnUnsupported=6;','kIOReturnUnsupported=6,kIOReturnBusy=9;').replace('struct ZornGen7ProcessTables26{}','class ZornGen7ProcessTables26{}').replace('struct ZornGen7HostRing26:OSObject {','class ZornGen7HostRing26:public OSObject {public:').replace('struct IOUserClient:IOService {','class IOUserClient:public IOService {public:');fixture=literal(D/'check-ios26-lazy-session.py','suffix').split('int main(){')[0].replace('f.service_->','f.service->').replace('++nativePrepare;if(failure==10)', '++nativePrepare;if(failure==17)return kIOReturnBusy;if(failure==10)')
  tests=r'''
int main(){
 {Fixture f;const auto before=nativePrepare.load();auto a=f.open(),b=f.open();assert(!a->attempted_&&!b->attempted_&&!f.service->reserved_&&nativePrepare==before);f.close(b);++checks;
  assert(!acquire(a));b=f.open();assert(!acquire(b));assert(f.service->client_==b&&b->nativeNext_==a&&a->nativeNext_==nullptr&&nativePrepare==before+2);++checks;
  f.service->returnClientSlot(nullptr);assert(f.service->client_==b);f.close(a);assert(f.service->client_==b&&!b->nativeNext_&&b->pinned_);f.close(b);++checks;
 }
 {Fixture f;auto a=f.open();const auto before=nativePrepare.load();failure=17;assert(acquire(a)==kIOReturnBusy&&!a->attempted_&&!a->pinned_&&!a->execution_&&!f.service->client_&&a->refs==1&&nativePrepare==before+1);failure=0;assert(!acquire(a)&&nativePrepare==before+2);f.close(a);++checks;}
 for(unsigned mode:{1u,2u,3u,4u,5u,6u,7u}){Fixture f;auto a=f.open();assert(!acquire(a));failure=mode;IOUserClient*out=(IOUserClient*)1;assert(f.service->newUserClient(&f.task,nullptr,0x4147,nullptr,&out)&&!out);assert(f.service->client_==a);failure=0;f.close(a);++checks;}
 for(unsigned mode=0;mode<4;++mode){Fixture f;Task other;IOUserClient*out=(IOUserClient*)1;task_t t=mode==0?nullptr:mode==1?kernel_task:mode==2?&other:&f.task;assert(f.service->newUserClient(t,nullptr,mode==3?1:0x4147,nullptr,&out)==kIOReturnNotPermitted&&!out);++checks;}
 for(unsigned mode:{10u,11u,12u,13u,14u,16u}){Fixture f;auto a=f.open();if(mode<13)failure=mode;assert(acquire(a)==(mode<13?int(mode):0));if(mode>=13)failure=mode;assert(a->clientClose()==int(mode)&&a->attempted_&&a->pinned_&&a->refs==2&&f.service->client_==a);failure=0;auto b=f.open();assert(!acquire(b));f.close(b);assert(f.service->client_==a);cleanupFailedFixture(f,a);++checks;}
 for(unsigned mode=0;mode<7;++mode){Fixture f;auto a=f.open();auto serial=a->serial_;auto views=a->views_;auto service=a->service_;auto owner=a->owner_;if(mode==0)a->serial_=nullptr;if(mode==1)a->views_=nullptr;if(mode==2)a->viewError_=1;if(mode==3)a->service_=nullptr;if(mode==4)a->owner_=nullptr;if(mode==5)callingTask=kernel_task;if(mode==6)a->live_=false;assert(f.service->reserveNativeClient(*a)==kIOReturnNotReady&&!f.service->reserved_);a->serial_=serial;a->views_=views;a->viewError_=0;a->service_=service;a->owner_=owner;a->live_=true;callingTask=&f.task;f.close(a);++checks;}
 {Fixture f;std::vector<ZornGen7AppIoClient26*>all;for(unsigned i=0;i<12;++i)all.push_back(f.open());auto before=nativePrepare.load();std::atomic<unsigned>winners{};std::vector<std::thread>threads;for(auto*p:all)threads.emplace_back([&,p]{callingTask=&f.task;assert(!acquire(p));++winners;});for(auto&t:threads)t.join();assert(winners==12&&nativePrepare==before+12);for(auto*p:all)f.close(p);++checks;}
 {Fixture f;std::vector<ZornGen7AppIoClient26*>all;for(unsigned i=0;i<65;++i)all.push_back(f.open());for(unsigned i=0;i<64;++i)assert(!acquire(all[i]));assert(acquire(all[64])==kIOReturnExclusiveAccess&&!all[64]->attempted_&&!all[64]->pinned_);f.close(all[64]);for(unsigned i=0;i<64;++i)f.close(all[i]);++checks;}
 assert(!viewArrays&&!liveLocks&&!liveObjects);printf("PASS257 actual service shared-member metadata/admission/close/failed retention and12 concurrent reservations;Root/native/XNU boundaries explicit (%u controls)\n",checks);
}
'''
  prepare=extract((S/'ZornGen7HostRing26.cpp').read_text(),'IOReturn ZornGen7HostRing26::prepareApplicationExecution(')
  create=extract((S/'ZornGen7AppExecution26.cpp').read_text(),'IOReturn ZornGen7AppExecution26::create(')
  assert prepare.index('return kIOReturnBusy;')<prepare.index('s.maps.createApplicationExecution(')
  assert create.index('out=p;')<create.index('authority_.acquire(')
  code=prefix+'\n'+h+'\n'+'\n'.join(extract(text,n) for n in names)+'\n'+fixture+tests;actual=[source,header,S/'ZornGen7HostRing26.cpp',S/'ZornGen7AppExecution26.cpp',S/'ZornGen7RegisterMaps26.cpp'];scope='Actual service/client header and eight methods;Root native/VM/OOB authority and XNU are explicit fixtures,not multiclient GPU hardware acceptance'
 f=O/'actual.cpp';f.write_text(code);env=dict(os.environ,ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0',TSAN_OPTIONS='symbolize=0:halt_on_error=1')
 def run(n,args):
  r=subprocess.run(args,capture_output=True,timeout=120,env=env);(O/(n+'.stdout')).write_bytes(r.stdout);(O/(n+'.stderr')).write_bytes(r.stderr);(O/(n+'.json')).write_text(json.dumps(dict(arguments=args,exit=r.returncode,symbolization_disabled=True),indent=2)+'\n');assert not r.returncode,r.stderr.decode(errors='replace')[-3500:];return r.stdout.decode()
 run('compile',['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-pthread','-g','-fsanitize='+a.sanitizer,'-fcheck-new',str(f),'-o',str(O/'check')]);stdout=run('run',[str(O/'check')]);pin=lambda p:dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
 (O/'result.json').write_text(json.dumps(dict(passed=True,kind=a.kind,sanitizer=a.sanitizer,actual_sources=[pin(p) for p in actual],test_tool=pin(Path(__file__).resolve()),stdout=stdout,scope=scope,hardware_qualified=False,phone_access=False,host_failed_fixture_cleanup_not_device_cleanup=True),indent=2)+'\n');print(stdout.strip())

if __name__=='__main__':main()

#!/usr/bin/env python3
"""Compile actual shared-member retirement and independent physical paths;platform/logical close/MMIO boundaries explicit."""
from pathlib import Path
import argparse,ast,hashlib,json,os,subprocess

def extract(t,start):
    a=t.index(start);b=t.index('{',a)+1;d=1
    while d:d+=(t[b]=='{')-(t[b]=='}');b+=1
    return t[a:b]

def main():
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--parent-source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sanitizer',choices=['address,undefined','thread'],default='address,undefined');a=p.parse_args();S=a.source_root.resolve();PS=a.parent_source.resolve();O=a.out.resolve();O.mkdir()
    texts={n:(S/n).read_text() for n in ['ZornGen7PhysicalOob26.h','ZornGen7AppExecution26.h','ZornGen7DarwinBoardOwner.cpp','ZornGen7HostRing26.cpp','ZornGen7DirectHfi26.cpp']};board=texts['ZornGen7DarwinBoardOwner.cpp'];ring=texts['ZornGen7HostRing26.cpp'];hfi=texts['ZornGen7DirectHfi26.cpp']
    previous=extract((PS/'ZornGen7DarwinBoardOwner.cpp').read_text(),'    bool nativeApplicationWindowHeld(')
    expected=previous.replace('bool nativeApplicationWindowHeld(IOUserClient &client,task_t task,unsigned phase,ZornGen7AppOperation26 operation)','bool nativePhysicalResourcesHeld()').replace('direct_app_publish_attempted && applicationSessionHeld(client,task) && !direct_client_attempted &&','direct_app_publish_attempted && !direct_client_attempted &&').replace('host_ring && host_ring->nativeApplicationBinding(client,task,phase,operation) &&','host_ring &&')
    if '    bool nativePhysicalResourcesHeld(' in (PS/'ZornGen7DarwinBoardOwner.cpp').read_text():
        expected=extract((PS/'ZornGen7DarwinBoardOwner.cpp').read_text(),'    bool nativePhysicalResourcesHeld(')
    assert extract(board,'    bool nativePhysicalResourcesHeld(')==expected
    logical=previous.replace('direct_app_publish_attempted && applicationSessionHeld(client,task) && !direct_client_attempted &&','direct_app_publish_attempted && applicationSessionHeld(client,task) && !direct_client_attempted &&\n            (phase==1 || (direct_physical_held && direct_physical_ring==host_ring)) &&')
    if '(phase==1 || (direct_physical_held && direct_physical_ring==host_ring))' in previous:logical=previous
    assert extract(board,'    bool nativeApplicationWindowHeld(')==logical
    for signature in ['    static bool request(','    static bool clear(']:
        assert extract(texts['ZornGen7PhysicalOob26.h'],signature)==extract((PS/'ZornGen7PhysicalOob26.h').read_text(),signature)
    callbacks='\n'.join(extract(board,'        applicationAuthority.'+n+'=[]')+';' for n in ['physicalAcquire','physicalCheck','physicalContextCheck','physicalRelease'])
    physical_names=['ZornGen7PhysicalOob26::Lease *ZornGen7HostRing26::physicalOobRecordForTransport','bool ZornGen7HostRing26::nativePhysicalBinding','IOReturn ZornGen7HostRing26::acquirePhysicalAuthority','bool ZornGen7HostRing26::physicalOobPermission','bool ZornGen7HostRing26::physicalOobReleaseReady','IOReturn ZornGen7HostRing26::releasePhysicalAuthority','IOReturn ZornGen7HostRing26::closeApplicationExecution','IOReturn ZornGen7HostRing26::checkApplicationExecution','bool ZornGen7HostRing26::applicationOobPermissionForTransport','IOReturn ZornGen7HostRing26::acquireApplicationOob','IOReturn ZornGen7HostRing26::releaseApplicationOob']
    actual_ring='\n'.join(extract(ring,n) for n in physical_names)
    actual_hfi='\n'.join(extract(hfi,n) for n in ['IOReturn ZornGen7DirectHfi26::acquirePhysicalOob','bool ZornGen7DirectHfi26::physicalOobHeld','IOReturn ZornGen7DirectHfi26::releasePhysicalOob'])
    assert 'IOUserClient' not in actual_hfi and 'execution.' not in actual_hfi and 'activeApp' not in actual_hfi
    assert 'client_' not in actual_ring[:actual_ring.index('IOReturn ZornGen7HostRing26::closeApplicationExecution')]
    close=extract(ring,'IOReturn ZornGen7HostRing26::closeApplicationExecution')
    assert close.index('p->closeAcquiredSession(client)')<close.index('raw=releasePhysicalAuthority()')<close.index('s.physicalOob.retire(')
    assert 'checkApplicationExecution(client,execution,ZornGen7AppOperation26::OobAcquire)' in extract(ring,'IOReturn ZornGen7HostRing26::acquireApplicationOob')
    assert ring.index('authorityOwner.retain();s.physicalAuthorityOwner=')<ring.index('const auto raw=ZornGen7AppIoService26::createAndPublish')
    # Reuse only the existing,explicit host primitive/MMIO fixtures. The actual
    # new Board callbacks,Ring methods and DirectHfi methods are not rewritten.
    fixture_tool=Path(__file__).with_name('check-ios26-physical-oob.py');tree=ast.parse(fixture_tool.read_text());prefix=next(ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='prefix' for x in n.targets))
    header='\n'.join(x for x in texts['ZornGen7PhysicalOob26.h'].splitlines() if not x.startswith('#include') and x!='#pragma once');prefix=prefix.replace('ACTUAL_HEADER',header)
    prefix=prefix.replace('using IOReturn=int;','''using IOReturn=int;using task_t=void*;using thread_t=void*;constexpr thread_t THREAD_NULL=nullptr;struct IOUserClient{};struct IOService{};struct IOMemoryDescriptor{};
static thread_t current_thread(){static thread_local int id;return &id;}
''')
    prefix=prefix.replace('static bool normal(){return normalContext;}','static bool normal(){return normalContext&&interrupts;}')
    prefix=prefix.replace('struct Lock{std::mutex mutex;bool held=false;};','struct Lock{std::mutex mutex;std::atomic<bool>held{false};std::atomic<thread_t>owner{THREAD_NULL};};')
    prefix=prefix.replace('p->held=true;}','p->held=true;p->owner=current_thread();}').replace('p->held=false;p->mutex.unlock();','p->owner=THREAD_NULL;p->held=false;p->mutex.unlock();')
    prefix=prefix.replace('return p&&p->held;','return p&&p->owner.load()==current_thread();')
    prefix=prefix.replace('struct Loop{','static void IORecursiveLockLock(Lock*p){IOLockLock(p);}static void IORecursiveLockUnlock(Lock*p){IOLockUnlock(p);}\nstruct Loop{')
    prefix=prefix.replace(' int calls=0,failAt=0;',' bool claims=true;bool providerClaimsHeld(){return claims;}\n int calls=0,failAt=0;')
    prefix=prefix.replace(' ZornGen7HostRing26 *ring_=nullptr;',''' ZornGen7HostRing26 *ring_=nullptr;
public:
 task_t task_=reinterpret_cast<void*>(2);int closeRaw=0;unsigned closeCalled=0;void*closeCookie=nullptr;void(*closeHook)(void*)=nullptr;
 IOReturn closeAcquiredSession(IOUserClient&){++closeCalled;if(!closeRaw){if(closeHook)closeHook(closeCookie);release();}return closeRaw;}
''')
    prefix=prefix.replace('ZornGen7AppExecution26*activeApp=nullptr','ZornGen7HostRing26*activePhysical=nullptr')
    prefix=prefix.replace(' IOReturn acquireApplicationOob(ZornGen7HostRing26&,ZornGen7AppExecution26&);\n bool applicationOobHeld(const ZornGen7HostRing26&,const ZornGen7AppExecution26&)const;\n IOReturn releaseApplicationOob(ZornGen7HostRing26&,ZornGen7AppExecution26&);',' IOReturn acquirePhysicalOob(ZornGen7HostRing26&);\n bool physicalOobHeld(const ZornGen7HostRing26&)const;\n IOReturn releasePhysicalOob(ZornGen7HostRing26&);')
    old=extract(prefix,'class ZornGen7HostRing26 {')+';'
    authority=extract(texts['ZornGen7AppExecution26.h'],'struct ZornGen7AppAuthority26 {')+';'
    replacement=r'''
using ZornGen7RegisterMaps26=Maps;
enum class ZornGen7AppOperation26:unsigned {PrepareTables,Map,Submit,Wait,CpuView,Close,OobAcquire,OobRelease,Timestamp};
ACTUAL_AUTHORITY
class ZornGen7HostRing26:public OSObject {
public:
 ZornGen7PhysicalOob26 physical;ZornGen7AppExecution26 app;ZornGen7DirectHfi26 hfi;Maps maps;std::mutex issuer;
 struct Queue {bool poison=false;unsigned count=0;unsigned completed=1;unsigned outstanding()const{return count;}bool poisoned()const{return poison;}unsigned completedFence()const{return completed;}};
 struct Storage {
  ZornGen7PhysicalOob26 &physicalOob;OSObject &hfiOwner;Maps &maps;std::mutex&issuer;Lock actualGate;Lock&gate=actualGate;thread_t issuerThread=THREAD_NULL;
  OSObject *physicalAuthorityOwner=nullptr;ZornGen7AppAuthority26 physicalAuthority;
  bool physicalAuthorityHeld=false,physicalAuthorityPending=false,physicalAuthorityReleasing=false;unsigned physicalAuthorityPhase=0;thread_t physicalAuthorityThread=THREAD_NULL;
  void*hfi=nullptr;bool applicationIoPublishAttempted=true;void*applicationIoService=reinterpret_cast<void*>(1);bool kernelIoPublishAttempted=false;void*kernelIoConnection=nullptr;
  bool kernelIoActive=false,kernelTaskActive=false;thread_t kernelTaskThread=THREAD_NULL;
  bool runtimeReady=true,bootstrapComplete=true,kernelTaskComplete=true;int kernelTaskRaw=0;
  bool imageVerified=true,imageUnmapped=true,taskReleaseAllowed=true;unsigned imageFence=1;
  struct Image{bool quarantine=false,refs=false;bool quarantined()const{return quarantine;}bool deviceReferences()const{return refs;}}imageMemory;
  bool nativeTableLease=false;unsigned nativeTableAcquires=2,nativeTableReleases=2;bool nativeAdopted=true;Queue native,runtimeSubmit;
  struct Vm{bool poison=false,pending=false;bool poisoned()const{return poison;}bool hasPendingSubmissionResources()const{return pending;}}runtimeVm;
  bool appOobTransition=false,appOobActive=false;thread_t appOobThread=THREAD_NULL,appReleaseIdleThread=THREAD_NULL;
  bool appOperationPending=false,appExecutionPending=false,processClients=false,processSelected=false,nativeProcessTableLease=false;
  unsigned nativeProcessTableAcquires=0,nativeProcessTableReleases=0;struct{unsigned rptr=0,wptr=0;}ring;
  ZornGen7AppExecution26*appExecution=nullptr;uint32_t stopped=0;struct Irq{unsigned stopped=0;void stopAndMask(){++stopped;}}irq;
  void lockIssuer(){issuer.lock();assert(!__atomic_load_n(&issuerThread,__ATOMIC_ACQUIRE));__atomic_store_n(&issuerThread,current_thread(),__ATOMIC_RELEASE);}
  void unlockIssuer(){assert(issuerHeld());__atomic_store_n(&issuerThread,THREAD_NULL,__ATOMIC_RELEASE);issuer.unlock();}
  bool issuerHeld()const{return __atomic_load_n(&issuerThread,__ATOMIC_ACQUIRE)==current_thread();}
  void setAppAuthorityCall(IOUserClient&,task_t,unsigned phase,ZornGen7AppOperation26){assert(issuerHeld()&&phase==3);}
  void clearAppAuthorityCall(){assert(issuerHeld());}
 }s{physical,hfi,maps,issuer};Storage*storage_=&s;
 bool health=true;bool bootstrapHealthy()const{return health&&!s.stopped&&hfi.health;}
 ZornGen7HostRing26(){app.ring_=this;hfi.s.maps=&maps;hfi.s.kernelOob.owner=this;hfi.s.hostStartup=&s.gate;}
 IOReturn reserve(){return physical.reserve(hfi,maps,app.oob_);}
 ZornGen7PhysicalOob26::Lease *physicalOobRecordForTransport(const OSObject&)const;
 bool nativePhysicalBinding(unsigned,uint64_t,bool=false)const;
 IOReturn acquirePhysicalAuthority();bool physicalOobPermission(const OSObject&,bool);
 bool physicalOobReleaseReady(const OSObject&)const;IOReturn releasePhysicalAuthority();
 IOReturn closeApplicationExecution(IOUserClient&,ZornGen7AppExecution26*&);
 bool retire(){auto*p=physical.retire(app.oob_);if(!p)return false;ZornGen7PhysicalOob26::disposeRetired(*p);return true;}
 bool leasePresent(){return physical.forTransport(hfi,maps)!=nullptr;}
 unsigned flags(){auto&r=*app.oob_;return r.attempted|r.requestReturned<<1|r.ackObserved<<2|r.ackCleared<<3|r.gxOn<<4|r.releaseAttempted<<5|r.releaseWriteReturned<<6;}
 uint64_t generation(){return app.oob_->generation;}

 void transition(bool release){s.appOobTransition=true;s.appOobThread=current_thread();if(release)s.appReleaseIdleThread=current_thread();}
 void transitioned(bool active){s.appOobTransition=false;s.appOobThread=THREAD_NULL;s.appReleaseIdleThread=THREAD_NULL;s.appOobActive=active;}
 // CPU host fixture cleanup only;never exported into the driver or a device
 // recovery procedure. Failed physical state has no cleanup API in target.
 ~ZornGen7HostRing26(){if(app.oob_){auto*p=app.oob_;p->transport->release();p->registerMaps->release();dispose(p);}if(hfi.s.activePhysical)hfi.s.activePhysical->release();while(app.refs>1)app.release();assert(refs==1&&hfi.refs==1&&maps.refs==1);}
};
class ZornGen7DarwinBoardOwner:public OSObject {
public:
 struct Storage {
  struct{Lock*startup=nullptr;}gates;
  ZornGen7HostRing26*host_ring=nullptr,*direct_physical_ring=nullptr;Maps*native_cx_maps=nullptr;ZornGen7DirectHfi26*direct_hfi=nullptr;
  uint64_t direct_physical_generation=0;bool direct_physical_attempted=false,direct_physical_held=false;
  void*direct_app_sessions=nullptr,*direct_app_active=nullptr;unsigned direct_app_acquires=0,direct_app_releases=0,direct_oob_epoch=6;
  bool resources=true;unsigned resourceCalls=0,refuseAt=0;
  bool nativePhysicalResourcesHeld(){assert(IORecursiveLockHaveLock(gates.startup));++resourceCalls;return resources&&resourceCalls!=refuseAt&&direct_oob_epoch==6;}
 }s;Storage*storage_=&s;
};
static ZornGen7AppAuthority26 boardCallbacks(ZornGen7DarwinBoardOwner &board){
 ZornGen7AppAuthority26 applicationAuthority;applicationAuthority.cookie=&board;
 ACTUAL_CALLBACKS
 return applicationAuthority;
}
struct Fixture {
 ZornGen7HostRing26 ring;ZornGen7DarwinBoardOwner board;
 Fixture(){board.s.gates.startup=&ring.s.gate;board.s.host_ring=&ring;board.s.native_cx_maps=&ring.maps;board.s.direct_hfi=&ring.hfi;ring.s.physicalAuthorityOwner=&board;board.retain();ring.s.physicalAuthority=boardCallbacks(board);assert(!ring.reserve());}
 void acquire(){assert(!ring.acquirePhysicalAuthority()&&board.s.direct_physical_held);ring.transition(false);assert(!ring.hfi.acquirePhysicalOob(ring));ring.transitioned(true);}
 void clear(){ring.transition(true);assert(!ring.hfi.releasePhysicalOob(ring));ring.transitioned(false);}
 ~Fixture(){board.release();}
};
'''.replace('ACTUAL_AUTHORITY',authority).replace('ACTUAL_CALLBACKS',callbacks)
    prefix=prefix.replace(old,replacement).replace('ACTUAL_METHODS',actual_hfi+'\n'+actual_ring)

    # Extend only host data/primitive fixtures for the current actual close API.

    # The completed-context implementation is compiled by the separate actual
    # handover test. This fixture rejects any accidental invocation here.
    prefix=prefix.replace(' IOReturn closeApplicationExecution(IOUserClient&,ZornGen7AppExecution26*&);', ' bool contextWindow=false;bool nativePhysicalContextBinding(uint64_t generation)const{auto*p=physical.forTransport(hfi,maps);return contextWindow&&p&&p->generation==generation&&!s.issuerHeld()&&IORecursiveLockHaveLock(&s.gate);}\n IOReturn restoreCompletedApplicationContext(){return kIOReturnNotReady;}\n IOReturn closeApplicationExecution(IOUserClient&,ZornGen7AppExecution26*&);',1)
    prefix=prefix.replace('#include <new>','#include <new>\n#define OSDynamicCast(T,P) static_cast<T*>(P)')

    prefix=prefix.replace('class ZornGen7AppExecution26:public OSObject {', 'enum class ZornGen7AppOperation26:unsigned;\nclass ZornGen7AppExecution26:public OSObject {')
    prefix=prefix.replace(' task_t task_=', ' IOReturn checkRaw=0;unsigned checkCalled=0;IOReturn checkCurrent(IOUserClient&,ZornGen7AppOperation26){++checkCalled;return checkRaw;}\n task_t task_=',1)
    idleFixture=r"""
struct hhr_io{void*cookie=nullptr;int(*guard)(void*)=nullptr;int(*read)(void*,uint32_t,uint32_t*)=nullptr;int(*delay)(void*,unsigned)=nullptr;};
static bool idleFailure=false;static unsigned idleCalls=0;
template<class R>static int hhr_idle(const hhr_io*io,R*){++idleCalls;if(idleFailure)return 1;uint32_t word=0;return io->guard(io->cookie)||io->read(io->cookie,0,&word);}
struct HwschedFixture{IOReturn acquireApplicationOob(ZornGen7HostRing26&,ZornGen7AppExecution26&){return kIOReturnNotReady;}IOReturn releaseApplicationOob(ZornGen7HostRing26&,ZornGen7AppExecution26&){return kIOReturnNotReady;}};
"""
    prefix=prefix.replace('class ZornGen7HostRing26:public OSObject {',idleFixture+'\nclass ZornGen7HostRing26:public OSObject {',1)
    prefix=prefix.replace('void*hfi=nullptr;', 'HwschedFixture*hfi=nullptr;')
    prefix=prefix.replace('assert(issuerHeld()&&phase==3);', 'assert(issuerHeld()&&(phase==2||phase==3));')
    prefix=prefix.replace(' IOReturn closeApplicationExecution(IOUserClient&,ZornGen7AppExecution26*&);',r"""
 IOReturn closeApplicationExecution(IOUserClient&,ZornGen7AppExecution26*&);
 IOReturn checkApplicationExecution(IOUserClient&,ZornGen7AppExecution26&,ZornGen7AppOperation26);
 bool applicationOobPermissionForTransport(const OSObject&,ZornGen7AppExecution26&,bool);
 IOReturn acquireApplicationOob(IOUserClient&,ZornGen7AppExecution26&);
 IOReturn releaseApplicationOob(IOUserClient&,ZornGen7AppExecution26&);
 static int guard(void*p){return static_cast<ZornGen7HostRing26*>(p)->bootstrapHealthy()?0:1;}
 static int read(void*p,uint32_t,uint32_t*out){*out=0;return guard(p);}
 static int delay(void*,unsigned){return 0;}
""")
    prefix=prefix.replace('class ZornGen7AppExecution26:public OSObject {','class ZornGen7AppExecution26:public OSObject {public:')
    prefix=prefix.replace(' task_t task_=reinterpret_cast<void*>(2);', ' IOUserClient*client_=nullptr;Maps*maps_=nullptr;ZornGen7AppExecution26*ringNext_=nullptr;bool oobMemberHeld_=false,oobMemberReleased_=true;task_t task_=reinterpret_cast<void*>(2);')
    prefix=prefix.replace('bool appOperationPending=false,appExecutionPending=false,processClients=false,processSelected=false,nativeProcessTableLease=false;', 'bool appOperationPending=false,appExecutionPending=false,processSelected=false,nativeProcessTableLease=false;struct Process{IOUserClient*clientOwner_=nullptr;Process*ringNext_=nullptr;struct{bool detached=true,poisoned=false;}state_;Vm vm_;bool clientOpen_=true,clientClosed_=false;struct Client{Queue submit;}client;Client*clientState_=&client;}blockedProcess;Process*processClients=nullptr;thread_t processTransitionThread=THREAD_NULL;')
    prefix=prefix.replace('ZornGen7AppExecution26*appExecution=nullptr;', 'ZornGen7AppExecution26*appExecutions=nullptr,*appExecution=nullptr;Lock appSerialLock;Lock*appSerial=&appSerialLock;thread_t appSerialThread=THREAD_NULL;')
    helpers='\n'.join(extract(ring,n) for n in ['    bool appSerialHeld() const','    ZornGen7AppExecution26 *applicationMember(','    bool ownsExecution(','    bool applicationQuiescent() const','    struct AppSerialScope {'])+';'
    prefix=prefix.replace('  void lockIssuer(){', helpers+'\n  void lockIssuer(){',1)
    prefix=prefix.replace('app.ring_=this;hfi.s.maps=', 'app.ring_=this;app.maps_=&maps;hfi.s.maps=')
    prefix=prefix.replace('~ZornGen7HostRing26(){if(app.oob_){auto*p=app.oob_;','~ZornGen7HostRing26(){if(auto*p=physical.forTransport(hfi,maps)){')
    prefix=prefix.replace(' bool leasePresent(){', ' void closeMember(IOUserClient &client){app.client_=&client;app.ringNext_=nullptr;s.appExecutions=&app;}\n bool leasePresent(){')
    tests=r'''
int main(){unsigned controls=0;
 {Fixture f;assert(f.ring.hfi.refs==2&&f.ring.maps.refs==2);f.acquire();assert(f.ring.refs==2&&f.ring.app.refs==1&&f.ring.flags()==31);f.clear();assert(f.ring.refs==1&&f.ring.flags()==127);assert(!f.ring.releasePhysicalAuthority());assert(f.board.s.direct_oob_epoch==4&&!f.board.s.direct_physical_held);assert(f.ring.retire());++controls;}
 for(unsigned mode=0;mode<7;++mode){Fixture f;if(mode==0)f.board.s.resources=false;if(mode==1)f.board.s.native_cx_maps=nullptr;if(mode==2)f.board.s.direct_hfi=nullptr;if(mode==3)f.board.s.host_ring=nullptr;if(mode==4)f.board.s.direct_physical_generation=99;if(mode==5)f.ring.s.physicalAuthorityOwner=nullptr;if(mode==6)f.ring.s.physicalAuthority.physicalAcquire=nullptr;
  assert(f.ring.acquirePhysicalAuthority()&&f.ring.leasePresent()&&!f.ring.s.physicalAuthorityHeld&&f.ring.maps.calls==0);++controls;}
 for(unsigned mode=0;mode<12;++mode){Fixture f;auto&s=f.ring.s;if(mode==0)s.runtimeReady=false;if(mode==1)s.nativeTableAcquires=1;if(mode==2)s.nativeAdopted=false;if(mode==3)s.imageMemory.refs=true;if(mode==4)s.processClients=true;if(mode==5)s.processSelected=true;if(mode==6)s.native.count=1;if(mode==7)s.runtimeSubmit.count=1;if(mode==8)s.maps.claims=false;if(mode==9)s.appExecutionPending=true;if(mode==10)s.kernelIoPublishAttempted=true;if(mode==11)s.nativeProcessTableLease=true;
  assert(f.ring.acquirePhysicalAuthority()&&f.ring.leasePresent()&&!f.ring.s.physicalAuthorityHeld);++controls;}
 for(unsigned mode=0;mode<4;++mode){Fixture f;assert(!f.ring.acquirePhysicalAuthority());if(mode==0)f.ring.s.appOobTransition=false;if(mode==1){f.ring.transition(false);f.ring.s.appOobThread=reinterpret_cast<void*>(1);}if(mode==2){f.ring.transition(false);f.ring.s.appOobActive=true;}if(mode==3){f.ring.transition(false);f.ring.s.appOperationPending=true;}
  assert(f.ring.hfi.acquirePhysicalOob(f.ring)&&f.ring.maps.calls==0&&f.ring.leasePresent());++controls;}
 for(unsigned access=1;access<=7;++access){Fixture f;assert(!f.ring.acquirePhysicalAuthority());f.ring.transition(false);f.ring.maps.failAt=access;assert(f.ring.hfi.acquirePhysicalOob(f.ring)&&f.ring.refs==2&&f.ring.app.refs==1&&f.ring.leasePresent());assert(!f.ring.retire());++controls;}
 for(unsigned at=3;at<=9;++at){Fixture f;assert(!f.ring.acquirePhysicalAuthority());f.board.s.refuseAt=at;f.ring.transition(false);assert(f.ring.hfi.acquirePhysicalOob(f.ring)&&unsigned(f.ring.maps.calls)==at-3&&f.ring.leasePresent()&&f.ring.refs==2);++controls;}
 for(unsigned mode=0;mode<4;++mode){Fixture f;assert(!f.ring.acquirePhysicalAuthority());f.ring.transition(false);if(mode==0)f.ring.maps.staleAck=true;if(mode==1)f.ring.maps.staleHost=true;if(mode==2)f.ring.maps.noAck=true;if(mode==3)f.ring.maps.gxOff=true;assert(f.ring.hfi.acquirePhysicalOob(f.ring)&&f.ring.leasePresent());++controls;}
 for(unsigned mode=0;mode<5;++mode){Fixture f;f.acquire();f.ring.transition(true);const int before=f.ring.maps.calls;if(mode==0)f.ring.s.processClients=true;if(mode==1)f.ring.s.native.count=1;if(mode==2)f.ring.s.ring.wptr=1;if(mode==3)f.ring.maps.failAt=before+1;if(mode==4)f.board.s.resources=false;
  assert(f.ring.hfi.releasePhysicalOob(f.ring)&&f.ring.leasePresent()&&f.ring.refs==2&&f.board.s.direct_physical_held);++controls;}
 for(unsigned mode=0;mode<4;++mode){Fixture f;f.acquire();f.clear();if(mode==0)f.board.s.direct_app_sessions=reinterpret_cast<void*>(1);if(mode==1)f.ring.s.processClients=true;if(mode==2)f.board.s.direct_physical_generation++;if(mode==3)f.board.s.resources=false;
  assert(f.ring.releasePhysicalAuthority()&&f.ring.leasePresent()&&f.board.s.direct_physical_held&&f.ring.hfi.refs==2&&f.ring.maps.refs==2);++controls;}
 {Fixture f;f.acquire();f.clear();f.ring.s.appExecution=&f.ring.app;f.ring.app.refs=4;f.board.s.direct_app_sessions=reinterpret_cast<void*>(1);f.ring.app.closeCookie=&f.board;
  f.ring.app.closeHook=[](void*p){auto&b=*static_cast<ZornGen7DarwinBoardOwner*>(p);assert(b.s.direct_physical_held);b.s.direct_app_sessions=nullptr;};IOUserClient client;auto*p=&f.ring.app;
  assert(!f.ring.closeApplicationExecution(client,p)&&!p&&!f.ring.leasePresent()&&!f.board.s.direct_physical_held&&f.ring.app.refs==1&&f.ring.hfi.refs==1&&f.ring.maps.refs==1);
  assert(!f.ring.reserve());f.board.s.direct_oob_epoch=6;assert(f.ring.generation()==2);f.acquire();f.clear();assert(!f.ring.releasePhysicalAuthority());assert(f.ring.retire());++controls;}
 {Fixture f;f.acquire();f.clear();f.ring.s.appExecution=&f.ring.app;f.ring.app.refs=4;f.ring.app.closeRaw=7;IOUserClient client;auto*p=&f.ring.app;assert(f.ring.closeApplicationExecution(client,p)==7&&p&&f.board.s.direct_physical_held&&f.ring.leasePresent()&&f.ring.s.stopped);++controls;}
 {Fixture f;f.acquire();f.clear();f.ring.s.appExecution=&f.ring.app;f.ring.app.refs=4;f.board.s.direct_app_sessions=reinterpret_cast<void*>(1);IOUserClient client;auto*p=&f.ring.app;assert(f.ring.closeApplicationExecution(client,p)&&p&&f.ring.leasePresent()&&f.board.s.direct_physical_held&&f.ring.app.closeCalled==1);++controls;}
 {Fixture f;std::atomic<unsigned>winners{0};std::vector<std::thread>threads;for(unsigned i=0;i<12;++i)threads.emplace_back([&]{if(!f.ring.acquirePhysicalAuthority())++winners;});for(auto&t:threads)t.join();assert(winners==1&&f.board.s.direct_physical_held&&f.ring.maps.calls==0);++controls;}
 {Fixture f;assert(!f.ring.acquirePhysicalAuthority());f.ring.transition(false);bool accepted=true;std::thread outsider([&]{accepted=f.ring.physicalOobPermission(f.ring.hfi,false);});outsider.join();assert(!accepted&&f.ring.maps.calls==0&&f.ring.leasePresent()&&f.board.s.direct_physical_held);++controls;}
 assert(allocations==frees);std::printf("PASS255 actual Board/Ring/DirectHfi physical-authority controls=%u;fixture_allocations=%u\n",controls,allocations);
}
'''

    tests=tests.replace('s.processClients=true','s.processClients=&s.blockedProcess')
    tests=tests.replace('f.ring.s.processClients=&s.blockedProcess','f.ring.s.processClients=&f.ring.s.blockedProcess')
    tests=tests.replace('IOUserClient client;auto*p=&f.ring.app;', 'IOUserClient client;f.ring.closeMember(client);auto*p=&f.ring.app;')
    # Physical cleanup depends on the actual final Root member,not which
    # client originally caused its allocation. Other VM is a declared fixture.
    additional=r"""
 {Fixture f;ZornGen7AppExecution26 second;IOUserClient a,b;
  f.ring.closeMember(a);f.ring.app.oobMemberHeld_=false;f.ring.app.oobMemberReleased_=false;f.ring.app.refs=4;
  assert(!f.ring.acquirePhysicalAuthority());assert(!f.ring.acquireApplicationOob(a,f.ring.app));
  second.ring_=&f.ring;second.maps_=&f.ring.maps;second.client_=&b;second.oob_=f.ring.app.oob_;second.refs=4;second.oobMemberHeld_=false;second.oobMemberReleased_=false;second.ringNext_=&f.ring.app;f.ring.s.appExecutions=&second;
  f.ring.s.blockedProcess.clientOwner_=&a;f.ring.s.processClients=&f.ring.s.blockedProcess;
  const auto generation=f.ring.generation();const auto stores=f.ring.maps.writes.size();assert(!f.ring.acquireApplicationOob(b,second)&&f.ring.maps.writes.size()==stores&&second.oobMemberHeld_);++controls;
  // Only the actual per-client VM retirement is a declared fixture boundary.
  f.ring.s.blockedProcess.clientOwner_=&b;
  assert(!f.ring.releaseApplicationOob(a,f.ring.app)&&!f.ring.app.oobMemberHeld_&&f.ring.app.oobMemberReleased_&&f.ring.s.appOobActive&&f.ring.maps.writes.size()==stores);auto*p=&f.ring.app;
  assert(!f.ring.closeApplicationExecution(a,p)&&!p&&f.ring.leasePresent()&&f.board.s.direct_physical_held&&f.ring.s.appExecutions==&second&&!second.ringNext_&&f.ring.hfi.s.activePhysical==&f.ring&&f.ring.maps.writes.size()==stores&&f.ring.app.refs==1&&second.refs==4);++controls;
  f.ring.s.processClients=nullptr;assert(!f.ring.releaseApplicationOob(b,second)&&!f.ring.s.appOobActive&&second.oobMemberReleased_&&f.ring.maps.writes.size()==stores+1);p=&second;
  assert(!f.ring.closeApplicationExecution(b,p)&&!p&&!f.ring.leasePresent()&&!f.board.s.direct_physical_held&&second.refs==1&&f.ring.maps.refs==1&&f.ring.hfi.refs==1&&generation==1);++controls;
 }
 {Fixture f;IOUserClient client;f.ring.closeMember(client);f.ring.app.oobMemberHeld_=false;f.ring.app.oobMemberReleased_=false;assert(!f.ring.acquirePhysicalAuthority()&&!f.ring.acquireApplicationOob(client,f.ring.app));const auto stores=f.ring.maps.writes.size();idleFailure=true;assert(f.ring.releaseApplicationOob(client,f.ring.app)&&f.ring.app.oobMemberHeld_&&!f.ring.app.oobMemberReleased_&&f.ring.s.appOobActive&&f.ring.leasePresent()&&f.ring.maps.writes.size()==stores&&f.ring.s.stopped);idleFailure=false;++controls;}

 {Fixture f;f.acquire();f.clear();f.ring.s.appExecutions=&f.ring.app;assert(f.ring.releasePhysicalAuthority()&&f.ring.leasePresent()&&f.board.s.direct_physical_held);++controls;}
"""
    tests=tests.replace(' assert(allocations==frees);', additional+'\n assert(allocations==frees);')

    contextChecks=r"""
 {Fixture f;f.acquire();f.ring.contextWindow=true;const auto before=f.ring.maps.calls;auto&auth=f.ring.s.physicalAuthority;assert(auth.physicalContextCheck&&!auth.physicalContextCheck(auth.cookie,f.ring,f.ring.generation())&&f.ring.maps.calls==before&&f.ring.leasePresent());++controls;f.clear();assert(!f.ring.releasePhysicalAuthority()&&f.ring.retire());}
 for(unsigned mode=0;mode<8;++mode){Fixture f;f.acquire();f.ring.contextWindow=true;auto&auth=f.ring.s.physicalAuthority;auto generation=f.ring.generation();if(mode==0)f.ring.contextWindow=false;if(mode==1)f.board.s.direct_physical_held=false;if(mode==2)f.board.s.direct_physical_ring=nullptr;if(mode==3)generation++;if(mode==4)f.board.s.resources=false;if(mode==5)f.board.storage_=nullptr;if(mode==6)generation=0;if(mode==7)normalContext=false;const auto before=f.ring.maps.calls;assert(auth.physicalContextCheck(auth.cookie,f.ring,generation)&&f.ring.maps.calls==before&&f.ring.leasePresent());normalContext=true;++controls;}
 {Fixture f;f.acquire();f.ring.contextWindow=true;IOLockLock(&f.ring.s.gate);auto&auth=f.ring.s.physicalAuthority;assert(auth.physicalContextCheck(auth.cookie,f.ring,f.ring.generation()));IOLockUnlock(&f.ring.s.gate);++controls;}
"""
    tests=tests.replace(' assert(allocations==frees);',contextChecks+'\n assert(allocations==frees);')
    tests=tests.replace('PASS255 actual Board/Ring/DirectHfi', 'PASS258 actual physical-context callback and shared close/Board/Ring/DirectHfi')
    source=O/'hostcheck.cpp';source.write_text(prefix+tests);args=['/usr/bin/clang++','-std=c++17','-O1','-g','-fno-omit-frame-pointer','-fsanitize='+a.sanitizer,str(source),'-o',str(O/'hostcheck')];runs=[]
    environment=dict(os.environ);environment.update(TSAN_OPTIONS='symbolize=0',ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0')
    for cmd in [args,[str(O/'hostcheck')]]:
        z=subprocess.run(cmd,capture_output=True,text=True,timeout=120,env=environment);runs.append(dict(arguments=cmd,sanitizer_environment={k:environment[k] for k in ['TSAN_OPTIONS','ASAN_OPTIONS','UBSAN_OPTIONS']},exit=z.returncode,stdout=z.stdout,stderr=z.stderr));(O/'commands.json').write_text(json.dumps(runs,indent=2)+'\n');assert not z.returncode,z.stderr[-6000:]
    pin=lambda p:dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
    result=dict(passed=True,sanitizer=a.sanitizer,actual_sources=[pin(S/n) for n in texts],fixture_tool=pin(fixture_tool),test_tool=pin(Path(__file__)),Board_physical_resources_predicate_preserved_except_logical_identity_split=True,actual_Board_callbacks_Ring_methods_DirectHfi_methods_compiled=True,request_clear_sequence_byte_equal_to254=True,transport_retains_Ring_not_first_application=True,actual_nonlast_close_keeps_physical_lease_and_final_close_releases_once=True,actual_logical_close_before_physical_release_before_lease_retirement=True,completed_context_implementation_tested_separately_not_stub_qualified=True,actual_Board_physicalContextCheck_compiled=True,platform_resources_logical_close_and_MMIO_are_explicit_host_fixtures=True,fixture_cleanup_not_hardware_cleanup=True,phone_access=False,hardware_qualified=False,output=runs[-1]['stdout']);(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result['output'],end='')
if __name__=='__main__':main()

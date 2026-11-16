#!/usr/bin/env python3
"""Compile actual physical-owner header and DirectHfi OOB methods against explicit host MMIO/authority fixtures."""
from pathlib import Path
import argparse,hashlib,json,subprocess

def extract(text,start):
    a=text.index(start);b=text.index('{',a)+1;depth=1
    while depth:
        depth+=(text[b]=='{')-(text[b]=='}');b+=1
    return text[a:b]

def main():
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--parent-source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sanitizer',choices=['address,undefined','thread'],default='address,undefined');a=p.parse_args();S=a.source_root;O=a.out;O.mkdir()
    owner=(S/'ZornGen7PhysicalOob26.h').read_text();direct=(S/'ZornGen7DirectHfi26.cpp').read_text();ring=(S/'ZornGen7HostRing26.cpp').read_text();app=(S/'ZornGen7AppExecution26.cpp').read_text();parent=(a.parent_source/'ZornGen7DirectHfi26.cpp').read_text()
    methods='\n'.join(extract(direct,x) for x in ['IOReturn ZornGen7DirectHfi26::acquireApplicationOob','bool ZornGen7DirectHfi26::applicationOobHeld','IOReturn ZornGen7DirectHfi26::releaseApplicationOob'])
    # The actual permission/map access/poll code is preserved;the physical
    # helper owns the SAME writes,flags and ordering,not a fixture backend.
    old=extract(parent,'IOReturn ZornGen7DirectHfi26::acquireApplicationOob');new=extract(direct,'IOReturn ZornGen7DirectHfi26::acquireApplicationOob')
    poll_start='    auto poll=';assert old[old.index(poll_start):old.index('    if(!poll(',old.index(poll_start))]==new[new.index(poll_start):new.index('    return done(ZornGen7PhysicalOob26::request',new.index(poll_start))]
    assert old[:old.index('    constexpr uint32_t request=')].replace('auto &r=execution.oob_;','auto &r=*execution.oob_;')==new[:new.index(poll_start)]
    body=extract(owner,'    static bool request(')
    expected=old[old.index('    constexpr uint32_t request='):old.index(poll_start)]+old[old.index('    if(!poll(',old.index(poll_start)):old.index('    return done(kIOReturnSuccess);')]
    actual=body[body.index('        constexpr uint32_t request='):body.index('        return true;')]
    normalize=lambda t:''.join(t.split()).replace('returndone(kIOReturnNotReady);','returnfalse;')
    assert normalize(expected)==normalize(actual)
    # Source call graph:live Board check on each access,lease identities,
    # actual create/bind,actual release BEFORE retirement,dispose outside lock.
    assert 'raw=s.physicalOob.reserve(*p,s.hfiOwner,s.maps,p->oob_)' in ring
    permission=extract(ring,'bool ZornGen7HostRing26::applicationOobPermissionForTransport(')
    assert all(x in permission for x in ['physicalOob.owns','oob_->transport!=&hfi','oob_->registerMaps!=&storage_->maps','checkApplicationExecution('])
    close=extract(ring,'IOReturn ZornGen7HostRing26::closeApplicationExecution(')
    assert close.index('p->closeAcquiredSession(client)')<close.index('s.physicalOob.retire(')<close.index('s.unlockIssuer();\n            ZornGen7PhysicalOob26::disposeRetired(')
    assert '(!oob_ || (oob_->attempted && !oob_->releaseWriteReturned))' in app
    assert (S/'ZornGen7DarwinBoardOwner.cpp').read_bytes()==(a.parent_source/'ZornGen7DarwinBoardOwner.cpp').read_bytes()
    prefix=r'''
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <mutex>
#include <thread>
#include <vector>
#include <utility>
#include <new>
using IOReturn=int;
constexpr int kIOReturnSuccess=0,kIOReturnNotReady=1,kIOReturnBadArgument=2,kIOReturnExclusiveAccess=3,kIOReturnNoMemory=4;
struct OSObject{std::atomic<int> refs{1};void retain(){assert(refs.fetch_add(1)>0);}void release(){assert(refs.fetch_sub(1)>1);}};
static bool allocationFails=false;static unsigned allocations=0,frees=0;
template<class T>T *allocate(){if(allocationFails)return nullptr;auto*p=new(std::nothrow)T{};if(p)++allocations;return p;}
template<class T>void dispose(T*p){++frees;delete p;}
#define IONewZero(T,N) allocate<T>()
#define IODelete(P,T,N) dispose<T>(P)
ACTUAL_HEADER
struct Lock{std::mutex mutex;bool held=false;};
static void IOLockLock(Lock*p){p->mutex.lock();assert(!p->held);p->held=true;}
static void IOLockUnlock(Lock*p){assert(p->held);p->held=false;p->mutex.unlock();}
static bool IORecursiveLockHaveLock(Lock*p){return p&&p->held;}
static bool normalContext=true,interrupts=true;
static bool normal(){return normalContext;}static bool ml_get_interrupts_enabled(){return interrupts;}
constexpr uint64_t NSEC_PER_MSEC=1000000;static uint64_t tick=0;
static void clock_interval_to_deadline(unsigned n,uint64_t scale,uint64_t*out){*out=tick+n*scale;}
static void clock_get_uptime(uint64_t*out){tick+=50000000;*out=tick;}
static void delay_for_interval_with_leeway(unsigned a,unsigned b,unsigned c){assert(a==26&&b==74&&c==1000);}
struct Loop{bool on=false,in=false;bool onThread(){return on;}bool inGate(){return in;}};
struct Maps:OSObject {
 int calls=0,failAt=0;bool staleAck=false,staleHost=false,noAck=false,gxOff=false;
 uint32_t ack=0,host=0;std::vector<std::pair<uint32_t,uint32_t>> writes;
 int accessGmuHfiWord(uint32_t at,bool write,uint32_t&v){
  ++calls;if(calls==failAt)return -5;
  if(write){writes.emplace_back(at,v);
   if(at==0x1f994&&v==(1u<<30)){host=v;if(!noAck)ack=1u<<31;}
   else if(at==0x1f991&&v==(1u<<31))ack=0;
   else if(at==0x1f994&&v==(1u<<31))host=0;
   else assert(false);
  }else if(at==0x1f992)v=staleAck?(1u<<31):ack;
  else if(at==0x1f996)v=staleHost?(1u<<30):host;
  else if(at==0x1f8d0)v=gxOff?3:0;
  else assert(false);
  return 0;
 }
};
class ZornGen7AppExecution26:public OSObject {
 friend class ZornGen7DirectHfi26;friend class ZornGen7HostRing26;
 ZornGen7PhysicalOob26::Lease *oob_=nullptr;
 ZornGen7HostRing26 *ring_=nullptr;
};
class ZornGen7DirectHfi26:public OSObject {
public:
 struct Storage {
  Lock actualGate,startup;Lock*gate=&actualGate,*hostStartup=&startup;Loop actualLoop;Loop*loop=&actualLoop;
  Maps *maps=nullptr;ZornGen7AppExecution26*activeApp=nullptr;bool commandBusy=false,pending=false;
  struct Kernel {ZornGen7HostRing26*owner=nullptr;bool attempted=true,requestReturned=true,ackObserved=true,ackCleared=true,gxOn=true,releaseAttempted=true,releaseWriteReturned=true;int raw=0;}kernelOob;
  struct Client{bool attempted=false;}clientOob;
 } s;Storage*storage_=&s;bool health=true,bootstrapReleased=true;unsigned failures=0;
 bool healthy()const{return health;}bool bootstrapOobReleaseReturned()const{return bootstrapReleased;}
 void fail(){++failures;health=false;}
 IOReturn acquireApplicationOob(ZornGen7HostRing26&,ZornGen7AppExecution26&);
 bool applicationOobHeld(const ZornGen7HostRing26&,const ZornGen7AppExecution26&)const;
 IOReturn releaseApplicationOob(ZornGen7HostRing26&,ZornGen7AppExecution26&);
};
class ZornGen7HostRing26 {
public:
 ZornGen7PhysicalOob26 physical;ZornGen7AppExecution26 app,foreign;ZornGen7DirectHfi26 hfi;Maps maps;
 bool permitted=true,idle=true;unsigned permissionCalls=0,revokeAt=0;
 std::mutex issuer;
 ZornGen7HostRing26(){app.ring_=this;foreign.ring_=this;hfi.s.maps=&maps;hfi.s.kernelOob.owner=this;}
 IOReturn reserve(){std::lock_guard<std::mutex>guard(issuer);return physical.reserve(app,hfi,maps,app.oob_);}
 bool applicationOobPermission(const ZornGen7DirectHfi26&transport,ZornGen7AppExecution26&execution,bool){
  assert(!hfi.s.actualGate.held);++permissionCalls;
  return permitted&&permissionCalls!=revokeAt&&physical.owns(execution,execution.oob_)&&execution.oob_->transport==&transport&&execution.oob_->registerMaps==&maps;
 }
 bool applicationOobReleaseReady(const ZornGen7DirectHfi26&,const ZornGen7AppExecution26&)const{return idle;}
 bool retire(){std::unique_lock<std::mutex>guard(issuer);auto*p=physical.retire(app,app.oob_);guard.unlock();if(!p)return false;ZornGen7PhysicalOob26::disposeRetired(*p);return true;}
 bool owns(){return physical.owns(app,app.oob_);}
 bool foreignOwns(){return physical.owns(foreign,app.oob_);}
 bool full(){return app.oob_&&ZornGen7PhysicalOob26::releaseReturned(*app.oob_);}
 unsigned flags(){auto&r=*app.oob_;return r.attempted|r.requestReturned<<1|r.ackObserved<<2|r.ackCleared<<3|r.gxOn<<4|r.releaseAttempted<<5|r.releaseWriteReturned<<6;}
 uint64_t generation(){return app.oob_->generation;}
 void corrupt(unsigned kind){auto&r=*app.oob_;if(kind==0)r.physical=nullptr;if(kind==1)r.member=&foreign;if(kind==2)r.generation=0;if(kind==3)r.generation++;if(kind==4)r.transport=nullptr;if(kind==5)r.registerMaps=nullptr;}
 void maxGeneration(){physical.generation_=UINT64_MAX;}
 // Explicit CPU-fixture teardown after failures. This is NOT a driver API
 // and supplies no DMA stop/recovery or hardware cleanup evidence.
 ~ZornGen7HostRing26(){if(app.oob_){auto*p=app.oob_;if(p->transport)p->transport->release();else hfi.release();if(p->registerMaps)p->registerMaps->release();else maps.release();dispose(p);}
  if(hfi.s.activeApp)hfi.s.activeApp->release();assert(hfi.refs==1&&maps.refs==1&&app.refs==1);
 }
};
ACTUAL_METHODS
'''
    stripped='\n'.join(x for x in owner.splitlines() if not x.startswith('#include') and x!='#pragma once')
    code=prefix.replace('ACTUAL_HEADER',stripped).replace('ACTUAL_METHODS',methods)+r'''
int main(){unsigned controls=0;
 {ZornGen7HostRing26 f;allocationFails=true;assert(f.reserve()==kIOReturnNoMemory&&!f.owns()&&f.hfi.refs==1&&f.maps.refs==1);allocationFails=false;++controls;}
 {ZornGen7HostRing26 f;f.maxGeneration();assert(f.reserve()==kIOReturnExclusiveAccess);++controls;}
 {ZornGen7HostRing26 f;assert(!f.reserve());assert(f.reserve()==kIOReturnBadArgument);assert(f.owns()&&!f.foreignOwns());assert(f.hfi.refs==2&&f.maps.refs==2&&!f.retire());++controls;}
 {ZornGen7HostRing26 f;assert(!f.reserve());assert(!f.hfi.acquireApplicationOob(f,f.app));assert(f.flags()==31&&f.hfi.applicationOobHeld(f,f.app));assert(f.app.refs==2);assert(!f.hfi.releaseApplicationOob(f,f.app));assert(f.flags()==127&&f.full()&&f.app.refs==1);assert(f.retire());assert(f.hfi.refs==1&&f.maps.refs==1);assert(!f.reserve()&&f.generation()==2&&f.flags()==0);assert(!f.hfi.acquireApplicationOob(f,f.app));assert(!f.hfi.releaseApplicationOob(f,f.app));assert(f.retire());
  std::vector<std::pair<uint32_t,uint32_t>> expected{{0x1f994,1u<<30},{0x1f991,1u<<31},{0x1f994,1u<<31},{0x1f994,1u<<30},{0x1f991,1u<<31},{0x1f994,1u<<31}};assert(f.maps.writes==expected);++controls;}
 for(unsigned mode=0;mode<6;++mode){ZornGen7HostRing26 f;assert(!f.reserve());f.corrupt(mode);assert(!f.owns());assert(f.hfi.acquireApplicationOob(f,f.app)==kIOReturnNotReady&&f.maps.calls==0&&!f.retire());++controls;}
 for(int access=1;access<=7;++access){ZornGen7HostRing26 f;assert(!f.reserve());f.maps.failAt=access;assert(f.hfi.acquireApplicationOob(f,f.app)==kIOReturnNotReady);assert(!f.retire()&&f.owns()&&f.app.refs==2&&f.hfi.refs==2&&f.maps.refs==2);assert(!f.hfi.health);++controls;}
 for(unsigned mode=0;mode<4;++mode){ZornGen7HostRing26 f;assert(!f.reserve());f.maps.staleAck=mode==0;f.maps.staleHost=mode==1;f.maps.noAck=mode==2;f.maps.gxOff=mode==3;assert(f.hfi.acquireApplicationOob(f,f.app)==kIOReturnNotReady&&!f.retire());assert(mode>1||f.maps.writes.empty());++controls;}
 // Permission revocation at each original acquire access: no MMIO after
 // that check fails;failed physical attempt/refs stay pinned.
 for(unsigned call=2;call<=8;++call){ZornGen7HostRing26 f;assert(!f.reserve());f.revokeAt=call;assert(f.hfi.acquireApplicationOob(f,f.app)==kIOReturnNotReady);assert(unsigned(f.maps.calls)==call-2&&!f.retire()&&f.owns());++controls;}
 for(unsigned mode=0;mode<5;++mode){ZornGen7HostRing26 f;assert(!f.reserve());assert(!f.hfi.acquireApplicationOob(f,f.app));const int before=f.maps.calls;
  if(mode==0)f.idle=false;if(mode==1)f.permitted=false;if(mode==2)f.revokeAt=f.permissionCalls+2;if(mode==3)f.maps.failAt=before+1;if(mode==4)f.hfi.s.pending=true;
  assert(f.hfi.releaseApplicationOob(f,f.app)==kIOReturnNotReady&&!f.retire()&&f.owns());assert(f.app.refs==2&&f.hfi.refs==2&&f.maps.refs==2);assert(f.maps.calls==before+(mode==3));++controls;}
 for(unsigned mode=0;mode<6;++mode){ZornGen7HostRing26 f;assert(!f.reserve());if(mode==0)normalContext=false;if(mode==1)interrupts=false;if(mode==2)f.hfi.bootstrapReleased=false;if(mode==3)f.hfi.s.actualLoop.on=true;if(mode==4)f.hfi.s.actualLoop.in=true;if(mode==5)f.hfi.s.startup.held=true;
  assert(f.hfi.acquireApplicationOob(f,f.app)==kIOReturnNotReady&&f.maps.calls==0);normalContext=true;interrupts=true;f.hfi.s.startup.held=false;++controls;}
 {ZornGen7HostRing26 f;unsigned winners=0;ZornGen7AppExecution26 contenders[12];std::vector<std::thread> threads;for(unsigned i=0;i<12;++i)threads.emplace_back([&,i]{std::lock_guard<std::mutex>guard(f.issuer);ZornGen7PhysicalOob26::Lease*unused=nullptr;});
  for(auto&t:threads)t.join();(void)winners;}
 assert(allocations==frees);std::printf("PASS actual physical lease and DirectHfi protocol controls=%u fixture_allocations=%u\n",controls,allocations);
}
'''
    # Concurrency goes through the same external issuer ownership required by
    # the real private class;the fixture does not invent internal locking.
    code=code.replace('ZornGen7PhysicalOob26::Lease*unused=nullptr;','if(!f.reserveContender(contenders[i]))++winners;')
    code=code.replace(' bool retire(){',' IOReturn reserveContender(ZornGen7AppExecution26 &member){return physical.reserve(member,hfi,maps,member.oob_);}\n bool retire(){')
    # Distinct members/output slots exercise the physical owner's exclusivity,
    # rather than merely rejecting reuse of an already nonnull output slot.
    code=code.replace('for(auto&t:threads)t.join();(void)winners;','for(auto&t:threads)t.join();assert(winners==1);f.cleanupContenders(contenders,12);++controls;')
    code=code.replace(' bool owns(){',' void cleanupContenders(ZornGen7AppExecution26 *members,unsigned count){assert(!app.oob_);for(unsigned i=0;i<count;++i)if(members[i].oob_){assert(!app.oob_);app.oob_=members[i].oob_;members[i].oob_=nullptr;}}\n bool owns(){')
    # Compile the actual Ring close method too;only its foreign Board/client
    # and queue boundaries are fixtures. This checks ordering and retention
    # across the new physical retirement integration,including contradictions.
    code=code.replace('using IOReturn=int;','using IOReturn=int;using task_t=void*;struct IOUserClient{};enum class ZornGen7AppOperation26 {Close};')
    code=code.replace(' ZornGen7HostRing26 *ring_=nullptr;',''' ZornGen7HostRing26 *ring_=nullptr;
public:
 task_t task_=reinterpret_cast<void*>(2);int closeRaw=0;unsigned closeCalled=0;
 IOReturn closeAcquiredSession(IOUserClient&){++closeCalled;if(!closeRaw)release();return closeRaw;}
''')
    marker=' std::mutex issuer;'
    code=code.replace(marker,marker+r'''
 struct Storage {
  ZornGen7PhysicalOob26 &physicalOob;std::mutex &issuer;bool issuerHeld=false;Lock gate;
  ZornGen7AppExecution26 *appExecution=nullptr;
  bool appExecutionPending=false,appOperationPending=false,appOobTransition=false,appOobActive=false,kernelIoActive=false,processClients=false;
  uint32_t stopped=0;struct Queue{unsigned count=0;bool poison=false;unsigned outstanding(){return count;}bool poisoned(){return poison;}}native,runtimeSubmit;
  struct Irq{unsigned stopped=0;void stopAndMask(){++stopped;}}irq;
  void lockIssuer(){issuer.lock();assert(!issuerHeld);issuerHeld=true;}
  void unlockIssuer(){assert(issuerHeld);issuerHeld=false;issuer.unlock();}
  void setAppAuthorityCall(IOUserClient&,task_t,unsigned phase,ZornGen7AppOperation26){assert(issuerHeld&&phase==3);}
  void clearAppAuthorityCall(){assert(issuerHeld);}
 } s{physical,issuer};Storage *storage_=&s;
 IOReturn closeApplicationExecution(IOUserClient&,ZornGen7AppExecution26*&);
 void initializeClose(){s.appExecution=&app;app.refs=4;}
''')
    code=code.replace('if(hfi.s.activeApp)hfi.s.activeApp->release();assert(hfi.refs==1&&maps.refs==1&&app.refs==1);','if(hfi.s.activeApp)hfi.s.activeApp->release();while(app.refs>1)app.release();assert(hfi.refs==1&&maps.refs==1&&app.refs==1);')
    close_body=extract(ring,'IOReturn ZornGen7HostRing26::closeApplicationExecution(')
    code=code.replace('int main(){unsigned controls=0;',close_body+'\nint main(){unsigned controls=0;')
    code=code.replace(' assert(allocations==frees);',r'''
 for(unsigned mode=0;mode<5;++mode){ZornGen7HostRing26 f;assert(!f.reserve());assert(!f.hfi.acquireApplicationOob(f,f.app));assert(!f.hfi.releaseApplicationOob(f,f.app));f.initializeClose();IOUserClient client;auto*p=&f.app;
  if(mode==1)f.app.closeRaw=7;if(mode==2)f.s.native.count=1;if(mode==3)f.s.appExecutionPending=true;if(mode==4)f.corrupt(0);
  auto raw=f.closeApplicationExecution(client,p);
  if(mode==0){assert(!raw&&!p&&!f.s.appExecution&&f.hfi.refs==1&&f.maps.refs==1&&f.app.refs==1&&f.app.closeCalled==1);}
  else{assert(raw&&p==&f.app&&f.hfi.refs==2&&f.maps.refs==2);assert(f.app.closeCalled==(mode==1||mode==4));assert(f.s.stopped==(mode==1||mode==4));}
  ++controls;
 }
 assert(allocations==frees);''')
    source=O/'hostcheck.cpp';source.write_text(code);exe=O/'hostcheck';args=['/usr/bin/clang++','-std=c++17','-O1','-g','-fno-omit-frame-pointer','-fsanitize='+a.sanitizer,str(source),'-o',str(exe)]
    runs=[]
    for cmd in [args,[str(exe)]]:
        z=subprocess.run(cmd,capture_output=True,text=True,timeout=120);runs.append(dict(arguments=cmd,exit=z.returncode,stdout=z.stdout,stderr=z.stderr));(O/'commands.json').write_text(json.dumps(runs,indent=2)+'\n');assert not z.returncode,z.stderr[-5000:]
    pin=lambda p:dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    result=dict(passed=True,sanitizer=a.sanitizer,source=[pin(S/n) for n in ['ZornGen7PhysicalOob26.h','ZornGen7DirectHfi26.cpp','ZornGen7HostRing26.cpp','ZornGen7AppExecution26.cpp']],actual_direct_protocol_sequence_preserved=True,actual_per_access_permission_and_bounded_poll_preserved=True,Board_source_byte_equal=True,actual_header_and_transport_methods_compiled=True,MMIO_authority_and_idle_boundaries_are_host_fixtures=True,failed_fixture_teardown_is_not_device_cleanup=True,phone_access=False,hardware_qualified=False,output=runs[-1]['stdout'])
    (O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result['output'],end='')
if __name__=='__main__':main()

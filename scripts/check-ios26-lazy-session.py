from pathlib import Path
import json,hashlib,subprocess,os,shutil
import argparse
parser=argparse.ArgumentParser(description='Check actual iOS26 lazy native-session service/lifecycle source with explicit host XNU/hardware stubs')
parser.add_argument('--source-root',type=Path,required=True)
parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--sanitizer',choices=('address,undefined','thread'),default='address,undefined')
options=parser.parse_args();S=options.source_root.resolve();O=options.out;O.mkdir();t=(S/'direct-runtime/ZornGen7AppIo26.cpp').read_text();header=(S/'direct-runtime/ZornGen7AppIo26.h').read_text();header='\n'.join(x for x in header.splitlines() if not x.startswith('#include'))
names=['IOReturn ZornGen7AppIoService26::newUserClient','IOReturn ZornGen7AppIoService26::reserveNativeClient','void ZornGen7AppIoService26::returnClientSlot','bool ZornGen7AppIoClient26::matchesOwnedSession','IOReturn ZornGen7AppIoClient26::ensureProcess','IOReturn ZornGen7AppIoClient26::dropViews','IOReturn ZornGen7AppIoClient26::clientClose','void ZornGen7AppIoClient26::free'];functions=[]
for name in names:
 a=t.index(name);z=t.index('{',a);depth=1;end=z+1
 while depth:
  if t[end]=='{':depth+=1
  elif t[end]=='}':depth-=1
  end+=1
 functions.append(t[a:end])
prefix=r'''
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <mutex>
#include <thread>
#include <vector>
#include <cstdio>
using IOReturn=int;using UInt32=uint32_t;using IOOptionBits=unsigned;using thread_t=void*;
static constexpr int kIOReturnSuccess=0,kIOReturnBadArgument=1,kIOReturnNotReady=2,kIOReturnExclusiveAccess=3,kIOReturnNoMemory=4,kIOReturnNotPermitted=5,kIOReturnUnsupported=6;
#define THREAD_NULL nullptr
struct Task {unsigned pid=0;uint64_t unique=0;std::atomic<unsigned> refs{1};};
using task_t=Task*;using proc_t=Task*;
static Task kernelObject;static task_t kernel_task=&kernelObject;static thread_local task_t callingTask;
#define TASK_NULL nullptr
static task_t current_task(){return callingTask;}
static thread_t current_thread(){static thread_local unsigned token;return &token;}
static void task_reference(task_t t){++t->refs;}
static void task_deallocate(task_t t){assert(t->refs>1);--t->refs;}
static void *get_bsdtask_info(task_t t){return t;}
static uint64_t proc_uniqueid(proc_t t){return t->unique;}
static unsigned proc_pid(proc_t t){return t->pid;}
static std::atomic<unsigned> binds{},nativePrepare{},nativeOob{},nativeOpen{},nativeClose{},nativeRelease{},nativeFinal{},terminated{},liveLocks{},viewArrays{},liveObjects{};
static unsigned failure=0;static std::atomic<bool> failClassAllocation{false};
struct OSObject {
 std::atomic<unsigned> refs{1};OSObject(){++liveObjects;}virtual ~OSObject(){--liveObjects;}
 virtual void free(){}void retain(){++refs;}void release(){assert(refs);if(--refs==0){free();delete this;}}
};
struct OSDictionary:OSObject{};
struct IOExternalMethodArguments{};struct IOExternalMethodDispatch{};
struct IOMemoryMap:OSObject {IOReturn unmap(){return failure==15?15:0;}};
struct IOMemoryDescriptor:OSObject {};
struct IOService:OSObject {
 IOService *provider=nullptr;bool init(){return true;}bool attach(IOService *p){if(failure==4)return false;provider=p;return true;}
 bool start(IOService*){return failure!=5;}void stop(IOService*){}void detach(IOService*){provider=nullptr;}
 IOService *getProvider() const{return provider;}bool terminate(){++terminated;return true;}
 virtual IOReturn newUserClient(task_t,void*,UInt32,OSDictionary*,class IOUserClient**){return kIOReturnUnsupported;}
 virtual IOReturn setProperties(OSObject*){return kIOReturnUnsupported;}
};
struct IOUserClient:IOService {
 bool initWithTask(task_t,void*,UInt32,OSDictionary*){return failure!=1;}
 IOMemoryMap *removeMappingForDescriptor(IOMemoryDescriptor*){return nullptr;}
 virtual IOReturn externalMethod(uint32_t,IOExternalMethodArguments*,IOExternalMethodDispatch*,OSObject*,void*){return kIOReturnUnsupported;}
 virtual IOReturn clientMemoryForType(UInt32,IOOptionBits*,IOMemoryDescriptor**){return kIOReturnUnsupported;}
 virtual IOReturn clientClose(){return kIOReturnUnsupported;}
};
struct IOAcceleratorES:IOService {};
#define OSDeclareDefaultStructors(Name) public: static void *operator new(std::size_t n) noexcept {if(failClassAllocation)return nullptr;return std::malloc(n);} static void operator delete(void *p){std::free(p);}
#define OSDefineMetaClassAndStructors(A,B)
struct IOLock {std::mutex mutex;};
static IOLock *IOLockAlloc(){if(failure==2)return nullptr;++liveLocks;return new IOLock;}
static void IOLockFree(IOLock *p){assert(p);--liveLocks;delete p;}
static void IOLockLock(IOLock *p){p->mutex.lock();}static void IOLockUnlock(IOLock *p){p->mutex.unlock();}
template<class T>static T *hostViews(size_t n){if(failure==3)return nullptr;++viewArrays;return new T[n]{};}
template<class T>static void hostDelete(T*p){assert(p);--viewArrays;delete[]p;}
#define IONewZero(T,N) hostViews<T>(N)
#define IODelete(P,T,N) hostDelete(P)
struct ZornGen7AppExecution26{};struct ZornGen7ProcessTables26{};struct ZornGen7AppAuthority26{};
struct ZornGen7HostRing26:OSObject {
 IOReturn prepareApplicationExecution(IOUserClient&,task_t,UInt32,OSObject&,const ZornGen7AppAuthority26&,ZornGen7AppExecution26*&);
 IOReturn acquireApplicationOob(IOUserClient&,ZornGen7AppExecution26&);
 IOReturn openApplicationProcess(IOUserClient&,ZornGen7AppExecution26&,ZornGen7ProcessTables26*&);
 IOReturn closeApplicationProcess(IOUserClient&,ZornGen7AppExecution26&,ZornGen7ProcessTables26*&);
 IOReturn releaseApplicationOob(IOUserClient&,ZornGen7AppExecution26&);
 IOReturn closeApplicationExecution(IOUserClient&,ZornGen7AppExecution26*&);
};
static void zorn26_client_event240(unsigned){}
static IOReturn ZornGen7AdmitTaskService26(IOService&,task_t,UInt32){return failure==6?6:0;}
static IOReturn ZornGen7AdmitTaskClient26(IOUserClient&,task_t,UInt32){return failure==7?7:0;}
static void appObservationBind(uintptr_t,uint64_t,unsigned){++binds;}
static void appObservationEvent(uintptr_t,unsigned,unsigned,unsigned,bool=false){}
'''
suffix=r'''
// The real XNU/hardware boundaries are explicit host fixtures,not claimed passes.
void ZornGen7AppIoService26::free(){if(clients_)IOLockFree(clients_);IOService::free();}
IOReturn ZornGen7AppIoService26::createAndPublish(ZornGen7HostRing26&,OSObject&,const ZornGen7AppAuthority26&,IOService*&){return kIOReturnUnsupported;}
IOReturn ZornGen7AppIoService26::setProperties(OSObject*){return kIOReturnUnsupported;}
IOReturn ZornGen7AppIoClient26::externalMethod(uint32_t,IOExternalMethodArguments*,IOExternalMethodDispatch*,OSObject*,void*){return kIOReturnUnsupported;}
IOReturn ZornGen7AppIoClient26::clientMemoryForType(UInt32,IOOptionBits*,IOMemoryDescriptor**){return kIOReturnUnsupported;}
static ZornGen7AppExecution26 execution;static ZornGen7ProcessTables26 process;
IOReturn ZornGen7HostRing26::prepareApplicationExecution(IOUserClient&,task_t,UInt32,OSObject&,const ZornGen7AppAuthority26&,ZornGen7AppExecution26*&out){++nativePrepare;if(failure==10)return 10;out=&execution;return 0;}
IOReturn ZornGen7HostRing26::acquireApplicationOob(IOUserClient&,ZornGen7AppExecution26&){++nativeOob;return failure==11?11:0;}
IOReturn ZornGen7HostRing26::openApplicationProcess(IOUserClient&,ZornGen7AppExecution26&,ZornGen7ProcessTables26*&out){++nativeOpen;if(failure==12)return 12;out=&process;return 0;}
IOReturn ZornGen7HostRing26::closeApplicationProcess(IOUserClient&,ZornGen7AppExecution26&,ZornGen7ProcessTables26*&out){++nativeClose;if(failure==13)return 13;out=nullptr;return 0;}
IOReturn ZornGen7HostRing26::releaseApplicationOob(IOUserClient&,ZornGen7AppExecution26&){++nativeRelease;return failure==14?14:0;}
IOReturn ZornGen7HostRing26::closeApplicationExecution(IOUserClient&,ZornGen7AppExecution26*&out){++nativeFinal;if(failure==16)return 16;out=nullptr;return 0;}
static IOReturn acquire(ZornGen7AppIoClient26*p){IOLockLock(p->serial_);auto r=p->ensureProcess();IOLockUnlock(p->serial_);return r;}
struct Fixture {
 Task task;ZornGen7HostRing26 owner;OSObject authority;ZornGen7AppIoService26 *service=new ZornGen7AppIoService26;
 Fixture(){task.pid=10;task.unique=10;callingTask=&task;service->owner_=&owner;service->authorityOwner_=&authority;service->clients_=IOLockAlloc();assert(service->clients_);}
 ~Fixture(){assert(task.refs==1&&owner.refs==1&&authority.refs==1&&service->refs==1&&!service->reserved_&&!service->client_);service->release();assert(!viewArrays&&!liveLocks);}
 ZornGen7AppIoClient26 *open(){IOUserClient *out=nullptr;assert(service->newUserClient(&task,nullptr,0x4147,nullptr,&out)==0&&out);return static_cast<ZornGen7AppIoClient26*>(out);}
 void close(ZornGen7AppIoClient26*p){assert(p->clientClose()==0&&!p->live_&&!p->openingTask_);p->release();}
};
static unsigned checks;
static void cleanupFailedFixture(Fixture&f,ZornGen7AppIoClient26*p){
 // Host stubs own no DMA/hardware. This cleanup is after retaining assertions,
 // outside the extracted production failure path;never a device recovery recipe.
 failure=0;f.service_->returnClientSlot(p);p->attempted_=false;p->live_=false;p->pinned_=false;p->release();p->release();
}
int main(){
 {
  Fixture f;auto before=nativePrepare.load();auto a=f.open();auto b=f.open();assert(!a->attempted_&&!b->attempted_&&!f.service->reserved_&&nativePrepare==before&&binds==0);++checks;
  f.close(b);assert(!f.service->reserved_&&nativePrepare==before);++checks;
  assert(acquire(a)==0&&a->attempted_&&a->pinned_&&f.service->client_==a&&binds==1);++checks;
  b=f.open();assert(acquire(b)==kIOReturnExclusiveAccess&&!b->attempted_&&!b->pinned_&&b->refs==1);assert(nativePrepare==before+1&&binds==1);++checks;
  f.close(b);assert(f.service->client_==a&&f.service->reserved_);++checks;
  f.service->returnClientSlot(nullptr);assert(f.service->client_==a&&f.service->reserved_);++checks;
  b=f.open();assert(f.service->reserveNativeClient(*b)==kIOReturnExclusiveAccess);f.close(a);assert(!f.service->reserved_);++checks;
  assert(acquire(b)==0&&binds==2&&nativePrepare==before+2);f.close(b);++checks;
 }
 for(unsigned mode:{1u,2u,3u,4u,5u,6u,7u}){
  Fixture f;auto a=f.open();assert(!acquire(a));failure=mode;IOUserClient *out=(IOUserClient*)1;auto raw=f.service->newUserClient(&f.task,nullptr,0x4147,nullptr,&out);assert(raw&&out==nullptr);assert(f.service->reserved_&&f.service->client_==a);failure=0;f.close(a);++checks;
 }
 {
  Fixture f;auto a=f.open();assert(!acquire(a));failClassAllocation=true;IOUserClient*out=(IOUserClient*)1;assert(f.service->newUserClient(&f.task,nullptr,0x4147,nullptr,&out)==kIOReturnNoMemory&&!out);failClassAllocation=false;assert(f.service->client_==a);f.close(a);++checks;
 }
 for(unsigned mode=0;mode<4;++mode){
  Fixture f;Task other;auto before=nativePrepare.load();IOUserClient*out=(IOUserClient*)1;
  task_t t=mode==0?nullptr:mode==1?kernel_task:mode==2?&other:&f.task;auto raw=f.service->newUserClient(t,nullptr,mode==3?1:0x4147,nullptr,&out);assert(raw==kIOReturnNotPermitted&&!out&&!f.service->reserved_&&nativePrepare==before);++checks;
 }
 for(unsigned mode:{10u,11u,12u,13u,14u,16u}){
  Fixture f;auto a=f.open();if(mode<13)failure=mode;assert(acquire(a)==(mode<13?int(mode):0));if(mode>=13)failure=mode;
  const auto tried=nativePrepare.load();assert(a->clientClose()==int(mode)&&a->attempted_&&a->pinned_&&a->refs==2&&f.service->client_==a);auto b=f.open();assert(acquire(b)==kIOReturnExclusiveAccess&&!b->attempted_);failure=0;f.close(b);assert(f.service->client_==a&&nativePrepare==tried);cleanupFailedFixture(f,a);++checks;
 }
 for(unsigned mode=0;mode<7;++mode){
  Fixture f;auto a=f.open();auto serial=a->serial_;auto views=a->views_;auto service=a->service_;auto owner=a->owner_;auto task=a->openingTask_;
  if(mode==0)a->serial_=nullptr;if(mode==1)a->views_=nullptr;if(mode==2)a->viewError_=1;if(mode==3)a->service_=nullptr;if(mode==4)a->owner_=nullptr;if(mode==5)callingTask=kernel_task;if(mode==6)a->live_=false;
  assert(f.service->reserveNativeClient(*a)==kIOReturnNotReady&&!f.service->reserved_);a->serial_=serial;a->views_=views;a->viewError_=0;a->service_=service;a->owner_=owner;a->openingTask_=task;a->live_=true;callingTask=&f.task;f.close(a);++checks;
 }
 {
  Fixture f;std::vector<ZornGen7AppIoClient26*> all;for(unsigned i=0;i<12;++i)all.push_back(f.open());auto before=nativePrepare.load();std::atomic<unsigned>winners{};std::vector<std::thread>threads;
  for(auto *p:all)threads.emplace_back([&,p]{callingTask=&f.task;auto r=acquire(p);assert(r==0||r==kIOReturnExclusiveAccess);if(!r)++winners;});for(auto &t:threads)t.join();assert(winners==1&&nativePrepare==before+1);++checks;
  auto *held=f.service->client_;for(auto *p:all)if(p!=held){assert(!p->attempted_&&!p->pinned_);f.close(p);assert(f.service->client_==held);}f.close(held);++checks;
 }
 assert(!viewArrays&&!liveLocks&&!liveObjects);printf("PASS251 %u actual service/session/lifecycle controls;metadata has no native calls,one real session,failure retains ownership\n",checks);
}
'''
suffix=suffix.replace('f.service_->','f.service->');f=O/'actual-lazy-session.cpp';f.write_text(prefix+'\n'+header+'\n'+'\n'.join(functions)+'\n'+suffix);args=['/usr/bin/clang++','-std=c++17','-pthread','-fsanitize='+options.sanitizer,'-fno-omit-frame-pointer','-fcheck-new',str(f),'-o',str(O/'check')];p=subprocess.run(args,capture_output=True,text=True);(O/'compile.json').write_text(json.dumps(dict(arguments=args,exit=p.returncode,stderr=p.stderr),indent=2)+'\n');assert not p.returncode,p.stderr[-3500:];p=subprocess.run([str(O/'check')],capture_output=True,text=True,env=os.environ|{'ASAN_OPTIONS':'symbolize=0','UBSAN_OPTIONS':'symbolize=0:print_stacktrace=0','TSAN_OPTIONS':'symbolize=0:halt_on_error=1'});(O/'run.json').write_text(json.dumps(dict(exit=p.returncode,stdout=p.stdout,stderr=p.stderr),indent=2)+'\n');assert not p.returncode,p.stderr[-2000:];(O/'result.json').write_text(json.dumps(dict(passed=True,actual_header_and_eight_function_bodies=True,functions=names,source_sha256=hashlib.sha256(t.encode()).hexdigest(),header_sha256=hashlib.sha256((S/'direct-runtime/ZornGen7AppIo26.h').read_bytes()).hexdigest(),ASan_UBSan=options.sanitizer=='address,undefined',TSan=options.sanitizer=='thread',stdout=p.stdout,hardware_and_XNU_boundaries_stubbed=True,fixture_failure_cleanup_not_device_cleanup=True,phone_access=False),indent=2)+'\n');print(p.stdout)

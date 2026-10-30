#!/usr/bin/env python3
"""Qualify and build GopFramebuffer for the exact zorn iPadOS 17 kernel.

Adapted from UniXNU-sheng 0e1f6e52638137db15905db8d775ad73757f39fa,
without sheng peripherals or its historical runtime observations. The current
kernel is checked independently; original class sizes are also checked live.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
ROOT = Path.cwd()
DEVICE = Path(os.environ.get('UNIXNU_DEVICE') or json.loads((ROOT.parents[1]/'state.json').read_text())['device']).resolve()
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--audit-only',action='store_true')
parser.add_argument('--build-test',action='store_true',help='Build but do not enable or boot the experimental display')
args=parser.parse_args()
if not (args.audit_only or args.build_test or 'CONFIG_XNU_NATIVE_LEGACY_DISPLAY=y' in (ROOT.parent/'.config').read_text().splitlines()):
    print('GopFramebuffer Legacy disabled for this profile');raise SystemExit(0)
touch_runtime=os.environ.get('UNIXNU_ZORN_TOUCH_RUNTIME','0')=='1'
OUT=ROOT/'build/native-legacy-display';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'kits/XnuPrelink'))
from native_prelink import macho,backed_offset,exports
def run(cmd,**kw):return subprocess.check_output([str(x) for x in cmd],timeout=90,**kw)
def require(v,why):
    if not v:raise SystemExit(why)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
path=ROOT.parent/'kernel/kernel.macho'
blob=path.read_bytes();plan=json.loads(path.with_suffix('.json').read_text());image=macho(blob)
# The legacy prelink plan predates this port's documented AMFI postlink shim.
# Qualify the actual selected original executables below, and record the actual
# kernel digest rather than treating the old plan's candidate digest as current.
require(plan['original_sha256']=='f18b4df865405f2a287b84977d7aca745e056d656d9fc9df1662970ce2969de7','Exact original iPad7,1 / 21H461 input')
FAMILY_TEXT_SHA='2e044ee68c1650397e1435234ca6459206262e4c7ed709cb7131c6f664f9bd9b'
require(plan['original_executable_sha256']['com.apple.iokit.IOMobileGraphicsFamily']==FAMILY_TEXT_SHA,'Exact original MobileGraphics family')
def read(va,n):
    at=backed_offset(image['segments'],va,n,len(blob));return blob[at:at+n]
names={n:v for v,group in exports(blob,image).items() for n in group}
family='com.apple.iokit.IOMobileGraphicsFamily'
text=next(e for e in plan['extents'] if e['module']==family and e['segment']=='__TEXT_EXEC')
require(hashlib.sha256(read(text['va'],text['size'])).hexdigest()==plan['original_executable_sha256'][family],
        'Complete original executable remains unchanged')
def vptr(pc):
    a,b,c=struct.unpack('<3I',read(pc,12))
    require(a&0x9f00001f==0x90000008 and b&0xffc003ff==0x91000108 and c==0x91004108,'Actual constructor ADRP/ADD/vptr header')
    imm=((a>>5)&0x7ffff)*4+((a>>29)&3)
    if imm&(1<<20):imm-=1<<21
    return (pc&~4095)+(imm<<12)+((b>>10)&4095)+16
def branch(pc):
    w=struct.unpack('<I',read(pc,4))[0];require(w&0xfc000000==0x94000000,'Actual direct constructor call')
    value=w&0x3ffffff;return pc+4*(value-(1<<26) if value&(1<<25) else value)
base_vptr=vptr(0xfffffff00577b324);service_vptr=vptr(0xfffffff00577b51c);legacy_vptr=vptr(0xfffffff0057865d8)
require(branch(0xfffffff0057865fc)==0xfffffff00577b510
        and branch(0xfffffff00577b540)==0xfffffff00577b318,'Actual protected Legacy -> Service -> Framebuffer constructor chain')
base=struct.unpack('<262Q',read(base_vptr,262*8));service=struct.unpack('<262Q',read(service_vptr,262*8))
require([i for i,(a,b) in enumerate(zip(base,service)) if a!=b]==[0,1,7],'Service adds no generic operational overrides')
legacy=struct.unpack('<358Q',read(legacy_vptr,358*8))
require(all(legacy) and read(legacy_vptr+358*8,24)==bytes(24),'Exact nonnull method extent and next aligned vtable boundary')
pure=[i for i,va in enumerate(legacy) if va==names['___cxa_pure_virtual']]
require(pure==[211,213,245,246,306,307,337,338,345],'Actual remaining abstract slots')
changed=[i for i,(a,b) in enumerate(zip(base,legacy)) if a!=b]
require(len(changed)==103 and [i for i in changed if i<168]==[0,1,7,14,21,44,79,85,86,87,111,141,155],
        'Actual original generic implementation overrides')
require(names['__ZN9IOService13newUserClientEP4taskPvjPP12IOUserClient']==base[141],
        'Actual newUserClient override occupies the native four-argument ABI slot')
for i,va in enumerate(legacy):
    if i>=168 and i not in pure:require(text['va']<=va<text['va']+text['size'],'Original family owns inherited generic method')
surface=next(e for e in plan['extents'] if e['module']=='com.apple.iokit.IOSurface' and e['segment']=='__TEXT_EXEC')
require(hashlib.sha256(read(surface['va'],surface['size'])).hexdigest()==plan['original_executable_sha256']['com.apple.iokit.IOSurface']=='6f30c4fccca429b53281ceb298de8cdd4d4dd67deabbe800d436a9d27e1e9dc9','Original IOSurface executable unchanged')
audit=dict(abstract_slots=pure,methods=[dict(address=hex(v)) for v in legacy],legacy_vptr=hex(legacy_vptr))
pure=audit['abstract_slots'];methods=audit['methods']
header='''// SPDX-License-Identifier: BSD-2-Clause-Patent
// Opaque ABI storage for the exact original class, not source-level access
// to its private fields. The actual original metadata supplies its full
// Framebuffer/Service/IOService ancestry. Only qualified base prototypes may
// be called from source; opaque entries are original dispatch targets only.
#pragma once
#include <IOKit/IOService.h>
#include <libkern/libkern.h>
struct OriginalLegacySwapRequest;
class IOMobileFramebufferLegacy : public IOService {
 OSDeclareAbstractStructors(IOMobileFramebufferLegacy)
 unsigned char originalPrivate[0x18a0-sizeof(IOService)];
public:
 // Both fields are qualified by the complete original slot-249 getter.
 // This modifies this object's own mode state, never a vtable or executable.
 void installBootDimensions(uint32_t width,uint32_t height) {
  *reinterpret_cast<uint32_t *>(reinterpret_cast<unsigned char *>(this)+5808)=width;
  *reinterpret_cast<uint32_t *>(reinterpret_cast<unsigned char *>(this)+5812)=height;
 }
 const OriginalLegacySwapRequest *pendingSwapRequest() const {
  const OriginalLegacySwapRequest *request=nullptr;
  memcpy(&request,reinterpret_cast<const unsigned char *>(this)+5480,sizeof(request));return request;
 }
 // The real normal scanout backend removes its pending head before calling
 // slot 295. Slot 312 is a discard path (terminal state 8), not presentation.
 // The queue is a tail queue (head at +5480, tail pointer at +5488, each request's next at +2960 and previous-link at +2968): taking the head
 // moves the next request, if a client already queued one behind it (int-132: swap 3 arrived during swap 2's GPU copy and the old
 // single-entry form refused to retire swap 2, so every wait on it stayed busy), up to the head. The original queue's reference
 // moves to the current-swap slot for the original completion body.
 bool activateOnlyPendingSwap(const OriginalLegacySwapRequest *request) {
  auto self=reinterpret_cast<unsigned char *>(this);
  auto bytes=reinterpret_cast<const unsigned char *>(request);
  const void *current=nullptr,*head=nullptr,*tail=nullptr,*next=nullptr,*previous=nullptr;
  memcpy(&current,self+5472,8);memcpy(&head,self+5480,8);memcpy(&tail,self+5488,8);
  if(!request || current || head!=request)return false;
  memcpy(&next,bytes+2960,8);memcpy(&previous,bytes+2968,8);
  if(previous!=self+5480)return false;
  if(next) {
   const void *link=self+5480;
   memcpy(const_cast<unsigned char *>(reinterpret_cast<const unsigned char *>(next))+2968,&link,8);
  } else if(tail!=bytes+2960)return false;
  memcpy(self+5472,&request,8);
  if(next) {memcpy(self+5480,&next,8);}
  else {const void *empty=nullptr,*emptyTail=self+5480;memcpy(self+5480,&empty,8);memcpy(self+5488,&emptyTail,8);}
  return true;
 }
 void free() override;
 bool init(OSDictionary *properties=nullptr) override;
 IOReturn setProperties(OSObject *) override;
 void systemWillShutdown(IOOptionBits) override;
 IOService *probe(IOService *,SInt32 *) override;
 bool start(IOService *) override;
 void stop(IOService *) override;
 IOWorkLoop *getWorkLoop() const override;
 IOReturn newUserClient(task_t,void *,UInt32,IOUserClient **) override;
 IOReturn setPowerState(unsigned long,IOService *) override;
'''
for i in range(168,358):
    if i==184:header+=' virtual bool isMainDisplay();\n'
    elif i==188:header+=' virtual IOReturn getDotPitch(uint32_t *);\n'
    elif i==213:header+=' virtual IOReturn supportedFrameInfo(uint32_t,uint32_t *,char *,uint32_t *)=0;\n'
    elif i==249:header+=' virtual void getDisplayDimensions(uint32_t *,uint32_t *);\n'
    elif i==290:header+=' virtual void kickSwapQueue();\n'
    elif i==296:header+=' virtual bool validateSwap(const OriginalLegacySwapRequest *);\n'
    elif i==295:header+=' virtual void completeCurrentSwap();\n'
    elif i==337:header+=' virtual IOReturn collectCompletionReports(uint32_t,void *,uint32_t *,uint32_t)=0;\n'
    elif i==288:header+=' virtual bool startHardware();\n'
    elif i==301:header+=' virtual bool getRefreshAttributes(uint64_t *,bool);\n'
    elif i in pure:header+=f' virtual __attribute__((noreturn)) void opaque{i}()=0;\n'
    else:header+=f' virtual __attribute__((deprecated("Unclassified ABI: never call from source"))) void opaque{i}();\n'
header+='};\nstatic_assert(sizeof(IOMobileFramebufferLegacy)==0x18a0,"Actual original instance extent");\n'
(OUT/'OriginalLegacyFramebufferABI.h').write_text(header)
def compile_source(source,output):
    r=json.loads((ROOT/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json').read_text().strip().rstrip(','))
    cmd=[];index=0;a=r['arguments']
    while index<len(a):
        v=a[index]
        if v==r['file']:cmd.append(str(source))
        elif v=='-o':cmd+=['-o',str(output)];index+=1
        elif v in ('-MF','-MJ','-MT'):index+=1
        elif v=='-Xclang' and a[index+1].startswith('-W'):index+=1
        elif not v.startswith('-W') and v not in ('-MD','-MP'):cmd.append(v)
        index+=1
    cmd+=['-DZORN_TOUCH_RUNTIME_ENABLED='+str(int(touch_runtime)),'-I',str(OUT),'-I',str(ROOT/'.cache/xnu-work/osfmk'),'-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-unnecessary-virtual-specifier','-Wno-deprecated-enum-enum-conversion','-Wno-c99-designator','-Wno-reorder-init-list','-Wno-deprecated-declarations','-mgeneral-regs-only']
    result=subprocess.run(cmd,cwd=r['directory'],capture_output=True,text=True)
    output.with_suffix('.compile.log').write_text(result.stdout+result.stderr)
    require(result.returncode==0,(result.stdout+result.stderr)[-5000:])
if not args.audit_only:compile_source(ROOT/'drivers/GopFramebuffer/NativeLegacyDisplay.cpp',OUT/'NativeLegacyDisplay.o')
obj=OUT/'NativeLegacyDisplay.o';raw=obj.read_bytes();image=macho(raw)
st=next(p for c,p,_ in image['commands'] if c==2);sy,count,strings,_=struct.unpack_from('<4I',raw,st+8);symbols=[]
for i in range(count):
    ix,kind,section,_,va=struct.unpack_from('<IBBHQ',raw,sy+i*16)
    symbols.append((raw[strings+ix:raw.index(b'\0',strings+ix)].decode(),va,kind))
vtable=next(va for name,va,_ in symbols if name=='__ZTV19NativeLegacyDisplay');relocations={}
for segment in image['segments']:
    for sec in segment['sections']:
        if sec['va']<=vtable<sec['va']+sec['size']:
            ro,rc=struct.unpack_from('<2I',raw,sec['command_offset']+56)
            for i in range(rc):
                offset,bits=struct.unpack_from('<2I',raw,ro+i*8)
                if bits>>27&1 and bits>>28==0 and bits>>25&3==3:relocations[sec['va']+offset]=symbols[bits&0xffffff][0]
compiled=[relocations.get(vtable+16+i*8) for i in range(358)]
require(all(compiled) and vtable+16+358*8 not in relocations,'Exact owned 358-entry vtable')
candidate=ROOT.parent/'kernel/kernel.macho'
old=candidate.read_bytes();old_image=macho(old)
names={n:v for v,group in exports(old,old_image).items() for n in group}
def read(va,n):
    at=backed_offset(old_image['segments'],va,n,len(old));return old[at:at+n]
bindings={'__ZN25IOMobileFramebufferLegacyC2EPK11OSMetaClass':0xfffffff0057865cc,
          '__ZN25IOMobileFramebufferLegacyD2Ev':0xfffffff005786618,
          '__ZN25IOMobileFramebufferLegacy10gMetaClassE':0xfffffff006b35940,
          '__ZTV25IOMobileFramebufferLegacy':int(audit['legacy_vptr'],16)-16}
owned=[];native=[]
for i,name in enumerate(compiled):
    expected=int(methods[i]['address'],16)
    if name.startswith(('__ZN19NativeLegacyDisplay','__ZNK19NativeLegacyDisplay')):
        owned.append(i);require(i in (0,1,7,14,84,86,87,141,155,184,188,288,290,296,301) or i in pure,'Only qualified own methods and guarded leaves override')
    elif '25IOMobileFramebufferLegacy' in name:
        require(i not in pure,'No unresolved original abstract backend target');bindings[name]=expected
    else:
        require(i<168 and names.get(name)==expected,'Actual inherited native base symbol '+str(i));native.append(i)
require(owned==sorted([0,1,7,14,84,86,87,141,155,184,188,288,290,296,301]+pure),'Exact owned method set')
undefined={n for n,_,k in symbols if k==1 and 'IOMobileFramebufferLegacy' in n}
require(undefined==set(bindings),'All and only actual original-class imports qualified')
# Exact original IOSurface getters, independently observed through the real
# original swap request. These aliases call original code; no object layout
# is substituted and no original method/vtable is patched.
for name,address,field,wide in [
    ('descriptor',0xfffffff004b9ead0,48,True),('width',0xfffffff004b9ebbc,88,True),
    ('height',0xfffffff004b9ebc4,96,True),('stride',0xfffffff004b9ebd4,104,True),
    ('allocation',0xfffffff004b9ebfc,144,True),('format',0xfffffff004b9ebac,128,False),
    ('planes',0xfffffff004b9ebf4,152,False)]:
    expected=(0xf9400000 if wide else 0xb9400000)|((field//(8 if wide else 4))<<10)
    require(read(address,8)==struct.pack('<2I',expected,0xd65f03c0),'Exact original surface getter '+name)
    bindings['_native_legacy_surface_'+name]=address
# The original display-refresh notification sender (self, timestamp, continuous host time, frame interval): it sends the six-word
# vsync message (type 5) to every client entry queued at +5592, the tail queue that selector 72's registration (slot 208) fills at
# +5512 + type*16. The platform subclass that normally calls it on each panel vblank is not part of this port.
require(read(0xfffffff005796720,16)==bytes.fromhex('ff0302d1fd7b07a9fdc30191a0831ff8') and
        read(0xfffffff005796830,4)==bytes.fromhex('08ed4af9') and
        read(0xfffffff00579685c,16)==bytes.fromhex('e2230091c3008052240080521684ff97') and
        read(0xfffffff005795fbc,4)==bytes.fromhex('0ab182d2'),
        'Original vsync sender, its +5592 queue and six-word drop-allowed async send')
bindings['_native_legacy_vsync_notify']=0xfffffff005796720
# Slot 301 fills the six refresh words that setDisplayRefreshProperties publishes as IOMFBDisplayRefresh (minimum interval, its mach
# time, maximum interval, its mach time, step, its mach time; intervals in 32.32 seconds): the generic body fixes the minimum at
# 0x04444444 (1/60 s), and the render server paces its display timer by it.
require(int(methods[301]['address'],16)==0xfffffff00579ea5c and read(0xfffffff00579ea68,8)==bytes.fromhex('888888d28888a0f2') and
        read(0xfffffff00579ec54,4)==bytes.fromhex('08b544f9'),
        'Original slot-301 refresh words with the 1/60 s minimum, called by setDisplayRefreshProperties')
# setDisplayRefreshProperties itself (self): fills the six words through slot 301 and publishes them as IOMFBDisplayRefresh. Nothing in
# the family calls it (the platform subclass does), so without it the render server falls back to its own 1/60 s heartbeat.
require(read(0xfffffff00579ebb8,16)==bytes.fromhex('ff0302d1fd7b07a9fdc30191a0031ff8') and
        read(0xfffffff00579ed54,16)==bytes.fromhex('086540f90173ff90218c0c9100013fd6'),
        'Original setDisplayRefreshProperties publishing IOMFBDisplayRefresh through setProperty')
bindings['_native_legacy_set_refresh_properties']=0xfffffff00579ebb8
# Both protected destructors/constructors must follow the exact original chain.
def branch(pc):
    word=struct.unpack('<I',read(pc,4))[0];require(word&0xfc000000==0x94000000,'Actual protected base call')
    value=word&0x3ffffff;return pc+4*(value-(1<<26) if value&(1<<25) else value)
require(branch(0xfffffff0057865fc)==0xfffffff00577b510 and branch(0xfffffff005786630)==0xfffffff00577b55c,
        'Original protected Legacy C2/D2 really call their original Service bases')
# Actual caller passes only self at slot 288 and tests bit zero of w0.
require(read(0xfffffff005787ef8,16)==bytes.fromhex('080040f9088144f900013fd6e0000037'),
        'Original bool start_hardware() call and result check')
getter=int(methods[249]['address'],16)
for offset,field in [(0x30,5808),(0x58,5812)]:
    require(struct.unpack('<I',read(getter+offset,4))[0]==0xb9400000|((field//4)<<10)|(8<<5)|8,
            'Actual original width/height getter fields')
require(int(methods[295]['address'],16)==0xfffffff005795b88 and
        read(0xfffffff005795b98,16)==bytes.fromhex('e00740f9280080520101001272d3ff97'),
        'Actual original slot-295 passes true to the normal current completion body')
require(read(0xfffffff00578aa7c,24)==bytes.fromhex('080040f9084545f9030080d2e20303aa0400805200013fd6'),
        'Original completion calls optional report slot 337 with null outputs and zero limit')
require(read(0xfffffff005777e9c,16)==bytes.fromhex('080040f908e142f900013fd6c0000036'),
        'Original isMainDisplay dispatch uses only self and tests boolean bit zero')
(OUT/'bindings-audit.json').write_text(json.dumps(dict(candidate_sha256=sha(path),original_sha256=plan['original_sha256'],family_sha256=FAMILY_TEXT_SHA,virtual_entries=358,abstract_slots=pure,owned_entries=owned,bindings={n:hex(v) for n,v in bindings.items()},original_instructions_modified=False,runtime_metadata_qualified=False),indent=2)+'\n')
if args.audit_only:
    print('PASS: current original display family, IOSurface, all 358 dispatch slots and bindings');raise SystemExit(0)
asm=OUT/'original-bindings.S';asm.write_text(''.join(f'.globl {name}\n.set {name}, {va:#x}\n' for name,va in sorted(bindings.items())))
sdk=run(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
run(['xcrun','clang','-target','arm64-apple-ios17.0','-isysroot',sdk,'-c',asm,'-o',OUT/'original-bindings.o'])
llvm=Path(run(['brew','--prefix','llvm'],text=True).strip())/'bin';late=OUT/'NativeLegacyDisplay.late.o'
run([llvm/'llvm-objcopy','--remove-section=__DATA,__mod_init_func','--globalize-symbol=__GLOBAL__sub_I_NativeLegacyDisplay.cpp',obj,late])
def code(data,info):
    sec=next(s for g in info['segments'] for s in g['sections'] if s['name']=='__text');return data[sec['fileoff']:sec['fileoff']+sec['size']]
require(code(raw,image)==code(late.read_bytes(),macho(late.read_bytes())),'Only owned initializer section registration changes')
probe=DEVICE/'native/display/ZornDisplayProbe.cpp'
compile_source(probe,OUT/'ZornDisplayProbe.o')
probe_image=macho((OUT/'ZornDisplayProbe.o').read_bytes())
require(not any(sec['name']=='__mod_init_func' and sec['size'] for seg in probe_image['segments'] for sec in seg['sections']),'Board probe has no unqualified early global constructors')
keystore=ROOT/'drivers/AppleKeyStoreState/NativeKeyStoreEvents.cpp'
compile_source(keystore,OUT/'NativeKeyStoreEvents.o')
keylate=OUT/'NativeKeyStoreEvents.late.o'
run([llvm/'llvm-objcopy','--remove-section=__DATA,__mod_init_func',
     '--globalize-symbol=__GLOBAL__sub_I_NativeKeyStoreEvents.cpp',OUT/'NativeKeyStoreEvents.o',keylate])
keyraw=(OUT/'NativeKeyStoreEvents.o').read_bytes();keydata=keylate.read_bytes()
require(code(keyraw,macho(keyraw))==code(keydata,macho(keydata)),
        'AppleKeyStoreState instructions unchanged by late initializer staging')
keyprobe=DEVICE/'native/display/ZornKeyStoreProbe.cpp'
compile_source(keyprobe,OUT/'ZornKeyStoreProbe.o')
hidprobe=DEVICE/'native/display/ZornHidServices.cpp'
compile_source(hidprobe,OUT/'ZornHidServices.o')
import importlib.util
hid_builder=DEVICE/'scripts/zorn_touch_hid_build.py'
hid_spec=importlib.util.spec_from_file_location('zorn_touch_hid_build',hid_builder)
hid_module=importlib.util.module_from_spec(hid_spec);hid_spec.loader.exec_module(hid_module)
hid_objects=hid_module.build(ROOT,DEVICE,OUT,plan,read,names,compile_source,run,require,macho,code,llvm,sdk) if touch_runtime else []
archive=OUT/'libNativeLegacyDisplay.late.a';archive.unlink(missing_ok=True)
run(['xcrun','ar','rcs',archive,late,OUT/'original-bindings.o',OUT/'ZornDisplayProbe.o',keylate,OUT/'ZornKeyStoreProbe.o',OUT/'ZornHidServices.o',*hid_objects])
sources=[ROOT/'drivers/GopFramebuffer/NativeLegacyDisplay.cpp',ROOT/'drivers/GopFramebuffer/NativeLegacyRequest.h',probe,DEVICE/'native/display/ZornPanelBrightness.h',DEVICE/'native/display/ZornDsiBrightness.h',DEVICE/'native/display/ZornTouchProbe.h',DEVICE/'native/display/ZornTouchHandoff.h',DEVICE/'native/display/ZornTouchIdentify.h',DEVICE/'native/display/ZornFt3683Wire.h',DEVICE/'native/display/ZornTouchFrames.h',DEVICE/'native/display/ZornTouchPrompt.h',DEVICE/'native/display/ZornTouchMatrix.h',keystore,keyprobe,hidprobe,DEVICE/'native/display/ZornTouchHid.cpp',DEVICE/'native/display/ZornTouchContacts.h',DEVICE/'native/display/ZornTouchRuntime.h',hid_builder,Path(__file__).resolve()]
sources += [DEVICE/'native/display/ZornTouchPacing.h',DEVICE/'native/display/ZornTouchTrace.h',DEVICE/'native/display/ZornTouchEdges.h',DEVICE/'native/display/ZornTouchEdgeDispatch.h']
sources.append(DEVICE/'native/display/ZornDisplayProgress.h')
(OUT/'build-report.json').write_text(json.dumps(dict(touch_runtime_compiled=touch_runtime,source_sha256={str(p):sha(p) for p in sources},archive_sha256=sha(archive),generated_abi_sha256=sha(OUT/'OriginalLegacyFramebufferABI.h'),original_candidate_sha256=sha(path),virtual_entries=358,owned_entries=owned,guarded_backend_leaves=[i for i in pure if i not in (213,337)],driver_initialized=False,display_presented=False,desktop=False),indent=2)+'\n')
print('PASS: built canonical GopFramebuffer Legacy with verified original ABI; runtime lifecycle remains unqualified')

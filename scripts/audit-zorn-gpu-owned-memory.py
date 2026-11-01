#!/usr/bin/env python3
"""Audit actual CPU-only GPU objects, Apple virtual ABI and packed payload."""
import argparse,hashlib,json,os,re,struct,subprocess,sys,tempfile,tomllib
from pathlib import Path
from zorn_gpu_link_audit import Kernel,base,bss_zero,call_consumers,code_compare,compare_vtable,indirect_memory_calls,macho,require,sha,symbols
from zorn_gpu_owned_build import compile_command
ROOT=Path(__file__).resolve().parents[2];TREE=ROOT/'UniXNU/out/zorn/tree';OUT=ROOT/'out/zorn/gpu-memory-integration'

def run(cmd,cwd,log):
 p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True);Path(log).write_text(p.stdout+p.stderr);p.check_returncode();return p.stdout

def memory_abi(kernel,tree,out):
 out.mkdir(parents=True,exist_ok=True);rows=[];bindings={};commands=[]
 for cls,table,count in [('IOBufferMemoryDescriptor','__ZTV24IOBufferMemoryDescriptor',44),('IOMemoryDescriptor','__ZTV18IOMemoryDescriptor',37)]:
  recpath=tree/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT'/(cls+'.cpo.json');rec=json.JSONDecoder().raw_decode(recpath.read_text())[0]
  obj=out/(cls+'-abi.o');cmd=compile_command(rec,Path(rec['file']),obj,[])
  run(cmd,rec['directory'],out/(cls+'-compile.log'));commands.append(dict(arguments=cmd,cwd=rec['directory']))
  rows.append(compare_vtable(kernel,obj,table,count))
  for p in [recpath,Path(rec['file']),obj]:bindings[str(p)]=sha(p)
 # Probe the exact public prototypes and real compiler-generated virtual offsets.
 probe=out/'memory-prototypes.cpp';probe.write_text('''#include <IOKit/IOBufferMemoryDescriptor.h>
static_assert(sizeof(IOReturn)==4 && sizeof(IOOptionBits)==4 && sizeof(IODirection)==4);
static_assert(sizeof(IOByteCount)==8 && sizeof(addr64_t)==8);
extern "C" IOReturn gpu_abi_prepare(IOBufferMemoryDescriptor *p){return p->prepare();}
extern "C" IOReturn gpu_abi_complete(IOBufferMemoryDescriptor *p){return p->complete();}
extern "C" void gpu_abi_release(IOBufferMemoryDescriptor *p){p->release();}
extern "C" IOByteCount gpu_abi_length(const IOBufferMemoryDescriptor *p){return p->getLength();}
extern "C" void *gpu_abi_bytes(IOBufferMemoryDescriptor *p){return p->getBytesNoCopy();}
extern "C" addr64_t gpu_abi_physical(IOBufferMemoryDescriptor *p,IOByteCount o,IOByteCount *n){return p->getPhysicalSegment(o,n,kIOMemoryMapperNone);}
extern "C" IOBufferMemoryDescriptor *gpu_abi_make(task_t t,IOByteCount n,addr64_t m){return IOBufferMemoryDescriptor::inTaskWithPhysicalMask(t,kIODirectionInOut|kIOMemoryMapperNone|kIOMemoryPhysicallyContiguous,n,m);}
''')
 recpath=tree/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json';rec=json.JSONDecoder().raw_decode(recpath.read_text())[0]
 obj=out/'memory-prototypes.o';cmd=compile_command(rec,probe,obj,[]);run(cmd,rec['directory'],out/'prototypes-compile.log');commands.append(dict(arguments=cmd,cwd=rec['directory']))
 data,text,functions,relocs=base.parse_object(obj);expected={'prepare':27,'complete':28,'release':5,'length':22,'bytes':41,'physical':19};offsets={}
 for name,slot in expected.items():
  lo=functions['_gpu_abi_'+name];hi=min([v for v in functions.values() if v>lo]+[text['va']+text['size']]);words=struct.unpack('<'+'I'*((hi-lo)//4),data[text['fileoff']+lo-text['va']:text['fileoff']+hi-text['va']])
  # Wrapper has exactly one LDR(Xt,[Xn,#slot*8]) feeding BR/BLR(Xt).
  found=[]
  for i,w in enumerate(words):
   if w&0xffc00000==0xf9400000 and (w>>10&4095)==slot and any((x&0xfffffc1f in (0xd61f0000,0xd63f0000)) and (x>>5&31)==(w&31) for x in words[i+1:]):found.append(i)
  require(len(found)==1,'fresh prototype virtual offset differs '+name);offsets[name]=slot
 make=functions['_gpu_abi_make'];targets=[r['name'] for r in relocs if r['type']==2 and r['external'] and r['site']+text['va']>=make]
 require('__ZN24IOBufferMemoryDescriptor22inTaskWithPhysicalMaskEP4taskjyy' in targets,'static allocation prototype differs')
 kernel.address('__ZN24IOBufferMemoryDescriptor22inTaskWithPhysicalMaskEP4taskjyy')
 for p in [probe,obj,recpath,tree/'.cache/xnu-work/iokit/IOKit/IOMemoryDescriptor.h',tree/'.cache/xnu-work/iokit/IOKit/IOBufferMemoryDescriptor.h']:bindings[str(p)]=sha(p)
 return dict(vtables=rows,prototype_virtual_slots=offsets,annotation_objects_not_linked=True,bindings=bindings,commands=commands)

def verify_menu(text):
 xnu=[e for e in tomllib.loads(text)['entry'] if e.get('type')=='xnu'];require(len(xnu)==1,'XNU menu entry count')
 tokens=xnu[0]['args'].split();required=['zorn_gpu_owned_memory=1','zorn_touch_trace=1','zorn_touch=6','zorn_touch_edges=1','zorn_touch_kernel_parser=1','zorn_touch_fast=1',
  'zorn_smp_preflight=8','zorn_smp_continue=1','zorn_smp_root_publish=1','cpus=8','zorn_data_store=2','zorn_data_retained=1','zorn_brightness=3',
  'zorn_gui_watch=1','zorn_wdt=1','zorn_gui_hold=300','sheng-vsync=60','offline-legacy-cpu-present=1']
 for t in required:require([x for x in tokens if x.startswith(t.split('=')[0]+'=')]==[t],'missing/duplicate/conflicting menu '+t)
 require(not any(t.startswith(('zorn_cpu_active=','zorn_display_progress=','zorn_gui_stack=','zorn_gui_kstack=','zorn_gui_krun=','zorn_smp_stop=')) for t in tokens),'forbidden observation/stop token')
 return tokens

def audit(kernel_path,tree,out,payload):
 out.mkdir(parents=True,exist_ok=True);kernel=Kernel(kernel_path)
 for n in ('_zorn_gpu_owned_configure','_zorn_gpu_owned_gui_tick','_zorn_gpu_owned_transport','_zorn_gpu_memory_profile_ready'):kernel.address(n)
 plan=json.loads(Path(kernel_path).with_suffix('.json').read_text());require(plan['original_sha256']=='f18b4df865405f2a287b84977d7aca745e056d656d9fc9df1662970ce2969de7','original donor identity differs')
 buildpath=tree/'build/zorn-ufs/gpu-owned/build.json';build=json.loads(buildpath.read_text());require(build['enabled'] is True,'GPU native profile is disabled')
 for path,h in build['source_sha256'].items():require(sha(path)==h,'GPU build source changed '+path)
 for path,h in build['object_sha256'].items():require(sha(path)==h,'GPU build object changed '+path)
 objects=[Path(p) for p in build['object_sha256']];command_records=list(build['commands'])
 # Every selected GPU provider/firmware object is independently recompiled.
 independent={};freshdir=out/'independent';freshdir.mkdir(exist_ok=True)
 for rec,obj in zip(command_records,objects):
  cmd=list(rec['arguments']);fresh=freshdir/obj.name;cmd[cmd.index('-o')+1]=str(fresh)
  run(cmd,rec['cwd'],freshdir/(obj.name+'.log'));require(sha(fresh)==sha(obj),'independent GPU object differs '+obj.name);independent[str(obj)]=sha(obj)
 # Actual board/BSD/UFS consumers use their real recorded recipes.
 bsd_recpath=tree/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/bsd/DEVELOPMENT/bsd_init.o.json';bsdrec=json.JSONDecoder().raw_decode(bsd_recpath.read_text())[0]
 bsd=Path(bsdrec['directory'])/bsdrec['output'];board=tree/'build/armcpu/ArmCpu.o';ufs=tree/'build/zorn-ufs/ZornUfsRead.o'
 boardrec=dict(arguments=json.loads((tree/'build/armcpu/compile-command.json').read_text()),cwd=tree/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT')
 ufsrec=json.loads((tree/'build/zorn-ufs/ufs-command.json').read_text())
 for obj,rec in [(board,boardrec),(bsd,dict(arguments=bsdrec['arguments'],cwd=bsdrec['directory'])),(ufs,ufsrec)]:
  cmd=[];i=0;a=rec['arguments'];fresh=freshdir/obj.name
  while i<len(a):
   if a[i] in ('-MF','-MJ','-MT','-MQ'):i+=2;continue
   if a[i] in ('-MD','-MMD','-MP'):i+=1;continue
   if a[i]=='-o':cmd+=['-o',str(fresh)];i+=2;continue
   cmd.append(a[i]);i+=1
  run(cmd,rec['cwd'],freshdir/(obj.name+'.log'));require(sha(fresh)==sha(obj),'independent consumer differs '+obj.name);independent[str(obj)]=sha(obj)
 matched=[];edges=[];got=[];callback_pages=[]
 for obj in objects:
  if obj.name=='stock-firmware.o':continue
  for seg in macho(obj.read_bytes())['segments']:
   require(not any(s['name']=='__mod_init_func' for s in seg['sections']),'unexpected new boot initializer '+obj.name)
  m,e,g,c=code_compare(kernel,obj);matched+=m;edges+=e;got+=g;callback_pages+=c
 for obj,targets in [(board,['_zorn_gpu_memory_profile_ready']),(bsd,['_zorn_gpu_owned_gui_tick']),(ufs,['_zorn_gpu_owned_configure','_zorn_gpu_owned_transport'])]:
  data,text,f,relocs=base.parse_object(obj)
  wanted=set(targets)&f.keys();external=[t for t in targets if t not in f]
  if external:wanted|=call_consumers(obj,external)
  m,e,g,c=code_compare(kernel,obj,wanted);matched+=m;edges+=e;got+=g;callback_pages+=c
 for caller,callee in [('_zorn_gpu_owned_gui_tick','__ZN18ZornGpuOwnedMemory7prepareEPK11ZornGpuBlobjPK18ZornGpuPrepareGate'),('__ZL7gpuGatePvyPK18ZornGpuOwnedMemoryjj','_zorn_gpu_memory_profile_ready')]:
  require(any(e['caller']==caller and e['callee']==callee for e in edges),'required direct edge missing '+caller+' -> '+callee)
 require(any('snapshotCheck' in c['callback'] for c in callback_pages),'actual snapshot callback address not verified')
 # Actual one-shot runtime gate pointer, exact epoch/cookie and original hook.
 gate=kernel.address('__ZZ23zorn_gpu_owned_gui_tickE4gate');pointers=struct.unpack('<3Q',kernel.read(gate,24))
 require(pointers==(1,0,kernel.address('__ZL7gpuGatePvyPK18ZornGpuOwnedMemoryjj')),'immutable prepare gate pointer differs')
 runtime=next(p for p in objects if p.name=='ZornGpuOwnedRuntime.o')
 storage=bss_zero(kernel,runtime,{'__ZL9gpuMemory':9856,'__ZL10gpuCapture':568,'__ZL13gpuConfigured':4,'__ZL10gpuEnabled':4,'__ZL8gpuTried':4,'__ZL8gpuReady':4})
 # Embedded blobs and size words are read-only, fixed stock input bytes.
 firmware=json.loads((ROOT/'UniXNU-zorn/native/gpu-owned/firmware-pins.json').read_text());fw=[]
 for key,rec in firmware.items():
  va=kernel.address('_zorn_gpu_mem_'+key);require(hashlib.sha256(kernel.read(va,rec['bytes'])).hexdigest()==rec['sha256'],'linked stock firmware differs '+key)
  require(struct.unpack('<Q',kernel.read(kernel.address('_zorn_gpu_mem_'+key+'_size'),8))[0]==rec['bytes'],'linked firmware length differs '+key)
  g,s=kernel.section(va,rec['bytes']);require(not g['initprot']&2,'firmware not read-only '+key);fw.append(dict(name=key,bytes=rec['bytes'],sha256=rec['sha256']))
 abi=memory_abi(kernel,tree,out/'abi')
 abi['actual_native_memory_virtual_calls']=indirect_memory_calls(next(p for p in objects if p.name=='NativeAdrenoMemory.o'))
 extent=next(e for e in plan['extents'] if e['module']=='com.apple.iokit.IOMobileGraphicsFamily' and e['segment']=='__TEXT_EXEC')
 require(hashlib.sha256(kernel.read(extent['va'],extent['size'])).hexdigest()=='2e044ee68c1650397e1435234ca6459206262e4c7ed709cb7131c6f664f9bd9b','original MobileGraphics execution changed')
 result=dict(kernel_sha256=sha(kernel_path),object_to_linked_code=matched,actual_call_edges=edges,verified_got_relaxations=got,verified_callback_page_targets=callback_pages,
  immutable_gate_pointer_exact=True,owned_bss=storage,stock_readonly_firmware=fw,original_memory_ABI=abi,independent_objects=independent,hardware_qualified=False,
  page_relocation_scope='Ordinary PAGE opcode/register checks; only callback PAGE targets and GOT relaxations have separately checked complete targets. Normal linker contract remains for other PAGE addresses.',
  new_kernel=True,packed_payload_checked=bool(payload),runtime_complete=False)
 if payload:
  with tempfile.TemporaryDirectory(prefix='gpu-memory-fat-',dir=OUT) as directory:
   directory=Path(directory)
   for name in ('unixnu.toml','Payloads/kernel.macho','Payloads/kernel.macho.adt'):
    run(['mcopy','-i',str(ROOT/'out/zorn/payload.img'),'::/EFI/UniXNU/'+name,str(directory/Path(name).name)],ROOT,out/(Path(name).name+'-fat.log'))
   result['menu_tokens']=verify_menu((directory/'unixnu.toml').read_text())
   for a,b in [(directory/'kernel.macho',Path(kernel_path)),(directory/'kernel.macho.adt',ROOT/'out/zorn/payload-with-trustcache.adt'),(directory/'unixnu.toml',ROOT/'out/zorn/payload-ramdata.toml')]:require(sha(a)==sha(b),'actual FAT content differs '+a.name)
   result.update(packed_kernel_exact=True,packed_ADT_exact=True,packed_menu_exact=True)
 bindings={str(p):sha(p) for p in [Path(__file__),ROOT/'UniXNU-zorn/scripts/zorn_gpu_link_audit.py',ROOT/'UniXNU-zorn/scripts/audit-zorn-cpu-active.py',buildpath,bsd_recpath,tree/'build/zorn-ufs/ufs-command.json',tree/'build/armcpu/compile-command.json']}
 bindings.update(abi['bindings']);result['audit_bindings']=bindings
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--kernel',type=Path,default=ROOT/'UniXNU/out/zorn/kernel/kernel.macho');p.add_argument('--payload',action='store_true');p.add_argument('--output',type=Path,default=OUT/'linked-audit.json');a=p.parse_args()
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.unlink(missing_ok=True)
 result=audit(a.kernel,TREE,OUT/'final-audit/actual',a.payload);a.output.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(dict(kernel_sha256=result['kernel_sha256'],independent_objects=len(result['independent_objects']),functions=len(result['object_to_linked_code']),calls=len(result['actual_call_edges']),virtual_slots=81,payload=a.payload,hardware_qualified=False)))
if __name__=='__main__':main()

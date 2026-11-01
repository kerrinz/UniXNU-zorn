#!/usr/bin/env python3
"""Actual CPU-only wire/runtime host checks; no phone or active build objects."""
from pathlib import Path
import ast,contextlib,hashlib,importlib.util,io,json,os,struct,subprocess,sys,zlib
R=Path(__file__).resolve().parents[2];N=R/'UniXNU-zorn/native/gpu-owned';A=R/'UniXNU/drivers/Adreno740';F=R/'UniXNU/kits/AdrenoFirmware'
O=Path(os.environ.get('UNIXNU_ZORN_HOST_CHECK_OUT', str(R/'out/zorn/gpu-memory-integration/host'))).resolve();O.mkdir(parents=True,exist_ok=True)
D=N/'tests/host-include'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
commands=[]
def run(cmd,name,cwd=None):
 commands.append(dict(arguments=list(map(str,cmd)),cwd=str(cwd or R)))
 p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True);(O/(name+'.log')).write_text(p.stdout+p.stderr);p.check_returncode();return p.stdout
# These are authored host doubles, with actual IOReturn numeric values. This is
# not an Apple virtual layout proof. Preserve upstream double unchanged.
fixture=(A/'tests/XnuMemoryFixture.h').read_text()
a=fixture.index('constexpr IOReturn kIOReturnSuccess=');b=fixture.index('constexpr unsigned kIODirectionOut=',a)
fixture=fixture[:a]+'''constexpr IOReturn kIOReturnSuccess=0,kIOReturnBadArgument=int(0xe00002c2),kIOReturnBusy=int(0xe00002d5),
 kIOReturnNoResources=int(0xe00002be),kIOReturnNoMemory=int(0xe00002bd),kIOReturnUnsupported=int(0xe00002c7),
 kIOReturnNotReady=int(0xe00002d8),kIOReturnIOError=int(0xe00002ca),kIOReturnTimeout=int(0xe00002d6);
'''+fixture[b:]
H=O/'include';H.mkdir(exist_ok=True);(H/'XnuMemoryFixture.h').write_text(fixture)
common=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer']
inc=['-I'+str(p) for p in (H,D,N,A,A/'tests',F)]
run(['clang++','-std=c++20',*common,*inc,N/'tests/test-wire.cpp','-o',O/'test-wire'],'wire-compile')
wire=json.loads(run([O/'test-wire',O],'wire-run'))
sys.path.insert(0,str(R/'UniXNU-zorn/scripts'))
from zorn_gpu_memory import decode as unpack
spec=importlib.util.spec_from_file_location('bound_log_reader',R/'UniXNU-zorn/scripts/read-zorn-log.py');reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
src=(O/'source.bin').read_bytes();cross=[]
for p in sorted(O.glob('wire-*.bin')):
 d=unpack(p.read_bytes());assert d['original_block']==src;cross.append(dict(name=p.name,state=d['state'],status=d['status']))
encoded=(O/'wire-0.bin').read_bytes();corrupt=0
for i in range(4096):
 b=bytearray(encoded);b[i]^=1
 try:unpack(b)
 except ValueError:corrupt+=1
 else:raise AssertionError(('accepted corruption',i))
# CRC-valid semantic corruptions must not become "available" captures.
from zorn_display_progress import SLOTS
semantic=0
for word,value in [(0,0),(0,struct.unpack_from('<I',encoded,1104+SLOTS[0]*8+4)[0]|1<<31),(2,0),(3,0),(4,0),(12,0),(14,0)]:
 b=bytearray(encoded);struct.pack_into('<I',b,1104+SLOTS[word]*8+4,value);struct.pack_into('<I',b,1356,0);struct.pack_into('<I',b,1356,zlib.crc32(b))
 try:unpack(b)
 except ValueError:semantic+=1
 else:raise AssertionError(('accepted semantic corruption',word))
# Actual runtime + actual common NativeMemory source, with explicit doubles.
sources=[N/(n+'.cpp') for n in ('ZornGpuFirmwarePlan','ZornGpuNativePlatform','ZornGpuOwnedMemory','ZornGpuOwnedRuntime')]
sources += [A/(n+'.cpp') for n in ('NativeAdrenoBoard','NativeAdrenoMemory','NativeAdrenoSha256')]+[F/'AdrenoFirmware.c']
objects=[]
for p in sources:
 obj=O/(p.stem+'.o');run(['clang' if p.suffix=='.c' else 'clang++','-std=c11' if p.suffix=='.c' else '-std=c++20',*common,*inc,'-c',p,'-o',obj],p.stem+'-compile');objects.append(obj)
pins=json.loads((N/'firmware-pins.json').read_text());asm=O/'stock-firmware.s';lines=['.section __TEXT,__const']
for key in ('gmu','sqe','aqe','zap'):
 p=R/pins[key]['path'];assert sha(p)==pins[key]['sha256'] and p.stat().st_size==pins[key]['bytes']
 lines+=['.p2align 3',f'.globl _zorn_gpu_mem_{key}',f'_zorn_gpu_mem_{key}:',f'.incbin "{p}"',
         '.p2align 3',f'.globl _zorn_gpu_mem_{key}_size',f'_zorn_gpu_mem_{key}_size:',f'.quad {pins[key]["bytes"]}']
asm.write_text('\n'.join(lines)+'\n')
run(['clang','-c',asm,'-o',O/'stock-firmware.o'],'host-stock-assembly');objects.append(O/'stock-firmware.o')
run(['clang++','-std=c++20',*common,*inc,N/'tests/test-runtime.cpp',*objects,'-o',O/'test-runtime'],'runtime-link')
runtime=[]
for mode in range(4):
 output=O/('runtime-%d.bin'%mode)
 runtime.append(json.loads(run([O/'test-runtime',str(mode),O/'source.bin',output],'runtime-%d'%mode)))
 if mode:
  d=unpack(output.read_bytes());assert d['original_block']==src
  assert d['state']==(2 if mode==1 else 3)
  if mode==3:assert d['quarantined_mask']==1 and d['allocation_status'][0]==d['status'] and not d['cleanup_status_available']
# Test guard AST prefixes, ending immediately after the actual GPU guard. No
# build/payload/USB command executes in either positive or negative control.
base=['--gpu-owned-memory-preflight','--smp-preflight','8','--smp-continue','--smp-root-publication','1','--gui-watch','--touch-trace','--touch-runtime','--touch-edges','--touch-kernel-parser','--touch-fast-poll','--touch-handoff','--hid-family','--retained-data','--data-profile','8g','--memory-mib','8192','--early-watchdog','1','--gui-hold-seconds','300','--display-mode','3','--brightness-mode','3','--data-store-mode','2']
def guard(path,builder):
 module=ast.parse(path.read_text());main=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='main');nodes=[];started=False
 for n in main.body:
  if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='parser' for t in n.targets):started=True
  if started:nodes.append(n)
  if started and isinstance(n,ast.If) and 'args.gpu_owned_memory_preflight' in ast.unparse(n.test):break
 assert nodes and isinstance(nodes[-1],ast.If)
 code=compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(path),'exec')
 import argparse
 argv=base+(['--defconfig','zorn_union_defconfig','--source-pins',str(R/'UniXNU-zorn/source-pins.json'),'--incremental-patched-tree','--recovery-timeout','600'] if builder else [])
 def check(args):
  old=sys.argv;sys.argv=['check',*args]
  try:
   with contextlib.redirect_stderr(io.StringIO()):exec(code,dict(argparse=argparse,Path=Path,ROOT=R,REPO=R,sys=sys))
   return True
  except SystemExit:return False
  finally:sys.argv=old
 assert check(argv)
 changes=[('--smp-preflight','0'),('--smp-root-publication','0'),('--data-profile','512m'),('--memory-mib','4096'),('--early-watchdog','0'),('--gui-hold-seconds','900'),('--brightness-mode','0'),('--display-mode','2'),('--data-store-mode','1')]
 negative=0
 for flag,value in changes:
  copy=argv.copy();copy[copy.index(flag)+1]=value;assert not check(copy),(flag,path);negative+=1
 for flag in ('--smp-continue','--gui-watch','--touch-trace','--touch-runtime','--touch-edges','--touch-kernel-parser','--touch-fast-poll','--touch-handoff','--hid-family','--retained-data'):
  copy=argv.copy();copy.remove(flag);assert not check(copy),flag;negative+=1
 for extra in ('--fresh-data','--smp-stop-after-pass','--cpu-active-observation','--display-progress','--gui-user-stacks','--gui-kernel-stacks','--gui-runnable-kernel-stacks'):
  assert not check(argv+[extra]),extra;negative+=1
 if builder:
  for extra in (['--defconfig','zorn_defconfig'],['--boot'],['--reuse-kernel-control','x'],['--reuse-smp-publication-control','x'],['--reuse-gui-budget-control','x'],['--recovery-timeout','1200']):assert not check(argv+extra);negative+=1
  for flag in ('--source-pins','--incremental-patched-tree'):
   copy=argv.copy();i=copy.index(flag);del copy[i:i+(2 if flag=='--source-pins' else 1)];assert not check(copy);negative+=1
 return negative
guards={name:guard(R/name,builder) for name,builder in [('UniXNU-zorn/scripts/build-zorn-debug.py',True),('uefi-zorn/scripts/make-zorn-payload.py',False)]}
# Restore existing GUI/text/trace semantics on two bound historical logs.
# A self-contained full84-slot fixture with real trace header is mandatory.
# Existing bound historical logs are additional local regressions only.
fixture=bytearray(4096);struct.pack_into('<8s2I',fixture,0,b'ZORNLOGD',84,17)
for i in range(84):fixture[16+12*i:16+12*i+4]=f'D{i:03}'.encode()
struct.pack_into('<8s6IQ',fixture,1024,b'ZORNGUI1',18,3072,1,12,0,1,15000)
trace=[0]*108;trace[0]=2;trace[1]=0x3152545a;trace[10]=1
struct.pack_into('<108I',fixture,3496,*trace);struct.pack_into('<Q',fixture,3952,0xffffffff)
legacy=[];legacy_sources=[('self-contained-v18',bytes(fixture))]
for folder in ('20261030-135043-6aea024f','20261030-160910-6aea024f'):
 path=R/'out/zorn/debug'/folder/'checkpoints.bin'
 if path.is_file():legacy_sources.append((str(path.relative_to(R)),path.read_bytes()))
for label,raw in legacy_sources:
 old=bytearray(raw)
 for slot in SLOTS:struct.pack_into('<I',old,1104+slot*8+4,0)
 struct.pack_into('<I',old,1032,18);b=bytearray(old)
 for slot in SLOTS:struct.pack_into('<I',b,1104+slot*8+4,struct.unpack_from('<I',encoded,1104+slot*8+4)[0])
 struct.pack_into('<I',b,1032,21);struct.pack_into('<I',b,1356,0);struct.pack_into('<I',b,1356,zlib.crc32(b))
 assert unpack(b)['original_block']==old and reader.decode(b)==reader.decode(bytes(old))
 actual=reader.gui_state(b);gpu=actual.pop('gpu_owned_memory');assert actual==reader.gui_state(bytes(old))
 legacy.append(dict(path=label,sha256=hashlib.sha256(raw).hexdigest(),source_version=struct.unpack_from('<I',raw,1032)[0],restored_version=18,gpu_state=gpu['state']))
files=[Path(__file__).resolve(),*sources,*N.glob('*'),*N.glob('tests/*'),R/'UniXNU-zorn/scripts/zorn_gpu_memory.py',R/'UniXNU-zorn/scripts/read-zorn-log.py',R/'UniXNU-zorn/scripts/build-zorn-debug.py',R/'uefi-zorn/scripts/make-zorn-payload.py',H/'XnuMemoryFixture.h',asm,A/'tests/XnuMemoryFixture.h']
result=dict(wire=wire,cross_language_examples=len(cross),corruptions_rejected=corrupt,crc_valid_semantics_rejected=semantic,runtime=runtime,guards=guards,legacy_restorations=legacy,
 bindings={str(p.relative_to(R)):sha(p) for p in sorted(set(files)) if p.is_file()},commands=commands,allow_boot=False,hardware_qualified=False,
 limits=['Actual native provider sources with host IOKit/cache doubles; no Apple object/virtual ABI or physical/DMA proof.','Canonical RAM log unchanged. Wire contains PA/page counts and losslessly representable report errors, not CPU/owner pointers. Incompatible extra error/shape keeps original log and makes GPU observation unavailable.','CRC detects tested corruption, not authentication. Snapshot release/acquire and caller exclusive writer scratch do not constitute full ARM weak memory proof.'])
(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('bindings','commands','limits')}))

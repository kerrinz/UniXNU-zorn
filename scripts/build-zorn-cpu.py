#!/usr/bin/env python3
"""Build canonical ArmCpu normally, or the explicitly pinned K80 preflight."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys
TREE=Path.cwd()
DEVICE=Path(os.environ.get('UNIXNU_DEVICE') or json.loads((TREE.parents[1]/'state.json').read_text())['device']).resolve()
ROOT=DEVICE.parent;STATE=ROOT/'out/zorn/smp/runtime/profile.json'
mode=os.environ.get('UNIXNU_ZORN_SMP','0')
if mode not in ('0','8'):raise SystemExit('unqualified zorn CPU profile')
profile=json.loads(STATE.read_text()) if STATE.exists() else None
if profile and profile['mode']!=('preflight8' if mode=='8' else 'normal'):
    raise SystemExit('CPU/source profile mismatch: use build-zorn-debug.py to restore/select it')
if mode=='0':
    subprocess.run([sys.executable,TREE/'scripts/build-arm-driver.py','ArmCpu'],check=True)
    raise SystemExit(0)
assert profile and profile['mode']=='preflight8'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=STATE.parent/'ArmCpu.cpp'
assert sha(source)==profile['driver_source_sha256']
for name,h in profile['driver_headers'].items():assert sha(STATE.parent/name)==h
for name,v in profile['files'].items():assert sha(TREE/'.cache/xnu-work'/name)==v['after']
record=json.loads((TREE/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json').read_text().strip().rstrip(','))
out=TREE/'build/armcpu';out.mkdir(parents=True,exist_ok=True);obj=out/'ArmCpu.o'
values=record['arguments'];command=[];i=0
while i<len(values):
    value=values[i]
    if value in ('-o','-MF','-MJ','-MT','-MQ'):
        i+=2;continue
    if value=='-Xclang' and i+1<len(values) and values[i+1].startswith('-W'):
        i+=2;continue
    if value in ('-c','-MD','-MMD','-MP') or value==record['file'] or value.startswith('-W'):
        i+=1;continue
    command.append(value);i+=1
command+=['-c',str(source),'-o',str(obj),'-I',str(STATE.parent),'-I',str(TREE/'.cache/xnu-work/osfmk'),'-mgeneral-regs-only',
    '-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-c99-designator','-Wno-reorder-init-list','-Wno-deprecated-enum-enum-conversion','-Wno-unnecessary-virtual-specifier']
(out/'compile-command.json').write_text(json.dumps(command,indent=2)+'\n')
result=subprocess.run(command,cwd=record['directory'],capture_output=True,text=True)
(out/'compile.log').write_text(result.stdout+result.stderr)
if result.returncode:raise SystemExit((result.stdout+result.stderr)[-6000:])
def asm(name):return subprocess.check_output(['xcrun','llvm-objdump','--disassemble','--disassemble-symbols='+name,str(obj)],text=True).lower()
assert re.search(r'dsb\s+ishst[\s\S]*msr\s+icc_sgi1r_el1[\s\S]*isb',asm('__ZN6ArmCpu9signalCPUEP5IOCPU'))
assert re.search(r'\bsmc\s+#0',asm('__ZN6ArmCpu8startCPUEmm'))
assert re.search(r'dsb\s+ishst[\s\S]*tlbi\s+vmalle1is[\s\S]*dsb\s+ish[\s\S]*isb',asm('_zorn_smp_tlb_flush'))
archive=out/'libArmCpu.a';archive.unlink(missing_ok=True)
subprocess.run(['xcrun','ar','rcs',str(archive),str(obj)],check=True)
report=dict(profile='preflight8',source_sha256=sha(source),object_sha256=sha(obj),archive_sha256=sha(archive),headers=profile['driver_headers'],ordered_actual_sgi=True,actual_psci_smc=True,ordered_actual_all_asid_inner_shareable_tlbi=True,hardware_qualified=False)
(out/'zorn-smp-build.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

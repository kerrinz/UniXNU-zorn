#!/usr/bin/env python3
"""Inspect actual linked eight-core preflight paths, not ADT node claims."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,re,struct,subprocess,tomllib
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--payload',action='store_true');parser.add_argument('--continue-gui',action='store_true');parser.add_argument('--fresh-data',action='store_true');args=parser.parse_args()
ROOT=Path(__file__).resolve().parents[2];TREE=ROOT/'UniXNU/out/zorn/tree';OUT=ROOT/'out/zorn/smp'
kernel=ROOT/'UniXNU/out/zorn/kernel/kernel.macho'
nm=subprocess.check_output(['xcrun','nm','-n',str(kernel)],text=True)
symbols={name:int(addr,16) for addr,name in re.findall(r'^([0-9a-f]+)\s+\S\s+(\S+)$',nm,re.M)}
def find(fragment):
    names=[name for name in symbols if name.startswith('__ZN6ArmCpu') and fragment in name and '.cold.' not in name];assert len(names)==1,(fragment,names)
    return names[0]
def asm(name):return subprocess.check_output(['xcrun','llvm-objdump','--disassemble','--disassemble-symbols='+name,str(kernel)],text=True).lower()
def calls(name,target):
    result={int(v,16) for v in re.findall(r'\b(?:bl|b)\s+0x([0-9a-f]+)',asm(name))}
    assert symbols[target] in result,(name,target)
calls('_zorn_ufs_read_gpt','_zorn_armcpu_preflight')
preflight=find('zornPreflight');coordinator=find('zornCoordinator')
calls('_zorn_armcpu_preflight',preflight)
calls(preflight,'_zorn_smp_tlb_flush')
calls(coordinator,'_processor_start')
calls(coordinator,'_thread_bind')
calls(coordinator,'_zorn_smp_tlb_flush')
calls(find('zornReport'),'_zorn_ufs_smp_record')
remap=find('zornRemapProbe');calls(coordinator,remap)
calls(remap,'_pmap_enter_options_addr');calls(remap,'_pmap_remove')
calls(remap,'_kmem_free_guard')
assert re.search(r'dsb\s+ishst[\s\S]*tlbi\s+vmalle1is[\s\S]*dsb\s+ish[\s\S]*isb',asm('_zorn_smp_tlb_flush'))
assert re.search(r'dsb\s+ishst[\s\S]*msr\s+icc_sgi1r_el1[\s\S]*isb',asm('__ZN6ArmCpu9signalCPUEP5IOCPU'))
assert re.search(r'\bsmc\s+#0',asm('__ZN6ArmCpu8startCPUEmm'))
assert '_zorn_smp_tlb_ready' in symbols
calls('_flush_mmu_tlb_full_asid_async','_zorn_smp_tlb_flush')
calls('_flush_mmu_tlb_region_asid_async','_zorn_smp_tlb_flush')
profile=json.loads((OUT/'runtime/profile.json').read_text())
assert profile['mode']=='preflight8'
for name,record in profile['files'].items():
    assert hashlib.sha256((TREE/'.cache/xnu-work'/name).read_bytes()).hexdigest()==record['after']
config=(TREE.parent/'.config').read_text().splitlines()
data_enabled='CONFIG_XNU_NATIVE_RAM_BLOCK=y' in config and 'CONFIG_XNU_NATIVE_LEGACY_DISPLAY=y' in config
if args.continue_gui:
    assert data_enabled
    calls('_zorn_ufs_runtime_snapshot','_zorn_armcpu_runtime')
else:
    assert 'CONFIG_XNU_NATIVE_RAM_BLOCK=y' not in config and 'CONFIG_XNU_NATIVE_LEGACY_DISPLAY=y' not in config
result=dict(kernel_sha256=hashlib.sha256(kernel.read_bytes()).hexdigest(),
    actual_pre_root_preflight_call=True,actual_processor_start_and_thread_bind_calls=True,
    actual_coordinator_tlb_call=True,actual_snapshot_log_call=True,actual_ordered_sgi_psci_and_shareable_tlbi=True,
    actual_standard_pmap_remap_probe=True,data_driver_disabled=not data_enabled,source_profile_matches=True,hardware_qualified=False)
if args.payload:
    spec=importlib.util.spec_from_file_location('adt',ROOT/'UniXNU-zorn/scripts/prepare-zorn-smp.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    adt=ROOT/'out/zorn/payload-with-trustcache.adt';tree=m.parse_adt(adt.read_bytes())
    cpus=m.child(tree,b'cpus');assert len(cpus[1])==8
    for id,cpu in enumerate(cpus[1]):
        p=dict(cpu[0]);assert p[b'reg']==struct.pack('<I',id*0x100)
        assert p[b'state']==(b'running\0' if id==0 else b'waiting\0') and p[b'compatible']==b'qcom,kryo\0'
    assert dict(m.child(tree,b'psci')[0])[b'method']==b'smc\0'
    mem=m.child(m.child(tree,b'chosen'),b'memory-map')
    if args.continue_gui:assert dict(mem[0])[b'PackedRAMDisk']==bytes(16)
    else:assert not any(k in (b'RAMDisk',b'PackedRAMDisk') for k,v in mem[0])
    entries=tomllib.loads((ROOT/('out/zorn/payload-ramdata.toml' if args.continue_gui else 'out/zorn/payload-debug.toml')).read_text())['entry']
    xnu=[e for e in entries if e.get('type')=='xnu'];assert len(xnu)==1
    assert bool(xnu[0].get('initrd'))==args.continue_gui
    tokens=xnu[0]['args'].split()
    for token in ('zorn_smp_preflight=8','sheng-smp=1','armcpu-self-ipi=1','cpus=8'):assert tokens.count(token)==1
    if args.continue_gui:
        for token in ('zorn_smp_continue=1','zorn_data_store=2','zorn_brightness=3'):assert tokens.count(token)==1
        if args.fresh_data:assert not any(t.startswith('zorn_data_retained=') for t in tokens)
        else:assert tokens.count('zorn_data_retained=1')==1
        assert not any(t.startswith(('zorn_gui_stack=','zorn_gui_kstack=','zorn_gui_krun=')) for t in tokens)
        assert all(t=='zorn_touch=6' for t in tokens if t.startswith('zorn_touch='))
    else:assert not any(t.startswith(('zorn_data_store=','zorn_data_retained=')) for t in tokens)
    result.update(actual_eight_distinct_affinities=True,psci_smc=True,payload_no_data=not args.continue_gui,
                  payload_adt_sha256=hashlib.sha256(adt.read_bytes()).hexdigest())
(OUT/'linked-call-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

#!/usr/bin/env python3
"""Require matched recovered eight-core remap evidence before any GUI trial."""
from pathlib import Path
import hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'out/zorn/smp'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
proof=json.loads((OUT/'eight-remap-qualified.json').read_text())
assert proof['cores']==8 and proof['remap_epochs']==9 and proof['remap_errors']==0 and proof['cleanup_passed']
run=ROOT/proof['run'];archive=ROOT/proof['archive'];r=json.loads((run/'run.json').read_text());b=json.loads((archive/'inputs.json').read_text())
assert r['status']=='recovered' and r['kernel_log_changed'] is True and r['serial']=='92988a43' and r['product']=='zorn' and r['slot']=='b'
assert sha(archive/'boot.img')==b['sha256']==r['sha256']==proof['boot_sha256']
assert sha(archive/'kernel.macho')==proof['kernel_sha256']==b['inputs'][str(ROOT/'UniXNU/out/zorn/kernel/kernel.macho')]
assert sha(run/'checkpoints.bin')==proof['log_sha256']
t=(run/'checkpoints.txt').read_text()
assert 'SMP PASS target=8 phase=80 seen=ff bound=ff failure=0' in t and t.count('remap=9 err=0 value=4b38305f50414741')==8 and 'panic:' not in t
spec=importlib.util.spec_from_file_location('profile',ROOT/'UniXNU-zorn/scripts/prepare-zorn-smp-runtime.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
current=(ROOT/'UniXNU-zorn/native/smp/ZornSmpRuntime.inc').read_text();original=(archive/'ZornSmpRuntime.inc').read_text()
for name in ('bool ArmCpu::zornRemapProbe','void ArmCpu::zornRemapWorker','void ArmCpu::zornCoordinator'):
    a,z=m.span(current,name);c,d=m.span(original,name);assert current[a:z]==original[c:d],name+' changed since hardware qualification'
for name in ('ArmCpu-assembly-newlines.patch','ArmCpu-zorn-preflight.patch'):
    p=ROOT/'UniXNU-zorn/native/smp'/name;assert sha(p)==b['inputs'][str(p)]
result=dict(qualified_boot_sha256=b['sha256'],fresh_recovered_log=True,matched_archive=True,eight_remap_workers_and_coordinator_exact=True,
            original_cpu_adapter_patch_exact=True,hardware_gui_qualified=False)
(OUT/'qualified-proof-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

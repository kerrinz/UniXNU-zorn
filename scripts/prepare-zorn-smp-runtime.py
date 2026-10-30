#!/usr/bin/env python3
"""Apply/restore a pinned opt-in SMP source profile; never touch USB or Git."""
import argparse,hashlib,json,re,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
TREE=ROOT/'UniXNU/out/zorn/tree';WORK=TREE/'.cache/xnu-work'
NATIVE=ROOT/'UniXNU-zorn/native/smp';OUT=ROOT/'out/zorn/smp/runtime'
sha=lambda data:hashlib.sha256(data).hexdigest()

def span(text,name):
    match=re.search(r'(?m)^'+re.escape(name)+r'\([^;{}]*\)\s*\{',text)
    if not match:raise ValueError('missing function '+name)
    depth=0
    for token in re.finditer(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\x27(?:\\.|[^\x27\\])*\x27|[{}]',text[match.end()-1:],re.S):
        if token.group()=='{':depth+=1
        if token.group()=='}':
            depth-=1
            if not depth:return match.start(),match.end()-1+token.end()
    raise ValueError('unbalanced function '+name)

def replace_function(text,original,name):
    a,b=span(text,name);c,d=span(original,name)
    return text[:a]+original[c:d]+text[b:]

def transform(relative,before,original):
    s=before.decode();ref=original.decode()
    if relative=='bsd/kern/bsd_init.c':
        native=ROOT/'UniXNU-zorn/native/cpu-active'
        record=json.loads((native/'source-profile.json').read_text())
        patch=native/'bsd-caller.patch'
        if sha(before)!=record['before'] or sha(patch.read_bytes())!=record['patch_sha256']:
            raise ValueError('CPU-active source/patch differs')
        with tempfile.TemporaryDirectory(prefix='cpu-active-source-') as directory:
            staging=Path(directory);target=staging/relative;target.parent.mkdir(parents=True);target.write_bytes(before)
            subprocess.run(['git','apply','--check',str(patch)],cwd=staging,check=True)
            subprocess.run(['git','apply',str(patch)],cwd=staging,check=True)
            desired=target.read_bytes()
        if sha(desired)!=record['after']:raise ValueError('CPU-active caller result differs')
        return desired
    if relative=='osfmk/kern/lock_rw.c':return original
    if relative.endswith('pmap_internal.h'):
        for name in ('pmap_lock','pmap_lock_preempt'):s=replace_function(s,ref,name)
    if relative.endswith('/pmap.c'):
        for name in ('alloc_asid','pmap_destroy_internal'):s=replace_function(s,ref,name)
    if relative.endswith('/tlb.h'):
        marker='#include <machine/atomic.h>'
        assert s.count(marker)==1
        declarations='''
#ifdef __cplusplus
extern "C" {
#endif
extern volatile unsigned zorn_smp_tlb_ready;
void zorn_smp_tlb_flush(void);
#ifdef __cplusplus
}
#endif
'''
        s=s.replace(marker,marker+'\n'+declarations)
        for name in ('flush_mmu_tlb_async','flush_mmu_tlb_allentries_async','flush_mmu_tlb_entries_async',
                     'flush_mmu_tlb_asid_async','flush_mmu_tlb_range_async','flush_mmu_tlb_allrange_async'):
            a,b=span(s,name);brace=s.index('{',a,b)
            s=s[:brace+1]+'\n\tif (__atomic_load_n(&zorn_smp_tlb_ready, __ATOMIC_ACQUIRE)) { zorn_smp_tlb_flush(); return; }'+s[brace+1:]
    return s.encode()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=['normal','preflight8'],required=True);a=p.parse_args()
    pins=json.loads((NATIVE/'runtime-source-pins.json').read_text())
    state=OUT/'profile.json';previous=json.loads(state.read_text()) if state.exists() else None
    changes=[]
    # Audit every source before mutating any, including source archives.
    for relative,record in pins.items():
        current=(WORK/relative).read_bytes();original=(TREE/'refer/xnu'/relative).read_bytes()
        if sha(original)!=record['original']:raise ValueError('original feed differs '+relative)
        backup=OUT/'baseline'/relative
        if sha(current)==record['before']:before=current
        elif previous and sha(current)==previous['files'][relative]['after'] and backup.is_file():before=backup.read_bytes()
        else:raise ValueError('unqualified current source '+relative)
        if sha(before)!=record['before']:raise ValueError('backup differs '+relative)
        desired=before if a.mode=='normal' else transform(relative,before,original)
        changes.append((relative,current,before,desired))
    OUT.mkdir(parents=True,exist_ok=True)
    driver={}
    # Validate and stage every driver patch before changing any XNU source.
    if a.mode=='preflight8':
        source=ROOT/'UniXNU/drivers/ArmCpu/ArmCpu.cpp';origin=json.loads((NATIVE/'origin.json').read_text())
        if sha(source.read_bytes())!=origin['source_sha256']:raise ValueError('ArmCpu input differs')
        with tempfile.TemporaryDirectory(prefix='driver-staging-',dir=OUT) as temporary:
            staging=Path(temporary);output=staging/'ArmCpu.cpp';output.write_bytes(source.read_bytes())
            for patch in ('ArmCpu-assembly-newlines.patch','ArmCpu-zorn-preflight.patch'):
                subprocess.run(['git','apply','--check',str(NATIVE/patch)],cwd=staging,check=True)
                subprocess.run(['git','apply',str(NATIVE/patch)],cwd=staging,check=True)
            driver['ArmCpu.cpp']=output.read_bytes()
        for name in ('ZornSmpPolicy.h','ZornSmpRuntime.inc'):driver[name]=(NATIVE/name).read_bytes()
        driver['ZornActiveHandles.inc']=(ROOT/'UniXNU-zorn/native/cpu-active/ZornActiveHandles.inc').read_bytes()
    files={}
    for relative,current,before,desired in changes:
        backup=OUT/'baseline'/relative;backup.parent.mkdir(parents=True,exist_ok=True)
        if backup.exists() and backup.read_bytes()!=before:raise ValueError('existing backup differs')
        if not backup.exists():backup.write_bytes(before)
        if current!=desired:(WORK/relative).write_bytes(desired)
        files[relative]={'before':sha(before),'after':sha(desired),'original':pins[relative]['original']}
    report=dict(mode=a.mode,files=files,original_rwlock_exact=a.mode=='preflight8',original_asid_allocator=a.mode=='preflight8',original_pmap_destroy=a.mode=='preflight8',runtime_tlb_global_switch=a.mode=='preflight8',hardware_qualified=False)
    if a.mode=='preflight8':
        for name,data in driver.items():(OUT/name).write_bytes(data)
        output=OUT/'ArmCpu.cpp'
        report['driver_source_sha256']=sha(output.read_bytes())
        report['driver_headers']={name:sha((OUT/name).read_bytes()) for name in driver if name!='ArmCpu.cpp'}
    state.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()

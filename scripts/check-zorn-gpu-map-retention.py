#!/usr/bin/env python3
"""Pinned lower-map failure semantics and isolated native error-retention repair.

Only Linux reference error paths execute on host. No native method or successful
allocator, map, address or handle model is provided. Native sources compile only.
"""
from pathlib import Path
import json,hashlib,subprocess,importlib.util,difflib,shlex
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-gen7-map-retention';N=R/'UniXNU/drivers/NativeAdreno'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
spec=importlib.util.spec_from_file_location('extent_source_util',R/'UniXNU-zorn/scripts/check-zorn-gpu-gmu-extent.py');util=importlib.util.module_from_spec(spec);spec.loader.exec_module(util)
def main():
 if (O/'check-result.json').exists():raise SystemExit('completed; do not repeat')
 pins={};expected={'kgsl_gmu_core.c':'af4a5b04f2aef2536434f4cb07d2c928a40fd528786bafc365a7a7299958eb34','kgsl_mmu.h':'e823b0e9dbcda345c83e5ee0a34011f7c03d0697683a906bd8d89865abb99604','kgsl_mmu.c':'a0ef9422cc24d350f91a182ff8fba3c990ab6e8d1b24836284b755990cdb1ce9'}
 for name,h in expected.items():assert sha(O/name)==h;pins[str(O/name)]=h
 for p in [N/'NativeAdrenoVm.h',N/'NativeAdrenoVm.cpp',R/'out/zorn/gpu-discovery-20261030/profile-reference/adreno_gen7_gmu.c']:pins[str(p)]=sha(p)
 (O/'source-preimages.json').write_text(json.dumps(pins,indent=2)+'\n')
 core=(O/'kgsl_gmu_core.c').read_text();body=util.body(core,'gmu_core_map_memdesc');signature=core[core.index('int gmu_core_map_memdesc('):core.index(body)]
 wrapper=util.body((O/'kgsl_mmu.c').read_text(),'kgsl_mmu_map_sg');assert 'KERNEL_VERSION(6, 2, 0)' in wrapper and wrapper.count('return iommu_map_sg(')==2
 assert 'memdesc->gmuaddr' not in body and 'iommu_unmap' not in body
 assert 'return (mapped < 0) ? mapped : 0;' in body and 'mapped = -ENOMEM;' in body
 assert 'mapped != memdesc->size' not in body
 (O/'exact-reference-map-body.c.inc').write_text(signature+body+'\n')
 prelude='''// SPDX-License-Identifier: GPL-2.0-only
/* Test projection of the pinned GPL reference function. Scalar diagnostic
 * failure stubs only. Not selected provider code or a successful map model. */
#include <stddef.h>
#include <stdint.h>
#include <sys/types.h>
#include <errno.h>
#include <assert.h>
#include <stdio.h>
typedef uint64_t u64;
struct iommu_domain {int unused;};
struct scatterlist {int unused;};
struct sg_table {struct scatterlist *sgl;unsigned nents;};
struct kgsl_memdesc {void *pages;unsigned page_count;size_t size;struct sg_table *sgt;uint64_t gmuaddr;};
#define GFP_KERNEL 0
static ssize_t failure;static int sg_failure;static unsigned maps,allocs;
static ssize_t kgsl_mmu_map_sg(struct iommu_domain *d,u64 a,struct scatterlist *s,unsigned n,int attrs){
 (void)d;(void)a;(void)s;(void)n;(void)attrs;assert(failure<=0);++maps;return failure;
}
static int sg_alloc_table_from_pages(struct sg_table *s,void *p,unsigned n,int a,size_t size,int flags){
 (void)s;(void)p;(void)n;(void)a;(void)size;(void)flags;assert(sg_failure<0);++allocs;return sg_failure;
}
static void sg_free_table(struct sg_table *s){(void)s;__builtin_trap();}
'''
 test='''
int main(void){
 struct sg_table s={0};struct kgsl_memdesc m={0,0,4096,&s,UINT64_MAX};
 failure=-37;assert(gmu_core_map_memdesc(NULL,&m,0,0)==-37&&maps==1&&m.gmuaddr==UINT64_MAX);
 failure=0;assert(gmu_core_map_memdesc(NULL,&m,0,0)==-ENOMEM&&maps==2&&m.gmuaddr==UINT64_MAX);
 m.pages=&s;sg_failure=-27;assert(gmu_core_map_memdesc(NULL,&m,0,0)==-27&&maps==2&&allocs==1&&m.gmuaddr==UINT64_MAX);
 puts("Exact reference body negative/zero/SG-construction failure checked; no successful map or native method");
}
'''
 commands=[]
 def run(args,name,cwd=R,good=True):
  args=list(map(str,args));p=subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=55);commands.append(dict(arguments=args,cwd=str(cwd),returncode=p.returncode));(O/(name+'.log')).write_text(p.stdout+p.stderr)
  if good:p.check_returncode()
  else:assert p.returncode!=0
  return p.stdout
 source=O/'reference-error-paths.c';source.write_text(prelude+signature+body+test);flags=['-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined'];run(['clang',*flags,source,'-o',O/'reference-error-paths'],'reference-host-build');run([O/'reference-error-paths'],'reference-host-run')
 negative=[]
 for name,a,b in [('negative-status-erased','return (mapped < 0) ? mapped : 0;','return 0;'),('zero-not-ENOMEM','mapped = -ENOMEM;','mapped = -EIO;')]:
  assert body.count(a)==1;p=O/(name+'.c');p.write_text(prelude+signature+body.replace(a,b)+test);exe=O/name;run(['clang',*flags,p,'-o',exe],name+'-build');run([exe],name+'-refused',good=False);negative.append(name)
 # Repair only the real native map publication error that fail() folds to a
 # generic IOReturn. A separate persistent field survives result_ resets.
 h=(N/'NativeAdrenoVm.h').read_text();cpp=(N/'NativeAdrenoVm.cpp').read_text()
 anchor='struct NativeAdrenoVmResult {';assert h.count(anchor)==1
 h=h.replace(anchor,'struct NativeAdrenoVmNativeFailure {\n    IOReturn first_map_cache_error=0;\n    uint32_t first_map_cache_error_available=0;\n};\n'+anchor)
 anchor='    NativeAdrenoVmResult result_{};';assert h.count(anchor)==1;h=h.replace(anchor,anchor+'\n    NativeAdrenoVmNativeFailure native_failure_{}; /* Never reset by operation result_ clearing. */')
 anchor='    NativeAdrenoVm()=default;';assert h.count(anchor)==1;h=h.replace(anchor,'    const NativeAdrenoVmNativeFailure &nativeFailure() const {return native_failure_;}\n'+anchor)
 anchor='        if(checked)return fail(ArmSmmu4KIoError);';assert cpp.count(anchor)==1
 replacement='''        if(checked) {
            if(!native_failure_.first_map_cache_error_available) {
                native_failure_.first_map_cache_error=checked;
                native_failure_.first_map_cache_error_available=1;
            }
            return fail(ArmSmmu4KIoError);
        }''';cpp=cpp.replace(anchor,replacement)
 for name,s in [('NativeAdrenoVm.h',h),('NativeAdrenoVm.cpp',cpp)]: (O/name).write_text(s)
 patch=''.join(''.join(difflib.unified_diff((N/name).read_text().splitlines(True),(O/name).read_text().splitlines(True),fromfile='a/drivers/NativeAdreno/'+name,tofile='b/drivers/NativeAdreno/'+name)) for name in ['NativeAdrenoVm.h','NativeAdrenoVm.cpp']);(O/'native-cache-error-retention.UNAPPLIED.patch').write_text(patch)
 def audit_native(s):
  m=util.body(s,'NativeAdrenoVm::map');assert m.index('checked=memory->publishForDevice')<m.index('native_failure_.first_map_cache_error=checked;')<m.index('return fail(ArmSmmu4KIoError);'),'raw error must precede folded fail'
  assert 'if(!native_failure_.first_map_cache_error_available)' in m,'retain first error'
  assert 'native_failure_={}' not in s and 'native_failure_ = {}' not in s,'no operation reset of persistent error'
 audit_native(cpp);static=[]
 for name,a,b in [('raw-native-error-zeroed','first_map_cache_error=checked;','first_map_cache_error=0;'),('first-error-overwritten','if(!native_failure_.first_map_cache_error_available)','if(true)')]:
  try:audit_native(cpp.replace(a,b))
  except (AssertionError,ValueError) as e:static.append(dict(name=name,refused=str(e)))
  else:raise RuntimeError('native source corruption survived '+name)
 abi=O/'native-abi.cpp';abi.write_text('#include "NativeAdrenoVm.h"\nstatic_assert(sizeof(IOReturn)==4);\nstatic_assert(__is_same(decltype(NativeAdrenoVmNativeFailure::first_map_cache_error),IOReturn));\nstatic_assert(sizeof(NativeAdrenoVmNativeFailure)==8);\n')
 recipe=R/'UniXNU/out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json';rec=json.JSONDecoder().raw_decode(recipe.read_text())[0];assert '--target=arm64-apple-ios17.0.0' in rec['arguments'];inputs={str(recipe):sha(recipe)};objects={}
 for name,p,include in [('original',N/'NativeAdrenoVm.cpp',N),('candidate',O/'NativeAdrenoVm.cpp',O),('ABI',abi,O)]:
  args=list(rec['arguments']);args[args.index(rec['file'])]=str(p);obj=O/(name+'.o');args[args.index('-o')+1]=str(obj);args+=['-I'+str(include),'-I'+str(N),'-I'+str(R/'UniXNU/kits/ArmSmmu4K'),'-mgeneral-regs-only'];run(args,name+'-first',rec['directory']);first=O/(name+'-first.o');first.write_bytes(obj.read_bytes());run(args,name+'-independent',rec['directory']);assert sha(first)==sha(obj);objects[name]=sha(obj)
  assert '__mod_init_func' not in run(['otool','-l',obj],name+'-sections');run(['nm','-u',obj],name+'-imports');run(['otool','-tvV',obj],name+'-disassembly')
  pp=[];i=0
  while i<len(args):
   if args[i] in ['-o','-MF','-MT','-MJ']:i+=2
   elif args[i]=='-c':i+=1
   else:pp.append(args[i]);i+=1
  dep=O/(name+'.d');run(pp+['-M','-MF',str(dep),'-MT','input'],name+'-deps',rec['directory'])
  for n in shlex.split(dep.read_text().replace('\\\n',' ').split(':',1)[1]):
   p=Path(n)
   if not p.is_absolute():p=Path(rec['directory'])/p
   inputs[str(p)]=sha(p)
 wrong=O/'wrong-raw-width.cpp';wrong.write_text('#include "NativeAdrenoVm.h"\nstatic_assert(sizeof(NativeAdrenoVmNativeFailure::first_map_cache_error)==8);\n');args=list(rec['arguments']);args[args.index(rec['file'])]=str(wrong);args[args.index('-o')+1]=str(O/'wrong.o');args+=['-I'+str(O),'-I'+str(N),'-I'+str(R/'UniXNU/kits/ArmSmmu4K'),'-mgeneral-regs-only'];run(args,'wrong-raw-width-refused',rec['directory'],good=False)
 for p,h in pins.items():assert sha(Path(p))==h,p
 (O/'check-result.json').write_text(json.dumps(dict(commands=commands,inputs=inputs,objects=objects,reference_error_only_host_negatives=negative,new_native_source_refusals=static,wrong_raw_width_compile_refused=True,patch_unapplied=True,upstream_unchanged=True,no_native_method_callback_allocator_VM_or_phone_invocation=True,no_host_successful_address_handle_mapping_model=True,allow_boot=False,readback_qualified=False,WriteAuthorized=0),indent=2)+'\n');print('Pinned lower map failure contract,2 error-only host negatives/2 native source refusals/1 width refusal checked;3 independently matching iOS17 objects;repair unapplied')
if __name__=='__main__':main()

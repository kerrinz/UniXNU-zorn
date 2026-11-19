#!/usr/bin/env python3
"""Execute the selected runtime's actual Mach memory bodies on owned host mappings."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path

def body(path,name):
    text=path.read_text();start=text.index('pub(crate) fn '+name+'(') if name=='read_pages' else text.index('pub(super) fn '+name+'(')
    # Select the existing Mach definition,not the Linux or fallback definition.
    marker='#[cfg(any(target_os = "macos", target_os = "ios"))]'
    section=text.index(marker);start=text.index('pub(',section);opening=text.index('{',start);depth=1;at=opening+1
    while depth:
        depth+=(text[at]=='{')-(text[at]=='}');at+=1
    return text[start:at].replace('#[cfg_attr(target_os = \"ios\", link_name = \"vm_read_overwrite\")]', '#[link_name = \"vm_read_overwrite\"]').replace('#[cfg_attr(target_os = \"ios\", link_name = \"vm_region_64\")]', '#[link_name = \"vm_region_64\"]')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--vendor',type=Path,required=True);p.add_argument('--cargo',type=Path,required=True);p.add_argument('--rustc',type=Path,required=True);p.add_argument('--sdk',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    copied=a.runtime/'crates/metal2vulkan-runtime/src/copied.rs';memory=a.runtime/'crates/metal2vulkan-runtime/src/host_memory.rs'
    source='use std::ptr::NonNull;\nmod actual {use super::NonNull;\n'+body(copied,'read_pages')+'\n'+body(memory,'mapped_writable')+'\n}\nuse actual::{read_pages,mapped_writable};\n'+r'''
#[cfg(test)] mod tests {
 use super::*;
 struct Pages {base:*mut u8,page:usize,live:Vec<bool>}
 impl Pages {
  fn new(count:usize)->Self {unsafe {
   let page=libc::sysconf(libc::_SC_PAGESIZE) as usize;assert!(page.is_power_of_two());
   let base=libc::mmap(std::ptr::null_mut(),page*count,libc::PROT_READ|libc::PROT_WRITE,libc::MAP_ANON|libc::MAP_PRIVATE,-1,0);
   assert_ne!(base,libc::MAP_FAILED);let base=base.cast::<u8>();std::ptr::write_bytes(base,0x5a,page*count);Self{base,page,live:vec![true;count]}
  }}
  fn pointer(&self)->NonNull<u8>{NonNull::new(self.base).unwrap()}
  fn writable(&self)->bool{mapped_writable(self.base as u64,self.base as u64+(self.page*self.live.len()) as u64)}
  fn protect(&self,mode:i32){unsafe{assert_eq!(libc::mprotect(self.base.cast(),self.page,mode),0);}}
  fn unmap(&mut self,n:usize){unsafe{assert_eq!(libc::munmap(self.base.add(n*self.page).cast(),self.page),0);self.live[n]=false;}}
 }
 impl Drop for Pages {fn drop(&mut self){for n in 0..self.live.len(){if self.live[n]{self.unmap(n);}}}}
 #[test] fn owned_read_write(){let p=Pages::new(1);let mut out=vec![0u8;p.page];assert!(read_pages(p.pointer(),&mut out));assert!(out.iter().all(|b|*b==0x5a));assert!(p.writable());}
 #[test] fn read_only_not_writable(){let p=Pages::new(1);p.protect(libc::PROT_READ);let mut out=vec![0u8;p.page];assert!(read_pages(p.pointer(),&mut out));assert!(out.iter().all(|b|*b==0x5a));assert!(!p.writable());}
 #[test] fn inaccessible_returns_failure(){let p=Pages::new(1);p.protect(libc::PROT_NONE);let mut out=vec![0u8;p.page];assert!(!read_pages(p.pointer(),&mut out));assert!(!p.writable());}
 #[test] fn unmapped_gap_returns_failure(){let mut p=Pages::new(3);p.unmap(1);let mut out=vec![0u8;p.page*3];assert!(!read_pages(p.pointer(),&mut out));assert!(!p.writable());}
}
'''
    (a.out/'memory.rs').write_text(source);(a.out/'Cargo.toml').write_text('[package]\nname="zorn279-mach-memory-check"\nversion="0.1.0"\nedition="2024"\n[workspace]\n[lib]\npath="memory.rs"\n[dependencies]\nlibc="0.2"\n');home=a.out/'cargo-home';home.mkdir();(home/'config.toml').write_text('[net]\noffline=true\n[source.crates-io]\nreplace-with="verified"\n[source.verified]\ndirectory='+json.dumps(str(a.vendor.resolve()))+'\n')
    c=a.out/'ios26-mach-abi.c';c.write_text('#include <mach/mach.h>\n#include <mach/vm_map.h>\n#include <mach/vm_region.h>\n_Static_assert(sizeof(vm_map_t)==4,"Mach task port");\n_Static_assert(sizeof(mach_vm_address_t)==8,"Mach address");\n_Static_assert(sizeof(mach_vm_size_t)==8,"Mach size");\n_Static_assert(sizeof(vm_region_basic_info_data_64_t)==36,"Basic info layout");\n_Static_assert(VM_REGION_BASIC_INFO_COUNT_64==9,"Basic info words");\nstatic kern_return_t (*read_fn)(vm_map_read_t,vm_address_t,vm_size_t,vm_address_t,vm_size_t*)=vm_read_overwrite;\nstatic kern_return_t (*region_fn)(vm_map_read_t,vm_address_t*,vm_size_t*,vm_region_flavor_t,vm_region_info_t,mach_msg_type_number_t*,mach_port_t*)=vm_region_64;\n')
    commands=[['xcrun','clang','-std=c11','-Werror','-target','arm64e-apple-ios26.0','-isysroot',str(a.sdk),'-fsyntax-only',str(c)],[str(a.cargo),'test','--offline','--manifest-path',str(a.out/'Cargo.toml'),'--','--test-threads=1']];runs=[];env=dict(os.environ,RUSTC=str(a.rustc),RUSTDOC=str(a.rustc.with_name('rustdoc')),CARGO_HOME=str(home),CARGO_INCREMENTAL='0',RUST_BACKTRACE='0')
    for args in commands:
        result=subprocess.run(args,env=env,capture_output=True,text=True,timeout=120);runs.append(dict(arguments=args,exit=result.returncode,stdout=result.stdout,stderr=result.stderr));(a.out/'command-runs.json').write_text(json.dumps(runs,indent=2)+'\n');assert result.returncode==0,result.stderr
    pin=lambda q:dict(path=str(q.resolve()),sha256=hashlib.sha256(q.read_bytes()).hexdigest());row=dict(passed=True,sources=[pin(copied),pin(memory)],test_tool=pin(Path(__file__)),actual_Mach_function_bodies_executed=True,iOS_public_symbol_binding_selected_in_host_harness=True,host_owned_mapping_tests=True,iOS26_SDK_Mach_ABI_checked=True,runs=runs,phone_access=False,hardware_qualified=False,scope='Host-owned readable/read-only/inaccessible/unmapped ranges;not K80 GPU memory or device acceptance');(a.out/'result.json').write_text(json.dumps(row,indent=2)+'\n');print('PASS279 actual Mach read/permission bodies and iOS26 SDK ABI;no phone')
if __name__=='__main__':main()

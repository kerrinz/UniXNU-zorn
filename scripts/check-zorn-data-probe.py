#!/usr/bin/env python3
"""Fault-check the actual Data vnode probe; mocked APIs do not qualify APFS."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "UniXNU/out/zorn/tree/.cache/xnu-work/bsd/kern/kern_exec.c"
OUT = ROOT / "out/zorn/data-store"
source = SOURCE.read_text()
start = source.index("static int\nnative_owner_data_probe(")
function = source[start:source.index("\n#endif", start)]
prefix = r'''
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#define NULLVP NULL
#define FREAD 1
#define FWRITE 2
#define O_CREAT 4
#define O_EXCL 8
#define O_NOFOLLOW 16
#define UIO_WRITE 1
#define UIO_READ 2
#define UIO_SYSSPACE 0
#define IO_SYNC 1
#define IO_NOCACHE 2
#define IO_UNIT 4
#define MNT_WAIT 1
#define VNODE_LOOKUP_NOFOLLOW 1
typedef void *proc_t;
#ifndef __APPLE__
typedef uintptr_t user_addr_t;
#endif
typedef void *vfs_context_t;
typedef void *mount_t;
typedef void *vnode_t;
struct unlink_args { user_addr_t path; };
static const unsigned char zorn_data_expected_seed[32]={1,2,3};
static int native_owner_data_probe_stage, native_owner_data_probe_status;
static int scenario, attempts, writes, reads, syncs, removed, created, opens, closes;
static char owned_path[96];
static unsigned char contents[64];
static vfs_context_t vfs_context_current(void){return (void *)1;}
static uint64_t mach_absolute_time(void){return 0x1234;}
static mount_t vnode_mount(vnode_t v){return v;}
static int vnode_isdir(vnode_t v){return !!v;}
static int vnode_isreg(vnode_t v){return !!v;}
static void vnode_put(vnode_t v){assert(v);}
static int copyout(const void *src, user_addr_t dst, size_t n){if(scenario==6)return EFAULT;memcpy((void*)dst,src,n);return 0;}
static int vnode_lookup(const char *p,int flags,vnode_t *v,vfs_context_t ctx){
 (void)flags;(void)ctx;
 if(!strcmp(p,"/private/var/tmp")){*v=(void*)1;return 0;}
 assert(created&&!strcmp(p,owned_path));return removed?ENOENT:EIO;
}
static int vnode_open(const char *p,int flags,int mode,int unused,vnode_t *v,vfs_context_t ctx){
 (void)unused;(void)ctx;
 if(flags&O_CREAT){
  assert(flags==(FREAD|FWRITE|O_CREAT|O_EXCL|O_NOFOLLOW)&&mode==0600);
  char expected[96];snprintf(expected,sizeof(expected),"/private/var/tmp/.zorn-data-probe-1234-%d",attempts++);
  assert(!strcmp(p,expected));
  if(scenario==2||(scenario==1&&attempts<4))return EEXIST;
  if(scenario==3)return EIO;
  assert(!created);created=1;strcpy(owned_path,p);
 }else {assert(flags==(FREAD|O_NOFOLLOW)&&!mode&&created&&!strcmp(p,owned_path));}
 *v=(void*)1;++opens;return 0;
}
static void *vfs_context_ucred(vfs_context_t ctx){return ctx;}
static int vn_rdwr(int rw,vnode_t v,caddr_t bytes,int n,int offset,int space,int flags,void *cred,int *residue,proc_t p){
 (void)v;(void)space;(void)cred;(void)p;assert(created&&n==64&&!offset);*residue=0;
 if(rw==UIO_WRITE){assert(flags==(IO_SYNC|IO_NOCACHE|IO_UNIT));++writes;memcpy(contents,bytes,64);}
 else {assert(rw==UIO_READ&&flags==IO_NOCACHE);++reads;memcpy(bytes,contents,64);if(scenario==5)bytes[0]^=1;}
 return 0;
}
static int VNOP_FSYNC(vnode_t v,int wait,vfs_context_t ctx){(void)v;(void)ctx;assert(wait==MNT_WAIT);++syncs;return scenario==4?EIO:0;}
static int vnode_close(vnode_t v,int flags,vfs_context_t ctx){(void)v;(void)flags;(void)ctx;++closes;return 0;}
static int unlink(proc_t p,struct unlink_args *arg,int32_t *result){
 (void)p;(void)result;assert(created&&!strcmp((void*)arg->path,owned_path));++removed;return 0;
}
'''
suffix = r'''
int main(void){
 const int errors[]={0,0,EEXIST,EIO,EIO,EIO,EFAULT};
 for(scenario=0;scenario<7;++scenario){
  unsigned char scratch[1024]={0};
  attempts=writes=reads=syncs=removed=created=opens=closes=0;
  native_owner_data_probe_stage=0;native_owner_data_probe_status=-1;
  int error=native_owner_data_probe(NULL,(uintptr_t)scratch,(void*)1);
  assert(error==errors[scenario]&&native_owner_data_probe_status==error&&opens==closes);
  assert(removed==created);
  if(!error)assert(native_owner_data_probe_stage==7&&writes==1&&reads==1&&syncs==1);
  if(scenario==1)assert(attempts==4);
  if(scenario==2)assert(attempts==8&&!writes&&!removed);
  if(scenario==3||scenario==6)assert(!writes&&!removed);
 }
 puts("PASS: actual probe; bounded collisions preserve old files; fsync/readback failures retained");
}
'''
OUT.mkdir(parents=True, exist_ok=True)
c = OUT / "data-probe-test.c"
c.write_text(prefix + function + suffix)
binary = OUT / "data-probe-test"
subprocess.run(["clang", "-std=c11", "-Wall", "-Wextra", "-Werror", "-O1",
                "-fsanitize=address,undefined", str(c), "-o", str(binary)], check=True, timeout=60)
subprocess.run([str(binary)], check=True, timeout=30)
(OUT / "data-probe-host-check.json").write_text(json.dumps({
    "passed": True, "cases": 7, "apis_mocked": True, "actual_apfs": False,
    "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
    "function_sha256": hashlib.sha256(function.encode()).hexdigest(),
}, indent=2) + "\n")

#!/usr/bin/env python3
"""Compile the actual read-only marker function with fault-injected syscall stubs."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "UniXNU-zorn/native/startup-policy/DataMarker.c"
OUT = ROOT / "out/zorn/data-store"
text = SOURCE.read_text()
function = text[text.index('__attribute__((noinline)) int zorn_boot_data_marker_existing'):text.index('\nint zorn_boot_data_marker(')]
prefix = r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <sys/types.h>
typedef void *proc_t;
#ifndef __APPLE__
typedef int64_t user_ssize_t;
#endif
#define O_RDONLY 0
#define O_NOFOLLOW 0x100
#define O_DIRECTORY 0x100000
#define S_IFDIR 0040000
#define S_IFREG 0100000
#define S_IFMT 0170000
#define S_ISDIR(m) (((m)&S_IFMT)==S_IFDIR)
#define S_ISREG(m) (((m)&S_IFMT)==S_IFREG)
struct stat64 { dev_t st_dev; mode_t st_mode; uid_t st_uid; gid_t st_gid; off_t st_size; };
struct open_args {uint64_t path; int flags; unsigned mode;};
struct close_args {int fd;};
struct fstat64_args {int fd; uint64_t ub;};
struct read_args {int fd; uint64_t cbuf; size_t nbyte;};
volatile unsigned zorn_data_marker_state;
volatile int zorn_data_marker_error;
volatile uint64_t zorn_data_marker_cookie;
const unsigned char zorn_data_expected_seed[32]={0x71,0x23,0x45};
static struct stat64 root,marker;
static unsigned char data[48];
static int mode,allowed,missing,symlink_file,short_read,opened,closed;
static unsigned native_ufs_store_mode(void){return mode;}
static int zorn_ufs_boot_policy_allowed(void){return allowed;}
static int copyout(const void *p,uint64_t dst,size_t n){memcpy((void *)(uintptr_t)dst,p,n);return 0;}
static int copyin(uint64_t src,void *dst,size_t n){memcpy(dst,(void *)(uintptr_t)src,n);return 0;}
static int open(proc_t p,struct open_args *a,int32_t *out){
 (void)p; assert(a->mode==0);
 const char *path=(void *)(uintptr_t)a->path;
 if(!strcmp(path,"/private/var")){assert(a->flags==(O_RDONLY|O_NOFOLLOW|O_DIRECTORY));*out=3;}
 else {assert(!strcmp(path,"/private/var/db/.unixnu-data-retained"));assert(a->flags==(O_RDONLY|O_NOFOLLOW));
  if(missing)return ENOENT;if(symlink_file)return ELOOP;*out=4;}
 ++opened;return 0;
}
static int sys_close(proc_t p,struct close_args *a,int32_t *out){(void)p;(void)out;assert(a->fd==3||a->fd==4);++closed;return 0;}
static int sys_fstat64(proc_t p,struct fstat64_args *a,int32_t *out){(void)p;(void)out;assert(a->fd==3||a->fd==4);return copyout(a->fd==3?&root:&marker,a->ub,sizeof(root));}
static int read(proc_t p,struct read_args *a,user_ssize_t *out){(void)p;assert(a->fd==4&&a->nbyte==48);*out=short_read?47:48;return copyout(data,a->cbuf,*out);}
'''
suffix = r'''
int main(void){
 unsigned char scratch[4096],original[48];unsigned tested=0;
 for(unsigned fault=0;fault<13;++fault){
  mode=2;allowed=1;missing=symlink_file=short_read=opened=closed=0;
  zorn_data_marker_state=zorn_data_marker_error=zorn_data_marker_cookie=0;
  root=(struct stat64){7,S_IFDIR|0755,0,0,0};marker=(struct stat64){7,S_IFREG|0600,0,0,48};
  memcpy(data,"ZRNKEEP1",8);memcpy(data+8,zorn_data_expected_seed,32);uint64_t cookie=0x2c59d71a;memcpy(data+40,&cookie,8);
  switch(fault){case 1:missing=1;break;case 2:data[0]^=1;break;case 3:data[12]^=1;break;
   case 4:memset(data+40,0,8);break;case 5:marker.st_uid=501;break;case 6:marker.st_mode=S_IFREG|0644;break;
   case 7:marker.st_dev=8;break;case 8:short_read=1;break;case 9:symlink_file=1;break;
   case 10:root.st_uid=501;break;case 11:allowed=0;break;case 12:mode=0;break;}
  memcpy(original,data,48);
  int error=zorn_boot_data_marker_existing(0,(uint64_t)(uintptr_t)scratch);
  assert(opened==closed && !memcmp(original,data,48));
  if(!fault){assert(!error&&zorn_data_marker_state==2&&zorn_data_marker_cookie==cookie);}
  else {assert(error&&zorn_data_marker_state==3&&zorn_data_marker_error==error);}
  if(fault==11||fault==12)assert(!opened);
  ++tested;
 }
 assert(tested==13);
}
'''
OUT.mkdir(parents=True, exist_ok=True)
case = OUT / "retained-marker-host.c"
binary = OUT / "retained-marker-host"
case.write_text(prefix + function + suffix)
subprocess.run(["clang", "-std=c11", "-Wall", "-Wextra", "-Werror", str(case), "-o", str(binary)], check=True)
subprocess.run([str(binary)], check=True)
result = dict(passed=True, cases=13, actual_function_sha256=hashlib.sha256(function.encode()).hexdigest(),
              source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              readonly_flags_checked=True, every_open_closed=True, no_content_mutation=True,
              missing_or_invalid_never_falls_back=True, hardware_retention_qualified=False)
(OUT / "retained-marker-host-check.json").write_text(json.dumps(result, indent=2)+"\n")
print(json.dumps(result))

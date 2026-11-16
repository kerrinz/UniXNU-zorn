// SPDX-License-Identifier: MIT
#include "ZornApplicationObservation26.h"
static void zorn26_application_capture_stderr(proc_t process,int fd,user_addr_t buf,
 user_size_t requested,user_ssize_t written,int nativeError,int flags){
 if(!process || fd!=2 || flags || nativeError || written<=0 || (user_size_t)written!=requested)return;
 // Actual kernel process identity; this name filter selects diagnostics only.
 // It never grants IOKit/GPU admission or changes a syscall result.
 const char *name=proc_best_name(process);
 static const char expected[]="zorn-metal-probe193";
 if(!name || strncmp(name,expected,sizeof(expected)))return;
 const uint64_t unique=proc_uniqueid(process);const uint32_t pid=(uint32_t)proc_pid(process);
 if(!zorn26_application_stderr_reserve(unique,pid))return;
 const uint32_t copied=requested<384?(uint32_t)requested:383;
 char text[384];int error=buf>UINT64_MAX-copied?EFAULT:copyin(buf,text,(size_t)copied);
 zorn26_application_stderr_commit(unique,text,copied,error);
}

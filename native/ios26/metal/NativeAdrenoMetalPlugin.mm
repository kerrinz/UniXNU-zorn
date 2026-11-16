// SPDX-License-Identifier: MIT
// K80 application-service discovery candidate. Existing real Metal frontend,
// Rust bridge and Turnip do the work. No test/mailbox/tunnel/diagnostic path.
#import <Foundation/Foundation.h>
#include <IOKit/IOKitLib.h>
#include <dlfcn.h>
#include <initializer_list>
#include <unistd.h>
#include <sys/stat.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "NativeBridgeMetalFrontend.h"
#include "NativeTurnipPolicy.h"
@interface _MTLDevice : NSObject
@end
@interface NativeAdrenoMetalDevice : _MTLDevice
- (id)initWithAcceleratorPort:(unsigned)port;
@end
namespace {
constexpr const char *serviceClass="ZornGen7AppIoService26";
static void trace(unsigned stage,long value=0){
    const int saved=errno;const char *name=getprogname();
    if(name && !strcmp(name,"zorn-metal-probe193")){
        char line[80];const int n=snprintf(line,sizeof(line),"ZORN195PLUG s=%u v=%ld\n",stage,value);
        if(n>0 && size_t(n)<sizeof(line))(void)write(2,line,size_t(n));
    }
    errno=saved;
}

// The selected ash/libloading source uses these same flags and public entry.
// Keep the dependency loaded through the process lifetime, including a refused
// bridge open; no GPU calls or alternate library path are made here.
static void loaderError(unsigned stage,const char *error){
    const int saved=errno;const char *name=getprogname();
    if(name && !strcmp(name,"zorn-metal-probe193")){
        const char *message=error?error:"no dynamic-loader detail";
        const size_t n=strnlen(message,2048);char detail[225]{};
        if(n<=224)memcpy(detail,message,n);
        else {memcpy(detail,message,64);memcpy(detail+64,message+n-160,160);}
        for(size_t i=0;detail[i];++i)if((unsigned char)detail[i]<32 || (unsigned char)detail[i]>126)detail[i]='?';
        char line[288];const int count=snprintf(line,sizeof(line),"ZORN198DL s=%u n=%zu cap=%u cut=%u %s\n",stage,n,n==2048?1u:0u,n>224?1u:0u,detail);
        if(count>0 && size_t(count)<sizeof(line))(void)write(2,line,size_t(count));
    }
    errno=saved;
}
static bool loadDriver(const char *path,void *&retained){
    retained=dlopen(path,RTLD_LAZY|RTLD_LOCAL);
    if(!retained){loaderError(16,dlerror());return false;}
    (void)dlerror();
    void *entry=dlsym(retained,"vkGetInstanceProcAddr");const char *error=dlerror();
    if(!entry || error){loaderError(17,error);return false;}
    trace(18);return true;
}

static bool adjacent(const char *name,char *path,size_t capacity){
    Dl_info info{};
    if(!dladdr(reinterpret_cast<const void *>(&adjacent),&info) || !info.dli_fname)return false;
    const size_t length=strlen(info.dli_fname);if(length>=capacity)return false;
    memcpy(path,info.dli_fname,length+1);char *slash=strrchr(path,'/');if(!slash)return false;
    const size_t room=capacity-size_t(slash+1-path);const int n=snprintf(slash+1,room,"%s",name);
    return n>=0 && size_t(n)<room;
}
static bool listed(){
    // Same explicit clients file beside the existing bundle,no implicit '*'.
    char path[1024];if(!adjacent("../NativeAdrenoMetal.clients",path,sizeof(path))){trace(10);return false;}
    FILE *file=fopen(path,"r");if(!file){trace(11,errno);return false;}
    char data[1024]{};const size_t bytes=fread(data,1,sizeof(data)-1,file);
    const bool complete=!ferror(file) && feof(file);fclose(file);if(!complete){trace(12);return false;}
    data[bytes]=0;const char *process=getprogname();if(!process || !*process){trace(13);return false;}
    char *save=nullptr;
    for(char *word=strtok_r(data," ,\t\r\n",&save);word;word=strtok_r(nullptr," ,\t\r\n",&save))
        if(!strcmp(word,process))return true;
    trace(14);return false;
}
static bool cacheDirectory(char (&path)[1024]){
    // Select a usable directory before any device open;there is one actual
    // bridge/Turnip attempt,not repeated GPU creation against fallback paths.
    for(int which:{_CS_DARWIN_USER_CACHE_DIR,_CS_DARWIN_USER_TEMP_DIR}){
        char base[900]{};const size_t count=confstr(which,base,sizeof(base));
        if(!count || count>sizeof(base) || !base[0]){trace(30+unsigned(which==_CS_DARWIN_USER_TEMP_DIR),errno);continue;}
        const size_t length=strlen(base);const int n=snprintf(path,sizeof(path),"%s%sm2v",base,base[length-1]=='/'?"":"/");
        if(n<0 || size_t(n)>=sizeof(path)){trace(32);continue;}
        if(mkdir(path,0700) && errno!=EEXIST){trace(33,errno);continue;}
        struct stat st{};if(!stat(path,&st) && S_ISDIR(st.st_mode) && !access(path,W_OK))return true;
        trace(34,errno);
    }
    return false;
}
}
@implementation NativeAdrenoMetalDevice
- (id)initWithAcceleratorPort:(unsigned)port {
    trace(1,long(port));
    self=[super init];if(!self || !port || !listed()){trace(2);return nil;}
    // The actual discovery port is independently checked and held while
    // obtaining its real epoch-scoped registry ID. No supplied/fake handle.
    if(IOObjectRetain(port)!=KERN_SUCCESS){trace(3);return nil;}
    uint64_t registry=0;const bool valid=IOObjectConformsTo(port,serviceClass) &&
        IORegistryEntryGetRegistryEntryID(port,&registry)==KERN_SUCCESS && registry;
    IOObjectRelease(port);if(!valid){trace(4);return nil;}
    static bool tried=false;static uint64_t openedRegistry=0;static id device=nil;static void *driverLibrary=nullptr;
    @synchronized([NativeAdrenoMetalDevice class]) {
        if(tried){trace(5);return registry==openedRegistry?device:nil;}
        char driver[1024]{},cache[1024]{};
        if(!adjacent("libvulkan_freedreno.dylib",driver,sizeof(driver)) || access(driver,R_OK) || !cacheDirectory(cache)){trace(6,errno);return nil;}
        char identifier[32]{};const int count=snprintf(identifier,sizeof(identifier),"0x%llx",(unsigned long long)registry);
        if(count<0 || size_t(count)>=sizeof(identifier)){trace(7);return nil;}
        tried=true;openedRegistry=registry;
        // Per-process actual service+ID selection. Normal XNU MACF/filter and
        // app authority still govern IOServiceOpen and every method. A refused
        // selector is never tunnelled or transported via a mailbox fallback.
        if(setenv("TU_DARWIN_SERVICE",serviceClass,1) || setenv("TU_DARWIN_OPEN_TYPE","0x4147",1) ||
           setenv("TU_DARWIN_REGISTRY_ID",identifier,1)){trace(8,errno);return nil;}
        // Preserve the existing software render policy of this exact stack;
        // no new GMEM qualification or concurrent-binning mode is claimed.
        houji_turnip::configure();
        if(!loadDriver(driver,driverLibrary))return nil;
        trace(9);device=native_bridge_metal_open(driver,cache,registry,nullptr);trace(15,device?1:0);
        return device;
    }
}
@end

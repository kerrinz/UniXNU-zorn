// SPDX-License-Identifier: MIT
// Ordinary Metal API qualification; no private frontend entry points or fabricated completion.
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <IOSurface/IOSurfaceRef.h>
#import <CoreVideo/CVPixelBuffer.h>
#include "ZornSurfaceProbe224.h"
#include <IOKit/IOKitLib.h>
#include <dispatch/dispatch.h>
#include <mach/mach_time.h>
#include <unistd.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <errno.h>
#include <stdlib.h>
static constexpr char tag[]="65f3efb4a587473a9caebe54d7a99aea";
static uint32_t stages,actualCRC,firstBad=UINT32_MAX;
static uint64_t serviceID,deviceID;
static uint32_t crc32(const uint8_t *p,size_t n){uint32_t c=~0u;for(size_t i=0;i<n;i++){c^=p[i];for(unsigned j=0;j<8;j++)c=(c>>1)^((0u-(c&1u))&0xedb88320u);}return ~c;}
static void report(unsigned phase,long status,long code=0){
 char line[384];int n=snprintf(line,sizeof(line),"ZORN193MTL run=%s phase=%u flags=%x status=%ld code=%ld service=%llx device=%llx crc=%08x bad=%08x ticks=%llu\n",tag,phase,stages,status,code,(unsigned long long)serviceID,(unsigned long long)deviceID,actualCRC,firstBad,(unsigned long long)mach_absolute_time());
 if(n>0 && (size_t)n<sizeof(line)){ssize_t count;do {count=write(2,line,(size_t)n);}while(count<0 && errno==EINTR);}
}
static void errorReport(NSError *error){
 if(!error)return;
 char detail[160];snprintf(detail,sizeof(detail),"%s:%ld %s",error.domain.UTF8String,(long)error.code,error.localizedDescription.UTF8String);
 for(size_t i=0;detail[i];i++)if((unsigned char)detail[i]<32 || (unsigned char)detail[i]>126)detail[i]='?';
 char line[384];int n=snprintf(line,sizeof(line),"ZORN193MTL run=%s error=%s\n",tag,detail);if(n>0 && (size_t)n<sizeof(line))(void)write(2,line,(size_t)n);
}
[[noreturn]] static void retainUntilWatchdog(){for(;;)sleep(1);}
static void deviceBoundary229(unsigned stage){
 const int saved=errno;
 char line[96];int n=snprintf(line,sizeof(line),"ZORN229DEV run=%s stage=%u\n",tag,stage);
 // One best-effort bounded write. No wait,retry,load,handle substitution or errno change.
 if(n>0 && (size_t)n<sizeof(line))(void)write(2,line,(size_t)n);
 errno=saved;
}
static void pipelineMarker215(unsigned stage){
 char line[96];int n=snprintf(line,sizeof(line),"ZORN215PIPE run=%s stage=%u\n",tag,stage);
 // One bounded diagnostic write; never retry or claim delivery on failure.
 if(n>0 && (size_t)n<sizeof(line))(void)write(2,line,(size_t)n);
}
struct ZornOwnedSurface224 {
 IOSurfaceRef value=nullptr;
 ~ZornOwnedSurface224(){if(value)CFRelease(value);}
};
static bool accessSurface224(IOSurfaceRef surface,uint8_t *out){
 return zornSurface224Access(IOSurfaceGetBaseAddress(surface),IOSurfaceGetWidth(surface),IOSurfaceGetHeight(surface),
  IOSurfaceGetBytesPerRow(surface),IOSurfaceGetAllocSize(surface),IOSurfaceGetPlaneCount(surface),(size_t)getpagesize(),out);
}
static int probe(){
 report(1,0);
 io_service_t service=IO_OBJECT_NULL;
 // This lookup only waits for publication. Metal performs its own normal discovery/open.
 for(unsigned second=0;second<240 && service==IO_OBJECT_NULL;second++){
  service=IOServiceGetMatchingService(kIOMainPortDefault,IOServiceMatching("ZornGen7AppIoService26"));
  if(service==IO_OBJECT_NULL)sleep(1);
 }
 if(service==IO_OBJECT_NULL){report(2,-1,1);return 2;}
 CFTypeRef pluginName=IORegistryEntryCreateCFProperty(service,CFSTR("MetalPluginName"),kCFAllocatorDefault,0);
 CFTypeRef pluginClass=IORegistryEntryCreateCFProperty(service,CFSTR("MetalPluginClassName"),kCFAllocatorDefault,0);
 const bool nameOK=pluginName && CFEqual(pluginName,CFSTR("NativeAdrenoMetal"));
 const bool classOK=pluginClass && CFEqual(pluginClass,CFSTR("NativeAdrenoMetalDevice"));
 fprintf(stderr,"ZORN195DISC es=%u name=%u class=%u\n",IOObjectConformsTo(service,"IOAcceleratorES")?1u:0u,nameOK?1u:0u,classOK?1u:0u);
 if(pluginName)CFRelease(pluginName);if(pluginClass)CFRelease(pluginClass);
 kern_return_t kr=IORegistryEntryGetRegistryEntryID(service,&serviceID);IOObjectRelease(service);
 if(kr!=KERN_SUCCESS || !serviceID){report(2,-1,kr);return 2;}
 stages|=1;report(2,0);
 deviceBoundary229(1);
 // Existing frontend diagnostic switch, local to this ordinary process.
 if(setenv("NMB_LOG_STDERR","1",1)){report(3,-1,3);return 3;}
 deviceBoundary229(2);
 id<MTLDevice> device=MTLCreateSystemDefaultDevice();
 deviceBoundary229(3);
 if(!device){
  // Diagnose Foundation loading only after normal Metal discovery has failed.
  // Never instantiate the principal or call the bridge/Turnip as a fallback.
  NSBundle *bundle=[NSBundle bundleWithPath:@"/System/Library/Extensions/NativeAdrenoMetal.bundle"];
  NSError *loadError=nil;const bool loaded=bundle && [bundle loadAndReturnError:&loadError];
  fprintf(stderr,"ZORN195DISC bundle=%u load=%u principal=%u code=%ld\n",bundle?1u:0u,loaded?1u:0u,(loaded && [bundle principalClass])?1u:0u,(long)loadError.code);
  if(loadError){char why[160];snprintf(why,sizeof(why),"%s",loadError.localizedDescription.UTF8String);
   for(size_t i=0;why[i];++i)if((unsigned char)why[i]<32 || (unsigned char)why[i]>126)why[i]='?';
   fprintf(stderr,"ZORN195DISC why=%s\n",why);}
  report(3,-1,1);return 3;
 }
 deviceID=device.registryID;
 if(deviceID!=serviceID){report(3,-1,2);return 3;}
 stages|=2;report(3,0);
 NSError *error=nil;
 id<MTLLibrary> library=[device newLibraryWithURL:[NSURL fileURLWithPath:@"/redwood/sbin/zorn-metal-probe193.metallib"] error:&error];
 if(!library){errorReport(error);report(4,-1,error.code);return 4;}
 id<MTLFunction> vertex=[library newFunctionWithName:@"zorn193_vertex"];
 id<MTLFunction> fragment=[library newFunctionWithName:@"zorn193_fragment"];
 if(!vertex || !fragment){report(4,-1,2);return 4;}
 stages|=4;report(4,0);
 pipelineMarker215(1);
 MTLRenderPipelineDescriptor *pipelineDesc=[MTLRenderPipelineDescriptor new];
 pipelineDesc.vertexFunction=vertex;pipelineDesc.fragmentFunction=fragment;
 pipelineDesc.colorAttachments[0].pixelFormat=MTLPixelFormatRGBA8Unorm;
 pipelineMarker215(2);
 pipelineMarker215(3);
 error=nil;id<MTLRenderPipelineState> pipeline=[device newRenderPipelineStateWithDescriptor:pipelineDesc error:&error];
 pipelineMarker215(4);
 if(!pipeline){errorReport(error);report(5,-1,error.code);return 5;}
 stages|=8;report(5,0);
 MTLTextureDescriptor *textureDesc=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm width:32 height:32 mipmapped:NO];
 textureDesc.storageMode=MTLStorageModeShared;textureDesc.usage=MTLTextureUsageRenderTarget;
 // Real IOSurface allocation and task mapping; no private frontend entry.
 ZornOwnedSurface224 surface;
 NSDictionary *surfaceProperties=@{(__bridge NSString *)kIOSurfaceWidth:@32,(__bridge NSString *)kIOSurfaceHeight:@32,
  (__bridge NSString *)kIOSurfaceBytesPerElement:@4,(__bridge NSString *)kIOSurfaceBytesPerRow:@128,
  (__bridge NSString *)kIOSurfacePixelFormat:@(kCVPixelFormatType_32RGBA)};
 surface.value=IOSurfaceCreate((__bridge CFDictionaryRef)surfaceProperties);
 if(!surface.value){report(6,-1,3);return 6;}
 uint32_t surfaceSeed=0;
 auto surfaceRaw=IOSurfaceLock(surface.value,0,&surfaceSeed);
 if(surfaceRaw){report(6,-1,(long)surfaceRaw);return 6;}
 const bool poisoned=accessSurface224(surface.value,nullptr);
 surfaceRaw=IOSurfaceUnlock(surface.value,0,&surfaceSeed);
 if(!poisoned || surfaceRaw){report(6,-1,surfaceRaw?(long)surfaceRaw:4);return 6;}
 id<MTLTexture> texture=[device newTextureWithDescriptor:textureDesc iosurface:surface.value plane:0];
 if(!texture || !texture.iosurface || IOSurfaceGetID(texture.iosurface)!=IOSurfaceGetID(surface.value) || texture.iosurfacePlane!=0){report(6,-1,5);return 6;}
 id<MTLCommandQueue> queue=[device newCommandQueue];
 id<MTLCommandBuffer> command=[queue commandBuffer];
 if(!texture || !queue || !command){report(6,-1,1);return 6;}
 stages|=16;report(6,0);
 MTLRenderPassDescriptor *pass=[MTLRenderPassDescriptor renderPassDescriptor];
 pass.colorAttachments[0].texture=texture;pass.colorAttachments[0].loadAction=MTLLoadActionClear;
 pass.colorAttachments[0].storeAction=MTLStoreActionStore;pass.colorAttachments[0].clearColor=MTLClearColorMake(0,0,0,0);
 id<MTLRenderCommandEncoder> encoder=[command renderCommandEncoderWithDescriptor:pass];
 if(!encoder){report(7,-1,1);return 7;}
 [encoder setRenderPipelineState:pipeline];[encoder setCullMode:MTLCullModeNone];
 [encoder setViewport:(MTLViewport){0,0,32,32,0,1}];
 [encoder drawPrimitives:MTLPrimitiveTypeTriangle vertexStart:0 vertexCount:3];[encoder endEncoding];
 stages|=32;report(7,(long)command.status);
 dispatch_semaphore_t completed=dispatch_semaphore_create(0);
 [command addCompletedHandler:^(id<MTLCommandBuffer> finished){(void)finished;dispatch_semaphore_signal(completed);}];
 stages|=64;report(8,(long)command.status);[command commit];
 const long wait=dispatch_semaphore_wait(completed,dispatch_time(DISPATCH_TIME_NOW,30LL*NSEC_PER_SEC));
 const MTLCommandBufferStatus status=command.status;
 if(wait || status!=MTLCommandBufferStatusCompleted){errorReport(command.error);report(9,(long)status,wait?1:2);retainUntilWatchdog();}
 stages|=128;report(9,(long)status);
 uint8_t pixels[32*32*4],texturePixels[32*32*4];memset(pixels,0x5a,sizeof(pixels));memset(texturePixels,0xa5,sizeof(texturePixels));
 [texture getBytes:texturePixels bytesPerRow:32*4 fromRegion:MTLRegionMake2D(0,0,32,32) mipmapLevel:0];
 // GPU completion was established above. Read the shared surface itself,
 // under the public CPU-access boundary, independently of Metal getBytes.
 surfaceRaw=IOSurfaceLock(surface.value,kIOSurfaceLockReadOnly,&surfaceSeed);
 if(surfaceRaw){report(10,(long)status,(long)surfaceRaw);return 10;}
 const bool copied=accessSurface224(surface.value,pixels);
 surfaceRaw=IOSurfaceUnlock(surface.value,kIOSurfaceLockReadOnly,&surfaceSeed);
 if(!copied || surfaceRaw){report(10,(long)status,surfaceRaw?(long)surfaceRaw:6);return 10;}
 if(memcmp(pixels,texturePixels,sizeof(pixels))){report(10,(long)status,7);return 10;}
 actualCRC=crc32(pixels,sizeof(pixels));
 for(unsigned y=0;y<32;y++)for(unsigned x=0;x<32;x++){
  const bool odd=((x/8+y/8)%2)!=0;
  const uint8_t expected[4]={(uint8_t)(odd?255:0),(uint8_t)(odd?0:255),(uint8_t)(odd?255:0),255};
  for(unsigned c=0;c<4;c++){unsigned i=(y*32+x)*4+c;if(pixels[i]!=expected[c] && firstBad==UINT32_MAX)firstBad=i;}
 }
 if(firstBad!=UINT32_MAX){report(10,(long)status,1);return 10;}
 stages|=256;report(10,(long)status);
 // Completion is established before releasing GPU resources. Process teardown is observed separately in kernel logs.
 encoder=nil;command=nil;pass=nil;texture=nil;queue=nil;pipeline=nil;pipelineDesc=nil;
 vertex=nil;fragment=nil;library=nil;device=nil;
 CFRelease(surface.value);surface.value=nullptr;
 stages|=512;report(11,(long)status);return 0;
}
int main(){@autoreleasepool {return probe();}}

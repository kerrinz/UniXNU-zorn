#include "ZornGpuOwnedRuntime.h"
#include "ZornGpuMemoryWire.h"
extern "C" int zorn_gpu_memory_profile_ready(void);
extern "C" {
extern const uint8_t zorn_gpu_mem_gmu[],zorn_gpu_mem_sqe[],zorn_gpu_mem_aqe[],zorn_gpu_mem_zap[];
extern const uint64_t zorn_gpu_mem_gmu_size,zorn_gpu_mem_sqe_size,zorn_gpu_mem_aqe_size,zorn_gpu_mem_zap_size;
}
static constinit ZornGpuOwnedMemory gpuMemory;
static ZornGpuMemoryReport gpuCapture;
static unsigned gpuConfigured,gpuEnabled,gpuTried,gpuReady;
static IOReturn gpuGate(void *,uint64_t epoch,const ZornGpuOwnedMemory *owner,unsigned,unsigned){
 return epoch==1 && owner==&gpuMemory && zorn_gpu_memory_profile_ready()?kIOReturnSuccess:kIOReturnNotReady;
}
extern "C" void zorn_gpu_owned_configure(unsigned enabled){
 unsigned zero=0;if(!__atomic_compare_exchange_n(&gpuConfigured,&zero,1u,false,__ATOMIC_ACQUIRE,__ATOMIC_RELAXED))return;
 gpuEnabled=enabled==1;__atomic_store_n(&gpuConfigured,2u,__ATOMIC_RELEASE);
}
extern "C" void zorn_gpu_owned_gui_tick(void){
 if(__atomic_load_n(&gpuConfigured,__ATOMIC_ACQUIRE)!=2 || !gpuEnabled)return;
 unsigned zero=0;if(!__atomic_compare_exchange_n(&gpuTried,&zero,1u,false,__ATOMIC_ACQUIRE,__ATOMIC_RELAXED))return;
 const ZornGpuBlob blobs[4]={{zorn_gpu_mem_gmu,size_t(zorn_gpu_mem_gmu_size)},
  {zorn_gpu_mem_sqe,size_t(zorn_gpu_mem_sqe_size)},{zorn_gpu_mem_aqe,size_t(zorn_gpu_mem_aqe_size)},
  {zorn_gpu_mem_zap,size_t(zorn_gpu_mem_zap_size)}};
 const ZornGpuPrepareGate gate{1,nullptr,gpuGate};
 (void)gpuMemory.prepare(blobs,40,&gate);
 gpuCapture=gpuMemory.report();__atomic_store_n(&gpuReady,1u,__ATOMIC_RELEASE);
}
extern "C" const void *zorn_gpu_owned_transport(const void *canonical,size_t bytes,uint8_t *wire){
 if(__atomic_load_n(&gpuConfigured,__ATOMIC_ACQUIRE)!=2 || !gpuEnabled ||
    __atomic_load_n(&gpuReady,__ATOMIC_ACQUIRE)!=1 || bytes!=4096)return canonical;
 return ZornGpuMemoryWire::encode(static_cast<const uint8_t *>(canonical),gpuCapture,wire)?wire:canonical;
}

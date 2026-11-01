#include "ZornGpuOwnedRuntime.h"
void zorn_gpu_owned_configure(unsigned enabled){(void)enabled;}
void zorn_gpu_owned_gui_tick(void){}
const void *zorn_gpu_owned_transport(const void *canonical,size_t bytes,uint8_t *wire){(void)bytes;(void)wire;return canonical;}

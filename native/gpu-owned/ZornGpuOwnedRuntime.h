#ifndef ZORN_GPU_OWNED_RUNTIME_H
#define ZORN_GPU_OWNED_RUNTIME_H
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
void zorn_gpu_owned_configure(unsigned enabled);
void zorn_gpu_owned_gui_tick(void);
const void *zorn_gpu_owned_transport(const void *canonical,size_t bytes,uint8_t *wire);
#ifdef __cplusplus
}
#endif
#endif

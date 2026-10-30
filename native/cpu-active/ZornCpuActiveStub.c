#include "ZornCpuActive.h"
void zorn_cpu_active_configure(int enabled,uint64_t epoch){(void)enabled;(void)epoch;}
void zorn_cpu_active_gui_tick(void){}
void zorn_cpu_active_gui_finish(void){}
const void *zorn_cpu_active_transport(const void *p,size_t n,uint8_t *wire,uint8_t *scratch){(void)n;(void)wire;(void)scratch;return p;}

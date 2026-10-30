// Isolated explicit ZCLA/2 error-preserving extension. No production integration.
#ifndef ZORN_ACTIVE_V2_CODEC_H
#define ZORN_ACTIVE_V2_CODEC_H
#include "two-sweep.h"
enum { ZORN_CODEC_OK=0, ZORN_CODEC_INCOMPATIBLE=1,
       ZORN_CODEC_INVALID=2, ZORN_CODEC_CORRUPT=3 };
// Input block/capture and exactly4096B caller-owned scratch must be stable,
// exclusive and disjoint. Failure preserves input and capture; scratch may change.
int zorn_active_v2_encode(uint8_t *,size_t,const struct ZornSweepCapture *,uint8_t *,size_t);
int zorn_active_v2_decode(uint8_t *,size_t,struct ZornSweepCapture *,uint8_t *,size_t);
#endif

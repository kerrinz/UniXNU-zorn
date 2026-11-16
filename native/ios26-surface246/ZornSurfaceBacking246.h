/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#pragma once
#include <stdint.h>
struct ZornSurfaceBacking246 {
    void *cookie;uint64_t bytes;
    bool (*segment)(void *,uint64_t,uint64_t *,uint64_t *);
};
enum : unsigned {ZornSurfaceNone246=0,ZornSurfaceMatched246=1,ZornSurfaceInvalid246=2,
    ZornSurfaceAmbiguous246=3,ZornSurfaceUnavailable246=4};
// Compare complete extents,independent of CPU/GPU page sizes or segment splits.
// Only physical metadata is inspected;no device access or pixel reads.
inline bool ZornSurfaceSameBacking246(const ZornSurfaceBacking246 &a,
    const ZornSurfaceBacking246 &b,unsigned &budget) {
    if(!a.segment || !b.segment || !a.bytes || a.bytes!=b.bytes)return false;
    uint64_t at=0;
    while(at<a.bytes) {
        if(!budget)return false;--budget;
        uint64_t ap=0,an=0,bp=0,bn=0;
        if(!a.segment(a.cookie,at,&ap,&an) || !b.segment(b.cookie,at,&bp,&bn) ||
           !ap || !bp || !an || !bn || ap!=bp)return false;
        const uint64_t left=a.bytes-at;
        uint64_t n=an<bn?an:bn;if(n>left)n=left;
        if(n>UINT64_MAX-ap || n>UINT64_MAX-bp)return false;
        at+=n;
    }
    return true;
}
extern "C" void *zorn_surface_copy_backing246(const ZornSurfaceBacking246 &,unsigned *);
extern "C" void zorn_surface_drop246(void *);
extern "C" void zorn_surface_completed246(void *,uint32_t);
extern "C" uint32_t zorn_surface_fence246(uint32_t);

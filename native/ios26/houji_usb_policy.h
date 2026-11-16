/* Offline candidate: pure predicates, no MMIO, allocation or storage access. */
#ifndef HOUJI_USB_POLICY_H
#define HOUJI_USB_POLICY_H
#ifdef HOUJI_HOST_TEST
#include <stdint.h>
#else
#include <sys/types.h>
#endif

static inline int huc_token(const char *s, unsigned n, const char *wanted)
{
    if (!s || !n || s[n-1]) return 0;
    unsigned start=0;
    while (start<n) {
        unsigned end=start, i=0;
        while (end<n && s[end]) end++;
        if (end==n) return 0;
        while (wanted[i] && i<end-start && wanted[i]==s[start+i]) i++;
        if (!wanted[i] && i==end-start) return 1;
        start=end+1;
    }
    return 0;
}

static inline int huc_board(const char *compatible, unsigned n,
                            const char *target, unsigned target_n)
{
    return target_n==6 && huc_token(target,target_n,"houji") &&
           huc_token(compatible,n,"xiaomi,houji") &&
           huc_token(compatible,n,"qcom,sm8650");
}

/* Called only for kmem_alloc_contig-owned memory, not arbitrary RAM addresses. */
static inline int huc_dma(uint64_t pa, unsigned size, unsigned bits,
                          uint64_t base, uint64_t bytes)
{
    uint64_t max=~(uint64_t)0;
    if (size!=0x20000 || (pa&0x3fff) || bits<36 || bits>64 ||
        !bytes || bytes-1>max-base || pa<base || bytes<size ||
        pa-base>bytes-size || size-1>max-pa) return 0;
    return bits==64 || pa+size-1<(1ULL<<bits);
}

static inline int huc_layout(uint32_t id0,uint32_t id1,uint32_t id2)
{
    return id0==0x4c017e6b && id1==0x60000047 && id2==0x5111;
}

static inline int huc_route(uint32_t s2cr,uint32_t cbar,uint32_t sctlr,uint32_t cba2r)
{
    unsigned type=(s2cr>>16)&3;
    return type==1 || (type==0 && (s2cr&255)<71 &&
           ((cbar>>16)&3)==1 && !(sctlr&1) && (cba2r&1));
}
#endif

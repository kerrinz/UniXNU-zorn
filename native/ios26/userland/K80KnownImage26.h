// SPDX-License-Identifier: MIT
#pragma once
#include "GpuKnownImage2d.h"
// Exact source relocation sites only. These are references INSIDE this one
// actually allocated/mapped BO,not chosen physical addresses or K80 geometry.
// No shader/user packet input or host-rendered GPU output is accepted.
static_assert(HGKI_PROGRESS==0 && HGKI_SELECTED_COMMAND_WORDS==247);
struct K80KnownImageRelocation26 {unsigned byteOffset;uint32_t original,relative;};
static const K80KnownImageRelocation26 k80KnownImageRelocations26[]={
    {8684u,0x62081000u,0x1000u},
    {8696u,0x62081000u,0x1000u},
    {12780u,0x62081000u,0x1000u},
    {12792u,0x62081000u,0x1000u},
    {16932u,0x62081000u,0x1000u},
    {16944u,0x62081000u,0x1000u},
    {17136u,0x62082000u,0x2000u},
    {17160u,0x62083000u,0x3000u},
    {17304u,0x62085000u,0x5000u},
};
static inline uint32_t k80KnownImageSourceWord26(unsigned offset)
{
    uint32_t v=0;for(unsigned i=0;i<4;++i)v|=uint32_t(hgki_initial_byte(offset+i))<<(8*i);return v;
}
static inline bool k80KnownImageLayout26(uint64_t actualIova)
{
    if((actualIova&4095u) || actualIova>UINT32_MAX-32767u)return false;
    for(const auto &r:k80KnownImageRelocations26)
        if(k80KnownImageSourceWord26(r.byteOffset)!=r.original || k80KnownImageSourceWord26(r.byteOffset+4))return false;
    return true;
}
static inline uint8_t k80KnownImageByte26(uint64_t actualIova,unsigned offset)
{
    for(const auto &r:k80KnownImageRelocations26)if(offset>=r.byteOffset && offset-r.byteOffset<4)
        return uint8_t(uint32_t(actualIova+r.relative)>>(8*(offset-r.byteOffset)));
    return offset<HGKI_BYTES?hgki_initial_byte(offset):0x5a;
}
static inline bool k80KnownImageBuild26(void *actualCpu,size_t bytes,uint64_t actualIova)
{
    if(!actualCpu || bytes!=32768 || !k80KnownImageLayout26(actualIova))return false;
    auto *p=static_cast<uint8_t *>(actualCpu);for(unsigned i=0;i<bytes;++i)p[i]=k80KnownImageByte26(actualIova,i);return true;
}
static inline bool k80KnownImageVerify26(const void *actualCpu,size_t bytes,uint64_t actualIova,hgki_result &result)
{
    if(!actualCpu || bytes!=32768 || !k80KnownImageLayout26(actualIova))return false;
    const auto *p=static_cast<const volatile uint8_t *>(actualCpu);result.verified=0;result.first_bad=UINT32_MAX;
    for(unsigned i=0;i<bytes;++i){
        const bool image=i>=5*4096 && i<6*4096;
        const uint8_t expected=image?(((i&3)==0 || (i&3)==3)?255:0):k80KnownImageByte26(actualIova,i);
        if(p[i]!=expected){result.first_bad=i;result.expected=expected;result.actual=p[i];return false;}
    }
    result.output_crc=hgki_crc32(static_cast<const uint8_t *>(actualCpu)+5*4096,4096);
    if(result.output_crc!=0xe843b26au)return false;result.verified=1;return true;
}

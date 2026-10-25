// SPDX-License-Identifier: BSD-2-Clause-Patent
static uint32_t houjiLe32(const uint8_t *p) {return uint32_t(p[0])|(uint32_t(p[1])<<8)|(uint32_t(p[2])<<16)|(uint32_t(p[3])<<24);}
static uint64_t houjiLe64(const uint8_t *p) {return uint64_t(houjiLe32(p))|(uint64_t(houjiLe32(p+4))<<32);}
static uint32_t houjiCrc32(const uint8_t *p, unsigned n, bool header=false) {
  uint32_t crc=0xFFFFFFFFU;
  for(unsigned i=0;i<n;i++) {
    crc^=(header && i>=16 && i<20)?0:p[i];
    for(unsigned b=0;b<8;b++) crc=(crc>>1)^(0xEDB88320U&(0U-(crc&1U)));
  }
  return ~crc;
}
static const char *houjiGptError(const uint8_t *h,unsigned hn,const uint8_t *e,unsigned en) {
  if(!h||!e||hn!=4096||en!=8192)return "GPT buffer size";
  static const uint8_t magic[8]={'E','F','I',' ','P','A','R','T'};
  static const uint8_t disk[16]={0x4d,0x48,0xd1,0xe7,0x8a,0xc5,0x30,0xaa,0x98,0xc1,0xb1,0x10,0xb4,0xbc,0x5e,0xc4};
  for(unsigned i=0;i<8;i++)if(h[i]!=magic[i])return "GPT signature";
  for(unsigned i=0;i<16;i++)if(h[56+i]!=disk[i])return "GPT disk GUID differs";
  if(houjiLe32(h+8)!=0x10000||houjiLe32(h+12)!=92||houjiLe32(h+20)||houjiLe64(h+24)!=1||
     houjiLe64(h+32)!=0x7AABFFF||houjiLe64(h+72)!=2||houjiLe32(h+80)!=64||houjiLe32(h+84)!=128)return "GPT geometry differs";
  if(houjiLe32(h+16)!=0x631FC7EA||houjiCrc32(h,92,true)!=0x631FC7EA)return "GPT header CRC differs";
  if(houjiLe32(h+88)!=0x9F1BB496||houjiCrc32(e,8192)!=0x9F1BB496)return "GPT entry array CRC differs";
  return nullptr;
}

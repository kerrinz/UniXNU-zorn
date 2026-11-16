// SPDX-License-Identifier: MIT
#pragma once
#include <stddef.h>
#include <stdint.h>
#include <string.h>
// Only the active32x32RGBA region is touched; padding and other planes are not.
static bool zornSurface224Valid(size_t width,size_t height,size_t row,size_t allocation,size_t planes,uintptr_t base,size_t page){
 return width==32 && height==32 && planes==0 && page && !(page&(page-1)) &&
  base && !(base&(page-1)) && base<=UINTPTR_MAX-allocation && row>=128 && row<=(SIZE_MAX-128)/31 &&
  allocation>=31*row+128 && allocation<=SIZE_MAX-(page-1);
}
static bool zornSurface224Access(void *base,size_t width,size_t height,size_t row,size_t allocation,size_t planes,size_t page,uint8_t *out){
 if(!zornSurface224Valid(width,height,row,allocation,planes,reinterpret_cast<uintptr_t>(base),page))return false;
 for(size_t y=0;y<32;++y){auto *line=static_cast<uint8_t *>(base)+y*row;
  if(out)memcpy(out+y*128,line,128);else memset(line,0x5a,128);
 }
 return true;
}

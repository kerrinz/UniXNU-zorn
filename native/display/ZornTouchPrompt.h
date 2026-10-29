// SPDX-License-Identifier: BSD-2-Clause-Patent
// Explicit mapped GOP cue for the short probe; independent of log-only tracing.
#pragma once
static bool zornTouchPrompt() {
    PE_Video video={};if(!videoValid(video))return false;
    const size_t bytes=video.v_rowBytes*video.v_height;
    IODeviceMemory *memory=IODeviceMemory::withRange(video.v_baseAddr,bytes);
    IOMemoryMap *map=memory?memory->map(kIOMapAnywhere|kIOMapInhibitCache):nullptr;
    bool ok=map && map->getPhysicalAddress()==video.v_baseAddr && map->getLength()==bytes;
    if(ok) {
        uintptr_t base=map->getVirtualAddress();
        const uint8_t letters[8][7]={
            {31,4,4,4,4,4,4},{14,17,17,17,17,17,14},{17,17,17,17,17,17,14},
            {15,16,16,16,16,16,15},{17,17,17,31,17,17,17},{17,25,25,21,19,19,17},
            {17,17,17,21,21,21,10},{0,0,0,0,0,0,0}};
        const unsigned text[9]={0,1,2,3,4,7,5,1,6}; // TOUCH NOW
        for(unsigned y=880;y<1000;++y)for(unsigned x=0;x<1440;++x)
            reinterpret_cast<volatile uint32_t *>(base+y*5760)[x]=0xff000000;
        for(unsigned i=0;i<9;++i)for(unsigned y=0;y<7;++y)for(unsigned x=0;x<5;++x)
            if(letters[text[i]][y]&(1u<<(4-x)))for(unsigned dy=0;dy<10;++dy)for(unsigned dx=0;dx<10;++dx)
                reinterpret_cast<volatile uint32_t *>(base+(900+y*10+dy)*5760)[40+i*60+x*10+dx]=0xffffffff;
        uint64_t ctr=0;__asm__ volatile("mrs %0,ctr_el0":"=r"(ctr));
        uintptr_t line=4u<<((ctr>>16)&15);
        for(uintptr_t at=(base+880*5760)&~(line-1);at<base+1000*5760;at+=line)
            __asm__ volatile("dc cvac,%0"::"r"(at):"memory");
        __asm__ volatile("dsb sy":::"memory");
    }
    OSSafeReleaseNULL(map);OSSafeReleaseNULL(memory);return ok;
}

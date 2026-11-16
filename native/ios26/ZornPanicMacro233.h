// SPDX-License-Identifier: MIT
#pragma once
#include "ZornPanicFormat232.h"
// Exact public panic_call.h suffix only. Never inspect file/line arguments.
static inline unsigned zorn_panic_format_lookup233(const char *format){
    if(!format)return ZornPanicFormatUnknown232;
    unsigned found=0;
    for(unsigned index=0;index<sizeof(zornPanicFormats232)/sizeof(zornPanicFormats232[0]);++index){
        const ZornPanicFormatEntry232 *entry=&zornPanicFormats232[index];unsigned n=0;
        for(;n<entry->length;++n)if((unsigned char)format[n]!=(unsigned char)entry->text[n])break;
        if(n!=entry->length)continue;
        const char *tail=format+n;bool match=tail[0]==0;
        if(!match){
            static const char suffix[]=" @%s:%d";unsigned k=0;
            for(;k<sizeof(suffix);++k)if(tail[k]!=suffix[k])break;
            match=k==sizeof(suffix);
        }
        if(match){
            const unsigned actual=index+1;
            if(found && found!=actual)return ZornPanicFormatUnknown232;
            found=actual;
        }
    }
    return found?found:ZornPanicFormatUnknown232;
}

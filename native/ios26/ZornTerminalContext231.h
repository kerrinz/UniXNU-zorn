// SPDX-License-Identifier: MIT
#pragma once
#include <stdint.h>
#include <stdbool.h>
// Source-defined categories only. Never parse numeric values,addresses or stacks.
static inline bool zorn_terminal_prefix231(const char *text,const char *literal) {
    if(!text)return false;
    for(unsigned n=0;literal[n];++n)if(text[n]!=literal[n])return false;
    return true;
}
static inline unsigned zorn_terminal_category231(const char *text) {
    if(zorn_terminal_prefix231(text,"Kernel data abort."))return 1;
    if(zorn_terminal_prefix231(text,"Kernel instruction fetch abort"))return 2;
    if(zorn_terminal_prefix231(text,"initproc exited"))return 3;
    if(zorn_terminal_prefix231(text,"initproc failed to start"))return 4;
    if(zorn_terminal_prefix231(text,"K80 GPU progress worker returned"))return 5;
    return 0;
}
#ifdef __cplusplus
struct ZornTerminalProgress231 { unsigned state,requested,acknowledged,result; };
static inline unsigned zorn_terminal_progress_pack231(const ZornTerminalProgress231 &a,const ZornTerminalProgress231 &b) {
    if(a.state!=b.state || a.requested!=b.requested || a.acknowledged!=b.acknowledged || a.result!=b.result ||
       a.state>5 || a.requested>6 || a.acknowledged>a.requested || (a.state==3 && a.result>88))return 0;
    return 0x80000000u | a.requested | (a.acknowledged<<3) | (a.state<<6) | ((a.state==3?a.result:255u)<<9);
}
#endif
static inline bool zorn_terminal_progress_valid231(unsigned p) {
    if((p&0xfffe0000u)!=0x80000000u)return false;
    const unsigned req=p&7,ack=(p>>3)&7,state=(p>>6)&7,result=(p>>9)&255;
    return req<=6 && ack<=req && state<=5 && (state==3?result<=88:result==255);
}
#ifdef __cplusplus
extern "C" {
#endif
unsigned zorn26_gpu_terminal_progress231(void);
#ifdef __cplusplus
}
#endif

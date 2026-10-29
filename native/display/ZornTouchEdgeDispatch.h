// SPDX-License-Identifier: BSD-2-Clause-Patent
// Board-owned table copy for this digitizer only; original tables/code stay
// unchanged. Every private slot/extent is independently checked at build time.
#pragma once
#include "OriginalHidEventABI.h"
#include "ZornTouchEdges.h"
extern "C" volatile uint32_t zorn_touch_edge_stats[8];
namespace ZornTouchEdges {
static uintptr_t table[ZornEventABI::DriverSlots];
static IORegistryEntry *installedDriver;
static uintptr_t originalDispatch;
static ZornEdgePolicy::Tracker tracker={};
static void count(unsigned n){__atomic_fetch_add(&zorn_touch_edge_stats[n],1,__ATOMIC_RELAXED);}
template<typename R,typename... Args> static R call(void *object,unsigned slot,Args... args) {
    return reinterpret_cast<R (*)(void *,Args...)>((*reinterpret_cast<uintptr_t **>(object))[slot])(object,args...);
}
static bool validEvent(OSObject *event) {
    return event && *reinterpret_cast<uintptr_t **>(event)==reinterpret_cast<uintptr_t *>(ZornEventABI::EventVptr);
}
static bool mark(OSObject *event) {
    if(!validEvent(event) || call<uint32_t>(event,18)!=11){count(4);return false;}
    count(2);
    auto index=call<int32_t,uint32_t,IOOptionBits>(event,23,0xb0005,0);
    auto mask=call<int32_t,uint32_t,IOOptionBits>(event,23,0xb0007,0);
    bool down=call<int32_t,uint32_t,IOOptionBits>(event,23,0xb0009,0)!=0;
    auto x=call<int32_t,uint32_t,IOOptionBits>(event,25,0xb0000,0);
    auto y=call<int32_t,uint32_t,IOOptionBits>(event,25,0xb0001,0);
    if(tracker.mark(static_cast<uint32_t>(index),static_cast<uint32_t>(mask),down,x,y)) {
        call<void,uint32_t,int32_t,IOOptionBits>(event,24,0xb0007,mask|ZornEdgePolicy::FromEdgeTip,0);
        count(3);return true;
    }
    return false;
}
static void dispatch(IOService *self,OSObject *event,IOOptionBits options) {
    count(1);
    if(validEvent(event) && call<uint32_t>(event,18)==11) {
        OSArray *children=*reinterpret_cast<OSArray **>(reinterpret_cast<uint8_t *>(event)+24);
        if(children && OSDynamicCast(OSArray,children) && children->getCount()<=32) {
            bool any=false;
            for(unsigned i=0;i<children->getCount();++i)any|=mark(children->getObject(i));
            if(any) {
                auto mask=call<int32_t,uint32_t,IOOptionBits>(event,23,0xb0007,0);
                call<void,uint32_t,int32_t,IOOptionBits>(event,24,0xb0007,mask|ZornEdgePolicy::FromEdgeTip,0);
            }
        } else if(!children)mark(event);
        else count(4);
    }
    reinterpret_cast<void (*)(IOService *,OSObject *,IOOptionBits)>(originalDispatch)(self,event,options);
}
static void install(IORegistryEntry *driver) {
    if(installedDriver || !driver)return;
    auto original=*reinterpret_cast<uintptr_t **>(driver);
    const uintptr_t *expected=nullptr;unsigned size=0,kind=0;
    if(original==reinterpret_cast<uintptr_t *>(ZornEventABI::DriverVptr)) {
        expected=ZornEventABI::DriverMethods;size=0x108;kind=1;
    } else if(original==reinterpret_cast<uintptr_t *>(ZornEventABI::UserDriverVptr)) {
        expected=ZornEventABI::UserDriverMethods;size=0x110;kind=2;
    }
    zorn_touch_edge_stats[6]=kind;
    zorn_touch_edge_stats[7]=driver->getMetaClass()->getClassSize();
    if(!expected){zorn_touch_edge_stats[5]=1;return;}
    if(zorn_touch_edge_stats[7]!=size){zorn_touch_edge_stats[5]=2;return;}
    if(memcmp(original,expected,sizeof(table))){zorn_touch_edge_stats[5]=3;return;}
    originalDispatch=original[198];
    memcpy(table,original,sizeof(table));table[198]=reinterpret_cast<uintptr_t>(&dispatch);
    driver->retain();installedDriver=driver; // fixed owned device, bounded boot lifetime
    __asm__ volatile("dmb ish" ::: "memory");
    *reinterpret_cast<uintptr_t **>(driver)=table;
    zorn_touch_edge_stats[0]=1;
}
}

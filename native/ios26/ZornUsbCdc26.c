/* Derived from the pinned houji CDC ACM endpoint implementation. */
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <kern/debug.h>
#include <kern/clock.h>
#include <kern/thread.h>
#include <mach/thread_act.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
#include <arm/caches_internal.h>
#include <mach/mach_time.h>
#include <pexpert/pexpert.h>
#include <pexpert/device_tree.h>
#define HOUJI_HOST_TEST 1
#include "houji_usb_protocol.h"
#include "ZornCdcStream201.h"
#include "ZornCdcTerminal230.h"
#include "ZornTerminalContext231.h"

extern vm_offset_t ml_io_map(vm_offset_t, vm_size_t);
extern unsigned zorn26_panic_ram_prepare239(void);
extern int zorn26_cdc_dma_allocate(vm_offset_t *, uint64_t *, unsigned, unsigned);
extern void *memcpy(void *, const void *, size_t);
extern unsigned long gPhysBase, gPhysSize;
unsigned zorn26_cdc_run(vm_offset_t regs, const char *marker, unsigned length);
#include "ZornPanicPacket236.h"
unsigned zorn26_cdc_terminal237(unsigned,unsigned,unsigned,const uint8_t *,const ZornPanicInput236 *);
void zorn26_cdc_status(unsigned *events, unsigned *setups, unsigned *completed, unsigned *state, uint32_t *phy, uint32_t *clocks);


#define GCTL 0xc110
#define USB2PHY 0xc200
#define USB3PIPE 0xc2c0
#define USB2_SUSPHY (1u << 6)
#define USB3_SUSPHY (1u << 17)
#define LINK_REQUEST (15u << 5)
#define GEVNTADRLO 0xc400
#define GEVNTADRHI 0xc404
#define GEVNTSIZ 0xc408
#define GEVNTCOUNT 0xc40c
#define DCFG 0xc700
#define DCTL 0xc704
#define DEVTEN 0xc708
#define DSTS 0xc70c
#define DALEPENA 0xc720
#define EPBASE(n) (0xc800+16*(n))
#define RUN (1u<<31)
#define RESET (1u<<30)
#define HALTED (1u<<22)
#define ACTIVE (1u<<10)
#define FORCE_REMOVE (1u<<11)
#define SET_CONFIG 1
#define SET_RESOURCE 2
#define STALL 4
#define CLEAR_STALL 5
#define START 6
#define END 8
#define START_CONFIG 9
#define T_NORMAL (1u<<4)
#define T_SETUP (2u<<4)
#define T_STATUS2 (3u<<4)
#define T_STATUS3 (4u<<4)
#define T_DATA (5u<<4)
#define HWO 1u
#define TRB_FLAGS (HWO|2u|(1u<<10)|(1u<<11))
#define EVENTS 0
#define EVENT_SIZE 4096
/* Separate cache lines: hardware never shares a dirty CPU-owned TRB line. */
#define SETUP 0x1200
#define DATA 0x1300
#define NOTIFY 0x1500
#define RX 0x4000
#define TX 0x2000
#define RX_SIZE 65536
#define TX_SIZE 2048
#define DMA_SIZE ZornCdcDmaBytes236
_Static_assert(ZornPanicOffset236>=RX+RX_SIZE,"panic TX overlaps ordinary USB buffers");
_Static_assert(ZornPanicOffset236+ZornPanicCapacity236<=DMA_SIZE,"panic TX exceeds DMA allocation");
_Static_assert(ZornPanicCapacity236<0x1000000,"panic TX exceeds DWC3 TRB length");
_Static_assert(RX+RX_SIZE<=DMA_SIZE,"USB RX exceeds DMA allocation");
_Static_assert(TX+TX_SIZE<=RX,"USB RX/TX overlap");
_Static_assert((RX&63)==0,"USB RX cache alignment");
static const unsigned trb_off[6]={0x1000,0x1040,0x1080,0x10c0,0x1100,0x1140};
static const char *const usb_strings[]={NULL,"UniXNU","Redmi K80 XNU CDC","ZORN269A697DEC3B02"};
// Every steady-state mutation and normal cleanup shares this nonblocking owner.
// A terminal caller never waits for it and never recycles an active DMA buffer.
static unsigned cdcOwner230,cdcReady230,cdcTerminal230;
static bool cdc_owner_enter230(void){unsigned empty=0;return __atomic_compare_exchange_n(&cdcOwner230,&empty,1,false,__ATOMIC_ACQUIRE,__ATOMIC_RELAXED);}
static void cdc_owner_leave230(void){__atomic_store_n(&cdcOwner230,0,__ATOMIC_RELEASE);}
static struct {
    vm_offset_t regs, dma;
    uint64_t pa;
    uint32_t pos, events, setups, mps;
    unsigned resource[6], requested[6];
    bool busy[6], failed, configured, dtr, notify;
    enum { SETUP_PHASE, DATA_PHASE, WAIT2, WAIT3, STATUS_PHASE } phase;
    bool data_in, set_line;
    uint8_t coding[7];
    int sleep_channel;
    const char *marker;
    unsigned length, completed;
    const char *failure;
    uint32_t phy[5], clocks[13];
    unsigned owned_clocks, owned_refs;
    bool progress_mode;unsigned frame_count,wire_bytes;
} u;

void zorn26_cdc_status(unsigned *events, unsigned *setups, unsigned *completed, unsigned *state, uint32_t *phy, uint32_t *clocks)
{
    memcpy(phy, u.phy, sizeof(u.phy));
    memcpy(clocks, u.clocks, sizeof(u.clocks));
    *events = u.events;
    *setups = u.setups;
    *completed = u.completed;
    *state = (u.configured ? 1u : 0u) | (u.dtr ? 2u : 0u) | (u.failed ? 4u : 0u);
}

static uint32_t read_reg(vm_offset_t base,unsigned off)
{
    uint32_t v=*(volatile uint32_t *)(base+off);
    __asm__ volatile("dmb oshld" ::: "memory");
    return v;
}
static uint32_t rd(unsigned off) { return read_reg(u.regs,off); }
static void wr(unsigned off,uint32_t v)
{
    *(volatile uint32_t *)(u.regs+off)=v;
    __asm__ volatile("dsb sy" ::: "memory");
}
static void sync_dma(unsigned off,unsigned size)
{
    if(__atomic_load_n(&cdcTerminal230,__ATOMIC_ACQUIRE)){
        // Existing VA-only PoC routine: no physical lookup or platform callback
        // in the terminal path. Only the already resident TX/TRB spans are used.
        FlushPoC_DcacheRegion(u.dma+off,size);
    }else flush_dcache64((addr64_t)(u.pa+off),size,TRUE);
    __asm__ volatile("dsb sy" ::: "memory");
}
static void fail(const char *why)
{
    if (!u.failed) u.failure = why;
    u.failed = true;
}
static int epcmd(unsigned ep,unsigned cmd,uint32_t p0,uint32_t p1,uint32_t p2)
{
    if (u.failed || ep>=6) return -1;
    wr(EPBASE(ep)+8,p0); wr(EPBASE(ep)+4,p1); wr(EPBASE(ep),p2);
    wr(EPBASE(ep)+12,cmd|ACTIVE);
    for (unsigned n=0;n<1000;n++) {
        uint32_t v=rd(EPBASE(ep)+12);
        if (!(v&ACTIVE)) {
            if ((v>>12)&15) { fail("endpoint command status"); return -1; }
            if ((cmd&15)==START) u.resource[ep]=(v>>16)&0x7f;
            return 0;
        }
        if(!__atomic_load_n(&cdcTerminal230,__ATOMIC_ACQUIRE))delay(1);
    }
    fail("endpoint command timeout"); return -1;
}
static void transfer(unsigned ep,unsigned buf,unsigned length,unsigned kind)
{
    if (u.failed) return;
    if (ep>=6 || u.busy[ep] || buf>DMA_SIZE || length>DMA_SIZE-buf) {
        fail("transfer ownership/bounds"); return;
    }
    unsigned off=trb_off[ep];
    uint64_t p=u.pa+buf,t=u.pa+off;
    volatile uint32_t *trb=(volatile uint32_t *)(u.dma+off);
    trb[0]=(uint32_t)p; trb[1]=(uint32_t)(p>>32);
    trb[2]=length; trb[3]=kind|TRB_FLAGS;
    u.requested[ep]=length;
    if (length) sync_dma(buf,length);
    sync_dma(off,16);
    u.busy[ep]=true;
    (void)epcmd(ep,START,(uint32_t)(t>>32),(uint32_t)t,0);
}
// Called once by the existing terminal path. Return1 means only START accepted;
// host capture,not this return,proves delivery. All resources stay resident.
unsigned zorn26_cdc_terminal237(unsigned reason,unsigned format,unsigned progress,const uint8_t *run_id,const ZornPanicInput236 *input){
    if(!run_id || reason<1 || reason>3 || format>65535u || (reason!=2 && format) || !cdc_owner_enter230())return 0;
    if(!__atomic_load_n(&cdcReady230,__ATOMIC_ACQUIRE) || __atomic_load_n(&cdcTerminal230,__ATOMIC_ACQUIRE)){cdc_owner_leave230();return 0;}
    const ZornCdcTerminalSoftware230 software={
        __atomic_load_n(&cdcReady230,__ATOMIC_ACQUIRE)!=0,
        __atomic_load_n(&cdcTerminal230,__ATOMIC_ACQUIRE)!=0,u.progress_mode,
        u.regs!=0,u.dma!=0,u.pa!=0,u.configured,u.dtr,u.failed,u.phase==SETUP_PHASE,
        u.busy[1]||u.busy[2]||u.busy[3]||u.busy[4]||u.busy[5],u.notify,
        u.completed,u.length,u.frame_count,u.wire_bytes};
    if(!zorn_cdc_terminal_software230(&software)) {cdc_owner_leave230();return 0;}
    // Unhandled reset/disconnect/events or an active command means unknown
    // controller ownership: refuse before any new DMA/cache/endpoint write.
    const ZornCdcTerminalHardware230 hardware={rd(DCTL),rd(DSTS),rd(DALEPENA),rd(EPBASE(3)+12),rd(GEVNTCOUNT)};
    const volatile uint32_t *trb=(const volatile uint32_t *)(u.dma+trb_off[3]);
    if(!zorn_cdc_terminal_hardware230(&hardware,trb[2],trb[3])){cdc_owner_leave230();return 0;}
    // Size-only budget check before publishing DMA ownership. Packet assembly
    // below touches only the separate, preallocated panic TX region.
    if(!input || !zorn_panic_budget236(u.frame_count,u.wire_bytes,ZornPanicCapacity236)){cdc_owner_leave230();return 0;}
    // Publish terminal ownership before touching TX: normal polling/cleanup may
    // no longer reuse or release any controller/DMA resource,even on failure.
    __atomic_store_n(&cdcTerminal230,1,__ATOMIC_RELEASE);
    __atomic_store_n(&cdcReady230,0,__ATOMIC_RELEASE);
    const unsigned length=zorn_panic_build236((uint8_t *)(u.dma+ZornPanicOffset236),ZornPanicCapacity236,
        run_id,reason,format,progress,input);
    if(!length){cdc_owner_leave230();return 0;} // ownership remains retained, even if input validation refused
    ++u.frame_count;u.wire_bytes+=length;
    transfer(3,ZornPanicOffset236,length,T_NORMAL);
    const unsigned result=u.failed?2u:1u;
    cdc_owner_leave230();return result;
}

static int complete(unsigned ep)
{
    if (ep>=6 || !u.busy[ep]) { fail("unexpected completion"); return -1; }
    sync_dma(trb_off[ep],16);
    volatile uint32_t *t=(volatile uint32_t *)(u.dma+trb_off[ep]);
    unsigned left=t[2]&0xffffff;
    if ((t[3]&HWO) || (t[2]>>28) || left>u.requested[ep]) {
        fail("invalid DMA completion"); return -1;
    }
    u.busy[ep]=false;
    return (int)(u.requested[ep]-left);
}
static void setup_arm(void)
{
    u.phase=SETUP_PHASE;
    transfer(0,SETUP,8,T_SETUP);
}
static void stall(void)
{
    (void)epcmd(0,STALL,0,0,0);
    setup_arm();
}

static void stop_data(void)
{
    for (unsigned ep=2;ep<6;ep++) {
        if (u.busy[ep]) {
            if (!u.resource[ep] || epcmd(ep,END|FORCE_REMOVE|(u.resource[ep]<<16),0,0,0)) return;
            u.busy[ep]=false;
        }
    }
    wr(DALEPENA,3);
    u.configured=false; u.dtr=false; u.notify=false;
}
static void configure(void)
{
    if (u.configured || u.failed) return;
    if (epcmd(0,START_CONFIG|(2u<<16),0,0,0) ||
        epcmd(2,SET_CONFIG,(2u<<1)|(u.mps<<3),(1u<<8)|(2u<<25),0) ||
        epcmd(2,SET_RESOURCE,1,0,0) ||
        epcmd(3,SET_CONFIG,(2u<<1)|(u.mps<<3)|(1u<<17),(1u<<8)|(3u<<25),0) ||
        epcmd(3,SET_RESOURCE,1,0,0) ||
        epcmd(5,SET_CONFIG,(3u<<1)|(16u<<3)|(2u<<17),(1u<<8)|(8u<<16)|(5u<<25),0) ||
        epcmd(5,SET_RESOURCE,1,0,0)) return;
    wr(DALEPENA,3|(1u<<2)|(1u<<3)|(1u<<5));
    u.configured=true;
    printf("K80 CDC: CDC ACM configured, bulk MPS %u\n",u.mps);
}
static unsigned string_desc(unsigned index,uint8_t *data)
{
    if (!index) { data[0]=4;data[1]=3;data[2]=9;data[3]=4; return 4; }
    if (index>=sizeof(usb_strings)/sizeof(usb_strings[0])) return 0;
    unsigned n=2;
    for (const char *s=usb_strings[index];*s && n<126;s++) { data[n++]=(uint8_t)*s;data[n++]=0; }
    data[0]=(uint8_t)n;data[1]=3;return n;
}
static void handle_setup(void)
{
    sync_dma(SETUP,8);
    const uint8_t *s=(const uint8_t *)(u.dma+SETUP);
    uint8_t *data=(uint8_t *)(u.dma+DATA);
    uint16_t value=(uint16_t)(s[2]|(s[3]<<8)),index=(uint16_t)(s[4]|(s[5]<<8)),length=(uint16_t)(s[6]|(s[7]<<8));
    unsigned n=0;
    int kind=vusb_request(s[0],s[1],value,index,length);
    u.data_in=(s[0]&0x80)!=0;u.set_line=false;
    if (u.setups++<40) printf("K80 CDC: setup %02x %02x %04x %04x len%u\n",s[0],s[1],value,index,length);
    switch (kind) {
    case VUSB_DESC:
        switch (value>>8) {
        case 1: if (value&255) break;memcpy(data,vusb_device,sizeof(vusb_device));n=sizeof(vusb_device);break;
        case 2: case 7:
            if (value&255) break;
            memcpy(data,vusb_config,sizeof(vusb_config));n=sizeof(vusb_config);
            data[1]=(uint8_t)(value>>8);
            /* Configuration and other-speed configuration have opposite MPS. */
            for (unsigned i=0;i<n;i+=data[i]) if (data[i+1]==5 && (data[i+3]&3)==2) {
                unsigned m=(value>>8)==7?(u.mps==512?64:512):u.mps;
                data[i+4]=(uint8_t)m;data[i+5]=(uint8_t)(m>>8);
            }
            break;
        case 3:n=string_desc(value&255,data);break;
        case 6:if (!(value&255)) { memcpy(data,vusb_qualifier,sizeof(vusb_qualifier));n=sizeof(vusb_qualifier); }break;
        default:break;
        }
        if (!n) { stall();return; }break;
    case VUSB_ADDRESS:wr(DCFG,(rd(DCFG)&~(127u<<3))|((uint32_t)value<<3));break;
    case VUSB_CONFIG:
        /* Reconfiguration while transfers are live is stopped, never recycled
         * before a controller reset drains stale completion events. */
        if (!value && u.configured) { fail("host deconfigured; reboot to reconnect"); return; }
        if (value) configure();break;
    case VUSB_GET_CONFIG:data[0]=u.configured?1:0;n=1;break;
    case VUSB_STATUS:data[0]=data[1]=0;n=2;break;
    case VUSB_INTERFACE:break;
    case VUSB_GET_INTERFACE:data[0]=0;n=1;break;
    case VUSB_SET_LINE:u.set_line=true;break;
    case VUSB_GET_LINE:memcpy(data,u.coding,7);n=7;break;
    case VUSB_CONTROL:
        if (u.configured) {
            u.dtr=(value&1)!=0;u.notify=true;
        }break;
    case VUSB_BREAK:break;
    case VUSB_CLEAR_HALT:
        /* Active transfer replay cannot be made safe by CLEARSTALL alone. */
        if (u.busy[(index&15)*2+((index>>7)&1)]) { fail("clear-halt on active endpoint");return; }
        (void)epcmd((index&15)*2+((index>>7)&1),CLEAR_STALL,0,0,0);break;
    default:stall();return;
    }
    if (u.failed) return;
    if (!length) { u.phase=WAIT2;return; }
    u.phase=DATA_PHASE;
    if (u.data_in) transfer(1,DATA,n<length?n:length,T_DATA);
    else if (u.set_line) transfer(0,DATA,64,T_DATA);
    else stall();
}
static void transmit(void)
{
    if (!u.configured || !u.dtr || u.failed || u.phase != SETUP_PHASE) return;
    if (u.notify && !u.busy[5]) {
        const uint8_t msg[10]={0xa1,0x20,0,0,0,0,2,0,3,0};
        memcpy((void *)(u.dma+NOTIFY),msg,sizeof(msg));u.notify=false;
        transfer(5,NOTIFY,sizeof(msg),T_NORMAL);
    }
    if (u.busy[3] || u.completed >= u.length) return;
    const unsigned left = u.length - u.completed;
    const unsigned size = left < 63 ? left : 63;
    memcpy((void *)(u.dma+TX), u.marker + u.completed, size);
    transfer(3,TX,size,T_NORMAL);
}
static void event(uint32_t e)
{
    if (e&1) {
        if ((e&0xfe)!=0) { fail("unexpected device event format");return; }
        unsigned type=(e>>8)&15;
        if (type==1) {
            if (u.configured) { stop_data();fail("bus reset after configuration; reboot to reconnect");return; }
            wr(DCFG,rd(DCFG)&~(127u<<3));printf("K80 CDC: bus reset\n");
        } else if (type==2) {
            unsigned speed=rd(DSTS)&7;
            if (speed!=0 && speed!=1 && speed!=3) { fail("unexpected non-USB2 speed");return; }
            u.mps=speed==0?512:64;
            (void)epcmd(0,SET_CONFIG,(64u<<3)|(2u<<30),(1u<<8)|(1u<<10),0);
            (void)epcmd(1,SET_CONFIG,(64u<<3)|(2u<<30),(1u<<8)|(1u<<10)|(1u<<25),0);
            printf("K80 CDC: connected speed=%u\n",speed);
        } else if (!type && u.configured) fail("cable disconnect; reboot to reconnect");
        else if (type==9 || type==11) fail("controller/event overflow");
        return;
    }
    unsigned ep=(e>>1)&31,type=(e>>6)&15,status=(e>>12)&15;
    if (type==1) {
        int n=complete(ep);if (n<0) return;
        if (status&1) { fail("USB transfer bus error");return; }
        if (ep==3) {
            if ((unsigned)n != u.requested[ep] || (unsigned)n > u.length - u.completed) {
                fail("short or invalid bulk IN completion");
                return;
            }
            u.completed += (unsigned)n;
        }
        if (ep>1) return;
        switch (u.phase) {
        case SETUP_PHASE:if (ep!=0 || n!=8) fail("setup length");else handle_setup();break;
        case DATA_PHASE:
            if (u.set_line) {
                if (ep!=0 || n!=7) { fail("line coding length");break; }
                sync_dma(DATA,64);memcpy(u.coding,(void *)(u.dma+DATA),7);
            }
            u.phase=WAIT3;break;
        case STATUS_PHASE:setup_arm();break;
        default:fail("control completion order");break;
        }
    } else if (ep<=1 && type==3 && status==2 && (u.phase==WAIT2 || u.phase==WAIT3)) {
        unsigned direction=u.phase==WAIT2?1:(u.data_in?0:1);
        if (ep!=direction) { fail("control status direction");return; }
        unsigned kind=u.phase==WAIT3?T_STATUS3:T_STATUS2;
        u.phase=STATUS_PHASE;transfer(ep,DATA,0,kind);
    }
}
static void poll_events(void)
{
    unsigned count=rd(GEVNTCOUNT)&0xffff;
    if (count>EVENT_SIZE || (count&3)) { fail("event ring size/alignment");return; }
    if (!count) return;
    sync_dma(EVENTS,EVENT_SIZE);
    for (unsigned i=0;i<count && !u.failed;i+=4) {
        uint32_t e=*(volatile uint32_t *)(u.dma+u.pos);
        u.pos=(u.pos+4)%EVENT_SIZE;
        ++u.events;
        event(e);
    }
    wr(GEVNTCOUNT,count);
}

/* GCC branch offsets and bit 0 enables from gcc-pineapple.c.
 * The original RCG parent/rate and the PHY reference votes stay with firmware. */
static const unsigned clock_offsets[] = {0x24, 0x28};
static void clock_vote(vm_offset_t gcc, unsigned index, bool enable)
{
    const unsigned offset = clock_offsets[index];
    const uint32_t value = read_reg(gcc, offset);
    *(volatile uint32_t *)(gcc + offset) = (value & ~1u) | (enable ? 1u : 0u);
    __asm__ volatile("dsb sy" ::: "memory");
}
static void restore_clocks(vm_offset_t gcc)
{
    for (unsigned i = 2; i-- > 0;) {
        if (u.owned_clocks & (1u << i)) clock_vote(gcc, i, false);
    }
}
static bool prepare_clocks(vm_offset_t gcc)
{
    for (unsigned i = 0; i < 2; ++i) u.clocks[i] = read_reg(gcc, clock_offsets[i]);
    for (unsigned i = 0; i < 2; ++i) {
        if (!(u.clocks[i] & 1u)) {
            u.owned_clocks |= 1u << i;
            clock_vote(gcc, i, true);
        }
        for (unsigned t = 0; t < 100 && (read_reg(gcc, clock_offsets[i]) >> 31); ++t) delay(10);
        u.clocks[2 + i] = read_reg(gcc, clock_offsets[i]);
        if ((u.clocks[2 + i] & 0x80000001u) != 1u) {
            restore_clocks(gcc);
            return false;
        }
    }
    return true;
}

/* Pineapple TCSR USB clock references use a delayed branch enable. */
static const unsigned ref_offsets[] = {0x1118, 0x1108};
static void ref_vote(vm_offset_t tcsr, unsigned index, bool enable)
{
    const unsigned offset = ref_offsets[index];
    const uint32_t value = read_reg(tcsr, offset);
    *(volatile uint32_t *)(tcsr + offset) = (value & ~1u) | (enable ? 1u : 0u);
    __asm__ volatile("dsb sy" ::: "memory");
    delay(10);
}
static void restore_refs(vm_offset_t tcsr)
{
    for (unsigned i = 2; i-- > 0;) {
        if (u.owned_refs & (1u << i)) ref_vote(tcsr, i, false);
    }
}
static bool prepare_refs(vm_offset_t tcsr)
{
    for (unsigned i = 0; i < 2; ++i) {
        if (!(u.clocks[4+i] & 1u)) {
            u.owned_refs |= 1u << i;
            ref_vote(tcsr, i, true);
        }
        u.clocks[8+i] = read_reg(tcsr, ref_offsets[i]);
        if ((u.clocks[8+i] & 0x80000001u) != 1u) {
            restore_refs(tcsr);
            return false;
        }
    }
    return true;
}

static unsigned cdc_run201(vm_offset_t regs, const char *marker, unsigned length, ZornCdcNext201 next, void *context)
{
    ZornCdcStream201 stream = {0};
    if(next){
        if(zorn_cdc_next201(&stream,false,false,0,next,context)!=1)return 15;
        marker=stream.bytes;length=stream.length;
    }
    // The caller requalifies the halted controller and route at each boot.
    if (!regs || !marker || !length || length>4096 || u.regs) return 1;
    u.regs=regs;u.marker=marker;u.length=length;u.mps=512;
    u.progress_mode=next!=NULL;u.frame_count=next?stream.frames:1;u.wire_bytes=next?stream.total:length;
    u.coding[1]=0xc2;u.coding[2]=1;u.coding[6]=8;
    unsigned width=rd(0xc140)>>24;
    vm_offset_t qs=ml_io_map(0xa6f8000,0x4000);
    if (qs) qs+=0x800;
    if (!qs) return 2;
    /* First stop any old device DMA; soft reset must finish before replacing
     * descriptors. PHY configuration and global bus settings remain from ABL. */
    wr(DEVTEN,0);wr(DCTL,rd(DCTL)&~(RUN|LINK_REQUEST));
    unsigned i;
    for (i=0;i<500 && !(rd(DSTS)&HALTED);i++) delay(1000);
    if (!(rd(DSTS)&HALTED)) { fail("controller halt timeout");return 8; }
    const vm_offset_t gcc = ml_io_map(0x139000, 0x4000);
    const vm_offset_t tcsr = ml_io_map(0x1ff0000, 0x4000);
    const vm_offset_t phy_reset = ml_io_map(0x112000, 0x4000);
    if (!gcc || !tcsr || !phy_reset) return 2;
    u.clocks[4] = read_reg(tcsr, 0x1118);
    u.clocks[5] = read_reg(tcsr, 0x1108);
    u.clocks[6] = read_reg(phy_reset, 0);
    if (!prepare_clocks(gcc)) return 12;
    if (!prepare_refs(tcsr)) {
        restore_clocks(gcc);
        return 13;
    }
    if (!(u.clocks[6] & 1u)) {
        const vm_offset_t phy = ml_io_map(0x88e0000, 0x4000);
        if (phy) {
            u.clocks[7] = read_reg(phy, 0x3054);  // COMMON0: PHY_ENABLE and SIDDQ
            u.clocks[10] = read_reg(phy, 0x3050); // UTMI CTRL5: POR
            u.clocks[11] = read_reg(phy, 0x303c); // UTMI CTRL0: SLEEPM
            u.clocks[12] = 1;
        }
    }
    // Require the inherited eUSB2 PHY to be enabled and out of POR/SIDDQ.
    if (!u.clocks[12] || (u.clocks[7] & 5u) != 1u ||
        (u.clocks[10] & 2u) || !(u.clocks[11] & 1u)) {
        restore_refs(tcsr);
        restore_clocks(gcc);
        return 14;
    }

    // Pineapple dwc3_phy_setup clears SUSPHY on both interfaces before reset.
    u.phy[0] = rd(USB2PHY);
    u.phy[1] = rd(USB3PIPE);
    wr(USB2PHY, u.phy[0] & ~USB2_SUSPHY);
    wr(USB3PIPE, u.phy[1] & ~USB3_SUSPHY);
    u.phy[2] = rd(USB2PHY);
    u.phy[3] = rd(USB3PIPE);
    if ((u.phy[2] & USB2_SUSPHY) || (u.phy[3] & USB3_SUSPHY)) return 11;
    // dwc3_core_soft_reset and dwc3_gadget_dctl_write_safe preserve other DCTL fields.
    wr(DCTL, (rd(DCTL) & ~(RUN | LINK_REQUEST)) | RESET);
    for (i = 0; i < 10 && (rd(DCTL) & RESET); ++i) {
        uint64_t tick;
        clock_interval_to_deadline(20, NSEC_PER_MSEC, &tick);
        (void)assert_wait_deadline(&u.sleep_channel, THREAD_UNINT, tick);
        thread_block(THREAD_CONTINUE_NULL);
    }
    u.phy[4] = rd(DCTL);
    if (u.phy[4] & RESET) { fail("controller reset timeout");return 9; }
    if (!zorn26_cdc_dma_allocate(&u.dma, &u.pa, DMA_SIZE, width)) {
        restore_refs(tcsr);
        restore_clocks(gcc);
        return 2;
    }
    sync_dma(0,DMA_SIZE);
    wr(GEVNTADRLO,(uint32_t)u.pa);wr(GEVNTADRHI,(uint32_t)(u.pa>>32));
    if (rd(GEVNTADRHI)!=(uint32_t)(u.pa>>32)) { fail("event address readback");return 10; }
    wr(GEVNTSIZ,(1u<<31)|EVENT_SIZE);wr(GEVNTCOUNT,rd(GEVNTCOUNT)&0xffff);
    wr(DCFG,rd(DCFG)&~(7u|(127u<<3))); /* high speed only */
    if (epcmd(0,START_CONFIG,0,0,0) ||
        epcmd(0,SET_CONFIG,64u<<3,(1u<<8)|(1u<<10),0) || epcmd(0,SET_RESOURCE,1,0,0) ||
        epcmd(1,SET_CONFIG,64u<<3,(1u<<8)|(1u<<10)|(1u<<25),0) || epcmd(1,SET_RESOURCE,1,0,0)) return 2;
    wr(DALEPENA,3);setup_arm();if (u.failed) return 2;
    uint32_t hs=read_reg(qs,0x10);
    *(volatile uint32_t *)(qs+0x10)=hs|(1u<<20)|(1u<<28);
    __asm__ volatile("dsb sy" ::: "memory");
    wr(DEVTEN,7|(1u<<9)|(1u<<11));wr(DCTL,(rd(DCTL)&~LINK_REQUEST)|RUN);
    for (i=0;i<500 && (rd(DSTS)&HALTED);i++) delay(1000);
    if (rd(DSTS)&HALTED) { fail("controller run timeout"); }
    uint64_t deadline, next_frame=0;
    clock_interval_to_deadline(120,NSEC_PER_SEC,&deadline);
    while (mach_absolute_time()<deadline) {
        if(__atomic_load_n(&cdcTerminal230,__ATOMIC_ACQUIRE))return 16; // resources retained
        if(cdc_owner_enter230()){
            if(__atomic_load_n(&cdcTerminal230,__ATOMIC_ACQUIRE)){cdc_owner_leave230();return 16;}
            if(u.failed){__atomic_store_n(&cdcReady230,0,__ATOMIC_RELEASE);cdc_owner_leave230();break;}
            poll_events();
            if(next && !u.failed && u.configured && u.dtr && u.phase==SETUP_PHASE &&
               !u.busy[3] && u.completed==u.length && mach_absolute_time()>=next_frame){
                const int step=zorn_cdc_next201(&stream,true,u.busy[3],u.completed,next,context);
                if(step<0)fail("progress frame bounds");
                else if(step>0){u.marker=stream.bytes;u.length=stream.length;u.completed=0;u.frame_count=stream.frames;u.wire_bytes=stream.total;}
                clock_interval_to_deadline(3,NSEC_PER_SEC,&next_frame);
            }
            transmit();
            const bool failed=u.failed;
            __atomic_store_n(&cdcReady230,!failed && u.progress_mode,__ATOMIC_RELEASE);
            const bool panic_log_ready239 = !failed && u.configured && u.dtr &&
                u.progress_mode && u.frame_count && !u.busy[3] && u.completed==u.length;
            cdc_owner_leave230();
            // Ready was published and the terminal ownership lock released.
            // An error inside native debug initialization can use retained CDC.
            if(panic_log_ready239) (void)zorn26_panic_ram_prepare239();
            if(failed)break;
        }
        uint64_t tick;
        clock_interval_to_deadline(1,NSEC_PER_MSEC,&tick);
        (void)assert_wait_deadline(&u.sleep_channel,THREAD_UNINT,tick);
        thread_block(THREAD_CONTINUE_NULL);
    }
    // Deadline/failure cleanup is serialized with the one terminal attempt.
    // Losing ownership retains everything;it never guesses DMA has stopped.
    if(!cdc_owner_enter230())return 16;
    if(__atomic_load_n(&cdcTerminal230,__ATOMIC_ACQUIRE)){cdc_owner_leave230();return 16;}
    __atomic_store_n(&cdcReady230,0,__ATOMIC_RELEASE);
    wr(DEVTEN,0);
    wr(DCTL,rd(DCTL)&~(RUN|LINK_REQUEST));
    for (i=0;i<500 && !(rd(DSTS)&HALTED);i++) delay(1000);
    if (!(rd(DSTS)&HALTED)){cdc_owner_leave230();return 3;}
    *(volatile uint32_t *)(qs+0x10)=hs;
    wr(USB2PHY, (rd(USB2PHY) & ~USB2_SUSPHY) | (u.phy[0] & USB2_SUSPHY));
    wr(USB3PIPE, (rd(USB3PIPE) & ~USB3_SUSPHY) | (u.phy[1] & USB3_SUSPHY));
    __asm__ volatile("dsb sy" ::: "memory");
    restore_refs(tcsr);
    restore_clocks(gcc);
    printf("K80 CDC: events=%u setup=%u completed=%u failure=%s\n",
           u.events,u.setups,u.completed,u.failure?u.failure:"none");
    const unsigned result=(!u.failed && u.completed==u.length)?0u:u.failed?4u:u.configured?5u:6u;
    cdc_owner_leave230();return result;
}

unsigned zorn26_cdc_run(vm_offset_t regs, const char *marker, unsigned length)
{return cdc_run201(regs,marker,length,NULL,NULL);}
unsigned zorn26_cdc_stream201(vm_offset_t regs, ZornCdcNext201 next, void *context)
{return next ? cdc_run201(regs,NULL,0,next,context) : 1;}

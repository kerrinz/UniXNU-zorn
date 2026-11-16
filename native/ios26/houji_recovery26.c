/* SPDX-License-Identifier: BSD-2-Clause-Patent
 * K80 platform-trial terminal,using unchanged source26 record/console ABI. The host must verify/prearm a no-wipe
 * recovery BCB before boot; this reset path performs no filesystem or UFS I/O.
 */
#include <kern/thread.h>
#include <kern/debug.h>
#include <pexpert/pexpert.h>
#include <console/video_console.h>
#include <stdint.h>
#include "HoujiTerminal26.h"
#include "ZornPlatformTrialIdentity26.h"
#include "ZornPlatformTrial26.h"
#include "ZornGen7RscStageScreen26.h"

extern void IOSleep(unsigned int);
#include <sys/msgbuf.h>
#include <stdarg.h>
#include "ZornPanicPacket236.h"
#include "ZornClientTrace240.h"
#include "ZornApplicationObservation26.h"
extern volatile uint32_t native_adreno_trace_stage;
extern unsigned zorn26_cdc_terminal237(unsigned,unsigned,unsigned,const uint8_t *,const ZornPanicInput236 *);
#include "ZornTerminalContext231.h"
void houji26_reset_recovery(void) __attribute__((noreturn));
void houji26_start_recovery_timer(void);
void houji26_finish_trial(unsigned reason) __attribute__((noreturn));
void houji26_capture_reason(const char *text);
const void *houji26_panic_record(void);
void houji26_smp_screen(const char *stage, unsigned cpu);

extern struct vc_info vinfo;
extern unsigned char iso_font[256 * 16];
#include "ZornPanicMacro233.h"
static unsigned firstPanicFormat232;
void zorn26_capture_panic_format232(const char *format){
    unsigned empty=0;
    if(!__atomic_compare_exchange_n(&firstPanicFormat232,&empty,ZornPanicFormatPending232,
                                   false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))return;
    const unsigned actual=zorn_panic_format_lookup233(format);
    __atomic_store_n(&firstPanicFormat232,actual,__ATOMIC_RELEASE);
}
// Static first-winner formatter storage, independent of the older 512-byte record ABI.
static struct {unsigned state,bytes,required;char text[ZornPanicReasonCap236];} panicReason236;
void zorn26_capture_panic236(const char *format,va_list *args){
    unsigned empty=0;
    if(!format || !args || !__atomic_compare_exchange_n(&panicReason236.state,&empty,1,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))return;
    va_list copy;va_copy(copy,*args);
    const int required=vsnprintf(panicReason236.text,sizeof(panicReason236.text),format,copy);
    va_end(copy);
    if(required<0){__atomic_store_n(&panicReason236.state,3,__ATOMIC_RELEASE);return;}
    panicReason236.required=(unsigned)required;
    panicReason236.bytes=(unsigned)required<sizeof(panicReason236.text)?(unsigned)required:sizeof(panicReason236.text)-1;
    __atomic_store_n(&panicReason236.state,2,__ATOMIC_RELEASE);
}
static ZornPanicInput236 panic_input236(void){
    ZornPanicInput236 in={0};
    in.reason_state=__atomic_load_n(&panicReason236.state,__ATOMIC_ACQUIRE);
    if(in.reason_state==2){in.reason=panicReason236.text;in.reason_bytes=panicReason236.bytes;in.reason_required=panicReason236.required;}
    // The existing XNU debug buffer is mapped/wired by its original owner.
    // Validate its published capacity; no mapping, allocation or storage call.
    const uintptr_t first=(uintptr_t)debug_buf_base,last=(uintptr_t)debug_buf_ptr;
    const unsigned capacity=debug_buf_size;
    if(!first || !last || !capacity)in.flags|=ZornLogMissing236;
    else if(last<first || capacity>1048576 || last-first>capacity)in.flags|=ZornLogInvalid236;
    else {in.panic=debug_buf_base;in.panic_bytes=(unsigned)(last-first);}
    // Same public msgbuf fields used by upstream BootLog, through the actual
    // selected XNU header. Keep raw bytes (including NUL), not decoded state.
    struct msgbuf *m=msgbufp;
    if(!m)in.flags|=ZornMsgMissing236;
    else {
        const char *text=m->msg_bufc;const int size=m->msg_size,index=m->msg_bufx,magic=m->msg_magic;
        if(magic!=MSG_MAGIC || !text || size<=0 || size>MAX_MSG_BSIZE || index<0 || index>=size)in.flags|=ZornMsgInvalid236;
        else {in.messages=text;in.message_size=(unsigned)size;in.message_index=(unsigned)index;}
    }
    return in;
}
// Terminal entry already has a single winner. Reserve POD outside panic stack.
// Original snapshot performs one CAS try-lock; no waiting or retry here.
static ZornApplicationObservation26 terminalApplication241;
static void zorn_terminal_application241(void) {
    if(!zorn26_application_snapshot(&terminalApplication241)) {
        paniclog_append_noflush("\nK80 APP241 snapshot=0 schema=1\n");
        return;
    }
    const ZornApplicationObservation26 *a=&terminalApplication241;
    const ZornNativeReturn225 *n=&a->nativeReturn225;
    // key is an internal pointer-like request identity: deliberately omitted.
    // Identities below are existing source-defined process counters only.
    paniclog_append_noflush("\nK80 APP241 snapshot=1 unique=%llu pid=%u report_unique=%llu report_pid=%u sessions=%u rejected=%u dropped=%u flags=%u calls=%u method=%u raw=%u close=%u/%u prepare=%u/%u/%u/%u/%u mask=%llu nr=%u/%u/%u/%u/%u/%u/%u/%u schema=1\n",
        (unsigned long long)a->unique,a->pid,(unsigned long long)a->reportUnique,a->reportPid,
        a->sessions,a->sessionRejected,a->dropped,a->flags,a->calls,a->method,a->raw,a->closeReturned,a->closeRaw,
        a->prepareStage,a->prepareRaw,a->prepareDetail,a->prepareEvents,a->prepareFailed,
        (unsigned long long)a->prepareMask,n->sequence,n->method,n->stage,n->runSeen,n->runRaw,n->externalRaw,n->overlaps,n->rejected);
}
static unsigned terminal_entered;
static uint64_t trial_deadline;
static Hjt26Reason first_panic __attribute__((aligned(16384)));

void houji26_smp_screen(const char *stage, unsigned cpu) {
    int enabled = 0;
    if (!PE_parse_boot_argn("houji_smp_screen", &enabled, sizeof(enabled)) || enabled != 1) return;
    Hjt26Surface surface;
    uintptr_t base = (uintptr_t)vinfo.v_baseaddr;
    size_t bytes = (size_t)vinfo.v_rowbytes * vinfo.v_height;
    if ((base >> 48) != 0xffff || !hjt26_surface(&surface, base, vinfo.v_width,
        vinfo.v_height, vinfo.v_rowbytes, vinfo.v_depth, bytes) || surface.height < 272) return;
    surface.base += 160 * surface.row_words;
    surface.height = 112;
    static const char title[] = "K80 IOS26 SMP";
    char detail[96];
    uint64_t mpidr = __builtin_arm_rsr64("MPIDR_EL1");
    unsigned affinity = (unsigned)(((mpidr >> 32) & 0xff) << 24 | (mpidr & 0xffffff));
    int length = snprintf(detail, sizeof(detail), "CPU%u %s (local affinity %08x)", cpu, stage, affinity);
    if (length <= 0 || (unsigned)length >= sizeof(detail)) return;
    hjt26_render(&surface, iso_font, title, sizeof(title) - 1, detail, (size_t)length);
    __asm__ volatile("dsb sy" ::: "memory");
}

// Actual retained kernel-console surface only. No descriptor/mapping/window
// is constructed and the normal console path is unchanged when unselected.
static void rsc_stage_rect(Hjt26Surface *s,unsigned x,unsigned y,unsigned w,unsigned h,uint32_t color)
{
    for(unsigned row=0;row<h;++row)
        for(unsigned col=0;col<w;++col)s->base[(y+row)*s->row_words+x+col]=color;
}
// RAM-only source checkpoint. No MMIO,allocation,lock,callback or storage.
// Zero means no instrumented checkpoint was reached; otherwise value=stage+1.
static unsigned zorn_rsc_checkpoint_word;
unsigned zorn26_rsc_stage_snapshot(void)
{return __atomic_load_n(&zorn_rsc_checkpoint_word,__ATOMIC_ACQUIRE);}
void zorn26_rsc_stage_screen(unsigned stage)
{
    if(stage<=255)__atomic_store_n(&zorn_rsc_checkpoint_word,stage+1,__ATOMIC_RELEASE);
    unsigned selected=0;
    if(!PE_parse_boot_argn("zorn26_rsc_stage_screen",&selected,sizeof(selected)) || selected!=1 || stage>255)return;
    Hjt26Surface surface;uintptr_t base=(uintptr_t)vinfo.v_baseaddr;
    size_t bytes=(size_t)vinfo.v_rowbytes*vinfo.v_height;
    if((base>>48)!=0xffff || !hjt26_surface(&surface,base,vinfo.v_width,vinfo.v_height,
        vinfo.v_rowbytes,vinfo.v_depth,bytes) || surface.width<640 || surface.height<480)return;
    unsigned x=(surface.width-640)/2,y=surface.height-480;
    rsc_stage_rect(&surface,x,y,640,480,0xff000000);
    // Two large hexadecimal digits,readable by the existing distant camera.
    static const unsigned segments[16]={0x3f,0x06,0x5b,0x4f,0x66,0x6d,0x7d,0x07,
        0x7f,0x6f,0x77,0x7c,0x39,0x5e,0x79,0x71};
    static const unsigned rect[7][4]={{30,0,160,30},{190,30,30,140},{190,200,30,140},
        {30,340,160,30},{0,200,30,140},{0,30,30,140},{30,170,160,30}};
    for(unsigned digit=0;digit<2;++digit){
        unsigned value=digit?(stage&15):((stage>>4)&15),bits=segments[value];
        for(unsigned i=0;i<7;++i)if(bits&(1u<<i))
            rsc_stage_rect(&surface,x+50+digit*300+rect[i][0],y+55+rect[i][1],rect[i][2],rect[i][3],0xffffffff);
    }
    __asm__ volatile("dsb sy" ::: "memory");
}

const void *houji26_panic_record(void) { return &first_panic.record; }
static void flush_panic_record(void) {
    /* Normal RAM only. A reset may preserve this exact tagged record; the
     * next firmware can accept it only by trial identity and CRC. */
    uintptr_t at = (uintptr_t)&first_panic.record & ~(uintptr_t)63;
    uintptr_t end = (uintptr_t)&first_panic.record + sizeof(first_panic.record);
    for (; at < end; at += 64) __asm__ volatile("dc cvac, %0" : : "r"(at) : "memory");
    __asm__ volatile("dsb sy" ::: "memory");
}
void houji26_capture_reason(const char *text) {
    hjt26_capture(&first_panic, text, kZornPlatformTrial);
    if (__atomic_load_n(&first_panic.state, __ATOMIC_ACQUIRE) == 2) flush_panic_record();
}

void houji26_finish_trial(unsigned reason) {
    if (__atomic_exchange_n(&terminal_entered, 1U, __ATOMIC_ACQ_REL))
        houji26_reset_recovery();
    /* A non-Apple loader may supply no iBoot panic region. Capture the existing
     * formatter's first reason before panic handling, including early panics. */
    if (__atomic_load_n(&first_panic.state, __ATOMIC_ACQUIRE) == 2) reason = 2;
    const unsigned format=reason==2?__atomic_load_n(&firstPanicFormat232,__ATOMIC_ACQUIRE):0;
    // Append scalar source milestones using the existing native panic writer.
    // No allocation, object traversal, protocol change or terminal retry.
    if(debug_buf_base && debug_buf_ptr && debug_buf_size &&
       debug_buf_ptr>=debug_buf_base &&
       (uintptr_t)debug_buf_ptr-(uintptr_t)debug_buf_base<debug_buf_size) {
        paniclog_append_noflush("\nK80 SOURCE240 events=%u schema=1\n",zorn26_client_snapshot240());
        zorn_terminal_application241();
        // Existing source diagnostic only,best-effort globally shared scalar.
        // Never dereference objects or infer machine-state/stack information.
        paniclog_append_noflush("\nK80 RELEASE243 native=%u schema=1\n",native_adreno_trace_stage);
    }
    const ZornPanicInput236 raw=panic_input236();
    (void)zorn26_cdc_terminal237(reason,format,zorn26_gpu_terminal_progress231(),kZornPlatformTrial,&raw); // one retained transfer;no retry
    const char *title = reason == 1 ? "K80 IOS26: TIME LIMIT; RECOVERY IN 20S" :
        reason == 2 ? "K80 IOS26: KERNEL PANIC; RECOVERY IN 90S" : "K80 IOS26: SYSTEM HALT OR RESTART; RECOVERY IN 90S";
    if (__atomic_load_n(&first_panic.state, __ATOMIC_ACQUIRE) == 0) {
        hjt26_capture(&first_panic, title, kZornPlatformTrial);
        if (__atomic_load_n(&first_panic.state, __ATOMIC_ACQUIRE) == 2) flush_panic_record();
    }
    const unsigned pause_seconds = reason == 1 ? 20 : 90;
    const char *detail = reason == 1 ? "Returning to Recovery in 20 seconds.\n" : "Returning to Recovery in 90 seconds.\n";
    size_t detail_length = __builtin_strlen(detail);
    if (reason == 2 && __atomic_load_n(&first_panic.state, __ATOMIC_ACQUIRE) == 2) {
        detail = first_panic.record.text;
        detail_length = __builtin_strlen(detail);
    } else if (reason == 2) {
        uintptr_t first = (uintptr_t)debug_buf_base, last = (uintptr_t)debug_buf_ptr;
        if (first && last > first && last - first <= 256 * 1024) {
            detail = debug_buf_base;
            detail_length = last - first;
        }
    }
    Hjt26Surface surface;
    /* Reuse the console's live mapping. Never map MMIO, allocate or use UFS
     * from a panic, and never interpret a boot physical pointer as a VA. */
    uintptr_t base = (uintptr_t)vinfo.v_baseaddr;
    size_t bytes = (size_t)vinfo.v_rowbytes * vinfo.v_height;
    if ((base >> 48) == 0xffff && hjt26_surface(&surface, base, vinfo.v_width,
        vinfo.v_height, vinfo.v_rowbytes, vinfo.v_depth, bytes)) {
        hjt26_render(&surface, iso_font, title, __builtin_strlen(title), detail, detail_length);
        __asm__ volatile("dsb sy" ::: "memory");
    }
    uint64_t frequency = __builtin_arm_rsr64("CNTFRQ_EL0");
    uint64_t started = __builtin_arm_rsr64("CNTPCT_EL0");
    if (frequency >= 1000000 && frequency <= 1000000000) {
        uint64_t duration = frequency * pause_seconds;
        uint64_t deadline = __atomic_load_n(&trial_deadline, __ATOMIC_ACQUIRE);
        if (deadline && (deadline <= started || deadline - started < duration))
            duration = deadline <= started ? 0 : deadline - started;
        while (__builtin_arm_rsr64("CNTPCT_EL0") - started < duration)
            __asm__ volatile("yield");
    }
    houji26_reset_recovery();
}

// Public compatibility names are retained by existing source26 panic/PSCI
// callers. The backend and identity here belong to this K80 candidate only.
void houji26_reset_recovery(void) { zorn26_reset_prearmed_recovery(); }
void zorn26_platform_terminal_init(uint64_t actual_deadline) {
    hjt26_initialize(&first_panic,kZornPlatformTrial);flush_panic_record();
    __atomic_store_n(&trial_deadline,actual_deadline,__ATOMIC_RELEASE);
}
void houji26_start_recovery_timer(void) {
    if(!zorn26_platform_trial_start())panic("K80 platform trial admission/start refused");
}

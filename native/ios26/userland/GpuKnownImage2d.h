/* SPDX-License-Identifier: MIT
 * Fixed A750/gen3 cold-context CP_BLIT qualification candidate.
 * Command words derive from Mesa 85fda3b36405bcaea8bffc64aa4f2651dc90770d:
 * Copyright 2016 Red Hat; 2016 Bas Nieuwenhuizen; 2015 Intel Corporation;
 * Copyright 2019-2020 Valve Corporation (Jonathan Marek).
 *
 * This is NOT integrated in the driver and has no MMIO, SMC or filesystem API.
 * A native adapter must independently prove fresh ownership, authenticated ZAP,
 * successful CP_SET_SECURE_MODE(0) completion and a disabled KMD preemption path.
 * The caller must retain the entire fixed allocation until its existing final
 * stop/reset isolation proves safety, on success AND on every partial failure.
 * No free/reuse/reopen-filesystem operation is implemented here.
 *
 * The complete selected tu_init_hw prefix and owned BR/BV bin preambles are
 * retained. No arbitrary register, address, shader or command input is accepted.
 * Linear RGBA8 CP_BLIT is an intentional diagnostic source branch; A750's
 * default VkCmdClearColorImage may instead choose the generic-event clear.
 * This proves dedicated 2D graphics only; it cannot prove shader/Metal support.
 */
#ifndef HOUJI_GPU_KNOWN_IMAGE_2D_H
#define HOUJI_GPU_KNOWN_IMAGE_2D_H
#include <stddef.h>
#include <stdint.h>
#ifndef HGKI_PROGRESS
#define HGKI_PROGRESS 0
#endif
#if HGKI_PROGRESS != 0 && HGKI_PROGRESS != 1
#error HGKI_PROGRESS must be zero or one
#endif

enum {HGKI_BASE=0x62080000,HGKI_CLASS_CURSOR=0x80000,HGKI_CLASS_END=0x620c0000,
 HGKI_PAGE=4096,HGKI_PAGES=7,HGKI_BYTES=HGKI_PAGE*HGKI_PAGES,
 HGKI_BORDER=0x62081000,HGKI_BR=0x62082000,HGKI_BV=0x62083000,
 HGKI_COMMAND=0x62084000,HGKI_OUTPUT=0x62085000,HGKI_WIDTH=32,HGKI_HEIGHT=32,
 HGKI_PITCH=128,HGKI_OUTPUT_BYTES=HGKI_PITCH*HGKI_HEIGHT};
enum {HGKI_OK,HGKI_ARGUMENT,HGKI_REUSED,HGKI_QUALIFICATION,HGKI_OWNER,
 HGKI_RESERVE,HGKI_PUBLISH,HGKI_SUBMIT,HGKI_COMPLETION,HGKI_READBACK,HGKI_CHANGED,
 HGKI_COLOR};

enum {HGKI_BR_WORDS=164,HGKI_BV_WORDS=158,HGKI_PREFIX_WORDS=213,HGKI_BODY_WORDS=34,HGKI_COMMAND_WORDS=247};
static const uint32_t hgki_br[] = {
 0x408e0701u,0x00000068u,0x400e1701u,0x00000000u,0x480e1001u,0x00000000u,
 0x400e1101u,0x00000080u,0x40ae0301u,0x10000402u,0x48ae0801u,0x00400000u,
 0x40ae0901u,0x00431800u,0x40ae0a01u,0x00800000u,0x40ae6c01u,0x00000000u,
 0x40ae0001u,0x10000000u,0x48980401u,0x00003f1fu,0x409e0001u,0x00100000u,
 0x409e2401u,0x01585600u,0x48a60001u,0x00008000u,0x40ae0601u,0x00000000u,
 0x40ae6a01u,0x00000000u,0x48ae6b01u,0x00000080u,0x48ae7301u,0x00000000u,
 0x48ab0201u,0x00000000u,0x48ab0101u,0x00000000u,0x40ab2201u,0x00000000u,
 0x48b31001u,0x00000000u,0x480ce201u,0x00000000u,0x400ce301u,0x00000000u,
 0x480ce401u,0x00000000u,0x400ce501u,0x00000000u,0x400ce601u,0x00000000u,
 0x480ce701u,0x00000000u,0x4880a701u,0x00000000u,0x40860001u,0x00004800u,
 0x48889901u,0x00000000u,0x488e0601u,0x02082000u,0x48960a01u,0x00000001u,
 0x40aa0201u,0x00000000u,0x48aa0301u,0x00000000u,0x40b60001u,0x13100000u,
 0x48960001u,0x02000000u,0x400e1201u,0x40000000u,0x40812001u,0x09510840u,
 0x48812101u,0x00000a62u,0x48ae0401u,0x00000000u,0x40ae0f01u,0x0000003fu,
 0x48ab2001u,0x00000000u,0x48b18201u,0x00000000u,0x40a9a801u,0x00000000u,
 0x40ab0001u,0x00000005u,0x48a00901u,0x00000003u,0x48881101u,0x00000010u,
 0x40811001u,0x00000002u,0x48881801u,0x00000000u,0x40923601u,0x00000000u,
 0x48930001u,0x00000000u,0x48930601u,0x00000001u,0x40b18301u,0x00000000u,
 0x4080af01u,0x00000000u,0x40960201u,0x00000000u,0x409e7201u,0x00000000u,
 0x40b30901u,0x000000a2u,0x40a9cb01u,0x000000fcu,0x40a00701u,0x00000000u,
 0x40886401u,0x00000000u,0x48b30202u,0x62081000u,0x00000000u,0x40b18002u,
 0x62081000u,0x00000000u,0x70c70002u,0x54000000u,0x00000006u,0x408e0401u,
 0x00000001u,0x408e0101u,0x00000000u,0x488e0901u,0x00000007u,0x48b60885u,
 0x00000000u,0x3fe05ff4u,0x3fa0ebeeu,0x3f5193edu,0x3f0243f0u,0x48988501u,
 0x00020000u,0x48988601u,0x00002000u,0x40a98001u,0x00000000u,0x40a82701u,
 0x00000102u,0x4088e501u,0x56600004u,0x70dc8006u,0x00009308u,0x0000c000u,
 0x00009309u,0x002b8000u,0x00009b09u,0x0000c000u,0x48881201u,0x00000000u,
 0x4888e401u,0x00000001u
};
static const uint32_t hgki_bv[] = {
 0x408e0701u,0x00000068u,0x400e1701u,0x00000000u,0x480e1001u,0x00000000u,
 0x400e1101u,0x00000080u,0x40ae0301u,0x10000402u,0x48ae0801u,0x00400000u,
 0x40ae0901u,0x00431800u,0x40ae0a01u,0x00800000u,0x40ae6c01u,0x00000000u,
 0x40ae0001u,0x10000000u,0x48980401u,0x00003f1fu,0x409e0001u,0x00100000u,
 0x409e2401u,0x01585600u,0x48a60001u,0x00008000u,0x40ae0601u,0x00000000u,
 0x40ae6a01u,0x00000000u,0x48ae6b01u,0x00000080u,0x48ae7301u,0x00000000u,
 0x48ab0201u,0x00000000u,0x48ab0101u,0x00000000u,0x40ab2201u,0x00000000u,
 0x48b31001u,0x00000000u,0x480ce201u,0x00000000u,0x400ce301u,0x00000000u,
 0x480ce401u,0x00000000u,0x400ce501u,0x00000000u,0x400ce601u,0x00000000u,
 0x480ce701u,0x00000000u,0x4880a701u,0x00000000u,0x40860001u,0x00004800u,
 0x48889901u,0x00000000u,0x488e0601u,0x02082000u,0x48960a01u,0x00000001u,
 0x40aa0201u,0x00000000u,0x48aa0301u,0x00000000u,0x40b60001u,0x13100000u,
 0x48960001u,0x02000000u,0x400e1201u,0x40000000u,0x40812001u,0x09510840u,
 0x48812101u,0x00000a62u,0x48ae0401u,0x00000000u,0x40ae0f01u,0x0000003fu,
 0x48ab2001u,0x00000000u,0x48b18201u,0x00000000u,0x40a9a801u,0x00000000u,
 0x40ab0001u,0x00000005u,0x48a00901u,0x00000003u,0x48881101u,0x00000010u,
 0x40811001u,0x00000002u,0x48881801u,0x00000000u,0x40923601u,0x00000000u,
 0x48930001u,0x00000000u,0x48930601u,0x00000001u,0x40b18301u,0x00000000u,
 0x4080af01u,0x00000000u,0x40960201u,0x00000000u,0x409e7201u,0x00000000u,
 0x40b30901u,0x000000a2u,0x40a9cb01u,0x000000fcu,0x40a00701u,0x00000000u,
 0x40886401u,0x00000000u,0x48b30202u,0x62081000u,0x00000000u,0x40b18002u,
 0x62081000u,0x00000000u,0x70c70002u,0x54000000u,0x00000006u,0x408e0401u,
 0x00000001u,0x408e0101u,0x00000000u,0x488e0901u,0x00000007u,0x48b60885u,
 0x00000000u,0x3fe05ff4u,0x3fa0ebeeu,0x3f5193edu,0x3f0243f0u,0x48988501u,
 0x00020000u,0x48988601u,0x00002000u,0x40a98001u,0x00000000u,0x40a82701u,
 0x00000102u,0x70dc8006u,0x00009308u,0x0000c000u,0x00009309u,0x002b8000u,
 0x00009b09u,0x0000c000u
};
static const uint32_t hgki_prefix[] = {
 0x70970001u,0x00000003u,0x70460001u,0x00000019u,0x70460001u,0x00000018u,
 0x70460001u,0x00000028u,0x70460001u,0x00000033u,0x70268000u,0x48ab1f01u,
 0x01fffeffu,0x70268000u,0x408e0701u,0x00000068u,0x400e1701u,0x00000000u,
 0x480e1001u,0x00000000u,0x400e1101u,0x00000080u,0x40ae0301u,0x10000402u,
 0x48ae0801u,0x00400000u,0x40ae0901u,0x00431800u,0x40ae0a01u,0x00800000u,
 0x40ae6c01u,0x00000000u,0x40ae0001u,0x10000000u,0x48980401u,0x00003f1fu,
 0x409e0001u,0x00100000u,0x409e2401u,0x01585600u,0x48a60001u,0x00008000u,
 0x40ae0601u,0x00000000u,0x40ae6a01u,0x00000000u,0x48ae6b01u,0x00000080u,
 0x48ae7301u,0x00000000u,0x48ab0201u,0x00000000u,0x48ab0101u,0x00000000u,
 0x40ab2201u,0x00000000u,0x48b31001u,0x00000000u,0x480ce201u,0x00000000u,
 0x400ce301u,0x00000000u,0x480ce401u,0x00000000u,0x400ce501u,0x00000000u,
 0x400ce601u,0x00000000u,0x480ce701u,0x00000000u,0x4880a701u,0x00000000u,
 0x40860001u,0x00004800u,0x48889901u,0x00000000u,0x488e0601u,0x02082000u,
 0x48960a01u,0x00000001u,0x40aa0201u,0x00000000u,0x48aa0301u,0x00000000u,
 0x40b60001u,0x13100000u,0x48960001u,0x02000000u,0x400e1201u,0x40000000u,
 0x40812001u,0x09510840u,0x48812101u,0x00000a62u,0x48ae0401u,0x00000000u,
 0x40ae0f01u,0x0000003fu,0x48ab2001u,0x00000000u,0x48b18201u,0x00000000u,
 0x40a9a801u,0x00000000u,0x40ab0001u,0x00000005u,0x48a00901u,0x00000003u,
 0x48881101u,0x00000010u,0x40811001u,0x00000002u,0x48881801u,0x00000000u,
 0x40923601u,0x00000000u,0x48930001u,0x00000000u,0x48930601u,0x00000001u,
 0x40b18301u,0x00000000u,0x4080af01u,0x00000000u,0x40960201u,0x00000000u,
 0x409e7201u,0x00000000u,0x40b30901u,0x000000a2u,0x40a9cb01u,0x000000fcu,
 0x40a00701u,0x00000000u,0x40886401u,0x00000000u,0x48b30202u,0x62081000u,
 0x00000000u,0x40b18002u,0x62081000u,0x00000000u,0x70c70002u,0x54000000u,
 0x00000006u,0x408e0401u,0x00000001u,0x408e0101u,0x00000000u,0x488e0901u,
 0x00000007u,0x48b60885u,0x00000000u,0x3fe05ff4u,0x3fa0ebeeu,0x3f5193edu,
 0x3f0243f0u,0x48988501u,0x00020000u,0x48988601u,0x00002000u,0x40a98001u,
 0x00000000u,0x40a82701u,0x00000102u,0x48930a01u,0x00000000u,0x488c3401u,
 0x00000000u,0x4088e501u,0xc0000000u,0x70dc8006u,0x00009308u,0x00020000u,
 0x00009309u,0x001e0000u,0x00009b09u,0x00020000u,0x70438003u,0x00040000u,
 0x00000000u,0x00000000u,0x709b0002u,0x00000002u,0x00000001u,0x70970001u,
 0x08000001u,0x70d58003u,0x62082000u,0x00000000u,0x001000a4u,0x70970001u,
 0x00000002u,0x70d58003u,0x62083000u,0x00000000u,0x0010009eu,0x70970001u,
 0x00000003u,0x70b98003u,0x82000000u,0x00000018u,0x00000010u,0x70d58003u,
 0x00000000u,0x00000000u,0x00000000u,0x70d58003u,0x00000000u,0x00000000u,
 0x00200000u,0x70970001u,0x08000001u
};
static const uint32_t hgki_body[] = {
 0x488c0101u,0x00000000u,0x408c0001u,0x00f03080u,0x48840001u,0x00f03080u,
 0x48b2d201u,0x20000000u,0x40a9bf01u,0x0000f180u,0x488c2c04u,0x000000ffu,
 0x00000000u,0x00000000u,0x000000ffu,0x408c1704u,0x00000030u,0x62085000u,
 0x00000000u,0x00000002u,0x488c2083u,0x00000000u,0x00000000u,0x00000000u,
 0x48840502u,0x00000000u,0x001f001fu,0x702c0001u,0x00000003u,0x70460001u,
 0x00000021u,0x70460001u,0x00000031u,0x70268000u
};
static const uint32_t hgki_ib[] = {
 0x70bf8003u,0x62084000u,0x00000000u,0x000000f7u
};
/* The source-qualified 247 DWORDs above stay byte-for-byte unchanged. The
 * optional diagnostic only interposes known CP_MEM_WRITE/WAIT_MEM_WRITES
 * packets. Linux/OnePlus source-bound host canaries already use these same
 * opcodes; their writes target only the explicitly owned first 32 guard bytes,
 * never the output image. A marker is not a completion or rendering fence.
 */
static inline const uint32_t *hgki_source_ib(void) {return hgki_ib;}
enum {HGKI_PROGRESS_MARKERS=HGKI_PROGRESS?8:0,HGKI_MARKER_BYTES=HGKI_PROGRESS_MARKERS*4,
 HGKI_SELECTED_COMMAND_WORDS=HGKI_COMMAND_WORDS+HGKI_PROGRESS_MARKERS*5};
static inline unsigned hgki_marker_boundary(unsigned i) {
 /* Source DWORD offsets: before/after first BOTH, after cache WFI, after
  * static+CCU setup, after all amble setup, before/after BLIT, after final WFI. */
 const unsigned positions[]={0,2,11,185,213,240,242,247};
 return i<8?positions[i]:UINT32_MAX;
}
static inline uint32_t hgki_marker_value(unsigned i) {return i<8?0x4b490101u+i:0;}
static inline uint32_t hgki_source_word(unsigned i) {
 return i<HGKI_PREFIX_WORDS?hgki_prefix[i]:
  i<HGKI_COMMAND_WORDS?hgki_body[i-HGKI_PREFIX_WORDS]:0;
}
static inline uint32_t hgki_command_word(unsigned i) {
 if(i>=HGKI_SELECTED_COMMAND_WORDS)return 0;
#if HGKI_PROGRESS
 for(unsigned m=0;m<HGKI_PROGRESS_MARKERS;m++) {
  unsigned at=hgki_marker_boundary(m)+5*m;
  if(i<at)return hgki_source_word(i-5*m);
  if(i<at+5) {
   const uint32_t packet[]={0x703d8003u,HGKI_BASE+4*m,0,hgki_marker_value(m),0x70928000u};
   return packet[i-at];
  }
 }
 return hgki_source_word(i-5*HGKI_PROGRESS_MARKERS);
#else
 return hgki_source_word(i);
#endif
}
#if HGKI_PROGRESS
static const uint32_t hgki_progress_ib[] = {
 0x70bf8003u,0x62084000u,0x00000000u,HGKI_SELECTED_COMMAND_WORDS
};
/* Existing consumers receive the selected fixed count without a mutable
 * packet API. hgki_source_ib still names the unchanged source-qualified IB. */
#define hgki_ib hgki_progress_ib
#endif

struct hgki_qualification {
 uint32_t chip_id,class_cursor;
 unsigned normal_owned,cp_init_idle,authenticated_zap,mode_exit_idle,kmd_preemption_disabled;
};
struct hgki_io {
 void *cookie;
 int (*guard)(void *); /* Existing fresh root/route/power/CM3/IRQ/fault owner proof. */
 int (*reserve_fixed)(void *,uint32_t,uint32_t,uint32_t); /* base, bytes, virgin cursor. */
 int (*publish_clean_poc)(void *,uint32_t,const uint8_t *,unsigned); /* Exact page, PoC+verify. */
 int (*submit_fixed_ib)(void *,const uint32_t *,unsigned); /* 4 DW into existing owned ring. */
 int (*bounded_idle)(void *); /* Existing RPTR/WPTR, RBBM, GMU-busy, IRQ/SMMU fault proof. */
 int (*readback_invalidate_poc)(void *,uint32_t,uint8_t *,unsigned); /* Entire retained image. */
};
struct hgki_result {
 unsigned started,code,phase,guards,reserve_attempted,retained,published_pages;
 unsigned submit_attempted,submit_returned,completed,readback_valid,verified;
 int callback_code;
 uint32_t output_crc,first_bad;
 unsigned expected,actual;
};
static inline uint32_t hgki_crc32(const uint8_t *p,size_t n) {
 uint32_t c=~0u;for(size_t i=0;i<n;i++){c^=p[i];for(unsigned j=0;j<8;j++)c=(c>>1)^(0xedb88320u&(0u-(c&1u)));}return ~c;
}
static inline unsigned hgki_qualified(const struct hgki_qualification *q) {
 return q && q->chip_id==0x43051401u && q->class_cursor==HGKI_CLASS_CURSOR &&
  q->normal_owned==1 && q->cp_init_idle==1 && q->authenticated_zap==1 &&
  q->mode_exit_idle==1 && q->kmd_preemption_disabled==1;
}
static inline uint8_t hgki_word_byte(const uint32_t *p,unsigned n,unsigned byte) {
 return byte<4*n?(uint8_t)(p[byte/4]>>(8*(byte&3))):0;
}
static inline uint8_t hgki_initial_byte(unsigned offset) {
 unsigned page=offset/HGKI_PAGE,byte=offset%HGKI_PAGE;
 if(page==0)return 0xa5;
 if(page==1)return 0; /* Explicit owned zero-border BO. No textures in solid clear. */
 if(page==2)return hgki_word_byte(hgki_br,HGKI_BR_WORDS,byte);
 if(page==3)return hgki_word_byte(hgki_bv,HGKI_BV_WORDS,byte);
 if(page==4){
  return byte<4*HGKI_SELECTED_COMMAND_WORDS?(uint8_t)(hgki_command_word(byte/4)>>(8*(byte&3))):0;
 }
 if(page==5)return 0x6d; /* CPU never initializes this page to the expected red. */
 return 0x5a;
}
static inline unsigned hgki_buffer(const void *cpu,size_t bytes) {
 return cpu && bytes==HGKI_BYTES && (uintptr_t)cpu<=UINTPTR_MAX-HGKI_BYTES;
}
static inline unsigned hgki_build(void *cpu,size_t bytes) {
 if(!hgki_buffer(cpu,bytes))return HGKI_ARGUMENT;
 uint8_t *p=(uint8_t*)cpu;for(unsigned i=0;i<HGKI_BYTES;i++)p[i]=hgki_initial_byte(i);
 return HGKI_OK;
}
static inline unsigned hgki_verify(const void *cpu,size_t bytes,struct hgki_result *r) {
 if(!r || !hgki_buffer(cpu,bytes))return HGKI_ARGUMENT;
 const uint8_t *p=(uint8_t*)cpu;r->verified=0;r->first_bad=UINT32_MAX;r->output_crc=hgki_crc32(p+5*HGKI_PAGE,HGKI_OUTPUT_BYTES);
 for(unsigned i=0;i<HGKI_BYTES;i++) {
  unsigned image=i>=5*HGKI_PAGE && i<6*HGKI_PAGE;
  unsigned expected=image?((i&3)==0 || (i&3)==3?255:0):hgki_initial_byte(i);
#if HGKI_PROGRESS
  if(i<HGKI_MARKER_BYTES)expected=(uint8_t)(hgki_marker_value(i/4)>>(8*(i&3)));
#endif
  if(p[i]!=expected){r->first_bad=i;r->expected=expected;r->actual=p[i];return image?HGKI_COLOR:HGKI_CHANGED;}
 }
 if(r->output_crc!=0xe843b26au)return HGKI_COLOR;
 r->verified=1;return HGKI_OK;
}
static inline unsigned hgki_guard(const struct hgki_io *io,struct hgki_result *r) {
 r->guards++;r->callback_code=io->guard(io->cookie);return r->callback_code?HGKI_OWNER:HGKI_OK;
}
static inline unsigned hgki_run(const struct hgki_io *io,const struct hgki_qualification *q,
 void *cpu,size_t bytes,struct hgki_result *r) {
 if(!r)return HGKI_ARGUMENT;
 if(r->started)return HGKI_REUSED;
 *r=(struct hgki_result){.started=1,.first_bad=UINT32_MAX};
 if(!io || !io->guard || !io->reserve_fixed || !io->publish_clean_poc ||
  !io->submit_fixed_ib || !io->bounded_idle || !io->readback_invalidate_poc ||
  !hgki_buffer(cpu,bytes))return r->code=HGKI_ARGUMENT;
 if(!hgki_qualified(q))return r->code=HGKI_QUALIFICATION;
 r->phase=1;r->code=hgki_guard(io,r);if(r->code)return r->code;
 if(hgki_build(cpu,bytes))return r->code=HGKI_ARGUMENT;
 r->phase=2;r->code=hgki_guard(io,r);if(r->code)return r->code;
 /* A callback failure may have reserved partially. Never infer it is reusable. */
 r->reserve_attempted=r->retained=1;
 r->callback_code=io->reserve_fixed(io->cookie,HGKI_BASE,HGKI_BYTES,HGKI_CLASS_CURSOR);
 if(r->callback_code)return r->code=HGKI_RESERVE;
 r->phase=3;
 for(unsigned i=0;i<HGKI_PAGES;i++) {
  r->code=hgki_guard(io,r);if(r->code)return r->code;
  r->callback_code=io->publish_clean_poc(io->cookie,HGKI_BASE+i*HGKI_PAGE,(const uint8_t *)cpu+i*HGKI_PAGE,HGKI_PAGE);
  if(r->callback_code)return r->code=HGKI_PUBLISH;
  r->published_pages++;
 }
 r->phase=4;r->code=hgki_guard(io,r);if(r->code)return r->code;
 r->submit_attempted=1;
 r->callback_code=io->submit_fixed_ib(io->cookie,hgki_ib,4);
 if(r->callback_code)return r->code=HGKI_SUBMIT;
 r->submit_returned=1;
 r->phase=5;r->code=hgki_guard(io,r);if(r->code)return r->code;
 r->callback_code=io->bounded_idle(io->cookie);
 if(r->callback_code)return r->code=HGKI_COMPLETION;
 r->completed=1;
 r->phase=6;r->code=hgki_guard(io,r);if(r->code)return r->code;
 r->callback_code=io->readback_invalidate_poc(io->cookie,HGKI_BASE,(uint8_t*)cpu,HGKI_BYTES);
 if(r->callback_code)return r->code=HGKI_READBACK;
 r->readback_valid=1;r->code=hgki_guard(io,r);if(r->code)return r->code;
 r->phase=7;r->code=hgki_verify(cpu,bytes,r);if(r->code)return r->code;
 r->phase=8;return HGKI_OK;
}
#endif

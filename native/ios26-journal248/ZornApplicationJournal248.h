/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#pragma once
#include <stdint.h>

enum { ZornJournalCapacity248=65536, ZornJournalSlots248=256,
    ZornJournalWriteLimit248=16384, ZornJournalChunk248=768, ZornJournalVectors248=8 };
enum { ZornJournalBusy248=1, ZornJournalCapacityLost248=2,
    ZornJournalSlotsLost248=4, ZornJournalCopyLost248=8,
    ZornJournalUnsupported248=16, ZornJournalBadToken248=32, ZornJournalLate248=64 };
typedef struct { uint64_t address,bytes; } ZornJournalVector248;
typedef struct { uint32_t index,bytes; void *target; } ZornJournalTicket248;
typedef struct {
    uint64_t unique,seen_bytes;
    uint32_t pid,reserved,published,records,pending,gaps,exited,exit_status,crc32,offset,bytes;
} ZornJournalSnapshot248;
#ifdef __cplusplus
extern "C" {
#endif
int zorn26_journal_begin248(uint64_t,uint32_t,uint64_t,unsigned,ZornJournalTicket248 *);
void zorn26_journal_finish248(uint32_t,unsigned);
void zorn26_journal_exit248(uint64_t,uint32_t,uint32_t);
int zorn26_journal_snapshot248(uint32_t,void *,uint32_t,ZornJournalSnapshot248 *);
#ifdef __cplusplus
}
#endif

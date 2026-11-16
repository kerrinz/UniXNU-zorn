/* SPDX-License-Identifier: MIT */
#ifndef ZORN_COMMAND_DB_FILE_H
#define ZORN_COMMAND_DB_FILE_H
#include <stddef.h>
#include <stdint.h>
/* Unselected,allocation-free FILE decoder. Not a platform memory provider.
 * Input storage must already be CPU-readable,immutable and retained through
 * the call. This API obtains no ownership/coherency/access rights and never
 * maps or dereferences a device address. Offsets below are FILE offsets.
 * All input/output storage must be disjoint. Failure leaves outputs unchanged.
 * No expected-version,resource-name,voltage/rate or board policy is selected.
 * Successful parsing is not snapshot authenticity or GPU readiness.
 */
enum { ZCDF_HEADER_BYTES=144,ZCDF_MAX_ENTRIES=4096,ZCDF_MAX_FILE_BYTES=4194304 };
typedef enum { ZCDF_OK,ZCDF_ARGUMENT,ZCDF_ALIAS,ZCDF_FORMAT,ZCDF_RANGE,
    ZCDF_BUDGET,ZCDF_CAPACITY } ZornCommandDbFileStatus;
typedef struct {
    uint8_t raw[24];
    uint32_t row_index,entry_index;
    size_t record_file_offset,aux_file_offset,aux_bytes;
    uint32_t aux_overlaps_record_table;
} ZornCommandDbFileEntry;
typedef struct {
    uint8_t header_raw[ZCDF_HEADER_BYTES];
    size_t source_bytes,entry_count;
    uint32_t searched_rows;
    uint32_t snapshot_qualified,expected_version_qualified,hardware_qualified;
} ZornCommandDbFileSummary;
/* The fixed budgets bound offline review work,not a K80 hardware limit.
 * entries may be NULL only when capacity is0. No byte copy is performed until
 * EVERY searched row/entry and capacity/alias check has passed. */
ZornCommandDbFileStatus ZornCommandDbDecodeFile(const uint8_t *data,size_t bytes,
    ZornCommandDbFileEntry *entries,size_t capacity,ZornCommandDbFileSummary *summary);
#endif

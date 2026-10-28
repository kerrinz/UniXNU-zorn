// SPDX-License-Identifier: BSD-2-Clause-Patent
// RamBlock's optional board-provider bridge. Default boot mode remains off.
// The C++ provider checks exact geometry/header and confines every command.
#include <stdint.h>
extern unsigned zorn_data_store_mode(void);
extern int zorn_data_store_open(uint64_t, uint64_t *, const char **);
extern int zorn_data_store_read(uint64_t, uint32_t, void *);
extern int zorn_data_store_write(uint64_t, uint32_t, const void *);
extern int zorn_data_store_sync(void);
extern unsigned zorn_data_store_gpt_check(void);
unsigned native_ufs_store_mode(void) { return zorn_data_store_mode(); }
int native_ufs_store_open(uint64_t blocks, uint64_t *first, const char **why)
{ return zorn_data_store_open(blocks, first, why); }
int native_ufs_store_read(uint64_t offset, uint32_t blocks, void *out)
{ return zorn_data_store_read(offset, blocks, out); }
int native_ufs_store_write(uint64_t offset, uint32_t blocks, const void *data)
{ return zorn_data_store_write(offset, blocks, data); }
int native_ufs_store_sync(void) { return zorn_data_store_sync(); }
unsigned native_ufs_store_gpt_check(void) { return zorn_data_store_gpt_check(); }

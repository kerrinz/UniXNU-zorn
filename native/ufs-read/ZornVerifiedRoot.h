// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include <stddef.h>
#include <stdint.h>
#include <sys/types.h>
#ifdef __cplusplus
extern "C" {
#endif
int zorn_verified_open(unsigned index, uint64_t image_bytes);
int zorn_verified_block(unsigned index, uint64_t offset, const void *data, size_t bytes);
dev_t zorn_ufs_window_device(unsigned index);
int zorn_ufs_window_healthy(unsigned index);
uint64_t zorn_ufs_window_bytes(unsigned index);
int zorn_verified_window_ready(unsigned index);
int zorn_systemos_iokit_device(const char *uuid, dev_t *, char *, size_t);
int zorn_systemos_iokit_matches(dev_t device, const char *uuid);
int native_verified_block_root_authorized(dev_t device);
int native_verified_block_volume_device(const char *uuid, dev_t *, char *, size_t);
int native_verified_block_manifest_sha384(dev_t device, const char *uuid, uint8_t digest[48]);
#ifdef __cplusplus
}
#endif

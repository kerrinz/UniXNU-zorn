// SPDX-License-Identifier: BSD-2-Clause-Patent
// One WRITE(10) with FUA, 4096 bytes, to the single armed log LBA. No SYNCHRONIZE CACHE.
static bool houjiUfsLogCommandAllowed(const uint8_t *u, unsigned n, unsigned dir,
                                    uint32_t bytes, bool enabled, bool armed) {
  if (!enabled || !armed || !u || n < 32 || dir != 1 || bytes != 4096 || !gLogBlocks) return false;
  if (u[0] != 1 || u[2] != 0 || u[1] != 0x20 || u[3] != 0) return false;
  uint32_t transfer = (uint32_t(u[12]) << 24) | (uint32_t(u[13]) << 16) |
      (uint32_t(u[14]) << 8) | u[15];
  if (transfer != 4096) return false;
  const uint8_t *c = u + 16;
  if (c[0] != 0x2a || c[1] != 0x08 || c[6] || c[7] || c[8] != 1 || c[9]) return false;
  uint32_t lba = (uint32_t(c[2]) << 24) | (uint32_t(c[3]) << 16) | (uint32_t(c[4]) << 8) | c[5];
  if (lba == gLogLba) return true;
  return gRecoveryArmed && gMiscLba != 0 && lba == gMiscLba;
}

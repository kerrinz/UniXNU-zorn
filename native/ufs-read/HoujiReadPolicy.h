// SPDX-License-Identifier: BSD-2-Clause-Patent
static bool houjiUfsReadCommandAllowed(const uint8_t *u, unsigned n, unsigned dir, uint32_t bytes)
{
  if (!u || n < 32 || dir == 1 || dir > 2 || bytes > 131072 || (bytes & 4095) ||
      u[8] || u[10] || u[11]) return false;
  if (u[0] == 0) return dir == 0 && bytes == 0 && u[1] == 0 && u[2] == 0 && u[3] == 1;
  if (u[0] == 0x16) return dir == 0 && bytes == 0 && u[1] == 0 && u[2] == 0 &&
    u[3] == 1 && u[5] == 1 && u[12] == 3 && u[13] == 2 && u[14] == 0 && u[15] == 0;
  if (u[0] != 1 || u[3] != 0 || u[1] != (bytes ? 0x40 : 0) || dir != (bytes ? 2U : 0U)) return false;
  uint32_t transfer = (uint32_t(u[12]) << 24) | (uint32_t(u[13]) << 16) | (uint32_t(u[14]) << 8) | u[15];
  if (transfer != bytes) return false;
  const uint8_t *c = u + 16;
  if (c[0] == 0x28 && u[2] == 0 && bytes) {
    if (c[1] || c[6] || c[9]) return false;
    for (unsigned i=10;i<16;i++) if(c[i]) return false;
    uint32_t lba = (uint32_t(c[2]) << 24) | (uint32_t(c[3]) << 16) | (uint32_t(c[4]) << 8) | c[5];
    unsigned count = (unsigned(c[7]) << 8) | c[8];
    if (bytes != count * 4096U || count == 0 || count > 32) return false;
    // GPT header is one block. Other reads are 1..32 blocks. Writes never reach here.
    if (lba == 1) return count == 1;
    return true;
  }
  if (bytes || dir || (c[0] != 0 && c[0] != 0x1B)) return false;
  if (u[2] != (c[0] == 0x1B ? 0xD0 : 0)) return false;
  for (unsigned i=1;i<16;i++) if(c[i] != ((c[0] == 0x1B && i == 4) ? 0x10 : 0)) return false;
  return true;
}

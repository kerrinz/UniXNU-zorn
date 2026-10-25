// SPDX-License-Identifier: BSD-2-Clause-Patent
// Zorn never arms the houji log writer. SYNCHRONIZE CACHE and WRITE stay refused.
static bool houjiUfsLogCommandAllowed(const uint8_t *, unsigned, unsigned,
                                    uint32_t, bool, bool) {
  return false;
}

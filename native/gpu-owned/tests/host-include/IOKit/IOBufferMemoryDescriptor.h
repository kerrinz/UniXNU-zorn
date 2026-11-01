// SPDX-License-Identifier: BSD-2-Clause-Patent
// Host-only shim; not an Apple ABI or hardware ownership implementation.
#include "XnuMemoryFixture.h"
using IODirection=IOOptionBits;
constexpr IOOptionBits kIOMemoryPersistent=0x00010000;

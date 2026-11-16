// SPDX-License-Identifier: BSD-2-Clause-Patent
#include "ZornGen7ProcessTables26.h"
OSDefineMetaClassAndStructors(ZornGen7ProcessTables26,OSObject)
void ZornGen7ProcessTables26::free()
{
    // Constructor failures before pinning only. The domain lifecycle must
    // later supply normal retirement;never release an uncertain partial.
    if(!pinned_)OSObject::free();
}

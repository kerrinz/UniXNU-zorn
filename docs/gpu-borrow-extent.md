# Borrowed-buffer interval representability

NativeAdrenoMemory::borrow accepts a mapping,physical start and byte count,then allocates span metadata,publishes backing fields and clears the range. Its original preflight checked nonzero/alignment but not whether the last byte fits either integer domain. No retained exact caller was found; this is a public argument-contract defect,not a demonstrated K80 caller fault.

The independent UNAPPLIED candidate adds bytes-1 <= UINTPTR_MAX-mapping_integer and uint64_t(bytes-1) <= UINT64_MAX-physical after the existing nonzero/alignment check,before allocation or any backing fields/bzero. It does not establish valid mappings,physical ownership,OAS,IOVA,coherency or clearing permission. It neither changes publication order nor invents recovery if a caller supplies inaccessible memory;bzero has no status-return transaction contract here.

Only generic unsigned interval arithmetic was executed. Two aligned nonzero scalar pairs pass old shape checks but have unrepresentable last bytes;the subtraction predicate refuses them. Six inclusive/zero/alignment controls,ASan/UBSan,three source controls and one changed real-header iOS17 NativeMemory object pass. Integer starts are not converted into pointers or supplied as hardware addresses. No mapped buffer,physical address,owner,successful provider/native object,borrow,bzero,allocator,getter,prepare or cache operation was modeled or executed. Object remains unlinked/unexecuted.

Original catalog/pins,32 independent driver patches,eight profiles,ABI/layout,wire/log/carrier and runtime policies remain unchanged. This source preflight is not GPU or hardware qualification.

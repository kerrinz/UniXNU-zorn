# Native table preparation and visibility source

This unselected source composes the current NativeAdrenoPrepareSmmuMemory API
with a persistent ArmSmmu4KLiveVisibility publisher. Both selectors default to
zero. A selected bridge asks the actual compiled publisher object for its
software mode before any native preparation. This checks configuration only.

The caller must retain the actual inactive table allocation, exclusive arena,
state, bridge and every possible callback through their complete lifetimes.
Geometry is forwarded without choosing a bank, ASID, OAS or IOVA policy. Valid
typed objects and stable mappings remain preconditions; range checks do not
authenticate arbitrary pointers. Table storage and metadata must be disjoint.

The bridge keeps the legacy callback private. Only successful preparation and
persistent publisher binding can export the member callback. The raw32 API
IOReturn and adapter/bind errors remain separate. The upstream preparation API
itself folds some ArmSmmu4K statuses; this bridge cannot recover those details.
Failure after preparation poisons state and retains/quarantines the table,
without retry, reset, reference release or destructor cleanup. Device reference
accounting and CPU cache publication do not prove powered/stopped masters,
context routing, DMA completion or hardware ownership. Native calls can block.

Host checks execute refusal paths only, using forbidden-entry traps that never
return native statuses or addresses. Selected preparation, cache publication,
callbacks and success/post-call failure paths have not executed. Independent
iOS17 objects and relocatable links are not a final kernel or hardware trial.
The private reports add no wire fields and pass no pointers across EFI/Darwin.
The parent CPU-backing profile and previous capsules remain unchanged.

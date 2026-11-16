# Gen7 supplied-reservation quarantine ledger

This fixed32-slot CPU ledger records caller-supplied ranges and borrowed real
NativeAdrenoMemory pointers. It selects/generates/returns no address or device
handle and calls no native method. Include this directory, its parent gmu and
the runtime directory plus the actual upstream native headers when compiling.
No component or runtime caller is selected.

The full rounded reservation, including unmapped tail, participates in overlap
checks and remains recorded after local failure. Key is decoded kind plus GMU
request handle. Reusing a key with changed request/range/backing pointer refuses;
only a valid changed message header may differ. Descriptor aliases, capacity32,
bad bounds and output/metadata aliases refuse. Failed retries never clear the
first signed64 adapter error. No reset/release API or destructor cleanup exists.
A local index names CPU metadata only; no index is a GMU/GPU/HFI handle.

This ledger does not hold native references or quarantine/release real backing
objects. The real caller must keep descriptors, backing and reservation alive
under its actual domain/lifetime/resource gate. The code cannot prove those
conditions. CPU pointer ranges and supplied GMU-space scalars are distinct and
are never compared as the same address space. Range checks authenticate nothing.
Native attempted/status-available/mapping-complete/runtime-complete stay zero;
all recorded entries have unknown native status. Reports contain no addresses.

Host tests seed only integer-interval metadata with deliberately unbacked real
native-class objects to exercise refusals, masks and local error retention.
No successful backing allocator, native reference/map/address/handle model or
provider stub is supplied. Independent iOS17 compilation and relocatable links
are not final kernel ABI, hardware ownership or device execution evidence.
Previous profiles/capsules and query/HFI/log formats remain unchanged.

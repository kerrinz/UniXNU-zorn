# Exported GMU I/O offset contract

The exact retained NativeAdrenoGmuPlatform header promises each exported access stays inside its window. Both exported size_t-offset callbacks used at+4, which wraps at SIZE_MAX-3 before the declared-byte comparison. This is a public callback-table input contract defect; no existing K80 startup trigger or live MMIO access was reproduced.

The independent UNAPPLIED candidate replaces only the two integer guards with aligned offset <= bytes and bytes-offset >= 4. It preserves callback signatures, null paths, accesses, bind publication, services, class layout and all runtime selections. It is not combined with other patches.

Three pure integer witnesses across declared byte counts 4,64,UINT32_MAX-3 pass the original predicate and are refused after repair. Eight inclusive/end/alignment/zero controls, ASan/UBSan, three source-corruption controls and one changed real-header iOS17 ARM64 module pass. Fixtures extract only the integer predicate: no native object, bind, callback, base/window/address, successful provider or MMIO operation is modeled or executed. The target object is unlinked and unexecuted.

Caller assessment: ShengGmuIo exposes unrestricted size_t byte_offset. The retained Sheng source forwards size_t, derives core offsets from uint32_t words and subtracts a generated delta, and uses generated setup write offsets. Its exact generated ShengGmuSource.h is absent. No whole-startup offset bound or K80 register geometry is inferred. This exported-table promise differs from the previously closed private Service SMMU exact-caller-chain hypothetical. No old fits or firmware suite was rerun.

Catalog and working submodule pins, original 32 patches, eight profiles, policies, wire/log/carrier and role API remain unchanged. Bounds checks do not establish mapping, owner/coherency, power, stop or hardware qualification.

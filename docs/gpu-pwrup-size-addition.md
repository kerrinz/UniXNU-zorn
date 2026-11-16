# Public power-up size helper addition

The requested GMU Service partial-map review found no new leak in the reviewed paths. Missing device memory,map failure or bases allocation failure calls stop(),which resets all retained map members,zeros count and calls base stop. Parse failure precedes the map loop. Local SDK source shows borrowed device-memory array lookup,shared-pointer reset releasing the held map,and default C++ member destruction. No live service,release/map/unmap operation or quiescence guarantee was exercised or added.

Continued independent source review found requiredBytes casts counts.ifpc+counts.preemption only after uint32_t addition,so the public size helper reports a wrapped result for wide count tuples. The isolated UNAPPLIED repair widens both operands before addition. On the64-bit target the full uint32 count-domain expression fits size_t. This changes no count policy or serialized layout.

Three scalar tuples give wrong original sums and correct repaired sums;three legal serializer-count controls stay identical. Extracted size arithmetic,ASan/UBSan and one changed iOS17 Pwrup module pass. pack already rejects oversized counts before calling this helper,so this is not a reproduced pack overrun or a claim existing K80 callers reach it. No buildA740/pack,register list,hardware value,callback,native object or provider was run or modeled. The previous byte-alignment candidate is not combined;this is an independent original-source patch. Target object is unlinked/unexecuted.

No rate/vote/bin/variant,power-up policy or runtime/component selection is generated. Catalog/pins,32patches,eight profiles,wire/log/carrier and hardware state remain unchanged.

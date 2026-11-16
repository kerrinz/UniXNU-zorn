# Byte-aligned list serializer stores

The requested firmware-view alias review found only the retained Service caller: separate local rules,member view and external embedded image. No concrete overlap was established, so no alias repair,validate call or SHA execution was introduced. Review continued to the independent Pwrup serializer's byte-output contract.

NativeAdrenoPwrupList::pack accepts uint8_t output and documents an exact byte image without requiring4-byte alignment. It cast output+16 to uint32_t* and stored through it. The independent UNAPPLIED candidate uses a byte cursor plus memcpy of each uint32_t. It preserves native byte order,all counts,capacity/error ordering,payload field order,lock/header bytes and callbacks. No list geometry or K80 policy was selected.

Only the individual store operation was executed in a raw-byte fixture. The original operation on a one-byte-offset buffer triggers UBSan misaligned-store failure; its exact stderr is retained as an expected negative result. The replacement passes four byte alignments,byte-order comparisons and canaries with ASan/UBSan. Three source controls and one changed real-header iOS17 Pwrup object pass. The full pack/buildA740 methods were not executed;no register arrays,policy list,hardware value,read callback,native provider or success model was constructed. A synthetic32-bit byte pattern has no register meaning and is never exported as a runtime list. The target object is unlinked/unexecuted.

This is a public byte-buffer contract defect,not an observed K80 unaligned producer. Catalog/pins,original32 independent patches,eight profiles,ABI/layout,wire/log/carrier,policy generation and runtime choices remain unchanged. No power/rate/vote/bin/variant selection or hardware qualification follows.

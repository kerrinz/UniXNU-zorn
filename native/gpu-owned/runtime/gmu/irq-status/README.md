# Supplied Gen7 GMU AO status classification

This unselected CPU-only function classifies a supplied32-bit scalar using the
pinned reference AO consumer: watchdog0, AHB fence3, host AHB bus5. Every other
bit stays unhandled by that consumer, including named RSCC1/DBD4. Raw bits are
preserved. AHB fence3 indicates a separate real AHB-fence status is needed;
none is invented. It is not HW_FENCE Tx/Rx queue or CP timestamp completion.

There is no register address, read/write/ack/mask/NMI/watchdog operation,
IRQ handler/source, stop proof or provider callback. It cannot establish that
a scalar was actually observed. Return OK means valid CPU classification only.
The current NativeAdrenoIrq RBBM/CP domain has different raw bits and must not
receive this AO status. This adds no query/HFI/log encoding or runtime caller.

The source is a fixed OEM reference, not Xiaomi stock attestation. Only exact
source/mask binding, CPU scalar cases and independent iOS17 target artifacts
are checked. Actual IRQ routing, powered ownership, masked/clear semantics,
auxiliary registers and readable-failure protection remain external gaps.
Existing profiles/capsules and both native repair patches are unchanged.

# Framed timeline destination extent

The retained Ring accepts fence buffers as small as64 bytes. Public setTimeline(true) enables timestamp packets without validating their destination extent. submitWords previously reserved ring command words but did not check fence buffer capacity before emitting framed timestamp packets. The timeline reader already required1536 declared bytes, so its read guard did not protect the producer.

The fixed source layout is512-byte prefix plus64 slots of16 bytes. The last end stamp occupies bytes1528..1535. These are byte offsets in the retained format, not a K80 IOVA, MMIO geometry or mapping permission. The independent UNAPPLIED candidate adds framed && stamps_ && fence_bytes_<1536 refusal before readRptr and packet emission. Plain/unstamped submissions are unaffected. No existing Ring commit/error candidate is composed.

Three short declared counts64/512/1535 are now refused;1536/4096 and plain/unstamped64 controls pass the extracted scalar predicate. Three source mutations, ASan/UBSan and one changed real-header iOS17 Ring object pass. No Ring instance, buffer/address/IOVA, timestamp result, successful commit/fence/provider, callback/cache or MMIO operation was modeled or executed. The target object was neither linked nor executed. No actual K80 short fence buffer or hardware corruption is claimed.

The requested ring-word arithmetic review found no new gap: attach bounds ring size to2048..262144 words; maximum extra101 plus8 reserved is below the minimum. The initial size guard bounds the later sum, and the occupancy mask bounds used before writes. No synthetic oversized unattached ring state was treated as reachable. drainBus's best-effort polling behavior was already recorded in the old stall-eligibility contract and was not reopened as a new stop/ACK repair.

Original catalog/pins,32 independent driver patches,eight profiles,public ABI/class layout,packet bytes,normal logs,carrier and runtime selections remain unchanged. This check does not qualify actual GPU timestamp writes,coherency,ownership,stop or DMA rights.

# Private CPU backing to GMU reservation composition

ZornGpuGmuRuntime is a new unselected persistent owner, derived from the frozen
CPU registry source. It embeds32 actual NativeAdrenoMemory objects and a private
supplied-reservation ledger. It does not copy a live object or expose a native
object/range accessor. Include this directory, runtime, gmu, reservations and
actual upstream native headers when compiling.

ZGBR_CPU_PREPARE_COMPILE_ONLY and ZGGMU_RECORD_COMPILE_ONLY both default zero.
OFF recording returns Disabled; record-ON/CPU-OFF returns ModeMismatch before
any native getter. Selected code records only after actual CPU attempt/status0,
backed/prepared and nonfailed report evidence; it reads actual retained native
bytes and validates stable native state before/after private ledger recording.
The same owner gate nests only into the private ledger, which has no callbacks.
Members must outlive any future use; no destructor cleanup/reset/release exists.

CPU native32 returns stay in their original report. GMU/local adapter64 errors,
ledger results and local-index availability are separate. A failure preserves
the backing object and, if recording succeeded, the full rounded interval.
Failure before a ledger index exists does not claim the range was recorded.
An external real reservation owner must retain that range independently.
No native reference hold or mapping happens. Native-map attempt/status/mapping
complete/runtime-complete remain zero. No index is an HFI handle or ACK.

Existing narrow generic host RAM/4K alignment/explicit CPU budget policy is
unchanged. This initial path therefore does not widen to larger alignments,
GPU-global/secure/IPC/fence resources or pool/WC/import mappings. Supplied starts
are not selected, authenticated or authorized by this class. CPU ownership and
metadata do not establish SMMU context/routing, power/stop or DMA rights.

Host tests run OFF/mixed refusal and report-separation paths only; selected
host linking refuses without a real allocator definition. Selected success and
post-record native failure paths remain unexecuted. Independent iOS17 targets,
actual dependency links and historical e328 symbol-name classification do not
qualify final kernel/vtables, a device trial, native cache or GPU execution.
Previous profiles/capsules and all query/HFI/log formats are unchanged.

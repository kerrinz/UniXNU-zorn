# Preflight approval and manifest work bounds

The caller-supplied --approval and --inputs files were fully read before strict SHA rejection. Two actual CLI traces reproduce whole-file reads of 1 MiB + 8192 bytes. An independent UNAPPLIED candidate applies a 1 MiB offline control-file budget to the actual read request before identity checks. This budget is not target memory geometry or permission.

The existing exact approval and manifest SHA gates remain mandatory. Four exact-limit/limit+1 cases show the limit is inclusive: an in-budget wrong body reaches the original SHA rejection, while the first over-budget byte triggers the reader bound. An oversized approval refuses before the manifest is opened. The parsed approval now reuses the exact bytes already checked against its fixed SHA; the valid approval is read once instead of twice.

The valid default plan retains identical output-content hashes and exact compiler command arguments. Dependency bytes are unchanged; only independent mirror paths differ. The guard confirms no output directory, header, compiler or subprocess is created. The original builder and all old approval receipts, manifests, profiles and driver patches remain unchanged. This candidate is independent of the prior verify-only artifact-bound candidate; it does not silently compose them or update old proofs.

This closes the planned provenance/reference/power/emitter/artifact/control read-bound investigations. Do not continue growing wrappers or repeating these tests. Further work must move to a distinct reproducible driver software gap while native, runtime selection and device execution remain disabled.

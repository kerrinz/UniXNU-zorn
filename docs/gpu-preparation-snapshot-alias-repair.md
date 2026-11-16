# Preparation report exclusions (independent UNAPPLIED candidate)

The table-preparation composition forwards a caller-retained memory object,arena and state to native preparation,then may retain them after failure. Its two report methods only excluded the composition object's own storage. They did not remember the external metadata/pool intervals needed to refuse reports targeting those bytes. The separate child-publisher patch does not fix the parent's Report copy,so this candidate stands independently.

The source patch is `out/zorn/gpu-preparation-report-alias-20261103/preparation-report-exclusions.UNAPPLIED.patch`. Main native source and the eight old profiles remain unchanged. This candidate is not composed with the32 driver patches or the previous child-visibility candidate.

After the existing argument extent/alias checks,the candidate remembers only the caller-retained memory-object,arena and state intervals. It does not retain the shorter-lived Geometry or callback-output argument as if those had permanent lifetimes. It records a valid pool interval immediately after the existing mapping/bytes observations and before subsequent failure checks. No getter is added. These non-owning exclusions do not acquire a reference or establish a memory/mapping lease.

Both report methods check exclusions while holding the existing composition lock and before writing or delegating to the child report method. Collision or malformed exclusion metadata returns Invalid with output unchanged and releases the lock. Empty/default-OFF state remains reportable. The source has no forget/reset/rebind operation;callers must continue to respect the persistent input lifetimes and must not treat these cached virtual intervals as physical alias proof. A stale address reused inside a cached interval can be conservatively rejected;this candidate grants no permission to release or recycle the underlying resources.

The public Report fields and method signatures are unchanged. Private context storage grows from168 host bytes to240 bytes;the changed iOS17 object independently confirms240 bytes and constinit storage without an initializer. This is a C++ context-layout change,not a compatible replacement for old-size storage. Any future integration needs consistently rebuilt callers and a separately reviewed profile. No old profile SHA is mechanically changed here.

Host tests call the actual snapshot methods over ordinary byte storage. A copied test header adds friendship only to inject non-owning exclusion metadata;no native object,successful backing,prepare,getter,bind or callback is constructed or executed. The original methods write into24 overlapping destinations;the candidate rejects all24 without writes. Sixteen adjacent cases remain allowed,empty snapshots work,rejection releases the lock,and malformed range metadata refuses. ASan/UBSan pass. This is a source-state reproduction,not an experiment involving real page tables or native preparation.

The changed candidate builds as default-OFF and compile-only-ON iOS17 ARM64 objects against real selected headers;the ON object is needed to type-check the new capture code,and is never linked or executed. The test friend and host IOKit type shim are absent from those target headers. A third object checks constant initialization and actual context size. Retained recipe flags stay unchanged;288 input hashes and actual undefined symbols are recorded. There is no new component,caller,FD/kernel candidate,runtime selector or hardware qualification.

Reproduction uses fresh output directories only:

```sh
python3 -B UniXNU-zorn/scripts/check-zorn-preparation-report-alias.py \
  --out /absolute/fresh/preparation-report-review
```

The saved target command and real-header inputs under the capsule's `ios17-candidate` directory describe the isolated compilation. Do not rerun sealed old suites or use a host report success as native ownership evidence.

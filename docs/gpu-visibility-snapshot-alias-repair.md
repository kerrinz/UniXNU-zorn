# Visibility report output alias repair (independent UNAPPLIED candidate)

The default-OFF native visibility publisher's `snapshot(Report*)` rejects output overlapping its own context,but did not exclude output overlapping its cached table-pool interval or its borrowed memory-object interval. Writing a report could therefore overwrite those regions. The existing `bind` code caches memory/base/bytes before backing validation,so failed validation can retain that metadata;checking only `report.bound` would miss it.

The candidate adds two interval checks after acquiring the existing lock and before copying the report. Both reject with Invalid and release the lock. They use cached numeric metadata and `sizeof` only;no native getter,cache operation,callback or allocation is introduced. Adjacent non-overlapping outputs remain allowed. The candidate adds no fields or public methods.

`out/zorn/gpu-visibility-report-pool-alias-20261103/visibility-snapshot-pool.UNAPPLIED.patch` is the combined source patch. It has not been applied to the maintained native source or composed with the32 driver patches or the separate CommandDB repair. The eight source profiles remain byte-identical. This document is not a selection or integration approval.

Host reproduction exercises the actual snapshot implementation under default-OFF compilation. Test-only friendship in a copied header permits injecting cached numeric metadata. Pool tests use ordinary host byte buffers. Additional owner-interval tests use an opaque pointer token to host byte storage;they do not construct or dereference a NativeAdrenoMemory object. No successful backend,bind,real mapping,physical address,handle,lease or native getter is provided. All bound/native-status availability flags remain zero.

Three pool-overlap cases originally returned Ok and changed the host buffer;the pool guard returns Invalid without changing it. Three borrowed-object interval cases show the same before/after result under the further owner guard. Two adjacent cases per concern retain behavior,and a safe subsequent snapshot confirms that rejection releases the lock. ASan/UBSan pass. These are source-state reproductions,not a demonstration involving a real GPU table or live native backing.

The first pool-only candidate,host outputs and object are retained. After adding the distinct borrowed-object alias guard,only the new owner-interval tests and the further-changed candidate object were run;the completed pool suite was not repeated. The maintained candidate generator is checked against the final tested source.

A single final default-OFF iOS17 ARM64 candidate object compiles against the real selected exported headers using the retained XNU recipe;its copied header has no test friendship or host IOKit shim. Its deployment load command and undefined symbols are inspected,and285 input hashes are recorded. The earlier pool-only object remains separate. No target object is linked or executed,no fullcore is retried,and no selected component or runtime caller changes.

The snapshot guard prevents a known virtual-interval overwrite. It does not prove physical alias isolation,coherency,device/stream ownership,SMMU routing or safe release. Those remain actual platform-owner responsibilities.

To reproduce into fresh directories only:

```sh
python3 -B UniXNU-zorn/scripts/check-zorn-visibility-report-alias.py --out /absolute/fresh/capsule
python3 -B UniXNU-zorn/scripts/check-zorn-visibility-owner-alias.py \
  --capsule /absolute/fresh/capsule --out /absolute/fresh/owner-review
```

The retained target command and real-header inputs are in the capsule's `ios17-final-candidate` directory. Do not rebuild into sealed capsules or reinterpret this isolated object as a selected driver build.

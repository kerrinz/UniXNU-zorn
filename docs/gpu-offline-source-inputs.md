# Offline GPU source inputs

This workflow reads retained files only. It does not choose a boot variant or produce startup policy,headers,FDs,kernels or device actions.

The comparison entry validates each raw DTB and graph JSON independently,including property bytes,reference cells,compatible roots and dependency closure. It retains all explicitly listed base identities and all raw table differences. Equal bytes do not prove equal hardware policy.

The explicit schema option adds the retained Sheng pure input check to each verified base. K80 multi-SKU sources remain incompatible;exit2 with compared=true and source_schemas_compatible=false means raw comparison succeeded but input compatibility was refused. prepare_allowed stays false. Without this option,the original comparison result and exit semantics are unchanged.

Verified invocation for the retained four-source manifest:

```sh
python3 -B /Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/compare-zorn-gpu-power-sources.py --inputs /Volumes/macData/projects/ios-zorn/out/zorn/gpu-power-source-compare-20261103/inputs.json --sha256 a8b6cb3aa94ca8214e0ba20e9b6ba886de6707f3ddfba60f5a1244912f914e88 --schema-diagnostics
```

The command prints JSON to stdout. Each source carries its own original DTB SHA,graph SHA,raw comparison identity and fixed pure-schema diagnosis. Unknown source fields remain raw bytes;no width conversion,scaling,bin/SKU selection or vote derivation occurs. A self-signed compatibility field in the input manifest is refused.

The owner subsequently approved the concrete unselected source-data header/layout review scope. Its receipt is out/zorn/gpu-source-layout-review/owner-scope-approval.json. All4 bases/16 tables remain unselected;the isolated iOS17 data-object review is not driver or hardware qualification. Runtime policy,prepare/audit/formatters,device authorization and hardware ownership remain unavailable.

## Approved source-data emission

The maintained scripts/emit-zorn-unselected-source-data.py requires the exact approved manifest SHA,the explicit scope receipt and --emit-unselected-source-data. It refuses to overwrite UnselectedSourceTables.h,source-layout-check.cpp or source-layout-data.json. The header stores raw bytes and file-array indices,not GPU addresses or settings;missing optional fields use explicit presence flags. Isolated compilation uses the retained clang with --target=arm64-apple-ios17.0.0 and -nostdinc/-nostdinc++;no SDK/driver imports,linking or native execution. The data object is verified independently against the original bytes,and remains outside every driver/startup build.

## Maintained isolated build entry

`python3 -B /Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/build-zorn-source-data-review.py --source-review-only --out-dir /Volumes/macData/projects/ios-zorn/out/zorn/source-review-example` validates and prints a plan only. Add `--execute --os 17 --target ios` only for an explicit new data-only review. The output directory must not exist or sit inside a sealed capsule. The fixed clang/source manifest/approval receipt are SHA-bound;there is no SDK,component,board-policy or native-caller selection. Build failures preserve partial source files,events and raw stdout/stderr;they never become completed review receipts. Source-review completion is not GPU readiness or device authority.

## Explicit read-only review verification

Add `--verify-only --receipt-sha256 <independently-retained-result-SHA>` to the maintained source-review entry and point `--out-dir` at an existing review. Obtain the receipt hash from an independent frozen record,not by treating a self-signed success JSON as authority. This mode writes no files and starts no compiler/process. It reconstructs source bodies from the fixed approved inputs and reads local archive filenames only;archive copies may relocate their known output filenames. It verifies data integrity,not trusted historical compiler execution or hardware readiness. `--execute` and `--verify-only` are mutually exclusive. Do not use this option as a recurring heartbeat hash poll.


Stock AOP source envelopes can be reviewed with `python3 -B UniXNU-zorn/scripts/inspect-zorn-aop-source-kind.py --input <retained-file> --sha256 <independent-source-SHA>`. Optional `--require-commanddb-snapshot` always refuses these static ELF inputs (exit2),even if literal magic occurs. Output is file extent/source-kind evidence only;it supplies no coherent memory snapshot,expected version,load address or mapping authority. Retained inputs and focused checks: `out/zorn/gpu-aop-source-kind-20261103/result.json`.


For an existing retained DTB,use `python3 -B UniXNU-zorn/scripts/inspect-zorn-commanddb-reservation.py --input <raw-dtb> --sha256 <independent-source-SHA>`. This reads explicit reservation-description cells and preserves raw properties. `--require-commanddb-snapshot` returns2 even for valid descriptions. Neither absent ranges nor no-map/status properties grant memory access or establish a coherent snapshot. See `out/zorn/gpu-commanddb-reservation-20261103/result.json`.


The static AOP envelope reader now validates all program ranges and caps the sum of payload bytes hashed at64MiB BEFORE hashing the first payload.Repeated/overlapping program ranges count separately;the per-file64MiB bound alone did not bound that work.Two retained real-source outputs remain identical;the cap is an offline processing budget,not firmware loading or hardware policy.

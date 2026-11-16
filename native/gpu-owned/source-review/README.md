# Unselected CommandDB file core

`ZornCommandDbFile.c` is an allocation-free C decoder for already supplied immutable CPU-readable file bytes. It is not selected in a component,boot image or native caller. It does not obtain a snapshot or memory ownership and is not an implementation of a platform provider.

Unlike the retained Sheng consumer,it does not depend on `ShengGmuVotes.h`,generated `ShengGmuCommandDbSource.h`,fixed resource names,slave policies,expected versions or board geometry. It preserves all24 raw bytes of every resource entry and all144 header bytes. AUX locations are file offsets only;no pointer or address accessor is published. It stops the interpreted slave prefix at the first zero ID,while preserving all raw header rows.

The caller supplies exclusive output storage and retains immutable input through both validation and copy passes. All searched row and AUX extents,budgets,output capacities and aliases are checked before any output write. Failure leaves both output regions unchanged. The source/header require disjoint storage and do not pretend to prove that arbitrary pointers are readable or owned. A concurrent writer violates the immutable-input precondition.

Summary qualification fields stay zero even after successful decoding. The original header contains an observed version,not an independently qualified expected version. Checksum/authenticity,capture completeness against a live reservation,coherency,power/clock/SMMU/IOVA/DMA and runtime startup admission remain outside this module.

The4096-entry/4MiB caps bound file-review work. They are not adopted K80 hardware limits. No target components,profiles,FD/kernel candidates or runtime policies are changed.

Run only the new isolated check into a fresh directory:

```sh
python3 -B UniXNU-zorn/scripts/check-zorn-commanddb-file-core.py \
  --out /absolute/path/to/fresh-review-directory
```

It compiles/runs a synthetic host-only sanitizer harness and builds a separate freestanding `arm64-apple-ios17.0.0` object without loading/linking/executing that object. This is not a full driver build or a device result. See `docs/gpu-commanddb-input-acquisition.md` for the independent capture/export problem.

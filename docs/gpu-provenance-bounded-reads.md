# Bounded provenance and reference file reads

The original provenance CLI read the entire source JSON and DTB, then hashed both before checking the JSON's 16 MiB limit. The reference CLI independently repeated those unbounded reads. Real file traces reproduced both paths: an oversized JSON also caused the DTB to be opened before rejection; oversized DTBs had no read cap.

Two independent UNAPPLIED patches are retained in `out/zorn/gpu-provenance-bounded-read-20261103`. The provenance candidate reads at most 16 MiB + 1 per input, rejects JSON before opening the DTB, and adds a 16 MiB DTB work bound. The reference candidate calls the same bounded helper and strictly pins that new candidate's actual body. These are offline file-work limits, not K80 memory geometry.

The original maintained scripts and their downstream strict pins are unchanged. The isolated mirror contains actual parser and pure-checker dependencies; there are no import stubs or pin bypasses. The reference candidate intentionally depends on the provenance candidate; neither patch is applied to the maintained source chain.

Real oversized-file before/after traces, an exact 16 MiB helper boundary, two existing source equivalences for each CLI, and a changed dependency refusal passed. Reference graph output is byte-for-byte JSON-value equivalent and remains free of generated policy or hardware qualification. The provenance pure schema refusal remains intact. All CLI checks run under the existing no-write/no-process guard; only the outer checker writes its fresh archive.

This does not repair downstream power-reader/emitter/build entry reads: the power reader still reads both files before its graph helper checks their size. That is a separate concrete entry to inspect and reproduce next, with any repaired chain confined to a new isolated variant. No old proof, receipt, source profile, firmware suite, target or fullcore was regenerated. No native or device execution occurred.

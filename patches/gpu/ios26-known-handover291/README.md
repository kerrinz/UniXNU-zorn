# iOS26 bounded handover and known-image candidate291

`candidate.patch` applies with zero fuzz to the exact290 native snapshot in `source-manifest.json`. Actual native inputs retain K80 OEM resources,Gen7.9.1 firmware,direct-ring submission,ABI1,16KiB CPU pages and4KiB GPU pages. The signed290 Metal frontend/Turnip and native arm64e PAC Rust archive are retained byte for byte;the original267 public Metal probe is reused.

A new client or context-dependent operation can encounter another client's pending asynchronous work. The existing real drain/idle/restore backend now accepts an explicit bounded budget for admitted initialization and foreign handover. Task/service admission precedes this work. Zero-budget Close polling keeps its previous semantics;positive-budget expiry stops operations and retains the selected owner and uncertain resources. There is no invented fence completion,reset,replay or fallback backend.

The known-image profile reconnects the existing265 full-frame serial sampler and267 probe,disables the unrelated desktop observation worker and timing environment,and requests120 real presents,four native client closes and process exit. Its dedicated iOS26 root policy change preserves Android,17,Data,GPT,Recovery and boot partitions. The actual installation and boot receipts independently establish what ran;an offline manifest is not hardware qualification.

The host checks compile actual dispatch,context,CPU-view,OOB-admission and serial-scope bodies. Native power/MMIO/SMMU/drain,OS memory and IOKit boundaries are explicit fixtures. Sanitizer results do not prove hardware teardown or rendering. See [current progress](../../../docs/progress-2026-11-18-ios26-upstream-gpu.md) and its exact device evidence for acceptance and remaining limitations.

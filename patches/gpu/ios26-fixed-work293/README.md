# iOS 26 fixed Metal workload

This candidate builds on the device-verified 292 kernel and the retained 290 Metal frontend and Turnip binaries. The separate [probe patch](../ios26-frame293/README.md) adds 16 consecutive 32 × 32 draws with fresh IOSurface contents, command completion and two CPU readbacks checked against CRC `718ed2ce`. This kernel patch binds the new probe and root identities. The GPU submission, fence, presentation and FT3683 implementations remain those selected in 292.

The boot manifest binds the new kernel and the root hash in ADT to the existing firmware and loader. The independent root replay covers 33 changed 4 KiB pages in 13 groups. The one-shot installation and boot admission have separate receipts. The performance verdict requires all 16 valid timing rows, a complete task-bound journal, and the existing Metal, client lifecycle and Recovery checks.

The reported intervals measure elapsed CPU wall time for this workload. The 120 paced presentations serve as the known-image regression. Desktop frame cadence needs a separate changing-scene measurement.

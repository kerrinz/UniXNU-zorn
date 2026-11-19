# Present-cost278 source

`ZornPresentCost278.h` stores CPU-clock wall-time totals for the real K80 presenter. It reuses the existing Trace245 snapshot owner; it does not allocate or operate device resources. LeaseCall is a subset of LeaseWall. Saturation,clock regression and publication loss invalidate performance windows.

`ZornUiMenuWire278.h` encodes nine CPU progress/cost samples into1248bytes,using the existing bounded CDC owner. No synthetic input is generated. See the [exact source/build and failed preclaim scope](../../docs/handoff-2026-11-17-k80-ios26-gpu-v278-present-cost.md). Host tests are not K80 timing or hardware acceptance.

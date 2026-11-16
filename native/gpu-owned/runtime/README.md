# CPU backing source, default OFF

These four source files are an unselected CPU backing component. No board
component, runtime caller, kernel/FD/image or device operation selects them.
The existing parent `source-profile.json` and historical static-eight-backing
qualification remain unchanged. This directory has its own exact source and
upstream-dependency pins in [source-profile.json](source-profile.json).

`ZornGpuStartupPlan.c/h` are byte-identical copies of the retained pure planner;
no HFI decoder, reply format or transport is extended. The registry revalidates
its output and stores32 real `NativeAdrenoMemory` objects. Default compilation
returns Disabled for CPU preparation. The nondefault
`ZGBR_CPU_PREPARE_COMPILE_ONLY=1` exists for isolated target inspection, and is
not permission to execute native allocation or select a production component.

The initial local CPU policy covers only generic host-accessible RAM with
explicit widths, alignment and budgets. A CPU backing does not supply a GMU/GPU
address, SMMU assignment, stop proof, DMA ownership, host success handle or ACK.
Native error and adapter error remain separate; failed attempts retain their
objects and logical budget. The underlying allocator may clean up its own
unpublished failure; its secondary cleanup status is unavailable. IOKit/cache
helpers can block, so a future real caller needs normal-thread execution and
independent protection. No destructor/reset/retry frees a retained slot.

The [closure checker](../../../scripts/check-zorn-runtime-cpu-native.py) requires
the preserved local capsules and current root iOS17 recipe/SDK inputs. It
refuses a completed result; it does not build a runnable kernel. The separate
saved source-promotion and ABI recipes in the evidence capsule recompiled these
maintained paths and checked current IOKit slots against the retained e328
baseline. That is static comparison, not new final-kernel or hardware evidence.
See [the source evidence](../../../docs/evidence/gpu-runtime-cpu-native-2026-11-01.json).

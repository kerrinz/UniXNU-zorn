# zorn SMP preparation

This directory holds an **offline candidate**, not an enabled SMP profile.
The default board still describes CPU0. No zorn multicore boot or speedup has
been demonstrated. The system lock screen is now owner-confirmed. The owner now explicitly requests a direct eight-core candidate. The phone is
in recovery. No active GUI image uses SMP; touch candidates remain preserved.

The captured K80 FDT has affinities `0, 0x100, …, 0x700` and PSCI `smc`.
The first pair has the same captured capacity. The actual pmap compile recipe
reports `MAX_CPUS=8` and `MAX_CPU_CLUSTERS=1`. This establishes available
configuration inputs, not working secondary cores.

`ArmCpu-assembly-newlines.patch` is derived from the exact upstream source in
`origin.json`; its license is retained. On Darwin, the old multi-instruction
inline assembly strings lost instructions following semicolons. The actual
Apple-logo kernel's `ArmCpu::signalCPU` contains DSB but no SGI register write.
The isolated candidate replaces separators in 17 assembly strings with real
newlines and corrects the input/output operand indices in one diagnostic timer probe. Its compiled object contains ordered DSB / ICC_SGI1R_EL1 / ISB and
the PSCI SMC instruction. The upstream checkout and active image are unchanged.

From the shared workspace root:

```sh
python3 UniXNU-zorn/scripts/prepare-zorn-smp.py --cores 8 --compile
```

This requires the captured hardware proof and the immutable `af82587b`
Apple-logo archive under ignored `out/zorn`. It creates `out/zorn/smp/ArmCpu.o`,
`eight-core.adt` and `eight-core-candidate.json` for the explicit eight-core
option; the default two-core option still writes its old files. Eight-core
preparation additionally requires the read-only recovery MIDR proof. CPU0/1
reported0x410fd801, CPU2-6 reported0x410fd811 and CPU7 reported0x410fd821. These
are Linux recovery observations, not XNU online-core evidence. Removing the added CPU nodes and PSCI node
reproduces every byte of the original ADT, including its identity, random seed,
memory window and sidecar placeholders. It does not package, link or boot them.

Before a hardware preflight, the port still needs:

- Cross-core TLB invalidation: current runtime operations are CPU0 local.
- Atomic ownership of the diagnostic block: UFS commands have a host mutex,
  but several log producers still use a plain `gLogBusy` check/store.
- Review of the remaining legacy synchronization bypasses. The prior complete
  RW-lock restoration did not produce a new early log and is not qualified.
- A bounded pre-root test proving CPU_ON success, actual MIDR/MPIDR, per-core
  timer and IPI receipt, and work bound to CPU1 before running userland.

The current XNU reset-vector source already retains Affinity1 under BCM2837;
the houji Darwin 22 reset-entry patch must not be copied wholesale into this
Darwin 23 kernel. Houji's phased preflight is the reference, not its addresses,
storage write policy or reported multicore result:
https://github.com/lonzzi/UniXNU-houji/blob/main/docs/cpu-scheduling.md


## Explicit eight-core runtime preflight

`build-zorn-debug.py --defconfig zorn_defconfig --smp-preflight 8 --memory-mib 8192 --early-watchdog 1 --recovery-timeout 360 --incremental-patched-tree` selects the board adapter and pinned reversible source profile. It stops after log/watchdog readiness and before root or Data publication. No RAM Data seed, overlay mount or GUI runs in this mode. The default remains CPU0; a later normal build restores the four pinned source files before rebuilding.

The boot-local interrupt controller has one enabled CPU; secondary interrupt handlers remain local to their own cores. Registration/start is deferred until UFS logging is ready and serialized on CPU0. After a bounded CPU0 all-ASID inner-shareable TLB probe, global flush entry points use VMALLE1IS. Per-core identity, PSCI status, timer/IPI receipt and bound work are required by the preflight, with an independent watchdog fallback. RW locks, ASID allocation and pmap destruction use pinned original semantics. Host policy/log stress checks and real linked-call audits are required before packaging. These changes are not yet hardware-qualified; cross-core remap correctness and eight-core userspace remain separate work.


2026-10-28 hardware results: `402f7682` proved eight real XNU cores with matching MIDR/MPIDR, timer/IPI and ten bound-task beats per core. `37100a75` additionally passed nine shared-VA mapping epochs on all eight cores and completed memory cleanup before automatic recovery. See the device docs/evidence SMP result files. The VA-only test entry is explicitly unwired (KMA_PAGEABLE); the physical backing stays wired separately. The earlier unwire assertion is recorded, not suppressed.

`--smp-continue` permits retained/dim union GUI only after the same eight-core checks pass on that boot. The builder requires matched recovered remap evidence and identical qualified mapping workers/coordinator/CPU adapter. CPU0 user/kernel stack samplers are excluded. The first GUI candidate `1a62f9de` reached lock screen as confirmed by the owner; its automatic log recovery is still pending. Conservative single-cluster SMP only: no AMP, DVFS, performance score or long-term stability claim.

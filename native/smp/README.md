# zorn SMP preparation

This directory holds an **offline candidate**, not an enabled SMP profile.
The default board still describes CPU0. No zorn multicore boot or speedup has
been demonstrated. The system lock screen is now owner-confirmed. Current order is persistent
Data qualification, then phased preflight to all eight cores, then remote-only
touch attempts; this directory is still an offline SMP candidate.

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
python3 UniXNU-zorn/scripts/prepare-zorn-smp.py --compile
```

This requires the captured hardware proof and the immutable `af82587b`
Apple-logo archive under ignored `out/zorn`. It creates `out/zorn/smp/ArmCpu.o`,
`two-core.adt` and `candidate.json`. Removing only the added CPU1 and PSCI nodes
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

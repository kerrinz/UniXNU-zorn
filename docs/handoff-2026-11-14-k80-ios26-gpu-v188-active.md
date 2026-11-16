# K80 iOS26 GPU v188 active handoff

Goal active, not complete or paused. User standing approval: 我批准后续的真机测试. Same fixed92988a43/zorn/slotA/privateADB5039/300sWDT/600sRecovery scope; no repeat confirmation. Strict no disassembly/reverse engineering; no subagents unless explicitly requested. Preserve Android/iOS17/Data/history.

## Current hardware evidence

v188 one temporary boot returned TWRP332.924s,7protected sample pairs equal and BCBtail/full-page checks pass. No root write or retry. Active_run cleared, stop_device_operations false. No live runner handle remains (98008 exit0).

2106B same-run CDCm88 verified. Application PID12/unique12 flags7 (admitted, execution prepared, application OOB acquired),5native events. First error `ax=26/e00002d8/0/16/1/0000007b0701023e`: stage26=domain-transition-return, detail0=Prepare, NotReady,16prepare events. Actual operation authority, scope/empty-list/connection, quiesce health/foreign idle/runtime wait/ring guard/hardware idle/no-outstanding all passed before error. Failure is inside `ZornGen7SmmuDomain26::transitionHostProcessTables(Prepare)`, before Select/AttachVm/openProcessClient. It does not yet prove whether Domain admission/window/fault checks or HostGpuTables allocation failed.

User Query phase1/method1/rawNotReady/flags0/fence0/closed0 remains. Task-death close retains failed resources. Known-image CRCe843b26a/fence2 still succeeds. No application image/normal close/Metal/shader/GPU presentation/fullFT3683 qualification.

## Exact artifacts

- Build `/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v188-application-prepare-trace-864d745159824ae5a059e99c246302c1`
- Source `/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v188-application-prepare-trace-864d745159824ae5a059e99c246302c1`
- Trial `/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v188-application-trial-864d745159824ae5a059e99c246302c1/root-trial`
- Kernel751651bae3caf0319af0b4af8b8506f72c1f07391dee1d0621701f971c2748c6
- Bootf693862ebfb5c7f8f10cb8a760708f90fdee61df3a0542c13e5902e62c3660ab
- Root4d636e89dd1f4b22539e682e00b3d304f9612f71d4d17bfe26b5482e33f04167, exact installed v186R2 reused; no full-device-root hash claim.
- Boot/USB tag864d745159824ae5a059e99c246302c1. Unchanged signed root application tagd55c2bab3d6d436386ca54c7b6a74f06 is separately pinned, not the boot identity.
- `/tmp/zorn-v186-path`, `/tmp/zorn-v187-path`, `/tmp/zorn-v188-path` locate builds.

## Next work

Create independent v189 and add bounded inner Domain Prepare observations, preserving exact native return values/short-circuit order/no retry or cleanup changes. Suggested boundaries: initial Ring transition permission; caller-unlocked gate; native window begin; Ring recheck and runtime-ready bits; global fault verify; each endpoint fault/stream checks; controller/consumer gate; actual HostGpuTables::prepareProcessTables return. Need actual client identity from Ring, not invented global permission. A small nonvirtual diagnostic Ring method can forward to existing observer only for the current actual application PrepareTables operation. Reserve remaining stage IDs below64; extend ax parser known-stage map and success requirements appropriately.

Existing first-error observer lives in AppIo translation unit through `ZornApplicationObservation26.inc`, exposed by header. It binds first admitted client, uses try-lock,128-event cap,64-bit mask and records first nonzero stage/raw/detail; later wrapper errors cannot overwrite it. CDC ax follows base64 at, and decoder distinguishes ring integer result stages36/37 from IOReturn. No extra hardware access. Actual v188 source has observe calls in open/begin/transition/quiesce. Only PrepareTables operation is instrumented.

Source checks so far: Domain has no current_task/kernel_task filter. `nativeControllerClaimHeld()` calls real PM nativeHeldFor; Board already passed PM during execution acquisition. `HostGpuTables::prepareProcessTables` has retained ready/context/heldMask/input/memory backing gates, then real page allocation/seed/audit/ASID. It must not be assumed reached. No behavioral fix identified yet; do not relax checks based only on wrapper error.

## Build and verification

Full build1398inputs/21replacements/1377retained/0undefined. Actual Ring/AppIo/Ufs/sys_generic resolve new observation header. Ufs CDC frame5696B (+32), not total call-chain stack proof. FAT only kernel changes; ADT/menu/FD/loaders/shim/root retained. Frozen ready-snapshot and prior snapshots preserved.

12 actual before/after quiesce branches preserve native calls/order/raw.20 observer checks,76 actual clientClose checks,208 capture checks and actual formatter/base64/63-byte USB producer pass. Fixtures are not GPU proof.

Copied observer test initially retained hardcoded `/tmp/zorn-v186-path`; it re-ran historical fixture before correction. All affected archived scripts/source/report files compared byte-identical to v186stage7 snapshot. `parent-observer-path-incident.json` records comparison. Corrected v188 test rerun passed and uses updated header. Avoid copying hardcoded parent paths blindly. Native compile recipes use `directory` field, not just cwd. Independent local FAT clone needs owner-write after copying read-only parent.

[Observed v188](evidence/k80-gpu-v188-prepare-trace-observed-2026-11-14.json) · [Ready v188](evidence/k80-gpu-v188-prepare-trace-ready-2026-11-14.json) · [Prior v187 handoff](handoff-2026-11-14-k80-ios26-gpu-v187-active.md)

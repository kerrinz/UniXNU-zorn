# K80 iOS26 GPU v192 active handoff

Goal active, not complete or paused. User standing approval: **我批准后续的真机测试**. Same fixed92988a43/zorn/slotA/privateADB5039/300s independent watchdog/600sRecovery temporary-boot scope, fresh scope/bundle/owner/ready/admission/claim every trial. Do not re-ask for this authorized scope. No bootstrap, blind retry, recovery flashing, Android/iOS17/Data destruction. If Recovery fails, stop device actions. **Strictly no disassembly/reverse engineering.** No subagents unless explicitly requested. Do not commit/push. Read UniXNU-zorn/AGENTS.md; preserve historical sources/artifacts/records.

## Current result and device state

**v192 ordinary mobile application GPU known-image and normal client close PASS.** Same-run2104B CDC verified, PID12/unique12,17native events, nativeflagsff,12complete program text lines, zero drops/copy errors. Signed unchanged probe reports phase11/method4/raw0/flags3ff/IOVA63040000/fence3/CRCe843b26a/firstBadffffffff/ticks3864373410/closed1. Actual IOServiceOpen/IOConnect BO allocate/CPU map/GPU map/247word2D submit/fence wait/full32768B CPU-visible image validation/unmap/free/IOServiceClose completed. Native close raw0. Existing kernel known-image fence2 also passes.

Preparation `ax=9/0/0/61/0/201fff7b070103fe` complete,61events, all required native window/Domain/table/selection/VM/client boundaries observed. This is one bounded ordinary application session, not shader/Metal/rendering UI/multiple-client/long-term stability evidence. CPU presenter remains selected; full FT3683 interaction still unqualified.

One temporary boot returned TWRP332.35943966702325s;7archived protection sample pairs equal; BCB tail/full-page readback passed. No root write or retry. Session71311 completed exit0; no live runner. Current active_run/active_build/active_admission/runner_session null, stop_device_operations false. v189/v190/v191/v192 claims consumed; never reuse.

## Root cause and repair

v188 narrowed firstfailure to Domain Prepare. v189 firstfailure stage43 native post-CP window begin, before table allocation. v190 added global helper observer callbacks but yielded no new CDC/UFS record; returned Recovery with protections intact, persistent log stayed v189. Its early-return cause is unknown, do not attribute it to instrumentation or claim boot instability fixed.

v191 forked observed v189 and changed helper to optional local failedPredicate output, with only the actual Domain Prepare caller emitting stage61. Actual `ax=61/e00002d8/38/21/1/20000f7b0701023e`: detailhex38=56 Domain failed(), after held gate/native-runtime-ready/native-controller-claim passed. Camera saw CPU lockscreen. Recovery332.958s/protections pass.

Source root cause: Board callback returns87 on application publication failure,88 only after successful publication and owner/ring/phase/known-image/forward checks. Domain deferred startup success-stage classifier included86 but omitted88, unconditionally setting stopped on actual success88. `failed()` is stopped||irq_faulted. v192 changes just that classifier to include88. Existing failure87/unknown stages/prior-stop/IRQ handling preserved; stopped is never cleared.1029actual classifier/publication/failed/window regression combinations reproduce old88 refusal at56 and corrected healthy window,233capture checks pass. Hardware now completes ordinary application image/normalclose. Keep prior v187 shared startup-lock binding fix as well.

## Exact artifacts

Base V: `/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90`.

- v192 build: `V/k80-gpu-v192-application-publish-stage-7e4c3eb5e7ba49f4bfdc547b7b6c54b5`, located by `/tmp/zorn-v192-path`.
- Source: replace `/build/ios-26.6.2-23G90/k80-` in build path with `/source/os/ios26/`. Main fix `ZornGen7SmmuDomain26.cpp` line2016. AppIo source under `direct-runtime/`, probe under `userland/`.
- Trial: `V/k80-gpu-v192-application-trial-7e4c3eb5e7ba49f4bfdc547b7b6c54b5/root-trial`.
- Kernel SHA `6ac9b51950dfe9a209e0c61f640a9fe05c57981fe67b0e8933ef9821b66e03ba`.
- Boot SHA `66ef592d404186e8d376983a72112be0d7dfd5265b37b3268c7167999d5d8cd0`,11755520B.
-1398exact inputs/21replaced/1377retained/0undefined;32shared-header resolutions validated. Freeze in build `ready-snapshot/manifest.json`. Only FATkernel changed; ADT/menu/FD/loaders/shim/root retained.
- Root remains installed v186R2 SHA `4d636e89dd1f4b22539e682e00b3d304f9612f71d4d17bfe26b5482e33f04167`,34359738368B. Installer92pages/12groups, written-page376832B readbackSHA `9e4b8998c442561c3f8eece54fbced0fa70fd24cd04741b57131fac33a675c34`; no full32GiBdevicehash claim. `/tmp/zorn-v186-path` points to root source and immutable receipts; each later installed-root-cohort pins it.
- Signed root `/redwood/sbin/zorn-gpu-probe186` SHA `5c9550e38f19c7520482d9ba850af5b329ae98c6998746477a6f3da74c0bf38c`,CDHashb94513d4602ec7f32540b091e2d0071d8dbe3a84. ProgramTAGd55c2bab3d6d436386ca54c7b6a74f06 stays separately pinned from freshboot/USB/UFS/CDC7e4c. Mobile/mobile,no-container owner entitlement, exact serviceZornGen7AppIoService26,open0x4147. Wait240s; GPUcheckpoint150s. Do not accidentally retag retained program.
- `/tmp/zorn-v189-path`, `/tmp/zorn-v190-path`, `/tmp/zorn-v191-path` locate intermediate source/tests/camera/provenance. v191camera `camera-observation/phone.png` and visual-review.json.

## Checks and tooling

Current runner `UniXNU-zorn/scripts/zorn_ios26_gpu_v192_application_trial.py`, capture `read-zorn-gpu-application192-cdc.py`, unchanged application decoder186 and preparation decoder191. Stage61detail53..59 means window failed predicate; stage9 raw0 plus full mask is successful preparation. Host checks are not GPU evidence.

Existing first-error observer binds real admitted client,try-lock,128event cap,64bit mask. No added register reads or hardware operations. v191 helper/Domain diagnostic source unchanged by v192 except outer startup classification. v190 PM provenance check recompiles retained PM object to byte-identical SHA9157eab71931e8f1bfbcefb962f4b66e97308c512943ce37b505dc502287bc30. Old recipe source_sha256 had copied Domain metadata; actual sourceSHA4ea684c0719656544266613f5660c392c1f4a97deeb30088d817ef3f30b7aa79 verified in `retained-pm-source-check/result.json`. Preserve old metadata; no reverse engineering was used.

For new builds derive isolated source/full build/package from actual current parent, preserve all old files. Recipes use `directory` or `cwd`, redirect every -o/-MF/-MJ; native VFS must resolve actual changed headers. No instruction inspection; llvm-nm -u only undefined symbols if needed. Independent copied FAT needs owner-write before mcopy (parent remains readonly). Root reuse package hashing32GiB takes time. Do not blindly copy hardcoded/tmp parent paths. `apply_patch` previously silent; quoted Python heredocs are reliable. Camera is ffmpeg `USB  Camera:none`, no audio,12s timeout, one frame (authorized).

## Next work

Ordinary native application memory/submission/fence/readback/normal-close milestone is now established. Proceed toward actual Metal device discovery, pipeline creation, shader rendering/readback, then GPU display and full FT3683. First audit pinned local iOS26 frontend/Turnip/metal2vulkan/Rust bridge inputs against actual K80 application ABI/provider discovery/task lifetime, not assume that this dedicated2D probe proves shader or frontend compatibility. Relevant local pinned-reference tree: `out/zorn/ios26-feasibility-20261107/reference/houji/graphics/metal/AdrenoMetal/`; inspect its provenance before reuse. Current [official GPU tutorial](https://unixnu.com/zh/porting/gpu) still supports staged known-image/client-lifecycle then Metal; its current iOS27 recipe examples are not iOS26 qualification.

Keep actual selected iOS26/Gen7.9.1/firmware/layout pins and strict protections. Reuse appropriate local houji/K80/official source; no disassembly. Prepare concrete bounded trial artifacts/checks before device action; standing scope authorized. Root writes/new layout are separately reviewed exact windows, never casually modify installed root. CPU lockscreen evidence is not GPU presentation. Goal remains active until Metal/render/presentation and complete FT3683 plus required lifetimes are actually verified.

[Observed v192](evidence/k80-gpu-v192-application-image-observed-2026-11-15.json) · [Ready v192](evidence/k80-gpu-v192-publication-stage-ready-2026-11-15.json) · [Root-cause v191](evidence/k80-gpu-v191-window-return-observed-2026-11-15.json) · [Unqualified v190](evidence/k80-gpu-v190-window-trace-observed-2026-11-15.json) · [Prior handoff](handoff-2026-11-14-k80-ios26-gpu-v188-active.md)

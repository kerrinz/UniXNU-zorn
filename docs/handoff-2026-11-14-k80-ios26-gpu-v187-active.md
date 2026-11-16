# K80 iOS26 GPU v187 active handoff

Goal remains active. User explicitly approved all subsequent same-scope device tests. No need to ask again. Strictly no disassembly or reverse engineering. No agents unless explicitly requested.

## Current result

v186 ordinary application admitted but execution preparation returned NotReady. Source-connected regression reproduced a shared startup lock contradiction: Board locks the same gate stored by Ring, while Ring nativeApplicationBinding rejected it held. v187 reverses only that condition, requiring the Board-held gate; external callback entry still requires unlocked gate, issuer/task/client/thread/phase guards preserved.

v187 actual hardware passed execution preparation and application OOB (flags7 vs v186 flags1). First Query still returns0xe00002d8 inside openApplicationProcess before event8. Inner operation/begin/quiesce/Prepare/Select/AttachVm/openProcessClient boundary is not yet distinguished. No app BO/submit/CRC/normal-close success. Task-death close retains failure. Known-image fence2/CRC e843b26a still correct.2067B same-run CDCm88 verified.

332.950s independent watchdog return to TWRP. Seven sample pairs equal; BCB tail/full-page checks pass. Runtime active_run cleared, stop_device_operations false. No root write during v187. Consumed v186/v187 scopes must never be reused.

## Exact paths

- Build: `/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v187-application-shared-lock-d2a0d92eb14546bc9110834052ccfee7`
- Source: `/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v187-application-shared-lock-d2a0d92eb14546bc9110834052ccfee7`
- Trial: `/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v187-application-trial-d2a0d92eb14546bc9110834052ccfee7/root-trial`
- Boot:99798f3586caa1e094c1946447a575b0177e0ad8db165ec913f3f03726b09638
- Kernel:7cb0725fde46efa66d7ea90c5acd1e2e232dd6fe1e66b4fb8593817ff18f7431
- Installed root:4d636e89dd1f4b22539e682e00b3d304f9612f71d4d17bfe26b5482e33f04167 (v186 R2, exact reviewed92-page installation; no full device-root hash)
- New boot/USB tag:d2a0d92eb14546bc9110834052ccfee7
- Retained signed app program tag:d55c2bab3d6d436386ca54c7b6a74f06. This is deliberately separate: kernel UFS/USB use new boot tag; stderr observer and parser bind actual retained root probe tag.
- `/tmp/zorn-v186-path`, `/tmp/zorn-v187-path` contain build paths.

## Next concrete work

Create separate v188 from frozen v187. Add bounded diagnostic stage/raw to openApplicationProcess and its operation authorization/quiesce/Prepare/Select/AttachVm/openClient sequence; preserve raw returns, no retry/cleanup policy change. Prefer first-failure trace and readiness bits without additional GPU/MMIO actions. Do not infer exact failing branch from wrapper NotReady. Inspect actual connected source guards and reproduce precise mismatch before behavioral change.

Retain installed root/probe if no userland change needed. Build script v187 reuses v186 root, retags four identity headers/UFS/USB, compiles21objects and links1398inputs with0undefined. Package only changes FATkernel; ADT/menu/FD/loaders/shim unchanged. Existing root receipt links via installed-root-cohort. New parser must bind new UFS/USB boot identity separately from fixed d55 program identity. Fresh scope/bundle/owner/ready/admission/claim and fixed300s/600s runner mandatory. Stop device operations if Recovery fails.

## Checks and known limitations

Actual Board+Ring shared-gate regression reproduces v186 refusal (7 assertions), v187 acquire/OOB/check/close passes(13).82 binding/identity assertions and193 parser checks pass; ASan/UBSan. Full build and package verified. Earlier isolated mocks failed to represent same gate: prefer connected callbacks.

First isolated native compile used wrong cwd field and failed meta_features.h; actual recipe uses `directory`, not `cwd`. Both records retained. First packaging clone inherited read-only FAT permissions; archived as boot-package-first-attempt, chmod only independent clone then successful rebuild. Do not mutate frozen parent files.

No Metal/shader/GPU presentation/full FT3683 acceptance yet. No camera frame for v187; v186 camera only shows blurred CPU-rendered graphical UI. Official tutorial reviewed at https://unixnu.com/zh/porting/gpu; its platform/OS examples are not K80 iOS26 qualification.

[Observed v187](evidence/k80-gpu-v187-application-observed-2026-11-14.json) · [v187 build and regression](evidence/k80-gpu-v187-shared-lock-ready-2026-11-14.json) · [Observed v186](evidence/k80-gpu-v186-application-observed-2026-11-14.json)

# Publication review — 2026-11-01

This review covers the pending source and documentation in the two existing root repositories. It does not run a phone, rebuild a native kernel/FD, activate a GPU, reset Data or modify an old manifest. Code and documentation are committed separately; historical device runs retain their original inputs rather than inheriting the publication revision.

## Structure and inputs

UniXNU-zorn retains format2 board/SoC/OS/component/patch metadata, its authoritative schema1 porting record, native board code, package entry and immutable historical compatibility board. uefi-zorn remains the firmware board package and links the device record instead of inventing a second whole-device record. The current dedicated unixnu64 layout and its initial8GiB Data are described in matching descriptors in both repositories.

External Apple/vendor binaries, prepared SDKs, source capsules and large raw logs are not redistributed. Their input roles/hashes and the non-bootstrap limits are documented. Historical out/zorn locators in source summaries are archive provenance, not accessible public log URLs or a claim of clean-machine reproduction. No host/device completion grade is promoted merely because these records are published.

## Corrections before publication

- Replace workstation-specific absolute tool/root paths with workspace-relative paths or UNIXNU_ADB/UNIXNU_FASTBOOT overrides. The historical sealed policy files remain local inputs and fail closed if their original binding no longer matches.
- Version authored host include shims under native/gpu-owned/tests/host-include so memory/wire checks no longer depend on a past out directory. Core component sources and stock firmware remain separately pinned external inputs.
- Refuse consumed installation claims before any USB action. Require complete matching input/archive membership, pinned runner/reader/storage helpers, a contained image/run directory, and mode1 watchdog markers before future device action.
- Synchronize current slotA/unixnu64 facts, remove obsolete README activation prose, and shorten the GPU next_action field into actual next steps. Add affected configuration/CPU/packaging/diagnostic findings and ownership patterns required by the official base-aware checker.
- Preserve the two unchanged legacy firmware text records with .json suffixes; document the exception rather than rewriting historical raw evidence. All newly published/modified JSON is parsed strictly.

## Host checks

From the common parent, with the documented matching core/component/vendor inputs:

```sh
python3 UniXNU/scripts/porting-record.py check --device UniXNU-zorn
python3 UniXNU/scripts/porting-record.py check --device UniXNU-zorn --base origin/main
python3 UniXNU-zorn/scripts/check-zorn-unixnu64-admission.py
python3 uefi-zorn/scripts/check-zorn-storage-profile.py
UNIXNU_ZORN_HOST_CHECK_OUT="$PWD/out/zorn/publication-host-check" python3 UniXNU-zorn/scripts/check-zorn-gpu-owned-memory.py
```

The GPU-memory command is a host-only software/codec regression using explicit IOKit doubles. Its output directory is independent of old qualification evidence. The storage admission test traps every process/USB call. The descriptor test uses a synthetic file for consistency parsing, not a hardware-success fixture. The actual archived GPT may additionally be passed to check-zorn-unixnu64.py for source-selector/CDB boundary checks without device I/O.

The review also parses changed Python/JSON/TOML, checks local Markdown targets, checks diffs and scans pending files for binary/proprietary payloads and credential signatures. The publication source revision and check summary are recorded separately in docs/evidence/publication-review-2026-11-01.json. Remote CI status is reported only after the push; local success alone is not a GitHub CI result.

Official requirements: [device repository](https://unixnu.com/zh/porting/device-repository), [records and change coverage](https://unixnu.com/zh/porting/records), [firmware integration](https://unixnu.com/zh/porting/uefi-firmware).

# UniXNU-zorn

[【简体中文】](README_CN.md)

UniXNU device repository for the Redmi K80 (`zorn`, SM8650-AB, 12 GB + 256 GB), targeting iPad7,1 / j120ap, iPadOS 17.7.11 (21H461, Darwin 23.6 / XNU 10063.141.1).

This repository owns the board configuration, DTS, native board services, XNU patches, packaging integration and diagnostics. [uefi-zorn](https://github.com/kerrinz/uefi-zorn) owns the Mu-Silicium board package, BootShim and firmware handoff. [UniXNU](https://github.com/UniXNU/UniXNU) supplies the build tools, component catalog and ARM64 / OS profiles.

[Porting record](porting.toml) is the authoritative per-area status. The official site generates device documentation from the published root `board.toml` and `porting.toml`, following the [record and publication guide](https://unixnu.com/zh/porting/records#publishing-and-reuse). README is the repository entry point.

As of2026-11-16,v247 has bounded same-IOSurface presentation evidence:known frame499/SID35/access fence4 and real acquire/copy,following the Metal pixel check. One run returned automatically toTWRP in332.500seconds with protection/BCB checks passing. Raw diagnostic loss36 keeps strict application incomplete;physical known-image output,full GPU desktop,FT3683 gestures and stability remain unqualified. See [current progress and build scope](docs/progress-2026-11-16-ios26.md).

## State

As of 2026-10-30, the owner has confirmed a desktop, swipe-to-unlock and icon taps. Eight-core identity / timer / IPI / bound-work checks and nine mapping rounds pass; an 8 GiB XNU window, retained 8 GiB UFS-backed Data and panel brightness 64 have bound device results. Two independent touch IDs and release were observed; system multi-touch gestures remain unqualified.

Historical checkpoint (2026-11-13): the CPU-rendered iOS 26 path reached the system lock screen during the bounded `b0da41e9` run, confirmed visually by the owner; the CPU kernel SHA-256 is `9f6474ce789a8ac860417e3e7526ca5e241366c4dd7bd3c8b1731712c409a091`. The owner confirms that earlier GPU-branch runs were real-device attempts that failed before the system lock screen, which led to switching to CPU rendering. Those GPU attempts exercised K80 GPUCC/PLL and clock stages, a masked SMMU IRQ route, the GMU cold-clock prefix and SMMU global control, plus a read-only bank/stream census. These are staged platform-initialization results; GMU firmware/HFI startup, GPU submissions and fences, GPU rendering, Metal and GPU display remain unqualified. The latest v80 GPU candidate is fully linked offline and remains unselected; the v73 Recovery stop gate remains active. See the detailed [GPU progress record](docs/progress-2026-10-30-gpu.md).

The CPU1 root-publication change passed the same-kernel 0-fail / 1-pass / 0-fail / 1-pass control and two uninstrumented layouts 16 KiB apart. This is bounded evidence for the narrow fix. A separate intermittent Apple-logo GUI failure remains unresolved. The final `c50ca7ea` observation recovered automatically, showed a lock screen, and recorded USER and SYSTEM accounting progress on all eight cores; it is not a performance or long-term stability result.

The default image remains `42f3d518`; the two owner-confirmed desktop runs of `3a8ac966` remain separate baselines. These are diagnostic images with bounded automatic recovery. Wi-Fi, Bluetooth, audio, cellular, cameras, sensors and complete power management are not qualified. Hardware graphics acceleration remains unqualified; ongoing GPU work is recorded separately below.

See the shared [non-GPU progress snapshot](docs/progress-2026-10-30-non-gpu.md) for evidence and qualification limits.

## Prerequisites

- A matching UniXNU checkout beside `UniXNU-zorn/` and `uefi-zorn/`, plus the existing Mu-Silicium dependency. The tracked `soc/sm8650/` input is a board-local resource slice, versioned with this device repository; no additional SoC repository is required.
- Matching Xcode / iPhoneOS SDK and pinned component sources. [source-pins.json](source-pins.json) records the prepared component bytes; [unixnu.lock](unixnu.lock) records resolved source commits.
- The matching donor IPSW, original trust cache, owner policy, prepared Data seed, verified firmware and historical ABI audit inputs. See [proprietary input notes](proprietary-files.txt) and [build instructions](docs/build-and-debug.md). This is not an artifact-free bootstrap.

Read the [device repository guide](https://unixnu.com/zh/porting/device-repository), [build guide](https://unixnu.com/zh/building), [bring-up order](https://unixnu.com/zh/porting/bring-up) and [AGENTS.md](AGENTS.md) before changing the port.

## Configuration and build entry points

The root configuration now uses format 2. From the UniXNU checkout, use a separate output root for configuration validation:

```sh
./unixnu defconfig zorn_union_defconfig -D ../UniXNU-zorn --out ../out/zorn-format2
./unixnu status --json -D ../UniXNU-zorn --out ../out/zorn-format2
python3 scripts/porting-record.py check --device ../UniXNU-zorn
```

The four configuration layers, selected components, explicit patch order, hardware DTS and build-tree assembly are checked on the host. Full native kernel / payload equivalence and a device run through this new format-2 output path remain unqualified. Historical device results belong to their recorded inputs, not automatically to this migration. See [migration and publication scope](docs/repository-format.md).

The existing guarded diagnostic entry remains, run from the common parent:

```sh
python3 UniXNU-zorn/scripts/build-zorn-debug.py --help
```

It uses the fixed format-1 compatibility board in [compat/legacy/board.toml](compat/legacy/board.toml), generated into a separate view, to preserve the flat build paths and existing audit / ready / recovery checks. Use the complete profile in [build-and-debug.md](docs/build-and-debug.md); `--help` does not build or boot. The compatibility selection has host checks; it has not been used for a new kernel or phone run in this documentation update.

## Layout

- `board.toml`, `feeds.toml`, `soc/sm8650/`: format-2 selection and board-local SoC input.
- `configs/`, `dts/zorn.dts`, `patches/xnu/series`: kernel configuration, hardware description and explicit patch order.
- `native/`, `scripts/`, `patches/zorn/`: board services, guarded build / diagnostic entry points and board patches.
- `package/`: board kit identity; common firmware modules come from UniXNU.
- `compat/legacy/`: retained diagnostic configuration, separate from the format-2 route.
- `porting.toml`, `docs/evidence/`: structured record and versioned evidence summaries. Large local build and raw-log paths are archival references, not bundled public artifacts.

## Device and storage boundaries

The active installation targets `92988a43` / `zorn` / slot `a`; `f85d4270` is a CC9 and must not be operated on. After the owner full-stock-flashed Android, they authorized a fresh dual-system installation with a dedicated64GiB `unixnu` partition. Android system, OrangeFox and slotA are preserved. Use the fixed runner's explicit `--unixnu64-install-trial` path and temporary `fastboot boot`; historical slotB and userdata-backed images must not be booted on this layout.

The new `unixnu` partition spans4096-byte LBAs47271680..64048895, uniqueGUID `b279731f-ccad-4ef5-a8b7-e7440cd08de3`. OS/SystemOS were restored and fully read back; runtime access remains read-only. The initial8GiB Data COW store is unixnu-relative16GiB,2097217 blocks; its fresh metadata/cookie is distinct from the historical store. The log remains one4KiB block at unixnu-relative2291712. Preserve the BCB tail and read back the entire page.64GiB is the partition capacity, not the current logical Data capacity. Full Android boot, long-term integrity and GPU execution remain separate checks. See [new installation evidence](docs/evidence/dual-system-reinstall-2026-11-01.json).

## Publication and license

Records currently use `implemented` plus source references where the tested working-tree bytes do not have a published matching commit. Do not assign the current Git HEAD to old runs or raise completion levels without matching evidence. Publish the reviewed source / record files and confirm the `Porting record` workflow before requesting official catalog ingestion; local validation does not mean the site has already updated.

New code is mainly [BSD-2-Clause-Patent](LICENSE); PMGR retains its [MIT license](native/pmgr/LICENSE.MIT), and upstream files retain their notices. Apple images, private keys, vendor binaries and generated boot images are not distributed here.

## GPU scope

GPU-owned memory preparation and its closed diagnostic helpers are published as implemented source. The v247 fixed probe has bounded same-surface queue/acquire/copy and native-close evidence;physical known-image output,complete GPU desktop and long-term behavior remain unqualified. Detailed research summaries are retained in [GPU progress](docs/progress-2026-10-30-gpu.md); many isolated capsules and large logs are local archives, not a runnable production driver. Historical input counts describe their own frozen runs.

The current stock-reflash/unixnu64 installation and owner-confirmed retained Data/touch are documented in [storage-unixnu64](docs/storage-unixnu64.md). Old userdata/slotB images must not be booted on that layout.

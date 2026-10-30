# UniXNU-zorn

[【简体中文】](README_CN.md)

UniXNU device repository for the Redmi K80 (`zorn`, SM8650-AB, 12 GB + 256 GB), targeting iPad7,1 / j120ap, iPadOS 17.7.11 (21H461, Darwin 23.6 / XNU 10063.141.1).

This repository owns the board configuration, DTS, native board services, XNU patches, packaging integration and diagnostics. [uefi-zorn](https://github.com/kerrinz/uefi-zorn) owns the Mu-Silicium board package, BootShim and firmware handoff. [UniXNU](https://github.com/UniXNU/UniXNU) supplies the build tools, component catalog and ARM64 / OS profiles.

[Porting record](porting.toml) is the authoritative per-area status. The official site generates device documentation from the published root `board.toml` and `porting.toml`, following the [record and publication guide](https://unixnu.com/zh/porting/records#publishing-and-reuse). README is the repository entry point.

## State

As of 2026-10-30, the owner has confirmed a desktop, swipe-to-unlock and icon taps. Eight-core identity / timer / IPI / bound-work checks and nine mapping rounds pass; an 8 GiB XNU window, retained 8 GiB UFS-backed Data and panel brightness 64 have bound device results. Two independent touch IDs and release were observed; system multi-touch gestures remain unqualified.

The CPU1 root-publication change passed the same-kernel 0-fail / 1-pass / 0-fail / 1-pass control and two uninstrumented layouts 16 KiB apart. This is bounded evidence for the narrow fix. A separate intermittent Apple-logo GUI failure remains unresolved. The final `c50ca7ea` observation recovered automatically, showed a lock screen, and recorded USER and SYSTEM accounting progress on all eight cores; it is not a performance or long-term stability result.

The default image remains `42f3d518`; the two owner-confirmed desktop runs of `3a8ac966` remain separate baselines. These are diagnostic images with bounded automatic recovery. Wi-Fi, Bluetooth, audio, cellular, cameras, sensors and complete power management are not qualified. Hardware graphics acceleration is not claimed here; this update excludes GPU development progress.

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

The only authorized target is `92988a43` / `zorn` / slot `b`; `f85d4270` is a CC9 and must not be operated on. Use the fixed-target runner and temporary `fastboot boot`; no flashing, erasing, slot changes or GPT changes.

The phone's userdata already contains the prepared system. Do not boot Android or reinstall userdata. OS / SystemOS remain read-only. Persistent writes are restricted to the existing Data window at userdata-relative 192 GiB (2,097,217 blocks of 4096 bytes), the existing single 4 KiB log block, and the recovery BCB with its tail preserved and read back. Never reset or enlarge Data. The `board.toml` userdata range is a capacity-relative legacy description, not an absolute GPT address.

## Publication and license

Records currently use `implemented` plus source references where the tested working-tree bytes do not have a published matching commit. Do not assign the current Git HEAD to old runs or raise completion levels without matching evidence. Publish the reviewed source / record files and confirm the `Porting record` workflow before requesting official catalog ingestion; local validation does not mean the site has already updated.

New code is mainly [BSD-2-Clause-Patent](LICENSE); PMGR retains its [MIT license](native/pmgr/LICENSE.MIT), and upstream files retain their notices. Apple images, private keys, vendor binaries and generated boot images are not distributed here.

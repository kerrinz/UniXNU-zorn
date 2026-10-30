# Format2 migration and publication scope

Updated2026-10-30. This change synchronizes non-GPU progress in the two existing repositories and migrates root device metadata for official record ingestion. It does not resume autonomous work, build a kernel/firmware/image, boot a phone, commit or push Git, or update GPU development.

## What the official site reads

The [official record guide](https://unixnu.com/zh/porting/records#publishing-and-reuse) specifies a format2 root `board.toml` (`schema_version=2`) and a valid `porting.toml` (`schema_version=1`) from a fixed published source commit. README supplies responsibilities, dependencies, build entry points and links; it is not parsed into the device's detailed record. The old root board omitted the version and was interpreted as format1, even while `porting-record.py check` accepted the record itself. That combination cannot produce a new format2 device page.

[UniXNU-alioth](https://github.com/FFT-infra/UniXNU-alioth) is a publication/layout reference, not K80 hardware evidence. No component or hardware completion level is inherited from another board.

## Root format2 route

- `board.toml` selects ARM64, `zorn-sm8650`, `ipados-17.7.11-21H461`, and the device layer.
- `feeds.toml` selects tracked `soc/sm8650/`. This board-local resource slice is pinned by the enclosing device commit, not an invented external SoC repository or independent source revision.
- `components.include` explicitly lists the9 required catalog components; each belongs to a record area. Board-native services remain explicit archive scripts.
- `patches/xnu/series` explicitly lists the retained157-patch base/device/prelink order. Arrays replace inherited arrays; the order is not an implicit combination of several series. Base entries resolve via the selected ARM64 root, board entries via `device:`, prelink entries via `component:XnuPrelink`.
- `dts/zorn.dts` includes the board-local SoC resource slice,8 CPU affinities,19.2MHz timebase, PSCI SMC and GIC. Nominal12GiB memory is not a claim that the full SKU map is hardware-qualified. The owned XNU request remains8GiB. Firmware, mailbox, shim and framebuffer reservations are explicit.
- The shared generator handles hardware FDT plus typed OS identity. The GIC and the legacy UFS class-matching node are exported here; the existing UFS board driver still owns controller/PHY/clock/DMA constants and bounds. The new DTS does not pretend to replace those implementations or qualify a new runtime tree.
- `package/` supplies kit identity. Common firmware modules remain in UniXNU's package. External IPSW/trust-cache/FD/seed/ABI inputs are documented, not redistributed.

For isolated host checks, from UniXNU:

```sh
./unixnu defconfig zorn_union_defconfig -D ../UniXNU-zorn --out ../out/zorn-format2
./unixnu status --json -D ../UniXNU-zorn --out ../out/zorn-format2
python3 scripts/porting-record.py check --device ../UniXNU-zorn
```

Configuration/DTS/ADT/tree/record checks are separate from full kernel and payload qualification. Several board-native recipes retain historical flat-path/ABI assumptions; they require output-path and native-link equivalence checks before a full format2 build. No format2 kernel, image or device run is claimed in this migration. Do not run a generic build/boot command merely because record ingestion passes.

## Retained diagnostic entry

The exact former root board is saved as `compat/legacy/board.toml`, SHA256 `d65567ecd289b9fcddb1c1a7dcbf5af277f990f1184a09def54a3582f194b380`.

`build-zorn-debug.py` calls `zorn_legacy_device.py` to construct an owned generated view at the host workspace's `out/zorn/legacy-device/`. It selects that view with `-D` and keeps the original flat UniXNU output paths. Source/config/native paths are shared read-only inputs; the board and lock are independent generated files. The view excludes the new format2 feeds and `patches/xnu`, so it does not replace the legacy base patch module. Unknown nonempty views and a changed compatibility-board SHA are rejected. `stage-zorn-build-workspace.py` and the explicit firmware builder use the same compatibility selection.

This adapter changes source provenance and therefore new builders/manifests must bind the root board, retained board and helper. It does not waive any existing source/ABI/object/start/final-link/ready/device/window/watchdog checks. Old manifests and ready files are not rewritten or automatically requalified. Host selection checks do not substitute for a new complete build, which is outside this documentation update.

## Status and evidence

Non-GPU record prose is concise English, as required for the shared Chinese/English site snapshots. The required GPU area remains a planned placeholder; detailed GPU progress is excluded from this synchronization and its investigation files are preserved separately. Working-tree implementations stay `implemented` with `source` references where no published commit identifies the tested bytes. `host` and `device` evidence require a genuine40-character revision and actual commands/logs; current HEAD must not be assigned to historical runs.

The latest complete c50 diagnostic had255 inputs/77 archive files matched at recovery. Old6aea and954 input statements remain historical. The docs/config migration does not modify normalized/raw proof workspaces or old manifests. Default42 and both3a desktop runs remain preserved.

## Publication

After review, publish the complete source and record files, confirm the `Porting record` workflow, and set the device repository's `unixnu` topic. The official scanner must then ingest the published commit and generate a page linking that version. This local update does not claim a push, GitHub CI result or live-site acceptance. The firmware repository links the device record and does not duplicate root board metadata.

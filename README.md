# UniXNU-zorn

[简体中文](README_CN.md)

UniXNU device repository for the Redmi K80 (`zorn`, SM8650-AB, 12 GB + 256 GB). **iOS 26.6.2 (23G90) is the active port** for Adreno 750 GPU, Metal, display presentation and FT3683 touch. The iPadOS 17 GPU port is retired. [iOS 26 mainline and evidence](docs/ios26-mainline.md) · [Historical OS ports](docs/archived-os.md)

## Current evidence

v366 completed the known native GPU task and measured display transfers during a bounded lock-screen window. v371 is a complete offline candidate that reports the FT3683 SMMU outcome earlier over CDC. The latest v366 manual acceptance was stopped before boot when the primary GPT differed from the protected baseline. End-to-end acceptance remains pending. [Current status and limits](docs/ios26-mainline.md)

## Repository layout

- `native/`, `soc/sm8650/`, `patches/` and `scripts/` contain the kernel integration, board resources and build and verification tools.
- `board.toml`, `configs/`, `profiles/os/`, `feeds.toml` and `unixnu.lock` define the format-2 inputs. Select `ios-26.6.2-23G90` explicitly for the active profile. The catalog default still resolves the historical iPadOS 17 configuration.
- [porting.toml](porting.toml) records the device scope. `docs/evidence/` holds exact input and run summaries.
- [uefi-zorn](https://github.com/kerrinz/uefi-zorn) supplies the board firmware, BootShim, menu and image packing tools.

## Build and protection

Start with the [iOS 26 build and evidence guide](docs/build-and-debug.md) and [device rules](AGENTS.md). The guide includes the format-2 preflight, the exact native build inputs and the verified offline packaging command. See the [UniXNU device repository guide](https://unixnu.com/zh/porting/device-repository).

The target is `92988a43` / `zorn` / slot A with dedicated 64 GiB `unixnu` storage. Device runs require a fresh exact manifest, independent watchdog, Recovery identity and full BCB readback. Android, the retained iPadOS system and Data have explicit protected windows. [Storage map and safeguards](docs/storage-unixnu64.md)

Most new code uses [BSD-2-Clause-Patent](LICENSE). PMGR retains its [MIT license](native/pmgr/LICENSE.MIT). Apple images, vendor binaries, private keys and generated boot images stay in the local workspace.

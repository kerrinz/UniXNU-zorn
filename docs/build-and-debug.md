# K80 iOS 26 构建与证据入口

当前候选是 iOS 26.6.2（23G90）。完整隔离源码、内核和启动包采用每轮清单里的固定输入。最新候选 v371 的清单给出 boot ID、内核、原根、启动参数、完整链接输入和源码重放。 [主线与最新结果](ios26-mainline.md) · [v371 构建清单](evidence/k80-ft3683-v371-early-smmu-cdc-offline-2026-11-19.json)

## 主机工作区

在共同父目录维护 `UniXNU/`、`UniXNU-houji/`、`UniXNU-zorn/`、`uefi-zorn/`、K80 小米内核与设备树参考。匹配候选记录中的 XNU、工具链、IPSW、依赖组件和原厂固件。Wi-Fi、摄像头等未验收组件的历史资料见对应阶段记录。

隔离 iOS 26 产物放在 `out/zorn/ios26-feasibility-20261107/`。复核新候选时查看同一轮的源码清单、实际编译配方、完整链接输入和 `boot-package/verified.json`。从新目录构建，保留已有归档及精确 SHA-256。准备工作区和证据中的本地输入路径均归属具体候选。 [主线验证记录](progress-2026-11-18-ios26-upstream-gpu.md)

## 格式 2 配置预检

在独立父目录准备 `UniXNU-zorn` 及同级 `UniXNU`，后者固定到 `630b85a307f19c8d8a4699d5bfc12f6796b874aa`。用 Python 3.11 或以上版本运行。

```sh
git -C UniXNU submodule update --init kits/XnuPrelink
bash UniXNU-zorn/scripts/check-package-profiles.sh "$PWD/out/profile-check"
```

脚本把 `profiles/os/ios-26.6.2-23G90/profile.toml` 安装到独立的上游检出，再用原版 `scripts/package.sh --check` 对两个明确的 profile 预检。23G90 解析为 iPhone18,1／v53ap、arm64e、16 KiB CPU 页和 `zorn_ios26_defconfig`。使用完整的 `--os ios-26.6.2-23G90`。上游数字别名 `--os 26` 解析为 iPadOS 26.5.2（23F84）。[官方打包流程](https://unixnu.com/zh/porting/packaging)

## 23G90 原生 release

在独立父目录准备 `UniXNU-zorn`、`uefi-zorn` 和固定提交的 `UniXNU`。主机需要 Xcode 27.0（27A266a）、Python 3.11 以上、mtools、LLVM 的 `clang`、`llvm-objcopy`、`llvm-nm`。`inputs` 指向保留 `out/zorn/ios26-feasibility-20261107/` 和 `references/ios26-build-inputs-20261107/` 的本地输入树。

```sh
inputs=/path/to/pinned-23g90-inputs
bash UniXNU-zorn/scripts/prepare-ios26-release.sh
UniXNU-zorn/scripts/package.sh --os ios-26.6.2-23G90 --no-deps \
  --release-inputs "$inputs" --uefi "$PWD/uefi-zorn" \
  --out "$PWD/out/zorn-release-23g90" --jobs 5
```

准备脚本只在独立的上游检出应用板级构建钩子，`scripts/package.sh` 沿用官方模板。通用 `release` 负责配置、步骤编排和最终 `verify`。23G90 的板级钩子从固定源码重建 XNU 和支持库，再编译板级对象，按记录顺序链接 arm64e 内核。生成的 `assym.s` 验证 CPU 页移位为 14。构建清单固定了已准备的 XNU 源码树、私有源文件和编译配方。[原生构建输入](../profiles/os/ios-26.6.2-23G90/native-release.json)

打包阶段新建 512 字节簇的 FAT32，写入新内核、固定加载器、ADT 和看门狗／触控交接标记，再把 FAT 与固定 FD 封装为启动镜像。最终在 `zorn/ios-26.6.2-23G90/zorn_ios26/` 生成 `boot/boot.img`、`payload/payload.img`、`kernel/kernel.macho`、`package.manifest.json`。`kernel/native-inputs.json` 和 `payload/payload.json` 记录本次链接与封装输入。FD、加载器、ADT 和安装根采用精确的 v371 归档，本流程重建内核和载体。重试请选择新的输出目录。

独立暂存快照上的正式运行编译了 1194 个基础对象和 206 个板级对象，两个支持库均从源码重建。链接无未定义符号。通用校验通过后，另行回读了内嵌 FD、FAT、五个 FAT 文件和两个标记扇区。[本地 release 构建证据](evidence/k80-ios26-native-release-2026-11-19.json)

## 固定输入的离线打包

准备原 v371 `boot-package` 归档、Python 3.11 以上、mtools 和 LLVM 的 `clang`、`llvm-objcopy`、`llvm-nm`。以下命令从归档重封装 FAT 和 boot，回读菜单与所有固定 FAT 成员，生成 `boot/boot.img`、`payload/payload.img`、`kernel/kernel.macho` 及 `package.manifest.json`，再运行 UniXNU 的标准产物校验。

```sh
verified=/path/to/v371/boot-package/verified.json
python3 -B UniXNU-zorn/scripts/package-ios26-v371-offline.py \
  --verified "$verified" --upstream UniXNU --uefi uefi-zorn \
  --out "$PWD/out/zorn/v371-budget-package"
```

整理版只移除旧菜单中的 `zorn26_gpu_provider_claim=1`。当前源码中实际读取的同类参数是 `zorn26_gpu_provider_claims_prep`。命令行由 1022 降至 994 字节，保留看门狗、Recovery 回收和触控选项。原 v371 归档和已安装根保持原身份。mtools 写入新 FAT 目录时间，因此每次重封装使用本次生成的 SHA-256。整理版的输出标记为离线验证，真机验收仍以原候选和对应审批记录为准。

当前构建验证通过上述本地命令执行。启动镜像和专有输入留在本机。

## 目录记录与日志

在共同父目录可离线检查格式 2 目录记录和查看 CDC 归档分析入口。

```sh
python3 UniXNU-zorn/scripts/check-catalog-record.py --upstream UniXNU
python3 UniXNU-zorn/scripts/analyze-ios26-ft-capture.py --help
python3 UniXNU-zorn/scripts/prepare-ios26-physical-review.py --help
```

格式 2 元数据、旧兼容 profile 和实际 iOS 26 构建各自有固定输入。 [格式 2 记录](repository-format.md) · [历史 OS](archived-os.md)

## 设备验收

启动前核对精确内核、FD、加载器、ADT、菜单、固件、根和配置。当前目标为 `92988a43`／`zorn`／slot A。固定 runner 核验 Recovery、GPT、各保护范围和 BCB 整页及尾部，再以一轮 scope／ready／claim 执行。300 秒看门狗和 600 秒主机回收预算以对应清单为准。

恢复后核对原生日志启动 ID、串口完成状态和保护区回读。当前设备停止原因见主线状态及取证记录。 [存储保护](storage-unixnu64.md) · [当前验收边界](ios26-mainline.md)

# K80 iOS 26 主线

目标是 Redmi K80（`zorn`、SM8650-AB、Adreno 750v2／Gen7.9.1）上的 iOS 26.6.2（23G90）。当前工作覆盖 direct-ring GPU、Metal、显示呈现和 FT3683。完成标准包括同一精确构建的固件和 GPU 任务、Metal 渲染与呈现、真实触控及客户端和资源生命周期。

## 证据入口

- v366 的原生已知图像、fence 2 和 CPU 读回通过。锁屏 500 ms 内确认 15 次 DSI 换帧，另有 1 次在窗外完成。持续滑动帧率和撕裂待测。 [实机证据](evidence/k80-gpu-v366-early-scanout-cdc-device-2026-11-19.json)
- v368 的触控启动越过 APPs SMMU 发布检查，随后遇到 UFS 锁忙。v370 的 250 ms 有界取锁与空闲复查已上机，设备在 332.968 秒自动回到 TWRP。串口缺少包含实际 SMMU 结果的长包。 [v368 实机证据](evidence/k80-ft3683-v368-after-root-device-2026-11-19.json) · [v370 归档](evidence/k80-ft3683-v370-ufs-lock-incomplete-device-2026-11-19.json)
- v371 将 FT3683 SMMU 结果提前放入 CDC 进度包，完整内核、启动包和离线重放通过。v371 真机试验待排。 [精确构建清单](evidence/k80-ft3683-v371-early-smmu-cdc-offline-2026-11-19.json)
- 23G90 本地 `release` 已从固定源码重新编译 16 KiB arm64e 内核并生成 K80 启动包。通用 `verify` 和载体回读通过。该产物尚待实机验证。[本地 release 记录](evidence/k80-ios26-native-release-2026-11-19.json)
- 最近的 v366 人工验收在启动前发现主 GPT 的 `vm-bootsys_b` 属性位与保护基线不一致。启动次数为零，手机当时在 TWRP，设备停止标记保持有效。 [启动前取证](evidence/k80-v366-manual-preboot-stop-2026-11-19.json)

## 文件与工作边界

- `UniXNU-zorn` 维护板级配置、XNU 接口、SoC 代码和试验。优先复用本地 UniXNU、UniXNU-houji、K80 内核与设备树的已固定输入。 [构建与证据入口](build-and-debug.md)
- `uefi-zorn` 维护 FD 板级包、BootShim、DarwinBoot 交接和镜像封装。候选以精确 FD、加载器、ADT、菜单、内核和根镜像绑定实际输入。 [固件仓库](https://github.com/kerrinz/uefi-zorn)
- 工作区 `out/zorn/ios26-feasibility-20261107` 存放 iOS 26 的隔离源码、构建和运行归档。`out/zorn/unattended-active/current.json` 记录当前设备状态。生成镜像和原始日志属于本地工作区。
- 实机仅针对 `92988a43`／`zorn`／slot A。Android、旧系统和 Data 受保护，实际启动采用固定 runner、新范围、独立看门狗和有界 Recovery 返回。 [当前存储布局](storage-unixnu64.md)

已退役平台见[历史 OS 适配记录](archived-os.md)。历史结果继续绑定原始构建。

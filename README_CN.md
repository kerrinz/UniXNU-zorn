# UniXNU-zorn

[English](README.md)

红米 K80（`zorn`，SM8650-AB，12 GB + 256 GB）的 UniXNU 设备仓库。**iOS 26.6.2（23G90）是当前主线**，覆盖 Adreno 750 GPU、Metal、显示呈现和 FT3683 触控。iPadOS 17 GPU 适配已退役。 [iOS 26 主线与证据](docs/ios26-mainline.md) · [历史 OS 适配记录](docs/archived-os.md)

## 当前验证范围

v366 完成了原生 GPU 已知图像任务，并测量了有界锁屏窗口内的 DSI 换帧。v371 已生成完整离线候选，可通过常规 CDC 进度包提前读取 FT3683 SMMU 结果。最近一次 v366 人工验收因主 GPT 与保护基线不一致在启动前停止。完整功能验收仍待完成。 [当前状态与范围](docs/ios26-mainline.md)

## 目录

- `native/`、`soc/sm8650/`、`patches/` 和 `scripts/` 存放内核集成、板级资源、构建与验证工具。
- `board.toml`、`configs/`、`profiles/os/`、`feeds.toml` 和 `unixnu.lock` 定义格式 2 构建输入。主线显式选择 `ios-26.6.2-23G90`，目录默认配置沿用历史 iPadOS 17 profile。
- [porting.toml](porting.toml) 记录整机适配范围，`docs/evidence/` 存放精确输入与试验摘要。
- [uefi-zorn](https://github.com/kerrinz/uefi-zorn) 提供板级固件、BootShim、菜单和镜像封装工具。

## 构建与保护

先阅读[构建和证据入口](docs/build-and-debug.md)及[设备规则](AGENTS.md)。构建指南提供格式 2 预检、主线原生构建输入和离线打包验证命令。[UniXNU 设备仓库指南](https://unixnu.com/zh/porting/device-repository)

目标为 `92988a43`／`zorn`／slot A，使用独立 64 GiB `unixnu` 分区。实机试验需要新清单、独立看门狗、现场核验 Recovery 和 BCB 整页读回。Android、保留的 iPadOS 系统和 Data 均有明确保护窗口。 [存储边界](docs/storage-unixnu64.md)

新增代码主要使用 [BSD-2-Clause-Patent](LICENSE)，PMGR 保留 [MIT 许可](native/pmgr/LICENSE.MIT)。Apple 镜像、厂商二进制、私钥和生成镜像留在本地工作区。

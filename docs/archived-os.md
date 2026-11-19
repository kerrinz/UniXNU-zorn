# 历史 OS 适配记录

## iPadOS 17.7.11（21H461）

红米 K80 的首条移植线采用 iPad7,1／j120ap 和 Darwin 23.6。早期实机确认过桌面、单指基本触控和有界自动回到 Recovery。GPU 实验只取得部分初始化和离线验证证据，未完成 GPU 与 Metal 验收。该 GPU 适配已退役，后续驱动开发集中于 iOS 26。 [早期实机记录](evidence/touch-desktop-fast-qualified.json) · [历史 GPU 记录](progress-2026-10-30-gpu.md)

UniXNU 格式 2 支持在同一设备仓库共享板级源码，并按 OS profile 解析各自的配置。两仓库保留适用于 iPadOS 17 的驱动、公共代码及已固定的兼容 profile，历史镜像和记录沿用原标识。独立 `unixnu` 中的原有 OS／SystemOS 和 Data 按当前布局保护。 [UniXNU 配置层](https://unixnu.com/zh/porting/device-repository#配置层) · [格式 2 记录](repository-format.md) · [存储布局](storage-unixnu64.md)

当前源码、候选镜像和验收从 [iOS 26 主线](ios26-mainline.md) 查阅。

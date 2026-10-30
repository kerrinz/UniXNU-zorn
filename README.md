# UniXNU-zorn

红米 K80 12 GB + 256 GB（`zorn`，Qualcomm SM8650-AB）的 UniXNU 实验移植。目标系统为 iPad7,1 / j120ap 的 iPadOS 17.7.11（21H461，Darwin 23.6 / XNU 10063.141.1）。

**截至 2026-10-29，机主已确认进入桌面、上滑解锁和图标点按正常。** 八核、8 GiB Data 跨启动保留及硬件低亮度已有真机证据；已验收竖屏基本单指交互，另取得双指独立 ID 跟踪与正常释放记录；仍保留调试镜像的有界自动回收。

## 仓库分工

本项目仅维护两个设备仓库：

- **[UniXNU-zorn](https://github.com/kerrinz/UniXNU-zorn)**：设备配置、板级驱动、XNU 补丁、构建与诊断脚本、结构化移植记录。
- **[uefi-zorn](https://github.com/kerrinz/uefi-zorn)**：Mu-Silicium 板级包、BootShim、UEFI 菜单与启动镜像打包。

SM8650 和 K80 的本地实现保留在这两个仓库内；使用现有上游 UniXNU、Mu-Silicium 及其依赖，不要求另建 SoC、触控或存储仓库。

## 移植状态

| 区域 | 已有结果 | 当前范围 |
| --- | --- | --- |
| 启动 | UEFI 菜单 → DarwinBoot → XNU → 原版用户态 → 桌面 | 菜单倒计时 5 秒；调试镜像会自动回 recovery |
| CPU | 8 核身份、定时器、IPI、绑定任务及跨核映射检查通过 | 前序偶发 CPU1 `SMP261` 早退原因未定；长期稳定性待验证 |
| 内存 | 8 GiB XNU 窗口进入系统 | 机型标称 12 GiB，不代表已验证全部物理内存 |
| 存储 | UFS 只读 OS / SystemOS；独立 8 GiB UFS Data 跨启动保留 | Data 不需要等量 RAM；当前不能启动 Android |
| 显示与亮度 | 1440 × 3200 CPU 显示；DCS 亮度降至 64 并读回 | 无硬件 GPU 加速；UEFI 菜单与系统亮度滑块未适配 |
| 触控 | FT3683 单指上滑 / 点按通过；双触点独立 ID 跟踪和释放有记录 | GPIO 轮询；系统多指手势、像素级校准及复杂手势未验收 |
| 其他外设 | 尚未验收 | Wi-Fi、蓝牙、音频、基带、相机、传感器及完整电源管理待适配 |

默认镜像与回退基线仍为 `42f3d518`，身份见 [桌面触控证据](docs/evidence/touch-desktop-fast-qualified.json)。独立源码快照的路径布局对照 `3a8ac966` 已连续两次进入桌面，记录见 [构建回归](docs/progress-2026-10-29-repro-build.md) 和 [双触点证据](docs/evidence/qualified-source-repeat-two-contacts.json)。不将一次进入桌面等同于整机适配完成。

## 目录

| 路径 | 用途 |
| --- | --- |
| `board.toml`、`configs/` | 设备描述与现有 defconfig |
| `unixnu.lock` | 已解析的上游源码版本 |
| `native/` | K80 的 UFS、Data、CPU、显示、FT3683、亮度与 PMGR 适配 |
| `patches/zorn/` | 追加到基础补丁集的设备 XNU 补丁 |
| `patches/core/` | 固定 UniXNU 基线所需的 CLI overlay |
| `scripts/` | 准备输入、构建、审计、临时启动和日志回收 |
| `porting.toml` | 按官方区域组织的移植记录、完成条件及证据 |
| `.github/workflows/porting-record.yml` | 官方移植记录检查 |
| `docs/` | 构建说明、阶段调查和可提交的证据摘录 |

## 开发记录

- [结构化移植记录](porting.toml)：采用与 [sheng 设备页](https://unixnu.com/zh/devices/sheng) 相同的区域与记录字段。
- [构建、测试与日志](docs/build-and-debug.md)：前置输入、当前桌面候选的完整参数及回收命令。
- [格式与发布范围](docs/repository-format.md)：本次整理与后续格式 2 构建迁移的边界。
- [触控与桌面验收](docs/progress-2026-10-29-touch-events.md)、[Data / 八核](docs/progress-2026-10-28-data-smp-touch.md)、[硬件低亮度](docs/progress-2026-10-28-brightness.md)。

历史阶段文档按日期保留，其中“尚未进入桌面”等描述只代表当时状态；当前结论以本页和移植记录为准。

## 构建与验证

在共同父目录准备 `UniXNU/`、`UniXNU-zorn/` 和 `uefi-zorn/`；另需 Mu-Silicium、匹配的 IPSW、工具链、SDK、签名策略及已经准备的 Data 输入。源码固定版本和准备顺序见 [构建说明](docs/build-and-debug.md)。

**现有入口仍使用格式 1 构建布局。** 上游更新后的 157 个补丁已两次干净重放，1011 个新 XNU 对象及预链接、统一打包通过；实际工作树快照的路径对照 `3a8ac966` 已连续两次进入桌面并通过八核 / Data / 低亮度检查，双触点跟踪也已取得真机记录；布局问题仍待定位，原已验收默认镜像仍保留为 `42f3d518`。该结果仍含显式路径 / 布局对照，历史 ABI 候选也是显式输入，尚不是仅凭源码和 IPSW 的一键构建。详见 [构建回归记录](docs/progress-2026-10-29-repro-build.md)。

仅检查结构化记录，在 UniXNU 主仓库执行：

```sh
python3 scripts/porting-record.py check --device ../UniXNU-zorn
```

生成镜像与读取日志的入口（在共同父目录执行）：

```sh
python3 UniXNU-zorn/scripts/build-zorn-debug.py --help
python3 UniXNU-zorn/scripts/read-zorn-log.py --save out/zorn/last-log.bin --tail 100
```

第一条只查看参数；第二条从目标 K80 的 recovery 读取现有日志。实际构建、临时启动及自动回收使用 [已记录的完整配置](docs/build-and-debug.md)，不要把构建器的默认只读基线当作桌面触控配置。

## 设备与数据范围

- `92988a43` = K80 / `zorn`，唯一目标，保持槽位 `b`。
- `f85d4270` = CC9 / `pyxis`，禁止对其操作。

所有 adb / fastboot 命令必须指定 `-s 92988a43` 并核对 product / slot。仅用 `fastboot boot` 临时启动，不 flash、不 erase、不改槽位或 GPT。

当前 userdata 已经机主授权用于系统，**不要启动 Android，也不要重新刷入 userdata**。OS / SystemOS 保持只读；持久写入仅限已核验的独立 Data 窗口、既有 4 KiB 日志块和保留尾部并读回的 misc recovery BCB。布局及既有窗口边界见 [构建说明](docs/build-and-debug.md#存储与回收边界)。当前不支持 Android / iPadOS 双系统共存。

## 文档与许可

- [官方移植流程](https://unixnu.com/zh/porting/steps)、[设备仓库与发布](https://unixnu.com/zh/porting/device-repository#publish)、[构建指南](https://unixnu.com/zh/building)、[技术参考](https://unixnu.com/zh/reference/)。
- 参考实现：[UniXNU-sheng](https://github.com/UniXNU/UniXNU-sheng)、[同 SoC 的 UniXNU-houji](https://github.com/lonzzi/UniXNU-houji)。硬件参数与 Darwin 版本必须按 K80 核对。

本仓库新增代码主要使用 [BSD-2-Clause-Patent](LICENSE)。PMGR 适配保留 [MIT 许可](native/pmgr/LICENSE.MIT)，其余上游文件保留各自版权头。IPSW、Apple 二进制、私钥、厂商固件和生成的镜像不随源码发布。

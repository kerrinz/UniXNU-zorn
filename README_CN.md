# UniXNU-zorn

[English](README.md)

红米 K80（`zorn`，SM8650-AB，12 GB + 256 GB）的 UniXNU 设备仓库。目标系统为 iPad7,1 / j120ap 的 iPadOS 17.7.11（21H461，Darwin 23.6 / XNU 10063.141.1）。

本仓库负责板级配置、DTS、原生板级服务、XNU 补丁、打包集成与诊断。[uefi-zorn](https://github.com/kerrinz/uefi-zorn) 负责 Mu-Silicium 板级包、BootShim 和固件交接。[UniXNU](https://github.com/UniXNU/UniXNU) 提供构建工具、组件目录以及 ARM64 / OS 配置层。

[结构化移植记录](porting.toml) 是各部分状态的权威来源。官网按照[记录与发布指南](https://unixnu.com/zh/porting/records#publishing-and-reuse)，从已发布版本根目录的 `board.toml` 和 `porting.toml` 生成设备文档；README 作为仓库入口。

## 当前状态

截至 2026-10-30，机主已确认进入桌面、上滑解锁及图标点按正常。八核身份、定时器、IPI、绑定任务检查和九轮映射检查通过；8 GiB XNU 内存窗口、保留的 8 GiB UFS Data 及面板亮度 64 均有绑定身份的真机结果。已观察到两个独立触点 ID 及正常释放，系统多指手势仍未验收。

CPU1 页表根发布修正通过同一完整内核的「0 失败 / 1 通过 / 0 失败 / 1 通过」对照，以及两个相差 16 KiB、无附加早期探针的布局验证。这是该窄修正的有界证据。另一个偶发停苹果标志的 GUI 问题仍未解决。最后一次 `c50ca7ea` 观察显示锁屏，记录到全部八核的 USER / SYSTEM 累计记账进展，并自动回到 recovery；它不构成性能或长期稳定性验收。

默认镜像仍为 `42f3d518`；`3a8ac966` 的两次机主确认桌面结果作为独立基线保留。它们均为会有界自动回收的调试镜像。Wi-Fi、蓝牙、音频、蜂窝通信、相机、传感器和完整电源管理尚未验收。本文不宣称硬件图形加速已可用，本次更新不包含 GPU 开发进度。

证据与验收边界见两仓库同步维护的[非 GPU 进度摘要](docs/progress-2026-10-30-non-gpu.md)。

## 前置条件

- 在 `UniXNU-zorn/` 和 `uefi-zorn/` 的相邻目录准备匹配的 UniXNU 检出，以及已有的 Mu-Silicium 依赖。受版本控制的 `soc/sm8650/` 是随设备仓库版本管理的板级 SoC 资源子集，不需要额外建立 SoC 仓库。
- 匹配的 Xcode / iPhoneOS SDK 和固定版本的组件源码。[source-pins.json](source-pins.json) 记录已准备组件的字节指纹；[unixnu.lock](unixnu.lock) 记录已解析的源码提交。
- 匹配的原始 IPSW、原版 trust cache、owner 策略、已准备的 Data 种子、已核验固件和历史 ABI 审计输入。见[专有输入说明](proprietary-files.txt)及[构建说明](docs/build-and-debug.md)。当前不能仅凭源码和 IPSW 完成从零构建。

修改移植实现前，请阅读[设备仓库指南](https://unixnu.com/zh/porting/device-repository)、[构建指南](https://unixnu.com/zh/building)、[启动验证顺序](https://unixnu.com/zh/porting/bring-up)和 [AGENTS.md](AGENTS.md)。

## 配置与构建入口

根配置现采用格式 2。在 UniXNU 检出内使用独立输出目录验证配置：

```sh
./unixnu defconfig zorn_union_defconfig -D ../UniXNU-zorn --out ../out/zorn-format2
./unixnu status --json -D ../UniXNU-zorn --out ../out/zorn-format2
python3 scripts/porting-record.py check --device ../UniXNU-zorn
```

四层配置、所选组件、显式补丁顺序、硬件 DTS 和构建树组装已通过主机检查。新格式 2 输出路径的完整原生内核 / payload 等价性及真机运行尚未验收。历史真机结果只对应各自记录的输入，不自动成为本次迁移的验证结果。见[迁移与发布范围](docs/repository-format.md)。

原有带保护的调试入口保留，在各仓库的共同父目录执行：

```sh
python3 UniXNU-zorn/scripts/build-zorn-debug.py --help
```

它使用 [compat/legacy/board.toml](compat/legacy/board.toml) 中固定的格式 1 兼容配置，生成独立输入视图，保留原平铺构建路径及审计 / ready / 回收检查。完整参数见 [build-and-debug.md](docs/build-and-debug.md)；`--help` 不构建或启动设备。兼容配置选择已通过主机检查，本次文档更新没有用它生成新内核或启动手机。

## 目录

- `board.toml`、`feeds.toml`、`soc/sm8650/`：格式 2 选择与板级 SoC 输入。
- `configs/`、`dts/zorn.dts`、`patches/xnu/series`：内核配置、硬件描述和显式补丁顺序。
- `native/`、`scripts/`、`patches/zorn/`：板级服务、带保护的构建 / 诊断入口及板级补丁。
- `package/`：板级 kit 身份；公共固件模块来自 UniXNU。
- `compat/legacy/`：保留的调试配置，与格式 2 路径分开。
- `porting.toml`、`docs/evidence/`：结构化记录和受版本控制的证据摘要。大型本机构建目录及原始日志路径仅作归档引用，不代表随仓库发布的公共产物。

## 设备与存储边界

唯一授权目标为 `92988a43` / `zorn` / 槽位 `b`；`f85d4270` 是 CC9，禁止操作。使用固定目标 runner 和临时 `fastboot boot`；不刷写、不擦除、不改槽位或 GPT。

手机 userdata 已包含准备好的系统，禁止启动 Android 或重新安装 userdata。OS / SystemOS 保持只读。持久写入仅限 userdata 相对 192 GiB 处的既有 Data 窗口（2,097,217 个 4096 字节块）、原有单个 4 KiB 日志块，以及保留尾部并完整读回的 recovery BCB。禁止重置或扩大 Data。`board.toml` 中的 userdata 范围是相对于容量的历史描述，不是绝对 GPT 地址。

## 发布与许可

对于尚无匹配已发布提交来标识受测工作树字节的结果，记录使用 `implemented` 和源码引用。不要把当前 Git HEAD 指派给历史运行，也不要在缺少匹配证据时提高完成等级。发布经审阅的源码与记录文件，并确认 `Porting record` 工作流后，再请求官方目录收录；本地验证通过不代表官网已经更新。

新增代码主要使用 [BSD-2-Clause-Patent](LICENSE)；PMGR 保留其 [MIT 许可](native/pmgr/LICENSE.MIT)，上游文件保留各自声明。Apple 镜像、私钥、厂商二进制和生成的启动镜像不随仓库分发。

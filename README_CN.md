# UniXNU-zorn

[English](README.md)

红米 K80（`zorn`，SM8650-AB，12 GB + 256 GB）的 UniXNU 设备仓库。默认format2配置仍为iPad7,1／j120ap的iPadOS17.7.11（21H461，Darwin23.6／XNU10063.141.1）；当前GPU适配主线使用独立固定的iOS26.6.2／23G90输入，保留17基线。

本仓库负责板级配置、DTS、原生板级服务、XNU 补丁、打包集成与诊断。[uefi-zorn](https://github.com/kerrinz/uefi-zorn) 负责 Mu-Silicium 板级包、BootShim 和固件交接。[UniXNU](https://github.com/UniXNU/UniXNU) 提供构建工具、组件目录以及 ARM64 / OS 配置层。

[结构化移植记录](porting.toml) 是各部分状态的权威来源。官网按照[记录与发布指南](https://unixnu.com/zh/porting/records#publishing-and-reuse)，从已发布版本根目录的 `board.toml` 和 `porting.toml` 生成设备文档；README 作为仓库入口。

截至2026-11-16，v251已取得会话修复的实机证据：两个正常IOKit连接打开、竞争Query被独占检查拒绝、两连接关闭，随后120／120次同表面呈现查询及实际退出0。完整5680字节日志、真机4×4棋盘、332.501秒自动回TWRP和保护／BCB检查均绑定本次kernel9f25532a／booteac7550c／rootc9382b31。原生GPU会话仍独占，普通系统GPU桌面、FT3683完整手势和稳定性尚未验收。见[当前进度](docs/progress-2026-11-16-ios26.md)和[251精确证据](docs/evidence/k80-gpu-v251-lazy-session-observed-2026-11-16.json)。

保留的v252已有普通系统合成器的实机结果：backboardd取得真实原生会话，第一个正常关闭并重新取得后端；正常表面804／SID836的GPU access fence807完成，acquire／copy／账本匹配。摄像头确认物理锁屏和时钟推进；一次受保护启动332.650秒自动回TWRP，39帧串口／9170字节进程观测前缀、8核采样与保护检查通过。这是有界系统客户端／显示证据；并发原生会话、逐帧GPU写入归属、完整生命周期／解锁后桌面和FT3683手势仍未完成。[252交接](docs/handoff-2026-11-16-k80-ios26-gpu-v252-early-system.md)、[精确实机证据](docs/evidence/k80-gpu-v252-early-system-observed-2026-11-16.json)。

v253已完成独立离线Board所有权候选：实际会话记录／generation、失败保留及精确正常退休替换全局身份标量，完整内核／启动包与源码、sanitizer检查通过，root／FD／ADT／配置沿用252。物理会话仍独占，共享执行链路尚未接通，未进行253实机。[253交接](docs/handoff-2026-11-16-k80-ios26-gpu-v253-board-sessions.md)。

v254已把实际OOB状态和transport／maps引用移到Ring拥有的物理租约，并接通原DirectHfi请求／clear与Board释放后的正常退休；当前源码／sanitizer／完整内核和启动包检查通过，8个头文件消费者全部重编。仍为单物理会话，持续共享授权／多上下文调度尚未实现，未进行254实机。[254交接](docs/handoff-2026-11-16-k80-ios26-gpu-v254-physical-oob.md)。

v255已接通独立于客户端的Board物理授权与Ring／maps／HFI／generation；DirectHfi保留Ring并逐次核对该真实授权，正常逻辑关闭后才释放物理授权并退休租约。当前源码／sanitizer／31对象重编完整内核与启动包检查通过，仍为一个逻辑原生会话，未进行255实机。[255交接](docs/handoff-2026-11-16-k80-ios26-gpu-v255-physical-authority.md)。

v256已完成新操作mutex／上下文代码的单次普通系统实机：333.725秒自动回TWRP，首会话关闭0后重开、第二会话末采样3293次调用／method13／返回0；正常表面151／SID183的access fence154完成。39帧58147字节串口、9170字节完整观测前缀、8核采样、保护／BCB及物理锁屏时钟推进通过。逻辑会话仍独占，逐次MMIO切换oracle、每帧GPU写入归属、完整daemon生命周期／全GPU桌面及FT3683手势未验收。[256交接](docs/handoff-2026-11-16-k80-ios26-gpu-v256-operation-context.md)、[精确实机证据](docs/evidence/k80-gpu-v256-operation-context-observed-2026-11-16.json)。

v257已接通服务／Board／Ring真实逻辑成员与连续物理OOB／最后成员释放，源码／sanitizer／完整内核与离线启动包检查通过，首成员退出保留剩余物理所有者。未进行257设备scope／启动，跨任务隔离、待完成上下文关闭及完整GPU／触控验收仍未完成。[257交接](docs/handoff-2026-11-16-k80-ios26-gpu-v257-shared-members.md)。

v258通过独立物理Root检查与精确RestoreKernel恢复已完成的其他成员上下文，再继续调用方原关闭路径；当前源码／完整内核／离线启动包检查通过，未进行258实机启动。未完成fence的clientClose续行及完整GPU／触控验收仍需继续。[258交接](docs/handoff-2026-11-16-k80-ios26-gpu-v258-context-handover.md)。

v259已接通清理前真实pending状态和同一次Close内的有界续行，不重做已完成清理段。当前源码／sanitizer／完整内核／离线启动包通过，未进行259实机启动。实际退出、作业退休／跨任务GPU／呈现及完整触控仍需验收。[259交接](docs/handoff-2026-11-16-k80-ios26-gpu-v259-bounded-close.md)。

v260修复259上机准入前发现的原生VFS身份不一致：平台记录／panic头已固定到候选源码，实际native预处理与旧覆盖层拒绝检查通过。完整内核／离线启动包通过，259共享上下文／关闭正文保持。尚无260实机启动，最新实机256。[260交接](docs/handoff-2026-11-16-k80-ios26-gpu-v260-platform-identity.md)。

260已完成一次精确普通客户端回归，333.19秒自动回TWRP；平台记录／CDC身份、八核及七组保护／BCB通过。第一段Close0，第二段Close0xe00002ca，末次SubmitBatch样本0xe00002c2；相机不可用，正常退出／GPU写入呈现／完整触控未验收。[260实机证据](docs/evidence/k80-gpu-v260-platform-identity-observed-2026-11-16.json)。

v261单次启动约333.63秒自动回核验TWRP，39帧串口与240秒录像成功。用户确认进入iOS桌面，滑动／点按／长按／解锁有响应，最终长按设置卡死；两条路径均低帧率，不比较CPU／GPU高低。首个记录后端错误为BoMap NoResources，内部原因及最终卡死仍待定位。[261交接](docs/handoff-2026-11-17-k80-ios26-gpu-v261-client-failure.md)。

官网收录EOF报错已在本地通过精简入口、完整归档历史记录和CI完整性检查修复；见[收录诊断与验证](docs/catalog-ingestion-2026-11-17.md)。线上页面仍需发布新版本并由官方重新抓取。

## 当前状态

截至 2026-10-30，机主已确认进入桌面、上滑解锁及图标点按正常。八核身份、定时器、IPI、绑定任务检查和九轮映射检查通过；8 GiB XNU 内存窗口、保留的 8 GiB UFS Data 及面板亮度 64 均有绑定身份的真机结果。已观察到两个独立触点 ID 及正常释放，系统多指手势仍未验收。

历史检查点（2026-11-13）：iOS 26 的 CPU 渲染路径在有界 `b0da41e9` 启动期间进入系统锁屏，机主已目视确认；CPU 内核 SHA-256 为 `9f6474ce789a8ac860417e3e7526ca5e241366c4dd7bd3c8b1731712c409a091`。机主确认此前 GPU 分支曾在 K80 真机上启动测试，但无法进入系统锁屏，因此当时转向 CPU 渲染。这些 GPU 真机尝试曾推进到 GPUCC/PLL 和时钟阶段、保持 masked 的 SMMU IRQ 路由、GMU 冷时钟前缀与 SMMU 全局控制，以及只读 bank/stream census；它们属于分阶段平台初始化结果。GMU 固件/HFI 启动、GPU 提交与 fence、GPU 渲染、Metal 和 GPU 显示仍未验收。最新 v80 GPU 候选仅完成离线完整链接，未选用、未上机；v73 Recovery停止门属于该历史检查点；后续独立scope见当前进度。详见[GPU 进度记录](docs/progress-2026-10-30-gpu.md)。

CPU1 页表根发布修正通过同一完整内核的「0 失败 / 1 通过 / 0 失败 / 1 通过」对照，以及两个相差 16 KiB、无附加早期探针的布局验证。这是该窄修正的有界证据。另一个偶发停苹果标志的 GUI 问题仍未解决。最后一次 `c50ca7ea` 观察显示锁屏，记录到全部八核的 USER / SYSTEM 累计记账进展，并自动回到 recovery；它不构成性能或长期稳定性验收。

默认镜像仍为 `42f3d518`；`3a8ac966` 的两次机主确认桌面结果作为独立基线保留。它们均为会有界自动回收的调试镜像。Wi-Fi、蓝牙、音频、蜂窝通信、相机、传感器和完整电源管理尚未验收。v250有界Metal图像／120帧查询及物理输出已通过；普通系统GPU桌面和稳定性仍未验收，见最新进度。

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

当前新安装目标为 `92988a43` / `zorn` / 槽位 `a`；`f85d4270` 是 CC9，禁止操作。机主完整重刷Android后，明确授权创建64GiB独立`unixnu`分区并重新安装iPadOS17，保留Android系统、OrangeFox和槽位A。只用固定runner显式`--unixnu64-install-trial`与临时`fastboot boot`；历史slotB/userdata镜像不得启动到新布局。

新`unixnu`为4096字节LBA47271680..64048895，uniqueGUID `b279731f-ccad-4ef5-a8b7-e7440cd08de3`。OS/SystemOS已写入并全量读回，运行时仍只读。初始8GiB Data COW窗口移至unixnu相对16GiB，共2097217块；新元数据/cookie与旧store不同。日志仍仅unixnu相对2291712的单4KiB块，recovery BCB保留尾部并整页读回。64GiB是专用分区容量，目前逻辑Data仍8GiB。Android实际启动、长期完整性和GPU执行需分别验收。详见[新安装证据](docs/evidence/dual-system-reinstall-2026-11-01.json)。

## 发布与许可

对于尚无匹配已发布提交来标识受测工作树字节的结果，记录使用 `implemented` 和源码引用。不要把当前 Git HEAD 指派给历史运行，也不要在缺少匹配证据时提高完成等级。发布经审阅的源码与记录文件，并确认 `Porting record` 工作流后，再请求官方目录收录；本地验证通过不代表官网已经更新。

新增代码主要使用 [BSD-2-Clause-Patent](LICENSE)；PMGR 保留其 [MIT 许可](native/pmgr/LICENSE.MIT)，上游文件保留各自声明。Apple 镜像、私钥、厂商二进制和生成的启动镜像不随仓库分发。

## GPU范围

已发布CPU自有内存准备代码及默认关闭的诊断辅助工具，硬件GPU执行、渲染和Metal仍未验收。详细研究摘要保留于[GPU进度](docs/progress-2026-10-30-gpu.md)；大量隔离源码胶囊和原始日志属于本地归档，不代表完整生产驱动。历史输入计数仅属于各自冻结轮次。

当前原厂重刷后的unixnu64安装、Data保留和机主确认的触控结果见[存储说明](docs/storage-unixnu64.md)。旧userdata/slotB镜像不得用于新布局。

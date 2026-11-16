# K80 iOS 26 GPU 驱动交接

> 当前暂停续接入口：[v179 暂停交接](handoff-2026-11-14-k80-ios26-gpu-v179-paused.md)。最后成功实机为 v178；v179 未完成构建、未启动。

2026-11-14。GPU 调试目标已暂停。最后一轮真机试验已结束，K80 已自动返回 TWRP。接手范围是同一台 Redmi K80（`92988a43`、`zorn`、slot `a`）的 iOS 26.6.2（23G90）Adreno 750v2 / Gen7.9.1 direct-ring 主线。继续优先 GPU。最终验收仍包括固件认证、GMU/HFI、GPU 作业和真实 fence、已知图像、Metal 与显示呈现，以及 FT3683 完整触控。**禁止逆向工程和反汇编**。依据开源源码、设备树、构建输入与实机日志。

## 当前接手点

- **锁屏与串口**：v138 恢复 CPU 显示初始化顺序后已实拍确认锁屏，v152 再次实拍确认。GPU 调试镜像以 USB CDC `/dev/cu.usbmodem21201` 采集带镜像标记的检查点，并与当轮 UFS 记录核对。独立 GENI UART 的实体线路接收仍待验证。[v152 锁屏实拍](/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-cpu-gpu-v152-mmu-preflight-8c62ce8e9a674b1db77e89269eb1f453/root-trial/camera/late-v152.jpg)
- **GPU 已验证**：GMU CM3 启动、三队列 HFI 实际应答、默认频率和带宽投票、USER/LPAC 页表 CPU 侧构造、GX 关断下的 QTB 隔离与释放、两条 stream 的阻断态和故障 IRQ，以及 v158 的 PRR 写入回读。
- **恢复后先修 ACTLR**：v158 停在 USER 的 ACTLR/TLB 步骤。源码显示 ACTLR 白名单依赖每个端点的 `requested_actlr_present`，但现有设备树解析只在 GMU 上下文映像准备时执行。USER 的源设备树值 `0x32b` 因而未进入其写入，按现有 guard 条件会被拒绝。先复用原解析逻辑填充 USER 和 LPAC，保留对实际阻断 stream 的匹配及回读。下一轮分别记录 ACTLR 写入、回读和 TLB 同步，验证修复后再启用两条 stream。故障点的具体写入拒绝属于源码定位，v158 串口只记录到整个步骤返回 I/O 错误。
- **后续验收**：核对 USER/LPAC 上下文写入和 stream 激活，再推进 GX OOB、HFI START、CP、ZAP、有界 GPU 作业及真实 fence、已知图像、Metal 与显示呈现。FT3683 连续轮询已有证据，本阶段的完整触控事件仍待实机验收。

## 已验证的里程碑

- CPU 渲染锁屏基线 `b0da41e9` 由机主目视确认，必须保留。独立的无 Home 键候选 `996ff287` 已由机主解锁进入桌面、打开设置，并确认打字跟手。两次 XNU 采样确认八核都有实际运行记账，FT3683 持续轮询。操作设置会回锁屏，机主接受这一阶段成果并把排查留后。[CPU 锁屏基线](evidence/k80-CPU-keystore-retag-observed-2026-11-13.json) · [桌面、触摸和八核阶段证据](evidence/k80-ios26-cpu-desktop-touch-eightcore-milestone-2026-11-13.json)
- GENI UART 的控制器已报告发送完成，实体线路接收仍待验证。当前用 Mac 上的 USB CDC 采集带镜像标记的 GPU 日志，返回 TWRP 后与同次启动的 UFS 检查点核对正文。[日志实现与实测](ios26-geni-uart.md)
- v120 通过真实 stream owner 激活 GMU SID 5、bank 2，CM3 保持复位，逐字核对 ITCM shadow 和 DTCM 固件数据。v122 把五个硬件实读的 DTCM 版本字交给板级驱动，并匹配实时 GPU 与 SCM 设备树节点。[v120](evidence/k80-gpu-v120-tcm-cdc-observed-2026-11-14.json) · [v122](evidence/k80-gpu-v122-cx-cdc-observed-2026-11-14.json)
- v124 实机完成 CX 安全初始化。现有 SCM owner 解析调用约定、检查服务可用性并执行 K80 请求 `0xb`，返回 `m=20,s=0000000000000000`。TWRP 在 332.83 秒恢复，七组保护样本一致。[v124](evidence/k80-gpu-v124-cx-cdc-observed-2026-11-14.json)
- v125 再次实测 SCM 返回 `0`，随后以 `m=22` 停在掩蔽 GMU IRQ 的创建或注册。寄存器配置尚未执行。TWRP 在 333.87 秒自动恢复，七组保护样本一致，CDC 与新 UFS 记录完成核对。该轮尚未执行 GMU/CM3 启动和 HFI。[v125](evidence/k80-gpu-v125-irq-cdc-observed-2026-11-14.json)

## 接手入口

工作区为 `/Volumes/macData/projects/ios-zorn`。先看 [AGENTS.md](../AGENTS.md)、[porting.toml](../porting.toml) 和 [GPU 进度](progress-2026-10-30-gpu.md)。最新可用实机证据及后续启动点见下方。

设备试验前确认 `out/zorn/unattended-active/current.json` 中的连接模式、活动试验和停止标记。使用新镜像的固定 runner、scope、ready、admission 和单次 claim。每轮从已核验的 TWRP 出发，验证保护样本和 BCB 整页及尾部，保留 300 秒独立看门狗和 600 秒主机回收限时。若无法返回 Recovery，停止设备操作并保存证据。保留 Android、iPadOS 17 和 Data。旧 claim 已消费时不得复用。

direct-ring 源码顺序为 TCM、版本及 shadow → CX SCM → GMU 配置和 IRQ → CM3 启动 → PDC/RSC → HFI。依据固定 K80 源码的 `gen7_gmu_first_boot` 和实机回读继续推进。原厂 Gen7.9.1 的 HWSCHED 候选继续独立保留。

## 2026-11-14 后续实测

v126 至 v129 的四个单次 scope 均已消费，手机已自动回到 TWRP。四次 CDC 正文均与同次启动的 UFS 检查点一致，每次七组保护样本均匹配。最新 v129 `e2e834e3` 返回 `m=30,s=0000000000000000,j=80013f0080013f00`，确认 GMU 掩蔽 IRQ 和寄存器配置、direct HFI 接收端绑定、ICC 输入绑定及初始 RPMh 投票。CM3 保持复位。v128 原始捕获的 HFI 布尔值漏计了高于 26 的成功阶段，证据按原始 `m=28` 重新解释，v129 捕获器已修正。[v126](evidence/k80-gpu-v126-irq-cdc-observed-2026-11-14.json) · [v127](evidence/k80-gpu-v127-hfi-bind-cdc-observed-2026-11-14.json) · [v128](evidence/k80-gpu-v128-icc-bind-cdc-observed-2026-11-14.json) · [v129](evidence/k80-gpu-v129-icc-initial-cdc-observed-2026-11-14.json)

下一依赖是 GEM NoC QoS 的编程窗口。复用已链接的 proxy vote、GCC 时钟和 QNoC 寄存器流程，按 K80 源码核实 shared fabric 的所有权后完成 recommit，再使能 GMU IRQ、提交启动带宽投票和进行有界 CM3 启动。v129 构建目录的 `offline-gmu-irq-arm/` 保留了已编译的 IRQ enable 拒绝传播修正。三队列接收端目前只完成 CPU 检查与绑定。原厂 Gen7.9.1 固件使用 HWSCHED 描述符，固件握手和 direct-ring 提交是后续独立验证项。

v130 实测全部 16 个 GEM NoC 端口可读，只有 4 个匹配 K80 源码配置。v131 的写入路径在首次端口读回前返回，`GenericARMPE` 的顶层发布顺序解释了私有 provider 前置条件为何不成立。v133 把 `gem-noc` 加到该试验模式的顶层排除列表并验证提升后的 DT 身份，沿用 K80 的 proxy vote、GCC 时钟及原始字段写掩码。[v130 证据](evidence/k80-gpu-v130-qos-readback-cdc-observed-2026-11-14.json) · [v131 证据](evidence/k80-gpu-v131-qos-program-cdc-observed-2026-11-14.json)

v133 `ed704f52` 已实测恢复正常投票并匹配全部 16 个 GEM NoC QoS 端口（`m=32,q=ffffffff`）。TWRP 自动回收 332.58 秒，七组保护样本一致。后续 GMU 使能候选保留该私有 provider 路径。[v133 证据](evidence/k80-gpu-v133-qos-private-cdc-observed-2026-11-14.json)

本地 houji `98bc0960f96076de8e8d16efcfb0c0603b166b85` 的主机 direct-ring 路径使用 `vendor/Ace5Gmu/giulia_gpu_hfi.h` 的 17 队列表与固件通信。K80 参考源码的普通 direct 路径定义三条启用队列，原厂 Gen7.9.1 描述则绑定 HWSCHED 分支。v142 已用三队列完成首条原厂固件查询。CPU 直接提交 CP ring 仍需独立实测。

v134 `ea2090b1` 经 GIC 回读确认 GMU 的两路 SPI 已使能。v135 `7588894c` 完成 K80 的 2136718 kB/s 启动带宽投票，返回 `m=36,a=3,q=ffffffff`。两轮均保持 CM3 复位，CDC 和 UFS 正文相符，手机自动回到 TWRP，七组保护样本一致。[v134 证据](evidence/k80-gpu-v134-gmu-arm-cdc-observed-2026-11-14.json) · [v135 证据](evidence/k80-gpu-v135-boot-bandwidth-cdc-observed-2026-11-14.json)

v137 `7aee4f03` 保留 v135 GPU 结果。PID1 启动 150 秒后记录到 SpringBoard 的 PID，BackBoard 交换帧和像素复制都是 0。两张摄像头画面像启动控制台，符合机主未见锁屏的反馈。对照已验证的 CPU 镜像实际链接的 `GenericARMPE.cpp`，发现 GPU 候选漏掉了 CPU presenter 前的 `MiniIOSurfaceStart` 和 `MiniAppleKeyStoreStart`。v138 恢复了该顺序。[v137 证据](evidence/k80-gpu-v137-ui-census-cdc-observed-2026-11-14.json)

v138 `19e248ea` 的两次实拍均已看到系统锁屏，时间显示持续更新。PID1 后 150 秒，BackBoard 交换帧和像素复制均达到记录上限 255。GPU 串口仍为 `m=36,a=3,q=ffffffff`，与 UFS 检查点一致，CM3 保持复位。TWRP 在 332.37 秒恢复，七组保护样本一致。后续 GPU 临时镜像沿用此 CPU 显示初始化顺序。[v138 证据及摄像头路径](evidence/k80-gpu-v138-ui-restore-cdc-observed-2026-11-14.json)

v139 `834de2bf` 实测 GMU CM3 启动确认。USB CDC 回报 `m=38,c=f0000100`，其中 `FW_INIT_RESULT[8:0]` 为 `0x100`。UFS 的复位字段采自解除复位前，后续 CDC 字段记录了实际解除及轮询。摄像头拍到 CPU 锁屏，两项帧计数均达 255。TWRP 在 332.77 秒恢复，七组保护样本一致。v136 的旧候选从未启动，由保留锁屏修复的 v139 替代。[v139 证据](evidence/k80-gpu-v139-cm3-ui-cdc-observed-2026-11-14.json)

v140 `21d1fca1` 在 CM3 返回成功之后执行原厂 PDC/RSC 的 19 次受检查写入，串口返回 `m=40,p=c3130000` 并与 UFS 正文核对。画面仍为 CPU 锁屏，两项帧计数均达 255。TWRP 在 332.73 秒恢复，七组保护样本一致。本轮记录写调用返回及软件 loaded 位，不包含 RSCC 休眠/唤醒实测。[v140 证据](evidence/k80-gpu-v140-pdc-rsc-cdc-observed-2026-11-14.json)

v141 `b99575bf` 完成 HFI 控制初始化写入，轮询读到状态 bit 0，串口为 `m=42,h=e0000001`。TWRP 在 332.79 秒恢复，CDC 与 UFS 正文相符，七组保护样本一致。两项 CPU 帧计数均达 255。[v141 证据](evidence/k80-gpu-v141-hfi-control-cdc-observed-2026-11-14.json)

v142 `ab30dbb9` 在三队列 HFI 上发送 `GET_VALUE(GMU_WARMBOOT,0)`。串口记录 `m=44` 和四字应答 `0001040c/0010030c/00000001/00000000`，确认请求头匹配、返回值 1、固件状态 0。相机仍拍到 CPU 锁屏，TWRP 在 332.66 秒恢复，七组保护样本一致。[v142 证据](evidence/k80-gpu-v142-hfi-query-cdc-observed-2026-11-14.json)

v143 `4aab9211` 的首次 PERF 表试验在发命令前返回 `kIOReturnNotReady`。实际表入口要求启动锁未持有，而当前入口由已持锁的板级 owner 调用。TWRP 在 333.92 秒恢复，CDC 和 UFS 正文相符，七组保护样本一致。板级表已与新读的 TWRP 设备树逐项核对，SoC 557 修订版 2.0、AB 在原厂选择器的全部 8 个可能 speed-bin 值下均选中表 3。[v143 证据](evidence/k80-gpu-v143-hfi-perf-cdc-observed-2026-11-14.json)

v144 `69b7bbda` 接受已持锁的板级启动入口，随后因表键查找返回 `kIOReturnUnsupported`。实链表以四份原厂 vendor FDT 的摘要为键。候选此前使用的是实际 Recovery 的组合 FDT 摘要。已对比当前 K80 的表 3、GMU 频率对与 DDR/CNOC 属性，确认与实链表的 Pineapple v2 原厂输入 `b082a6b8` 一致。v146 改用该原厂表的摘要。v144 在 333.64 秒回到 TWRP，七组保护样本一致。[v144 证据](evidence/k80-gpu-v144-hfi-perf-gate-cdc-observed-2026-11-14.json)

v146 `e0895483` 复用实际 CommandDB 和已核对的 Pineapple v2 输入，生成并发送 HFI typed PERF 表。收到 `m=46`，命令为 ID 15、52 个 32 位字，请求头 `0020340f` 匹配，返回值为 0。两项 CPU 帧计数均达 255，TWRP 在 332.34 秒恢复，七组保护样本一致。[v146 证据](evidence/k80-gpu-v146-hfi-perf-stock-cdc-observed-2026-11-14.json)

v147 `c02684c5` 收到 160 字 HFI 带宽表的匹配应答。CDC 为 `m=48`，请求头 `0030a003`，返回值 0。两项 CPU 帧计数均达 255。TWRP 在 332.08 秒恢复，CDC 与 UFS 正文相符，七组保护样本一致。[v147 证据](evidence/k80-gpu-v147-hfi-bw-cdc-observed-2026-11-14.json)

v148 `90780425` 依次收到 BCL、IFPC 与 `CORE_FW_START` 的匹配应答。CDC 为 `m=50,k=12040000/22040000/32030000/0060020e`。本候选未建立 GPU AOP mailbox，沿用源码的 ACD 关闭分支。TWRP 在 331.99 秒恢复，七组保护样本一致。[v148 证据](evidence/k80-gpu-v148-hfi-core-cdc-observed-2026-11-14.json)

v149 `a8847ba2` 的默认频率与带宽投票均收到结果为 0 的匹配应答。GMU AB 查询返回 1 和状态 0，CDC 为 `m=52,d=02030000/02030000/02040100/0090030c/00000001`。TWRP 在 332.09 秒恢复，七组保护样本一致。下一步接通实际 AB 投票和 USER/LPAC 页表准备。[v149 证据](evidence/k80-gpu-v149-hfi-dcvs-cdc-observed-2026-11-14.json)

v150 `de2ab470` 返回 `m=53,v=030002d8`，确认启动带宽撤票和 GMU AB 投票完成，随后 CPU 页表准备返回 `kIOReturnNotReady`。原生 SMMU 通路已有保留的上下文视图和禁用状态读回，外部可写视图标志保持未置位。v151 仅为 CPU 页表构造接受这一原生通路，仍要求同一控制器持有和 GMU 校验，并保留寄存器写入限制。v150 在 332.71 秒回到 TWRP，七组保护样本一致。[v150 证据](evidence/k80-gpu-v150-native-gpu-tables-cdc-observed-2026-11-14.json)

v151 `050c85f6` 的 USB CDC 为 `m=54,v=07000000`。同一启动周期内，启动带宽撤票、GMU AB 投票和 USER/LPAC 两套 GPU 页表的 CPU 侧构造均返回成功。TWRP 在 332.86 秒恢复，CDC 与 UFS 检查点相符，七组保护样本一致。下一步检查两套上下文映像、禁用状态和 PRR 寄存器可读性，随后接通 GBIF/QTB 隔离和原生 USER/LPAC 上下文写入。[v151 证据](evidence/k80-gpu-v151-gpu-tables-view-cdc-observed-2026-11-14.json)

v152 `8c62ce8e` 在启动后约 143 秒由摄像头拍到 CPU 锁屏。TWRP 在 334.37 秒恢复，七组保护样本一致。这一轮直接调用了固定启动脚本，USB CDC 接收器未同步启动，UFS 记录又在 SMMU 预检查之前落盘，因此本轮无法确认预检查结果。v153 已通过串口入口启动，在同一轮收集预检查结果及后续 GBIF/QTB 隔离试验结果。[v152 实拍和恢复证据](evidence/k80-gpu-v152-mmu-preflight-camera-observed-2026-11-14.json)

v153 `3d557d1f` 的 USB CDC 返回 `m=57,w=000002d6`。该阶段证明 USER/LPAC 上下文映像编码、SCTLR 禁用状态和 PRR 两字读取已通过。随后隔离试验返回 `kIOReturnTimeout`，无 GBIF ACK，未进入 QTB 操作。对照原厂 `gen7_gmu_wait_for_idle` 和 `gmu_core_timed_poll_check`，原候选错误地用反向掩码检查 GMU 空闲。v154 按源码检查 `(status & BIT(30)) == 0`，并区分空闲、client halt 写入和 arbiter halt 写入的失败边界。v153 在 332.17 秒自动返回 TWRP，七组保护样本一致。[v153 串口和恢复证据](evidence/k80-gpu-v153-mmu-fence-cdc-observed-2026-11-14.json)

v154 `9aa6e624` 修正轮询掩码后仍得到 `m=57,w=000002d6`。新增诊断表明，在 GMU 空闲轮询阶段超时，两个 GBIF halt 写入都还未发出。原厂冷启动顺序为先 `kgsl_mmu_start`，再请求 `oob_gpu` 和发送 `H2F_MSG_START`。v155 保留运行期 GBIF 检查，并在冷启动时试验 GX 关断回读、QTB halt ACK、QTB 释放和再次读取 GX 状态。v154 在 332.41 秒返回 TWRP，七组保护样本一致。[v154 串口和恢复证据](evidence/k80-gpu-v154-mmu-idle-mask-cdc-observed-2026-11-14.json)

v155 `a4adc551` 的串口为 `m=59,w=010002f0`，确认 MMU 冷启动路径读到 GX 电源和时钟关闭，随后 QTB 查找返回 `kIOReturnNotFound`。实际 FAT 中的 ADT 无 `gpu-qtb` 子节点。v157 从 Pineapple K80 源设备树补入 QTB 基址、stream 范围、端口和 TBU 带宽路由，使用 XNU 的 ADT 资源解析入口。v156 仅完成离线构建。v155 在 332.23 秒返回 TWRP，七组保护样本一致。[v155 串口和恢复证据](evidence/k80-gpu-v155-mmu-cold-qtb-cdc-observed-2026-11-14.json)

v157 `82f41b6c` 的 USB CDC 返回 `m=62,w=ff000000`。实机在 GX 关断期间收到 QTB halt ACK，启用 USER/LPAC 的故障 SPI 709/710，并核对两条新 stream 处于阻断态。随后恢复 QTB，读回 GX 仍关闭。TWRP 在 332.79 秒恢复，七组保护样本一致。v158 在相同隔离条件下验证 PRR、ACTLR 和两个上下文编程，保留两条 stream 的阻断态。[v157 串口和恢复证据](evidence/k80-gpu-v157-mmu-qtb-adt-cdc-observed-2026-11-14.json)


v158 `21ac8c0b` 的 USB CDC 返回 `m=63,w=070002ca`。高字节 `0x07` 确认已在冷启动 QTB 隔离下完成前置检查、PRR 零页持有，以及 PRR 两字写入和读回。随后 USER ACTLR/TLB 步骤返回 `kIOReturnIOError`，两套上下文未完成编程。同次启动的 CDC 与新 UFS 检查点正文相符，TWRP 在 332.50 秒返回，七组保护样本一致。该试验只启动一次，claim 已消费。恢复调试时从 v158 的归档源码派生新候选。[v158 串口、构建和恢复证据](evidence/k80-gpu-v158-mmu-context-cdc-observed-2026-11-14.json)

## v160 ACTLR 候选

v160 `71a1b89a` 从 v158 归档源码派生，复用同一个设备树解析器填充请求端点的 ACTLR 写入白名单，并保留阻断 stream 的有效 SMR 独立匹配。启动包 FAT 中的 ADT readback 确认 USER、LPAC、GMU 的 SID 0、1、5 均匹配 `0x32b`。串口 `x=` 分别记录 USER 和 LPAC，最高半字节 `1/3/7` 依次表示写入返回、读回返回、TLB 同步成功。新字段在 v158 的 505 字节样本上达到 525 字节，v160 将两端的发送容量调到 576 字节。

内核全量链接、启动包读回、固定 runner 的离线准入检查、串口解析回归和 SMMU 编程与 stream 软件测试均通过。查到设备已在专用 ADB 5039 的 TWRP，序列号 `92988a43`、机型 `zorn`、槽位 `_a`。自动审批拒绝了 v159 的启动。v160 已取代 v159，新的 claim 尚未消费。下一次启动先验证 `m=64,w=ff000000,x=7000032b/7000032b`，再进入两条 stream 的翻译启用阶段。 [离线证据](evidence/k80-gpu-v160-mmu-actlr-offline-2026-11-14.json)

### v160 实机与 v161 下一轮

v160 已单次启动。USB CDC 返回 `m=63,w=0f0002ca,x=7000032b/00000000`，与同一次启动的 UFS 正文核对通过。USER ACTLR 已写入、匹配读回 `0x32b` 并同步 TLB。接着 USER 上下文编程返回 `kIOReturnIOError`，尚未执行 LPAC ACTLR，两条 stream 仍在阻断阶段。相机拍到 CPU 锁屏。

已自动回到 TWRP，七组保护样本全部匹配。主机 482.64 秒时完成 Recovery 身份确认，其中包含临时 ADB 服务抢占接口造成的延迟。已停止本次排查启动的两个临时 ADB 服务，后续仅用固定 runner 的 5039 服务。

v161 `0b70e807` 已离线全量链接、打包、读回校验。串口新增 `y=`，记录页表审计或稀疏上下文编程状态、阶段、写入计数以及回读字段差异。K80 GMU v113 已观察到 TCR2/SCTLR 单向差异，可以和本轮 USER/LPAC 实读核对。v161 保留现有上下文验收条件，等具体回读再判断如何修复。 [证据](evidence/k80-gpu-v160-mmu-actlr-cdc-observed-2026-11-14.json)

### v161 已定位 USER 上下文的回读比较

v161 `0b70e807` 返回 `m=63,w=0f0002ca,x=7000032b/00000000,y=405cd648/00000000`。USER 稀疏编程状态为成功、phase 5，readback_valid 和 enabled 均置位。差异掩码仅为 TCR2 和 SCTLR，底层共用校验器已限定为 TCR2 bits 5/6 的单向置位与 SCTLR bit 12 的单向清位。故障来自板级随后重复的逐位比较。334.20 秒自动返回 TWRP，七组保护样本和 CDC/UFS 正文匹配。

v162 在 programContext/verifyContext 的板级重复比较中使用同样的单向归一化，其余上下文字段完整比较。逐位 host 测试通过，包括反向变化和 TTBR 差异拒绝。用户已明确回复“授权每次”，后续同范围新 scope 单次试验沿用此授权。 [v161 实机证据](evidence/k80-gpu-v161-mmu-context-cdc-observed-2026-11-14.json)

### v162 USER/LPAC 上下文编程通过

v162 `ef9cc3c3` 串口返回 `m=64,w=ff000000,x=7000032b/7000032b,y=405cd648/405cd648`。两套上下文的底层编程、回读、TLB 同步与受限原生回读比较均通过，QTB 已释放，GX 仍关闭。332.77 秒自动回到 TWRP，七组保护样本及 CDC/UFS 正文匹配。此轮保留 stream 阻断状态。

v163 `7e79a119` 复用现有 activatePreparedWithPeer，初始上下文通过后激活两条原生 stream，并分别回读两个上下文、stream、故障状态及 GX 关断状态。新增 `z=` 的 bits 0/1 表示各 stream 激活返回成功，bits 2/3 表示激活后的分别复核通过。源码写入许可只覆盖已记录的实际所属 slot 与准确 SMR/S2CR 值。 [v162 实机证据](evidence/k80-gpu-v162-mmu-context-cdc-observed-2026-11-14.json)

### v163/v164 stream 写入失败与 v165 修复

v163 `7e79a119` 为 `w=7f0002ca,z=00000000`。v164 `fbdecd67` 进一步返回 `u=0a0002ca/02000000`，两套上下文激活前校验通过，USER 在 S2CR 写入阶段失败。两轮分别在 332.66、332.74 秒自动回 TWRP，七组保护样本及 CDC/UFS 正文全部匹配。

源码定位到本次新增的原子回调内 nativeControllerClaimHeld 检查。底层 AtomicSmmuIo 在 MMIO 访问时屏蔽本地 IRQ，而 RuntimePm 的 providerClaimUsable 明确要求 IRQ 开启。v165 `ba5d0584` 将完整 owner 检查移到持有 domain gate、即将进入写入窗口的位置，原子回调继续核对同一线程、实际所属 slot、准确 SMR/S2CR 值、QTB held 及故障位。host 回归测试复现旧拒绝并验证新路径与负例。 [v163](evidence/k80-gpu-v163-mmu-context-cdc-observed-2026-11-14.json) · [v164](evidence/k80-gpu-v164-mmu-context-cdc-observed-2026-11-14.json)

### v165 USER/LPAC stream 翻译已激活并回读

v165 `ba5d0584` 单次实机返回 `m=64,w=ff000000,x=7000032b/7000032b,y=405cd648/405cd648,z=0000000f,u=0f000000/0f000000`。USER 与 LPAC 的 ACTLR、页表上下文、TLB 同步、SMR/S2CR 激活以及两条 stream 激活后的上下文/故障复核全部通过。随后释放 QTB 并再次读到 GX 关断。332.40 秒自动返回 TWRP，七组保护样本及同次启动 CDC/UFS 正文均匹配。

后续从 v165 归档源码派生。下一步按 K80 gen7_gpu_boot 顺序接通 GPU OOB、HFI START、CP ring 和 ZAP，再验证有界 GPU 作业、真实 fence 与 CPU 可见结果。当前三队列 direct_hfi 已有真实应答，后续启动入口需要复用该 owner。现有普通 host_hfi 启动路径及其 callable 前置条件不能直接代表三队列入口已接通。

源码仅据公开原厂驱动、设备树及实机日志修改。v165 的原子 guard 回归、v162 单向位比较回归及 ACTLR 解析回归均通过。本阶段 GPU 作业、真实 fence、已知图像、Metal 与 GPU 显示呈现仍待实机验收。 [v165 实机证据](evidence/k80-gpu-v165-mmu-context-cdc-observed-2026-11-14.json)

### v166 GPU OOB 实机通过

v166 `306a42a0` 在两条 USER/LPAC stream 激活后执行原厂 OOB 请求：HOST2GMU_INTR_SET 写 bit30，GMU2HOST_INTR_INFO 轮询 bit31，清 ACK 后检查 GX 状态。串口为 `m=66,o=0000003f/00000000/00000000/00000000/00000000`，确认请求、ACK、清除及 GX 上电均通过。轮询采用原厂 100 毫秒上限。332.73 秒自动回到 TWRP，七组保护样本以及同轮 CDC/UFS 正文匹配。 [v166 证据](evidence/k80-gpu-v166-mmu-context-cdc-observed-2026-11-14.json)

v167 `5d059193` 复用三队列 direct_hfi 的 exchange，以 ID10 发送无载荷 HFI START。收到应答后检查实际三字 ACK、请求头 ID/字数、固件零状态和 IRQ/HFI 健康状态。OOB 与 START 分开记录。

### v167 三队列 HFI START 实机通过

v167 `5d059193` 串口为 `m=68,t=00000002/00000003/00a1030a/00b0010a/00000000`。同一 direct_hfi owner 发出的 ID10 一字请求收到匹配三字 ACK，固件状态为零。OOB 阶段仍全部通过。332.43 秒自动回到 TWRP，七组保护样本及同轮 CDC/UFS 正文匹配。精确内核与镜像 SHA256 见本轮证据引用的 full-link/link-result.json 和 boot-package/verified.json。

下一步从 v167 归档源码派生，接通 GX/CP 初始化。现有 HostRing 的 Storage/构造入口仍硬绑定 HwschedHfi26，实际三队列 DirectHfi26 已验证到 START，需要复用 ring/内存/提交实现并接入当前 transport 的健康状态和 OOB 生命周期。不得把类型替换当作其生命周期已经接通。CP ring、ZAP、真实 GPU 作业/fence、已知图像与 Metal/呈现仍待实机验收。 [v167 实机证据](evidence/k80-gpu-v167-mmu-context-cdc-observed-2026-11-14.json)

### v168 固件代码绑定入口与 v169

v168 `72ba19b7` 已增加 DirectHfi26 重载，两个入口保留原 HwschedHfi26 调用方式并共用原固件校验和 hcb_run 后端。现有绑定源码已与 v167 实链对象对应源码逐字核对，并用实际 native-smmu-full-authorized 配方复现原对象哈希。27 个原有 SQE/AQE 固定基址绑定回归通过。

v168 实机 `m=69,n=00000000/00000000/00000000/00000000`，在绑定工厂前拒绝，未写 SQE/AQE 基址。334.20 秒自动回到 TWRP，七组保护样本及同轮 CDC/UFS 匹配。源码中的新增 direct 判断错误地要求父对象私有 gate 已持有，而当前持有板级 startup gate。v169 `96c244be` 在父对象 gate 内核对实际固件/页表准备状态，随后继续由板级入口核对真实 direct_hfi、MMU/OOB 与 provider。另把绑定函数的返回值记入串口，覆盖工厂前拒绝。 [v168 证据](evidence/k80-gpu-v168-mmu-context-cdc-observed-2026-11-14.json)

### v169 SQE/AQE 固件基址绑定实机通过

v169 `96c244be` 串口为 `m=70,n=00000000/03d02020/00000000/0000000f`，原 hcb_run 后端的四个准确基址写入及读回全部匹配，SQE_CNTL 仍为零。332.41 秒自动回到 TWRP，七组保护样本及 CDC/UFS 正文匹配。原对象已由准确 native-smmu-full-authorized 编译配方复现；复用源码相同。新增 DirectHfi26 入口保留 HwschedHfi26 的原调用方式并共用同一校验、寄存器与资源保留逻辑。

下一步从 v169 归档源码派生，适配 HostGpuRegisters 的三队列入口，接通原 GpuGen7Config 初始化与实际板级授权，然后启用 GPU IRQ、接通 CP ring 和 ZAP。HostRing 的 HFI 生命周期接口仍待接入。当前完成的是固件代码基址绑定，真实 CP 作业、fence、GPU 渲染和 Metal 仍待验收。 [v169 实机证据](evidence/k80-gpu-v169-mmu-context-cdc-observed-2026-11-14.json)

### v170 GX 初始化实机通过

v170 `c274db2a` 给 HostGpuRegisters 增加 DirectHfi26 入口，复用同一配置算法，原 HwschedHfi26 调用入口保留。板级 callback 核对实际 GPU/GMU provider/resource 对、同一代码描述符、SCACHE bypass 读回、已实测的 MMU/OOB/HFI 状态，并持有原有板级 gate 和资源。原有 775 个失败/副作用回归用例通过，实际原对象由准确配方复现。

实机为 `m=72,r=00000000/00000066/03d0f008/00000000/00000000/00000001`，确认102项配置完成、75对powerup值写入记录、记录发布及SCACHE结束检查。332.09秒自动回到TWRP，七组保护样本和同轮CDC/UFS正文匹配。

从 v170 归档源码派生下一候选，接通GPU IRQ，随后适配HostRing的三队列transport与OOB生命周期，推进CP_INIT、ZAP、真实ring推进和fence。对应官网GPU教程第3步，正在推进其第3小项。 [v170实机证据](evidence/k80-gpu-v170-mmu-context-cdc-observed-2026-11-14.json)

### v171/v172 GPU IRQ 注册边界

v171 `2af3feec` 已接通 DirectHfi26 的 GPU IRQ 准备入口，实机到达 `m=73,i=e00002be/00000000/00000000/00000000`。该错误是 `kIOReturnNoResources`，不是此前口头误判的 `kIOReturnUnsupported`。事件源工厂返回空会统一产生这一错误，因此不能据此断定内存不足。332.27 秒自动回到 TWRP，七组保护样本及 CDC/UFS 正文匹配。

v172 `e996597b` 新增运行时设备树和工厂边界诊断，返回 `m=73,i=e00002be/00000006/000c000d/0000012c`。实际 `interrupts` 为12字节，名称为13字节，SPI编号300（INTID332），属性/名称/tuple检查及provider创建均通过，随后事件源工厂返回空。332.86秒自动回到TWRP，七组保护样本和CDC/UFS正文匹配。v173进一步记录实际GIC attach返回与寄存器回读；尚不启用GPU IRQ或执行CP作业。

[v171证据](evidence/k80-gpu-v171-mmu-context-cdc-observed-2026-11-14.json) · [v172证据](evidence/k80-gpu-v172-mmu-context-cdc-observed-2026-11-14.json)

### v173 定位 GIC 路由读回不匹配；v174 候选

v173 `7c0dca0e` 返回 `m=73,i=e00002be/00000011/00000005/003f0000`。事件源创建确实进入原生注册，底层返回 `KERN_FAILURE`（5），GIC回读掩码为0x3f，触发类型为level、enable为0，但请求路由与实际路由不等。332.65秒自动回到TWRP，七组保护样本和CDC/UFS匹配。这一结果排除仅凭外层NoResources判定分配失败的推测。

v174 `68b4258a` 为准确GPU INTID332新增bootCPU注册入口，复用已实测GMU/SMMU的真实拓扑和redistributor检查，以及原masked attach/readback；只做一次attach，无回退或重试。源码提取的12项host检查及全量链接通过。实机验收以该候选新scope串口及恢复结果为准，不能提前认定GPU中断已接通。 [v173证据](evidence/k80-gpu-v173-mmu-context-cdc-observed-2026-11-14.json)

### v174 GPU IRQ 屏蔽注册与 workloop 挂接实机通过

v174 `68b4258a` 串口为 `m=74,i=00000000/00000007/00000000/00000000`。实际bootCPU路由通过原有GIC寄存器读回检查，GPU事件源创建、初始屏蔽状态与workloop挂接均通过。该阶段保持GPU中断禁用，尚未绑定ring接收者、开启GPU IRQ或执行CP命令。332.79秒自动回TWRP，七组保护样本和同轮CDC/UFS正文匹配。12项源码提取host回归和全量链接通过。

根因是v173实际GIC请求路由与回读不等；修复采用已经实测的GMU/SMMU策略，以内核真实拓扑boot_cpu及其redistributor为依据，在首次且唯一一次GPU INTID332注册前选定路由，保留全部回读条件。未放宽成功判定，也未在失败后重试。

后续HostRing以当前真正实链的 `gpu-kernel-client-owner-candidate/ZornGen7HostRing26.cpp` 为起点，对应 `k80-kernel-client-owner26/ZornGen7HostRing26.cpo-command.json`。已从源码复现其对象SHA256 `5c746468e6be95169e8e0ee6daa973fda5866bbf4f4e413a904ed48da3353aec`，与当前镜像输入逐字节相同；旧native-smmu-full-authorized目录的HostRing对象不等，不可作为当前实链输入的替代。下一步适配HostRing真实三队列transport/OOB生命周期与板级CP授权，验证CP_INIT及ring推进，再接ZAP、真实fence、已知图像和Metal。本目标仍未完成。

[v174实机证据](evidence/k80-gpu-v174-mmu-context-cdc-observed-2026-11-14.json)

### v175 CP_INIT、ring 推进与初始空闲实机通过

v175 `eb07e69b` 为当前实际HostRing后端增加DirectHfi26初始化入口，保留原HWSCHED接口。该入口保留并检查真实transport、pool/code描述符和GPU/GMU资源对，复用原ring发布、IRQ绑定/启用、1秒有界等待与失败保留逻辑。修正板级startup递归锁层数，使CP/IRQ访问和等待期间无startup锁。后续DirectHfi的OOB释放及客户端runtime仍待接通，不能把此CP入口当作完整生命周期。

实机串口 `m=76,cp=00000000/00000303/00000007/00000001/0000000a/0000000a/00000000/03d8ec30`，确认CP授权与ring发布均返回、7项ring配置完成、SQE启用、RPTR/WPTR均为10，最后GMU busy读回及原空闲判定通过。GPU IRQ已由真实ring接收者绑定并启用；本轮未单独证明IRQ送达。该结果证明初始CP_INIT被GPU执行并推进ring，不是正常任务fence、ZAP认证、已知图像或Metal成功。

332.17秒自动返回TWRP，同轮CDC/UFS正文匹配，七组保护样本一致。通用runner保留的旧 `GPU_started=false` 字段不识别新增CP阶段；本阶段以新CP专用观测和同轮UFS校验为准，原始runner记录不改写。全量链接1398输入/29替换/零未定义；118项ring状态机与5项串口解析host检查通过。历史测试把IRQ bit0作为fatal注入，与当前native通知位策略不符；归档测试副本改用bit2注入，未放宽原失败预期。

下一步核对ZAP完整CPU父页保留范围、ALL-CPU别名排除和SCM实际独占条件，接通真实板级owner，再验证ZAP认证、安全模式切换、原生ring接管及真实fence。已确认加载器绑定的是K80签名资产与0x9b09a000/0x2000保留区，不能只凭no-map标量认定完整窗口已持有。没有执行新ZAP试验。

[v175实机、输入和host检查证据](evidence/k80-gpu-v175-mmu-context-cdc-observed-2026-11-14.json)

### v176 ZAP 完整 CPU 父页租约通过，认证前返回 NotReady

v176 `3bbed4f7` 接入实际K80 ZAP owner。候选在现有IOMemoryDescriptor全局映射锁下记录物理映射尝试，独占完整16KiB父页0x9b098000..0x9b09c000；先前外来映射使claim拒绝，claim后外来物理映射拒绝。原始io_map/high-window路径对该准确父页范围拒绝并记录冲突；其余范围沿用原路径。managed直接映射排除与实际固定descriptor检查独立执行，复制结束后封存禁止新映射。三个原始kernel对象已由准确编译配方逐字节复现，新代码只在独立候选中。

实机 `m=77,zp=e00002d8/00000007/00000000/00000000/00000000/00000000/00000000/00000000/c0000000/00000008/00000000/00000002/00000005/00000004`。实际XNU物理窗口为0x8c0000000起、0x200000000字节，与完整父页不重叠。owner/lease获取和受控映射均通过，无先前外来映射/原始I/O映射冲突；CP初始ring仍RPTR/WPTR10。随后认证阶段返回kIOReturnNotReady，hzl结果尚未开始，未复制镜像、未执行PAS AUTH。此结果不能区分SCM入口拒绝与loadWithHeldScm内先行PAS能力查询失败；v177同时记录两者的真实条件和64位返回。

332.88秒自动回TWRP，七组保护样本匹配，CDC身份与同轮UFS检查点核对通过。42项实际租约helper检查（含并发），19478项K80实际asset loader策略检查，以及11项解析检查通过。历史houji测试的metadata CRC按独立核对的K80原厂元数据更新为c4ca6dbe；原策略预期未放宽。全量1398输入/33替换链接零未定义。ZAP认证、模式切换、真实任务fence、已知图像与Metal仍待实机验收。

[v176实机及完整输入](evidence/k80-gpu-v176-mmu-context-cdc-observed-2026-11-14.json)

### v177 定位 PAS 查询回调误用 loader 阶段；v178 修复

v177 `4c4ae30e` 返回 `m=77,sc=00000006/00000047/00100200/00000fe3/00010105/00000001/00000000/00010306/42000601/00000000/00000001/00000000`。SCM入口完整通过，normal上下文、会话、原CX结果及Arm64 convention资格均有效；DAIF仅D位0x200置位。失败位于第一次PAS能力查询：hpp已开始、phase1，但回调返回1，输入帧x0=0x42000601/x1=1未被Native SMC改写。

源码根因是ZAP call/delay共用hzl的load.phase，而hpp查询发生在hzl_run之前，此时load.phase为0。板级授权正确拒绝阶段0。v178 `ddefe3bd` 在load尚未started时选用实际QUALIFY阶段1，真正load开始后继续使用其实际phase，保持阶段0、失效窗口及其余拒绝条件。原/新实际callback函数的48项ASan/UBSan回归复现旧拒绝并验证修复；全量链接和打包通过。

v177在332.31秒自动回TWRP，七组保护样本匹配，CDC身份与UFS检查点核对通过。新增诊断本身经22项原/新SCM入口控制流、锁和隔离状态对照验证，4项解析检查通过。v178硬件结果另行记录，尚不能认定ZAP认证通过。

[v177实机与源码证据](evidence/k80-gpu-v177-mmu-context-cdc-observed-2026-11-14.json)

### v178 K80 ZAP 认证实机通过

v178 `ddefe3bd` 修复查询阶段后，实机为 `m=78,zp=00000000/00000008/00000000/00000000/00000000/00000008/00000000/00000000/c0000000/00000008/00000000/00000002/0000000d/0000003f`。K80原厂签名资产的PAS能力查询通过，metadata发布、INIT/MEM_SETUP、实际镜像复制及AUTH按原loader顺序完成；AUTH响应x0/x1均为0。复制已结束，CPU完整父页窗口已封存，authenticated/CPU-ended/map/attempt/valid/response六项标志均置位。SCM上下文为`6/47/00100200/fe3/00030600/000f1f1f/1/0/0/0/0/0`。hpp完成后phase为6，末查询单项字段在此不再采集，available/valid/attempted掩码与supported均有真实记录。

CP初始RPTR/WPTR仍为10。此轮仅完成认证，未执行CP_SET_SECURE_MODE、首次上下文prefix、原生ring接管、真实任务fence、已知图像或Metal。通用runner的旧GPU_started=false字段不识别新增CP/ZAP观察器，不能用它否认或扩大专用观测范围；原始记录保持不改写。

332.89秒自动回到TWRP，七组保护样本匹配；CDC身份与同轮UFS检查点核对通过。1117字节串口帧完整接收并通过解析。48项实际call/delay新旧回归通过，复现原查询拒绝并保持非法阶段/失效窗口拒绝。全量1398输入、34替换、零未定义链接，解析逻辑除scope模块外与v177一致。

后续从v178归档源码派生新scope，不复用已消费claim或Recovery前的RAM状态。下一步接通HostRing认证后流程的真实DirectHfi OOB生命周期：当前completeAuthenticatedBootstrap仍有针对缺少旧hfi指针的阶段门槛；保留HWSCHED旧入口，复用固定模式切换、首上下文、两次writeback与NativeRing timestamp fence后端。DirectHfi当前只持有实际三队列transport，没有OOB释放/运行期引用计数接口，不能以恒定回调或类型转换替代。还须核对authorizeOwnedPostCpUserRestore及SmmuDomain post-CP路径对原legacy owner/maps/lease字段的依赖，接入已验证的native所有者与逐位/受限归一化规则；不能放宽到未知TCR/SCTLR状态。

[v178认证、恢复与构建证据](evidence/k80-gpu-v178-mmu-context-cdc-observed-2026-11-14.json)

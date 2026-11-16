# K80 iOS 26 CPU 锁屏与 GPU 驱动交接

更新时间：2026-11-13

设备：Redmi K80 `92988a43`，UniXNU `zorn`，slot `a`

目标：CPU 显示路径进入 iOS 26.6.2 锁屏后，优先推进 K80 Adreno 750v2 / Gen7.9.1 GPU 驱动、固件与 direct-ring；FT3683 触控开发暂停。

## 现在的状态

- 2026-11-13：CPU 显示路径已经进入 iOS 系统锁屏。保存记录的 scope 是 `single-K80-ios26-CPU-keystore-retag-300s-b0da41e9`，运行 ID `b0da41e98417481f979a24106c21f3bc`。一次启动，332.5 秒回到 TWRP。机主在这次启动的显示期间目视确认画面是 iOS 锁屏。诊断页显示 BackBoard 完成 69 次换帧和像素拷贝，两次检查点之间又继续做了 66 次。SpringBoard PID 5 不再停在 `com.apple.sessionservices`。运行器的 `lockscreen_proven` 仍是 false，因为这类诊断页不设置它；这次也没有保存相机照片。
- 同一套 `MiniAppleKeyStore` 代码的前一次启动 `b6440b7e` 也被机主看到锁屏，但运行器在读回诊断页之前被停下，记录没有保存。用相同内核再开一个 scope 时，运行器在任何启动命令之前拒绝，原因是磁盘上的诊断页标记已经是这个运行 ID。`b0da41e9` 只更换了记录标记。
- GPU 分支此前做过 K80 真机阶段试跑，但当时没有进入 iOS 系统锁屏，因此切换到 CPU 渲染。最新硬件证据是 v60 只读 SMMU bank/stream census；GMU 固件/HFI、GPU 作业/fence、Metal 与 GPU 呈现仍未实测通过。
- v81 是把 CPU 锁屏路径和可选 GPU/GMU provider claim 合在一起的独立离线候选。它保留 `zorn26_cpu_presenter=1`、原根区/ADT/FD，仅替换 GPU 候选内核和启动菜单；内核 SHA-256 `5b803527c084ba30989ee010141e127bd45328b6029592f0f0819172a2db6a6f`，启动镜像 SHA-256 `d1df60c65701d5054868d7eb37d6502cfc0391fdc882a061c33ce66eba464eca`。v81 已完成离线完整链接与封装，尚未上机、未选择。它不启动 GMU 固件/HFI 或 GPU 作业，也不证明 DMA 静止或全主设备排他。
- v81 离线完整链接输入 1,397（filelist 1,318、direct 79），缺失输入 0、未解析符号 0；十条链接诊断与 v80 完全相同。owner-confirmed CPU 锁屏内核 `9f6474ce789a8ac860417e3e7526ca5e241366c4dd7bd3c8b1731712c409a091` 及原 CPU 启动包均未改动。
- v73 Recovery 停止门仍活动：旧 scope 的首个根页 pin 来自较早页面，实际读到 `be93aab9…c700` 与两次后续 CPU 前后读回一致，但这只是历史 pin 来源对账，不代表设备当前状态。v81 还没有新 scope、ready/admission 或 one-shot claim；下一次真机操作前必须先生成新的固定 runner，并在 Recovery 全量复核 GPT、根区/Data/fence 与整页 BCB 后再决定是否单次启动。
- GPU、Metal 和 FT3683 仍未完成验收。直接完成环启动镜像 `c65446594ad15ef3640df300132a53589adee70059caefe4fb3b5dd196ed4182` 仍未准入：它的启动路径还没有证明 GPU 提交和 DMA 保持空闲。
- 2026-11-13 v59 SMMU global-fault/control 硬件阶段：设备一次启动后在 122.845 秒回到 TWRP；新 SMMU 记录显示 controller active、GFSR=0、global TLB sync 一次状态读取即完成、CR0 读回一致、全局 INTID 705 arm 返回 0，context fault bits 保持不变。启动前 CR0 已是 `0x2f0406`，GFRE/GFIE 的 `0x06` 原先就在位，所以这轮没有证明从关闭态启用；也没有 fault、IRQ 投递、context/bank/stream 所有权、SMMU 映射/翻译、GMU 固件启动、GPU 执行或 Metal。Data、root 首页和两侧 fence 捕获一致，BCB 整页读回且尾部保留；native log-writer readback 标志仍为 false。见 [v59 实测记录](evidence/k80-native-SMMU-global-fault-control-observed-2026-11-13.json)。
- v59 SMMU global-fault/control 阶段一次启动后在 122.845 秒回到 TWRP；上述状态显示全局控制读回一致，但没有证明关闭态使能、fault、IRQ 投递、SMMU 映射/翻译、GMU 固件启动、GPU 执行或 Metal。见 [v59 实测记录](evidence/k80-native-SMMU-global-fault-control-observed-2026-11-13.json)。
- 随后的只读 SMMU census `single-K80-ios26-native-SMMU-readonly-bank-stream-census90s-v60` 一次启动后在 122.814 秒回到 TWRP，117 次读取及 CRC 均有效。CR0=`0x2f0406`、GFSR=0、sTLBGSTATUS=0；22 个 bank 的 CBAR/CBA2R 均为0，SCTLR.M 位均未置位；24 个 SMR valid 位均为0，S2CR 原始值均为 `0x20000`。这是历史空闲表快照，不等于保留了 bank/ASID/stream 租约。该阶段没有写 bank、stream、translation 或 global fault-control 寄存器；上一阶段已有的 non-secure sACR probe 写/readback 仍在前缀中。Data、root 首页和两侧 fence 捕获一致，BCB 整页读回并保留尾部；新日志由主机读回并通过解析，但 native log-writer readback 标志仍为 false。没有 IRQ 投递、映射、GMU/GPU 执行、Metal 或触摸启动。见 [v60 census 实测记录](evidence/k80-native-SMMU-readonly-bank-stream-census-observed-2026-11-13.json)。
- v61 在独立本地源码树中加入 native context-bank allocator 候选：只收三个已解析端点，在保留的 SMMU 控制器 claim 下读全局状态、24 组 SMR/S2CR 与候选 bank 的 CBAR/CBA2R/SCTLR.M，通过后仅记软件 `reserved[]`。外部 bank authority 路径未改，stream-master quiescence 与 mapping authority 仍独立要求。一个 TU 编译成功，完整1396输入链接仅替换 SMMU 域对象，未解析符号0，链接警告与 v60 相同。v61 没有打包、启动或访问设备，不构成运行时 bank 租约或 GPU 执行证据。见 [v61 离线候选记录](evidence/k80-native-SMMU-bank-lease-candidate-2026-11-13.json)。
- v62 将 v61 bank allocator 与双 GPU stream 的 peer-aware 激活修复合并：第二条 stream 激活时，精确复核已经准备或已激活的 peer 表项，避免把首条 stream 合法变化误判为漂移。Domain 与 Stream 两个 TU 分别编译成功（3/0 条既有/新增警告），1396 输入完整链接替换两个对象，未解析符号0，10条链接警告与 v61 一致；内核 SHA-256 为 `ef1ddd65877c285d207aad27c3069369a4844bc6f511e5ef38ee00a40fcfa984`。候选未打包、未启动、未访问设备。peer 状态校验没有提供真实 stream-master quiescence；外部 `acquireActualStream` 权限和 actual GPU startup owner 仍未接通。见 [v62 离线候选记录](evidence/k80-native-SMMU-peer-stream-activation-candidate-2026-11-13.json)。
- v63 在更新的 QTB power/resume 完整候选上重放 v61 bank allocator 和 v62 peer-aware stream 激活：实际 QTB/TBU 电源与恢复、native SMMU bank 检查、双 GPU stream peer 校验现已处于同一个完整链接候选。Domain/Stream 编译成功（3/0 条警告）；完整1397输入链接替换2个对象、未解析符号0，10条链接警告与 QTB 基线逐字节相同。内核 SHA-256 为 `f7e238f1c9c6fb7889ad7bd1e06673f1b3d05484d6efa0b1282e3886bfc7d640`。候选仍未打包、未启动、未访问设备。真实 GPU/GMU producer quiescence、独立 SMMU mapping authority、actual startup owner 与 direct-ring 调用仍缺失；QTB ACK 与 peer 校验不能替代这些权限。见 [v63 离线候选记录](evidence/k80-native-SMMU-QTB-bank-peer-candidate-2026-11-13.json)。
- v64 在同一候选里把真实 ICC/TBU 电源对象传给 SMMU 启动路径，并将“全 GPU producer 停机授权”和 QTB TBU `FENCEACK` 分成两个必需条件：外部停机授权成功、PRR 未变后，按 K80 DT 核对 `gpu-qtb` 资源 `0x3de8000`、stream 范围和双端口；QTB halt 保持到两路 context/stream 都编程、回读并复核完成，再恢复 QTB 并降 TBU 电源。BoardOwner、QTB fence、SMMU Domain 三个 TU 新编译为 0/0/3 条警告，Stream 对象复用；完整1397输入链接替换3个 filelist 对象和1个直接 BoardOwner 对象，未解析符号0，10条链接警告与基线逐字节相同。内核 SHA-256 为 `56f47655483b7e228ee7427117f694318aa72cde0d1e74eca6d20026eb2cdaeb`。v64 未打包、未启动、未访问设备、未选入运行时。候选内部调用可从 StartupOwner 走到 SMMU Domain，但维护源码中仍没有真实 OS/板级调用方构造 `ZornGen7StartupGpuInputs26`；全 GPU 停机回调也没有具体 provider，独立 mapping/page-table ownership 仍缺。见 [v64 离线候选记录](evidence/k80-native-SMMU-QTB-stream-gate-candidate-2026-11-13.json)。
- v65 把 QTB/RSC 启动与板级资源路径合入同一候选，44 个 C++ 单元编译成功，1,397 输入完整链接、未解析符号为 0，内核 SHA-256 为 `0f19ae8ec9cd402f1fb73d6234266ca781d4c84ec4649531f69e31a54eaf6c8f`。候选离线、未选择、未打包、未启动。
- v66 在 `acquireExclusiveGpuMmuStart` 返回成功后增加 Gen7 GMU idle 轮询、GBIF client halt/ACK、arb halt/ACK；双 context/peer stream 配置与 QTB 收尾期间保持 halt，成功末尾复查 idle 后清 halt 并验证 ACK 清零。失败保留 halt 和资源；释放不确定时尝试恢复 arb halt。此流程使用固定 SM8650 Gen7 源码寄存器语义，但仍要求现有真实访问守卫。两个修改单元编译成功，警告与 v65 原有警告相同；1,397 输入完整链接、未解析符号为 0，内核 SHA-256 为 `10ea8283561553eb6a5d77adb98dbe04ddfb7b17aa207e0066bdfdaa8da471fd`。见 [v66 候选记录](evidence/k80-gpu-v66-gmu-idle-gbif-halt-2026-11-13.json)。
- GPU 硬件最新证据仍是 v60 只读 census；v65/v66 都只是离线候选。SMMU bank/stream、GMU/HFI、GPU、Metal 均未通过硬件验收。v66 仍缺真实 GPU/GMU 所有权 provider、OS/板级启动调用方和独立 mapping/page-table owner；这些接通前不产生启动包。HWSCHED 保持不变，FT3683 触控暂停。
- 机主在本次交接中明确授权对本机 K80 iOS 26 分区进行操作。后续每次硬件试验仍沿用固定运行器、新 scope/ready/claim、完整 BCB 页读回、独立看门狗及有界 Recovery 返回；范围外存储不纳入本次授权。
- 不要复用 `b6440b7e`、`b0da41e9`，以及下文已经消耗的 scope。更早的 `998f15fd` 预算观察仍是历史记录：当时 SpringBoard 还在等 `lsd`，没有锁屏。

## 上一轮为什么回到 TWRP

上一轮新增的 `lsd` VFS 观察器调用 ARM64 `copyinstr` 时，把必需的长度输出参数传成了空指针。所选内核的 [copyinstr 实现](</Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/kernel/zorn26-platform-build-candidate/osfmk/arm64/copyio.c#L557>) 在入口处无条件写这个指针。维护的主机回归以 UBSan 重现并拒绝了空指针调用。

修复版在 [ZornLSDVfsAdapter26.inc](</Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/cpu-lsd-vfs-ed2b48d33f94481d95966074a9713cb8/ZornLSDVfsAdapter26.inc>) 提供有效的 `size_t copied` 输出变量。候选回归通过：并发采集、边界路径分类和位图检查、339 个合法格式用例、10 个畸形记录拒绝；诊断页 4096 字节，历史区 1920 字节，工作线程栈帧 6176 字节。回归细节见 [离线验证结果](</Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-cpu-lsd-vfs26-ed2b48d33f94481d95966074a9713cb8/offline-lsd-vfs-verification.json>)。

完整链接输入 1397 个，替换 6 个、保留 1391 个，未解析符号 0，原有链接诊断不变。内核 SHA-256：`d66f61b46b2cc25b21a1d33e022dc1b1f1dad2879297c2a34a19c0dafa9af37e`。启动包 SHA-256：`8cce968485462fd2a30e9b3c3d8d8e7b46c0ce23be7fb0824362003d1cdbfdc9`。FAT 中仅 `EFI/UniXNU/Payloads/kernel.macho` 改变；根区 SHA-256 仍为 `227ba639a3f765fce15b1bb6f08ccf53f36872fd0a95bba7bb778f067c34e32e`，启动参数未变。链接结果在 [link-result.json](</Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-cpu-lsd-vfs26-ed2b48d33f94481d95966074a9713cb8/full-link/link-result.json>)，包核验在 [verified.json](</Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-cpu-lsd-vfs26-ed2b48d33f94481d95966074a9713cb8/boot-package/verified.json>)。

## `lsd` 与系统服务线索

[根区与 RAMFS 审计](</Volumes/macData/projects/ios-zorn/UniXNU-zorn/docs/evidence/k80-CPU-lsd-config-audit-2026-11-12.json>)确认根区配置中 `lsd` 仍启用为 mobile job，并包含 demand Mach service。iOS 26 启动时会在 RAMFS 上新建 `/private/var` 骨架，再由运行时服务补齐状态；模板里缺少部分容器目录，单靠模板审计不能认定它们是故障原因。

生成配置未包含 demand-only 的 `mobileassetd`，Houji 配置会补上它。这个差异可供后续检查，但尚无证据证明它导致本次 SpringBoard/lsd 等待。上一次同根区 CPU 记录曾看到 SpringBoard PID 5、PosterBoard PID 72、45 秒和 150 秒各两次复制，仍没有 VSync 端口或回调。服务禁用目前没有验证结果；不要据此扩大禁用范围。

## 接手后的顺序

1. 阅读 [K80 工作约束](</Volumes/macData/projects/ios-zorn/UniXNU-zorn/AGENTS.md>)、当前 `porting.toml` 和 [这次锁屏记录](evidence/k80-CPU-keystore-retag-observed-2026-11-13.json)。不要复用 `b6440b7e` 或 `b0da41e9`。
2. CPU 锁屏已由机主目视确认，并保留为 GPU 适配参考。v81 离线包仅到 provider claim 阶段；下一步先为 v81 建立新的固定 scope/runner，并重新读取完整 Recovery 保护数据，再决定一次受限启动是否可执行。之后继续把真实 GPU/GMU/SMMU owners、完整有效 match set 的停止/恢复和 direct-ring startup 接到实际 OS/板级调用方。v60 空闲表快照不等于租约；硬件 DMA、GMU/HFI 与 GPU 执行仍未验收。HWSCHED 保持不动，FT3683 暂停。
3. 新的手机启动仍须从 TWRP 开始，使用独立归档、新 scope、ready 和 claim，保留看门狗，并在单次启动后自动回 Recovery。无法回 Recovery 时立即停止设备操作。
4. FT3683 开发和验收暂停，不新增触摸驱动改动。

## 外部资料复核（2026-11-12 22:30）

`a1c0e5b7` 记录到 SpringBoard 锁持有线程在同步等待 `lsd` 的 Mach 回复。`com.apple.lsdschemes.plist` 的首次 `ENOENT` 不能作为根区改动依据：23G90 捐赠根的 `/var/db/lsd` 本身就是空目录，这个文件由 `lsd` 在运行时生成，没有可信的静态来源，因此不加入 `/private/var` 骨架。

外部与本地资料提供了三条依据：

- [iOSPlus10 笔记](https://github.com/akshaynexus/iOSPlus10)第 2 节写明，ADT `/chosen` 缺少 `mac-address-wifi0`、`mac-address-bluetooth0`、`mac-address-ethernet0` 时，MobileGestalt 每次查询 Wi-Fi 地址都会等 IONetworkController，首次启动时 `lsd`/`installd` 会停约 15 分钟。bergamota、ios-flame、sailfish、HackiOS 都验证过这一点。当前 iOS 26 ADT 三个属性都没有。K80 iOS 17 的 `check-zorn-wifi-identity.py` 当时只补了 `wifi0`，并且没有解开 iOS 17 那次的等待。
- 同一份笔记记录：新根区没有 LaunchServices `.csstore`，第一次启动会从 `/Applications` 重建数据库。iOS 26 的 `/private/var` 每次启动都由 RAMFS 骨架重建，所以每次都是首次播种。
- K80 iOS 17（[GUI 进度](progress-2026-10-27-gui.md) 09:31 一节）同样停在 `lsd` 的 LaunchServices seeding group。当时的修复是撤销 `zorn-vmap-nosleep`，恢复可睡眠的 VM map 读写锁，锁屏在约 900 秒时出现。iOS 26 源码的 `vm_map_lock_init` 已经是原版 `lck_rw_init`，没有这个问题。DroidVM 在 SM8650 上用 CPU 渲染约一分钟进锁屏，但它有持久 Data 和 4 个 vCPU。

下一步候选按单变量排序：（1）只在 ADT `/chosen` 中加入三个开发用本地管理地址；（2）把有界观察窗口延长到 900 秒以上，并相应提高主机 Recovery 回收上限。两者都只改启动包，不改根区、Data 或分区。

### `0035ea43` 网络身份 ADT 实测

第（1）项已经实测。只在 ADT `/chosen` 中加入三个开发地址，内核仅更换记录 ID，根区、启动参数和 FD 都不变。手机 332.5 秒后自动回到 TWRP，诊断页是本轮新写入的，claim 已消耗。在 150 秒检查点，SpringBoard 主线程第一次离开 lsd 持有的锁等待，改为自己同步等待一个 Mach 回复；线程数从 5 个增加到 12 个。lsd 的文件操作量由 14048 次增至 94051 次。VSync 仍未注册，两个检查点之间没有新帧，锁屏仍未证实。详细记录见 [观察记录](evidence/k80-CPU-network-identity-observed-2026-11-12.json)。

### `6412899f` 900 秒窗口实测

第（2）项已经实测。试验时长 1080 秒，晚期检查点 900 秒，主机回收上限 1500 秒。ADT、根区和固件沿用 `0035ea43`。新增的只是：SpringBoard 主线程自己处于同步 Mach 接收时，记录它的 special reply 对端。手机 1112.7 秒后自动回到 TWRP，诊断页是本轮新写入的，claim 已消耗。

900 秒时 SpringBoard 仍是 12 个线程、主线程仍在同步 Mach 接收，对端状态是 `destination-unbound`（回复端口指向的目标端口找不到接收任务）。lsd 的文件操作量是 94049 次，和上一轮 150 秒时的 94051 次相同。两个检查点之间没有新帧，VSync 未注册。所以 150 秒时的状态一直保持到 900 秒，加长等待没有让它进入锁屏。详细记录见 [观察记录](evidence/k80-CPU-long-window-observed-2026-11-12.json)。

下一步不再加长窗口，改查这个找不到接收任务的回复目标端口。

### `fe04d302` 回复目标端口分类实测

试验时长回到 300 秒，ADT、根区和固件沿用 `6412899f`。新增的只是：对端为 `destination-unbound` 时，记录目标端口的类型和状态。手机 333.9 秒后自动回到 TWRP（165 次轮询），诊断页是本轮新写入的，运行 ID 匹配，claim 已消耗。

150 秒时 SpringBoard 仍是 12 个线程、主线程在同步 Mach 接收。目标端口类型为 `plain-port`（不是服务端口、回复端口或内核对象），状态解码为 `active-no-receiver`。lsd 文件操作量 94051 次，没有新帧。

解码有一处限制：探针先判断 `ip_active`，而本内核的 `io_state_active()` 对除 `IO_STATE_INACTIVE` 外的所有状态都为真，所以 `active-no-receiver` 同时涵盖“在某个空间但解析不到任务”、limbo 和 in-transit 三种情况。可以确定的是：端口活着、是普通端口、没有可解析的接收任务。较可能的情况是接收权还夹在一条未投递的消息里，或正处在内核搬移中，例如服务端点没有 check-in，或已交给尚未接收它的任务。详细记录见 [观察记录](evidence/k80-CPU-reply-destination-observed-2026-11-12.json)。

这项探针随后做了，结果见下一节。不要再从 `fe04d302` 重开。

### `babbbe2b` 与 `056afd15`：回复停在 launchd 的服务端口

`babbbe2b` 先按原始 `io_state` 分类，并在 in-transit 时一次锁一跳地沿 `ip_destination` 走到最终持有端口。150 秒时目标仍是普通端口、状态是 in-transit，持有者是名单外的用户进程。手机 332.2 秒回到 TWRP。

`056afd15` 只增加持有者的 `p_comm`、排队消息数，以及该端口是不是服务端口。150 秒时持有进程是 `launchd.ios`，端口是服务端口，上面排队 3 条消息。手机 332.8 秒回到 TWRP。两个检查点之间没有新帧。

`launchd.ios` 是 ramfs init 执行的 `/sbin/launchd.ios`，所以允许名单里的 `launchd` 对不上。SpringBoard 主线程同步等待的连接端口，其接收权夹在 launchd 仍持有的服务端口的未投递消息里。这表示提供该 Mach 服务的 job 没有启动，或没有 check-in。两轮都已消耗。详细记录见 [观察记录](evidence/k80-CPU-reply-holder-observed-2026-11-13.json)。

### `18a1c0e6`：服务名是 `com.apple.sessionservices`

这一轮只增加持有服务端口的 launchd 服务名和域。手机 332.5 秒回到 TWRP，诊断页是本轮新写入的，claim 已消耗。150 秒时服务名是 `com.apple.sessionservices`，域是 1，名称没有截断；持有进程仍是 `launchd.ios`，排队仍是 3 条消息。启动包 SHA-256 `2e102b2ccaf49c7d73fb3f04b2ab201ebcd7fa4f3c3b3e2f238df05549643b03`。本 scope 已消耗。

### 外部资料里的同一等待

没有找到一份现成的 iOS 26 修复。K80 iOS 17 的只读记录里，`liveactivitiesd`（SessionCore）声明 `com.apple.sessionservices`。alioth、munch、sirius 上这个进程会在 `SessionSyncEngine` 里以 SIGTRAP 反复退出。UniXNU-qemu 在 CPU 渲染下遇到 `liveactivitiesd`、chronod 和 SpringBoard 一起等待，修复方式是补回 AppleKeyStore 的状态和事件组件，而不是禁用服务。上游有 `AppleKeyStoreState` 和 `NativeKeyStoreEvents`；K80 iOS 26 用的是 `MiniAppleKeyStore.cpp`。`disable-jobs` 只适合做隔离，不是修复。资料整理见 [检索记录](evidence/k80-CPU-sessionservices-research-2026-11-13.json)。

### `b6440b7e` 与 `b0da41e9`：CPU 路径进入 iOS 锁屏

`b6440b7e` 在 CPU 显示路径上调用已链接的 `MiniAppleKeyStoreStart()`，其余诊断和根区不变。内核 SHA-256 `31c1b11daec4dbe6043492253574916b07548a6fe7f61c8474ae7d56087abd60`，启动包 SHA-256 `50a7e999e4de22196c96df6e53ab95be69fb4abfdc24b3da4831e50814662435`。机主看到 iOS 锁屏，手机自己回到 TWRP。运行器在读回诊断页之前被停下，所以这轮没有保存记录。claim 已消耗。

用同一内核再开 scope 时，运行器在发出任何启动命令之前拒绝：磁盘上的诊断页标记已经是 `b6440b7e`，`boot_attempts` 为 0。

`b0da41e9` 因此只更换记录标记。平台对象没有重编，`GenericARMPE.cpp` 和 `ZornUfsOwner26.cpp` 与 `b6440b7e` 相同。重新编译的 5 个对象只含新标记。链接输入 1397 个，替换 5 个，未解析符号 0，链接诊断不变。内核 SHA-256 `9f6474ce789a8ac860417e3e7526ca5e241366c4dd7bd3c8b1731712c409a091`，启动包 SHA-256 `9c674c2959074a25db38e44cc26674e397f4b4c56184f439bffd8df3f647801f`。根区、ADT 和启动参数未变。

这次一次启动，332.5 秒回到 TWRP，诊断页是本轮新写入的，claim 已消耗。45 秒时 SpringBoard 有 6 个线程，150 秒时有 14 个，PID 5 仍在运行。两个检查点的主线程都不是同步 Mach 接收；150 秒时没有持有中的服务名。BackBoard 完成 69 次换帧和像素拷贝，两次检查点之间又增加 66 次。机主在 `2026-11-13 00:40` 确认，这次显示期间看到的是 iOS 系统锁屏。显示窗口是 fastboot 返回的 `00:31:45` 到记录保存的 `00:37:17`。没有相机照片。运行器的 `lockscreen_proven` 保持 false。GPU 和触控没有启动。详细记录见 [观察记录](evidence/k80-CPU-keystore-retag-observed-2026-11-13.json)。

## 清理与可复查记录

按机主要求删除了 7 个已确认过期的 iOS 26 主机生成镜像，逻辑大小合计 34,998,591,488 字节。APFS 实际可用空间从 131,481,600 增至 565,248,000 字节，净增 433,766,400 字节（约 413.6 MiB）；未删除 iOS 17 基线、当前候选或手机分区数据。逐项哈希与清理理由见 [清理记录](</Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/evidence/removed-obsolete-ios26-images-20261112.json>)。清理和本轮构建后最近一次 `df` 显示卷剩余约 387 MiB，继续构建前应再检查空间。

Daybreak 的安全提示没有暴露具体触发规则；不能据此断定某条本地项目规则或某个命令是原因。它与本地设备准入/执行检查是不同层面的机制。

主要运行证据：[这次锁屏记录](evidence/k80-CPU-keystore-retag-observed-2026-11-13.json)、[服务端口检索](evidence/k80-CPU-sessionservices-research-2026-11-13.json)、[回复持有者记录](evidence/k80-CPU-reply-holder-observed-2026-11-13.json)、[上一轮硬件记录](</Volumes/macData/projects/ios-zorn/UniXNU-zorn/docs/evidence/k80-CPU-lsd-vfs-observed-2026-11-12.json>)、[项目进度索引](</Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/next-plan.json>)。

文档校验：`python3 -B UniXNU/scripts/porting-record.py check --device UniXNU-zorn` 通过，报告 `13 structured areas checked`；`git diff --check` 与新文件 whitespace 检查通过。

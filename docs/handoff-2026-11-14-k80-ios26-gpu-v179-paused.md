# K80 iOS26 GPU 续接交接：v178 已认证，v179 离线未完成

记录日期：2026-11-14，Asia/Shanghai。此文是当前续接入口；历史细节见 [原交接文档](handoff-2026-11-14-k80-ios26-gpu.md)。[暂停快照与文件摘要](evidence/k80-gpu-v179-paused-handoff-2026-11-14.json) 固定了本次交接时的源码、编译错误、测试和最后实机记录。

## 先读这一段

- **目标当前为 paused。** 用户明确暂停后，本次只生成交接文档，没有恢复目标、编译新候选或操作手机。其他 Agent 应在收到用户恢复/继续工作的明确指令后再推进调试，不把交接本身当作恢复。
- 完整目标仍是 K80 的 iOS26 GPU、Metal、显示呈现和 FT3683 触控完整验收。只有初始 CP 和 ZAP 已通过，不等于渲染完成。
- 最后成功实机版本为 **v178 `ddefe3bd539d496f936b53753487a864`**：CP_INIT、ring RPTR/WPTR10、K80 ZAP/PAS 认证通过。332.89 秒自动返回 TWRP，七组保护样本匹配。
- **v179 `38443aaea4c94d39961c1d4418aeb5f0` 尚未编译完成、全量链接、打包或启动。** 没有 v179 设备 trial/claim。当前手机状态仅以 v178 已恢复记录为依据；本次没有再次连接手机确认。
- 严格禁止反汇编和逆向。只读公开源码、设备树、固件打包来源/既有生成输入以及实机日志。不要打开历史目录中的 disassembly/反汇编产物，也不要运行生成它们的旧脚本。
- 不 commit/push、不改 `_副本`，不改旧 iPadOS17/Data/Android/历史验收基线。遵守 `/Volumes/macData/projects/ios-zorn/UniXNU-zorn/AGENTS.md`。

## 已有硬件证据

官网教程目前处于 [第3步：建立内存和命令提交路径](https://unixnu.com/zh/porting/gpu)，正在完成 CP/ring/fence 小项。第4步 Metal 尚未硬件验收。

1. GMU CM3、三队列 DirectHfi 的 QUERY/PERF/BW/CORE/DCVS/START 均有实机匹配应答。
2. USER/LPAC 页表、ACTLR0x32b、上下文、TLB、stream 激活与读回通过。保留 v162/v165 对 K80 实读 TCR2/SCTLR 的严格单向归一化规则，不扩大差异白名单。
3. GPU OOB 请求/ACK/清 ACK、GX 上电、SQE/AQE 基址读回、102项 GX 配置操作通过。
4. v174 通过 GPU INTID332 的 masked GIC 注册、事件源和 workloop 挂接。路由使用真实 topology boot_cpu；原 current CPU 路由读回不匹配。v175 绑定 ring 接收者并启用 IRQ；没有把 IRQ 通知等同于 fence，也未单独证明 IRQ 送达。
5. v175 已执行初始 CP_INIT，SQE=1、RPTR/WPTR=10、空闲检查通过。
6. v176 增加 ZAP 完整16KiB CPU父页租约，实机验证该窗口不属于 XNU 连续内存窗口、独占映射成功。v177 定位 PAS 查询误用 load.phase=0；v178 修复为 loader 启动前使用 QUALIFY，随后 PAS 能力、metadata/INIT/MEM_SETUP/copy/AUTH 全部通过，AUTH x0/x1=0，CPU复制结束、父页租约封存。

权威证据：

- [v175 CP_INIT](evidence/k80-gpu-v175-mmu-context-cdc-observed-2026-11-14.json)
- [v176 CPU窗口](evidence/k80-gpu-v176-mmu-context-cdc-observed-2026-11-14.json)
- [v177 根因诊断](evidence/k80-gpu-v177-mmu-context-cdc-observed-2026-11-14.json)
- [v178 ZAP认证](evidence/k80-gpu-v178-mmu-context-cdc-observed-2026-11-14.json)

v178 capture 为 m78，zp 的 lease/auth flags 为0x0d/0x3f；CP仍为RPTR/WPTR10。通用 runner 中继承的 `GPU_started=false` 不识别新增 CP/ZAP 专用观察器，原始记录未改写；以对应专用观察器判定其有限范围，不能由此声称正常 GPU 渲染。1117字节 CDC 帧已完整接收，身份与同轮 UFS 检查点核对通过。

尚未完成：CP_SET_SECURE_MODE、首次上下文 prefix、post-CP TCR 恢复、两次 GPU canary 写回、NativeRing timestamp fence、正常作业、已知图像、Metal/客户端/pipeline/呈现、完整退出和释放，以及 iOS26 FT3683 全部交互验收。现有锁屏/桌面证据属于 CPU 绘制。

## 当前目录与构建依据

工程根目录：`/Volumes/macData/projects/ios-zorn`。

v178 构建：
`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v178-zap-query-phase-ddefe3bd539d496f936b53753487a864`

v178 已验证源码：
`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v178-zap-query-phase-ddefe3bd539d496f936b53753487a864`

v178 最后实机原始目录：
`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-cpu-gpu-v178-zap-query-phase-ddefe3bd539d496f936b53753487a864/root-trial/trial`

v179 当前构建目录：
`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v179-first-fence-38443aaea4c94d39961c1d4418aeb5f0`

v179 当前源码目录：
`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v179-first-fence-38443aaea4c94d39961c1d4418aeb5f0`

以上绝对路径是永久续接依据，不依赖 `/tmp/zorn-v179-path`。临时 pointer 仍存在，但不应当作唯一索引。`compile-result.json` 或部分 `.cpo` 的存在不代表 v179 构建成功；完整 link-result/verified 启动包均不存在。

当前主线是 iOS26.6.2/23G90 独立构建树，arm64e 编译。root board 的旧17配置不等于本候选 OS；不要为此机械修改旧 profile 或混入17对象。

本地 houji 参考曾固定到 `98bc0960f96076de8e8d16efcfb0c0603b166b85`，实际采用文件另由每轮 recipe/source pins 固定。其他机型参数不能当 K80 参数。需要时先查本地 K80 小米内核、设备树和已有原生实现，再查官网及其他公开 UniXNU 项目。

## v179 已写入但未硬件验证的改动

`ZornGen7DirectHfi26.cpp/.h`：

- 新增真实初始 OOB owner 绑定、持有状态检查和单次释放。
- 绑定当前 board 的真实 OOB epoch、startup lock 和 owner 健康检查。
- release 在 DirectHfi command/startup 锁外取得独立授权，再检查 pending/健康状态和 ring 的真实完成条件，最后只写一次 GMU word0x1f994 bit31。
- 返回只表示 source clear store 返回，不声称 release ACK、GX-off、DMA-stop 或可释放 BO。失败保留并停止，无重试。
- 原 DirectHfi 对象已用准确 recipe 复现，与 v178 实链对象逐字节相同，见 `original-DirectHfi-proof.json`。

`ZornGen7HostRing26.cpp/.h`：

- 保留原 HWSCHED 入口，新 Direct 路径检查实际 held OOB。
- 复用已有认证后固定模式切换、25字首上下文、两次 GPU 写回与 NativeRing timestamp fence 后端。
- bootstrap 完成授权按实际 OSObject transport 身份匹配；不是提供恒定成功回调。
- 新增16字 `bf` snapshot，失败前的真实状态也保留。

`ZornGen7SmmuDomain26.cpp/.h`：

- native 冷启动确实完成上下文/stream、QTB恢复和GX-off复核后，发布真实 `host_gpu_mmu_ready` 与单独 native runtime-ready 状态；没有伪造 legacy 外部 grant。
- 新增 native post-CP authority 绑定，以及同一线程、持 domain gate 时建立的 post-CP I/O 窗口。
- post-CP 默认只读；只有真正的恢复授权返回成功后，才准许 USER 的准确 TCR 值及准确 ASID/TLB 同步写。禁止 SCTLR、TTBR、MAIR、CBAR 写及 LPAC 写。
- 同时处理 buildFirstContext/restorePostCp/verifyRuntimeContexts 的 native 观察窗口。外部恢复授权前后仍检查实际 owner、故障与上下文，待验证锁顺序和异常分支。

`ZornGen7HostGpuTables26.cpp`：首上下文及 post-CP 检查复用已在 K80 实测的 `nativeHostImage` 单向归一化；对恢复前后的两个实际快照仍保留 exact 比较。仅允许既有 TCR2 bits5/6单向置位、SCTLR bit12单向清位，以及原有首上下文 EPD1 效果；未新增任意位容忍。

`ZornGen7DarwinBoardOwner.cpp`：接通 native bootstrap/OOB epoch、真实资源与认证 owner 的授权，成功 fence 后才授权 OOB clear；适配原 native post-CP 恢复 owner/maps 与验证。保留旧 HWSCHED 分支。

`ZornGen7InactiveOwner26.cpp`：为实际 native 已完成路径接通父对象入口，板级真实状态继续独立检查。

`ZornUfsOwner26.cpp`/`ZornUsbCdc26.c`：新增 bf=16字字段；发送/格式化容量改为1280。源端成功/失败阶段为80/79，Domain final-stage 白名单已改80。

这些改动仍须完整审查、编译和回归，不能当作硬件通过结果。

## 当前编译失败的确定原因与下一步

最新 `build.log` 的实际错误：

```text
ZornGen7StartupOwner26.cpp:347:62:
no member named 'prepareRegisterOperationGuard' in 'ZornGen7InactiveOwner26'
```

v179 的 `build-cpu-touch.py` 在通用 `run()` 内为 **所有 `-c` 命令** 前置：

```text
-iquote .../gpu-direct-runtime-attach-quiescence-v83-20261113
```

这是为补齐新暂存 Domain 头的依赖而加的临时措施，但改变了无关 TU 的头选择。依赖文件已明确证明：

- v178 StartupOwner 使用 `gpu-guarded-smmu-reservation-v96-20261113/ZornGen7InactiveOwner26.h`，含所需声明。
- v179 StartupOwner 被全局 `-iquote` 改成 `gpu-direct-runtime-attach-quiescence-v83-20261113/ZornGen7InactiveOwner26.h`，缺所需声明。

**先修复 include 来源，不要删调用或改成成功返回。** 建议移除全局注入，对准确的 Domain 头及其依赖采用窄范围/VFS重定向或按 TU 指定引用；保留各 TU v178 实际 `.d` 所指的其他接口版本。不要用整个旧目录覆盖所有新接口。

Domain 头的首次暂存也曾误用 native-smmu-full-authorized 中旧版本，缺当前 runtime 方法；后来已改为 v178 Domain `.d` 指向的 attach-quiescence-v83 实际头，再追加新私有方法。见 `domain-header-provenance.json`。当前 `.h` 源码为权威，`stage-first-fence.py` 和分步转换脚本保留了初始历史选择，**不能盲目整套重跑覆盖当前修正**。

暂停时最后构建已终止为失败，没有运行中的设备 trial。未修此编译错误后的其他错误仍未知，不要把它当作唯一剩余问题。

## 回归状态

已完成并已读取结果：

- `/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v179-first-fence-38443aaea4c94d39961c1d4418aeb5f0/direct-oob-regression.json`：**52项**，实际提取 DirectHfi 新方法，ASan/UBSan，mock 仅限 native IO/owner/锁边界；覆盖一且仅一 clear、提前/失败/重试不写、锁外授权及 owner 持有。报告 source SHA 与当前 DirectHfi cpp 匹配。这不是硬件验证。
- `original-DirectHfi-proof.json`：原实际对象复现。

尚未实现/完成：

1. native post-CP 写白名单实际 helper 的正反例测试，包含原子 I/O 屏蔽 IRQ 时不能再次调用要求 IRQ 开启的强 owner 检查（v165 既有坑）；检查 USER准确TCR/ASID写允许，LPAC/SCTLR/TTBR/MAIR/CBAR及错误值拒绝。
2. 首上下文和 inspectPostCpContext 的实际源码测试：已知单向 TCR2/SCTLR变化可接受，反向或其他位拒绝；EPD1只允许已核实的原效果，实际二次快照仍 exact。
3. bootstrap/fence snapshot 与串口解析回归。
4. 完整受影响 TU 重编、零未定义链接、启动包逐项校验、固定 runner --check-only。

原有118项 ring、42项 ZAP租约、19478项 K80 ZAP loader、48项查询回调等成功证据属于对应版本，必要时按修改覆盖范围选用，不能把旧版本通过自动归给 v179，也不要无新理由反复重跑全部套件。

## v179 串口/runner 尚未更新完整

`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v179-first-fence-38443aaea4c94d39961c1d4418aeb5f0/stage-v179-first-fence-run.py` 目前仅从 v178 改了名称/nonce，**尚未加入 bf 字段或79/80解析**；尚未执行此脚本生成 trial/capture。不要直接启动。

需要同步：

- m阶段正则接受79/80。
- `zp` 成功及认证标志从 `m==78` 扩展到后续合法阶段；原 CP/IRQ/HFI 成功检查继续保留。
- 在 sc 后追加 bf 的16个32位字。成功80要求 raw=0、phase6、grant0、flags0x7f、RPTR==WPTR且大于47、writebacks2、observed0/1为c0ffee00/c0ffee01、nativeRaw0、非零nativeFence==nativeObserved、nativeWaitComplete(0)、OOB raw0、最后IO raw0。
- **不要猜 NativeRing 最终指针为51**；后端自己编码 fence，使用实际 RPTR/WPTR 与 fence结果。
- 确认实际格式化帧容纳于1280，USB多包接收及旧1117字节帧回归正确；core帧仍需核对同轮UFS身份及tag。
- bf 索引依次为：raw、phase、bootstrapGrantRaw、状态flags、RPTR、WPTR、writebacks、canary0、canary1、nativeRaw、nativeFence、nativeObserved、nativeWait、OOBraw、最后IO地址、最后IOraw。

## 续接操作顺序

用户恢复后：先读本文件、AGENTS.md、porting.toml、v178证据及当前v179源码；确认目标仍为当前范围。随后修正头依赖、完成上述回归、全量链接和打包。未启动的 v179 可以继续离线迭代，变更和输入要重新固定；如另派生候选，使用新 UUID/scope。

仅在完整候选和全部主机检查通过后，按已经审核的固定流程准备新 owner/ready/admission/一次性 claim，并从重新核验的 TWRP/OrangeFox 启动。不能复用 v178 已消费 claim 或旧手机RAM状态。所有前置硬件阶段必须在新启动周期重新成功完成。

构建脚本在当前目录内，以下是**将来恢复后的**典型命令，不是当前已成功记录：

```sh
cd /Volumes/macData/projects/ios-zorn
python3 -B /Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v179-first-fence-38443aaea4c94d39961c1d4418aeb5f0/build-cpu-touch.py > /Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v179-first-fence-38443aaea4c94d39961c1d4418aeb5f0/build.log 2>&1
python3 -B /Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v179-first-fence-38443aaea4c94d39961c1d4418aeb5f0/package-cpu-touch.py > /Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v179-first-fence-38443aaea4c94d39961c1d4418aeb5f0/package.log 2>&1
```

若已有某轮 `full-link` 或证据，不要覆盖已启动的冻结产物。当前 v179 尚无 full-link；后续重建若需重新生成，先保存该轮产物/日志，保持历史证据。

## 设备授权、存储与工具约束

- 唯一目标：92988a43 / zorn / slot `_a`。禁止CC9 `f85d4270`；禁止 flash/erase/GPT/slot变更、自行恢复刷机或扩范围。
- 用户此前明确“授权每次”，同范围试验在用户恢复目标后无需重复询问。但暂停状态优先，不能自行恢复。
- 64GiB专用unixnu：4096字节LBA47271680..64048895，GUID b279731f-ccad-4ef5-a8b7-e7440cd08de3；Data为其相对16GiB处初始8GiB窗口。日志仅相对2291712的一块4KiB；OS/SystemOS运行时只读。详见 [存储约束](storage-unixnu64.md)。
- 固定 runner 必须新 scope/ready/claim，完整 BCB 页读回并保留尾部、独立300秒看门狗、600秒主机Recovery上限，只做临时 `fastboot boot`。
- **无法回到Recovery时立即停止设备操作并报告**。不靠物理按键、插拔、触摸或人工拍照回收。
- 只使用已有私有 ADB server **5039**。不要新开5037/5038 daemon，曾因此延迟回收。手机命令需要当前工具环境的沙箱升级；沿用固定runner，不自己拼装临时读写/启动流程。
- 正确启动入口是生成后的 `read-zorn-gpu-irqNNN-cdc.py`，它同时启动CDC接收器和固定runner。不要只跑内部runner而漏掉串口采集。内部runner的 --check-only 需要准确 --bundle。不要把 --check-only 直接传给capture脚本，其旧报告路径不支持空stage。
- CDC product为 Redmi K80 XNU CDC，设备序列号按新tag构造 ZORN26+前12位大写；串口 `/dev/cu.usbmodem...` 动态发现，不硬编码。还可用看门狗+Recovery日志读取。相机非常模糊，可用本机 ffmpeg avfoundation USB camera `0:none` 辅助观察，不依赖它回收。
- 失败或DMA状态不明时保留可能仍被访问的资源，不做自动复位/解绑/重试；正常生命周期释放另按真实条件实现，不永久保留所有客户端对象。

## 暂存脚本与快照

当前源码和 compile command/dependency 为权威。相关临时转换/测试脚本已额外复制到：
`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v179-first-fence-38443aaea4c94d39961c1d4418aeb5f0/handoff-support`

其中 `zorn-record-context.py` 是旧报告助手，默认只固定少数源码；新报告应补齐本次真正改变的源码、测试、link/package及新字段资格说明。不要仅跑助手就认为新硬件范围已验收。

交接快照已保存当前源码 SHA，后续修改请保留此历史快照，不回填为新结果；新成果另写新的证据并更新 porting.toml。

# K80 iOS26 v241 当前交接（2026-11-16）

目标active。手机已确认回TWRP，保护区/BCB检查通过。241及此前已consumed的候选不重试。严格禁止任何反汇编/逆向、地址符号化、寄存器或回溯解释。继承[v240交接](handoff-2026-11-16-k80-ios26-gpu-v240-active.md)的存储窗口、基线和工具约束。

B241：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v241-terminal-session-8eae8662b4894169b58c2c2d773cd498`

S241：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v241-terminal-session-8eae8662b4894169b58c2c2d773cd498`

T241：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v241-metal-trial-8eae8662b4894169b58c2c2d773cd498/root-trial`

kernel SHA：f86ec1c0b0518371f8c565f364d70b552735e50a806256c8cb54041640a9b013

boot SHA：8364b94c8a3b964dd81723100cf28877563d94623320d1f33cab1e5d5fc720f4

## 已完成

终止处复用一次原zorn26_application_snapshot、原CAS try-lock，常驻POD不在panic栈。只输出既有source标量，request key和对象地址未输出。锁忙unavailable不清锁/不重试，原native writer边界。除Recovery新helper及调用外只有UFS/USB retag；无根修改、GPU授权或失败清理变化。

实际1398输入/24重编/0undefined/57头和5身份依赖通过。新真实snapshot/observer/formatter锁忙、并发、关闭、指针遗漏及原字节恢复ASanUBSan/TSan通过；新parser使用实际formatter输出，严格字段/重复/越界/identityCRCfooter检查通过。相关原包、formatter、producer、cleanup、failure-retain及race/parser/capture重跑通过。原scalar event recorder/header与240逐字节同，明确仅该范围复用旧host证据。原startup对象/源亦明确哈希复用。完整FAT和boot回读、原source loader consumer检查通过，只有kernel变动；43拒绝、实际receiver PTY402350B和check-only通过。测试里旧PASS237/239文字不代替实际本轮证据。

## 单次真实结果

200.270秒自动回TWRP，receiver/inner均exit0，284009B，14普通帧和277215B原始panic包。精确身份、CRC62b3592f及footer通过，0errors/partial；原因1050B、paniclog144948B、并发msgbuf131072B，导出无截断。保护区相同、完整BCB读回及tail保护通过。没有做额外设备恢复/重启。PAC原因前缀仍在，原始非文本数据留存不解码。

APP241实际终止快照与reporter均unique10/pid10，sessions2，rejected0/dropped0。flags31，calls91，method0/raw0，close0/0；prepare9/0/0/61/0。nativeReturn是seq87/method7/stage3/runSeen1/run0/base0/overlap0/reject0。method7按实际表为GetTimestamp，真实XNU外部分发函数已返回0，但不能据此证明随后的IPC交付/GPU任务或渲染完成。

关键源码线索：flags31包含clientClose在dropViews成功后设置的16；随后的closeApplicationProcess成功才会设置32，现在尚未出现，closeReturned也为0。method0/raw0是dropViews事件覆盖了最近普通method摘要，不能把0当作原生external selector。prepare9仍是open完成事件，不是close进度。由此确认进入关闭路径的观测，**不能断定PAC一定发生在closeApplicationProcess内，也不能排除其他线程**。

最后普通CDC帧仍phase1/无session，是较早采样，不能覆盖终止快照。无需继续围绕“从未进入newUserClient”假设加日志。证据：[v241实测](evidence/k80-gpu-v241-terminal-session-observed-2026-11-16.json)。

## 当前源码核对与下一步

真实关闭链：AppIo clientClose -> dropViews -> HostRing closeApplicationProcess -> beginApplicationOperation(Close) -> closeProcessClient -> quiesceKernelIo -> DirectClient releaseAll -> submit/timer detach -> ClientStorage析构/IOFree -> RestoreKernel/DetachVm/RetireDetached -> finishApplicationOperation。失败原样保留；不能跳过真实quiescence或强制释放。

已用完整对象SHA找出真正被选中的DirectClient配方：`k80-direct-fence-width26/ZornGen7DirectClient26.cpo-command.json`，输出SHA00e42681403fc929649be857e83c4d547c25354a07f732064b584116b6809c65，与本轮所选input1300整对象一致。公开源为`source/board/zorn/firmware/gpu-direct-fence-width-candidate/direct-runtime/ZornGen7DirectClient26.cpp`。先阅读的kernel-client-owner版本CPP及头与它逐字节同，未以参考版本冒充所选版本。184也有逐字节重编对照；若扩大头/ABI审计必须按当前真实配方与依赖进行。

目前没有证实源码缺陷，不盲改PAC、不把所有资源永久保留，也不把源码ABI推测当硬件根因。下一步可利用SOURCE240已声明保留的20..23位，给上述实际close授权、quiesce、releaseAll和ClientStorage退役添加无等待标记；它们若导出可区分关闭子阶段。扩展parser必须独立新模块保留240/241已绑定decoder，不能直接修改旧候选hash。必要时核对ClientStorage/DirectClient/NativeTimer等实际跨TU布局，而不是重复既有IOService/OSObject/MemoryDescriptor审阅。最终完整GPU/Metal/显示/FT3683验收未完成。

## v242 当前已完成的离线工作（未启动）

B242：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v242-close-source-ba560d3ea4d34be8964dd3463fcd7062`；S242：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v242-close-source-ba560d3ea4d34be8964dd3463fcd7062`；kernel SHA：`b46bad0585fa1373ac535da2c89009df3e427800ebbd38eb313ac7c18d527690`。实际1398输入/24重编/0undefined及58相关头依赖通过。新增HostRing对已存在ZornClientTrace240.h的引用；头、AppIo事件实现和241终止快照源逐字节不变。仅HostRing真实close源码插入20..23四次原子标记，另UFS/USB retag。删除新include和四行后HostRing逐字节还原241，未改quiesce、返回值、失败保留、正常释放或表退役顺序。

独立`UniXNU-zorn/scripts/inspect_ios26_gpu_source242.py`支持24位，240/241已绑定旧decoder未改。新parser覆盖四位单独/全位、未知bit24拒绝并成功重解当前241真实包；不解码原生非文本数据。source位置/原字节恢复检查在B242/close-source-check；其结果明确只属source/compile/parser范围，不冒充运行真实关闭代码。无新增存储或根镜像变动。

v242尚未打包、未生成runner/bundle/ready/claim、未访问手机。下一步先完成本候选实际终止分支/源绑定与decoder/capture回归，再生成完整启动包和新固定工具；不能使用只有kernel的产物启动，不复用241claim。原脚本在B242/stage242.py，完整配方/命令/输入和58头结果均已保存。详见[evidence/k80-gpu-v242-close-source-offline-2026-11-16.json](evidence/k80-gpu-v242-close-source-offline-2026-11-16.json)。

242后续已实测并回收，最新状态见[v242及243离线追加](handoff-2026-11-16-k80-ios26-gpu-v242-active.md)。

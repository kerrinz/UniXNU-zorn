# K80 iOS26 v256：完整操作串行化与进程上下文退出

v256已完成一次固定入口的普通系统实机验证，**333.724595秒自动回TWRP；当前无活动设备操作**。首个backboardd原生会话关闭0并重开，第二会话最后快照3293次调用、method13／raw0；正常表面151／SID183的access fence154与producer／tail／completed匹配。39帧58147字节串口、9170字节完整观测日志前缀、真实八核采样、七组存储保护和完整BCB检查通过。150／225秒原录像帧显示物理锁屏4:02→4:03。真实逻辑准入仍独占；本次不是逐次MMIO切换oracle、完整GPU桌面、所有客户端退出或FT3683手势验收。251的专用Metal已知像素／棋盘／退出基线和252硬件记录原样保留，目标继续active。

## 实际调用链

255已分离物理授权，但Ring操作开始时只拒绝pending竞争，进程页表则一直保持选中到关闭。要容纳其他独立VM，必须先接通完整操作所有权和真实上下文退出，不能只去掉服务排他判断。

- Ring在原实际创建方分配sleepable PI操作mutex，分配失败保留原部分所有者并返回NoMemory。锁序是实际客户端serial、完整操作mutex、issuer、native domain。新锁跨越真实authority检查、context选择、分发、drain和恢复；不在issuer下等待，不获取presentation registry。精确持锁线程用release／acquire发布；递归进入直接拒绝，外来finish不能清除或解锁合法scope。
- 普通操作和Close进入时按真实client／task查找已有进程，核对Ring／domain／VM／阶段，只能选择自己的上下文；已有别人的选中上下文返回Busy并保留。保留VM重选调用原transitionProcessTables→SmmuDomain→HostGpuTables Select，实现不变，包含原实际资源／stream／bank／ASID检查、TTBR写、TLBSYNC及读回。新sub-scope只许可精确当前进程的Select／Restore；原native逐次访问守卫仍执行。
- 成功Prepare在真实open后也恢复内核根；普通操作结束通过原quiesceKernelIo等待真实submit／fence、观察硬件idle，再走原RestoreKernel。映射、VM和ASID继续归原客户端，恢复根不是退休或DMA停止证明。正常Close仍先真实BO／VM清理、恢复／detach／retire，退休成功后清除借用的进程指针，再结束操作。
- 健康的有界WaitFence到期如果仍有真实未完成提交／资源，不再延长这次wait或切换其根，保留当前上下文；同一所有者后续操作可继续，其他已声明上下文不能借其grant。未知／poison／fault或硬件切换失败停止并保留，不复位、回滚、重试或自动释放。

本次实际改动只有HostRing头／实现以及新启动身份的UFS／USB字符串。Board、独立物理授权、DirectHfi、SMMU、HostGpuTables、VM／submit、用户客户端、Metal wire、插件、Turnip和Rust不变。HostRing公开对象字段／虚方法不变，private Storage增加锁和scope字段并由真实分配单元重编。HWSCHED候选没有被选用。

## 复现并修复的晚到故障

新退出流程增加了context步骤，最初只在进入finish时判定一次“健康超时”。控制在这之后注入故障，实际提取方法仍返回Timeout，主机以73退出并输出REPRO256。原源、内核、包和输出独立保留于before-late-fault-fix／late-fault-before-fix。

最小修复是在最后重新取得issuer后再次核对真实applicationOperationHeld与bootstrap健康；故障使结果变为NotReady、stop／mask并保留当前上下文／资源。实际Ring重编、完整重链接和当前全部相关控制通过。**这是未部署候选中的源码问题，不认定为252实机超时根因。** 全部sanitizer显式symbolize=0；没有地址／回溯分析或反汇编／逆向。

## 当前验证与精确输入

[实际操作检查](../scripts/check-ios26-operation-context.py)编译实际begin／finish、enter／leave、sub-scope、Ring transition、prepare／close以及真实client/task匹配方法。30项控制及48个并发请求序列化通过ASan／UBSan与TSan，覆盖正常重选／恢复、prepare退出、正常／失败关闭、每种身份拒绝、drain／切换失败保留、健康超时继续、晚到故障及外来scope。两个预置上下文交错只测试声明authority／SMMU边界下的本段源码，**不证明实际多客户端准入已实现**。MMIO／SMMU／drain／authority和客户端native正文是明确主机fixture，硬件后端以完整原生构建与下述实际256观察为准；主机边界仍不冒充实机。

当前physical57、Board29和service35已有控制以256源通过两种sanitizer；检查器兼容保留254源的控制另存，不作为256功能资格。31个实际消费者重编，1398实际链接输入核哈希、0undefined、90项有效头依赖与实际CPU16KiB检查通过；GPU／磁盘4KiB独立。原选择／恢复后端与真实drain源码逐字节保持，未用软件标志代替真实后端。

- kernel：`0f1840cb5d0afe0f3aa223784c3adcecdc769ef0173d44dec04ed60d37fa1aa3`。
- boot：`79249c64e1ec72666e8784912abc416a1a7271f9844e95d8cb92dd512c807944`。
- 已安装252 root：`859c7ebae6355ef7e089896680b0b8ffd9a03af8a1f078918feec740b7a06b02`。
- ADT：`98f04ff54b9573ddaa2c4716da0e954fae8192d15b1f105426eba7f216805936`；FD：`1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab`。
- 新启动ID：`21ebf249d0b54cd0b38305c2ce63535a`；禁用旧探针身份`f80eb1403d7e4f958b5eddacb49d98d0`不变。

完整FAT成员读回、payload重组、源码构建的文件／section元数据consumer通过；相对255仅kernel成员改变，root／FD／ADT／menu／政策及系统内容不变。以上为创建时的离线检查；当时无新根、增量、安装或设备操作。随后使用同一精确内核／包完成下述独立scope实机，旧创建证明不回写为已部署，也不补造手机整根哈希或loader／PAC全面资格。

源码：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v256-operation-context-21ebf249d0b54cd0b38305c2ce63535a。构建：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v256-operation-context-21ebf249d0b54cd0b38305c2ce63535a。[四份精确补丁与来源](../patches/gpu/ios26-operation-context256/source-manifest.json)零fuzz重放等于当前源；[当前离线证据](evidence/k80-gpu-v256-operation-context-offline-2026-11-16.json)保留晚到故障复现、当前输入和全部资格边界。

## 固定入口与一次真实启动

新增[256固定入口](../scripts/zorn_ios26_gpu_v256_system_trial.py)、[接收器](../scripts/read-zorn-gpu-system256-cdc.py)和[摄像头入口](../scripts/capture-zorn-video256.py)，由run-zorn-debug.py的显式256分支调度，继续复用原受审Recovery／BCB／传输核心。不是替换252入口的SHA。当前UFS／USB仅新启动身份改变，252 wire／journal／observer相关源逐字节一致；当前early、callback、终止包、晚到gate、close-reset用256实际源重测，解析／接收器以新TAG合成回归。81项包／scope／根／固件／上下文／保护拒绝以及准入、摄像头、接收器、固定runner check-only控制通过。全部sanitizer显式symbolize=0。

新scope `single-K80-ios26-gpu-v256-operation-context-300s-21ebf249`，完整独立归档、owner／ready／admission和新claim。现有native SDK37 ADB5039，实际已识别TWRP／zorn／slotA起步，接收器先于单次临时启动。300秒独立WDT、600秒返回上限，0重试，333.72459524997976秒自动回TWRP。七组原根／Data／边界样本逐字节一致，启动前BCB仅前864字节准备、完整4096字节读回且尾部保留；它们不是全Android／Data／32GiB根读回。没有新root安装、Android／Data／17／GPT／slot／boot分区写入、bootstrap、刷机恢复或物理协助。最初沙箱拒绝本机5039 TCP预检，尚无claim／设备访问；使用已授权的同一固定命令后完成本次单次启动。

早期持久化页明确CPU样本pending；实际后续CPU_done1、maskff、online8、USER／SYSTEM增量mask均ff。最终实际初始化worker state3、返回88、point6／ack6／failed0、publication0x100000000。严格backboardd日志与原生记录unique／PID均10；第一个会话9次调用、关闭返回0，第二个准备成功、最后3293次调用、method13／raw0，尚无关闭／进程退出记录。本次最后采样不是252的method6超时，但不能据此宣布252超时根因已修复或保证整个未采样时段均无故障。

正常surface记录frame151／SID183，1125×2436为客户端表面请求。producer／access fence／tail／completed均154，lease2、acquire／copy／账本成功，copy150→151。GPU_surface_write_proven／physical_scanout_proven仍false；原wire没有逐次TTBR／TLBSYNC读回的独立证据。选用并实际经过256上下文源码与获得每次切换的独立硬件oracle是不同资格。帧数和调用数与252不同，窗口／负载与新增每次操作drain都影响它们，未据此给出性能结论。

串口39帧／58147字节，runner／receiver／camera均0，解析无错误。journal 9170字节／60写入记录，seen／reserved／published／接收长度一致，gaps／pending0，SHA0596e585d56b9acc40f11aef3ddb34d99d3e8174dd17f18616b9824ab027f51d，CRC1162101630；daemon未退出，complete=false，旧紧凑摘要drop1保留。未采到panic终止包不证明永不故障。摄像头240秒无音频原录像29542219字节，SHA6e9ba8a9553e42e245a0f59811f6c7c95ca79b0f61fb2078dc34219c03fddf2c；实际查看150／225秒原帧，为物理锁屏4:02／4:03。未做地址／回溯解释、符号化、反汇编或逆向。

[精确本轮实机证据](evidence/k80-gpu-v256-operation-context-observed-2026-11-16.json)绑定kernel／boot／FD／ADT／root、当前源码／链接／日志／录像、scope／claim和保护结果。创建时offline证据保留原有未上机时间点，独立观察不改写旧收据。

## 下一步

继续多个逻辑成员的服务／Board／Ring准入及最后成员物理释放，沿用实际当前task／VM／ASID／fence／真实资源检查；未确认停止的DMA继续保留，正常生命周期满足后正常释放。256仍为单逻辑原生会话，不能只删除排他判断。补齐普通每帧渲染附件写入／提交／fence／呈现身份及完整客户端退出，继续FT3683完整触点／手势。保留252未解释的有界WaitFence原始状态；不重复同一启动。Android／Recovery／17／Data与历史产物保留，仅暂存，无新增commit／push。目标未完成，未暂停。

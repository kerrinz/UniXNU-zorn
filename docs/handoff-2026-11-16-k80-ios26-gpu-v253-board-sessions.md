# K80 iOS26 v253：Board 执行授权的会话所有权

最新实机基线仍为252：普通backboardd两个顺序原生会话、第一个正常关闭0、第二个持续使用，带已完成GPU access fence807的正常表面链路，物理锁屏及332.649883秒自动TWRP。253只完成下述真实Board实现、完整内核及完整启动包，**未启动、未生成设备scope／ready／claim**。不把这次结构改造称为已支持并发GPU客户端，也不转移252硬件资格。完整GPU／Metal／桌面／触控目标继续active。

## 依赖核对与本次真实改动

原实际252的服务reserveNativeClient、Ring单一appExecution、Board单一direct_app_identity／task／attempted／granted以及DirectHfi.activeApp共同限定一个真实GPU会话。现有HostGpuTables已支持保留VM映射、观察／恢复内核根、重新选择进程根及独立ASID退休，但所有实际执行／OOB权限仍要求唯一客户端。不能删除一个排他判断就开放其他任务的页表或复用其OOB结果。

只读核对本地houji参考HEAD`98bc0960f96076de8e8d16efcfb0c0603b166b85`的NativeAdrenoPublish.cpp，实际文件SHA`2e7b025b3d5b92d1144d80a20f2ad6d82850f204b1265c5129198df5e780cbd6`，文件与HEAD逐字节一致：`True`。该源自述多连接实现尚未具备每进程GPU页表，不能照搬到K80当前实际独立页表／ASID生命周期。这次没有新增上游代码或其他机型板级参数。

本次将Board的全局身份／attempt／grant标量换成Board实际拥有的ApplicationSession记录，含真实client／task、单调generation、Acquiring／Held／Failed／Retired阶段和所有权链接。记录属于小型内核CPU元数据，不是硬件grant或伪造的NativeAdreno后端。实际acquire／check／release三个回调都已接入，非仅声明；原物理资源和Ring代码仍在完整内核中执行。

- 实际acquire在原Board启动锁下分配并发布唯一尝试记录，之后才核对原资源身份、阶段、epoch、真实Ring调用与既有OOB观察。只有这些条件及原完整nativeApplicationWindowHeld都通过，才返回实际成功。分配失败返回真实NoMemory；参数／上下文／物理失败不会伪造成功。
- 成功记录必须与精确client／task及generation匹配；原源中的电源、PM、IRQ、SMMU、ZAP、资源引用、provider claim与Ring阶段／线程／OOB／VM检查逐字节保留，仅替换原身份表达式。原生失败留下Failed记录，不重置／回滚／重新利用。后续检查失效仍由原Ring停止／保留路径处理。
- 正常release必须先通过原phase3条件，即真实进程／VM退役、fence与原生队列已满足条件、OOB clear返回、实际clientClose线程和任务身份均匹配，之后只退休并释放自己的CPU记录。其他／旧client、错误task或generation不能释放当前记录。释放节点在解锁后完成，没有“所有对象永久保留”。
- AppExecution在进入这些实际回调之前已经retain client／Board及task_reference；正常回调返回之后才释放这些引用。记录中的身份指针依靠这条既有真实所有权链，不保存栈地址或临时回调cookie。失败时原AppExecution／client pin继续保留。

**物理会话仍独占**。本次只是共享执行所有者所需的第一层会话记录改造；共享物理电源／OOB所有者、多个逻辑授权成员、跨任务进程切换和最后客户端关闭后的物理释放尚未实现。不能据记录是链表、12个host竞争者或编译成功认定支持多任务GPU。

## 回归与构建

[可重跑源码检查](../scripts/check-ios26-board-sessions.py)直接提取实际记录方法和三个Board回调；28项状态／拒绝／正常释放控制及12个并发acquire在ASan／UBSan与TSan下通过。覆盖分配失败、原资源／Ring／OOB失败、grant后的真实窗口拒绝、错误／陈旧释放、counter边界、正常关闭与新generation。失败fixture清理仅是主机测试清理，不是手机恢复或释放未知DMA资源的方法。物理和Ring边界明确为fixture；实际物理谓词另外与252源逐字节核对，未以fixture代替硬件后端。

全部1398实际链接输入核哈希，30个身份／源码消费者重编，0undefined；79项有效头依赖核对，原生CPU宏仍ARM_PGSHIFT14／16KiB，GPU4KiB和磁盘4KiB独立。所有公开及私有头文件与252逐字节相同，没有IOKit对象字段／虚方法或Metal wire ABI变化。改变的是Board单元私有Storage与新增CPU元数据，实际sizeof分配随新单元编译。原HostRing／AppExecution／HFI／SMMU／页表／VM／submit源逐字节保留。完整变化只有Board源和新启动身份所需的UFS／USB字符串。

- kernel：`3700e98dc184a7fc37cc7910589c0437aef14df78db9a175f0545c1a3773d1d4`。
- boot：`0af365fb21f01d206ba4caa9328fc86e40b5977b631011666d7a75520b6a1b81`。
- 复用已安装252 root：`859c7ebae6355ef7e089896680b0b8ffd9a03af8a1f078918feec740b7a06b02`。
- ADT：`98f04ff54b9573ddaa2c4716da0e954fae8192d15b1f105426eba7f216805936`，与252相同。
- FD：`1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab`，与252相同。
- 启动ID：`b7865e69bc1d477c8864d05c51cda033`；旧禁用探针身份`f80eb1403d7e4f958b5eddacb49d98d0`不变。

没有新根镜像、根增量或存储安装。继续复用252的实际16页安装／保护／已启动收据链，未执行手机整32GiB根哈希。root、插件、Rust、Turnip、策略、Data、配置和ADT均不变，FAT只替换kernel成员；完整成员读回、payload重组、原源码构建的文件元数据consumer通过。它们不是loader运行／PAC／Board新分配器／GPU硬件验证。

[精确来源和三份补丁](../patches/gpu/ios26-board-sessions253/source-manifest.json)零fuzz重放等于当前候选；[完整离线证据](evidence/k80-gpu-v253-board-sessions-offline-2026-11-16.json)保留命令、根复用和引用顺序证明。构建目录：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v253-session-records-b7865e69bc1d477c8864d05c51cda033。源码目录：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v253-session-records-b7865e69bc1d477c8864d05c51cda033。

## 接下来需要完成的实现

1. 建立真实service生命周期的共享物理执行／OOB所有者，核对Board、Ring、HFI、map／资源引用、IRQ／SMMU及释放条件，不能用常成功authority或把第一个客户端永久冒充所有者。
2. 每个正常准入客户端保持独立任务、VM／ASID／BO／fence与metadata权限。完整操作串行化；切换前排空真实任务／fence，再复用现有RestoreKernel／Select／TLB观察，不能让另一个任务访问当前页表。
3. 正常关闭只退役自己的上下文，最后客户端再满足物理释放条件；状态不明／fault时保留全部仍可能被访问的资源。补齐跨任务交错提交、关闭、失败保留的实际源码控制与原生构建。
4. 如需验证253，先绑定当前所有者、callback／CDC／终止包／入口检查，准备新的固定scope／归档／ready／claim及300秒WDT／600秒Recovery；不得把新SHA塞进252旧入口或复用已消费claim。该接入属于后续工程工作，不是需要用户提供材料的阻塞。
5. 同时继续普通客户端逐帧GPU写入／提交／fence／呈现归属，以及FT3683完整触点和手势。现有矩阵Detector／HID注册不能充作完整物理手势验收。

本轮没有USB、摄像头、手机写入或启动操作；最后已确认设备状态仍为252收据中的TWRP，当前状态文件无活动设备操作，预期根859c7eba。无反汇编、符号化或逆向；未新增commit／push。目标未完成，也未暂停。

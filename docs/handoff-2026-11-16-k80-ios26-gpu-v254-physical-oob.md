# K80 iOS26 v254：Ring 拥有的物理 OOB 租约

v254完成真实物理租约／DirectHfi协议接入、完整原生内核和完整离线启动包，**未上机、未创建scope／ready／claim**。最新实机仍是[v252](handoff-2026-11-16-k80-ios26-gpu-v252-early-system.md)：普通backboardd顺序会话、完成access fence的表面链路、物理锁屏及约333秒自动TWRP；已知Metal像素／棋盘／正常退出属于v251。完整GPU／Metal／显示／FT3683目标保持active。

## 实际问题与本次改动

253已把Board身份标量接到真实会话记录，但OOB请求历史仍直接内嵌在AppExecution里，DirectHfi又保存唯一activeApp。它不能代表多个独立VM共享一个物理窗口。仅删除排他判断不能解决任务、页表、物理资源与OOB权限的对应关系。

新增ZornGen7PhysicalOob26，嵌入实际Ring Storage，随真实Storage placement构造；不是另一个虚构硬件后端或仅声明的所有者。每次实际Board acquire返回后，Ring在原issuer下创建带generation的独立租约，真实retain当前HFI及RegisterMaps。AppExecution仅保存该租约的精确指针；Ring拥有其物理存储和引用。尚未把这些CPU记录称为电源／MMIO grant。

- 实际DirectHfi acquire／held／release已使用该租约。原请求、ACK、ACK clear、GX观察及clear store代码移到物理所有者中由实际HFI调用；寄存器地址、操作顺序、100ms轮询与时钟逐字节／归一化核对。每次实际读写仍先走原Ring→AppExecution→Board当前权限检查，再调用原RegisterMaps访问，不复制内核OOB结果或绕过任务检查。
- Ring同时核对租约属于当前实际执行、generation、transport及register-map对象。旧／外来租约、失败或未完成释放不能当作新窗口。真实物理会话当前仍唯一。
- 实际关闭先完成原进程／VM／fence／idle与OOB clear，再取得Board phase3释放返回。仅成功后退休自己的物理租约；解除issuer后才release真实transport／maps引用及释放CPU租约。矛盾结果停止／mask并保留未退休租约。失败不会自动复位、重试或释放未知DMA资源。
- 分配失败发生在实际Board acquire之后，仍走原stop／pin保留路径，不伪造回滚成功。DirectHfi中的activeApp、服务slot、Board唯一成员和Ring当前执行约束没有取消。
- HWSCHED候选只适配记录指针与空指针拒绝，未被选用。Direct协议原文件为GPL-2.0-only；新物理头保留同一许可及来源。未新增上游代码或其他机型板级参数。

**本次完成的是物理OOB存储、资源引用和实际协议的所有权分离；尚未完成持续共享的电源／OOB授权、多成员上下文调度或最后成员关闭释放。** 不把编译或租约记录升格为多客户端功能。

## 回归、构建与范围

[当前可重跑检查](../scripts/check-ios26-physical-oob.py)编译实际物理头、DirectHfi的acquire／held／release方法及Ring关闭方法；45项控制及12个issuer串行化竞争者通过ASan／UBSan和TSan。覆盖OOM、generation边界、外来／损坏身份、每次MMIO失败与权限撤销、陈旧ACK／HOST、ACK／GX超时、释放失败、正常下一代、真实关闭调用顺序及退休矛盾。MMIO、Board、idle和外来关闭边界明确为主机fixture；失败fixture析构只用于主机，不能用作设备清理证据。

原有服务35项与Board28项／12竞争者检查也以当前254源重新运行，通过ASan／UBSan与TSan；它们仍只检验所声明的主机边界，不替代固件或设备证据。

本次AppExecution私有布局改变：内嵌记录换成租约指针。实际新共享头的8个消费者已全部重编并核对有效依赖，未混用旧对象；Metal wire和虚方法声明不变。完整1398实际输入核哈希、30个受影响／身份消费者重编、0undefined、87项有效头检查通过。实际CPU ARM_PGSHIFT14／16KiB，GPU4KiB及磁盘4KiB独立。Board253、RegisterMaps、SMMU、页表、VM、submit和用户客户端源逐字节保持。

首个原生编译发现当前SDK的IODelete宏要求指针左值；已改为局部指针后删除并完整重编，失败日志保留。随后补齐继承协议的GPL来源说明，再重编当前全部消费者并重跑当前sanitizer；先前中间产物独立保留，不能充作最终构建证据。

- kernel：`d2396a999171dc8dcd4ec9535301d7e0c4c5f6374bf8b55d3af12e50716a7c7f`。
- boot：`336d1b2861258792fc52d328372e889ef7a27673b8ca0f735f4838daa32b91ad`。
- root：`859c7ebae6355ef7e089896680b0b8ffd9a03af8a1f078918feec740b7a06b02`，复用252实际安装收据链，无新根或增量。
- ADT：`98f04ff54b9573ddaa2c4716da0e954fae8192d15b1f105426eba7f216805936`。
- FD：`1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab`。
- 新启动ID：`89af55e715684434803961954c18f126`；禁用旧探针二进制身份保持`f80eb1403d7e4f958b5eddacb49d98d0`。

完整FAT成员读回、payload重组、原源码构建的文件／section元数据consumer通过；相对253仅kernel成员改变，root／FD／ADT／menu／策略／插件／Turnip／Rust不变。不是loader／PAC运行、固件、OOB或GPU硬件资格，也未执行手机整32GiB根读回。没有USB或摄像头操作，没有手机写入、安装或启动。

源码：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v254-physical-oob-89af55e715684434803961954c18f126。构建：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v254-physical-oob-89af55e715684434803961954c18f126。

[八份精确补丁及来源](../patches/gpu/ios26-physical-oob254/source-manifest.json)在253冻结源上零fuzz重放等于当前候选；[离线证据](evidence/k80-gpu-v254-physical-oob-offline-2026-11-16.json)绑定当前测试工具、实际源、链接、包与252历史硬件收据。按[官方GPU教程](https://unixnu.com/zh/porting/gpu)分别保留源码、命令／fence、已知图像、呈现与退出证据，不迁移其他SoC板级输入。

## 继续推进

1. 将Board／Ring／RegisterMaps／HFI的物理电源和当前操作授权接到真正独立于首个客户端的生命周期。现有租约仍绑定一个真实执行，不能永久冒充第一客户端或把release-return当DMA停止证明。
2. 每个准入客户端保有独立task／VM／ASID／BO／fence；完整操作串行化，切换前真实排空，再复用现有RestoreKernel／Select／TLB观察。正常关闭只退役自己的上下文，最后成员才释放物理窗口；未知状态保留相关资源。
3. 本候选上机前仍须接通当前源码对应的固定入口、callback／CDC／终止包检查及新scope／ready／claim，保持300秒独立WDT与600秒Recovery。不得机械替换252旧SHA或复用claim。这些是后续工程工作，不是用户材料阻塞。
4. 普通系统每帧附件GPU写入／提交／fence／呈现归属、第二个daemon正常关闭及FT3683完整触点／手势仍未验收。252末WaitFence超时原因没有因这次重构而被认定解决。

Android／Recovery／17／Data与历史成功产物保持。本轮无反汇编、符号化或逆向，无新增commit／push。目标未完成，未暂停。

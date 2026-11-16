# K80 iOS26 v255：独立物理执行授权

v255已把实际Board物理授权、Ring所有者及DirectHfi接通，并完成完整原生内核和离线启动包。**未上机、未建立scope／ready／claim；逻辑原生会话仍独占，不能称已支持多客户端。** 最新硬件仍为[v252](handoff-2026-11-16-k80-ios26-gpu-v252-early-system.md)，已知Metal像素／棋盘／正常退出基线仍为v251。完整GPU／Metal／显示／FT3683目标保持active。

## 源码依据和实际改动

再次核对本地houji提交`98bc0960f96076de8e8d16efcfb0c0603b166b85`的NativeAdrenoPublish.cpp，SHA`2e7b025b3d5b92d1144d80a20f2ad6d82850f204b1265c5129198df5e780cbd6`，工作文件与HEAD逐字节一致。核对Published全局VM／submit／ring、issuer串行化、mount scope及clientClose的quiesce／releaseAll／失败保留。它的多连接窗口不能直接替代K80独立VM／ASID；本轮参考所有者与关闭顺序，没有导入新上游代码或其他机型板级参数。另查同SM8650候选NX769J、shennong；前者固定porting正文未取得，后者只读README状态，没有将其作为构建输入。参考查询失败不是本工程的阻塞条件。

254已将物理OOB存储移出AppExecution，但每次MMIO仍调用带client／task的权限回调，HFI仍retain唯一AppExecution。255新增实际physicalAcquire／physicalCheck／physicalRelease，参数只有Ring、真实maps／HFI和generation，不保存或永久冒充首个客户端。

- Board物理acquire先保存真实尝试身份，再核对原完整电源／PM／IRQ／SMMU／ZAP／资源／provider谓词和精确Ring回调绑定。只有这些真实条件通过才发布held；失败保留，不重试。原完整资源谓词经明确剥离逻辑身份后逐字节核对；逻辑会话仍保留原task／client／MACF准入，phase2／3额外要求对应物理所有者held。
- Ring在服务暴露前retain实际Board回调代码／存储，独立于首个客户端生命周期。物理租约继续retain真实maps及HFI。回调的phase／generation／释放意图与精确线程由实际Ring维护，线程用release／acquire发布，拒绝外来线程、重入、错误对象及旧generation。所有外来Board调用都在issuer／startup／HFI锁之外进入，Board在自己的startup锁下核对真实条件。
- DirectHfi实际acquire／held／release现在接受Ring，不含AppExecution或task参数，保留的对象也变为真实Ring。每次MMIO仍先调用真实Board physicalCheck，后走原RegisterMaps；request／ACK／ACK clear／GX与100ms轮询代码不变。正常逻辑入口仍先检查自己的OobAcquire权限；其他GPU操作仍依赖实际声明操作、任务和原逐次native访问守卫。
- 正常关闭依次完成原VM／BO／fence／idle与OOB clear、实际逻辑authority释放、独立物理authority释放，最后退休租约并在issuer外释放引用。逻辑记录退休时不再提前退掉物理epoch；真实物理release还要求所有逻辑记录已退休及原完整释放条件。clear返回不等于DMA停止／断电证明，没有新增复位或恢复流程。
- 逻辑关闭前的失败继续保留原client／task/session pin和物理资源；逻辑正常关闭后若物理释放失败，保留尚未退休的物理租约、Board／maps／HFI引用。不会把已经真实正常退役的逻辑元数据谎称仍持有，也不会释放未知物理资源。

当前服务slot、Board唯一逻辑记录及Ring单一appExecution仍限制一个逻辑原生会话；独立物理授权已接入实际后端，多个逻辑成员与跨任务调度尚未启用。HWSCHED候选与提交模式不变。

## 构建、回归与风险

[当前物理授权检查](../scripts/check-ios26-physical-authority.py)直接编译实际Board三个回调、Ring物理方法／关闭路径及DirectHfi方法；57项控制和12个竞争申请者通过ASan／UBSan与TSan。覆盖资源／phase／generation／线程拒绝、每次MMIO失败和权限撤销、ACK／GX超时、正常关闭顺序、下一generation与释放失败保留。平台资源、MMIO和外来逻辑关闭明确为主机fixture，绝不代替硬件grant。原Board检查适配显式物理guard后，29项／12竞争者通过；原服务35项控制也以当前源通过。

一次早期TSan默认运行意外尝试外部符号化，并报告测试替身锁的竞争。未使用地址／回溯进行定位；按可见fixture源码把布尔锁模型改为原子当前线程所有权。当前全部sanitizer显式symbolize=0并通过；旧报告按原样保留，未执行反汇编或逆向命令。另一个fixture const锁类型编译失败也已保留并按实际引用锁模型修正。目标源码的物理线程发布也已用release／acquire明确绑定，并重编实际Ring。

AppAuthority增加真实物理回调，嵌入它的AppExecution／服务／客户端私有布局随之改变，8个实际消费者已全部重编。额外追踪到原BootBuffers也包含DirectHfi头，保留其原源码正文并用当前iOS26配方重编；完整链接共31个替换对象／1398个输入／0undefined，90项有效头依赖检查通过。实际CPU仍16KiB，GPU和磁盘4KiB独立；IOKit虚方法和Metal wire声明不变。原RegisterMaps、SMMU、页表、VM、submit、AppExecution实现及AppIo实现正文保持，不能混用旧私有布局消费者。

- kernel：`f92e5f03a54683587fc1978c328055a12afb328f6de2822b2e39c3164a12dc98`。
- boot：`1d7d452086ea8f45f436569d831281a6c82ad18344db0f45d154ed704512e027`。
- 复用已安装252 root：`859c7ebae6355ef7e089896680b0b8ffd9a03af8a1f078918feec740b7a06b02`。
- ADT：`98f04ff54b9573ddaa2c4716da0e954fae8192d15b1f105426eba7f216805936`；FD：`1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab`。
- 启动ID：`1cb835aa6d994f3e82707a63221b483e`；禁用旧探针身份保持`f80eb1403d7e4f958b5eddacb49d98d0`。

完整FAT成员读回、payload重组和源码构建的文件／section元数据consumer通过，相对254只有kernel成员改变，root／FD／ADT／menu／插件／Turnip／Rust／政策不变。没有新根或增量、安装、USB、摄像头或手机操作；不是loader／PAC／物理授权／GPU硬件资格，也不是手机整32GiB根读回。

源码：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v255-physical-authority-1cb835aa6d994f3e82707a63221b483e。构建：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v255-physical-authority-1cb835aa6d994f3e82707a63221b483e。[十份精确补丁及来源](../patches/gpu/ios26-physical-authority255/source-manifest.json)零fuzz重放等于当前源；[当前离线证据](evidence/k80-gpu-v255-physical-authority-offline-2026-11-16.json)绑定实际输入、测试和包。

## 下一步

实际允许多个逻辑成员之前，接通完整操作串行化、每客户端task／VM／ASID／BO／fence以及真实排空后的RestoreKernel／Select／TLB观察。正常关闭只退役自己的上下文，最后成员才释放物理窗口，未知状态保留相关资源。继续普通系统每帧GPU写入／提交／fence／呈现归属与252末WaitFence超时定位，以及FT3683完整触点和手势。255上机前仍需当前源码固定入口、callback／CDC／终止包检查、新scope／ready／claim、300秒WDT／600秒Recovery，不复用旧claim或机械替换252 SHA。这些是后续工程工作，不是用户材料阻塞。

Android／Recovery／17／Data与历史产物保留；无新增commit／push。目标未完成，未暂停。

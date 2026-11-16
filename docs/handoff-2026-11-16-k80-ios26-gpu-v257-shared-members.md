# K80 iOS26 v257：真实逻辑成员与最后成员释放

v257已把服务、Board、Ring的实际逻辑成员集合及连续物理OOB／最后成员释放接到原后端，当前源码检查、完整内核与离线启动包通过。**未上机、未生成设备scope／ready／claim。** 最新实机仍为[v256](handoff-2026-11-16-k80-ios26-gpu-v256-operation-context.md)；原生跨任务隔离、退出、每帧GPU写入及完整FT3683手势均未验收。目标继续active。

## 实际实现

服务按实际IOKit客户端登记成员，仍在正常XNU service／client／MACF过滤之后才允许首个真实方法申请原生所有者；空连接只持元数据。Board分别保存真实client／task／generation，正常退出只退休该记录；原电源、时钟、RSC、SMMU、IRQ、固件认证、provider与真实资源对检查保持。成员上限64是CPU元数据边界，不是借用其他机型参数或无限GPU能力声明。

Ring实际列表分别持有每个AppExecution，活动指针只在完整操作mutex保护下临时指向当前客户端。生命周期API也使用同一个mutex；不在issuer／startup门下等待，递归或持issuer进入先拒绝。每次操作仍核对真实task／client、自己的VM／ASID，并调用原Select／drain／Restore／TLBSYNC读回。健康未完成的其他上下文继续返回Busy，不借用其授权或抢走页表。

物理租约移除了借用的首客户端指针，仍独立持有真实Ring／maps／HFI generation与原请求／ACK／GX／clear观察。第一个成员取得真实物理授权与OOB，后续成员必须先经过新的实际Board／task授权与当前资源检查才能加入。非最后成员释放仍走新鲜逻辑检查和原有界idle，但仅标记自身逻辑OOB释放；它的VM／BO／ASID真实退休之后才进入实际Board逻辑release并释放自己的引用。剩余成员继续持有原物理租约。只有最后成员走原DirectHfi clear、实际Board逻辑释放、独立物理释放及租约退休；未知DMA／清理失败仍停止并保留。不是常量成功后端，原HWSCHED未选用。

暂时不能进入的健康新客户端在createApplicationExecution之前收到Busy；实际AppExecution在首个外来授权调用之前必先发布partial输出。因此只在Busy且没有partial时归还该客户端未使用的CPU槽位与self-pin，仍保持IOKit连接；没有重试任何已尝试授权、OOB或硬件初始化。其余失败继续保留原partial。

## 实际发现的源码问题

首轮检查覆盖“逻辑grant成功后，最后一次真实资源复核失败”。grant已清除正在申请的活动指针，旧failure助手只按该指针匹配，遗漏了已Held记录。当前最小修复改为在实际拥有的列表中查找精确记录，将Acquiring／Held转为Failed并保留身份、generation与所有原引用。修复前Board源、内核、对象和失败输出保存于before-late-Board-acquire-fix及board-members-host-first-failure；不能把它认定为252实机超时根因。

## 回归范围与精确构建

[成员检查](../scripts/check-ios26-shared-members.py)编译实际服务／客户端方法及Board记录／回调；[操作检查](../scripts/check-ios26-shared-operation.py)编译实际成员查找、物理identity owns、task匹配和Ring上下文方法；[物理生命周期检查](../scripts/check-ios26-shared-physical.py)编译实际Ring check／acquire／release／close、Board物理回调与DirectHfi原协议。覆盖不同task／VM／ASID的交错与并发请求、首成员关闭后剩余授权、最终一次clear／退休、失败保留和未尝试Busy。全部通过ASan／UBSan与TSan，显式symbolize=0。

主机的MMIO／SMMU／drain／资源predicate、VM退休和逻辑close等边界均明确为fixture，不能代替完整原生后端和实机。原SMMU、HostGpuTables、DirectHfi协议、VM／submit、Metal wire、插件、Turnip与Rust不变。31个实际消费者及分配／metaclass重编，最后三个正文修复单独重编再完整链接；1398实际输入、0undefined、90项有效头检查和实际CPU16KiB通过。GPU／磁盘4KiB独立。九份补丁零fuzz重放匹配当前源。

- kernel：`82ad5d4a011181f24de8220d06a7fd022e5395c47cf8f138c1b86775707e9bca`。
- boot：`f07fb1ef16f7a3a4ad2ef6dff55e4f326a1a37ecab7c662748ca7418c9f3ea52`。
- 保留的已安装252 root：`859c7ebae6355ef7e089896680b0b8ffd9a03af8a1f078918feec740b7a06b02`。
- ADT：`98f04ff54b9573ddaa2c4716da0e954fae8192d15b1f105426eba7f216805936`；FD：`1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab`。
- 新候选启动ID：`ecb96de011624a6ea8c3d96ee9726dbe`，禁用探针身份`f80eb1403d7e4f958b5eddacb49d98d0`保持。

完整FAT成员读回、payload重组及原源码构建的文件／section元数据consumer通过；相对256只替换kernel成员。root、FD、ADT、menu、插件和backboardd政策均保持；没有新根、增量、手机整根哈希、安装或设备操作。源码/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v257-shared-members-ecb96de011624a6ea8c3d96ee9726dbe；构建/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v257-shared-members-ecb96de011624a6ea8c3d96ee9726dbe。[补丁和来源](../patches/gpu/ios26-shared-members257/source-manifest.json)、[当前离线证据](evidence/k80-gpu-v257-shared-members-offline-2026-11-16.json)。

## 后续仍需完成

当前源接通了正常共享路径，但其他成员健康待完成上下文的Busy／关闭退出处理仍需进一步验证；不将这些边界伪装为已完成功能。现有诊断仅覆盖原有限会话窗口，宽泛并发验证前要补齐逐客户端归属。保留的backboardd根也不提供独立跨任务工作负载或政策资格。先完成这些源码及固定入口／receiver／terminal／owner检查，再按新scope、300秒WDT和600秒Recovery做精确构建回归；不替换256旧SHA或复用claim。普通每帧渲染写入／提交／fence／呈现归属及FT3683完整触点／手势继续推进。

Android／Recovery／iPadOS17／Data及全部基线和历史产物保留；无符号化、反汇编或逆向，无新增commit／push。

# K80 iOS26 v259：未完成fence的有界关闭续行

v259已接通真实pending状态与同一次clientClose内的有界续行，修复258遇到健康待完成上下文时提前进入closing后不再继续的问题。源码回归、完整原生内核和独立离线启动包通过，**未上机、未建立scope／ready／claim**。最新实机仍为[v256](handoff-2026-11-16-k80-ios26-gpu-v256-operation-context.md)，完整GPU、呈现、退出和触控验收未完成，目标继续active。

## 根因与修改

[修复前复现](evidence/k80-gpu-v259-bounded-close-offline-2026-11-16.json)直接编译258实际IOClient方法，Root边界明确模拟健康的清理前pending：首次Close返回Busy且保持closing，第二次Close拒绝，未再观察后续完成。它不是252实机Timeout根因。

Root恢复、上下文进入、操作作用域及三段关闭接口新增明确pendingFence输出，入口初始化false。只有真实原Ring／Submit报告未完成fence且物理资源、租约、身份与健康检查成立，才在清理正文之前输出true；Close-process还必须经过真实scope退出且仍返回Busy。已经开始的process清理、OOB clear、逻辑authority释放和VM／资源错误不能输出可续行状态。release-OOB把foreign上下文检查放到outstanding拒绝之前，避免清理段之间的新任务丢失pending证据；原后置quiescence检查保留。

IOClient维持同一次Close线程、原task／client身份及serial锁，三段分别等待完成，只有Busy加明确pending才继续。共用原有1000ms关闭观察预算，另设每段最多1000次观察；每次1ms睡眠时不持issuer、startup或Root操作锁。前一段成功后永不重做。原真实cleanup／idle后端仍可能消耗自己的时间，因此这里不承诺总Close硬实时1000ms。到期或未知失败保留所有仍有风险的对象／task／资源引用，不伪造成功、不后台重试、不复位或强制释放。没有新增异步线程／worker。

## 复用与回归

核对本地小米14提交`98bc0960f96076de8e8d16efcfb0c0603b166b85`的NativeAdrenoPublish.cpp，沿用其串行真实releaseAll、仅成功才解除live及失败保留的机制；该实现没有可直接用于K80逐task VM／ASID的pending交接，故没有搬入其全局VM／slots或板级参数。精确文件SHA见来源清单。

[实际IOClient关闭检查](../scripts/check-ios26-bounded-close.py)38项控制覆盖三段各自等待、完成段仅一次、非pending Busy／Timeout不重试、时间到期、停滞时钟的1000次上限及内核task关闭；[Root上下文检查](../scripts/check-ios26-close-context.py)48项控制及两组各48次并发操作覆盖真实pending状态、完成清除、迟到故障和释放Timeout；[物理生命周期检查](../scripts/check-ios26-close-physical.py)75项覆盖实际Board／Ring／DirectHfi及释放前pending传递；保留[Ring／Submit fence检查](../scripts/check-ios26-context-fence.py)14项。全部通过ASan／UBSan和TSan，显式关闭symbolization。主机时钟、IOClient测试的Root后端、Root测试的MMIO／SMMU／drain／资源均明确为fixture，不能替代实际后端或实机。

当前32个实际对象重编，1398输入0undefined、106有效头检查、CPU16KiB、完整FAT读回／payload重组／原源码文件section元数据consumer与五份零fuzz补丁重放通过。GPU页／磁盘块4KiB独立。Ring、Submit、VM、SMMU正文、Board物理回调、Metal wire、插件、Turnip及Rust保持258实际输入。

- kernel：`7b838014b141a936bafa24583a515b6a2b95bcd2e38c214e89f2e23bd3f8aa3e`。
- boot：`ea6e4b851820328c5548066064473ae7b5d25b6ae2dd92ac3e973aafbe0c5d20`。
- 保留已安装252 root：`859c7ebae6355ef7e089896680b0b8ffd9a03af8a1f078918feec740b7a06b02`。
- ADT：`98f04ff54b9573ddaa2c4716da0e954fae8192d15b1f105426eba7f216805936`；FD：`1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab`。
- 启动ID：`d302c7f376ae4abc98d2a55184a2e41e`，禁用探针身份`f80eb1403d7e4f958b5eddacb49d98d0`保持。

[补丁与精确来源](../patches/gpu/ios26-bounded-close259/source-manifest.json)、[当前离线证据](evidence/k80-gpu-v259-bounded-close-offline-2026-11-16.json)。源码：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v259-bounded-close-d302c7f376ae4abc98d2a55184a2e41e；构建：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v259-bounded-close-d302c7f376ae4abc98d2a55184a2e41e。启动包只替换kernel成员，保留root／ADT／FD／menu／backboardd政策，没有新根／增量／安装／手机操作。

## 后续退休链源码检查

新增[联合退休链检查](../scripts/check-ios26-retirement-chain.py)直接组合原Ring wait／observeFence、实际DirectSubmitGateScope、Submit wait／waitAll／release以及VM退休／导入缓存／surface完成方法，七项控制通过ASan／UBSan与TSan。确认真实fence缓存读取在提交门外；作业引用退休、可写import缓存可见、submission资源退休、surface／fence账本发布按原顺序执行。缓存错误会隔离实际VM记录并保留作业／submission引用；退休错误不会被标记为健康pending。

先前怀疑独立Root物理作用域在门内被Ring guard拒绝，进一步源码追踪与联合检查未证实该调用路径：导入缓存维护走NativeAdrenoMemory，Ring nativeAcquire所在的实际wait段在门外。没有据此扩大guard权限或修改内核。Memory backing／缓存／引用方法及SMMU route仍明确为fixture，该检查不能证明旧NativeAdrenoMemory对象与源码等价，也不能代替实际硬件退休／缓存／MMIO／退出验收。精确kernel／boot保持；[附加证据](evidence/k80-gpu-v259-retirement-source-2026-11-16.json)独立保存，不改写前面离线构建证据。

## 后续

继续核验真实selected-submit完成后的缓存／作业／资源退休链，补齐逐客户端诊断和独立跨任务工作负载／政策，再准备固定入口、receiver、新scope／ready／claim、300秒WDT与600秒Recovery回归。完整实际正常退出、跨任务隔离及每帧GPU写入／fence／呈现仍需对应构建的实机证据；FT3683完整触点与手势继续实现。超时后的保留对象不是正常完成释放的替代，硬件生命周期尚未验收。

Android／Recovery／iPadOS17／Data及历史产物保留；无反汇编、逆向、符号化或新增commit／push。

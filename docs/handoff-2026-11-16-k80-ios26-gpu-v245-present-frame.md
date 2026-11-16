# K80 iOS26 v245：同帧呈现记录，完整内核离线候选

目标保持active，尚未完成GPU显示、FT3683手势和稳定性验收。上一轮只有Git状态核对，未推进驱动；本轮重新核验244源码/实机结果后实现245并完成完整链接。没有设备访问、启动、bootstrap或重试，没有推送，也没有修改原有暂存内容。严格禁止反汇编/逆向，所有检查只用公开源码、编译和输入元数据。

## 实际改动

复用244 framebuffer已经连接的Gen7完成lease、surface acquire和CPU copy，不新造成功后端。HostRing在真实beginPresentation成功、实际registry/issuer仍持有时保存cached tail/completed两个标量；仅同一实际presenter线程持有GPU lease时可以读取。原有HostRing类头文件与244逐字节相同，没有类布局/接口变化。NativeRing的lastSubmitted/completedFence在实际头文件中都只返回缓存成员，不新增MMIO或轮询。

framebuffer仍先取得真实lease并完成全部surface acquire，随后调用原show。show前后读取实际houji26Presents计数，只在原实现完成像素stores并发布计数后记录copy。记录包含原swap ID、producer fence、lease类型、cached tail/completed、surface数量/首SID、acquire结果、copy计数及尺寸。没有指针、机器地址或回溯字段。没有surface时acquire字段表示空集合通过，必须结合surface数量解释，不能声称实际获取了一个surface。

ZornPresentTrace245使用原子标量和序列号；writer try-lock只尝试一次，snapshot只尝试一次，不等待。seq繁忙/变动时返回不可用，避免半帧数据。各字段均用原子读写；不依赖普通非原子seqlock数据访问。该快照是最近完成的presenter调用，不是当前CDC帧的同步硬件采样。它不能单独证明surface来自GPU或物理scanout。

CDC实际next回调在原progress frame后追加dp字段，保持原39帧、3072字节单帧、529408总预算。新严格parser验证schema/字段数/lease/缓存完成/copy计数关系，交给原parser前只移除已经验证的dp字段，原Metal/会话/错误检查不变。原244 stderr丢失36问题没有通过放宽检查掩盖。

## 精确路径

B245：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v245-present-frame-46fe207f80874ffab3cff3464a4ed1ed`

S245：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v245-present-frame-46fe207f80874ffab3cff3464a4ed1ed`

最终kernel SHA：`67b097245cab175ac823dc98a402ccf7a3fcf692ee79277d48ea62aa8be3cda6`；1398输入，28重编，1370保留，0undefined。原root193e5f01不变。此处原为离线候选。后续本轮已完成独立包/runner/准入与一次实机观察，见下方补充。scope已消费，不得再次启动。

第一份245类方法方案已改为不改变既有类头文件的缓存标量方案；旧源码/对象/内核/记录保存在B245/revision-before-no-class-ABI。B245/stage245.py保存的是首份生成脚本，不是最终修订的幂等重建入口；复现最终版应使用source-manifest的最终源码SHA、minimal patches和实际build配方。不要盲跑旧生成脚本或覆盖历史目录。

## 已验证范围

- present-trace-host：真实新头文件ASan/UBSan，空快照/准确复制/繁忙丢弃/奇序列拒绝/100000次并发发布不混帧。
- present-ledger-host：提取实际getter，验证无lease、无owner、异线程、null及end后拒绝，同线程缓存完成读取；host stub不是硬件证据。
- progress-host-check及progress-frame-host：提取实际callback/worker/publication源码ASan/UBSan，原有成功、超时、失败和所有者路径；第二份从真实next回调生成包含dp的零帧，通过245parser。
- present-parser-host：原fixture合成dp及schema、lease、pending completion、fake copy、null SID、reserved负例；CPUcopy、不可用和计数低32位wrap单独检查。它们明确是合成数据。
- present-call-order.json：实际源lease/acquire/show/counter/record顺序；present-patch-replay：三个minimal patch在独立目录真实应用后等于归一化run ID后的最终源。
- full-build-review：实际1398输入SHA、58项相关头依赖与身份核对通过。最终修订重新编译全部28受影响单元；旧版通过没有代替新版链接/输入校验。

仓库源：[新trace头](../native/ios26-present245/ZornPresentTrace245.h)、[parser](../scripts/inspect_ios26_gpu_present245.py)、[补丁/输入清单](../patches/diagnostics/ios26-present245/source-manifest.json)、[离线证据](evidence/k80-gpu-v245-present-frame-offline-2026-11-16.json)。

## 下一步

1. 固定最终源/新header的影响闭包，补齐新frame源的成功/不可用/容量/PTY组合验证，更新fixed receiver调用245parser。原244 receiver不识别dp，不能直接复用启动。
2. 结合245实际源码变化审阅终止包、身份、close生命周期和原生产者测试的复用范围；固定新的full-build/source/identity receipt，不机械换SHA。
3. 由244完整包生成新的独立kernel/FD/loader/ADT/固件/root配置清单、FAT回读/loader验证和独立scope/ready/claim。看门狗300s、返回600s、完整BCB/tail/七组保护区检查保持。
4. 首次245硬件观察只验证这些实际同帧标量是否在GPU lease下出现，以及原Metal/close、Recovery与保护区是否保持。即使copy返回也不推断surface来源或物理扫描；再依据实际结果推进GPU surface提交与最终显示的对应验证。FT3683真实手势在无人值守没有物理输入时不能被轮询或合成事件替代。

## 本轮已完成包、采集和一次实机观察

上一目标轮完成源码/完整链接，本轮完成实际framebuffer成功/无copy/CPU/空surface分支、实际next callback正例/容量边界、实际终止sender、实际receiver/PTY，以及66项runner拒绝检查。原时钟源与244相同；245原配方独立重编与本次所选245对象逐字节相同。跨候选不同源路径造成的对象字节差异未被误写为相同。完整源码/测试体/对象闭包由present-source-closure.json绑定。

早期合成终止包仅替换run ID时被严格CRC拒绝；失败夹具保存在terminal-host-prior-synthetic-rejected，不是硬件故障。之后从245真实sender源码重新生成，组合parser/capture/PTY通过。未改CRC检查规则。

Boot SHA `7ed1d9f7d029fad864ad78477765cc50472a1a86a9feb33727bf97ecc0c2f286`，kernel仍为67b09724。FD、ADT、loader、原根193e5f01及固件由boot-package/verified.json和新root-trial/bundle.json精确绑定，无新根安装或窗口变化。真实启动仅通过固定外层read-zorn-gpu-metal245-cdc.py。实际run目录：B245同父目录的k80-gpu-v245-metal-trial-46fe207f80874ffab3cff3464a4ed1ed/root-trial/trial。

实际一次临时启动332.815134792秒自动回TWRP，runner/receiver exit0。CDC39帧40678字节，verified=true，无部分尾帧；全部39份dp快照可用。最后swap3148、producer/tail/completed均4、lease2、surface1个/首SID3、acquire通过、copy计数3147→3148，尺寸1125×2436。记录表示原GPU所有者完成lease下实际surface缓存获取和CPUstores返回；不代表该surface由同一GPU job写入，也不代表panel扫描ACK。

Metal报告仍phase11/flags1023/status4/code0，CRC718ed2ce，两个native会话closeRaw0；raw stderr丢失计数36，strict complete保持false。约176秒相机拍到iOS锁屏。七组before/after保护区样本SHA相同，完整4096字节BCB读回及864之后尾部一致。没有panic terminal包；没有导出panic不意味着故障阶段或隐藏错误。已完成Recovery回收，无后续恢复命令/重试。

[实机证据](evidence/k80-gpu-v245-present-frame-observed-2026-11-16.json)与B245/device-observed.json绑定实际run/capture/raw/camera及保护区SHA；[ready阶段补充](evidence/k80-gpu-v245-present-frame-ready-2026-11-16.json)是启动前快照，不覆盖初始离线记录。

## 下一项真实适配工作

当前39帧期间fence尾部仅2→4而presenter计数持续增加。不能从GPU lease模式推断所有锁屏帧都由GPU生成。实际公开MiniIOSurface.h将drawn描述为引用像素的最后GPU提交；在核对的公开源里RedwoodGPU.cpp在实际提交后写入该字段，并明确可能读或写，不能只凭该字段证明render target写入。当前DirectClient/VM/Submit源没有这条MiniIOSurface关联。下一步需在真实IOSurface-backed导入/资源提交/完成与显示surface之间建立有所有权和生命周期检查的关联，复用已有surfaceBuffer与importTask；不能伪造surface drawn或恒定成功回调，也不能只去掉software_accelerator启动参数便宣称GPU桌面。该字段目前仅作为源码线索，尚未证明当前显示来源。

FT3683轮询结果继续与真实点按/滑动/抬起/边缘验收分开。目标保持active，尚未完成，不重复245启动。所有后续Git只做本地commit，不推送。

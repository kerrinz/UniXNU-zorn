# K80 iOS26 v229：取消Metal前诊断等待的离线候选

目标active，未暂停。先读[v228实测交接](handoff-2026-11-15-k80-ios26-gpu-v228-active.md)、原224交接和AGENTS；严格禁止任何反汇编/逆向/符号化及寄存器回溯分析。

v229从228实际源代码仅移除215加入的10秒诊断等待及失败guard，保留正常setenv/标准MTL调用、真实handle/null结果、IOSurface全图oracle和失败保留。日志改用ZORN229DEV独立语义：stage1为phase2报告已返回probe，stage2为setenv成功后/MTL前，stage3为MTL返回；不再把stage1称作wait返回。真实调用片段12种ASan/UBSan与精确还原228检查通过；arm64e编译签名通过，新cdhash22d87b1d。完整内核89b13c9b、boot4456d99c、根193e5f01已离线生成；1398输入/22重编/44共享头/0undefined，source producer及52parser、新标记与45秒UFS绑定通过；根仅替换probe，63页/10组完整本地回放哈希一致，存储窗口重新核对。Metal bundle/Rust214/Turnip/着色器/启动job保持，不继承150秒UI或触控验收。thread_act.o依当前精确recipe重编与已选对象逐字节相同，确认同步kernel线程自退出，无需线程退出补丁。229尚未安装/启动、未创建device scope，当前手机为228根4651199b、最后单次启动已回TWRP。所有host进程已完成。

目标active。先从D228真实44页读回与其既有7118页重建实际228覆盖；准备229精确63页/10组新plan与原完整source/签名/前镜像/读回/保护校验。新plan应显式核对pre_Metal_delay_seconds=0、diagnostic_wait_unselected与229源代码精确还原检查，不复用旧10秒guard断言、不删安全门槛。完成固定安装工具登记/拒绝/新scope/ready/claim后安装；成功并核验Recovery后才准备独立单次boot接收器。不得复用228claim，不得把移除诊断wait预先认定为PAC或会话根因修复。

B229：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v229-no-preMetal-wait-65f3efb4a587473a9caebe54d7a99aea`。源码：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v229-no-preMetal-wait-65f3efb4a587473a9caebe54d7a99aea`。tag/kernel/probe身份：`65f3efb4a587473a9caebe54d7a99aea`。D228仍可从/tmp/zorn-v228-delta-review定位，已消耗，禁止重用。229无D229和设备claim。

父路径初始全局替换错误被挂载前/编译前检查拒绝，失败配方和空候选目录已分别保存，最终配方显式使用真实parent路径；失败版本未安装/启动。最终root/内核/boot和相关原始命令均保留。

[离线证据](evidence/k80-gpu-v229-no-preMetal-wait-offline-2026-11-15.json)。 [v228实机证据](evidence/k80-gpu-v228-device-boundary-observed-2026-11-15.json)。


安装准备：v229精确63页/10组根差分计划已完成：7150页154组实际228及更早读回覆盖与不可变本地228镜像一致；原完整源码/签名/前镜像/分组读回/BCB保护校验保留，新plan明确要求preMetal=0、diagnostic_wait_unselected及源语义精确还原。新增固定工具scope已登记并验证旧scope参数保持；host拒绝测试通过，独立scope/owner/ready/admission已固定，当前工具副本随准入立即冻结。仅unixnu专用iOS26根内更新，不写Android/iOS17/Data、不自动boot/重试；手机现场Recovery/全部保护/BCB/前镜像仍由固定runner执行前确认。 [证据](evidence/k80-gpu-v229-root-install-ready-2026-11-15.json)。


v229 READY，本段替代未安装状态：v229根193e5f01已安装，63页10组实际读回f343fc22匹配本地回放；保护元数据/边界与完整4KiB BCB安装前后相同，TWRP前后核验通过，无自动boot。新内核89b13c9b/boot4456d99c/ADT/普通probe229身份绑定，单独接收器先启动scope/ready/claim已准备，10项runner拒绝及check-only通过，保持120秒39帧119808B CDC、300秒独立WDT/600秒Recovery。移除的是可选10秒诊断wait，尚未证明根因/Metal/GPU或显示成功。 [证据](evidence/k80-gpu-v229-no-preMetal-wait-ready-2026-11-15.json)。


v229已单次观测并自动回收，本段替代未启动状态：v229移除10秒可选wait的候选已单次receiver-first启动，200.008秒自动回TWRP，session58616 exit0/inner0；6794B/14帧CDC，无尾帧/诊断丢失。最后state2/point5/ack5，source中gate5之后才调用实际registerService，未见gate6/注册返回；probe229仅phase1等候服务，service/device均0、native session0，尚未触及此次移除wait后的路径。不能把取消等待称作修复，也不能把缺记录当作registerService内部故障、panic或PAC根因。七组保护与完整BCB通过，root229193e5f01保持；安装63页/10组读回f343fc22，非全手机根哈希。 [证据](evidence/k80-gpu-v229-no-preMetal-wait-observed-2026-11-15.json)。
目标active，不重跑已消耗229scope。保留实际root/probe229及frontend226/Rust214/Turnip等，下一独立kernel-only候选优先完善串口终止原因：仅在真实CDC所有者try-lock成功、bulk IN已有传输完成、控制器/端点有效且无未知事件时发送单个<=63字节源终止枚举，限制在原39帧/119808B总预算内；无法证明USB安全状态则不做新DMA，保留资源。保留原复位/WDT/Recovery流程，不从内存地址、寄存器或回溯读取原因，不作任何逆向。先完成真实USB/终止hook源码、生命周期与失败拒绝回归、完整链接及新scope后再考虑硬件。

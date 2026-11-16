# K80 iOS26 v228：设备创建源调用边界

目标active。先读[v227实测](handoff-2026-11-15-k80-ios26-gpu-v227-active.md)和AGENTS；严格禁止任何逆向、反汇编、符号化或寄存器回溯推断。

v228只在真实probe的10秒wait返回、setenv成功后/标准MTL调用前、MTL返回后各增加一次有界write并保留errno；不增加加载、线程、重试、等待或假handle，普通Metal调用和全部IOSurface/已知图像/退出逻辑保持。实际原片段24种ASan/UBSan通过、移除新标记/身份可精确还原227原探针；arm64e编译签名通过。新根4651199b只改探针，44页/12组，本地完整回放相同，32GiB独立根窗口重新审核通过；Metal bundle/Rust214/Turnip/着色器保持。实际226读回叠加后覆盖7118页151组，与不可变本地226一致，非手机全根读回。内核1ac1c498/bootcc110cc8，1398输入22替换44头/0undefined；实际producer和52parser案例、新边界parser及45秒UFS绑定通过。初始plan因继承214而非实际226的215父frontend证明被拒，保留失败输入；修正精确父证明后原完整校验通过。安装新scope/ready/claim已准备，只允许unixnu原iOS26根内44页，每组读回、失败即停、不自动启动；尚未安装/启动。

B228：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v228-device-boundary-554a417898d14e899a0fcc8ba92862c2`。D228：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-metal228-root-delta-review-554a4178`。源源码见candidate.source；program_tag与kernel本轮tag均为554a417898d14e899a0fcc8ba92862c2。安装入口install-command.json；此安装无boot，必须成功读回并回Recovery后才准备独立boot scope。新probe只细分phase2之后的真实调用，不把stage2当作调用已经进入，也不把stage3当作返回非空。

[离线证据](evidence/k80-gpu-v228-device-boundary-offline-2026-11-15.json)。


v228 READY，本段替代未安装状态：v228根差分已按固定新scope安装并读回：44页/12组，e063d566匹配本地回放，全部保护/BCB检查通过，安装前后TWRP，未自动启动、未读回手机全根。新root4651199b/内核1ac1c498/bootcc110cc8/ADT与普通probe228身份已绑定；独立boot scope接收器先行120秒39帧119808B、独立300秒WDT/600秒Recovery，check-only和8项拒绝通过。只增加原wait/setenv/标准Metal返回处有界标记，仍需实机确认实际到达边界和后续正常渲染/退出，不认定功能完成。 [安装与准备证据](evidence/k80-gpu-v228-device-boundary-ready-2026-11-15.json)。


v228已单次观测并自动回收，本段替代未启动状态：v228普通探针新身份已实际运行，单次receiver-first210.621秒自动回TWRP，session86527 exit0/inner0，8412B/17帧，无尾帧或诊断丢失。最后phase2/flags1/service10000024b/device0，raw仅DISC，新增wait返回、setenv后/MTL前、MTL返回三个标记均未观测；native session0/nr0。证据尚未确认phase2 report本身返回EL0、10秒wait进入/返回或MTL进入，不能断定MTL/Rust失败，更不能认定panic或PAC根因。七组保护及完整BCB通过，root2284651199b保持；安装44页读回e063d566，不是全手机根哈希。实际XNU线程退出源代码确认kernel_task自退出同步thread_apc_ast，排除普通thread_terminate返回落入panic的猜想；无需改动。 [实测证据](evidence/k80-gpu-v228-device-boundary-observed-2026-11-15.json)。
不复用228claim。独立229候选移除215最初增加的10秒诊断wait，保持真实标准Metal调用、setenv、来源明确的边界日志、原backend及IOSurface/已知图像/生命周期；这是源时序对照，不先宣称修复。继续源码级定位，不执行任何逆向/反汇编。官方指南及其他机型公开README检索未提供可直接采纳的本机26修复；不照搬27/macOS/Mali板级和安全策略。

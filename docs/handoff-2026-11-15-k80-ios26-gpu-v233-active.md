# K80 iOS26 v233：精确静态宏后缀

目标active，严格禁止逆向、反汇编、符号化、寄存器/回溯分析。先读[v232实测](handoff-2026-11-15-k80-ios26-gpu-v232-active.md)、AGENTS。

v233独立kernel-only修正静态panic宏模板识别，沿用232源格式ID/63B协议、229根193e5f01与全部实际GPU/Metal输入。唯一实际诊断功能变化是recovery源改用ZornPanicMacro233.h：同一canonical模板表匹配精确字面量或其后紧接公开panic_call.h固定后缀 @%s:%d；不读实际文件名、行号或任意格式参数。一个有界表遍历，无分配、sleep、计时器、重试或新硬件写；若canonical与宏形式产生歧义，明确unknown。3565模板ID及原606源SHA完全沿用232；实际选用native编译参数的宏预处理表达式经主机编译oracle证明后缀匹配，全部canonical及宏形式、四类非法后缀、synthetic歧义、firstentry/unknown/pending、784进度上下文ASanUBSan通过，100组实际捕获竞争及USB竞争TSan通过；普通producer/52parser/83terminal边界和完整/截断capture通过。原formatter hook、USB/DMA/所有者/GPU/Recovery主体恢复对照逐字节相同。完整kernel2ac4092a/boot61ea463d，1398输入23重编50头0undefined，FAT仅kernel变化；FD/ADT/菜单/根不变。18拒绝/check-only通过，新scope必须校验macro233选择及原源目录和decoder同表SHA。无新root安装、重试或手机启动；未启动233。

B233：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v233-source-panic-macro-e5bb0aacbb254fa2a556319f0fb9f788`。源码：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v233-source-panic-macro-e5bb0aacbb254fa2a556319f0fb9f788`。kernel/USB/record为233e5bb0aacbb254fa2a556319f0fb9f788；普通probe仍22965f3efb4a587473a9caebe54d7a99aea。启动仅launch-command.json中的receiver入口，不单独执行inner、复用claim或重试。源模板ID是我们新增日志协议中的静态字面量分类，不能当作PC或调用点映射。

[准备证据](evidence/k80-gpu-v233-source-panic-macro-ready-2026-11-15.json)。[源码补丁](/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v233-source-panic-macro-e5bb0aacbb254fa2a556319f0fb9f788/panic-macro233-final.patch)。


v233已单次观测并自动回收，本段替代未启动状态：v233kernel-only单次receiver-first启动，200.019秒自动回TWRP，session31781 exit0/inner0。收到6857B、14正常帧及本轮e5bb0aac完整63B包r2/fffe/p652/vff。精确固定宏后缀修正后原模板仍未匹配；不能将宏覆盖缺口认定为GPU故障根因。终止源census已request6/ack5/state2，registerService实际返回；普通最后point5/ack5，probe phase1/native0，未验证渲染或退出。七组保护及完整BCB通过，根193e5f01未写，无诊断丢失、尾帧或解析错误，USB资源保留到整机Recovery。新增纯源码检查发现sleh.c的通用panic_with_thread_kernel_state静态格式643B，超过原512B模板预算而被明确排除；这只是又一已证实覆盖缺口，尚无实机证据证明本次走该函数。 [证据](evidence/k80-gpu-v233-source-panic-macro-observed-2026-11-15.json)。
目标active，不复用已消耗claim或重试。准备公开异常入口的有界固定来源枚举，报告已经由原源码分支决定的类别，不读取或输出PC/寄存器/地址/回溯/异常参数，不调用任何指令读取或解码函数；保持原异常处理主体和ABI。先离线精确重编、source恢复比较和实际分支控制测试，再准备后续独立验证。

# K80 iOS26 v225：原生请求返回观测已准备

先读[224实测交接](handoff-2026-11-15-k80-ios26-gpu-v224-active.md)及AGENTS。目标active，禁止任何反汇编/逆向、寄存器/回溯推断或符号化。

v225修复224观测盲区：旧完成计数位于serial解锁前，既不证明run/基类返回，也不记录后续请求入口。新增按内部args身份匹配的入口/run返回/IOUserClient基类返回三级快照，导出序号/selector/真实结果及覆盖/拒绝计数，不导出地址；未绑定首次调用不冒充匹配，跨session重置，try-lock丢失显式累计，无新增等待和原生返回值修改。实际action/external函数体、owner生命周期和tracker ASan/UBSan通过；C共享头兼容、实际formatter最大2005B/3072B，52既有parser+24新增拒绝/关联及同次UFS绑定通过。22对象重编/1398输入/0未解析导入/44头依赖，kernel6301affc/boot3d211739。沿用已装root224caaaa8af/同一签名probe224，未写新根。新scope/独立归档/owner/ready/admission/check-only与6runner拒绝通过；接收器优先、CDC120秒39帧119808B、300秒独立看门狗/600秒Recovery。只是更完整的源码进度观测，PAC根因和IOSurface渲染尚未解决，尚未执行225。

B225：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v225-native-return-3d3cd6e50e5f49f4ae8e5f04afe23b9c`。最终源码以source225-final.json/patch为准，初始stage文件保留，helper后补C兼容和首次未绑定返回忽略。所有旧root/源码/产物保持；未新增根写入。新decoder225继承223严格检查，nr只表示源码返回层级，不代表IPC返回或用户态继续；overlap/rejected/drop非0时不能作无歧义结论。

下一步只运行launch-command.json中的receiver-first wrapper，inner entry只check-only。成功与失败都等同一次有界Recovery结果，不重启livehandle或重复已消耗claim。只从源码和字段观察定位，不能把当前诊断当作PAC修复。 [准备证据](evidence/k80-gpu-v225-native-return-ready-2026-11-15.json)。


v225 COMPLETED，本段取代前文未执行状态：v225单次接收器优先观测310.525秒自动回TWRP，session77619 exit0/inner0，9528B/18帧有效CDC。新同请求观测nr=71/6/3/1/0/0/0/0：最后WaitFence6的run及基类externalMethod实际返回0，无覆盖/拒绝及结构化丢弃；随后普通Metal设备发现与shader/function完成，phase4/flags7/service=device10000024f。第二session74次完成调用，首session9次正常close0；尚无第二session关闭。辅助stderr截断29，仍严格拒绝完整验收。末尾frontend215标记1/11/3/4/5可见，缺6；精确源码5..6同时包含真实nmb_render_pipeline_new_with_options和gTimePipeline.add，不能把缺6当作Rust入口或挂死证据。未到IOSurface创建/渲染。七组保护采样与整页BCB/tail通过，root224保持，无新根写入/手机全根读回。此观测补足kernel返回盲区，PAC根因仍未确认。 [实测证据](evidence/k80-gpu-v225-native-return-observed-2026-11-15.json)。
以225实际phase4和frontend5为新窗口，先核对所选FFI descriptor/options布局、真实Rust pipeline入口/guard及返回后的gTimePipeline.add源码；必要时把实际FFI返回和计时更新分为独立有界标记，不用新增等待或假返回。新root若改变frontend/Rust必须仅替换必要载荷，以当前已装224和65页实际回执重新累计覆盖、完整delta/replay/保护审核；不能复用225scope或直接套旧root窗口。不盲重跑225，不将stage3推断为所有IPC返回或PAC修复。

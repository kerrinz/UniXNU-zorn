# K80 iOS26 v226：FFI返回与计时边界已准备

先读[225实测交接](handoff-2026-11-15-k80-ios26-gpu-v225-active.md)和AGENTS。目标active；禁止任何逆向/反汇编、符号化、寄存器/回溯推断。

v226沿225实际frontend5窗口核对了C/Rust descriptor/options全部字段布局和arm64e目标C断言，实际descriptor value-init清零通过；未发现明确ABI/生命周期错误。仅在真实nmb_render_pipeline_new_with_options返回后、原gTimePipeline.add后各增加一个有界write，不增加等待/重试、不改变调用次数/真实handle。实际helper/语句成功/空句柄/写失败/短写ASanUBSan通过；frontend重编签名，Rust214/Turnip/principal/PM4/probe224字节保持、无新增undefined导入。root226d94042c9只改frontend；4962页/88组完整本地回放一致，重新审核存储窗口，已安装224实际65页叠加后累计7068页151组覆盖。新根差分已安装/读回1c3322cb匹配，全部保护/BCB通过、安装前后TWRP；未做手机全根读回。内核1ef011ba/bootb4d5f39d，22对象/1398输入/44头依赖/0未解析导入通过，生产者/严格parser及UFS绑定通过。新scope/owner/ready/admission/check-only及6runner拒绝通过，保持接收器先启动、120秒39帧119808B、300秒独立看门狗/600秒Recovery。尚未启动226，不宣称Rust返回、pipeline或IOSurface成功，PAC根因未解决。

B226：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v226-pipeline-return-01e033d5c00e485aa92df8b986e55ec0`。D226：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-metal226-root-delta-review-01e033d5`。新frontend位于candidate.source/frontend226；修改仅两个有界标记，root226已装，probe224与Rust214保持。初始plan漏改“probe replacement”断言的失败版本保存为initial-plan-unselected.py，最终plan已针对仅frontend替换修正并重新固定/测试，未部署失败plan。

本轮root安装session78345 exit0，4962页实际读回。当前应由新launch-command.json接收器优先单次执行；inner entry仅check-only，不复用225已消耗claim。标记1只证明实际FFI返回、无论handle是否为空；标记2证明原timer.add已返回。所有GPU/图像/显示/退出结果仍用原严格检查，stderr丢失仍拒绝完整验收。

所有host进程已结束，226系统尚未启动。 [准备与安装证据](evidence/k80-gpu-v226-pipeline-return-ready-2026-11-15.json)。


v226 COMPLETED，本段取代前文未启动状态：v226新frontend根d94042c9已安装，4962页/88组实际读回1c3322cb与本地回放一致，安装前后TWRP。单次receiver-first系统观测310.419秒自动回TWRP，session77735 exit0/inner0；8412B/17帧有效CDC，无尾帧/诊断丢失。新probe224实际phase2/flags1/service10000024f、device0；raw仅发现DISC，未见principal入口标记，原生session0/nr全0。因此本轮没有进入226新增RustFFI/timer标记，不能由缺标记断定Rust或timer错误，也不能宣称panic。七组保护及完整BCB/tail通过，root226保持；无手机全根读回。USB摄像头现可用：有界取帧成功、手机在视野内但屏幕暗/反光，无可辨OS/panic文字，Recovery依据仍为固定runner的ADB身份。GPU/Metal pipeline/IOSurface/显示及完整触控未验收。 [实测证据](evidence/k80-gpu-v226-pipeline-return-observed-2026-11-15.json)。
保留226根/源码/全部实测，不盲重跑226。先核对所选principal对象的准确编译源码/recipe，以及frontend加载构造器与动态初始化；本轮比225的phase4更早，不能继续仅盯pipeline5..6或把未到当作Rust失败。原先C/Rust ABI检查与原生返回观测仍有效但未定位PAC根因。摄像头USB0有界捕获已验证，后续新scope可在运行中读取一帧观察手机；不要操作KiPhone或依赖物理协助，不从寄存器/回溯/二进制指令推断。维持接收器先启动、300秒独立看门狗和600秒Recovery。

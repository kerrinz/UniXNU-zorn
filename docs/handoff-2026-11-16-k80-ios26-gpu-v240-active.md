# K80 iOS26 v240 当前交接（2026-11-16）

完整目标active。手机已由固定工具确认回TWRP，保护回读通过；239和240 claim已消耗，不重试。继承[v239交接](handoff-2026-11-16-k80-ios26-gpu-v239-active.md)的源、基线、存储约束及禁止反汇编/逆向要求。禁止PC/寄存器/回溯解释、符号化、原生非文本数据解码。

B240：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v240-client-source-a307416d23c446e7b2cbcaf38fe152bc`

S240：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v240-client-source-a307416d23c446e7b2cbcaf38fe152bc`

T240：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v240-metal-trial-a307416d23c446e7b2cbcaf38fe152bc/root-trial`

kernel SHA：baaf4a14e70423d18058ba4c2be62b8461e3f8d680954e529bc0867de03b5fc3

boot SHA：fc6cb6556449f6c54c6a821c324e0ac9b662ff6c786559b2007fc3a3a0dc22fa

## 修改与验证

独立source候选继承239晚初始化。新增ZornClientTrace240.h及AppIo里的常驻uint32_t原子OR事件集：事件0..19来自真实registerService、新用户客户端和原生方法路径，20..23保留。没有新GPU授权、硬件调用、等待或恢复。Recovery终止处经原native paniclog writer追加唯一K80 SOURCE240文本行，原236包/原始原因/其他内容不变。去掉新标记和导出后AppIo/Recovery按原字节还原；UFS/USB仅retag。

实际1398链接输入、24重编、0undefined，55头依赖含新头在AppIo和Recovery的真实解析，5身份依赖通过。源标记/导出ASanUBSan/TSan、实际producer/formatter/包/normal cleanup/失败保留/竞争/严格parser/capture、真实receiver PTY402350B与37runner拒绝/check-only通过。原startup对象/源码哈希相同，明确复用已逐字节重建证据。完整启动包/FAT/原source加载器consumer通过，只有kernel变化，根229/FD/ADT/菜单/启动器保留。

回归发现新源码行parser将合法的截断paniclog传输错误判失败；已改为transport仍有效、source unavailable。实测前保留两套旧准备目录与旧binding/launch元数据，用stage240-boot.py重新生成完整bundle/owner/ready/admission并重新验证，未简单改hash越过门禁。主机脚本初次路径/字符串匹配错误均保留，修改的是测试/准备脚本，不是内核真实逻辑。result里的PASS237/239为复用文本，实际路径及本轮结果以B240为准。

## 实际单次观测

200.317秒自动回TWRP，inner/receiver exit0，277883B，14普通帧+271089B原始panic包。精确身份、CRC00a7f0fc、尾标记有效，0errors/partial。原因1050B、paniclog138822B、并发msgbuf131072B，导出无截断。七组保护及完整BCB/尾部通过，根和Data未写。

SOURCE240 events=1048575，所有0..19源码标记出现：registerService返回、新客户端准入/初始化/成功返回、externalMethod/action/run/prepareApplicationExecution进入及准备返回均曾发生。**这是并发汇总，不是同一会话或调用顺序证明；不能据此定位culprit。** 普通最后帧仍phase1/无session，恰说明不能把此前的普通frame当作终止时刻状态。PAC症状仍在；不解释原因中的机器状态。约148秒摄像头仅见过曝文字区域，不可辨读；无桌面/GPU画面验收。

证据：[v240实测](evidence/k80-gpu-v240-client-source-observed-2026-11-16.json)。

## 下一项具体工程工作

复用已有zorn26_application_snapshot，在终止时只调用一次，原函数的CAS try-lock失败即 unavailable，无等待/重试。用常驻静态POD而非在panic栈放大对象；只输出既有unique/pid/session/method/return/close及nativeReturn序号字段，绝不输出其key指针或对象地址，也不解码堆栈。这会提供真正终止时的最新原生阶段，避免普通3秒frame与panic之间的观测空隙。先对真实snapshot/formatter/竞争和失败无阻塞做host检查，再全量核对受影响头/对象与完整包，才能准备新scope。

继续源码接口、对象/会话与映射生命周期主线；不盲关PAC，不重新运行已consumed候选，不把本次日志标记成功当GPU修复。最终Metal/显示/FT3683完整验收仍未达到。

## v241 已完成的离线工作（未启动）

B241：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v241-terminal-session-8eae8662b4894169b58c2c2d773cd498`；S241：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v241-terminal-session-8eae8662b4894169b58c2c2d773cd498`。精确kernel SHA为`f86ec1c0b0518371f8c565f364d70b552735e50a806256c8cb54041640a9b013`，1398输入/24重编/0undefined，57实际头依赖通过。`houji_recovery26.c`新增终止时一次真实zorn26_application_snapshot，常驻静态POD，原CAS try-lock无等待/重试；锁忙只输出snapshot=0。成功时只打印既有进程计数身份、session/method/return/close/prepare/nativeReturn标量；不打印key或其他指针，不做额外对象遍历。原客户端及240事件源未改，数据根/存储无变化。

B241/terminal-session-host用实际观察器和snapshot源码、实际新增导出函数，检验锁忙不输出旧字段、并发更新、真实关闭字段及不输出synthetic key；ASanUBSan/TSan通过。native writer为明确主机边界替身。去掉新增函数/include/调用及原guard新增花括号后，Recovery源逐字节还原240。源码和现有POD头均有精确SHA。新helper在既有single-winner终止分支之后调用；没有新增panic栈大POD或分配。

尚未打包241、未生成241runner/bundle/ready/claim、未访问241手机。必须完成新的APP241解析与capture边界、实际完整终止分支review及相关检查，再生成完整启动包和固定工具；不能复用240已消耗claim或把仅kernel的241用于手机。详见[evidence/k80-gpu-v241-terminal-session-offline-2026-11-16.json](evidence/k80-gpu-v241-terminal-session-offline-2026-11-16.json)。241准备脚本及原命令保存在B241。目标保持active，下一步直接完成这些源码工程工作，无需用户补充源码或重复授权。

当前241已单次取得终止会话快照并自动回收；后续状态以[v241交接及242离线追加](handoff-2026-11-16-k80-ios26-gpu-v241-active.md)为准。

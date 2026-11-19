# K80 iOS26：278 呈现耗时采样与启动前拒绝

设置交互按机主指示独立待修。277 的最终结论为设置列表不能滑动、Home手势可返回桌面，不是系统整体卡死；[原始结论与更正](handoff-2026-11-17-k80-ios26-gpu-v277-manual-acceptance.md)继续保留。GPU主线优先定位低帧率，尚无准确FPS或已确认性能瓶颈。

## 实际输入与源码

278 来自实际277，boot ID `840cdc02db2b41919a8fc2ba68dcccb3`。完整kernel `6bb95f1ea11f2646b00bed3d23a1eb5609f98f1c2a01946cf811d259c3476d74`，boot `9d91967e47881538b855e470af5be043851a0c94e3dde40ac8cc7a868250d413`，11870208字节。复用实际271只读root `c60b198ded30a982cf96ee9cb66211a8f74c7d8fa80f5b6dd8e0839e121304fc`，FD／ADT／loader／manager与1022字节参数保持；没有新固件、根增量或布局变化。[精确构建与拒绝证据](evidence/k80-gpu-v278-present-cost-offline-2026-11-17.json)，[补丁与源码清单](../patches/gpu/ios26-present-cost278/source-manifest.json)。

实际MiniIOMobileFramebuffer的presenter增加原生CPU时钟计时：入队后等待、pace、真实lease调用及重试墙钟等待、cache acquire、show复制／缩放。保留GPU后端、锁、lease RAII、队列退休、失败资源保留与原呈现策略。复用原Trace245原子标量快照；只有presenter写入，无新增分配、MMIO或设备回调。累计微秒数饱和时记录故障，倒退时钟／丢弃发布也明确标记。

工作线程不创建虚拟HID、不生成触点。根EL0后90秒开始9次采样、间隔10秒，分别记录uptime、16项进度和16项耗时；1248字节K80PF278包，304words，CRC位于1240、schema位于1244。普通30帧＋perf1帧＋ROI7片保持38帧预算，终端／panic预算不变。中断采样先写end再发布done，保留部分采样。接收器先于固定runner；端口查找和串口capture函数与原252实现AST一致。

## 离线验证

实际编译33原生对象、1399完整链接输入、0 undefined、143关键依赖，CPU16KiB／GPU4KiB／磁盘4KiB分别核验；完整启动包与源码零fuzz重放通过。实际presenter／clock和观察线程正文经ASan／UBSan、TSan执行，覆盖正常完成、两次pending、真实终止分支、cache失败、无像素show、时钟倒退、饱和、并发快照、部分采样发布。GPU／时钟／cache／queue／show边界在主机测试中明确替代，主机耗时不当作K80性能。

解码／最终JSON、ROI和日志、缺失raw、传输／Recovery失败、旧schema／CRC／缺失快照拒绝通过。使用实际主机观察线程产包及明确重标记的275历史传输作测试fixture，绝不记为278硬件结果。完整bundle输入、准入与相机绑定控制通过；107项包拒绝含需要人工操作、旧计时工具、旧采样源和错误中断发布。没有削弱旧GPU资源／DMA检查。

初始入口检查误用了`address,undefined`而实际新cost收据为`address-undefined`，启动前拒绝；修正精确字段拼写并保留失败脚本／说明，无手机访问。源码主机测试初始mock及闭包脚本失败也各自保留，不拿早期失败产物替代最终结果。

## 实际启动前拒绝

已通过固定runner check-only，生成新独立archive、scope／owner／ready／admission。按既有无人值守授权调用接收器时，私有ADB5039监听不可达，**入口在claim与手机指令前退出**。主机只读lsof也未找到5039监听。无claim、无run.json、boot_attempts0、无手机命令或持久写入；current无活动run／admission／build，stop标志保持false。失败cdc-capture.json及精确输入保留，未覆盖或重跑。

相机helper等待fresh claim／live boot90秒后退出，没有打开相机、没有录像；继承的超时字符串含旧267编号，实际模块、scope和输入均为278，该字符串不构成267启动。此前设备清单实际识别`USB  Camera`，设备枚举成功不等于本次取得画面。

**278从未启动，也没有新的Recovery状态核验**；最后硬件证据仍为277约333.48秒回TWRP。不能用旧状态文件或历史回收代替当前手机状态。后续设备阶段需要已审核nativeSDK37私有ADB5039服务重新可用；不得自行bootstrap或重试这次已有失败证据的入口。新尝试需独立审查当前状态和新的scope／ready／claim／归档，保留300秒独立硬件WDT、600秒核验Recovery返回及零重试。无法核验回Recovery时停止设备操作。

## 性能解释与后续

LeaseCall是LeaseWall子集，不能相加；排队延迟可能与其他帧工作重叠，所有累计值也不能直接相加当墙钟占比。completed-copy rate包含空闲，仅是CPU完成复制率，不能当物理FPS、GPU时间戳或固定交互场景性能。缺失、故障、饱和、倒退或相同发布时间均不输出有效速率。

当前采样尚未覆盖frontend／转换器／submit CPU耗时、SwapEnd等待空slot和物理scanout。先取得278实际分段数据，再增加不依赖设置的受控场景并按瓶颈优化，避免猜频率或仅由静态画面判断GPU hang。完整渲染、跨task、客户端退出／资源生命周期、失败处置和FT3683身份／边缘验收继续保留。全程无反汇编、逆向或地址符号化；本轮暂存，无新commit／push。

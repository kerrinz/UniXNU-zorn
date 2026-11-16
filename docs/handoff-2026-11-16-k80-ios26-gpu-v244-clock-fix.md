# K80 iOS26 v244：时钟生命周期修复与续接

v244 从 v243 独立派生，保留全部旧源码、iOS17/Data和产物。目标尚未完成。禁止反汇编、逆向、机器地址符号化或寄存器/回溯解释。当前无人值守、有真机连接；只允许92988a43/zorn/slotA，固定工具、300秒看门狗、600秒有界Recovery返回，不bootstrap/重试/刷机恢复。

## 修复

实际选择的 DirectClient dispatch 原来把栈上 NativeAdrenoRingClock 和可能同样在栈上的cookie留在全局诊断hook。后续closeProcessClient直接releaseAll，VM unmap的PhaseClock可访问失效栈对象。原源码ASan复现再次触发stack-use-after-return。

新候选删除全局clock/context安装。DirectVM定义无上下文的XNU uptime函数，使用已存在HostRing::nativeNow相同的clock_get_uptime/absolutetime_to_nanoseconds方式；DirectSubmit改为直接调用函数。DirectClient的Tally仍在调用期间使用传入clock；实际ring/fence等待、cookie、releaseAll及DMA未知时保留策略不变。这样不需要共享可变clock的序列化或嵌套恢复。未声称所有现有volatile诊断计数器并发安全。

三份实际源补丁和输入SHA保存在 `patches/diagnostics/ios26-clock-lifetime244/`；精确对象/源码/命令见证据JSON。函数替代数据符号，三个使用单元必须一起重编。实际1398输入的undefined符号名检查确认唯一外部引用是新重编DirectSubmit，没有遗留指针使用者；这是符号名字检查，不读取指令或机器地址。

## 精确输入

B244：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v244-clock-lifetime-9a697dec3b024930bd83b9161c05e99d`

S244：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v244-clock-lifetime-9a697dec3b024930bd83b9161c05e99d`

Trial：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v244-metal-trial-9a697dec3b024930bd83b9161c05e99d/root-trial`

kernel SHA：`fac558258f3c8f0da78a88c5061dcc5ebdfab5c9644d9301659435bc74567af1`

boot SHA：`04af84279f32c798142d3f35cc24433c36a23caa2041fc08d909129b7973b05c`

Root保留 `193e5f01df3b0481412a980f4e7c562401762af53ffe2ea051fee11b66f5fc0e`。FD、ADT、启动器、菜单、固件和根配置均由bundle和boot-package/verified.json绑定；没有根安装或布局变化。nearest complete package为242，243没有启动包；不是伪造243包。完整链接1398输入，27重编、1371保留、0undefined。三个原始配方在独立目录重编与实际243所选对象逐字节一致，新源头依赖与原始输入按内容核验。

## 离线证据

- `clock-lifetime-regression/result.json`：旧源码预期ASan失败，新实际OS clock/PhaseClock/SubmitDiagScope/releaseAll源片段ASan+UBSan通过；返回后计时、嵌套、null、未open、wait失败不释放、free失败不close、正常释放等。host stub不代表硬件。
- `clock-provenance/result.json`、`clock-symbol-consumers.json`、`full-build-review.json`：原始对象字节证明、实际头依赖、精确链入及消费者检查。
- `source-delta-review.json`、`terminal-source-review.json`：改动范围及未变部分组合检查。复用历史测试均明确rerun=false，不能写成全部重新执行。
- `offline-tests.json`：生产者、reason、terminal、loop/race、packet、parser/capture、panic init及late gate本轮重新执行。
- `runner-source-review.json`：56项实际固定runner拒绝条件；`large-PTY-capture-check.json`：实际最终receiver函数收到402350字节，513字节边界，只有PTY的DTR被stub。
- boot-package：完整FAT五个成员回读、gzip/payload相等、loader源实现检查、300秒看门狗及touch标记。

所有辅助脚本已保存在B244；有些阶段脚本非幂等且依赖/tmp路径，重跑必须先读脚本并使用独立归档，不能覆盖已消费scope或历史证据。

## 本轮设备观察

固定外层 `read-zorn-gpu-metal244-cdc.py` 是唯一启动入口。第一次在沙盒内，访问127.0.0.1:5039在claim之前被拒；无run/claim/设备操作。该报告归档到trial的pre-device-sandbox-denial目录。随后同一固定外层在host权限运行，核验TWRP后只发起一次临时boot，不启动ADB服务。

运行中CDC收到39帧。应用报告phase11、flags1023、status4/code0、CRC718ed2ce、badffffffff，解析器render_complete=true；两个会话flags255、closeReturned1/closeRaw0，native_teardown_complete=true。raw_stderr_dropped=36使现有严格complete仍为false；没有放宽解析条件。这个新结果支持时钟修复后关闭路径推进，不独立证明历史真机崩溃必然由该缺陷导致。

摄像头clock244-live在约41秒拍到文本控制台；clock244-post-render在约170秒拍到清楚的iOS锁屏。照片不单独证明GPU桌面呈现或触控手势通过。

最终Recovery与保护回读结果须以trial/run.json及cdc-capture.json核验；运行结束后的补充记录见本页末尾及对应证据。

## 继续方向

保留244不重试；先绑定完整实际run/保护区/BCB和CDC结果，再从源码核对显示提交与呈现的实际路径。仍缺对应构建的GPU显示呈现、FT3683完整手势和长期稳定性最终验收。诊断丢失须如实区分stderr保留预算与渲染/关闭功能，不通过删掉严格检查获得complete。用户不允许依赖无人值守时的按键/触屏/插拔；不能把轮询成功当成点按、滑动、抬起、边缘行为的硬件证据。

## 已完成的回收与保护核验

本次实际单次试验331.983816秒自动回TWRP，runner/receiver exit0。39帧34867字节CDC，verified=true，0partial tail；没有terminal panic packet，因此不存在RELEASE243行，不能把缺行当作故障阶段。七组before/after样本逐字节哈希相同；4096字节完整BCB回读及864之后tail相同。设备不需要外部恢复，没有重试。详见 `evidence/k80-gpu-v244-clock-lifetime-2026-11-16.json` 和B244/device-observed.json。

泛用run.json仍保留保守静态GPU_started=false/lockscreen_proven=false，未修改历史输出。更窄的真实应用渲染/关闭证据来自同次CDC，锁屏证据来自绑定本次scope的摄像头照片，不能直接把泛用字段升级为GPU呈现验收。照片约170秒，root快照名义PID1后45秒，二者不是同一时间点。

## 显示源核对已继续完成

B244/display-source-review/result.json：从实际framebuffer配方的VFS overlay解析出真正输入，而非命令行表面路径；原配方在独立输出重编，MiniIOMobileFramebuffer对象与244实际所选对象逐字节相同。undefined符号名字检查确认实际引用capture/begin/end三个Gen7呈现hook，均由244 HostRing实现。沿用的CPUcopy呈现器已有真实GPU完成lease及surface acquire路径；不应重新实现相同逻辑。下一项需要把同一帧的GPU-produced surface、producer fence、真实completion/acquire与copy/panel结果关联；仅全局tail和锁屏照片不足以证明该帧来自GPU。

# K80 触控事件派发与边缘手势（2026-10-29）

基线 `bb4bd81b` 已通过锁屏、8 核、保留 8 GiB Data 和低亮度；触摸仍无界面响应。仅修改原 `UniXNU-zorn`、`uefi-zorn` 的开发内容，不同步两个 `_副本` 仓库、不提交或推送 Git。

## 当前证据

FT3683 原始矩阵和位置方向已由先前配对实验验证。上一轮 833 帧解码、bad0；原版 IOHIDEventDriver 已匹配，187 次 handleReport 提交，末次返回 0。报告提交不等于 backboardd 或 UIKit 已接收事件。早期触摸时间不确定，不能据此排除基线污染。

## 本轮改动与判读

参考[官方触控适配](https://unixnu.com/zh/porting/input)及当前固定上游 `NativeHidInput.cpp` 的边缘策略。原版 21H461 IOHIDFamily 的方法槽、构造函数、对象大小和可执行段哈希仍逐项审计；仅为本设备的 IOHIDEventDriver 使用独立 vtable 副本，派发后始终调用原版 dispatchEvent。`--touch-edges` 是显式开关，此前没有启动验证。它给从屏幕边缘开始的接触添加 `FromEdgeTip=0x800` 并保留到抬起，不把中央接触移动到边缘冒充边缘起始。

日志升级为 ZORNLOGD/footer v17，仍占既有单个 4 KiB 日志块、84 个词槽及 3072 B footer。touch[1..6] 的低 32 位保持原 UInt32 传感器值，高 32 位分别记录 installed、dispatches、digitizer_events、edge_marks、skipped_events、install_error。时间和其他 64 位字段不变。读取器先拆分，再校验传感器值；仍兼容 v16 和更早格式。独立字快照可能跨相邻事件，不是原子整帧快照。

新增 C 布局到 Python 的 v17 往返检查，覆盖最大计数、坐标不被高位污染、非法安装状态拒绝和历史格式；边缘接触生命周期、抬起/ID 复用及边界的 ASan/UBSan 检查通过。GUI 构建均执行并归档 footer 检查，读取器与相关源文件哈希纳入输入。

若 dispatches=0，则先查原报告解析/事件派发；若 digitizer_events>0 但 edge_marks=0，则核对实际触点和边缘坐标；若标记已进入事件仍无手势，再查用户态事件订阅。任何单项计数都不能单独认定触控可用。

## 构建与实测

保留基线的八核预检、9 轮映射、8 GiB 持久 Data、低亮度、服务策略与总线协作节奏，只启用边缘标记及诊断。300 秒观察、600 秒主机回收，独立 watchdog 和 recovery BCB 保留。候选正在构建，尚未启动或验证触摸响应。

候选 `de7bdb63` 已完成构建和 115 项输入核对，boot SHA `de7bdb63ed67f314a4f71d8fe7380aa9aff327869191aa2570dd8dc694e709bb`，kernel SHA `290c589b2970996cd482ac2406115c2ab86cb9aa94dc112815a9c4c82c9e906a`。实际链接的日志写入函数读取六项事件计数，边缘派发包装通过固定原地址的间接尾调用返回原版 dispatchEvent；构建、原版 ABI、完整归档通过。尚未取得真机事件计数或触摸成功结果。

## de7bdb63 自动回收结果

12:29:01 临时启动，12:35:39 自动回 recovery。新日志与 boot/kernel/归档匹配；机主观察为苹果标志，未到锁屏。810 帧解码、bad0、无触点/HID 报告；installed0/install_error1/dispatches0，适配器在修改 vtable 前被拒绝，不能认定边缘包装造成启动卡住，也不能把 reports0 当作解析器故障。八核各 mask ff、存储/读取错误0、Data 原 cookie 保留、低亮度读回64。见 [回收证据](evidence/touch-edge-rejection-result.json)。

离线核对最终原版 EventDriver 方法表与生成表完全相同，未发现表内容漂移。原版代码另有 AppleUserHIDEventService 子类（父类 IOHIDEventDriver、大小0x110、vptr0xfffffff005d012c0），自身覆盖 dispatchEvent0xfffffff004acc010。原适配器只允许基类0x108。现新增该子类的名称/元类/父类/大小/完整220槽方法表及派发入口检查，运行时仍拒绝未知 vptr、错误大小或任一槽不符；仅改变本设备实例的表副本，并调用该实例原有的 dispatchEvent，而不是强行转到基类。尚待真机类型和计数证明。

安装错误细分为1未知vptr、2大小不符、3方法表不符；TCH 附 ED=installed/error/kind/classSize（kind1基类、2已核对子类）。同一v17字段保持原义，只允许这三种明确失败码。下一候选保留Data/8核/低亮度/触控节奏，观察600秒、主机回收900秒，给系统初始化更多时间；正在构建，尚未启动。

候选 `37059cf4`（boot `37059cf4324a6ecb11790d0349c86d04dce059162bbc96e2f4ebbc8d76998e25`，kernel `aa55e638a89aad1676495e3407478bbd60fcb06f359d980f75ef42e225e983ee`）通过 115 项输入及完整归档核对；实际编入适配器的基类和子类两张 220 槽表均与最终内核的原表逐字一致。已于 2026-10-29T12:41:12+0800 定向临时启动，600/900 秒，尚待真机类型、触点和事件链结果。

额外宿主检查直接包含实际 ZornTouchEdgeDispatch.h，在 ASan/UBSan 下验证两种已核对类各自调用原派发方法、仅改实例副本的198槽、原表完全不变、未知vptr/错误大小/任一槽变化均拒绝且不保留或改动对象；并覆盖父子事件、抬起/ID复用、过大children和错误子事件。检查源SHA与37059cf4归档输入相同，结果保存该run目录；后续边缘候选的构建器会自动执行并归档此项，不冒充真机成功。

## 37059cf4 真机结果：接触报告与事件之间断开

12:52:51 自动回 recovery；新日志/boot/kernel/reader/归档已核对。1619 帧有效解码、bad0；机主在提示后执行按住/上滑，HID提交86次、末次返回0。ED=1/0/2/272 证明实际为 AppleUserHIDEventService，精确vptr/大小/220槽检查通过并已安装实例包装；footer dispatches/digitizer_events/edge_marks 全0。不是未读到传感器，也不是边缘标记已经生效。尚不能声称全部报告成功或 backboardd 接收到事件。机主画面仍苹果标志或色条。Data原cookie/8GiB/错误0、SMP8全ff、亮度64保持。见 [本轮证据](evidence/touch-subclass-result.json)。

[Apple 的公开源码](https://raw.githubusercontent.com/apple-oss-distributions/IOHIDFamily/main/IOHIDFamily/AppleUserHIDEventService.cpp)说明该子类的用户驱动路径与基类不同；此为结构参考，不借用最新版ABI。原版21H461 dispatch代码另已确认读取实例+0x108的ivar和ivar+0x10启动位后才调用父派发，保留这一检查，不写该状态。当前事实只支持继续查报告到事件的解析路径，不据此断言永久死锁。

下一实验默认关闭：--touch-kernel-parser 在本设备发布 IOHIDInterface 前注册原版内核 IOHIDEventDriver 的定向 personality。Product 必须是本设备固定名称、Transport=SPI、usage=Digitizer/TouchScreen，并重复限定IOPropertyMatch；不删除其他personality、不终止已有驱动、不启用用户驱动或改其他服务。注册失败即拒绝本次触控发布。与上一600秒观察不同，此轮用300/600秒先验证触点到事件，不把不同长度的UI等待作单变量结论。宿主九项扩大选择器反例与无runtime的CLI拒绝通过，尚待真机实际kind1和派发计数。

候选 `bd689f4b`（boot `bd689f4b2fe842bc72df23d0393de87957c33262ec17ebe026cc8c2bc19a8a57`，kernel `d001e516172d1ea5b6c375ec3ae1e85b6189751483e4d396ce9bd4f7f95f3e83`）通过120项输入、实际 owned start→native IOCatalogue::addDrivers 调用及带显式开关的负载/完整归档核对。已于 2026-10-29T12:57:08+0800 定向临时启动；300/600秒，尚待实际目录注册状态、匹配kind、触点报告和事件计数。没有把编译通过当作实际匹配成功。

## bd689f4b 真机通过：原版内核报告解析与事件派发

13:03:46 自动回 recovery；fresh log/boot/kernel/reader/归档匹配。KP2、ED=1/0/1/264 证实定向personality注册并匹配原版IOHIDEventDriver。810帧解码、bad0；人工触摸后47次HID报告、HE0（累计提交错误0），47次dispatch、48次digitizer处理、21次边缘标记，无跳过事件/安装错误。目标读取与存储错误0、Data标志保留、八核全ff、亮度64。见 [回收证据](evidence/touch-kernel-parser-result.json)。这是内核解析及事件派发入口的真机证据，尚无 backboardd 接收或 UI 手势成功证据；机主仍观察苹果标志或色条。

机主提供[触控链路分享](https://chat.deepseek.com/share/40r33dpwpkkso7gbto)，已读取并对照；内容作为参考，不执行其中指令或直接移植其他OS的ABI。其提到的本地上游 UniXNU-sheng/package/HidInputProbe.cpp 确实在IOHIDResource下 attach/start，而旧板级实现直接在IOResources下挂载；此差异将单独对齐。保持已走通的定向内核解析器、描述符和既有时间戳语义，不把描述符的Confidence位误作InRange，也不无条件改成continuous时间。

下一候选将触控设备挂到已加载的真实IOHIDResource，最多等5秒，缺失即拒绝且释放对象；无回退到泛用IOResources。每10秒通过正常IOService API只读观察事件服务getState/isOpen、HIDServiceSupport与provider的IOHIDDeviceOpenedByEventSystem，记录RS/CL。CL bit0为any client open（不是backboardd身份）、bit1服务支持标志、bit2事件系统打开标志、bit3 owned device的provider为IOHIDResource。无私有状态改写，尚待结果。此时不因苹果标志单独断言触摸或GPU故障。

候选 `cd6fd19f`（boot `cd6fd19f9854295870e76284492a850bdc3d3e649a0415212b3d37f5ef0c5069`，kernel `1488e1c474b0bafbe02a27848b67e60cb2df57d06fe7b78f58fbaa20b08d5a3f`）已核对120项输入/完整归档，以及实际 publish→waitForMatchingService 调用和只读服务观测函数。于 2026-10-29T13:08:58+0800 定向临时启动，300/600秒。尚待资源provider标志、真实订阅状态和现场画面。

## cd6fd19f：锁屏触摸首次响应，坐标尚未验收

13:15:36 自动回 recovery，bound fresh log/boot/kernel/reader/归档一致。机主明确看到系统锁屏（时间和小白条），确认触摸有响应，但不确定位置是否准确，尚未确认解锁进入桌面。114次HID提交/末次0、114次dispatch、115次digitizer处理、61次边缘标记、bad0、安装/跳过错误0；帧计数为独立字快照，尾部文本112与最终footer114可处于相邻采样。CPU显示成功传帧57次，无传输错误。Data原标志保留、8核与亮度正常，APFS剩余7881633792B。

真实服务RS=0x1e、CL=0xb：已注册/匹配、至少一个client打开、HIDServiceSupport已设置，owned digitizer的provider确为IOHIDResource。bit2未置位不等于没有backboardd，因为公开isOpen仅说明有client，不确定具体进程或打开选项。机主的锁屏响应另作独立端到端观察。见 [本轮证据](evidence/touch-resource-response-result.json)。

此镜像与完整内核已保留在out/zorn/builds/cd6fd19f，known-good-touch-response-cd6fd19f.json明确仅验收锁屏响应，不把它称为坐标、多点或长期稳定通过。下一步先用同一镜像进行可见控件命中和方向测试，不在未定位前更改坐标映射。

## cd6fd19f 重复轮次离线复核与下一候选（未上机）

机主已带走手机，本轮没有查询 adb/fastboot、临时启动或写入设备。已核对 `20261029-132005-cd6fd19f` 的 recovered 状态、新旧日志 SHA、当时读取器身份、boot/kernel 和归档清单，原始 4 KiB 日志 SHA 为 `80f09ffa75e1e2a2169b89712cc41945d3087ebf1d255e8a2184a5a62e2fff73`。149 次报告提交及派发、150 个 digitizer 处理、22 次边缘标记，解码/提交/安装/跳过错误均为 0；Data 原 cookie、八核全 ff 和低亮度 64 保留。见 [坐标复核证据](evidence/touch-coordinate-analysis.json)。

末次传感器坐标 `(9805, 8409)` 在 0..32767 范围内，约为横向 29.92%、纵向 25.66%，对应当前面板约 `(431, 821)`。机主说明先误按左上，随后补按偏左下；旧日志没有触点序列及相应时间，不能把末次值强行归属到纠正后的按压，也不能据此证明纵轴应再次翻转。上次“右上向下滑像锁屏长按编辑”同样不足以单独判定位置变换错误。当前只验收锁屏响应，不验收坐标准确、解锁或桌面。

### 新增的有界证据

`--touch-trace` 默认关闭，要求 runtime touch，且与 GUI 用户/内核栈采样互斥。候选保持原坐标映射、报告描述符、原版内核解析器、真实 IOHIDResource、8 核、8 GiB RAM、保留的 8 GiB Data、低亮度和总线协作参数。仅增加观测开关及对应诊断代码。

v18 复用原来未启用的 432 字节栈记录区，保存最近 32 个按下／移动／抬起记录及毫秒时间、触点 ID、位置、接触数、异常释放原因和采样间隔上界；移动超过 512/32767 或静止满一秒才保留一条，超过容量显式计数覆盖。记录的是送 HID 前的已解码传感器输入，不代表用户态已收到；圆环首条可能已是手势中段。异常连续帧和 worker 结束产生的释放与正常抬起分开标注。

单生产者以原子字发布，读者最多三次获取一致快照，忙时明确记录 unavailable，避免阻塞触控线程。只有轨迹区是这种一致快照，其他历史 footer 计数仍可能跨相邻采样。GUI footer 仍 3072 字节，环形文本仍 84 槽，总日志仍为既有的单 4096 字节块；未新增任何持久写入范围。

ASan/UBSan 覆盖按住、移动、抬起、异常帧释放、ID/坐标越界、循环覆盖、并发发布和忙写者；C++ → Python v18 回读、13 项损坏反例及 CLI 拒绝通过，151 份历史日志仍可解析。最终 ARM64 内核已核对 worker 内联发布、共享 BSS 地址、acquire/release 指令、读屏障及 v18 选择。以上都是离线资格，不能当作新镜像的真机通过。

### 待测镜像

- Boot：`349a923188caaf7b90f835e52442926b1124b7705899bf195dae69c812170a3e`，81125376 字节。
- Kernel：`93e8600dd2730793a1c0ad38be2460ad3b36028e1a198d238d6e78bf2dd2e858`。
- 固定归档：`out/zorn/builds/349a9231/boot.img`；默认 `out/zorn/boot.img` 与其相同。
- 123 项输入及完整归档哈希已核对，其余 profile 字段与 cd6fd19f 相同。
- 300 秒 GUI 观察、600 秒主机回收，独立 watchdog/BCB 保留。没有使用 `--boot` 或 `--fresh-data`，未重置 Data。
- 初次构建被主机沙盒 sysctl 拒绝，生成目标缺失随后按原编译命令修复；最终完整构建成功，不沿用失败构建的旧镜像。

构建与证据摘要见 [候选离线核对](evidence/touch-coordinate-candidate.json)。目前按机主要求暂停，heartbeat 和全局保持唤醒任务不恢复；两个 `_副本` 仓库没有修改，不提交或推送 Git。

### 下次接回后的单轮操作

在共同父目录执行固定归档回收器（本轮未执行）：

```sh
python3 UniXNU-zorn/scripts/run-zorn-debug.py \
  --image out/zorn/builds/349a9231/boot.img --timeout 600 --arm-recovery-bcb
```

只针对 92988a43 / zorn / 槽位 b，手机从 recovery 或 fastboot 起步，不启动 Android。先保持不触屏至少 20 秒，待系统锁屏出现后，再依次按住屏幕的左上四分之一、右上四分之一、左下四分之一、右下四分之一、正中央：每次约 2 秒，松开后停约 2 秒。左右分别指宽度的 25%/75%，上下分别指高度的 25%/75%；中央为 50%/50%。只做这五次，之后不再触摸，等自动回 recovery，避免后续动作覆盖轨迹。若操作有误，记录误按顺序，不重复补一串无法对应的点。

本轮回收目录会包含 `run.json`、`checkpoints.bin` 及解码文本，读取器将输出 `touch_trace`。仅离线重读可执行：

```sh
python3 UniXNU-zorn/scripts/read-zorn-log.py \
  --block out/zorn/debug/本轮目录/checkpoints.bin --tail 100
```

出现锁屏、进入桌面、控件命中、坐标方向、多点和稳定性分别记录；若未自动回 recovery，保留主机日志后停止，不反复启动。

## 349a9231 首次上机：八核预检提前退出，触控尚未开始

2026-10-29 19:43:54 建立轮次 `20261029-194354-349a9231`，经固定 bootstrap 回 recovery 并读回 BCB，19:45:56 主镜像临时启动返回。19:46:43 自动回 recovery，run=recovered、kernel_log_changed=true，boot/kernel/读取器/归档及原始日志均已核对。

新日志为 `SMP FAIL phase=90 seen=01 bound=00 failure=261`。代码中 261 表示 CPU1 的 processor_start 返回成功后，2 秒内仍未同时观察到 Running 状态和 SGI；CPU1 MIDR/MPIDR 仍未记录。触控、显示和用户态尚未初始化，v18 明确输出 snapshot-unavailable，而非假造空的已成功轨迹。完整绑定结果保存在该 run 的 touch-trace-preflight-failure.json。

新旧 ArmCpu 源码、头文件及实际目标文件 SHA 完全相同；ar 容器 SHA 不同不足以认定对象改变。单轮失败不能确认是新诊断引起或是临时启动状态问题。现已从 recovery 临时启动完全相同的已验证旧镜像 cd6fd19f 做对照（`20261029-194854-cd6fd19f`）；未改触控映射、放宽预检或重置 Data。先前五点操作已取消，等待新轮次明确提示。

## 349a9231 复测：完整轨迹确认纵轴方向错误

旧基线 `20261029-194854-cd6fd19f` 已 recovered/fresh，八核 seen/bound/remap/timer/IPI 全 ff、Data cookie 保留、低亮度 64；机主画面为苹果标志，三次 CPU 传帧。从相同 recovery 起点重测未改动的 349a9231，`20261029-195615-349a9231` 于 20:02:53 自动回 recovery，新日志/镜像/内核/读取器/归档匹配，八核全 ff、Data 原标志及亮度保持。机主已确认锁屏。首次 SMP261 未在复测中复现，原因未定位，不能声称已修复或长期稳定。

轨迹为一致快照：810 帧解码、bad0；26 条轨迹无覆盖，六次接触全部正常抬起，单指 ID 保持；60 次 HID 报告及事件派发、61 个 digitizer 处理、累计错误 0。最大相邻矩阵采样间隔 386 ms，包含调度/读取/提交等待，不当作纯 SPI 用时。机主补充确认实际顺序为左上、右上、左下、右下、中央、中央，且前摄在上、锁屏文字正向。不能把第六次中央补按丢掉或当成随机噪声。

六次中位坐标依次约为 (40.2%,74.2%)、(66.3%,76.5%)、(36.1%,22.1%)、(71.3%,23.0%)、(52.4%,45.1%)、(52.8%,48.3%)。仅 Y 翻转的归一化 RMS 误差约 0.091，下一候选约 0.333；结合机主确认，纵轴方向已区分。横向为大致手按位置，尚不足以确定比例/偏移，不据此拟合横轴；精确控件命中也未验收。见 [六点结果](evidence/touch-coordinate-six-point-result.json)。

下一候选只移除互容 TX→HID Y 的反向换算，改为物理顶部对应较小 Y；横轴、噪声/跟踪、报告描述符、HID 解析及 provider、GPIO 节奏、八核门槛、Data 和亮度不变。新增四个电极象限的方向检查，原有真实矩阵、噪声、按住、抬起、边缘/多指 ASan/UBSan 检查通过。旧版归档保留。新镜像正在构建，尚未启动；接下来重点验收底边上滑与可见控件命中，而不是先调采样速度或强行跳过预检。

## 纵轴修正与 CPU1 启动诊断

纵轴修正版 `2d31480c`（kernel 906a0a27722508cd20672474cf1c9903c77060fdefc38de6773bdfed765c9c18）通过 123 项输入/归档核对，但 `20261029-200728-2d31480c` 和一次相同镜像复测 `20261029-201042-2d31480c` 均在触控前出现 SMP261 并自动回 recovery。未重复第三次，也未把它算作坐标修正失败或成功。

本地 XNU cpu_start 源码已清理 CpuDataEntries 与 cpu_data，匹配内核的 FlushPoC_DcacheRegion 实际包含 dc civac 和屏障；缺少该操作的假设不受证据支持，因此没有加入额外缓存修改。当前仅在 GUI 紧凑失败报告里增加失败 CPU 的 START step/PSCI rc/fail 原子读取，保留原超时、门槛和硬件操作。320 项实际报告格式的 ASan/UBSan 检查均小于 800 字节，完整八核摘要保留，成功路径格式不变。

诊断候选 `4ba3a335`（boot 4ba3a3358c7c40297c02250e467ada0d590d8753155608cf232f5045cf3d04e5，kernel 3ddfbde1c3d9d773bda7b0a38c6768d3d816698d1d73174adf1c541dbc269d14）通过相同完整核对，保留 Y 修正，已于轮次 `20261029-201627-4ba3a335` 临时启动。目前等待原看门狗自动回收；若进入锁屏，由机主测试底部上滑和可见图标命中。尚未记录这轮触控可用或桌面通过。

## 4ba3a335：点按命中已改善，手势仍待完成

`20261029-201627-4ba3a335` 已自动回 recovery，fresh log、boot/kernel/读取器/归档匹配。八核各 mask 全 ff、Data 原 cookie 保留、亮度 64、存储错误 0。829 帧解码、bad0，214 次报告及派发、217 个 digitizer 处理、87 次边缘标记，累计提交/安装/跳过错误 0。机主确认小控件点击正确，但从小白条上滑仍被识别为锁屏编辑，不将其称为解锁或桌面通过。

后段轨迹 211 条、覆盖 179 条，最初的上滑已无法从残留 32 条精确归属；后段既有短 Down/Up，也有一次因位置跳跃而换号，不能把全部短接触认定为手势断裂，因为机主还进行了其他点按。测得最大采样间隔 386 ms。保留修正 Y 与已响应点按的镜像，下一候选仅做明确的快采样节奏对照：协作从每 8 字节到每 32 字节、帧间休眠从 100 ms 到 20 ms；1 ms 协作睡眠和 GPIO 位时序不变。默认仍为旧节奏，只在八核 GUI + 轨迹开启时显式允许，非法模式和不满足前置条件均拒绝。噪声门槛、ID 跟踪及 HID 描述符/服务链不改。

下一轮只安排一次 1–2 秒上滑，之后停止触碰，保留整段轨迹；若成功到桌面，最多再点一次图标。实际速率必须用新日志测量，不能把减少等待的理论值当作已达性能。证据见 [Y 修正点按结果](evidence/touch-y-corrected-taps-result.json)。

## 42f3d518 快采样：机主首次确认解锁到桌面

快采样候选 boot `42f3d5183b67bd42b2e02ec1d193ba888d0e6c2dc4cd50dafab2211ce589583e`、kernel `824f882cf22cab37a0f6e2c83478eb30f5147a3127bdc79d0321e73227816b0f`，通过 124 项输入和完整归档核对。profile 仅显式启用 fast-poll，GPIO 位时序、命令、Y 修正、X、噪声/ID 跟踪、HID/资源链、八核门槛、Data 和亮度保持。32 字节协作/20 ms 帧间等待只在闭合的 mode1 下开启，旧 mode0 保留 8/100；CLI 和内核均拒绝缺少八核/轨迹前置的快模式。

轮次 `20261029-202921-42f3d518` 已定向临时启动。机主按本轮提示确认：从小白条缓慢上滑进入系统桌面，图标点击正常。这是基本单指解锁和可见目标点按的首次明确确认，不扩展为所有应用、多指、像素校准或长期稳定性。当前等待原有独立看门狗自动回 recovery 后核对新日志；不提前重启。



## 42f3d518 回收验收：基本单指触控已进入桌面

轮次 `20261029-202921-42f3d518` 已自动回 recovery，recovered/changed log、boot/kernel、当时读取器及完整归档一致，124 项当前输入哈希再次核对。机主确认上滑解锁进入桌面，图标点击正常。八核各 mask 全 ff、保留 Data cookie `2dde8229`、低亮度 64、存储错误 0。

一致轨迹共 31 条、无覆盖，2248 个矩阵样本、bad0；footer 显示读取 2249/解码 2248 可处于相邻字快照，不据此推断一次失败。34 次 HID 报告/派发、35 个 digitizer 处理、18 次边缘标记、提交/安装/跳过错误 0，末次 contacts0。保留了两段约 2.1 秒的同 ID 连续向上轨迹（Y 约 98.9%→57.5%、99.4%→51.1%）和一次正常抬起的点按，与机主结果相符。不要将这些记录强称为只操作一次；实际记录两段上滑。

典型移动样本约 140 ms，最大矩阵采样间隔 148 ms，旧节奏最大 386 ms；该量包含调度、读取与提交等待，不是纯 SPI 传输耗时。本轮动作数量与旧轮次不同，不能用总报告数直接比较性能。

保存基线：`out/zorn/known-good-touch-desktop-42f3d518.json`，固定镜像 `out/zorn/builds/42f3d518/boot.img`；默认 `out/zorn/boot.img` 与其相同。证据见 [桌面触控验收](evidence/touch-desktop-fast-qualified.json)。本轮结束后手机保持 recovery，不自动开启新轮次，heartbeat 继续暂停，无 Git 提交或推送，两个副本仓库不改。

当前范围是竖屏单指上滑解锁与图标目标点按。仍是 GPIO 轮询，硬件 SPI/IRQ、多指/复杂手势、像素级校准、全部应用和长期稳定性未验收。前序部分镜像曾 CPU1 预检 SMP261，原因未定位，安全自动回收与定向诊断保留；不能因本轮全八核通过而称启动可靠性已经解决。硬件 GPU 后置，当前仍是有界自动回收的测试镜像。

下次仅临时复用已验证镜像，可从共同父目录执行（本轮不再执行）：

```sh
python3 UniXNU-zorn/scripts/run-zorn-debug.py \
  --image out/zorn/builds/42f3d518/boot.img --timeout 600 --arm-recovery-bcb
```

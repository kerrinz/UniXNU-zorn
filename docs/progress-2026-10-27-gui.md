# 2026-10-27：恢复 GUI 无人值守调试

机主重新连接 K80（92988a43），fastboot product=zorn、slot=b 已核对。
直接 reboot recovery 后读回 BCB，再临时启动；本轮没有 flash、erase 或槽位修改。
继续优先系统界面，触控后置、GPU 暂停。

## 首轮恢复

`20261027-190638-07ebe68e` 已自动回 recovery，kernel_log_changed=true。
原版 watchdogd、UserEventAgent、sleepd、cfprefsd、containermanagerd_system、
coresymbolicationd、thermalmonitord 等有 exec 边界记录；BEGIN 仅表示进入，
ACTIVATE_RETURN/error=0 才表示实际镜像 activation 返回成功。
最后 340 个词没有保留完整 GUI 采样，不能据此声称采样线程已执行或系统桌面通过。

只读挂载本机原版 SystemOS 窗口（UUID 8846FE78-2910-4297-AF97-D59BB6F8FC16），
提取主 cache 与 .symbols 到忽略的 out。两者 UUID 匹配，文件 SHA256 为：

- 主 cache：354ac39e0c5ac36d9c2652c6d092ec4f3cbcdc2655879f6cc3bc16b36bc927d4
- .symbols：1126abcd7cbb76957c489ed5a1e2b7bd278b1758bb5b0ff26c32d220480f0b37

格式结构来自 Apple dyld-1125.5（d1a0f6869ece370913a3f749617e457f3b4cd7c4）的
实际 C offsetof/sizeof；没有猜测结构偏移。内核符号解析与 nm 的实际 native 函数
地址交叉核对通过。符号准备/解析只读本机镜像，不向手机增加接口。

## 保留最后诊断状态

只在 --gui-watch 启用时使用 ZORNLOG3，同一个已授权的 4096 字节日志块：
16 字节头、180 个 12 字节文本循环槽、偏移 2176 的 1344 字节固定诊断区。
固定区随已有日志提交刷新，保存采样 tick/stage/PID、VM 页计数、RAM Data I/O、
32 项显示计数、三个目标进程各最多四线程、四条原始退出状态/reason。
它不新增 UFS 写入位置；普通基线继续 ZORNLOG2。

采样改为仅寄存器，不读取用户 VM/用户栈。固定区保留最新结果，文本环绕不会覆盖。
每 15 秒、最多 12 次，采样不 pet watchdog，不暂停进程，也不改变原版鉴权或退出决定。
寄存器仍可能与运行中的线程存在竞态，truncated 会标明线程数截断。

采样 stage：1=开始进程遍历，2=选中进程，3=持有 task 引用，4=开始读取任务，
5=共享区引用已释放，6=已取 task lock，7=已解锁，8=寄存器快照已保存，
9=进程回调返回，10=遍历返回，11=标量摘要返回，12=次数上限结束。

新增 zorn-gui-log-snapshot 补丁及 XNU-only 头文件导出。正向/反向补丁、头文件
镜像、C++ 结构大小/偏移、Python 环绕解码及非法版本/线程数拒绝通过。
旧 V2 真机归档仍可读。增量构建因新增头文件和前次失败缺失 exception.o 中断，
已补齐 XNU_ONLY_EXPORTS 并按原编译记录恢复目标文件，完整构建及链接后审计随后通过；
没有把该缓存修复当作全新克隆重放通过。

`dae66d26` 8 GiB 固定诊断区候选已于 19:23 临时启动并自动回收，结果见下文。

## 主机复现入口

先准备本地固定版本格式参考（不下载 Apple 固件）：

```sh
git clone --depth 1 --branch dyld-1125.5 https://github.com/apple-oss-distributions/dyld.git out/zorn/refer/dyld-1125.5
python3 UniXNU-zorn/scripts/prepare-zorn-gui-symbols.py
# 已有符号输入可只检查：
python3 UniXNU-zorn/scripts/prepare-zorn-gui-symbols.py --check-only
```

恢复轮次和对应内核哈希必须匹配，且本轮日志确实变化，才允许解析：

```sh
python3 UniXNU-zorn/scripts/symbolicate-zorn-gui.py \
  --run out/zorn/debug/<轮次> --kernel out/zorn/builds/<镜像前缀>/kernel.macho \
  --output out/zorn/debug/<轮次>/gui-symbols.json
```

这些命令在三个仓库的共同父目录执行。符号和镜像不提交；可提交输入哈希与诊断 JSON。

## 首次真实 CPU 图形输出

`20261027-192328-dae66d26` 自动回收，新日志为 ZORNLOG3，固定区解码通过。
机主明确观察到苹果标志。显示 registered=1、clients=4、accepted=6，CPU 传输
回调共 5 次，最后一次 status=0、bytes=18432000；非黑像素采样为 41011。
这证明原版客户端到 CPU/实际屏幕路径，尚不代表系统桌面或所有传输均成功。
RAM Data reads=74/writes=582/errors=0，仍有 1668544 个空闲 4 KiB 页。
采样 tick=11/stage=11，launchd 与 backboardd 的线程记录保留下来；
SpringBoard 最近可采记录属于 tick 6，不能当作最后一刻存活状态。

固定区累计捕获 14 条关键进程退出，最后四条都为 SpringBoard：Objective-C
namespace=8/code=1 的 SIGABRT 和 signal namespace=2/code=11 的 SIGSEGV。
普通文本还保留 couldn't dlopen libobjc-trampolines.dylib / no such file。
后者与主仓库已有 native RAM Data/owner-union 研究记录的缺失路径相同。

新增独立 zorn_union_defconfig，启用上游现有 XNU_OWNER_UNION_SYSTEMOS，关闭
旧 carrier，使用已授权的原版只读 SystemOS 覆盖原版 OS 的 native union 根。
真实 UUID、只读、设备、owner 和 native union 关系仍由既有代码验证；错误即拒绝。
无新固件或二进制补丁，Data 继续使用原独立 RAM 种子。98b33744 候选已临时启动，
观察该路径是否解除缺失库错误及 SpringBoard 崩溃，尚待本轮结果。

## 只读 native union 第一轮

`20261027-193226-98b33744` 自动回收，新日志。配置和编译模式确认
XNU_OWNER_UNION_SYSTEMOS=1、旧 carrier=0。tick=8/stage=11，RAM Data
reads=71/writes=125/errors=0。仍捕获 SpringBoard SIGSEGV 和 backboardd SIGTRAP；
该轮显示客户端/传输为 0，不能把 carrier 轮次的苹果标志归因于此镜像。
原版 libobjc-trampolines 在 OS 不存在、SystemOS 存在，68080 字节，原始 SHA256
8089b4432232e56464ce724e1ef334e5b95dfc0eaa33eacc8eb2a76b669744d4 已只读核对。

为定位剩余信号退出，增加 zorn-gui-exit-detail：退出寄存器读取留在 osfmk，
BSD 仅复制经 kcdata 验证且位于已知内核 buffer 内的原因字符串。只对显式 GUI
观察模式的目标进程启用；不读取用户 VM、不修改退出决策。诊断区版本 2 扩展到
1920 字节，日志仍恰好 4096 字节；退出细节保存 PC/LR/FAR/ESR/CPSR、共享区
slide、main header、fixup 次数及最多 91 字节原因文字。新版读取器兼容版本 1。

补丁正反重放、头文件镜像、原生 C++ 字节布局、解码及旧日志兼容检查通过。
BSD 私有类型编译边界已调整到 osfmk，按原编译记录修复缺失的增量目标文件。
当前正在构建/实测扩展版本；原始 dae66d26 苹果标志候选仍保留在 builds 归档。

## 扩展诊断首轮与有界观察窗口

`20261027-194745-e84450b0` 自动回收，新日志，版本 2 的 1920 字节诊断区解码通过。
最后 tick=9/stage=11/ms=148064，RAM Data reads=71/writes=107/errors=0。
SpringBoard[5] 和 backboardd[37] 在最后采样仍存活；仅有 launchd[2] 子进程的
早期退出，未捕获本轮 GUI 退出。显示 clients=1，accepted/transfers=0。
SpringBoard 主线程等待 workloop/kevent，backboardd 主线程等待 dispatch semaphore；
普通等待状态不足以断言死锁或系统初始化完成。local-symbol 解析只给最近局部符号，
不包含全部导出符号，不能将一个较大的 symbol+offset 自动当作准确函数名。

增加单独、默认关闭的 --gui-hold-seconds 30..180，依赖 --gui-watch、mode 3 和
--early-watchdog 1。正常调度的观察线程只有在这个绝对期限之前才允许 pet；
所有原有 exec/hash pet 也仍有独立上限。该模式为有界启动观察，不冒充实际 exec
进展；定时线程卡住时也不会继续 pet。普通 --gui-watch 不选择该参数时保持不喂狗。

`20261027-200042-dbdb51e9` 选择 180 秒观察窗口、主机等待 360 秒，已自动回收。最后 tick=8/stage=11/ms=123759，RAM Data reads=71/writes=107/errors=0，显示客户端和传输仍为 0。具体复位来源未独立确认。


## 苹果标志尚不能稳定复现

机主提醒后续几次没有再看到苹果标志。随后按归档原样恢复 `dae66d26` 的
boot.img 和 inputs，`20261027-200805-dae66d26` 仍自动回收且取得新日志，
但 clients/transfers=0，并捕获 backboardd SIGSEGV、SpringBoard Objective-C abort。
因此只能记录「一次真机观察到苹果标志，CPU 显示路径有通过证据」；相同镜像也会
失败，不能将现象仅归因于 native union，更不能宣称已稳定进入系统。

`20261027-201442-2f758c0f` 回到原 carrier 目录，保留扩展退出诊断。
SpringBoard 的一条 SIGSEGV 是 PC=0；另一条 Objective-C abort 仍为缺失
libobjc-trampolines。backboardd 的 unslid PC=0x1a9443dfc，准确局部符号为
`dyld4::Atlas::ProcessSnapshot::addSharedCacheImage+0x14`，FAR=0xa0。
Apple 对应源码此处访问共享缓存对象，符合空指针方向；尚未证明根因。

## carrier 库回退和 dyld 开关对照

新增独立 `zorn_library_defconfig`：保留原 carrier，只启用主仓库已有的
`XNU_OWNER_CRYPTEX_FILES`。它将 SystemOS 的 `/private/preboot/usr/lib` 作为
DYLD_FALLBACK_LIBRARY_PATH 传给 launchd。没有拷贝或修改 Apple 库，原版鉴权继续。
新增显式 `--disable-dyld-compact-info`，保留其他 dyld_flags，清除冲突的 bit18，
设置 Apple 已有的 bit19（0x80000）调试选项；默认关闭。选项对应 Apple dyld
公开源码中的 compact process metadata 开关，不能把主机参数等同于运行时生效。

`20261027-202321-40dfe00d` 自动回收，新日志；tick=6/stage=11/ms=98579，
RAM Data reads=72/writes=96/errors=0，显示 clients/transfers=0。仍记录相同的
backboardd Atlas 空指针和 SpringBoard 缺失库 abort，另有 malloc/lock 路径 SIGSEGV。
因此该组合未解除阻塞。编译记录确认 OWNER_CRYPTEX_FILES=1；实际用户态是否采用
环境变量和 dyld 标志，需要继续诊断，不据此放宽原版加载策略。

为避免高频服务文本覆盖关键标量，新增独立 ZORNLOG4：仍写同一个 4096 字节块，
172 个 12 字节文本槽，偏移 2080 的 2016 字节 GUI 版本3固定区。保留原有线程和
退出信息，新增实际 dyld_flags、owner 发布值、fixup 解析/应用数、观察窗口、watchdog
模式、owner 阶段/挂载标志，以及首次采样对四个固定库/cache 路径的 errno/vnode 类型。
只做内核 VFS 查询，不打开用户数据、不改变查找结果；读取器兼容旧 ZORNLOG1/2/3。
新布局、旧真机日志回读、非法版本拒绝、补丁正反检查已通过；新镜像正在构建验证。


## 实际参数与标准路径结果

`20261027-203303-151de078` 的固定区确认：owner 发布 dyld_flags=0x80008，
后来实际值为 0x80009；fixups_parsed=3、applied=0，hold=180、watchdog=1。
RAM Data reads=71/writes=111/errors=0，空闲约 6.68 GiB。四路径查询中 carrier 下
标准库和标准 cache 路径均 ENOENT(2)，而两条 /private/preboot 路径均为 VREG、errno=0。
因此不能用「内存不足」或「主机没传参数」解释本轮缺失库 abort。

只读从 OS 和共享缓存分别核对实际 dyld，两者均为 dyld-1165.3。
官方对应提交 a571176e8e00c47e95b95e3156820ebec0cbd5e6 已取到忽略的 out。
此前 1125.5 仅作为 cache/symbol 格式参考，UUID 和偏移校验有效；代码行为需按实际
1165.3 复查。该源码虽然解析 disableCompactInfo，但 enableCompactInfo 没有后续消费点，
不能据此宣称运行时已关闭 Atlas。实际故障指令也已只读提取、与寄存器 FAR 对照。

`20261027-203808-c6fddc85` 同样参数改为 readonly native union，自动回收、新日志。
标准 /usr/lib/libobjc-trampolines.dylib 和 /System/.../dyld_shared_cache_arm64 均已
errno=0/VREG，/private/preboot 路径反为 ENOENT，符合挂载布局。未再捕获缺库 abort；
仍有 SpringBoard SIGSEGV，显示 clients/transfers=0。不能将路径补齐等同于系统启动成功。
最后 tick=5/ms=78693，RAM Data reads=72/writes=306/errors=0。

## ASID 清理遗漏调查

复查板级早期 zorn-local-tlbi 补丁发现两个 ASID invalidate helper 被置为空操作，
原因为早期 ASID-selective TLBI 后 DSB 卡住。跳过清理会保留重用 ASID 的旧翻译，
是当前随机空指针和相同镜像不能稳定出图的一个合理解释，尚待真机对照证明。
新增 zorn-asid-full-invalidate：两个 helper 都改用已有本地全量 `tlbi vmalle1`，
保留外层完成屏障，限当前 CPU0 范围；完整清理比原 ASID 请求更强，包含 global。
不再跳过地址翻译失效。源码补丁正反检查及提取真实 helper 的 ARM64 编译/反汇编
已确认两个调用均生成 d508871f。保持同一 union/8 GiB/观察参数的 `20261027-204242-6b816f14` 已临时启动，硬件结果待回收。
归档内核审计确认 `_flush_mmu_tlb_full_asid_async` 从 0 条变为 1 条 vmalle1，
`_pmap_switch_internal` 从 1 条变为 2 条；实际依赖记录指向修改的 tlb.h，
并非只修改源码而复用了旧目标文件。


## TLB 修正第一轮回收

`20261027-204242-6b816f14` 自动回 recovery 并取得新日志。SpringBoard[5] 在
第 12 次（约 183 秒）仍存活，未捕获 SpringBoard/backboardd 退出；唯一退出是
早期 launchd[2] 子进程。标准库/cache 路径仍为 VREG、errno=0；RAM Data
reads=69/writes=29/errors=0、空闲 1810029 页。display clients/transfers=0，
没有桌面通过证据。此轮比上一轮少了异常退出，但单次结果不能证明完全解决随机故障。
SpringBoard 主线程等待 IPC receive，未采到 backboardd。正常 IPC/工作线程等待本身
不等于死锁，需要进一步确认服务启动和请求去向。

机主要求重试观察，已按相同 boot.img/inputs 启动 `20261027-205229-6b816f14`，
未将新源码改动混入本次重试。下一候选另行增加 RAM 中的 IPC 请求标量和有界进程
目录：只保留三个目标各两次送出尝试，记录 msg id/receiver PID/header bits，
不读取用户消息正文、不改发送/接收结果。仅由原定时观察线程将缓存打印到同一日志块；
IPC 路径不做 UFS I/O。编译和硬件结果尚待验证。


原版只读目录审计：OS 含 523 份 LaunchDaemons plist，SpringBoard、backboardd、
logd、runningboardd 的原版条目均存在，前两者均 RunAtLoad；SystemOS 没有该目录。
这仅证明原版输入，尚不替代目标机 union 下的枚举/启动结果。
IPC 候选 `fa750519` 的完整增量构建、链接后 ABI 检查和打包通过，尚未启动。
后续构建清单将 compact-info 字段命名改为 disable_requested，避免把参数请求误写成
已关闭运行时功能；旧清单的 disabled 字段也仅表示当时传入了该请求。


同镜像重试 `20261027-205229-6b816f14` 自动回收、新日志；tick=6/ms=98649，
显示 clients=4，但 accepted/transfers=0。仍未捕获 GUI 进程退出；原版用户服务
继续到 mobilerepaird[139] 等。因仍未传帧，不能据四个客户端推断苹果标志或桌面。
旧的锁诊断词 LC2/LD2/LV2/LW2 留在文本结尾，具体停止原因仍需上下文。
已转入 `fa750519` IPC 观察轮次，原版磁盘输入和同块日志/BCB 写入范围不变。


机主确认前一轮重试未出现苹果标志，与 accepted/transfers=0 一致。
`20261027-205646-fa750519` 自动回收、新日志，tick=6/ms=95734，
SpringBoard/backboardd/launchd 均有线程快照，未捕获 GUI 退出。
RAM Data reads=74/writes=625/errors=0，display clients=5、transfers=0。
高频原版服务输出覆盖了所有 IPC/进程目录文本，不能由文本缺失断言观察钩子未执行。

将六条 RAM 中 IPC 尝试也保存在固定区：ZORNLOG5 使用 162 个文本槽，固定区
位于 1960、GUI 版本4长2136字节，仍恰好同一个4096字节块。保留全部旧字段，
每个目标各两条 sequence/PID/message/receiver-PID/bits 标量，无消息正文和裸指针。
读取器保留旧1/2/3/4兼容；真实旧日志、环绕、非法PID拒绝和C++字节布局通过。
新轮次移除没有实际消费点的 compact-info 请求，其余 union/8GiB/TLB修正保持。


`20261027-210305-dcc32d90` 自动回收，新日志，ZORNLOG5 固定区解码通过。
RAM Data reads=74/writes=833/errors=0，display clients=4/transfers=0，未捕获GUI退出。
IPC 数组仍全空。核对实际编译记录/内核指令发现 ipc_kmsg.o 未传入文件级
XNU_NATIVE_LEGACY_DISPLAY，钩子被编译掉；此前仅检查回调符号存在不足以发现此遗漏。
已承认并修正构建接线，不把空数组解释为没有 IPC 活动。

新增 CLI overlay 0003，按显示模式设置 ipc_kmsg.o_CFLAGS_ADD，并在模式变化时
清理对应增量目标。新增 audit-zorn-gui-hook.py，GUI 构建必须同时通过实际编译参数
及 ipc_kmsg_send 到 enabled/recorder/原版 receiver accessor 三个实际 BL 目标检查，
否则在打包/USB 之前拒绝。旧空钩子镜像负例已拒绝；新候选重新构建中。


## IPC 观察实际接通

首次启用编译时 osfmk/BSD 头的 typedef 冲突已修复：使用已核对的精确函数声明，
不把 sys/proc.h 引入 ipc_kmsg。实际编译记录恢复后完整构建通过，内核调用审计通过。
`20261027-211402-9be788f2` 自动回收，新日志。固定区首次保留有效 IPC：
SpringBoard[5] 最后向 PID99 发送 0x20000000 和69；backboardd[37] 最后发送
2881 到 kernel receiver、70 到PID75。发送尝试不等同于送达或回复。
2881 经当前生成的 MIG server 确认为 io_service_get_matching_services_bin。
RAM Data reads=71/writes=301/errors=0，display clients=3/transfers=0，未捕获GUI退出。

原版 cache 导出 trie 补充确认：backboardd 采到 nanosleep+216 / __semwait_signal+8，
SpringBoard 采到 mach_msg2_trap+8 / mach_msg2_internal+76；pthread 工作线程为
_pthread_wqthread。此前较远的局部符号不能用于给这些等待命名。

新增 zorn-gui-service-observer：接收方 PID 经安全 proc_name 查询保留15字节名称；
IOKit 在原匹配字典仍有效时只读 IOProviderClass，记录原 status 和返回 iterator 是否非空。
不遍历或消耗原 iterator；iterator 非空不代表有匹配对象。最多三个目标各保留一条查询。
ZORNLOG6 为140文本槽、偏移1696的2400字节GUI版本5固定区，日志仍恰好同一4096字节。
旧格式兼容、布局和非法标志拒绝通过。构建审计另验证真实 IOKit API→内部函数→观察器→
记录函数的调用链和对应编译参数。`20261027-212708-8f96ce91` 已自动回收，结果见下节。


## 官网流程复核后的状态

8f96ce91 已自动回 recovery，新日志。固定诊断区显示 backboardd 的最后匹配类为
IOAcceleratorES，原 status=0、iterator_present=false；显示 clients=4、accepted/transfers=0。
RAM Data reads=74/writes=800/errors=0，未捕获 GUI 退出。SpringBoard 的最后通信接收方
为 notifyd；前一轮 PID99 不能跨轮次当作同一个服务身份。

机主要求按官网重新梳理，已停止新增试启动，完成配置/补丁/平台/存储/显示与OS依赖核对。
具体差异、已验证范围和后续次序见 [官网流程复核](review-2026-10-27-official-porting.md)。
未更换 OS、迁移配置格式或重置当前缓存；当前镜像与输入仍保留。


## 21:57：CPU 渲染路线和 sRGB 对照

官网 QEMU 设备页明确说明：未启用 Metal 时，原版 QuartzCore 可以使用 CPU 渲染器。
只读下载 xVanTuring/UniXNU-qemu 固定提交 97b75b1f63c6b7e895cd7646029db741d5fe5488
的配置/板级 probe 作比较，未执行下载脚本。sheng 的 ADT 已将 artwork-display-gamut
设为 sRGB，并说明 P3 的部分 CoreGraphics 绘制需要 GPU。zorn 由 P3 改为 sRGB，
保持内核、只读 union、8 GiB、512 MiB RAM Data 和 watchdog 条件。

2742649e（20261027-215301）已自动回 recovery，kernel_log_changed=true；
记录 tick8、145341 ms，显示 clients=5、accepted=2、transfer callbacks=2、
最后返回0、每次完整帧18432000字节，记录到非黑像素。仅最后一次返回值被保存；
没有捕获 GUI 退出。机主随后确认本轮出现苹果标志；尚未进入系统，也不能称为两次传帧均成功。
这次改善仍需重试，不能把单轮差异全部归因于色域。

下一试验接入官方 AppleKeyStoreState（42ff83e08b2265fe741d4adaf084bebe003452ba），
QEMU 的同版本 OS 记录显示，缺少它会使 liveactivitiesd/chronod/SpringBoard 等待。
板级生命周期仅在 ephemeral-storage=1、显式 --keystore-state、RAM Data 配置下启用；
保留官方 selector 处理，未知操作返回错误，不生成密钥/密码/持久 keybag，也不提供 SEP。
该组件的实际源文件已通过既有 closed-boundary 主机检查，实际 XNU ABI 编译已通过；
此时尚未进行新接口的真机启动。GPU 硬件和触控继续后置。


## 22:03：临时 Data 的 AppleKeyStoreState 首轮

9198bf8e / 20261027-215829 已自动回 recovery，机主确认仍为苹果标志。
显示 clients=5、accepted=5、transfer callbacks=5，最后一次返回0、18432000字节；
没有捕获 GUI 退出。RAM Data reads=75/writes=1641/errors=0，tick8/162130ms。
backboardd 最后完成的匹配为 AppleHPMDevice，status0、iterator为空。
不能据此认定 AppleHPMDevice 是唯一阻塞项。SpringBoard IPC 已到 bluetoothd。
原版组件、启用边界和实际内核调用链检查通过；服务初始化/调用的早期文本可能被覆盖，
下一轮增加周期性的 AKS stage/status/opens/calls/refused/last/result，只用既有日志块。

保持相同功能配置，启用300秒的有界观察窗口，最长12次采样，间隔从15秒调为25秒；
只有成功调度的观察线程在绝对截止前喂狗，超时回收仍在。原有180秒和更短窗口不变。
对应追加补丁为53z-zorn-gui-long-window，保留所有旧轮次、旧ABI解码和镜像。

另准备显式 --shared-data-volume 候选，向原版APFS传 -apfs_shared_datavolume，
按 QEMU 同版本配置描述单一RAM Data布局。没有Data seed时拒绝打包；此时尚未启动该候选。
该选项不改变分区、Data容量、原版系统文件、密钥或卷授权。


## 长窗口首试未跑满，追加固定状态快照

a8cf0aa0 / 20261027-220705 于22:10:38自动回 recovery。实际最后tick4/116188ms，
显示clients=4、accepted/transfers=0，未捕获GUI退出，backboardd最后查询IOAcceleratorES，
status0/iterator为空。配置记录hold=300，但未完成300秒观察，不能把它算成长时间稳定运行。
复位的具体触发源尚无证据，不能只凭回到recovery断言是某个watchdog。
AKS早期文本已被覆盖，故此轮不能单独证明状态服务是否发布/被调用。

54z-zorn-gui-keystore-state 恢复15秒采样间隔，将最多次数扩展为20，
绝对喂狗截止仍为300秒；同时给同一个4KiB块追加48字节固定状态：
stage/status/opens/calls/refused/last selector+result。新格式ZORNLOG7为136个12字节文本slot，
footer偏移1648、GUI版本6/2448字节；总计仍4096字节，没有新增UFS写入位置。
实际C++布局/环形跨界往返、错误版本/尺寸/超界tick拒绝、83份历史真机日志解码、
XNU/原生头文件一致、补丁前像dry-run均通过。新格式真机结果待后续轮次。


## 22:21：状态服务实际通过，诊断遍历等待已定位

90d98df3（显式共享Data）自动回收；accepted/transfers=1，最后返回0；最后tick5/stage9。
98ba0dd0（ZORNLOG7固定状态）也自动回收，最后tick5/87196ms；
AppleKeyStoreState stage3/status0/opens17/calls52/refused0，last selector7/result0。
这证明实际发布和状态调用，不代表52次调用全部成功；组件不支持的操作仍返回错误。
该轮显示clients3、accepted/transfers0，未捕获GUI退出。

检查XNU原始proc_iterate实现发现：没有PROC_NOWAITTRANS时，它会在调用每个callback前
执行proc_transwait，连不属于目标GUI进程的exec转换也会等待。当前观察器为进程清单
遍历所有服务，因而可能先于OS完成而停住，并使依赖该观察器的喂狗停止。
这是一项已定位的诊断问题，不能把全部提前回收解释为OS死锁。

55z-zorn-gui-no-transition-wait仅修改诊断调用选项：ALLPROCLIST|NOWAITTRANS=5，
并跳过正在转换的目标；原版proc_iterate和exec转换处理不变。
补丁前像检查和实际5bb42709内核反汇编已确认调用flags=5；该轮真机结果待回收。


## 22:29：诊断遍历修正版完成20次采样

5bb42709 / 20261027-222237 于22:29:23自动回收，最后tick20/ms312203，
已覆盖300秒观察窗口。显示clients/accepted/transfers均0，机主确认色条；
仅73个进程，许多仍为xpcproxy，GUI固定快照中有launchd和SpringBoard，没有backboardd。
AKS stage3/status0，但只有opens1/calls1、last0/result0；RAM Data无错误。
这证明观察器等待修正有效，同时说明完整观察也不能保证OS继续初始化。

新增显式 --quiet-gui 对照：保留固定快照、IPC/退出原因和真实exec进度的有界喂狗，
跳过用户write缓冲copyin和逐次exec文本；只减少观察开销，不改系统操作/返回。
接着准备56z-zorn-voucher-lock-restore，单独恢复原版thread_set_mach_voucher
的线程互斥锁与started/voucher同步。旧绕过补丁仍保留为历史，追加补丁恢复其语义；
前像应用后可重新应用原无锁补丁，确认这是针对原变更的逆向修正。运行结果待后续轮次。


## 22:38：低日志开销对照仍未出图

b527527d / 20261027-223104 自动回收，tick20/ms308799；
显示clients3、accepted/transfers0，未捕获GUI退出；
AKS stage3/status0/opens15/calls43/refused0、last7/result0。
backboardd最后匹配IOAcceleratorES，status0/iterator为空。
因此日志采集不是该轮未出图的唯一原因，不能据此认定不存在其他时间开销。

2318ec0c隔离恢复voucher锁：最终内核反汇编中thread_set_mach_voucher
从0次mutex lock/unlock恢复为1次lock、2处unlock，原版started检查也在锁内。
本轮尚在运行。HID基础服务加载适配已通过实际XNU ABI编译，尚未真机启用；
它只加载原版IOHIDFamily/IOHIDEventDriver并核实IOHIDResource，不创建HID设备或触控事件。


## 22:50：恢复原版同步机制，保留单项对照

2318ec0c（恢复voucher线程mutex）自动回收；最后tick9/139572ms，
显示clients5、accepted/transfers5、最后返回0；AKS opens44/calls192/last7=result0。
该轮已越过早期用户态/显示初始化，不能再把原版voucher锁描述为必然卡住。
仍未稳定进入系统；也未捕获GUI退出。

a9e61971（另恢复VNOP_READ）自动回收；最后tick9/143477ms，
显示clients5、accepted/transfers5、最后返回0；AKS opens37/calls161/last7=result0。
backboardd最后查询IOAccessoryManager，status0/iterator为空。
恢复后的VNOP_READ与XNU d8b80295118ef25ac3a784134bcf95cd8e88109f原函数逐字一致；
二进制保留原间接vnode分派，已无zorn_say调用。全局zorn_read_trace不再于文件读取时置1，
条件性强行改锁不再由正常读取激活。尚不等于所有旧同步绕过都已清理。

58z-zorn-pmap-lock-init-restore恢复pmap_lock_init(p)，匹配现存的原版
pmap_lock_destroy；此前noref初始化不增加锁组引用，销毁却仍释放，存在账目不配对风险。
该候选1f0bc21c正在真机观察。

59z-zorn-rwlock-semantics-restore恢复lock_rw.c与pmap_internal.h；
两份最终源码均与固定原版XNU逐字一致（通过逆旧补丁和git原版双重比对）。
移除强行写interlock/锁字、无视抢占回调、删除前置断言等旧改动，去除已无调用的noref函数。
原版pmap初始化保留；最终构建/真机结果另记。MAC重入等其他历史改动仍未清理，
不能称为完整平台或SMP资格验证。所有历史镜像/证据保留，GPU硬件与触控继续后置。


## 完整读写锁恢复未通过早期启动；转回可取证基线

1f0bc21c（原版pmap_lock_init）自动回收，已进入launchd/显示客户端，
但最后tick9/135323ms，clients4、accepted/transfers0；AKS opens27/calls120。
58206852（59z完整原版读写锁 + 60z关键服务退出观察）于22:58:21启动、22:59:58回收，
kernel_log_changed=false。没有生成新日志，不能把旧日志中的阶段/帧数归给该镜像。
尚未定位具体早期断言/复位源，完整读写锁恢复不能称为通过。

61z恢复到59z之前的两份锁文件，用于继续GUI取证；原版voucher、VNOP_READ和
pmap_lock_init恢复保留。旧RW抢占等遗留仍待早期日志定位，MAC等历史改动也仍存在。

## 23:17：实际接入官方服务裁剪

机主指出CoreLocation等未裁剪；此前zorn确实未接入这套策略。官方
https://unixnu.com/zh/guide/skip-setup 给出sheng-disable-jobs，
本地UniXNU-sheng/package/BootWatchdogPolicy.c还记录了location/identity/蜂窝/蓝牙
同步XPC等待链。zorn在保留原版框架文件、GPU/触控后置的前提下，先对上述四个job
加上缺少对应用户态后端的watchdogd做临时禁用；内核Gunyah回收watchdog保留。

原始kern_exec调用受XNU_BOOT_PROGRESS限制而在zorn编译掉；新增核心overlay0004
及62z，实际构建记录XNU_ZORN_STARTUP_POLICY=1。只在Ram Data成功挂载/读写探针通过后，
原版launchd执行前调用策略。正常syscall创建disabled.plist、fchown/fchmod/fsync/stat，
重新打开逐字读回，并创建disabled.migrated。仅写入易失RAM Data。
ZORNLOG8/GUI版本7固定保存真实status、uid/gid/mode/bytes，同一4KiB日志块不变。

8a7d0021已构建并于23:17左右临时启动。真实调用链、编译flag、文件校验调用均已审计；
不带hook的旧内核负例拒绝。实际C ABI编译、元数据往返/错误版本与边界拒绝、
91份历史日志解码通过。此时真机策略状态和服务裁剪效果仍待本轮回收，不能称为已进入系统。


## 23:24：服务策略真实写入/读回通过，仍为色条

8a7d0021 自动回recovery；固定startup_policy recorded=true、status0、uid0/gid0、
mode0100644、bytes380。已通过fsync/stat及重新打开逐字读回，策略文件元数据满足原版loader要求；
未直接观察launchd内部每个job的disabled状态，不能仅凭文件状态宣称所有job均已停用。
机主确认色条，clients4、accepted/transfers0，未捕获所选关键服务退出。
最后tick6/97554ms；后续固定IPC seq已到25202（其中backboardd4807待对照MIG定义），
SpringBoard最后接收方为sharingd。RAM Data无错误。

## 23:33：接入官方skip-Setup/no-auto-dim Data副本

只读检查确认原Data种子没有com.apple.springboard.plist；按官网工具
UniXNU/scripts/seed-data-skip-setup.py --no-auto-dim 对独立副本合并5个偏好plist。
只读重新挂载核实UUID仍C7D77FF3-6437-4C4A-8E05-E8E239AC1641，5个文件uid501、mode0600，
Setup完成/版本21H461及三个禁息屏键值正确。没有创建激活记录、用户或密钥。
原512MiB种子哈希未变；派生种子编码1142880字节，逻辑SHA fa0174317c0f3d4a3b566341f0b421f13e35627b25e28f7de3a51b45ea5e4bd5。

--skip-setup显式选择独立report，默认仍为原种子。新增实际内核常量审计，逐项核对
_zorn_data_expected_seed/uuid/bytes与选定Data报告，保证加载器和RamBlock选的是同一副本。
51bd1146已通过构建/实际policy调用/种子常量审计；真机效果待回收。


## 2026-10-27 23:42 至 10-28 00:02：再次确认苹果标志；完整服务预设对照

`af82587b` 加载原版 IOHIDFamily/IOHIDEventDriver（HID stage3、两个加载返回0、
IOHIDResource=1），没有创建触控设备或合成输入。机主在该轮运行中确认：色条较久后出现苹果标志。
这轮自动回收且有新日志，tick20/317730ms；显示 clients5、accepted5、transfers5，
最后状态0、帧18432000字节；该统计不保存每次传输结果，不能称所有五次都成功。
KeyStore stage3/status0/opens56/calls226；RAM Data reads79/writes4552/errors0。
没有捕获所选关键 GUI 服务退出，尚无欢迎页/桌面。证据：
[evidence/gui-desktop-hid-apple-state.json](evidence/gui-desktop-hid-apple-state.json)。

`b1137cba` 仅切换为上游完整 sheng-lite 服务预设（22个label，含watchdogd），
23:55:53启动，00:02:35自动回收，新日志。策略status0、uid/gid0、mode0100644、1083字节，
fsync/stat/重新打开逐字读回均通过。tick20/307879ms、accepted3、transfers2、最后状态0；
RAM Data reads79/writes729/errors0。该轮没有绑定到它的机主屏幕观察，不称已进入系统。
IPC最后一两条发送不等于正在等待对应服务；尤其bits0x12是send-once类型，可能为回复。
不再据此把maild或PerfPowerServices当成已证实的阻塞者。

## 2026-10-28：用户栈取证与独立 SMP 候选

新增显式 `--gui-user-stacks`，保留CPU0与既有写入边界。GUI观察线程先保存寄存器、
释放task锁，再引用目标map并通过原版vm_map_read_user读取首个符合条件线程的frame chain。
最多16层，每次16字节、16字节对齐、限制在SP上方1MiB内，链必须前进；保留真实VM错误，
不把未读到的地址伪造为成功。它可能缺页，受既有独立watchdog的有限回收窗口保护。
这是运行任务的尽力采样，不是冻结所有线程的原子stackshot。

ZORNLOG9/footer v8：98文本槽、offset1192、footer2904字节，合计仍4096；
旧字段偏移相对于footer不变，追加三份带pid/tick的16帧记录。旧样本不会被附到新tick的寄存器。
C ABI与指针边界、4个错误元数据负例、95份历史日志解码通过；旧内核缺少实际VM调用的负例被拒绝。
最终内核实际map引用/读取/释放/记录调用均审计通过。
`ffd39fb4` 已生成并于00:14:09临时启动，真机读取结果待本轮回收。

多核按机主要求同步准备，但不抢先改变GUI基线。实机live.dtb SHA
8a8e5a0b8954bb71d1451e71b388e96a7d1d985828b6dd3ff789fcd504ae6ac7：
8个reg为0到0x700、PSCI smc，首两核相同capacity；真实pmap预处理为MAX_CPUS8/MAX_CPU_CLUSTERS1。
UFS命令及共享DMA缓冲区有gHost.lock；日志gLogBusy仍有非原子生产者，运行时TLBI仍只针对CPU0，
旧同步绕过也未全部消除。以上都尚未通过SMP资格验证。

实际 `af82587b` 的 ArmCpu::signalCPU 只有DSB，没有ICC_SGI1R_EL1写入：
Darwin汇编器将分号后的指令视为注释。原版ArmCpu的17处汇编串在独立副本中改为换行，
生成真实ARM64对象并核实DSB/SGI/ISB顺序及PSCI SMC；旧内核缺SGI为负例。
两核ADT只添加CPU1(reg0x100)和PSCI，移除这两项后逐字还原苹果标志基线。
`native/smp` 与 prepare-zorn-smp.py 保存完整来源/步骤，未改上游检出、默认板级配置或本轮镜像。
当前XNU在BCM2837条件下的reset vector已保留Affinity1；未套用houji的Darwin22启动入口。
尚无真机多核启动或提速结论；跨核TLB、日志原子性与逐核定时器/IPI预检仍待完成。


## 00:21：用户栈真机读取通过，定位 LaunchServices 同步等待

`ffd39fb4` 于00:20:44自动回收，有新日志；机主明确确认该轮苹果标志。
最终tick20/stage12/317294ms，显示accepted5/transfers5，最后状态0，尚无桌面。
launchd读取1帧/error0，SpringBoard读取16帧/error0，backboardd读取7帧后error1。
采样错误仅记录真实值，没有改变目标任务的执行或VM读取返回。

SpringBoard主线程的实际返回地址落在libdispatch同步等待、Foundation
`__NSXPCCONNECTION_IS_WAITING_FOR_A_SYNCHRONOUS_REPLY__`、CoreServices
`_LSCopyServerStore`/`LaunchServices::Database::Context::_get`、
`LSApplicationRecord initWithBundleIdentifier:fetchingPlaceholder:error:`、
ControlCenterServices的模块可用性查询。证据来自同tick用户栈，强于此前末尾IPC猜测；
只能说明采样时的等待链，还未识别服务端实际卡点。backboardd主线程位于CFRunLoop的Mach端口等待。
底层系统库有些nearest-local-symbol距离较远，不按这些误认函数；CoreServices具名帧为本轮重点。

下一轮显式 `--gui-launchservices` 将进程/栈槽0从launchd换为lsd，
保留SpringBoard/backboardd和原有launchd IPC槽；ZORNLOG9/footer版本9、字节数和物理写区不变。
新增lsd退出观察，仅记录，不禁用或修改LaunchServices。
C/解码往返、旧96份历史日志与旧/新进程槽身份校验通过；真机结果另记。


## 00:35：lsd 主线程在安装进度日志恢复队列等待

`0959f393` 已自动回收，新日志、tick20/stage12/316692ms；机主确认该轮苹果标志。
lsd[69] 首线程9帧后error1：`_LSInstallProgressService performJournalRecovery` →
libdispatch同步队列等待；SpringBoard仍在同样的_LSCopyServerStore同步XPC链。
backboardd主线程仍为CFRunLoop；显示accepted5/transfers5，最后状态0，RAM Data无错误。
这定位了主线程等待，但没有取得lsd全部工作线程的栈，不能直接认定是网络身份问题。

对照本地houji的migration-upstream-research.md及固定Ace5原始实测JSON，
其iOS16中lsd曾在MobileGestalt等待IONetworkController；补/chosen/mac-address-wifi0后该等待消失，
仍未完成迁移。zorn的当前ADT也缺该属性。新增显式--development-wifi-identity，
从专用开发命名空间及K80序号生成6字节本地管理单播地址，非硬件MAC、非Wi-Fi驱动。
检查移除该属性后逐字还原0959f393的ADT，七个无效/冲突地址负例被拒绝，默认关闭时不变。
准备单变量试验，效果须由zorn自身日志验证；未复制参考机的userdata或写盘做法。

多核独立候选另修正一处诊断汇编的输入/输出操作数编号，重新生成并检查对象；
仍未装入本轮内核或改变CPU0默认配置。固定来源和候选哈希见native/smp/origin.json及镜像外证据。


## 严格设备树对照：47d67736

最初重建的7d68461f内核带有新的UUID、调试对象mtime和PrelinkKCID；后续652e0365的
新属性顺序与独立预期不同。两份都未在手机启动，均被单变量核对挡住，未算真机结果。
最终47d67736直接复用0959f393归档内核，真实SHA仍
eeed35f259f9257f61c513f9747ccec07d6336f1bfbec5f7def5610de95fe676。
固件、RAM Data、启动参数逐字一致，ADT SHA
65622077e7e130e916b4b354057c2c334a7dbb9e85eedb15d3d20612a3fe37d5；
仅新增/chosen/mac-address-wifi0=5e:20:0b:8a:04:21（开发地址，非出厂MAC）。
具体打包证明见evidence/wifi-identity-packaging-proof.json。

旧归档未保存预链接描述。重新从固定原始cache及现存native布局生成审计描述，
逐一核对所有原版组件extent与0959f393实际字节一致，并明确标记为reconstructed-layout，
不是伪称找回旧原始报告。实际AES/IOStorage/RamBlock/显示ABI与GUI/VM/policy/seed审计再次通过。
后续正常归档会同时保存kernel-plan.json及其哈希，--reuse-kernel-control仅允许此类
开发Wi-Fi对照，要求其他profile选项一致，并核对归档镜像、内核与审计描述身份。
47d67736已交给既有单块日志/BCB的自动回收流程，真机效果仍待观察。


## 00:56 至 01:04：网络身份未解阻；发现并准备修正 RAM Data 数字属主

47d67736自动回收，有新日志，tick20/stage12/317313ms，机主确认仍为苹果标志。
lsd和SpringBoard的主线程等待链均未变化，accepted5/transfers5，不能称网络身份属性修复了当前卡点。
随后机主要求完全无人值守：继续自行分析日志；若必须人工看画面/操作，则先回recovery并暂停。
不再要求实时屏幕反馈。摄像头工具尚不可用，必要时再检查本机可用采集途径。

只读挂载原OS及RAM Data，明确启用owners on，发现Data根、db、containers等均501:20，
而原OS的/private/var与db是0:0，mobile为501:501；源passwd中_installd为33:33。
此前prepare-zorn-data.py用owners-off复制，已标记ownership_preserved=false，但尚未补齐数字元数据。
这是一项实际初始化遗漏，尚未证明就是LaunchServices卡点。

宿主机没有免交互sudo凭据，改在已验证的易失RAM Data副本中，通过原版fchown/fchmod恢复现有路径。
从两份只读镜像生成232条固定清单（188目录、44普通文件），不处理符号链接，不创建文件或改内容。
先核对路径类型与同一Data设备号，再设置uid/gid/mode并fstat读回；失败保留错误并停止launchd启动。
仅显式--data-permissions启用，须GUI/临时服务策略/skip-Setup与新内核，守卫仍要求真实Data探针7/0、
非持久后端、已武装日志与watchdog。默认关闭，OS/SystemOS及宿主种子不改。

65z允许选择lsd工作线程窗口，保留真实原始线程编号；66z为固定权限结果扩展日志。
新ZORNLOGA/footer v11：96文本槽、offset1168、2928字节footer，总计仍4096。
追加真实阶段、errno、已核对/总条目数和Data根uid/gid。旧1..9格式与v8/v9/v10仍解码。
C ABI/往返、线程编号/错误元数据负例及98份历史日志通过；完整构建与真机结果待续。


## 01:12 权限实测与 04:13 无人值守续调

50081fc9于01:12:08自动回收，新日志。Data metadata stage3/error0，232/232全部核对，
根uid/gid0:0；说明真实fchown/fchmod和fstat读回通过，宿主种子及OS输入未改。
仍未得到桌面证据；显示accepted5/transfers5，最后状态0，RAM Data errors0。
lsd原始线程编号3的10帧栈显示`LSInstallProgressService restoreInactiveInstalls`等待dispatch group；
SpringBoard仍等_LSCopyServerStore，故不能将数字属主修正宣称为已解阻。
线程编号是本次采样的ordinal，不保证跨启动固定身份。

机主追加05:00关机要求后，曾准备本机一次性收尾任务并验证同执行环境AppleEvents权限。
04:12机主取消关机；任务已bootout且查询确认不存在，配置标为cancelled并改名停用，
截止guard已解除，原任务的caffeinate已释放。没有待执行的05:00关机请求。
继续真正无人值守；单独active-debug保活任务只防空闲睡眠，不修改电源设置或关机，暂停时卸载。
run-zorn-debug的每轮也用caffeinate -w绑定自身PID，防止测试期间宿主空闲睡眠。

04:18临时启动650308ad，保持已验证的权限恢复与其余参数，仅把lsd采样窗口前移至ordinal7。
USB摄像头0可取单帧、没有音频，但当前画面不能可靠识别K80，不将其当作桌面确认。
若必须人工查看或物理操作，按机主要求先回recovery并暂停。


## 04:24：线程窗口回收及有限长观察

650308ad 已于04:24:19自动回recovery，新日志身份匹配；tick20/stage12/317368ms。
Data权限仍232/232、root0:0，RAM Data读83/写2166/errors0；显示accepted5/transfers5、最后状态0。
最终lsd记录的ordinal7窗口为空；旧tick16的一帧没有冒充tick20的新栈。
SpringBoard仍在同步_LSCopyServerStore等待，backboardd在CFRunLoop。
没有新的屏幕确认，也不能据此宣称进入桌面。证据见gui-lsd-worker7-*。

只读按原版21H461/SystemOS UUID与实际cache映射提取少量具名方法。
restoreInactiveInstalls先调用_LSDatabaseGetSeedingGroup，再无限dispatch_group_wait；
此前50081fc9的返回地址位于此处。说明安装恢复尚在等数据库播种，不证明网络、磁盘或某个
IPC接收方就是根因。原版文件与执行逻辑均未改，分析二进制仅放忽略的out。

67z增加显式30..900秒的有限GUI观察；每15秒最多60次，达到绝对期限不再pet watchdog。
若观察线程卡住仍由独立watchdog回收，不改成无期限等待。
68z把lsd加入现有IPC/IOKit预过滤，选择LaunchServices profile时槽0的两项也采lsd；
未选时仍launchd。仅RAM标量观察，不消费原版IOKit iterator，不改IPC或匹配返回。
ZORNLOGA/footer v13仍为offset1168/2928字节、96文本槽和同一个4KiB物理块；
v11/12的旧IPC槽保持按launchd解码。C ABI、身份往返、60/61次边界和100份历史日志通过。

cf7c7a70已完成所有构建/真实调用/存储和显示ABI审计，于04:27:11通过既有回收脚本临时启动。
显式观察900秒，主机最多等1140秒，lsd采样从ordinal0开始。长期初始化是否继续推进，
以及v13的设备实测结果，仍须本轮新日志判断。05:00关机保持取消。

USB摄像头在普通沙盒中不枚举；按已授权的相机权限采集单帧成功、无音频，但画面很暗，
不能确认K80屏幕。没有借此宣称苹果标志或桌面；继续以日志分析为主。


## 04:34 起：摄像头可辨认苹果标志，补只读 Data 容量诊断

cf7c7a70运行中，USB摄像头0等待两秒曝光后取得单帧，实际可见苹果标志；
同机位recovery帧没有该标志。房间很暗、手机边框不可辨，未见欢迎页/桌面。
不启用音频或其他摄像头。截图留在忽略的out，元数据见gui-long-camera-apple.json。

69z准备ZORNLOGB/footer v14：92文本槽，offset1120，2976字节footer，仍恰好4096字节。
仅在已验证RAM Data/独立watchdog守卫下，定时从/private/var的独立挂载读取原版vfs_getattr；
记录真实errno、支持位、块大小/总块/可用块和实际APFS UUID，不调用setattr或文件写操作。
这样才能区分APFS空间耗尽与块传输错误，不能用RamBlock errors0排除ENOSPC。
C布局/新旧往返、UUID、三个容量负例与100份历史记录通过；实际内核已验证观察线程
到helper以及vnode_lookup/getattr/put、守卫、记录器的真实调用，且没有文件系统变更调用。
f32bac92是已完成构建审计但未在手机启动的初始候选；随后改采ordinal1并恢复300秒窗口，
以读取此前未展开的lsd锁等待栈，真机证据待后续新日志。

原版缓存导出符号补充还纠正了一处nearest-local误标：0959f393的0x187da4bcc实际是
导出_LSServerMain+2920，而非前一个CleanEphemeral block；performJournalRecovery具名帧不变。
补充文件必须匹配原版OS、SystemOS UUID与缓存SHA，身份错误负例会在输出前拒绝。
旧报告保留，修正版单独保存gui-symbols-exports.json；未改原版函数或绕过数据库播种。


## 04:43：长观察取得新的用户态阶段

cf7c7a70于04:43:46自动回recovery，原始日志确有变化。最终tick59/stage11/886345ms，
并未完整记录60次；watchdog与回收没有被取消。显示accepted7/transfers6、最后状态0，
Data权限232/232/root0:0，RAM读128/写8094/errors0，原版profile fixups parsed3/applied1。
两次摄像头采样（04:34、04:42）均为苹果标志，没有桌面。

SpringBoard实际16帧已不在_LSCopyServerStore：进入MediaRemote的
MRGroupSessionRequestManager sharedManager及libsystem_featureflags的
_os_feature_enabled_load/SLOWPATH。末尾用户PC 0x1cb78631c，按原版系统库文本哈希核对指令，
此前mov x16,#5/svc#0x80，确为open系统调用的返回地址；线程state0x9，为WAIT|UNINT，
continuation0。单次快照不足以证明这里持续卡死，但需要内核栈判断所等的内核资源。

lsd主线程也越过performJournalRecovery，已在beginListening的XPC endpoint初始化中。
本轮没有记录lsd IOKit匹配，不能将参考机IONetworkController等待认作本机根因。
最后IPC到chronod等仅作调用历史，不单独当作当前等待对象。
较长窗口观测到了后续初始化阶段，不代表仅延时就能保证进入桌面。

38dd08b2于04:45:55临时启动，保持900秒观察，新增v14 Data实际容量/UUID，只读诊断结果待回收。
a26c22ba（300秒/ordinal1）因长观察已显示主线程推进，没有在手机启动；f32bac92也仅本地构建。

70z准备显式--gui-kernel-stacks：只在processor_count为1、引用的目标线程为阻塞且不运行时，
短暂禁止本CPU抢占并通过原版ml_nofault_copy读其保留的wired内核栈，范围限于真实栈分配、16帧。
目标有continuation时只记该地址；其他状态或读取失败保留真实失败，不暂停目标线程。
恢复抢占后才记录RAM标量。默认仍采原版用户VM栈，SMP下拒绝此内核采样。
v15不增写区或结构尺寸，以stack error高位标识内核来源、低位保留错误；主机分开解析
内核/用户帧，并拒绝旧版本冒充或陈旧样本挂到新线程记录。边界/类型/陈旧负例通过，
101份历史日志仍可解码，实际编译及设备结果须另记。


## 05:02：RAM Data 剩余空间实测；本机归档空间修复

38dd08b2于05:02:30自动回recovery，新日志；tick60/stage12/918661ms。
原版vfs_getattr成功，支持位15，Data实际UUID C7D77FF3-6437-4C4A-8E05-E8E239AC1641，
4096字节块×131072=512MiB，可用77739块=318418944字节（约304MiB）。
本轮可排除APFS Data容量耗尽；RAM块传输errors0也独立保留。
Data权限232/232/root0:0；显示accepted5/transfers5、末状态0，摄像头04:55仍为苹果标志。
这轮lsd仍在performJournalRecovery队列等待，SpringBoard仍等_LSCopyServerStore；
上一轮的后续阶段不是稳定可复现的完成状态，不能只增加等待就宣称修复。

内核栈候选087deb5d/361f8f28仅本地构建，未在手机启动。实际nofault/helper调用与线程引用释放审计通过；
从实际helper及原版保存态声明提取C，在宿主测试12种状态/越界/循环/16帧上限/读取失败情形，
均保持目标线程和栈字节不变，且记录前抢占已平衡恢复。硬件资格仍待实测。
紧凑日志漏去重LC2/LD2/LV2/LW2已准备补齐，保留首个和指定检查点，并计数实际写盘及避免的重复写。
未改变锁、open、IPC返回或服务初始化语义。

8fe5aa54完整打包后在归档内核时遭本机ENOSPC，整轮构建判失败，没有交给手机。
其ready归档清单已撤回为incomplete-inputs，留下失败原因；只删了不完整复制出的内核片段，完整源仍在。
归档器已改为临时完整复制、哈希核对后发布，ready清单放最后；已有文件不符会拒绝，避免把半份拷贝当成功。

为恢复空间，将生成的512MiB空白Data原始镜像变为稀疏文件，物理536870912→1048576字节，
逻辑SHA仍4d9b3e43255e940e928e34cc901a6ae2c09d28352e763a7406d61ee377576db8。
随后仅对较旧构建归档内核做gzip，每份完整解压比对归档SHA后才去掉其raw重复；
当前/近期、关键调查基线、boot镜像、日志、原始IPSW与手机备份保留。
历史内核可用gzip -dk PATH/kernel.macho.gz逐字恢复。操作仅在本机，手机保持recovery；05:00关机仍已取消。


## 05:08：继续完全无人值守的工作线程采样

本机64份较旧生成内核已逐份gzip完整解压并核对归档SHA，约释放2505535488字节；
加上稀疏Data节省的空间，构建时已有足够余量。保留近期和关键调查基线的raw内核。
构建器新增1GiB最低余量检查；归档用临时文件、完整SHA核对及原子发布，inputs清单最后发布。
历史kernel.macho.gz用gzip -dk恢复，boot镜像、运行日志、原始IPSW和备份未删除。

2c784bad（完整SHA 2c784bada25a5b42bc34e465e3414d5a125b1963f1881918fcf7cd38ad4c1384）
已完整归档并验证，05:08:33只对K80临时启动。显式v15内核栈、lsd原始ordinal1、900秒窗口，
保留Data元数据及只读空间诊断、独立watchdog和自动recovery；新增LOGIO计数及stage2重复去重。
VFS源码确认LCn/LDn/LVn/LWn来自路径分量查找的进入/返回标记，不是独立服务报错。
05:10的单帧可识别K80与UEFI色条/菜单，还未出现桌面；不据此判断内核执行位置。
实际栈读取、去重计数和本轮系统进度仍待日志回收。05:00关机任务保持取消，没有改成其他时刻。


## 05:15 起：当前轮次苹果标志；准备保留完整等待链

2c784bad的05:15单帧已显示苹果标志，仍未见桌面。正在等待自动回收，而非要求机主拍照。

后续观察改进保持v15线格式：有保留内核栈的阻塞线程仍进行有界nofault读取；
如果只有continuation，地址已在进程记录中，转而读取原有用户VM栈，以免用同一个地址覆盖更深的等待链。
可运行目标也只读原有用户帧，不读取其内核栈；SMP及终止目标仍明确拒绝内核读取。
真实读取失败继续记录错误，不用用户栈覆盖内核读取错误。12项实际helper宿主控制仍通过，
GUI线格式/边界/源类型/陈旧样本与102份历史记录检查通过；新行为尚未在设备运行。

VFS源码中的路径标记最多计至9，因此下一候选补齐LC/LD/LV/LW的3..9去重，
继续保留首个和指定检查点，不改变路径查找结果。修正文本IPC槽0的lsd名称，固定footer一直按实际来源解码。
下一候选只在本机构建，待2c784bad回收后按日志决定是否启动。


## 05:25：continuation 实测及最终快照提交修正

2c784bad于05:25:13自动回recovery，日志确有变化；摄像头05:23仍为苹果标志。
最终tick60/stage10/921429ms，Data可用344469504字节、UUID正确，权限232/232，RAM errors0。
显示accepted6/transfers6、最后状态0，仍无桌面。
lsd ordinal1/3共享wait_event，ordinal1的用户LR落在libdispatch __dlock_wait+52，
实际内核记录仅为_ulock_wait_continue；SpringBoard/backboardd仅为_ipc_mqueue_receive_continue。
这些是continuation分支的真实地址，未实际进入nofault读深栈，因此不能声称物理栈读取已获资格。
下一观察保留原有用户栈，正是为展开这种等待链，而非重复同一continuation。

最后一次LOGIO文本为writes14523/ok13861/dedup8245592/stage2=4448。
dedup总数包含此前就已去重的标记，不能全部算作本次新增节省；新增stage2数为4448。
写入未成功数也不等同于OS读盘失败；Data块错误仍独立为0。

stage10没有证明观察线程卡在这里：原代码在输出runtime文本之后才更新stage11/12，
超过hold绝对期限后不再pet/写GHOLD；静默日志时最终BSS阶段可能没有随后的写盘。
71z增加最终一次有界刷新：同一4KiB日志块，最多三次、两次10ms调度等待，不再pet watchdog。
实际写成功后磁盘中的GUIEND才表示该最终阶段已提交；未改过期回收时限。

3a98edc8是已归档但未在设备启动的中间候选；当前继续构建含最终快照刷新的版本，
全部检查与完整归档通过后由--boot自动临时启动，仍为900秒/lsd ordinal1。


## 05:29：完整等待栈与最终快照试运行

9ead2e85（SHA 9ead2e85dbb183d5176e52d0fd6d56486ba2fc13203c3894a7f521d206cbf871）
于05:28:59仅对K80临时启动，v15混合栈/lsd原始ordinal1/900秒。
摄像头05:32与05:36均为苹果标志，尚无桌面；等待自动recovery及新日志。
包含完整LC/LD/LV/LW 0..9去重及71z最终快照提交。
最终刷新从实际源函数提取，在宿主执行10项禁用/成功/失败/锁忙/重试控制：
固定同一4096B缓冲、最多三次写和两次10ms调度等待，无watchdog pet；不代替设备实测。
ace059a4为已完整归档的ordinal2备选镜像，尚未启动。05:00关机继续取消，未设置新截止时刻。

5f3bedbf（SHA 5f3bedbf83a74b3abec7b2c4324552e79d45b4490db76031feb7bca678934362）
已在本机完成ordinal2镜像及检查，尚未启动。相对ace059a4增加RAM统计：
实际OS/SystemOS逐块hostRead4k调用次数、失败次数、调用累计耗时，以及诊断写累计耗时。
只在GUI观察开启后计时，不改变原版读盘、逐块认证、返回值或只读写保护。
UFSIO read_us包含host锁等待与抢占，log_us也可能包含抢占，二者可能重叠，
不是硬件纯延迟，不能相加作为墙钟占比；errors仅指这里的传输调用失败，不代替认证错误。
统计放已有文本环，不扩展4KiB日志写区或ABI。此候选尚无设备结果。


## 05:45：混合栈已取回，SpringBoard推进到ActivityKit

9ead2e85于05:45:34自动回recovery，日志变化；tick60/stage12/908197ms。
Data实际UUID正确，可用283287552字节，元数据232/232/root0:0，RAM errors0。
显示accepted6/transfers6，最后状态0；05:42后期摄像头仍为苹果标志，没有桌面。
混合模式真实保留了lsd和SpringBoard各16帧用户链；backboardd7帧后保留实际error1。
lsd ordinal1已在_LSPersonaDatabase refreshFromUserManagementIfNecessary调用内，
通过libxpc _xpc_user_sessions_info_routine查询；SpringBoard主线程已越过原LS等待，
改在ActivityKit经BoardServices同步IPC。此快照证明这轮有后续推进，不证明持久卡死或根因。
最后两个IPC消息不等于这条主线程的当前等待对象，暂不据此禁用其他服务。
LOGIO writes13970/ok12749/dedup20110647/stage2=8312。stage12已落盘；
最后92项没有GUIEND，可能被后续runtime输出覆盖，不能仅凭阶段号确认最终flush的独立写成功。

5f3bedbf于05:46:58开始ordinal2/900秒临时启动，含只读UFS耗时统计。
3a98edc8、ace059a4仍仅本地构建；05:00关机保持取消。


## 05:55：有界延长观察与ActivityKit对照候选

原版缓存导出补充与LC_FUNCTION_STARTS证实，9ead2e85中ActivityKit返回PC 0x21ca26a1c
实际属于0x21ca269ec起的192字节私有函数，并非最近导出的构造函数。
其真实ObjC选择器为activitiesExceedingReducedPushBudget；原函数有nil分支。
只读原OS确认liveactivitiesd由SessionCore提供，启动声明包括com.apple.sessionservices；
com.apple.activitykit.output是框架接口标识，当前未把它直接当作已证实的等待Mach端口。
lsd原版libxpc导出也确认查询为_xpc_user_sessions_get_foreground_uid。
所有原版代码切片和反汇编仅留ignored out，证据目录只存来源、符号与哈希。

72z扩展显式hold上限到1800秒，>900时每30秒观察、最多60次，
第一段睡眠前增加一次受绝对epoch期限保护的pet。55秒独立watchdog没有禁用；
到期不再pet，错过调度仍会bite回recovery。主机timeout上限2400，--boot要求hold+120余量。
实际native pet函数、初始化表达式和实际观察周期代码在宿主枚举-1..2200并测试期限前/等于/超过边界。
fe55ffa5（SHA fe55ffa50e88ef53b7053e13ec4c563625398e607b67f206a2480c7c3468fec9）
1800秒/ordinal1/服务不变，已构建检查，尚未启动，设备效果未获资格。

7516d9be（SHA 7516d9bec393e74aaab84d2e11a3a84483aff53fa304ab47b42b32954d22d2cc）
900秒/ordinal1，另外通过现有sheng-disable-jobs临时停用com.apple.liveactivitiesd，尚未启动。
官方22项lite列表不改，合计23项；预期1126字节plist、root0:0/mode0644必须由实际运行读回另行确认。
这只是有原始调用证据支持的bring-up隔离假设，不宣称服务已被有效停用或根因修复。
--disable-jobs需最小RAM策略、受199字节ASCII输入限制，归档记录+custom及完整标签，
仍只改本轮易失RAM Data；不改变原版framework/LaunchDaemon文件、系统卷或独立watchdog。
当前手机继续跑5f3bedbf，待回收后决定使用哪个候选。


## 06:03：UIKit主事件循环与真实UFS耗时

5f3bedbf于06:03:33自动回recovery，日志变化；tick60/stage12/909733ms。
RAM Data权限232/232、实际UUID正确，可用297312256字节，RAM errors0。
lsd原始ordinal2在LSDatabaseBuilder createAndSeedLocalDatabase的group wake中，
SpringBoard主线程已进入UIApplication _run下的CoreFoundation事件循环；
backboardd主线程在AccessibilityUtilities处理客户端注册。
因此上一轮ActivityKit同步请求不是稳定复现的永久卡点，暂不运行7516d9be服务隔离候选。
本轮显示accepted8/transfers8、末状态0，后期摄像头仍为苹果标志，没有桌面。

实际readonly OS/SystemOS hostRead4k共1079180块、传输错误0、调用累计83039805微秒；
诊断写入调用累计21611422微秒，LOGIO writes14472/ok13266/dedup20648438/stage2=8488。
耗时含等待/抢占且可能重叠，不当作纯硬件延迟或相加计算占比。
读取约4.12GiB经原逐块校验路径，不能把RAM错误0替代所有系统认证或驱动资格。

fe55ffa5于06:05:53临时启动，服务配置不变，1800秒/30秒周期，自动回收上限2100秒。
06:10摄像头为苹果标志；新时间窗口设备结果仍待回收。

当前compact过滤在每条重复标记上依次strcmp最多163项。新查表由本轮精确源哈希提取相同163标签，
用7字节无损键及有界二分查找，不增加忽略集合，保留原首次/指定检查点/噪声规则。
实际C++头已通过全部原标签、前缀/单字节变体及100000组未知输入对照。
b0975c91已构建/检查/完整归档，尚未启动，不声称真机提速。
APFS归档改用独立inode的copy-on-write clone并逐份SHA验证；宿主写副本不改变源文件已测试，
临时文件链接发布后即清理，不把源文件硬链接成归档。

73z仅允许显式选取backboardd原始线程窗口，默认0；0..63、最多4条寄存器和16帧限制不改，
线程原编号写回既有字段，无footer尺寸或版本改动。准备ordinal4候选供后续检查渲染工作线程，
不把一个空闲主循环当作所有合成线程都已运行，也不更改GPU或触控范围。


## 06:17：当前会话的后台续调已启用

7f6b5a18（SHA 7f6b5a18dadcbdff65c498cb60ddd5c63da6a5bbb10624c3ef0258a25e7878f0）
已构建、通过实际调用/边界检查并完整归档，1800秒/lsd1/backboardd4/精确163项查表；尚未启动。
105份历史日志解码、C/Python ABI、线程原编号、陈旧栈拒绝及真实helper控制通过；未声称真机提速或深内核栈资格。
当前手机仍在fe55ffa5有界30分钟轮次中，后台会先等实际回收再决定下一步。

已创建并启用当前本地会话的10分钟定时续调，应用返回automationId k80-unixnu、ACTIVE。
它读取current.json避免重叠临时启动，回收后凭新日志/准确归档继续分析和构建，
没有重新设置05:00关机。遇到必须物理操作或最终现场确认时，能连接则回recovery、
暂停续调并卸载active-debug唤醒任务；不向离线机主提问、不自动刷写恢复。

06:27后台检查：fe55ffa5仍在已授权的1800秒观察/2100秒主机超时内；绑定本轮的USB摄像头单帧仍为苹果标志，未见桌面。保持现场等待自动回收，没有重叠启动或重复同镜像。


## 06:37：30分钟有界观察已自动回收，数据库等待仍会复现

fe55ffa5于06:37:41自动回recovery，新日志；tick60/stage12/1830267ms，末尾GUIEND存在。
首次1800秒窗口和最终提交标记已在设备记录；55秒独立watchdog和主机2100秒上限保持。
Data权限232/232/root0:0，实际UUID正确，剩余342114304字节；RAM errors0。
显示accepted5/transfers5、末状态0；06:27画面仍为苹果标志。06:37摄像头拍到的是已自动回收后的TWRP，
不能把recovery界面误记为iPadOS界面，也不能据此推测回收前最后一分钟的完整画面。
实际UFS读1005647块/传输错误0/调用累计51044182微秒，日志写40078780微秒；
LOGIO writes13665/ok13178/dedup8845582/stage2=4654，累计耗时仍含等待与抢占。

lsd原编号1在LSDatabaseBlockingFetchClient的数据库seeding group等待，原编号3共享wait_event；
SpringBoard这次在ControlCenterServices模块可用性查询中同步等待_LSCopyServerStore，
backboardd主线程为CFRunLoop。更长观察没有稳定进入桌面；此前UIKit事件循环不能当作稳定完成初始化。
为追查这轮原编号2的Mach消息等待，下一候选改采lsd2，同时保留backboardd4和163项查表，
服务配置保持不变；7f6b5a18仍仅构建，暂不重复已知的lsd1等待栈。新候选完成检查和归档后才临时启动。

dd3ef48e（SHA dd3ef48e8bff64891a9de874254bf018a9a0e74cabef4df9eb7b7a3db28a27bc）已完成全部构建检查与归档哈希核对，于06:42:33仅对92988a43/zorn/b临时启动，BCB尾部保留并读回，fastboot发送/Booting均成功。1800秒观察、2100秒回收上限，lsd2/backboardd4；这是新的定向采样轮次，没有重复启动fe55ffa5，也未使用服务隔离候选。
06:46绑定dd3ef48e的USB摄像头单帧已确认苹果标志，尚无欢迎页或桌面；继续等待新轮次自动回收。后台提示已改为读取实时current.json，不再固定声称fe55ffa5为当前轮次。


## 07:18：lsd2 等待种子组，IOMFB 线程用户栈已采到

dd3ef48e 于07:13:51自动回 recovery；run.status=recovered、kernel_log_changed=true，
ready归档与启动镜像SHA、对应kernel.macho SHA均逐份核对后才解析。最后记录为tick59/stage10/1800081ms，
这次没有记录完整tick60/stage12或GUIEND；不能据此宣称最终提交分支通过，也不能把最后阶段直接当作死锁。
独立watchdog/自动回收正常。06:46、06:58和07:08的绑定单帧均为苹果标志，仍无桌面证据。

lsd pid69原编号2的真实用户栈在restoreInactiveInstalls的dispatch_group_wait，
与已核对的原版实现一致：先等数据库seeding group，未证明卡在恢复安装本身。
SpringBoard主线程仍经ControlCenterServices查询等待_LSCopyServerStore。
backboardd原编号4首次采到QuartzCore CA::WindowServer::IOMFBServer::thread_body的CFRunLoop栈，
说明该线程存在且可采样；不能当作整个合成管线已输出桌面的证据。原编号5..7为Mach消息等待。
lsd当前窗口2..5仍truncated，确认原编号6及以后存在；4、5为workq等待，下一次定向采6..9，
以找到实际seeding工作线程，避免继续重复已知的group waiter。观察改为900秒/1200秒回收上限，
其余8 GiB、CPU0、lite22服务、只读OS、RAM Data、backboardd4均保持。

实际Data剩余341368832字节、权限232/232/root0:0、RAM errors0；显示accepted6/transfers6、末状态0。
UFS读1009788块/传输错误0/read_us53755337，日志写log_us37859528；
LOGIO writes13503/ok12933/dedup8970109/stage2=4586。计时含等待及抢占，不能相加当墙钟占比。
精确163标签查表已随此镜像在真机运行；线程窗口也改变了，不能据此声称严格单变量提速。
证据见docs/evidence/gui-seeding-worker2-backboard4-{run,state,symbols}.json。

a659853c（SHA a659853c6d3474dd2a167fcaf33af843e3315fdae9d22de67316afb005a49035）
已通过构建及实际helper/ABI/调用边界检查，ready归档的boot和kernel哈希已核对。
07:21:05仅对92988a43/zorn/b临时启动，BCB首864字节以外保留并读回，fastboot发送/Booting均成功；
900秒观察、1200秒回收上限，lsd6/backboardd4，原服务配置；尚待新日志，未宣称修复数据库或进入系统。
07:22新轮次的早期单帧为色条及保留的UEFI背景，尚无苹果标志/桌面；细小阶段文字无法辨认，不推定为回退或死锁，继续有界观察。
07:28绑定a659853c的摄像头单帧已为苹果标志，仍无欢迎页/桌面；轮次尚在900秒观察/1200秒回收上限内，保留现场等待新日志。


## 07:38：SpringBoard 再次到主循环，转向其他显示线程与末段画面

a659853c于07:37:38自动回recovery，新日志、ready归档及准确boot/kernel哈希均已核对。
最后tick60/stage12/918239ms，RAM Data剩余277770240字节、UUID正确、权限232/232/root0:0，RAM errors0。
显示accepted9/transfers9、末状态0；07:28单帧为苹果标志。UFS读1087015块、传输错误0、
read_us90926965/log_us14918191；LOGIO writes14297/ok13186/dedup20617699/stage2=8572。
计时仍包含等待和抢占，不是可相加的硬件耗时占比。此次没有保留下GUIEND。

SpringBoard主线程又到UIApplication _run/CFRunLoop，实际保留10帧后error1，不能抹掉读取错误，
也不能把主循环当作桌面。backboardd4仍在IOMFBServer thread_body/CFRunLoop；窗口4..7的truncated确认
原编号8及以后存在。lsd6窗口本次末样本为空：该时刻不足7个符合采样条件的线程，
不是采到空闲或阻塞栈，更不能据此宣称数据库已稳定完成。下一候选采lsd0/backboardd8，
服务和GPU/触控范围保持，继续寻找合成/启动异步工作线程。

为避免10分钟续调错过临近回收的画面，run-zorn-debug新增默认关闭的--capture-after秒数。
仅ready GUI watchdog镜像可用，在fastboot boot返回后指定时刻最多调用一次既有USB单帧脚本；
不采音频、不自动判定界面，子进程上限25秒，至少保留26秒deadline余量，绝对回收期限不变。
摄像头缺失/超时/失败不影响原ADB日志回收；意外device状态和ADB错误仍中止，bootstrap回收不采集。
12项实际wait_for_recovery/capture_screen宿主控制已通过，无USB访问；真实定时触发仍待下一轮验证。
证据见docs/evidence/gui-seeding-worker6-{run,state,symbols}.json及runner-observation-host-checks.json。

6f9950ba（SHA 6f9950ba391b70c00399856215b40c08e4ce8959625c549f50428c93d888065f）
已通过全部构建检查与ready归档boot/kernel哈希核对；07:43:53仅对92988a43/zorn/b临时启动，
BCB尾部保留并读回、发送/Booting成功，lsd0/backboardd8、900秒观察/1200秒回收上限。
本轮显式--capture-after 900，实际宿主脚本哈希与12项控制报告随run保存；
定时摄像头帧和新内核日志尚待产生，不能将上一轮苹果照片或主循环记录当作本轮结果。
07:48绑定6f9950ba的单帧仍为色条及保留的UEFI背景，未见苹果或桌面，细小标记无法辨认；当前仍在有界观察内，不提前重启，定时末段单帧尚未到时。
07:59末段定时单帧已实际触发：fastboot boot返回后900.902秒，子进程returncode0；绑定6f9950ba的图像仍为色条/保留UEFI背景，未见苹果或系统界面。主机轮次仍started，继续等自动回收，不把未回收的旧日志当作此轮结果。


## 08:08：本轮停在显示服务启动前，补采可运行线程的内核上下文

6f9950ba于08:00:29自动回recovery，新日志；准确boot/kernel与ready归档已核对。
tick60/stage12/901447ms且GUIEND保留，定时单帧900.902秒触发成功后仍正常回收。
07:48及07:59画面均为色条/保留UEFI背景。这次没有backboardd/lsd进程样本，
显示clients0/accepted0/transfers0；因此不能将之前IOMFB或UIKit记录算成本轮成功。
RAM Data剩余534085632字节、权限232/232、RAM errors0；UFS读796715块、传输错误0、
read_us24051914/log_us2748596。容量没有耗尽，传输调用计时仍含抢占/等待。

SpringBoard pid5主线程state=TH_RUN，EL0保存PC落在SpringBoard.framework的
objc_msgSend$sharedManager入口，LR为该框架0x1cfa37af0；仅1帧后保留error1。
这是最后异常/陷入保存寄存器，不是实时PC轨迹，单点不能证明在该ObjC方法内永久自旋。
此前内核栈诊断特意对TH_RUN回退到用户栈，故没有实际内核等待/被抢占调用链；
当前证据不足以归因GPU、LaunchServices或修复某个Apple组件。

74z新增单独显式--gui-runnable-kernel-stacks（zorn_gui_krun=1），默认行为保持：
仅在原gui-kernel-stacks模式且初始化CPU数=1时，短暂禁止抢占，允许读取已引用、非当前、
非终止的TH_RUN目标已保存内核上下文；有continuation仍回退用户链。
原版Switch_context确实在无continuation切换前保存FP/LR/SP；machine_stack_attach布局已核对。
仍只在目标实际有界wired stack中使用ml_nofault_copy、最多16帧，恢复抢占后才记录，
不暂停目标、不改调度/锁/映射，不改4096B块、footer v15或OS文件。
20项实际helper控制通过，包含默认拒绝、显式RUN/WAIT|RUN、SMP/当前/终止/空目标、
continuation、地址边界/循环/故障/帧数上限及无目标内容写入；两CLI拒绝缺失前置选项。
74z在当前增量树reverse --check通过；干净重放仍未验证，物理RUN栈读取仍仅待测，未宣称解阻。
下一候选保持lsd0/backboardd8、900秒/1200秒、CPU0和原服务配置，只加入该显式诊断，
继续保留第900秒末段单帧。全部构建/调用检查及完整归档通过后才临时启动。
证据见docs/evidence/gui-backboard8-{run,state,symbols}.json和对应camera/scheduled报告。

2ddf7cb4（SHA 2ddf7cb4e126404cd1689c6ec90a6214a9c4c9d038e6f2cab549d3a759016d82）
已通过20项实际helper控制、真实链接调用审计、其余构建检查和完整ready归档哈希核对；
派生启动参数zorn_gui_krun=1恰好一项。08:15:09仅对92988a43/zorn/b临时启动，
BCB尾部保留并读回、发送/Booting均成功；900秒/1200秒并保留末段单帧。
尚未回收，不声称已读取物理RUN内核栈或解除早期停顿，未重试旧镜像/启用多核/GPU/触控。
08:18绑定2ddf7cb4的单帧已为苹果标志，仍无欢迎页/桌面；尚待回收，不能把画面变化归因于诊断选项或宣称物理RUN栈读取通过。保留现场，不重复启动。


## 08:31回收与官网/houji路线复核：首次真实VM读锁内核栈

2ddf7cb4自动回recovery，changed log为true，ready归档与boot/kernel完整哈希核对后解析。
最后tick57/stage11/857487ms，无完整GUIEND；不能称60次观察全部完成。
lsd主线程14帧、SpringBoard主线程13帧保留内核栈，读取错误均为0。
lsd为用户缺页→vm_fault_internal→lck_rw_lock_shared→shared_gen→抢占路径；
准确归档nm确认IORWLockRead与lck_rw_lock_shared同址，调用点反汇编与源码对应VM map读锁。
这是首个实际内核争用线索，尚无同一锁重复时间序列/持有者，不宣称永久死锁或已定位唯一补丁。
SpringBoard位于Mach消息发送；backboardd原编号8为IOMFBServer/CFRunLoop、用户栈10帧/错误0。
线程编号会跨轮次变化，不把原编号4或8视为固定功能身份。

08:30定时单帧仍为苹果标志；accepted7/transfers6/末错误0。
Data剩余300089344B、权限232/232、UUID正确、RAM读126/写7724/错误0；
空闲1284561个4KiB页。UFS1067180块/错误0/read_us76651579/log_us9208747，计时含等待/抢占。
74z显式RUN内核栈路径已有本轮硬件成功读取证据，不等于其修复GUI或完整硬件负例验证。
证据见docs/evidence/gui-runnable-kernel-*；摄像头原图未放入发布目录。

按用户要求重新核对官网移植/构建/参考和本地houji快照，完整分析见
[2026-10-28复核](review-2026-10-28-official-houji.md)。
后续优先锁状态/持有者/重复时间证据及观察者效应，再检查LaunchServices生产者与CPU合成链；
不盲目增加服务隔离、内存或多核。houji为iOS16/HFSX，CPU桌面已由作者验证，
其ABI/根卷安装脚本不能直接搬到K80的17版APFS；已有skip-Setup/开发板身份无需重复添加。
本次只取证与更新文档，没有新增试启动或修改设备，最近设备状态为recovery。


## 09:14：定向恢复VM map锁初始化，构建中

从2ddf7cb4准确内核反汇编、原版源码与当前工作树交叉核对发现，早期12z的
zorn-vmap-nosleep在每个vm_map_lock_init后强制清LCK_RW_CAN_SLEEP_BIT；
这使正常VM map读写锁争用只能自旋。原版该锁由lck_rw_init初始化为可睡眠。
新75z只撤销这条初始化修改，当前整个vm_map.h SHA已与固定原版相同：
aa356431b157c5b73ab4404b7bfb432e40a4773393dd12586a857760c398d76d。
没有整体恢复lock_rw.c/pmap，也没有强行解锁或伪造成功。
这与新采到的lsd VM读锁争用直接相关，但尚未证明它是唯一根因。

新增audit-zorn-vm-map-lock.py核对原版macro与真实vm_map_create_options调用，
拒绝旧源文件与旧归档内核的0xffbfffff清位指令；两项负例均已实际拒绝。
源头核对、75z在当前增量树reverse-check、Python语法检查通过；新链接产物审计待构建完成。
构建器将报告、脚本及vm_map.h SHA纳入ready输入和归档，保持原900/1200秒、8GiB、CPU0、
原服务、线程窗口和采样模式。仅全部检查/归档通过后才临时启动。
当前设备定向只读核对为92988a43 recovery，没有重叠轮次。

为满足本机编译空间，既有压缩器新增可选--keep-recent（默认14不变，最低4），
本次取6，仍保留指定调查基线；只压缩生成的旧kernel/plan，逐份解压核对SHA后才移除raw副本。
IPSW、系统卷、设备备份和日志没有删除；旧内核可gzip -dk恢复。


f8533418已完成全部构建/调用/ABI检查与ready归档，完整boot SHA
f8533418c14f26413079de0aa07eef61655029151aec428d0e60e97170f560b7，
kernel SHA 1622062d994246ba24f0539e34d786a206e8a4456a607712cdcee6b802b32e86。
与2ddf7cb4的运行选项逐项比较一致，唯一内核功能改动为原版VM map锁初始化。
新审计已核对真实_lck_rw_init调用与旧清位指令缺席，并随ready归档保存；
当前整个vm_map.h SHA与固定原版相同。首次构建在新增审计处发生Python变量引用错误，
发生于USB操作前；已修正路径并完整重跑构建通过，失败日志单独保留。
09:16:33仅对92988a43/zorn/b临时启动，BCB首864字节之外保留并读回验证，
fastboot发送/Booting成功；900秒观察、1200秒回收上限、第900秒单帧仍保留。
当前尚待本轮新日志/画面，不宣称修复死锁或进入桌面。
10分钟续调已更新为引用本次复核和最小改动路线，应用返回ACTIVE，原取消关机保持。
09:17早期单帧为色条/保留UEFI背景，小字无法辨认；尚在观察窗口，不能据此判定停在固件或已回退。保留现场等待定时末段单帧及新回收日志。


## 09:31首次出现系统锁屏；09:33自动回收并按规则暂停

f8533418于09:33:08自动回recovery，kernel_log_changed=true；准确boot/kernel、
ready输入与本轮绑定照片SHA均核对后解析。定时单帧于boot返回后900.505秒触发，
09:31:44照片清楚显示大号4:15锁屏时钟与底部白色手势条，已不是苹果标志或色条。
手机显示时间不是本机记录时间，未据此宣称RTC已适配；照片没有解锁/桌面/触控操作证据。
这是首次可见系统锁屏，不是完整日用系统资格，也未重复验证启动稳定性。

最后tick60/stage12/918062ms；lsd主线程在CoreServices runServerMainRunLoop/CFRunLoop，
SpringBoard主线程到UIApplication _run/CFRunLoop，两者用户栈均保留实际读取错误1。
本末样本未再采到前一轮的VM锁争用，但单次事件循环不能证明所有数据库工作完成。
backboardd原编号8仍为IOMFBServer线程/CFRunLoop、10帧/错误0。
显示accepted8/transfers8/末错误0，profile三项精确fixup本轮均applied。
RAM Data剩余290320384B，权限232/232/root0:0，UUID正确，读154/写10069/错误0。
UFS1095974块/传输错误0/read_us65288882/log_us8804867，LOGIO14580/13554；
计时含等待/抢占，仍不能相加作为墙钟占比。

在只恢复原版VM map锁初始化的轮次出现了锁屏，提供了沿同步正确性继续工作的正面证据；
没有对照复测或证明它是唯一原因，其他早期lock_rw/pmap修改仍需核对。
准确实测证据见docs/evidence/vm-map-sleepable-{run,state,symbols,camera-observation,result}.json。
图片像素仅留在忽略的out，未把摄像头房间照片加入发布仓库。
首个成功基线索引保存在out/zorn/known-good-lockscreen-f8533418.json，绑定完整镜像、
内核、输入哈希、日志与单帧观察；暂不改写现有userdata或更换RAM Data策略。

按机主明确的无人值守停止规则：发现系统界面后先回recovery并暂停，等待本人确认最终画面。
09:37左右定向ADB已核对92988a43、zorn、recovery；无需额外重启。
应用返回heartbeat k80-unixnu=PAUSED；com.unixnu.zorn.active-debug已bootout并确认不再加载。
本次没有继续启动其他候选、启用触控/多核/GPU或发送异步提问，也没有Git提交/推送。
待机主恢复后，优先复核可见锁屏/解锁和稳定性，再适配触控；GPU继续后置。

机主要求远程摄像头查看，2026-10-28T09:53:07+0800以完全相同f8533418镜像单次临时复测；保留900秒观察和1200秒回收上限，后台续调仍PAUSED，本轮不调用摄像头以供机主查看。仅启动成功不等于锁屏复现。轮次：out/zorn/debug/20261028-095307-f8533418。


## 机主确认锁屏，恢复Data → 全核CPU → 远程触控尝试

新的授权、Data窗口完整前像/元数据读回、只读探测及迟到回收的失败边界见[阶段记录](progress-2026-10-28-data-smp-touch.md)。后台续调已恢复ACTIVE，原锁屏确认暂停已解除；SMP/触控仍未启用。Data保留须跨两轮实际标志文件读回后才能判为通过。


78c070a8（boot SHA 78c070a81ce4c8d2cedd6e30fda93c43c1d8928b772e51b3b4146d4b4570104a，kernel SHA 6b574e6f77f84097b890db44bc57dbd316d2b01e1d98db68944b4e1ef5e56711）已通过全部检查、真实provider/marker调用审计与ready归档哈希核对。2026-10-28T10:58:20+0800仅对92988a43/zorn/b临时启动首次mode2写回轮次，BCB保留尾部并读回、fastboot发送/Booting成功。900/1200秒与末段单帧，尚无新回收结果；Data保留未判通过，多核/触控未启用。
11:13:31绑定78c070a8的末段单帧（900.378秒触发）已见系统锁屏时钟/底部手势条，图像SHA核对一致；未操作解锁/触控。尚待回收DSTORE/DKEEP记录，不能据画面判定Data已保留。

## 11:14首次Data写回成功；低亮度插队

78c070a8于11:14:55在1200秒上限内自动回recovery，changed log及完整boot/kernel/ready归档一致。
实际记录为 `DSTORE mode=2 open=1 state=2 header=0 gpt=0/0 present=58340 writes=80450 loaded=600 errors=0`，
`DKEEP state=1 error=0 cookie=2c59d71a`。APFS UUID正确，剩余295899136B，RAM接口150读/10300写/0错误。
末样本tick60/stage12/917243ms；lsd与SpringBoard主线程到事件循环，实际用户栈错误1仍保留。
本轮backboardd原编号8解析到CoreMotion/CFRunLoop，不能沿用旧轮的IOMFBServer身份。
锁屏照片与此轮绑定。首次文件创建、同步和重新打开读回已通过，跨重启保留尚未验证。

机主随后将“硬件低亮度，降低长时间调试屏幕发光强度”插到最高优先级。
已核对recovery=92988a43/zorn/_b、panel0-backlight最大16383、当前brightness/actual_brightness均0（自动灭屏）。
因此先保留现有overlay，在下一次长观察前完成面板亮度控制；不重置Data，不启动Android。
真实面板o11_42_02_0a及DCS/高字节优先/DSI0 v2.8地址已从实机FDT与MiCode固定源码核对；
当前UEFI使用SimpleFb，没有可直接调用的厂商亮度实现。第一步候选仅读取DSI寄存器，
在BLSNAP自动回收；还未发送亮度命令、未宣称屏幕已经调暗。

12:19低亮度短测d22986fe真机通过：307→64，单次写后新鲜读回64、ACK/TIMEOUT均0，自动回收。详见[亮度记录](progress-2026-10-28-brightness.md)。短测未运行完整GUI；已有Data重复启动权限模板在 `/private/var/containers/Temp` 的ENOENT仍待修正，不重置overlay。

2026-10-28 12:53：eb55ebe5由机主确认锁屏，手动回recovery；真实DKEEP2/相同cookie及正常低亮度307→64通过，首次跨重启保留已证实，详见[阶段记录](progress-2026-10-28-data-smp-touch.md)。触摸仍无作用，CPU0保持。


2026-10-28 13:14：机主在现场，按新指令触控优先。FT3683 只读 handoff 探针自动回收，SE断钟、六针未启用；详见[触控阶段记录](progress-2026-10-28-touch.md)。CPU0保持。首次Data保留成功后的第二次重复测试停在亮度交接保护，未到Data，未重置overlay。

2026-10-28 13:24以后：触控原生电源/时钟交接短测自动回收并通过；机主带走手机后转离线，新 bce3bdbe 仅构建未上机。[手动测试/日志回传](touch-test-instructions.md)。后台继续PAUSED。

# K80 iOS26 v238：真机测试前交接

用户最新要求：**v238 真机测试前编写交接文档，交给其他 Agent 续接。本 Agent 未启动 v238。** 总目标未完成，未标记完成或擅自暂停。接手者先阅读本文、`AGENTS.md`、README、`porting.toml` 与用户完整授权；本文覆盖旧交接中 v238 以前的状态，旧证据保留。

## 当前位置与当前任务

GPU/Metal/display/FT3683 完整实机验收仍是最终目标。目前先补齐 panic 日志，再定位 GPU 路径中的 PAC 认证失败。不要把日志成功、完整链接或旧版本局部渲染成功当作目标完成。

上一阶段 v237 单次真机试验成功导出当前精确身份的 1050 字节 panic 原因和 131072 字节 msgbuf，约 199.836 秒自动回 TWRP。原始原因首句为内核 PAC 认证失败；只确认症状，未定位根因。完整 kernel paniclog 不可用（flags 384：并发 msgbuf + 缺失 paniclog）。普通 Metal probe 停在 phase1，终止请求6/ack5/state2 表示 registerService 已返回，不能据此断定故障调用点。

v238 只新增 kernel-owned RAM panic 后备区，保留 v237 GPU、USB 协议、Recovery、已安装229根和原 SLEH。完整内核与启动包已生成，29项拒绝测试及 check-only 已通过。**未进行 v238 手机访问，未产生 one-shot claim。** 所有本轮构建/测试进程已经终止；最后 session4323 exit0。不要把 ready.json 的存在当作已经通过设备 Recovery 前置条件。

## 精确路径与身份

- 构建 B238：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v238-ram-panic-83e87b997704427faf54a248b03c3aa0`
- 源码 S238：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v238-ram-panic-83e87b997704427faf54a248b03c3aa0`
- 父构建 B237：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v237-panic-identity-fe0210f9e7fc49a0a6df60de689992dd`
- 独立运行目录 T238：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v238-metal-trial-83e87b997704427faf54a248b03c3aa0/root-trial`
- tag：`83e87b997704427faf54a248b03c3aa0`
- scope：`single-K80-ios26-gpu-v238-ram-panic-300s-83e87b99`
- kernel SHA256：`a10164090a5167b32312fc55a7cc296c001080c48532486d70866cf1e44c0a09`
- boot SHA256：`81930c11c2a91d809f6497cafbea137f357b795443d55beeea5c5c3663ab3442`
- FD SHA256：`1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab`
- ADT SHA256：`9bc3124329f66ba4a21fc8dd2e5941a18dab90813ed9ec9672341c0e91c15494`
- 根镜像 SHA256：`193e5f01df3b0481412a980f4e7c562401762af53ffe2ea051fee11b66f5fc0e`
- 普通用户态 probe tag 仍为 `65f3efb4a587473a9caebe54d7a99aea`，不要与 kernel/CDC 身份混淆。

完整路径、固件、启动器、FAT五成员、根镜像和配置在 B238/boot-package/verified.json；所有实际1398个链接输入见 full-link/exact-inputs.json。新编译24个对象，保留1374个，无未定义符号。FAT仅 kernel 改变，FD/ADT/菜单/启动器/根保留。`/tmp/zorn-v238-path` 只是便利指针，接手以此处精确路径和哈希核对，不能仅相信 /tmp。

## 日志缺失调查与 v238 改动

v237/panic-init-source-audit/result.json：所选 pe_init.o 按原配方重编逐字节相同；实际预处理走设备树 pram/embedded-panic-log-size 分支。实际打包 ADT 经已有 codec 解析并原字节 roundtrip，两个属性均缺失。参考启动器源码未搜索到它们的注入；**参考源码尚未完成对实际 EFI 的精确构建溯源，不能将这点写成硬件证明。**

S238/pe_init.c 是实际所选公开 PE 源文件的独立副本。增加 `ZORN_RAM_PANIC_LOG238=1` 编译开关，仅允许 ZORN+iOS 配置；静态16KiB对齐、`262144 + sizeof(embedded_panic_header)` 字节 BSS。PE_create_console 调用原 check_for_panic_log 后，再调用 zorn_init_panic_ram238。只有 gPanicBase、gPanicSize、panic_info、panic_text_len 全零才接入该 RAM；任何已有或部分初始化状态均原样保留。一次正常启动初始化，不在 panic 中分配、映射、写存储或重新清空。原生 header、debug_log_init、debug_putc、CRC 和 panic 流程保留。

源补丁与初始测试：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-panic-ram238-offline`。修改前后逐字节恢复检查已过。正常编译原配方外仅加专用宏和独立源码路径。构建 S238 其余文件相对237仅两个现有文件 retag，无 GPU 功能改动。

新增 RAM 激活了此前没有区域时不运行的原生 debug_log_init/ext_paniclog_init，**这是真实行为变化和风险**；离线测试不能证明真机不会出现嵌套 panic，也不能保证完整 panic 执行到导出点。有限缓冲区不等于所有启动历史；msgbuf仍为有限并发环快照。

## 已完成验证及证据边界

- full-build-review.json：1398实际输入哈希、53相关头依赖、独立输出与身份字节核对。
- identity-dependency-check.json：5个实际身份依赖均正确 VFS 映射；USB不自行 include 身份头，保留237从 Recovery 传入身份的修复。IOUserClient/debug/pe_init 缺少的 .deps 用原参数仅预处理生成，不改对象。
- startup-source-audit/result.json：实际选中的 arm_init、startup、machine_routines_common、ext_paniclog 按原 recipe 重编均逐字节相同。源码 PE_create_console 位于 arm_init 的 machine_startup 之前；machine_init 在正常 VM 初始化后调用 debug_log_init。
- segment-layout-check.json：只读 Mach-O 载入命令/节元数据，__DATA/__bss 为可写 zerofill，3946348→4235884字节（含对齐）。不读取指令、不解析 panic 地址；节信息本身不证明真机内存生命周期。
- panic-init-host/result.json：实际新增初始化函数、原生头/偏移/写入函数、实际 arm64 debug_log_init 分支及扩展区指针保护。15种已有/部分状态保留，256KiB边界加100次超量写入，重复初始化保留数据，扩展区边界停止写入，ASan/UBSan通过。ext_paniclog分配器用主机计数器替代，不宣称真实内核分配成功。
- raw-packet-host、raw-reason-host：C/Python原始字节一致、CRC/尾标记/部分包/损坏包、va_copy/首次赢家/截断/非法尺寸，ASan/UBSan及相关TSan通过。
- terminal-host、terminal-loop-host、terminal-race-host：实际源码单次START/29拒绝、DMA失败保留、正常完成清理、100组竞争和1000启动发布拒绝，TSan通过。MMIO/cache/clock为明确主机边界替身，不宣称硬件通过。
- progress-host-check、progress-parser-check、terminal-parser-check、progress-capture-check：实际producer、52普通parser、新原始包边界与保存、历史日志不覆盖，通过。
- terminal-source-review.json 区分本轮重跑与按源码哈希明确复用的旧测试；没有把旧硬件验收转给238。
- boot-package/verified.json：完整FAT/Android启动包回读、原实际加载器输入解析器检查、原shim/FD/ADT/菜单不变。
- runner-source-review.json：29拒绝条件通过，包括新增 RAM 选择、源绑定、host/startup/segment结果；check-only.json exit0，明确无USB、无claim。

保留失败的离线测试构造：panic-init-host-initial-extraction-failure 是函数名子串误匹配 extended_debug_log_init；check-segments-initial-ambiguous-section.py 是只按 __bss 名称误选段。均修正后重跑，未修改目标内核以迁就测试。测试输出中的 PASS237/227 等旧文本来自复用测试函数，真实执行路径与本轮结果以 B238 文件为准。

## 固定工具与接手前必须完成的事情

新文件：

- UniXNU-zorn/scripts/zorn_ios26_gpu_v238_metal_trial.py
- UniXNU-zorn/scripts/read-zorn-gpu-metal238-cdc.py

它们由237固定工具最小派生，加入 RAM 源及host/startup/segment证据绑定。bundle、owner、ready、admission已独立生成；claim不存在。本轮没有bootstrap、设备重试、刷机恢复或根安装。candidate.json 的 hardware_trial_ready 仍 false，表示尚待接手者完成下列审阅，不要直接改成true跳过检查。

1. 核对本文列出的输入与 B238/boot-package/verified.json、bundle 以及当前源码，确认无人同时运行旧工具。核对 CURRENT 实际状态及 one-shot.claim.json 仍不存在；历史“空闲”不代表现在空闲。
2. 完成参考启动器源码与实际所选EFI的构建来源/内存生命周期核验。参考源码 DarwinBoot.c 会按 Kernel.End 覆盖分配区，先 ZeroMem(Used) 再复制各段 FileSize；但尚不能仅凭参考路径宣称实际EFI已逐字节复现。查既有加载器证据/构建配方，不反汇编、不猜地址。
3. 审阅新runner差异和ready硬件待验证项；必要时完成当前版本真实receiver的本地PTY回归（238尚未重跑large-PTY；237同捕获逻辑已有通过记录，不能冒充238新结果）。当前preview capture检查确实重跑，但它不是新238实际入口的全部测试。
4. 运行离线 check-only（不消耗claim）：

```sh
/opt/homebrew/bin/python3 -B /Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/zorn_ios26_gpu_v238_metal_trial.py --bundle /Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v238-metal-trial-83e87b997704427faf54a248b03c3aa0/root-trial/bundle.json --check-only
```

5. 在以上审阅以及固定工具内部Recovery身份/保护条件满足后，唯一设备入口为 B238/launch-command.json 所列的 receiver-first 命令：

```sh
/opt/homebrew/bin/python3 -B /Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/read-zorn-gpu-metal238-cdc.py
```

**上述命令本 Agent 未执行；这是交接给续接者的入口，不是要求跳过剩余检查立即启动。** 不单独执行inner runner、不复用237/236 claim、不重跑同一候选。receiver SHA256：0756f421955c966a085ffcd5a9c30da0400994db1791809da24f5fc76ea75ef4。改动任何已绑定文件后必须重新处理归档/检查，不能简单修改bundle哈希绕过门禁。

## 真机验证范围、停止条件和数据保护

只允许92988a43/zorn/slot a，现有核验过OrangeFox/TWRP，existing ADB server only。原Android/iOS17/Data不可破坏；unixnu64 sda35绝对LBA47271680，iOS26根相对6291712、8388608块，Data相对4194304；唯一日志4KiB相对2291712。新RAM区域不新增任何磁盘布局或写窗口。229根已装63页10组，receipt和保护边界在bundle；本候选不安装根。

独立300秒看门狗、600秒有界Recovery；正常终止20秒、panic/停止90秒并受实际deadline限制，沿用原代码。receiver先准备、一次尝试。无法确认回Recovery立即停止设备操作并保存证据，不依赖按键/触屏/插拔，不bootstrap、不刷机恢复。硬件执行状态不明或DMA未确认停止时保留资源，不据host收到包推断DMA已静止。正常完成仍沿用真实生命周期清理，不能所有对象永久泄漏。

本次仅硬件能验证：新增区域真实初始化、原生paniclog写入未造成嵌套故障、导出是否可用/完整、CDC控制器资格和传输、精确身份/CRC/尾标记、自动Recovery和完整保护回读。若GPU继续到pipeline/render可记录，但不能预设已通过。原包最大400KiB，一次DMA，预分配528KiB，总39帧/529408B；不分块重用，不新增UFS panic写。

返回后先确认Recovery，再记录run/claim/cdc-capture/原始分段/保护与BCB证据，更新候选和porting记录。协议仍236，原始文件名 panic236-reason.txt、panic236-paniclog.txt、panic236-msgbuf.txt 在238 trial内属正常。paniclog文本原样保存；严格禁止任何反汇编、逆向、指令解码、地址符号化或PC/寄存器/回溯解释。读取普通panic原因文本允许，不再退回只报枚举方案。

## 上游依据与后续GPU主线

[官方日志采集](https://unixnu.com/zh/porting/log-capture)、[官方调试](https://unixnu.com/zh/guide/debugging)。精确源码归档：`/Volumes/macData/projects/ios-zorn/out/zorn/panic-log-source-research-20261115/sources.json`，包含UniXNU-sheng 24aab96163799cb1db083d94539a5eefc07e0475、ShengUfs b6fe07b307eeddc5e258c9d5d4387b968a55e4e9、OnePlus-Ace5 aaa100d19f6fb14e5897a7e496edf7838d4d4e9f。不能照搬其他机型存储窗口或执行其binary cave/entry patch脚本；logs panic只是已有文本过滤，UART须真实线路/后端，当前用K80实际CDC。

日志就绪后回到GPU PAC根因：从公开源码接口、回调签名、对象/线程生命周期和实际编译输入查证。已有IOService/IORegistryEntry/OSObject/IOAcceleratorES以及IOMemoryDescriptor/NativeAdrenoMemory的源码ABI审阅未证实缺陷；不得因此盲关PAC或混链旧OS对象。旧222/223普通Metal小图像曾有局部证据，但stderr dropped33，非完整严格验收；IOSurface/显示呈现及触控完整验收仍未完成。目标维持完整GPU/Metal/显示/触控和正常退出/失败处置，不缩为日志专项。

旧交接与实机证据见 [v234及后续追加记录](handoff-2026-11-15-k80-ios26-gpu-v234-active.md)、[v237实测](evidence/k80-gpu-v237-panic-identity-observed-2026-11-16.json)。不删除17产物、不提交或推送Git、不建立定期任务。源码/配方/测试脚本均保存在B238；保留现有无关工作树修改。

## 续接实测（2026-11-16，覆盖本文未启动状态）

已完成真实所选EFI精确复建：原路径/原配方生成的整文件SHA与所选ccae7c1d一致；独立路径复建不一致的结果保留，未解释机器码。原loader工作区完整归档并恢复。v238实际receiver本地PTY402350B逐字节通过，check-only通过。新增核验记录在B238/continuation-preflight-review.json。

v238只执行一次receiver-first试验，89.956秒自动回TWRP。inner exit0/receiver exit1，0字节、无端口，单日志块未变化且拒绝旧artifact；未确认XNU进入、RAM日志初始化或GPU执行，不按时间推断panic根因。保护区回读相同、完整BCB回读和尾部保护通过。claim已消耗，不重试238，不修改既有bundle。证据见[evidence/k80-gpu-v238-ram-panic-observed-2026-11-16.json](evidence/k80-gpu-v238-ram-panic-observed-2026-11-16.json)。GPU PAC根因仍未知。

后续239已单次取得原生paniclog并自动回收，当前状态以[v239交接](handoff-2026-11-16-k80-ios26-gpu-v239-active.md)为准。

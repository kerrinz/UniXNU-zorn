# 2026-10-27：按 UniXNU 官方流程重新核对 zorn

本次是对正在进行的移植复核。最后一轮 `20261027-212708-8f96ce91` 已自动回 recovery，
取得新日志后停止新增试启动。保留当前镜像和缓存，不执行 clean，不改分区或槽位。
唯一目标仍为 92988a43；f85d4270/pyxis 不操作。

## 结论与准确进度

按官方 [bring-up 阶段](https://unixnu.com/zh/porting/bring-up)，目前到达第7阶段的用户态，
图形系统仍未通过。UEFI、菜单、DarwinBoot、CPU0 的 XNU/EL0、UFS 只读 OS/SystemOS
和原版 launchd 有真机证据。独立 RAM Data 的文件读写通过，但不是完整或持久 Data 资格。
曾有一轮机主确认苹果标志；相同镜像也不能稳定复现，不能称为进入桌面。
第5阶段的平台完整性仍欠同步、内存压力和长期运行验证，不能因已进入用户态就略过。

本次已阅读官网移植步骤、平台、显示、GPU、4 KiB 页表、源码补丁和迁移指南，
并核对本地固定版本的 CLI 实现、实际 status、配置、补丁和原版系统输入。
官网 CLI 页面正文未能由网页工具取得，CLI 细节以本地该提交的 docs/zh/reference/cli.md
与实际 `./unixnu --help` / `status --json` 交叉核对，未假定新版文档与旧配置完全相同。

## 1. 构建基线与仓库规范需要补齐

官方 [移植步骤](https://unixnu.com/zh/porting/steps) 和
[迁移指南](https://unixnu.com/zh/porting/migration)要求明确的 profile、组件依赖、
硬件 DTS、固定版本和可重放的补丁序列。

实际 status 显示 schema_version=1，输出仍为 UniXNU/out/zorn，profiles 只有 device，
components 与 patch_order 均为空。格式1的 archives 仍实际构建了驱动，空组件数组不能
解释为「没有驱动」，但当前报告也不能替代格式2的依赖与顺序核对。
设备还没有 feeds.toml、正式硬件 DTS/SoC DTSI、porting.toml、设备 AGENTS.md 等格式2输入。
主仓库仍依赖三个本地 CLI overlay；成功构建依赖已补丁源码树、编译记录和历史预链接输入。
完整干净重放仍未通过，不能发布为全新克隆一键复现。

版本选择本身没有发现混用：目标 iPad7,1/j120ap、17.7.11/21H461，XNU 固定为
10063.141.1/d8b80295118ef25ac3a784134bcf95cd8e88109f。BCM2837 是官网用于4 KiB
布局的 XNU 构建机型，不意味着错误地把 K80 当成树莓派。
当前主仓库提交为16e592abee8a550dec8154ed1f38b5ebc4f16213。

修正方向：在独立输出目录建立可重放基线，先清点脚本的硬编码路径和旧候选依赖，
再整理 series、DTS 和组件选择。保留现有可取日志的基线，不能直接 clean 或只把
schema_version 改成2。没有为通过格式检查而建立空 package 或虚假的能力记录。

## 2. 早期临时绕过不能继续当作稳定平台适配

[源码与补丁流程](https://unixnu.com/zh/xnu/source-and-patches)要求固定版本、有序应用、
构建检查和受影响阶段的设备验证。当前72份板级补丁混有观察代码、实际硬件适配和临时绕过。
重点复核项：

- zorn-rwlock-noref 在观察标志开启时能强制清 INTERLOCK，或在原子重试失败后直接写锁字；
  还修改 can_sleep 和抢占相关路径。它改变同步语义，不是纯日志。
- zorn-voucher-nolock 去掉 thread_set_mach_voucher 的 thread mutex，原本受锁保护的
  started/voucher 更新现在没有同等同步保证。
- zorn-macr-reenter 改写 MAC 读检查、凭据及重入处理，需要单独证明行为。
- 旧 zorn-local-tlbi 曾将两个 ASID 清理函数置空。已用当前 CPU0 的完整本地 vmalle1
  补回，归档内核指令核对通过；这不代表 SMP 广播清理和全部平台问题已经解决。

这些改动需要在隔离配置中逐项恢复原语义，回到实际中断、抢占、内存属性或调用约定定位。
不能只因绕过了某次停机或某个断言就认定该机制已适配。当前不贸然整体删除，避免丢失
唯一可调试基线；也不再叠加同类强行放行。

## 3. CPU 显示与用户态渲染必须分开

官网 [显示流程](https://unixnu.com/zh/porting/display)先验证 CPU 呈现、交换完成和
IOSurface 生命周期，再进入 GPU 呈现。GopFramebuffer 的 CPU 路径从已有 surface
复制像素到固件 framebuffer，并完成交换；它不是一个完整的软件 Metal/OpenGL 渲染器。
因此一次苹果标志或客户端连接不能替代 SpringBoard/backboardd 的渲染初始化验证。

最新8f96ce91轮次：显示 clients=4，accepted/transfers=0；backboardd[37] 最后匹配
IOAcceleratorES，原返回 status=0、没有返回 iterator。IPC 2881 已由实际生成的 MIG
server 确认是 io_service_get_matching_services_bin。这个结果是具体线索，尚不能单独
证明整套桌面只被这一项阻塞，仍需区分匹配结果与分配等失败情形。
SpringBoard 的最后请求接收方是 notifyd；不能根据前一轮 PID99 直接猜服务身份。

[GPU 指南](https://unixnu.com/zh/porting/gpu)明确区分硬件后端、前端、渲染和呈现。
官方 Adreno740 的硬件范围是 A740/SM8550，不能直接作为 K80 的 A750 后端。
本地 NativeOfflineAccelerator 源码也明确仅作未发布的对象生命周期验证，不能当作
已经可用的软件加速器或通过注册空服务解决等待。

按机主要求继续搁置 GPU 硬件适配。下一步先查清17.7.11是否有实际可用的软件渲染/
兼容路径，以及该路径的具体依赖；验证前不能承诺完全不涉及加速器接口就可进入桌面。
不伪造 IOAcceleratorES 成功、渲染结果或 fence 完成。

## 4. 对三项 OS profile 修补的解释已纠正

只读按原版 subcache 映射和 UUID 匹配的局部符号定位得到：

- .15+0x421e8bc 位于 AttentionAwareness 的 +[AWAttentionAwarenessConfiguration initialize]。
- .13+0x1b05bec 与 .13+0x1b05b08 位于 PosterBoardServices 的两个路径属性处理 block。

它们属于选定 OS profile 的启动兼容修补，不是关闭 GPU 等待或提供 CPU 渲染的开关。
此前统称为「显示启动补丁」容易造成误解。原字节均只读核对通过；实际内核显示
parsed=3/applied=0，所以运行时生效尚未证实。也可能尚未执行到对应路径，不能把0
直接当作 GPU 等待根因。源码中修补位于签名验证慢路径，还需核对快路径、实际 vnode
名称/页偏移及调用覆盖。保持原始签名验证和字节匹配，不用无条件改指令来代替分析。

## 5. 存储、Data 和 OS 服务仍有边界

[平台与 OS 服务指南](https://unixnu.com/zh/porting/platform)要求验证真实接口和所需
状态/通知。现有 UFS/原版 IOStorageFamily/APFS、owner 卷身份、SoftwareAES 与原版
IOSurface ABI 是已经取得的进度，应保留。8 GiB 连续窗口能运行，不等于12 GiB全内存、
SMP或完整压力测试已通过。

RAM Data 为独立512 MiB逻辑APFS，重启丢失；seed 明确 ownership_preserved=false。
本轮实际 reads=74/writes=800/errors=0，不支持「当前就是内存不足」的推断。
后续还要用真实 errno 和原版需求核对 uid/gid、目录模式、迁移、所需状态通知及容量，
Data 的基本文件测试不能替代原版 OS 服务初始化验证。

本次不重写 userdata、不刷 boot/super/vbmeta、不改槽位。已批准的日志仍为原来的一个
4 KiB块，BCB仍只改恢复命令并保留尾部；手机最后处于 recovery。

## 后续顺序

1. 冻结8f96ce91及输入/审计/日志，保存官方流程复核结果。
2. 在独立构建输出整理补丁与编译依赖，优先隔离同步、抢占、MAC 和页表临时绕过；
   先重获可靠的单核、定时器、内存和存储基线，再继续用户态试验。
3. 明确 IOAcceleratorES 查询及17.7.11软件渲染路线，补足实际必需的 OS 服务依赖；
   保持 GPU 硬件适配搁置，不以空服务或跳过等待代替实现。
4. 分别验证 OS profile 修补和 RAM Data 元数据/初始化要求，每轮只隔离一项。
5. 将已验证输入迁到格式2，补齐 DTS、feeds、组件、series 与 porting 记录；稳定界面后
   再适配触控，发布时逐项写清源码检查、构建检查与真机通过范围。

这次复核没有重置源码、升级 OS、迁移格式或新启动手机。以上是完成的核对与后续修正顺序，
不是宣称这些后续工作已经完成。完整原始输入仍在忽略的 out，Git 中只保存说明和证据。

# zorn 内核补丁

这些补丁跟在 UniXNU 的 `patches/xnu` 后面应用。它们在屏幕色条下方留一个状态词，接上只读 UFS 探针，并在没有把根卷切回恢复盘的情况下继续启动。

2026-10-28 新增第 63 个 z 的 `zorn-gui-user-stacks`：默认关闭的有界用户栈读取，
只在定时 GUI 观察线程释放 task 锁后调用原版 VM 接口，最多 16 层；
ZORNLOG9 固定保存样本时间与真实错误，同一 4 KiB 日志写入范围不变。
多核汇编修正另存 `native/smp`，尚未装入默认内核；不是本补丁系列中的 SMP 启用。

本目录不叫 `xnu`。设备仓库里的 `patches/xnu` 会整份替换基础仓库的补丁模块，内核就编不过去。用 `scripts/install-zorn-patches.sh` 把这里的文件复制到 UniXNU 检出的 `patches/xnu/`，再运行 `./unixnu build kernel`。

色条下方同时只留一个词，后写的盖掉先写的。`MEND` 是早期曾到达的里程碑；
2026-10-27 已进入用户态，已解除 Image4 ignition_blob 等待，已通过真实 SystemOS 挂载及 owner 授权，继续验证共享缓存。
启用纯日志后屏幕词可能停留在旧阶段，以持久日志和主 README 的状态为准。

| 补丁 | 作用 |
| --- | --- |
| `zzz-zorn-early-bars` | 入口处的色条 |
| `zzzz-zorn-c-bands` | 色条，以及色条下方的状态词 |
| `zzzzz-zorn-timebase` | 时间基 |
| `zzzzz-zorn-dt-panic` | 设备树失败时把 panic 留在屏幕上 |
| `zzzzzz-zorn-vm-bands` | 虚拟内存阶段 |
| `zzzzzzz-zorn-startup-bands` | `startup` 阶段 |
| `zzzzzzz-zorn-bsd-stages` | `bsd_init` 阶段 |
| `zzzzzzzz-zorn-mount-skip` | 跳过会停住的挂载等待 |
| `zzzzzzzz-zorn-root-wait` | 根卷等待 |
| `zzzzzzzz-zorn-launch-trace` | `launchd` / `exec` 跟踪 |
| `zzzzzzzz-zorn-machload-trace` | Mach-O 加载跟踪 |
| `zzzzzzzzz-zorn-namei-trace` | 路径查找 |
| `zzzzzzzzz-zorn-csblob-trace` | 代码签名 |
| `zzzzzzzzz-zorn-panic-say` | panic 时画返回地址 |
| `zzzzzzzzz-zorn-pmap-trace` | `pmap` 跟踪 |
| `zzzzzzzzzz-zorn-macr-reenter` | MAC 策略重入 |
| `zzzzzzzzzz-zorn-read-wait` | 读路径上的等待 |
| `zzzzzzzzzz-zorn-rwlock-noref` | 读跟踪期间的独占锁，并画出调用者。`lck_rw_lock_shared_b` / `exclusive_b` 入口先清可睡眠位 |
| `zzzzzzzzzz-zorn-thread-state` | 线程状态 |
| `zzzzzzzzzz-zorn-vmap-trace` | `vm_map` 创建 |
| `zzzzzzzzzz-zorn-vnop-read` | `VNOP_READ` 跟踪，并在这次读取里打开中断恢复 |
| `zzzzzzzzzz-zorn-vnrd-trace` | `vn_rdwr` 跟踪 |
| `zzzzzzzzzzz-zorn-map-delete-trace` | `vm_map_delete` 的阶段词：`MDEL`、`MWAT`、`MWIR`、`MUNW`、`PREM`、`MEND` |
| `zzzzzzzzzzz-zorn-zalloc-nofail` | 读跟踪把中断关掉之后，进 `zalloc` 前先恢复 |
| `zzzzzzzzzzzz-zorn-stack` | 内核栈 |
| `zzzzzzzzzzzzz-zorn-local-tlbi` | 运行时 TLB 作废只打当前 CPU。全 ASID 作废不完成，销毁页表时跳过 |
| `zzzzzzzzzzzzz-zorn-pmap-nosleep` | 拿 pmap 锁之前清掉可睡眠位。`lck_rw_lock_shared_b` 看到该位会断言 |
| `zzzzzzzzzzzzz-zorn-ufs-call` | 调用只读 UFS 探针 |
| `zzzzzzzzzzzzzz-zorn-os-mount` | 把 OS 容器登记成只读 `md0`，并挂上 apfs |

`MDEL` 是进入拆表。`MWAT` 是有条目正在切换，准备等待。`MWIR` 是条目仍被钉住，准备等待。`MUNW` 是准备解除钉住。`PREM` 是准备从页表摘掉映射。`MEND` 是两次拆表都已返回。`LTLB` 表示本地全 ASID 作废已经发出，紧接着的屏障没有返回。下一颗不再发这条作废，也不做这道屏障，直接画 `PLOC`。


后续无人值守诊断补丁：`zorn-hint-return` 添加 `SAVR`；`zorn-insert-return`
添加 `INMR/I4KR/IRET/VMRT`；`zorn-log-only` 在 UFS 就绪后可跳过状态词
画屏与其 DAIF/cache 操作；`zorn-panic-log` 保存完整 panic 原因到 UFS。
独立超时回收在 `native/ufs-read/ZornWatchdog.h`，依据 K80 原厂 Gunyah ABI。
`SAVR` 已回收成功；IRET 那一轮实际停在更早的 CSMAC，随后纯日志与看门狗
试验已记录到多次 IRET/VMRT，不能把屏幕上的单词当作唯一的停止证据。

`zorn-pmgr` 在 UFS 日志和独立看门狗就绪后调用板级 PMGR 适配。
`native/pmgr` 复用与当前 iPadOS 完全相同的原版 ApplePMGRNub，
先验证对象生命周期，再验证服务发布；不提供尚未实现的硬件电源操作。

`zorn-amfi-worker`、`zorn-thread-create-observe`、`zorn-copyin-observe`
仅为 native XNU 边界增加有界观测。最后一项将用户拷贝记录限定到触发
Mach 分配的当前线程。`TIM` 是 UFS 日志就绪后的十六进制毫秒数；
`KPC/KFH/KFL/KES` 保存缺页指令、故障地址和 ESR。
2026-10-27 已捕获 `_bcopyin+0x34` 同址权限故障循环；板级 defconfig
补选官方 ARM64 配置原有的 `CONFIG_XNU_NATIVE_PAN`，以验证访问切换。

恢复调试后，`zorn-image4-observe` 保存 UFS 就绪前的原版 Image4 服务/回调
边界及实际 mutex gate 调用；真机已确认等待缺失的 IOAESAccelerator，接入
上游 SoftwareAES 后打开锁门。`zorn-user-trace-compact` 不重复记录 write
SVC 的入口/返回，保留其实际文本及其他系统调用。`zorn-owner-cache-observe`
只记录现有 owner mount 函数的 stage/error/authorization 结果；它不改变挂载
或授权决定。VerifiedRoot 签名打开、真实读取和 OS 根卷授权已在真机通过，真实 SystemOS 挂载及 owner 授权现已通过。
`zorn-systemos-path-observe` 与 `zorn-systemos-path-buffer` 保留路径 errno/type/device；
`zorn-systemos-mount-printf` 被动缓存挂载期间原始 printf，返回后才写日志。

`zorn-hash-progress` 记录实际签名文件与已通过原始签名验证的 chunk 进度；
仅在显式、有界预算内 pet 诊断 watchdog，保留全部原始验证决定。

`zorn-ram-data-mount` 核对独立 RamBlock 的真实种子哈希、容量、卷 UUID、设备号、
可写 APFS 状态，并以正常 vnode API 创建、同步写入、重新打开读回、删除临时文件。
它只作用于 RAM Data；`DPT=7 / DPE=0` 和实际块写入已在 K80 通过。
`zorn-service-observe` 为实际 exec image activation 添加只观察的开始/返回记录；
`zorn_service_trace=1` 过滤重复启动通知，保留实际装载和错误，不改变 exec/write 返回值。
`zorn-display-init-order` 把可选 GopFramebuffer 初始化移到 zorn UFS 日志、watchdog、
PMGR 就绪之后。三者与原版 Apple 二进制修改无关。

`zorn-8g-bootstrap-capacity` 将非 Apple 4 KiB bootstrap 池从 16 页扩大到
32 页，覆盖 8 GiB 双映射最多 21 页的需求；不改原版 kext 虚拟地址布局，
保留现有分配越界保护。高地址 UEFI 分配已获照片证明；
`20261027-131211-d3dc6081` 已产生新 UFS 日志、通过 SYSOK/PMOK2 并自动回收。

`zorn-gui-observer` 为显式 zorn_gui_watch=1 增加有界关键用户进程采样及真实退出状态观察。
初版用户栈读取随后由 zorn-gui-log-snapshot 移除；当前每次只采最多 4 线程的寄存器，
最多 12 次、默认关闭。普通采样不 pet watchdog，已通过真机回收。

`zorn-gui-log-snapshot` 增加仅 XNU 导出的公共诊断头、同块固定快照及无用户 VM
读取的寄存器采样。`zorn-gui-exit-detail` 在 osfmk 采退出寄存器，BSD 只复制
有界内核原因。`zorn-gui-observation-window` 为显式 30..180 秒启动观察增加
独立有界 pet；默认 watcher 保持不喂狗。真实苹果标志与后续 union 试验见 GUI 进度文档。

`zorn-gui-configuration` 为固定日志增加实际内核参数和四个固定库/cache 路径的被动查询，
避免服务文本覆盖关键状态；新 ZORNLOG4 仍为同一个 4 KiB 块，读取器兼容所有旧格式。

`zorn-asid-full-invalidate` 修复早期 zorn-local-tlbi 将 ASID 清理置空的遗漏：
在当前 CPU0 上以全量本地 vmalle1 覆盖原请求，保留完成屏障。与显示/原版库补丁无关，
编译与指令审计通过，真机稳定性仍需单独记录。

`zorn-gui-ipc-observer` 仅在显式 GUI 观察时保留 launchd/SpringBoard/backboardd
各两条已复制内核头的发送尝试标量，使用原版带锁 receiver-PID accessor；
不读取用户正文、不改变 IPC 返回值、IPC 路径无 UFS 写入。定时器另行打印缓存和
最多 512 字节的进程名/PID 目录，目录可能截断，不将发送尝试当作送达或服务响应。

`zorn-gui-ipc-fixed-log` 将六条 IPC 请求标量也保存在同一块固定区，防止用户态高频
日志覆盖；ZORNLOG5/GUI版本4、总4096字节，旧格式读取保持兼容。

`zorn-gui-service-observer` 只读记录 IPC 接收进程名及原 IOKit 匹配字典中的 provider
类名、原结果和 iterator 指针是否非空；不遍历原 iterator 或改变匹配。ZORNLOG6 保持同一块。

后续GUI补丁的实际结果见GUI进度文档。当前63z..71z依次保留有界用户栈、
lsd控制进程/线程窗口、RAM Data元数据、900秒观察、lsd IPC匹配、真实Data容量/UUID、
可选CPU0内核栈和最终快照刷新。v14/v15仍使用同一4096字节日志块，深内核栈物理读取尚未实测。
72z只把显式观察扩展至1800秒，较长轮次改为30秒周期、最多60次；
pet仍受原日志epoch绝对期限控制，独立watchdog保留。30分钟候选目前仅完成构建和宿主边界检查。

# zorn 内核补丁

这些补丁跟在 UniXNU 的 `patches/xnu` 后面应用。它们在屏幕色条下方留一个状态词，接上只读 UFS 探针，并在没有把根卷切回恢复盘的情况下继续启动。

本目录不叫 `xnu`。设备仓库里的 `patches/xnu` 会整份替换基础仓库的补丁模块，内核就编不过去。用 `scripts/install-zorn-patches.sh` 把这里的文件复制到 UniXNU 检出的 `patches/xnu/`，再运行 `./unixnu build kernel`。

色条下方同时只留一个词，后写的盖掉先写的。`MEND` 是早期曾到达的里程碑；
2026-10-27 已进入用户态，当前停止在 Image4 ignition_blob 处理函数。
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

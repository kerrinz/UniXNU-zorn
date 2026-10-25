# zorn 内核补丁

这些补丁跟在 UniXNU 的 `patches/xnu` 后面应用。它们在屏幕色条下方留一个状态词，接上只读 UFS 探针，并在没有把根卷切回恢复盘的情况下继续启动。

本目录不叫 `xnu`。设备仓库里的 `patches/xnu` 会整份替换基础仓库的补丁模块，内核就编不过去。用 `scripts/install-zorn-patches.sh` 把这里的文件复制到 UniXNU 检出的 `patches/xnu/`，再运行 `./unixnu build kernel`。

色条下方同时只留一个词，后写的盖掉先写的。2026-10-26 的真机停在 `MEND`：`vm_map_destroy` 里的两次 `vm_map_delete` 都已返回。

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
| `zzzzzzzzzz-zorn-rwlock-noref` | 读跟踪期间的独占锁，并画出调用者 |
| `zzzzzzzzzz-zorn-thread-state` | 线程状态 |
| `zzzzzzzzzz-zorn-vmap-trace` | `vm_map` 创建 |
| `zzzzzzzzzz-zorn-vnop-read` | `VNOP_READ` 跟踪，并在这次读取里打开中断恢复 |
| `zzzzzzzzzz-zorn-vnrd-trace` | `vn_rdwr` 跟踪 |
| `zzzzzzzzzzz-zorn-map-delete-trace` | `vm_map_delete` 的阶段词：`MDEL`、`MWAT`、`MWIR`、`MUNW`、`PREM`、`MEND` |
| `zzzzzzzzzzz-zorn-zalloc-nofail` | 读跟踪把中断关掉之后，进 `zalloc` 前先恢复 |
| `zzzzzzzzzzzz-zorn-stack` | 内核栈 |
| `zzzzzzzzzzzzz-zorn-ufs-call` | 调用只读 UFS 探针 |
| `zzzzzzzzzzzzzz-zorn-os-mount` | 把 OS 容器登记成只读 `md0`，并挂上 apfs |

`MDEL` 是进入拆表。`MWAT` 是有条目正在切换，准备等待。`MWIR` 是条目仍被钉住，准备等待。`MUNW` 是准备解除钉住。`PREM` 是准备从页表摘掉映射。`MEND` 是两次拆表都已返回。

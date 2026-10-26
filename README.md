# UniXNU-zorn

红米 K80 12GB+256GB（zorn，SM8650-AB）的 UniXNU 实验移植。目标系统为 iPad7,1 / j120ap 的 iPadOS 17.7.11（21H461，Darwin 23.6 / xnu-10063.141.1）。固件板级包独立放在 `uefi-zorn`。

**2026-10-27 暂停状态：UEFI、XNU、UFS 只读根卷和 PID 1 的早期用户代码已运行，尚未进入 launchd 主循环或 iPadOS 桌面。** 已主动验证第 32 次 EL0 SVC；继续执行时停在 `security.mac.img4.ignition_blob` 的原版 AppleImage4 处理函数。无人值守看门狗会自动回 recovery。

当前进度、测试哈希和下一步见 [进度记录](docs/progress-2026-10-27.md)，可提交的日志摘录在 [docs/evidence](docs/evidence)。日志路径相对于三仓库的共同父目录；原始镜像和完整运行目录不放进 Git。

## 已验证的范围

- UEFI 菜单、DarwinBoot 交接和 1440×3200 framebuffer 工作，倒计时 5 秒。
- zorn 专用 UFS 传输可读 GPT、`userdata` 的 `SHNGROOT` 和 OS 窗口；OS APFS 容器作为 `md0` 只读挂载。
- 两份原版 trust cache 已加载，签名检查通过（`SIGPASS`），`load_init_program` 返回（`INITOK`）。
- EL0 执行及系统调用入口/返回已有真机证据：`mprotect`、Mach VM 分配返回 0，`getpid` 返回 1，第 32 次 SVC 检查点自动回收成功。
- 参照 sheng 的原版 ApplePMGRNub 适配通过对象生命周期、绑定、原版 AON 方法和服务发布检查；完整硬件电源管理尚未实现。
- 补选官方 ARM64 的 `CONFIG_XNU_NATIVE_PAN` 后，修复了 `_bcopyin` 同址权限故障循环。用户访问窗口内保留标准拷贝序列。
- UFS 持久日志、完整 panic、用户 write 文本、sysctl MIB/名称/处理边界、独立 Gunyah watchdog 和 recovery 自动回收均已验证。

SystemOS 窗口已随系统镜像写入 userdata，但当前 zorn 传输尚未将它单独发布、挂载和接入启动链。可写 Data、完整显示/GPU、触控、网络、音频、基带及其他外设尚未完成。当前只描述 CPU0；12 GiB 是标称配置，DRAM 实测和扩大 XNU 引导内存范围仍待完成。

## 设备与写入范围

- `92988a43`：红米 K80 / zorn，唯一目标，活动槽保持 `b`。
- `f85d4270`：小米 CC9 / pyxis，不对它执行操作。

所有定向 adb/fastboot 命令都要带 `-s 92988a43`。`userdata` 已于 2026-10-25 经机主授权改用于系统镜像；当前不具备 Android/iPadOS 双系统共存能力，**不要启动 Android 或重刷这份 userdata**。

内核通过 `fastboot boot` 内存启动。OS 传输回调拒绝写入。已授权的诊断方案只写 userdata 镜像末尾之后的一个 4 KiB 日志块，以及 GPT 选定的 misc recovery BCB 页；BCB 前 864 字节更新为 recovery 命令，其余字节保留，没有 wipe 参数。不要写 boot、super、vbmeta、vendor_boot，不改槽位。

## 文件结构

```text
board.toml                         schema-1 板级配置与原版 IPSW 针
configs/zorn_defconfig             内核配置（含 trust cache runtime、PAN）
native/ufs-read/                   UFS 只读根、受限日志/BCB、watchdog
native/pmgr/                       精确原版 PMGR ABI 适配
patches/zorn/                     板级 XNU 补丁
patches/core/                     本次依赖的主 UniXNU CLI 修改
scripts/install-zorn-patches.sh    安装补丁，--core 同时安装 CLI overlay
scripts/build-zorn-ufs.py          UFS archive 构建
scripts/build-zorn-pmgr.py         私有 ABI 审计与 PMGR archive 构建
scripts/prepare-zorn-trustcache.py 提取并校验两份原版 trust cache
scripts/build-zorn-debug.py        遇错即停的构建/打包流程，可选 --boot
scripts/run-zorn-debug.py          固定设备的内存启动/recovery 回收
scripts/read-zorn-log.py           读取或离线解码 ZORNLOG1/2
scripts/make-zorn-adt.py           当前 ADT 生成器
docs/                             当前状态和可提交的证据
unixnu.lock                       已解析源码提交
```

本设备仍使用旧版 schema-1 布局；尚未迁移到官方当前 schema-2 的 DTS、组件列表和 `porting.toml`。`package/` 不建空目录，避免被识别为设备 kit。`patches/zorn` 通过安装脚本追加到基础 XNU 补丁，不能改名为会替换基础模块的 `patches/xnu`。

## 构建状态与依赖

本次主 UniXNU 基线是 `16e592abee8a550dec8154ed1f38b5ebc4f16213`，XNU 针为 `d8b80295118ef25ac3a784134bcf95cd8e88109f`。当前成功结果来自本机已经应用补丁的 XNU 工作树，以及之前的预链接候选。

**干净检出的补丁重放仍未通过。** 已观察到 boot-progress/early-bars 顺序和 vm-bands 空行上下文冲突；PMGR 构建还需要前一份候选与编译记录。因此下面的增量命令不代表全新克隆可以一键复现。早期锁、TLBI 和 MAC/exec 的试验性修改仍保留，稳定性及完整安全语义尚未验证。

主 UniXNU 中的本地修改已保存为 [CLI overlay](patches/core/README.md)，其中包含现有 AMFI 空字段修补和缓存 kernelcache 的使用。准备专用于 zorn 的主仓库后，从主仓库运行：

```sh
../UniXNU-zorn/scripts/install-zorn-patches.sh . --core
./unixnu defconfig zorn_defconfig -D ../UniXNU-zorn
```

组件源码、SDK、编译记录、IPSW、ADT、恢复内存盘及固件 FD 需预先准备；源码按主仓库 feeds 和本仓库 `unixnu.lock` 取用。`board.toml` 使用公共 IPSW URL，机器本地路径通过 `UNIXNU_IPSW` 或调试构建器 `--ipsw` 指定。IPSW、Apple 二进制、keys、镜像和生成的 archive 不提交。

## 本机增量构建与回收

以下在 `UniXNU`、`UniXNU-zorn`、`uefi-zorn` 的共同父目录执行。先准备原版 trust cache：

```sh
python3 UniXNU-zorn/scripts/prepare-zorn-trustcache.py \
  --ipsw iPad_Pro_HFR_17.7.11_21H461_Restore.ipsw
```

只生成镜像：

```sh
python3 UniXNU-zorn/scripts/build-zorn-debug.py \
  --incremental-patched-tree \
  --ipsw iPad_Pro_HFR_17.7.11_21H461_Restore.ipsw \
  --fd ../Mu-Silicium/Build/zornPkg/DEBUG_CLANGPDB/FV/SILICIUM_UEFI.fd
```

恢复无人值守试验时，在上述命令加 `--boot`。当前按机主要求暂停，不自动启动新的轮次。脚本默认也会寻找共同父目录中的同名本地 IPSW。

每一步失败都会停止流程，`out/zorn/boot.inputs.json` 保存构建状态与输入哈希。回收脚本在 USB 操作之前核对 `ready` 状态和 `boot.img` SHA256；失败构建使用旧镜像的反向控制已验证为零 USB 命令。已有匹配清单的镜像可单独回收：

```sh
python3 UniXNU-zorn/scripts/run-zorn-debug.py
```

脚本核对 zorn 和槽位 b，从 recovery 定向重启 bootloader，再临时启动。180 秒未发现 recovery 就停止。成功后保存 `run.json`、构建输入清单、启动输出和 4 KiB 原始日志到 `out/zorn/debug/<时间>-<哈希前缀>/`，手机留在 recovery。

## 负载与系统卷

UEFI 打包见 `uefi-zorn/README.md`。当前负载是 192 MiB FAT32、512 字节簇，包含内核、ADT、原版 trust cache sidecar 和恢复内存盘。两块原版模块的 bundle SHA256 为 `7416ca4f8377146626bb284e2133c76bee6cb4e3ee0af5d648b186235a7323a7`；`TC00000003` 证明均被内核接受。

恢复盘 `root.img` 展开后为 176 MiB，仍随负载保留；真正的根是 userdata OS 容器 `md0`。当前没有可写 Data 种子。XNU 的 `owned_memory_size` 仍为 384 MiB，和 UEFI 256 MiB 的镜像解压窗口是不同参数。

已写入的 SHNGROOT 镜像为 9382658048 字节，SHA256 `fd43ee7035ce185ce4215ac93fdc006fd784a54b3b7442e21457c226cbe03093`。OS 窗口偏移 `0x100000`，SystemOS 偏移 `0x16a600000`。板级 userdata 的 first/last LBA 仅复现容量，不是实际 GPT 起始地址；运行时由 GPT 按名称定位。

## 日志

日志块是 userdata 分区内第 `2291712` 个 4096 字节块，位于系统镜像结束后 4 MiB。`ZORNLOG2` 是 340 个 12 字节循环槽，另存格式化 panic、用户输出和 sysctl 名称；读取器兼容旧 `ZORNLOG1`。

```sh
python3 UniXNU-zorn/scripts/read-zorn-log.py --save out/zorn/last-log.bin --tail 100
python3 UniXNU-zorn/scripts/read-zorn-log.py --block out/zorn/last-log.bin --tail 100
```

第一条固定从 K80 recovery 只读提取；第二条只读本地文件。`zorn_log_only=1` 在 UFS 就绪后停止刷新屏幕词，因此屏幕旧词不能代表最新执行位置。检查点复位也不能解释成自然故障。详细协议、watchdog ABI 和写入限制见 [UFS 诊断说明](native/ufs-read/README.md)。

## 参考与许可

- [官方 CLI](https://unixnu.com/zh/reference/cli)、[移植总览](https://unixnu.com/zh/porting/)、[bring-up 顺序](https://unixnu.com/zh/porting/bring-up)
- [UniXNU-sheng](https://github.com/UniXNU/UniXNU-sheng)、[同 SoC 的 UniXNU-houji](https://github.com/lonzzi/UniXNU-houji)

本仓库主要使用 [BSD-2-Clause-Patent](LICENSE)。`native/pmgr/ZornPlatformPower.cpp` 改编自 sheng 的 MIT 源码，保留 [MIT 许可](native/pmgr/LICENSE.MIT)；原有上游文件继续使用各自版权头。

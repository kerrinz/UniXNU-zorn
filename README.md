# UniXNU-zorn

**当前进度（2026-10-28）：已进入 iPadOS 系统锁屏，机主在现场确认；当前优先适配触控。** CPU0 保持，多核及硬件 GPU 后置。尚未验证触摸解锁或桌面操作。

[硬件低亮度](docs/progress-2026-10-28-brightness.md)已通过一次完整锁屏启动，DCS307→64并读回64；[Data](docs/progress-2026-10-28-data-smp-touch.md)首次跨重启读回同一初始化标志。第二次复测被亮度交接保护提前拒绝并自动回 recovery，未到 Data；因此尚不宣称重复启动稳定。现有 overlay 保留。

[触控记录](docs/progress-2026-10-28-touch.md)：真实芯片为 FT3683；首轮只读 XNU 探针证明触控 SE 时钟关闭、GPIO未启用。K80 专属 L14/3.2V 与 L12/1.8V 原生交接已在短测走通，时钟开启、控制器空闲。`bce3bdbe` 已实测读到芯片 ID `3683`、固件 `35`，三条读取均首次 CRC 通过并恢复 GPIO；下一步采集真实触点帧。按[启动与抓日志说明](docs/touch-test-instructions.md)回传结果（提供 Windows PowerShell 命令行包，仅需现有 adb/fastboot，无 Python 依赖）。尚无 HID 或物理触摸成功证据。

红米 K80 12GB+256GB（zorn，SM8650-AB）的 UniXNU 实验移植。目标系统为 iPad7,1 / j120ap 的 iPadOS 17.7.11（21H461，Darwin 23.6 / xnu-10063.141.1）。固件板级包独立放在 `uefi-zorn`。

**2026-10-27：UEFI、XNU、UFS 只读 OS 根卷及早期用户态已通过；SystemOS 现已由真实 IOBlockStorageDevice → 原版 IOMedia/APFS 挂载为 `/dev/disk1s1`，owner 授权到达 `OWNOK`。原版 launchd 已进入主循环并启动子服务；尚无 iPadOS 图形桌面。** 已解除原版 Image4 的 AES 等待、raw mdev 的 fsindex/IOKit 资格阻塞，原版 dyld/共享缓存已支持 launchd 执行并生成 ptpd、rapportd 服务日志。UEFI 提前回收和主机 BCB 写入读回已完成真机测试，多轮自动取得新日志。

**本轮新增：512 MiB 逻辑容量的独立 RAM Data 已在真机以 APFS 可写挂载。临时文件的创建、同步写入、关闭后读回、删除和删除后查询均通过（`DPT=7 / DPE=0`）；实际 RamBlock 写请求为 1、错误为 0。这是当时的易失配置；10月28日已接入受限持久 overlay，最新资格见上文。** 见 [RAM Data 记录](docs/progress-2026-10-27-ram-data.md)。

最新显示与崩溃调查见 [GUI 续调记录](docs/progress-2026-10-27-gui.md)。恢复后的进度和测试身份见 [续调记录](docs/progress-2026-10-27-resumed.md)；先前的 [暂停记录](docs/progress-2026-10-27.md) 保留为历史快照。可提交的日志摘录在 [docs/evidence](docs/evidence)。日志路径相对于三仓库的共同父目录；原始镜像和完整运行目录不放进 Git。

## 已验证的范围

- UEFI 菜单、DarwinBoot 交接和 1440×3200 framebuffer 工作，倒计时 5 秒。
- zorn 专用 UFS 传输可读 GPT、`userdata` 的 `SHNGROOT` 和 OS 窗口；OS APFS 容器作为 `md0` 只读挂载。
- 两份原版 trust cache 已加载，签名检查通过（`SIGPASS`），`load_init_program` 返回（`INITOK`）。
- EL0 执行及系统调用入口/返回已有真机证据：`mprotect`、Mach VM 分配返回 0，`getpid` 返回 1，第 32 次 SVC 检查点自动回收成功。
- 参照 sheng 的原版 ApplePMGRNub 适配通过对象生命周期、绑定、原版 AON 方法和服务发布检查；完整硬件电源管理尚未实现。
- 补选官方 ARM64 的 `CONFIG_XNU_NATIVE_PAN` 后，修复了 `_bcopyin` 同址权限故障循环。用户访问窗口内保留标准拷贝序列。
- UFS 持久日志、完整 panic、用户 write 文本、sysctl MIB/名称/处理边界、独立 Gunyah watchdog 和 recovery 自动回收均已验证。
- 原版 AppleImage4 的服务匹配、无限等待和 ignition 锁门已在真机定位。SoftwareAES 适配在链接前后校验 181 个原版 ABI 槽位及两份原版可执行段；接通后已越过此前等待点并验证第 64 次 SVC。

SystemOS 的 raw `md1` 仍用于只读诊断；正常挂载使用原版存储栈实际发布的 IOMedia。历史只读基线为 `/dev/disk1s1`，启用 RAM Data 后为 `/dev/disk3s1`；按 UUID 选择，不固定 disk 编号。真机已通过两个 owner 签名打开、实际区块校验，以及两卷 APFS UUID/只读/设备号授权和 owner manifest 路径。原版 launchd 及子服务已有执行证据，未将每个共享缓存页面或全部子服务的功能都算作通过。完整显示/GPU、触控、网络、音频、基带及其他外设尚未完成。当前只描述 CPU0；12 GiB 是标称配置。live FDT 高地址范围已只读核对，实际 8 GiB UEFI 分配及 XNU/UFS 控制路径通过；整窗内存压力测试和长期稳定性未通过。

## 设备与写入范围

- `92988a43`：红米 K80 / zorn，唯一目标，活动槽保持 `b`。
- `f85d4270`：小米 CC9 / pyxis，不对它执行操作。

所有定向 adb/fastboot 命令都要带 `-s 92988a43`。`userdata` 已于 2026-10-25 经机主授权改用于系统镜像；当前不具备 Android/iPadOS 双系统共存能力，**不要启动 Android 或重刷这份 userdata**。

内核通过 `fastboot boot` 内存启动。OS 传输回调拒绝写入。已授权持久写入包括 userdata 的独立 Data overlay 窗口（10GiB偏移、131077个4KiB块，前像已备份验证），既有单4KiB日志块，以及 GPT 选定的 misc recovery BCB 页；BCB 前 864 字节更新为 recovery 命令，其余字节保留，没有 wipe 参数。不要写 boot、super、vbmeta、vendor_boot，不改槽位。

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
scripts/build-zorn-aes.py          上游 SoftwareAES 构建与前后 ABI 校验
scripts/prepare-zorn-verified-root.py 原始窗口签名及全量 C 验证（主机）
scripts/build-zorn-verified-root.py VerifiedRoot / mdev 卷身份绑定构建
scripts/prepare-zorn-trustcache.py 提取并校验两份原版 trust cache
scripts/build-zorn-debug.py        遇错即停的构建/打包流程，可选 --boot
scripts/run-zorn-debug.py          固定设备的内存启动/recovery 回收
scripts/read-zorn-log.py           读取或离线解码 ZORNLOG1 至 B
scripts/capture-zorn-screen.py     绑定最新 K80 轮次的 USB 单帧采集（无音频）
scripts/check-zorn-runner-observation.py  宿主单帧时序/回收期限控制（无 USB）
scripts/compact-zorn-archives.py   逐份解压核对 SHA 后压缩较旧的生成内核
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

当前候选选用独立 owner 验证路径。既有 `userdata-root.img` 保持不变，先在三仓库的共同父目录准备真实的签名/区块策略：

```sh
python3 UniXNU/kits/VerifiedRoot/tests/check.py \
  --output out/zorn/verified-root-host --openssl-prefix /opt/homebrew/opt/openssl@3
python3 UniXNU-zorn/scripts/prepare-zorn-verified-root.py
```

OpenSSL 路径按本机调整。私钥只在忽略的 `out/zorn/verified-root-host/keys` 内；内核只嵌入公钥和签名策略。两份完整镜像 SHA256 不符、C 验证失败或实际读取区块不符都会拒绝。当前 mdev 适配还会核对实际 APFS 挂载 UUID、只读状态和设备号；签名打开、真实区块读取及 OS 根卷身份校验已获真机证明，SystemOS 现已通过真实 IOMedia/APFS 挂载并完成 owner 授权；raw md1 的失败保留为历史诊断。

## 本机增量构建与回收

以下在 `UniXNU`、`UniXNU-zorn`、`uefi-zorn` 的共同父目录执行。先准备原版 trust cache：

```sh
python3 UniXNU-zorn/scripts/prepare-zorn-trustcache.py \
  --ipsw iPad_Pro_HFR_17.7.11_21H461_Restore.ipsw
```

存储接口注释编译需要固定的公共 IOStorageFamily feed（`e45fbe30…`），在主 UniXNU 目录先运行 `./unixnu fetch IOStorageFamily`。`build-zorn-storage.py` 只链接本仓库只读适配；公共参考对象不链接，原版 IOStorageFamily 可执行段按哈希保持不变。

默认 `zorn_defconfig` 保留已验证的只读基线。独立 RAM Data 使用 `zorn_ramdata_defconfig`：

```sh
python3 UniXNU-zorn/scripts/prepare-zorn-data.py
python3 UniXNU-zorn/scripts/build-zorn-debug.py \
  --defconfig zorn_ramdata_defconfig --incremental-patched-tree \
  --early-watchdog 1 --boot
```

种子准备器只操作本机镜像，拒绝覆盖已有种子；需先具备原始 `userdata-root.img` 与已验证的只读 OS 窗口。构建器从种子清单取得实际 UUID，核对逻辑/编码 SHA256，再生成独立派生菜单和 PackedRAMDisk ADT；OS 仍从 UFS 的 md0 只读启动。主机准备未保留全部文件属主，完整服务权限仍待验证。

当前 8 GiB CPU 显示与有界 GUI 采样候选（需要前述已准备的输入）：

```sh
python3 UniXNU-zorn/scripts/build-zorn-debug.py \
  --defconfig zorn_display_defconfig --display-mode 3 --memory-mib 8192 \
  --checkpoint NOHIT --gui-watch --incremental-patched-tree \
  --early-watchdog 1 --recovery-timeout 300 --boot
```

`--gui-watch` 默认关闭，只观察进程/线程和真实退出状态，最多 12 次。默认采样不喂狗；显式 `--gui-hold-seconds 30..180` 是单独的有界启动观察窗口，要求 `--early-watchdog 1`。
`07ebe68e` 已在恢复连接后自动回收；后续固定快照版本 `dae66d26` 已由机主确认苹果标志。当前独立 `zorn_union_defconfig` 继续验证 SystemOS/OS 只读目录组合与 GUI 退出原因。
镜像身份以各轮 `build-inputs.json` 与 [GUI 续调记录](docs/progress-2026-10-27-gui.md) 为准；此前 snapshot-ram-data 为历史快照。

只生成只读基线镜像：

```sh
python3 UniXNU-zorn/scripts/build-zorn-debug.py \
  --incremental-patched-tree \
  --ipsw iPad_Pro_HFR_17.7.11_21H461_Restore.ipsw \
  --fd ../Mu-Silicium/Build/zornPkg/DEBUG_CLANGPDB/FV/SILICIUM_UEFI.fd
```

无人值守试验在上述命令加 `--boot`。已按机主新指令恢复调试；脚本默认也会寻找共同父目录中的同名本地 IPSW。当前菜单使用不会命中的 `NOHIT` 检查点，由独立 watchdog 回收，以观察自然停止位置。当前 `zorn_hash_budget=120` 只在前 120 秒内、原始签名块实际验证成功时允许 pet；停滞仍由 55 秒 bite 回收。默认主机等待 300 秒，覆盖最晚 pet 后的 bite 与 recovery 启动。

UEFI 提前 watchdog 为显式选项，先用 `uefi-zorn/scripts/build-zorn-firmware.py` 构建并记录 FD，再给统一构建器加 `--early-watchdog 1`。`2` 是在 UEFI 主动停 CPU 的独立测试，不启动内核。主机从 recovery 准备并读回同一页 recovery BCB；若初始在 fastboot，先用固定哈希的已验证镜像临时启动回 recovery。该扩展已完成真机停止测试并自动回 recovery；后续模式 1 的内核 `WON` 确认 watchdog 接管时已开启。bootreason 为空，具体复位源未独立确认。普通镜像不带 marker，不改 UEFI watchdog。

每一步失败都会停止流程，`out/zorn/boot.inputs.json` 保存构建状态与输入哈希。回收脚本在 USB 操作之前核对 `ready` 状态和 `boot.img` SHA256；失败构建使用旧镜像的反向控制已验证为零 USB 命令。已有匹配清单的镜像可单独回收：

```sh
python3 UniXNU-zorn/scripts/run-zorn-debug.py
```

成功打包的镜像、内核和输入清单自动归档到 `out/zorn/builds/<哈希前缀>/`。自定义镜像旁可带同名 `.inputs.json`，回收器同样核对身份。recovery 起步时保存启动前日志摘要，返回后标注日志是否变化，避免将 UEFI 测试留下的旧内核日志当作本轮进展。

脚本核对 zorn 和槽位 b，从 recovery 定向重启 bootloader，再临时启动。300 秒未发现 recovery 就停止（早期历史测试使用 180 秒）。成功后保存 `run.json`、构建输入清单、启动输出和 4 KiB 原始日志到 `out/zorn/debug/<时间>-<哈希前缀>/`，手机留在 recovery。

## 负载与系统卷

UEFI 打包见 `uefi-zorn/README.md`。当前候选负载是 192 MiB FAT32、512 字节簇，包含内核、ADT、原版 trust cache sidecar，已省去不用作根的恢复内存盘。只读基线删除派生 ADT 的零值 RAMDisk/PackedRAMDisk 占位；RAM Data 配置改为仅保留合法 PackedRAMDisk，并设置 ephemeral-storage。两块原版模块的 bundle SHA256 为 `7416ca4f8377146626bb284e2133c76bee6cb4e3ee0af5d648b186235a7323a7`；早前真机 `TC00000003` 证明均被内核接受。

历史恢复盘 `root.img` 展开后为 176 MiB，仍保留在本机归档，但新候选不携带；真正的根是 userdata OS 容器 `md0`。`zorn_ramdata_defconfig` 新增已验证读写的独立 512 MiB RAM Data 种子；默认只读基线仍不携带它。只读基线默认 XNU 窗口为 384 MiB；当前 CPU 显示试验用 `--memory-mib 8192` 派生 8 GiB。它们和 UEFI 256 MiB 的 BootShim 解压窗口是不同参数。

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


## LaunchServices 定向取证与设备树对照

`--gui-user-stacks --gui-launchservices` 在原有 GUI/recovery profile 中，
将进程/栈槽0换为lsd，并读取最多16层首线程frame chain；SpringBoard/backboardd继续保留。
这些是可缺页、尽力读取的样本，真实错误保留，不是在task锁内执行的原子stackshot。
旧profile默认关闭这两项。ZORNLOG9仍只占既定4KiB日志块。

`--development-wifi-identity` 只增加开发用MAC身份属性，未实现网络驱动。
`--reuse-kernel-control out/zorn/builds/0959f393` 仅用于这项单变量对照，
要求归档内核、审计描述及其他profile选项一致；RAM Data、参数和最终ADT还需按打包证明核对。
旧0959归档的审计布局是重新计算并逐extent复核的记录，完整来源写在续调文档；
新归档会保存原始kernel-plan.json。它不代表干净检出构建已通过。

对已授权 USB 摄像头的 GUI watchdog 轮次，可单独使用
`python3 UniXNU-zorn/scripts/run-zorn-debug.py --timeout 1200 --capture-after 900`。
默认关闭定时采集；此选项在 fastboot boot 返回900秒后仅调用一次既有无音频单帧脚本，
子进程最多25秒，剩余回收期限不足26秒则跳过。摄像头错误不改变 recovery 截止时刻，
生成的图像仍须人工解析；运行 `scripts/check-zorn-runner-observation.py` 可在不访问 USB 时校验时序边界。

`--gui-runnable-kernel-stacks` 是默认关闭的额外诊断，依赖 `--gui-kernel-stacks`
及其 GUI watchdog/用户栈前置选项。它仅在 CPU0 读取非当前、已引用且非终止线程的
有界已保存内核上下文，最多16帧；有 continuation 时仍优先用户链。它不启用多核，
也不改变目标线程/调度/锁。20项宿主控制通过，真机资格须以对应回收日志为准。

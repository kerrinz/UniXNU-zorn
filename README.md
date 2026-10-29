# UniXNU-zorn

红米 K80 12GB+256GB（代号 zorn，SM8650-AB）的 UniXNU 设备仓库。这里放 `board.toml`、内核 defconfig、ADT 脚本和板级内核补丁。

固件仓库是 `uefi-zorn`，和本仓库分开发布。构建驱动、UniXNU 菜单和 DarwinBoot 在 [UniXNU](https://github.com/UniXNU/UniXNU)。

- [命令行](https://unixnu.com/zh/reference/cli)
- [移植总览](https://unixnu.com/zh/porting/)
- [设备仓库布局](https://unixnu.com/zh/porting/device-repository)
- [bring-up 顺序](https://unixnu.com/zh/porting/bring-up)
- 参考：[UniXNU-sheng](https://github.com/UniXNU/UniXNU-sheng)、[同 SoC 的 UniXNU-houji](https://github.com/lonzzi/UniXNU-houji)

## 构建

在 UniXNU 检出目录里执行。设备仓库用 `-D` 指定，驱动会记住它；`--core` 同时安装本次依赖的 [CLI overlay](patches/core/README.md)。下文命令按发布后的目录名 `UniXNU-zorn`、`uefi-zorn` 编写。

```sh
../UniXNU-zorn/scripts/install-zorn-patches.sh . --core
./unixnu defconfig zorn_defconfig -D ../UniXNU-zorn
```

**干净检出的补丁重放仍未通过。** 当前成功结果来自本机已应用补丁的 XNU 工作树和此前的预链接候选；已知有 boot-progress/early-bars 顺序、vm-bands 空行上下文冲突，PMGR 构建还依赖前一份候选及编译记录。下面的增量命令不代表全新克隆可以一键复现。

组件源码、SDK、编译记录、IPSW、ADT 和固件 FD 需预先准备，源码按主仓库 feeds 和本仓库 `unixnu.lock` 取用。公共 IOStorageFamily feed（`e45fbe30…`）需在主仓库执行 `./unixnu fetch IOStorageFamily`；它只供接口编译参考，不链接参考对象或修改原版可执行段。

在三仓库共同父目录准备原版 trust cache，再生成只读基线镜像：

```sh
python3 UniXNU-zorn/scripts/prepare-zorn-trustcache.py \
  --ipsw iPad_Pro_HFR_17.7.11_21H461_Restore.ipsw
python3 UniXNU-zorn/scripts/build-zorn-debug.py \
  --incremental-patched-tree \
  --ipsw iPad_Pro_HFR_17.7.11_21H461_Restore.ipsw \
  --fd ../Mu-Silicium/Build/zornPkg/DEBUG_CLANGPDB/FV/SILICIUM_UEFI.fd
```

`./unixnu ipsw info` 用于核对产品、版本和 build。本地 IPSW 通过 `UNIXNU_IPSW` 或调试构建器 `--ipsw` 指定，不写入 `board.toml`。IPSW、Apple 二进制、keys、镜像和生成的 archive 不提交。

固件和负载在 `uefi-zorn` 打包，内核镜像只通过 `fastboot boot` 临时启动。不要写 `boot`、`super`、`vbmeta`、`vendor_boot`，不要 `erase` 或改槽位。`userdata` 已有系统卷，不要再刷，也不要启动 Android。

## 进度

阶段划分跟 [bring-up 顺序](https://unixnu.com/zh/porting/bring-up) 一致。2026-10-28 已进入 iPadOS 系统锁屏，机主已确认；当前优先适配触控，CPU0 保持，多核及硬件 GPU 后置。尚未验证触摸解锁或桌面操作。

| 阶段 | 状态 |
| --- | --- |
| 1 UEFI | 工作。`fastboot boot` 进入固件，framebuffer 1440×3200 |
| 2 UniXNU | 工作。菜单标题 Redmi K80，读取 `\EFI\UniXNU\unixnu.toml`，倒计时 5 秒 |
| 3 负载 | 工作。卷标 `ZORNESP`，192 MiB FAT32，512 字节簇，携带两份原版 trust cache |
| 4 DarwinBoot | 工作。完成内核、ADT、trust cache 及独立 RAM Data 的交接 |
| 5 内核入口 | 工作。平台、时间基、虚拟内存、EL0/SVC 及 CPU 显示路径已取得真机证据 |
| 6 存储与根卷 | OS 作为 `md0` 只读挂载；SystemOS 经真实 IOBlockStorageDevice → IOMedia/APFS 只读挂载，owner 授权到达 `OWNOK`。独立 512 MiB Data 已可写，受限持久 overlay 已首次跨启动恢复 |
| 7 用户态 | 原版 launchd 进入主循环并启动子服务，图形启动已到系统锁屏；尚未验证解锁和桌面操作 |

[硬件低亮度](docs/progress-2026-10-28-brightness.md)通过一次完整锁屏启动，DCS 307 → 64，读回 64。[Data](docs/progress-2026-10-28-data-smp-touch.md)首次跨重启读回同一初始化标志；第二次复测被亮度交接保护提前拒绝并自动回 recovery，尚未到 Data，因此不宣称重复启动稳定。现有 overlay 保留。

[触控](docs/progress-2026-10-28-touch.md)已确认真实芯片 FT3683。首轮只读探针发现 SE 时钟关闭、GPIO 未启用；K80 专属 L14 / 3.2 V、L12 / 1.8 V 交接已短测走通。`bce3bdbe` 读到芯片 ID `3683`、固件 `35`，三条读取均首次 CRC 通过并恢复 GPIO。下一步采集真实触点帧，尚无 HID 或物理触摸成功证据。[启动与抓日志说明](docs/touch-test-instructions.md)提供仅依赖 adb/fastboot 的 Windows PowerShell 命令行包。

镜像身份和日志证据见 [GUI 续调记录](docs/progress-2026-10-27-gui.md)、[续调记录](docs/progress-2026-10-27-resumed.md)及 [docs/evidence](docs/evidence)。[暂停记录](docs/progress-2026-10-27.md)与 [RAM Data 记录](docs/progress-2026-10-27-ram-data.md)保留为历史快照；原始镜像和完整运行目录不放进 Git。

## 板级

```toml
[board]
name = "zorn"
soc = "SM8650"
description = "Redmi K80 12GB+256GB"
kit = "zorn"
```

输出目录是 `out/zorn/`。本设备仍使用 schema-1 布局，尚未迁移到 schema-2 的 DTS、组件列表和 `porting.toml`。`package/` 不建空目录，避免被识别为设备 kit。

```text
board.toml                  板级配置、原版 IPSW 和预链接针
configs/                    只读基线、RAM Data、CPU 显示等配置
native/ufs-read/             UFS 传输、只读根、受限日志/BCB、watchdog
native/pmgr/                 原版 PMGR ABI 适配
patches/zorn/                板级 XNU 补丁，追加到基础补丁
patches/core/                主 UniXNU CLI overlay
scripts/                    构建、ADT、打包、真机回收及日志工具
docs/                       阶段记录与可提交证据
unixnu.lock                 已解析源码提交
```

`patches/zorn/` 通过安装脚本追加到基础 XNU 补丁，不能改名为会替换基础模块的 `patches/xnu/`。

## IPSW

和 sheng 使用同一份未修改的 iPad7,1 恢复镜像。

| 项 | 值 |
| --- | --- |
| 产品 | iPad7,1（12.9 英寸 iPad Pro 第二代） |
| 版本 | iPadOS 17.7.11，build 21H461 |
| device class | j120ap |
| ApChipID / ApBoardID | `0x8011` / `12` |
| 内核 | Darwin 23.6，xnu-10063.141.1 |
| OS | `044-76040-038.dmg` |
| Cryptex1,SystemOS | `044-76034-038.dmg` |

`[ipsw.sha256]` 固定这两份 DMG，哈希与 sheng 的板级文件相同。`fetch` 列表是 KernelCache、DeviceTree、StaticTrustCache 和 Cryptex1,SystemTrustCache。本地 iPhone X 16.7.16 是 Darwin 22，不能用来预链接这颗内核。

## 内核

主 UniXNU 基线为 `16e592abee8a550dec8154ed1f38b5ebc4f16213`，XNU 针为 `d8b80295118ef25ac3a784134bcf95cd8e88109f`。预链接目标是固定的 iPad7,1 kernelcache，SHA256 为 `f18b4df865405f2a287b84977d7aca745e056d656d9fc9df1662970ce2969de7`，slide 为 `-0x1000000`。

`configs/zorn_defconfig` 启用 ArmDTPlatform、ArmCpu、corecrypto 14、pthread、PAN、签名哈希缓存、trust cache runtime、SoftwareAES 和 owner 验证。`CONFIG_XNU_NATIVE_UFS` 仍关闭，改用 `native/ufs-read/` 的板级传输及相关 archive。早期锁、TLBI 和 MAC/exec 试验性修改仍保留，稳定性与完整安全语义尚未验证。

两份原版 trust cache 已通过 `SIGPASS`，`load_init_program` 返回 `INITOK`。EL0/SVC 入口和返回、`mprotect`、Mach VM 分配、`getpid=1` 及第 32 次 SVC 已验证。原版 PMGR 对象、绑定、AON 方法及服务发布通过，完整硬件电源管理未实现。PAN 修复了 `_bcopyin` 同址权限故障循环；SoftwareAES 在链接前后核对 181 个原版 ABI 槽位及两份原版可执行段，解除 AppleImage4 等待并越过第 64 次 SVC。

当前候选使用独立 owner 验证路径。在三仓库共同父目录准备签名和区块策略：

```sh
python3 UniXNU/kits/VerifiedRoot/tests/check.py \
  --output out/zorn/verified-root-host --openssl-prefix /opt/homebrew/opt/openssl@3
python3 UniXNU-zorn/scripts/prepare-zorn-verified-root.py
```

OpenSSL 路径按本机调整。私钥只在忽略的 `out/zorn/verified-root-host/keys` 内，内核只嵌入公钥及签名策略。两份完整镜像 SHA256、C 验证或实际读取区块不符都会拒绝。真机已通过两卷签名打开、区块校验、APFS UUID、只读状态及设备号授权。SystemOS 按 UUID 选择，不固定 disk 编号；历史只读基线为 `/dev/disk1s1`，加入 RAM Data 后为 `/dev/disk3s1`，raw `md1` 仅保留为历史诊断。

独立 RAM Data 和 CPU 显示候选需预先准备对应输入，在共同父目录执行：

```sh
python3 UniXNU-zorn/scripts/prepare-zorn-data.py
python3 UniXNU-zorn/scripts/build-zorn-debug.py \
  --defconfig zorn_ramdata_defconfig --incremental-patched-tree \
  --early-watchdog 1 --boot
```

种子准备器只操作本机镜像，拒绝覆盖已有种子；构建器核对逻辑/编码 SHA256 和实际 UUID，生成独立派生菜单及 PackedRAMDisk ADT。主机准备未保留全部文件属主，完整服务权限仍待验证。

```sh
python3 UniXNU-zorn/scripts/build-zorn-debug.py \
  --defconfig zorn_display_defconfig --display-mode 3 --memory-mib 8192 \
  --checkpoint NOHIT --gui-watch --incremental-patched-tree \
  --early-watchdog 1 --recovery-timeout 300 --boot
```

这里的 8 GiB 是 XNU 内存窗口，不是 Data 卷容量。`zorn_union_defconfig` 用于 SystemOS/OS 只读目录组合的独立候选；具体 profile 和镜像身份以各轮 `build-inputs.json` 为准。

`--gui-watch` 默认关闭，最多 12 次采样且默认不喂狗；`--gui-hold-seconds 30..180` 是要求 `--early-watchdog 1` 的独立有界窗口。`--gui-user-stacks --gui-launchservices` 定向采样 lsd 等进程，最多 16 层用户 frame chain；`--gui-runnable-kernel-stacks` 另需相应内核栈前置选项，仅在 CPU0 有界读取有效线程保存的上下文。这些样本可缺页，保留真实错误，不是原子 stackshot。

`--development-wifi-identity` 只做开发 MAC 身份对照，不提供网络驱动。`--reuse-kernel-control out/zorn/builds/0959f393` 仅用于这项单变量对照，须核对归档内核、审计描述和其余 profile；该归档的审计重建不代表干净检出构建通过。

已有匹配清单的镜像可单独运行：

```sh
python3 UniXNU-zorn/scripts/run-zorn-debug.py
```

构建器遇错即停，`out/zorn/boot.inputs.json` 保存状态和输入哈希；回收器先核对 `ready` 和 `boot.img` SHA256，再执行 USB 操作，失败构建不能沿用旧镜像。成功镜像、内核及清单归档到 `out/zorn/builds/<哈希前缀>/`；每轮输出到 `out/zorn/debug/<时间>-<哈希前缀>/`，包括 `run.json`、输入清单、启动输出和 4 KiB 原始日志。启动前后比较日志摘要，避免把旧日志当成新结果。

提前 watchdog 需先构建并记录 UEFI FD。模式 2 为 UEFI 停 CPU 测试，已自动回 recovery；模式 1 的内核 `WON` 证明接管时已开启。bootreason 为空，具体复位源未独立确认。`NOHIT` 不主动命中检查点；`zorn_hash_budget=120` 仅在前 120 秒内原始签名块验证成功时 pet，停滞由 55 秒 bite 回收。默认主机等待 300 秒，成功后手机留在 recovery，超时则停止。

已授权摄像头的轮次可加 `--timeout 1200 --capture-after 900`，仅调用一次无音频单帧采集，子进程上限 25 秒，剩余期限不足 26 秒跳过，不延长回收期限。宿主时序控制可运行 `scripts/check-zorn-runner-observation.py` 校验。

日志读取和离线解码：

```sh
python3 UniXNU-zorn/scripts/read-zorn-log.py --save out/zorn/last-log.bin --tail 100
python3 UniXNU-zorn/scripts/read-zorn-log.py --block out/zorn/last-log.bin --tail 100
```

第一条固定从 K80 recovery 只读提取，第二条只读本地文件。持久日志、完整 panic、用户 write 文本、sysctl 边界及独立 Gunyah watchdog 已验证。读取器兼容多版日志；`zorn_log_only=1` 在 UFS 就绪后停止刷新屏幕词，旧屏幕词不代表最新执行位置，检查点复位也不等于自然故障。协议和写入限制见 [UFS 诊断说明](native/ufs-read/README.md)。

## 负载

`[payload]` 记录通用驱动能读的数值，实测镜像由 `uefi-zorn/scripts/make-zorn-payload.py` 打包。

| 键 | 值 |
| --- | --- |
| 卷标 | `ZORNESP` |
| 大小 | 192 MiB FAT32，512 字节簇 |
| 加载器 | 固件卷里的 DarwinBoot |
| 菜单项 | Boot XNU |
| 倒计时 | 5 秒 |
| DRAM | `0x300000000`，12 GiB 标称配置，不代表整窗验证通过 |
| 引导窗口 | 默认 `0x18000000`（384 MiB）；CPU 显示试验派生 8 GiB |
| CPU | `cpu_regs = 0`，仅 CPU0 |
| 身份 | iPad |
| 基础参数 | `rd=md0 -v serial=3 debug=0x14e` |
| 检查点与回收 | `NOHIT`、纯日志、独立 watchdog，具体参数由 profile 记录 |

EDK2 EnhancedFatDxe 要求 FAT32 簇数不少于 65525。打包器固定 512 字节簇并清掉 mtools 的假分区表；通用 `unixnu build payload` 不处理这些条件，因此不是当前实测打包路径。

两块原版 trust cache 的 bundle SHA256 为 `7416ca4f8377146626bb284e2133c76bee6cb4e3ee0af5d648b186235a7323a7`，真机 `TC00000003` 证明均被接受。历史恢复盘 `root.img` 展开后为 176 MiB，新候选不携带它；真正的根是 `userdata` OS 容器 `md0`。只读基线移除派生 ADT 的零值 RAMDisk/PackedRAMDisk 和 ephemeral-storage；RAM Data 配置保留合法 PackedRAMDisk 及临时存储标记，原始 ADT 不变。

live FDT 高地址范围已核对，实际 8 GiB UEFI 分配及 XNU/UFS 控制路径通过；整窗压力测试和长期稳定性未通过。此窗口与 UEFI 的 256 MiB BootShim 解压窗口是不同参数。

## userdata

`board.toml` 的 `[userdata]` 描述 `unixnu build userdata` 生成的文件；`first_lba` / `last_lba` 只复现容量，不是实际 GPT 地址。运行时由 GPT 按名称定位分区。

| 项 | 值 |
| --- | --- |
| 系统镜像 | `out/zorn/userdata/userdata-root.img`，`SHNGROOT` |
| 大小 | 9382658048 字节 |
| SHA256 | `fd43ee7035ce185ce4215ac93fdc006fd784a54b3b7442e21457c226cbe03093` |
| OS 窗口 | 偏移 `0x100000`，只读 |
| SystemOS 窗口 | 偏移 `0x16a600000`，只读 |
| Data | 独立 512 MiB APFS；持久 overlay 位于 userdata 相对 10 GiB、131077 个 4 KiB 块，前像已备份验证 |
| 日志 | userdata 内第 `2291712` 个 4096 字节块，系统镜像结束后 4 MiB |

系统镜像已于 2026-10-25 经机主授权写入并读回验证。早期易失 RAM Data 已完成文件创建、同步、关闭后读回和删除（`DPT=7 / DPE=0`）；当前受限持久 overlay 的跨启动资格见进度节，不能将历史易失测试当作重复启动证明。

持久写入限定为上述 Data overlay、既有单 4 KiB 日志块及 GPT 选定的 misc recovery BCB 页。BCB 仅更新前 864 字节为 recovery 命令，其余字节保留并读回验证，无 wipe 参数；OS/SystemOS 传输拒绝写入。

唯一目标是 `92988a43` / zorn / 槽位 `b`，所有 adb/fastboot 命令必须带 `-s 92988a43`。`f85d4270` 是小米 CC9 / pyxis，禁止操作。当前没有 Android/iPadOS 双系统共存能力，不要启动 Android，也不要重刷现有 `userdata`。

## 设备支持

| 功能 | 状态 |
| --- | --- |
| UEFI 菜单 | 工作，倒计时 5 秒 |
| 显示交接 | 工作，1440×3200，CPU 显示路径已到系统锁屏 |
| 亮度 | DCS 307 → 64，读回 64，一次完整锁屏启动通过 |
| 内核与用户态 | 原版 launchd 及子服务执行，系统锁屏已确认；解锁和桌面操作未验证 |
| UFS / 系统卷 | 板级传输工作；OS/SystemOS 只读，签名、区块及卷身份授权通过 |
| Data | 512 MiB APFS 可写；受限 overlay 首次跨启动恢复通过，重复启动稳定性未证明 |
| CPU | 仅 CPU0，多核未适配 |
| 触控 | FT3683 芯片 ID、固件读取通过，真实触点与 HID 尚未验证 |
| GPU | 硬件 GPU 未适配 |
| 电源管理 | 原版 PMGR 对象及服务发布通过，完整硬件电源管理未实现 |
| Wi-Fi、蓝牙、音频、基带、摄像头、传感器 | 未完成；开发 MAC 身份属性不代表联网 |
| Android 双系统 | 不支持；当前 userdata 已用于 iPadOS |

## 许可

本仓库主要使用 [BSD-2-Clause-Patent](LICENSE)。`native/pmgr/ZornPlatformPower.cpp` 改编自 sheng 的 MIT 源码，保留 [MIT 许可](native/pmgr/LICENSE.MIT)；原有上游文件继续使用各自版权头。

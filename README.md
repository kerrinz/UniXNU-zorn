# UniXNU-zorn

红米 K80 12GB+256GB（代号 zorn，SM8650-AB）的 UniXNU 设备仓库。这里放 `board.toml`、内核 defconfig、ADT 脚本和这次 bring-up 的内核补丁。

固件仓库是 `uefi-zorn`，和本仓库分开发布。构建驱动、UniXNU 菜单和 DarwinBoot 在 [UniXNU](https://github.com/UniXNU/UniXNU)。

- [命令行](https://unixnu.com/zh/reference/cli)
- [移植总览](https://unixnu.com/zh/porting/)
- [设备仓库布局](https://unixnu.com/zh/porting/device-repository)
- [bring-up 顺序](https://unixnu.com/zh/porting/bring-up)
- 同代参考：[小米平板 6S Pro（sheng）](https://unixnu.com/zh/devices/sheng)、[一加 Ace 5（giulia）](https://unixnu.com/zh/devices/giulia)

## 构建

在 UniXNU 检出目录里执行。设备仓库用 `-D` 指定，驱动会记住它。

```sh
./unixnu defconfig zorn_defconfig -D ../UniXNU-zorn
./unixnu fetch
../UniXNU-zorn/scripts/install-zorn-patches.sh .
./unixnu build kernel
```

`./unixnu ipsw info` 核对产品、版本和 build。本地 IPSW 用 `--ipsw` 或 `UNIXNU_IPSW` 指向文件，不写进 `board.toml`。

固件、负载和 `fastboot boot` 用的镜像在 uefi-zorn 里打包。不要对这台机器执行 `fastboot flash`。Android 留在当前槽位，关机后回到原来的系统。

## 进度

阶段划分跟 [bring-up 顺序](https://unixnu.com/zh/porting/bring-up) 一致。2026-10-25 停在阶段 7，屏幕上最后一个词是 `PARSE`。内核调试先停在这里。

| 阶段 | 状态 |
| --- | --- |
| 1 UEFI | 工作。`fastboot boot` 进入固件，framebuffer 1440×3200 |
| 2 UniXNU | 工作。菜单标题是 Redmi K80，读到 `\EFI\UniXNU\unixnu.toml`，倒计时 10 秒 |
| 3 负载 | 工作。卷标 `ZORNESP`，192 MiB FAT32 |
| 4 DarwinBoot | 工作。已经把内核交出去。这台机器没有串口，依据是屏幕上的阶段词 |
| 5 内核入口 | 工作。平台专家、时间基、虚拟内存和屏幕初始化都已返回 |
| 6 存储与根卷 | 部分。没有原生 UFS。iPadOS 17.7.11 的恢复内存盘作为 `md0` 挂上了 APFS |
| 7 用户态 | 部分。`/sbin/launchd` 已经打开。`load_machfile` 停在调用 `parse_machfile` 之前，屏幕词是 `PARSE` |

到达这一步的启动镜像 sha256 是 `0c1300e0c0b2e8ebfcebb7978708fa76d5076e448cdad3188c7c31d973f14828`，内核 sha256 是 `c79e9ff9b4acd9b8061cfd0c86850f5b67fe5e8f66067f664569ff5a48132c76`。镜像大约 145 MB，在 fastboot 768 MiB 的下载上限以内。

`PARSE` 之前，同一次启动还打印了用户页表、地址空间和 ASLR。恢复盘里的 `/sbin/launchd` 是 ad-hoc 签名。ADT 仍带 `amfi-only-platform-code`。去掉这项并加上 `amfi_get_out_of_my_way=1` 时，内核停在更早的 `mac_policy_initmach`。

这是恢复环境，不是 iPad 主屏幕。恢复盘展开后 176 MiB，里面有 `/sbin/launchd`、`/usr/lib/dyld` 和恢复工具，没有 dyld 共享缓存。

## 板级

```toml
[board]
name = "zorn"
soc = "SM8650"
description = "Redmi K80 12GB+256GB"
kit = "zorn"
```

输出目录是 `out/zorn/`。还没有设备 kit、驱动或 `package/`。空的 `package/` 会变成一块设备 kit，所以先不建这个目录。

## IPSW

和 sheng 使用同一份未修改的 iPad7,1 恢复镜像。

| 项 | 值 |
| --- | --- |
| 产品 | iPad7,1（12.9 英寸 iPad Pro 第二代） |
| 版本 | iPadOS 17.7.11，build 21H461 |
| device class | j120ap |
| ApChipID / ApBoardID | 0x8011 / 12 |
| 内核 | Darwin 23.6，xnu-10063.141.1 |

`[ipsw.sha256]` 固定 `044-76040-038.dmg`（OS）和 `044-76034-038.dmg`（Cryptex1,SystemOS），哈希与 sheng 的板级文件相同。`fetch` 列表是 KernelCache、DeviceTree、StaticTrustCache 和 Cryptex1,SystemTrustCache。

本地的 iPhone X 16.7.16 镜像是 Darwin 22，不能用来预链接这颗内核。

## 内核

`configs/zorn_defconfig` 打开 Arm 设备树平台、ArmCpu、corecrypto 14、pthread、代码签名哈希缓存，预链接引导。`CONFIG_XNU_NATIVE_UFS` 没有打开。链接还需要 `scripts/build-zorn-link-stubs.py` 提供的空 `native_legacy_display_probe`。

预链接针和 `kernelcache_sha256` 与 sheng 的 iPad7,1 kernelcache 相同。slide 是 `-0x1000000`。

`patches/zorn/` 里的补丁在复制进 UniXNU 的 `patches/xnu/` 之后才会参与构建。说明见该目录的 README。

## 负载

`[payload]` 记录通用驱动能读的数值：

| 键 | 值 |
| --- | --- |
| 卷标 | `ZORNESP` |
| 大小 | 192 MiB |
| 加载器 | 固件卷里的 DarwinBoot |
| 菜单项 | Boot XNU |
| 倒计时 | 10 秒 |
| DRAM | `0x300000000`（按 12 GiB 售卖规格填写，不是从 SMEM 读到的） |
| 引导窗口 | `0x18000000`（384 MiB） |
| CPU | `cpu_regs = 0`，只描述 CPU0 |
| 身份 | iPad |
| 参数 | `rd=md0 -v serial=3 debug=0x14e` |

真机上跑过的那份卷由 uefi-zorn 的 `scripts/make-zorn-payload.py` 打包。它把簇大小固定成 512 字节。EDK2 的 EnhancedFatDxe 拒绝簇数小于 65525 的 FAT32；192 MiB 只有在 512 字节簇时才够簇数。通用的 `unixnu build payload` 不传这个簇大小，所以那一步还不是这台机器的打包路径。

恢复内存盘放在 `Payloads/root.img`，菜单里的 `initrd` 指向它。ADT 里是 `RAMDisk` 占位，DarwinBoot 把 `DBRDISK1` 展开进这块窗口。没有安装 trust cache，也没有 Data 种子。

## userdata

`board.toml` 没有 `[userdata]`。不准备刷写 userdata，也不改分区表。

OS 约 4.80 GiB，SystemOS 约 3.08 GiB，合计约 7.88 GiB。fastboot 的下载上限是 768 MiB，ABL 解压内核的窗口是 256 MiB。主系统镜像走不了现在这条内存启动路径。官方 sheng 把系统写进整个 userdata 分区；这块板子还没有走那一步。

## 设备支持

| 功能 | 状态 |
| --- | --- |
| UEFI 菜单 | 工作 |
| 显示交接 | 工作，1440×3200 |
| 内核启动 | 工作到 `PARSE` |
| 内存根卷 | 工作，恢复盘 |
| UFS | 未做 |
| 触控 | 未做 |
| GPU | 未做 |
| Wi-Fi、蓝牙、音频、基带、摄像头、传感器 | 未做 |
| 分区上的 iPadOS | 未做 |

## 许可

BSD-2-Clause-Patent。见 [LICENSE](LICENSE)。

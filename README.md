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

固件、负载和 `fastboot boot` 用的镜像在 uefi-zorn 里打包。内核镜像只做内存启动。不要写 `boot`、`super`、`vbmeta`，不要改槽位。`userdata` 上已经是核对过的系统卷，不要再刷，也不要启动 Android。

## 进度

阶段划分跟 [bring-up 顺序](https://unixnu.com/zh/porting/bring-up) 一致。2026-10-26 停在阶段 7，色条下方最后一个词是 `MEND`。这一阶段先提交仓库，不再编下一颗内核。

| 阶段 | 状态 |
| --- | --- |
| 1 UEFI | 工作。`fastboot boot` 进入固件，framebuffer 1440×3200 |
| 2 UniXNU | 工作。菜单标题是 Redmi K80，读到 `\EFI\UniXNU\unixnu.toml`，倒计时 5 秒 |
| 3 负载 | 工作。卷标 `ZORNESP`，192 MiB FAT32，512 字节簇 |
| 4 DarwinBoot | 工作。已经把内核交出去。这台机器没有串口，依据是屏幕上的阶段词 |
| 5 内核入口 | 工作。平台专家、时间基、虚拟内存和屏幕初始化都已返回 |
| 6 存储与根卷 | 工作到只读挂载。`CONFIG_XNU_NATIVE_UFS` 仍关着。`native/ufs-read` 只读探针读 `userdata` 上的 `SHNGROOT`，把 OS 窗口里的 APFS 容器注册成 `md0`。只读 apfs 根已经挂上，屏幕词是 `APOK`。内核不发 WRITE，也不发 SYNCHRONIZE CACHE |
| 7 用户态 | 部分。挂载之后继续读文件。`MEND` 表示 `vm_map_destroy` 里的两次 `vm_map_delete` 都已返回。这张表是 4K 内核给 16K 用户映射做物理拷贝时的临时表。还没有桌面 |

到达 `MEND` 的启动镜像 sha256 是 `07f183f9ecba184ef88dea9267d80eebdec6d1f6e7255ec43152ec215c6f8797`，内核 sha256 是 `dd91221f3d671766270874cf225c307ac35ccd90f9c0b2e0339ac886ea30c8bb`。镜像 144732160 字节，在 fastboot 768 MiB 的下载上限以内。

`MEND` 之前，同一次启动已经过了 `APOK`。中间还见过 `P07993938`（中断仍关着就进了 `zalloc`）、`LROK`、`LIRQ` 和 `C07341634`。`C07341634` 是 `vm_map_destroy` 拿到地址空间锁之后的返回地址 `0xfffffff007341634`。恢复盘里的 `/sbin/launchd` 是 ad-hoc 签名。ADT 仍带 `amfi-only-platform-code`。去掉这项并加上 `amfi_get_out_of_my_way=1` 时，内核停在更早的 `mac_policy_initmach`。

负载里的 `Payloads/root.img` 仍是恢复内存盘，展开后 176 MiB，里面有 `/sbin/launchd`、`/usr/lib/dyld` 和恢复工具，没有 dyld 共享缓存。根卷不是这张恢复盘。内核在登记恢复盘之前，先把 `userdata` 上的 OS 容器登记成 `md0`，所以 `rd=md0` 指向这只读容器。恢复盘占用后面的空闲单元。

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

`configs/zorn_defconfig` 打开 Arm 设备树平台、ArmCpu、corecrypto 14、pthread、代码签名哈希缓存，预链接引导。`CONFIG_XNU_NATIVE_UFS` 没有打开，因为那条路会带上 verified-root、boot progress 和 `IOBlockStorageDevice`，这颗内核还没链它们。只读探针在 `native/ufs-read/`，由 `scripts/build-zorn-ufs.py` 编成 `libZornUfs.a` 再强制链接。链接还需要 `scripts/build-zorn-link-stubs.py` 提供的空 `native_legacy_display_probe`。

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
| 倒计时 | 5 秒 |
| DRAM | `0x300000000`（按 12 GiB 售卖规格填写，不是从 SMEM 读到的） |
| 引导窗口 | `0x18000000`（384 MiB） |
| CPU | `cpu_regs = 0`，只描述 CPU0 |
| 身份 | iPad |
| 参数 | `rd=md0 -v serial=3 debug=0x14e` |

真机上跑过的那份卷由 uefi-zorn 的 `scripts/make-zorn-payload.py` 打包。它把簇大小固定成 512 字节。EDK2 的 EnhancedFatDxe 拒绝簇数小于 65525 的 FAT32；192 MiB 只有在 512 字节簇时才够簇数。通用的 `unixnu build payload` 不传这个簇大小，所以那一步还不是这台机器的打包路径。

恢复内存盘放在 `Payloads/root.img`，菜单里的 `initrd` 指向它。ADT 里是 `RAMDisk` 占位，DarwinBoot 把 `DBRDISK1` 展开进这块窗口。没有安装 trust cache，也没有 Data 种子。

## userdata

`board.toml` 的 `[userdata]` 描述 `unixnu build userdata` 写出的文件。`first_lba` / `last_lba` 只复现 fastboot 报出的字节数，不是盘上的 GPT 地址。已生成的文件在 `out/zorn/userdata/userdata-root.img`，9382658048 字节，sha256 `fd43ee7035ce185ce4215ac93fdc006fd784a54b3b7442e21457c226cbe03093`。开头是 `SHNGROOT`，OS 窗口在 `0x100000`，SystemOS 窗口在 `0x16a600000`。2026-10-25 已用 256 MiB 分段写入 `userdata`，探针读回后停在 `SHNGOK`。不要再刷这卷。不要启动 Android，否则会把它当成加密的 Android 数据。

## 设备支持

| 功能 | 状态 |
| --- | --- |
| UEFI 菜单 | 工作，倒计时 5 秒 |
| 显示交接 | 工作，1440×3200 |
| 内核启动 | 工作到 `MEND` |
| 内存根卷 | 恢复盘仍打进负载；当前根是 `userdata` 上的只读 APFS |
| UFS | 只读探针工作。没有打开 `CONFIG_XNU_NATIVE_UFS`。内核不写盘 |
| 触控 | 未做 |
| GPU | 未做 |
| Wi-Fi、蓝牙、音频、基带、摄像头、传感器 | 未做 |
| 分区上的 iPadOS | 系统卷已在 `userdata`，只读根已挂上，还没有桌面 |

## 许可

BSD-2-Clause-Patent。见 [LICENSE](LICENSE)。

# K80 构建、测试与日志

本文对应 2026-10-29 的现有格式 1 构建入口。它记录已准备工作区的使用方式，不是全新克隆的一键安装说明。后续上游构建验证见 [构建回归记录](progress-2026-10-29-repro-build.md)，与已验收桌面基线分开记录。

## 基线与前置输入

- 主 UniXNU 基线：`16e592abee8a550dec8154ed1f38b5ebc4f16213`；本仓库 `patches/core/` 保存本地 CLI overlay。
- XNU：`d8b80295118ef25ac3a784134bcf95cd8e88109f`，Darwin 23.6 / XNU 10063.141.1；其余已解析源码见根目录 `unixnu.lock`。
- 本机共同父目录内已有 `UniXNU/`、`UniXNU-zorn/`、`uefi-zorn/`；Mu-Silicium 路径单独传入。上游依赖按主仓库说明准备，不必 fork 成额外仓库。
- 工具链、SDK、编译记录、匹配的 IPSW、原版 trust cache、签名/区块策略、ADT 与 Data 种子必须事先准备。
- IPSW 为 `iPad_Pro_HFR_17.7.11_21H461_Restore.ipsw`（iPad7,1 / j120ap）。公开来源与成员哈希见 `board.toml`；本地文件可用 `--ipsw` 或 `UNIXNU_IPSW` 指定。
- Mu-Silicium 中的厂商 DXE、Apple 二进制和私钥不随两仓库分发；私钥仅保存在忽略的本机 `out/` 内。

当前成功结果依赖本机已打补丁的 XNU 工作树和此前预链接候选。**后续已修正陈旧上下文，157 个补丁的干净重放及独立新对象编译通过，但新候选未验收桌面；另已固化实际工作树的 97 文件过渡源码快照，提供隔离工作区入口。PMGR 等配方仍显式使用此前 ABI 候选。** 旧锁、pmap、MAC / exec 的部分实验修改仍须复核，不因本轮桌面成功而视为全部合格。

## 已准备工作区的入口

以下准备步骤按实际缺失输入使用，不要覆盖已有 Data 或签名身份。在专用于 zorn 的主 UniXNU 检出中安装 overlay 并选择设备：

```sh
../UniXNU-zorn/scripts/install-zorn-patches.sh . --core
./unixnu defconfig zorn_defconfig -D ../UniXNU-zorn
```

安装器向基础补丁集追加 `patches/zorn`，不能直接把设备目录改名为 `patches/xnu`。公共 IOStorageFamily feed 固定为 `e45fbe30a7879e0b16e26dddb78538f1b00e0bff`，用于 ABI 参考，不将参考对象链接为替代的原版存储栈。

在共同父目录准备原版 trust cache：

```sh
python3 UniXNU-zorn/scripts/prepare-zorn-trustcache.py \
  --ipsw iPad_Pro_HFR_17.7.11_21H461_Restore.ipsw
```

owner 验证输入的准备依赖既有只读镜像及 OpenSSL，使用 `prepare-zorn-verified-root.py` 和主仓库 `kits/VerifiedRoot/tests/check.py`。Data 种子与持久窗口的前像、容量、UUID 和已安装状态分别由既有 Data 清单维护；**本次不重新初始化或安装这些输入**。来源与验证过程见 [Data / 八核记录](progress-2026-10-28-data-smp-touch.md)。

固件由 [uefi-zorn](https://github.com/kerrinz/uefi-zorn) 的 `stage-into-mu.sh` / `build-zorn-firmware.py` 构建；统一构建器支持 `--fd /path/to/SILICIUM_UEFI.fd`，需使用包含对应触控供电和提前 watchdog 的已核验固件。

## 基本桌面触控配置

以下在共同父目录执行，只生成新镜像，不隐式启动，也不重建 Data：

```sh
python3 UniXNU-zorn/scripts/build-zorn-debug.py \
  --incremental-patched-tree --defconfig zorn_union_defconfig --data-profile 8g \
  --source-pins UniXNU-zorn/source-pins.json \
  --smp-preflight 8 --smp-continue --display-mode 3 --brightness-mode 3 \
  --touch-handoff --touch-runtime --touch-edges --touch-kernel-parser --touch-trace \
  --gui-watch --development-wifi-identity --data-permissions --keystore-state \
  --shared-data-volume --data-store-mode 2 --retained-data --quiet-gui --hid-family \
  --minimal-services --skip-setup --lite-services --gui-hold-seconds 300 \
  --memory-mib 8192 --early-watchdog 1 --recovery-timeout 600 --touch-fast-poll
```

这是 `42f3d518` 所属的已验收配置组合，重建结果须以新的清单和 SHA256 为准，不保证逐字节相同。`--development-wifi-identity` 仅提供系统身份属性，不是 Wi-Fi 驱动；`--retained-data` 保留已有 Data 初始化成果；不要随意追加首次初始化或重置参数。

快采样模式将合作让出间隔从每 8 字节调整为每 32 字节、帧间等待从 100 ms 调整为 20 ms。真实日志约每 140 ms 一点，最大采样间隔 148 ms；这不是 60 / 120 Hz 的硬件 SPI / IRQ 驱动。

输出包括 `out/zorn/boot.img`、`boot.inputs.json` 和 `out/zorn/builds/<哈希前缀>/` 的完整归档。格式 1 的 XNU 工作树仍为 `UniXNU/out/zorn/tree`。输入审计或构建失败时停止，不沿用旧镜像宣称新版本成功。

## 临时启动与回收

仅在设备已连接、需要新测试且准备好自动回收时使用。当前已验收归档可按下面的命令启动；自行重建后替换为新归档路径：

```sh
python3 UniXNU-zorn/scripts/run-zorn-debug.py \
  --image out/zorn/builds/42f3d518/boot.img --timeout 600 --arm-recovery-bcb
```

脚本只针对 `92988a43` / `zorn` / `b`，核对 ready 清单及镜像身份，执行临时 `fastboot boot`，等待有界自动回 recovery。归档缺失时不能用这个短哈希替代真实镜像和清单。不要同时运行多个启动或回收任务。

该配置使用 300 秒 GUI 观察和独立 watchdog；600 秒是主机回收预算，不是系统永久驻留时间。成功回收后手机留在 recovery，运行结果在 `out/zorn/debug/<时间>-<镜像前缀>/run.json`。只有 `status=recovered`、`kernel_log_changed=true` 且 boot / kernel / 归档身份匹配，才能把对应日志归为这次启动。

## 存储与回收边界

- SHNGROOT 系统镜像：9382658048 字节，SHA256 `fd43ee7035ce185ce4215ac93fdc006fd784a54b3b7442e21457c226cbe03093`。OS 位于镜像内 `0x100000`，SystemOS 位于 `0x16a600000`，运行时由真实 GPT 定位 userdata，两者保持只读。
- 当前 8 GiB Data 使用 UFS 持久后端（RamBlock 的 DirectDisk 路径），不是分配等量 RAM 的 8 GiB 内存盘；不可变压缩种子提供尚未写入的页。独立窗口从 userdata 相对 192 GiB 开始，共 2097217 个 4096 字节块，包含其格式元数据，并非另改 GPT 分区。APFS UUID 为 `C7D77FF3-6437-4C4A-8E05-E8E239AC1641`。
- 原 userdata 相对 10 GiB 的 512 MiB Data 窗口保留；不是当前活跃的 8 GiB Data。禁止因种子或校验不匹配而隐式清空旧窗口。
- 日志位于 userdata 内第 `2291712` 个 4096 字节块，始终只用既有单页。
- recovery BCB 仅更新 GPT 选定 misc 页的前 864 字节，保留尾部并读回验证，不使用 wipe 参数。

不 flash / erase、不改槽位、不写 boot、super、vbmeta、vendor_boot 或 GPT。当前 userdata 已用于 iPadOS，不能启动 Android；这里不是双系统配置或安装教程。板级 first / last LBA 的历史值仅复现容量，不是真实 GPT 起始地址。

## 日志与身份

读取目标 K80 recovery 的既有日志，或离线解析本地副本：

```sh
python3 UniXNU-zorn/scripts/read-zorn-log.py --save out/zorn/last-log.bin --tail 100
python3 UniXNU-zorn/scripts/read-zorn-log.py --block out/zorn/last-log.bin --tail 100
```

触控轨迹与 GUI 快照复用既有 4 KiB 页；`zorn_log_only=1` 后屏幕旧词不表示最终执行位置。用户栈、内核等待栈与真实读取错误分开记录，不凭一次采样认定死锁，也不将包含锁等待和抢占的读盘计时相加当墙钟占比。

当前基本触控验收身份：

```text
boot    42f3d5183b67bd42b2e02ec1d193ba888d0e6c2dc4cd50dafab2211ce589583e
kernel  824f882cf22cab37a0f6e2c83478eb30f5147a3127bdc79d0321e73227816b0f
log     3c5015fc70dbbd510459cc6a73bfc14167b02a6ba5811a9cd0f978ef72e9c508
```

证据、主机检查及未解决的 CPU1 早退见 [触控阶段记录](progress-2026-10-29-touch-events.md) 与 [验收摘要](evidence/touch-desktop-fast-qualified.json)。诊断私钥、IPSW、完整系统副本、生成内核及手机镜像不提交到 Git。

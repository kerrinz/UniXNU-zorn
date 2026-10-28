# zorn：2026-10-27 恢复无人值守调试

机主明确恢复调试，手机初始位于 fastboot。再次核对 `92988a43`、`product: zorn`
和槽位 b。两个仓库此前的暂停快照保留；本记录描述暂停后的实验。

## 已解除的阻塞

原版 AppleImage4 初始化在 UFS 日志就绪前已开始。仅记录就绪后的 syscall
会丢失这段历史。本轮以 64 个固定 BSS 记录保存早期 start、服务匹配、实际
等待以及锁门调用，在 ignition 查询时重放到原有 4 KiB 日志块。

镜像 `b7cdb904a614030020a7a1622af34c244e37c7977607e3f7d93e2a45b377a3a9`
的真实事件为：

```text
AppleImage4 start enter; provider IOPlatformDevice
serviceMatching("IOAESAccelerator"); caller 0xfffffff004a98218
waitForMatchingService; caller 0xfffffff004a98224; timeout UINT64_MAX
ignition_blob: gate_try_close returned KERN_FAILURE (5)
lck_mtx_gate_wait; caller 0xfffffff004a94998; deadline 0
```

这将上轮的静态推测推进为真机证据：初始化没有取得所需 AES 服务，查询等待
初始化释放锁门。由独立 watchdog 自动回 recovery，完整运行目录
`out/zorn/debug/20261027-055536-b7cdb904/`。

## SoftwareAES 接通

选择现有 `drivers/SoftwareAES` 组件，保留运行时类名 `NativeAES`。板级
recipe 使用上游未修改源码及原版 IOAESAccelerator 绑定。源文件 SHA256：
`e05761b7c7a5077f695a108b522cc5b4b77ffc65be7c1ddf731fa37168499f22`。

构建前及最终 prelink 后都核对 181 个 vtable 槽位：11 个 native override、
其余方法对应当前内核导出或已固定的原版方法地址。原版 Image4、
IOCryptoAcceleratorFamily 可执行段逐字节哈希保持一致。源组件只提供真实的
软件密钥 AES-CBC，包含 128/192/256 位 NIST 已知答案和接口测试；硬件密钥
选择器仍返回 unsupported。

接通后的镜像：

- Boot：`0b886dcd932f5c3d26c5b532162312a92f4a034bca72e93bf56947f621f3d346`
- Kernel：`d70c1ddc4411ff48709c2281e8067209c4305b4d185315624e9bf927c39b564e`
- 大小：144809984 字节。
- 运行：`out/zorn/debug/20261027-060001-0b886dcd/`，状态 `recovered`。
- 日志：libignition 继续解析 `program: launchd`、`os environment: main`、
  `rd: md0` 等启动参数，随后 `RSET / HIT00000040 / BCBK`。

这是第 64 次 SVC 检查点主动停止，不能描述为在第 64 次 SVC 自然卡死，
也不代表 launchd 主循环已运行。加入 SoftwareAES 解决了原来的等待。

## 后续自然运行

该阶段菜单为 5 秒；`zorn_checkpoint=NOHIT` 不会提前命中，独立 watchdog
保持 55 秒 bite。write 已有内容捕获，SVC 入口/返回不再重复记录 write，
以保留更多日志空间。非 write SVC 与 write 内容各自最多记录 512 次。

自然运行镜像 `ee6681fd77ba97a3756a32d82a5d6487ba19428d9cf3cbc6c4c8fc4e5ac88548`
已自动回 recovery，实际输出为：

```text
dyld[1]: Library not loaded: /usr/lib/libSystem.B.dylib
Referenced from: ... /sbin/launchd
Reason: tried: '/usr/lib/libSystem.B.dylib' (no such file, no dyld cache)
```

这是解除 Image4 等待后的下一个实质阻塞，仍未进入 launchd 主循环。
见 [真实 dyld 输出](evidence/dyld-missing-cache.txt)。

## SystemOS 只读设备已通过

OS 窗口内有一层 512 字节扇区的 GPT；SystemOS 直接是 raw APFS，不能复用
OS 的内层分区偏移。两个回调共用传输锁，写入返回 `EROFS`，越界返回 `EINVAL`。

镜像 `25c717a75f4b70706e840b050ce4cd2e420c164c451332193cf207c8b4a84883`
在真机到达 `SYSREAD / SYSRO / SYSBND / SDV19000001 / SYSOK`，主动回收。
实际 NXSB 首块匹配原始 SystemOS，SHA256：
`557802857a9dbf401af64d4ea28f83b16a556a75642c1644aded536657757726`。
806400 个 4096 字节块的容器成功发布为 `md1`。

同轮完整事件还证明 SoftwareAES `start true` → Image4 service found → gate open
→ IODTNVRAM 匹配 → Image4 `start true`，见 [完整日志](evidence/systemos-md1.txt)。

## VerifiedRoot 已在真机执行

主机以独立 owner RSA3072 策略和真实 C 校验器检查 OS 1483785 块、
SystemOS 806400 块，完整窗口摘要为 `e5634d04…`、`b4908cde…`。
私钥仅在忽略的主机输出内，内核只嵌入只读公钥和签名策略。
复制给 APFS 前验证每个完成 DMA 的物理快照；OS 内层容器相对物理区块
错开 1024 字节，最后策略区块只有 1536 字节，均按实际窗口边界处理。

运行 `20261027-083757-c1c7845e` 已实际到达 `VR0OK / VR1OK`，随后
只读 OS 根卷的 APFS UUID、设备号、唯一挂载和健康状态授权返回 `VRQOK`。
SystemOS 挂载已发出真实 UFS 读取，返回的元数据通过区块校验。
该轮将新路径从主机验证推进到真机；后续 SystemOS 挂载成功证据见下节。

这是独立 owner 信任路径，并非 Apple 硬件密钥认证。历史 AMFI 单指令
修补、锁/TLBI/MAC 研究补丁和干净构建限制仍存在。

## 已解除的 SystemOS fsindex 与 IOKit 阻塞

`20261027-090400-866ab388` 在 owner 阶段 3 的 `mount()` 返回错误 2。
缓冲路径探针在挂载后输出，避免并发 best-effort 日志丢失：

```text
/dev              error 0, VDIR
/dev/md1          error 0, VBLK, dev_t 0x03000001
/private          error 0, VDIR
/private/preboot  error 0, VDIR
/private/var      error 0, VDIR
ZCS00000003 ZCE00000002 ZCA00000000 OWNFAIL
```

因此缺失路径不是 ENOENT 来源。SystemOS raw APFS 的前 12 次观察读取全部
成功，不能据此宣称卷已挂载。主机独立只读挂载原始窗口也确认两个 UUID：
OS `04769D26-2CA0-4825-B443-E2E5F88300F2`，SystemOS
`8846FE78-2910-4297-AF97-D59BB6F8FC16`；SystemOS 的完整 dyld 缓存与
子缓存确实存在。主机临时虚拟磁盘检查后已卸载，镜像未写入。

运行 `20261027-091232-840d2a5c` 捕获了原版 APFS printf：

```text
nx_mount:1617: md1 checkpoint search: largest xid 14, best xid 14 @ 9
nx_is_mount_valid:2306: md1 invalid fsindex: -1
apfs_vfsop_mount:2550: unable to mount from /dev/md1: 2
```

因此已定位为卷选择失败，而非容器数据损坏或不存在的路径。证据见
[原始 APFS 日志](evidence/systemos-apfs-fsindex.txt)。SystemOS NXSB 的
`max_filesystems=7`，只有 `fs_oid[0]=1026` 有内容。
Apple 的 [libfs 源码](https://github.com/apple-oss-distributions/libfs/blob/main/FSFormatName.c)
从设备名末尾的 `s1` 解析第 0 个卷；据此进行只读 slice 别名对照，
这条用户态源码本身不能证明内核实现完全相同。

迟至 PID1 路径调用 `devfs_make_node` 的候选连续两轮没有返回/挂载日志；
不能当作成功。改为设备发布时 `devfs_make_link` 后，运行
`20261027-092550-97f8cd70` 捕获 `devfs event log overflowed` panic。
源码中零个挂载平面导致事件数组容量为零，而容量检查在 vnode 检查之前。
已加入最小 2 个事件槽位的修复，保留原来的实际溢出检查，继续真机验证。
所有别名都保留真实 dev_t、几何信息和已验证的只读回调，不伪造 IOMedia
身份，也不绕过挂载返回值、实际 UUID 或 owner 授权。

## 真实存储设备与挂载成功

别名对照 `20261027-092931-5ee7f164` 已选到正确 SystemOS 卷，但原版 APFS
明确报 `fs iokit node was not found` / eligibility EPERM（1）。因此正常路径
改用真实 `ZornUfsBlock : IOBlockStorageDevice`，继续复用既有验证/只读 UFS
回调。原版 IOStorageFamily 和 APFS 创建 IOMedia、UUID 和 BSD 节点；本仓库
不手工填入卷身份。选择时检查真实 UUID、BSD major/minor/name、唯一匹配和
到该具体 UFS provider 的祖先链，挂载后仍重新检查实际只读 APFS UUID。
诊断专用 slice 和 devfs 最小事件数组试验已从正常补丁/发布路径移除。

公共参考源固定 IOStorageFamily `e45fbe30a7879e0b16e26dddb78538f1b00e0bff`，
参考对象只作注释，绝不链接。`build-zorn-storage.py` 在链接前与最终 prelink
后检查 190 个槽位、23 个 override、原版 protected constructor/base destructor
和所有私有导入，拒绝 abstract D0/D1。原版可执行段 SHA256 保持
`852b7846a9039c58fde08478416080af38ffcd5b47c08c889b28497f5f5b4061`。
运行时再次确认父类 0x90、IOService 0x88 与真实父链，然后才注册子类。

首次自然运行被大量正常 VNOP_READ 跟踪覆盖。compact 模式现保留首次各类
读阶段和前 8 个无标签地址，省去重复记录的 FUA 写开销；不修改实际读取。
随后 `20261027-094852-4997cc98` 在 `OWNOK` 检查点主动回 recovery，真机为：

```text
disk1s1 mounting volume DawnUpdate21H461.J120J121J207J208SystemCryptex
vol-uuid: 8846FE78-2910-4297-AF97-D59BB6F8FC16
... mount-complete ...
ZDV01000002 ZCS00000006 ZCE00000000 ZCA00000001 OWNOK
WSTOP RSET TC00000003 HIT00000001 BCBK
```

这证明真实只读挂载、provider 身份、两卷授权和 owner manifest 路径通过；
是成功后主动停止，不能声称已加载共享缓存或已进入 launchd 主循环。
该测试 boot SHA256 为 `4997cc98c076df7b0fa5532402e4c385c84811d4fc212a4ffc687b0b6ad3a914`。
之后已恢复 `NOHIT` 自然运行，继续验证原版 dyld。完整证据见
[SystemOS owner 成功日志](evidence/systemos-owner-success.txt)。

## 共享缓存实际加载与有界长轮次

自然运行 `20261027-095132-1d0b7d21` 已继续进入 dyld 文件加载，多个
`openat` 成功返回真实 fd、`pread` 返回 0x4000 字节、`fcntl` 经过
`CSBI / CSMAC / CSMAD` 后返回。`CSMAD` 在源码中只会在 MAC 签名检查
成功返回后输出，不能误写成它在 MAC 内卡死。

后续 `cs_native4k_prepare` 会验证完整原始 16 KiB 签名块，再从同一已认证
缓冲区派生 4 KiB 页摘要。约 3 GiB 的缓存可能超出固定 55 秒采样窗口。
新增 `zorn-hash-progress` 仅观测真实文件名、已完整认证的 chunk 字节数和
原函数返回值；签名/散列/只读发布决定均不变。`HFBEGIN/HFEND`、`HG/HL`、
`HRE` 保存文件、进度/总量和结果。

当前显式 `zorn_hash_budget=120` 允许在日志 epoch 的前 120 秒内每至少
10 秒 pet 一次，而且只从已通过原始签名验证的 chunk 完成点调用。
停止进展仍有 55 秒硬件 bite；停止 pet 的最晚时刻为 120 秒，之后最多
再等 55 秒硬件回收。主机默认 300 秒，包含 recovery 自身启动耗时。
未设置此参数的镜像保持原有固定采样窗口。此为诊断延时，不跳过验证。

## 已进入原版 launchd 主循环

长轮次 `20261027-100050-478cdb22` 自动回 recovery，启动前后日志不同。
原始系统卷没有改写，使用原版 `/sbin/launchd` 和刚挂载的 SystemOS。
真机输出（日志 RTC 尚为 1970）：

```text
com.apple.xpc.launchd ... com.apple.ptpd [48] ... Successfully spawned ptpd[48]
com.apple.xpc.launchd ... com.apple.rapportd [56] ... service state: running
```

见 [原始用户态日志](evidence/launchd-services.txt)。这已经超过最初的 PID1
入口或 exec 成功检查点：launchd 正在管理系统子服务，dyld/共享缓存足以
支持这段原版用户态执行。服务的完整功能、每个缓存页面、SpringBoard 和
图形桌面均未因此自动视为通过。当前没有可写 Data，也未接入 XNU
MobileFramebuffer/GPU；UEFI 菜单和早期色条不能等同于 iPadOS 图形显示。

当前精简重复 namei、已成功的拷贝步骤和线程阶段，保留拷贝故障、错误、
所选停止点和实际用户输出，以取得后续用户态服务日志。

## 最新无临时 Data 标记的自然运行

解析实际派生 ADT 确认主身份为 iPad7,1 / J120，`osenvironment=main`。
未找到移植补丁强制设置 UID 501；`user/501` 日志不能据此判定身份错误。
实际发现的是恢复内存盘已省去、chosen 仍保留 `ephemeral-storage=1`。
按设备树约定该标记描述临时可写 Data，不能用于这里的只读 UFS 系统卷。
打包器现在随 `--no-initrd` 删除此残留，保留原始 ADT，并在携带 RAMDisk
时保留原声明。主机正反向检查见 [标记合同](evidence/ephemeral-contract.json)。
这项修正没有创建可写 Data，也未改变生产/安全状态字段。

最新 `20261027-102912-28793d46` 已自动回 recovery，取得 19 条完整用户
输出；其中有 `system/com.apple.logd [65]` 的 xpcproxy 状态、
`system/com.apple.distnoted.xpc.daemon [66]` 的 `xpcproxy spawned` 与
`SPAWNED, code = 0`。因此系统 domain 也在运行。type 6 persona 查询
报 ESRCH，但随后仍生成进程，暂不把它单独定为阻塞原因。
相邻轮次还出现硬件/系统变体限制和 plist importer 警告，不能将这些
报错全部当作内核失败或通过强制身份/绕过检查来消除。

最新镜像 SHA256：`28793d4656c2a0126c1f6fe98f391dd09b2622f8e6d59797eaf41bdb938bc059`。
内核：`a136627c83eaf1f6bf5f33de10339d6ff0da343368256b1e7914ad5efd588ab3`。
菜单仍为 5 秒，NOHIT 自然运行，有界签名进度预算 120 秒，主机等待 300 秒。
见 [系统服务输出](evidence/userland-system-output.txt) 和
[最新包内文件核对](evidence/resumed-final-preflight.json)。

## 提前回收已完成真机测试

历史候选 `2f8bbdc4…` 无恢复盘却保留 RAMDisk ADT 占位，触发加载器拒绝，
未回 recovery。机主物理复位后已恢复循环。打包器现移除派生 ADT 的零值
RAMDisk/PackedRAMDisk；非零值仍拒绝，原始 ADT 不变。

固件 FD SHA256 为 `2a43a7994a264a37022d9639eebcc2977a538e376f2f9a44f24be9a12c9e2a2b`。
运行 `20261027-083236-7e1b435c` 的模式 2 在 UEFI 阶段主动停 CPU，
随后自动回 recovery，启动前后内核日志一致，符合未进入内核的预期。
bootreason 为空，不能仅由这一轮断言具体复位源或精确 bite 时长。
后续模式 1 真机内核记录 `WON`，确认接管时 Gunyah watchdog 已开启。

主机 BCB 写入已在真机多次读回验证：只替换 4096 字节 misc 页中的前
864 字节，保留尾部，无 wipe 参数。每轮核对 serial、product、slot b、
镜像 ready/SHA256，并保存启动前后日志摘要。最新轮次均自动回 recovery。

## 实验入口和未完成范围

统一入口为 `scripts/build-zorn-debug.py --incremental-patched-tree --early-watchdog 1 --boot`，
在三个仓库共同父目录运行。当前默认 `out/zorn/boot.img` 是模式 1 的最新
诊断候选；模式 2 独立测试镜像和首次 owner 候选各有同名 inputs 清单。
实际哈希与结果见 [续调快照](snapshot-2026-10-27-resumed.json) 和
[运行索引](evidence/resumed-runs.json)，不是桌面发布镜像。

尚未完成：可写 Data、完整图形显示/呈现、输入和桌面，以及各子服务/外设
的功能验证。菜单仍为 5 秒，系统卷只读；本轮仅写既有 userdata 日志
块和 misc recovery BCB，没有重新刷系统卷、boot 分区或切换槽位。

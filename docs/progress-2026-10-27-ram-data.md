# 2026-10-27：独立 RAM Data

本轮按机主要求继续无人值守；到需要确认真实屏幕画面或触控时暂停。

## 已验证

- 原只读 UFS OS/SystemOS 及 launchd 基线保留，新增独立 `zorn_ramdata_defconfig`。
- 原版 RamBlock 经与 UFS 相同的 190 槽 IOBlockStorageDevice ABI 校验，24 个自身覆盖槽；公共参考对象不链接。
- 512 MiB APFS Data 由 DBRDISK1 保存约 1 MiB 非零页；仅在 RAM 中可写。持久 store 回调明确返回不可用，没有向 UFS 提交 Data 写入。
- 引导前核对逻辑/编码 SHA256，内核核对种子 SHA256/容量，挂载后核对真实设备、APFS 类型、UUID 和非只读状态。
- 真机首次挂载：`20261027-113540-eb2d02fc`，`DST=4 / DRE=0 / DRO=0`。Data 是 `/dev/disk1s1`，SystemOS 动态变为 `/dev/disk3s1`；选择依据为 UUID，没有依赖固定 disk 编号。
- 真实文件试验：`20261027-114302-a00d9f84`，`DPT=7 / DPE=0 / DWR=1 / DER=0 / DATAOK`。在 `/private/var/tmp` 独占创建文件，写入 64 字节、同步、关闭并重新打开无缓存读回、比较、关闭、删除并确认 ENOENT。正常 VFS/MAC/APFS 授权，没有绕过鉴权。
- 两轮均自动回 recovery，并取回本轮变化的日志。只操作 K80 `92988a43`；CC9 `f85d4270` 未操作。

## 输入与边界

实际种子 UUID：`C7D77FF3-6437-4C4A-8E05-E8E239AC1641`。逻辑 SHA256：`4d9b3e43255e940e928e34cc901a6ae2c09d28352e763a7406d61ee377576db8`。编码 SHA256：`063bacc7cdef9ceca89e0cc57042af23af14d6a50c1bc43092fe44a2f0dde695`。

初始 var 骨架来自固定原版 OS，只复制 39 个普通文件（611715 字节），保留链接，排除 staged_system_apps，并添加空运行目录。未添加用户身份记录或密钥。主机 owners-off 准备没有保证属主保留，完整服务权限仍待验证；root 文件读写成功不能代表所有用户及服务目录权限正确。

Data 不持久化，512 MiB 尚未进行容量/长期运行验证。原 Apple 镜像保持不变；Android userdata 中现有 SHNGROOT 布局保持不变，既有诊断日志块和 recovery BCB 的读回流程继续使用。没有 flash、erase 或槽位修改。

## 继续验证

当前正在执行挂载完成后自然继续运行的 watchdog 轮次，观察 launchd 子服务与可写 Data 的实际行为。此文件随后补充最终轮次。尚无 iPadOS 桌面、GPU 或触控通过结论。

显示参考为本机官方 `docs/zh/porting/display.md` 与 GopFramebuffer/sheng 实现；小米 14 的 iOS 16.7.16 显示用户客户端 ABI 与本机 iPadOS 17.7.11 不同，不能直接接入。

## 追加：服务与显示生命周期

- `20261027-114457-ef4f28eb` 自然继续运行后进入 user/501 服务域；containermanagerd、cloudpaird、imagent 已有 xpcproxy 生成记录。
- `20261027-115155-a025d381` 的新 exec 观察记录了 runningboardd、bluetoothd、sharingd、imagent、siriactionsd、identityservicesd、CommCenter、cfprefsd、nfcd、usermanagerd 的实际镜像 activation 返回 0。此状态不等同于完整服务健康或已进入它们各自 main。backboardd/SpringBoard 有启动安排记录，暂未证明桌面。
- GopFramebuffer 主机校验通过：358 个 Legacy 槽位、24 个覆盖、193 个原版绑定，MobileGraphics/IOSurface 可执行段与固定输入一致。
- 初次显示试验的钩子早于 zorn UFS 日志，结果会被后续日志覆盖；已将真实初始化延后到 UFS/logger/watchdog/PMGR 之后。
- `20261027-120558-528b6aa8`：真实原版元类身份和大小 `0x18a0` 通过，构造、init、release 完成（DSS=4 / DSE=0）。DSPDONE 自动回 recovery。
- `20261027-120751-2fa7a526`：DSM=1，真实 1440×3200 GOP 映射通过，registerService 已调用；最初即时状态检查返回未就绪。下一轮使用真实 registryEntryID 匹配作有界异步发布验证。

CPU 呈现与实际屏幕仍待验证；触控未实现。当前 XNU 所有内存窗口仍为 384 MiB，与 512 MiB 的稀疏逻辑 Data 容量及整机 12 GiB SKU 不同。后续会采集实际页面计数；未把整机容量当作 XNU 可用内存结论。

## 追加：发布通过与 CPU 系统启动试验

- `323fe6ee` 显示发布候选：DSS=10 / DSE=0 / DSZ=0x18a0，真实 entry-ID 匹配通过，并在 DSPDONE 自动回 recovery。生命周期摘要改为有界获取日志写入权后一次提交，避免被临时忙状态丢弃。
- `20261027-121313-aeecc28c` 的自然运行记录了 UserEventAgent、rapportd、mediaserverd、fseventsd、iomfb_fdr_loader、notifyd、ReportCrash 的 running 状态。独立 RAM Data 累计 85 次实际块写入、错误 0；XNU 仅剩 711 个空闲 4 KiB 页，约 2.8 MiB。
- 已核对官方 ipados-17.7.11-21H461 OS profile 的三条显示启动兼容 text-fixup，原始缓存文件字节全部匹配。仅将该表加入 CPU 显示试验的派生 ADT；原版镜像不改，既有内核机制仅在页面原始签名校验通过后、原始字节一致时修改 RAM 页面。
- 机主回到设备旁，明确优先进入系统，触控后置、GPU 暂停。新增 display-mode 3 选用现有 CPU 呈现/验证/完成路径，逻辑 PM、2 倍 UI scale 和 60 Hz 软件通知计时器；不声明物理面板刷新率。
- 512 MiB XNU 窗口由 DarwinBoot 仅从真实 UEFI ConventionalMemory 申请，失败即拒绝，不映射猜测的内存。512 MiB 与稀疏逻辑 Data 容量同值但用途不同，仍未开放整机 12 GiB。
- `f9d8fa5c` 候选开始自然启动；机主观察到色条 + WRGO，已越过 UEFI 分配并进入 XNU 日志。CPU 图形帧、系统桌面仍待本轮结果。

## 8 GiB 内存上限试验

机主根据小米 14 开发者建议要求提高内存上限。K80 recovery 的只读 live FDT
记录了 11 个 DRAM 条目和 45 个保留区条目；高地址两段相邻的 3 GiB 与 6 GiB
合并后覆盖 0x8c0000000–0xb00000000，DT 保留区没有覆盖该 9 GiB 范围。
这只是 DT 可用范围证明，不等于运行时已分配。原始 DTB 留在忽略的 out 目录。

ZornBootMemoryDxe 原来只新增最多 1 GiB 且只接受 4 GiB 以下的地址。新候选
允许真实高地址 DRAM，仍扣除全部 GCD 已知区域、reserved-memory 和 FDT reserve
map；非法/溢出的表会拒绝。先通过 ArmMmuLib 建立 WB 映射，再向分配器登记，
避免页表分配器收到尚未映射的新高地址页。包内加载器上限仍为 8 GiB，构建器
--memory-mib 8192 与其一致。没有把整机 12 GiB 作为一块可覆盖保留区的内存。

固件 cab23145 已构建，当前 --early-watchdog 清单与实际 FD/源码哈希匹配。
55be9b33 的首轮 8 GiB/PMOK2 控制试验自动回 recovery，但日志与启动前完全
相同，因此未进入可观测的 XNU，不把旧的 SpringBoard 日志归因到 8 GiB 镜像。
同镜像第二轮 `20261027-130355-55be9b33` 也自动回收且日志未变。机主照片确认
`window 0x200000000`（8 GiB）、内核 PA `0x8c007c000`、入口
`0x8c77e2488`：UEFI 高地址分配已通过。绿色交接条及 XNU 入口红条可见，
页表完成的青条尚未出现；停止范围缩小到早期页表建立。

512 MiB / wfi=0 轮次 49477254 已自动回收，出现 dyld[78] 的 ProcessAtlas.cpp:1880
断言。Apple 官方 dyld-1125.5 源码确认该位置为已映射文件卷 UUID 的查找断言；
其根因和 8 GiB 是否改变此行为尚未确认，没有删除断言或改写原版系统镜像。

## 8 GiB 早期页表容量修正

原 native 4 KiB bootstrap 池为 16 页。8 GiB 非 1 GiB 对齐窗口的 V=P
与 KVA 映射分别最多消耗 9 个 L2 页，另有两个根和一个 framebuffer L2 页，
最多需要 21 页；原容量保护会在进入 C/UFS 日志之前停机。新增板级补丁
`zorn-8g-bootstrap-capacity` 将该池扩大到 32 页，保留汇编越界保护、
既有内核虚拟地址布局和 40 位物理地址宽度。补丁正向/反向应用及镜像一致性
检查通过，生成 assym.s 为 131072 字节。

`20261027-131211-d3dc6081` 真机 8 GiB/PMOK2 控制试验已通过：
日志 SHA 与启动前不同，记录 VR0OK、VR1OK、SYSOK、PMOK2，约 51 秒自动
回 recovery。已越过页表停止点并通过 XNU/UFS/存储身份和 PMGR 控制路径。
随后移除 PMOK2，保持 8 GiB/CPU display mode 3，验证用户态及实际呈现；
本结果不代表已进系统桌面或完成整窗内存压力测试。

## 8 GiB 自然启动：内存压力已显著缓解

`20261027-131412-49d2037a`（镜像 `49d2037a…`）移除 PMOK2 后自动回收，
取得与启动前不同的新日志。108297 ms 的实际 VM 计数为 free=1774805、
active=20640、inactive=32854、wired=92560 个 4096 字节页，空闲约 6.77 GiB。
独立 RAM Data 已发生 reads=72、writes=112、errors=0，未持久化到 UFS。

显示摘要 stage=10/error=0/registered=1，但 clients=0、accepted=0、
transfers=0、pixels=0。SpringBoard[106] 已记录 service state: running；
backboardd[96] 有 uncorking domain 记录。running 是 launchd 进程状态，不能
推导为已完成应用初始化或系统桌面。最后 340 个日志词没有此前 dyld 断言，
但环形日志不足以证明全程没有断言。机主没有观察该轮屏幕，已要求同镜像重试。

当前后续重点是 GUI 用户进程的装载/等待和实际显示客户端连接；触控后置，
GPU 暂停。8 GiB 不是 12 GiB SKU 的整窗内存压力测试或完整外设稳定性结论。

## 同镜像复测与后续 GUI 采样

`20261027-132015-49d2037a` 再次自动回 recovery，取得新日志。机主照片确认
仍为 UEFI 背景、色条和 WRGO，未见苹果标志/系统界面。WRGO 在 logger 置为
armed 之前绘制，之后 zorn_log_only=1 只保存持久日志，所以该词不是最后执行位置。
本轮最后日志是 launchd 的 user/501 plist 导入/装载提示，不能将上一轮
SpringBoard[106] 的状态当作本轮的最新进度。

新增显式 `--gui-watch`（仅 display-mode 3），参考本地 houji 的 userland sampler：
最多 12 次、间隔 15 秒；每个目标最多 4 个线程、每线程最多两个用户栈帧。
选择 launchd、SpringBoard、backboardd；持有 task lock 时只采寄存器及状态，
解锁后使用独立引用的 map 读取用户栈。寄存器/栈是观察值，可能与运行中的进程竞态，
超出上限会标注 truncated；不暂停进程、不改变退出值/鉴权、不从定时采样 pet watchdog。
另保留四条关键进程的真实 exit status/reason，并随 VM/RAM Data/display 摘要输出。

新补丁 `zorn-gui-observer` 的正向/反向应用和主仓库镜像检查通过，Python 语法及
非法 profile 组合的提前拒绝通过，原有 AES/storage/RAM/display 链接后审计通过。
构建曾因 libpthread 参考目录的未跟踪 .DS_Store 被完整性检查拦截；元数据已保留到
忽略的 out/zorn/build-metadata，参考源码保持 clean，未关闭检查。

候选 `07ebe68e2e02825cb6402ee4a3d79b29356d017250a188b11a9d961a04f65bb3`
已生成；`20261027-132806-07ebe68e` 因 K80 在 adb/fastboot 都不可见而停止，
尚未发出这份候选的 fastboot boot。待恢复连接后继续实测，不能将编译通过当作
采样运行通过。可用构建身份及当前验证边界见 snapshot-2026-10-27-ram-data.json。

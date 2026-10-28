# 2026-10-28：官网、小米14与K80当前启动卡点复核

本次范围是分析、日志取证和路线整理，没有新启动或修改设备。正在运行的
`2ddf7cb4` 已于北京时间08:31:14自动回到recovery，取得新日志。
结论：已进入官方启动验证第7阶段的用户态，但没有欢迎页、锁屏或桌面证据。
平台同步仍存在未验证的早期绕过，不能把进入用户态等同于平台完全适配。

## 资料与基线

- 官网：[移植步骤](https://unixnu.com/zh/porting/steps)、
  [构建](https://unixnu.com/zh/building)、[技术参考](https://unixnu.com/zh/reference/)。
- 进一步核对：[启动验证](https://unixnu.com/zh/porting/bring-up)、
  [UFS](https://unixnu.com/zh/porting/ufs)、[显示](https://unixnu.com/zh/porting/display)、
  [GPU](https://unixnu.com/zh/porting/gpu)、[Skip Setup](https://unixnu.com/zh/guide/skip-setup)、
  [平台身份](https://unixnu.com/zh/guide/mobilegestalt)、
  [源码与补丁](https://unixnu.com/zh/xnu/source-and-patches)。
- 本地 `UniXNU-houji` HEAD：`d4fb1472c86210303e36f311c07411dd486a753f`。
  核对README、SOURCE_SNAPSHOT、board.toml、migration-upstream-research、skip-setup、
  display-performance及SweetFramebuffer实现。下述小米14实测结果属于其作者记录，
  本次未重新测试小米14，也未执行它的设备脚本。
- K80保持iPad7,1/j120ap、17.7.11/21H461、XNU10063.141.1、8GiB、CPU0、
  只读UFS OS/SystemOS、512MiB易失RAM APFS Data及既有lite服务策略。

## 本轮新增的直接证据

对应 `out/zorn/debug/20261028-081509-2ddf7cb4`，已核对run为recovered、
kernel_log_changed=true、run/build输入与ready归档一致，以及完整镜像与内核SHA。
boot SHA：`2ddf7cb4e126404cd1689c6ec90a6214a9c4c9d038e6f2cab549d3a759016d82`。
kernel SHA：`fb22283c77762d85225e7bacc1d0097b49dded4089e2c596f139e2add91ebd79`。
解析使用该归档内核和已验证的原版共享缓存补充符号。

最后保留tick57/stage11/857487ms；没有完整末段GUIEND，不能称60次观察全部完成。
08:30:21的定时单帧仍是苹果标志，图像SHA与元数据一致；不是系统界面。

- `lsd`主线程TH_RUN，首次读取14帧真实保留内核栈，读取错误0：用户缺页异常 →
  `vm_fault_internal` → `lck_rw_lock_shared` → `lck_rw_lock_shared_gen` → 中断抢占/调度。
  这证明采样时处于VM读锁争用路径，不证明同一把锁永久死锁，也没有锁持有者证据。
- 初始最近符号显示`IORWLockRead`。准确内核的nm与反汇编确认它和
  `lck_rw_lock_shared`同址`0xfffffff00b892e5c`；`vm_fault_internal`在
  `0xfffffff00b93ad8c`实际调用后者。结合源码`vm_map_lock_read(map)`，
  不应把这个别名误解成显示驱动的I/O锁。
- SpringBoard主线程13帧内核栈，错误0，位于Mach消息发送的
  `ipc_mqueue_send_locked`及抢占路径。最后IPC记录出现backboardd/notifyd，
  但该记录并非和线程栈原子对应，不能直接宣称某个接收方永久不回复。
- backboardd原编号8为IOMFBServer线程的CFRunLoop用户栈，10帧/错误0；
  该轮IOMFB线程在8，之前在4。线程原编号不是跨启动的稳定线程身份。
- 显示accepted7、完成传帧6、末错误0。两者差1尚不能推定掉帧或fence故障。
  已有少量传帧，不等于桌面场景完成合成，也没有持续刷新资格。
- Data权限232/232、真实卷UUID正确、剩余300089344B（约286MiB），RAM读126/写7724/错误0。
  空闲1284561个4KiB页（约4.90GiB）。这次没有容量耗尽证据。
- UFS读取1067180个4KiB块、传输错误0，read_us76651579、log_us9208747。
  计时含锁等待/抢占，不能相加推算墙钟占比或纯硬件速度。

证据：`docs/evidence/gui-runnable-kernel-{run,state,symbols,camera-observation}.json`，
及同前缀`vm-fault-lock-call.txt`、`rwlock-aliases.txt`。摄像头原图留在忽略的out，
没有复制房间画面到发布仓库。74z的有界RUN内核栈路径已有本次设备成功读栈证据；
不等于该诊断解除了启动阻塞，或已完成全部负例的硬件验证。

## 当前卡点：已定位范围，还没有唯一根因

1. **优先排查内核同步与缺页路径。** 真实VM读锁争用与现存早期锁修改相交：
   工作树`osfmk/kern/lock_rw.c`仍有强清INTERLOCK、修改can_sleep及原子失败后写锁字的路径。
   这些不是纯诊断，可能破坏锁状态或等待关系；但本轮没有证明具体哪一条造成停顿。
   应先记录锁地址/状态、持有者或写锁调用点、等待时长与重复栈，再做最小恢复原语义实验。
   此前整体恢复锁曾在新日志前失败，不能再次不加分辨地整体回退。
2. **LaunchServices的等待链未闭合。** 历史多轮看到数据库seeding group、
   SpringBoard经ControlCenterServices等待数据库。那些主要是消费者等待栈；
   还没证明负责完成数据库初始化的线程为什么不推进。本轮给出了更底层VM争用线索。
   下一次按实际栈/线程身份选择生产者与锁持有者，不继续机械递增线程编号。
3. **显示首帧到桌面仍未闭合。** UIKit主循环、IOMFB线程和苹果帧分别有证据，
   但没有稳定完成的桌面。服务启动顺畅后才将swap序列、surface内容、复制及完成通知串起来。
   CPU呈现是复制已生成surface，不能称为完整软件Metal/OpenGL渲染器。
4. **诊断本身也要隔离。** 用户栈读取可能缺页；最终footer只保留有限快照，
   不能说明15分钟一直停在同一函数。新读栈路径只读取非当前线程的保留内核上下文，
   本轮成功不免除观察者效应检查。后续保留少量早/中/末摘要或重复栈计数，
   在原4KiB范围内给出时间关系，并用减少用户栈读取的对照区分业务阻塞与采样影响。

## 小米14可借鉴的部分与差异

houji记录的桌面成功基线是iOS16.7.16/20H392、Darwin22、HFSX完整可写根卷。
其r54在双核阶段已到桌面，八核r56随后改善性能；GPU尚未可用于桌面加速。
因此八核和硬件GPU不是该成功基线的先决条件，但也不能推导17.7.11具有完全相同的兼容路径。

可复用的是方法：固定可恢复基线、区分服务等待与硬件停机、真实权限校验、
匹配系统版本的迁移偏好、官方开发板ADT身份、CPU呈现时序/生命周期、
新增CPU先独立验证定时器与IPI。SM8650硬件经验有价值，面板/触控/内存保留区仍须用K80输入。

不能直接复制的是Darwin22显示user-client ABI、锁/页表补丁、HFSX镜像安装脚本、
固件内存图和设备绑定。houji源码快照本身也明确尚未验证全新电脑一键构建。

houji单独隔离CoreLocationMigrator未解决启动；其后使用匹配版本的迁移基线，
加skip-Setup偏好与开发板ADT才到桌面。这不支持继续盲目禁用更多Apple组件。
K80已具备21H461迁移/skip-Setup/no-auto-dim种子、开发板四属性、开发WiFi身份、
lite服务策略和guest权限修复；应查实际消费/错误，而非再次添加同样的配置。
服务策略文件落盘成功尚不能代替所有launchd内部状态的验证。

K80的RAM Data每次重启回到相同种子；houji的可写根卷保存首次启动成果。
这是重要实验差异，可能反复重做数据库初始化，但还不是本轮VM锁争用的证明。
若后续证实启动成果被丢弃是瓶颈，可设计可回收Data快照或匹配版本的预置数据库实验；
当前不因此扩大设备写入范围，不直接迁移到可写userdata，不把512MiB未满误当容量不足。

## 后续顺序与验收门槛

1. **先锁定可重放的观察基线。** 保留2ddf7cb4与已到UIKit主循环的归档，
   保持8GiB/CPU0/原服务集合；每轮只更改一个诊断或修复因素。
   不因一次色条或苹果标志就更换系统版本、内存、服务、CPU配置。
2. **针对VM读锁查持有者和时间关系。** 优先回答同一锁是否反复争用、
   写锁线程是否能调度、抢占/中断/内存属性是否一致、采样是否参与等待。
   有证据后逐项恢复正常同步语义；禁止强行解锁、伪造成功或吞错误来追检查点。
3. **验证LaunchServices初始化真正完成。** 以生产者退出初始化、数据库查询成功、
   SpringBoard不再同步等待为门槛，而非某次main runloop或线程窗口为空。
4. **确认CPU桌面链。** 对应一次真实桌面场景的surface提交、复制和完成通知，
   再以摄像头/机主确认欢迎页或桌面。若服务完成却无帧，再集中核对17版显示ABI/软件路径。
5. **之后触控，再性能。** 按用户优先级适配K80触控；多核须先解决跨核TLB、
   日志并发、IPI/逐核定时器，默认CPU0保持；硬件GPU继续后置。

仓库整理走独立输出目录：本次`./unixnu status --json`仍是schema1、空patch_order/组件报告，
设备缺正式feeds.toml/porting.toml/AGENTS.md等格式2输入；驱动实际由archives构建，
不能把空组件报告误说成没驱动。增量构建成功不等于干净补丁重放成功。
先梳理实际源版本、依赖、按序补丁和历史候选依赖，再迁移DTS/组件/记录，不能仅改schema数字。
这一工作影响复现质量，但没有证据说明目录格式导致当前运行时锁争用。

## 总进度边界

已验证：UEFI菜单/加载器、CPU0 XNU与8GiB窗口、UFS只读系统根、原版APFS/launchd、
RAM Data基础读写及关键权限、部分系统服务、CPU苹果帧、持久诊断/自动回收/定时单帧。
未验证：稳定进入欢迎页/锁屏/桌面、完整同步正确性、完整可持久Data、触控、
多核运行、GPU加速及日用硬件、全新检出可重放构建。
不提供总百分比：早期启动已打通，但剩余内核正确性和图形初始化工作量无法由检查点数量估算。
当前最近设备状态为08:31回收成功；本次分析后没有另启镜像、改槽、刷分区或提交Git。

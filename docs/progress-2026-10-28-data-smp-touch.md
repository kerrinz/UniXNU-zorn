# 2026-10-28：Data保留 → 全部CPU核心 → 远程触控尝试

机主已通过远程摄像头确认系统锁屏，明确按上述顺序恢复真正无人值守调试。
当前阶段为Data保留。CPU0继续作为存储验证基线，触控和GPU尚未启用。
既有锁屏本身不再触发暂停；需要物理复位、实际触屏或回收不可恢复时才暂停。

## 已确认的系统基线

f8533418的第二轮 `20261028-095307-f8533418` 于10:09:42自动回recovery，
changed log及准确boot/kernel归档已核对。机主确认锁屏；末样本tick60/stage12，
完成8次传帧，RAM Data剩余289636352B。此前第一轮摄像头也确认锁屏。
没有验证解锁桌面、触控、全部CPU或生产环境数据保护。

这两轮均为易失RAM Data。10:09回收前没有导出运行后的RAM，不能找回那些内存内容。
本阶段从保存的不可变种子开始建立保留机制，不假称已恢复上一轮初始化成果。

## 已完成的Data区域准备

复用固定上游RamBlock的 `PersistOverlay.h` / `DirectDisk.h`，不复制houji的HFSX安装脚本。
基种子仍为512MiB APFS、UUID `C7D77FF3-6437-4C4A-8E05-E8E239AC1641`、
SHA `fa0174317c0f3d4a3b566341f0b421f13e35627b25e28f7de3a51b45ea5e4bd5`。
变化页使用单独的userdata区间；系统OS/SystemOS及原4KiB日志块保持原布局。

在92988a43/zorn/b的recovery实际只读核对双GPT、分区容量、SHNGROOT manifest及边界块：

- userdata：绝对4KiB LBA `3112704..64049146`，249595670528字节。
- Data专用区：分区内偏移10GiB（LBA2621440），绝对LBA5734144，131077块。
- 总长536891392字节：1块header、4块bitmap、131072块变化页。
- 既有系统镜像9382658048字节、日志相对LBA2291712，均在此范围之外。
- 区间完整前像已压缩备份并完整解压核对，SHA
  `61db490b9960cc5e17b8aa4359fe2599a33506be896b8fb17057f64aae79f7e0`。
  备份留在忽略的out，不发布旧分区内容。

`prepare-zorn-data-store.py`只读准备计划；`verify-zorn-data-store.py`在有效mode1探测、
再次核对完整前像、设备身份及边界后才允许显式初始化。
本次已只写入5个4KiB元数据块；之后全区读回SHA为
`920013a9c20632f23ce4369a7ee784addc2597047b049fcd76b0f747615d1932`，
与“前像仅替换这5块”的计算结果一致，双GPT、系统manifest及两端保护块不变。
已安装元数据不等于已保存初始化成果。

## 驱动边界与主机检查

`ZornDataStorePolicy.h`固定该设备的精确分区/窗口；传输沿用原gHost锁、DMA队列、
超时和poison处理。默认mode0仍关闭。mode1拒绝Data写入；mode2只有验证打开后，
允许精确窗口内最多32块的FUA WRITE(10)及真实SYNCHRONIZE CACHE。
其他写入仍只有原日志块及受限misc recovery BCB。OS回调仍拒绝写入。

store_open先核对双GPT与完整header的版本、大小、CRC、种子身份，再交给上游overlay。
错误种子/损坏/外来header直接拒绝，不交给上游自动清空；禁止reset参数。
新GPT校验使用原子占有的静态缓冲，避免把36KiB数组放上内核栈。

实际policy/provider及未修改的上游overlay已在宿主控制中执行，验证范围/CRC负例、
只读拒绝、错误header/GPT、读写/同步失败传播、poison后不写DMA以及变化页恢复读回。
这些是主机检查，不能替代设备持久化资格。
实际链接已核对6条provider bridge及原hostScsiDir调用。
后续mode2还要核对原始open/write/fsync/重新open/read/fstat调用，不能以空stub替代。

## 只读探测与超时记录

09e55e9a于10:40:17临时启动，只读mode1，60秒GUI hold、240秒主机上限。
主机240秒先超时退出；随后手机自行回recovery，未发额外重启。
原失败run保留为 `run-failed-at-host-deadline.json`，迟到取证后run另记
host_deadline_exceeded=true / bounded_recovery_qualified=false，不能称按时回收通过。

新日志实际显示 `DSTORE mode=1 open=0 state=4 header=9 gpt=0/255 present=0 writes=0 loaded=0 errors=0`：
双GPT校验成功，未初始化的外来header被拒绝，运行中的Data仍是RAM副本。
回收后全区SHA与前像完全一致，保护边界也未变，mode1写保护获得这次设备证据。

源码核对发现独立exec进度可在180秒内继续pet，60秒GUI hold不代表60秒就复位。
原240秒主机余量不足；新构建器/runner统一拒绝低于 `max(GUI hold,180)+180` 的GUI回收预算。
正常900/1200窗口满足此限制。12项既有摄像头/绝对deadline控制和新预算边界检查通过。
本次是主机期限测试失败；设备实际自动返回，不需要机主物理复位。

## 下一项设备验收

mode2候选增加普通文件 `/private/var/db/.unixnu-data-retained`：只在首次不存在时创建，
写入固定种子身份和当次cookie，fsync后重新打开读回。后续只读该文件，拒绝错误内容、
符号链接、错误属主/权限/设备号，不截断或删除旧标志。
`DKEEP state=1`表示创建并读回，`state=2`表示读回已有文件；必须跨两轮cookie一致，
且DSTORE恢复、错误计数、APFS挂载与实际启动阶段相符，才算Data保留初步通过。
mode2首次真机运行和跨启动结果仍待测，不能在此处填为成功。

当前保持原offline开发板/无保护key-store兼容配置。这不是SEP、口令保护、
加密持久Data或生产安全资格；持久写入模式和OS对ephemeral fixture的启动行为还需分开验证。
种子内容保持不变，不通过更换种子/自动reset清理已建立的overlay。

## 后续阶段门槛

Data跨启动验证通过后才进入多核：ArmCpu汇编修正、跨核TLB、日志原子性与旧锁绕过，
先独立验证逐核CPU_ON、MIDR/MPIDR、定时器、IPI和绑定任务，再逐步到8核用户态。
ADT列出8个节点不算全部核心在线。

最后按K80原厂资料核对触控芯片/总线/供电，再尝试读取芯片状态和发布HID设备。
机主远程没有实体触点，最多报告自动探测/注册，不声称触摸坐标或手势可用。
硬件GPU继续搁置。Git提交和推送仍由机主处理。

## 本机空间整理

仅对旧生成镜像/内核作完整gzip解压SHA核对后压缩，恢复方式记录在本地journal。
既有bootstrap和锁屏基线保留。另对生成的userdata-root.img中438个已确认全零的1MiB区间
释放宿主物理分配，操作前后完整SHA均为原 `fd43ee70…03093`，逻辑字节完全相同；
没有修改手机系统卷或删除IPSW、密钥、分区备份。此整理不作为设备功能进度。


78c070a8（boot SHA 78c070a81ce4c8d2cedd6e30fda93c43c1d8928b772e51b3b4146d4b4570104a，kernel SHA 6b574e6f77f84097b890db44bc57dbd316d2b01e1d98db68944b4e1ef5e56711）已通过全部检查、真实provider/marker调用审计与ready归档哈希核对。2026-10-28T10:58:20+0800仅对92988a43/zorn/b临时启动首次mode2写回轮次，BCB保留尾部并读回、fastboot发送/Booting成功。900/1200秒与末段单帧，尚无新回收结果；Data保留未判通过，多核/触控未启用。
11:13:31绑定78c070a8的末段单帧（900.378秒触发）已见系统锁屏时钟/底部手势条，图像SHA核对一致；未操作解锁/触控。尚待回收DSTORE/DKEEP记录，不能据画面判定Data已保留。

## 11:14首次Data写回成功；低亮度插队

78c070a8于11:14:55在1200秒上限内自动回recovery，changed log及完整boot/kernel/ready归档一致。
实际记录为 `DSTORE mode=2 open=1 state=2 header=0 gpt=0/0 present=58340 writes=80450 loaded=600 errors=0`，
`DKEEP state=1 error=0 cookie=2c59d71a`。APFS UUID正确，剩余295899136B，RAM接口150读/10300写/0错误。
末样本tick60/stage12/917243ms；lsd与SpringBoard主线程到事件循环，实际用户栈错误1仍保留。
本轮backboardd原编号8解析到CoreMotion/CFRunLoop，不能沿用旧轮的IOMFBServer身份。
锁屏照片与此轮绑定。首次文件创建、同步和重新打开读回已通过，跨重启保留尚未验证。

机主随后将“硬件低亮度，降低长时间调试屏幕发光强度”插到最高优先级。
已核对recovery=92988a43/zorn/_b、panel0-backlight最大16383、当前brightness/actual_brightness均0（自动灭屏）。
因此先保留现有overlay，在下一次长观察前完成面板亮度控制；不重置Data，不启动Android。
真实面板o11_42_02_0a及DCS/高字节优先/DSI0 v2.8地址已从实机FDT与MiCode固定源码核对；
当前UEFI使用SimpleFb，没有可直接调用的厂商亮度实现。第一步候选仅读取DSI寄存器，
在BLSNAP自动回收；还未发送亮度命令、未宣称屏幕已经调暗。

12:19低亮度短测d22986fe真机通过：307→64，单次写后新鲜读回64、ACK/TIMEOUT均0，自动回收。详见[亮度记录](progress-2026-10-28-brightness.md)。短测未运行完整GUI；已有Data重复启动权限模板在 `/private/var/containers/Temp` 的ENOENT仍待修正，不重置overlay。

## 低亮度常规启动与已有Data模板分离候选

8ebb2922已完整构建/归档检查通过，并已定向临时启动；900秒观察、1200秒回收、600秒摄像头单帧。`--brightness-mode 3`使用已在d22986fe实测通过的307→64路径，成功后继续启动。新增`--retained-data`要求mode2+metadata policy，先通过只读现存marker验证（同卷、root所有权、0600/48B、魔数/种子SHA/cookie），再保留系统初始化后的目录和权限；不存在/错误即拒绝，不创建、不重置。DataPermissions stage4/checked0表示保留既有状态，不冒充重新验证232项。实际链接审计确认只读helper调用open/fstat/read/copyin/close及卷模式守卫，且没有write/chown/chmod/mkdir等修改调用。尚待本轮DKEEP2/相同cookie和APFS/GUI实测。应用定时续调于12:15:53已为PAUSED，本次更新仅保存新提示并保留暂停状态；现场单轮脚本的自动回收仍独立运行。

## 12:30：已有 Data 探针碰撞，修复候选构建中

8ebb2922已自动回recovery，status/recovered、新日志及准确boot/kernel/ready归档核对通过。实际APFS挂载成功，UUID仍为C7D77FF3-6437-4C4A-8E05-E8E239AC1641，但固定O_EXCL文件名的读写探针返回EEXIST（DPT1/DPE17），导致Data mount错误路径提前退出。没有执行到只读DKEEP验证；本轮不能作为跨启动保留或常规低亮度完整GUI通过的证据。

修复仅将探针文件名改为本次计数器加有界8次编号，O_EXCL及NOFOLLOW保留，碰撞不删除旧文件。不绕过Data卷身份、真实写入/fsync/重新打开读回/删除/不存在证明。实际函数主机故障注入7项通过，包含多次/全部碰撞、创建失败、fsync失败、读回不符和copyout失败；readonly retained marker的13项检查也通过。两组检查纳入构建和归档，模拟不等于真机。当前正在构建新候选；Data仍未宣称跨两次启动验收通过。

机主已回到手机旁。应用定时续调状态仍保留PAUSED；本轮手动授权工作继续，单轮自动回收独立生效。CPU0保持，多核和触摸尚未进入验收。

12:45更新：`eb55ebe5`完整构建和64项输入哈希/boot/kernel/ready归档通过，新增7项真实探针函数与13项只读marker主机检查均随归档保存。仅92988a43/zorn/b定向fastboot boot已成功；900秒观察/1200秒回收，600秒摄像头。运行结果尚待回收，不先判Data保留或完整GUI成功。旧历史boot的gzip整理因APFS共享块反而增加占用，已用COW副本逐块恢复并逐份核对完整SHA，撤销此次boot压缩；所有原始boot字节保留，未触碰手机备份或固件原件。

## 12:53：首次跨重启保留与常规低亮度通过

机主确认eb55ebe5显示系统锁屏、触摸无响应，随后手动回recovery。固定92988a43/zorn/_b已只读复核；原始4KiB日志再次读取完全一致，与ready boot/kernel归档匹配且不同于启动前。最初采集脚本只允许Data权限stage0..3，误将新的stage4判为格式错误；已严格支持stage4（error0、checked0、root0:0、非零total），7项新旧解析/反例检查通过。原failed run.json保留为run-before-parser-repair.json，当前状态为recovered并明确owner manual reboot，不能算自动回收验收通过。

实际DKEEP state2/error0/cookie2c59d71a与首次78c070a8创建的一致；DSTORE mode2/open1/state2/header0/GPT0/0/present65017/writes19181/loaded4616/errors0。权限stage4/checked0/total232是保留已有状态，不是重新恢复232项。APFS UUID正确，可用262926336B；RAM1477读/2350写/0错误。首次跨重启文件标志保留获得证据，计划再用原镜像重复一次后结束该阶段。

常规启动同时记录BL mode3/ok1/error0/old307/target64/readback64，单次写、第一个读回样本成功，ACK/TIMEOUT0；与机主锁屏反馈对应。末快照tick15/stage11/225346ms，不推断首次锁屏所用时间。触摸无作用按未适配记录；全核CPU仍未启用。

12:54：不修改内核/ADT/种子，以同一eb55ebe5镜像启动第二次已有Data复测（轮次20261028-125358-eb55ebe5）。再次核对64项输入与准确镜像，日志解析器SHA记入新run.json；900/1200秒及600秒单帧保持，等待有界自动回收。尚未进入多核启动，不把读出的8个ADT节点当作8核在线。


## 21:53 新增第二次独立绑定的 Data 恢复证据

触控短测 `20261028-214203-ece3d0e8` 自动回收，匹配的新4KiB日志再次读取原初始化标志 `DKEEP state=2 error=0 cookie=2c59d71a`；与首次创建和eb55ebe5的cookie一致。overlay loaded4669、errors0；APFS UUID正确，保留模式只验证已有权限标记，不重放模板。结合此前eb55ebe5，这是至少两次独立绑定的跨启动恢复通过；不等于完整文件系统或长期耐久性验证。见[重复恢复证据](evidence/data-retained-repeat-result.json)。


## 22:31 机主要求直接八核目标

手机已自动回recovery；不启动Android。只读采集确认recovery当前0-7在线，CPU0/1 MIDR410fd801，CPU2-6为410fd811，CPU7为410fd821，与实际FDT八个affinity/capacity交叉核对。它证明Linux recovery硬件身份，不等于XNU八核上线。

prepare-zorn-smp.py新增显式--cores8，生成八个不同reg的隔离ADT，保留通用qcom,kryo类型和共用timebase，副核加入实际MIDR/容量元数据；移除新增七个节点与PSCI后逐字节还原原ADT。隔离ArmCpu对象编译通过，实际DSB/SGI/ISB和PSCI SMC存在，旧内核缺SGI负例成立。见[离线候选](evidence/smp-eight-offline-candidate.json)、[实际核型](evidence/smp-eight-midr-recovery.json)。

当前boot.img仍是CPU0触控诊断，未打包/启动八核。直接八核预检前仍须完成跨核TLB、日志原子互斥、旧锁绕过复核及每核实际任务/定时器/IPI证据；通过后再放行用户态。机主明确八核优先、触控候选保留、硬件GPU后置。


## 23:17 八核预检进入实际链接阶段（尚未真机启动）

新增显式 `--smp-preflight 8`，仅适用于 `zorn_defconfig` / watchdog1 / 当前增量源码树，禁止混入 GUI、触控或 Data 保留参数。默认仍 CPU0。板级 ArmCpu 包装层修复 boot CPU 的 IOCPUInterruptController 等待全部 CPU 使能、却尚未调度副核启动的注册顺序问题：boot controller 仅负责本核；副核使用现有本地 interrupt handler，在 UFS 日志和独立 watchdog 就绪后依次注册/CPU_ON。

本配置将 RW 锁实现和 pmap 锁恢复为固定原版，恢复原版 ASID 分配器及 pmap 销毁流程；不再允许 try-lock 失败后继续改 ASID 位图。CPU0 首先在可回收的日志检查点执行全 ASID、inner-shareable VMALLE1IS；只有指令返回后才切换六个全局 TLB 入口，并启动副核。实际链接的 SGI/PSCI/TLBI、processor_start、绑定任务和日志调用已核对；完成预检仍需真机每核 MIDR/MPIDR、timer/IPI、10 次绑定任务和 TLB 返回证据。该探测暂不等于已完成跨核重映射一致性或八核 GUI 验收。

日志块所有权改为原子获取/释放，包含 watchdog 头文件；8 个宿主生产者压力检查、越界和旧源码反例在 ASan/UBSan 下通过。此为宿主检查，不能替代 UFS 真机并发验证。最终复位先验证 BCB，再停止 watchdog；若 PSCI 意外返回则尝试重新开启 watchdog。Data 驱动在预检关闭，标志接口明确返回 ENOTSUP，不使用虚假种子或挂载旧 Data。

首次完整链接因非 Data 配置仍拉入 DataMarker 的 Data/种子符号而失败，已单独提供拒绝访问的非 Data 接口修复。第二次链接成功，审计器对函数与同名数据及内联调用路径的识别被纠正后，正在重新完成整个打包流程；失败日志保留在 ignored out。当前手机已核对 recovery/zorn/_b；尚未启动八核，不宣称八核在线。已有 d2c17be2 CPU0/低亮度/保留 Data 基线和触控候选保持归档。


23:18：`402f7682`（完整 boot SHA `402f76822c3919be1f0bea547cb6664b1d8ddb08d1a1d8a7d0dcb2f98e5ee2d5`，kernel SHA `05a1f62b1abeba93af8208a19a1adb351fe65286bfb5f8a2b8da3bbdfbb38463`）完成37项输入、实际调用/负载审计和独立完整归档核对。只对92988a43/zorn/b临时启动，run `20261028-231842-402f7682`，主机回收上限360秒；独立watchdog和BCB已验证，尚待新的回收结果。此镜像为预根卷硬件测试，不应拿它等系统锁屏。


## 23:19 八核 XNU 预检真机通过

`402f7682` 于23:19:36自动回recovery，run.status=recovered、kernel_log_changed=true，完整boot/kernel/reader及归档SHA匹配。实际 `SMP PASS target=8 phase=80 seen=ff bound=ff failure=0 tlb=1`。CPU0/1为A520、CPU2-6为A720、CPU7为X4；MPIDR实际为81000000至81000700。副核全部step7/PSCI返回0，每核timer>0、IPI>0、10次绑定任务、VMALLE1IS返回，详见[eight-core evidence](evidence/smp-eight-preflight-result.json)。这证明八个实际XNU核心已运行，未挂载Data、未启动八核用户态或验证性能。

下一独立候选增加真实映射可见性测试：CPU0使用标准pmap接口，将保留的同一内核VA在两张自有物理页间切换，八个绑定worker逐次核对9个epoch的标志值并记录错误；停止worker确认后才撤销映射和释放内存。所有操作仅在RAM，仍在根卷发布前自动回收。此候选正在构建，不能将第一轮仅TLBI返回当成映射一致性已通过。


## 23:38 完整八核与映射清理通过，准备八核用户态

`37100a75`（boot `37100a7596d683ce84e3ba8d34537e38cd8e7d8f7c80e8a4f150b6508a36e511`，kernel `13495dbd92cbe2c5e6f003d5c291833c5af8fea60506c94847020952d1edbf21`）已自动回recovery，新日志/完整归档SHA匹配。`SMP PASS phase80 seenff boundff failure0`，每核remap9/error0，原先phase76清理断言消失。旧 `5655bfe2`、`5d8b2662` 的失败证据保留；后者证实9轮读值全部正确、断言仅在kmem_free的VM entry unwire。修正为KMA_VAONLY|KMA_PAGEABLE，独立wired backing保持，未删除断言、未手工改PTE或丢弃错误。详见[完整预检](evidence/smp-eight-remap-result.json)。

接入显式 `--smp-preflight 8 --smp-continue`：每次启动仍先执行同一八核/9轮映射预检，通过后才允许根卷/Data/用户态继续；失败仍自动回收。构建前要求真实recovered proof、原始块/boot/kernel哈希，以及与已通过归档完全相同的worker/映射/协调函数与ArmCpu补丁。八核GUI排除旧CPU0用户/内核栈采样和触控实验；保留Data/低亮度/原服务裁剪。Data标志验证不再依赖LaunchServices采样选项，运行时写入资格守卫仍保留。正在构建，尚未把八核系统界面计为通过。


23:42：`1a62f9de`（boot `1a62f9deafbd6503ec8eb163c9893f6a6b024a9cc5e242b0078020e6ffc71294`，kernel `47a2abb81089b21e454827929c81ff2a832bc8a61b318d2be1b836a251fe1b25`）通过83项输入/归档、真实CPU调用和保留Data负载审计后，固定设备临时启动；run `20261028-234251-1a62f9de`，300秒观察/600秒回收。23:45机主现场回复“系统锁屏”。这是八核候选的实际画面确认，尚待本轮新日志核对SMP8、Data和亮度；触控实验在此轮关闭，不能据此判定八核解决触摸问题。


## 23:49 八核锁屏、保留 Data 和低亮度联合通过

`1a62f9de` 自动回recovery，status/recovered、changed log、精确boot/kernel/reader哈希匹配。机主确认系统锁屏，与末快照tick20/stage12/ms313807及10次CPU传帧一致。原始文本保留 `SMP8 phase80 seenff boundff remapff timersff ipisff failure0 tlb1`；DKEEP state2/error0/cookie2c59d71a，Data模式2/原卷UUID/overlay错误0、权限stage4保留模板，亮度307→64/readback64。见[八核系统证据](evidence/smp-eight-gui-result.json)。八核用户态本轮通过，尚未做长期稳定性/性能测量。

另发现Data可用仅11079680B（512MiB总容量），本轮已有初始化和服务写入显著增多。待测 `2c64d623` 八核+原触控驱动已完整构建并核对104项输入，尚未启动；先调查容量占用。完整Data导出被自动审批因可能包含私人内容、缺少明确导出授权而拒绝，未执行该导出；只读头/位图替代调查和授权确认分开记录。不重置已有Data，不关闭文件系统错误检查，不扩大持久写入窗口，不据单次锁屏声称触摸已修复。


## 2026-10-29 00:05 Data容量复核

用户明确授权完整512MiBData本机诊断。已在recovery仅读取既有窗口，核对SHNGDATA头CRC/种子和二次读回，在本机按126678个已变页重建原APFS；仅只读挂载分析。完整副本留在ignored out、未上传；原卷11MiB可用得到宿主复核。db/uuidtext约157MiB、diagnostics约79MiB、analyticsd约32MiB，三项约268MiB，说明512MiB不宜作为后续系统调试容量。未清理文件或重置Data。

建议迁移到8GiB的UFS持久Data，不需要等量RAM。按上游seed-data-grow.py --gib8仅在本机生成新的最小种子，逻辑8GiB、编码1175696B，原种子哈希不变。初始化后的Data尚未迁入；直接换种子会改变store身份并重置，禁止使用此捷径。提案是在userdata相对20GiB的独立窗口保留8GiB Data，旧10GiB/512MiB窗口保留；只完成静态范围核对，仍需实机GPT/新窗口前像/边界与种子绑定/原标志迁移验证及新增写入范围确认。没有安装新窗口、没有扩分区或flash。见evidence/data-8g-offline-proposal.json。


## 2026-10-29 全新8GiBData，机主取消数据迁移

机主明确无重要Data、要求直接扩大，改为全新8GiB初始化，省去原初始化数据迁移。旧512MiB窗口和本机副本仍保留作独立回退。8GiB种子已核对逻辑容量、原卷UUID和232项模板路径，编码仍约1.12MiB；默认构建保持512m，显式--data-profile8g选择新策略，--fresh-data限定首次mode2初始化。

20GiB候选非空。完整前像导出被自动审批因未知旧Android私人内容而拒绝，未执行；改用允许的手机端空白校验。新的userdata相对192GiB候选完整8590200832B/2097217块哈希与全零一致，未导出其内容；在本机构造对应零前像并完整解压SHA核对，压缩约36MiB。实际新窗口relative50331648、absolute53444352、pages2097152、64块bitmap+1块header；双GPT、manifest、真实容量和边界均核对，避开OS/SystemOS/日志/旧Data。当前installed=false，没有写新窗口或改GPT。

实际8GiB策略/原版provider/overlay的宿主边界、坏GPT/坏seed/越界/只读写拒绝/写失败测试通过；512MiB旧策略回归也通过。1eb799ec仅mode1只读探针已完整50项输入与boot/kernel归档核对，开始定向临时启动；仍需新回收日志及全窗不变证明才初始化65块元数据。下一阶段为八核新Data首次启动，再验证跨重启保留及触控。


00:32：严格匹配新mode1轮次7a57b0cb（recovered、changed log、boot/kernel归档一致）后，全新8GiB窗口初始化完成。实际日志为DSTORE mode1/open0/state4/header9/GPT0/255、present/write/loaded/error全0，保留了只读写探针EBUSY16，不当作可写挂载成功。初始化前整窗仍与零前像SHA相同；仅写65块header/bitmap，之后整窗SHA为ac676e6512e4bad824ec9a2e395133c881e156995c6ac0157f42cfa9c2442975，GPT/manifest/前后边界不变。一次人工轮次路径拼错在任何USB写入前失败，随后按唯一真实目录自动定位；失败日志保留。见evidence/data8-metadata-install.json。

00:35：82e697c5全新8GiBData八核候选完成84项输入/归档/真实调用/种子大小及UUID审计后，仅92988a43/zorn/b临时启动；--fresh-data、不携带retained标志，300秒观察/600秒回收。它会先重跑八核和9轮共享映射检查，再创建全新Data初始化标志。系统初始化/新可用容量仍待回收。后续保留Data触控候选正在本地构建，不并发手机测试；最终日常测试镜像将使用--retained-data，避免再次重放首次权限模板。


00:38：机主确认82e697c5（全新8GiBData/8核）已进入系统锁屏，先保持现场自动回收；尚待真实容量、Data标志和错误计数。后续bb4bd81b已完成109项输入及完整归档/真实调用核对，使用8GiB/retainedData/8核/低亮度/原触控报告格式，未启动，等待首启新日志后才测试。


## 00:43 全新8GiBData首次启动通过

82e697c5已自动回recovery，精确boot/kernel/reader/归档及changed log核对。实际APFS总容量8589934592B、可用8155586560B（约7.60GiB）、UUID仍C7D77FF3-6437-4C4A-8E05-E8E239AC1641。权限stage3/error0/232项全部校验；DKEEP首次创建state1/error0/cookie2dde8229，overlay mode2/open1/state2/header0/GPT0/0/errors0，SMP8全maskff/failure0、11次CPU传帧和亮度读回64。机主确认锁屏。见evidence/data8-firstboot-result.json。此时跨重启保留尚待下一轮，不把首次创建当成恢复证据。

随后bb4bd81b（boot bb4bd81bfae49051e22fffc59017e6bd92639abd7ac8ce12d0813551eee19353，kernel054c37045862a55ff2daaebfc9ee8348f3788452406afaca69f0e9b80e0064c0）重新核对109项输入后定向临时启动，8GiB/retainedData/8核/低亮度/原触控报告格式。它只验证已初始化标志，不重放模板；若标志缺失或新seed不符即拒绝。用于同时验证新Data的跨重启保留与8核下的触摸反应，300/600秒，等待回收。out/zorn/boot.img现为此保留模式候选，首启fresh镜像只保留在归档，避免日后手动测试再次套用首次权限模板。

## 2026-10-29 00:51 8 GiB Data 跨启动保留通过

`bb4bd81b` / `20261029-004452-bb4bd81b` 已自动回 recovery，新增日志、boot/kernel 和完整归档哈希匹配。Data 总量 8589934592 B、可用 7967285248 B（约 7.42 GiB）；DKEEP state2/error0，cookie 与首启相同为 `2dde8229`，权限 stage4，未重放首次 232 项模板。UFS Data 错误为 0，SMP8 各核掩码 ff、failure0，硬件亮度读回 64。机主确认锁屏；见 [本轮证据](evidence/data8-retained-touch-result.json)。这证明一次初始化后的跨启动保留，不代表长期稳定性验收。

本轮触控读取 834 次、解码 833 帧、bad0；HID 提交 187 次，末次返回 0，机主仍无 UI 响应。机主补充早期自由触摸、后期完成 2–3 次中央按住与底部上滑，因此不将本轮当作干净的无触摸基线对照。00:59 已重新只读下载同一日志到本机，按机主要求暂停；随后机主明确恢复触控适配。后续事件派发计数及边缘手势候选详见 [触控事件记录](progress-2026-10-29-touch-events.md)。

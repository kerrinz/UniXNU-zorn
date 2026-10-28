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

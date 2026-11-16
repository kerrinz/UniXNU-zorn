# K80 iOS26 v251：延迟取得真实原生会话

当前实机基线仍是v250：120／120次同表面呈现查询、正确Metal像素、实际退出0和物理4×4棋盘，332.473秒自动回TWRP。v251是后续完整离线候选，未安装、未启动；没有新设备scope／ready／claim，不能转移250硬件资格。

## 根因与实际修复

实际250的ZornGen7AppIoService26::newUserClient在正常准入后立即设置reserved_，而真实authority／OOB／VM直到首个ensureProcess才创建。因此一个仅打开IOKit连接、尚未调用GPU的客户端就阻止所有其他连接。appObservationBind也过早跟随元数据连接，后来的未使用连接会污染会话拒绝计数。

251保留正常task／current_task／openType、服务与客户端MACF／filter准入、真实对象／任务引用及原生会话独占。服务新增非虚私有reserveNativeClient：在实际客户端serial_下，先核对真实provider／owner／task／live／views等，再在服务锁下绑定唯一实际client。ensureProcess仅在取得这个真实slot后设置attempted_／pin并调用原authority／OOB／VM后端；busy拒绝不设置这些状态，也不固化为原生失败。诊断绑定移到真实会话取得前。原returnClientSlot的精确指针比较继续保护：未使用连接的close／free、分配／attach／start／准入失败都不能释放另一个客户端的slot。

原生prepare／OOB／VM／dispatch／fence／close后端与250保持；任何原生失败继续固定实际客户端、slot和资源，不自动回滚／重试。正常完成后的原有释放保持。多个元数据连接不等于多个并发硬件会话；后续仍需实现和验证普通系统客户端的共享后端生命周期。

## 回归与原生构建

可重跑的[实际服务检查](../scripts/check-ios26-lazy-session.py)直接提取当前类声明及8个实际方法，35项ASan／UBSan与TSan控制覆盖12个并发连接只有一个真实会话获胜、未使用连接关闭、分配／attach／start／任务准入失败、foreign释放、native各阶段失败保留及正常关闭后新连接取得。XNU／硬件边界明确为主机替身；失败fixture的清理只属于主机，不能作为设备恢复方案。

新真实探针仍执行原Metal shader／pipeline／像素检查，再用正常IOKit打开两个独立元数据连接，对其中一个发出公开NativeAdrenoMethodQuery，必须得到kIOReturnExclusiveAccess，然后每个实际成功打开的连接只关闭一次。关闭失败、意外GPU方法成功、外来registry身份、缺失连接均使探针失败；没有用户态重试或假成功。随后仍要求原120帧／20秒逐项呈现与正常退出。10项实际helper控制及[typed251接收判定](../scripts/inspect_ios26_gpu_sessions251.py)的synthetic完整日志／程序身份／范围／重复／拒绝控制通过，合成数据不充作实机结果。

用户探针按arm64e-apple-ios26.0原生编译、原entitlement集合签名通过。新增公开NativeAdrenoABI头与内核实际依赖逐字节相同；原生私有头仅增加非虚方法声明，原字段和虚声明不变，两个直接消费者ZornGen7AppIo与HostRing都重编。共1398精确链接输入、30重编对象、0undefined；编译器实际CPU页仍16KiB，GPU／磁盘4KiB分别处理。现有呈现host checker修正了提取函数的结束边界，避免把后加的独立helper包含进去；当前20秒和旧249的8秒函数回归均通过，旧失败记录保留。

## 精确候选与边界

- 程序／boot ID：`f80eb1403d7e4f958b5eddacb49d98d0`。
- kernel：`9f25532a038664dc1e3a897f3477d11d4d9f136f6dbd75d649ca3309e2368003`。
- boot：`eac7550c8a36907968caed9527c46bfe6aae632837a1d8f202831334eb7f23a7`。
- root：`c9382b3183ebf63ac90b41992fb2ed43e2cce45633a512268e6a240fe4fa6842`，32GiB，未安装。最新已确认手机根仍为250的40338c39。

新根只在独立克隆中替换已签名探针，568个监控输入及原job／用户／权限／inode／Metal bundle／Turnip／系统文件属性核验保持，文件系统与签名通过。49个4KiB页、10组的完整本地增量重放等于候选SHA；从受保护Data末端重新按1MiB对齐算放置，Data间隔782336字节，根后保留8588886016字节，无布局变化。初次compose父路径错误在任何镜像创建／挂载前拒绝，失败目录保留；修正为实际250父路径后才生成候选。没有手机访问。

完整启动包保持FD及1023字节原配置，FAT仅替换kernel与root-hash ADT，全部成员读回／payload重组及原loader文件元数据消费检查通过。创建记录显式绑定当前程序身份、独立ABI／source闭包和未安装状态。没有反汇编、符号化或逆向。旧244归档源码保持原样；本次7份最小真实源码改动在[来源与补丁清单](../patches/gpu/ios26-lazy-session251/source-manifest.json)，零fuzz重放等于冻结候选源码。

[完整离线证据](evidence/k80-gpu-v251-lazy-session-offline-2026-11-16.json)。构建目录：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v251-lazy-session-f80eb1403d7e4f958b5eddacb49d98d0。源码目录：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v251-lazy-session-f80eb1403d7e4f958b5eddacb49d98d0。

## 下一步与未验收条件

先为251新根准备独立增量审核，合并250实际保留／写后读回页，核对当前预映像及Android／Recovery／17／Data／日志边界；独立安装成功后，才能准备新boot scope／ready／claim、receiver-first、300秒WDT、600秒自动Recovery及有界摄像头。更新后的服务／观察器、所有受影响source与close测试须绑定当前源，再做当次实机。

只能由251实机确认的是：实际IOKit可打开两个元数据连接、竞争Query明确拒绝、两个close不破坏仍在用的真实Metal会话，随后120帧／像素／关闭／退出及Recovery仍正确。普通系统GPU客户端、原生多会话／namespace切换、全GPU桌面与FT3683完整手势仍未完成。目标保持active，没有新增commit或push。


## 独立根安装与一次实机结果

251根在独立Recovery-only scope中核验7351个历史实际保留页／157组、全部49页新预映像及保护，10组49页写入／读回，聚合SHA7104ed508d8cda443785134a94dbb7f7f53e4548e14aef8b565296de418586b1等于本地重放。安装后仍为已核验TWRP；不是手机全根32GiB读回。77安装器／6准入拒绝控制通过，旧scope／claim与固定传输保持。

187项启动输入拒绝、当前服务／关闭／观察器／发送器／接收器及入口／摄像头检查通过后，仅一次临时启动，332.501407秒自动回TWRP。39帧59591字节、runner／receiver均0，无解析错误或部分终止包。七组启动保护样本逐字节相同；BCB前864字节准备、完整4096字节读回及尾部保持通过。没有重试、bootstrap、刷机恢复或Android／17／Data／GPT／slot写入；当前活动scope已清空，stop_device_operations=false，251claim已消费。

实际ZORN251META记录open0=0、open1=0、busy=e00002c5、close0=0、close1=0、identity=1：两个正常IOKit元数据连接成功，竞争Query被真实独占检查拒绝，两者分别关闭一次。随后原Metal已校验表面的120／120次精确呈现查询完成、displayclose0；完整日志和最终原生关闭也成功。它证实延迟申请／未使用连接关闭的有界路径，不代表已支持两个并发GPU会话。

Metal探针phase11／flags1023／status4／code0，像素CRC718ed2ce、badffffffff；两个原生session关闭均返回0。完整5680字节／56写入记录，unique／PID10、seen／reserved／published／接收长度和CRC一致，gaps／pending0，实际task-detached退出waitstatus0。旧紧凑摘要app.complete仍false、raw_stderr_dropped38保留；独立完整journal、120帧及application251_with_recovery_complete／metadata_session_complete251均true。没有把旧摘要截断清零，也不把exit marker当作完整process reap或任意DMA停止证明。

呈现first548／last1067、SID35、公开时基625／12、ticks290660389，即15.138561927秒；末known记录frame1067／access fence4／lease2，acquire／copy完成，copy1067→1068。循环时间包含调度和呈现查询，不作为GPU帧率。元数据关闭后没有再执行一次新的原生GPU渲染提交，此处只确认后续呈现与最终原生关闭；下一阶段须验证更广提交／资源生命周期。普通系统末SID1的access fence仍0，不能据锁屏推断GPU桌面。

240秒无音频原录像10598455字节，SHAe8289666b4db04fd6ca0a525b826318fb92214f63fe95fcb6be34a4a6f4fd49a。人工检查139.925、130.984、138.424秒帧，确认手机上预期绿／品红4×4棋盘；180／225秒为锁屏。候选排名只挑帧，不自动判定物理输出；原标量parser physical flag保持false。物理图像是本次精确构建的独立视觉证据，不扩大为直接GPU scanout、普通系统GPU客户端、颜色校准或稳定性。

[本次安装、日志、原帧及回收证据](evidence/k80-gpu-v251-lazy-session-observed-2026-11-16.json)。上方“未安装／未上机”是离线创建时序，以本节独立收据为当前事实。完整GPU桌面、原生多客户端／namespace切换和FT3683完整手势仍未验收；目标保持active，没有新增commit或push。

## 同期触控输入核验

通过实际链接清单追溯当前选中的TouchBoard、Ft3683Source-shared、Ft3683Worker、TouchHost对象与原编译配方，独立重编全部逐字节相同。拥有内核资源的单元实际宏为ARM_PGSHIFT14；共享传输／解析单元不据未展开的SDK页宏推断CPU页所有权。源码明确仍调用readMatrixFrame并使用矩阵Detector，不能把它当作已完成的厂商触点帧或完整手势。此次没有执行旧文档中的二进制／私有ABI研究步骤。来源、编译命令、对象哈希及范围见[触控所选输入证据](evidence/k80-ft3683-selected-inputs-2026-11-16.json)。这不是新增触控实机验收，也没有修改当前触控实现。

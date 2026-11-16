# K80 iOS26 v252：普通系统客户端的早期 GPU 发布候选

v252已完成独立16页Recovery安装及一次真实早期系统启动，332.649883秒自动回TWRP。普通backboardd建立两个顺序原生会话：第一个正常关闭0，第二个持续使用；观察到带完成GPU access fence807的正常表面呈现，以及150／225秒物理锁屏。39帧58161字节和9170字节普通进程完整观测前缀、8核真实采样及七组保护样本／完整BCB检查通过。**这不是全GPU桌面、并发多原生会话、完整客户端生命周期或FT3683手势最终验收**。251的正确Metal像素／物理4×4棋盘／退出0基线原样保留，不能自动转移为252普通客户端的已知图像验收。创建时未安装的记录保留原时序，当前事实以下述独立实机收据为准。目标保持active。

## 源码发现与修改范围

实际251编译没有定义ZORN_GEN7_APP_PROBE186，真实ZornGen7AppIoService26已在registerService前设置MetalPluginName／MetalPluginClassName。源码中的历史条件不能当作当前实际编译行为。其真实GPU发布却要等PID1之后原25／45秒采样、检查点落盘和CDC启动；CPU占位IOAcceleratorES先行发布且不带插件属性。**这说明当前输入的时序，不证明它已经是普通系统回退的唯一根因**。正常框架何时发现GPU、是否缓存无设备结果，仍须本候选实机确认；未检查或修改专有框架实现。

252从现有根设备EL0入口、实际RootRegistered／device身份和原有单次调度门之后，调度独立早期worker。新增ZornGpuEarly252.h集中处理候选选择：显式-g0且原CDC、300秒WDT、预置Recovery、独立根、连续触控和CPU显示配置均匹配；与-g45冲突或值错误直接拒绝，不回退到旧GPU尝试。无-g0时沿用原排程。

worker无启动锁地最多等待30秒，只观察实际SMMU deferred-owner的CPU release／acquire发布，既不消费它，也不读取MMIO或宣称GMU就绪。取得后再次核对真实根注册，按原单页日志路径写入“cpu_samples=pending”检查点，必须真实write／readback返回且匹配，才进入原CDC身份／路由检查。三个实际完成的CDC帧、诊断握手、原单次deferred调用、固件／GMU／HFI／ring／已知任务及服务创建调用链均保留。没有恒定成功authority、跳过认证、取消独占或自动重试。

25／45秒CPU采样仍由独立原worker实际执行。完成前ep字段明确pending，完成后发布实际mask／online和USER／SYSTEM增量非零掩码；原始8核增量也写入IOLog。它不会再次占用早期worker拥有的单次日志／CDC。早期路径抑制竞争占位accelerator；真实CPU framebuffer仍注册，真实GPU服务继续按原方式设置插件属性，正常task／MACF／filter准入不变。

新根只改两个已有文件：NativeAdrenoMetal.clients选择backboardd；原探针job的RunAtLoad改false并设Disabled=true，防止探针争用仍独占的后端。不bootstrap／respring，不改系统守护程序、签名、插件、Turnip、Rust、转换器、Data或其他输入。此单一普通合成器阶段是后续完整系统接入的一步，不是把最终目标缩小成单客户端。真实多客户端生命周期仍需继续实现。

## 回归、精确构建与存储

- [实际早期源码检查](../scripts/check-ios26-early-system.py)提取真实mode／worker／调度／CPU发布／ep格式化／日志进程选择，38项控制、100轮原子发布竞争及容量边界在ASan／UBSan与TSan下通过。线程、持久化和CDC边界是明确主机fixture，不充作设备成功或恢复证据。
- 原完整journal store／capture／CRC／并发测试用当前源码通过两种sanitizer，只有fixture进程名改为backboardd。当前[ep解码器](../scripts/inspect_ios26_gpu_early252.py)16项拒绝／不冒充验收控制及[单页解码器](../scripts/inspect_ios26_gpu_early252_record.py)9项身份／新鲜度／CRC控制通过。合成ep加旧251输运仅做回归，绝不是252或backboardd实机日志。
- 既有实际capture函数以本轮合成ep帧及旧原始终止包作不解释的输运fixture，主机PTY以509字节分片读回457853字节逐字节相同；仅模拟PTY没有DTR针脚，不访问USB，不把旧包归为252硬件证据。
- 完整1398项输入全部核哈希，30个受影响／身份消费者重编，0undefined；79项有效头依赖核对，新共享头的UFS／framebuffer两个实际消费者均重编。CPU实际宏ARM_PGSHIFT14／16KiB，GPU4KiB和磁盘4KiB分开。原AppIo、HostRing、Board、authority／OOB／VM／submit等实际后端逐字节保持；SMMU文件仅增加非消费观察函数，原主体相同。
- 568个根输入监控；两个政策文件原inode／UID／GID／mode保持，其他监控字节相同；原可执行及bundle／Turnip签名、文件系统核验通过。16个4KiB页／11组完整本地重放等于候选整32GiB哈希。放置重新从受保护Data末端按1MiB计算，Data间隔782336字节、根后保留8588886016字节，没有套用新窗口或改变布局。
- FAT只改kernel／ADT根哈希／menu的-g45→-g0；完整成员读回、payload重组、原源码构建的元数据consumer通过。FD、manager、loader与板级常量保持。不是实际loader执行／PAC或硬件资格。

- kernel：`8a3e8c257321a3cf7f44290fd1711cd030c0c436ad5bce7ec8d21c6e90b996b4`
- boot：`8c01452c95af163202028d1cea086aa9a5b306f0c5490f49efca90308218fc12`
- root：`859c7ebae6355ef7e089896680b0b8ffd9a03af8a1f078918feec740b7a06b02`
- ADT：`98f04ff54b9573ddaa2c4716da0e954fae8192d15b1f105426eba7f216805936`
- FD：`1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab`

boot ID：`f5bb017ece0045d3a06ec1711a1c8b88`。禁用探针原二进制／文本观察前缀仍保留其251身份`f80eb1403d7e4f958b5eddacb49d98d0`，不把旧二进制冒充新程序。普通合成器日志通过严格backboardd成功write的真实unique／PID与原生会话关联，缺日志不能冒充无错误。

构建：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v252-early-system-f5bb017ece0045d3a06ec1711a1c8b88。
源码：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v252-early-system-f5bb017ece0045d3a06ec1711a1c8b88。
[八份精确补丁与来源](../patches/gpu/ios26-early-system252/source-manifest.json)可对251冻结源码零fuzz重放到当前候选；[完整离线证据](evidence/k80-gpu-v252-early-system-offline-2026-11-16.json)包含各命令、输入、检查和布局引用。没有新增上游代码；本地houji参考提交98bc0960f96076de8e8d16efcfb0c0603b166b85保持，参考[官方GPU教程](https://unixnu.com/zh/porting/gpu)的设备／客户端／渲染／呈现分层验证要求，不把官网现有27配方或其他机型参数用作K80板级输入。

## 当前限制和下一步

固定设备入口已接通252：新Recovery-only安装scope检查7386个实际历史读回页／158组及全部16页预映像，11组写入读回聚合等于本地重放d429efd1；73安装器、6安装准入、77包／源码、35真实安装bundle及入口／摄像头／接收器拒绝控制通过。随后独立owner／ready／admission、完整归档和新claim仅启动一次；旧251claim没有复用。252的新记录解码不套用旧45秒触控判定。安装及启动claim均已消费，当前无活动设备操作，stop_device_operations=false。

本次实际支持的范围见下一节；普通渲染附件写入／提交／完成／呈现的逐帧归属、更广Metal接口、并发多任务原生会话与第二个持续客户端的正常结束仍待实现和验收。仍保留一个原生硬件会话；任意结果不明的DMA／原生失败继续保留资源，正常成功生命周期按原实现释放。不得把锁屏、单个access fence或“没有采到panic”升格为完整GPU桌面／生命周期／稳定性。

首轮macOS镜像服务attach在修改前失败，确认无活动挂载后保存失败目录，使用已授权镜像服务在新独立目录完成；没有手机访问。一个部分panic合成fixture最初错误要求必须返回，修正为允许原严格解码器拒绝，拒绝逻辑未放宽，失败资料保留。全部镜像已卸载，独立安装／启动后已再次核验TWRP；当前状态文件无活动设备scope，预期根为252的859c7eba，来源是本次16页实际写后读回及保护链路，非手机整32GiB根哈希。Android／Recovery／17／Data保护范围保持。无反汇编、符号化或逆向，无新增commit／push。


## 一次普通系统实机观察

精确kernel8a3e8c25／boot8c01452c／root859c7eba／ADT98f04ff5／原FD1bf94507，新的300秒看门狗／600秒Recovery范围，一次尝试无重试。安装始终留在TWRP；后续启动前完整BCB读回及尾部保持，332.649882541秒自动回已识别TWRP，七组启动前后保护样本逐字节相同。没有bootstrap、respring、刷机恢复或Android／Data／17／GPT／slot／boot分区写入。七组保护样本不是整Android／Data／32GiB手机根读回。

实际检查点明确写cpu_samples=pending；后续真实ep最终flags63，cpu_done1、maskff、online8、USER／SYSTEM增量非零掩码均ff。三个pre-GPU帧、六次实际投递ack均保留，最终worker state3／源定义返回88、point6／ack6／failed0、真实应用服务publication=0x100000000。它把当前真实源调用链的结果绑定到252，不代替所有硬件／长期条件。

严格backboardd日志进程与原生会话unique／PID均10。第一个原生会话flags255、9次调用、closeReturned1／closeRaw0；第二个准备阶段成功后持续使用，最后flags15、8641次调用，尚未正常关闭。最后快照method6／raw0xe00002d6原样保留。公开IOReturn.h中它是kIOReturnTimeout；当前HostRing只在有界waitExpired且guard保持健康时保留该值，否则转NotReady并停止相关路径。这是源码对末返回的约束，不能据单次快照认定GPU永久挂死，也不能把它清零当成功。

最后正常显示记录frame804／SID836，client表面1125×2436，GPU access fence807与producer／tail／completed匹配，lease2、所有acquire成功、像素copy返回、完成账本匹配，copy803→804。1125×2436是本次客户端表面请求，不是移植进来的K80物理面板参数。标量GPU_surface_write_proven／physical_scanout_proven仍false；这里只确认带已完成GPU访问的真实表面链路，没有用access fence代替“附件确由该GPU渲染写入”的逐帧证据。已知图像探针在252根中禁用，不能要求／伪造251终态报文。

39帧58161字节、runner／receiver均0，无解析错误和部分终止包。普通进程journal 9170字节／60写入记录，seen／reserved／published／接收长度和CRC一致，gaps／pending0，SHA54d60f42c17b8b86870cb293e920764baa3aa2412619a463d2e1bf21efcc8bb4。daemon未退出，journal.complete=false；这里只是完整有界观测前缀，非完整进程结束日志。旧紧凑摘要drop57、app.complete=false及原生末调用状态全部保留。未采到终止包不证明任何时段都无故障。

240秒无音频原录像12128271字节，SHA938b6d586bc68f8a5c086e143677e19503a0665fa9c1d8e7512dfc86ca09b647。实际人工查看60秒原帧为启动控制台、90秒苹果标志、150秒锁屏4:02、225秒锁屏4:03；没有解释机器地址／指令。后两帧证明物理锁屏和时钟推进，不作为已知像素oracle、解锁后桌面／应用、颜色校准、GPU每帧写归属或性能结果。

[安装、原始串口／进程日志、帧、scope与回收证据](evidence/k80-gpu-v252-early-system-observed-2026-11-16.json)。独立原始run的GPU_started=false和typed ordinary_GPU_desktop_qualified252=false保持；本记录补充实际原生客户端／表面／摄像头观察，不改写旧平台摘要成全GPU成功。下一步继续真正的多客户端上下文与资源生命周期，并把普通渲染附件写入／提交／fence／呈现身份接通；FT3683仍需真实完整触点与手势工程及对应验收。无新增commit／push。

# K80 iOS26 v249：有界重复呈现与物理图像验证准备

248已补齐实际stderr完整日志和真实退出/Recovery证据；其首120秒录像没有确认棋盘。249接着验证正常显示队列的重复使用与同一已校验Metal IOSurface的可观察输出，仍不声称完整GPU桌面或触控手势验收。

## 实际实现与边界

复用原ZornKnownPresentSubmit247/Query247公开板级API、原present FIFO、surface独立hold、真实GPU completion lease、cache acquire、drawLayer/show和退休处理；MiniIOMobileFramebuffer.cpp、MiniIOSurface.cpp、公共known-ticket及DirectClient/VM/Submit源码与248逐字节一致，没有新增硬件寄存器、复位或HWSCHED路径。查询不使用SwapWait。

探针继续原真实Metal shader/pipeline、32×32 RGBA IOSurface预填充及逐像素/CRC比较；保留texture/surface直到重复呈现结束。一个正常IOMobileFramebuffer客户端最多提交120次，每次只在精确frame/SID/schema2、非零已完成access fence、实际acquire和copy增量1均匹配后才继续；帧号须递增，失败停止，不重试原生错误。调用之间按公开mach_timebase_info/mach_absolute_time设置8秒截止，成功帧之间按正常节奏等待16667微秒，不阻断其它UI、不宣称图像持续占屏。这个截止不能中断被阻塞的原生调用，原队列超时及未来独立300秒硬件WDT仍必需。

最后只有120次提交/查询均完成且IOServiceClose成功才允许原phase11及资源清理。新ZORN249PRESENT行记录实际次数、首末帧/SID、关闭结果及公开时基；typed249接收端还要求完整248日志/退出、原Metal/native-close和最后known记录对应，不从标量自动推断物理scanout。

实际函数提取后36项ASan/UBSan控制覆盖完整循环、首/中途错误、ID/记录/fence/copy拒绝、200次轮询界限、全局截止、时基错误与溢出、关闭和不打开/不关闭错误句柄。新typed249正例明确为synthetic fixture，旧248捕获仅提供旧格式回归输入；缺失/重复/错误次数、ID、关闭、时基或程序身份不冒充新实测。实际iOS26探针编译链接及原entitlement集合签名通过，无新授权绕过。

## 当前离线候选

kernel：`becc15016c59e6642fce1661347edd030a470508cffd3535189e765c529c18e1`。

boot：`3e20e0f8ad2fb27a31708a95df8e3477f95f97a2dd43d11cf07a903b5db8d2be`。

root：`1a8ea4a1f7f6a91a40e5865af837c109dcb19b62f4f3dd42123bab2c837d3e93`，32GiB；程序/boot tag为fe1bff87a3d943c1aa877cac8e5ddadb。新root只在独立克隆中替换签名探针，启动job/UID/GID/mode/inode、Metal bundle、转换器/Rust/Turnip及其余受监控文件保持。文件系统和签名检查通过；原已安装247/248 rootdde仍只读保留，不把旧收据当作新root安装证明。

1398输入、30个相对248重编对象、0undefined；当前头/所有输入及native宏检查通过，CPU页仍16KiB，磁盘delta4KiB另行处理。新完整启动包的FD不变、启动参数仍1023字节/mode2，FAT只改变kernel和root-hash ADT。全部成员读回、重组、原loader文件元数据消费检查通过；没有反汇编、符号化或解释panic地址/寄存器。

新root相对dde变化63个4KiB页、10组；本地完整重放后全镜像SHA一致。放置从受保护Data末端重新按1MiB对齐计算，再校验现有窗口兼容性：Data间隔782336字节、root后保留8588886016字节，未新增布局或覆盖Android/17/Data/单日志块。末组预映像拒绝与首组读回失败停止控制通过。它没有写入手机；新根仍需独立固定installer、全部当前retained页/预映像/保护检查和读回收据。

构建目录：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v249-present-burst-fe1bff87a3d943c1aa877cac8e5ddadb

源码目录：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v249-present-burst-fe1bff87a3d943c1aa877cac8e5ddadb

[精确离线证据](evidence/k80-gpu-v249-present-burst-offline-2026-11-16.json)、[五份最小补丁及来源](../patches/diagnostics/ios26-present-burst249/source-manifest.json)、[可重跑函数控制](../scripts/check-ios26-present-burst.py)、[typed249接收判定](../scripts/inspect_ios26_gpu_burst249.py)。补丁零fuzz重放与实际五个源文件逐字节一致。旧248源码/全部产物、实际日志和已消费claim保留；没有新增commit。

## 继续工作

下一步准备新根的独立增量审核/安装scope及拒绝控制；完成后再准备精确249 boot scope、receiver-first和更长的有界摄像头窗口，确认真实棋盘图像并核对重复呈现/引用退休/退出。当前未创建249设备ready/claim、未安装或启动249，手机保持248试验自动返回的TWRP。新的无错误日志判定不等于GPU桌面或FT3683完整验收，目标保持active。


## 独立根安装与一次实机更新

新249root已通过独立Recovery-only scope安装：从实际247保留覆盖和实际247写后读回合并7250页、155组，重叠页采用最后实际值；与父镜像匹配。核验全部7250页、63页新预映像及保护后，10组63页写入/读回，聚合SHA88ca515a…与本地重放一致。保护样本及完整BCB不变，停留TWRP，没有自动启动。47安装器/6准入拒绝控制通过；不是全手机32GiB根读回。旧scope/claim保持，固定传输和all-preimages-first引擎未改。

启动准入首次发现离线包创建时继承了旧application_probe_run_id=c0；实际签名探针、root、kernel、ADT和artifact identity均是fe1。旧创建文件及错误准入描述保留，独立admission-proof修正该元数据并绑定真实签名源/根安装收据；没有修改任何载荷字节或绕过拒绝检查。随后152项启动输入控制、入口和240秒摄像头检查通过。

仅一次临时启动，334.595秒自动回TWRP；runner/receiver均0、39帧59453字节，无解析错误或部分terminal包。5570字节/55个写入记录均送达，unique/PID10、前缀CRC/最终SHA及seen/reserved/published/接收长度一致，pending/gaps0。实际退出waitstatus2560，即code10；严格application249_with_recovery_complete、known_burst_complete249及原application.complete均false，未把传输成功当作应用通过。

Metal探针达到phase10/flags511/status4，像素CRC718ed2ce、badffffffff；之后重复呈现报告submitted72/completed71、first807/last1043、SID35、close0。公开时基numer625/denom12、ticks154110262，对应8.026576145秒；在8秒截止条件下有一项查询未确认，原120帧目标未完成。最后known记录仍为frame1043/SID35/access fence4，真实acquire/copy完成；两个native session关闭记录均0。它符合截止先到的源码路径，没有以此判为GPU性能、驱动崩溃或完整生命周期通过。

240秒固定USB摄像头无音频录像8513730字节，SHA4c8b1af1…。人工检查135.887867、130.349867和132.117867秒候选帧，手机上实际可见与探针对应的绿色/品红4×4交替棋盘；180/225秒为锁屏。这补齐精确构建的有界已知图像物理输出证据，源像素oracle和同SID/fence/队列记录分别保留。颜色候选算法只用于挑帧，没有自动把计数或饱和度认定为scanout；不声称颜色校准、完整GPU桌面或所有Metal特性。原parser的scalar physical flag仍false，独立视觉证据不篡改它。

七组boot保护样本逐字节相同，BCB前864字节准备、4096字节读回和尾部保持通过；无Android/17/Data/GPT/slot写入或重试。没有导出terminal包，不据缺包推断从未故障。手机已回TWRP，249claim消费。下一候选将据本次真实时基和循环进展调整有界观察预算，继续验证120帧、正常退出及资源生命周期；完整GPU桌面和FT3683手势仍未验收。

[本次原始录像/帧、日志、安装及回收证据](evidence/k80-gpu-v249-present-burst-observed-2026-11-16.json)。上方“未安装/未上机”保留离线创建时序，以本节独立收据为当前事实。目标保持active。

# K80 iOS26 v248：分段 stderr 日志与真实退出记录

248已形成独立完整内核和启动包，未部署或启动手机，尚未创建248设备scope/ready/claim。最新实机证据仍是247：Metal像素、同一IOSurface显示队列/acquire/copy和两次native close已有有界对应，但raw诊断丢弃36使旧application.complete=false；物理棋盘、完整GPU桌面、FT3683完整手势和稳定性尚未验收。目标保持active。

## 根因与最小修改

旧观察器只保留383字节首尾摘要，超出时丢弃中段；单次较长write也只复制前383字节。它不是完整stderr存储，不能据摘要和成功phase提前抹去丢失。248保留旧观察器全部字节和原丢失计数，另接一份有界CPU日志；严格旧判定没有改变。

实际sys_generic的write_internal在原writev_internal返回后采集真正返回的字节前缀。writev_uio在原调用前保存至多8个内核已规范化iovec描述符，原调用后只复制实际返回前缀，避免使用被uio推进的描述符。没有改变原syscall结果、fd、权限或错误。只观察既有zorn-metal-probe193的真实uniqueid/PID；它不授予GPU访问权。用户内存在write后采样，有并发用户修改时不能把本日志称为fd接收端逐字节读回。

公共store提供64KiB静态数据、256个记录、单次至多16KiB。每个写者独占不重叠的已预留范围，不在copyin期间持有元数据门；完成后才发布连续前缀并增量计算CRC32。忙、容量不足、复制失败、不支持的向量/flags/错误、非法票据和退出后写入均产生单调丢失位，不能伪造完整。失败不重试、不覆盖旧数据，无DMA或分配/释放。静态对象为零初始化POD。

退出钩子来自真正选中的kern_exit.o配方，原配方独立重编与原0704对象整文件SHA一致。新增回调位于proc_exit中file/AIO清理后的task detach点；只记录实际unique/PID及p_xstat，不等待、不改资源所有权。它不是proc_prepareexit意向记录，也不是进程完全reap、GPU停止或DMA静止证明。

UFS原progress producer追加jl元数据和jb的base64片段，依据实际剩余空间决定片段长度，至多768原始字节；完整格式能放入原3072字节帧后才推进cursor。39帧、529408总字节、panic容量、原门控及看门狗保持。紧容量回归发现“刚好放入无日志帧时拒绝”的错误，已修正；初版1213482f内核及原对象保存在revision-before-tight-capacity，未上机。最终内核以本页下方e03f1e57为准。

新typed parser校验进程绑定、偏移连续、长度、规范base64、单调状态及前缀CRC；只有真实退出状态0、pending/gaps均0、seen/reserved/published/实际接收长度相等并包含同一个终末报告，才可能给出独立lossless_application_complete248。它还要求原render/native teardown、其余native观察无错误及完整传输；接收器另以application248_with_recovery_complete同时要求真实Recovery包络和runner成功。原application.complete及raw_stderr_dropped原样保留。原panic文本始终作为不透明字节保存，没有地址/寄存器/回溯解释、符号化、反汇编或逆向。

## 离线验证与精确输入

ASan/UBSan覆盖乱序完成、真实返回前缀、部分写入、向量、溢出/复制失败、容量/槽位、错误/重复票据、退出及并发；ThreadSanitizer通过实际store并发测试。真实UFS producer/worker、六阶段门控、服务发布和容量回归通过；真实base64及动态片段边界通过。新接收器准备源码经本机PTY传输449746字节逐字节一致；DTR仅在PTY边界模拟，不连接USB或手机。旧247原始捕获作为旧判定回归；新增完整日志正例明确为人工fixture，不是补造丢失的实机内容。完整/部分原始panic、错误启动身份、runner失败和sticky loss等接收控制通过。

原生链接1398输入、30个与247相比重编对象、0undefined；实际选中头文件的77条依赖边、所有输入SHA及MachO文件/段元数据通过。实际选中配方预处理为ARM_PGSHIFT=14，CPU16KiB；GPU页和磁盘4KiB块另行处理。没有混入17对象或套用通用arch profile的4KiB CPU假设。

kernel：`e03f1e57fe4b8b9a82bbfdc34aa8db49ac031eb87e53eb5fd9f567f33b10948d`。

boot：`28b3c66e63c5cccacf11acf6b3d68cbb48af8d76895b398b022beb350de9ea8c`。

复用已安装247 root：`dde0082d112afdaa07d46ef15e1b38ca9d6072ed4c0b1d71a578c8b6e3ce6f9e`；程序tag保持c0bed9d9c79d4aeca33d0ad509f2984d，新boot tag为0b6e1744c27f410a9a7fc1030cf45206。FD仍1bf94507…、ADT仍dd49b399…、启动参数及1023字节长度保持。FAT仅kernel.macho改变；全部成员、解压重组及实际源码loader文件解析检查通过。没有新根、布局或手机写入；旧17/Data/Android及247产物保留。package中的“已安装”仅由先前247独立收据证明原root，不是248实测。

构建目录：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v248-log-journal-0b6e1744c27f410a9a7fc1030cf45206

源码目录：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v248-log-journal-0b6e1744c27f410a9a7fc1030cf45206

[精确离线证据](evidence/k80-gpu-v248-journal-offline-2026-11-16.json)、[最小六份补丁与来源](../patches/diagnostics/ios26-journal248/source-manifest.json)、[公共日志实现](../native/ios26-journal248/ZornJournalStore248.h)、[可重跑主机检查](../scripts/check-ios26-journal.py)、[typed接收判定](../scripts/inspect_ios26_gpu_journal248.py)。补丁按原上下文零fuzz应用后与实际候选六个源文件逐字节相等；退出基线独立固定。新源码暂存，不生成额外commit。

## 下一步与验收边界

准备好的接收器尚未连接固定248设备runner。下一步绑定当前kernel/FD/启动器/ADT/固件/root/配置和全部源码测试，完成新的负向准入检查及独立scope/ready/claim；receiver-first、300秒独立WDT和600秒Recovery返回保持。只有从核验过的TWRP/OrangeFox开始才可执行，旧247 claim不可重用，未创建“ready”不等于外部阻塞。物理已知图像需更早开始的有界摄像头观察；同帧计数不替代scanout。无法回Recovery则立即停止设备操作。当前没有248硬件日志完整、退出成功或GPU新功能验收结论。


## 单次实机更新

248随后完成一次独立有界临时启动，332.214秒自动回TWRP，runner/receiver均0。39帧58889字节，传输与Recovery包络通过，无解析错误或部分terminal包。5422字节stderr日志、54个真实写入记录、50行，unique/PID均10；seen/reserved/published/接收长度一致，前缀CRC及最终SHA508a86c0…一致，pending/gaps均0，实际task-detached退出状态0。journal_terminal_report_matches、lossless_application_complete248及含Recovery条件的application248_with_recovery_complete均true。原application.complete=false/raw_dropped36保持，未修改旧判定或补造中段。

固定Metal探针phase11/flags1023/status4/code0、CRC718ed2ce、badffffffff；两个native session的flags255及close返回0。已知frame341/SID35/access fence4、producer/tail/completed均4、GPU lease2、实际acquire和copy340→341，目标1125×2436。按固定源码对应到同一已校验IOSurface的Submit/Query/Close、原清理及实际退出；access fence标量自身仍不作为GPU像素写入或物理scanout证明。最后普通frame2492/SID1/access fence0，不据此认定完整GPU桌面。

七组定义的保护样本逐字节一致；BCB仅准备前864字节，4096字节整页读回等于准备页、尾部保持。没有root/Android/17/Data/GPT/slot写入或启动重试；不是全手机root或Android读回。没有导出terminal panic包，不能由缺包推断从未有内核故障。claim已消费，不能重用；固定流程已清空active_run，手机在TWRP。

固定USB摄像头120秒无音频录像6089760字节，覆盖启动早段；20/60秒样本为启动文字、100秒为Apple logo，颜色候选未确认棋盘。没有本次物理已知图像或GPU桌面视觉验收结论。新日志保留的metal2vulkan能力降级/未知属性提示不是地址解释，也没有拿Apple测量值伪装为Adreno能力。

[本次精确构建、完整日志与保护证据](evidence/k80-gpu-v248-journal-observed-2026-11-16.json)。上方离线创建时“未上机/未准入”保留其时序；当前事实以本节和独立收据为准。下一步解决已知图像的可观察呈现和真实系统GPU客户端/显示连接，并继续FT3683完整验收；目标仍active。

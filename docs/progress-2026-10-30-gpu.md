# K80 GPU发现与适配（2026-10-30）

> 最新：已恢复无人值守GPU适配；显式Gen7收发通过隔离软件peer及ARM64接口链接。Gen7静态内存provider已实现，下一进入规范原生集成/完整链接，见文末最新阶段。旧“下一步”均为历史。


CPU1窄发布证据及默认42 / 桌面3a保留。c50唯一CPU/GUI观察已完成、历史苹果标志未复现且未缩小根因，按机主方向转GPU。当前仅主机只读材料分析，没有新手机操作或GPU代码接入。

## 本机身份与资源来源

旧K80 live FDT本身包含gpu-model=Adreno750v2、chipid=0x43051401、compatible=qcom,adreno-gpu-gen7-9-1。本地pineapple-v2-gpu.dtsi及绑定文档声明相同三项 / Pineapple V2，已绑定源SHA与仓库提交。这是缓存描述与源码对应，不是重新读硬件ID或证明现有Adreno740寄存器兼容。

先前库存把clocks尾部0当作未知phandle而整体拒绝，错误原样保留。精确本版Linux of迭代器把0当无参数空项，按名称/索引找到请求项即返回；前四个clock-names均可解析，第四项apb_pclk对应aoss_qmp的零cell QDSS provider，末尾0成为第五个空项。qcom_aoss.c使用of_clk_hw_simple_get，GPIO/DT均无需改写。10项隔离索引控制覆盖截断、前后未知provider、空项及负索引；不是运行Linux或实际启用时钟的证据。

## 固定OEM参考及明确差异

下载固定OnePlusOSS SM8650模块提交453d8875f815bf9dfad9035982861226a4823a6c的相关源，只存隔离out。该参考gen7_9_1按compatible优先匹配，使用gen7_9_0_hwsched，声明AQE、SQE、GMU和ZAP文件分别为gen70900_aqe.fw、gen70900_sqe.fw、gmu_gen70900.bin、gen70900_zap.mbn；这些是待核对的候选名称，尚未取得/验证K80固件字节，更不能以文件名认证版本。OnePlus源不是Xiaomi当前stock内核的来源证明。

现有主Adreno740 service导入ShengGmu启动/投票及两个firmware image默认符号；所查service、firmware及CpInit中未找到AQE绑定，不能仅改型号/文件名就运行K80。GMU/硬件调度队列、电源/时钟、安全初始化、SMMU所有权和Darwin IOGPU ABI须按本机重新接合。DT GPU stream0/1/2及GMU5不是context bank / slot / ASID分配证明，不套用sheng或houji的硬件状态。

另外，固定提交原始gen7_reg.h为SHA2e564d7eaeec26bc30e79b1d117b86efa79603345769626157c83610fc4c051c，与旧houji生成器宣称的5da9d8b1不同；原始URL与GitHub contents端点字节相同，Git blob对象校验通过，换行归一化不能消除差异。保留旧报告、不借用其寄存器表为K80证明。初次沙箱DNS失败、错误GMU源文件名404与旧SHA拒绝也全部保留；实际源为adreno_gen7_gmu.c/h。

## 下一项可执行工作

从已有OS3.0.308原始super.img进行有界只读元数据/文件定位，优先仅取得vendor / vendor_dlkm中的GPU固件和KGSL模块及版本/哈希，避免解出完整9GB镜像或删除原备份。先核对AOSP sparse/LP及实际文件系统工具来源和输出边界，再做选定文件提取；不读写手机分区、不启动Android。取得实际固件/模块后比较固定参考的格式/版本/队列依赖，形成最小初始化设计并审计，当前不启动GPU探针。

255项c50当前输入、77完整归档、raw231旧证明工作区及默认42在记录后仍匹配。触控、CPU显示、FD、Data窗口和八核门槛未改。[来源、解析结果及边界](evidence/gpu-source-resolution-2026-10-30.json)。


## 原厂四份固件和KGSL已取得

从已有OS3.0.308.0.WOKCNXM_16.0 super.img只读解析Android sparse及LP，整源SHA3bf4e842a65b3046522d35cd574cc2e3267cbf9b3c55a28055cf5451bad230ae。两份geometry和六份LP头/表checksum均通过且六副本一致；未展开完整super。只还原工具所需vendor约479MB、vendor_dlkm约31MB及后续查找ZAP所需ODM约2034MB的EROFS分区镜像，不解出全部文件系统。包中_a/_b是原包逻辑名称，_b为空；没有操作或改变手机slot b。

取得vendor/firmware的gen70900_aqe.fw（33176B，SHA25237c16）、gen70900_sqe.fw（85300B，SHA8e2c5ce7）、gmu_gen70900.bin（78588B，SHA9685f62c）；vendor_dlkm/lib/modules/msm_kgsl.ko为3538096B、SHAcd3b4985。ZAP不在先查的vendor/firmware和NON-HLOS image目录，随后在ODM/firmware找到gen70900_zap.mbn（12088B，SHA890f7e9d），已保留查找顺序和原始错误，未绕过或调用认证。完整SHA及路径见证据。

工具来自官方Homebrew瓶包，下载SHA校验后仅在out解出dump/fsck.erofs和mtools读取别名，没有全局安装。初次EROFS依赖解析失败保留；仅对子进程设置既有lz4/xz库路径后通过，二进制和系统库未修改。四份主要文件的EROFS选定文件检查与ZAP检查通过。小读者231个精确子区间、7项稀疏损坏及7项LP损坏拒绝；它不是AOSP全面等价证明，也不是原厂签名认证。

实际模块为AArch64 ELF64 REL，build-id0240c57ab32f9f5643e2bcc58c6cd92edec0c86e，vermagic6.1.68-android14-11-gef5271fe2aef-dirty。vendor build.prop表明组件仍为Android14 / SDK34、2026-09-01安全级别，不能仅按外层包名的16.0假定vendor组件版本。gen7_9_1实际264B对象的ABS64重定位指向上述四个文件名、同compatible及gen7_9_0_hwsched_gpudev；没有猜C结构偏移或执行模块。这确认包内引用，不代表手机正加载该模块、运行时选中该profile，或与OnePlus参考源码完全相同。

共用AdrenoFirmware实际C解码器在ASan/UBSan下与独立Python逐项对应GMU15块：11条零size元数据/预分配请求、4个payload；4项截断/超长/容量/未映射控制失败不改输出。payload type实际为0xefbebade，不能强行要求0或丢掉type7持久请求。此检查不证明预分配所有权、安全认证或运行兼容。

按固定参考DTCM位置从文件payload取得原始core0x40020014、power0x40020010、hfi0x20060001；core_dev0xffffffff与power_dev0保持原值不解释。它们是待加载文件中的字，不是真机GMU/HFI版本或已经协商的队列协议。未写寄存器、供电、SMMU、SCM/PAS，未生成GPU内核或启动手机。

下一项在隔离out实现固定SHA的最小firmware布局适配，复用共用解码器，按实际gen7预分配和队列定义检查持久元数据、TCM/IOVA、AQE/SQE payload和容量。现有ShengGmu五缓冲及0x4000 log/HFI不能直接当gen7契约；参考GMU_LOG_SIZE为64KiB，仍需核对真实HFI/hwsched队列。先完成有界主机适配及目标接口设计，再决定最小运行时接入，不依据文件名选择SMMU bank/ASID或直接boot。[原厂材料、工具来源及检查](evidence/gpu-stock-provenance-2026-10-30.json)。


## 固定SHA固件布局原型与17队列契约通过隔离检查

勘误：前阶段文字及旧计划把payload type写为0xefbebade。实际文件与旧原始JSON的数值一直为4022250974，即0xefbeadde；本轮host断言发现了文字/测试常量转写错误，已保留首次拒绝。旧固件、原始记录、SHA与既有报告未改；新适配器保留原始type，既不硬编码该标记，也不强制payload type0。

隔离ZornGpuFirmwarePlan.cpp/h已实现：四文件长度及固定SHA全部匹配后，调用现有AdrenoFirmware解码器，保留15块原字段和11条预分配（含2条type7）；TCM与需要自有IOVA后备的范围分开，拒绝未知元数据、迟到元数据、范围/对齐/覆盖错误、容量不足及别名。错误不改最终输出，scratch归独占调用者。没有分配物理内存、修改映射或把GMU虚址当物理地址。

实际原厂需求形成6项固定虚址后备，加无固定地址的LOG/HFI共8项、565248B。此预算仅覆盖固件预分配和LOG/HFI，未包括bigIB、硬件fence、运行时分配与平台依赖；runtime_complete恒0、ZAP仍要求认证，不作可启动资格。

新取固定OEM真实hwsched HFI与generic HFI源后，确认应区分两条路径：hwsched为17队列、表头24B、每队列头48B、整表840B、首队列offset848，HFIMEM请求70488B、4KiB粒度后备73728B；LOG为65536B。精确结构片段在host及ARM64进行sizeof/offsetof断言，17行ID/priority/offset逐项匹配固定源init_queues。AQE与SQE两条真实consumer均调用adreno_get_firmware，实际复制fw->data[4]并跳过首word，已绑定源码，不凭旧注释决定。所有这些仍是固定OEM参考契约，不证明stock运行中的wire ABI。

当前共用AdrenoHfi.c严格验证3队列/16384B、按页开始的queue data和0xa00|q类型，而新参考hwsched的queue data从848B开始。仅加大buffer不能复用该transport；本轮没有修改旧transport或把描述表发布给GPU。

实际源ASan/UBSan通过16项公开拒绝、9项私有decoded-record损坏控制及8线程128份独立scratch/output计划一致检查。公开入口始终校验固定SHA；私有检查仅host测试直接包含实现，目标对象无绕过接口。全部原始块/请求与旧真实解码记录逐项相同；并发检查只说明不共享可变存储时的重入，不声称共享scratch安全或ARM内存模型证明。

共用decoder、SHA与新适配器用iPhoneOS SDK进行独立ARM64/general-regs-only编译，3对象可重定位链接通过，未解析项仅普通memcmp/memcpy/memset和stack protector。初次导入检查遗漏显式调用的memcmp而拒绝；已有c50定义经实际可执行段核对，预链接nm的S并非未定义，首次误要求T的失败也保留。没有放宽源码SHA或修改内核。这不是原生kernel配方、最终kernel B/BL/ready或硬件验收。

下一项对现有HFI形成显式gen7-hwsched profile的隔离布局/校验及参数化草案，保留原3队列严格行为，先确认真实command/ACK字段和停止/独占/一致性生命周期再接Send/Poll。不直接改活跃队列、发通知或启动手机。[实现、源绑定与检查](evidence/gpu-firmware-layout-2026-10-30.json)。


## 显式HFI停止态profile通过隔离主机及目标检查

在out内形成对现有AdrenoHfi的追加式补丁：显式选择原Modern3（3队列 / 16384B）或Gen7Hwsched17（17队列 / 73728B），未知profile拒绝，不自动猜格式。原C源完整前缀、旧头API/结构和旧测试保持；补丁独立重放逐字节一致，生产源码没有修改。

新接口只初始化/校验新鲜停止态私有内存。调用者必须在整个调用期间持有真实停止、独占、稳定epoch及CPU/GMU一致性保证；回调只是检查调用者声明，不证明硬件停止或安全所有权。先检查再写，首次写前保存所有权记录；写后丢失lease或检测损坏进入隔离态，保留backing/epoch，重复初始化拒绝，不回滚、释放或重置。停止态校验不能用于运行队列。

精确固定OEM initializer及宏作为源oracle，实际比较840B头；fixture另行清零剩余内存后全buffer比较。新接口要求队列内容、索引、保留字和padding初始为零是本原型策略，不说OEM initializer清零了整个73728B。该参考仍非Xiaomi stock精确源码/运行ABI证明。

实际源ASan/UBSan通过276项wire损坏、26项参数拒绝、24项lease/生命周期及128份线程私有上下文检查；只读页校验通过，隔离态在PROT_NONE backing下不读取内存或回调。原接口基线与候选的510项绕回收发及4100次序号交换结果一致；它们是软件peer，不是真GMU ACK。独立ARM64/general-regs-only对象及新C++/C接口可重定位链接通过，仅保留stack protector导入，不是原生kernel最终链接或ready。

真实Gen7 consumer先按ACK type1分流，清除两侧RECORD bit18后比较完整回显请求头；word2为0xffffffff才是此处失败标记，其他值需按具体命令解释。旧Poll仅比较序号并把任意非零word2视为错误，不能原样沿用。当前没有Gen7 Send/Poll、notify或激活入口。

首次源oracle缺少宏导致编译拒绝、host保护页fixture误用4KiB而非本机16KiB页对齐，均已保留日志；修正的是隔离检查，不是手机驱动故障，GPU4KiB粒度未改。下一仅实现显式Gen7命令/ACK transport并保留原行为、错误与超时后的所有权；先软件peer/目标检查，仍不访问GPU、供电、SMMU或启动手机。[实现与检查](evidence/gpu-hfi-stopped-profile-2026-10-30.json)。


## 恢复无人值守：Gen7收发完成，启动语义与动态资源接续

机主在Git/文档工作后明确恢复无人值守GPU适配。已恢复原heartbeat和caffeinate唤醒，不设关机时间。小米14参考固定d4fb1472、一加Ace5固定aaa100d1；对照17队列ring及启动消息边界，没有复制其IOVA、SMMU bank/ASID、投票、安全状态或Darwin22私有ABI。

勘误：旧停止态阶段文字/检查器和下一计划把RECORD写为bit18；实际固定OEM头始终为BIT(19)，bit18是NOP。旧报告不改，本阶段按精确宏和31项其他bit的完整echo负控制执行；NOP必须参与匹配。

在隔离out的现有候选上追加Gen7 Attach/Send/Poll/Wait。完整保留旧Modern3实现及头API；显式17队列/73728B，无格式猜测。停止态state2仅一次转交为attached state4，运行时检查独立的coherent phase，不调用停止态validator检查运行队列；两份私有所有权记录必须存活。lease回调是caller声明，仍需真实平台停止/DMA/TLB/缓存与映射证明。

发送保持四字对齐/FAFA填充、完整12bit序号及发布后通知。ACK要求type1与仅去除bit19的完整请求头匹配。成功仅表示收包；正word2保留待命令解释，FFFFFFFF失败标记保留并隔离。未知非ACK（含内存请求/故障）原样返回、保留未退休队列并隔离，尚无自动分配器/假回应；超长/损坏不截断。不确定发布、通知失败、lease丢失、等待错误或超时保留pending/epoch/backing，不提供reset/free/盲重发；原始回调错误及阶段留存。

实际ASan/UBSan通过2048绕回/填充、8200序号交换、31项完整echo差异、288损坏/未处理消息、14生命周期、13参数/12attach/5reply拒绝及128份独立上下文。错误RECORD位和仅比序号的两个实际突变对象均被同一fixture拒绝。原Modern3基线/候选510/4100回归输出一致；追加补丁独立重放字节一致。ARM64/general-regs-only及四个新C ABI的C++可重定位链接通过，仅stack protector导入。它们是软件peer和SDK独立对象，不是原生kernel最终链接、真实GMU ACK、完整ARM弱内存或并发共享队列证明。

首次fixture把零/短错误包表示成空ring而拒绝，原日志保留；修正的是可见错误包/部分可见范围，未改手机。规范AdrenoHfi源、normalized/raw证明树、255输入/77归档/raw231/default42均未变，无新kernel或手机操作。

下一只实现固定容量启动packet/ACK语义与MEM_ALLOC需求plan：逐项绑定generic/v5/async consumer，未知实际HFI版本不可选协议；完整保留请求和地址/大小/标志，不实际分配IOVA、写映射或伪造ACK。bigIB/fence/动态资源及K80平台安全电源所有权仍缺，runtime_complete保持0。随后按明确平台缺口推进最小运行时接入，不能据孤立接口启动GPU。[证据和具体计划](evidence/gpu-hfi-transport-2026-10-30.json)。


## 启动回包语义和动态内存需求实现完成，转K80原生平台接合

隔离ZornGpuStartupPlan.c/h已实现固定容量最小九项启动步骤模板、逐consumer回包判断和MEM_ALLOC需求解析。它是小米14参考中的最小子集，不是完整原厂冷/暖启动序列。PERF/BW保持缺少K80 OPP/command-DB输入而不可发送；预占策略必须显式提供，未照搬houji的关闭预占。文件版本字/未知版本来源/epoch0不能选择协议；LIVE标记仍只是未来caller声明，本轮没有读真机。

绑定三段精确OEM函数后区分：generic要求word2为0；v5必须实际存在word3状态、GET_VALUE正结果是数据而feature非零返回会停止后续；START/async只按FFFFFFFF失败标记。不能把四字回包要求施加给所有legacy消息，也不能把缺失word3清零补成成功。实际GMU版本来源consumer读取DTCM，但当前文件字不是已运行版本，未据文件做握手。

MEM_ALLOC保留全部10字legacy/version0和11字current/version1原始请求、GPU/GMU地址及两handle；高版本保留raw但拒绝解释（参考对所有正版本按current复制，本候选更窄）。完整32位size/alignment校验、零size/未知flag/kind/指数/舍入/地址溢出不截断。分类GMU RAM/GPU global/IPC固定资源/预分配fence/memstore，secure/MMIO需求显式保留；没有产生成功host handle、实际地址或ACK。原GMU-only RAM分配器实际使用READ|WRITE|PRIV，GPU import/IPC才用get_attrs，不能只从请求flag推断真实映射权限。runtime_complete恒0。

实际ASan/UBSan与原始函数/packed结构oracle通过840组回包语义、53248组描述符/分配路径、65654不可用或边界、8参数及128独立上下文控制；两个真实突变（缺word3仍接受、未知版本接受）被拒绝。目标ARM64/general-regs-only及实际packed sizeof/offsetof、三新C ABI的C++可重定位链接通过，仅memcpy导入。source oracle只是wait/log/device结构shim，不是Linux对象布局、K80硬件或Darwin23最终内核资格。首次fragment拼接少换行的编译拒绝日志保留，修正隔离wrapper而非手机。

下一已经从协议推进到K80原生平台资源/config接合：现有NativeAdrenoGmuPlatform/Config/Service绑定Sheng五窗口、五缓冲、16KiB LOG/HFI、sheng投票和ShengGmuColdStart，不能改名复用。复用NativeAdrenoBoard描述解析和既有decoder，按K80命名资源、真实持有的映射/电源/安全lease及原生类型设计独立Gen7接合；DT地址及callback返回不代表所有权，不按SID猜bank。先隔离目标接口和明确缺失provider，禁止自动服务挂载/MMIO/供电/SMMU/固件执行。CPU显示、触控及88份原驱动源、255/77/raw231/default42仍匹配，无新kernel或手机操作。[证据与下一计划](evidence/gpu-startup-contract-2026-10-30.json)。


## K80原生资源接合及实际backing接口通过，下一准备自有内存

隔离ZornGpuNativePlatform.cpp/h已复用真实NativeAdrenoBoard::parseReg，分别按名称接GPU7项/GMU3项，不把10项塞入Sheng五窗口接口，也未改共用8项解析容量。输入未知/重名/缺项、错范围/长度/cell、别名/溢出失败不改最终描述；中间解析用私有数组隔离原parser的部分写入。描述中保留范围重叠mask，不做ioremap/读取/供电，也不据SID选择bank。固定profile来自已绑定缓存FDT，非重新读取硬件。

关键具体区别：节点名是gmu@3d69000，实际名为gmu的reg却是0x3d68000、0x37000字节；不能从unit-address或其他机型常量推起始地址。其宽范围与CX-misc重叠0x1000；AO区间[0x3d40000,0x3d50000)与RSCC相邻而非重叠。最初fixture错误按节点名断言及误判相邻区间被拒，日志保留；生成profile一直按原reg正确，不是手机修复，更不是可访问整个aperture的证明。

接合已读取真实NativeAdrenoMemory的公开getter：仅在caller整个调用持有真实停止/独占/稳定lease时观察CPU映射、完整单物理span、显式宽度policy、引用/隔离/缓存状态；前后lease失败保留原IOReturn且不发布snapshot。没有分配、加设备引用、cache维护、映射或释放的副作用。回调只是caller断言，不是停止/DMA/TLB/一致性证据；policy宽度不是SMMU OAS观测，物理地址也没有当IOVA。

通过实际固定SHA firmware plan一次集成调用，8项/565248B、6个fixed IOVA需求和2个动态IOVA需求与64KiB LOG/72KiB HFI相符；实际runtime config仍明确缺操作scope/电源时钟/SMMU所有权/ZAP认证/board votes/live HFI/动态资源/真实backing绑定，runtime_complete0，不产生伪造的ShengGmuConfig。

实际ASan/UBSan通过94资源拒绝、11配置拒绝、8份真实共用NativeAdrenoMemory实现的host backing描述、13 backing拒绝和128份独立资源上下文。host IOKit/cache是double，PA不是手机实测；未在并发线程共享非原子memory fixture。两个实际突变（错误range接受、忽略后lease失败）被拒绝。首次host fixture缺IODirection/kIOMemoryPersistent及负控制选择器命中两处的拒绝日志保留；补充host-only声明按冻结真实头核对，未改原头/实现。

这次使用真实冻结IOPlatformExpert C++配方和XNU/IOKit头，独立编译新adapter、原NativeAdrenoBoard以及原NativeAdrenoMemory本体，general-regs-only通过；adapter+parser可重定位链接仅memcpy/stack protector导入，无分配/MMIO/ColdStart调用。不是最终内核、原Apple二进制对象ABI或真实分配器/物理/缓存/DMA验收。88原GPU源/255输入/77归档/raw231/default42仍匹配，无新kernel/镜像/手机操作。

下一具体平台操作是自有Gen7静态backing准备，调用真实NativeAdrenoMemory::allocate，以固定SHA公共plan限制一次8项565248B，私有持久对象保留所有部分/隔离失败及原错误。不是继续扩启动协议；不用Sheng固定五buffer，也不设IOVA、不发布设备引用、不改缓存策略或启动固件。先实际实现/失败控制/同版原生目标及来源链接，再决定最小原生资格检查；任何手机轮次仍需完整start.o/最终链接/负载/当前输入/归档/ready与原回收保护。[证据及下一项](evidence/gpu-native-platform-2026-10-30.json)。


## 自有Gen7静态内存provider完成，进入规范原生集成

隔离ZornGpuOwnedMemory.cpp/h已调用真实NativeAdrenoMemory::allocate，为固定SHA公共FirmwarePlan的一次8项565248B准备CPU自有backing；不再用Sheng五buffer。9856B对象（host尺寸，目标constinit存储也通过）含私有plan/scratch/八对象，放持久存储而非kernel栈。一次状态机区分FRESH/PREPARING/CPU_PREPARED/RETAINED_FAILURE，任何已开始尝试的失败都保留原报告/对象/epoch，重复或重入拒绝，不清锁、重试或析构清理。

记录逐项真实allocation IOReturn、attempted/backed/described/quarantine mask及成功/实际保留字节；失败allocator可能自行回收它自己的未发布对象，外层不回收任何已取得backing。provider若内部complete失败，则保留隔离对象与原分配错误；现接口没有返回内部cleanup错误，明确标不可用，未伪造。仅成功getter给出CPU映射/完整单span/PA/尺寸/缓存状态；八对象互相CPU/PA范围重叠也拒绝并保留。未设IOVA、holdForDevice、改缓存策略、复制/执行固件、SCM/PAS或GPU MMIO。CPU_PREPARED不代表GPU/runtime ready，runtime_complete恒0。

实际共用实现加host IOKit/cache double检查：8项成功、56次逐项分配/prepare/metadata/cache/cleanup/CPU/长度失败、34 gate失败、9参数/4文件hash拒绝、7物理别名拒绝及重复prepare/析构保留通过ASan/UBSan。两个实际突变（允许prepared后再prepare、析构释放保留对象）被拒。最初过宽删除guard的负控制因重入导致host ASan stack-overflow，日志保留；已收窄为有限重复prepare负控制，候选原实现未发生此问题。正常gate回调/host teardown仍不是真实SMP、DRAM或DMA证据。

九个独立对象使用真实冻结C/C++配方及XNU/IOKit头（含原NativeAdrenoCpu缓存provider）编译/可重定位链接通过，内部NativeAdreno/Zorn/firmware导入闭合，余24个kernel符号在完整c50旧kernel中都找到并记录段；这只是旧镜像可用性，不能移植地址或替代新kernel最终链接/虚表ABI。constinit存储无__mod_init_func，prepare局部目标stack报告为144B级别，非完整调用链界限。外层仅最多8次调用；IOKit可能阻塞，现有cache统计CAS无显式次数上限，不称整套耗时有上限，未来正常线程及独立watchdog必需。

下一落实规范main builder/payload默认关闭的GPU-owned-memory开关、真实原八核门槛/一次正常线程caller、最小可回收日志与完整原生链接/来源/负载/ready；不是再做一轮CPU观察或继续扩纯协议模型。日志暂拟用已证明unsigned high32位置上的新GPU专用版本、独立稳定传输副本和严格范围/fallback，须先证明84文本/432触控及原错误完全保留，尚未实现或授权直接启动。主源改动先备份SHA/preimage，旧255/231工作区尽量保持，旧manifest不改。全通过后才选择一次原保护的新GPU内存资格轮；此阶段无新kernel/手机操作，原88源/255输入/77归档/raw231/default42仍匹配。[证据及下一项](evidence/gpu-owned-memory-2026-10-30.json)。


## GPU内存资格模块已接入规范主源，最终链接审计尚待完成

本轮已把固定SHA Gen7静态内存provider安装到维护中的native/gpu-owned，新增默认关闭的--gpu-owned-memory-preflight。主构建器和payload分别通过34/26项实际parser负控制，只允许新pins+incremental、原8核/8GiBRAM/保留Data/pub1/dim64、现有touch handoff/runtime/edges/parser/trace/fast-poll/HID及300/600/WDT1配置；拒绝自动boot、全部reuse、stop、深栈和CPU-active/display-progress载体冲突。选择该诊断时build manifest和boot镜像另放out/zorn/gpu-memory-integration，校验默认42前后不变；归档仍按新镜像SHA独立保存，不覆盖默认镜像。

实际BSD采样线程在原tsleep后、日志/proc_iterate/VFS前调用一次。GPU gate直接acquire检查原preflight_active==0、phase80/coordinatorDone/boundff/seenff/failure0/TLBready，不要求或读取CPU-active处理器句柄。constinit持久对象只做一次CPU自有backing准备；完成/失败后release发布不可变capture，writer acquire只读且绝不分配。四固件只读嵌入供hash/plan，没有复制到backing或执行。关闭路径链接C空实现，不自动挂载IOService。

新增D/v21-GPM1仅编码原gLogBusy持有期间的独立4096B传输副本，RAM规范环仍D/v18。复用16个原unsigned字段的高32位，保留原低位、84文本槽、3072B页脚和432B触控轨迹。64B容纳8个32位PA页号、8个经范围检查的8位页数、状态/阶段/下标/错误源/宽度policy/plan、原IOReturn/epoch/masks、magic与整块CRC。页数由固定SHA plan限定为19/27/19/37/1/1/16/18；PA必须4KiB对齐且页号/epoch可无损32位表示。不是24位截断或PA当IOVA。只接受能精确还原逐项allocation与原native/gate/snapshot错误的报告；其他错误/原高位冲突/越界整块保持原日志，并将新GPU观察视为不可用，不能解释成零错误/零分配。CPU/owner指针不属于此线格式。CRC不是认证，实际编码/IOKit开销未测，log_us包含编码/I/O/抢占锁等待，不能当CPU时间。

实际ASan/UBSan通过11个C/Python逐字节实例、40个fallback控制、2个别名控制、4096逐位置损坏拒绝、7个CRC正确非法语义拒绝；原生runtime四模式为关闭0分配、成功8分配565248B、门槛失败0分配及部分失败保留隔离对象/原错误。重复tick与8线程私有wire读者不重分配、不释放或改变capture。自包含满84槽v18及两份旧v19恢复后，旧读取器全部原GUI/文本/触控字段相同；历史日志是额外本地回归，不是新手机证据，也不是生产构建测试的必需私有输入。

10个组件/只读固件对象用实际冻结XNU/IOKit配方独立编译，两次相同输出位置重编译全SHA一致；另编译真实BSD caller、UFS及生成ArmCpu gate，13对象可重定位链接的新GPU C/C++名称闭合。关闭stub也单独编译，runtime对象无启动initializer。原活动对象未改。这不是最终kernel B/BL/callback/BSS或IOBuffer/IOMemoryDescriptor原Apple虚表ABI资格。兼容view此前尚未生成；生成后确认CPU/verified-root脚本仍按旧DEVICE.parent找输入的问题，已先保存preimage再按真实native symlink定位规范设备根目录，两个实际路径检查通过，完整compat路线仍须第一次真实build。

两次host fixture拒绝保留：prepare失败会正确回收未发布对象，因此改用metadata+complete失败验证保留隔离；旧reader要求bytes，测试误传bytearray后修正。没有放宽生产检查。主源及两处兼容修正均有精确preimage/SHA/provenance；冻结c50 normalized255输入/77归档、raw231、88原GPU源和默认42仍匹配。ps被sandbox拒绝的读取错误保留，未把读取错误当进程不存在的证据；current无活跃run，未执行手机操作。

下一只实现真正的audit-zorn-gpu-owned-memory.py并完成第一次规范compat完整构建，不能再扩模型。构建器已在打包boot/ready前要求此审计，但审计器尚未实现，当前ready明确allow_boot=false；不得用pass stub补齐。必须核对独立当前start.s及选定对象、实际最终指令/重定位/B-BL/回调/BSS/initializer、原Apple虚调用ABI、FAT kernel/ADT/menu和全部当前输入/不可变归档。全通过后才最多一次原保护GPU内存资格轮；本阶段没有最终kernel/镜像/手机启动，仍不代表GPU渲染或Metal。未改变CPU显示、触控、服务、SMMU、时钟/电源/SCM/PAS。[主源集成证据与下一项](evidence/gpu-owned-memory-integration-2026-10-30.json)。


## 规范完整构建与唯一GPU内存资格轮通过

规范root构建器经固定compat视图完成完整内核、真实FAT kernel/ADT/menu、342项当前输入和190份不可变归档核对。boot为0fe61e0dd19d2968ea90a431954dee0854fa3eddd1a27e407dc5acc05f2f7360，完整kernel为dcb055be71b2069f1ee31bdc15396c52e03b9cb918a8daa752c0ce3445526857，归档为out/zorn/builds/0fe61e0d。GPU诊断manifest/boot另放out/zorn/gpu-memory-integration，默认42未覆盖。当前主构建器SHA33bb324b0274cb85187e0984351803ce1034ce10ecddac98f1b7fbb9010cc9ab；前494/165是对应preimage，不冒充新源码。

新最终审计器已实际核对13份独立重编译对象全SHA、48函数、336条B/BL调用边、回调及新owned runtime/wire BSS、初始化/只读固件。按真实XNU/IOKit配方重新编译IOBufferMemoryDescriptor和IOMemoryDescriptor注解对象，与每个被审计的实际内核核对44+37个虚表槽；六个新编译原型的槽位及NativeAdrenoMemory本体24处虚调用一致，不复制Darwin22偏移。注解对象未链接/执行。新回调和owned runtime/wire的完整PAGE目标单独核对，其余普通PAGE地址保留正常链接器契约，不声称穷尽地址证明。首次把共用pool的不同基本块ADRP当线性配对而拒绝，日志保留；特殊owned检查限定真实新runtime/wire，所有原CPU/display检查不改。真实内核独立副本的指令、调用目标、回调、虚表、owned BSS写权限及固件字节六项破坏全部拒绝，原内核不改。BSS原为无文件后备zerofill，第一次尝试按文件偏移改BSS字节的fixture拒绝也保留。

第一次规范路线暴露的失败均有原日志和最小修正：SMP检查器传递与prepare相同的显式profile环境，源比对未放宽；sandbox禁止sysctl后经授权执行本地构建，未伪造主机数值；失败make删除KernelConfigTables后用原有bootstrap修复依赖，未省略导出/对象；startup记录恢复前独立重编译与未改活动对象全SHA相同。修复时一次缩进错误在构建前被拒，已保留并修正。根工作区97项源码与冻结合格回放及5项单独pin变换完全匹配、tracked改动闭合，才建立精确字节继承绑定；没有新patch回放/干净bootstrap或跨机器复现的宣称，旧对象确有增量复用。独立当前start.s完整重组装SHA一致且无早期/虚拟/translation探针，最终SMP调用审计通过。OS profile SHA更新后原payload guard正确拒绝旧证明；现有脚本实际只读挂载并复核SystemOS UUID及三处原字节，再生成新证明，未修改系统镜像或放宽SHA。

唯一新轮out/zorn/debug/20261030-222034-0fe61e0d于22:20:34–22:27:11自动回recovery，397秒。新日志SHA2f10a7e2ccb49b4bc2fccd3c4af9eb0ccc7528351c1951736e8de8f0555504c5，与boot/kernel、342当前输入和190归档完整绑定。归档读取器实际位于gpu-owned-host-inputs/UniXNU-zorn/scripts/read-zorn-log.py，依赖的GPU decoder/progress helper也按各自实际路径/SHA绑定；最初qualifier错假设根目录别名而拒绝，未改旧归档/manifest。新日志分析仅用这些归档字节，没有读取跨核运行栈。

本轮确为D/v21-GPM1，观测可用。state2/phase5/index8，epoch1，plan及所有native/gate/snapshot/allocation状态为0；attempted/backed/described均ff，quarantine0，8个成功单span描述合计565248B。page数19/27/19/37/1/1/16/18，实际PA逐项保留在绑定结果中，不当IOVA；40bit仅显式分配policy，非SMMU OAS。说明本版真实IOBuffer分配/CPU映射/单span查询/零初始化与现有CPU cache helper准备路径完成；不是GPU DMA一致性、SMMU lease/映射或固件执行证明。

原八核phase80/seen/bound/remap/timers/ipis全ff、failure0/TLBready；Data仍C7D77FF3-6437-4C4A-8E05-E8E239AC1641和cookie2dde8229，可用7443562496B，RAM Data错误0、dim64。GUI tick20/ms316265/hold300。120秒单帧实际看到锁屏4:02、壁纸与home indicator，音频关闭；不是桌面、触摸、全窗口连续画面、压力/性能/长期验收，更未解释历史苹果标志。旧c50观察与本轮GPU-memory名额各自已消耗，禁止重启它们或追加同类CPU/GUI/内存资格轮。

冻结c50的255输入/77归档、raw231、88原GPU源及默认42回收后仍匹配。root342当前也匹配；后续改变任何选定源码/对象要先保存preimage并把相应当前声明标历史，绝不改旧manifest。没有Git commit/push。完整format2原生路线仍未验收；本次是规范root入口通过固定format1 compat视图完成，不混称为新format2内核等价。

下一具体工作是隔离K80按role持有IODeviceMemory/IOMemoryMap的原生窗口owner，读取真实Gmu/Smmu/Service映射路径及本版头/原始ABI；保持GPU7/GMU3边界和重叠，严格区分CPU映射所有权与供电/停止/DMA/TLB/安全权限。当前没有NativeAdrenoMmio.cpp/h这个文件，错误读取已保留，不假造现有接口。实际map API无IOReturn时保留未知，不把nullptr臆测成某个原生错误；部分持有对象/错误/epoch保留，无析构自动清理/盲重试。只先做实际源的host failure/lifetime及同版目标/ABI检查，不新增线协议、CPU观察或手机轮次；真实硬件访问还需独立K80 power/security/access/stop provider，callback0/DT地址/已映射CPU指针都不代表许可。不改CPU显示、触控、SMMU/IOVA、时钟电源、SCM/PAS或执行固件。[完整构建、失败、回收证据与下一项](evidence/gpu-owned-memory-trial-2026-10-30.json)。


## 隔离原生窗口 owner 完成，尚未取得寄存器访问资格

[本阶段证据](evidence/gpu-native-window-owner-2026-10-30.json)记录实际 `IODeviceMemory`/`IOMemoryMap` 持有层；源码仅在独立 `out/zorn/gpu-native-window-owner`，未接入活动 Service。复用固定 K80 GPU7/GMU3 描述与原 parser，按角色选择、固定容量10项、不可复制，显式 `Anywhere|InhibitCache|Unique`，不暴露地址或 volatile MMIO 访问器。任意所选物理页重叠在首个 factory 前拒绝，包括 GMU/CX-misc 的0x1000重叠；尚未实现共享页优化。

一次准备，部分失败保留实际 descriptor/map 引用、阶段、mask 与隔离状态；nullptr 没有原生错误码，不能伪造 NoMemory。成功路径才可显式 retire，析构不自动释放，失败或重复调用不重试。实际 XNU `unmap` 即使返回错误也可能清掉地址，因此分别保留 attempted/success mask 与原 IOReturn，不能据错误认定旧映射仍可用。串行 epoch gate 只检查调用者所有权，不证明 GPU 停止、供电或安全访问；IOKit 仍可能阻塞。

实际源 ASan/UBSan 覆盖1023角色子集，其中256种重叠在 factory 前拒绝；150逐项原生失败、73 gate失败、9参数/描述控制、重入/重复/析构保留与128私有上下文通过。三处真实源码突变（接受重叠、重复准备、丢弃unmap原错误）均被检查拒绝。原生冻结 XNU/IOKit 配方独立编译3对象，另目录重编完整SHA一致。实际 Apple `IOMemoryDescriptor`/`IOGeneralMemoryDescriptor`/`IOMemoryMap` 共98虚表槽、11个编译原型及新对象11处虚调用核对通过；factory实际返回 IOGeneralMemoryDescriptor，不假造独立 IODeviceMemory 虚表。首次检查器错找 createMappingInTask 的拒绝及修正前脚本保留，provider未因该修正改变。无新 initializer、SIMD 或隐式析构注册。

这些是 host double 与真实目标/原内核ABI检查，不是手机映射、DMA或新最终内核验证。旧0fe的342当前输入/190归档、冻结255/raw231、原88GPU源和默认42仍匹配；没有新build/run/手机操作，上一轮397秒回收结果保留且不可重复。下一项是精确K80电源/时钟provider解析与真实接口接合：先绑定gen7-9-1 HWSCHED consumer和实际Clock/RPMh/CommandDB来源/ABI，区别UEFI Boot Services与Darwin生命周期，不能把引用机资源回调当已实现provider。未闭合power/security/access/stop前不设计MMIO试写，不改触控/CPU显示。


## GPU 电源资源的真实 UEFI 查询接口完成隔离实现

[本阶段证据](evidence/gpu-power-resolver-2026-10-30.json)记录 `out/zorn/gpu-power-resolver/ZornGpuPowerResolver.cpp/h`。复用实际 EDK II `Uefi.h` 和 Qcom `EFIClock.h`，只定位 Clock/RPMh/CommandDB，再查询固定 K80 CX GDSC、GMU 和 HUB 三个名称；`hub_cx_int` 与参考机 `hub_aon` 不混用。HWSCHED 完整源码早已在固定453d8875参考及清单中，本次只核对SHA/consumer，没有再次下载。其first-boot使用 `GMU_MAX_PWRLEVELS-1`，本地DTS对应第二档625MHz/SVS、参考gen7-9-1 hub200MHz；这些是未执行的输入策略，不是测量或Xiaomi stock源码等价证明，本次不设置频率。

实际 ClockDxe INF 与当前 Build FFS 选择 patched `53c18b9e`，旧触控host检查绑定的原文件为 `b1608ab9`。两文件差一个4字节指令，已用的版本1.0.a及lookup入口一致；旧证明不改，不把当前Build FFS当成已提取归档FD/当前手机模块。真实 `EFIClock.h` 宏为1.0.9，严格只核对实际消费的GetClockID槽1/GetClockPowerDomainID槽10，两槽在该二进制共用0x14dc入口；不宣称未消费的尾部ABI完全相同。选定Qcom树没有RPMh/CommandDB公共头，本实现只读已绑定8字节版本前缀，未造完整协议结构或调用任何未知方法。

成功路径6次协议/名称调用；原64位EFI_STATUS、正警告、失败时原始输出均保留，不把警告清零为成功，也不为本地版本/类型检查伪造原生错误码。私有借用指针只在串行Boot Services epoch有效，显式close只本地失效，不调用固件释放/disable；失败/重复/重入不重试，析构没有固件调用。查询返回的ID不是电源或停止所有权token。实际ClockDxe名称命中会经过0x3ea4客户端列表，可能分配24B软件bookkeeping；列表遍历无显式次数上限，不能称查询完全无副作用或6次调用就有墙钟超时保证。没有执行这些provider。

实际源ASan/UBSan通过36项64位原状态失败/警告、12项gate失败、23项ABI/作用域/参数控制及128私有上下文。放行Darwin作用域、把warning当成功、删除ID类型检查三处真实源码突变均拒绝。首个wrong-tag负控制因fixture给出重复错误ID而被重复检查遮蔽，初版脚本/日志保留；改为互不重复错误ID并核对首个失败位置后通过，provider未因该修正改变。`llvm-readobj`在本机不可用，改用已有`llvm-objdump`检查section，错误保留。

实际ZornBootMemoryDxe CLANGPDB配方和真实头编成独立AArch64 COFF/LTO对象，另输出完整SHA一致；反汇编注解显式关闭LTO并使用general-regs-only，核对真实Boot Services `LocateProtocol`偏移0x140、Clock偏移8/80及完整64位原型，无未解析导入、SIMD或初始化/析构注册。注解不是最终FD链接或Darwin23内核运行时provider证明。

当前342输入/190归档、冻结255/raw231、原88GPU源和默认42仍匹配，无新kernel/FD/手机操作。真正的EBS事件所有者、归档FD内精确模块身份及live lookup尚未验证；下一项在新隔离目录实现实际CreateEventEx/CloseEvent生命周期owner，并有限只读绑定归档FD模块。完整power/security/access/stop/DMA所有权仍缺，不调用Enable/SetRate、RPMh vote、SCM/PAS/reset、MMIO或固件，不改变CPU显示/触控，不重复0fe/c50。


## EBS 生命周期持有层与归档 FD 模块身份已完成

[本阶段证据](evidence/gpu-boot-lifecycle-2026-10-30.json)对应独立 `out/zorn/gpu-boot-lifecycle`。实际UEFI `CreateEventEx`在查询前注册BeforeExitBootServices和ExitBootServices两个事件；回调只release-store单调失效锁存，不调用Boot Services/解析器/锁，不取消已经在途的provider。后续gate禁止下一原生调用，即使解析器仍RESOLVING。选定DXE在终止内存映射前先发Before事件，失败MapKey也保持永久失效，不重新启用查询。

显式close只在退出前关闭确知成功注册的事件；失败/警告返回的未知partial handle保留，重复handle隔离而不double-close，析构不自动清理，失败/重复不重试。回调上下文必须持久存活至所有可能通知结束；实际CoreCloseEvent先移除notify/signal队列。这个源契约不等于任意共享多核事件安全性或真实EBS调度验收，caller仍须选定固件的串行正常线程契约。

实际源ASan/UBSan通过34项native失败/警告/partial/duplicate控制、21个退出注入时点、5参数控制和128私有上下文；忽略expired、删除事件锁存、关闭未知event三个源码突变均拒绝。真实固件配方的两个LTO对象另输出完整SHA相同，52项递归头/源绑定；CreateEventEx/CloseEvent偏移0x170/0x70、真实EFI_EVENT_NOTIFY签名核对。回调目标只有一个STLR且无调用，实际armv9.2+rcpc配方的acquire为LDAPR；初版检查器误认LDAR的脚本保留，未改provider或夸成完整ARM弱内存证明。另用真实CompilerIntrinsicsLib完成无入口LTO链接注解，不强制未解析符号；注解没有装入FD或执行。最初fixture缩进Werror和checker把-o当最后参数的错误保留并修正。

有界只读解析原归档3MiB `SILICIUM_UEFI-05b8b30b.fd`：107个FFS/295个section，LZMA展开9883656B仅在RAM，落盘仅3个PE32目标。FV/FFS头与按attribute启用的数据checksum保留，16MiB累计输出、64MiB解码内存、深度/计数上界；不支持的格式拒绝。8种checksum/state/未知GUID/压缩/扩张/截断控制通过。这是固定FFS2/短头/已知GUID-LZMA子集，不是通用UEFI校验器。

实际归档内ClockDxe全文件SHA为`53c18b9e1569cebbcb9837c1d773cc5e836fb7e902df7c29b27b485a13d4fdfc`，RPMh为`cdebce5c9f96d16e71a0db8f9c4dbf591ed314dd94a6543b08c238902df65267`，CommandDB为`5c58d445f356af9f8497ea6f449ba534fd7920b045067cd3b02ad997863077bf`，均逐字节匹配且不需重定位归一化。此前“当前Build FFS不等于归档FD证明”的边界现在由新提取解决；旧触控checker的原Clock b1608来源证明及全部旧manifest不改。没有新live GPU查询，不能把归档模块存在当运行时接口/供电/停止所有权验收。

342当前输入/190归档、冻结255/raw231、原88GPU源/default42仍匹配，手机最后仍为0fe健康recovery，无新FD/kernel/手机操作。下一项仅在新隔离staged模块实现真实ZornBootMemoryDxe的默认关闭查询caller/C ABI与指针无关的不可变RAM结果，先读原watchdog/BCB/touch/marker顺序并编译实际消费者/链接审计；暂不加线协议、覆盖活动FD或启动手机。power/security/access/stop/DMA仍缺，不调用GPU寄存器、clock/power mutation、SCM/PAS/reset/SMMU或执行固件。


## 默认关闭的真实固件查询 caller 与 C ABI 已隔离链接

[本阶段证据](evidence/gpu-real-caller-2026-10-30.json)对应 `out/zorn/gpu-real-caller`，包含真实 `ZornBootMemoryDxe.c` staged副本、C++查询wrapper和原生命周期/解析器源码。`stage-caller.py`默认输出与原C源逐字节一致的OFF版本；只有显式 `--gpu-query --early-watchdog 1` 才生成ON版本，拒绝boot/reuse或省略watchdog选择。只是隔离host选择，不是规范builder新参数或现有镜像授权。

实际 `PublishRange` 顺序为：原范围检查、新诊断once门、原ArmEarlyWatchdog成功返回并保留原status、原触控交接成功、查询C ABI、原载荷copy/publish。once门在watchdog之前，防止反复扫描候选载荷而重设watchdog或重触查询。原watchdog模式1仍60000/65000ms并检查实际SMC状态和enable读回，模式2仍原故意停机分支；querywrapper另拒绝缺失/非mode1/坏反码/watchdog非成功/无原触控marker，不把原“无marker返回SUCCESS”当已保护。新wrapper自身不SMC，BCB必须由未来原runner按新镜像fresh准备/读回，不能以旧BCB记录冒充当前保护。

C ABI持久常量初始化owner、一次attempt和release READY，封存272B无指针标量RAM snapshot，保留原64位版本/ID/Locate/Query/Create/Close/错误/原watchdog status及有效性/partial/expiry mask。guard未尝试项明确MAX_UINT32不可用，不当零成功；重复/重入不覆写capture，输出须caller稳定独占。只供preEBS本地copy，未发布给Darwin、未新增线协议/持久写范围或改旧v18/19/20/21。EBS后的snapshot不是live lease。

实际C ABI加真实watchdog函数及PublishRange前缀ASan/UBSan通过23场景，覆盖原SMC失败/enable读回失败/touch失败/坏marker/mode2/所有10个原生调用失败/EBS到来/重复扫描与capture不变；4项host CLI拒绝。SMC、触控和协议均为host double，此测试只说明真实源调用顺序与拒绝逻辑，不是手机watchdog/BCB或live GPU查询。初版prefix漏marker宏、测试括号Werror已保留并修正，生产guard未放宽。

实际固件配方编译4个选定对象，另目录完整SHA相同；73项递归头/源及真实静态库绑定。独立编译原AutoGen并链接真实模块入口，显式排除旧模块归档，防止旧对象掩盖新caller。RAM读取函数以/include保留，Run noinline供实际边审计；未保留reader的初次未合格source/module/map preimage保留。链接器输出为preGenFw隔离PE，不是新完整FD。独立LTO模块除已单独记录的PE timestamp外逐字节同，不据此假设元数据无消费者。

最终PE核对真实caller→query B/BL目标、callback单次release且无调用、目标编译尺寸的272Bcapture/360Bowner及ready/once存储可写初始零、5项readonly名称/marker及无新CRT初始化注册；C++回调在LTO折叠为实际 `STLUR w9,[x8,#0x38]`，初版只认STLR的auditor拒绝保留，修订仅接受该已核对实际opcode，未改provider。实际三个独立模块副本改坏调用目标/release存储/存储区写权限均拒绝。协议GUID IN参数池可写，不夸成所有provider数据readonly；其他优化CFG/PAGE仍保留编译器/链接器契约边界，不冒充完整canonical最终qualification。

342当前输入/190归档、冻结255/raw231、原88GPU源/default42保持，活动Mu模块/FD未覆盖，无新kernel/手机操作。RAM capture尚无recovery读取通道，allow_boot=false。下一项只做实际DarwinBoot的preEBS不可变RAM→ADT handoff：全272B原值复制，不将固件指针传入内核，不新造持久线协议；后续仍须可读诊断、规范builder/FD/payload/输入归档/ready/看护完整闭合，不能凭不可读结果启动。GPU供电/security/access/stop/DMA仍未完成，CPU显示和原触控保留。


## 查询报告的真实固件 RAM→DarwinBoot ADT 交接已隔离实现（跨日续调）

[本阶段证据](evidence/gpu-ram-handoff-2026-10-30.json)对应 `out/zorn/gpu-ram-handoff`。默认OFF的driver和DarwinBoot源与原文件字节一致；只有显式host选择 `--gpu-query-handoff --early-watchdog 1` 才生成配对staged源码。这不是canonical builder已提供的新参数，也没有生成新FD/kernel/手机轮。两仓库/历史文件名仍沿用10月30日，JSON记录真实跨日时间。

实际DarwinBoot只有现成AdtNode解析和整树CopyMem，未找到通用chosen追加API。此次直接扩展该实际解析器定位唯一chosen上的 `zorn-gpu-query` 精确272B零占位，复用实际node()编码器生成测试树；不新造第二个ADT解析器、runtime树扩容或firmwarecodec。独立GUID配置表只指向持久不可变标量capture；preEBS加载器校验后先全量复制到Tree，原整树复制再把它带入内核启动窗口。固件指针、event、协议和callable地址都不进入ADT。

生产端在原query后once尝试InstallConfigurationTable，原query错误优先、不改成成功。强制原WDT SUCCESS/mode1、owner关闭、无expiry、所有返回event已关闭；发现EBS到来或partial未关闭即不调用发布服务。源码复核中补充该门，修订前源码保留。原64位发布EFI_STATUS/非零warning保存在独立24B本地publication report，不改已经READY的272B capture；一旦尝试原生发布，静态对象一直保留，不因错误而猜表未生效/卸载/释放/重试。选定DXE实现可能分配和回调，非纯查询或墙钟有界；正常preEBS单调用者/稳定系统表仍是前提，不能靠callback填硬件所有权。

消费端限制最多1024表项，拒绝相同GUID重复（即使指向相同对象）、null/错版本/错尺寸/越界或未知mask/不兼容形状/源目标别名；真实AdtNode拒绝错节点、多个chosen、重复属性和错长度。272B目标必须全零，失败不改整树；源表/内容再次比较只能检查可观察变化，不能证明任意地址安全、认证或原子一致。所有raw64版本/ID/status原样保留，不截成32bit，不把ID或snapshot当GPU停止/电源/安全/DMA lease。

实际C源ASan/UBSan通过14个独立发布场景，每场35项消费拒绝，另4项host CLI拒绝；包括原native错误/warning、install后报错仍保留、重入/重复、不兼容表/ADT/flags、原raw64往返和可观察变动。实际旧watchdog/PublishRange前缀加真实query/lifetime/resolver/publisher/consumer组成的链通过7场景，SMC/触控/协议仍为host double，没有执行手机provider。首次BaseMemoryLib语言链接/ScanMem8声明冲突、partial-event测试状态串入独立consumer控制的断言、pipeline链接缺C符号日志均保留，修正测试/接合，不称手机修复。

真实两个固件模块配方编译12对象，独立输出全SHA一致，112递归输入绑定，旧module归档排除；Entry.S独立以实际PP/EDK Trim/assembler链重组装。首次只删预处理行标记留下AutoGen C typedef而被assembler拒绝，改用真实Trim；make变量continuation/WORKSPACE解析初版拒绝也保留。两个preGenFw链接PE的独立输出除分别记录timestamp外逐字节一致，不假设元数据无消费者。这不是完整FD/原生format2路线或真机资格。

最终两个实际PE核对caller query→publish顺序及B/BL、Boot→真实consumer/AdtNode、exact272B输入/输出CopyMem、原整树copy边、单个InstallConfigurationTable真实原型/slot0xc0和寄存器、release callback/无新initializer、Published/Report/once等可写初始零。5个实际独立PE副本破坏driver调用、native slot、存储写权限、loader调用或copy长度均拒绝。首个checker误要求movw2紧邻CopyMem，实际第一处多一个movx25,sp；原checker保留，修订只接收这两个精确序列，不放宽成任意回溯。其他优化CFG/PAGE/dataflow保留编译器/链接器契约，不夸穷尽。

342当前输入/190归档、冻结255/raw231、88原GPU源/default42仍匹配；current/run显示最后0fe已recovered且名额消耗，无新build/run。本次ps进程读取仍被sandbox拒绝，错误保留，不能把拒绝当全系统无进程证明。活动FD和旧manifest未改。另修正porting.toml中残留Git暂停时期的诊断next_action，以机主明确恢复GPU为准，不恢复旧CPU/GUI轮。

尚无native ADT消费者或recovery读回；24B发布错误报告也不在272B ADT内。原caller在query/发布失败时中止payload发布，故RAM中有错误记录不等于DarwinBoot会运行或回收后可读。下一项是实际Darwin23 CPU-only属性消费者和一个容量/生命周期明确的既有日志读回路径；不将64B载体称能无损放下272B，不扩线协议/偷偷占旧text，未闭合就保留不可用。allow_boot=false，无GPU供电/MMIO/SCM/PAS/SMMU/执行，CPU显示与触控保持。


## Darwin23原生ADT消费者完成，原格式读回容量不合格（2026-10-31）

[本阶段证据](evidence/gpu-native-query-consumer-2026-10-31.json)对应 `out/zorn/gpu-native-query-consumer`。真实Darwin23 `SecureDTGetProperty`仅返回第一个同名属性，所以原生消费者使用实际SecureDT entry/property iterator检查唯一chosen、唯一name/报告属性，而非用首次lookup冒充重复检查；上限为256 root children、每child1024 properties。没有另造DT解析器、调用可分配的Enter/ExitEntry或读私有布局。实际SecureDT内部skipTree仍可递归，损坏bootDT可由原API panic；已验证、内核持有且稳定的DT区域是前提，不声称这些API对任意坏地址有有界失败。

从上一阶段精确272B scalar CABI/shape源码派生native头，只有UEFI typedef改为原生整数类型及static inline适配，无新codec/手机线格式。先把可能4B对齐的ADT值拷入8B对齐持久native report，再检查size/version/masks/形状。64位原versions/IDs/status不截断或解释成权限；失败时available0，即使RAM保留已复制的坏capture也不能解释为有效结果。原API未尝试status用INT32_MIN，已尝试原int错误保留，adapter错误另列，不造EFI/IOReturn原因。

隔离真实BSD caller在原GUI线程tsleep后、任何log/proc/VFS之前调用一次；`zorn_gpu_query_adthandoff=1`才读DT，关闭或非1不调用DT/gate。复用原全部八核acquire active0/phase80/coordinatorDone/boundff/seenff/failure0/TLBready gate，前后检查；没有调用memory prepare或CPU accounting。一次atomic attempt、release不可变336B native报告/acquire读取，不加线程、定时器、IOService挂载、锁清理或自动重试。OFF BSD源与原字节相同，规范builder尚未加入此新选择。

实际完整device_tree.c仅替换host所需kernel includes/安全宏/allocator shim，函数体保持；真实node()编码器构造合法树与重复/边界场景。ASan/UBSan40个独立process覆盖关闭/前后gate/缺失/重复chosen和property/错size/未知mask/数量上限/16个真实API调用逐项原-77错误/重入/重复及raw64全复制，host allocator计数0。shim不是真XNU地址空间、硬件或完整ARM弱内存证明。删除首次gate及放行重复属性两项实际源突变均拒绝；首次header静态helper在测试TU未用被Werror拒绝后改inline，初版fixture请求不存在的第17..20个API注入而断言失败，已保存并按实际成功路径16calls生成控制，生产guard未放宽。

真实XNU C/pexpert/BSD配方独立编译consumer、原device_tree、stagedBSD及原ArmCpu，共4对象对应独立SHA；原ArmCpu完整SHA还与活动对象相同。711递归头/源绑定，新consumer/gate名称可重定位链接闭合，无新initializer，原对象未改。核对实际BSD调用、所有新SecureDT/gate branch relocation、两次gate、272B输入memmove和336B报告memcpy、release/acquire及无间接service/SIMD；3个实际对象副本改坏BSD调用/copy长度/release均拒绝。不是最终kernel B/BL/PAGE/FD/FAT/ready或真机资格。初次依赖清单把cwd相对meta_features.h当root相对而拒绝，已绑定实际recipe cwd，不改生成头或原manifest。

只复用现有 `ZornLogBlock/zorn_log_put` 实际函数做了有限容量核对：GUI模式84个12B槽、每槽11字符，272B按带索引hex下界需68槽；满环新增68槽确实挤掉68旧槽。空环写入68后仅容16条后续词，第17条覆盖第一份capture。3072B footer字节保持不代表旧84text全部保留。现有void log_word还可能在busy/off时丢弃，没有返回原写错误；普通进度会继续写。64B unsigned highword载体也不能直接容纳272B原值，未尝试新压缩codec、扩协议、偷用旧text或改v18/19/20/21。因此完整保留契约下recovery读回明确不可用，不拿空环示例当实际可靠通道。

失败覆盖也仍有具体缺口：原UEFI query或table发布出错会停止payload发布，native consumer可能根本不运行，24B发布status未随272B进ADT。未把失败改成功、未启动不可读诊断。下一项只绑定现有选定UFSDxe/DiskIo/Partition及原单4KiB日志块的真实preEBS身份/权限能力，先实现隔离的有界只读eligibility selector，不执行Read/WriteBlocks/Flush/Reset或live lookup；源选择不是手机安装/可写所有权证据。若无符合保护契约的现成路径，保留具体阻塞并推进其余GPU平台源码，不再扩诊断协议。

342当前输入/190归档、冻结255/raw231、原88GPU源/default42核对不变，原0fe/c50轮名额消耗不重启。current与最后run仍为已完成/recovered，本轮无新kernel/FD/手机操作，allow_boot=false。CPU显示/触控/8GiB/Data/pub1/原2s门槛不改；GPU电源/security/access/stop/DMA/执行均未资格验收。


## 早期检查点介质身份选择器完成，查询读回仍未资格验收（2026-10-31）

[本阶段证据](evidence/gpu-early-checkpoint-provider-2026-10-31.json)对应 `out/zorn/gpu-early-checkpoint-provider`。规范host reader和原native UFS一致给出原唯一4KiB日志块：userdata-relative LBA2291712。旧只读GPT资料的userdata3112704..64049146导出absolute5404416；仅历史几何，不是本轮读GPT、当前partition unique GUID或CRC验证，Data窗口/原UUID/cookie未改。

仅复用既有有界FD reader、改变此次选择的三模块目标，在原05b8完整FD中提取UFSDxe143360B/b8dfd16a、DiskIoDxe40960B/27da79fa、PartitionDxe53248B/8b269013，完整SHA和选定文件逐字节一致；没有重做Clock/RPMh/CmdDb提取或改旧报告。FFS/section检查边界保持。归档含模块仍不等于K80接口已安装，常规MdeModulePkg源码只作协议消费参考，不称它与giulia二进制精确源码等价。

新纯C selector直接包含实际Uefi/BlockIo/DiskIo/PartitionInfo/DevicePath头，最多32候选、每path512B/32节点，caller提供稳定有效typed描述符及六项原lookup status/available mask。只描述性匹配标准UFS PUN0/LUN0、唯一GPT userdata child与历史边界、HD签名和PartitionInfo一致、exact parentprefix、4096B/present/nonremovable/non-readOnly且parent physical/child logical。原ZornBootMemoryDxe512B/readonly/nonlogical RAMDisk被排除。未知vendor path严格不可用，没有把二进制未绑定的实际Qcom路径猜成标准UFS。child与parent原MediaId分开保留，区分relative/absolute LBA；不把一个相同名字或GUID当可写lease。

caller-zeroed独占持久report一次使用，错误前检查report/输入及nested对象别名，原64bit lookup错误/warning和unknown mask保留，歧义/缺失/重复/重用/错scope/epoch拒绝。selector不枚举live handle、不调用Locate/Read/Write/Flush/Reset，不保留协议指针；scope1只是caller软件作用域，不是EBS事件或硬件证明。即使DescriptorEligible1，LiveDiscoveryVerified/GptReadVerified/WriteAuthorized始终0。此函数不是通用任意指针认证器，内存有效、稳定、typed且caller独占是前提。

ASan/UBSan40项候选拒绝、12项逐原status错误/warning、歧义/scope/alias/重用控制通过，所有协议方法设trap且调用数0；放行错误LUN和丢失原status两源码突变均拒绝。最初错误LUN只改child而使parentprefix同时不匹配，mutant因此幸存；旧fixture/output保留，改child/parent一致的LUN1隔离该guard后拒绝，生产guard未变。

真实固件配方selector对象独立SHA一致，45递归输入绑定，general-regs-only注解无间接protocol call。实际ABI取Media48B、BlockIo.Media偏移8、BlockSize12/LastBlock24、PartitionInfo144B/Info16、HD42B/UFS6B、report1888B。无入口PE注解使用真实选定库和独立编译原AutoGen/driver解决SDK导入；初版缺DebugAssert/LShiftU64、原PCD/callerbase、原entry依赖的失败日志均保留，没有pass stub或强制未解析。注解中原driver仅为真实SDK闭合，不生成新模块/FD或执行旧entry；不称新完整kernel/实际手机资格。

原84text+272B报告保留和加载器前失败读回仍没有合格路径；selector/归档证明不授予写入权限，ready=false，不会因为软件检查通过而启动不可读query。诊断链保留待查，不再扩载体/环/协议。下一项推进真正GPU平台缺口：固定gen7-9-1 ZAP consumer与实际EFIScm/scm_sip_interface、选定ScmDxeCompat安全provider的来源/ABI绑定和默认不调用的native请求配置，不执行SMC/SCM/PAS、认证/reset或GPU固件，不绕ZAP签名。

342当前输入/190归档、冻结255/raw231、原88GPU源/default42核对不变，无新FD/kernel/手机轮，无CPU/GUI/内存重复资格。CPU显示、触控、8GiB、Data、pub1和原2s门槛保持；GPU加速渲染/Metal仍未启用，真实power/security/access/stop/DMA尚未闭合。


## 机主暂停GPU实现，等待上游重构（2026-10-31）

机主提出先暂停GPU实现，说明UniXNU上游之后将更新重构的GPU实现。此处记录机主给出的方向，不把上游发布时间或兼容性当作已验证事实。GPU自动续调已暂停，专用 `com.unixnu.zorn.active-debug` 防休眠LaunchAgent已卸载；没有关机计划、自动上游轮询或新的手机操作。

暂停边界为早期检查点描述符selector及归档存储模块阶段。SCM/PAS阶段本轮只读取了既有头/参考源码，没有生成新适配器、最终内核、FD或手机轮次。所有源、测试、错误、归档和待查缺口保留，不重启旧0fe/c50资格轮。CPU1窄修正证据、现有CPU显示与触控、Data/8GiB/原八核门槛/default42及3a桌面基线不变。

后续须机主明确恢复，再核对上游实际提交/接口和K80 ABI、所有权与保护边界，决定哪些隔离实现可复用。旧章节所有“下一步/继续/已恢复”均为本次暂停前历史，不构成自动恢复授权。暂停记录见 `out/zorn/gpu-paused-20261031/pause.json`。


## 机主恢复仅离线GPU适配，SCM/PAS配置隔离完成（2026-10-31）

机主明确恢复GPU适配，手机未连接；仅离线预处理，必须真机调试时暂停。此授权取代前段暂停，自动续调已改为offline-only，不允许探测/操作手机或自动启动，旧0fe/c50名额仍消耗。

上游feat/ipados27-gpu-parity固定759d646比main5c8c145多28提交，作为参考不移植Darwin23 ABI。固定OEM kgsl_util.c链和实际stock KGSL对象确认PAS13、qcom_mdt_load后AUTH_RESET；该接口同时认证/解除复位，不是查询。原归档FD的ScmDxeCompat完整SHA17080673与选定binary逐字节一致，实际版本50002而头40001；只绑定ScmSipSysCall槽7/0x38到2410及寄存器参数，整个tail不宣称兼容。

隔离ZornGpuPasConfig直接使用真实UEFI/SCM头，184B无指针软件配置，raw64 lookup保留；native status/results未尝试明确unknown，InvokeAllowed恒0、缺失provider maskff，不传入metadata/物理地址/firmware指针或执行调用。ASan/UBSan与三源码突变拒绝，真实固件配方独立对象全SHA一致、原SDK无入口注解链接通过；不等于真实安全/power/stop/SMMU所有权、新FD/kernel或GPU执行。342当前输入/190归档、冻结255/raw231、88原GPU源/default42核对不变。

下一项仅离线追踪现有ZAP MDT加载器和K80保留区契约，复用已有decoder、不扩诊断协议、不赋真实地址/权限；需要手机时保存阻塞并暂停续调。证据见[evidence](evidence/gpu-scm-pas-binding-2026-10-31.json)，下一计划为out/zorn/gpu-scm-pas-binding/zap-loader-next-plan.json。


## ZAP固定文件的CPU准备与真实MDT契约已离线核对（2026-10-31）

新增隔离out/zorn/gpu-zap-loader，不改活动GPU/FD/kernel。已有AdrenoFirmware仅解GMU容器，不能拿它解ZAP；复用前阶段绑定的ELF报告与原SHA，未新造ELF codec。cached FDT原解析器确认zap-shader引用no-map的gpu_microcode_region@9b09a000/0x2000，仅声明资源，不是可写/供电/security/stop权限。

本地Xiaomi kernel d9e81e6的MDT/SCM源码已绑定，非stock模块精确源码声明。真实mdt_phdr_valid/bins_are_split/get_size函数体在host shim核对固定stock为non-split、relocatable、需求4096B；实际metadata consumer要求header148B紧接hash3896B共4044B，payload在文件4096处1072B。Linux调用顺序含PAS_INIT_IMAGE、relocatable MEM_SETUP、拷贝和KGSL AUTH_RESET；认证会解除复位。metadata物理连续/4K对齐/一致性需要真实DMA provider，普通CPU数组不提供。

新ZornGpuPrepareZap复用原NativeAdrenoSha256，只有完整固定SHA匹配才在caller独占CPU存储准备4044B metadata和1072B segment；失败不改输出，没有物理地址、SCM调用、认证、分配或执行能力。12088逐byte单bit损坏、尺寸/null/alias与三实际源码突变拒绝，ASan/UBSan通过。真实固件配方两个新目标对象分别独立重编SHA相同；原SDK无入口注解链接闭合，不是最终FD。为真实SDK PCD/callername闭合另编原AutoGen/driver，不称这两closure对象双编一致或执行旧入口。初次BaseMemory C linkage、target缺string.h声明、SDK链接缺PCD及oracle误截文档comment的日志/preimage全部保留，未放宽SHA/保护。

342当前输入/190归档、冻结255/raw231、原88GPU源/default42仍匹配，无手机探测/操作。下一项离线审计此保留区在真实UEFI/HOB/Darwin内存图中的排除/保留路径，metadata需另一真实provider；不把no-map或CPU字节当DMA/安全lease。读回仍不合格，allow_boot=false；真需手机时才暂停续调。[证据](evidence/gpu-zap-loader-2026-10-31.json)。


## ZAP保留区的实际源路径与描述符检查完成（2026-10-31）

隔离out/zorn/gpu-reserved-region读取真实平台MemoryMapLib、SEC/MemoryInitPei、ZornBootMemoryDxe和DarwinBoot：cached ZAP0x9b09a000/0x2000包含于PIL_Reserved0x8bc00000/0x17580000，原类型为AddMem/MEM_RES/Reserv。真实AddHob生成reserved resource HOB而不为此行生成system allocation HOB；实际ZornBootMemoryDxe在AddMemorySpace前减去DT reserved ranges，原DarwinBoot只连接conventional run并AllocateAddress，然后把单个window base/size交给bootargs。Darwin23 arm_vm_init来源显示原生VM据bootargs连续window管理，不能把Linux no-map直接当Darwin独立排除表。实际live HOB/GCD/EBS/window未读取，未声称手机所有权。

新ZgrDescribe直接使用真实EFI_MEMORY_REGION_DESCRIPTOR，纯只读检查唯一完整reserved cover及冲突/溢出/别名，上限128；输出明确LiveGcdVerified/DarwinWindowVerified/MetadataOwned/WriteAllowed全0，不保留指针、不调用固件。host以原MemoryMapLib实际GetMemoryMap取表；8项描述符拒绝和两源码突变拒绝通过ASan/UBSan。真实AddHob/Subtract/RunEnd函数体在host shim核对该reserved路径、subtract排除与run不跨保留洞；这是函数行为验证，不能替代实际启动次序/运行map证明。

真实固件配方describe和实际MemoryMapLib各自独立编译SHA相同、真实SDK无入口链接通过；活动源/对象未改，非新FD/kernel。342当前输入/190归档、冻结255/raw231、原88GPU源/default42核对保持，无手机探测/操作。下一项实现隔离preEBS CPU-owned metadata page owner，实际EFI页分配/释放及原退出gate，只host调用/目标编译；不改变cachepolicy或写保留区，普通page不代表SCM一致性/XPU许可。allow_boot=false，仍须真实power/security/stop/SMMU与可读保护诊断。[证据](evidence/gpu-reserved-region-2026-10-31.json)。


## 隔离preEBS CPU metadata页owner完成，SCM一致性仍未知（2026-10-31）

新增out/zorn/gpu-metadata-owner；所有活动调用点仍0，不改FD/kernel/旧源码。复用真实退出owner的隔离副本，仅增加event-only prepare与epoch+同一BS表检查，metadata路径不Locate/query clock；原query路径34失败/21退出/5参数/128上下文回归通过。原source/preimage保留，不扩新事件协议。

ZornGpuMetadataOwner正常preEBS串行once：固定准备metadata SHA/形状核对后，仅一次AllocateAnyPages/EfiBootServicesData/1页，再一次固定16KiB GetMemoryMap查询，最多256描述符、stride40..64；唯一完整BootServicesData映射且无RO/RP才拷4044B并清尾52B。返回页拒绝零/错对齐/溢出/保留区与owner/输入/BS/lifetime别名。各步前后检查退出锁存；不能取消在途native方法。raw64三状态、known/attempted、map key/version/stride/attrs、partial地址、ownership-known/隔离保留，不伪造native错误。失败/重复不retry或cleanup，析构不释放；只有完整CPU准备可显式一次pre-expiry FreePages，失败后所有权未知保留。CPU准备不是SCM coherent/XPU/security lease，相关资格恒0。

实际源ASan/UBSan18个raw状态/警告/partial/退出/map失败场景，另wrongBS/到期后retire/重入/重复/坏hash/析构保留控制通过，三源码突变拒绝。5个真实配方目标对象各独立重编全SHA一致，constinit无CRT、AllocatePages/FreePages/GetMemoryMap实际原型/slot0x28/30/38及SDK无入口注解链接通过；报告128B/owner16536B。注解不是新FD或手机资格。选定DXE AllocatePages可内部更新内存保护/属性表并产生通知，GetMemoryMap持内部锁；不宣称墙钟有界或纯无副作用，也不调用设置cachepolicy的API。

342当前输入/190归档、冻结255/raw231、88原GPU源/default42仍匹配，无手机探测/操作。下一项只追踪已有归档ScmDxeCompat对PAS_INIT metadata参数的真实buffer/cache/地址/lifetime契约，不能拿普通WB页或alignment补SCM一致性，不扩log/query协议。allow_boot=false；真需手机时暂停。[证据](evidence/gpu-metadata-owner-2026-10-31.json)。


## 实际SCM参数buffer机器契约审计完成，一致性缺口保留（2026-10-31）

隔离out/zorn/gpu-scm-buffer-contract只审计原归档17080673的机器指令，没有执行provider或重抽旧模块。PAS INIT/MEM/AUTH均走slot7/2410→2078→6fa4；0x82/3/1低四位分别2/3/1个参数，完整64位scalar复制至stack，再由SMC叶加载x2/x3/x4。INIT的metadata地址是x3中的值，未在所核对显式transport路径复制metadata字节/做地址翻译或证明pointee cache clean；二进制其他cache函数存在不代表此路径调用。外部TPL/诊断helper及secureworld副作用不夸穷尽。

实际指令把SMCid OR0x40000000；SMC w0==0时EFI_SUCCESS，Results[0]=1后接raw x1..x3。prefix1不是PAS语义成功/认证证据；错误路径可能只写Results[0]，剩余word不可假装有效。初脚本误把x22写入称Parameters[0]，已按20a8保存Results指针和2184 store修正，旧脚本/结果保留且新增寄存器base检查，无runtime/手机结果受影响。6fd4对SMC正返回循环至6fcc，没有次数/取消门；外层lifetime不能取消在途call，不能称native调用有界。

真实指令/实际B-BL和六个指令破坏拒绝通过；实际UEFI头独立目标注解核对INIT02000201/82、MEM02000202/3、AUTH02000205/1、10参数/4结果、slot0x38及64bit原型。只读无执行body。首次COFF CodeView因两个输出名不同导致SHA不同，原产物保留；改在相同原输出位置独立编译，原始完整字节一致，未归一化/改写元数据；这只是ABI注解，不是新驱动/FD。没有把普通CPU-owned WB页升级为SCM coherent/XPU许可，因此没有新增native调用器，认证/复位继续关闭。

342当前输入/190归档、冻结255/raw231、原88GPU/default42保持；无手机探测/操作。下一项离线核对真实native SMMU provider接口与K80上下文分配消费路径，只在真实类型允许时做最小隔离描述符适配，未知bank/ASID/IOVA/stop保持不可用，不按SID猜bank或访问硬件。allow_boot=false，读回仍未合格。[证据](evidence/gpu-scm-buffer-contract-2026-10-31.json)。


## K80 SMMU角色描述接合完成，bank/ASID/slot不赋值（2026-10-31）

隔离out/zorn/gpu-native-smmu-provider读取真实NativeAdrenoSmmuService/Context、GPU/GMU wrapper及ArmSmmu4K接口。核心要求caller bank/ASID和真实电源/全局lease/故障处理/停止master；现wrapper固定IAS32/coherent_walk1、下2GiB、OAS cap40及Sheng五buffer，不是K80 provider。原Service只映射/发布也不证明硬件所有权，新代码不调用它。

针对本阶段集成角色读取原cached FDT，USER/LPAC/SECURE/GMU spec分别(provider253,SID0/1/2/5,mask0)，provider实际reg为base3da0000/40000和TCU3de6000/40。原NativeAdrenoBoard parseIommus只提SID，会丢第二mask；新纯描述适配器在调用原parser前严格核对同provider/2cells并拒绝未知或非零mask，保持失败不改输出。使用原reg/parser，不另造DT codec、不生成ArmSmmu4K可运行route。bank/asid/slot/OAS/power/stop/ownership/handler/runtime标志全0。

本地Xiaomi源码d9e81e6的QSMMUv500 Adreno实现确实复用Qcom context allocator；GPU SID0和LPAC SID1均进入0..2 bitmap范围，其他起点2。KGSL按context分别domain_alloc/attach后取bank，arm-smmu保存返回bank并在其owner内导出ASID。这是Linux分配策略，不是当前bank/ASID，不按SID猜分配。vendor ACTLR/TCU/TBU/安全aperture hook也不由通用architecture-register kit自动提供，原OEM参考不等于stock精确源码。

ASan/UBSan实际共用parser成功与21项描述拒绝/参数/别名、三源码突变拒绝通过；真实冻结Darwin23 XNU/IOKit配方新adapter+原parser独立对象全SHA一致，可重定位链接仅memcpy/stack保护导入，无native MMIO/service调用。这不是最终kernel/vtable/hardware资格。初fixture与现有XnuMemoryFixture全局名称冲突被编译拒绝，旧fixture/日志保留，改本地变量名而未放宽生产guard。

342当前输入/190归档、冻结255/raw231、原88GPU/default42保持，无手机探测/操作。下一项只离线核对QSMMUv500实际cfg_probe/init_cb与ACTLR/TCU/TBU/fault/power依赖，必要时实现真实类型的描述接合，不能由DT推硬件lease或选择bank。allow_boot=false。[证据](evidence/gpu-native-smmu-provider-2026-10-31.json)。


## QSMMUv500实际厂商消费契约核对完成（2026-10-31）

隔离out/zorn/gpu-qsmmuv500-contract绑定本地Xiaomi源和原缓存FDT。ACTLR表为id0/mask3ff/value32b，实际SMR subset消费匹配SID0..1023；它是设置选择规则，不能当四角色mask0路由的宽匹配授权。实际group拒绝冲突，init_cb按domain所有者的bank写ACTLR后flush。原Linux缺失/坏长度表返回0，本阶段不沿用为native配置成功。

缓存QTB为3de8000/1000、debugchain3dec000/1000、range0+1024、ports2，iova-width49只在所查ECATS诊断范围guard使用，不是实际IAS/OAS；TCU3de6000/40在所查create中是CONFIG_ARM_SMMU_TESTBUS条件映射。四个父clock、CX gdsc与子interconnect的真实phandle/provider已绑定。parent26个IRQ spec/global1、child未声明IRQ；这不等于故障处理已注册。实际power源要求interconnect/regulator/prepare+enable clocks及完成读，通用ArmSmmu4K不提供这些所有权。

两个具体返回值陷阱已核对：cfg_probe清CACHE_LOCK被secure权限阻止时只WARN仍返回0；context IRQ申请失败将索引置INVALID后仍可能发布pgtable ops/返回0。未来native必须分别确认真实访问和handler存续，不能据Linux return0/DT/callback0补成ready。无寄存器访问或新runtime调用器。

六个实际函数体在显式Linux OS/寄存器标量trace double下通过ASan/UBSan：2048 SID、mask/冲突/缺失/坏长度/分配失败及写ACTLR再flush、secure锁告警路径；两实际源码突变拒绝。另仅纯subset函数与原SMR字段声明用真实冻结XNU配方独立重编全SHA相同、无调用/导入/SIMD/initializer的可重定位目标注解；不是Linux完整ABI、可运行native provider、最终kernel/FD或硬件验收。342/190、冻结255/raw231、原88GPU/default42保持，无手机探测/操作。

下一项离线追踪实际三层IAS和USER/LPAC/GMU TTBR/IOVA消费到原native table API；必要时只实现有源依据的CPU配置准备，不按TBU49、SID或静态声明生成可执行硬件镜像。allow_boot=false，读回仍不合格。[证据](evidence/gpu-qsmmuv500-contract-2026-10-31.json)。


## Gen7页表地址边界已接合，inactive表准备仍待实现（2026-10-31）

隔离out/zorn/gpu-table-geometry追踪实际QCOM页表consumer，非误用通用io-pgtable-arm。缓存三层表选项在AArch64 S1中把IAS限制为min(真实va_size,39)，不是实际IAS/OAS；TTBR1 hook实际包括USER/LPAC，KGSL从真实TTBR1 cfg派生TTBR0并同时交两context，不能据此把两domain/bank合一。GMU是单独domain/no-stall/fault handler，低地址0x60000000和0xc0000000不是GPU upper地址。

固定453d8875两份此前缺失的kgsl_iommu.h/mmu.h已新取并单独绑定完整SHA，原manifest不改；sandbox DNS失败原记录保留，授权网络只取公开源码，无手机操作。实际split base1ff8000000000是GPU truncated49表示，_iommu_map_sg扩展为ffffff8000000000，QCOM map guard要求完整upper符号扩展。新ZornGpuNormalizeSplitGlobal只接受显式split-global、4K对齐/非零/不跨2^49范围，失败不改输出；拒绝canonical重复输入和低/GMU地址，无PA/分配/bank/ASID/route/权限。

复用原ArmSmmu4KBuild/BuildUpper及实际SG函数体double核对：512个upper39根槽、末页/low39/GMU低32及错误表示/extent/旧IAS32拒绝通过ASan/UBSan，两源码突变拒绝；合成PA/OAS40只是host标签，未生成native硬件context。另发现固定OEM guard-page consumer先复制addr再扩展gpuaddr，map收到旧addr而rollback用新gpuaddr；两个API条件分支均由原函数参数捕获确认，保留参考差异、不改OEM源、不称stock手机故障。

新helper和原table builder用冻结真实XNU配方独立重编全SHA相同，30递归输入绑定；可重定位链接仅stack保护导入，2个库内BR26和stack-fail边核对，无间接调用/SIMD/initializer。这不是最终kernel/FD/PAGE或设备ABI/所有权验收。原NativeAdrenoPrepareSmmuMemory会publishForDevice/holdForDevice，不宜用作CPU-only准备；下一步隔离实现只用原NativeMemory/原inactive builder的持有层，禁止发布/设备hold或靠policy补live能力。342/190、冻结255/raw231、原88GPU/default42保持，allow_boot=false，读回仍不合格。[证据](evidence/gpu-table-geometry-2026-10-31.json)。


## CPU-only inactive页表持有层隔离完成（2026-10-31）

新增out/zorn/gpu-inactive-tables/ZornGpuInactiveTables，实际复用原NativeAdrenoMemory、ZornGpuSnapshotNativeBacking、split-global边界和原ArmSmmu4KBuild/BuildUpper。每实例单次独占CPU表池，最多128页/8range/4096leaf；payload仅借用，真实caller须持续保留与独占，callback0不补硬件lease。输入/输出位宽仅显式policy，低地址不转换、upper39要求原truncated49表示；不选bank/ASID/slot或分配IOVA。

准备前后gate和实际getter检查单span/CPU映射/refs0/隔离/非WC，按真实PA+offset构造inactive range；不同owner间CPU/PA别名及表池对payload整对象别名均拒绝。同一owner的不同切片可用，排序/范围/permissions/cache字段仍由原builder严格核对。保留原allocation/snapshot/gate/build状态与attempt/mask/phase/未知cleanup信息；重复/reentry不重试，不提供release/reset，析构不释放。原allocator的零初始化/cache helper不省略；新owner建表后不publishForDevice/holdForDevice/改cache，未生成context/register镜像，也无可访问表映射的公开接口。

ASan/UBSan实际原NativeMemory+IOKit/cache double通过4成功形状（低/upper、8backing、同backing切片）、9 native/pool失败、9 gate时点、11初始参数与10range/backing/capacity拒绝；容量失败保留原零表，晚期失败保留已构建CPU表。物理别名放行与析构释放两实际源码突变均拒绝。host混合auto类型、low39根slot0错误假设、mutant输出目录冲突三fixture/driver错误原样保存；修正测试未放宽provider。hostPA不是真DMA/手机证据。

8个真实冻结XNU配方目标（含原NativeMemory/NativeCpu/parser/snapshot/builder）各独立重编原始全SHA相同，348递归输入绑定；新provider仅import allocate/snapshot/normalizer/Build两入口，无publish/hold/release/MMIO依赖。constinit1496B持久对象无initializer，prepare局部stack208B不是全调用链/墙钟保证；22 kernel imports为可重定位外部依赖，非最终kernel/虚表/PAGE验收。当前CPU_PREPARED仅表示编码完成，尚未整合原table read-auditor，DMA/runtime/readback均false。下一项只用原AuditTables/TableMemory读真实私有pool做CPU静态审计，不能重建参考表代替。342/190、冻结255/raw231、原88GPU/default42保持，无手机探测/操作，allow_boot=false。[证据](evidence/gpu-inactive-tables-2026-10-31.json)。


## 原CPU页表图审计器已接入inactive持有层（2026-10-31）

在新out/zorn/gpu-inactive-table-audit独立修订，不改上阶段源码/SHA。实际ArmSmmu4KBindTableMemory绑定私有NativeMemory表池CPU映射，原AuditTables按原ranges/result/root直接读取描述符；无重建/参考/影子表或新walker。调用者显式给1..65536读预算；可达表页每页全部512槽均查，未引用备用页不在图审计范围，两份scope控制明确该限制。

审计前后分别复用真实snapshot检查payload及表池的owner/CPU/PA/bytes/epoch/span/refs/cache身份；变化或gate错误保留原错误/阶段/mask。只有图审计和两轮身份复核、最终gate全过才置audit_complete，原raw读数/失败描述符/status另保留。原分配/cache helper不省略，仍不publish/hold/生成context或硬件镜像。CPU身份比较不能发现未持有lease的写者改后恢复，真实稳定独占仍是前提，不能据callback0补硬件所有权。

实际NativeMemory/原auditor+TableMemory在ASan/UBSan通过4原成功形状、9分配/pool失败、22gate时点、13初始参数和10range/capacity拒绝；另12实际表损坏（上下区各六类）、4前后payload/pool身份变化均拒绝，1535/1536读预算边界通过。放行真实audit失败、忽略身份变化两实际源码突变拒绝。无手机探测/操作。

12个真实冻结C/C++配方对象各独立重编全SHA一致、437递归输入绑定；新provider实际Audit/Bind/Build/normalizer分支及snapshot两对PAGE、原CPU reader一对PAGE核对。原Audit整TU未使用的Observe入口由原Program/Context闭合，未给其硬件config或调用它；新provider无MMIO/Observe/Program导入。constinit1792B无initializer，prepare272B/recheck176B/原walk每帧112B只是局部stack，非全链或墙钟保证。22 kernel imports仍是可重定位依赖，非最终kernel/虚表/全PAGE/FD/FAT/ready或弱内存验收。

CPU表图审计完成不代表设备可见性、SMMU运行、DMA或渲染；runtime/dma/readback保持false，allow_boot=false。342/190、冻结255/raw231、原88GPU/default42保持。下一项转尚未闭合的真实power-transition消费/精确Clock used-slot ABI，只离线绑定且调用关闭，不重复已完成查询或重抽FD模块。[证据](evidence/gpu-inactive-table-audit-2026-10-31.json)。


## 电源vote实际used-slot绑定及关闭调用的请求配置完成（2026-10-31）

隔离out/zorn/gpu-power-transition-binding复用已归档ClockDxe53c18，不重抽/执行。EnableClock/Disable槽2/3（offset16/24）与PowerDomain槽11/12（88/96）分别共用151c/1560 wrapper；真实kind1走5178/4034，CX kind2走6b34/454c，未误用kind3。原头1.0.9/实际1.0.a差异保留，仅这些新used slots及实际原型绑定。原生方法有模式位直接返回0的路径，未观测模式值；成功返回不能当作电源/时钟改变。头的client vote/不递归计数语义不补共享资源所有权，provider更深层状态/计数不夸穷尽。

固定OEM新增kgsl_pwrctrl.c完整SHA单独记录；CX consumer含completion等待、regulator enable和MMU TLB hint，wait timeout告警后仍尝试enable；disable也有hint/completion步骤。GMU enable-clks先RDPM更新、GMU/HUB设频再bulk prepare_enable，后续才AHB timeout。几项UEFI方法不能替代完整Linux顺序，未沿用5秒Linux等待为新门槛，未按参考频率选择rate/OPP。

新ZptRequest224B只准备一个不可调用vote描述符，保留原resolver160B完整raw64标量report/ID/status；严格成功形状、固定版本、kind/high32/重复ID及软件preEBS scope。没有协议指针/频率/自动顺序或rollback；invoke_allowed/attempted/status_available/prior_vote_owned/runtime全0、缺失providerff。report形状/软件scope不是live/EBS owner证据，不存在执行入口。

ASan/UBSan通过6操作/资源组合和29拒绝，开调用/放Darwin两实际源码突变拒绝；四个实际binary槽/branch/模式位语义破坏均拒绝。真实固件配方request与ABI注解在相同输出位置独立重编全字节SHA相同，无元数据归一化；52递归输入绑定，4实际slot和5头原型检查，ABI调用wrapper不链接/执行。实际SDK无入口链接闭合，非新FD。初source前缀/缺UINTN类型、nm格式检查和SDK缺memmove均先拒绝并保存；结构赋值改显式不重叠memcpy，复用原声明头和真实CompilerIntrinsicsLib，无pass stub或强制未解析。candidate只导入memcpy/memset且无间接native调用。

电压/corner、RPMh/CommandDB、共享vote/真实power/access/stop及可读保护诊断仍缺，readback=false/allow_boot=false。342/190、冻结255/raw231、原88GPU/default42保持，无手机探测/操作。下一步离线跟踪真实gen7_build_rpmh_tables/command-DB数据消费，不猜opaque协议方法/level或发送vote。[证据](evidence/gpu-power-transition-binding-2026-10-31.json)。


## 真实RPMh consumer及ARC离线准备完成（2026-10-31）

固定453d8875目录定位到实际adreno_gen7_rpmh.c，完整SHA256与目录Git blob SHA1双核对；不冒称小米stock精确源。真实gen7_build_rpmh_tables先DCVS再BW，准备供GMU/HFI消费的数据，不是UEFI RPMh直接发送顺序。ARC资源gfx.lvl/cx.lvl/mx.lvl；原u16计数保留初始0、在nonzero→0截尾，packed word为VLVL16/secondary index8/primary index8。真实secondary取首个足够档或最后一档，最后档低于primary也成功，不能改写成相等/足够证明。

新隔离ZornGpuArcPrepare直接复用原结构、ARC宏、计数loop和dependency函数原字节，仅增加CPU输入边界：显式available/status、raw64非零拒绝、偶数长度2..512、首0递增/尾0、256索引界与本地16请求容量，后两者不是liveGPU能力。160B report保留成功来源尺寸/状态/计数/request/vote及secondary-below-primary mask；失败输出原样，原错误留输入，不造EFI错误。没有协议指针/查询/地址/频率选择/发送，invoke/attempted/hardware_verified/runtime恒0；没有将cached DT频率补造成真实CommandDB数据或实际K80 vote。

BCM真实资源SH0宽16、MC0宽4、ACV fixed、CN0宽4；8B AUX是LE32unit/LE16width/U8vcd/reserved，按原逐步取整/最小1/14bit饱和及相邻VCD提交。实际OEM部分ARC/BCM查询未检查ERR_PTR/长度/unit0，单独记录不执行坏地址、不称stock故障；本地cmd-db只做NULL/magic等consumer检查，不包装成通用CRC/损坏数据库验证器。Cached DDR/CNOC及所有bin描述绑定，尚未选live bin/OPP。

ASan/UBSan全部65536个u16请求、48项失败不改输出、255边界/16批量/零档/非对齐AUX/别名通过，开启调用和忽略rawstatus两源码突变拒绝。实际固件recipe51递归输入、独立对象全SHA一致，真实SDK无入口通用count注解PE闭合；最终5个SDK调用/完整B-BL目的及rawstatus branch/160B copy/invoke-zero检查，三个真实PE破坏拒绝。只导入memcpy/memset，无native间接调用/SMC或新initializer；不是新kernel/FD/完整条件CFG或墙钟/全栈证明。初sign-compare告警与最终auditor寄存器/regex误判均拒绝且保存，未改真实provider。

342/190、冻结255/raw231、原88GPU/default42保持，allow_boot/readback=false，无手机操作。机主同时提示houji更新，隔离核对c4d962f后继续真实BCM纯CPU准备；不pull覆盖冻结参考或活动源。[证据](evidence/gpu-rpmh-commanddb-contract-2026-10-31.json)。


## 机主提示houji新发布已核对，更新参考结论（2026-10-31）

新公开commit c4d962fb22babc434c73d4e1d00147710ab255ec比冻结d4fb1472多1提交（10月30日15:36Z）。比较API只含前300文件，另取未截断2622项/2205blob整树；隔离读取23份有效源码/说明/依赖锁，Git blob+SHA验证，22份另与发布清单相同。原UniXNU-houji/旧reference和manifest不改，没有pull或执行下载脚本。

本次发布已有有效kernel/uefi/bootloader/graphics覆盖层、固定依赖和r222基线；当前README/known-issues报告真实提交/写回/完成同步及实验性桌面渲染，同时明确掉帧、黑屏、紫色/文字问题、热保护未验收和SCM间歇停顿。因此旧参考“houji CP/fence/Metal未完成”结论仅保留为旧快照历史，不能继续用于新提交。作者报告不是本项目独立真机验收，K80渲染/Metal仍未启用。archive/gpu-progress停在旧r170，不覆盖当前r222说明。

真实路径仍Darwin22/XNU8796/iOS16.7.16 d22ap；ABI不能直接套Darwin23。新增ZAP预约/GCD/metadata/PAR/SCM guard、持久owner/VM/submit与Metal桥接有参考价值，不代表本机权限。HFI生成器明确绑定houji AOP c572b184及固定偏移，live_command_db_verified=false；不能复制rail/vote/BCM地址当K80数据。新发现本地既有K80包aop.mbn334912B SHA4eef99e6、aop_devcfg25128B SHAd5ea30f1；前者确有ARC/BCM名字，当前只核对文件/名字位置，未解析表/选择variant，不当安装版本或live证据。下一离线计划从K80实际字节及原有有界reader/真实consumer追踪，禁止沿用houji偏移。

保留刚完成的ARC65536/48/2源码突变/3PE突变及342/190/255/231/88/default42保护证明；allow_boot/readback=false，无手机操作。[更新核对证据](evidence/houji-update-2026-10-31.json)。


## K80实际AOP静态注册与ARC/BCM包数据已绑定（2026-10-31）

新隔离out/zorn/gpu-aop-commanddb读取既有K80原厂包aop.mbn334912B/SHA4eef99e6，实际RISC-V32 ELF，非ARM64 GPU可执行物。复用LLVM23 ELF reader核对11段与文件边界；code5按真实FileSize取片，用LLVM objcopy生成不执行的注解、dump回原字节全相同，未造新ELF decoder。Xcode工具缺RISC-V和原full synthetic反汇编遇非file-backed尾部的错误均保留，不当手机故障。

由实际AOP指令而非houji偏移推导：code5+3f6/408/428均到+5c30，实际VA81c21c30/file36c30。两条真实分支绑定ARC header/AUX28项448B、MOL14项28B及共同BCM31项248B；注册函数24Bentry/16Bheader/实际拷贝参数核对，三份实际binary指令突变拒绝。selector调用者语义/当次分支未知，不选liveSKU；所有记录保持两份。相关gfx/cx/mx的两份raw32B/address均相同，不凭同SoC猜兼容，MOL也不当level。

实际包gfx.lvl为0/52/56/60/64/80/128/144/192/224/256/320/384/416/432；cx/mx均0/16/64/128/192/256/320/384/416/480，仅VLVL数据非MHz。BCM实际MC0为50000/4700000/16/vcd0，SH0为50004/4800000/64/vcd1，CN0为50030/140000/4/vcd5，ACV为50068/1/0/vcd12；这些resource地址不是PA/MMIO访问权限。实际AOP在runtime构造DB header/magic，未伪造一个live DB来调用Linux consumer。

新552B ZaopPrepared只在原NativeAdrenoSha256完整固定SHA匹配后CPU复制两组3rail及4BCM的ID/rawAUX/address/长度；不是generic parser。FILE1、selected variantFFFFFFFF，invoke/native-status-available/runtime/liveDB/hardware-ownership恒0；文件输入没有造EFI成功或原生状态。ASan/UBSan10实际资源/58失败不改输出及3源码突变拒绝；真实固件recipe两个对象独立同输出位置全SHA一致，54递归输入、实际Linux24Bentry/16Bheader/144BDB及OEM8Baux布局与typed552B接口编译通过。ABI首版缺stddef的拒绝保存并仅修注解。

真实SDK无入口PE闭合；最终10copy calls、全部B/BL、readonly SHA PAGE pair/32B compare-reject/552B zero-copy/unknown-variant+invoke0配对store核对，3实际PE突变拒绝。无间接hardware/SIMD/导入/TLS/新可写存储；其他PAGE/参数CFG/dataflow仍链接器契约，非最终kernel/FD或live协议/执行资格。

342/190、冻结255/raw231、原88GPU/default42保持，无手机操作。静态资源数据缺口已缩小，但liveDB/callable RPMh-CmdDb ABI/真实power-security-stop-SMMU-DMA/readback仍缺，allow_boot=false。下一项只复用真实OEM BCM计算做有界CPU准备，不拷houji策略/选择live频率或发送命令。[证据](evidence/gpu-aop-commanddb-2026-10-31.json)。


## 原厂BCM逐步计算的CPU准备完成（2026-10-31）

新隔离out/zorn/gpu-bcm-cpu-preparation复用固定453d8875 bcm结构/tcs_cmd_data原函数和VCD wait-mask原loop，以及本地实际Linux TCS宏；没有新codec/替代wire算法。保留ab*width/buswidth先取整再*1000/unit、独立ib、非零最小1、14bit饱和、相邻VCD/末项commit及fixed ACV分支。do_div兼容层仅保留原函数使用的无符号quotient，丢弃的余数未造用途，little-endian字段含义不改。

新956B ZbcmPrepared内部真正调用原ZornGpuPrepareAop重核完整固定SHA文件，保留552B FILE来源/两ARC变体；按实际8B AUX取得unit/width/vcd及原资源地址。Mandatory显式8B policy（vote<=3fff，FromLevel<=DDR count）不自动挑K80频率/corner，也不沿用houji阈值或OEM默认。输入AB/IB原值保留，支持不相等；DDR1..16、CNOC0..2容量绑定原kgsl_gmu_core.h SHA560027df，CNOC0是明确省略。输出只有unframed CPU数据/地址/计数/waitmask/policy，没有HFI header/序号/queue或provider指针；invoke/native-status/runtime/live-data/ownership恒0。

ASan/UBSan通过cached DDR10/CNOC2、11显式阈值、8192私有原函数算术样本、8VCD模式、逐步舍入/最小1/饱和/AB-IB/fixedACV/最大容量及CNOC省略、16计数失败不改输出和额外别名拒绝；开启调用/放宽policy截断/除法改向上取整三实际源码突变均拒绝。这些是纯计算检查，没有mock成功EFI或GPU所有权。

真实固件recipe新BCM+原AOP+原SHA三个对象独立同路径全SHA一致，57递归输入和原source/macro/header额外pins闭合；8参数typed API/8Blevel-policy/956Breport+invoke offset936注解双编一致，真实SDK无入口PE链接通过。最终4UDIV/2MUL及1000/3fff/14bit pack、policy高位拒绝、只读SHA PAGE pair/956B zero-copy/invoke0，以及两个tcs/两个waitmask调用和全部B/BL核对。四实际PE破坏分别拒绝；无导入/TLS/新可写存储/间接hardware/SIMD，其他PAGE/参数CFG仍链接器契约，非新FD/kernel/墙钟或完整栈验收。

342/190、冻结255/raw231、原88GPU/default42保持；无手机探测/操作，allow_boot/readback=false。下一只离线接实际pwrlevel/bin/DCVS源码到文件化CPU模板，保留全部bin与未知选择；不重复旧ARC/HFI/CPU/GUI/memory轮或发送命令。[证据](evidence/gpu-bcm-cpu-preparation-2026-10-31.json)。


## 原厂DCVS四个cached bin的FILE准备完成（2026-10-31）

隔离out/zorn/gpu-dcvs-file-preparation复用实际453d8875 setup_cx/setup_gx/to_cx计算体，只替换3/4条device→CPU数据绑定和signature，dev_err只去日志；无fake Linux device/provider/owner。原依赖/count函数复用，不重跑旧65536 ARC。实际packed opp_gx12B/opp8B、gen7_dcvs_table424B，以及原core的32GX/4CX/GMU2容量均绑定，不据32内部容量选择HFI版本或套旧16项packet。

原adreno.c按reg索引、跳零频点、默认CX FFFFFFFF；cached所有index连续/频率非0/voltage<=u16，拒绝洞或截断。实际selector依赖speed_bin/SoC feature-pcode/sku-codes、首次命中与SKU0 wildcard，全部保持未观测。完整保留四bin的12/14/9/12项、speedbin present/4及1/4/1/1 SKU、原initial11/13/8/11；bin1源描述含1GHz，不当实际运行频率/选择策略。GMU原DT两个frequency/VLVL pair为260MHz/64、625MHz/128，不用源码default补造。

新4864B FILE准备真正重核AOP完整SHA，并保留552B来源、两AOP变体、4bin rawHz/voltage/CX及metadata、8份实际424B表和cachedDT SHA8c3712d8。原zero-entry、GPU倒序、Hz/1000 floor及缺CX sentinel（含追加零档）全部保留；GMU0+2及原dependency计算。SelectedBin/AopVariant均FFFFFFFF，invoke/runtime/live/native-status/ownership恒0；无protocol/header/queue/发送或原生rate/corner选择。

ASan/UBSan4×2变体、94GPU非零/24GMU及零档/unused零/metadata、7个新CX/floor/capacity边界、9失败不改输出及别名通过；开启调用/造选bin0/改GPU除数100三实际源码突变拒绝。真实固件recipe3对象同输出路径独立全SHA一致，60递归输入，packed424/1056/4864B和invoke offset4844/API注解双编相同；真实SDK无入口PE闭合。最终3个1000除法、zero/reverse/CX sentinel、capacity32、两dependency调用、两只读SHA PAGE pair、4864zero-copy/未知选择+invoke0及全部B/BL核对，四实际PE破坏拒绝。没有硬件/SIMD/导入/TLS/新可写状态；其他PAGE/CFG仍链接器契约，较大局部stack不当正常firmware caller/完整stack或墙钟验收。

初packed结构提取过宽、原ARRAY_SIZE重定义、mutant输出路径目录冲突均先拒绝且日志/源码保留，修注解/fixture未改原provider算法。初source-pin fallback在资格前改为必须匹配旧manifest键，无放宽SHA。342/190、冻结255/raw231、原88GPU/default42保持；无新kernel/FD/手机探测操作，allow_boot/readback=false。下一只做一次有界FILE组合/真实静态闭合并明确live provider/caller/readback边界，若下一具体步骤必须手机则按离线授权暂停，不再扩协议或重复旧试验。[证据](evidence/gpu-dcvs-file-preparation-2026-10-31.json)。


## FILE准备接合与真实SDK最终审计完成，停在live平台资格边界（2026-10-31）

隔离out/zorn/gpu-offline-composition用原实现接合AOP/BCM/DCVS，5820B结果直接含956B BCM与4864B DCVS，未加协议、owner token、native状态或默认policy。显式BCM参数原样传递，先BCM再DCVS，真实软件错误原样返回；失败不修改输出，完整输出区与全部输入别名在首consumer前拒绝。两份552B AOP来源逐字节一致且FILE/version/unknown选择及所有invoke/runtime/live/status/ownership门必须关闭；不因数据组合成功就允许硬件调用。所有cached bin/AOP变体保留，测试perfmode5/from2不当K80实际policy。

新组合ASan/UBSan核对完整结果与两真实组件相同、23项错误/数据不一致事务失败（19个来源/门/选择变化）、5个完整输出区别名及参数/count溢出拒绝、显式CNOC省略/never policy；host注入只在真实组件执行后改变软件返回/数据，目标链接无shim。去后半区别名/吞原错误/忽略来源分歧三实际组合源码突变拒绝；旧8192/65536/DCVS等套件未重跑。真实固件recipe五个原组件同路径独立LTO对象全SHA一致、65递归输入，552/956/4864/5820B与956偏移/8参数C ABI独立编译；实际SDK无入口PE闭合。最终552B来源比较循环/偏移、完整alias门、fileOnly两调用、组件关闭门、5820B zero-copy、两只读SHA PAGE pair及全部B/BL核对，四真实PE破坏拒绝。原BCM4+DCVS3个整数除法保留，无导入/TLS/新可写状态/间接硬件/SIMD；其他PAGE/CFG仍普通链接器契约，局部11232B frame并非完整栈或真实线程/墙钟资格。

目标首次因选定CRT无memcmp声明拒绝，改有界字节比较而不造库符号，原记录保留。独立ABI COFF出现真实timestamp字节差异，保留两原文件/除timestamp外一致，不宣称metadata消费者等价；不同PE输出名会改导出目录和下游布局，原失败保留，修为同一路径重链接后只差实际timestamp。原像未归一化/改时间/改编译flags；资格不靠恰好同秒。

platform-boundary.json逐项绑定真实源和既有证据：当前GCD/保留区所有权、SCM metadata可见性与AUTH_RESET解复位、shared power vote/状态、QSMMUv500 bank/ASID/路由/stop与DMA均未由FILE提供。NativeAdrenoService仍走Sheng commandDB/ColdStart，旧GmuPlatform假设五已供电窗口，SmmuContext仍IAS32/coherent_walk1；不是新K80执行caller。UEFI callable生命周期不能跨EBS移植Darwin23。原84text+完整272B及payload前错误仍无合格读回，未扩codec/环。没有可启动候选、最终FD/kernel/规范负载或硬件资格，GPU/Metal仍未启用。

本次仅结束有界FILE准备接合；不宣称所有GPU离线工程完成。下一语义验收必须对照当前真实平台所有权/状态，而本聊天仅授权离线、禁止探测；按机主指令保存明确边界并请求工具暂停k80-unixnu，不要求本人连接/按键等物理动作。后续原生provider/caller集成仍缺，不能用host owner模型补造资格或拿旧轮试启动。allow_boot/readback=false；342/190、冻结255/raw231、原88源/default42保持，无任何手机操作。[证据](evidence/gpu-offline-composition-2026-10-31.json)。

automation_update已返回PAUSED，且实际automation.toml再次核对同值；current现指向新pause.json和platform-boundary.json。历史pause.json不改，allow_boot/readback仍false，无手机探测或物理动作请求。


## 机主在旁恢复调试；实际recovery来源闭合与native介质身份加固（2026-10-31）

机主明确“手机已接入rec，继续适配GPU驱动，我在旁边可以辅助”，覆盖之前仅离线/暂停；历史pause.json不改。只对92988a43确认recovery/zorn/slot b/TWRP3.7.1_16。沙盒首次拒绝本机ADB listener，隔离权限下固定序列号身份读取通过，不当手机故障；无重启、flash/BCB/GPT/Data/OS写入或GPU访问。旧CPU/GUI/内存名额仍消耗，不重跑。

当前b槽AOP分区sde31为524288B，其中前334912B与离线包AOP4eef99e6完整文件SHA完全一致；这将FILE来源绑定到实际分区前缀，不等于整分区hash/签名/已加载AOP或选中variant。当前FDT900407B、SHA dfafb7be，与旧8c3712d8整文件不同；实际GPU/GMU及SMMU子树逐节点/属性比对相同，两份来源身份分别保存，不把旧manifest换成新hash。

复用原prepare-zorn-data-store.py的gpt函数，只提取解码体不执行其main，实际读取主/备GPT并核对header/entry CRC、表字节一致、sda34 userdata3112704..64049146。真实分区unique GUID为cc6ddf0b-0ed0-d42e-76e4-cd44c1a849f4，type GUID1b81e7e6-f50d-419b-a739-2aeef8da3335；它不是原Data文件系统UUID C7D77FF3...。原日志relative2291712/absolute5404416的当前几何闭合，无写权限或UEFI路径/介质句柄推导。

隔离staged原ZornCheckpointIdentity只新增两个真实EFI_GUID常量与精确type/unique比较，保留原native类型/1888B报告ABI/方法trap。即使HD签名和PartitionInfo自洽，更换任一GUID字节仍拒绝；32字节扰动及把DataUUID当分区GUID共33拒绝通过，原raw64错误/重复使用不回归；去unique/type检查两个实际源码突变拒绝。真实固件recipe新selector独立完整SHA相同，46递归输入，实际SDK依赖/旧closure对象明确逐SHA绑定复用，非freshFD/kernel。最终只读GUID PAGE pair/16B CompareMem两个真实目标与拒绝分支、write/live/GPT门0核对；三实际PE破坏拒绝。scope仅selector，SDK DebugAssert/旧closure不是live caller或墙钟证明。descriptor eligible仍不准LiveDiscovery/GptRead/WriteAuthorized，recovery已读GPT不能冒充未来UEFI现场验证。

Recovery当前无/sys/class/kgsl/kgsl-3d0、无kgsl/msm_kgsl已加载模块；已有arm_smmu和msm_drm，不能当GPU/SMMU空闲或Darwin lease。AB/pcode1/SoCID557是真实sysfs文本；按固定参考consumer与enum仅能投影bin3（AB不使用pcode），不是实际运行档位或频率，未读speedbin且所有runtime选择仍未知。exec-out在缺路径时host返回0且错误在stdout，已显式判不可用；debugfs无节点不挂载/补零/重试。无module autoload或SMC/PAS/power/MMIO/SMMU调用。

342/190、冻结255/raw231、原88GPU/default42保持，allow_boot/readback=false。下一只追真实归档UFSDxe的parent/child DevicePath构造/used-method身份，再形成最小真实Gen7-9-1 provider/caller；不把Linux sda34当UEFI handle/MediaId或写授权，不扩query codec/日志载体。任何新候选仍须canonical build/finalkernel/currentstart/FAT/menu/ADT/input/archive/ready及独立WDT/freshBCB/readable失败保护闭合。恢复自动续调时以上新授权/当前计划优先旧离线提示。[证据](evidence/gpu-recovery-resume-2026-10-31.json)。

automation_update与实际配置均确认k80-unixnu已ACTIVE；原独立caffeinate -i任务恢复，无关机计划。当前未arm手机watchdog/BCB且allow_boot仍false；机旁协助不替代native/provider/保护资格。


## 真实归档UFSDxe路径绑定，修正standard-UFS假设（2026-10-31）

新out/zorn/gpu-ufs-provider-binding直接复用已归档UFSDxe b8dfd16a、Partition8b269013、DiskIo27da79fa，不重抽FD、不访问手机。旧selector按standard MSG_UFS_DP/PUN0/LUN0筛选，实际上会拒绝所选UFSDxe的真实路径；之前host描述符通过不能作为live资格。原阶段和旧manifest完整保留。

实际UFSDxe3fbc..3fdc复制20B hardware vendor模板与1a200+16×LUN GUID，3ff8..4020写4B EndEntire；path步长24、GUID步长16，41cc通过BS148安装DevicePath，传入exact path。8个GUID与实际QcomPkg.dec逐值一致，LU0为860845c1-be09-4355-8bc1-30d64ff8e63a。不是看到“UFS”名字就放行vendor或把Linux sda34映射成UEFI句柄。实际Partition append2744→6910→686c→678c在67ec减原end4B，附加42B GPT HD/End，实际GPT header0401/types0202与144B PartitionInfo复制/安装另核；父24B/child66B由真实consumer链得出，不是通用devicepath兼容承诺。SDK Partition源码仅解释性参考，不冒称OEM二进制精确源。

实际父BlockIO template1e358 revision2001f，Media8/Reset16/Read24/Write32/Flush40及14dc/14e4/15a4/1664入口绑定；Reset14dc直接mov0/ret，成功不证明复位/停止。DiskIo template8130 revision10000、Read192c/Write19bc及真实安装核对。实际头/配方独立编译vendor20/HD42/report1888/BS148、Block/Disk slots和四种原生read/write原型；只确认used prefix，不声称整尾、完整内部算法或墙钟。

新隔离staged selector保留上一阶段current partition unique/type GUID与原native类型，只把path gate改为精确LU0 vendor20/父24/child66，无标准UFS、额外prefix、其他LU、controller/RPMB fallback。1888B报告不变，descriptor eligible仍LiveDiscovery/GptRead/WriteAuthorized0；不枚举/调用协议、不保留指针、不执行任何I/O。新47项path/parent/旧标准path/当前分区拒绝及raw64/reuse控制通过，所有协议trap0call；删除LU0或parent-prefix两实际源码突变拒绝。真实固件recipe新对象独立全SHA一致、47递归输入、旧真实SDK closure显式复用并SHA绑定，不称freshFD/kernel。四份原provider副本改坏GUID/stride/append-end/DiskIO入口均被语义检查拒绝；最终selector三实际破坏也拒绝。最终只读LU0 PAGE pair/16B compare、20B parent compare、24/66长度、全部selector B/BL和权限零store核对；其他PAGE/CFG仍普通链接契约，SDK DebugAssert/旧closure不是live caller或完整栈/时间验收。

342/190、冻结255/raw231、原88/default42保持。无手机操作、无新FD/kernel/boot/BCB，readback/allow_boot=false；不扩query codec/载体/环。下一只准备真实pre-EBS只读介质/GPT verifier，用actual EFI GPT/CRC/原始status和真实EBS gate，不能继承recovery的GPT成功或构造owner；新候选仍须所有规范build/ready/保护闭合。[证据](evidence/gpu-ufs-provider-binding-2026-10-31.json)。


## 真实pre-EBS只读GPT verifier源码与目标静态闭合（2026-10-31）

out/zorn/gpu-readonly-media-verifier新增真实类型的ZornCheckpointReadOnly，代码仅调用parent BlockIO.ReadBlocks四次及BS CalculateCrc32四次；raw64 status、attempted/returned/CRCavailable/首个本地错误与operation完整保留。任何native错误或非零warning停止且不解释buffer，不造ReadBlocks不存在的返回字节数。无Write/Reset/Flush/分配/挂载/GPU/SCM调用，不新增query wire/carrier/日志格式；实际固件尚未执行这段代码。

从旧真实生命周期实现提取event-only owner，保留CreateEventEx/Before-EBS/EBS release锁存/partial handle/单次关闭，去掉Clock/RPMh/CommandDB resolver并核对精确源变换。正常串行pre-EBS caller、有效稳定typed对象是前提；每次native读/CRC前后查真实latch/epoch与父子MediaId、全部media字段及指针身份，in-flight无法取消。持久context保留所有错误buffer与可能callbacks，无析构释放/重试，只有显式retire关闭已知event。新接合另外拒绝create_attempted!=created时的安全retire成功：成功+NULL、错误/warning+NULL即使returned==closed0也不能当全部清理。旧GPU/query owner及历史报告不改；首次原始native错误不被cleanup覆盖。

直接使用真实EFI packed GPT92B/entry128B和native CRC，复用原固定设备签名/rev/header/count<=256/entry128/primary2及有界backup校验语义，再核对current disk GUID/LastBlock、双header互指/可用范围、两表CRC及字节一致、唯一userdata/当前unique+type GUID/完整128B PartitionInfo。前后重跑真实selector，不继承recovery GPT成功。实际header只有64项/8192B，但backup区预留16384B、条目始64049147而header64049151；初版按used长度相邻的假设被真实fixture拒绝，改原有界after-LastUsable/before-header位置，不改旧SHA/手机。CRC校验不是认证或任意并发原子证明，平台的native ReadBlocks/CRC契约仍需真实caller。

私有77824B/4096对齐persistent owner含两份4Kheader和32Ktable，160B报告仅标量。GptReadVerified只在该运行调用实际全过后置1；host double的1只表示软件测试，绝非当前手机native资格，也不是跨epoch lease。LiveDiscovery/WriteAuthorized/RuntimeComplete始终0。显式retire后或expiry的报告保留历史数据/expired状态，不准后续native访问。UEFI指针不交给Darwin23。

ASan/UBSan新8真实形状native错误、8正warning、8在途EBS失效、10父子media值/指针变化、12 GPT/CRC/entry破坏、10event/partial/NULL/close及额外2native错误+expiry同时发生、重入/once/参数/别名通过；成功4read+4CRC/2event后显式2close，write0。4个实际源码突变拒绝，未重跑旧无关套件。真实固件recipe三对象独立同路径全SHA一致、53递归输入；native GPT92/128、BS158/170/70/BlockRead24及owner4096对齐注解通过，真实SDK noentry链接，原SDK closure明确逐SHA复用、不是fresh完整FD/kernel。constinit属性强制owner零初始化；目标sizes77824/4096/160/160/88。

最终实际Read24/CRC158/Create170/Close70间接边、raw64存储后严格零判定及前后gate、单release STLUR回调、diskGUID只读PAGE pair、77824B可写初始零owner、160B标量copy、只设GPT成功与未知event-retire拒绝分支核对。6个实际PE破坏（Read→Write、warning放行、删除release、成功改写权限位、NULL-retire绕过、BSS不可写）均拒绝。同输出路径独立重链接仅差保留的PE timestamp，不归一化原文件、不声称metadata消费者等价；其他PAGE/CFG/SDK DebugAssert仍链接器契约，不是完整栈/墙钟/ARM弱内存或任意指针认证证明。

首次C/C++ linkage/fixture初始化Werror、backup位置错误源码/日志均保留；修真实ABI/数据假设，不当手机故障。342/190、冻结255/raw231、原88/default42保持；无本轮phone/boot/BCB/kernel/FD操作，allow_boot/readback=false。下一只做真实有界Handle/protocol discovery与默认关闭的pre-EBS caller，不能传host成功/合成句柄，不能扩query载体或借旧CPU/GUI/内存轮试启动。[证据](evidence/gpu-readonly-media-verifier-2026-10-31.json)。


## 有界真实UEFI发现与只读调用方静态闭合（2026-10-31）

out/zorn/gpu-native-media-discovery新增默认OFF的真实类型调用方：一次LocateHandle(ByProtocol,BlockIO)、512个persistent handle/4096B容量，无分配/扩容/重扫/ConnectController。原raw64返回值及原UINTN required/returned size先保存再严格零判断，BUFFER_TOO_SMALL不重试、warning不当成功。逐handle实际BlockIO/DevicePath返回状态和available分开保存；从同一真实inventory中找唯一24B vendor-LU0父路径与66B当前GPT子路径，再取得真实PartitionInfo/DiskIo、复用原selector和只读GPT verifier。NULL/重复handle、接口别名、缺失/歧义/任一查找失败明确不可用，不拿Linux sda34/recovery GPT或caller-success补UEFI handle/MediaId。

组合审查发现原双事件owner独立注册仍有窗口：outer先收到EBS、inner刚注册，或inner CloseEvent期间outer失效。新隔离reader/lifetime derivative在每次读/CRC及嵌套注册/关闭前后同时查真实typed outer owner和inner latch。实际parent对象通过prepare/close原生C++参数传递，root无parent；没有host成功callback/虚构lease。成功路径4event、显式inner先outer retire；未知partial/NULL/native close错误保留context，不析构回收/重试。旧只读/查询阶段源和manifest不改，修订前组合source/target/log保留；parent-only注册/读/关闭失效专门控制通过，删除三处parent检查的真实源码突变拒绝。

所有实际protocol/media/path snapshot在verifier前后复核，路径walk最多32node/512B；合法稳定typed对象与串行handle数据库是前提，不是任意坏指针认证/任意并发原子性。caller无allocator，但实际所选SDK CoreHandleProtocol以DXE-core agent调用CoreOpenProtocol，可遍历list、AllocatePool或增加OpenCount；未发明对不属于自己的agent的CloseProtocol。LocateHandle即使buffer不足仍遍历数据库计算required size。有限调用次数不是服务内部分配、完整栈或墙钟上限；解释性SDK源码不冒称整个归档DXE二进制精确源码。

target owner524288B/align4096、局部scalar报告104B/每handle48B；不发布UEFI指针给Darwin23，不修改272B query/ADT/日志/codec/载体，原1888Bselector报告保持。DiscoveryComplete/GptReadVerified仅属该epoch运行观察；host的1不是当前手机native验证，LiveDiscoveryVerified/WriteAuthorized/RuntimeComplete恒0。源码未接入canonical driver入口/FD/kernel，allow_boot/readback仍false，无新boot/写分区/GPU执行。

ASan/UBSan实际GPT bytes+typed provider double通过16lookup错误/warning、15expiry、38无效/partial/close/参数控制，成功512handle/1026lookup及合法512B路径边界。常规成功1枚举/8lookup/4read/4CRC/4event、显式4close，write0；defaultOFF/reentry/once保持，7实际源码突变拒绝。真实固件recipe四对象独立同路径完整SHA相同、55递归输入；实际BS LocateHandle b0/HandleProtocol98参数/64bit状态和目标布局核对，constinit owner强制、真实SDK noentry PE闭合，旧SDK closure显式SHA复用，不是freshFD/kernel。

最终六种实际native间接边、raw64保存后严格零判定、ByProtocol/BlockIO/4096容量、默认OFF、typed-parent门、单release callback、4SDK GUID/pointer table、524288B writable zero owner、104/48B copy及GPT-only store与新B/BL目标审计通过，10实际PE破坏拒绝。同路径独立重链接仅差保留timestamp；未声称metadata消费者等价或全部PAGE/CFG/SDK路径穷尽。首次GUID宏自带分号导致编译拒绝、提取器continuation/一条callback注解错误均保留，修实际头/指令解释，不当手机问题。

342当前输入/190归档、冻结255/raw231、原88GPU源/default42保护通过。下一转实际已归档ClockDxe的GPU电源操作方法/ABI和固定consumer语义，做调用恒关闭的最小K80配置；不重复lookup-only resolver/UFS/GPT/旧CPU/GUI/内存轮，不扩query协议，不以host模型补power/security/stop/SMMU/DMA所有权。[证据](evidence/gpu-native-media-discovery-2026-10-31.json)。


## 实际调频/复位ABI与调用关闭请求完成（2026-10-31）

current上一项计划重提Enable/Disable电源投票，检查发现同日11:21的out/zorn/gpu-power-transition-binding已经完成；本轮核对其真实源SHA并复用纯shape validator，未重做旧套件或改历史报告。新增仅out/zorn/gpu-clock-rate-reset-binding的SetClockFreqHz/ResetClock绑定。

实际归档ClockDxe53c18：SetClockFreqHz槽6/48→1624→7fa8→kind1的5b30；真实头ResetClock在槽16/128→17cc→5f50。槽15/120是SetClockDivider→178c→80cc→kind1的5d14，不能把两个同样第三个32bit参数的操作混为一谈。首次新注解/test误认120，被实际offsetof输出拒绝，原脚本/记录/失败保留；候选始终从真实offsetof取值，未执行固件。头1.0.9/provider1.0.a差异和整尾未知保留，未扩大ABI承诺。Reset实际0/1/2通过c574分别assert/deassert/pulse，头明确destructive，需要重配，不是GPU停止或安全回退资格。

调频mode-bit3可zero-success且不写ResultFreq，实际5b30含kHz/MHz的32bit乘法、rate-plan选择和锁内更新；返回UINT32是选择频率信息，非测频或供电证明。Reset也可能mode短路，c574缺descriptor/backend/callback直接ret、上层仍可0；不能把SUCCESS当硬件执行。内部volt/vote/poll/完整调用链时限未验收，无provider调用。

新256B ZcrRequest保留原160B report和raw64 IDs/statuses/请求UINT64，复用原PowerVote临时shape检查但不发布为enable投票。仅GMU/HUB、4种Hz match和已知reset0/1/2；拒绝0Hz/>UINT32/kHz/MHz/CX reset/未知enum，不截断、不选择625MHz/200MHz默认值。InvokeAllowed/native attempted/status available/result available/ResultHz/runtime/prior vote/preEBS verified全0，missing ff；零status存储明确未尝试/不可用。无协议指针或native执行API，不将scope/report形状当真实EBS/硬件owner，不改query272B/ADT/日志/codec/载体。

ASan/UBSan30有效描述符/21拒绝、失败不改输出/源与4实际源码突变拒绝通过；仅软件输入，provider调用0。真实recipe两对象独立同路径完整SHA相同、55递归输入，旧SDK closure明确SHA复用；实际调频This+UINTN+UINT32+enum+UINT32*、复位This+UINTN+enum原型和8/8/4/4宽度、256B/Invoke224/method168/native184/source160布局通过。独立typed wrapper48/128仅注解、不链接执行。SDK noentry PE实际主函数的边界/48-128选择/160copy/256copy/InvokeAllowed清零、纯memory调用、无新间接native/SIMD/SMC/initializer核对，5实际PE破坏均拒绝；同路径重链接仅差保留timestamp，非完整FD/kernel或全部PAGE/CFG/SDK证明。另4份真实provider副本的slot/branch/kind/短路破坏均被语义检查拒绝。

342/190、冻结255/raw231、原88/default42保持。无phone/boot/写分区/GPU调用，allow_boot/readback=false，GPU渲染/Metal未启用。下一只追实际所选ClockDxe的GPU表/频率计划/voltage-vote关联和runtime选择边界，不重做投票/调频/复位绑定，不拿参考频率或host模型补硬件所有权。[证据](evidence/gpu-clock-rate-reset-binding-2026-10-31.json)。


## 实际ClockDxe GPU表、共享domain与运行选择边界（2026-10-31）

新out/zorn/gpu-selected-clock-plan只复用已归档53c18和旧有界PE reader，不重抽/下载、不执行或模拟固件。实际795c初始化经7998把BSP2bba8写到global35818，FILE原global为0；静态clock数组20368/count379/stride104、power-domain数组2ab38/count37/stride112，selected name/domain/rate/handler指针的DIR64 relocation另核。文件ImageBase0下的值是RVA，不是当前PA/UEFI指针/clock ID。

GMU name唯一绑定28f90→clock-domain30060，与gpu_cc_gx_gmu_clk共享；HUB CX INT29470→domain30130还被acd_ahb/ahb/crc_ahb/hub_aon四clock引用。CX gdsc在2b8c8。静态共享rate-domain关系不证明client vote或可以关闭其他消费者。

实际5404按domain+0/8取plan/count、stride56并先把entry+32交48bc筛选。GMU337e8共5项：19.2MHz、两项260MHz、两项625MHz；HUB33de0共3项：两项200MHz、300MHz。重复频率有不同原始hardware filter和+24字段，全部56B逐条保留，不按Hz去重或选当前。+24原始GMU[52,52,56,128,192]/HUB[52,56,128]不当微伏或Linux corner；16B筛选值包括范围形状和138比较输入，未核全信息协议类型/当前返回值，不用AB/参考625-200推导live资格。

FILE domain+56选中指针为0，实际55e8会更新它并处理锁/计数；49ec另有从backend信息分配/重建56B记录的路径，48bc涉及原生信息查询/c80c，初始化也读ClockLogDefaults/ClockStubConfig。因此本轮表不是当前频率/电压/variant/vote证明，也没有host模拟选择。真实EFIClock公开EFI_CLOCK_FREQ_PLAN_TYPE仅8B、nFreqHz0/eVRegLevel4，不能把它覆盖到私有56B记录。真实冻结recipe注解独立完整LTO SHA相同、49递归输入，AArch64注解[8,0,4,8,8]，无代码/导入、不链接执行；没有发明私有native struct或新增runtime解析器。

7份真实provider字节的count/domain/rate/filter/shared-HUB/selector-stride/selected-pointer语义破坏均拒绝，不仅靠原SHA；有界section/DIR64和selected consumer指令通过，其他CFG/PAGE/voltage/property/poll路径不夸全验收。无新FD/kernel/phone/boot/写分区或GPU/clock/reset调用，query272B/ADT/日志载体不变。342/190、冻结255/raw231、原88/default42保护通过，allow_boot/readback=false。

下一只做既有实际ZornBootMemoryDxe的最小K80平台配置caller隔离接合，默认OFF字节一致、真实EBS/原resolver和原inert request复用；未知rate/variant/vote必须拒绝准备，不从FILE目录填成功或默认频率，不改原query格式/保护顺序，不重复旧查询交接套件。[证据](evidence/gpu-selected-clock-plan-2026-10-31.json)。


## 实际平台caller关闭前快照与缺策略拒绝完成（2026-10-31）

out/zorn/gpu-native-platform-caller仅隔离接合既有真实C入口/Query/BootLifetime/Resolver。OFF与活动原cd4798逐字节相同，ON的C入口与已完成query-on完全相同；新hook在owner.close前复制真实160B resolver report，两次typed owner.check与实际EBS失效锁存配合。旧272B capture在close后是CLOSED，不能反造RESOLVED。新248B无指针标量快照只在本地持久存储，不发布/不编码，不改query272B/ADT/日志载体。GateBefore/After为本地门判断，原native raw64错误/warning保留。

权威vote/rate/variant policy仍缺，正常lookup成功也返回ZPC_POLICY_UNAVAILABLE5；没有调用Zpt/Zcr preparer或生成操作请求，只复用真实224/256B类型。prepared/invoke/runtime恒0，QueryRun返回EFI_ABORTED并终止payload发布，不能启动这个不可读失败路径。once/release-ready/acquire-copy、显式gate attempted、别名拒绝只属软件生命周期，不补硬件lease。staged close增加create_attempted==created_events，SUCCESS+NULL注册也不当清理完毕；旧owner源码不改。

10独立ASan/UBSan实际集成场景、4源码突变及4CLI拒绝通过，所有native/SMC/touch为double。5个真实目标对象独立完整SHA相同、78递归输入、fresh AutoGen与26显式SDK库绑定，排除旧模块archive；实际入口完整隔离PE链接，不是FD/kernel/boot候选。272/248/360/224/256布局、关闭前调用/双门/160-248-272copy/once/原callback release/ready LDAPR-STLR/零初始可写存储通过，9实际PE破坏拒绝。独立链接除保留timestamp外相同；LTO特化实际static owner/epoch1，其他CFG/PAGE/SDK仍普通编译链接契约，不夸穷尽。

fixture ZeroMem原型拒绝、MS include搜索Werror和初checker把d0/d4/d8指令地址当SIMD寄存器的失败保留；分别修fixture、复制精确旧头及限定指令部分检查，未放宽native编译警告。342/190、冻结255/raw231、原88/default42保持。无手机操作/boot/写分区/原生GPU激活，allow_boot/readback=false。

机主提供的[官方GPU与Metal指南](https://unixnu.com/zh/porting/gpu)及平台/驱动接入页已核对。其GMU头固定4e0314d与本地逐字节相同，接口要求caller先持有已映射/供电窗口；A740/SM8550成功不证明K80 A750。后续显式保留Gen7-9-1内核后端与compiler target/所选OS ABI/CP-fence/已知图像/Metal分级门槛，不搬sheng池/IOVA/五窗口/投票常量。下一只补尚缺的真实typed只读GCD/保留span观察provider，GetMemorySpaceDescriptor不修改资源；其结果也不是secure/DMA所有权。复用已完成reserved源码证据，不重做旧CPU/GUI/内存或query套件。[证据](evidence/gpu-native-platform-caller-2026-10-31.json)。


## 真实只读GCD provider与默认关闭caller完成（2026-10-31）

out/zorn/gpu-readonly-GCD-provider复用真实PiDxe EFI_DXE_SERVICES.GetMemorySpaceDescriptor（槽偏移56，无This；descriptor56B、type32/handles40-48），仅查询旧已声明0x9b09a000/0x2000，最多16descriptor。真实已有EBS owner.check先于借用table、逐调用前后检查；原raw64 native status/warning与attempt/return/valid/gate mask保留，非零warning、非reserved、未知type、越界/空洞/无进展、table变化或expiry失败。未分配/修改GCD或访问物理内容，不用caller callback造lease。

2312B私有对象保留16真实typed descriptor/handles及借用owner/services/method，1384B标量快照仅保留owner存在布尔值；once/release/acquire和getter state/owner/table别名拒绝，不发布指针或改query272B/ADT/日志载体。SpanObserved只是历史分段观察，多个native调用不构成同一generation整图快照，reserved/NULL ImageHandle不证明secure/coherent/stop/SMMU/DMA或写权限。原生getter会获取锁/升降TPL并遍历链表，无次数上界，释放可dispatch回调；16次是调用次数上限而非墙钟保证，EBS gate不能取消在途调用。

实际DxeServicesTableLib缓存config-table的gDS、真实AutoGen constructor边及DxeMain/Gcd getter/search/BuildMemoryDescriptor/lock源码已绑定；此处不是归档DXE core二进制精确匹配或live接口安装证明。复用旧reserved源码，不重跑旧阶段。OFF Query.cpp与上一caller preimage字节一致，C入口/272B头不变；显式ON在原config prepare/close前调用GCD observer，真实gDS来自原库。缺平台策略仍EFI_ABORTED并停止payload发布，不能拿本轮去boot。

21独立ASan/UBSan场景+2原C-prefix/实际Query ON-OFF集成、5源码突变及4CLI拒绝通过，全部native/SMC/touch为double。6真实目标对象独立完整SHA相同、80递归输入、fresh AutoGen/26显式复用SDK库与旧module archive排除。实际入口完整隔离PE和used no-This ABI通过；最终gDS/caller/method、双门/原status保存-严格零、reserved/循环边界、handle转布尔、1384copy而非2312private、once/释放获取/初始零可写存储核对，10实际PE破坏拒绝；独立链接除保留timestamp相同，不夸其余CFG/PAGE/SDK或metadata等价。初stage ternary空格matcher拒绝及fixture错误ID tag被真实resolver拒绝均保留，修测试不放宽provider。

342/190、冻结255/raw231、原88/default42保持，无手机/native/GPU操作或新FD/kernel，allow_boot/readback=false。按机主官方指南继续A750编译器身份consumer：当前Darwin Mesa patch仅对43050a01 special-case740，43051401按字面fallback为6770；尚未追完固定Mesa的chipid匹配优先级/生成表/IR3，不能据此宣称不支持或直接改750。下一核对固定85fda3b的实际consumer并做必要最小隔离修正，不搬A740 shader/池/IOVA或造硬件资格。[证据](evidence/gpu-readonly-GCD-provider-2026-10-31.json)。


## 固定Mesa正确识别K80 FD750与Gen7，身份分支无需修补（2026-10-31）

out/zorn/gpu-A750-compiler-identity按机主官方指南，只取固定compiler-inputs的Mesa85fda3b七文件289679B。mirror的已知root treeb72ff1e、各级tree ID、每个原Git blob和独立SHA256闭合，无全克隆/依赖安装/活动patch。sandbox DNS失败后只读网络获取成功，目录拒绝猜测的拆分physical-device/.c路径；以实际tu_device.cc为准。

关键勘误：Darwin patch给43051401的数字gpu_id确实是6770，但不导致当前匹配失败。真实GPUId对显式chipid默认gpu_id0，表已有43051401与ffff43051401的FD750/A7XX/a7xx_gen3。dev_id_compare只有ref和input的gpu_id均非0才按数字比较，此处按真实chipid匹配；fd_dev_gen读取匹配info.chip7，非6770/100。tu_physical_device_init按name/info/gen分支并把同一dev_id/info交IR3，ir3_compiler_create也从fd_dev_gen选7。无需猜改750、替换chipid或伪装A740。

原Python CHIP/GPUId和原C matcher/name/rawlookup函数体复用；73有序ID/32CHIP组仅投影ID/name/order/chip，其余fd_dev_info字段未生成、fixture为0，不是完整设备表或成功GetInfo。8实际源码ASan/UBSan身份场景及2源码突变拒绝通过，覆盖K80、原740、fuse wildcard、数字750单独不足和未知patch拒绝。独立AArch64 macOS13通用C注解raw SHA相同，仅assert runtime导入；非所选Darwin23/XNU配方或完整Turnip/IR3/shader编译。初独立ARRAY_SIZE有符号比较Werror拒绝已保存，仅该注解显式Wno-sign-compare，生产配方/guard和原C体未改。

Native64B DeviceInfo仍需真实GMEM/VA/trap/UBWC/coherency等输入，发布要求live VM/submit/ring；Sheng固定43050a01和资源不当K80资格。未造kernel GetInfo成功、未发布Metal或执行GPU。342/190、冻结255/raw231、原88/default42保持，无手机或新FD/kernel，allow_boot/readback=false。

身份疑点已闭合，完整编译器功能和硬件仍未验收。下一转已缓存OEM453d8875的gen7_cp_init_cmds/hwsched raw-command consumer，复用原PM4/HFI做最小仅CPU请求准备；缺DMS/真实GPU-visible pwrup-list地址必须拒绝，不填假IOVA/零地址，不执行trust/unsecure/ZAP/MMIO或旧启动轮。[证据](evidence/gpu-A750-compiler-identity-2026-10-31.json)。


## Gen7 CP不完整请求准备与地址拒绝完成（2026-10-31）

out/zorn/gpu-Gen7-CP-init复用固定OEM gen7_cp_init_cmds/hwsched raw consumer，只补同453d8875缺少的PM4头11611B/SHA19208220。THREAD_CONTROL0x17/ME_INIT0x48、10CP/11HFI字、3context/error20000000/operation2/triplet31、DMS bit11及main/LPAC131/135已从真源绑定。bit6是性能计数器save/restore，不拿它推断preemption。原async后有独立CX/LPAC busy poll（原参数200/bit23），本轮不调用/不宣称idle或墙钟保证，也不执行后续ZAP/trust/unsecure路径。

新48B输入/144B纯C不完整plan复用原AdrenoPM4Type7。FILE DMS/LPAC仅显式软件意图，不是实测或owner；KnownWordMask277/27f始终排除地址字7/8，DMS未知时也排除word3。Raw64地址/source/native诊断原样保留但不编码，CPU PA/文件值不当IOVA；真实GPU list owner/content、策略权利、platform/completion恒缺。所有有效描述均UNAVAILABLE，PacketAvailable/InvokeAllowed/RuntimeComplete/NativeAttempted0，没有完整可发CP包/HFI envelope/sequence，没有native操作。无效/别名/范围/chipid/FILE布尔错误不改输出。

27不完整描述/4无效拒绝与原OEM CP/parity/type7函数体比较已知字，oracle地址0明确为缺失，未当有效GPU地址。3源码突变拒绝invented-ready/DMS反转/raw地址注入；不重跑旧HFI/CPU/GUI/内存套件。helper+原PM4独立iOS17 SDK ARM64/general-regs-only对象raw SHA一致，C可重定位链接仅memcpy；非所选XNU配方/最终kernel/FD。选定对象K80 guard、mask/DMS/131-135/地址与启动标志清零、2Type7+1memcpy relocation/144copy核对，无新间接call/SMC/SIMD，4实际对象突变拒绝；其他CFG/PAGE仍编译链接契约。

oracle缺CP_TYPE7_PKT的首编译拒绝保存后补来源常量并复用原parity；初对象checker误假设reloc顺序/把数字hex指令字当SIMD也保留首版，改规范排序和只读解码operands，不改candidate/原PM4/生产flags。342/190、冻结255/raw231、原88/default42保持，无手机/完整packet/新FD/kernel或GPU执行，allow_boot/readback=false。下一只追实际pwrup-list PAGE_SIZE privileged producer、cpu_gpu_lock、IFPC/preemption pairs与dynamic aperture/address/data triplets，准备最小不活动shape，缺真实值/IOVA必须拒绝，不能用host填寄存器。[证据](evidence/gpu-Gen7-CP-init-2026-10-31.json)。


## Gen7 pwrup原生布局与含头容量准备完成（2026-10-31）

out/zorn/gpu-Gen7-pwrup-list复用原cpu_gpu_lock结构和selected数组，真实布局16B、ifpc/preemption/dynamic偏移12/13/14且8/8/16bit。当前完整gen7_reg.h SHA2e564d7eaeec26bc30e79b1d117b86efa79603345769626157c83610fc4c051c绑定，不用旧houji表。Gen7-9-1选择普通IFPC54+9_x附加4、preemption17，共75对/600B，加16B头后dynamic offset616B；动态为aperture/address/data triplets。PAGE_SIZE/privileged只是参考分配策略，真实allocation/page/IOVA未观测。

新40B输入/152B纯C要求对象按616+12*requested triplets检查容量和u16上界，FILE容量必须显式给出且含头，unknown容量不解释，最大triplets不超65535。请求count含末尾control triplet，不是live list观测。raw诊断/status available原样保留但无native调用；List/Invoke/Runtime/LockOwned/NativeAttempted恒0、missing ff。没有填任何寄存器值/list字节/GPU地址、分配映射或操作锁，非法/别名/范围参数不改输出。

新边界发现：实际参考update的data已跳过16B头，容量式却用完整size/4。在纯4096B算例里现有290triplet再加一个RESTORE entry，原比较offset1017+pending2*3=1023<1024可放过，而完整616+291*12=4108超12B。新要求检查明确拒绝。这只是实际源码谓词的算术反例，未证明stock K80能达到该组合、未复现设备损坏，也未改活动/OEM源。真实kgsl_hwlock request/turn/barriers及1000ms jiffies策略另绑定但不执行，不把零lock字段当owner或GPU停止。

10245软件extent组合及范围/unknown/exact-fit/无效/别名、4真实源码突变拒绝通过。独立iOS17 SDK ARM64/general-regs-only对象完整SHA相同，无导入/调用；选定chipid/u16/header-inclusive算术/count/零store审计及4实际对象破坏拒绝，非所选XNU/最终kernel/FD或native运行证明。初checker把短SHA手工补错被严格拒绝，首版保留，已改读既有gen7-reg-source-verification完整SHA，不改旧manifest/guard或寄存器源。

342/190、冻结255/raw231、原88/default42保持，无phone/boot/GPU或新FD/kernel，allow_boot/readback=false。下一做真正所选Darwin23 NativeAdrenoService/Board的最小隔离Gen7 provider/caller准备，默认OFF字节一致，ON只在ShengColdStart/MMIO/SMMU/publish前检查真实typed资源并拒绝不合格旧路径；不加仅为运行已知unavailable算术的BSD诊断，不编造资源所有权。[证据](evidence/gpu-Gen7-pwrup-list-2026-10-31.json)。


## Darwin23 Gen7真实Service准备入口隔离完成（2026-10-31）

out/zorn/gpu-native-Gen7-caller已接合实际NativeAdrenoGpuService，默认OFF源逐字节一致；只有显式--gen7-prepare产生ON。ON用私有560B实例报告，整个start只有准备调用和false，在super start/映射/ShengColdStart/SMMU/publish之前停止，所有输入都不落入旧路径。五个失去旧start引用的静态SMMU callback只在ON加maybe_unused，函数体和严格编译flags不变；原metaclass/probe写callback/stop/client仍存在，不能说整个module无副作用。

新provider用真实IOService/OSData读取compatible，256B内精确NUL token、拒绝前缀/重复/混代。软件ProfileChipId来自已绑定gen7-9-1选择，不称live芯片值；FRESH/RETAINED门在virtual lookup前关闭，重复/重入拒绝。复用Zcp/Zpl准备未知policy/capacity/address的不完整要求；可选有效typed描述符复用真实ZornGpuDescribeResources/Board并保留IOReturn/overlap，成功仍missingff/invoke/runtime0。当前真实ADT builder没有GPU/GMU节点，Service明确传null描述符，不把缓存FDT或已映射GMU当运行时输入；没有ADT/查询/日志载体改动、EFI指针、分配映射或GPU操作。

20项focused host ASan/UBSan与4源码突变拒绝，host IOKit对象为double。实际Darwin23 XNU/IOKit配方7对象（含完整ON Service）独立SHA相同，489递归输入；组件链接内部API闭合。目标start10条指令仅null描述符调用并false；helper的once门、3真实查询slot、Zcp/Zpl/parser和560Bcopy已核，4实际对象破坏拒绝。所用SM8550三公共头来自catalog固定23b2049且Git blob匹配，仅编译类型，无旧平台实现执行。非最终kernel/新类布局虚表或所有CFG/PAGE证明。

未隐藏失败：OFF原源在当前no-Sheng-rules配置下因9未用变量被Werror拒绝，OFF只证明字节一致、未获编译资格，不改源/降warning去凑通过。首duplicate突变被另一target==1检查冗余挡住，首checker/log保留，换独立prefix负控制后拒绝，candidate未改。网络/缺头和ON未用静态callback首拒绝日志保留。

342/190、冻结255/raw231、原88/default42匹配，无手机/boot/GPU/新FD/kernel；allow_boot/readback=false。下一核对实际GMU/SMMU companion入口和ArmDTPlatform registry/ADT字节序、祖先及生命周期，先阻断旧映射路径再接真实typed描述符，不能猜registry路径或把描述符当owner。GPU渲染和Metal未启用。[证据](evidence/gpu-native-Gen7-caller-2026-10-31.json)。


## 原生GMU/SMMU拒绝门及真实ADT表示契约完成（2026-10-31）

out/zorn/gpu-native-resource-contract以单一隔离ON/OFF选择绑定三个Service，GPU ON沿用上阶段已核对象/源码。GMU/SMMU ON的probe直接null、start直接false，在property/score/super/device-memory/map/属性发布/registerService之前停止；仅旧matcher加maybe_unused，原metaclass/stop仍在。三份OFF均与活动源逐字节一致，两个companion各自ON/OFF严格原生编译通过，不重跑或修复原GPU OFF九变量Werror失败。GPU旧probe仍会写clock callback，后续发布节点前必须处理，不能称所有三模块完全无副作用。

真实XNU MakeReferenceTable按原字节复制或借用OSData，没有数值swap；ARM64 CellsValue按本机序、低cell在前。GetUInt32要求精确4B，IODTResolveAddressing从DT-plane parent取cell counts/ranges，和旧Service读child/default2,2不同。nub在Service-plane挂platform expert，DT-plane祖先由init重接保留，不可混用。getProperty解锁后返回非retained对象，char重载可intern/分配OSSymbol；copyProperty只保留对象而非冻结多属性snapshot/图结构。IODTResolveAddressing实际返回OSArray*并分配CPU资源描述符；getResources发生在probeCandidates之前，所以probe/start拒绝不构成启用节点后的全路径零副作用证明。

实际XNU三个cell函数体、原NativeBoard及共用hardware_properties编码器完成16项source对照：10缓存GPU/GMU窗口的ADT LE低cell表示不能直接送入BE FDT parser，cell顺序源码突变拒绝。这里只用base0合成root比表示，不当新板级地址布局/完整format2证明。另只读已消耗0fe不可变归档的13584B ADT，用原实际SecureDT对象检查8个root子节点/2个armio子节点；没有直接GPU/GMU/SMMU节点，counts2/2及armio child0->physical17000000/08000000与intc本机序实际字节匹配。十个GPU/GMU物理窗口均低于17000000，不能直接把其绝对地址作为此bus偏移。树字节不变，未重跑原query套件或手机轮。

4完整XNU/IOKit对象独立SHA相同、344递归输入绑定；probe是64bit零返回+ret，start是32bit零返回+ret，无call/reloc。2源码突变、4实际对象破坏全部拒绝；与原GPU ON对象三类可重定位注解链接闭合，非最终kernel/类虚表或硬件资格。首checker误认pointer return为32bit及源码突变选择器过宽的拒绝保存，已按真实方法/ABI修正，不降flags或改candidate。

342/190、冻结255/raw231、原88/default42保持，无新DT/ADT属性/节点启用/FD/kernel/phone/boot/GPU，allow_boot/readback=false。下一最小真实typed retained-ADT描述符binder，先按真实parent/字节序/lifetime适配到共用资源parser；不猜registry路径、不新增算术BSD探针、不用retained对象/descriptor补GPU owner。实际power/security/stop/SMMU/IOVA/coherency及可读保护仍缺，GPU渲染/Metal未启用。[证据](evidence/gpu-native-resource-contract-2026-10-31.json)。


## 真实typed retained-ADT描述符binder隔离完成（2026-10-31）

out/zorn/gpu-native-ADT-binder使用实际IORegistryEntry/OSData/OSSymbol，私有固定4600B owner复用原560B无指针报告。caller持有有效typedGPU/GMU/bus/root与7个不可变symbol，单线程普通上下文且输入/属性字节与owner分离。once在首virtual query前关闭；symbol键名精确、copyProperty保留至多13属性，copyParentEntry保留DT first-parent并核对root挂真实registry root。只支持明确2/2cell、本机LE低cell在前的root直下或一层bus；root无ranges且name=device-tree，GMU精确gen7，bus最多8个24B ranges。拒绝溢出/缺失/混cell/不完整跨度/歧义/部分重叠，不调私有resolver、不猜默认或identity；BE规范化副本复用原Board/资源parser，PA不当IOVA。

原Gen7软件准备的精确源码变换只改为已保留OSData输入并移除字符串属性重查，原选择/Zcp/Zpl/560B形状不变，旧源/caller不改。没有伪造IOService proxy或GPU owner。复制后复核对象/长度/字节及祖先，变化即令descriptor_valid无效并保留parser attempted/status；retention/两次读不当不可变事务或唯一祖先证明。正常返回释放本次引用并清空保留指针，Missing ff/Invoke/Runtime/GPUAttempted恒0。无返回error码的null property/parent只记软件拒绝，不造原生OOM或成功码。

50项focused host ASan/UBSan含direct/非零高cellbus、表示/范围/祖先/键错误、20个lookup错类、重入/重复、属性内容/对象/graph变化和引用平衡；host对象仅元数据fixture，未补造硬件权限。fixture用实际共用编码器，3真实源码突变拒绝。首突变marker同时命中注释被拒并保留首checker，已缩为实际return语句，candidate不改。

3个真实所选Darwin23 XNU/IOKit对象独立SHA相同，351递归输入；5个原合格共用对象完整SHA复用，不重跑旧套件。链接导入仅registry/OSData元数据和CPU helper。独立真实头注解核对copyProperty(symbol)138、copyParent90、OSData lengtha0/bytesd8及4600B constinit零BSS/无initializer；selected once/大小门、560copy、重查/失效目标检查和5个实际对象破坏拒绝通过。局部stack880/736B不是全调用链或墙钟界限，IOKit可阻塞；非最终kernel/类虚表或全CFG/PAGE证明。

342/190、冻结255/raw231、原88/default42保持。当前ADT仍无GPU/GMU节点，Service仍传null描述符，binder未在真实内核调用；没有节点启用/activeADT/FD/kernel/phone/boot/映射或GPU操作，allow_boot/readback=false。下一仅source-only可选板级资源producer，复用实际node编码器、defaultOFF字节一致，不把新描述当已存在路径或owner；实际平台权利/可读保护/完整候选仍缺，GPU渲染和Metal未启用。[证据](evidence/gpu-native-ADT-binder-2026-10-31.json)。


## 可选板级资源节点producer与三probe拒绝源链完成（2026-10-31）

out/zorn/gpu-board-resource-producer只在隔离源提供--gpu-resource-descriptions，默认OFF builder和三Service逐字节一致。ON使用实际hardware_properties/node编码器，把来源SHA固定且本轮既有FDT比较未变的GPU7/GMU3 reg/names/compatible生成两个新root直下标准节点。根直下位置是明确提出的新板级描述，不冒称已存在registry路径、stock ABI、live variant或owner；GMU名保留3d69000、reg按实际3d68000。只有name/compatible/reg-names/reg，无IRQ/clock/SID/pool/lease或query诊断属性。flag只允许新建本阶段test-data文件，拒绝越界/覆盖。

同一8GiB/8CPU测试参数下，OFF和ON未选项输出均12280B。用真实SecureDT返回的64B随机seed定位唯一offset336，仅在内存比较时忽略该64B，其余字节完全一致；未改文件或伪造实际seed。选项输出12940B，增660B、恰好2root节点，所有原属性/子树内容除新seed保持。此为源码test数据，不是旧0fe canonical参数/完整format2/设备等价性证明，未覆盖当前ADT。

未改的真实SecureDT对象检查实际生成树，再将其返回的原属性字节送入实际binder/common parser/request的7个已合格host对象（完整SHA复用，不重跑50项旧套件）。仅元数据IORegistry fixture，描述符合且保留GMU/CX overlap、引用平衡，560B报告仍missingff/Invoke/Runtime0，不是live设备权利。OFF CLI、越界输出、已有输出、实际源码改回raw FDT reg的四项控制通过。

GPU ON probe现为movx0zero+ret，不写旧clock callback、不查询property/score；仅两个失去引用的旧helper加maybe_unused，函数体/strict flags不变。原start仍10指令null描述符准备+false。一个完整实际XNU/IOKit对象独立SHA相同，398递归/来源输入绑定，旧clock全局不再导入；源码重新加callback写入及对象返回provider均拒绝。两个companion ON对象原SHA复用，三类可重定位注解链接。原metaclass/其他方法、probe前getResources副作用仍在，不能称整个module/节点发布无副作用或最终kernel已验收。

342/190、冻结255/raw231、原88/default42保持，无active源/ADT/FD/kernel/canonical构建/phone/boot/节点启用/发布/GPU操作，allow_boot/readback=false。当前真实Service仍null描述符；下一真实隔离pair caller及retained partner/symbol生命周期源码接合，再回到平台所有权/可读保护/完整候选门槛。GPU渲染和Metal未启用。[证据](evidence/gpu-board-resource-producer-2026-10-31.json)。


## 实际Gen7原生pair caller源码接合完成（2026-10-31）

out/zorn/gpu-native-pair-caller把真实NativeAdrenoGpuService start接到私有4720B caller，再调用既有retained ADT binder，原560B标量报告不变。使用实际OSSymbol::withCString的7键、DT-plane保留父节点/partner/name对象，root须挂实际registry root；所有正常返回的部分引用均释放并清空，重复/重入在查询前拒绝。symbol仅CPU元数据分配且可阻塞，null无原生错误码，不造NoMemory或成功码。全3probe仍null，start固定false，未调super/map/publish或硬件。

真实MakeReferenceTable保留完整name，默认location是reg首本机U32按%X格式化：GPU3D00000/GMU3D68000。真实getChildFromComponent先比完整getName，故新producer的qcom,gmu@3d69000按全名匹配，不能把后缀当MMIO基址；fromPath拒绝残余路径。实际三函数体进入focused host oracle，alias resolver/锁为fixture且拟议树无aliases，不称live路径或唯一/不可变图。

调用后复核partner、GPU/GMU/root first parent、name对象和字节。可观察变化令caller报告getter不可用，原attempt报告/IOReturn仅保留取证，不被解释为成功；不是原子snapshot/任意并发证明。描述匹配仍missingff/Invoke/Runtime/GPUAttempted0及NotReady。34项ASan/UBSan含7symbol部分失败/路径/变化/重入/引用平衡，3源码突变拒绝。首fixture缺other默认name及GPU/GMU共享location导致拒绝日志保留，按真实reg默认location修正，candidate未放宽。

3实际Darwin23 XNU/IOKit对象独立SHA相同，401递归输入；7旧binder/common对象和2companion完整SHA复用，不重跑旧套件。真实ABI核childFromPath248/null残余参数、const release28、parent90/property138，Service直接call后false、once/7symbol调用、原IOReturn保存、11引用release/clear与availability getter通过；4720B constinit零BSS/无新initializer，6实际对象破坏拒绝。caller局部144B不是全链栈/墙钟界；原metaclass/其他方法及probe前getResources仍存在，非最终kernel/类布局虚表/全CFG/PAGE或硬件资格。

4OFF源逐字节一致，ON builder/两companion沿用原阶段，仅GPU Service私有caller/入口接合。342/190、冻结255/raw231、原88/default42保持，无active/canonical源或ADT/节点发布/新FD/kernel/phone/boot/GPU操作。下一回到实际平台权利、最早失败的可读保护和规范候选接合/拒绝设计；不扩query/报告/codec/环或再造元数据模型。GPU渲染和Metal未启用，allow_boot/readback=false。[证据](evidence/gpu-native-pair-caller-2026-10-31.json)。


## 平台保护缺口及构建器/runner隔离拒绝补丁（2026-10-31）

out/zorn/gpu-platform-protection-closure核对真实固定runner：USB前有build ready/image SHA检查，但没有读取当前GPU allow_boot/readback或已消耗c50/0fe资格。recovered只表示回收，kernel_log_changed=false仍可记录recovered，不是GPU成功或新报告证明。未发生新运行；原runner/构建器和所有旧manifest保持字节一致。

新review.UNAPPLIED.patch仅为可审查草案：ON builder/runner各在main最前插两行，真实helper无任何接受/return分支，在deadline helper/caffeinate/参数/镜像/输出/USB前无条件拒绝本未合格阶段。current只用于解释拒绝，缺失/损坏/伪造true都不当权利；无新接受schema/override、原生成功码、设备命令、写盘或定时器。2OFF文件逐字节一致，ON除两行外与真实源码一致；补丁git apply --check通过但未应用，不能宣称活动runner已受此门保护。

22项真实staged main入口拒绝覆盖11种current上下文，4实际负控制（删runner门/删builder门/门移后/伪造接受helper）都只触及首个trap被拒；没有真实subprocess/设备调用、build输出或caffeinate进程。此为host拒绝路径检查，无新原生对象/kernel/FD或硬件资格。

真实源码顺序另核：PlatformConfigPrepare即使ID/lifetime满足也以POLICY_UNAVAILABLE终止；QueryRun close/seal后返回EFI_ABORTED，PublishRange在payload分配/协议发布前返回错误。因此native/loader不保证运行，WDT/fresh BCB自动回收不能替代报告传输。复用既有读回不合格证据，不重跑容量/codec套件、不扩272B/24B/560B或原84text/footer/trace/持久窗口。当前选定路径仍无合格最早失败读回，allow_boot/readback=false。

342/190、冻结255/raw231、原88/default42保持；无手机/boot/分区写/GPU操作或物理协助请求。平台集成草案保持拒绝，下一独立推进必须的A750实际IR3/AirNir编译器构建输入：沿用已证43051401->FD750/gen7，不重做identity，不盲跑硬编码Sheng且写/清共享prefix的旧host脚本；已查出真实host入口引用的build-adreno-compiler-host.py在活动/解析树均缺失；首record严格拒绝不存在的next input，未改docs/current。缺项单独记录，下一先按真实catalog/source绑定缺失构建配方，再隔离最小实际编译，不造shader成功。GPU渲染和Metal仍未启用。[证据](evidence/gpu-platform-protection-closure-2026-10-31.json)。


## A750真实编译器配方来源与隔离工具引导完成（2026-10-31）

out/zorn/gpu-A750-compiler-bootstrap查明缺失配方属于catalog固定Sheng设备08cde20，脚本与package/AdrenoCompilerProbe.c的实际Git blob已核对归档；它不是应向核心仓库补回的丢失blob，K80解析树尚未集成。参考脚本/A740探针未执行或改动。新隔离K80输入只替换两处chipid/FD名与标签，保留真实NIR/IR3 API和shader图，明确synthetic NIR，不称原UI AIR或手工ISA；不沿用A740输出128B/SHA作为A750期待。

按现有固定版本下载6个wheel并大小/SHA校验后，仅在本out的venv离线安装。原固定SHA的2817324B GNU Bison3.8.2源包真实编译/安装至隔离prefix；840项工具输入绑定，未改活动缓存/系统工具。现有LLVM23.1.4不满足AIR精确23.1.3，原guard不改、不下载大工具链；IR3-only使用原真实配方llvm=disabled，不等于AIR/iOS资格。

实际固定85fda3b的include/bin/IR3三个必要子树312条目，解包7837722B/压缩1444508B，完整tree与312blob经独立真实Git逐项复核。首保守归档拒绝真实symlink并保留错误；修正后把Git symlink mode/目标字节纳入完整tree校验，只允许新源码根内目标，不接受硬链接或逃逸。先前10个Meson/patch输入保留；只用前4个真实compiler patch并逐字节反向恢复，不声称9个runtime patch等价。

真实Bison/flex执行IR3 Meson的原语法生成命令，产生555904B parser/header/lexer，尚未编译这些C或生成shader。两次真实Meson的非零结果均保留：首次缺include/meson.build，补齐必要目录后推进至src/gtest/meson.build缺失；没有用空目录/stub/放宽flag来凑通过。IR3配置、库/可执行文件、A750 shader、原AIR、iOS target与Metal均未完成。

342/190、冻结255/raw231、原88/default42保持，无新FD/kernel/phone/boot/GPU或物理请求，allow_boot/readback=false。下一按真实src/meson.build补齐必要源码闭合，再构建一个真实A750 synthetic NIR编译目标/asm roundtrip；不重跑旧identity/固件/codec/CPU轮，也不以工具引导成功代替GPU驱动或平台权利。[证据](evidence/gpu-A750-compiler-bootstrap-2026-10-31.json)。

计数勘误：首批10源码实际194064B；原combined中一处文字写为194063B，原文件保留，源码/Git/tool校验与失败结果不变。见[修订证据](evidence/gpu-A750-compiler-bootstrap-v2-2026-10-31.json)。


## 实际A750离线IR3构建与首个synthetic NIR shader完成（2026-10-31）

out/zorn/gpu-A750-IR3-source-closure按真实Meson图补齐28个必要子树/2932条目（解包49094146B/压缩9225160B），固定Git tree独立复核，无完整镜像或LLVM下载。只复用原工具/前4个compiler patch并精确反向恢复，未启用Gallium/Vulkan/OpenGL/EGL/LLVM/shader cache或下载fallback。真实Meson通过；首轮编译在440/458处缺drm/freedreno_drmif.h，原失败保留，补固定blob的真实声明头后增量构建成功，不用DRM stub/实现或旧Mac objects冒充新目标。

真实host编译器13856456B，Mach-O ARM64仅link libSystem；405对象/11archives/1595实际头/源输入完整SHA绑定。实际原NIR/IR3 API输入43051401/FD750/gen7生成128B、32dword顶点代码、原NIR与反汇编；内部实际disasm/parse/reassemble未填充word比较通过，无GPU执行。此简单图的机器码实际与既有A740样例相同，结果来自真实编译而非沿用期待SHA，不能当A750专属指令覆盖/语义或硬件证明，更非原UI AIR。

清理IR3/NIR等环境后的缺roundtrip测试真实exit5且无文件。删除必需debug guard的C源码突变实际重编/重链后返回0并留3文件，checker按提前拒绝/无输出契约识别，不只相信stdout的asm_roundtrip布尔字面量；原target对象另目录独立重编完整SHA一致。没有重跑旧368ISA/delay/identity模型套件。

首宽源码snapshot核对拒绝了Finder自动更新的.DS_Store；旧snapshot及前后SHA保留并明确列为非Git/非C-Ninja输入，真实源码/头/对象/归档与canonical guard未放宽。原先构建源码字节保持，只有真实缺失DRM头作为新输入加入。此为host构建，iOS17目标、AIR精确LLVM23.1.3、原UI shader、runtime/Metal均未验收，23.1.4没有替代guard。

342/190、冻结255/raw231、原88/default42保持，无新FD/kernel/ADT/手机/boot/GPU或物理请求，allow_boot/readback=false。下一仅实际ARM64/iOS17 SDK的IR3-only交叉构建/最终链接，不用Mac objects/stub/旧OS偏移，不执行目标手机程序；平台所有权/最早失败可读保护与完整候选门槛仍缺。[证据](evidence/gpu-A750-IR3-source-closure-2026-10-31.json)。


## 实际IR3的ARM64/iOS交叉构建与最终静态验收（2026-10-31）

out/zorn/gpu-A750-IR3-ios17完成真实Xcode iPhoneOS27.0 SDK、arm64-apple-ios17.0 deployment target交叉构建。明确不是原版iOS17 SDK，也不是iOS17/Darwin23运行时验收。原build-air-nir-ios.py只读派生真实IR3-only选项，LLVM disabled；精确23.1.3检查未改，23.1.4没有替代。源码3250条严格SHA独立复制，symlink只限新源码内，不拷主机对象/静态库、不用stub SDK或假exe wrapper，nodownload/runtime render/cache关闭。新编译458/458通过，无目标执行。

实际405个ARM64 MH_OBJECT、11个archive的403个成员及1593个真实头/源依赖已逐一SHA/平台检查，目标头不来自MacOSX SDK。所有对象/成员和最终MH_EXECUTE均为IOS平台2/minOS17.0/sdk27.0；每个库成员完整SHA对应新编对象。最终13693680B，SHA fb1a70101fac1c610de51988b7f68b6d76e6dfda80bcffc3eac85e3fa8498550，只有libSystem动态依赖，真实clang/ar/ld/SDKSettings/libSystem TBD另外绑定。最终main到10项真实Mesa/NIR/IR3 API的BL机器字、实际符号与目标地址核对；不宣称全部CFG/PAGE/数据流穷尽。

真实fixture同配方另目录重编SHA b050e0939c0e2840512aa9cf9bfd3c44d94cd16bc7619a5527074869d03dcb7b与构建对象完整相同。两个独立最终文件副本篡改platform为Mac或minOS18，以及一个archive成员改Mac均被拒绝，原产物不改。独立真实重链成功，仅LC_UUID16字节不同，其余全部字节一致；不称完整文件SHA一致或UUID没有消费者。首次checker误要求局部静态名全局唯一、第二版误要求hidden Mesa符号带N_EXT，均原样保留失败脚本/log；最终按实际N_PEXT/N_SECT0x1e及所需符号唯一地址核对，未改compiler/provider/image。

本轮没有执行iOS目标或生成新shader，更非GPU/Metal完成。之前host128B简单顶点结果保持，尚无A750专属指令/语义覆盖。下一仅以固定源码的gen3 has_compliant_dp4acc/真实signed-dot consumer做一个保留动态输入的NIR案例，实际编译/反汇编/未填充roundtrip和窄负控制，不手编码ISA或猜SHA；随后只独立交叉编译变更caller，不重复旧套件/405对象整轮。AIR精确LLVM、原UI shader、运行时/原生平台所有权、可读失败保护和完整候选门槛仍缺。

342/190、冻结255/raw231、原88/default42保持；最后手机轮仍为已回收0fe，无新FD/kernel/ADT/手机操作/物理请求，allow_boot/readback=false。[证据](evidence/gpu-A750-IR3-ios17-2026-10-31.json)。


## A750/gen3真实signed packed-dot编译路径完成（2026-10-31）

out/zorn/gpu-A750-gen3-packed-dot使用原固定Mesa85fda3b的真实IR3 compiler和NIR API建立新案例：vertex_id/instance_id均为动态shader输入，累加项为vertex_id XOR0x7ffffff0，sdot_4x8_iadd_sat经i2f32输出position.x，未用常量图代替动态路径。真实gen3 has_compliant_dp4acc、compiler signed-dot选项及emit_alu_dot_4x8_as_dp4acc的mixed/high/SAT分支已逐源绑定；实际输出`dp4acc.mixed.high (sat)r0.x, (last)r0.x, r0.y, (last)r0.z`。这是A750/gen3指定编译路径覆盖，不宣称opcode只属于A750或shader语义/硬件执行已证明。

主机真实编译结果256B/36未填充dwords；两个signed-dot lowering选项关闭的窄负控制使用逐字节相同1020B输入NIR，DP4ACC消失，实际输出ashr/mul/mad/sad/add.s(sat)整数序列，256B/64dwords，binary SHA不同。两个实际内部disasm/parse/reassemble未填充代码比较均通过，没有拿固定stdout布尔值单独充当验证，没有重跑旧顶点/368ISA/delay/identity套件。

只重编新caller并分别链接已绑定真实host和iOS archives；iOS arm64/minOS17/sdk27新caller有264实际头/源依赖和12原目标链接输入，平台/最低版本/仅libSystem动态依赖通过，绝不拿Mac对象当iOS输入。iOS caller另目录同配方重编完整SHA一致；最终main到真实ternary NIR builder/IR3 APIs的机器BL与实际符号核对，将新NIR builder调用改NOP的独立最终文件副本被拒绝。没有执行iOS目标，不说它生成过shader，也不是新native kernel/FD或iOS17运行时验收。

原host/iOS阶段全部归档绑定和342/190、冻结255/raw231、原88/default42保持；last run仍recovered，无手机/boot/GPU/物理请求，allow_boot/readback=false。下一具体工作为真实选定AirNir的C MesaBackend与当前K80 Mesa API接合：它已接受uint64 chip并校验gen7，不臆造A740 hardcode；保持LLVM23.1.3原guard、不把C backend当原AIR frontend完成。原UI/Metal/平台所有权/可读最早失败及完整候选门槛仍缺。[证据](evidence/gpu-A750-gen3-packed-dot-2026-10-31.json)。


## 真实AirNir C后端与K80编译器接合完成（2026-10-31）

out/zorn/gpu-A750-AirNir-C-backend确认实际AirNir checkout为catalog固定b356371a74cd158c2902f4886f373ebb0f833a36，工作树干净；复制的每份C/C++/头文件与真实Git blob及SHA逐字节绑定。原样MesaBackend.c/BackendABI/FusedF32与真实已构建Mesa配方接合，无源码兼容补丁、stub或未解析导入放行。它已接受uint64 chip并校验gen7，没有臆造A740硬编码缺陷。新公开C API client用attribute3四分量到position输出，未调用AIR Frontend.cpp或Library.c，原完整消费配方/精确LLVM23.1.3仍未验收，23.1.4不替代guard。

主机实际C backend生成原有.nir/.backend.nir/.bin/.asm/.ir3.json五文件，FD750/43051401/gen7、128B/32reported code dwords、真实内部asm roundtrip通过，reciprocal_lowerings=0。透传属性复用寄存器，实际代码为end/填充，不是新算术指令/语义覆盖。原format1导出input slots4包括3个component_mask0的空项，仅1个有效attribute(maskf)，保留其原register_id/slot数值，不能当4个已绑定资源；runtime_binding_qualified/gpu_executed明确false。没有扩JSON/查询报告/协议，也未把源码原有original AIR字样当真实AIR输入证明。

真实attribute16 API拒绝返回-1且无输出；仅将原边界>=16改>16的独立backend副本实际重编/重链后被client识别为exit20，无shader编译或hardware模型。host/iOS实际后端和client共4对象另目录重编完整SHA相同，实际依赖260/269项，两个平台对象/链接输入分离。iOS最终仍arm64/IOS2/minOS17/sdk27，仅libSystem，核对main公开API调用与backend到真实IR3 variant的机器BL/实际符号；2个独立最终文件副本分别改坏public attribute和IR3调用均拒绝。iOS目标未执行，也不是原版iOS17 SDK/用户态运行时或native kernel ABI验收。

原342/190、冻结255/raw231、原88/default42、先前gen3/IR3归档与活动源保持；last run仍recovered，无FD/kernel/ADT/手机/boot/GPU/物理动作，allow_boot/readback=false。下一仅离线只读核对新iOS executable的原17用户态imports/export/reexport闭合，优先复用已归档原cache资料/原有有界reader，必要按真实只读SystemOS UUID/窗口核对；不重跑旧CPU/Metal/cache实验或改系统镜像，不把SDK27链接成功当原17运行证明。AIR/Metal/真实平台所有权、可读最早失败与完整候选门槛仍缺。[证据](evidence/gpu-A750-AirNir-C-backend-2026-10-31.json)。


## 原17用户态的静态imports/export/reexport闭合完成（2026-10-31）

out/zorn/gpu-A750-iOS17-imports对前轮真实C后端iOS executable核对134个chained import/nlist名称及库序号/weak位，遍历138处实际bind和10778处rebase，全部import有引用，rebase目标offset均在目标image段内。沿原libSystem实际load/reexport/export trie闭合134项，没有拿SDK27导出表代替原17缓存。3个pthread_mutexattr weak imports原样保留；9项带STUB_AND_RESOLVER，保留其stub/resolver字段，未调用resolver，更不说运行时函数地址、函数ABI/行为、pthread/allocator语义或dyld/code-sign可加载已证明。

先前组合路径下cache/reader源码不在原路径，实际固定a571176e源码在out/zorn/refer/dyld-1165.3找到并逐Git blob/SHA绑定；此版本标签不自动等于目标Darwin23。真实头派生cache table/chained import/start/pointer布局及bitfields，与原缓存观察逐项匹配，无猜offset。按原本地userdata-root.img的SystemOS section11874304,6451200只读挂载，fresh Writable=false及UUID8846FE78-2910-4297-AF97-D59BB6F8FC16核对；原sandbox设备未配置错误保留，在授权环境相同只读选项成功，没有降保护。

实际读取32个original Mach-O image头/UUID、选定导出树等728528B请求数据，归档请求块和137个完整签名块/原CodeDirectory共9417809B，所读内容逐字节覆盖到完整签名块并通过原SHA256比较；未重跑旧全cache签名/CPU/Metal实验。最初主文件读取含签名尾部、超出code-hash范围被拒，原脚本/log/部分归档保留；修为真实signature-offset前缀，没有放宽hash guard。嵌入CodeDirectory比较不是Apple信任认证，未重算3.3GB SystemOS或整root image SHA，不夸整镜像验证。

只卸载本轮建立的本地只读映射，源镜像大小/mtime不变；卸载后完全从归档输入重解析32个原头并重放134条导出链，结果一致。改变新target library ordinal或name offset、改变原malloc导出树精确edge的3个独立副本均拒绝/找不到指定export。仍非所有stub/调用ABI、动态dlsym路径、执行或性能证明。当前手机installed OS不由本地volume UUID代证。

原342/190、冻结255/raw231、原88/default42及前轮C backend归档不变，无活动源/FD/kernel/ADT/手机/boot/GPU/物理操作；allow_boot/readback=false。下一具体接实际Turnip Darwin KMD与当前native provider的used ABI/请求准备caller，默认禁用且不新增endpoint/query codec/tunnel/protocol或运行IOKit服务；复用原chip_id优先证据，不因deprecated6770重做identity模型/伪造A750 fix。AIR精确LLVM、Metal/Turnip runtime、真实平台所有权/可读最早失败及完整候选门槛仍缺。[证据](evidence/gpu-A750-iOS17-imports-2026-10-31.json)。


## Turnip/native实际输出长度边界与关闭caller完成（2026-10-31）

out/zorn/gpu-A750-Turnip-call-boundary绑定真实runtime patch的dw_call、dw_open_connection与物理设备consumer，以及catalog Adreno7404e0314df的NativeAdrenoABI/UserClient/Publish实际Git字节。Query1要求0输入/24B输出，GetDeviceInfo15要求0/64B；producer dispatch确实检查精确尺寸。原dw_call只返回IOConnectCallStructMethod状态、丢弃out_bytes，真实函数体在native返回0/输出0B请求24B时被测试捕获。隔离UNAPPLIED修订在原native非零错误时逐位保留，仅对成功但长度不等的结果返回本地kIOReturnBadArgument，不伪称provider报错；原24/64布局、ABI1、method IDs及现有direct/NTNL格式不改。

实际函数体配真实IOKit公开声明/implementation double的36案例覆盖2methods×2现有路由×精确/短/长长度及4种原非零状态；double仅填A5毒字节，不解释为任何设备字段/句柄/租约。原函数首短成功被识别为exit20，修订全过；没有IOKit native调用、服务打开、selector扫描或驱动动作。审阅patch仅在新独立文件应用，逐字节复现corrected完整源，活动patch/源码不改。

真实iOS用户ABI注解：kern_return_t4B、size_t8B、port4B、params24/info64、共有字段max_bo_bytes16/va_start24/flags56；实际Darwin23冻结recipe/kernel头另编注解测得IOExternalMethodArguments248B、inputSize offset56/outputSize96，两个counter均4B，与用户size_t分开，不猜MIG行为。共4新对象独立重编SHA一致；依赖user295/native-call291/defaultOFF287/kernel356。原生调用注解对象具有真实IOConnectCallStructMethod relocation，但不链接进关闭程序、不执行或部署。

最终关闭程序仍arm64/IOS2/minOS17/sdk27，仅libSystem且无IOKit调用导入/新initializer；保留preflight函数只返回真实header的NotReady，改坏其返回常量的独立最终文件被拒。main将恒定preflight结果折叠，仅保留两项method输出尺寸检查；不把它冒充实际KMD启动拒绝路径或完整图穷尽。第一次host缺显式Mac SDK的真头失败保留，改用实际xcrun SDK；初链接保留无用libc++的旧二进制/audit失败保留，正常dead_strip_dylibs后最终闭合，旧独立对象按完整SHA复用，无guard放宽。

原342/190、冻结255/raw231、原88/default42和前轮导入归档保持，last run仍recovered；无活动源/FD/kernel/ADT/手机/boot/GPU/物理操作，allow_boot/readback=false。下一具体准备实际完整Turnip runtime source闭合/目标构建，先在K80隔离tu_knl_darwin_load入口无条件拒绝、早于dw_open_connection，保留输出长度修订为单独新diff；不把SDK/libdylib/独立用户caller当真实平台资格。AIR/Metal/native所有权、可读最早失败与规范完整候选门槛仍缺。[证据](evidence/gpu-A750-Turnip-call-boundary-2026-10-31.json)。


## 真实Turnip runtime隔离构建与K80关闭入口完成（2026-10-31）

out/zorn/gpu-A750-Turnip-closed-runtime从既有3250项iOS源码独立导出，补齐Mesa85fda3b的Vulkan/runtime/DRM/subprojects四个真实Git tree：427项/9,721,664B，其中393项新增；原始3643项完整应用9个原补丁，独立逆序还原到原字节。输出长度修正与K80 tu_knl_darwin_load无条件拒绝分别保留新diff，两个patch从前轮完整原KMD精确复现当前3646项源码中的完整KMD。原活动源码/9patch/旧manifest不改。

新固定主机依赖glslang16.0.0 a57276bf/tree cfec6b90，3131项/42,999,966B逐Git tree验证，真实49步工具构建；采用上游支持的无external optimizer/HLSL/tests选项，GLSL/SPIRV功能保留，未绕Mesa最低版本/--no-link/depfile检查。完整install因未构建兼容静态archive拒绝，保留错误后仅执行上游StandAlone安装规则；glslangValidator为上游创建的工具别名symlink。-Olib属于Mesa脚本并转换--no-link，不假设它是glslang直接参数。精确AIR LLVM23.1.3约束未改、未下载LLVM。

采用原runtime iOS配方release/NDEBUG，而非旧IR3 debugoptimized；真实arm64/iOS17部署/SDK27，wrap-mode=nodownload。实际libvulkan_freedreno.dylib为17,859,456B，SHA e69c6ed4728be4ae523e50911cfa8e2cb81aa0d2309b1c9cc095632756bae119；550目标对象、20archives/513成员和2405实际依赖绑定，三项实际glslang SPIRV生成头单列。完整KMD TU独立重编全SHA一致；最终KMD函数为MOVN w0,#8/RET，实际返回VK_ERROR_INCOMPATIBLE_DRIVER(-9)，早于原native open。完整TU改成功、最终库改成功、最终minOS18三突变均由同正例检查拒绝。没有加载/执行目标库、native服务或GPU。

最终导出真实Vulkan ICD入口，无本库initializer section/IOConnect或IOService导入；不据此宣称所有其他入口/依赖framework可安全执行。原patch明确保留dynamic_lookup选项，5571动态查找项全为原始弱引用，0强项；另241项导入指向8个framework/dylib（含3项弱libc）。它们不是旧IR3仅libSystem导入资格的延伸，optional dispatch和真正iOS17框架可用性未验收。新source-manifest/profile ID明确不同于原builder的Git-diff ID，无builtin pack输入/重标记，不称完整原脚本调用、原17SDK、AIR/frontend/Metal/GPU完成。

首次cross单引号格式、直接Ninja漏传已存PATH导致Mako失败、注解负控制过早同名return、将生成头当对象等错误均保存并按真实类型/实际配方修正，没有放宽provider或保护门。342/190、冻结255/raw231、88源/default42、840旧tools及前轮绑定保持；last run仍recovered。无新kernel/FD/ADT/boot/phone，allow_boot/readback=false。下一项只核对这个新runtime的实际public caller→关闭KMD路径和新增导入，复用已有精确归档，不重放旧134/编译/CPU/GUI/内存/缓存库存套件。[证据](evidence/gpu-A750-Turnip-closed-runtime-2026-10-31.json)。


## Turnip真实公共创建入口关闭及新增导入边界（2026-10-31）

out/zorn/gpu-A750-Turnip-public-closure发现前阶段KMD拒绝不等于公共启动拒绝：原实际CreateInstance先环境/allocator/instance初始化并可返回成功，common枚举实际接受0/-9，未找到设备可成功返回零设备。这是源码/最终CFG推导，不是执行观察。新隔离实际tu_CreateInstance在tu_env_init前无条件返回VK_ERROR_INITIALIZATION_FAILED(-3)，不读写参数/输出或分配，原KMD -9保持。源码patch独立精确复现，不改活动源或已冻结前阶段源。

只重编tu_device和使用源码身份的tu_builtin_cache两个实际完整TU；其他35个受同宏影响的TU按新旧identity预处理字节一致，复用原对象。新source-profile e3fe9ae2530bbcad40ac32890f69bc52c96a5468288d68db9ae73e766713b356真实绑定此次source delta，缓存guard不改、无pack重标。新库17,859,240B，SHA 2b37193be5f4bf703b209ef15067fb7a8f3b6fe888d22490f752dbc401221000，两个新TU独立重编SHA一致，依赖1056/1021。最终两public loader的实际ADRP/ADD/table地址及tail B目标、CreateInstance首slot内部rebase到立即-3/RET及原KMD-9通过；公共返回改成功/slot改到异原型KMD/loader尾跳改目标/弱flat导入标志清除四个真实最终文件突变拒绝。绑定实际名称lookup源和最终body，但不宣称全部strcmp/CFG穷尽或所有其他入口/framework可执行。

新库实际是LC_DYLD_INFO_ONLY传统流，不是旧IR3 chained格式：5812原nlist导入与5817绑定位置对上，22176rebase均在本image内；212个lazy stub-helper初始rebase与lazy bind重叠是实际格式，单独保留。5571flat lookup均弱/0强，另241普通导入。133项继承旧精确libSystem证据，51个新名仅用既有SHA归档头/trie解析，57项因7framework/dylib及libsystem_symptoms重导出尚未归档而未知，不说原OS不存在；没有重放旧134/cache库存/签名块套件，也未新挂载/读取OS镜像。后续明确8provider/57query、只读源UUID/section/挂载持有/新块归档和读回上限见新计划。

初解析器误用chained假设、Python整数未按实际dyld uint64回绕以及误拒lazy初始重定位的错误/修正保留，未知reexport不造成功。一次复用旧audit-runtime模块意外触发其顶层重审计/同字节生成文件，8211旧文件和5symlink逐项确认SHA/文本未变；已改只AST提取解析函数，修正版仅复用新独立对象并重查新候选。此事件不冒称未重跑旧审计。342/190、冻结255/raw231、88/default42保持，last run仍recovered。无target load/执行、手机、GPU、kernel/FD/ABI扩展，allow_boot/readback=false。[证据](evidence/gpu-A750-Turnip-public-closure-2026-10-31.json)。


## 新Turnip库剩余57项原系统导出归档完成（2026-10-31）

out/zorn/gpu-A750-Turnip-provider-exports只处理新库2b37193b剩余57项资料：按既定RAW section11874304,6451200只读挂载本地原SystemOS，fresh UUID8846FE78-2910-4297-AF97-D59BB6F8FC16/Writable=false及源size/mtime核对后，复用原路径/映射元数据和旧SHA归档，不调用旧Cache库存构造器。实际读取11个新影像（8provider与真正需要的libc++abi/libunwind/libsystem_trace等路径），新资料335,464B/41capture；8个源cache文件UUID/尺寸/签名位置匹配，48个新完整签名块共786,432B按原CodeDirectory hash通过。非全image/cache SHA或Apple信任验收。

只卸载本轮attach返回并持有的raw disk，挂载点cache路径消失、source size/mtime保持，再纯归档重解析43个所需原影像头（11新+32继承），57个完整原导出/reexport链和provider requested-compatibility/current-version全部匹配，无missing。57个terminal export中55普通/2弱定义，0新resolver要求；旧184项已有resolver/weak事实不被清零。新capture字节/完整签名块字节/实际Metal terminal export边三损坏控制均被拒。此前133继承+51既有归档新名+本次57，使241普通导入的原OS名称资料闭合；5571weak flat slots、所有函数ABI/loadability/运行/硬件资格仍未验收。

首次sandbox diskutil框架不可用/空plist失败保留；随后只读授权查询确认身份。初raw设备选择错误期待GPT hint而被拒，实际固定APFS section无此hint，改以本次attach确切raw及verified child绑定；没有猜设备或访问手机。hdiutil detach成功并保留deprecated警告。无旧134/cache库存/137签名块套件重放、无compiler/CPU/GUI/内存重复，342/190、冻结255/raw231、88/default42/前79绑定保持，last run仍recovered。

下一项转actual production frontend→Rust/C startup consumer及失败传播：已只读核对AdrenoMetal454ff2ce的NativeBridgeMetalFrontend.mm、NativeMetalObjects.rs/h及真实build recipe，文件与该component HEAD一致，board尚未选择该component。frontend对空Rust device目前返回nil，但实际Device::system_default_with/loader内部路径仍待精确绑定；不假设有缺陷或伪造设备。原builder会删输出/改源/生成旧replay/AIR/签名和daemon/job数据，未执行，下一阶段只隔离必要源码/真实类型目标工作。无target load/执行、phone、GPU、kernel/FD/ABI扩展，public CreateInstance -3/KMD -9和allow_boot/readback=false保持。[证据](evidence/gpu-A750-Turnip-provider-exports-2026-10-31.json)。


## 真实前端启动失败路径及正确gitlink源码绑定（2026-10-31）

out/zorn/gpu-A750-frontend-startup发现根UniXNU066c8d8的AdrenoMetal gitlink实际为ce5e19e，而活动组件仍454ff2c，仅7补丁，不足以满足真实bridge builder的16补丁列表。先前454参考编译保留但不冒充当前配方；不切换活动检出，按精确gitlink取得必要23文件/399,175B及16补丁，逐Git tree/blob核对。固定metal2vulkan720ef1ce只取5个启动/错误源码blob共266,268B和两个真实Cargo.toml。五文件受16序列中第3/9/13号相关hunk投影影响，精确应用并独立反向还原；不是整个runtime/16patch完整构建。

实际Device::system_default_with→group?→create_instance在ash返回-3时走vulkan(error)，Error::Vulkan(VkResultCode(i32))保留原值；-9单独变NoDevice。选定ce5e Rust nmb_device_open把该错误格式化后由guard保存每线程原因并返回null，前端取nmb_last_error并返回nil。该论断是实际源码条件路径，未执行或编译Rust/ash，不假设此前cache/options/loader初始化已成功，也不把未构造InstanceShared当任意GPU停止/库卸载证明。没有发现应修改生产源才能传递该失败的缺陷。

正确ce5e完整NativeBridgeMetalFrontend.mm及真实C/ObjC头ABI注解按arm64/iOS17部署/SDK27构建，两个对象独立重编完整SHA一致；实际依赖1309/597。真实头证明opaque device*/函数指针/size_t/id/SEL等均8B、bool1B，不伪造Rust/Metal/Vulkan布局。完整目标对象的nmb_device_open调用relocation、结果CBZ x0、原每线程原因调用和nil选择验证通过；移除实际目标CBZ、调错producer relocation、错配实际头返回类型、删除Rust raw状态映射四控制拒绝，最后一项仅source guard不是Rust编译。对象含__mod_init_func及大量真实活跃方法，不加载/链接部署，不把对象编译当整插件/所有入口可执行或完整CFG证明。

只读工具检查显示本机stable rustc1.98.1，缺配方精确1.98.0及aarch64-apple-ios std，固定producer无root Cargo.lock、ash声明0.38范围/std+loaded，未冒称完整锁定依赖。未用+语法触发安装、不替换版本、不Cargo下载或完整Rust桥构建；原builder会改源/生成旧replay/AIR/签名/daemon/job，未执行。下一项准备精确Rust/startup依赖及实际loader/drop前提证据，保存noLLVMdownload/23.1.3约束，不重复本轮对象或旧编译/缓存/CPU/GUI/内存轮。

142前轮绑定、342/190、冻结255/raw231、88/default42及活动454检出保持，last run仍recovered。无新source mount、kernel/FD/ADT/phone/boot/GPU/ABI扩展，board仍未选择AdrenoMetal，原public CreateInstance-3/KMD-9与allow_boot/readback=false保持。[证据](evidence/gpu-A750-frontend-startup-2026-10-31.json)。


## 精确Rust与实际ash loader依赖绑定（2026-10-31）

out/zorn/gpu-A750-rust-startup-dependencies按官方Rust1.98.0版本清单/SHA取得4个固定包：116,767,648B压缩、593,827,323B展开，先核字节/磁盘上限，再拒绝路径穿越/链接并按原component manifest复制204文件到独立prefix；未执行install.sh或改rustup/Cargo全局配置。精确rustc1.98.0与iOS标准库可用。Rust包自带LLVM22.1.8编译后端，不是AIR要求的LLVM23.1.3，没有独立LLVM下载/版本替代。

固定producer无Cargo.lock，故本轮明确新增候选pins：ash0.38.0+1.3.281、libloading0.8.9、cfg-if1.0.4，官方索引checksum/167源码文件绑定。不是原producer锁，也没有Cargo解析/latest或无界下载。直接rustc按iOS unix/ash std+loaded+隐式libloading特性构建3个真实完整crate和真实ash类型的独立注解，各自两份目标SHA相同；不含windows/dev/optional core依赖。实际ash build.rs只有linked特性下发Vulkan链接指令，未启用；独立host IR main为空，未执行脚本。不是完整producer runtime/bridge或最终插件链接。

注解目标确认真实ash CreateInstance：非零原i32状态直接写入错误结果，只有零成功分支调用Instance::load；iOS部署17.0而对象SDK字段0，不冒称SDK27。实际dlopen/dlsym及flags5、Entry Arc最终释放→真实libloading Unix Drop→dlclose调用链核对；不是库成功卸载、可中断有界close、GPU停止/租约证明。两实际对象分支/状态存储突变、真实头类型宽度错误编译和真实Drop分支突变四控制拒绝。最初checker误认dlclose已内联到ash、显式特性闭合及build.rs存在性拒绝均保存原脚本/日志/产物，按真实链纠正，没有改provider或放宽原guard。

额外只取固定Git blob keeper.rs/loader_word.rs共7,611B，核对选定16补丁不改它们。keeper只在device成功后克隆Entry并保留bare instance，不能覆盖最初-3失败；loader_word的真实handle读写前提仍未满足，未编译/执行它。库初始化可在CreateInstance-3前发生；失败Entry最后Arc释放可能dlclose并丢弃close状态。producer open_loader还丢弃各次ash LoadingError，仅保留tried路径；本轮如实记录，没有新增错误codec或改失败语义。下一项绑定实际CacheSetup/choose/Host/MetalLevel这些早于loader的源码/副作用前提，不重复已完成编译或旧缓存/CPU/GUI/内存轮。

前轮143绑定、342/190、冻结255/raw231、88/default42及活动454检出不变。新编译源仅隔离out，无库加载、最终plugin/FD/kernel/phone/boot/GPU/Metal执行；board仍未选择AdrenoMetal，canonical/readable保护和真实平台所有权未闭合，allow_boot/readback=false。[证据](evidence/gpu-A750-rust-startup-dependencies-2026-10-31.json)。


## 真实早期缓存与MetalLevel前提绑定（2026-11-01）

out/zorn/gpu-A750-startup-preconditions只按固定metal2vulkan720ef1ce取得metal_level.rs及shader_cache/mod.rs、store.rs共3个Git验证blob/64,120B；shader_cache树独立重算Git SHA。选定16补丁中仅第3号触及这3文件中的mod.rs，全部相关hunk按fuzz0/无offset投影并精确逆向还原，不是完整16patch/runtime构建。

真实system_default_with顺序为CacheSetup::of→choose(asked,Host::this())→group→create_instance→open_loader。CacheSetup先拒capacity/memory零，再clone显式目录或取平台默认路径；显式路径没有absolute/containment/Data UUID/所有者/no-follow检查。Directory::open先递归创建root及root/v1/真实build哈希目录（0700），再create_new探针（0600）、写5字节probe并尝试remove；即使创建/写失败仍尝试删除该路径，最后written.and(removed)返回错误。现有目录权限不因此修复，源没有证明路径/删除对象属于当前调用者。未执行这些操作，也没有宣称修复或路径授权。默认容量25GiB/内存256MiB不是预分配、Data窗口资格或允许扩写。

实际iOS cfg的Host::this为Other；默认缓存取绝对XDG_CACHE_HOME/metal2vulkan或绝对HOME/.cache/metal2vulkan，缺有效HOME保留实际ShaderCacheError。所选前端明确传in_directory并设置MetalLevel::NEWEST=MacOS27_0_1（Apple M4参考表）；choose先返回Asked，不是K80/guest能力测量，不猜一个替代档位。this_build还依赖真实Cargo版本/translator digest/生成runtime source ID，未伪造哈希或闭合完整CacheSetup/choose。

仅将真实Host、MetalLevel enum+NEWEST、ShaderCacheOptions/default_directory/实际ShaderCacheError及三个真实私有fs helper按原item字节提取，增加隔离typed注解，精确Rust1.98.0/producer edition2021/iOS17编译；两份目标完整SHA相同。SDK字段0，不冒称SDK27；实际Host Other/NEWEST常量、0700/0600及标准库调用边核对，3个实际对象突变及1个source-only绝对路径guard突变拒绝。没有伪造Rust类型/文件系统/host模型，也未编译完整CacheSetup/Directory::open/choose、运行fs helper或加载对象。首次注解误用edition2024被编译器拒绝，按真实2021修正并保留；unique源片段的首次行边界checker错误按精确字节/SHA纠正，原源/目标未改。

前轮488绑定、342/190、冻结255/raw231、88/default42及活动454检出保持，13项record与两仓库diff/link检查通过。下一项只按已归档ce5e树取实际NativeAdrenoMetalPlugin.mm caller，追loader/cache实参及拒绝前副作用；不执行原builder/daemon/job/sign/AIR流程。无手机/启动/GPU/Metal/存储执行、完整Rust桥或新kernel/FD，board仍未选AdrenoMetal；路径所有权和canonical/可读失败保护不合格，allow_boot/readback=false。[证据](evidence/gpu-A750-startup-preconditions-2026-11-01.json)。


## 真实插件caller与隔离默认拒绝入口（2026-11-01）

out/zorn/gpu-A750-plugin-caller按既有ce5e树只取NativeAdrenoMetalPlugin.mm和必要NativeTurnipSmoke/CacheExport/ExceptionDiag头，4个Git验证blob/80,107B，未使用活动454头充当当前源。实际turnip::libraryPath从dladdr所在插件目录拼libvulkan_freedreno.dylib，R_OK不等于SHA/profile/加载资格。实际publish分支在桥之前设异常handler、环境/CFPreferences、retain/查IOKit port、makeGpu/mark，尝试缓存和可选pack导入；publicCreateInstance-3/KMD-9没有覆盖这些更早副作用。无publish标记反而会开旧adrenoUserTest线程，不是安全关闭模式。后续原硬编码QuartzCore地址读写/旧显示试验没有移植或运行。

backboardd候选实际顺序为passwd-home Library/Caches/com.apple.backboardd/m2v、confstr用户cache/m2v、confstr用户temp/m2v、/tmp/m2v、/private/var/tmp/m2v，最多5次桥尝试；列名client只试前两项，最多2次。W_OK检查没有Data UUID/窗口/路径/符号链接所有权证明。可选NativeAdrenoMetal.m2vpack先dlopen libz并读包、mkdir、写.import后rename/unlink，再调用桥；未执行或扩展任何pack/日志codec。deviceForPort静态tried及frontend既有gDeviceObject短路只是源语义，不是lease/ready。

新增UNAPPLIED隔离保护：完整翻译单元默认ZORN_GPU_PLUGIN_ENTRY_ALLOWED=0，仅保留真实原类声明和nil init入口，所有原26,233B插件源逐字节保留在inactive else；任何非零宏值编译#error拒绝。原活动源/board/builder均未改。实际完整OFF候选按iOS17/SDK27原ARC/C++17/Werror配方独立编两份，完整SHA一致，595项真实SDK/源输入绑定。实际入口24B，一次objc_release后返回nil；这是ARC消费init receiver的真实释放，dealloc副作用和私有_MTLDevice ABI未证明，ObjC类元数据仍存在，不能加载/注册或冒称无调用。不是legacy ON/完整Rust桥/最终plugin构建。

两实际对象破坏nil/ARC调用、非零激活编译拒绝及原publish模式source-only控制共4项通过；补丁fuzz0/无offset正向及逆向精确。初方法投影产物与ARC发现保留，随后把保护放至整TU。首次MMD没有SDK头而资格检查拒绝，改MD完整输入清单并核对对象原SHA不变，错误/脚本/对象均保留，未改provider/ABI或放宽Werror。下一项只读绑定实际RamBlock/persistent Data/union路由与这些缓存实参，保留动态confstr/sandbox/ownership未知，不mount/扫描设备，不重复旧Data/CPU/GUI/内存资格。

前轮65绑定、342/190、冻结255/raw231、88/default42及活动454保持，record13项与两仓库diff/link检查通过。无目标加载、IOKit/存储/phone/boot/GPU/Metal执行或新FD/kernel，board未选AdrenoMetal；完整canonical/早期可读失败和真实平台所有权仍缺，allow_boot/readback=false。[证据](evidence/gpu-A750-plugin-caller-2026-11-01.json)。


## GPU缓存写入的实际Data/union源码路由（2026-11-01）

out/zorn/gpu-A750-cache-route只读绑定25个真实源/配置文件及独立副本，12项与已消耗0fe声明输入完整SHA一致（含kern_exec、UFS桥与Data策略）。当前RamBlock源/对象同既有bindings-audit，8GiB seed UUID/hash同实际owner-data-volume.h/expected.S；没有重审旧最终内核函数或重跑Data/CPU/GUI/内存轮。真实clang-MJ编译元数据尾随逗号按原格式读取，记录union/Data/nativeRamBlock宏；根format2、compat及冻结legacy输入分开，未冒称完整等价。

实际源码先将SystemOS UUID8846FE78-2910-4297-AF97-D59BB6F8FC16以MNT_RDONLY|MNT_UNION接到/，要求原生union关系；再经唯一typed IOMedia/NativeRamBlock seed size/hash识别Data，在/private/var挂APFS，检查mounted dev、非readonly、f_uuid及原Data probe后才继续launchd。原VFS lookup在union上ENOENT才遍历下层；这不是自动把所有临时目录写入Data。RamBlock direct IO经既有native_ufs_store桥进入K80写窗口策略，mode2、192GiB相对起点50331648、2097217×4KiB窗口（1头+64bitmap+2097152逻辑页）保持；原UUID/cookie2dde8229未重读/重置/扩展。无新的存储授权或文件操作。

只有字面路径/private/var/tmp/m2v位于Data mountpoint下，仍须真实子目录vnode/卷、符号链接、替换、sandbox及所有者证明。/tmp/m2v的原镜像symlink/mount未在本轮观测，不假设其等同Data；passwd-home及confstr user cache/temp完全是运行时值，不能从源码推成/var/mobile或Data。旧Data成功挂载/一次probe及底层块界限不构成某进程cache dirfd或独占清理lease；所有缓存候选WriteAuthorized仍0。

真实挂载目标改到/private/tmp、去掉VFS UUID比较两源级负控制拒绝；仅检查源不执行旧探针/系统调用，不造路径/handle成功。下一项核对Darwin23实际attrlist/fd/statfs实现与真SDK声明，准备调用关闭的只读目录/卷身份ABI；真实只读身份也不自动授权写入，不扩query/日志codec/carrier。首轮绝对路径过滤误匹配macData前缀导致多打印输入，已按relative path和外部Mu路径边界纠正；原源/旧清单均未改。

前轮682绑定、342/190、冻结255/raw231、88/default42保持，13项record及两仓库diff/link检查通过。没有新target/kernel/FD构建、source mount/扫描、文件系统/手机/启动/GPU/Metal操作，默认拒绝插件补丁仍UNAPPLIED，canonical/早期可读失败/真实平台lease保持不合格，allow_boot/readback=false。[证据](evidence/gpu-A750-cache-route-2026-11-01.json)。


## 缓存只读身份ABI配置（2026-11-01）

固定Darwin23 attrlist实现与真实SDK头绑定：fgetattrlist对vnode fd进入卷属性路径，非根vnode以VFS_ROOT替代，未支持属性被过滤；必须核对returned bits及fullsize长度，不能把40B请求形状/零UUID视为成功。LP64 options为unsigned int32而非unsigned long64，实际原型static_assert及错误宽度编译拒绝通过。真实attrlist请求配置与只读open标志注解独立编译iOS17对象SHA相同，无未解析syscall符号，WriteAuthorized恒0；未调用任何fs/native API或观察UUID。没有新增传输/日志codec。机主明确长期离机，current记录无人辅助条件；需要物理协助或有界回收失败时停止设备操作并通知。下一项仅隔离真实类型的结果验证，调用仍关闭。无手机/boot/GPU执行，allow_boot/readback=false。[证据](evidence/gpu-A750-cache-identity-abi-2026-11-01.json)。


## 原生attrlist结果验证隔离实现（2026-11-01）

实际attribute_set_t私有验证器已实现：要求captured/raw status成功、供给和报告长度均40B、returned common/volume及其他group形状正确、UUID非零。只判断原生缓冲形状，不输出owner/lease，WriteAuthorized恒0；调用仍关闭，不发布新wire/query/log/carrier。两份iOS17目标对象SHA一致，77项malformed/unavailable纯数据ASan/UBSan检查通过，没有构造有效owner成功fixture或执行任何fs/native调用。稳定可读buffer是前提，不声称任意指针认证。下一项只从既有原iOS17归档核对fgetattrlist/fstatfs等实际used export，不重复旧import套件。机主长期不在手机旁条件保持，无手机/启动/GPU执行，allow_boot/readback=false。[证据](evidence/gpu-A750-cache-result-validation-2026-11-01.json)。


## 两个只读文件系统used export归档绑定（2026-11-01）

真实SDK引用注解的未解析名称确认为_fgetattrlist/_fstatfs，两份iOS17对象SHA一致。仅解析这两个symbol：既有原iOS17 libSystem通过LC_REEXPORT_DYLIB指向libsystem_kernel普通export；为按真实顺序排除前置reexport，读取30个既有image头/trie、核对54个已归档完整签名块。没有重放134/241导入套件、重挂源镜像、源扫描或新增原系统读取。export元数据不证明函数体ABI、Apple信任、可安全加载或运行。初注解缺unistd/auto C-linkage的Werror拒绝日志保留，改为真实类型而未放宽警告。

保护hash342/190、冻结255/raw231、88/default42保持。没有native/fs/phone/boot/GPU执行或UUID观测，WriteAuthorized0；UEFI handle不是userspace fd，插件早期副作用与可读失败保护仍不合格。下一项只允许最小真实只读fd caller源接合，先核对errno与statfs语义，调用关闭；若不能填具体源码缺口则转真实平台provider，不再扩cache诊断。机主长期离机条件不变，allow_boot/readback=false。[证据](evidence/gpu-A750-cache-used-exports-2026-11-01.json)。


## 只读fd caller边界收束，返回原生Service入口（2026-11-01）

已绑定真实Darwin23 errno/TSD/cerror与statfs实现及SDK声明：errno只在真实错误路径即时读取才有意义，成功不保证清零；fstatfs会经MAC检查、更新VFS统计再拷贝，并非已证明无副作用或墙钟有界。实际fsid字段8B、UUID16B，flags/type/owner均不能代替卷UUID或目录独占/清理权。两份纯声明iOS17对象SHA一致，无syscall导入或执行。现有GPU路径没有真实持有的userspace目录fd、合格受保护调用点及原始错误报告接合；因此没有新增游离cache caller/报告或有效owner模型，按既定分支结束cache预备，不再扩errno/export/openat/测试。

下一项回到真实Gen7 native Service入口，先追selected IOKit在probe/start前的provider getResources接收者和实际资源动作；不能假定给GPU Service加override就控制provider。保留已有pair caller/报告/once与全部保护，不重做旧轮。329旧绑定及342/190、冻结255/raw231、88/default42核对通过；机主长期离机，无native/fs/phone/启动/GPU操作，allow_boot/readback=false。[证据](evidence/gpu-A750-fd-caller-boundary-2026-11-01.json)。


## 原生匹配前资源拒绝的隔离候选（2026-11-01）

真实IOService::doServiceMatch在provider上调用getResources，之后才probeCandidates、alloc/init/attach候选并调用probe。新隔离ON在该共同调用点按两个提议GPU/GMU完整名称拒绝，跳入原matches释放路径；因此不依赖给候选GPU Service覆写getResources。OFF与当前源码字节相同，补丁正反向fuzz0准确；未改活动源/节点/镜像。真实完整IOService配方462递归依赖、两独立对象SHA一致；实际对象guard跳转/调用重定位/名称检查及分支反转、名称破坏两副本拒绝通过。初隔离路径缺IOServicePrivate.h的失败保留，恢复原源目录quote搜索，未放宽原警告/特性。

此拒绝只覆盖两个名称及此调用点，不是GPU身份/权限，也不覆盖未知或重命名节点、前置notifier/元数据动作、其他入口、完整CFG/PAGE或运行时。公开IOPlatformDevice路径已有源证据，但配置选中原AppleARMPlatform，其实际私有nub/override仍未绑定；下一项仅追现有prelink原字节来源，不能把公开实现当原二进制。272旧绑定及342/190、冻结255/raw231、88/default42保持；机主长期离机，无native/手机/启动/GPU操作，allow_boot/readback=false。[证据](evidence/gpu-Gen7-prematch-containment-2026-11-01.json)。


## 原AppleARMPlatform nub来源绑定（2026-11-01）

固定原kernelcache完整SHA与既有compat pin一致，使用原reader纯函数读取AppleARMPlatform1.0.2的原prelink元数据：AppleARMPE personality匹配IOPlatformExpertDevice/AppleARM，score1000。原模块nlist和字符串表均0，不能由无符号推断getResources/createNub等方法不存在；公开IODT实现仍不是原私有实现证明。只归档必要header/prelink元数据、37个init指针及64B窗口，4个含先行调用的窗口按512B固定预算补读。实际AppleARMPE字面量在initializer11的直接BL前定位，尚未绑定call target ABI/父类/vtable。未知initializer27未超预算追读。

原parent objdump窗口没有输出prelink指令的事实保留，改用已有llvm-mc解码捕获原字节；初版错误要求RET的拒绝保留，修为RET或tail B止读而未扩大预算。没有执行emitter/plan/旧KC套件、挂载镜像、调用原函数、改原二进制或启动手机。下一项只解这一个原BL stub/GOT及真实registration ABI，不猜私有槽。499旧绑定及342/190、冻结255/raw231、88/default42保持，机主长期离机，allow_boot/readback=false。[证据](evidence/gpu-Gen7-original-platform-nub-2026-11-01.json)。


## 原AppleARMPE注册调用与父类绑定（2026-11-01）

精确原BL→12B stub→8B GOT指向原导出OSMetaClass三参数构造函数；实际x0/x1/x2/w3参数绑定为原MetaClass对象、AppleARMPE字面量、IODTPlatformExpert::gMetaClass、296B。对应两个原public nlist/name记录已归档并逐范围读回，真实Darwin23头/构造源的原型相符。只绑定该used constructor，不声称完整原Apple ABI。后续vptr写入属于MetaClass对象而非AppleARMPE实例；父类注册也不证明没有私有nub/resource override，未创建任何原对象或执行函数。

下一项先用真实公共类型目标注解与原public vtable/导出对照used dispatch，才能解释私有MetaClass alloc，禁止猜槽或按296B重造私有类。此前78绑定及342/190、冻结255/raw231、88/default42保持，没有旧套件/initializer27扩展或手机/native/GPU操作；拒绝候选仍UNAPPLIED，机主长期离机，allow_boot/readback=false。[证据](evidence/gpu-Gen7-AppleARMPE-registration-2026-11-01.json)。


## 三个公共dispatch与原AppleARMPE实例两槽绑定（2026-11-01）

真实Darwin23公共类型alloc/getNubResources/createNub注解按原native配方独立目标编译SHA一致；实际9指令三个调用槽与原具名OSMetaClass/IODT虚表逐项相符，两份移槽对象拒绝。由既证MetaClass子对象注册继续只读定位原alloc：原typed new→具名IODTPlatformExpert C2→实例vptr写入→instanceConstructed，未执行分配/构造。原AppleARMPE实例虚表两个对应槽确实指向原IODT getNubResources/createNub，而非用公开源码猜私有槽。

原getNubResources窗口还证实直接BL到IODTResolveAddressing；不构成运行时nub/映射/lease。createNub128B只读前缀遇到的是内部B，初tail标签已保留并修正，尚未证明完整路径；下一项按固定<=512B只追这一个函数及实际nub getResources接收者。没有重做旧表/套件/手机轮，27旧绑定及342/190、冻结255/raw231、88/default42保持，活动源/拒绝候选状态不变，allow_boot/readback=false。[证据](evidence/gpu-Gen7-public-dispatch-ABI-2026-11-01.json)。


## 原nub工厂与getResources接收者链绑定（2026-11-01）

原createNub固定512B窗口中，具名下一函数界定240B工厂体，RET在236；原vptr写入精确等于具名IOPlatformDevice虚表+16，选定内部跳转均核对，独占更新倒跳仍非墙钟有界。实际公共getResources/getProvider目标注解各两份SHA一致，原基类槽及nub槽逐项对应。派生getResources无可用export名，初按名字读取的失败保留，改由已证虚表槽读原13条指令：保存nub→getProvider→用返回的provider调getNubResources并传原nub。没有构造/执行对象或模拟成功。

这仍是原文件链。实际NativePrelink会按具名导出重绑组件到native kernel，下一项只核对AppleARMPE两个既定slot的原重定位表项和不可变0fe最终指针，不运行emitter/plan/旧KC套件、不重启0fe。391旧绑定及342/190、冻结255/raw231、88/default42保持；活动源/候选不变，无手机/native/GPU操作，allow_boot/readback=false。[证据](evidence/gpu-Gen7-original-nub-resource-chain-2026-11-01.json)。


## 两个保留组件到native最终指针闭合（2026-11-01）

AppleARMPE原getNubResources/createNub两site均在原KASLR重定位表，按既有compat slide和具名唯一绑定，直接读不可变0fe最终两个8B指针，分别精确等于该内核的native IODT对应函数地址。只证明已消耗旧镜像的两个静态边，没有运行plan/emitter/构建/旧候选，不能当新kernel或当前live ABI/所有权。此前381绑定及342/190、冻结255/raw231、88/default42保持。

已核对实际Service→pair→binder→NativePrepare缺口：仍Missingff/InvokeAllowed0/RuntimeComplete0/NotReady，8类真实平台provider不因指针闭合而补足。下一项不再扩ABI库存，而做最小隔离原生CPU源码接合：复用真实只读固件与原builder/requirements函数，把资源描述与固定SHA plan接入现有private caller；不调用旧内存prepare，不新增公共报告/传输，不授权start/map/设备操作。机主长期离机，活动源/FD/kernel不变，allow_boot/readback=false。[证据](evidence/gpu-Gen7-two-native-pointer-edges-2026-11-01.json)。


## 原生现有caller的CPU固件资源接合（2026-11-01）

隔离PairCaller在真实binder资源描述有效后，复用四个原只读固件symbol和固定SHA plan builder，再调用现有DescribeRequirements。plan/scratch/requirements及raw尝试状态仅新增private成员，公共API尾部、560B报告和Service源码不变；once先于plan调用，原plan错误先存后判，requirements只在hash成功后尝试，错误/重复保留。startfalse/probenull/Missingff/InvokeAllowed0/runtime0不变，不是硬件provider或可运行候选。

六对真实独立目标对象SHA一致，405递归输入及10个原对象闭合所需内部调用/只读固件；新ABI注解不链接。4项真实源码投影的纯CPU接合ASan/UBSan检查通过（含原固件组合、重复保留、requirements拒绝、坏hash），未运行完整IOKit caller或旧plan/内存套件；2源码与3真实对象破坏拒绝。新helper局部frame128B非全链/墙钟保证。OFF3源字节相同，两源码patch正反准确，原活动源/default42及342/190、冻结255/raw231、88保持。下一项仅核对既有source-selection配方并形成隔离OFF selector接线，不启用新硬件路径/报告。机主长期离机，无手机/boot/GPU执行，allow_boot/readback=false。[证据](evidence/gpu-Gen7-native-cpu-caller-join-2026-11-01.json)。


## Gen7现有caller源码选择器隔离接线（2026-11-01）

规范compat路线仍只有build-zorn-ufs→gpu-owned组件；root debug只核对归档其build.json，没有新Gen7 caller/Service选择。通用Adreno740及XNU_NATIVE_ADRENO仍是Sm8550/Sheng依赖和旧archive，不能作为K80新闭合路线。此次只给已有隔离pair暂存入口形成默认关闭的UNAPPLIED补丁，显式cpu-firmware-join依赖pair-prepare；新cpu-on独立新目录拒绝重复，防残留私有header/Service混用。

默认OFF4文件、原pair4文件逐字节相同，新caller/header/Service3文件与已验收版本一致；另3个companion/ADT文件保持。缺pair选项、重复目录、源码pin、pair对象和Service对象5项拒绝通过，补丁正反fuzz0准确。清单绑定先前真实目标配方/405依赖/6对象/10共用只读对象，只作来源参考，本轮没有新编译/链接/目标执行或规范archive选择。下一项实现默认关闭的隔离build helper，配套重编译选定caller/Service并核对与gpu-owned的重复符号边界，不能将参考对象当新候选。调用/写授权/boot/readback均false；活动源、default42、342/190、冻结255/raw231及88保持，无手机操作。[证据](evidence/gpu-Gen7-caller-source-selector-2026-11-01.json)。


## Gen7隔离构建helper与共用对象冲突（2026-11-01）

新helper默认关闭返回空对象且不读manifest/创建目录/编译；开启只消费固定SHA选择清单，配套编译选定PairCaller和Service，保留新私有类布局来源及原560B报告。两对独立对象SHA一致，400递归输入；命令只替换已审查源码、include和输出/依赖路径，活动recipe及输出不改。重复目录和活动树输出拒绝，无完整archive/规范builder接入/加载执行。

实际nm强定义比较发现完整引用closure与gpu-owned有16个重叠，含plan、资源/requirements/snapshot、boardparser、SHA、decoder及8个固件名字，helper拒绝直接并入两组；仅新pair/Service本身不重叠。共用对象仍仅来源参考，不能按同名符号任取variant。四原stock文件、只读__TEXT,__const assembly及原object固定绑定，没有拷固件或执行。下一项只在隔离out对16项生产源/对象/flags和实际用到ABI做精确组合，单一定义或明确拒绝不等价variant；不扩ABI库存，不调用旧memoryprepare。342/190、冻结255/raw231、88/default42及原CPU/显示/触控/Data保护保持；无手机操作，allow_boot/readback=false。[证据](evidence/gpu-Gen7-isolated-build-helper-2026-11-01.json)。


## Gen7共用对象单一定义组合（2026-11-01）

16个重复强定义已按6组映射实际源、声明头、对象和原compile flags：plan/SHA/board/stock四组全对象相同；resource与decoder两组运行节逐字节、全部规范化重定位目标及定义位置相同，源/声明头也相同。调试节单独SHA保留；C decoder的LC_BUILD_VERSION平台2/最低17相同但SDK27与0不同，首次严格整命令比较正确拒绝后保留记录，最终选规范对象原metadata，不宣称整对象或metadata consumer等价。

默认OFF解析器返回空；开启只读选择19个对象引用union，16个共享强定义各一次，未归档/链接/加载或调用旧memoryprepare。实际指令修改、声明头修改、同名对象未知SDK三项独立拒绝通过，原对象不改。该19对象仅说明与旧owned组件的组合边界，不授权重启已消耗diagnostic；下一项从中去掉OwnedRuntime/OwnedMemory，按实际未解析符号形成最小Gen7-only隔离可重定位aggregate并审计，无新kernel/FD/候选/手机操作。342/190、冻结255/raw231、88/default42及CPU/触控/Data保护保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-common-object-composition-2026-11-01.json)。


## Gen7最小隔离aggregate及剩余自有导入（2026-11-01）

从19引用union排除旧OwnedRuntime/OwnedMemory后，以17对象完成一次独立目录ld-r；共享16强定义各一次，原四固件字节及sizeword一致，位于对象__TEXT,__const（不是最终页权限）。实际Service→NativeMemory两项发布/获取方法、NativeMemory→Cpu四项cache/query导入证明这两支支持对象为何被保留，但没有执行。

审计仍有2个自有实现导入：NativeAdrenoKernelTime::now_us与NativeAdrenoUserClient::dispatch，另236外部导入尚未新最终kernel验收。三个既有Service/GMU/SMMU metaclass initializer保留，不能说无初始化或可安全加载。probe实际立即null；坏固件独立对象副本及真实旧OwnedRuntime对象均拒绝，原对象不改。下一项仅追这2处实际callsite/源码，优先在现有fail-closed Service隔离消除不可达legacy依赖，必要才编确切CPU叶实现，不能拉入Sheng全archive。无规范builder/FD/kernel/加载/设备/GPU执行；342/190、冻结255/raw231、88/default42及CPU/显示/触控/Data保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-minimum-native-aggregate-2026-11-01.json)。


## Gen7现有Service两项自有导入闭合（2026-11-01）

真实2处BRANCH26来自未使用ring时钟和旧GpuClient action→core dispatch；当前probe=null/start=false且core_ready_无置true路径。仅在隔离ON版移除旧client类/工厂及未用clock定义，newUserClient无条件清空可用handler并返回原生NotReady；不是补成功stub或引入Sheng实现。Service完整类声明/私有数据、probe/start/stop及PairCaller源码/header不变，公共报告560B不变。

OFF3源逐字节相同，补丁正反fuzz0准确；2对独立目标对象SHA一致，新17对象可重定位aggregate不再有自有导入，仍211外部导入和3个既有TU metaclass initializer，不能称可加载/完整kernel或GPU执行。实际clear-handler/NotReady/return五指令核对，改坏返回指令副本及真实旧未闭合Service对象2拒绝通过；原四stock保持，旧OwnedRuntime/OwnedMemory仍排除。初编译后仅更正历史头注释，preimage/初对象保留，最终实际对象绑定更正源码。下一项形成固定build-zorn-ufs及debug manifest/归档消费的默认OFF隔离集成补丁，不先改活动源或跑完整builder。342/190、冻结255/raw231、88/default42和原CPU/触控/Data保护保持，无手机操作，allow_boot/readback=false。[证据](evidence/gpu-Gen7-Service-self-import-closure-2026-11-01.json)。


## 固定组件入口与输入归档消费隔离补丁（2026-11-01）

形成build-zorn-ufs组件入口、debug输入/归档消费及新增helper/17真实配方共4个UNAPPLIED补丁，默认关闭，两原脚本OFF逐字节相同。新Gen7选择与旧gpu-owned诊断冲突即拒绝；完整debug入口在启用profile时于main前明确拒绝，尚不支持新完整镜像，不隐式启动旧trial。

17对象全部从实际源新编，无旧对象复用，515绑定输入含9个真实Xcode头；初假设全部在workspace的检查正确拒绝，随后仅修正外部头归档namespace，原错误/源码保留，不重编同一批对象。实际新增consumer语句在隔离fixture路径消费533个输入及533归档映射，错SHA/旧诊断拒绝，4补丁正反准确。新可重定位组合无自有导入，共享16定义各一次及stock字节保持，仍211外部导入/3既有初始化入口。下一项把已完成prematch拒绝与新组件源选择绑定，并限定核对3初始化入口，不能缺拒绝保护就启用metaclass；不重做旧suite或改DT/ADT。无活动源/fullbuilder/FD/kernel/加载/手机/GPU执行，342/190、冻结255/raw231、88/default42及CPU/触控/Data保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-fixed-hook-integration-2026-11-01.json)。


## Gen7组件与匹配前拒绝源码绑定（2026-11-01）

复用已完成prematch源码/目标证明，不重编/重跑旧suite。新增默认OFF源码/报告/实际kernel路径检查：缺源码、当前活动OFF源码、缺prematch字段旧报告及把归档ON路径当实际kernel输入4种拒绝；三脚本OFF仍等于上一隔离版本，源补丁正反准确，新增policy也正反准确。两名称仅来自既有proposed resource-profile，与原拒绝名单相同，不改DT/ADT也不冒称live身份。

只查当前新编组件3个initializer，分别登记NativeAdrenoGpuService16144B、Gmu336B、Smmu336B，准确w3尺寸/类名及metaclass调用/vptr重定位已绑定，每入口一次OSMetaClass构造；真实尺寸指令副本破坏拒绝。登记会在匹配前执行且可有bookkeeping，不证明安全初始化/硬件权利。源profile仅派生构建元数据，旧17对象不重编，kernel_selected=false，完整builder拒绝不变。下一项补真实IOService目标对象与源码/配方/依赖关联检查，不能用归档target.o代替活动kernel输入。无活动源/fullbuilder/FD/kernel/加载/手机/GPU操作；342/190、冻结255/raw231、88/default42及CPU/触控/Data保护保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-prematch-source-binding-2026-11-01.json)。


## IOService目标与源码配方关联检查（2026-11-01）

读取实际IOService.cpo/json/cpd及当前源码身份，活动单元仍OFF且未改。只按真实选定flags重定向ON源码/独立输出并恢复原quote查找，实际编译一次新单元；462递归输入和SHA700661c9绑定。虽与原归档proof对象同SHA，也不把它当当前kernel对象。

新增源/对象/recipe/cmd/deps关联验证及组件消费要求。缺receipt、当前OFF源、旧实际对象、归档对象替代当前输出、错对象SHA、改flags、漏依赖、旧source-only组件共8项拒绝，已有脚本OFF保持和3补丁正反准确。旧17组件未重编，kernel_selected=false，完整builder拒绝不变。receipt是本地无签名构建来源，不是认证执行/GPU权利；下一项仅在实际编译记录产生步骤设计默认OFF成功完成receipt hook，不能把任意旧对象序列化成证明。无活动源/fullbuilder/FD/kernel/加载/手机操作，342/190、冻结255/raw231、88/default42及CPU/触控/Data保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-prematch-object-association-2026-11-01.json)。


## 实际C++编译完成receipt hook隔离实现（2026-11-01）

实际XNU MakeInc.rule的P_RULE_1A用-MJ记录，与MD/MF/MP同次编译；KC++由既有CCACHE/CXX展开。只对显式启用的IOService.cpo加runner前缀，默认OFF展开原命令相同，其他单元不变，缺runner即make拒绝。producer要求真实固定编译器、新object/dep/MJ/receipt、成功退出和462输入前后匹配，才写原来源schema；consumer核对实际MJ配方/路径/完成记录，当前真实kernelOFF路径仍拒绝。

真实编译成功receipt及4过程拒绝（已有产物、真实编译错误exit1、语法检查成功但无对象、预输入错误）通过，3补丁正反准确。初次严格比较拒绝Apple clang自动追加固定metadata参数；只接受完整已观测精确后缀且全部保留。初Make夹具KC++=误按+=解析、consumer误把MP phony行当输入的拒绝和旧脚本均保留，分别修夹具空格/首逻辑依赖规则，无重复编译旧套件。hook还会拒绝普通增量旧输出，下一项按既有workspace staging做小范围独立inode的新输出/preimage绑定，不能删/覆写基线或冒称fresh。无活动rule/源/fullkernelmake/FD/kernel/加载/手机操作，342/190、冻结255/raw231、88/default42及CPU/触控/Data保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-compile-completion-hook-2026-11-01.json)。


## 小范围工作区选择包与空输出暂存（2026-11-01）

沿用实际stage-zorn-build-workspace.py的cp -cR独立写入复制，隔离暂存34文件/2187666B、437绑定和22个空输出位置。旧IOService源/cpo/cpd/MJ及rule/stager/debug独立保存；修改暂存旧对象副本确认活动对象不变后恢复完整SHA。closed Service/配对caller/17配方/prematchON/rulehook/receipt producer+verifier合并绑定。已有目录、错SHA、路径越界、preimage与输出冲突4拒绝，默认OFF无I/O，新增stager补丁正反准确且未应用。

此包明确不可构建：原配方/策略仍含原绝对路径，仅作来源保存，尚未重定位、未编译任何目标或应用活动树。下一项只做staged IOService最小路径/quote/依赖策略重定位与一份真正新输出的单元receipt闭合，不重复17组件或旧probe套件，不抬完整builder拒绝。211外部导入、3初始化器、8真实provider、最终kernel/最早失败可读保护与canonical资格仍缺；342/190、冻结255/raw231、88/default42与CPU/触控/Data保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-workspace-fresh-staging-2026-11-01.json)。


## 暂存IOService单元路径与真实receipt闭合（2026-11-01）

只重定位IOService源码/绝对object、MD/MF/MJ和原quote父目录，原工作目录保留以读取既有生成头；461项原输入pin加1份等SHA暂存源码，共462项。通过未改的receipt producer CLI实际编译一次新单元，consumer和prematch源码选择核对通过；新对象SHA cde868a8由实际编译形成，不移植历史proof对象。Apple实际metadata精确后缀完整保留。旧源码路径、旧活动对象、已有输出、错误预输入4项拒绝，后两项在编译器启动前拒绝。

仍未成为实际Make选中的kernel对象。下一项仅做默认关闭的小型新树source/rule/helper安装与fresh OBJROOT身份描述，不能把本receipt迁到另一Make路径冒称已编译。不重复17组件/旧prematch套件、不执行完整stager/baseline或抬fullbuilder拒绝；原工作区与上一选择包保持，342/190、冻结255/raw231、88/default42及CPU/触控/Data保持。211导入/3初始化器/8真实provider/最终内核与可读失败保护仍缺，allow_boot/readback=false。[证据](evidence/gpu-Gen7-staged-unit-relocation-2026-11-01.json)。


## 新小型树source/rule/helper安装绑定（2026-11-01）

实际生成IOService规则620/622行从SOURCE_DIR/iokit/Kernel取源，P_RULE_1B只取前提文件名；baseline817/826行固定xnu-work及OBJROOT。默认关闭的新树installer在写入前核对OFF源码/rule原件及7个选择入口，只在全新绝对非符号链接目录沿用实际cp -cR复制34文件、17组件来源并保留23个空输出。独立inode/SHA核对通过；已有树、活动树别名、符号链接、错误OFF原件、错误rule、旧receipt声明6拒绝，无删除/覆盖活动产物。

该新树仅为小型安装布局，descriptor flag0且不可构建；旧receipt不安装，原policy/17recipes绝对路径只作来源。未执行Make、编译器或完整stager/kernel。下一项闭合真实生成Make单元的源码/rule/输出选择及生成头需求，不重复独立编译/17组件套件。211导入/3初始化器/8provider/最终kernel与可读失败/canonical资格仍缺；342/190、冻结255/raw231、88/default42与CPU/触控/Data保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-fresh-tree-installation-2026-11-01.json)。


## 实际Make单元选择与生成头缺口检查（2026-11-01）

从真实生成Makefile提取IOService620/622规则及安装hook的P_RULE定义，实际make -n -rR只在隔离最小夹具展开OFF/ON。使用真实MJ冻结语义flags作为CXXFLAGS输入，非完整Make变量回放；选中新树ON源码/rule/runner前缀。初夹具独立cwd后收窄到真正选定的空OBJROOT/iokit目录，初始脚本/结果保留；两次均只干运行，未启动编译器或生成对象。旧root源码、旧OBJROOT、错误source布局3拒绝。

核对原461依赖pin，9项外部只读输入仍匹配；新树缺452项树内头/生成输入，因此配方/编译资格仍false。下一项仅以精确SHA集合暂存452文件并显式映射include/生成头路径，不克隆整个SDK/工作区、不重复独立编译/17组件套件或移植旧receipt。完整builder/native/设备保持关闭；342/190、冻结255/raw231、88/default42与CPU/触控/Data保持，211导入/3初始化器/8provider/最终kernel/canonical资格仍缺，allow_boot/readback=false。[证据](evidence/gpu-Gen7-Make-unit-selection-2026-11-01.json)。


## 有界452输入capsule与15路径参数映射（2026-11-01）

按上一精确SHA清单复制452项树内头/生成输入，9项外部输入仍只读pin；加所选源码共462项观察输入。连同34文件选择包共486文件/10252883B，沿用cp -cR且inode独立。仅15个已知TREE路径operand和cwd映射，新记录可精确反向还原原配方；不改其他语义flags/order/compiler，不泛化改17配方。已有capsule、缺头、错SHA、路径冲突、错误原root5项拒绝通过。

未启动编译器，旧receipt未移植，receipt策略未签发；观察输入齐全不等于完整include查找等价或编译后依赖验收。下一项必须在既有producer/consumer入口校验原配方SHA/15处受限派生，闭合后仅一份真正Make驱动的新单元才能生成receipt，不把任意新reference序列化当来源。完整builder/内核/设备保持关闭，342/190、冻结255/raw231、88/default42与CPU/触控/Data保持；211导入/3初始化器/8provider/最终kernel/canonical资格仍缺，allow_boot/readback=false。[证据](evidence/gpu-Gen7-bounded-header-capsule-2026-11-01.json)。


## 配方派生强制门槛与单次Make单元拒绝（2026-11-01）

在隔离既有receipt producer/consumer中绑定原配方完整SHA、唯一15路径映射和462输入，缺派生mode/漏输入/旧source/旧cwd/新语义flag共5项在编译前拒绝；consumer缺派生记录也拒绝，合法legacy来源保持，2补丁正反准确。只一次真正Make驱动的IOService尝试生成object/rawMJ/dep/compilerlog，462依赖及前后输入匹配。

Make实际exit2：旧严格matcher拒绝P_RULE命令产生的-c移到--driver-mode=g++之前；另含已知固定Apple metadata后缀。离线逐参数比较其余完全一致，但未放宽checker、未签发receipt、未重试或补造成功。编译器101条警告完整保留；对象不合格，不作为kernel选择证据。下一项只修精确排序匹配并用保留rawMJ做拒绝检查，不重新编译/覆盖本次产物或倒填完成receipt，随后转具体canonical组件选择边界。无活动源码/完整kernel/设备操作，342/190、冻结255/raw231、88/default42与CPU/触控/Data保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-derivation-Make-unit-2026-11-01.json)。


## Make metadata精确匹配修正与组件验证输入接合（2026-11-01）

只在完整已核对P_RULE argv形状下接受-c/driver-mode两token的已观察顺序，所有其他参数/重复/顺序及固定Apple后缀完整保留，不排序/过滤/泛化normalize。保留rawMJ离线匹配通过，改优化/删flag/缺c或driver-mode/未知或重复suffix/重复c/删重复Xclang/无关重排/错command共10拒绝。原派生门槛及2合法legacy形状保持。没有Make/编译器/重试/倒填receipt，旧exit2和未合格对象原样保留。

具体接合补丁使consumer返回验证器实现与参考/派生依据的verification_inputs，component必须纳入source_sha256及报告校验；缺失/改SHA两拒绝，仅读取一份旧合法receipt确认兼容，不将其当新kernel来源。验证工具当前身份不等于历史实际运行的编译器脚本身份。3个UNAPPLIED补丁正反准确，未应用活动树；下一项为canonical debug真实source-replay变换来源闭合，禁止继续staging包装轮或机械改pin。342/190、冻结255/raw231、88/default42及CPU/触控/Data保持，211导入/3初始化器/8provider/最终kernel/canonical资格仍缺，allow_boot/readback=false。[证据](evidence/gpu-Gen7-Make-metadata-matcher-2026-11-01.json)。


## Canonical source-replay精确投影与组件来源门槛（2026-11-01）

读取真实debug verify_source_replay：原97项源码、5项独立运行时变换和tracked-change闭合保持。IOService已有baseline pin，MakeInc.rule原记录未覆盖；两份OFF原件与ON结果的固定补丁正反准确，独立投影表98项。仅明确两项变换允许新SHA，未机械改旧marker。缺源码/遗漏旧pin/旧helper/额外tracked改动/错commit/实际OFF工作树共6拒绝；原debug默认OFF验证返回完全一致，Gen7=1完整image早期拒绝原字节保留。

组件补丁在任何新组件编译前要求实际工作树投影，并将119项lineage/原件/补丁/helper验证输入纳入既有source_sha256及UFS/debug归档。旧报告缺投影2拒绝，component默认OFF无I/O，debug/component两补丁正反准确且未应用。隔离描述不是实际worktree选择或新replay；fresh_replay_performed=false、历史oldobjectsreused=true、compiled=false原样保留，历史标记不授权未来复用对象。下一项为17配方实际workspace选择与pin校验，不继续staging包装轮；无编译/replay/设备操作，342/190、冻结255/raw231、88/default42与CPU/触控/Data保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-canonical-source-provenance-2026-11-01.json)。


## 17配方显式工作区选择门槛（2026-11-01）

原419profile pin与实际冻结515输入（含9外部只读）全部保持，4stock incbin显式留在原只读pin。549个完整usedpath逐项声明；各配方仅允许source/cwd/include/ignorelist及object/MF输出的明确变换并精确反向还原，不全局替换root字符串。首次严格拒绝9项原MF路径，保留初脚本/拒绝后仅补role.d输出映射。缺角色/错角色/额外flag/错输出/头别名/用旧root冒充新workspace6拒绝及篡改选择报告1拒绝通过。

正例只验证实际当前root身份映射，不称搬迁workspace、ON源码或编译合格。组件UNAPPLIED补丁在mkdir/进程前要求选择guard，归档map/policy/原配方/编译来源/验证器并重新推导报告选择；补丁正反准确，无新输出/编译器/17组件构建。现有sourceprojection仍固定旧helper，下一项必须明确父policy+旧新helper+补丁来源，不能静默换SHA。342/190、冻结255/raw231、88/default42与CPU/触控/Data保持，完整builder/native/设备关闭，allow_boot/readback=false。[证据](evidence/gpu-Gen7-workspace-recipe-selection-2026-11-01.json)。


## 父policy与所选helper精确来源闭合（2026-11-01）

既有sourceprojection校验器新增明确helper lineage：固定父policy完整SHA、原helper SHA、新helper SHA和现有补丁正反准确来源；增加recipe guard/policy/map三项后合计9个helper角色。97源码pin、5已有runtime变换和两项source补丁未改，旧policy/marker未重写。错父policy/旧helper/缺guard/错map/错workspace/回放旧角色声明6拒绝，实际工作树仍拒绝，root identity不冒称搬迁资格。

独立补丁未应用，验证输入同时保留父policy/旧新helper/补丁/新增文件及原lineage。未执行Make/编译器/回放或设备操作。实际下一缺口为receipt validator仍硬绑先前单一capsule路径：下一项只在既有入口派生并校验真实canonical工作区context，不增staging包装器、不倒填旧失败receipt；完整image早期拒绝保持。342/190、冻结255/raw231、88/default42及CPU/触控/Data保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-helper-policy-lineage-2026-11-01.json)。


## 既有receipt入口的canonical工作区context校验（2026-11-01）

新增隔离canonical-workspace模式，以固定原配方派生实际TREE/OBJROOT/source/cwd/object及462输入；旧capsule冒充规范树、缺context、错source/cwd/compiler、漏输入、额外flag、伪projection共8拒绝，consumer不能借legacy记录身份跳过ON工作区context。合法legacy/旧path-rebased模式与rawMJ/精确Make顺序guard保持，两补丁正反准确。正例只验证纯派生形状，实际当前OFF源码被明确拒绝，未产生可编译context或receipt。

发现完整helper投影会形成producer→helperpolicy→同producer的SHA环，改用固定source-core对实际98源码/commit/tracked集合独立验证；其归档helper是验证器历史，不冒称实际安装版本，组件仍必须验证当前helper lineage。没有以caller布尔值放行。下一项仅把本次producer/consumer两端点补丁明确接入既有helper lineage，不静默改父pin。未执行Make/编译器/回放/重试/设备操作，342/190、冻结255/raw231、88/default42与CPU/触控/Data保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-canonical-receipt-context-2026-11-01.json)。


## Receipt两端点helper来源与单一具体选择包核对（2026-11-01）

将producer/consumer与已验证component三项变换明确绑定到父policy，三份原件/新件/补丁逐项正反准确，helper合计10角色。旧producer/旧consumer/缺template/错parent/map回放/错workspace6拒绝，97原pin、5runtime及两源码补丁保持，actualroot仍拒绝。source-only verifier与真实helper安装身份继续分开，避免SHA依赖环。

单一具体选择包17文件已核对，含8个同目录policy依赖；初清单漏两项已显式补齐并保留初版本。另对实际活动debug/UFS原件到候选源码的两个完整未应用补丁做正反核对，未改活动树。选择包未安装、rootmap未搬迁、无实际context/新receipt/17新对象；下一项只选定一处独立canonical最终路径并推导真实文件义务，不再包装staging轮或冒称缺文件存在。无Make/编译/回放/设备操作，342/190、冻结255/raw231、88/default42及CPU/触控/Data保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-receipt-endpoint-lineage-2026-11-01.json)。


## 单一规范工作区最终路径推导（2026-11-01）

选定out/zorn/gen7-canonical-workspace但未创建，549已用路径、515pin、17配方逐项推导，列出621缺失文件（已列逻辑量18230130B，不代表完整构建需求）及Git/完整源码/设备固件仓库/新receipt/17对象缺口。9外部头与4绝对incbin原路径/SHA保持。实际stock汇编证明四条绝对incbin；目录搬迁检查原本错误涵盖它们，现仅在隔离候选豁免这四项目录关系，保留所有逐文件SHA检查。配方guard和selector两份未应用补丁正反准确，父记录未改。

生产guard仍拒绝缺失目标文件，actual projection因缺Git HEAD拒绝，描述符检查不当安装或搬迁资格。diskutil信息不可用并留原错误，只记录stat/可用字节，不称APFS或完整构建空间合格。下一项按621文件明细有界独立副本物化，禁止全仓库/SDK复制或编译；实际Git/来源等缺口继续显式保留。未Make/编译/回放/手机操作，342/190、冻结255/raw231、88/default42及CPU/触控/Data保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-canonical-final-paths-2026-11-01.json)。


## 规范目录621文件有界物化（2026-11-01）

在已选out/zorn/gen7-canonical-workspace独占创建621个文件副本，共18230130逻辑字节，全部SHA与源一致且逐项dev/inode不同，无硬链接或整工作区/SDK/Git历史复制。明确目录映射已创建，原9外部头和4绝对incbin路径保持。实际安装的配方guard核对515pin、17配方，selection报告再次验证，10helper来源数据核对通过；无新对象。

真实source projection因缺XNU Git HEAD返回128，明确保持actual context/搬迁资格不合格。设备目录虽存在，仅含所列helper，不称完整仓库。下一步只处理原本地仓库到目标的真实HEAD/tree/index/完整tracked源码来源，不伪造Git身份、不重做复制或编译。无Make/编译/回放/手机操作，342/190、冻结255/raw231、88/default42与CPU/触控/Data保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-canonical-file-materialization-2026-11-01.json)。


## 原生Git来源浅快照与tracked源码闭合（2026-11-01）

原core HEAD066c8d83、XNU HEADd8b80295的真实commit/tree/blob分别1092/5446对象已提取成独立浅快照，明确shallow边界，无新commit/历史重写/父历史复制。Git fsck与完整HEAD文件树逐字节核对通过，原索引保持且无staged变化；原core8、XNU92 tracked改动保留。

6239个tracked源码文件逐项当前SHA已绑定，目标已含156个XNU文件，还缺6083文件/71884890逻辑字节。现有两处差异严格对应IOService/MakeInc已固定补丁；19core子模块gitlink仅记录、不冒称已复制或合格。原621副本未变，两个快照尚未安装到目标.git，actual source/context/搬迁资格仍未闭合。下一项只安装真实独立Git元数据及所列缺失源码，保留既有文件和两overlay，再由原validator核对；不得编译/改validator放行。342/190、冻结255/raw231、88/default42与CPU/触控/Data保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-canonical-git-provenance-2026-11-01.json)。


## 真实tracked源码与Git元数据安装（2026-11-01）

按明细安装6083个缺失源码和两份独立真实浅Git元数据，原621文件及两补丁保留，文件SHA和独立inode全匹配。XNU HEAD/tree/真实索引与94项tracked改动核对通过，原source projection实际检查98源码/10helper成功，actual_worktree_selected=true但compiled/kernel_selected=false。配方515pin/17项仍通过，无编译对象。

core真实HEAD/index已安装，但19gitlink未填充，其实际tracked状态与原core8项不等价，明确未通过完整core/工作区资格。初次复制遗漏Git空refs目录导致config发现失败，修复目录复制后core子模块差异被拒；原脚本/错误保留，逐项核对后续接缺件，未放宽validator。下一项使用既有producer构造真实IOService context/reference和462输入义务，不调用编译器/capture。源检查通过不等于GPU执行或最终kernel。342/190、冻结255/raw231、88/default42与CPU/触控/Data保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-canonical-tracked-source-installation-2026-11-01.json)。


## 实际canonical IOService context资格检查（2026-11-01）

由既有producer实际derive/validate构造canonical reference/context/policy，462项真实输入与编译器SHA全部匹配，98源码/10helper另经实际安装检查。缺失63头文件共647433B仅按原完整SHA独立inode复制，既有源码未覆盖。producer删除输入/伪造projection两拒绝通过，未修改验证器。

context仅为软件编译来源准备；无compiler/capture/Make/object/receipt。core19gitlink与完整工作区、最终kernel/平台所有权仍不合格。下一项仅允许一项新canonical路径、由原Make规则驱动且55秒有界的IOService receipt尝试，先绑定原规则/当前输入并拒绝任何缺件，不重试旧capsule、不启动完整构建或设备。342/190、冻结255/raw231、88/default42与CPU/触控/Data保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-canonical-receipt-context-readiness-2026-11-01.json)。


## 单次canonical IOService真实编译receipt（2026-11-01）

唯一一次实际Make驱动编译exit0，IOService对象SHA7f9ff6be、全462项编译前后依赖一致，canonical context、真实MJ及consumer核验通过。绑定原generated Makefile701447和已安装P_RULE2161/展开命令，范围是实际target/rule片段与冻结MJ语义flags，非完整XNU变量回放。101条编译warning保留。后处理harness首次缺producer搜索路径错误已保存，仅重做只读consumer验证，未重跑编译；旧失败capsule产物逐SHA不变。

实际新canonical17对象构建前置guard已通过，输出目录仍不存在；下一项仅调用现有build helper产17新对象并验证实际报告，不重用旧对象或重跑旧suite。core19gitlink、完整工作区/最终kernel/平台所有权仍未合格。无设备操作，342/190、冻结255/raw231、88/default42与CPU/触控/Data保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-canonical-one-unit-receipt-2026-11-01.json)。


## 新canonical17对象实际构建（2026-11-01）

现有已安装build helper单次调用生成17个全新canonical对象，未复用旧对象，逐对象45秒上限保留，缺省OFF无动作。实际build.json由现有verify_report通过：17命令/883递归输入/17完整对象SHA，真实IOService receipt与462依赖、实际源码/helper/配方guard继续绑定，runtime_complete=false。旧失败capsule仍逐SHA不变。

尚未重定位或完整kernel链接。下一项只用这17个新对象及原固定链接配方形成一个新relocatable aggregate，复用原只读解析/audit核对selfimport/NotReady拒绝/固件/三个初始化器及真实外部导入，不重编译或重跑旧suite。core19gitlink与最终kernel/平台所有权仍缺。无设备操作，342/190、冻结255/raw231、88/default42与CPU/触控/Data保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-canonical-fresh-components-2026-11-01.json)。


## 新canonical17对象重定位链接审计（2026-11-01）

按原固定MachO ld-r配方单次链接17个已核对新对象，aggregate SHA861ed91c；工具全SHA与实际输入绑定，未再编译。仅复用原只读解析/audit定义，未执行旧脚本toplevel或旧suite。内部selfimport为0，实际Service清输出/NotReady五指令与probe=null核对通过，四stock固件字节和完整SHA/尺寸符号匹配。

仍211外部kernel导入及3既有metaclass初始化器，MH_OBJECT节名不等于最终页权限/类ABI/加载/平台所有权。下一项处理真实core19gitlink选定本地源码来源和规范builder实际缺件，至少落实具体缺件；不改活动源、重编译或放行完整镜像guard。无设备操作，342/190、冻结255/raw231、88/default42与CPU/触控/Data保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-canonical-component-link-audit-2026-11-01.json)。


## canonical core19子模块真实源码闭合（2026-11-01）

按现有source-pins选定本地HEAD填入19真实子模块，363tracked源码逐SHA核对，新复制325文件且inode独立；各自真实浅Git HEAD/index/fsck通过，原索引及活动源码不变。4选定HEAD与core gitlink不同，严格保留原Adreno740/AdrenoMetal/GopFramebuffer/ArmSmmu4K选择，不强制checkout；目标core8项改动名称现与原目录一致。source-pins完整复制，原621+6083+63文件/receipt/17对象/aggregate保持。

实际旧342构建路径投影仍缺192项，另有IOService/debug/UFS三处已选定差异。缺件147071641B主要为旧kernel125833216B/kernel.json16981191B及旧owned/ABI对象，明确不得整体复制或当新输出。下一项只补实际native-device/config/helper源码依赖，并将旧证据与未来新构建输出义务区分；完整builder资格仍未闭合。不编译/链接/设备操作，342/190、冻结255/raw231、88/default42与CPU/触控/Data保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-canonical-core-source-closure-2026-11-01.json)。


## canonical设备源码/config/helper缺件闭合（2026-11-01）

按具体旧342缺件与当前固定builder静态本地import补入116文件/736211B，全部原SHA与独立inode核对；115来自已列源码/config/helper，1为实际本地import依赖。绑定debug/UFS所选11模块，未执行builder顶层。IOService/debug/UFS三既有overlay保留，旧kernel/对象/报告/ABI证据未复制复用。

明确仍26项新构建输出、3项须实际准备runtime源码、3历史ABI对象及45原证据/不可变数据未迁移；静态import不称动态输入闭合。下一步仅按既有prepare脚本准备canonical runtime源码，先验证原feed/patch/5desired字节严格等于当前XNU，保留preimage，不进行CPU/GUI回归或编译。完整kernel/平台/读回仍不合格，342/190、冻结255/raw231、88/default42与CPU/触控/Data保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-canonical-device-input-closure-2026-11-01.json)。


## canonical runtime源码一致性门拒绝（2026-11-01）

已补齐8真实前置文件（5原feed、origin及2header），保存98源码/profile/5baseline共104preimage。源transform检查4项一致，但默认GPU_MEMORY=0会从bsd_init.c固定36ce318f移除两行旧owned caller，得到b7aa9be0；精确差异已保存，按计划在main前停止。98源码、profile及baseline未改，未开启旧内存诊断、未编译或操作设备。

现有UFS disabled分支明确选ZornGpuOwnedStub.c，其gui_tick为空；下一项只做最小UNAPPLIED显式Gen7来源准备接合，保持GPU_MEMORY0而保留已合格源码字节。Gen7缺省OFF行为、runtime/source/receipt pins和完整builder拒绝门均不得放宽，不能设旧Memory1绕过。此为源码管线冲突，非手机故障且无需机主动作。342/190、冻结255/raw231、88/default42与CPU/触控/Data保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-canonical-runtime-source-preparation-2026-11-01.json)。


## Gen7 runtime源码准备最小未应用接合（2026-11-01）

仅在隔离候选修改原transform一项条件：显式Gen7prepare1且Memory0时复用已固定GPU caller补丁，保留现有源码字节而不启用旧allocation诊断。6组实际source-transform开关/每组5文件核对：缺省及Gen7OFF行为相同，ON+Memory0五处均等于当前源码（BSD36ce318f）；其他函数/main AST完全不变，补丁fuzz0正反准确。

实际owned builder关闭分支仅选ZornGpuOwnedStub.c，gui_tick为空；未编译或调用main。canonical脚本、98源码/profile/104preimage未改。下一项才按精确preimage和候选补丁在canonical目录接合并单次重新准备来源，显式Memory0，旧manifest保持历史；不得改变活动根源码、CPU/GUI检查或完整镜像拒绝门。342/190、冻结255/raw231、88/default42与CPU/触控/Data保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-canonical-runtime-source-integration-2026-11-01.json)。


## canonical runtime准备补丁接合及源码生成（2026-11-01）

仅在隔离canonical目录安装已审查精确补丁，准备脚本旧0e62a4df保留为历史preimage，新97da876a完整绑定，旧manifest未改。实际五处desired字节等于当前后，以Gen7=1、GPU_MEMORY=0单次执行现有main。ArmCpu/3header/profile五输出核对，driver/header源码与原固定补丁结果匹配；98XNU/baseline/profile源码字段保持，实际sourceprojection、receipt及17对象/aggregate不变。未开启旧allocation诊断。

下一项对实际Gen7-only UFS/debug依赖与输出消费作最小未应用接合：旧owned输出不能当必选项，现有17新对象目录也不能删除重建或泛化reuse；应仅消费现有验证器核实的精确当前报告，完整镜像早期拒绝门仍保留。无CPU/GUI回归、编译/链接或设备操作，342/190、冻结255/raw231、88/default42与原CPU/触控/Data保护保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-canonical-runtime-source-apply-2026-11-01.json)。


## Gen7-only输出与精确报告消费未应用接合（2026-11-01）

实际UFS会重新构建已存在的17对象目录，已准备最小UNAPPLIED补丁：仅验证并消费完整SHA固定的当前canonical build.json，通过现有verify_report及真实source/receipt/helper/map/输出目录上下文。在任何UFS编译前验证，失败不fallback/rebuild；独立consumption记录objects_reused=true、原component的objects_reused=false分别保留，不修改原报告。实际17对象验证、7拒绝、默认OFF AST一致及fuzz0补丁正反通过，未执行UFS顶层。

26历史输出已按Memory0重新分类：10旧owned诊断对象不再必选；disabled stub及其报告、真实kernel/native/ADT与ABI审计义务保留，新增Gen7消费来源记录义务。17对象/aggregate未重编或加入归档，debug完整镜像早期拒绝不变。下一项仅在canonical目录精确接合本补丁及验证真实consumer，不编译/链接/手机操作；原342/190、冻结255/raw231、88/default42与CPU/触控/Data保护保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-canonical-output-contract-2026-11-01.json)。


## canonical精确报告consumer接合（2026-11-01）

已仅在隔离canonical目录安装已验证UFS补丁，新SHA9d6caefc；旧文件独立inode preimage保留，原manifest明确历史、不回写。实际安装函数经AST-only调用核实当前17对象报告，OFF无I/O；原report/receipt/helper/17对象/aggregate及根活动源码不变。未执行UFS顶层、编译或将对象加入归档，debug完整镜像早期拒绝保持。

实际5份native recipe仍缺：bsd_init、IOPlatformExpert、processor、IOBufferMemoryDescriptor和IOMemoryDescriptor元数据，不能复制旧文件冒称新生成。下一项追现有core内核构建入口及来源/配置/Make接合，落实最小真实前置修正，再形成有界新native构建条件；当前不编译/链接/设备操作。342/190、冻结255/raw231、88/default42及CPU/触控/Data保护保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-canonical-report-consumer-installation-2026-11-01.json)。


## canonical内核入口三处具体缺件闭合（2026-11-01）

现有kernel.build实际指向tree/scripts/build-xnu-4k-baseline.sh，但canonical目录此前缺scripts入口。仅提取现有tree._copy_scripts函数，补入原内核shell、头源码准备器和已接合UFS三份精确源码独立inode副本；不执行完整assemble、脚本顶层或构建，不改原文件。此修正只解除最早missing-script错误，不能称全bootstrap闭合。

真实5份recipe仍须原Make bootstrap生成；shell仍缺refer/XNU Git及AvailabilityVersions/libplatform/libdispatch和availability工具输入，且当前kernel/debug未设置IOService所需receipt runner。下一项只对现有kernel.build做显式Gen7最小未应用前置guard/接合，拒绝缺项或破坏现有receipt/17对象的重编译，缺省OFF及完整镜像拒绝不变。无编译/链接/设备操作；342/190、冻结255/raw231、88/default42及CPU/触控/Data保护保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-canonical-native-entry-closure-2026-11-01.json)。


## Gen7内核入口最小未应用前置检查（2026-11-01）

仅准备kernel.build首语句显式Gen7 guard未应用补丁：默认关闭无I/O；开启时先验证精确canonical helper/report及真实source/receipt/17对象，再拒绝未设runner/policy或缺bootstrap输入。即使表面输入齐全，当前whole-kernel bootstrap仍不放行，保留原IOService receipt与对象。删除新增函数/调用后完整模块AST与原相同，补丁正反通过。

5项实际拒绝覆盖无效开关、旧内存诊断、错误树、真实缺runner和缺bootstrap；负控制runner字符串未验证/未获准/未执行，不作成功证据。实际报告复核通过后按预期拒绝，未运行builder顶层或编译。下一项仅canonical安装并补至少一项实际本地bootstrap输入，完整debug拒绝不变。342/190、冻结255/raw231、88/default42及CPU/触控/Data保护保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-canonical-kernel-prerequisite-guard-2026-11-01.json)。


## canonical内核前置检查安装与availability工具依赖闭合（2026-11-01）

仅在隔离canonical内核入口安装已审查补丁，新SHA3c670200，独立preimage保留且旧manifest为历史。实际安装guard经AST-only调用验证OFF无I/O，ON核对真实报告后拒绝缺runner；未执行builder顶层、bootstrap或编译。原receipt/17对象/aggregate及根活动源码保持。

补入一项具体bootstrap依赖availability.pl，37578B/SHA88f5b097，独立inode并保留执行权限，但没有执行。原AvailabilityVersions tracked源码/DSL/CMake与真实HEAD核对，按INSERT_DSL_CONTENT规则推导出的完整字节与原已安装工具和新副本一致；此为源码工具，不是复用旧native对象或元数据。其余reference源码及5份recipe仍缺，下一项按既有本地feed精确闭合实际reference输入；新guard和debug完整镜像拒绝保持。342/190、冻结255/raw231、88/default42与CPU/触控/Data保护保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-canonical-kernel-guard-installation-2026-11-01.json)。


## canonical四项bootstrap reference真实源码闭合（2026-11-01）

固定feed的xnu/AvailabilityVersions/libplatform/libdispatch四仓库真实HEAD匹配，5544tracked文件逐Git blob及SHA核对；新增5539独立inode源码副本，共77922826B输入。仅选定commit/tree/blob形成真实浅Git对象、HEAD和索引，fsck通过，不复制父历史、不网络或复用旧native输出；原索引不变。原5份reference源码匹配保留，98patched work源码/IOService/MakeInc及receipt/17对象/aggregate均未改。

reference缺件已闭合但未运行shell或生成5份recipe，whole-kernel和debug拒绝保持。下一项限定到缺失的5个原生目标，追实际generated Make/rule与当前源码依赖，准备最小隔离目标/context并补具体头输入；排除已有IOService、不复制旧编译元数据冒称新生成，再形成独立有界编译条件。无编译/链接/设备操作，342/190、冻结255/raw231、88/default42与CPU/触控/Data保护保持，allow_boot/readback=false。[证据](evidence/gpu-Gen7-canonical-bootstrap-reference-closure-2026-11-01.json)。


## 机主要求先更新上游并重读GPU指南（2026-11-01）

UniXNU主仓库已从066c8d8快进到627c932，271提交；四份本地构建脚本改动已备份并恢复，两文件冲突合并完成，保留上游原子发布保护和既有K80逻辑。19子模块实际HEAD未切换，恢复stash保留；语法/diff及上游发布测试与本地patch失败保留旧镜像检查通过，无编译或设备操作。

已读官方GPU指南及新本地文档：A740/sheng与OS27记录不能当K80 A750/Darwin23验收，硬件代际后端/编译器、DMA/电源/GMU-HFI到CP/ring/fence/已知图像和Metal发布需各自证据。当前5原生目标/1173输入已准备，109实际依赖补齐但未编译；先核对新上游差异再接合冻结canonical，不自动更新原组件或pins。原归档与默认42保留；旧342当前输入差异另存，不能继续宣称全部当前匹配。allow_boot/readback=false。证据：out/zorn/upstream-gpu-review-20261101/result.json、historical-342-input-delta.json。


## 有人值守恢复与新main实际iOS17接合批次（2026-11-01）

机主明确进入有人值守，physical_assistance_available=true。已确认main共享17/27实现，按--os17/--target ios与Darwin23真实配方使用，不按分支名称排除共享代码。隔离取main固定Adreno740149ef6d、AdrenoMetala0f0287和ArmSmmu83969cd，原组件HEAD不切换。本批实际重编17Gen7组件并一次链接；首次Service16592B被真实16KiB guard拒绝，改为同一IOKit类的CPU描述准备配置，排除无用A740运行态成员，实际13536B。probe不附着/client固定NotReady、固件字节、3既有初始化器检查通过。217外部导入仍待完整内核接合，其中pmap诊断hook已验证weak，不用假实现补齐。

5个缺失原生目标已真正经Make编译，新对象/MJ/deps及1173输入核对，现有IOService未重编。初C++ Make变量KC++=被GNU Make解释为+=导致未调用编译器，输出完整性门正确拒绝；新隔离配方改KC++ =后完成，旧日志保留。元数据全部参数仅允许既有driver顺序与固定后缀差异，未复制旧记录当新产物。后续直接接合新batch的真实来源/消费与Darwin23虚调用，再推进A750平台后端；不得机械改旧pins或把对象成功当GPU执行。原342因机主授权pull保留340匹配/2历史差异，冻结255/raw231、190归档和默认42不变。无新手机操作，allow_boot/readback=false。[证据](evidence/gpu-upstream-attended-2026-11-01.json)。


## 新main组件实际构建消费与Darwin23 ABI接合（2026-11-01）

继续按有人值守/iOS17处理，已把这一批17组件接入两处现有canonical UFS构建脚本，显式GEN7_PREPARE=1与GEN7_MAIN=1选择新来源；默认关闭及旧分支余下字节不变，旧report/helper不改。11项错context、旧内存轮冲突、坏选择、失配源码/ABI/对象和开放调用门拒绝通过。两份脚本preimage/独立inode及新policy输入链保存，未执行整个UFS/CPU构建。

实际新NativeMemory的26个间接调用与新编译IOMemoryDescriptor37槽/IOBuffer44槽及原同OS内核ABI对照通过；6个真实虚方法与2个静态factory原型、实际对象坏槽负控制通过，旧内核地址仅用于ABI对照。17成员真实ar归档逐成员字节/顺序核对；17组件+5新原生对象+原IOService共23对象真正ld-r链接，75个组件导入由实际原生定义闭合，包括两个IOBuffer工厂，无补桩。合并后768外部导入/7个初始化器仍需完整内核链接审计；不是完整UFS归档或GPU执行。

两次检查器问题均保留原版：physical-mask mangling实际为jyy，初版误写jmy；ar含正常__.SYMDEF SORTED索引，检查器已单列核对。均未改生产对象或放宽ABI/成员字节要求。canonical核心脚本仍为066c8d基线，627c932仅按明确的新组件来源接合，未冒称完整新main迁移。下一连续批次直接移入新main构建/OS选择/原子发布逻辑并推进真实host完整原生构建；保持旧receipt/对象证据。真实GPU平台所有权、最终镜像及失败读回仍缺，allow_boot/readback=false。[证据](evidence/gpu-main-ios17-consumer-abi-2026-11-01.json)。


## 连续推进新main核心构建与OS选择入口（2026-11-01）

未等下一轮，继续把627c932真实kernel入口、baseline/source/storage-header脚本及CLI/config/profile resolver接入现有隔离canonical，共11目标路径（包含tree独立副本），每个旧文件先存独立preimage。原Gen7整内核/完整镜像拒绝和设备保护保留。新CLI实际接受--os17/--os27，canonical现有OS17 profile真实解析；K80仍选Darwin23/arm64，未构建OS27，也未宣称全部271提交迁移完成。CLI新增pipeline模块缺件已按真实上游源码补齐，未执行其打包流程。

6项实际canonical kernel模块功能检查通过，涵盖真实OS17 profile/17.0缺省、native staging字节和坏输入、原子预链接成功/emit失败/本地AMFI patch失败时保留旧输出，以及旧Gen7冲突在构建前拒绝。测试fixture是普通字节，只有fixture内mock AMFI；生产AMFI函数与root真实源码相同。初测试误以为旧17 profile显式带ios_version，实际不带而走shell17.0默认，已按真实选项修正测试，没有补造profile字段。

上一批17组件消费、26虚调用/81槽ABI、23对象真实链接继续匹配。下一批直接补全一次真实完整native构建所缺的worktree/输入并执行Make/链接，旧98源码overlay、IOService/receipt和历史proof先保存；不能用新脚本存在代替完整kernel验收。无手机操作，allow_boot/readback=false。[证据](evidence/gpu-main-canonical-core-port-2026-11-01.json)。


## 新main Gen7完整原生编译与实际原厂kext接合（2026-11-01）

本批连续完成了真实XNU Make编译和12项配套库构建，不再停在独立对象。1011原生对象/1010实际依赖文件/3263递归输入已绑定，新main的17组件（准备态）实际进入完整原生内核。原生407aa14e…共93122936B；接合固定21H461原厂kext后的新内核cabefd1e…共125968384B。两个完整Mach-O均独立inode归档。沿用format1兼容路线和已绑定Darwin23投影源码，不宣称新source replay、完整format2或全部上游提交迁移。

逐实际输出核对108函数、233条B/BL边、81个当前原生虚表槽、四份stock固件和三个GPU类初始化器；Service probe仍为空、client固定NotReady。当前root start.s与所选源码相同，独立重编译的start.o完整SHA等于活动对象。两份实际Mach-O分别用四个RAM副本改坏client返回值、Memory BL、虚表、固件字节，全部拒绝，原文件不动。普通PAGE仍有正常链接器边界，不夸全地址穷尽。新候选的AES181/UFS190/RAM190/显示358/PMGR340接口检查通过，明确移除旧ABI参考环境，库字节未变。

真实缺件/失败已修正并保留日志：沙箱sysctl需主机权限；新脚本缺OS/SystemOS UUID输入按既有验证源码补入；两份旧局部IIG头缺实现，保存后由实际Make/IIG重生；补齐真实catalog/兼容lock及源码/签名策略/只读原图输入，未复制OS/SystemOS/SDK或旧native对象；修复SoftwareAES规范输出目录与设备wrapper断接。按固定HEAD独立补齐三项参考源码，源Git不复制父历史或共享可变元数据。已完成的库按真实源码/输出绑定恢复，未重跑前项。

完整内核的首次链接揭示弱导入native_pmap_user_mappings仍被静态kernel linker拒绝。未伪造pmap实现：隔离Memory候选增加默认开启的诊断开关，仅本Darwin23 profile显式关闭缺失的计数诊断；实际释放/缓存/隔离/设备引用门不改，26虚调用和81槽再对上真实当前对象，不能把诊断计数0当无用户映射。

还修复一项实际发布错误：AMFI本地补丁后候选字节为cabefd1e，但计划仍记录补丁前7c7a67cd。Root和canonical源均先保存preimage，再校验emitter摘要/保留补丁前摘要/发布实际最终摘要；7项测试通过，真实重生成候选字节仍完全相同。错误旧计划保留，正确归档为kernel.postlink-plan.json。正常完整镜像路径AST及Gen7拒绝不变，新增host模式拒绝boot/os27。

原630可变产物先保存；旧IOService/五目标关联在新Make重生后按历史保留，不机械更新旧proof。66份设备native基线源码与旧绑定一致；默认42、冻结255/raw231、190归档保持，旧342仍340匹配/2项授权pull历史差异。无手机操作或旧CPU/GUI/内存轮，无GPU/Metal执行。下一连续批次接合实际FD平台准备caller/规范host候选与最早失败读回资格；真实power/security/stop/QSMMUv500/access/DMA/GMU-HFI所有权仍缺，allow_boot/readback=false，不扩query/84text/footer协议。[证据](evidence/gpu-main-native-build-2026-11-01.json)。


## 实际完整FD与独立host候选接合（2026-11-01）

连续接合已审计的Clock/SCM/EBS生命周期/GCD/平台配置源码，使用真实ZornBootMemoryDxe/DSC/FDF配方编译完整3MiB FD c11d2fef…，模块dfd3a448…共94720B。原C调用顺序、触控头、FDF和SOC_TYPE2保留；新hook只生成248B私有RAM软件报告，provider/lookup未知，PAS配置184B的InvokeAllowed恒0。原272B查询capture未变，实际query/GCD函数仅保留供最终链接核对，未接入调用。不能把整个模块称为没有原生调用：原WDT/触控和未调用的查询实现仍含真实native方法。

实际FD中抽取的模块与新生成PE完整字节相同。新hook的完整直接调用/尾调用闭包只有3个纯软件函数，无间接native/SMC/HVC边；caller目标、release发布、248B/once/ready初始零且可写、无新CRT注册通过。4份实际PE副本分别改坏caller目标、release、写权限或改指向QueryRun均拒绝；新2对象按实际生成配方独立两次编译全SHA相同，目标ABI248/184/272/360/1384/256/224核对。5项ASan/UBSan真实源前缀检查覆盖范围/WDT/触控失败与成功、重复prepare及未知status保留；WDT/触控是host double，非手机保护资格。

固定build-zorn-debug.py新增显式host-only组装入口，旧函数AST及正常Gen7拒绝保持；直接复用已完成cabefd1e内核和正确postlink-plan，不重跑内核/CPU/旧内存轮。新boot c8f24dd3…的FAT、菜单、ADT和shim/FD/gzip完整接合，5个FAT文件逐一完整SHA读回相等。保持Darwin 8GiB owned window、8个独立CPU affinity、原Data/触控/dim64/看门狗marker及backup；原模板声明的12GiB DRAM保留，不能混称Darwin内存或新硬件测量。无CPU-active/display-progress/consumed-memory/query标志。当前iPadOS17 profile按只读本地SystemOS实际UUID及三处原字节重新验证，旧proof未改SHA。

完整固件548对象/549实际依赖/3055当前构建输入和4470个独立inode生成归档已绑定，约457MB逻辑数据以APFS clone/独立copy保留，未克隆SDK/OS/历史。默认42、旧FD05b8及默认capability/menu/CPU-proof保持；旧parent输入的主动源码变化均有preimage，旧proof不改。初次core路径、CXX14注解、缺原Data保护参数、DRAM声明/owned窗口检查器假设和EDK依赖注释拒绝均保留，未放宽生产guard。

这是完整HOST候选的重大接合；真实GPU power/security/stop/GCD metadata/QSMMUv500/DMA/GMU-HFI所有权及最早失败可读保护仍缺，248B私有报告不能从recovery读取。新候选无fresh BCB或手机WDT资格，allow_boot/readback=false，未操作手机或启用渲染/Metal。后续把已完成media-discovery/readonly-GPT verifier接入真实canonical生命周期caller并保持调用关闭，直接推进具体平台/保护缺口，不重建旧suite、不扩query/84text/footer协议。[证据](evidence/gpu-canonical-firmware-2026-11-01.json)。


## 原生checkpoint发现与GPT生命周期进入实际FD（2026-11-01）

复用先前已完成的native discovery、readonly GPT verifier、typed父子EBS owner及identity源码，不重写或重跑旧descriptor/lookup/GPT套件。原4个C ABI函数体原样保留；在上一批真实PublishRange的WDT/触控成功后接入新once准备入口，正常caller固定ZcdRun(...,FALSE)，未注册事件/枚举/读GPT/算CRC/关闭事件，也无写入或GPU调用。新增512B标量capture仅私有RAM，DISABLED是已知adapter结果，ObservationAvailable0；原native raw/status/attempted mask仍在真实owner中保留，未尝试不当零成功。未执行retire，也不伪造成功close。原272B query/1888B identity/184B PAS及线协议不变。

新实际3MiB FD58c00270…、模块ca6f0991…共106496B。真实最终PE证明caller的W2固定0，ZcdRun在任何native调用前按该参数走返回分支；callback仅单release且无调用。524288B/align4096 owner是持久静态BSS，不在栈上；512B capture/once/ready可写初始零且无新CRT注册。最终C ABI保留的enabled路径仍含真实native方法，不能说整个模块无原生调用或全调用链墙钟有界。5个实际PE副本改坏caller目标、FALSE参数、disabled分支、callback latch、owner写权限均拒绝；实际生成配方的5对象独立两次重编SHA一致，SDK原型/offset和512/524288/104/160/88/1888尺寸再对上新输出。4项新接合ASan/UBSan前缀检查覆盖范围/WDT/触控失败与成功、重复prepare/未知项保留；WDT/触控是host double，不是新手机观察。

553固件对象/554依赖/3074当前输入、4493个独立inode生成归档已绑定。保持原cabefd1e内核及上一批不可变FAT/menu/ADT完整字节，仅重组新FD/shim/outer boot8ef343bb…；没有重建内核、FAT或再跑CPU/GUI/内存轮，默认42和旧FD/capability保持。各旧入口函数AST不改，新host模式拒绝boot/os27及冲突旧输出。

更正当前输入计数的时间范围：旧342清单如今339匹配/3项差异，除授权pull的feeds/OSprofile，上一批为隔离CPU-profile proof路径修改的payload脚本是第三项；其原SHA对应的独立preimage已验证。此前340/2是native阶段的历史值，不能当固件源码修改后的当前值。旧报告/manifest原样保留，新增来源与差异记录，不机械改SHA。

新host候选仍没有实际平台所有权、fresh BCB/WDT或早期失败可读证据；512B私有capture不等于recovery日志。下一连续批次针对既有单4KiB log sink准备精确typed介质/父EBS/一次调用与原buffer契约，保持WriteAuthorized0；只能复用原log producer/reader，不新造query codec、不挪84text/footer或CPU字段。若原producer确实不能在pre-EBS复用，先保存具体源码冲突和可审查替代方案。未操作手机，未GPU执行/渲染/Metal，allow_boot/readback=false。[证据](evidence/gpu-canonical-checkpoint-2026-11-01.json)。


## 单4KiB日志producer的真实pre-EBS边界（2026-11-01）

按current检查实际source后确认了具体阻塞，未新造writer/codec：ZornUfsRead.cpp原zorn_write_log4k只接受Darwin内部gLogBlock的地址，每次都会刷新Mach/VM/CPU/显示/触控footer，调用原CPU/GPU transport，再经依赖gHost/队列/cache/MMIO ownership的hostWriteLog4k写入。它不是EFI BlockIO方法；原void log_word还会busy/off丢弃且不返回真实写错误。只有4KiB结构布局相同，不代表整个producer能在UEFI原样运行，不能补假的Mach/VM/IOKit/UFS服务使它通过。已有84text/3072footer/272B报告容量结论直接引用，不重跑旧套件。

原结构体与实际Darwin23 IOPlatformExpert编译配方、新FD实际UEFI配方的布局注解核对4096B/word偏移16、原footer3072B/84槽/偏移1024。真实SDK WriteBlocks的槽0x20、原64bit EFI_STATUS、固定child-relative2291712/parent-absolute5404416和WriteCaching字段偏移8编译核对；no-entry PE只作类型注解，未部署/执行，不能当writer或native权限。初注解checker只认BLR而实际尾调BR X5的拒绝与旧版保留，修checker未改生产代码。

具体替代方案已保存为out/zorn/gpu-checkpoint-sink-boundary/owner-proposal.json，仅是待审规范：只在payload前终止失败时，在原单4KiB日志块使用专用早期记录；128B头+2352B已有精确scalar报告+1616B保留零。原正常v18/84text/footer及v19/E20/v21不变，但该早期格式本身仍是新协议，明确需要机主对当前“不扩query codec/日志载体/84text/footer协议”的一项离线例外。未编写新encoder/decoder/native sink，也未以debugtext改名绕过禁令。规范保留raw64/known mask/部分报告不可用、只取首个失败lookup而非伪称完整512handle历史；用readonly nonce与外部manifest绑定避免bootSHA自引用。

未来至多一次WriteBlocks及成功后一次readback，必须实际同epoch typed discovery/GPT/EBS gate及稳定media，WriteCaching非FALSE则拒绝，不加flush/reset/retry或其他范围。记录不能持久化其自身失败的写/读status；那些raw值留私有RAM，缺少新鲜恢复记录只能判不可用。批准本方案也仅允许离线实现，绝不自动授权phoneboot/介质I/O/SCM/PAS/MMIO/GPU；原独立WDT/freshBCB/规范归档/ready等仍须闭合。

原FD58c00270/host8ef343bb及其内核/FAT/ADT不动，设备和生产源码未操作，allow_boot/readback=false。需机主决定这一项具体规则例外；未答复前不开发新格式、不重复通知或复跑旧检查。[证据](evidence/gpu-checkpoint-sink-boundary-2026-11-01.json)。


## 机主批准的早期终止记录离线实现（2026-11-01）

机主在本聊天明确答复“允许这项离线格式例外”，对应前项owner-proposal.json，授权已保存；这是原单4KiB日志块、仅payload前终止失败记录的狭窄离线例外，不授权boot/写手机/查询或GPU。其余query/HFI载体限制不变，不应反复再问同一权限。

新增ZORNGQF1编码与读取：128B头、9份原精确scalar报告片段、2480B使用/1616B保留零，完整raw64/known/origin/present mask/CRC/nonce与外部expected身份。片段按原字节保留，不另造firmware解析器；present只表示提供了字节，不能当原生成功。adapter自生的EFI形状错误同样保留完整64bit，并与nativeEFI来源分开。未提供expected时freshness明确unverified；即使匹配也不是认证/所有权/设备资格。C与Python各4096单字节损坏拒绝，512片段mask、修CRC语义损坏、raw64/未知/失败输出保留、3种expected身份失配与2真实当前源码突变通过。

维护中的read-zorn-log.py只增加新magic的显式CLI分支；其余decoder函数AST不变。同一份已归档旧0fe块的新旧CLI输出完全一致，只是读取器回归，无新手机/CPU/跨核运行栈观察，未重跑旧资格轮。原84text/3072footer/v18/v19/E20/v21不变。初构造的legacy fixture缺有效GUIfooter、旧reader测试harness缺脚本导入路径的拒绝均保存；修测试，未放宽旧parser。

ZornEarlyFailureSink实现仅为默认关闭的CPU缓冲准备，8192B持久context/4096B私有buffer，无commit/WriteBlocks方法。通过真实typed discovery与reader父子EBS/epoch/未retire/GPT/media稳定状态检查，WriteCaching不为FALSE则拒绝；不接受report/callback0替代owner，不保持协议指针。现阶段owner未观测、默认OFF、参数/别名/重复拒绝的ASan/UBSan检查通过，没有host硬件成功fixture，NativeAttempted/NativeStatusKnown/WriteAuthorized/runtime始终0。两个复制header只添friend声明，原source body/524288B owner ABI保持。

实际选定SDK配方编译、两个新对象独立SHA相同、13项真实类型尺寸、no-entry PE的关闭参数/目标/BSS/无新initializer与2个PE破坏拒绝通过。链接使用fresh真实AutoGen与canonical原entry，并显式绑定8个原已审计对象闭合其依赖，旧module archive排除，无强制未解析/成功stub；真实entry仅为noentry链接闭合，未调用，不能冒称新完整FD或所有SDK指令均无硬件路径。初缺AutoGen/原entry和checker函数名遮住builtin的日志保留。

原FD58/host8ef/内核/FAT/ADT与默认42保持；新增root reader分支使旧342当前为338匹配/4项授权源码差异，原reader preimage与旧清单SHA对上，旧proof不改。下一连续批次将真实终止失败collector、只读nonce/输入digest和新codec接入新的隔离canonical FD，正常调用与介质提交仍OFF；尚无collector实际接合、native writer/持久读回或GPU平台所有权，allow_boot/readback=false。[证据](evidence/gpu-early-failure-record-2026-11-01.json)。


## 真实终止失败collector接入新FD，原生提交继续关闭（2026-11-01）

沿用机主“允许这项离线格式例外”的明确批准，将既有ZORNGQF1源码、纯RAM collector和默认OFF typed sink接入真实canonical ZornBootMemoryDxe。批准范围仍仅离线，不授予phoneboot、介质I/O、SCM/PAS或GPU执行。正常PublishRange只初始化48B armed报告，不生成失败记录；真实WDT Failed和触控终止分支在原reset/deadloop之前记录，原返回/恢复顺序不改。Query、publication及required-discovery的错误接合保留，但正常driver没有调用这些入口。未来commit必须位于真正阻止payload继续的终止driver分支，不能仅凭helper返回错就写盘。

Collector仅调用既有READY-copy getter，unready片段缺席；实际query/publication/discovery/reader/父子lifetime/first-failed-lookup/GCD/PAS保持原精确scalar字节，未补造native成功、handle或租约。9片段/2480B使用/1616B保留的格式和原84text/footer没有再改。私有8192B持久context含独立对齐4096B record；两个不可变报告槽避免初始化报告发布后被终止报告改写。once拒绝重复/重入，release后不可变，getter acquire读取。检查发现输出还需拒绝覆盖三个私有atomic状态字，已修正；完整首版FD ec16b7d3…/外层25aed5d8…及源码/对象/日志均以独立inode保存，未覆盖历史证据。

修正后真实3MiB FD14248a3e…、模块9100ea6d…、新外层镜像557bca5e…完成。只读80B身份由新nonce、实际cabefd1e内核SHA和不含生成头/FD/boot的pre-injection输入清单组成，实际OS/CPU profile与格式契约叶子已显式绑定，避免自摘要循环；外部完整清单另绑定最终FD/boot。nonce和CRC只用于软件身份/完整性核对，不是认证或硬件权利。

36个ASan/UBSan collector场景覆盖可用片段组合、unknown/nativeEFI完整raw64、重复/重入、初始化不造记录、无效metadata、私有buffer和全部状态字别名拒绝；35份记录经Python reader与当前expected身份匹配。4项真实WDT/PublishRange前缀及真实disabled-owner join通过，native/SMC/touch仅为host double或未调用，不构成硬件成功fixture。2个实际collector源码突变、6个真实最终PE突变均拒绝；7个新候选自身SDK配方对象独立重编全SHA相同，17项实际类型尺寸确认。最终PE核对正常FALSE参数、owner关闭返回路径、真实终止目标、READY release/acquire、raw64存储、只读身份、零初始化private context及无新CRT。源码typed sink未新增commit方法，最终C ABI仍无条件返回DISABLED；整个模块保留真实原生方法，不能宣称全部SDK路径都无硬件操作或全CFG/PAGE已穷尽。

558个固件对象、559份依赖、3096项当前输入及4660项独立生成归档已核对。复用精确旧cab内核/FAT/menu/ADT，只重组新FD/shim/outerimage；没有新增CPU/GUI/内存/c50/0fe轮。旧342清单仍为338匹配/4项已授权源码差异，原清单/preimage保持。归档检查正确拒绝了Finder自行变化的非构建.DS_Store；该元数据不进入新编译证据，真实源码/对象/FD的SHA门槛不放宽。

仍没有持久读回或GPU执行资格。WDT原SMC Arg0/Arg1未进入本格式，header只保守保留adapter EFI_DEVICE_ERROR；owner尚未真实可用时也不能将该RAM记录写盘。记录无法持久化其自身失败的write/read状态，有限调用次数不保证provider墙钟有界。下一连续批次实现真正typed、固定单块、一次write及精确SUCCESS后一次readback的提交源码，原生入口继续OFF；不加flush/reset/retry、日志载体或其他范围。独立WDT/freshBCB/实际平台所有权与新候选ready仍未闭合，allow_boot/readback=false，GPU渲染/Metal未完成。[证据](evidence/gpu-terminal-collector-2026-11-01.json)。


## 固定单块提交源码及实际SDK注解完成，正常原生调用编译关闭（2026-11-01）

在新隔离目录实现ZornEarlyFailureSink::commit源码：原单4KiB日志块userdata-relative2291712，父坐标5404416仅记录、不传给child I/O；最多一次WriteBlocks，仅其精确EFI_SUCCESS后至多一次ReadBlocks，不加flush/reset/retry/其他范围。真实typed discovery/reader的同epoch GPT/CRC/GUID来源、精确prepared C++ owner、当前child MediaId/稳定media/WriteCaching FALSE、真实父子EBS gate在write/read前后分别复核。不是Linux/recovery/外部report或callback0输入。所有借用protocol/media/path/interface范围还必须与整个新sink分离。

保留原88B“准备报告”ABI，另加仅私有RAM的184B提交报告和4KiB readback缓冲；context12288B/align4096，原写入buffer仍独立4096对齐。prepare成功后仅私有借用同一持久C++ owner，未缓存或序列化firmware协议指针。184B报告分别保留两个raw64 native status、四阶段各两个原生lifetime-check原值、attempted/returned/known/passed/stable/match/隔离位；Returned位不在时raw0是未知，不能当成功。原88B报告只描述prepare，不代表commit总体I/O。9份原线格式片段不变，提交报告没有加入载体，记录本身仍不能持久化自身失败的write/read状态。

第一次实际I/O之前置真实discovery和reader的busy interlock，终止路径永不释放，即使provider返回错误或成功也不推断controller已静止；不retire/free/析构回收或重试。原native警告/错误优先保留，调用后的expiry/media变化原值另存；warning不进入读回，read错误不解释buffer。只有精确SUCCESS、真实gate稳定及整个4096B格式/字节核对均通过的代码分支才置Match，现阶段未执行此分支，绝非持久读回证据。缺新鲜恢复记录只能判不可用。

默认ZEF_NATIVE_COMMIT_INSPECTION=0把提交方法整个原生调用体编译掉，即使强传enabled TRUE也直接DISABLED，不访问owner/buffer、不制造native完成报告。宏1只用于离线、无入口且未调用的SDK ABI/指令注解，不是实际候选的运行开关或授权。内部C ABI没有enable参数，两份注解的caller均固定FALSE。真正终止C driver/新canonical FD尚未接合；不能因helper返回错而写盘，未来必须确认不再继续payload/候选扫描/GPU，并保留原主失败码。

9项ASan/UBSan关闭/参数/别名/真实未观测owner/重复/不可变报告拒绝及2个实际当前源码突变通过，native calls0，没有构造成功硬件owner/lease fixture。默认OFF导致未使用private字段的首次Werror拒绝已保存，用不求值sizeof标记保留两变体共同布局，未放宽编译告警，也无状态访问。实际canonical SDK配方新编译19份source/AutoGen/probe闭合对象，排除旧module archive，3组LTO对象独立SHA相同；16项实际类型/方法ABI确认88/184/12288/4096/524288/512/496和64bit EFI_STATUS、Read/Write槽0x18/0x20、WriteCaching偏移8。默认0与仅审计1分别链接NOENTRY PE，未部署/调用；不是新FD/kernel/boot。

最终注解检查默认方法仅mov DISABLED/ret、caller FALSE、inspection恰好两处BlockIO间接调用、实际child指针/MediaId/固定LBA/4096/分离buffer、原生status的STR X0完整64位和精确零分支、4次真实checkCommit调用、永久owner interlock、真实READY release/acquire及readonly80B身份。8个实际PE副本破坏default closure、caller参数、write slot、read LBA、raw64宽度、status判定宽度、postwrite gate、owner锁序列均拒绝；非法inspection selector2由实际SDK编译器拒绝，不生成对象。不能夸全CFG/PAGE/SDK所有指令均无硬件路径；provider耗时没有墙钟保证。

注解复用父FD的只读nonce仅作绑定，不是新候选nonce或租约。原FD14248a3e/host557bca5e/cab内核/FAT/menu/ADT/默认42保持，没有重跑CPU/GUI/内存或c50/0fe，旧342仍338/4。下一连续批次按固定builder接入真正终止driver与新实际FD，native body仍编译0、caller FALSE，并生成新的无摘要循环nonce/输入身份，精确复用旧kernel/FAT/menu/ADT后审计归档；不得用inspection1启用运行。实际live平台资格、独立WDT/freshBCB、读回保护和新候选ready仍缺，allow_boot/readback=false，GPU渲染/Metal未完成。[证据](evidence/gpu-terminal-commit-source-2026-11-01.json)。


## 终止C调用点及关闭的单块提交进入新实际FD（2026-11-01）

将上一批4份已核对的commit/copied源码及identity声明接入新的隔离canonical package，C header只移动既有无enable参数的C ABI声明供真实C driver使用。仅在原WDT Failed和touch失败的reset/deadloop分支，真实记录收集之后加入关闭提交入口；正常成功路径、query/publication helper错误路径不提交，不造失败或增加日志载体。原主失败码与reset/deadloop顺序保留。actual INF显式ZEF_NATIVE_COMMIT_INSPECTION=0，未把inspection1变为运行选项。

真实3MiB FDb5cc3b15…、模块2d1bbfe9…共110592B、新外层bootaedc3bf0…完成。实际编译/预处理确认commit原生body整段不存在；最终链接保留入口仅mov DISABLED/ret。LTO消除了两处没有副作用且结果未使用的关闭调用，这是正常优化，不能冒称两个live commit调用已执行或为保留调用新增伪硬件动作。C源码接合已编译，宏0关闭行为是实际最终产物。原prepare入口这次保留State非零返回USED、否则DISABLED的原检查，只读自身准备状态，不访问owner/blob/provider；首次checker误套上批常量返回、随后CINC NE机器字转写假设均被拒绝并保留，修checker未改provider或放宽关闭边界。

实际FD抽取的模块与build OUTPUT全文件相同。最终C ABI检查184B私有提交报告的acquire/复制长度、12288B/align4096 sink初始零BSS、正常query/storage FALSE门、原terminal collector调用、readonly80B候选身份、原始raw64存储和无新CRT。8个实际PE破坏控制、7个候选自身实际配方独立重编对象SHA相同、20项类型尺寸核对通过。整个模块仍含其他真实SDK/native路径，其他CFG/PAGE仍受链接器契约约束，不能说整模块无硬件指令、任意坏指针安全或provider墙钟有界。

4项ASan/UBSan测试直接以C编译真实WDT/PublishRange前缀，跟踪真实collect→commitAdapter→reset顺序；commit adapter的任意非零测试返回值未替换原EFI_DEVICE_ERROR/EFI_NOT_READY。该driver测试中的WDT/touch/reset/adapter是明确double，不是硬件证据。另用新package的真实typed owner/class/C ABI与宏0检查报告仍不可用、原readonly发现/准备不执行；无host成功hardware owner/lease fixture。5项新入口拒绝覆盖boot、OS27、冲突stage、旧输出和inspection运行参数。

新只读nonce/kernel/pre-injection bundle身份独立生成，明确排除生成头/FD/boot，实际OS/CPU profile及格式契约/父kernel/FAT叶子绑定，外部清单再绑定最终镜像。未沿用SDK注解父nonce冒充新候选；CRC/nonce仍非认证或权限。558固件对象/559依赖/3095项当前构建输入和4557个独立inode生成归档核对。精确复用cab内核及旧FAT/menu/ADT，只重组新FD/shim/outerimage；无新CPU/GUI/内存/c50/0fe轮，默认42、桌面3a、旧342当前338/4及全部旧proof/preimage保持。

这仍是关闭调用的真实FD，未操作手机，没有native介质I/O、query、SCM/PAS或GPU执行/渲染/Metal资格。真实可写owner之前的失败和永不返回的provider无法靠此块记录；记录也不能持久化自身failed write/read status。下一批形成首次介质资格验证的具体离线caller/候选提案，先完成可审查源码/目标/保护设计，不新造普通成功boot的失败。若专用资格诊断要在query成功后有意终止，也必须作为单独提议的真实adapter终止策略、保持UNAPPLIED/未选择，不能假报native硬件失败或擅自扩协议。任何首次native调用、介质写入/boot或对pre-owner失败可见性要求的例外，都需要新的明确机主决定；旧离线格式批准不涵盖。现有独立WDT/freshBCB/有界回收/ready门槛保留，allow_boot/readback=false。[证据](evidence/gpu-terminal-commit-integration-2026-11-01.json)。


## 首次UEFI介质资格诊断：具体离线提案完成，策略未批准（2026-11-01）

隔离实现ZornMediaQualification真实C ABI及C驱动分支，原WDT/touch处理后、payload发布前进入；默认0在参数访问前返回DISABLED。拟议分支只调用真实typed discovery/GPT/EBS owner；失败保留真实adapter结果，成功则明确以stage8/origin adapter/EFI_ABORTED表示“专用诊断主动终止”，不伪称native硬件失败或普通成功boot。只复制真实READY记录，prepare成功才以同一个私有owner进入原固定child日志块commit；无重试/释放。C驱动对所有诊断结果都进入原system recovery reset/deadloop，永不发布payload或进入XNU/GPU。专用策略、成功后主动终止及pre-owner失败不可见边界仍待机主决定；此前离线格式许可保持有效。

新80B结果/8192B context仅私有RAM，不扩9片段/原4096B格式/正常84text/footer。原184B提交结果同样不在介质记录内；新鲜nonce/CRC记录不能证明自身Write/Read两项EFI_STATUS均成功。有效owner之前、provider不返回或自身写读失败不能靠同一块持久化，缺失/旧记录必须unavailable。未放宽实际typed owner、主备GPT/CRC/GUID、MediaId、WriteCaching FALSE、EBS前后gate、2291712固定childLBA及一次write/精确SUCCESS后一次read；没有live owner/lease或GPU权限证明。

两个真实SDK NOENTRY链接变体、24个新源/AutoGen闭合对象、8份独立完整SHA、15项ABI、3项无效selector拒绝、7个最终PE破坏控制通过；19源单元并非新完整FD。新caller9项拒绝及真实C驱动默认/选中2项ASan/UBSan检查通过；不构造成功hardware owner/回调/handle。链接检查发现只根真实驱动入口会让NOENTRY的gBS被LTO折成NULL，已保留真正SDK模块入口/构造列表后重链核对真实gBS和调用，未执行构造函数。非LTO COFF独立输出的CodeView路径与跨秒timestamp差异、初checker的ADRP转写假设均保留；完整SHA通过实际同命令独立编译取得，不抹timestamp/伪造元数据。普通SDK路径及完整CFG/PAGE仍不是硬件证明。

runner提案新增启动前纯文件准入，当前pending模板在USB前拒绝；未来需完整候选/新身份/批准/源及归档pins、600秒/无screen capture、原fresh BCB、一次性claim、recovery开始、BCB写前精确serial/zorn/slot b，禁止bootstrap。原BCB/bootloader/wait helpers AST不变；复用实际reader --block/--early-expected离线接口，旧/坏/未改变记录只标unavailable。24项纯host文件/decoder检查通过，真实runner main从未执行。三个补丁dry-run并只应用于独立review sandbox，逐文件与提案全同；维护源码、当前FDb5cc3b15/bootaedc3bf0/默认42均未应用或改变。

这批没有生成选中策略的实际新FD/boot，SDK注解继承父身份，不是新nonce或启动租约。未操作手机、原生介质、query、SCM/PAS或GPU。机主先决定这项新诊断策略及失败可见性边界，之后才按固定builder完成真实新候选、fresh acyclic身份、currentstart/kernel/FAT/menu/ADT/FD/输入/独立归档和ready/独立WDT/fresh BCB闭合；本批allow_boot/readback仍false。明确方案与可审查补丁在out/zorn/gpu-media-qualification-proposal/owner-proposal.json；[证据](evidence/gpu-media-qualification-proposal-2026-11-01.json)。


## 已批准专用策略的完整离线候选完成，尚未启动（2026-11-01）

机主明确答复“批准该策略，继续制作完整候选”，已保存新owner-approval并绑定原proposal SHA；这是专用终止策略、pre-owner/不返回I/O不可见边界及完整候选制作许可，不伪称已经取得phone/native执行许可，也不重复询问该策略。固定build-zorn-firmware.py新增独立选项，按批准记录和源receipt构建隔离真实FD。普通既有stage/default不变，inspection宏仍0；只有此专用诊断stage的media_commit/caller/driver宏为1。编入真实UFS/GPT/EBS owner和原单日志块提交代码，不是调用或租约。

实际3MiB FD4f71bc54…、模块da848e41…、完整外层boot57c2ed36…生成。新nonce与kernel/pre-injection输入digest只绑定生成头/FD/boot之前的叶子，最终manifest再绑定实际产物，不自哈希/沿用父nonce。实际FD有界抽取出的module与OUTPUT全字节同。最终真实LTO调用ZcdRun(TRUE)、真实READY记录、prepare精确成功后commit、adapter策略EFI_ABORTED终止、原system recovery reset/deadloop均核对；只有原child LBA2291712/4096B的2个native方法，4次真实双lifetime/media gate顺序、原raw64结果、warning不读回、永久owner interlock保留。LTO将内部commit特化为W0 bool且硬绑定static owner/sink，正常旧关闭入口W0=0在访问owner之前返回；没有误套NOENTRY的X0/X1/W2外部注解布局。8个实际新FD PE破坏控制、5个本候选真实配方独立对象SHA通过。原提案9+2host拒绝/实际C前缀和15ABI检查按源字节相同继承，没有重跑整套或造成功native owner。

精确复用cabefd1e…Darwin23完整prelinked内核、原FAT/menu/ADT；本候选额外以真实配方重新组装当前start.s，完整对象SHA a7786002…与内核所用对象相同、活动对象不改。实际boot解压逐字节为新shim+新FD+原FAT；原WDT ZORNGHWD/touch ZORNTPWR均mode1及反码正确。未重建旧kernel/FAT或重复c50/0fe/CPU/GUI/内存轮，8GiB/八核/九轮/Data/dim64/触控约束保持。普通SDK CFG/PAGE/provider墙钟和真实hardware owner仍未由静态检查证明。

真实fixed runner已接入已审查的特殊policy/单次claim/恢复后旧decoder接口；原BCB/bootloader/wait helpers AST不变。另补强未来ready镜像也不得绕过显式资格policy选项，并拒绝非mode1、GPU开启或非payload前终止的manifest；9项新纯host准入检查和4项CLI拒绝通过，runner main未执行。补强前已组装的首份完整image/policy/源码preimage全部保留，再以显式host-source转换清单和新final policy从固定builder重组；两份boot全SHA相同，未改旧proof或仅替换旧SHA。

559个固件对象/560份实际依赖/3107项当前输入及完整生成归档核对。新可变对象/归档均独立inode/APFS clone，不硬链接活动对象、不改_副本或默认42/桌面3a/旧归档。新增维护脚本改动均不在旧342清单中，原338/4历史差异保持，不冒称重查了全部旧清单。GPU供电/SCM/PAS/QSMMUv500/IOVA/DMA/固件执行/渲染/Metal仍未资格化。

下一步才是这个确切候选的单次原生UEFI介质轮：activation-proposal.json已列出92988a43/zorn/b、recovery起步/禁止bootstrap、原日志预备份、原misc首864B/尾部保留整页读回、原独立WDT、600秒有界回收与恢复失败停止规则。机主此前批准的不可见边界保持；新鲜CRC/nonce记录不包含自身write/read私有状态，不是两个EFI_STATUS成功或GPU执行证明。当前无新执行授权，fresh BCB/当次hardware WDT均未观测、allow_boot/readback/WriteAuthorized为0，未操作手机。[证据](evidence/gpu-media-qualification-candidate-2026-11-01.json)。


## 单次原生介质轮在Recovery前置条件处拒绝，未启动（2026-11-01）

机主明确回复“授权下一轮这一次有界介质验证”后，保存了绑定57c2ed36/原activation-proposal的独立执行授权，3107项当前输入/4550核心归档/6入口源码快照全部匹配；仅新建per-trial image/ready/policy，冻结候选manifest不改。条件allow_boot只表示该次执行权限，未伪称已有新BCB/当次hardware WDT或native/GPU lease。

固定runner的20261101-154811-57c2ed36准入在第一次adb枚举后拒绝：未识别目标为recovery。原日志未保存实际返回state，不能进一步判定未连接、fastboot、Android或当前硬件健康。严格禁止bootstrap/额外boot的门正常生效，在BCB读取/写入、原日志读取、重启bootloader和fastboot boot之前停止；无preboot/misc/bcb/fastboot/checkpoints文件。没有进入UEFI/原生介质/GPU，不能据此判断driver硬件成功或失败，也未测试有界回收。

设计中的单次claim在首个USB调用前已consumed-no-repeat，记录不清除、不补造新的同轮许可，不自动重试。已停止设备操作，保留当前未知设备状态及历史last recovered结论；后续需要机主确认连接/Recovery状态，并对任何新准入另行明确授权。按原物理协助停止规则暂停heartbeat、卸载独立唤醒agent，不做flash/恢复或猜测设备状态。[证据](evidence/gpu-media-qualification-attempt-2026-11-01.json)。


## 原厂重刷后的64GiB双系统重新安装（2026-11-01）

机主重新线刷完整Android后，明确要求保留Android系统/槽位A/OrangeFox，在userdata尾部为iOS划出64GiB；Android应用与个人数据可清空。该新安装授权覆盖这次重建所需的旧存储/slot-b限制，不能把旧Data内容或旧运行证明当作当前设备。其余设备身份、CPU/触控/8GiB内存/默认镜像保护和GPU调用禁令保持。

已按实际OrangeFox R12.0身份接合官方dual_sys的F2FS在线缩容与GPT流程；userdata保留起点/GUID，缩为168.453125GiB，新增unixnu为64GiB。主备GPT均精确读回，重启Recovery后新块设备、加密映射和F2FS尺寸通过；没有格式化Android数据、改槽或写Android系统/Recovery。iPadOS17的9.38GB原镜像只写入unixnu，随后完整读回SHA fd43ee70…一致。

新增显式unixnu64存储profile：内核只接受唯一unixnu名称、实际type/uniqueGUID/精确边界，无userdata回退；Data移到unixnu相对16GiB，沿用已验证8GiB seed/COW实现和2097217块窗口，新65块元数据及新cookie已写/readback，GPT/root/fences保持。64GiB是专用分区容量，目前Data逻辑容量8GiB，其余保留，未冒称64GiB Data。

实际iOS17原生内核和原kext完整重链e3288034…，7个存储函数/220调用边、六provider桥、原Data marker路径、原GPU关闭行为/108函数/233边/81槽及独立当前start.s对象核对。新FAT/ADT/menu/WDT与完整外层image5c622cef…核对，11884当前输入及独立inode/APFS归档绑定。最初工具PATH、误移动派生unstripped而未重链noctf、fresh/touch与checkpoint组合拒绝均保留；未改旧proof或放宽生产guard。

首次新Data初始化按原fresh保护不启用触控，在单独新存储镜像验证后再恢复原retained触控配置；原触控代码和基线未移除。当前一次固定runner新安装轮进行中，freshBCB整页及尾部读回已过，仍待Recovery回收和新日志；尚未确认iOS可用界面或Android实际启动，GPU/Metal未启用。旧57/c50/0fe不重启。[证据](evidence/dual-system-reinstall-2026-11-01.json)。

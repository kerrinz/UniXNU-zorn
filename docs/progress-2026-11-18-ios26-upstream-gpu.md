# 2026-11-18：新上游GPU与呈现耗时

新Metal／metal2vulkan／Turnip已完成K80实际运行验证，完整GPU、显示、生命周期与FT3683验收仍未完成。当前无人工操作条件，所有设备步骤使用独立归档、固定SDK37私有5039、精确92988a43／zorn／slot A、单次claim、300秒设备看门狗和600秒Recovery返回上限。未创建新commit或push。

## 282：已知图像和有界客户端生命周期

kernel `c8643edc…`／boot `1d29fe20…`，保留281根 `b87e132b…`、FD `1bf94507…`、ADT `9aaa913f…`。实际Metal设备、library、pipeline、GPU渲染和CPU可见CRC `718ed2ce`通过，120次已知呈现完成，4个注册客户端均真实Close成功，测试程序exit0。3192字节／32条完整journal无缺口，原生观察器丢失0，相机103秒帧显示绿／紫4×4棋盘格。一次启动333.13秒自动回TWRP，保护／BCB检查通过。

最小修复位于`native/ios26/ZornApplicationObservation26.inc`：未被跟踪或已经关闭的客户端回调先检查原子发布的观察身份，再尝试诊断锁；真实被观察事件的竞争、溢出、错误和拒绝记录保留。主机测试复现旧误计数，并验证真实丢失仍被计数；ASan／UBSan／TSan及完整原生重编通过。这个缺陷与281的两次丢失相符，但没有把旧281原始失败回执改为通过，也不声称已证明那两次的具体来源。

首次282主机启动路径在沙箱端口检查处拒绝，尚无claim／USB／boot；原始失败记录保留。随后具备本机端口权限的路径才执行唯一一次实际启动。

详见[282精确设备证据](evidence/k80-gpu-v282-known-image-device-2026-11-18.json)。有界探针通过不等于普通桌面、所有任务隔离、失败恢复或完整FT验收通过。

## 283：专用根策略切换，内核未启动

实际281根到已有280普通backboardd根 `d9856b43…`仅相差22个4KiB页面／11组／90112字节。独立重算Data边界、根放置与保留空间，完整本地镜像哈希和增量回放匹配。固定安装器先核验13716个已记录父页面与全部保护／BCB，再逐组写入读回；安装成功、无启动，前后TWRP身份及保护一致。

仅切换`NativeAdrenoMetal.clients`为backboardd并禁用测试探针。签名Metal／runtime／Turnip文件保持与282已知图像所用根一致。Android、17、Data、GPT、Recovery和启动分区不在写入范围。详见[283实际安装证据](evidence/k80-gpu-v283-desktop-policy-installed-2026-11-18.json)。

283完整内核、包和离线归档保留，未创建启动claim。启动前审查发现串口复用器在某些晚就绪情形会把已完成的耗时记录与尚未就绪的ROI截图一起等待，因此由有实际源码修复的284接续，未浪费一次283设备启动。

## 284：普通backboardd与被动呈现耗时

kernel `93511957…`／boot `6d6f4127…`，复用已安装的`d9856b43…`根，FD保持不变，ADT `5c01b2f6…`。完整1399输入链接／142项受检查头文件依赖和实际原生身份检查通过。`ZornSerialShot270.h`仅调整晚就绪等待条件：完成的CPU耗时包可独立发送，随后继续等待截图；38帧限制、DMA源缓冲完成条件与原GPU后端保持原语义。新旧实际头文件对照测试复现阻塞，ASan／UBSan／TSan和原有ROI／CRC／流控检查通过。

一次无人值守启动采到9份真实CPU时钟快照及完整ROI，30个普通进度帧、7个ROI块和1个耗时包；333.12秒自动返回TWRP，保护／BCB检查通过，相机145秒帧显示实际锁屏。backboardd的两个客户端仍然存活，本次被动观察不要求守护进程退出，不能据此补齐其最终资源回收验收。

首末有效发布间隔79969毫秒，完成533次CPU像素复制。该区间每次完成复制对应的平均CPU墙钟耗时为：show约16.02毫秒、lease等待约4.24毫秒、cache acquire约0.39毫秒、队列驻留约0.013毫秒。lease实际调用约3.98毫秒，已包含在4.24毫秒内，不能重复相加。

复制计数速率约6.665次／秒，包括空闲时间；它不是物理FPS、GPU硬件时间戳或固定负载基准。九份成本记录的时钟／饱和／发布故障均为0。CF记录没有采到后端失败或丢失，但旧紧凑观察器记录丢失4，不能宣称没有任何未观测失败。

这些数据尚不能把约150毫秒平均复制间隔全部归因于CPU显示复制。GPU在present前的工作、原生接口等待、用户态调度／渲染和空闲时间需进一步区分。详见[284精确设备证据及全部采样](evidence/k80-gpu-v284-upstream-present-cost-device-2026-11-18.json)。

## 285：复用上游计时，晚报告未完整传出

kernel `a831bf67…`／boot `a940ef4d…`／根 `03bb3929…`。保留实际279原生arm64e/PAC Rust archive和280 Turnip，重编签名Metal frontend；复用真实上游pipeline、编译、提交回调、等待及线程CPU计数。仅在实际Metal设备创建后启动一次报告线程，20／120秒各报告一次，每份单次writev、短写即停止；省去调用栈／地址归因，未启用shader dump、abort探针或指令改写。

专用根7454页／130组安装及读回成功，父页面13716页和保护／BCB通过。一次启动333.20秒自动回TWRP，相机显示锁屏，9份呈现耗时无时钟／发布故障。完整GPU验收仍为false；紧凑观察器丢失5保留，CF记录未采到失败或丢失。

首份完整上游报告显示累计89次pipeline创建4420毫秒，6次commit到完成回调累计8129毫秒、最大6232毫秒；这是启动早期CPU墙钟统计，包含驱动、调度等工作，不能当作纯GPU时间。第二份在固定30个普通进度帧临近结束时到达，只传出768字节。实际内核journal已记录8527字节、无缺口／待完成写入，但主机仅收到4742字节。因此两报告完整性严格为false，不能计算稳态差值。

[285实际安装](evidence/k80-gpu-v285-scalar-root-installed-2026-11-18.json)与[285设备采样](evidence/k80-gpu-v285-upstream-scalar-timing-device-2026-11-18.json)分别保存。已消费的原生review中两项沿用描述字段有误：实际探针保持禁用、用户态Metal文件实际改变；补充更正文件说明依据，未覆盖历史review、原始日志或运行回执。

## 286：两份上游报告完整采到

kernel `bd9e561b…`／boot `f13a9877…`／根 `d867d741…`／ADT `c2e6af9c…`（完整哈希以证据为准）。第二次报告提前到设备发布后60秒，保留20秒首报和最多两次／单次writev约束。相对285根23页／15组／94208字节，完整本地回放、真实安装13732个父页面及全部改动页读回通过。没有改变GPU、Rust、Turnip、渲染或时钟策略。

一次启动332.91秒自动回TWRP，串口／相机／保护／BCB通过，8017字节／6条journal全部收到，缺口和pending均为0，两份报告完整。9份呈现耗时故障0，CF未采到失败或丢失；旧紧凑观察器仍丢失6，不能据此宣称没有任何未观测失败。相机145秒帧为物理锁屏。

约40秒的两报告窗口新增183次commit到完成回调，累计24815毫秒，均值约135.60毫秒；scheduled等待累计5179毫秒，均值约28.30毫秒；pipeline创建新增29次、723毫秒。各指标存在包含／重叠关系，不能相加。最大耗时仍为跨窗口累计，不能相减得到窗口最大值。线程CPU报告在40002毫秒窗口计30049毫秒，其中ca.display.prim约13132毫秒、m2v队列等待线程约7867毫秒；这些也不是GPU时间。

另一个约80秒呈现窗口完成508次CPU复制，show平均约14.82毫秒、lease墙钟约3.93毫秒。它与上述40秒窗口不同，约6.35次／秒的复制计数速率包含空闲，不能换称物理FPS或优化收益。

[286安装证据](evidence/k80-gpu-v286-scalar-root-installed-2026-11-18.json)与[286精确设备证据、两份原表及累计差值](evidence/k80-gpu-v286-upstream-scalar-timing-device-2026-11-18.json)绑定实际构建。下一步测量真实IOKit Submit／Wait／内存调用，以区分串行锁、页表切换／fence排空和实际渲染，不按猜测调频。

## 287：定位原生接口墙钟开销

kernel `ae5b863f…`／boot `1eace80e…`／根 `03593ebb…`。复用原生arm64e/PAC Rust，实际重编Turnip与Metal frontend，在真实ABI1 IOKit调用外侧记录调用次数、CPU墙钟总时长／最大值和错误／超时分类；计数更新不持有跨IOKit调用的观察器锁。沿用20／60秒两份有界标量报告，没有启用调用栈、shader dump或指令改写。

11724页／248组专用根安装及逐组读回通过。一次无人值守启动333.44秒自动回TWRP，保护／BCB通过，相机145秒帧显示锁屏。两份报告和8995字节／6条journal完整收到，无缺口／pending；独立RPC计数两份均无丢失或故障。旧紧凑观察器丢失6仍保留，CF没有采到后端失败或丢失。

约40秒窗口内，GetTimestamp新增348次、均值19.31毫秒；GetStatus新增167次、均值13.40毫秒；SubmitBatch新增168次、均值27.28毫秒；WaitFence新增548次、均值13.83毫秒且无错误／超时。各调用时间包含等待串行锁及上下文处理，可能跨线程重叠，不能相加成为GPU耗时。

GetStatus的167次非超时错误不能直接判为GPU故障：实际源码未给该客户端连接status后端，返回Unsupported，所选Turnip明确容忍这一缺少的能力。计数仅记录错误类别；上述返回值判断来自源码，不能伪称日志记录了原始错误码。后续若补接status，必须连接真实故障／挂起状态，不能用恒定成功对象替代。

源码显示Query、GetStatus、GetDeviceInfo与全局CP时间戳也走了完整进程页表Select／Restore。该证据支持下一步在保留真实任务、资源与MMIO检查的前提下，验证只读查询省去这两次切换。287的约135.93毫秒commit到完成回调均值、6.77次／秒CPU复制计数都不是固定负载FPS，不据此宣称优化收益。

[287实际安装证据](evidence/k80-gpu-v287-native-rpc-root-installed-2026-11-18.json)与[287实际调用窗口和精确构建](evidence/k80-gpu-v287-upstream-scalar-timing-device-2026-11-18.json)保留原始采样与限制。完整GPU／Metal／显示／FT验收仍未完成。

## 288：只读查询省去GPU页表切换，实机采样通过

kernel `dfdc82d1…`／boot `acdc3516…`／根 `c33f8f56…`。Query、GetStatus、GetDeviceInfo和全局CP时间戳读取在direct路径中省去进程页表Select／Restore；保留串行操作作用域、真实任务／资源／MMIO检查、原始返回值及错误处置，内存、提交、等待和关闭继续使用原上下文流程。实际重编33个原生对象，1399项完整链接及142项有效头文件检查通过；Metal frontend、Turnip和原生PAC Rust均复用287原始字节，计时协议仍为287。

专用根仅更新日志会话标签，36页／9组／147456字节安装读回通过，核对13754个父页面，布局不变。一次无人值守启动332.87秒自动回TWRP，保护／BCB一致，接收器和相机exit0。两份标量／RPC报告完整收到，8851字节／6条journal无缺口／pending；两个RPC快照flags和dropped均为0。初始GPU任务、真实fence与CPU可见结果检查通过，相机145秒帧显示实际iOS锁屏。

约40.002秒窗口，GetTimestamp新增289次，均值8.05毫秒；GetStatus新增122次，均值8.75毫秒，全部为所选后端未实现status能力对应的非超时错误分类，不能当作GPU故障。287对应均值为19.31／13.40毫秒；这一观察支持继续排除上下文切换开销，但负载未固定，不能解释为同工作量加速比。SubmitBatch均值30.44毫秒、WaitFence15.09毫秒且无错误／超时，提交／内存串行化仍待推进。

新增122次commit到完成回调累计11150毫秒、均值91.39毫秒；另一个83.321秒窗口完成523次CPU复制，show均值14.81毫秒、lease墙钟2.51毫秒。两者窗口不同且包括调度／空闲，不是纯GPU时间或物理FPS。旧紧凑观察器丢失从7到9必须保留；CF未采到后端失败或丢失，9份呈现成本故障均为0。这次没有人工触控、解锁或桌面稳定性验收。

[288实际安装](evidence/k80-gpu-v288-query-root-installed-2026-11-18.json)和[288精确构建与实际计时](evidence/k80-gpu-v288-readonly-query-scalar-timing-device-2026-11-18.json)绑定真实输入。后续CPU视图优化前，增加对确切且唯一进程链表成员的显式检查，避免仅依靠已省去的context入口来保证该约束；主机边界测试与硬件可达性须分开记录。完整GPU／Metal／显示／FT验收仍未完成。

## 289：CPU视图与进程身份检查实机观察，RPC计时未通过完整性

kernel `60c33ec8…`／boot `ac852931…`／根 `3d59c447…`。在保留真实任务、资源、逻辑VM与原始结果的前提下，CPU map／unmap、token视图和租约查询省去direct路径中的GPU页表切换。新增确切且唯一的进程链表成员检查，明确拒绝未登记／重复成员、已污染VM及不匹配调用任务；主机实际源码对照证明288会进入这些模拟后端边界、289会提前拒绝，不能把该测试说成真机出现了非法指针或GPU故障。原生GPU分配、映射、提交、等待、关闭和失败后端代码不变。

实际完整链接1399输入、142项有效头文件检查、CPU16KiB配置、实际调度／CPU视图／租约／失败处置及并发检查通过。继续使用287签名用户态字节和原生PAC Rust；专用根仅更新日志会话标签，16页／8组／65536字节安装读回及13754个父页面核对通过，存储布局不变。

一次无人值守启动333.13秒自动回TWRP，保护／BCB一致，串口和相机exit0；145秒帧确认物理锁屏。初始GPU任务、fence、CPU可见结果及9份被动呈现成本检查通过，CF未采到后端失败或丢失；紧凑观察器丢失2到3。完整8865字节／6条journal、两份上游标量报告收到，无缺口或pending。

RPC观察器两个快照都记录flags4、dropped3。实际共享计数器在trylock竞争时丢弃更新并置Lost；这是可见的诊断计数丢失，不是GPU任务失败证明。严格解码器保持`native_RPC_complete=false`，不生成合格RPC窗口；原始计数和未验收差值仍保存。这次CPU映射／解映射耗时不能作为完整性能结论，不重跑同一构建来掩盖丢失。

独立呈现窗口79.85秒完成701次CPU复制，show均值15.03毫秒、lease墙钟2.09毫秒；复制速率包含空闲，不是物理FPS。两份上游标量报告新增253次commit到完成回调、累计14899毫秒，仍是非固定负载的CPU墙钟聚合，不是纯GPU时间或同负载收益。

[289安装证据](evidence/k80-gpu-v289-cpu-root-installed-2026-11-18.json)和[289实际构建、完整日志及RPC未通过判定](evidence/k80-gpu-v289-cpu-view-scalar-timing-device-2026-11-18.json)保留实际结果。先修复观察器竞争，再继续成功提交保留真实在途fence／资源的离线候选；该异步候选尚未部署或启动。完整GPU／Metal／显示／触控／生命周期验收仍未完成。

## 290：真实在途提交与无丢失RPC观察

kernel `6b9db0da…`／boot `32c71ce7…`／根 `449ce79a…`。实际成功Submit后，只有真实队列或VM提交资源仍在途时才保留该进程的硬件上下文；不提前宣布fence完成、不释放在途资源。已有Wait、关闭、MMIO、内存与失败后端保持原代码；跨上下文切换仍经过真实排空／TLBSYNC。主机回归覆盖连续同客户端提交、真实等待边界、关闭失败保留、完成后关闭，以及提交成功后才出现的故障不得返回成功。显式主机后端边界不能代替新构建的真机关闭验收。

另修复289观察器的真实竞争：短用户态互斥只覆盖计数更新／快照，IOKit调用不持该锁；快照在锁内取得时间。原trylock源码丢计数可复现；真实锁错误、时钟与饱和故障仍使观察无效。重编签名Turnip和Metal frontend，原生PAC Rust、ABI1及287计时协议保留。完整内核链接、实际头文件／SDK依赖、共享头字节与标量／RPC回归通过。

独立根4292页／129组／17580032字节及13754个父页面核验、安装读回通过，布局不变。一次无人值守启动333.24秒自动回TWRP，保护／BCB一致，串口／相机exit0，145秒帧确认锁屏。初始GPU任务、真实fence与CPU可见结果检查通过；两份报告、9005字节／6条journal完整收到，无缺口／pending，两份RPC快照flags0／dropped0。

约40.013秒窗口，SubmitBatch365次、均值10.21毫秒；WaitFence1310次、均值8.22毫秒，其中346次为正常在途等待超时，非超时错误为0。GetTimestamp均值4.17毫秒，CPU unmap133次、均值0.207毫秒；GetStatus365次仍为缺少status后端所对应的非超时错误分类，不能换成GPU故障或假称已有该能力。观察原始错误类别与基于源码的解释分开保存。

上游标量窗口新增365次提交到完成回调、累计20698毫秒，均值56.71毫秒。另一个80.037秒窗口完成817次CPU复制，show均值17.05毫秒、lease墙钟11.92毫秒；异步后部分真实等待移到后续阶段，不能只看Submit返回变快，也不能重复相加包含关系的统计。复制速率包含空闲，不是物理FPS或固定负载加速比。

完成fence在九份采样中820→1637，两个普通backboardd客户端持续存活，未要求守护进程退出；其最终关闭未验收。CF未采到后端失败或丢失，但旧紧凑观察器丢失8→36必须保留，不宣称没有任何未观测失败。完整GPU／Metal／显示／FT验收仍未完成。下一步核对在途GPU期间的新客户端初始化／外部上下文交接，并用新构建重新验证已知图像、CPU结果和4客户端Close／exit0。

[290根安装](evidence/k80-gpu-v290-async-root-installed-2026-11-18.json)与[290实际构建、全部报告和限制](evidence/k80-gpu-v290-async-submit-scalar-timing-device-2026-11-18.json)记录精确输入。启动前的归档预检曾拒绝模板误改的固定fastboot哈希；失败草稿保留，修正后完整重建归档及回归，工具校验未放宽、没有错误工具或失败草稿的真机尝试。289原始包的一项沿用描述字段仍写288；补充更正绑定实际源码／构建，不覆盖已消费包、review或运行记录。

## 291：实机棋盘与四次Close可见，严格日志绑定未通过

kernel `66824792…`／boot `fab7b08e…`／根 `bb489797…`。复用290签名用户态与异步提交后端，在实际任务／服务准入后，使用已有真实排空／idle／SMMU恢复后端完成有界外部上下文交接及新客户端初始化。Close的零预算正常轮询保持不变；正预算到期停止操作并保留旧上下文及在途资源。源级回归覆盖实际调用、任务身份、失败保留和OOB准入，主机MMIO／电源／原生排空边界仍显式标记。

恢复265整屏串口截图及267原始图像探针，关闭无关桌面观察线程。专用26根仅改客户端策略、探针启动项和桌面计时环境，31页／12组／126976字节安装读回通过，核对13755个父页面；布局与290用户态字节不变。一次临时启动332.80秒自动回TWRP，BCB和保护通过，相机exit0。99秒相机帧明确显示实际4×4绿／紫棋盘，145秒已回锁屏；整屏串口缩略图完整收到。

严格接收结果保持`verified=false`，错误为`native/program task identities differ`。已定位到本轮源码遗漏：`ZornApplicationStderr26.inc`及`ZornJournalCapture248.inc`仍沿用290的backboardd过滤器，原生记录对应探针任务10，而stderr／journal对应backboardd任务11。探针CRC和exit日志未被捕获，不能凭相机补造这些结果。旧紧凑观察器最后丢失1条也保留。

独立解码的原始客户端记录显示四个已登记客户端64／129／194／259均属于任务10，全部Close stage16、raw0、无后端failure或诊断丢失；GetStatus仍有Unsupported拒绝类别。该独立证据与严格整体未通过同时保存，不将291重新标为完整通过，也不重复启动相同构建。

[291实际根安装](evidence/k80-gpu-v291-known-root-installed-2026-11-18.json)和[291严格失败、原始客户端记录与相机帧](evidence/k80-gpu-v291-known-image-incomplete-device-2026-11-18.json)绑定精确输入。292只修正两处诊断进程选择并重编完整内核，保留291根与290用户态；新增测试复现291旧选择并检查准确探针名、错误名称／描述符／写入拒绝，验收条件不放宽。

## 292：新异步后端的已知图像与完整有界生命周期通过

kernel `82e5126e…`／boot `26d9434a…`／根仍为`bb489797…`。两处诊断过滤器改为准确的`zorn-metal-probe193`，完整重编33个原生对象、1399项完整链接、136项有效头文件与当前身份检查通过。GPU／任务准入／内存／异步提交／fence／交接／关闭后端与291逐函数／字节核对不变；290签名Metal／Turnip及原生PAC Rust保留。复用291已安装根，本次没有新增根写入；FAT仅内核成员改变，FD、ADT、启动器与菜单保持原字节。

一次无人值守临时启动332.78秒自动回TWRP，串口与相机exit0；Android／17／Data／GPT／根边界及完整BCB／尾部检查通过。严格接收`verified=true`，31个普通帧＋7个整屏截图包、80556字节，已知图像／原生任务／Metal／完整客户端生命周期判定均通过。

实际Metal设备发现、library／pipeline、真实GPU完成、Metal getBytes与独立IOSurface CPU视图一致，CRC为`718ed2ce`。120次已知呈现全部完成，两个附加IOKit共享Query／Close成功，四个已登记客户端64／129／194／259均Close stage16／raw0，进程exit0。相机99秒明确显示物理4×4绿／紫棋盘，整屏串口图像也完整。此结果属于本精确构建，不能给291失败记录追认通过。

完整journal为3192字节／32条，seen＝reserved＝published＝received，缺口／pending为0，真实任务身份与exit0绑定。原生事件dropped为0、CF无后端failure或诊断丢失；旧383字节stderr摘要仍记录13次容量省略，两个并发Query的旧顺序观察拒绝计数仍为2。严格267／268判定使用完整journal和实际客户端登记记录，原有摘要限制不隐藏，不能说所有日志表示都零丢失。

ready记录新增与实际编译根头文件及存储描述一致的地址／页大小检查。离线模板草稿曾误替换版本号所在的LBA数字，已保留草稿并改用数字／哈希边界匹配，在归档／准入／292设备访问之前修正；回归明确拒绝错误LBA、Data边界及CPU页大小。FAT预检也拒绝把未改变ADT列作已改变成员，修正为仅内核成员后重建独立包；失败目录保留。

[292精确实机证据、原始日志、完整生命周期及相机帧](evidence/k80-gpu-v292-known-image-device-2026-11-18.json)保留全部输入和限制。完整普通桌面／应用兼容性、跨任务隔离、长期稳定性、完整FT3683物理行为仍未验收。120次呈现包含显式节流和查询轮询，不能当成桌面FPS。

## 293 固定绘制实测

内核 `4006a884…`，启动包 `19720b1c…`，根镜像 `93347609…`。专用 iOS26 根只有签名探针可执行文件改变，实机增量 33 页／13 组，逐组读回与保护检查均通过。一次无人值守启动在 333.59 秒自动返回 TWRP，相机 100 秒处看到绿紫棋盘。探针完成 16 次 32×32 绘制，每次重新填写 IOSurface，等待完成回调，再核对两处 CPU 读回及 CRC `718ed2ce`。串口收齐 6334 字节 journal，丢失和待发布均为零。120 次已知呈现、四个客户端正常关闭和进程 exit0 均有独立记录。

旧压缩诊断计数器丢失 4 条事件，严格组合验收及性能判定保留失败。原始计时只作定位线索。平均每次完整操作约 36.31 ms，其中提交返回至完成回调约 36.10 ms，区间为 19.47–78.84 ms。该区间包含用户态调度、驱动提交和完成处理。32×32 绘制和主动节流的棋盘呈现无法给出普通桌面 FPS。[精确实机证据](evidence/k80-gpu-v293-fixed-work-device-2026-11-18.json) [独立根安装回执](evidence/k80-gpu-v293-fixed-work-root-installed-2026-11-18.json)。

## 294 固定负载和客户端生命周期通过

内核 `846789a9…`，启动包 `c9c3c995…`，复用实机 293 根 `93347609…`。单次启动在 333.84 秒自动返回核验过的 TWRP，保护区和 BCB 检查通过。16 次固定绘制全部通过回调和双路 CPU 读回检查，CRC 为 `718ed2ce`。串口记录了 120 次已知呈现、四个客户端实际 Close 成功、探针 exit0，6334 字节完整 journal 以及零条压缩原生诊断丢失。另一条摘要通道达到容量上限，仍如实保留 29 条省略。相机第 97 秒显示物理绿紫棋盘。[294 精确实机证据](evidence/k80-gpu-v294-compact-observer-device-2026-11-18.json)。

16 次 32×32 绘制的单任务 CPU 墙钟时间平均 35.87 ms，中位 35.48 ms，范围 22.37–77.48 ms。提交后的完成等待平均 35.69 ms，其中包括调度、原生提交和完成回调交付。该试验给出固定负载延迟，桌面的逐帧和物理刷新节奏仍需同场测量。

## 桌面材质待验证

机主报告 Dock、设置长按菜单、状态栏缺少液态玻璃，观察尚未绑定到精确启动标识。旧 274 的同场对照里，菜单看起来呈浅灰，实际 backboardd 原生完成 fence 在菜单出现前后从 310 推进到 314，同场截图记录到 317。截图背后几乎全黑，无法判定透光或模糊是否正确。290 的 backboardd 实测覆盖锁屏，294 的彩色棋盘覆盖独立探针。下一轮在现有栈的同一桌面场景获取原生客户端、提交、fence、同帧 IOSurface、材质外观及可用 pipeline 证据。外观设置也参与材质判定。[274 同场对照](handoff-2026-11-17-k80-ios26-gpu-v274-context-menu.md) [Apple iOS 26 显示设置](https://support.apple.com/guide/iphone/adjust-iphone-display-and-text-settings-iphd6804774e/26/ios/26) [UniXNU 帧诊断步骤](https://unixnu.com/porting/gpu#find-where-a-slow-frame-goes)。

机主补充了可对照的视觉判据。材质正常时，Dock 后的壁纸被模糊。异常时，Dock 看起来完全透明。现有 274 和 275 相机画面的 Dock 很暗，无法用作确认过的正样本。判断时需要看到 Dock 内外的可辨背景纹理，并记录对应的同帧 fence。继续保留菜单和状态栏作为辅助观察。[274 桌面相机帧](evidence/images/k80-v274-camera-home-screen-2026-11-17.png)。

295 离线恢复现有 GPU 栈的普通 backboardd 策略和旧 274 的有界长按场景，延迟截取右上菜单。296 复用 295 的独立根，把串口截图改为长按前的桌面底部四分之一，保留 104×48 像素、同帧呈现记录与原 CDC 帧预算。等待滑动抬起后五秒再开放取景，长按前关闭。两个版本均完成 1399 输入的内核链接及启动包。296 通过 146 个实际依赖检查、4992 像素的带 CRC 往返验证和 ASan／UBSan、TSan 场景门控测试。专用根的 25 页／14 组增量已在本机全量重放验证。[295 精确候选](../patches/gpu/ios26-ordinary-materials295/source-manifest.json) [296 精确候选](../patches/gpu/ios26-dock-material296/source-manifest.json)。

## 296 普通桌面实测与材质／帧延迟根因定位

先在 TWRP 安装专用 iOS26 根 25 页／14 组增量（`93347609…` → `181e7fc6…`），逐组读回与保护检查通过，随后单次无人值守启动 296（内核 `c34d9751…`、启动包 `6697a85d…`），332.27 秒自动返回核验过的 TWRP，零重试，七组保护采样、GPT 与整页 BCB 检查全部通过。[296 根安装回执](evidence/k80-gpu-v296-dock-root-installed-2026-11-18.json) [296 精确实机证据](evidence/k80-gpu-v296-dock-material-device-2026-11-18.json) [296 Dock 串口裁剪图](evidence/images/k80-v296-serial-dock-ROI-2026-11-18.png)。

串口完整收齐 76055 字节原始帧、8864 字节 `backboardd` journal（零缺口、零挂起）、压缩原生诊断零丢失（31945 条）且后端错误为零。104×48 底部裁剪命中 `present_frame=618`、`surface_id=651`、`producer_fence=completed_fence=access_fence=1209`：Dock 圆角底栏呈均匀深灰 `RGB(46,46,46)`，外部壁纸为纯黑 `RGB(0,0,0)`，按机主判据在纯黑背景下记为 `inconclusive_black_background`（`material_blur_qualified=false`）。旧相机脚本 `SECONDS=340` 叠加 `+faststart` 重写超过 358 秒上限（`camera_exit=124`，缺少 `moov`），已定位并将在下一版改为分段 MP4 与充足收尾超时。

40.02 秒同场桌面窗口（355 次提交，累计 1209 次 `SubmitBatch`）给出精确逐阶段耗时：帧间隔均值 `78.43 ms`（约 `12.75 FPS`），CPU 编码仅 `3.73 ms`（266／357 帧低于 `1 ms`），提交至完成回调 `pg=56.06 ms`（`G commit-to-complete` 均值 `57.92 ms`）。`NativeAdrenoABI` 方法耗时定位到全局串行锁竞争：`m2v-queue-wait` 在 `WaitFence`（1306 次，均值 `8.18 ms`）睡眠等待期间同时持有 `s.appSerial` 与 `s.issuer`，加上 `MiniIOMobileFramebuffer::presenter()` 在整屏 CPU 像素拷贝期间持有 `s.issuer`，导致单次耗时不到 `1 us` 的 `GetStatus` 被阻塞到均值 `21.54 ms`、`BoImport` 均值 `29.53 ms`、`BoFree` `10.53 ms`、`SubmitBatch` `10.25 ms`、`BoMap` `10.17 ms`。

源码对照 `hakios` iOS 26（`dada-ios.sh`、`fbfetch.ll`、`nativemetal-dada.patch`）同时定位到液态玻璃缺失根因：iOS 26 CoreAnimation 默认启用内联 SDF（`fixed_frag_*` 依赖 `fc_framebuffer_fetch` 读取 `[[color(n)]]`）、tile shader 与 filter merging；当前 `metal2vulkan`／Turnip 不支持普通 pass 的 `[[color(n)]]` 帧缓冲读取，导致液态玻璃与长按菜单退化为不透明纯色／纯黑。`backboardd` 缺少 `CA_DISABLE_INLINE_SDFS=1`、`CA_DISABLE_FILTER_MERGING=1`、`CA_DISABLE_TILE_SHADERS=1` 与 `CA_DISABLE_FRAMEBUFFER_COMPRESSION=1`，且 `boot_args` 仍保留历史 `sb_wallpaper=0` 与被动 PosterBoard 钩子导致桌面背景全黑。

## 297 液态玻璃材质与分段 MP4 相机实机验证通过

先在核验过的 TWRP 安装专用 iOS26 根 21 页／11 组增量（`181e7fc6…` → `951d3de6…`），仅在 `com.apple.backboardd.plist` 增加 `CA_DISABLE_INLINE_SDFS=1`、`CA_DISABLE_FILTER_MERGING=1`、`CA_DISABLE_TILE_SHADERS=1`、`CA_DISABLE_FRAMEBUFFER_COMPRESSION=1`，逐组读回与保护检查通过。随后单次无人值守启动 297（内核 `a2a68439…`、启动包 `e9427877…`、标签 `9c37385967304b6fae92874309c81104`），332.90 秒自动返回核验过的 TWRP，零重试，七组保护采样、GPT 与整页 BCB 全部通过；分段 MP4 相机录制（320 秒／`32,131,051` 字节）以 `camera_exit=0` 正常收尾。[297 根安装回执](evidence/k80-gpu-v297-glass-root-installed-2026-11-18.json) [297 精确实机证据](evidence/k80-gpu-v297-glass-material-device-2026-11-18.json)。

`backboardd` 激活完整离屏模糊路径：Vulkan 管线从 28 个增至 61 个（`tile 0`），单帧从 3–5 个 pass 增至 25 个 render pass（`rp25 dr59..64 kpx23965`），40 秒窗口执行 368 次离屏 2D 模糊／拷贝（`GMb s2d 368/368/368/0`），零后端错误、零日志缺口。串口 `104×48` 顶部半屏裁剪（`present_frame=391`、`surface_id=424`、`fence=910`、435 种颜色）与 175s／220s 相机帧共同验证液态玻璃模糊透色：设置长按菜单横跨左侧浅紫小组件（`RGB(206,205,210)`）与右侧暗底，菜单在小组件上方呈磨砂透白 `RGB(210,209,212)`，跨越底层小组件右边界 `x=42..50` 呈平滑高斯模糊衰减至右侧暗底上方的 `RGB(177,177,180)`，底部圆角磨砂 Dock 与 `Search` 胶囊同样清晰可见。主机初始 `cdc-capture.json` 因将物理面板尺寸与逻辑表面尺寸比较报错，原始回执保留，修正解码器后全部 7 分块与两份 287 计时报告完整通过。[297 串口裁剪图](evidence/images/k80-v297-serial-menu-ROI-2026-11-18.png) [297 相机 Dock 帧](evidence/images/k80-v297-camera-dock-175s-2026-11-18.png) [297 相机菜单帧](evidence/images/k80-v297-camera-menu-220s-2026-11-18.png)。

在每帧 25 个 pass 的完整材质负载下，40.00 秒窗口完成 188 帧：CPU 编码均值仅 `6.58 ms`（145／188 帧低于 `4 ms`），帧间隔均值 `105.04 ms`（`G commit-to-complete` `103.34 ms`），`< 1 us` 的 `GetStatus` 被阻塞至均值 `22.88 ms`、`BoImport` `42.55 ms`、`WaitFence` `12.33 ms`。

## 298 呈现线程释放 `s.issuer` 实机验证通过（吞吐量 +64.5%，延迟 -42.4%）

复用已安装的 297 根 `951d3de6…`，在 `MiniIOMobileFramebuffer::presenter()` 中通过 `ZornPresenterScope298.h` 于完成表面缓存取得与同帧完成账本／表面 fence 快照后立即释放 `s.issuer` 与 `presentationRegistry`，再执行 `~16.6 ms` 整屏 `show()` 像素拷贝（早期无 GPU 纯 CPU 帧仍保留原租约保护）。通过 ASan／UBSan 与 TSan 256 次并发锁无竞争测试后，单次启动内核 `ca5aca6a…`、启动包 `cd7872c5…`（标签 `5968f06ef28b4046b0ba8c9e4c49056c`），`333.41s` 自动返回核验过的 TWRP，`receiver_exit=0`、`camera_exit=0`、`verified=true`，七组保护采样、GPT 与整页 BCB 全部通过。[298 精确实机证据](evidence/k80-gpu-v298-presenter-unlock-device-2026-11-18.json) [298 串口裁剪图](evidence/images/k80-v298-serial-menu-ROI-2026-11-18.png)。

同场 40.005 秒液态玻璃窗口对比 297：完成帧数从 `186` 帧跃升至 **`306` 帧（`+64.5%`）**，提交至完成均值从 `103.34 ms` 降至 **`59.51 ms`（`-42.4%`）**，`< 64 ms` 帧占比从 `27.7%` 升至 **`78.6%`**（静止桌面帧 `22.44–25.22 ms`）；`GetStatus` 均值从 `22.88 ms` 降至 **`7.35 ms`（`-15.53 ms`）**，`BoImport` 从 `42.55 ms` 降至 **`27.68 ms`（`-14.86 ms`）**，液态玻璃菜单模糊保持一致（`present_frame=334`、`fence=943`、435 色）。剩余主导瓶颈明确为 `WaitFence`（`1,030` 次，均值 `10.99 ms`）睡眠等待期间仍持有 `p->serial_`、`s.appSerial` 与 `s.issuer`。

## 299–308：WaitFence 解锁、CPU 方法免排空、活跃 SMMU 上下文保持、578 MHz 标称频点与完整生命周期真机验收

- **299（`WaitFence` IRQ 睡眠解锁实机验证通过）**：经授权停止外部 `tcp:5037` ADB 后复用已安装 297 根 `951d3de6…`，单次启动内核 `7176814b…`、启动包 `eb312f67…`（标签 `db9363f8a0ac496c807f98f3282cf597`），`333.65s` 自动返回核验过的 TWRP（`receiver_exit=0`、`camera_exit=0`）。菜单截图时刻跃升至 `present_frame=587`（较 298 `+75.7%`），`m2v-queue-wait` CPU 降低 `-55.8%`（`7,867 -> 3,477 ms`），`BoAlloc` 降低 `-43.9%`（`12.66 -> 7.10 ms`）。[299 精确实机证据](evidence/k80-gpu-v299-waitfence-unlock-device-2026-11-18.json) [299 串口裁剪图](evidence/images/k80-v299-serial-menu-ROI-2026-11-18.png)。
- **301 + 302（`IOKit` 根幻影 busy 归零 ＋ 12 项纯 CPU 方法免 `RestoreKernel` 排空实机验证通过）**：定位 `!NO_KEXTD` 下 `StartIOKitMatching()` 遗留 `gIOServiceRoot` busy 计数导致 `Preferences.app` 在 `__wait_for_IOKit_to_quiesce` 挂起 300s 的根因（`ZornIokitDaemonQuiet301.h`），并通过 `ZornCpuViewContextFree302.h` 豁免 `BoImport`／`BoAlloc`／`Metadata`／`Queue` 等 12 项纯 CPU 方法免于触发 `RestoreKernel -> quiesceKernelIo()`。单次启动内核 `07d5030f…`、启动包 `f3d836a3…`（标签 `1881eb67fb094ba09abb05ad8f7cbdeb`），`334.06s` 自动返回 TWRP，`BoImport` 均值从 `42.55 ms`（297）／`23.12 ms`（299）骤降至 **`0.498 ms`（`-98.8%`）**，`FA3 res` 从 `12.26 ms` 降至 **`1.57 ms`（`-87.2%`）**。[301 离线证据](evidence/k80-gpu-v301-iokit-quiet-offline-2026-11-18.json) [302 精确实机证据](evidence/k80-gpu-v302-cpuview-ctxfree-device-2026-11-18.json) [302 串口裁剪图](evidence/images/k80-v302-serial-menu-ROI-2026-11-18.png)。
- **303（同进程健康活跃 SMMU 上下文保持 ＋ `BoMap`／`BoFree` 锁外 IRQ 等待实机验证通过，吞吐量跃升 `4.24×`！）**：消除同活跃客户端在 `BoMap`／`BoFree`／`WaitFence` 之间反复 `RestoreKernel <-> Select -> p.vm_.auditLive()` 遍历 400+ MiB 稀疏页表与重置 CP 上下文（每帧节省 ~40 ms CPU 时间，保留跨进程切换、`PrepareTables`、`Close`、`OobRelease` 与故障保留路径不变）。单次启动内核 `7df77ba7…`、启动包 `0b4b696e…`（标签 `2f4ee01ef2c24506b38fd065d47bb57d`），`334.19s` 自动返回 TWRP：40.005s 液态玻璃完成帧达 **`788` 帧（较 297 `4.24×`）**，`commit-to-complete` 均值降至 **`33.87 ms`**，`789/790 (99.87%)` 帧 `< 64 ms`，`BoFree` 降至 `1.14 ms`（`-90.5%`）、`SubmitBatch` 降至 `3.13 ms`（`-73.3%`）。[303 精确实机证据](evidence/k80-gpu-v303-context-retain-device-2026-11-18.json) [303 串口裁剪图](evidence/images/k80-v303-serial-menu-ROI-2026-11-18.png)。
- **305（K80 原厂 SKU bin 3 标称频点 `578 MHz`／`0x80 NOM` ＋ `bus=5` `8.17 Gbps` DDR 投票实机验证通过，吞吐量跃升 `5.84×`！）**：替代原 `231 MHz` MIN_SVS 怠速启动档（`ZornNominalOpp305.h`，源自 `ZornGen791StockVoteData.inc` `stock_0_power_3[6]` 与 `stock_0_ddr[5]`）。单次启动内核 `b1ee73d6…`、启动包 `eba8bd8b…`（标签 `78871e9ec441484592f84b6bacab8dfa`），`332.19s` 自动返回 TWRP：40.006s 完成帧跃升至 **`1,086` 帧（较 297 `5.84×`）**，菜单捕获 `present_frame=1,856`，离屏 2D 模糊 `2,150` 次，`commit-to-complete` 均值降至 **`19.63 ms`（较 297 `-81.0%`，最大 `54 ms`）**，**`1,085/1,088 (99.72%)` 帧 `< 32 ms`**、**`1,088/1,088 (100%)` 帧 `< 64 ms`**，`FA1` 间隔 `12.45 ms`，对应该阶段 `80.32` 次/秒。实际完成吞吐量约 `27.1` 帧/秒，液态玻璃保持 435 色。[305 精确实机证据](evidence/k80-gpu-v305-nominal-opp-device-2026-11-18.json) [305 串口裁剪图](evidence/images/k80-v305-serial-menu-ROI-2026-11-18.png)。
- **306 + 307（完整 `v298..v305` 后端上的已知图像 `CRC718ed2ce` ＋ 120 次棋盘呈现 ＋ 四客户端 `Close` 真机验收通过，命令提速 `15.48×`，并恢复液态玻璃桌面根！）**：经 TWRP 40 页／19 组根增量切换至探针根 `93347609…` 后，单次启动 `v306`（内核 `5072b9e4…`、启动包 `089286af…`、标签 `ba667cc788eb47d8adc50c3be81839c2`），`332.35s` 自动返回 TWRP：固件认证、GMU/HFI、初始已知图像 `HGKI`、16 次 `32×32` Metal `CRC718ed2ce` 绘制及 IOSurface 双重读回（均值由 `v294` 的 `35.87 ms` 骤降至 **`2.32 ms`，提速 `15.48×`！**）、`120/120` 次绿紫棋盘呈现（串口截图与 98s 相机物理屏幕双验证）及 **`4/4` 原生客户端 `Close` 与 `exit 0`** 全部零错通过；随后在 TWRP 执行 307 反向 40 页／19 组根增量将手机恢复至已验证的液态玻璃桌面根 `951d3de6…`（同时保留 300／304 历史离线候选与零合成输入的 308 人工物理触控候选包）。[306 根安装回执](evidence/k80-gpu-v306-known-root-installed-2026-11-18.json) [306 精确实机证据](evidence/k80-gpu-v306-known-lifecycle-device-2026-11-18.json) [306 串口棋盘图](evidence/images/k80-v306-serial-checkerboard-2026-11-18.png) [306 相机棋盘帧](evidence/images/k80-v306-camera-checkerboard-98s-2026-11-18.png) [307 根恢复回执](evidence/k80-gpu-v307-glass-root-restored-2026-11-18.json)。

## 309–312 设置应用与回收状态

309 确认设置首页呈现并自动返回 TWRP，滑动后仍停在 frame 2056／fence 2737。310 完整构建并通过父 Hand 集合坐标、触点身份和抬起回归，固定工具在接触设备前拒绝了 SDK 35 服务。312 以相同修复做了独立单次启动。设置列表仍未滚动，串口收齐 7 片截图，并记录 frame 2118／fence 2801。600 秒内未核验 Recovery，主机日志记录 5037 占用目标 USB ADB 接口。设备操作停在该状态，后续的 FT3683 物理验收和动态调频暂停在设备侧。[续接与精确回执](handoff-2026-11-18-k80-ios26-gpu-v296-dock-material.md)


## 人工复验与面板撕裂

原样 v309 单次启动后，机主确认解锁、桌面滑动、Dock 模糊和液态玻璃，观察到低帧率及画面撕裂。设置列表仍不能滚动，串口在脚本滑动前后保留同一帧和完成 fence。自动回 TWRP 用时 332.503 秒，保护区读回与 BCB 检查通过。v317 已构建，可在 FT3683 及 GPU 状态采样的同时对照已存在的显示阶段耗时。该构建保持离线。面板相位和撕裂根因仍待测量。[v309 人工复验](evidence/k80-gpu-v309-manual-repeat-device-2026-11-18.json) [v317 精确构建](evidence/k80-gpu-v317-present-cost-offline-2026-11-18.json)

v305 人工复验中，首次打开设置缺图标且无法滚动，关闭后第二次打开时图标恢复且可以滚动。机主认为 v305 和此前 v309 的体感帧率相近，均偏低，较几天前略好。此前的 v309 只观察了首次打开。两次打开的手动事件缺少同步标记，现有串口截图无法为这个差异归因。[v305 人工观察](evidence/k80-gpu-v305-manual-repeat-device-2026-11-18.json)

再次启动 v309 后，机主也看到首次打开设置缺图标，第二次打开图标恢复且可以滚动。手机在 332.265 秒自动回 TWRP。该轮串口的自动长按分支返回 `NoClient`，后续脚本动作均跳过，设置重开结果来自机主的观察。已按生产端的未尝试抬起标记修正解析器，保留原始拒绝、串口和复验记录。[v309 第二次打开设置](evidence/k80-gpu-v309-settings-second-open-device-2026-11-18.json)

v318 把已核验的 K80 DPU INTF1 原始计数接入物理观察串口帧，读取由已观察到的 GOP 呈现和实际显示电源、时钟状态约束。编译、完整链接、打包和主机回归通过。真机仍需确认计数器是否可读并推进，以及采样期间的面板扫描模式。[v318 精确构建](evidence/k80-gpu-v318-panel-timing-offline-2026-11-18.json)

v318 单次无人值守启动在 332.680 秒自动返回 TWRP。GCC 显示 AHB 的 `CLK_OFF` 在 9 次采样中均置位，DPU 计数器读取按保护条件跳过。期间 GPU 完成 fence `1624→4003`，CPU 完成 `2,379` 次活动 GOP 缓冲复制，约 `29.74` 次/秒。CPU `show()` 每次复制平均 `20.47ms`。FT3683 持续产生空报告，完整实体手势和面板刷新率仍待验证。[v318 真机采样](evidence/k80-gpu-v318-panel-timing-device-2026-11-18.json)

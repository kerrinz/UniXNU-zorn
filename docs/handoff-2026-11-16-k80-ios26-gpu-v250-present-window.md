# K80 iOS26 v250：120帧呈现的有界时间预算

v249实机摄像头已确认预期绿／品红4×4棋盘，Metal探针像素CRC718ed2ce、badffffffff；但120帧循环仅提交72、确认71，公开时基625/12对应8.026576145秒，触及8秒截止，实际退出10。此失败与物理图像证据一并保留，不据此认定GPU性能或驱动崩溃。一次启动334.595秒自动回TWRP。

v250保留120帧、每帧200次轮询上限、精确frame/SID/schema2、已完成access fence、acquire/copy及close检查，仅将调用之间截止从8秒改为20秒。源码仍名presentKnown249、ZORN249PRESENT协议不变，继续复用typed249接收器；没有新API或成功条件放宽。此截止不能打断阻塞的原生调用，原队列超时与独立300秒WDT仍必需。正常系统仍使用CPU presenter；该探针结果不等于GPU桌面。

## 精确离线候选

- 程序／boot ID：`9735df98f85745cd9f43a43290398656`。
- kernel：`52a7b61c88c7b850ec58f37914c6cc39f57c22706991bc276c3b1083d5aff0be`。
- boot：`6ba14e9d32ff6b75fab3548489f610cd0d8a145f68ad64f694b9a546ff1a7ed2`。
- root：`40338c39e91e4932c63271cea073c1eba208080d3356de20a6a7c3593629bb0d`，32GiB，未安装。最新已确认手机根仍为v249的1a8ea4a1。

1398个精确输入核验，30个对象重编，完整链接0undefined；77项实际依赖绑定及编译器宏确认CPU16KiB。GPU4KiB与磁盘4KiB单独核对。原GPU、SMMU、资源所有权、呈现队列、Metal shader／frontend／Turnip后端与249源码相同。真实探针按arm64e-apple-ios26.0编译，entitlement集合保持，签名／文件系统验证通过。实际函数36项ASan／UBSan控制、更新程序身份的观察器／发送器／typed parser控制通过；主机边界替身只验证软件逻辑。

新根只替换签名探针，相对实际249父根58个4KiB页、7组；完整本地增量重放SHA等于4033。从Data末端重新按1MiB对齐计算放置，Data间隔782336字节、根后保留8588886016字节，无布局变化。末预映像不匹配先拒绝、首组读回失败停止控制通过。初次布局报告错误引用248父头文件，原报告保留，现另核验249真实父头／根SHA及全部数字几何字段并更正归属；没有修改镜像或冒充再次重放。

FD、启动参数保持；FAT仅替换kernel和root哈希ADT，全部成员读回及payload重组通过，原loader的文件元数据消费检查通过。创建记录显式写入当前application_probe_run_id，避免249旧字段继承问题；根部署／复用字段明确为未安装，249收据仅证明父根。没有反汇编、符号化或逆向。

[离线证据](evidence/k80-gpu-v250-present-window-offline-2026-11-16.json)、[五份最小补丁及来源](../patches/diagnostics/ios26-present-window250/source-manifest.json)、[实际函数控制](../scripts/check-ios26-present-burst.py)。所有补丁零fuzz重放等于冻结源码。构建目录：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656。源码目录：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656。

## 下一阶段

准备独立250根增量审核：合并实际249保留页及写后读回，再核验全部当前预映像、GPT／Data／17／日志边界和完整BCB。只有独立安装成功、停留已核验Recovery，才准备新boot scope／ready／claim、receiver-first、600秒Recovery期限及有界摄像头观察。离线候选没有设备ready／claim，不把本地重放当作设备安装。

本次硬件仍须确认120帧全部完成、真实fence／同SID记录、正常退出与资源生命周期；物理图像需与新构建重新关联。普通系统GPU客户端／完整桌面及FT3683点按、滑动、抬起、身份和边缘验收仍未完成。完整目标保持active；不新增commit或push。


## 独立安装与一次实机结果

v250独立根安装核验7300个历史实际保留页／156组、全部58页新预映像及保护后，7组58页写入／读回，聚合SHA dc58e53affc16cfa25b370a3f34b8e67ff0d9db5bc83ea72d5fd943f19767a23 与本地重放一致。完整BCB及保护样本不变，安装后停留已核验TWRP；49项安装器、6项准入拒绝控制通过。新根只在本次单独安装后成为当前4033输入，不据离线创建记录声称早已安装；不是手机全根32GiB读回。

154项启动输入拒绝及入口／摄像头检查后，仅一次临时启动。332.473304秒自动回TWRP；runner与receiver均0，39帧59474字节，无解析错误或部分终止包。七组启动保护样本逐字节相同，BCB准备前864字节、4096字节读回和尾部保持通过。没有重试、bootstrap、刷机恢复或Android／17／Data／GPT／slot写入。当前活动scope已清空，stop_device_operations=false；250claim消费。

完整5572字节／55写入记录、unique／PID10，seen／reserved／published／接收长度和CRC一致，gaps／pending0，实际task-detached退出waitstatus0。Metal探针phase11／flags1023／status4／code0，CRC718ed2ce、badffffffff；两个原生session关闭均返回0。旧紧凑摘要app.complete仍false、raw_stderr_dropped37保留；基于完整journal的lossless_application_complete248、known_burst_complete249与application249_with_recovery_complete均true。名字中的248／249是沿用未变协议，并非把旧实测转移为250结果；退出marker不扩大为完整process reap或任意DMA停止证明。

实际提交120／确认120、first757／last1281、SID35、displayclose0，公开时基625／12、ticks287553665，对应14.976753385秒。末known记录frame1281／SID35／access fence4、acquire／copy完成，copy1280→1281；20秒预算足以完成本次要求，未降低120帧或查询／关闭条件。该耗时包含调度和呈现查询，不作为GPU帧率测量。普通系统末SID1的access fence仍0，不能把普通锁屏归属为GPU渲染。

240秒无音频原录像10028561字节，SHA e91715b8bd288dc1a891f0f96bb6e6dc971f3943e00decd05acb77e1d93cca58。人工逐帧检查140.993033、133.986066、131.518066秒候选，手机上清楚显示预期绿色／品红4×4棋盘；180／225秒为锁屏。候选排名仅帮助选帧，物理结论来自实际图像检查，原标量parser physical flag仍false。它证明此有界Metal结果经既有呈现链输出，不等于GPU直接scanout、全桌面、颜色校准或长期稳定性。

[本次精确安装、日志、摄像头和Recovery证据](evidence/k80-gpu-v250-present-window-observed-2026-11-16.json)。上方离线“未安装”记录保留创建时序；以本节独立收据为当前状态。下一步继续普通系统Metal客户端和呈现接入、FT3683完整手势及更广生命周期验收，完整目标仍active。没有新增commit或push。


## 普通系统客户端的下一项源码接入

当前根的NativeAdrenoMetal.clients仍只有zorn-metal-probe193；ZornGen7AppIoService26::newUserClient以reserved_保证一个原生会话，MiniIOMobileFramebuffer的software_accelerator=2继续publishAccelerator(...,false)。这些是当前源码／配置明确保留的边界，不能把探针通过当作全桌面成功，也不能仅删掉独占检查或放宽clients文件。下一候选须先按实际共享后端的任务／namespace／关闭生命周期接入普通系统客户端并保留正常IOKit准入，再验证其渲染表面。现有frontend226源码已经在presentDrawable三种方法中等待成功command completion才调用drawable呈现，应复用实际实现；文件顶部“drawables未实现”的旧注释不足以判断功能缺失。原始日志／二进制不进行反汇编或逆向。

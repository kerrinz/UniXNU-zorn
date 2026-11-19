# K80 iOS26：280 上游图形栈离线候选

279的新Metal frontend／Rust bridge／metal2vulkan runtime已与新版公共Turnip组合，形成独立签名bundle、32GiB根镜像、完整K80内核及启动包。**未安装、未启动，无新FPS或硬件验收结果**。[精确证据](evidence/k80-gpu-v280-upstream-stack-offline-2026-11-17.json)、[补丁与输入](../patches/gpu/ios26-upstream-turnip280/source-manifest.json)。实际硬件基线仍为277；设置列表不能滚动继续独立待修。

## 复用的源码

官方UniXNU `630b85a307f19c8d8a4699d5bfc12f6796b874aa` 的compiler输入仍选Mesa `85fda3b36405bcaea8bffc64aa4f2651dc90770d`，不是另一个历史translator参考钉点。现有本地归档的全部Git blob经缓存的完整Git树核对；仅在新副本修正31个CSV的换行以恢复原Git字节。历史归档、源码和构建保持。

按官方顺序原样应用24个Mesa补丁，再应用K80适配补丁。独立重放重新构成实际选中源码，零fuzz核验通过。保留上游的进程级IOVA分配器、BO缓存命中时减少回收锁竞争、BO释放前清零稀疏槽、pipeline共享及提交时尽量沿command buffer边界切分等实现，没有重写成诊断后端。

Metal仍为279的AdrenoMetal `8c7f9502de593c04a1003690f4a9441fe88551e8`，translator为development `46e7cc96a284150bdf19b4a6a7890b0a8bc0ef71` 加官方0063补丁、iOS公开Mach及有界no-copy适配。[279来源及实际编译](handoff-2026-11-17-k80-ios26-gpu-v279-upstream-runtime.md)。这里复用其完整配套编译产物，普通重新签名封装后更新嵌套Turnip，不混入17对象。

## K80接口与故障契约

复用实际K80 registry-ID服务发现与ABI-v1传输函数；Query、16-IB旧Submit和128-IB SubmitBatch保持真实布局。原内核头、279编译门禁实际进入新Turnip对象依赖；新v2头不适用。selector17仍是SubmitBatch，flag2仍表示批量提交，不当作OwnedCoherent。CPU映射保持现有WriteCombine，priority／note明确不支持且不发送v2方法。现有用户客户端、安全检查、GMU/HFI、direct-ring、固件、时钟、SMMU和K80板级参数保持。

新版“故障后保留设备继续使用”依赖上游内核已经复位并重放其他任务。K80尚无这项契约的验收，因此280在观察到fault后仍标记device lost，不假设GPU已经复位或DMA已停止。正常完成按真实回收路径释放，失败不确定状态保留对应资源。不能把上游公共优化当作K80故障恢复许可。

上游transient／memoryless附件可能改用GMEM，即使原TU_DEBUG=sysmem也有此例外；lazy BO与提交切分实现已包含在候选中。它们仍需Gen7.9.1、实际GMEM资源和对应图像／fence实测。没有改动boot args加入tum=模式试验，也未宣布低帧率已解决。实际呈现仍走原CPU-copy presenter。

## 当前精确产物

- tag：`434fe1f2f3be4ee89e7166d9b61cf1d9`。
- Turnip：`6a72c7da534a1d7df2c8beac7724cb4d20f9776d45eb946649233859747f8dde`。
- 根镜像：`d9856b4342a307d915f43d8cd7d9540b8a2d3933f07dfd46750cfe5a32c0c622`，34359738368字节。
- 完整内核：`6d129fe32eba2ef16342f18061faa170f8614289143068f2ce9cd74c417e3b9f`。
- 启动包：`29b7bb7d5610422c5cc336938d2425e307ed81ea40137a64da31867cc34b8895`。

本地独立归档为`out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v280-upstream-turnip-434fe1f2f3be4ee89e7166d9b61cf1d9`。完整文件清单、构建命令、源码／依赖和检查结果保存在该目录；公开摘要不意味着本地产物可从Git下载。

## 已完成的离线检查

Turnip完整iOS26 arm64e交叉编译和正常链接／签名通过。保留上游WSI weak入口的dynamic_lookup链接策略，不能把它称为所有动态导入已在真机解析。新增唯一undefined导入`sysctlbyname`来自可选bootargs模式读取；实际iOS SDK公开原型与libSystem导出均存在，失败时不选择override。

[主机回归工具](../scripts/check-ios26-turnip280.py)编译实际选中的dw_call、submit、priority／note及BO-finish函数体，ASan／UBSan检查通过：直接／tunnel传输的16／128-IB长度、越界／零长度拒绝、Busy与失败传递、不调用v2方法、释放时稀疏槽立即重用不会被后续清零、回收记录扩容失败仍报错。IOKit、fence wait、reap和分配失败是明确的测试边界，不执行GPU或shader，不证明硬件完成或缓存可见性。

独立克隆已安装271对应的只读本地根，只改Metal bundle内可执行文件、嵌套driver和CodeResources；原根`c60b198d…`的全镜像哈希及元数据复查不变。所有监测文件、LaunchDaemons、禁用探针、backboardd策略和既有UID/GID／mode／inode保持；签名及HFS卷检查通过。新镜像的主／备用HFS几何、实际大小与分区地址算术重新核对：Data之后留782336字节，根之后到unixnu末尾留8588886016字节；Android／17／Data／GPT无布局变化。这是离线边界核验，不是手机前像或安装审批。

打包前检查发现冻结平台头仍为271根摘要，已替换为实际280摘要，并再次重编全部33个native替换对象、完整链接1399输入，零undefined；143项关键头依赖和实际16KiB CPU页宏检查通过。前一份未绑定新根的内核及其输入保留在before-root280-binding，不能用作本次产物。ADT只变更chosen的root-image-sha256，其余字节复原对照一致。FAT五成员读回、原FD／loader／manager、BootShim／300秒WDT标记、1022字节bootargs、完整payload和既有源码构建的loader元数据消费检查通过。

初始配置缺少实际glslang路径、Meson源内绝对include路径、生成的Python缓存／Finder元数据导致源码门禁拒绝、主机fixture字段写错，以及外层重签名后的整文件哈希比较不适用等失败均保留。最终配方使用明确的native／cross工具链、相对ABI include和禁止Python字节码生成；新源码锁为只读，产物源指纹核验通过。外层签名会正常改变plugin签名字节，源码／链接输入继承关系单独记录，没有据此修改指令。

全程仅正常开源源码编译、链接、签名、undefined-only导入检查、文件头／版本／文件系统格式检查；没有反汇编、指令重写、地址符号化或Apple shader二进制分析。

## 尚待完成

280根增量审核现已形成：11878个4KiB页／48652288字节，按既有65页上限分为220组；另保留实际271及历史安装已读回的7441页／170组。全镜像比对与独立本地重放均为d9856b43…，现有apply_delta算法和Recovery传输适配器原样复用；最后前像错误时零写入，首次读回错误时停止后续组，实际传输适配器的完整本地fixture路径也通过。明确fixture边界，不把主机结果当作Recovery或手机写入证据。

固定安装入口`--ios26-upstream280-root-delta <exact-review> --check`已通过。审核SHA为`6629293a398d57e563d2fffd393b25c9fec3e3d3ebbd6cadc485c654910124cd`，本地独立目录为`k80-upstream280-root-delta-review-434fe1f2`。错误页序／范围、payload、额外根文件、ABI2、旧native身份、未完成父安装及错误根头均被实际计划拒绝。维护入口还拒绝关闭的admission及多个安装flag；设备状态文件原字节保持，没有创建admission／claim。

安装入口原顺序在创建claim后才检查既有ADB监听；现把纯主机TCP检查移到claim之前，监听缺失不消耗一次性安装资格或改变设备状态，仍不启动服务器或发送ADB请求。实际run分支的缺监听回归通过。根安装仍需fresh Recovery及全部前像／保护检查，600秒内零重试、不自动启动；部分或未知写入须停止设备操作、保留Recovery。此处尚未安装。

278原固定入口的拒绝归档不覆盖。本轮仅读取本机5039端口监听状态，未报告现有监听；没有ADB／USB／手机命令、bootstrap或重试，也没有新的Recovery观察。280的系统启动入口、fresh scope／ready／claim和实际新根安装仍待完成，当前无启动资格。

继续准备与新栈匹配的有界已知图像验证及系统启动入口，保留精确安装审核／前像；只有既有连接和Recovery条件满足后才进入受保护验证。必须保留300秒独立WDT、600秒核验Recovery返回及失败停止条件。新栈的固件认证／GMU/HFI、有界任务／fence／CPU结果、已知图像、Metal与呈现、生命周期及FT3683仍需对应精确构建的实机证据。帧率瓶颈还没有测量，性能改善未成立。仅暂存，本轮不新增commit／push。

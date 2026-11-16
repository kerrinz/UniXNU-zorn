# K80 iOS26 v246：IOSurface backing关联与真实退休生命周期

上一轮245实机观察属于实际进展：Metal像素校验、会话关闭、完成lease下的像素拷贝及332.815s自动Recovery有证据，但surface由哪次GPU访问尚未关联。246最初完成离线源码接入和完整链接；随后已补齐独立启动包/schema2串口采集并完成一次有界实机试验，332.535秒自动回TWRP。没有重试、commit或push。目标保持active，完整GPU/Metal/显示/FT3683验收没有完成。

## 实现和语义

新公共ZornSurfaceBacking246按完整物理页段元数据比较backing，不假设CPU4KiB页或GPU页大小，也不读取像素或设备寄存器。两个描述符可以采用不同的连续段划分；比较必须覆盖全部等长范围。无效、溢出、预算耗尽、锁忙及多个surface共用同一backing均不产生唯一关联。一次扫描最多遍历原16384槽的surface表，物理比较预算32768；预算不是硬件成功条件，耗尽保持未知。回调上下文仅在同步比较期间借用，不存储在全局或对象中。

MiniIOSurface复用现有gSurfaceLock/table及surfaceHold/Drop。内部surface的像素描述符从实际PAGE_SIZE后的部分开始；wrapped surface沿用实际client描述符。只接受精确长度且所有段匹配的唯一surface，返回真正held对象。整个实现不改变MiniIOSurface类布局或用户态IOSurface ABI，也不增加IPC操作。使用try-lock查询/完成记录；锁忙意味着未知，不伪造成功。

DirectVM只在实际map事务成功后保存关联的held surface。失败、poison或DMA未知时沿用原Mapping保留；只有真实unmap完成、retireAfterQuiescence返回成功后才drop，再清空Mapping。映射消失后旧surface仍可由合法客户端持有；最后原surfaceUnhold删除SID时清零新fence元数据，避免SID复用污染。现有VM owner大小/对齐不变，私有堆Mapping从56变为64字节；实际IONewData/IODeleteData共用新头，受影响对象已重编。

DirectSubmit只在实际job完成后的release路径调用：IB引用退休、全部import cache acquire、namespace retirement均成功后，标记关联且可写的surface的完成fence。wait及retireCompleted调用链仍保留真实NativeRing完成条件，未增加成功回调或跳过等待。IB列表不区分读/写，namespace覆盖所有映射，因此该标记表示“backing在已完成的GPU可访问命名空间中”，不证明GPU写入了该surface。只适用于当前固定单direct-ring生命周期，不宣称跨GPU/复位epoch通用。

framebuffer仍沿用原lease/acquire/show顺序，输出schema2，把原保留字变为该SID的已完成GPU-access fence。新parser保持原字段校验，并拒绝未来fence、错误schema、CPU lease带GPU访问fence等不一致组合；始终不推断GPU像素写入或物理scanout。245receiver不能读取该schema，禁止直接借用245工具启动246。

## 实际输入修正

初始完整链接虽通过，但追加的源码字节核对发现MiniIOSurface原生通用配方与245实际所选对象不同。不是硬件失败。已沿实际对象SHA定位到cpu-posterboard-passive26的MiniIOSurface.cpo-command.json和VFS选中的native/MiniIOSurface.cpp；用该原配方重建与245实际6cebd072…对象逐字节一致。随后将关联部分patch应用到这份真正源文件，保留原日志/客户端行为，并重编全部29项、重新完整链接。旧候选、对象、源及失败证据保留在revision-before-selected-surface-source，不用旧版通过替代最终版。

新增VirtualVm头变化还明确把原DirectClient使用的fence-width路径纳入VFS；所有实际相关头依赖经外部映射后指向新相同定义，防止混用旧Routing/Mapping声明。最终67项头依赖与1398个实际输入SHA通过检查。

## 精确路径与状态

B246：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v246-surface-backing-ff97459cd92747f1bb1f1cd163e2a6b0`

S246：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v246-surface-backing-ff97459cd92747f1bb1f1cd163e2a6b0`

最终kernel SHA：`13af1f1287b389133d9905379c6ffa99e2de59bbe997fc1be00c42993cad382e`，1398输入，29重编/1369保留，0undefined。root仍193e5f01。此为最初离线检查点：当时没有246完整启动包、新receiver/runner或准入。现已由下方单次实机结果替代，不再是待启动状态。最初stage246.py使用较早Mini源，最终必须结合rebase246-surface.py、source-manifest最终SHA及实际build配方；脚本不是可覆盖历史目录的幂等重建入口。

原245 scope已消费，不重试。仅92988a43/zorn/slotA，从固定工具核验Recovery开始，300秒WDT、600秒有界返回、七组保护样本和完整BCB/tail保持。不能回Recovery时立即停止设备操作。Android系统/用户数据、17系统/Data和历史产物保留。未新增根镜像或存储写入。禁止反汇编/逆向；本轮只读源码、编译器类型元数据、完整文件SHA和测试结果。

## 检查与复用

- surface-backing-host：从最终实际Mini源提取helper，4KiB/16KiB CPU几何下ASan/UBSan通过；完整段、wrapped、歧义、后半段不匹配、忙锁、预算、溢出和完成fence检查。
- surface-actual-drop-host：仓库回归脚本再次提取真实surfaceUnhold/Drop；验证VM额外hold使原owner释放后仍存活，最终drop执行删除/清fence，SID复用不继承旧值。同SID不同活对象不能更新完成记录。锁/描述符仍是host stub，不是硬件。
- surface-lifetime-host：提取真实DirectSubmit::release和VM note方法，逐个退休/cache/namespace失败均不发布surface fence且保留job；只标记可写活映射，zero/poison/unattached不标记。真实map后关联、unmap退休成功后drop的源顺序另检查。
- mapping-layout-host：真实arm64e编译配方的类型布局输出验证VM owner ABI不变、Mapping56→64。没有指令/二进制分析。
- surface-source-provenance：原245实际Mini overlay源/配方完整重建字节一致。
- surface-parser-host：schema2正例、未来fence/非法文本/schema/CPU lease负例及zero未知控制；均为合成数据。
- patch-replay：五份最小补丁实际应用后逐字节恢复最终源。完整链接和头依赖结果归于当前最终版本。

[源码及输入清单](../patches/diagnostics/ios26-surface246/source-manifest.json)；[离线证据](evidence/k80-gpu-v246-surface-backing-offline-2026-11-16.json)；[回归脚本](../scripts/check-ios26-surface-association.py)。脚本必须提供包含实际MiniIOSurface.cpp及新header的prepared source-root，使用新out目录，不会访问USB。

## 继续工作

246 producer/schema2/receiver组合、当前panic sender、实际framebuffer body和PTY验证已完成。当前246 scope已消费，不得再启动。接下来应连接已经GPU写入并校验的已知IOSurface与实际显示请求，或在下一独立候选中补充有限匹配结果以辨别未关联原因；现有零fence不能区分未匹配、其他surface或生命周期已结束。不能把关联fence直接升级为GPU写入或最终呈现。接下来仍需已知GPU输出与实际显示surface的像素/提交对应验收，及FT3683真实点按、滑动、抬起、身份、边缘行为。没有物理输入时，host合成触点或空帧轮询不能替代手势实机证据。

## 246完整包与单次实机结果（更新）

kernel仍为13af1f12…，boot为`0e100342d5917eddc3f4af0e2a7d93db29d2a83076ca36c13778ac91d0d49711`。FD为1bf94507…，ADT为9bc31243…，root仍193e5f01…；FAT五成员核验、真实PAC consumer、原300秒看门狗/600秒Recovery和原启动参数保持。新工具为read-zorn-gpu-metal246-cdc.py及zorn_ios26_gpu_v246_metal_trial.py，绑定实际surface源/29项重编中的相关对象/依赖/完整链接和schema2 parser；82项错误输入拒绝检查通过。当前VM/Submit源已变化，因此时钟回归重新提取当前真实片段执行ASan/UBSan，并按当前配方重建三个clock owner对象字节一致。原时钟回归脚本增加显式ring-header输入，供prepared source不含direct-ring目录时使用；没有默认猜测头文件。

一次receiver-first临时启动于332.535487秒自动回TWRP，outer/inner exit0，39帧40678字节，准确身份/schema2通过，无部分terminal包或解析错误。Metal报告phase11/flags1023/status4/code0、CRC718ed2ce、badffffffff；两个native close均返回0。raw stderr丢弃计数仍36，strict application.complete仍false，没有削弱检查。约94秒摄像头为Apple标志，约193秒为锁屏；图像不证明GPU来源。

最后frame3071，producer/tail/completed均4，lease2，surfaces1/firstSID1，实际acquire通过、copy counter3070→3071，1125×2436；显示SID的surface_gpu_access_fence为0，全部可用帧都未见非零值。Metal探针的32×32 IOSurface与显示1125×2436 SID是不同验收对象，不能因探针像素通过就宣称桌面GPU呈现通过。零值也不能证明匹配逻辑错误：246没有独立导出匹配状态计数。

七组定义的保护样本前后逐字节一致；BCB只准备前864字节，启动前设置后4096字节整页读回一致、tail保持。此范围不等于全Android文件系统/Android启动验收。没有新root安装、存储布局写入、bootstrap、重试或刷机。

[完整包与采集组合证据](evidence/k80-gpu-v246-surface-backing-ready-2026-11-16.json)；[实机观察证据](evidence/k80-gpu-v246-surface-backing-observed-2026-11-16.json)。原离线证据保留其当时状态。后续应解决raw诊断保留容量，同时保留已通过的实际像素/close与失败资源保留路径。完整GPU显示、FT3683手势、稳定性尚未验收，目标继续active。

# K80 iOS26：无人值守 UI 复现场景269

最近实机[268](handoff-2026-11-17-k80-ios26-gpu-v268-client-census.md)已补齐4／4同task客户端CloseReturn成功，并再次通过Metal device／pipeline／GPU回读CRC718ed2ce、两个真实共享Query／Close、120次呈现、完整journal与exit0。串口frame64／SID4／fence4和95秒相机均为绿紫棋盘；332.7029秒自动回核验TWRP，7组保护一致。[268实际证据](evidence/k80-gpu-v268-client-census-observed-2026-11-17.json)。这不等于跨task、GPU桌面／Settings稳定性或FT3683完整验收。

## 当前完整离线候选

- kernel：`a36a98793849b122465d0237f8b58946a86fe174f95e36cb5523cb410fdf8ebe`。
- boot：`e75703bb730fb8b59116fd269d0d3e86bb64c13adcef7452f69ffceadc3e5ff0`；boot ID `fc312a9aa2c04015b536ec5af59242df`。
- root：`f3ad6b7b6bae2ffd8aaa835427e0b4ace823f52bd614a298d2b7d191da33dd26`；实际267安装／268观测复用，无新root写入。探针ID仍`ddb9c8640ab544cd85cae684e0fb8f66`，仅固定探针允许GPU，普通桌面仍CPU策略。
- FD：`1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab`；ADT：`421760d43d4ce113166181db5d57fb6bca3aa9a8634c6718db7075d23d186d1b`，原启动器／菜单参数1022字节保持。

[当前源码／构建／测试证据](evidence/k80-gpu-v269-autonomous-ui-offline-2026-11-17.json)，[精确补丁与实际HID来源](../patches/gpu/ios26-ui-scene269/source-manifest.json)。完整K80原生链接1399输入、0undefined；CPU16KiB／GPU4KiB／磁盘4KiB分开。33对象编译后，加入探针退出条件又重编受影响2对象并重新完整链接，当前133关键头依赖与5个启动身份消费者通过；不把此前未部署内核473354be／boot00ba96e0当成当前输入。

## 真实接口与有界动作

从实际根设备、PID1 EL0和正常线程检查后的入口启动一次独立worker，延迟120秒。先读当前GPU启动结果、初始已知任务、真实journal detached exit0及全部4个同task CloseReturn16／raw0；活动scope、backend failure、lost／recycled／pending均拒绝。CPU快照只控制是否新增该UI诊断，不授权停止DMA、重置或释放GPU资源；初始任务快照仍是冻结结果。journal API必须传非空缓冲和capacity，读取cursor0一个字节不推进CDC独立cursor。

仅在这些条件成立后，创建独立`Virtual` HID服务，复用实际选用的OS26 ZornTouchEventService26／帧构造／事件派发。实际SweetHID修复版保留关闭后的数组条目，因此用继承的锁内open判定跳过tombstone，不用数组长度判断订阅者。没有FT3683 provider open、GPIO／总线访问或物理触点状态借用。

等待打开客户端至多30秒；规范化显示坐标中执行一次底边上滑，17个接触帧、60毫秒间隔，任意一次接触派发后都尝试一个空帧抬起；软deadline32秒停止新接触／移动，阻塞后端仍由独立300秒WDT兜底。真实submitFrame返回只证明构造／void派发调用返回，不能代替队列接收、解锁或真触控证据。

未发布的init／attach／start失败按已核验引用条件清理；正常注册服务在场景后释放producer创建引用，由真实service-plane和订阅者保有正常服务生命周期，等待IOKit正常终止。不强制关闭用户客户端，不拆物理驱动，不把所有对象永久泄漏作为失败保护。失败后不继续手势。

## 串口、相机和本次验收边界

原3072字节单帧、38非终端＋1终端／529408字节预算保持：30普通＋7SHOT＋1个96字节UI终态。额外二进制帧不会ack新GPU检查点。UI包绑定boot ID、schema和CRC；未知标志、重复、截断、超预算均拒绝。源关联CPU截图等待场景终态后才采样；必须结合本次摄像头画面判断是否真正响应。

实际creator／worker／派发失败与抬起、closed-client谓词、真实Store261／Journal248入口条件已通过ASan／UBSan／TSan。40项GPU／journal／关闭条件拒绝、实际模块global程序ID与接收器、113项完整构建／根／准入错误输入拒绝通过。测试夹具明确为主机合成，不作为269真机证据；旧失败夹具与未部署完整候选保留。新增入场检查没有放松旧GPU错误判断。USB DMA发送器正文保持；当前wrapper和呈现截图条件从实际新源码核对并测试。

269单次真机已经完成：[实际证据](evidence/k80-gpu-v269-autonomous-ui-observed-2026-11-17.json)。30普通＋7SHOT＋1UI／81715字节完整接收；Metal／120呈现／完整5708字节journal／exit0与4客户端关闭再次通过。虚拟服务实际获得订阅者，入口条件成立，17接触帧与抬起均返回，派发用时1287毫秒（不是界面响应延迟）。摄像头140／150秒仍为大时钟锁屏，180／210／270秒为状态栏、组件和两个图标的桌面布局，支持无人操作下上滑进入桌面的有界结论。332.7474秒自动回核验TWRP，7组保护与完整BCB／tail一致，无重试。95秒相机仍观察到本轮Metal棋盘。

本轮串口截图完成CRC，但采到frame2190／SID3／GPU-access-fence0的黑色过渡帧，不能当最终桌面或GPU写图证据。普通桌面仍CPU策略；Settings长按、跨task和物理FT3683均未验收。下一步需延迟到界面稳定后的实源截图，并从实际图像定位目标图标，再单独审核正常backboardd GPU配置。未来试验继续从核验Recovery，以新scope／owner／ready／claim、receiver-first、340秒无音频H264相机、300秒独立WDT和600秒有界Recovery进行一次试验、零重试。新增scene仅验证无需人工操作的CPU界面输入能力，为后续真实GPU桌面复现作准备；不提前声称解锁、Settings长按或FT3683物理点按／滑动／身份／边缘行为通过。所有硬件专属未知项仍列在精确包与ready中。不能回Recovery立即停止设备操作，不bootstrap／刷机／恢复／依赖物理协助。

Android、17GPU、Data、Recovery、GPT和slot边界保持；新增工作仅暂存，不额外commit或push。没有反汇编、回溯符号化或逆向。

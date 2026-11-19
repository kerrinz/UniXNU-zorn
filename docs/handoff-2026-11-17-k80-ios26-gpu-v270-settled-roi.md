# K80 iOS26：延迟区域截图270

最近实机[269](handoff-2026-11-17-k80-ios26-gpu-v269-autonomous-ui.md)重复通过Metal／CRC718ed2ce／120呈现／exit0／4客户端关闭，真实摄像录像还确认一次合成上滑后由锁屏进入CPU策略桌面，332.7474秒自动回核验TWRP、7组保护一致。串口第一张截图却是frame2190的黑色过渡帧，不能代替最终桌面。新候选只解决截图时机和观测区域，为下一步实际定位Settings图标、GPU桌面复现提供输入；不是第二条OS适配线，也不比较两种呈现的帧率。

kernel：`57e5c0ac085680d32db69a6275568a3ead76833530a24e507509e416ff288df7`；boot：`6a147b4a6948a1627db844a7fdf5e27d7414213233cf0086ec55b5bf25f2674c`；boot ID `be48c59f862d43c49b41047053bece60`。实际267root `f3ad6b7b6bae2ffd8aaa835427e0b4ace823f52bd614a298d2b7d191da33dd26`、探针程序ID `ddb9c8640ab544cd85cae684e0fb8f66`、FD `1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab`、ADT `421760d43d4ce113166181db5d57fb6bca3aa9a8634c6718db7075d23d186d1b`和启动器保持，无新root或布局写入。

[离线证据](evidence/k80-gpu-v270-settled-roi-offline-2026-11-17.json)，[精确源码／补丁／来源](../patches/gpu/ios26-serial-roi270/source-manifest.json)。33实际原生对象重编，完整1399输入链接0undefined，139关键头和5个启动身份消费者通过；CPU16KiB／GPU4KiB／磁盘4KiB分开。

## 复用与真实条件

保留实际265 checked sampler、20048字节不可变payload、原LE／CRC／chunk生成器及原201stream结构和检查。新ROI包装只提供经检查的右上半宽／半高源别名：宽高、stride、extent来自实际Mini presenter的vinfo／fBase构造输入，不复制其他机型地址或板级参数。新68字节header携带ROI和header CRC，payload仍48×104 BGRX＋原完整呈现记录。ROI坐标是CPU面板像素，原呈现记录仍是完整逻辑帧；不能把局部图当全屏或GPU写图证据。

实际UI终态发布时通过原XNU clock API计算30秒门槛，截图仍须发生在真实present copy／helpers完成、issuer lease和fLock保护内。时间门槛只表示允许采样，不证明画面已经稳定。UI条件、17接触／抬起、正常与失败引用语义保持，FT3683 provider／总线／触点状态不受影响。

为避免30个普通日志已完成而延迟图像尚未就绪时提前结束，新增明确的late Pending适配。它调用原201检查，只有真实首帧已完成后的显式Pending转为等待；普通0、越界、首次Pending及旧错误仍失败。等待不推进frame／byte计数或GPU point ack，真实USB loop／transmit分支不发起新bulk-IN复制或START；原notification行为保留。285秒poll、300秒独立WDT、600秒Recovery、30普通＋1UI269＋7ROI／38非终端＋1终端／529408字节上限保持。

实际sampler像素／原记录、ROI/header CRC、不可变单writer、延后100次不消耗计数、真实发送分支和30秒边界均通过ASan／UBSan／TSan。当前wrapper／捕获条件／完整接收器与真实模块程序ID测试通过；119项root／kernel／源／ABI／准入拒绝通过。原helper尾部自复制错误发生在完整包已验证之后，保留错误脚本并独立验证已有包，没有重建或手机操作；路径夹具PosixPath名称错误也保留后修正。所有主机合成像素及重标启动ID夹具明确不是270实机图像。

## 本次实机结果

精确270已完成一次无人值守启动、零重试，332.1867秒自动回核验TWRP；7组保护采样一致，BCB尾部保留／完整页读回通过，当前无活动试验。30普通＋1UI269＋7ROI共81760字节完整保留，340秒无音频H264录像成功；实际内核known-task／fence／CRCe843b26a、Metal CRC718ed2ce／120呈现／exit0和4客户端CloseReturn再次通过。[实际证据](evidence/k80-gpu-v270-settled-roi-observed-2026-11-17.json)。

![实际串口右上区域，仅最近邻放大](evidence/images/k80-v270-serial-Photos-Settings-ROI-2026-11-17.png)

真实ROI来自1440×3200面板的x720／y0／w720／h1600，传输48×104，payload SHA `e0711edf605a92d85af11d8b48320743654336ff5b3662c6c101913e3eb48e62`。记录frame2227／SID1／accessfence0，清楚可见照片花朵和设置齿轮；仍是CPU策略图像，无GPU写入证明。录像95秒见Metal棋盘，140秒锁屏，180／210／240／270秒桌面，330秒TWRP。实际捕获／7片传输成立，但没有Pending调用计数，不能声称真机进入了late Pending分支。

设置图标可取ROI样本中心(35,25)，对应全屏归一化约(0.86458,0.12019)、HID约(28330,3938)，由实际图像推导；尚未执行长按，新GPU根上的布局需重新确认。17接触和抬起调用返回，dispatch1286ms不是UI响应延迟，不构成FT3683物理输入验收。

## 接收端最小修复

原接收器成功保存raw／ROI／5708字节journal且系统回Recovery后，最终`json.dump`因tuple键失败，退出1，原部分JSON／旧源码均保留。根因为生成脚本的宽泛替换把一个字符串键误改成两个元素的tuple。仅恢复该键；ROI和合成场景各自的字符串判定保持独立。新增`check-ios26-receiver-json270.py`执行实际接收后处理直至JSON写入：复现旧错误、真实raw修复后往返通过、合成UI失败时ROI仍独立通过。风险限于主机结果序列化，无驱动／设备改变；原测试漏测最终落盘，旧通过记录不冒充新覆盖。

实际raw使用固定程序ID离线重解到独立`offline-redecode270.json`，不覆盖失败原件、不为主机错误重启手机。新修复接收器并非本次启动所用；原bundle／归档／ready仍固定旧SHA，不能重写以规避 consumed 检查。完整根／ADT／FD／启动器未改，无新根或布局写入。

普通桌面依旧CPU策略。下一步单独审核backboardd GPU策略／root与内核，以及真实运行中GPU UI就绪条件；不能把探针exit0／4关闭门槛直接套在持续运行的backboardd上。随后以实际目标坐标复现Settings长按。GPU桌面、跨task和FT3683实际点按／滑动／抬起／身份／边缘／生命周期仍未验收，目标未完成。17GPU与所有基线保留。新增工作仅暂存，无额外commit／push，无反汇编／符号化／逆向。

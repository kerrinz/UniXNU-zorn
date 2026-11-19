# K80 iOS26 v268：关闭记录公平轮询与实际探针ID

最近实机[267](handoff-2026-11-17-k80-ios26-metal-v267-shared-probe.md)已通过真实Metal device／pipeline／GPU命令、IOSurface CRC718ed2ce、两个共享Query／IOServiceClose、120次呈现和exit0；串口与真实相机确认相同4×4棋盘，约332.79秒自动回核验TWRP。逐客户端内核Close证据仍不齐，完整目标未完成。

## 已定位的两个诊断问题

Store261 snapshot在没有backend故障但有能力查询Unsupported时，一直只发送同一reject记录。267 store记录数4，wire只见129，另外3个成员的终态被采样策略遮住。268仅改变CPU快照调度：phase0优先failure否则reject；phase1优先reject否则failure；phase2轮询全部注册记录，包括正常关闭。每类cursor用completedFrames/3，避免客户端数与3／6／9／63相同因数导致永远跳过某些成员。failure／reject仍优先、raw与失败关闭保留；bind／scope／end／finish／recycle／真正GPU生命周期正文保持。

267 receiver还残留禁用251的PROBE_TAG，导致最终汇总拒绝有效267报告。原失败汇总／入口归档保留，原始83580字节已用精确构建的实际ID离线重验，没有为主机bug重启。268 receiver从固定268入口导入实际仍选用的267程序ID。新的接收夹具加载真实模块全局，用真实267完整Metal报告、仅明确重标boot ID的夹具验证渲染／Query／呈现结果，并重现旧ID拒绝；不再靠手动注入正确tag漏过模块常量。旧267只有1／4客户端的记录仍判未完成。

## 当前完整候选

- kernel：`bf0bbb455c8c9948045927c4fab0e169a033e34a4af000a48af8bd953654e195`。
- boot：`4c88db3be7884b031ca5a9673bb7bdcdb3561dfd4d7d0583beed60a70b649c88`；boot ID `68353193691144bd9bae517b08d3770a`。
- 实际267 root：`f3ad6b7b6bae2ffd8aaa835427e0b4ace823f52bd614a298d2b7d191da33dd26`；程序ID保持`ddb9c8640ab544cd85cae684e0fb8f66`。
- FD：`1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab`；ADT：`421760d43d4ce113166181db5d57fb6bca3aa9a8634c6718db7075d23d186d1b`，与267逐字相同。
- [5个精确补丁／来源](../patches/gpu/ios26-client-census268/source-manifest.json)、[离线证据](evidence/k80-gpu-v268-client-census-offline-2026-11-17.json)。源码：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v268-client-census-68353193691144bd9bae517b08d3770a；构建：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v268-client-census-68353193691144bd9bae517b08d3770a。

32实际原生对象重编／1398输入完整链接0undefined、126关键头依赖与5消费者真实ID检查通过。Store仍10264字节，快照仍104字节，wire／共享头名称261保持；CPU16KiB／GPU4KiB分开。受Store变化影响的真实close／context／retirement方法重新用ASan／UBSan／TSan编译验证，原正常／失败持有语义保留。新增测试实际复现旧饥饿并验证1..64客户端和模数重合场景可轮询到所有记录，priority／failed-close不丢失。

GPU／VM／HFI／固件／root／已签名探针／shader／presenter与267逐字保持，正常UFS／CDC只重标boot ID。现有early／journal／探针场景复用以前提明确的正文／共同头相同证明和当前native身份核对，当前callback／record／terminal／gate／close-reset、完整接收器与新census判定已重跑。未选用旧sanitizer结果冒充新Store通过。主机测试曾因旧projection比较需要260基线而误传267、旧fixture假定本目录early测试、最大帧加长及helper自复制失败，失败版本保留后按实际契约修正；期间没有268设备操作。

当前102项bundle／实际安装／root／kernel／ABI错误输入拒绝与busy／stop／独立storage准入拒绝通过；接收／相机控制通过，H264编码器固定。继承原31普通＋7图像槽、38非终端＋1终端／529408字节上限、285秒poll、300秒独立WDT／600秒Recovery，零重试，无新根安装或存储布局变化。新的最终判定要求捕获全部注册记录、同一task、每个CloseReturn成功、无活动scope／backend failure／lost／recycled，不能用3条闭合记录代替4条注册记录。

磁盘清理只移除266从未owner／ready／claim准入的旧重复准备目录中4个大文件247382520字节；先逐字SHA匹配到保留的真实266归档，保存清理记录与旧bundle。实际真机产物、源码、17GPU和所有根／Data基线保持。

268实际单次启动完成：接收器verified=true，31普通＋7图像／83600字节；4个客户端64／129／194／259全部同task，CloseReturn stage16／raw0，无活动scope、backend failure、诊断丢失或recycle。当前Metal device／pipeline／GPU回读CRC718ed2ce、两个实际共享Query／Close、120／120呈现、5708字节完整journal和真实exit0通过；VM成功map21／unmap21、8929280字节对应。旧两槽observer仍保留session_rejected=2和stderr dropped38，不改写为旧协议完整成功。串口frame64／SID4／fence4与95秒相机都显示4×4绿紫棋盘。约332.7029秒自动回核验TWRP，7组boot保护字节一致、完整BCB／tail通过；无新根安装或重试。[实际证据](evidence/k80-gpu-v268-client-census-observed-2026-11-17.json)。该探针范围内逐客户端生命周期完成；跨task隔离与全桌面仍未验收。仍从核验Recovery、独立scope／ready／claim、receiver-first和340秒无音频H264相机开始。不能回Recovery立即停止设备操作，不bootstrap／重试／刷机恢复，不依赖用户物理协助。全部桌面／Settings长按、跨task隔离与FT3683实际点按／滑动／边缘／生命周期验收仍未完成。没有反汇编、回溯符号化或逆向。新增工作只暂存，不额外commit或push。

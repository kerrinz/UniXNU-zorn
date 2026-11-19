# K80 iOS26 v267：真实Metal探针与共享成员同步

最近实机[266](handoff-2026-11-17-k80-ios26-gpu-v266-known-readback.md)已验证初始GPU图像任务：fence2、CRCe843b26a、unmap／device refs0、table2:2及taskOOB释放，约332.61秒自动回核验TWRP。本候选267完整内核／根镜像／启动包与离线检查已形成，已安装精确46页根增量并完成一次系统启动，约332.79秒自动回核验TWRP；7组boot保护采样一致。

## 最小变更与来源

[探针说明](../native/ios26-probe267/README.md)、[9个精确补丁／来源](../patches/gpu/ios26-metal-probe267/source-manifest.json)、[离线证据](evidence/k80-metal-v267-shared-probe-offline-2026-11-17.json)。旧251探针预期Metal原生会话存活时第二Query被ExclusiveAccess拒绝；257之后已真实实现多逻辑成员，旧断言不再适用。这是继续使用旧探针前发现的接口差异，不是Settings长按卡死根因。

保留实际Metal设备发现、library／shader／pipeline、真实IOSurface poison与逐像素／CRC718ed2ce校验、原120次有界呈现／查询及资源生命周期。只把旧拒绝断言改为两个真实Query／ABI校验／相等参数与正常Close；失败后保留到看门狗，不接受恒定成功。内核GPU／VM／ring／GMU/HFI／共享成员及原presenter正文保持，原生变化为精确boot／program身份、探针stderr筛选和真实新root digest。公共265SHOT／266初始任务／264VM totals协议保持。

独立32GiB根只改3个现有文件：已签名zorn-metal-probe193、NativeAdrenoMetal.clients探针专用策略、既有launchd job RunAtLoad／Disabled；KeepAlive仍false。其余Metal／Turnip／Rust／系统文件和568项受监控属性保持，原252镜像哈希与metadata复核不变，签名／文件系统检查通过。

## 精确输入与验证

- kernel：`8c14ac8cfa2b0b60626dd658292f299f6a33fdc1e700f03f46c5407c12151975`。
- boot：`749d6ebeb3b0221a7fded36d0825087d2705299b531161329816d952b7536c46`；boot／program ID均为`ddb9c8640ab544cd85cae684e0fb8f66`。
- root：`f3ad6b7b6bae2ffd8aaa835427e0b4ace823f52bd614a298d2b7d191da33dd26`；父已安装252 root `859c7ebae6355ef7e089896680b0b8ffd9a03af8a1f078918feec740b7a06b02`。
- FD：`1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab`，保留原固件／启动器。
- ADT：`421760d43d4ce113166181db5d57fb6bca3aa9a8634c6718db7075d23d186d1b`；仅chosen:zorn26,root-image-sha256改变，反向还原后与266 ADT逐字相同。
- 源码：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/metal-v267-shared-probe-ddb9c8640ab544cd85cae684e0fb8f66；构建：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-metal-v267-shared-probe-ddb9c8640ab544cd85cae684e0fb8f66。

新root形成后更新实际ZornRootWindow26.h再重编受影响原生对象与完整链接；初步父root头构建保存在before-current-root-binding，不能作为新root资格。当前32对象／1398输入／0undefined，126项关键头依赖、CPU16KiB／GPU4KiB与真实5消费者身份检查通过。原物理后端和共同头逐字核对，root头只换哈希、几何逐字保持；root敏感原生对象已重编。

当前实际callback／observer／journal、early、close reset、终端sender／gate／cadence以及共享Query／Close检查通过，ASan／UBSan／TSan均禁用符号化。旧early夹具写死backboardd、旧parser夹具的base64程序ID未改导致失败，保留失败产物后改为显式进程选择与明确synthetic retag；原252测试不改。新增严格结果检查保留原loss／rejection字段，不把主机夹具或参考机型结果作267硬件证明。没有反汇编、地址／回溯符号化或逆向。

新root从Data实际末端重新计算1MiB对齐位置：relative LBA6291712、32GiB、gap782336、尾部reserve8588886016；不是直接复用旧窗口。全镜像差异46个4KiB页／18组，本地clone重放完整SHA相同，Data／log／越界／未对齐、末组预映像错与首组读回错停止控制通过。独立Recovery-only计划核对7395页既有真实读回覆盖和新46页所有预映像；78项错误输入拒绝，原安装scope、运输／失败函数保持，固定入口只加精确267 review哈希的新flag。

## 尚待实机

存储安装需新scope／owner／ready／claim、固定工具、核验Recovery／92988a43／zorn／slotA、GPT／Data／17根／保护边界／完整BCB，所有预映像通过后仅写46页并逐组读回；600秒、零重试、无自动启动，停留Recovery。安装成功后才能另建独立单次boot准入，receiver-first、340秒H264相机、300秒独立WDT／600秒有界Recovery；这些硬件条件尚未提前成立。不能回Recovery立即停止设备操作。

需要确认实际Metal device／pipeline／GPU渲染／CRC、两个共享Query／Close、原生关闭、已知图像呈现与真实进程退出。267探针只有同一task的逻辑成员，不能外推跨task隔离、桌面所有像素、物理scanout或FT3683点按／滑动／边缘。完整目标仍active，不依赖用户观察或操作。新工作只暂存，不额外commit或push。

## 实际根安装补记

[安装证据](evidence/k80-metal-v267-root-installed-2026-11-17.json)：7395页既有实际覆盖和全部46页预映像通过，18组46页188416字节逐组读回成功，汇总SHA322963faeeb2bc599194deb507b915a808dfb4415c550eb70f65921ebb047b33。8组保护元数据／边界／BCB／log字节一致，仍为核验TWRP，零重试、无启动。不是全手机32GiB root读回。新first-page只取实际写入读回的第0页，并与候选页逐字核对；boot入口分别核验新实际安装收据与保留的offline package状态，未把offline root_installed改成成功。

独立267 boot bundle已建立：新root／ADT／kernel／FD／菜单、receiver、固定H264相机和共享头／结果解码器分别归档。98项内核／根／程序／实际安装／共享inode等错误输入拒绝，当前状态busy／stop或另一个存储准入会在probe／claim前拒绝。当前未生成实际boot claim；真实Metal任务、呈现和自动回收仍是下一次硬件待证。

## 精确267实机补记

[实机证据](evidence/k80-metal-v267-shared-probe-observed-2026-11-17.json)：真实Metal device与内核service ID一致，library／pipeline／命令完成，真实IOSurface逐像素与CRC718ed2ce／bad ffffffff通过。两个额外IOKit连接的Query／ABI校验／Close均成功。原120呈现请求和完成均120，SID4／access fence4，first3／last333；5708字节journal完整CRC／task绑定、真实detached exit0。31普通＋7图片片83580字节，340秒H264相机成功，单次零重试约332.79秒自动回核验TWRP，BCB完整读回／尾部保护及7组boot采样一致。

[实际串口棋盘](evidence/images/k80-v267-serial-Metal-checkerboard-2026-11-17.png)为source关联frame64／SID4／fence4；[95秒真实相机画面](evidence/images/k80-v267-camera-Metal-checkerboard-2026-11-17.png)可辨绿色／品红4×4棋盘。32×32 Metal像素回读、同一surface的真实呈现与CPU截图及实屏已知图像分别关联；图像是实采样，没有生成或补画。相机模糊／过曝不支持逐像素panel色度结论，也不外推桌面全部像素或稳定性。110秒后锁屏、330秒TWRP splash。

原receiver仍残留旧禁用251 PROBE_TAG=f80eb140…，因此运行时最终汇总拒绝报告；原失败cdc-capture.json及入口归档不改。离线用实际源码／已签名探针／ready绑定的ddb9c864…重解原始字节，通过精确boot／CRC／journal／原生记录检查，没有为主机bug重启／重试手机。此前接收夹具直接注入tag且没有当前Metal报告，漏测模块全局。下一receiver必须导入实际选用的PROBE_TAG，并以本次真实Metal报告和实际模块全局作回归。

完整关闭验收仍false：CF store共有4条记录，但原snapshot在无backend故障时永远优先同一条method8能力查询的Unsupported拒绝，因此只导出已正常Close的129，遮住其他客户端。两个IOServiceClose返回0与实际进程退出已记录，仍不冒充全部内核Close闭环。268独立源码只修CPU采样调度：优先failure／reject，并保留每3帧一次all-client轮询，使用独立round计数避开3／6／9等模数重合；GPU后端／root／探针保持。完整GPU／Metal桌面／Settings长按及FT3683实触手势验收未完成。

# K80 iOS26：277 手动验收与待修项

用户明确要求“尝试进行一次验收，我来操作手机”。277 为独立手动候选，不使用尚未实机运行的276自动设置／列表滑动候选。已完成一次手动实机验证，333.4819秒自动回核验TWRP。用户确认解锁、设置长按菜单出现／收起及上滑返回桌面有响应；设置列表可见但无法滑动，**不是系统整体卡死**。用户决定将设置交互单列待修，GPU主线优先定位低帧率。[精确实机证据](evidence/k80-gpu-v277-manual-acceptance-observed-2026-11-17.json)。此前275一次菜单出现与收起的证据继续保留，不转移为277验收。[275交接](handoff-2026-11-17-k80-ios26-gpu-v275-menu-dismiss.md)。

## 精确输入与实际变化

boot ID `e13cccee337c43fc8020baea055232ae`；kernel `c2ccd636cd55da3a1587c5c1d8e0353beef337b86648a6c26127d2a5437e9745`；boot `189853747c68062f05f14d8c5a1e41c80b782d43f4aa0154b2d6c09787023e9a`。33原生对象、1399完整链接输入、0 undefined，142实际关键编译依赖、CPU16KiB／GPU4KiB／磁盘4KiB。来源为实际275源码，GPU／VM／时钟／固件／提交／fence／Metal frontend／Rust／Turnip及物理FT3683后端保持。[源码与零fuzz重放](../patches/gpu/ios26-manual-acceptance277/source-manifest.json)。

277替换诊断UI工作线程：不创建／注册虚拟HID service，不打开触控provider，不发送任何合成触点。实际根EL0之后90秒开始9次CPU进度采样，间隔10秒，每次保存uptime及原有16项真实呈现／fence／CF／应用观察值；其后5秒满足既有已完成呈现截图条件才保存ROI。672字节K80MN277记录由7项头部与9×17项样本组成，CRC覆盖664字节，schema277位于668。缺失采样源／平坦fence／后端错误原样记录，观察线程完成不等于触控、菜单或GPU通过。物理触控仍由已有FT3683总线／工作线程／HID路径提供；此次未增加触点身份原始帧日志，不能仅凭相机把完整身份与边缘验收记为通过。

## 启动保护与操作顺序

仅92988a43／zorn／slotA，从固定runner内重新核验的TWRP／OrangeFox出发。现有271根 `c60b198ded30a982cf96ee9cb66211a8f74c7d8fa80f5b6dd8e0839e121304fc` 只读复用，无新安装／布局变化。FD、ADT、loader、manager、1022字节参数保持275实际输入；完整清单位于本地独立scope `single-K80-ios26-gpu-v277-manual-300s-e13cccee` 的bundle／ready归档。接收器先行、300秒独立硬件WDT、600秒核验Recovery返回、新owner／ready／claim、一次启动零重试。Android／Data／17／GPT／Recovery／slot／启动分区保护保持；异常DMA状态保留资源，不重试、bootstrap、刷机或恢复。不能核验回Recovery时立即停止设备操作。

提示手机就绪后，由用户解锁；长按设置等待菜单，短暂停留；点空白处收起，打开设置；上下滑动并松手观察，检查屏幕边缘响应。卡死时停止触摸、记录最后动作，由看门狗回收。视频340秒、不录音；相机入口绑定age不是首帧曝光时间，视频时间不直接与kernel uptime对齐。

## 离线验证与限制

实际观察线程／创建方／CPU采集／wire经ASan／UBSan及TSan检查；9次采样、无虚拟HID发送、一次调度、错误机型／上下文拒绝、线程创建失败、未知handle保留、5秒capture边界通过。已有GPU回调、关闭、未知DMA保留、早期启动、日志页、实际编译身份与5个旧VFS拒绝、串口latePending／ROI预算和38帧限制重新检查。277解码／最终JSON后处理25项控制及94项包／准入拒绝通过；所有合成测试数据明确标记，不是手机结果。

固定runner的新入口最初有模块顶层return语法错误，check-only在owner／ready／claim／USB前拒绝。已改为既有elif分派并重新核验，旧离线bundle／runner／检查记录保留于本地failed-runner-dispatch-preflight；未发生启动重试。新的相机设备清单已实际核对USB  Camera，仅主机设备枚举。

完整GPU／Metal／显示／触控验收仍未完成。本次观察不能代替完整Liquid Glass光学正确性、长期稳定性、跨task隔离、客户端退出／资源释放或物理触点身份验证。全程不反汇编、不逆向、不做地址符号化或Apple shader二进制分析。仅暂存，不新增commit／push。

## 本次结果与问题边界

机主先描述“设置能打开但卡死”，随后明确更正：“打开设置后展示了列表但不能滑动……能通过上滑手势回到桌面，所以并非系统卡死”。更正为本次最终结论，不将它记成GPU hang、系统卡死或Liquid Glass故障。机主另述此前CPU路径也出现设置无法操作，这是历史观察，不是本次精确构建的对照实验。按新指示保留设置待修记录，暂不阻塞GPU主线；未提供未经证实的根因或伪修复。

九次实际CPU快照的uptime为140774至220782ms，完成fence依次72、80、83、87、87、89、89、89、90；CF后端sequence0／dropped0，compact观察丢失1条。普通记录上限30帧，不能把末普通计数2599或阶段性平坦fence解释成系统卡死。延后ROI来自frame88／SID130／producer=completed=access93，payload SHA315313ec302cfc5096f882c5cc2f25b9b4a120afc7f93355261cdaece013d5cd，可见Photos／Settings桌面图标。这些粗粒度进度样本不是实测FPS，也不证明每帧GPU写入或物理scanout。

![实际串口右上ROI，仅最近邻放大](evidence/images/k80-v277-serial-home-ROI-2026-11-17.png)

初始有界GPU任务完成，真实fence2／CRCe843b26a／ring101:101／table2:2／引用0／OOB127。接收器exit0，30普通＋1manual672B＋7ROI共83642字节；backboardd日志9621字节／62records全部发布收到，pending0／gaps0。其日志保留render-pass split、memoryless backing及attachment-read-in-place等警示；没有Settings进程日志，不能据此确定设置交互或低帧率根因。末普通VM map591／unmap146、累计2025553920／1300824064字节不是实时用量／无泄漏证明。

视频340秒／15678959字节，SHA033f7a40773c7af5247ff761a90ad13c956bf12ada9bdbd83413531b3bff472d，未录音；相机入口绑定age7.1687秒不是首帧曝光时间。手机大部分移到镜头左侧画外，只能看到部分菜单样／列表样区域，无法凭这些帧独立验收全屏或列表滑动；交互结论以明确记录的本次机主观察为依据。无补画或图像增强。

一次启动零重试，333.4819秒核验回TWRP，7组保护采样及BCB尾部／完整页读回通过，活动scope清空。未新增根写入、固件构建或布局变化。完整目标仍未完成；后续优先建立提交、fence等待、frontend／转换器、CPU复制和呈现各阶段的实际耗时，再决定优化，避免直接猜频率或把九个采样点换算成帧率。设置问题留作独立待修，渲染正确性、资源生命周期、跨task、长期稳定性及完整FT触控仍需验收。

## 低帧率主线的实际起点

精确277源码核对发现：K80的真实present lease／ready检查位于show之前，已有fStatWaiting从show内部才开始计时，未覆盖这段等待，不能直接当作完整GPU等待耗时。ZORN_IOS26实际路径还要CPU drawLayer复制／缩放并完成stores，非ZORN的直接scanout代码不参与；已有houji_fb_stats默认关闭，本次1022字节参数也未启用它。后续应复用实际CPU时钟转换与计数，把排队、lease／acquire等待、复制／缩放、完成呈现的分段耗时接入受检查串口，再对不含设置的固定工作负载测量。以上是计时覆盖缺口和真实路径发现，不是已确认性能瓶颈。[源码审核与精确输入](evidence/k80-gpu-v277-performance-source-audit-2026-11-17.json)。

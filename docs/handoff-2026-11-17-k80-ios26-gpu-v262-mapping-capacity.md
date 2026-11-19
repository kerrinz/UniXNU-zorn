# K80 iOS26 v262：真实映射拒绝与后期串口覆盖

v262已完成一次无人值守真机启动，零重试，332.783秒自动返回核验TWRP。38帧／65708字节串口完整，8CPU采样有效；实际VM预检捕获stage170／reason25／BoMap NoResources：剩余572条，请求847条。所选4096容量已用3524条，本次合计需要4371条；这是CPU跨度元数据预检拒绝，不证明物理页表或固件异常，也未证明它就是最终卡死原因。其后第二客户端继续9379次调用，未采到退出／关闭。

340秒相机录像成功：8秒启动console、95／210秒暗屏、330秒TWRP。暗屏原因不明，不能据此宣称桌面或物理scanout正确。本次没有手动／合成输入，不曾重演长按设置场景。最近实际交互证据仍是[v261](handoff-2026-11-17-k80-ios26-gpu-v261-client-failure.md)：用户确认锁屏／桌面及滑动、点按、长按、解锁，最终长按设置卡死；两条路径均低帧率，不比较高低。后续完全无人值守，不依赖物理协助。

[本次实机证据](evidence/k80-gpu-v262-mapping-capacity-observed-2026-11-17.json)。其中owner_261_long_press_freeze_not_reproduced_by_synthetic_input仅表示本次未实施合成输入，不是“实施后未复现”的断言。所有7组受保护采样相同，BCB864字节写入经完整4096字节读回与尾部检查；未改Android／Data／17／根／布局。完整GPU验收仍否。

## 实际源码连接

261只记录到BoMap的NoResources汇总，未指明内部来源。262在真实VM预检原有拒绝条件中记录对象上限或剩余／请求跨度；原有handle耗尽、holdForDevice和VM map返回也连接到CPU记录。stage170理由24为对象数／上限，理由25为剩余／请求跨度；171为handle，172为真实引用错误，173为真实VM返回。计数溢出明确饱和为UINT32_MAX，不输出地址。原生容量仍4096，原有条件、返回、资源引用与提交路径保持，未把资源错误改成成功。

原正常串口poll120秒，无法覆盖录像中的晚期桌面；262仅对现有progress路径延长到285秒，非progress仍120秒。实际保留的进度owner提供CPU节奏元数据：启动／等待确认点3秒，成功完成point6且无等待时9秒；新等待点会缩短已排期的慢间隔，原10秒gate预算不变。这不是GPU权限或完成回调，没有新增线程、MMIO或GPU操作。实际节奏和较长USB持有对时序的影响仍需真机确认。

新边界检查发现原panic发送条件要求已有帧数小于39，而普通流可发满39；发满后panic会被拒绝。262在调用原producer前限制普通帧最多38，为终端留一帧。原39总帧、529408字节总预算和409600字节panic容量均保持，普通帧最大116736字节；无强行取消、复用未完成DMA或放宽失败清理。未知状态仍保留。

## 离线验证与精确产物

实际预检容量／边界／饱和控制、实际owner节奏／deadline代码、共享记录器／关闭／上下文／退休链的ASan／UBSan及TSan、当前worker／服务／终端发送与严格容量解码通过；硬件边界夹具明确。源码投影保留原生操作条件与返回，额外CPU大小读取明确列出；Board／HFI／底层Ring／执行权及AppIo正文与261相同。32个实际对象重编，1398输入完整链接0undefined，118有效头检查，CPU16KiB、GPU／磁盘4KiB独立。实际编译器核对五个记录／panic消费者并拒绝旧覆盖层。七份补丁零fuzz重放，FAT成员读回／payload重组／原源码文件section元数据consumer通过；未解析指令或地址。

- kernel：`031799d7b9472ac77102042bf42c561a667ec903b28c220fdf1f08712dce648c`。
- boot：`7a6e820b52a11fc45bc7d74cfa5189d55837b67447cd2299d5a8eb078ae173db`。
- root：`859c7ebae6355ef7e089896680b0b8ffd9a03af8a1f078918feec740b7a06b02`，实际已安装252根，只读复用。
- FD：`1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab`；ADT：`98f04ff54b9573ddaa2c4716da0e954fae8192d15b1f105426eba7f216805936`。
- 启动ID：`3df21cbd4e974475befb85cebe382928`；禁用探针ID保持`f80eb1403d7e4f958b5eddacb49d98d0`。

[精确补丁与来源](../patches/gpu/ios26-mapping-capacity262/source-manifest.json)、[当前离线证据](evidence/k80-gpu-v262-mapping-capacity-offline-2026-11-17.json)。源码/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v262-mapping-capacity-3df21cbd4e974475befb85cebe382928；构建/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v262-mapping-capacity-3df21cbd4e974475befb85cebe382928。离线打包首次因版本文字替换误改历史日期路径而失败，独立partial输出已保留，已修复并逐项核对文字日期／身份不变后重建；未访问设备。

## 截图来源与下一步

本地UniXNU-sheng固定提交6a3d35c02504b712897799c5481952a61761325d的BootDiagExport.c已有16字节SHOT／BGRX封包、pitch／depth检查和有界降采样，read-sheng-log.py通过Linux reader的CDC shell取导出数据。该机型userdata导出区域、GOP地址和直接scanout hook不作为K80输入；此候选尚未接入截图。后续只复用适用格式与处理逻辑，采集必须绑定K80实际呈现owner／fence／缓存及独立有界传输，截图不冒充物理scanout证明。

下一步见[v263跨度容量修复](handoff-2026-11-17-k80-ios26-gpu-v263-span-room.md)：将实际K80创建方容量调到8192并记录真实Domain值，仍须验证实际映射、fence、渲染与故障处置。Android／Recovery／17／Data／根／布局不变。完整GPU／Metal／显示／FT3683验收尚未完成；新增262工作按既有要求暂存，不自动再生成commit或push。

# K80 iOS26 v266：既有内核图像任务的真实回读

[v265](handoff-2026-11-17-k80-ios26-gpu-v265-serial-shot.md)已自动回Recovery并实际取得串口锁屏缩略图。v266已完成一次精确构建实机：31普通帧＋7图片片／84142字节，约332.61秒自动回核验TWRP，零重试、7组保护采样字节相同、BCB完整读回／尾部保护通过；本次只导出既有初始GPU任务的结果，不增加GPU工作或更改根镜像／策略／触摸路径。

实际HostRing runKnownImage后端保持逐字不变：真实CPU16KiB backing／32KiB任务缓冲、GPU4KiB映射、poison6d、既有命令提交、最多1000000us等待真实fence、原idle检查、device-write acquire、全32KiB边界／32x32红色图像CRC验证、真实unmap／引用回收／OOB释放。backing按既有组件资格生命周期保留。新增[公共投影](../native/ios26-known266/README.md)由真实UFS完成回调读取既有getter；worker完成前为不可用，失败数据原样保留。导出24字段，不导出地址或handle。冻结初始记录不能用作后来客户端DMA已停的释放许可。

判定要求raw0／phase6／flags、grant、正值且相等的完成fence、outstanding与device refs为0、无poison、CRC e843b26a／firstBad ffffffff、table lease平衡与taskOOB flags127／raw0。idle严格沿用源码：游标相同、status除bit0以外清零、raw busy bit23清零；不错误要求整个busy寄存器为0。

- kernel：`2afbaca451c13a15e6704db0838083b911f67e3f37614d89dbf73980a5ffc345`。
- boot：`5ac95441fb9f76ce759b1838084bde504313bfde6d05365bbd2655be4ff9f1d6`；bootID `df2c09e8c23f42cba9b0a3e6e2e78ae9`。
- root：`859c7ebae6355ef7e089896680b0b8ffd9a03af8a1f078918feec740b7a06b02`，复用已安装252只读镜像；FD／ADT／启动器／1022字节参数保持。
- [五补丁及来源](../patches/gpu/ios26-known-readback266/source-manifest.json)、[离线证据](evidence/k80-gpu-v266-known-readback-offline-2026-11-17.json)。源码：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v266-known-readback-df2c09e8c23f42cba9b0a3e6e2e78ae9；构建：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v266-known-readback-df2c09e8c23f42cba9b0a3e6e2e78ae9。

32实际对象／1398输入／0undefined，CPU16KiB与126项实际选中关键头依赖核对；包含Shot265、KnownTask266和实际known-image helper头。v265原120项只代表其明确选中的关键头，不代表全体头文件；[补充依赖审计](evidence/k80-gpu-v265-supplemental-header-closure-2026-11-17.json)保留原始记录并核对四项编译器依赖。五记录／panic消费者拒绝旧覆盖层；五补丁零fuzz重放。当前formatter／callback／decoder／early／close／terminal／gate／cadence检查通过，底层复用测试以实际正文与头相同为条件。最大字段帧3068字节、最差仍容纳30字节journal；kt投影实际增加221字节（初版离线风险文字222为估算，未重写该历史证据）。主机夹具中协议名、截图清理路径和截断点错误已修正并保留失败版本；失败期间没有设备操作。

仅本次硬件能确认：精确266任务的真实fence、CRC、unmap与taskOOB结果，普通客户端与图像传输并存，以及自动回收。准备独立scope／owner／ready／claim、receiver-first、300秒独立WDT、600秒Recovery、零重试；38普通＋图片共用槽／1终端槽／529408字节上限保持。相机恢复固定libx264，340秒无音频／358秒host timeout，新增编码器不变量检查。原Android／Data／iPadOS17／分区／只读根保持。

无用户操作依赖。不能回Recovery立即停止设备操作。初始内核任务即使通过也不是Metal前端pipeline、普通surface GPU像素、物理scanout、Settings长按、全部客户端退出或FT3683物理手势验收。新增工作仅暂存，不额外commit或push。

## 本次实机结果

[实际证据](evidence/k80-gpu-v266-known-readback-observed-2026-11-17.json)：初始任务raw0／phase6／flags63，实际ring游标101:101，fence2已完成，outstanding0、无poison、device refs0；真实输出CRC e843b26a、firstBad ffffffff，table acquire／release2:2，taskOOB flags127／raw0已释放。raw busy71000000／status1符合原idle掩码；不要求整个busy清零。该冻结记录验证本次初始内核已知图像任务及其释放，不是后来客户端的DMA静止证明。

[本次串口图像](evidence/images/k80-v266-serial-lockscreen-2026-11-17.png)boot／CRC与frame64／surface96／accessfence67关联，20048字节SHA220300b1fb1906a32902e7cf32bfb7f24d9f5eacb5d7a89b0ba84ea787e13706，可辨4:02锁屏。340秒无音频H264相机成功，210秒4:03锁屏，330秒TWRP splash。图像是CPU framebuffer实采样；初始红图GPU结果和锁屏缩略图是不同对象，不能合并成普通surface GPU像素或物理scanout资格。

窗口内无容量／后端拒绝，成功map733／unmap447；累计字节5901189120／5393629184独立采样，不能相减为精确活跃PTE或证明无泄漏。第二客户端4886调用，未采到其退出；Settings长按和真实FT3683手势未实施。Metal frontend／pipeline／显示和完整生命周期验收仍未完成。266 receiver与相机均正常结束，设备状态idle／stop false。离线证据中的硬件pending保留其生成时的事实，由此精确构建实机记录补充。

# K80 iOS26 v265：实际presenter串口缩略图

最近实机[v264](handoff-2026-11-17-k80-ios26-gpu-v264-pool-capacity.md)确认运行容量131072，采样窗口无跨度容量／后端拒绝，成功map1039／unmap700；38帧／68910字节与340秒录像成功，210秒可见锁屏，约332.67秒自动回核验TWRP，7组保护采样一致。不能由此排除泄漏或认为Settings长按卡死已解决。

v265已完成一次无人值守实机：31普通帧＋7图片片／77313字节串口，340秒录像成功，约332.75秒自动回核验TWRP，零重试，7组保护采样一致，BCB完整读回／尾部保护通过。仍使用同一已安装252只读根、131072CPU元数据后端、direct-ring／HFI、backboardd-only策略与禁用探针，未添加触摸输入或新存储路径。

## 截图来源与真实连接

[公共代码](../native/ios26-serial265/README.md)参考固定sheng6a3d35c02504b712897799c5481952a61761325d的BootDiagExport.c SHOT／BGRX格式、stride／depth边界与最近邻行采样。没有借用该机型GOP地址、userdata区域、Linux reader shell或直接scanout hook。CRC／小端写复用现有236实现，USB DMA／FIFO／失败处置复用原K80 owner。

实际factory先核对完整CPU alias／页范围，再给framebuffer对象设置已核验extent；presenter保留原issuer lease，show已返回、helper stores完成且copy counter前进、实际frame>=64时，在原fLock下采样对齐32位字。仅一次48x104 BGRX，不分配新GPU资源或访问新MMIO。20048字节包含16字节SHOT头、19968像素和64字节真实present记录尾部；release／acquire发布后保持不可变，串口只复制其内容。

七片各不超过3072字节，绑定当前bootID、偏移、长度、单片与整图CRC。与普通日志共用原38非终端帧／529408字节预算，预留1终端帧；不增加panic容量或重用未完成DMA。普通序号仅在真实普通帧后推进，新GPU确认点仍需两次普通观察；图片片不作确认。等待gate保持3秒，已就绪七图片片临时3秒，完成后idle回9秒，285秒poll／300秒WDT不变。

现有启动参数长1022字节，沿用本次265内核的zorn26_gpu_cdc=1诊断选择，没有新参数、菜单或根镜像变化。没有读取性证明的CPU alias仍是本次硬件待证条件：地址翻译／写屏成功不等于对齐读取一定成功。截图仅代表CPU framebuffer采样，不能证明GPU写像素或panel scanout。

## 精确构建与离线验证

- kernel：`d0be4b147df9fdcaa7726c6946ec6df949280da6bdcc39db8b6cb77605992287`。
- boot：`1742fa9209d4b668fcf53bd07b878c9d6fb455ba8ff6a6616ef81498e4dc0345`。
- root：`859c7ebae6355ef7e089896680b0b8ffd9a03af8a1f078918feec740b7a06b02`，已安装252只读复用。
- FD：`1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab`；ADT：`98f04ff54b9573ddaa2c4716da0e954fae8192d15b1f105426eba7f216805936`。
- bootID：`dc48e662130d4dc28186229f33c6aa7e`；禁用探针ID不变f80eb1403d7e4f958b5eddacb49d98d0。

[精确六补丁／来源](../patches/gpu/ios26-serial-shot265/source-manifest.json)、[当前离线证据](evidence/k80-gpu-v265-serial-shot-offline-2026-11-17.json)、[最近实机](evidence/k80-gpu-v264-pool-capacity-observed-2026-11-17.json)。源码：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v265-serial-shot-dc48e662130d4dc28186229f33c6aa7e；构建：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v265-serial-shot-dc48e662130d4dc28186229f33c6aa7e。

32实际对象／1398输入完整链接0undefined，120有效头与CPU16KiB核对，实际编译器五记录／panic消费者匹配并拒绝旧覆盖层。新增头与公共源相同，六补丁零fuzz重放。实际capture hook／getter／CDC wrapper在CPU夹具中通过flag0、frame63、未copy、extent不足拒绝与frame64采样、七片、确认点顺序及3→9秒切换；共同头的发布竞争和边界通过ASan／UBSan与TSan。解码验证31普通＋7图片、外来boot、CRC、缺片／乱序、预算、部分片和不覆盖已有文件；图片夹具不是265实机。原普通worker／producer、idle谓词与原present流程在移除明确新增CPU采样后逐字投影相同。当前early／close reset／终端／gate及此前实际VM／Board／HFI／Ring生命周期按正文／头相同证明保留，未移用旧硬件结论。

主机夹具曾因identity头搜索路径和声明链接属性失败，已独立保留并修正后重跑；原生编译先前已通过，未因这些夹具失败上机。新参数触及长度上限前改用既有CDC开关，保留上一内核／对象／输入，重编受影响UFS对象、完整重链并重跑当前identity／frame／cadence。没有反汇编、地址／回溯符号化或逆向。

[本次实机证据](evidence/k80-gpu-v265-serial-shot-observed-2026-11-17.json)与[实际串口图像](evidence/images/k80-v265-serial-lockscreen-2026-11-17.png)：20048字节完整、boot／偏移／CRC校验成功，SHA为0ec5d707796b19292a54e5b0b0bf0bec6884e3297a9f185cc0675c03f6197869。关联真实frame64／producer=tail=completed=67／surface96／accessfence67，copy63→64。图像可辨识锁屏约4:02时钟和home indicator；相机210秒可见4:03锁屏、330秒TWRP splash。PNG仅将48x104最近邻放大到384x832，没有生成或补画内容。所选对齐CPU读取和七片传输获得实机证据，不能外推每个framebuffer字节或GPU写像素／物理scanout。

采样窗口内无跨度容量／后端拒绝，成功map648／unmap360，第二客户端4149调用，未采到退出／Close。图片占用7个原观察槽，使末次普通采样更早；这些帧／调用总数不作跨构建FPS比较。Settings长按及真实物理触控场景未实施。

本次主机录像实际为HEVC／libx265：版本文字替换误改libx264，采集成功且真实命令／字节已保存；不把历史重写为H264。下一候选将恢复固定H264并增加编码器不变量检查。后续试验仍须独立固定入口、receiver-first、新scope／ready／claim、300秒WDT／600秒Recovery和零重试。任何未知硬件／DMA状态仍保留资源；不能回Recovery立即停止设备操作。全套GPU已知图像／Metal／显示／FT3683和Settings长按／退出／故障生命周期验收仍未完成；后续不依赖用户查看或操作。

新增工作暂存，不自动额外commit或push。已完成的整理commit仍为8067bd3与434f827；网站EOF本地修复仍待发布及官方重扫。

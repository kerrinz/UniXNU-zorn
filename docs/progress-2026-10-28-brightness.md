# K80 调试低亮度

机主将硬件低亮度插到 Data 保留、全核 CPU、触控之前。目标是降低长时间固定画面的发光强度；不将它描述为消除 OLED 老化风险。GPU 继续后置。

## 真实硬件与实现边界

- 实机 live FDT、recovery cmdline 均选中 `o11_42_02_0a_dsc_cmd`，DSI0 `0x0ae94000/0x1000`、控制器 v2.8。
- 面板亮度走 DCS `0x51`，读取为 `0x52`；O11 的 inverted DBV 配置要求高字节在前。设备树范围 15..16383，初始值 670；数值不是线性的亮度百分比或校准 nits。
- 当前 UEFI 为 SimpleFb，未安装可直接调用的厂商背光实现。首先在 XNU 的 CPU 显示板级适配中接入一次性控制，发生在用户态及 framebuffer 发布之前。UEFI 菜单阶段尚不受此控制。
- 只映射实机确认的 DSI0。固定 FIFO 命令，不使用新的内存 DMA 缓冲，不改面板供电、PHY、时钟、复位、触控或显示合成。
- 写入候选将上限固定为原始值 64；当前值低于此值时不调高。只接受完整两字节 DCS 回复；超时、错误包或写后不一致都保留错误，不能算成功。
- CPU0 单次启动调用；不是通用 DSI 主机，不提供 iPadOS 亮度滑条、自动亮度或休眠唤醒资格。后续 SMP 前须重新确认串行边界。

## 依据

[UniXNU 显示移植说明](https://unixnu.com/porting/display)要求确认真实亮度传输并提供读写；其中 KTZ8866 的 I2C 示例不是 K80 硬件。
本实现依据 [MiCode K80 DSI 驱动固定提交](https://github.com/MiCode/vendor_opensource_display-drivers/tree/3f527f3e55ef27f240507ace3181d13900c3ed7f/msm/dsi) 的寄存器与包格式、
[K80 面板设备树固定提交](https://github.com/MiCode/vendor_qcom_proprietary_display-devicetree/tree/f7f3985271239fa8af013048cb3c95a190e63efd/display)，
并与本机抓取的 FDT 对照。源码文件 URL/SHA 清单保存在忽略目录 `out/zorn/brightness/sources.json`；没有导入整份 Linux 驱动。

## 已验证与待验证

`fb8a8a4e` 于 11:39:53 临时启动，11:40:45 自动回 recovery，新日志及 ready boot/kernel 一致。只读寄存器显示 version=20080000、CTRL=1f5、STATUS=0、TRIG=80000004、LANES=1f1f，ACK/TIMEOUT 均为 0。没有改变亮度。第一段文本受每条 256 字节上限截断，尾部寄存器不能视为已观测；后续已拆分日志。

实际传输头文件的主机模拟检查通过：错误型号/忙状态/ULPS 不发命令，写包字节序和固定目标、只降不升、5ms 有界等待、禁止越界 MMIO、保留无关中断状态、写后读回不符拒绝成功。模拟测试不等于真机成功。

`10b0e5f9` 是 mode2 的 DCS 亮度读取候选，当前仅读取，不发送 `0x51`。真机读出及后续低亮度写回、摄像头可见效果尚待验证。现有 Data overlay 原样保留；不能把短探测当作跨启动 Data 文件保留已通过。

## 调试入口

`build-zorn-debug.py --brightness-mode 1/2/3/4` 分别为寄存器、面板读取、低亮度写后读回、短时降亮验证；缺省 0 关闭。必须使用 CPU 显示配置、新构建内核和独立 watchdog。
mode1/2 使用 `BLSNAP` 自动回收；mode3 的失败检查点为 `BLFAIL`，成功后继续有界系统观察。任何镜像仍只允许固定设备 `92988a43/zorn/b` 的 `fastboot boot`。

`10b0e5f9` 已自动回收新日志：BLGATE secure=0、TPG=0、FIFO=0、split=33531000；BL mode2 err1，未发送任何 DSI 命令。原检查误要求整个 SPLIT_LINK 为零；已按同一厂商源码改为检查 EN bit0（此实测值为关闭），不修改寄存器。主机用例同步采用真实非零初值并测试 EN=1 时拒绝。下一轮仍只读面板亮度。

`8b996c76` 未在旧检查点退出，后续 Data 权限模板在 index40 `/private/var/containers/Temp` 报 ENOENT；亮度结果被覆盖，不能推断读取结果。已将短测结果与回收改为同一有界获取日志写锁的流程。现有 overlay 保留，Data 重启策略仍需单独修正。

`8a453398` 于 12:00:49 启动并正常自动回收，新日志与准确归档通过核对：`BL mode=2 ok=1 err=0 old=307 target=307 got=307 writes=0 int=00100501 ack=0 tout=0 cnt=4 raw=22013337`。DCS 读取真机通过；仍未发送亮度写命令。下一短测目标改为64（不是校准亮度百分比），mode4成功后保留40秒观察并直接回recovery；失败立即回收，不进入用户态。

`e318c99c` 首次写入真机测试失败：DCS命令完成、ACK/TIMEOUT为0，但1ms后 `old=307 target=64 got=307 writes=1 err=8`。自动回收；黑屏照片处在回收过程，不能算低亮度成功。下一候选增加完成状态实际清除检查，且只写一次后在150ms内观察读回，不把传输完成冒充面板生效。20秒摄像头参数被脚本在USB操作前拒绝，已改用允许的30秒；失败参数日志单独保留。

`c15f315c` 加长等待候选在独立watchdog保护下于12:12:08回recovery，但未留下最终BL记录。最后时间10245ms，摄像头为色条/UEFI残留文字；不能据此认定写入成功。XNU `_clock_delay_until_deadline_with_leeway` 在早期idle latency未知时可将IODelay转为thread_block，因此短等待改用CNTFRQ/CNTPCT常速计数器，撤销40秒IOSleep停留；增加读取回复计数清零确认，防止误认旧回复。新候选尚未启动，构建因磁盘不足1GiB在USB操作前被拒绝，正在对旧生成内核做完整解压SHA核对后的无损压缩，锁屏/Data基线和原始手机备份不动。

## 12:19：硬件降亮与新鲜读回通过

`d22986fe`（准确SHA见 evidence/brightness-dim-result.json）于12:18:42定向临时启动并自动回收，新日志/boot/kernel/ready一致。实测 `BL mode=4 ok=1 err=0 old=307 target=64 got=64 writes=1 reads=1 ack=0 tout=0 cnt=4 raw=22004029`。读取前回复计数确实清零，单次写后第一个10ms样本即读到64，错误为0。没有40秒人为停留，Data未进入用户态。硬件DCS降低亮度已通过；未把64/307当作校准光学百分比，未声称UEFI菜单或系统滑条已实现，也没有可用的光学前后对照。常规mode3使用相同传输，成功后继续启动；接下来处理已有Data重复应用首次权限模板的错误。

12:53：eb55ebe5常规mode3也通过：307→64新鲜读回，ACK/TIMEOUT0，机主确认锁屏后手动回recovery；无需再仅引用mode4短测。系统滑条/UEFI菜单仍未适配。

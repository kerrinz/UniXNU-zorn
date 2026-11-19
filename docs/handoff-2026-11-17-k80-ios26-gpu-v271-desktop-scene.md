# K80 iOS26：普通GPU桌面上滑与Settings长按271

271已完成一次无人值守启动、零重试，332.1232秒自动回核验TWRP，7组保护采样一致，BCB尾部保留／完整页读回通过。接收器正常退出0，30普通＋1UI271＋7ROI共83139字节，340秒H264相机成功。实际初始GPU任务／fence2／CRCe843b26a通过；普通backboardd的上滑及长按返回，串口图像出现图标减号和右上完成按钮，符合进入桌面编辑态的表现。尚未验证进入编辑态之后能否正常退出、继续操作；不能据此宣称历史卡死根因已经解决。[完整实机证据](evidence/k80-gpu-v271-desktop-scene-observed-2026-11-17.json)。

![实际271串口ROI，仅最近邻放大](evidence/images/k80-v271-serial-edit-mode-ROI-2026-11-17.png)

## 精确输入及根安装

kernel `f90ba4001c3b32f25f9a7cbf13b5ce1fb76e38b72f4b4016defda54b2ee132b3`；boot `efc1d86d0e8ba12b0443d9b44def00b416c75b1297afe345e4c12fab2d50e846`；boot ID `2073ff1494c64d61a0f63ce88573ceab`。根 `c60b198ded30a982cf96ee9cb66211a8f74c7d8fa80f5b6dd8e0839e121304fc`；ADT `c089535db85a5998f1da010663b7384a921c7417c48af224fa0dc6d94113d1f3`；FD继续复用 `1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab`，启动器不变。[源码／补丁／实际依赖](../patches/gpu/ios26-desktop-scene271/source-manifest.json)。33实际原生对象、1399输入完整链接0undefined，143关键依赖及CPU16KiB／GPU4KiB／磁盘4KiB边界核对通过。

独立根只改两个已有文件：`NativeAdrenoMetal.clients`选择backboardd，既有探针job改为Disabled／非RunAtLoad。签名267探针、Metal frontend／Rust／Turnip完整bundle、568文件及属性监测保持，其固定程序ID `ddb9c8640ab544cd85cae684e0fb8f66`只保留作解码输入，探针本轮不运行。根位置从Data末端独立重算，仍为unixnu相对LBA6291712／32GiB，Data间隔782336字节、末尾保留8588886016字节。完整本地增量重放匹配，25页／9组。

安装最初被自动审批拒绝，认为持久系统写入不属于候选构建授权；当时未执行USB／claim，并撤下准备态。机主随后明确回复“明确批准这次25页根增量安装”。同一精确审核SHA `f76f0756dd294dfde0d94209fe3931784d28ce7ca2eaee6be5d1bba2be94f87d`重新准入后，在核验TWRP内检查7423页实际旧覆盖及全部25页预映像，9组写入／读回聚合 `638016a4683ae9adabca4bc84e3f5c4d68a4a61d1a86c51d6f0397cb3e55e4ca`，保护元数据一致，安装scope未启动系统。之后另建独立boot scope。本轮boot无额外根写入；安装失败／批准／实际收据分开保留，不声称完整32GiB手机读回。历史离线package的未安装／未启动字段不回写，实际部署由独立收据与本次证据记录。

## 实际场景与边界

271不再使用269探针exit0／4关闭就绪条件。实际openingTask的proc名称／unique／PID、初始任务、正常live native客户端及真实245呈现记录共同准入：GPU lease、完成ledger、全部acquire／copy、非零surface GPU access fence必须匹配。单纯CPU surface的fence0不能通过。保持正常Scope／能力拒绝语义，后端失败／CF观测丢失／身份不一致拒绝输入。这只是合成输入门槛，不能授权停止DMA、复位或释放资源。

真实Virtual HID服务复用269上滑，17接触＋抬起返回0，dispatch1289ms；等待30秒后以270实图坐标(28330,3938)长按6次／400ms间隔，再抬起，返回0，dispatch2405ms。均非UI响应延迟或逐事件队列ACK。末次UI phase6／flags1023。ROI来自实际1440×3200面板右上720×1600，frame265／SID299／producer268／access268／completed268，payload SHA `f1c81f7166bacec27aec5379067d53fee98fd2009de89a99109925310667441f`。图像与已完成GPU来源关联，但无已知参考CRC，局部图不能代替全屏／scanout验收。

相机140秒锁屏、180秒桌面，210／240／270秒仍为桌面布局；330秒是红色Recovery过渡文字，不误写成TWRP splash，最终TWRP由实际回收检查确认。相机本轮视野较广、手机较小，图标减号和完成按钮主要由真实串口ROI辨识。静态编辑态没有证明之后仍可交互，未比较CPU／GPU帧率。

backboardd日志9621字节全部已发布／已接收、CRC完整、pending0／gaps0；daemon仍存活，`complete=false`的退出语义正常，不要求伪造probe exit。实际记录2个native客户端：64 CloseReturn16／raw0，129仍live、4336次调用；CF无后端失败／丢失，方法8 Unsupported是能力拒绝。旧census的“probe”说明文字不适用于所选daemon，不能把它作为本轮4客户端关闭等级。

旧紧凑application observer末样本有dropped1，本事实保留；权威CF无丢失。正常GPU来源fence仍从普通样本262推进到ROI268，不能把旧observer的丢失直接说成GPU错误。其try-lock观测丢失可能让271的后续输入门槛永久为false，下一候选需依据真实CF／fence条件区分并显式报告。VM成功map825／unmap305、累计字节4299948032／3627991040，表示正常回收发生，不是无泄漏或live内存用量证明。Metal精度、shadow texture、render-pass split／memoryless backing和attachment-read-in-place等原日志警示保留，不把它们先验归因为卡死。

接收端真实`main`至JSON写入、runner失败／重复claim、相机边界及91个bundle拒绝通过。最初主机夹具把USB VID十进制误写，循环只在显式模拟边界内；测试进程停止、旧夹具保留，修为4617并加入单次发现限制后通过，未因此访问或重启手机。

下一步依据本轮Done区域图像验证有界退出编辑态及Settings继续响应；保持实际GPU／CF失败与未知DMA保护。完整Metal桌面稳定性、跨task、物理FT3683手势／身份／边缘／生命周期仍未验收，目标未完成。17GPU和历史产物保留；只暂存，不额外commit／push。无反汇编、逆向或地址符号化。

机主补充关键复现场景：桌面Settings长按先弹出带Liquid Glass背景的菜单，该菜单可能是历史卡死触发点。此为待验证假设；271约2.4秒hold最终进入编辑态，未单独验收菜单阶段。保留272 Done离线候选，主线转向273较短hold／release、菜单前后真实CPU fence／CF快照与实际ROI／相机观察。不得把Precision提示直接写成已定位的GPU故障，不做反汇编或逆向。

# K80 iOS26 v261：客户端首个错误与关闭阶段日志

v261已完成一次固定有界实机验证：从核验TWRP开始，约333.63秒自动返回同一TWRP，串口39帧／67975字节完整验证，本次240秒无声录像成功。**已进入iOS锁屏／桌面，用户确认滑动、点按、长按、解锁有响应，最终长按“设置”后卡死。GPU与纯CPU路径都低帧率，不作帧率高低比较；GPU路径稳定性仍有问题。完整GPU／Metal／显示／FT3683验收未完成。** [本次观察证据](evidence/k80-gpu-v261-client-failure-observed-2026-11-17.json)。下文离线构建过程及原始creation proof保留其生成时状态。

## 当前问题与源码修改

v260中backboardd首个客户端9次调用后Close成功，第二个客户端3119次调用后Close返回原始`0xe00002ca`（IOReturnIOError）。末个采样是method17 SubmitBatch的`0xe00002c2`（BadArgument）；它不是已证实的第一个错误，也不足以确定关闭失败阶段。没有panic终端包，不能把此次错误归因为旧252的Timeout。

v261在原生Client／Submit／VM／Root／SMMU返回路径连接CPU诊断记录，分别保存首个拒绝与首个后端错误，记录真实关闭阶段。三个新增头为ZornClientFailure261.h、ZornClientFailureStore261.h和ZornClientFailureWire261.h；AppIo.h增加私有CPU token，所有实际消费者已重编。原生返回值、条件、操作数、短路顺序与调用次数由[源码投影检查](../scripts/check-ios26-failure-source.py)核对；Board／HFI／GPU表／执行权／底层Ring正文保持父版本。此检查只检查源码，不分析机器指令。

Root清理旧物理上下文时，日志按已核实且保留的实际客户端所有者归属，临时保存并恢复当前调用方的CPU诊断范围。内部method18仅表示这段Root清理，不增加外部ABI selector；外部仍为1..17。stage160的raw属于ZornSmmuSparse4KStatus，其他记录点的raw为IOReturn。该观察修正不代表已定位v260的根因。

记录器占10264字节驻留CPU存储，单份快照104字节、最多64行、尝试锁失败不阻塞且显式计丢失。正常关闭CPU元数据可回收，失败行保留；记录器不持有或释放GPU资源，不更改原生失败保留规则。串口增加cf字段，置于原有自适应journal之前；原有3072字节帧预算保持，最大值主机夹具3068字节。日志抽样、回收和丢失不能证明所有客户端都被观察。

## 验证与精确构建

当前Store／关闭／上下文／联合退休链分别在ASan／UBSan与TSan下通过；覆盖真实源码方法及明确列出的OS／硬件边界夹具。真实进度帧生成器通过暖机、确认点、worker／服务创建、超时和生命周期检查；解码器通过实际生成帧与20个合成变异拒绝检查。固件认证、MMIO、DMA、GPU执行和真实显示不由这些夹具证明。所有sanitizer关闭符号化，未使用反汇编或逆向。

原生CPU页为16KiB，GPU与磁盘页独立为4KiB；118项有效头引用核对，实际编译器验证5个记录／panic消费者与当前ID一致，并拒绝父版本覆盖层。14份补丁零fuzz重放字节相同。独立完整启动包FAT成员逐项读回、payload重组及原源码file／section元数据consumer通过，仅替换kernel。

- kernel：`fd74f710a949b40d1f7076e534d2836106aa140bf45e7365fecf718a9c4de90f`。
- boot：`0e2b7278b8d5cd54121f11add6a71cf02628d1411620f9e404d2a32b950b7596`。
- root：`859c7ebae6355ef7e089896680b0b8ffd9a03af8a1f078918feec740b7a06b02`，复用已安装252根、运行只读。
- FD：`1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab`；ADT：`98f04ff54b9573ddaa2c4716da0e954fae8192d15b1f105426eba7f216805936`。
- 启动ID：`186b81acea5f4a5b8424a1d8fded3eae`；禁用探针ID：`f80eb1403d7e4f958b5eddacb49d98d0`。

[源码来源与精确补丁](../patches/gpu/ios26-client-failure261/source-manifest.json)、[离线证据](evidence/k80-gpu-v261-client-failure-offline-2026-11-17.json)。源码为/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v261-client-failure-186b81acea5f4a5b8424a1d8fded3eae；构建为/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v261-client-failure-186b81acea5f4a5b8424a1d8fded3eae。沿用[官方适配记录](https://unixnu.com/zh/porting/records)区分源码／主机／设备证据。保持本地已核验houji26输入与K80资源，不将网站新增OS profile当成本次26输入。

## 下一步与保护

完成新的固定入口和接收器准入检查后，准备一次300秒独立WDT／600秒有界自动Recovery回归，先确认实际首个错误、关闭阶段和日志归属。新camera路径必须使用已验证能枚举USB Camera的完整权限环境；[本机相机复核](evidence/k80-camera-host-recheck-2026-11-16.json)仅证明摄像头可用，旧v260录像失败记录保留。

Android／Recovery／iPadOS17／Data／原根和旧产物保持，无新根或存储布局写入。本候选尚未部署，不证明正常退出、真实并发隔离、每帧GPU写入及显示或FT3683完整触点与手势通过。没有新commit或push。

## v261实机观察与下一步（2026-11-17）

精确kernel／boot／FD／ADT／根与上文一致，一次启动、零重试，消费独立261 scope／ready／claim。scope实值为`single-K80-ios26-gpu-v261-client-failure-300s-81683386`；名称末八位沿用父版本标签，但完整scope含独立261版本，nonce／启动ID／独立归档路径均为当前186b81…，未复用260claim。七组受保护抽样逐字节相等，BCB完整页读回与尾部保护通过。当前设备状态idle、stop=false；未重新发起设备操作。

早期CPU done=1、在线8核／mask ff；真实初始化记录state3／smr88／point6／ack6／failed0／publication0x100000000。backboardd PID／unique10：第一个客户端9次调用后Close0；第二个客户端在采样末尾3325次调用，**未观察到其Close返回或进程退出**，不能将v260的CloseIOError移植到此次。新增诊断client129记录第一个后端错误为sequence11／stage10(run)／method3(BoMap)／raw`0xe00002be`（kIOReturnNoResources）；内部具体拒绝分支仍未知。同一客户端首个reject为method8 GetStatus Unsupported，它不是已证实的渲染错误。诊断dropped／recycled均0，但只抽样到一个有错误的客户端行，不能声称覆盖所有对象。

最新surface记录frame59／1125×2436／producer和completed fence63，匹配GPU访问完成、acquire／CPU copy账本通过，仍无直接GPU写入／物理scanout证明。完整journal收到9621字节／62条、gaps0／pending0、未见exit；旧紧凑stderr仍drop59。串口正常窗口只覆盖既有120秒poll循环，录像后段与用户长按卡死可能在其后，不能凭现有采样证明最终GPU／UI仍健康或定位最终卡死点。下一候选应在保持既有总字节／帧／panic预算及看门狗的条件下覆盖后期，并在真实BoMap／VM预检边界捕获容量与原始失败，不直接增大4096容量或改变返回值。

录像640×360、240秒、无音频、41191742字节，SHA256为`f284b3da472595df944afd9d215a6ebd98870132bb3da4ad16769e3d1bcfff45`，已查看8／95／210秒帧；后段可见系统图标界面但文字模糊，未凭此认定已知图像或逐帧GPU写入正确。用户交互观察作为本次部分功能证据，触点ID、边缘、多点、抬起与失败生命周期仍需独立验收。当前调试重点为低帧率下的稳定性与长按设置卡死，不比较CPU／GPU帧率，不进行无证据调频。

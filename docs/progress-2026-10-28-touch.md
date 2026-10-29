# K80 FT3683 触控接入（2026-10-28）

机主已回到手机旁，确认低亮度锁屏可见、触摸无响应。本阶段按新指令优先触控，CPU0 保持，多核和 GPU 后置。后台 heartbeat 保持 PAUSED；当前由会话进行有界单轮测试。

## 已验证

- recovery 实测触控为 FocalTech FT3683，芯片 ID `3683`，驱动 `V3.4 20241129`，固件版本文本 `35`。它不是 houji 的 Synaptics S3910，不能复用 TouchCom 报文。
- 真实 DT：SE `0xa90000` / SPI mode 0 / 15 MHz 上限；MISO/MOSI/CLK/CS 为 GPIO48/49/50/51，reset161、IRQ162。
- AVDD 是 `ldob14` / 3.2 V；IOVDD 是 `ldob12` / 1.8 V。houji 的 AVDD L9 / 3.0 V 不适用于 zorn。
- 最大 10 个触点，Linux 使用 100 倍坐标精度，面板为 1440×3200。原生 FT 帧布局尚未从 K80 真机验证，不能直接假定为普通 6 字节触点格式。
- live FDT SHA256：`8c3712d8850a3eba0c53d266ea96268f3b908975cabe9e866bcf991dbcc8382a`。

`483919ab` 于 13:13:26 临时启动，13:14:18 自动回 recovery；新日志、boot/kernel/ready 归档一致。只读 25 次寄存器读取得 `TOUCHRO rc=1`：SE 时钟 halt；六个 GPIO 都为 `cfg=1, in=0`。探针按设计未读取断钟的 SE，也没有 GPIO/控制器/亮度写入。当前尚未在 XNU 读到触控芯片 ID，更没有触点或 HID 事件证据。

详见 [本轮证据](evidence/touch-handoff-readonly-result.json)。

## 正在实现

新 UEFI `ZORNTPWR` marker 显式选择原生 RPMh + Clock 电源/时钟交接。独立 watchdog 先启动；查询全部资源和版本后才发出两路准确电压/HPM/enable 请求。失败返回 recovery，不直接操作 PMIC、不写触控固件。默认无 marker 的镜像不启用此路径。

真实 giulia 的 RPMh/CmdDb/Clock PE 完整 SHA 与函数表已核对；实际头文件通过 ASan/UBSan 宿主 mock：空/错误 marker、精确六次电源 vote、重复调用、每个接口失败、错误资源/版本/缺方法均验证。新 FD `05b8b30b` 已构建，并在 `7ce0e293` 完成真机交接测试。这些宿主检查不代表电源或触控已在硬件工作。

后续按官网顺序：供电/时钟交接 → 空闲总线/引脚所有权 → 限定读命令和 CRC 的 FT3683 ID → 真实触点帧 → 当前 17.7.11 IOHIDFamily ABI 及 HID 发布 → 机主轻触/滑动验证。不会凭设备注册或计数器递增宣称触摸可用。

## 已有成果及边界

`eb55ebe5` 首次跨启动读到 DKEEP2 / cookie `2c59d71a`，原 Data 初始化标志保留；该轮低亮度 307→64、读回64且机主确认锁屏。机主手动回 recovery，因此该轮不作自动回收资格。

紧接的同镜像第二次复测在亮度交接资格检查提前拒绝，写0/读0，并自动回 recovery；未到 Data，第二次跨启动资格尚未通过。未重置 overlay，也未放宽亮度保护。新只读触控探针额外记录全部 DSI 交接条件，供后续定位这一差异。

OS/SystemOS 仍只读；已有受限 Data overlay、单4KiB日志、保留尾部的 misc BCB 规则不变。只对 `92988a43/zorn/b` 临时启动；不启动 Android、不刷分区、不改槽、不提交 Git。

## 来源

- [UniXNU 官方输入驱动流程](https://unixnu.com/porting/input)
- 本地 `UniXNU-houji/native/touch` 和 `uefi/Platforms/Xiaomi/houjiPkg/Application/HoujiStorageProbe/TouchHandoff.h`，仅参考资源交接、GPIO SPI 与有界测试方法。
- 本地 MiCode `bsp-zorn-v-oss` 的 SM8650 GCC/pinctrl 实现，以及本机 recovery 的真实 FT3683 信息。


## 13:24 原生电源/时钟交接真机通过；机主带走手机后转离线

`7ce0e293` 于13:24:01临时启动，13:24:52自动回 recovery，boot/kernel/ready及新日志匹配。
读32次得到 `TOUCHRO rc=0`，SE branch `00004000`（halt清除）、vote `463c0200`，
SE `102/1/0/1/0/0/0`：SPI协议1，状态空闲、FIFO空、DMA接口未启用。六个GPIO仍是cfg1，尚未驱动触控。
[证据](evidence/touch-power-handoff-result.json)。这证明路径完成且时钟可读，不等于已测量电源轨电压或读到芯片ID。

机主随后带走手机，明确改为离线开发＋自行回传日志。本会话没有再次USB操作或启动；heartbeat继续PAUSED。
新 `bce3bdbe` 增加受限GPIO SPI身份读取：检查GPI/引脚所有权，设置六针并复位控制器，只允许A3/9F/A6读，校验CRC/状态，每条至多三次，保留原始响应，恢复GPIO后自动回收。没有升级触控固件，没有修改OS/SystemOS/Data。
实际编译、所有既有ABI审计、宿主报文/故障测试、真实调用链、ready完整归档及离线启动脚本检查均通过。**该新镜像仅构建，未上机，不是可用触摸驱动。**

下一步由机主运行[测试与日志回传说明](touch-test-instructions.md)，取得匹配的新ID响应后，再确认K80真实触点格式并接入当前系统的HID ABI。保留错误，不以外机型号或纯HID注册代替物理事件证据。

## Windows 离线交付（2026-10-28 14:23）

机主使用另一台 Windows 电脑且已有 adb/fastboot，新增纯 PowerShell 测试包，无 Python 依赖。固定 bce3bdbe 候选与 ee6681fd recovery bootstrap；从 recovery/fastboot 开始均先校验序号、产品、b槽及镜像 SHA。BCB 首4KiB 备份、864字节修改范围、尾部保留及完整读回沿用开发机流程；只定向临时启动。日志通过 adb pull 原样保存，比较启动前后 SHA，独立采集明确标为未绑定轮次。自动回收有界，不自动反复重启。

包：`out/zorn/touch-return/K80-touch-bce3bdbe-windows.zip`，操作见 [触控测试说明](touch-test-instructions.md)。PowerShell tree-sitter 语法检查、固定 boot/kernel/bootstrap 哈希及 ready 状态、ZIP CRC 和解压成员哈希均通过。没有 PowerShell 运行时或 Windows USB 真机端到端验证；不把静态检查写成运行成功。验证记录见 [Windows 包证据](evidence/touch-windows-package.json)。

本轮未访问手机，未新增触控芯片识别/HID/触摸成功证据。等待机主回传新生成的日志 ZIP；保持 heartbeat 暂停。

## 19:53 FT3683 芯片通信真机通过

机主接回手机并指定优先触摸、多核 CPU。原 bce3bdbe 镜像于19:51进入受控引导流程，19:53:46自动回 recovery；本轮新日志、boot/kernel/ready哈希匹配。返回 `TOUCHID err=0 id=3683 fw=35 match=1 count=3 restored=1`，A3/9F/A6均首次读成功、状态/CRC通过，GPIO恢复校验通过。见[本轮证据](evidence/touch-identify-result.json)。本结果证明总线通信，尚不代表触点或 HID 可用。

机主配合 recovery 轻触/滑动时，原厂 sysfs 导出的缓存帧仍全FF且未更新，并伴随 bad-count 导出告警；不将该接口作为触点格式依据。下一步使用已验证的 XNU GPIO SPI 路径，20秒有界读取 0x01/84字节原始帧、校验CRC、保存首/末变化与IRQ计数后恢复GPIO并自动回收。只采集真实报文，尚不发布HID。CPU0保持，多核为下一优先级。

## 20:04 原始触点采集候选已构建，尚未上机

`2ef2d650`：boot SHA `2ef2d650f1f8c77160239247afc390de7f77b9712403e973bda2aa2d649e59a3`，kernel SHA `eb11c7b8fc1eb705002fd72d87792e54ad116325dc5f016ef485b69981217df4`。`--touch-frames` 要求 ID/原生供电/独立 watchdog，导出 `zorn_touch=3`；确认芯片后只执行 0x01/84字节读取，最多20秒/200次，保留错误/CRC/IRQ及原始首末帧，恢复GPIO后走原受限日志与recovery。没有控制器配置或固件写命令。

84个逐字节CRC损坏、状态/传输/全FF响应、有界重试、实际744位GPIO时序宿主ASan/UBSan测试通过，原ID测试继续通过。完整构建/ready归档和最终实际链接到帧探针及日志回收入口通过。第一次沙箱构建被sysctl权限中断，补回因中断缺失的生成对象后，以完整构建器重跑通过；失败输出与成功输出保留在 out。

`20261028-200442-2ef2d650` 在准备并读回BCB后，recovery重启又回recovery，30秒内未见fastboot。runner明确failed，**新镜像没有启动，也没有新触点结果**。手机仍可通过recovery adb连接，已请机主物理切到fastboot；不反复自动重启，不启动Android。

HID离线预核对：K80实际预链接IOHIDFamily完整指令SHA与官方17.7.11参考一致，207槽对象、208字节实例、原构造/析构thunk、报告描述符slot180与handleReport slot181均独立检查通过。见[HID ABI预检查](evidence/touch-hid-abi-precheck.json)。这还不是HID设备注册或触摸报告成功。

编译空间通过有完整SHA往返验证的归档存储调整恢复；缓存符号文件现为 `out/zorn/gui-symbols/dyld_shared_cache_arm64.symbols.gz`，后续使用前须 `gzip -dk` 恢复，原版符号SHA保留。没有删除手机备份、IPSW或启动基线。

## 20:41 完整 THP 帧与可见触屏提示真机通过

`2ef2d650` 两轮自动回收，分别170/171帧且CRC失败0；首末报文为A55F头，不能当作标准6/8字节触点包。旧TWAIT仅写日志，机主无法看到，后续已修正为通过受限GOP映射绘制大字 TOUCH NOW。

`5e842c32` 于20:40:51启动、自动回recovery，82帧CRC全通过；机主确认看到提示，并在约(x=1/4,y=3/4)保持触摸直到重启。新格式ZORNLOGC仅重排原有同一个4KiB日志块：64条checkpoint、元数据及3120字节完整帧，固定日志LBA不变，保存与回收均未访问额外分区。完整帧已由新版reader验证CRC并导出 `checkpoints.touch.bin`。见[完整帧证据](evidence/touch-full-result.json)。

真实FDT进一步确认 `focaltech,tx-num=40`、`rx-num=18`。recovery自带touch_report与O11_THP/FT3683处理库，完整数据中存在原始互容矩阵；不把自主帧计数变化认定为触点，也不将该库作为已移植或已开源的模块。研究读取均为只读，临时ramdisk提取副本已释放，保留选定私有输入和来源哈希，不提交到Git。

下一步在同一次启动内取得无手指基线，再与机主按住期间的矩阵比较，核对变化位置与方向；之后才接入经核对的17.7.11 HID接口。仍是CPU0，多核第二优先级。

## 20:52 同启动基线差分已定位真实手指信号

`7d332caf` 两轮各82帧CRC全通过、8份无触摸基线；机主确认提示出现后按住，后补充澄清：前一配对样本为左侧1/4、高度3/4，最新一轮为左侧1/4、上下中央。原始互容矩阵的线性排列为RX优先（18组、每组40个TX），物理纵轴与TX方向相反。强信号峰由约TX12移动至TX20。

开放的实验性差分/连通域跟踪器在这两份真实采样上各识别一个触点，归一化位置分别约(0.237,0.706)、(0.268,0.471)，与机主大致位置及移动方向相符。已提高最小强度门限，过滤首版算法出现的低强度干扰点；合成噪声/移动/抬起/双边缘触点通过ASan/UBSan。见[跟踪器检查](evidence/touch-contacts-host-check.json)。这不证明原厂精度、复杂环境、多点或系统HID已可用。

正在集成仅显式启用的运行态：严格FT3683/固件35识别、GPIO所有权、基线、有限错误后释放、正常原版IOHIDDevice报告和低亮度GUI。新增HID适配层完整原版指令/207槽/208字节对象及全部引用逐项核对通过。硬件会话构造延后到显示发布后，编译审计拒绝板级探针出现早期全局构造函数。常规短测与旧GUI配置不隐式启用该层。运行态GUI真机仍待测试，多核保持下一优先级。


## 21:42 运行态首轮未到 GUI，新增独立触控记录

`dcff9903` 于21:18启动、21:29:39自动回recovery；本轮日志确实变化且镜像与归档内核哈希匹配。机主观察到色条。620988ms末段显示设备发布成功，但无选定GUI进程、无显示客户端/传帧；不能据此认定触点算法或HID报告成功。原TCH文字已被系统调用文本覆盖，缺少初始化阶段证据。

`52b24acd` 仅构建未启动，随后由带固定触控记录的 `ece3d0e8` 替代。新格式ZORNLOGD/v16：84条文本、3072字节footer（含12字触控状态），总长仍4096，固定日志LBA不变；保留所有旧日志解码。C布局与Python往返、非法元数据、133份历史日志、真实ring1000次覆盖不破坏footer及原始采集格式均通过。XNU生成/导出头与设备头一致。HID原版完整指令保持不变，实际晚期探针→运行态→HID调用、延后构造与工作线程优先级20逐项审计通过。

新短测21:42定向临时启动，180秒GUI窗口/420秒host上限，独立watchdog、低亮度64、原Data overlay保持。轮询从原81优先级/10ms休眠改为20/100ms，是调度干扰的有界对照，尚未证实因果；需新日志确定是否进入轮询、HID发布或其他路径。多核仍未启用。


## 21:47 低优先级运行态与原版 HID EventDriver 真机通过

`ece3d0e8` 已自动回recovery，run=recovered、kernel_log_changed=true；完整boot及归档kernel SHA与该轮manifest匹配。新独立footer记录：尝试130次，解码129帧，传输/CRC错误0，空闲峰85/噪声11，HID发布阶段5且原版IOHIDEventDriver已发现。计数是独立对齐字段，允许正处于下一帧时读取，不能把130/129差1算成丢帧。未要求本轮触摸，contacts/reports为0，不是触摸失败或成功的证据。

201785ms保留样本已有lsd、SpringBoard、backboardd，显示accepted6、完成传帧5、末错误0。相较旧81/10ms轮次恢复了GUI进度，支持存在调度干扰；同时新增记录，不能仅凭两轮就声称唯一根因。启动长窗口实际触摸验证前，先完成构建与原版HID指令/实际调用检查。见[运行态证据](evidence/touch-runtime-result.json)。


## 22:03 锁屏已恢复，HID 报告有成功返回，触摸仍无界面响应

长窗口 `d31ceca5` 于22:02:11自动回recovery。机主确认锁屏、小白条，但多次触摸无响应，并完成约10秒中央长按和10秒慢滑。新日志和对应boot/kernel归档哈希匹配；620136ms记录142次读取、141帧解码、错误0、历史坐标(8108,18151)，原版IOHIDEventDriver存在，4次handleReport且末返回0。显示完成34帧。此结果只证明检测历史与报告提交，尚不证明这些坐标完整对应中央长按，也不证明HID事件到UIKit；不宣称触控完成。

priority20候选在600秒内约0.23次读取/秒，采样稀疏；边缘手势标记尚未接入，也是独立待查项。下一候选使用1504字节（64字节头+720个uint16）只读矩阵命令，旧3120字节完整采集保留；CRC/状态、3次有界重试及1504处损坏、12104位实际GPIO位序宿主检查通过。运行态改为BASEPRI_DEFAULT31/100ms，新增报告前stage7记录。物理1504长度与实际采样率仍待180秒短测。

长/短两份内核全SHA不同；逐字节复核79字节差异仅为LC_UUID、N_OSO调试对象mtime与PrelinkKCID，规范化后所有指令和运行态数据相同。两轮仍各用自己的完整哈希绑定，未混用内核解析结果。新实际链接调用审计已加入构建器，失败则不生成ready归档。


## 22:27 持续采样恢复，触摸仍无界面响应；转入八核优先

`d2c17be2` 已自动回recovery，镜像/归档内核、新日志及实际reader哈希匹配。每8个wire字节在CS有效、时钟低时IOSleep(1)，帧间100ms，priority81。318811ms快照已有759帧解码/传输错误0、历史坐标(18377,14094)、IOHIDEventDriver存在、220次handleReport提交且末次返回0。之前每次返回未全部单独保留，不能称220次都成功。机主仍报告无响应；采样改进不等于事件已到UIKit，不能把剩余问题全归咎于单核卡顿。见[受控让出结果](evidence/touch-cooperative-result.json)。

尚未上机的边缘事件适配已做离线编译、当前原版构造函数/220槽EventDriver和37槽Event方法边界核对及纯策略ASan/UBSan检查，使用本设备独立分发表副本。--touch-edges显式启用，默认关闭；没有硬件手势成功证据。为按机主最新要求优先八核，保存该候选，不在本轮继续启动触控镜像。v16日志格式保持，无未完成的v17协议变更。

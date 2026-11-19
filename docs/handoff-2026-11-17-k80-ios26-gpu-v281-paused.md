# K80 iOS26 GPU：281 暂停交接（2026-11-17）

## 接手先读

这是供其他 Agent 续接的状态交接，不是硬件验收报告。**目标状态为 paused**；本次只生成交接和按机主要求清理重复镜像，没有恢复 GPU 调试。若新会话明确要求续接，可继续已授权的离线工程工作；不要因本文件自行启动设备。

完整目标仍是 Redmi K80／zorn／SM8650／Adreno750v2（Gen7.9.1）的 iOS26 GPU、Metal、显示呈现、FT3683 触控及正常／失败生命周期的精确构建实机验收，**未完成**。不能把281离线构建、原267／268的棋盘成功或277手动体验当作新栈最终验收。

当前最新候选是 **281：新上游 Metal/runtime/Turnip 的有界已知图像测试**。完整根、内核、启动包、根增量审核与主机回归已形成；**未安装、未启动，没有281实机或FPS结果**。固定根安装入口已增加281范围，但281的系统启动入口／receiver／camera／bundle／ready／claim尚未接好。

先读本文件和[当前状态快照](evidence/handoff-2026-11-17-k80-ios26-gpu-v281-paused.json)，再读[280交接](handoff-2026-11-17-k80-ios26-gpu-v280-upstream-stack.md)、[279交接](handoff-2026-11-17-k80-ios26-gpu-v279-upstream-runtime.md)、[277真实手动观察](handoff-2026-11-17-k80-ios26-gpu-v277-manual-acceptance.md)、[AGENTS.md](../AGENTS.md)及[权威记录](../porting.toml)。根记录目前主要更新到280，281尚未完成公开记录整理。

## 不可突破的约束

- **严禁反汇编、逆向工程、指令重写、地址／回溯符号化和Apple shader二进制分析。** 仅正常开源源码阅读／编译／链接／签名、哈希、文件头／版本／文件系统格式检查。导入核对沿用`llvm-nm -u`，不做正符号枚举或指令查看。
- 新上游默认Metal构建器会执行`rust-pac-rewrite.py`和unsigned-pointer shim；**不得运行该路线**。279沿用已验证的原生Rust arm64e/PAC工具链和参数，保留其实际命令。
- 只维护`UniXNU-zorn`和`uefi-zorn`，不碰`_副本`。不混用17／26对象，不照搬sheng／houji板级参数，不切HWSCHED，不把HFI存在解释为提交模式选择。
- 保留 Android、Data、iPadOS17、GPT、Recovery、槽位和真实验收基线。运行时OS/SystemOS只读，var为既有RAMFS。CPU页16KiB、GPU页4KiB、磁盘块4KiB、签名页4KiB各自区分。
- 仅92988a43／zorn／slot a；CC9 f85d4270禁止操作。既有SDK37私有ADB5039、固定工具、核验Recovery、receiver-first、fresh scope／owner／ready／claim、单次临时boot、零重试、独立300秒WDT和600秒核验Recovery返回仍有效。不得自行bootstrap、刷机恢复或扩大范围；不能回Recovery立即停止设备操作并保留证据。
- 不依赖人工按键、触屏、插拔或拍照。相机可在合格设备尝试中辅助观察，但不能替代Recovery／日志／存储保护检查。
- GPU执行／DMA是否停止不明时停止后续操作，保留对应资源；正常完成按真实生命周期释放，不把失败保留扩大成全部对象永久不释放。
- 用户要求：**只在明确要求时生成commit**；本轮不commit／push。现有HEAD曾被用户回调，勿reset、rebase、checkout覆盖工作区，也不要`git add -A`卷入未选用276工作。

## 持久路径与精确产物

项目根：`/Volumes/macData/projects/ios-zorn`。

281构建目录（下文B281）：

```text
/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v281-upstream-known-image-36e4614944b04a64bee5499cb2e8338f
```

281平台源码（S281）：

```text
/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v281-upstream-known-image-36e4614944b04a64bee5499cb2e8338f
```

281根增量审核（D281）：

```text
/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-known281-root-delta-review-36e46149
```

同一`build/ios-26.6.2-23G90/`目录下：B280为`k80-gpu-v280-upstream-turnip-434fe1f2f3be4ee89e7166d9b61cf1d9`；B279为`k80-gpu-v279-upstream-runtime-c06c80df1b754ba1aef8c3ec6b050ca9`。完整Rust构建配方是`B279/rust-build/command279.json`，当前新栈bundle／Turnip配方及源码清单在B280，281保留它们。

`/tmp/zorn-v281-path`、`/tmp/zorn-s281-path`、`/tmp/zorn-v281-delta-review`只是便捷指针，可能随重启丢失；以以上持久目录为准。

- boot tag：`36e4614944b04a64bee5499cb2e8338f`。
- 保留的267探针program tag：`ddb9c8640ab544cd85cae684e0fb8f66`，**不能拿boot tag代替程序ID**。
- 最终内核：`full-link/kernel.ZORN26-KNOWN281.UNSELECTED.macho`，SHA256 **`d1e3e7ff3f80e44060b0e5a5b0e86169aef39a9dbdb73de09ca1153ee38ef2ee`**。
- 最终boot：`boot-package/boot.ZORN26-GPU-V281-KNOWN-UNSELECTED.img`，11862016字节，SHA256 **`1d9e57e149139a53d9fcbdf5dad29cba745b3556b662741e5b0b42ab93204245`**。
- 根：`root-candidate/ios26-root-known-image281.UNSELECTED.hfsx`，34359738368字节，SHA256 **`b87e132bbf509d13ff3475606abef000a1f43478ad4889bdcfbf47eb0db39e8d`**。
- ADT：SHA256 `9aaa913f7861164c84cac130f6906f7b155528904ab69e0686a81e5e072bdfc6`。只更换chosen的root-image-sha256，其他字节通过反向恢复对照。
- 原FD：`1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab`。
- 原loader：`ccae7c1d2d7934812a5668c9b33c409ae3850d21aa20999259d592a533b021d8`。
- 原manager：`ff9c6d7ed60b8d93976a736422cbfd2a4200f44c9cee0e3cd3a211a7cd19ae49`。

本次交接重新计算了最终kernel／boot／FD／ADT哈希；随后镜像清理又实时计算了保留281主根与其重复重放镜像的完整SHA，两者均为b87e132b…，才删除重复副本。没有手机全根读回。

## 279／280新栈与真实ABI

独立上游参考：`UniXNU-upstream-630b85a307f1`，官方commit `630b85a307f19c8d8a4699d5bfc12f6796b874aa`。旧`UniXNU/main`仍为627c932a及其本地修改；origin/main已更新，**不要盲目pull／reset旧脏树**。此次上游来源按完整Git树逐文件核验，历史更新细节见[上游更新说明](upstream-refresh-2026-11-17.md)。

选中源码：

- AdrenoMetal：`8c7f9502de593c04a1003690f4a9441fe88551e8`，`references/upstream-20261117/AdrenoMetal-8c7f9502de59`。
- metal2vulkan development：`46e7cc96a284150bdf19b4a6a7890b0a8bc0ef71`，`references/upstream-20261117/metal2vulkan-46e7cc96a284`，加官方0063 consumer patch。这是逐Git blob验证的编译源码闭包，未导入约1.9GB观测corpus。
- Mesa：`85fda3b36405bcaea8bffc64aa4f2651dc90770d`，tree `b72ff1eb2138026ed6aba524770899faabf7d7c8`，加官方24个有序补丁和K80适配。实际源码为`source/graphics/turnip-upstream280-434fe1f2f3be4ee89e7166d9b61cf1d9`。
- 新Adreno740 `1c9029bc3216a39d9e514ba41dee12e95e8f3598`只是参考；没有把A740／SM8550内核替换为K80后端。

279实际修复了iOS Mach源路径：使用公开`vm_read_overwrite`／`vm_region_64`，避免iOS落入缺函数或恒false写权限fallback。no-copy接回已有有界VM身份walker。实际Rust archive SHA `83705f5f82273c927277227bc6c06105fd5eedac499f96e58ee1a20f1714c506`；使用原生nightly-20261103 arm64e/PAC目标和`-Zpointer-authentication=+calls,+return-addresses,+auth-traps,+intrinsics`。具体工具链、Clang resource目录、SDK27／部署目标iOS26和离线vendor由279实际命令绑定。

280完整bundle是`B280/metal-plugin/NativeAdrenoMetal.bundle`；281原样保留该bundle。Turnip SHA `6a72c7da534a1d7df2c8beac7724cb4d20f9776d45eb946649233859747f8dde`。保留WriteCombine和实际ABI-v1：旧Submit416字节／16IB，扩展SubmitBatch3104字节／128IB／selector17，flag2是SubmitBatch。上游v2的selector17是SetPriority，flag2是OwnedCoherent，**不能换头或混发**。unsupported priority／note返回false且不发v2请求，不是伪造成功后端。

保留上游进程级IOVA、缓存／回收锁竞争修复、早清BO槽、pipeline共享和command-buffer边界切分。K80故障仍device-lost，不假设v2自动复位／重放成立。新transient／memoryless／GMEM行为即使TU_DEBUG=sysmem也可能进入GMEM，尚待Gen7.9.1实测。未选用macOS Aqua缓存代理、HWSCHED或上游默认指令重写配方。性能提升未成立。

## 281做了什么

281继承280真实GPU／VM／ring／SMMU／时钟／固件／共享成员和退出后端，使用旧267的同OS真实Metal探针。探针执行device发现、library／pipeline、GPU渲染、IOSurface poison／逐像素／CRC718ed2ce校验、两个真实共享Query／Close、120次有界呈现及退出；**此处只复用程序，不能复用旧实机成功结论**。

根从离线280克隆，只恢复两个既有文件的原267策略：`NativeAdrenoMetal.clients`选择`zorn-metal-probe193`；既有launchd job启用RunAtLoad、取消Disabled、KeepAlive仍false。探针二进制、整个新Metal bundle和其他监测文件／UID/GID／mode／inode保持。签名、HFS检查通过，原280根哈希／元数据复核不变。

平台只更换root／boot身份、探针stderr及journal筛选、已验证268的串口／早期观察路径和整屏265缩略图。保留280 presenter的CPU计时调用。`ZornUiSceneService269.o`这次不链接，避免桌面观察线程介入已知图像阶段；没有删除物理FT3683后端。三项仅属于该未选用线程的HID头依赖不再要求出现在32个替换单元中，依据保存在`unselected-worker-header-scope281.json`；其他128项实际关键头依赖仍逐个核对。

新修复：旧缩略图仅以frame>=64为门槛，可能采到先出现的CPU锁屏。现在先取得`zornKnownPresent247.complete(record)`的真实成功返回，只有当前frame／SID完成源定义known-present、真实acquire／show返回且原捕获条件满足才采样。不新增GPU任务、Surface所有权或DMA操作。

[测试适配器](../scripts/check-ios26-known-presenter281.py)复用原presenter测试并编译实际KnownPresent247／Shot265类：未arm、错误SID、错误frame均不捕获；仅匹配完成帧捕获测试进程自己的合成像素。ASan／UBSan／TSan通过。旧门槛源码确实被新回归触发错误捕获并拒绝，见`legacy-capture-gate-negative281/result.json`。这些不是GPU／physical scanout证明。

最终受影响对象已重新编译，完整链接1398输入、32个native替换对象、零undefined；实际CPU16KiB宏、128项头依赖和5消费者的record／panic身份预处理及stale-VFS拒绝通过。测试中的`PASS278`／`PASS280`文案来自复用工具，不代表旧对象混入；以收据的actual source／hash／plan路径为准。

## 根增量与安装入口

**280从未安装。** 当前手机期望根仍为271的`c60b198ded30a982cf96ee9cb66211a8f74c7d8fa80f5b6dd8e0839e121304fc`。281构建父根是离线280的d9856b43，但安装差异必须直接 **271 c60b198d → 281 b87e132b**，不要先装280，也不要拿280的安装scope／ready替代281。

B281的`root-candidate/install-base281.json`明确区分组合父根和安装基线。直接全镜像比对得到11897个4KiB页／48730112字节／227组，每组最多65页；独立本地重放的完整镜像SHA等于b87e132b，写入组汇总读回SHA为`0f4fa912db5f8be69e6dd484b9df0d8cac77fac7ed713ca401ec7d8e31be49bd`。Data／log重叠、越界、未对齐、最后前像不符时零写入、首组读回错误停止后续组均通过。

D281保留实际271及更早安装已读回的7441页／170组，并与当前本地c60b198d基线逐字核对。安装前仍必须重新读取这些页面和全部新前像；历史读回不是新的手机观察。审核SHA：**`680b0ec4db336248fcdfe402958bb63a22e03f8262d19d3e624bd2efa1c7fe94`**。

固定安装入口已增加`--ios26-known281-root-delta`，`--check`实际通过；`D281/plan-adapter-host281/result.json`通过实际计划拒绝及原Recovery适配器的本地成功／失败路径。当前`D281/admission`不存在，无owner／ready／claim／安装。

280期间修复了通用安装入口的顺序问题：纯主机5039监听检查移到claim／目录／状态修改之前，监听缺失不消耗安装claim，也不bootstrap或发送ADB请求。后续真实Recovery仍需原完整校验；未知／部分写入必须停止设备操作。仅曾有机主针对271的25页增量作过明确批准，不能把那份收据／旧准入当作281的收据／新准入；新操作按用户现有总授权、具体审核及实际审批结果处理，不反复确认已授权离线工程。

下面仅是**获准续接后的离线检查示例**，不是设备执行指令：

```sh
cd /Volumes/macData/projects/ios-zorn
python3 UniXNU-zorn/scripts/run-zorn-debug.py \
  --ios26-known281-root-delta \
  /Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-known281-root-delta-review-36e46149/review-inputs.json \
  --check
```

不要在当前暂停状态执行安装、添加admission或开始boot。

## 设备与最后实机证据

交接读取`out/zorn/unattended-active/current.json`：active_run／active_admission／active_build／runner_session为空，stop_device_operations=false；GPU模式仍unattended-phone-connected，但allow_boot=false／allow_readback=false。这不是新Recovery或在线设备证明。本Agent最后启动的主机检查84172已exit0，其余已知构建／测试也已结束；接手仍须重新检查实时busy状态。

最后主机连接观察在`B280/host-listener5039-availability280.json`：提升权限的本机lsof未报告5039监听。没有运行ADB、启动服务器、USB或手机命令。278原receiver曾在claim前因监听不可达拒绝；失败归档不覆盖、不重跑。没有新的Recovery观察；不要因“有真机连接模式”就假设现在可操作手机。

最后真实手机尝试是277：单次／零重试，约333.48秒自动回核验TWRP，7组保护／完整BCB及tail检查通过。机主确认能解锁、设置长按菜单显示／收起、Home手势响应；设置列表不能滚动，但可上滑回桌面，**不是整机卡死**。设置交互按机主指示独立待修，不把它当作GPU／Liquid Glass根因。CPU与GPU路径均低帧率，没有可靠排名或FPS数值。

267／268旧栈曾有真实Metal棋盘、CRC718ed2ce、120次呈现、exit0和相机／串口一致证据；268补齐所观察4客户端的CloseReturn。新279／280／281不继承那些硬件资格。277相机多数时间手机在边框外，不冒充完整物理验收。FT3683完整身份／边缘／手势、跨task隔离、长期稳定性和性能都未最终验收。

## 存储边界

详细依据：[存储说明](storage-unixnu64.md)、`storage/unixnu64.json`及B281重新计算的布局收据。

- Android userdata为sda34，末LBA47271679。
- unixnu为sda35，4KiB LBA47271680..64048895，64GiB，uniqueGUID `b279731f-ccad-4ef5-a8b7-e7440cd08de3`。
- iOS17原根在unixnu起点，保留9382658048字节。
- Data从unixnu相对16GiB开始，结束25770070016字节，窗口2097217块。
- 单个4KiB原生日志位于unixnu相对LBA2291712／绝对LBA49563392。
- iOS26根重新按Data末端1MiB对齐计算：相对LBA6291712／字节25770852352，绝对字节219395653632，大小32GiB。Data后间隙782336字节，根后保留8588886016字节。

这些是离线输入／算术和历史保护依据，不是当前手机GPT／前像／空闲状态证明。不得向Android userdata写镜像，不得改GPT、槽位、Recovery或复用旧192GiB窗口。

## 失效／中间产物与Git状态

281第一次构建在加入known-present捕获门槛前，内核541de6a7…／boot d56e6076…已移入`B281/before-known-present-capture-gate/`，连同旧源码、测试、重定位映射保留；**不要作为最终281运行**。最终必须是d1e3e7ff…／1d9e57e1…。该目录里的旧FAT等冗余镜像如本次清理已移除，可按清理账本定位保留的等价数据／恢复方式，不代表旧观察被改写。

`presenter-before-final-comment-host/`是最终源码注释归一前的测试记录，不是当前精确source hash；使用当前`presenter-host/`／`presenter-tsan/`。`review281-before-removed-object-dependency-adjustment.py`保留了旧检查错误要求三项未选用线程头的失败；之后按实际编译recipe的-MF依赖路径核实归属。D281还保留`before-closure-field-correction/`，修的是旧280模板字段名与281的new_root_installed差异，未放宽硬件门禁。

当前HEAD：

- UniXNU-zorn：`8067bd3836bde6a201f657109818562c3aa3f790`。
- uefi-zorn：`434f8278c68c6915df5aaa260c22dd0f5988f7b7`。

大量261..280成果原已暂存。暂停时281新增／未暂存部分：

- `scripts/run-zorn-debug.py`及`scripts/zorn_ios26_metal_root_delta.py`的281精确安装flag（MM，280修改已暂存，281增量未暂存）。
- `scripts/check-ios26-known-presenter281.py`（untracked）。
- `patches/gpu/ios26-upstream-known281/`（untracked），含最终8文件补丁、series和source-manifest。
- B281／D281的所有大产物和本地配方保存在out，不进入Git。

276 Settings相关untracked目录／脚本仍在，尚未选用，不能顺手暂存、删除或合并成281。281的README／progress／porting和公开evidence尚未完成同步；本交接及状态快照用于补足续接上下文，不声称已完成仓库发布。根porting.toml约49034字节，48KiB门槛49152，只余118字节，继续记录时要保留历史并压缩当前摘要，不可直接膨胀再触发站点EOF问题。

## 下一步顺序

1. 根据新用户指令／目标状态决定是否恢复离线工作；先看磁盘与本次清理账本。不要重新下载已核验源码或重跑没有新输入的旧检查。
2. 复核B281最终tuple／当前源码、D281精确review和已知图像门槛收据；整理281公开source/evidence/README/porting及两仓库进度，按范围暂存，不额外commit。
3. 以原268已验证的known-image receiver／census判定接入281系统启动入口。复用同一267程序ID，更新boot身份与根／kernel／ADT；不要用278菜单／ROI包替代281整屏SHOT协议。继承receiver-first、错误输入拒绝、全部客户端真实Close、journal完整性和原串口预算；同时保留266内核已知任务的fence／CRCe843b26a及GMU/HFI检查，不能提前当作281硬件前提；现有设备状态／未安装根必须在probe／claim前拒绝。
4. 建立281完整、独立、但未准入的boot bundle和camera配置。明确本次只验新栈已知图像／120呈现／退出／生命周期，不把它包装成桌面FPS测试。300秒独立WDT／600秒核验Recovery、无物理协助、零重试仍不可省略。
5. 只有当前既有SDK37连接及核验Recovery条件具备后，才能按具体审核进入281根安装及独立boot阶段；不bootstrap或重用旧scope。根安装不自动boot，所有历史保留页＋新前像先核对，逐组读回，保护不符／部分未知写入即停止。
6. 新栈已知图像／fence／退出证据通过后，再回280普通backboardd路径或其明确后继版本测量。278的CPU Queue／Beat／LeaseWall／LeaseCall／Acquire／Show是分段观察，空闲拷贝率不是物理FPS，重叠阶段不可相加；结合上游CM／FP和实际GPU时间线，使用固定场景定位低帧率。随后继续完整Metal／显示／跨task／触控／失败生命周期验收。

## 本地镜像清理记录

机主在交接期间另行要求“清理本地无用镜像”。清理仅针对有完整等价保留主镜像的iOS26 local-replay重复副本，逐对实时完整SHA核对，并检查只读、未挂载／未打开；保留17 GPU、Data、真实运行主镜像、当前281主镜像、源码、日志和原验证收据。不因APFS副本的逻辑32GiB大小夸大实际释放空间。

清理明细及每个被删路径到保留镜像／SHA的映射：`/Volumes/macData/projects/ios-zorn/out/zorn/image-cleanup-20261117-handoff281/cleanup-ledger.json`。原历史收据保持原字节；若旧校验器确需一个被移除的重复路径，先从账本保留镜像独立clone并验证对应SHA，再使用，不能把缺少重复路径说成原始数据损坏。最终实际释放量见随文清理摘要。

清理已完成：[15项镜像清理摘要与恢复映射](evidence/image-cleanup-2026-11-17-handoff281.json)。移除了13份与保留主镜像完整SHA相同的iOS26重放副本，以及281旧捕获门槛候选的原始FAT／旧内核；后两者已从保留的旧压缩boot验证可完整恢复。当前281主根／最终内核／最终boot、全部17／Data／真实运行主根均在。清理开始到结束观测的可用空间净增约314 MiB，结束时约1.16 GiB可用；不能把删除的约416GiB逻辑副本当作物理释放量。后续大Rust构建前仍需核对空间。

随后文件系统回收后的复查可用空间约1.87 GiB，已另存清理摘要的later_space_observation；它是主机空间观测，可能含APFS延迟归还及并发主机变化，不据此声称精确物理释放量。

## 后续追加：可再生缓存清理

机主另行要求进一步清理无用文件。[本轮缓存清理摘要](evidence/cache-cleanup-2026-11-17-handoff281.json)及原账本保存在`out/zorn/cache-cleanup-20261117-handoff281/`。

只清理279独立iOS26 Cargo target内的可再生.o／rlib／rmeta／重复静态归档及失效fingerprint，另清理280首次metadata门禁拒绝构建的.o／.a缓存。最终实际链接archive仍在原路径，SHA保持83705f5f…；当前Metal bundle、选中Turnip、当前281 kernel／boot哈希复核不变，主根仍在。保留全部源码／vendor／工具链／命令／日志／收据；Cargo生成的文本源码、依赖和fingerprint元数据另有逐字备份。17 GPU、Data、真实硬件主产物不受影响。

本轮删除约2.01 GiB可再生文件；物理空间观测受APFS共享块／并发主机变化影响。清理后采样可用约2.49 GiB。目标仍paused，没有设备操作或新commit。

后续Agent不要将Cargo中间文件缺失当作损坏，也不要沿用残存cache宣称重编完成：fingerprint已随缓存失效。若需重编，使用原279精确源码／离线vendor／原生PAC工具链／命令在独立新输出中重新生成，保留当前最终archive及历史收据；冷编可能变慢。

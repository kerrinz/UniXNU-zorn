# K80 iOS26 v242 当前交接（2026-11-16）

目标active；完整GPU/Metal/display/FT3683及正常生命周期验收仍未完成。手机已自动回TWRP且保护区/BCB检查通过。242和旧已消耗候选不重试。禁止反汇编/逆向、机器地址/寄存器/回溯解释或符号化。原生panic非文本数据保持opaque。

B242：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v242-close-source-ba560d3ea4d34be8964dd3463fcd7062`；S242：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v242-close-source-ba560d3ea4d34be8964dd3463fcd7062`；T242：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v242-metal-trial-ba560d3ea4d34be8964dd3463fcd7062/root-trial`。

本次实际kernel SHA5543771df442be025c6a97dabd330425a4553ca3aa8981f7c6d8ad8cca214cde，boot SHA4ba09468511ccf3b6e2c025588048c89a0ef6cd4b2e60abd71f633ab3c2eccac。原229根、FD/ADT/菜单/EFI及存储窗口保持。精确输入以当前boot-package/verified.json和full-link/exact-inputs.json为准。

## 启动前修正与离线证据

初版242只OR四个关闭位，后经多会话审阅发现首个成功关闭会污染第二次关闭进度。未访问手机前完整归档到revision-before-close-reset（含源/对象/kernel/boot/原配方）。实际版本在closeApplicationProcess入口原子清除20..23，低20位保留，然后原调用链在Close授权完成、quiesce返回、releaseAll返回及ClientStorage销毁/free后分别置20..23。新reset函数在AppIo中以同一个原子AND操作完成，原header仅加C声明。没有改变实际权限、检查顺序、返回、DMA状态判定或失败保留/正常释放。

新reset/real recorder/双会话与并发低位保留测试ASanUBSan/TSan通过，去掉新增include/helper/调用后HostRing/AppIo/header逐字节恢复241。全部24受影响对象重编、1398输入/0undefined/58头依赖/5身份核对通过。原snapshot/observer/formatter源及POD头与241逐字节同，复用范围明确记录；原CAS try-lock仍只尝试一次。相关包/formatter/producer/cleanup/failure-retain/race/parser/capture重跑；新24位decoder独立于旧240模块，未知bit24拒绝，并重解真实241包。真实receiver PTY402350B、51拒绝及check-only通过。

重新准备测试夹具时capture/PTy曾因producer目录归档后尚未重新运行parser生成application-fixture而拒绝；按producer->parser->capture依赖顺序修正后通过，没有修改内核迁就测试。startup源码/对象保持原哈希，明确复用历史精确重建，不把它记为242重编。完整FAT/boot回读及source loader consumer通过。新scope/ready/claim只对应修正后当前完整包。

## 单次实测

200.274秒自动回TWRP，receiver/inner exit0，286375B。身份/CRC/footer通过；完整原因/paniclog/msgbuf及具体长度在cdc-capture.json；导出无截断，源decoder0errors。七组保护及全页BCB/tail通过，没有额外设备重启/恢复。

SOURCE240 events4194303，即低20位+20/21，未出现22/23。高四位已在当前Close入口重置，所以不再由首个成功关闭污染。已完成Close授权、quiesce返回，但没有releaseAll返回标记。**21只表示quiesce函数返回，不表示它的raw=0；目前仍可能是releaseAll路径、quiesce错误处置或其他线程的panic，不能直接定为releaseAll内部根因。**

终止APP241仍与probe同unique10/pid10，sessions2，flags31/dropViews成功，close0/0，rejected0/dropped0；seq87/method7/GetTimestamp的run/base0已返回。普通最后phase1为早期帧，不替代真实终止快照。PAC症状仍在，未解释任何机器状态。证据：[v242实测](evidence/k80-gpu-v242-close-source-observed-2026-11-16.json)。

## 已完成的实际关闭边源码调查

以完整对象SHA确认DirectClient00e426…来自k80-direct-fence-width26的实际配方；DirectSubmit def0b82…来自185/native-compile；NativeRing fd8f56…来自k80-direct-fence-prefix26。核对HostRing/DirectClient实际均arm64e+iOS26目标，未发现混用arm64/OS17的证据。

额外audit在B242/close-buffer-source-audit：所选NativeAdrenoMemory34c80d…与IOBufferMemoryDescriptor源均按原配方重编，整个对象逐字节等于本轮所选对象。源码编译器AST record-layout只检查类型/偏移，未检查机器指令。起初缺cwd导致meta_features.h缺失的审阅脚本错误已保留并修正；原始布局文本不同处是既有OSPtr别名与OSSharedPtr展开，不能冒充根因。明确规范该表示后有效成员偏移/数字布局相同；不扩大为所有行为ABI一致。结果json明确保留这个限制。

## 下一步具体工程工作

实际选中DirectClient::freeBo已有native_adreno_trace_stage=1/2/3/4，所选NativeMemory::release已有30/31/32/33/34，且这些是公开源码诊断变量，不是CPU寄存器。应优先复用它而不是另造每层完整trace：在真实releaseAll调用前给这个既有诊断标量写一个明确的新entry哨兵，避免上一个会话留下旧stage；终止时只导出该scalar，并说明全局/最佳努力归属限制，不解析地址。确认全体写入者来源与实际对象，未知stage保持未知。不得把阶段数值当作GPU完成或DMA已停的证明。

具体close链和原资源释放约束见[v241记录](handoff-2026-11-16-k80-ios26-gpu-v241-active.md)。只有新完整候选、固定工具、独立scope/ready/claim及Recovery保护回读/WDT/600s界限全部满足后，才能继续设备试验。完整验收未达，不暂停目标。

## v243 已完成离线工作（未启动）

B243：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v243-release-stage-38367112517a40e2acc6353195823ac1`；S243：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v243-release-stage-38367112517a40e2acc6353195823ac1`；kernel SHA：`c238ba443b923b800058ae6e0dbe46f89acc08750e4c1f7b094804fba6e8c75b`。1398实际输入、24重编、0undefined及58相关头依赖已核对。完整包及固定工具尚未准备，不得拿仅kernel启动。

HostRing在原if(!raw)及原issuer/gate保护内、实际releaseAll调用紧前写既有native_adreno_trace_stage=100（新source入口哨兵），避免沿用此前释放留下的旧phase；不会改变返回或硬件policy。Recovery在既有native panic writer保护内追加K80 RELEASE243 native=… schema=1，只读一次既有scalar，不走对象/地址/回溯。HostRing/Recovery删除新增声明、哨兵与export后逐字节还原242。

B243/release-source-host/result.json覆盖实际赋值/formatter文本、UInt32上下界与新parser数值/重复/schema检查，ASanUBSan通过。writer是明确host边界替身，没有执行真实release/GPU；既有global volatile不是原子会话快照，测试和decoder均明确不宣称并发安全或culprit。独立decoder `UniXNU-zorn/scripts/inspect_ios26_gpu_release243.py` 不改旧绑定模块。source阶段1..4来源实际DirectClient，30..34来源精确复建过的所选NativeMemory，100是当前候选新source哨兵；其他stage如10保持unknown直至核对其实际所选写入者，不能臆测。

下一步完成上列offline-progress.json剩余source/组合/receiver边界/完整打包/固定scope工作，再决定新单次试验；无需用户提供工程源码或重复授权。尚未生成243bundle/ready/claim、未访问手机。证据：[243离线进展](evidence/k80-gpu-v243-release-stage-offline-2026-11-16.json)。原32位trace变量由实际NativeMemory定义，链接无新增未定义项，不添加替身变量。

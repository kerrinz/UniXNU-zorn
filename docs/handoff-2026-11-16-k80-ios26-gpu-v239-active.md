# K80 iOS26 v239 当前交接（2026-11-16）

目标仍active；GPU/Metal/display/FT3683完整实机验收未完成。严格禁止反汇编、逆向、地址符号化及寄存器/回溯解释。当前手机已由固定工具确认回TWRP，保护区回读通过，238和239 claim均消耗，不再启动它们。

## 当前精确输入

B239：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v239-late-panic-c1114b2d991e46feb2f24b66c0b6ce4b`

S239：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v239-late-panic-c1114b2d991e46feb2f24b66c0b6ce4b`

T239：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v239-metal-trial-c1114b2d991e46feb2f24b66c0b6ce4b/root-trial`

kernel：`f8496bf47610e35857f3c577187b8b0cad2affb736c59a8c733766ae0ca7777a`

boot：`4efd929907b565a35f2a84bc7c55c1104c2da26cdfd1c6afed5f4bc9b770a52b`

根仍为已安装229的193e5f01…，FD/ADT/启动器/菜单及存储窗口未改，只有FAT中的kernel改变。完整输入以B239/boot-package/verified.json与full-link/exact-inputs.json为准，不仅相信/tmp指针。实际1398输入、24重编、1374保留、0undefined、53头依赖及5实际身份依赖检查通过。公开来源和精确原配方均继承238归档；未使用新的上游源码。

## 本轮完成与源码变化

v238启动前留下的EFI来源缺口已补齐：历史原路径/原命令复建EFI整文件逐字节等于当前ccae7c1d，原目录归档后恢复。独立路径不一致的结果保留，未解读机器码。详见B238/loader-exact-rebuild-result.json及loader-original-archive。

v238单次89.956秒回TWRP，0B CDC/旧日志，不能确认任何RAM初始化或GPU执行。没有重试238。

v239在独立源/构建中从238派生，只改pe_init.c和ZornUsbCdc26.c的初始化时序及ZornUfsOwner26.cpp/USB身份retag。RAM容量、内核BSS所有权及原生writer保持；沿用238宏和数组名是内部实现名称，不表示仍在console中激活。删除PE_create_console调用；正常CDC线程确认首帧完成、发布ready并释放原ownership lock后，调用新的同类型C接口zorn26_panic_ram_prepare239。只尝试一次，全部现有或部分初始化状态保留，真实调用debug_log_init（含原ext_paniclog_init），panic时不分配、不写存储。不是恒成功替身。

ASan/UBSan真实初始化提取检查16种初态、重复调用、原生header/writer边界通过；128种实际首帧门槛组合通过。真实allocator未在主机执行；loop测试明确替代MMIO/cache/clock及外部初始化边界，另测initializer。正常清理、DMA未知保留、29sender拒绝、100竞争与1000发布拒绝TSan通过。C/Python包、formatter/va_copy、producer/parser/capture、真实receiver PTY402350B通过。固定239runner新增late-source门禁，33拒绝及check-only通过。构建及打包/FAT/加载器公开source consumer检查通过。

保留host构造错误：首次capture检查缺preview文件，首次review239漏import re；均已修正，未改内核迁就测试。B239/review239-initial-missing-import.py保留失败脚本。239启动源对象未改，以相同对象和源码哈希明确复用238已逐字节复建证据，未宣称239重编它们。

## v239实际结果及边界

单次receiver-first，200.248秒自动回TWRP，inner/receiver均exit0。收到276407B：14普通帧和269613B原始panic包；身份、长度、CRC012871c0和尾标记通过，0partial，0errors。原因1050B、paniclog137347B、msgbuf131072B，三段均无导出截断。paniclog是原生缓冲快照，包含不解码的原生非文本数据；不能把它当作全部启动历史或证明panic全部流程执行完成。msgbuf为有限并发环。

普通panic原因仍报告内核PAC认证失败；不解释地址、寄存器或回溯。普通Metal probe phase1，render/normal close未完成。terminal progress_word与普通frame可能时点不同，不因缺少registration-return帧推断registerService失败。应按已有源协议解码纯state/request/ack字段后再决定下一源码观察点。

约86秒摄像头帧可见Apple标志；仅为画面观察，不是GPU呈现或桌面证据。七组保护及BCB完整页/尾部检查通过，根和Data未写。完整证据见[evidence/k80-gpu-v239-late-panic-observed-2026-11-16.json](evidence/k80-gpu-v239-late-panic-observed-2026-11-16.json)。

## 下一步

日志通道已提供当前身份的paniclog快照；回到公开源码GPU PAC主线，核对实际服务发布、newUserClient/用户态Metal设备发现、回调签名和对象生命周期。以前已有IOService/OSObject/IOMemoryDescriptor源码ABI审阅未证实缺陷，不能重复它们或盲关PAC。不得将PC/回溯转换为源码定位依据。不要为同一现象反复改日志协议或添加恒定成功后端。

任何新试验仍须新候选、精确完整包、独立scope/ready/claim、固定receiver-first、300秒WDT和600秒Recovery，以及Recovery内实时身份/边界核验；保留原Android/iOS17/Data，不bootstrap、不刷机恢复，不依赖物理协助。完整验收仍未达到，不把本轮日志交付当作GPU修复。

# K80 iOS26 v230：有界串口终止原因

目标active。先读[v229实测](handoff-2026-11-15-k80-ios26-gpu-v229-active.md)及AGENTS；严格禁止任何逆向/反汇编、符号化或寄存器回溯分析。

v230为独立kernel-only串口终止原因候选，保留已安装root/probe229193e5f01及frontend226/Rust214/Turnip/全部GPU实际调用。原terminal入口仅增加source原因枚举1/2/3调用，不读取/输出panic文本、地址、寄存器或回溯；不改原等待、reset或WDT。CDC正常轮询/清理与terminal共用非阻塞所有者，先读ready再访问普通状态；只有已完成bulk IN、无数据端点DMA/notify、控制器运行/命令闲置/TRB无HWO/残留/错误且无未处理事件时才允许单个47字节包，计入原39帧/119808B，START只尝试一次，命令轮询1000次无sleep/时间源依赖。无法证明状态则零新写；尝试后USB资源全部保留，正常轮询/清理不得复用或关时钟。真实sender/transfer/epcmd、实际loop/cleanup及原terminal分类片段ASanUBSan通过；100组实际双线程竞争与初始化发布的TSan通过。初始测试把全局锁空闲当作本线程已解锁、混用原子读，已修正测试边界；生产锁未因此改动。测试运行库首次默认尝试符号化但失败，该配置已停止，成功测试显式关闭symbolize；无反汇编或二进制指令检查。所选cache对象按原源码/recipe重编字节相同，宏预处理证明APPLE_ARM64_ARCH_FAMILY未定义，既有VA PoC源路径为真实通用cache循环，不走物理查找/平台回调。新终止帧含原始源sender输出47B/CRLF，23项parser边界和完整/截断capture拒绝通过，原52parser与producer通过。完整内核14ee6941/bootd292cd35、1398输入22重编45头/0undefined，source/编译输入/terminal literal绑定通过；FAT仅kernel成员变化。初始配方误将不变menu列为变化被检查拒绝并保留，最终仅kernel变化验证通过。新scope/owner/ready/check-only及14项拒绝通过；未启动230。

B230：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v230-terminal-cdc-75e1d78baaf544a0bad79e5e4bfdf39e`。源码：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v230-terminal-cdc-75e1d78baaf544a0bad79e5e4bfdf39e`。根及普通probe身份仍为22965f3efb4；kernel/USB/record为23075e1d78b。没有新root安装或写入。launch-command.json固定receiver先启动，禁止单独执行inner entry、复用旧claim或重试。仅47B完整tag/枚举可作为source结束分支证据，不是故障源、DMA已停或GPU完成证据；partial/missing/foreign均不得推断panic。

[准备证据](evidence/k80-gpu-v230-terminal-cdc-ready-2026-11-15.json)。 [最终源补丁](/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v230-terminal-cdc-75e1d78baaf544a0bad79e5e4bfdf39e/terminal-cdc230-final.patch)。


v230已单次观测并自动回收，本段替代未启动状态：v230kernel-only在保留229root/probe193e5f01下单次receiver-first启动，199.991秒自动回TWRP，session78527 exit0/inner0。收到6841B、14个正常CDC帧及一个完整47B终止包r=2，身份与本轮75e1d78b匹配；无尾帧、诊断丢失或解析错误。原terminal源码把此次结束分类为panic分支，首次获得真实串口结束原因；具体panic触发源未知，不能由该枚举分析地址/寄存器/回溯，也不能据此认定PAC根因。最后仍state2/point5/ack5，未观测registerService返回后的gate6；probe229仅phase1等待服务、native session0，新Metal路径未到。单包到达证明实际尝试/传输送达，不证明设备侧DMA完成或停机，代码保留全部USB资源直至整机回Recovery。七组保护及完整BCB通过，根193e5f01未写，本轮无root安装。 [证据](evidence/k80-gpu-v230-terminal-cdc-observed-2026-11-15.json)。
目标active。保持230新串口来源与全部已归档构建/结果，不复用claim。围绕实际registerService前后源码，核对已链接IOService/IOAcceleratorES/ZornGen7AppIoService的精确对象、实际头依赖/布局和arm64e编译参数，先排除源码或ABI混用；仅进行源码/编译器元数据/精确重编对照，不作任何二进制指令检查或符号化。必要时再由明确源码分支输出无格式化值的原因类别；不得读取/分析panic地址、寄存器或回溯。

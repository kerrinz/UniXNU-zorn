# K80 iOS26 GPU 续接交接：v243 离线与时钟生命周期缺陷（2026-11-16）

这是最新续接入口，补充并更新 [v242 交接](handoff-2026-11-16-k80-ios26-gpu-v242-active.md)。用户要求生成交接交给其他 agent；本次只保存交接，未进行设备操作。目标没有完成，也没有标记暂停。GPU、Metal、显示、FT3683 及资源生命周期最终实机验收仍需继续。

## 先做什么

**优先修复已经用实际源码复现的时钟指针生命周期缺陷，再考虑下一次启动。** 不必为了已有诊断而先启动 v243。建议保留 v243 为未启动诊断候选，在新独立 v244 源码/构建目录完成最小修复；版本号须先确认未被其他工作占用。不要重试已消耗的 v242，不要修改历史共享源或旧构建。

当前没有实现该修复。已确认的是主机源码 stack-use-after-return，不是实际内核崩溃位置，也不是已经证明真机 PAC 症状由此导致。

## 已证实的源码问题

实际链接的 `ZornGen7DirectClient26::dispatch` 包含：

```cpp
static const NativeAdrenoRingClock *vm_clock=nullptr;
vm_clock=clock;
zorn_direct_vm_now_us=[]()->uint64_t {
    return vm_clock && vm_clock->now_us ? vm_clock->now_us(vm_clock->cookie):0;
};
```

调用者 HostRing 的 `dispatchProcessClient` 传入栈上 `NativeAdrenoRingClock clock`，或带栈上 `FenceWaitClock wait` cookie 的 `waitClock`。dispatch 离开后上述全局 hook/静态指针未恢复或清除。后续 `closeProcessClient` 直接调用 `client.releaseAll(&clock,0)`，不经过 dispatch；freeBo/unmap 中 `PhaseClock` 调用该 hook，可能读到已经退出的 dispatch 调用栈。

`NativeAdrenoMemory::release` 的对象布局检查没有发现此前怀疑的数值布局差异；OSPtr 与 OSSharedPtr 文本差异只是别名表示，不应继续当作根因。

主机复现从实际 DirectClient、DirectVM 和 NativeAdrenoRing.h 提取安装代码、PhaseClock 和时钟类型，用 noinline 调用者创建栈对象、返回后再调用 PhaseClock。Clang ASan `detect_stack_use_after_return=1:symbolize=0` 检出预期 stack-use-after-return，result.json 的 passed=true 表示**成功复现缺陷**，不是修复通过。未运行 GPU/MMIO/DMA，未解释机器地址。源 SHA、源片段、编译日志、预期失败日志及测试脚本已保存。

建议最小修复方向是限定 hook 与时钟绑定的有效作用域，并在 dispatch/释放路径都正确安装和恢复，覆盖早退与嵌套。实施前必须检查所有 hook 调用者及跨实例/线程的序列化保证；不要直接假设全局状态天然安全，也不要永久复制带栈 cookie 的 clock。HostRing 的 nativeNow 当前忽略 cookie，但这不足以授权持久保留任意 cookie。若采用 RAII，验证析构顺序、旧 hook/上下文恢复与 releaseAll 作用域；不能用恒定成功或禁用实际资源回收替代修复。

## 精确路径与输入

工作根：`/Volumes/macData/projects/ios-zorn`。

B243：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v243-release-stage-38367112517a40e2acc6353195823ac1`

S243：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v243-release-stage-38367112517a40e2acc6353195823ac1`

下文 B243 相对文件均在上述构建目录。核心证据：

- `clock-lifetime-reproducer/result.json`：复现成功；`actual-source.cpp`、`test.py`、`compile.log`、`expected-failure.log` 为原证据。原 test.py 使用 /tmp 路径且 mkdir 非幂等；重跑请复制到新目录，不覆盖原失败证据。
- `trace-source-provenance/result.json`：六个所选对象按原配方完整重建后逐字节相同，包括 DirectClient、DirectVM、NativeMemory、旧 NativeAdrenoUserClient/VM/Publish；记录源、配方、对象 SHA 和 trace 写入位置。不是反汇编。
- `full-link/exact-inputs.json`、`full-link/link-result.json`、`full-build-review.json`：精确内核输入、链接、头依赖。
- `handoff-prepare243-checks.py`、`handoff-repro243-clock.py`：从 /tmp 持久保存的辅助脚本，只作为复用参考；不要盲跑非幂等脚本。

DirectClient 源：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/board/zorn/firmware/gpu-direct-fence-width-candidate/direct-runtime/ZornGen7DirectClient26.cpp`；所选对象 SHA `00e42681403fc929649be857e83c4d547c25354a07f732064b584116b6809c65`；配方位于同一 build OS 目录的 `k80-direct-fence-width26/ZornGen7DirectClient26.cpo-command.json`。

DirectVM 源：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v185-kernel-client-info-f9db3c322f1348d5b8175f07ed5fc9a9/direct-runtime/ZornGen7DirectVm26.cpp`；对象 SHA `131e66a87511882d959c92bd01822a1aac2bafbf1baa96f89cc207f5d5618011`；对应 v185/native-compile 配方。DirectSubmit 也使用 `zorn_direct_vm_now_us`，必须纳入影响检查。

## 手机最后一次已验证状态

最后实际启动是 v242，约 200.274 秒自动回 TWRP；receiver/inner exit0，保护区七组检查、完整 BCB 页与 tail 检查通过。这里只陈述上次验证状态，续接时应通过固定工具重新确认当前状态。交接期间没有新手机访问。

实际 kernel SHA `5543771df442be025c6a97dabd330425a4553ca3aa8981f7c6d8ad8cca214cde`；boot SHA `4ba09468511ccf3b6e2c025588048c89a0ef6cd4b2e60abd71f633ab3c2eccac`。完整实际路径、run 与原始证据见 [v242 实测](evidence/k80-gpu-v242-close-source-observed-2026-11-16.json) 及 v242 交接。

终止 SOURCE240 events=4194303，当前 Close 的 bit20/21 已出现，22/23 未出现。高四位在每次 Close 入口重新清除，旧会话不能污染。bit21 **只证明 quiesce 返回，不证明 raw=0**；未见 releaseAll 返回不能单独证明其内部崩溃。APP241 与 probe 同 unique10/pid10，sessions2，flags31/dropViews 成功；最后原生调用 seq87/method7/GetTimestamp 已返回。普通 CDC phase1 是更早的帧，不能替代终止快照。PAC 只按文本症状记录，未解析寄存器/回溯。

## v243 已完成与尚未完成

v243 完整内核 SHA `c238ba443b923b800058ae6e0dbe46f89acc08750e4c1f7b094804fba6e8c75b`，1398 输入，24 重编、1374 保留，0 undefined，58 相关头依赖核验。**尚无完整启动包、新固定 runner、bundle/ready/claim，没有启动，也没有包含时钟修复。**

唯一运行逻辑增量是原受保护 releaseAll 调用前写既有 trace 标量100，Recovery 在原安全导出路径增加 `K80 RELEASE243 native=… schema=1`。删除诊断增量后 HostRing/Recovery 恢复242。该全局 volatile 标量仅最佳努力诊断，不是线程安全会话快照、DMA停止或GPU完成证明。

新增 parser `UniXNU-zorn/scripts/inspect_ios26_gpu_release243.py` 已测试1..4、30..34、100、未知值及非法输入。后来通过实际对象/源码确认 DirectVM 也写10..14；parser 尚未补充这些含义，不要凭数值猜测，也不必为标签单独启动。

本轮已完成 raw reason/packet、terminal host/loop/race、close reset、producer/parser/capture、panic init、late gate 与 segment 等离线检查。close-source-check、terminal-session-host/parser 是经过明确字节一致与组合证明的旧结果复用，receipt 明确 rerun=false，不应写成全部新跑。旧测试输出中的237/239字样是历史文案，应以实际输入路径为准。

B243 `offline-progress.json` 是较早进度快照，其中 trace writer review 等条目已经完成；本交接更新其状态。`capture-preview.py` 仍来自242，既有 capture 检查不等于 RELEASE243 已接入最终新 receiver。仍缺完整新 source/identity 组合审阅、client-source-host receipt、新 receiver 真实边界/PTY/负例/固定工具检查与完整包回读。建议这些工作直接结合下一份修复候选完成，避免无修复的额外诊断启动。

## 续接验证与构建要求

1. 读仓库 AGENTS.md、README、porting.toml、storage-unixnu64.md；保留现有改动和旧17产物。使用公开源码；必要时查 UniXNU 官方 GPU 教程与其他机型公开项目，核实精确提交，不能复制其他机型板级参数。
2. 在新独立源目录复制实际选中 DirectClient，按原配方和匹配头文件做作用域修复。原 build-cpu-touch.py 只重编既有24项，必须明确加入新的 DirectClient 编译与对应链接替换，不能只修改未入链副本。recipe 的工作目录键有 `cwd` 与 `directory` 差异，按实际数据处理。
3. 新测试需证明原复现失败、修复后通过，并覆盖返回后再次计时、releaseAll、空 clock、早退、嵌套/上下文恢复；并发保证须有实际源码依据。验证 DirectSubmit 等 hook 用户不受破坏，维护真实 DMA未知时保留与正常完成后释放规则。
4. 重编受影响源/头/ABI对象，完整链接与依赖核验；保存精确源、命令、对象和 kernel SHA。构建脚手架可参考 B243/stage243.py、build-cpu-touch.py 和 B242 的 review242.py/package-cpu-touch.py/prepare242-runner.py/stage242-boot.py/check242-runner.py；修改版本时逐项核实，不能机械改 SHA 绕过检查。
5. 完整 kernel、FD、启动器、ADT、固件、根镜像/配置清单、FAT/readback/source loader 检查、新独立 scope/ready/claim、固定 CDC 外层 receiver 与保护检查齐备后才做一次真机试验。旧根窗口不能套给新根；新增写入/布局变化另审。历史实际验收不能替代新构建验收。

## 必须延续的操作边界

仅92988a43/zorn/slotA。无人值守、有真机连接；保护 Android 系统与用户数据、现有 iPadOS17/Data/验收基线。固定已审核工具从核验 Recovery 开始，独立归档，300秒看门狗、600秒有界返回，完整 BCB/tail 与保护区校验。实际启动只通过固定 CDC 外层 reader；不要直接运行内层试验绕过 capture。不得自行 bootstrap、重试、刷机恢复或扩大范围。若不能回 Recovery，立即停止设备操作并保存证据。现有专用 ADB 服务端口5039，不自行启动服务。

严格禁止任何反汇编和逆向工程；不做机器地址符号化或寄存器/回溯解释。可读公开源码、编译器类型元数据、完整文件哈希、明确源代码诊断字段与普通日志。摄像头可以通过既有 capture-zorn-screen26.py 辅助观察，不依赖物理协助。不要运行可能输出秘密参数的进程命令行清单。

不创建定期任务，不提交/推送，不覆盖历史证据，不清理未完成17 GPU产物。工程缺件、编译或链接问题由 agent 自行继续解决；最终完整GPU/Metal/显示/触控与生命周期的对应精确构建实机证据齐全前，不能标记目标完成。

本次交接证据索引：[源码生命周期复现与检查哈希](evidence/k80-gpu-clock-lifetime-handoff-2026-11-16.json)。

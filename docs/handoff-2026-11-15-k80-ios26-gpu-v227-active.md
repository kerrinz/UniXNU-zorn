# K80 iOS26 v227：提前GPU检查点

目标active。延续[v226交接](handoff-2026-11-15-k80-ios26-gpu-v226-active.md)。严格禁止反汇编/逆向/符号化及寄存器回溯推断。

v227从实际源码确认原GPU观察路径在25/45秒CPU采样后额外等待105秒，150秒才持久化检查点并开启120秒CDC窗口。新增独立GPU验证开关-g45，仅省去该105秒，保留CPU25/45、RootRegistered、UFS成功写入/回读后CDC和原GPU所有门槛；默认150秒不变，不继承150秒UI/触控验收。u保留位16明确记录选择，新解析器验证原tag/CRC并拒绝旧150记录或其他保留位。实际worker108组ASan/UBSan与原始XNU参数解析通过。长参数导致1044字节的候选被封装检查拒绝并归档；最终-g45参数1023字节含独立NUL，原GMU最后参数21仍正确解析。最终内核6a8d9d45、boot4c89a8b6，1398输入/22替换/44头检查/0undefined；只改FAT内核和菜单，根226d940保持，无根安装。新scope接收器优先、300秒独立WDT/600秒Recovery；真机结果未成立，时序改善为待验证假设，不是PAC根因修复。

B227：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v227-checkpoint45-c65e1ef41544494f93192b8e32e9180f`。执行入口是launch-command.json固定接收器，禁止单独调用inner entry、复用已消耗claim或自行重试。当前根为226，probe224、frontend226、Rust214/Turnip/PM4均保持。手机Recovery状态由固定运行器现场核验，摄像头仅提供辅助屏幕观察。

[准备证据](evidence/k80-gpu-v227-checkpoint45-ready-2026-11-15.json)。


v227已单次观测并回收，本段替代未启动状态：v227仅内核/菜单改为-g45提前GPU检查点，保留根226/probe224/frontend226，单次receiver-first已在210.131秒自动回TWRP，session42679 exit0/inner0；8412B/17帧CDC、无尾帧/诊断丢失。真实UFS记录u位16确认选中名义45秒，CPU25/45采样和八核通过，不能继承150秒触控/UI验收。最后仍为probe phase2/flags1/service10000024f/device0，native session0/nr全0，未见principal/FFI标记，图像/Metal/IOSurface/显示未验收。更早进入日志没有解除phase2停滞；Recovery也从226约310秒提前到210秒，不能声称已增加完整有效应用窗口。源码phase2之后尚有nanosleep10和setenv，缺后续报告不能直接断定MTL调用已进入。运行中USB0摄像头一帧暗屏，无可辨panic/OS文字；不能证明panic。七组保护与完整BCB通过，根未写、未读回全根。 [实测证据](evidence/k80-gpu-v227-checkpoint45-observed-2026-11-15.json)。
保持目标active，不复用227 claim。基于probe224真实源代码，在既有10秒wait返回、setenv返回/标准Metal调用进入及返回处加最小有界日志，保持原API调用顺序/真实结果/失败保留，继续缩小phase2未观测窗口。Recovery早于300秒只记录实际返回，不推断panic或PAC根因。官方GPU教程仍要求逐项记录设备发现、pipeline、渲染/呈现与生命周期；当前指南示例OS27不得直接替换本地已核验26配置。

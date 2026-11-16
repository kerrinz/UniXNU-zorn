# K80 iOS26 v224 续接：完整离线候选，尚未准入

用户已明确继续；目标active，不再沿用旧交接的暂停状态。必须先读 [旧交接](handoff-2026-11-15-k80-ios26-gpu-v224-paused.md) 与仓库AGENTS。所有禁止逆向/反汇编、存储和设备保护约束继续有效。

v224 IOSurface探针离线推进：保留原stage证据并补最终helper可重现修订；实际helper ASan/UBSan通过4K/16K对齐、stride/padding、独立读取、溢出及拒绝不访问内存检查。仅替换probe构成root224 caaaa8af，568个受监测文件与属性核对，Metal frontend215/Turnip/Rust214保持。65页266240B/11组delta完成实际本地回放，完整镜像哈希一致；重新核对iOS17/Data/log边界，未访问手机。已安装215历史读回由最新5627页实际delta重建为7016页150组覆盖，不能称手机整根读回。22对象重编/1398完整输入/0未解析导入/40头文件依赖通过，kernel72031545；启动包20a00898，ADT仅替换根摘要，300秒看门狗标记保持、现有loader源码preflight通过。新root未安装、新scope/准入/claim未生成、未启动，不是硬件成功。

继续实际NativeMemory/Cpu/MiniIOSurface历史输入及板级coherence策略绑定，核对新探针trust/launch；完成224 producer/decoder/runner与实际检查，再以准确新根delta/replay/保护审核准备新scope。仅执行接收器先启动的固定wrapper，300秒独立看门狗/600秒有界Recovery；未具备准入前不访问手机。PAC根因、IOSurface实际共享图像、GPU显示呈现、完整触控及长期稳定均未验收。

构建目录：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v224-IOSurface-image-19a4a5e9872542ebab85c20db1e20129`。该目录candidate.json已更新实际离线状态；原stage224-probe.py/probe-source-stage.json保留原字节，最终可重现步骤为reproduce-final-helper224.py及probe-source-stage-revision1.json。

root-candidate-attempt1-mount-failed保存沙箱挂载失败、未修改文件系统的候选副本与日志；正式root-candidate通过受控提权执行完成。首次host溢出用例把16KiB顶部地址的4096B范围误当溢出，已修正为page大小，生产helper未修改；失败原因单独记录。

实际direct VM/Submit由v185保留对象提供，已按编译配方确认224副本源码字节相等。MiniIOSurfaceLock/Unlock只维护seed，不提供互斥或缓存同步；必须靠真实完成及native acquireImported。缓存审查JSON仍标明未全部完成，不得当作准入通过。

本轮没有手机命令、没有新root安装、没有scope/claim、没有commit/push；current.json仅只读核对active字段均空、stop=false，未重新实时确认Recovery。所有host进程已完成。证据见 [v224离线证据](evidence/k80-gpu-v224-IOSurface-offline-2026-11-15.json)。

补充：NativeAdrenoMemory/Cpu和实际overlay MiniIOSurface均按历史编译命令在cache-provenance中重新编译，与所选三个对象SHA完全一致；MiniIOSurface实际源的allocation/lock函数体与审查参考一致。剩余是板级coherence策略、新probe trust/launch和224解码/准入绑定。


v224 COMPLETED，当前以本段取代上文“未准入/未安装/未启动”状态：v224 IOSurface探针差分65页/11组已安装并读回匹配69ef0197，保护通过。单次receiver-first启动309.673秒自动回TWRP，session37460 exit0/inner0；8563B/18帧有效CDC，无尾帧/报告丢失。新probe已执行且phase2/flags1/service10000024f，device0；principal标记9位于native_bridge_metal_open之前，未观察到返回15。原生第二session60次完成调用，最后WaitFence6返回0，第一session9次正常close0；第二session未关闭。未到新增IOSurface创建/渲染，不能归咎IOSurface实现或宣称fence挂死/PACpanic。七组保护采样及完整BCB/tail通过，当前root224caaaa8af；没有手机全根读回。GPU渲染、共享图像、GPU显示与完整触控仍未验收。 [实测证据](evidence/k80-gpu-v224-IOSurface-observed-2026-11-15.json)。
保留224根与全部实测，先沿所选principal/frontend215/Rust214的真实native_bridge_metal_open调用链，核对60次原生完成后到principal返回标记15之间的源码回调/对象/FFI生命周期及已有观测盲区；不从地址/寄存器/回溯推断、不禁用PAC、不反汇编。不盲重跑224，不重新写相同根。新的源码修复或有依据的有界观测需新候选/完整受影响构建/新scope，仍仅wrapper接收器先启动、300秒看门狗/600秒Recovery。

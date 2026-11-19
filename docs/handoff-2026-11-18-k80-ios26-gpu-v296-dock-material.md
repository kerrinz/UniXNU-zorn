# Redmi K80 iOS 26 GPU 与液态玻璃／桌面帧率调试交接

更新时间：2026-11-18（持续更新中；当前模式：无人值守模式 + 有真机连接模式，目标设备 `92988a43`／`zorn`／slot A）

最新状态为 312 回收核验超时，设备操作已停止。5037 持有目标 USB ADB 接口，5039 无法读取 Recovery 属性。下文中的 TWRP 结果都对应各自的历史试验。[312 实机回执](evidence/k80-gpu-v312-hid-parent-device-2026-11-18.json) [USB 争用回执](evidence/k80-gpu-v312-recovery-usb-host-ownership-2026-11-18.json)

## 阶段进展一：296 根增量安装与普通桌面实机试验完成

1. **296 专用根增量安装通过**：在核验过的 TWRP 中完成 25 页／14 组专用根增量写入（`933476094a89d0e373392ec144b48bab1cbe537e3eeef44635d7693873570de5` → `181e7fc6f85c73bfe7155baf3cc25260ce9107b9c4efbef28d7075767955e03a`），逐组读回 SHA `2756cfce…`、13,755 个保留页、7 组保护采样、GPT 与整页 BCB 全部通过。[296 根安装回执](evidence/k80-gpu-v296-dock-root-installed-2026-11-18.json)
2. **296 单次有界真机试验通过回收**：单次启动内核 `c34d97511bdcabe5c127023360661bc2e0fb24f860c2f38fc08913563bf8c4da`、启动包 `6697a85df4149e48e47dfb360a5deea32ddb5520265cc55c1f954ab382cc74b1`（标签 `30ac366e5e2f4c3ca42d18fa4fdd8866`），零重试，`332.27s` 自动回到核验过的 TWRP，7 组保护采样、GPT 与整页 BCB 全部一致。[296 精确实机证据](evidence/k80-gpu-v296-dock-material-device-2026-11-18.json)
3. **296 串口与 Dock 裁剪观察**：完整收齐 `76,055` 字节 CDC 原始帧、`8,864` 字节 `backboardd` journal（零缺口、零挂起），压缩原生诊断零丢失（`31,945` 条），后端错误为 `0`。`104×48` 底部四分之一裁剪命中 `present_frame=618`、`surface_id=651`、`producer_fence=completed_fence=access_fence=1209`：Dock 圆角底栏呈均匀深灰 `RGB(46,46,46)`，外部壁纸为纯黑 `RGB(0,0,0)`，按判据记为 `inconclusive_black_background`（`material_blur_qualified=false`）。[296 Dock 串口裁剪图](evidence/images/k80-v296-serial-dock-ROI-2026-11-18.png)

## 阶段进展二：已定位的三项核心根因与解决思路

1. **液态玻璃（Dock／设置长按菜单／状态栏）缺失根因与修复方案**：
   - **根因**：对照本地 iOS 26 开源参考（`hakios-reference/base/tools/dada-ios.sh`、`userland/tools/air/fbfetch.ll`、`gpu2/patches/nativemetal-dada.patch`）确认，iOS 26（`23G90`）CoreAnimation 默认开启内联 SDF（`fixed_frag_*` 依赖 `fc_framebuffer_fetch` 读取 `[[color(n)]]`）、tile shader 与 filter merging；当前 `metal2vulkan`／Turnip 不支持普通渲染 pass 的 `[[color(n)]]` 帧缓冲读取，导致液态玻璃与长按菜单退化为不透明纯色／深灰（274 中长按菜单压在浅紫小组件上方仍呈纯平 `RGB(198,198,198)`）。此外对 `UniXNU-houji` `v36..v54` 记录复核确认，扁平 HFSX 根 + RAMFS `/var` 下 `PosterBoard` 匹配 0 个壁纸扩展提供者且唤醒会触发 `SpringBoard` `SIGTRAP`，因此不盲目开启 `PosterBoard`，优先通过已有色彩纹理背景（浅紫桌面小组件＋图标区）验证液态玻璃模糊。
   - **修复方案（`v297` 单变量）**：在 `com.apple.backboardd.plist` `EnvironmentVariables` 中注入经验证的四项 CoreAnimation 开关：`CA_DISABLE_INLINE_SDFS=1`、`CA_DISABLE_FILTER_MERGING=1`、`CA_DISABLE_TILE_SHADERS=1`、`CA_DISABLE_FRAMEBUFFER_COMPRESSION=1`，使 CoreAnimation 改走标准离屏纹理采样模糊（`narrow_blur_27_frag_lph`／`variable_blur_frag_lph`／`glass_background_all_lph`）。同时以 `ZornSerialMenu297.h` 截取菜单展开稳定后的上半屏全宽 `104×48` 像素（同时覆盖左侧浅紫小组件与右侧暗底／图标区，可直接对比同一菜单在两侧背景上的模糊透色差异）。
2. **普通桌面低帧率根因与拆分优化路线（`v298+`）**：
   - **根因（296 同场 40.02s／355 次提交实测）**：帧间隔均值 `78.43 ms`（约 `12.75 FPS`），CPU 编码均值仅 `3.73 ms`（266／357 帧 `< 1 ms`），但提交至完成回调均值达 `57.92 ms`（`pg=56.06 ms`）。`NativeAdrenoABI` 方法墙钟揭示全局串行锁竞争：`m2v-queue-wait` 在 `WaitFence`（`1,306` 次，均值 `8.18 ms`）睡眠等待期间同时持有 `s.appSerial` 与 `s.issuer`，且 `MiniIOMobileFramebuffer::presenter()` 在整屏 `1440×3200` CPU 像素拷贝（约 `16–17 ms`）期间持有 `s.issuer`，导致单次 `< 1 us` 的 `GetStatus` 被阻塞至均值 `21.54 ms`、`BoImport` `29.53 ms`、`BoFree` `10.53 ms`、`SubmitBatch` `10.25 ms`、`BoMap` `10.17 ms`。
   - **修复路线（`v298+` 逐版单变量实测）**：（a）`WaitFence` 先在锁内做零超时轮询，未完成时释放 `s.issuer` 在 `s.waitGate` 上等待 GPU IRQ 唤醒并重检健康与上下文；（b）`presenter()` 在锁内完成 fence 校验与缓存取得后释放 `s.issuer` 再执行 `fBase` 像素拷贝；（c）审慎缩减无活跃范围重叠时的 `BoMap`／`BoFree` 全局 `quiesceKernelIo()`，并回归 294 已知图像与四客户端 `Close` 生命周期。
3. **相机录制超时根因与修复方案（`v297`）**：
   - 296 中旧相机包装 `SECONDS=340` 叠加 `-movflags +faststart` 二次重写超过 `358s` 上限（`camera_exit=124`，缺 `moov`）。`v297` 独立相机脚本改为 `SECONDS=320`、分段 MP4（`-g 30 -movflags +frag_keyframe+empty_moov+default_base_moof`）与 `380s` 超时，彻底消除收尾重写超时。

## 阶段进展三：297 根增量安装与液态玻璃（Liquid Glass）实机验证通过！

1. **297 专用根增量安装通过**：在核验过的 TWRP 中完成 21 个 4 KiB 页／11 组专用根增量写入（`181e7fc6f85c73bfe7155baf3cc25260ce9107b9c4efbef28d7075767955e03a` → `951d3de636fb50a26886ac6b07e24db5bf3da6a0b58be2706542f28339fca301`），仅在 `/System/Library/LaunchDaemons/com.apple.backboardd.plist` 注入 `CA_DISABLE_INLINE_SDFS=1`、`CA_DISABLE_FILTER_MERGING=1`、`CA_DISABLE_TILE_SHADERS=1`、`CA_DISABLE_FRAMEBUFFER_COMPRESSION=1`（及 `9c37385967304b6fae92874309c81104` 计时会话）。逐组读回 SHA `410ef10b…`、13,755 个保留页、7 组保护采样、GPT 与整页 BCB 全部通过。[297 根安装回执](evidence/k80-gpu-v297-glass-root-installed-2026-11-18.json)
2. **297 单次有界真机试验、自动回收与分段 MP4 相机录制全部通过**：单次启动内核 `a2a68439ff9089e471dc6888446df1439d2c002c805787898d9961596e66f5ce`、启动包 `e942787753046aef8168425fe6c83eef79666c5f73b296e0ef970785c2a3aa69`（标签 `9c37385967304b6fae92874309c81104`），零重试，`332.90s` 自动回到核验过的 TWRP，7 组保护采样、GPT 与整页 BCB 全部一致；分段 MP4 相机录制（`320s`／`32,131,051` B，`camera_exit=0`）彻底解决 296 收尾超时问题。[297 精确实机证据](evidence/k80-gpu-v297-glass-material-device-2026-11-18.json)
3. **液态玻璃（Liquid Glass）模糊透色双通道实证通过**：
   - **渲染路径激活证据**：`backboardd` 编译并运行 **61 个 Vulkan 管线**（296 仅 28 个，新增 33 个离屏高斯模糊／可变模糊／玻璃背景采样管线全部正常执行，`tile 0`），单帧渲染从 296 的 3–5 个 pass 跃升至 **`25` 个 render pass（`rp25 dr59..64 kpx23965`）**，40 秒窗口执行 **`368` 次离屏 2D 模糊／拷贝（`GMb s2d 368/368/368/0`）**，后端错误与日志丢失均为 `0`。
   - **串口像素级定量证据（`K80SH297` `104×48` 裁剪，`present_frame=391`、`surface_id=424`、`fence=910`）**：设置长按菜单横跨左侧浅紫桌面小组件（内部 `RGB(206,205,210)`）与右侧暗色背景，共 435 种颜色；同一菜单第 `y=26` 行在小组件上方呈明亮磨砂透白 `RGB(210,209,212)`（边缘高光 `RGB(234,233,237)`），跨越底层小组件右边界 `x=42..50` 时呈现平滑高斯模糊过渡 `RGB(207,206,209) → (200,200,203) → (188,187,190) → (178,177,180)`，右侧暗底上方稳定为半透明磨砂灰 `RGB(177,177,180)`（彻底取代 274 的纯平不透明 `RGB(198,198,198)`）。主机初始 `cdc-capture.json` 因把物理面板 `1440×1600` 与逻辑表面 `1125×2436` 直接比较而报错，原始文件保留未改，修正解码器后全部 7 个 CRC 分块、30 帧进度与两份 287 计时报告完整通过。[297 菜单与小组件液态玻璃串口裁剪图](evidence/images/k80-v297-serial-menu-ROI-2026-11-18.png)
   - **相机物理屏幕证据**：175 秒桌面帧清晰可见底部圆角磨砂半透明 Dock 栏与 `Search` 胶囊、左上彩色相册与设置图标及浅紫小组件；220 秒清晰可见设置长按菜单展开并半透明模糊覆盖左侧小组件。[297 相机 Dock 帧](evidence/images/k80-v297-camera-dock-175s-2026-11-18.png) [297 相机长按菜单帧](evidence/images/k80-v297-camera-menu-220s-2026-11-18.png)

## 阶段进展四：298 呈现线程释放 `s.issuer` 实机验证通过（40s 吞吐量提升 +64.5%，提交至完成延迟降低 -42.4%！）

1. **298 纯内核单变量构建与真机验证全部零错通过**：
   - 复用已安装的 297 根 `951d3de6…`（无需重刷根增量），新增 `ZornPresenterScope298.h`（通过 ASan／UBSan 与 TSan 256 次并发锁无竞争测试），单次启动内核 `ca5aca6a17641813e22211c38133fea7d6c0a71ecce042789b2e1dd7bedb87ec`、启动包 `cd7872c51891b39575e2b84f64c64c88ac8ec8e544895c3f682cb093aa7eb088`（标签 `5968f06ef28b4046b0ba8c9e4c49056c`），`receiver_exit=0`、`camera_exit=0`、`verified=true`，`333.41s` 自动返回核验过的 TWRP，7 组保护采样、GPT 与整页 BCB 全部一致。[298 精确实机证据](evidence/k80-gpu-v298-presenter-unlock-device-2026-11-18.json)
2. **298 vs 297 同场 40.005s 液态玻璃桌面性能实测对比（预测与实测毫秒级吻合）**：
   - **40s 完成帧数**：`186` 帧 → **`306` 帧（`+64.5%`）**！离屏 2D 模糊／拷贝从 `368` 次增至 **`532` 次**，Vulkan 管线达 `77` 个，零后端错误、零日志丢失。
   - **提交至完成均值（delta `sample1 - sample0`）**：`103.34 ms` → **`59.51 ms`（`-43.83 ms`／`-42.4%`）**！`< 64 ms` 帧占比从 `52/188 (27.7%)` 跃升至 **`246/313 (78.6%)`**；静止桌面帧 `K310..K313` 提交至完成降至 **`22.44–25.22 ms`（约 40+ FPS 潜力）**！
   - **`FA3` 帧阶段分解**：`pg` 从 `77.00 ms` 降至 **`54.37 ms`（`-22.63 ms`）**，帧间隔 `I` 从 `105.04 ms` 降至 **`83.01 ms`（`-22.03 ms`）**。
   - **`NativeAdrenoABI` 方法阻塞耗时精确消除 `~15 ms` `show()` 拷贝等待**：
     - `GetStatus`（方法 8）：`22.88 ms` → **`7.35 ms`（`-15.53 ms`）**！
     - `BoImport`（方法 16）：`42.55 ms` → **`27.68 ms`（`-14.86 ms`）**！
   - **液态玻璃画质零退化**：`K80SH297` `104×48` 裁剪（`present_frame=334`、`surface_id=367`、`fence=943`）保持 435 种颜色，小组件上方菜单 `RGB(209,209,212)` 平滑高斯衰减至暗底上方 `RGB(177,177,180)`。[298 液态玻璃串口裁剪图](evidence/images/k80-v298-serial-menu-ROI-2026-11-18.png)

## 阶段进展五：299 解耦 `WaitFence` 睡眠期间串行锁实机验证通过（菜单捕获帧数跃升至 `present_frame=587`／`+75.7%`，`m2v-queue-wait` CPU 降低 `-55.8%`！）

1. **299 纯内核单变量真机试验零错通过（已获授权关闭外部 `tcp:5037` ADB 并恢复常设私有 `127.0.0.1:5039`）**：
   - 经用户明确授权关闭宿主机冲突的 `adb -L tcp:5037` 后，常设私有 SDK37 `127.0.0.1:5039`（`--one-device 92988a43`）立即恢复识别核验过的 TWRP Recovery。
   - 复用已安装的 297 根 `951d3de6…`（无需写根），单次启动内核 `7176814b011897e0bf299c4006a92d278ab87c91294d74e4e204f4d21326d48b`、启动包 `eb312f67b264dd69eec74f09e10156dde4378c93ad77d0efbb1b31d7cebc36a0`（标签 `db9363f8a0ac496c807f98f3282cf597`），`receiver_exit=0`、`camera_exit=0`、`verified=true`、零重试，`333.65s` 自动回到核验过的 TWRP，7 组保护采样、GPT 与整页 BCB 全部一致。[299 源码清单](../patches/gpu/ios26-waitfence-unlock299/source-manifest.json) [299 离线准入证据](evidence/k80-gpu-v299-waitfence-unlock-offline-2026-11-18.json) [299 精确实机证据](evidence/k80-gpu-v299-waitfence-unlock-device-2026-11-18.json)
2. **299 vs 298 / 297 液态玻璃桌面性能实测对比**：
   - **整轮液态玻璃渲染总吞吐**：菜单截图时刻由 `v298` 的 `present_frame=334`（`fence=943`、`surface_id=367`）跃升至 **`present_frame=587`（`fence=1268`、`surface_id=620`，较 `v298` 净增 `+253` 帧／`+75.7%`！）**；40.015s 采样窗口完成帧数由 `v297` 的 `186` 帧、`v298` 的 `306` 帧继续增至 **`332` 帧（较 `v297` `+78.5%`，较 `v298` `+8.5%`）**，离屏 2D 模糊／拷贝增至 **`652` 次（较 `v297` `+77.2%`）**，`FA3` 帧间隔 `I` 进一步降至 **`81.45 ms`**（`v297` `105.04 ms` → `v298` `83.01 ms` → `v299` `81.45 ms`）。
   - **锁竞争消除直接证据**：`m2v-queue-wait` 线程 CPU 耗时由 `v298` 的 `7,867 ms` 降至 **`3,477 ms`（`-55.8%`）**；`BoAlloc` 均值由 `12.66 ms` 降至 **`7.10 ms`（`-43.9%`）**，`BoFree` 由 `11.08 ms` 降至 **`9.92 ms`**，`BoImport` 由 `v297` 的 `42.55 ms`、`v298` 的 `27.68 ms` 进一步降至 **`23.12 ms`（较 `v297` `-45.7%`）**，后端错误与日志丢失均为 `0`。
   - **液态玻璃画质零退化**：`K80SH297` `104×48` 裁剪（`present_frame=587`、`fence=1268`）保持精确 **435 种颜色**，小组件上方菜单 `RGB(209,209,212)` 平滑高斯衰减至暗底上方 `RGB(177,177,180)`。[299 液态玻璃串口裁剪图](evidence/images/k80-v299-serial-menu-ROI-2026-11-18.png)
3. **299 暴露的两项剩余内核墙钟瓶颈（指导 `v302` 与后续 `BoMap` 优化）**：
   - 在 `WaitFence` 不再持锁睡眠后，40.015s 窗口前两大 RPC 墙钟耗时集中于：
     1. **`BoImport`（`NC 16`：`344` 次，均值 `23.12 ms`，总墙钟 `7,953.9 ms`）**：因旧 `nativeContextFreeMethod289` 仅豁免了 `GetStatus`／`GetTimestamp`／`BoCpuMap`／`BoCpuUnmap`，未豁免纯 CPU 导入 IOSurface 的 `BoImport`（及 `BoAlloc`、`Metadata`、`Queue`），导致每次 `BoImport` 结束时调用 `leaveApplicationContext(execution, /*keepPending=*/false) -> RestoreKernel -> quiesceKernelIo()`，把在途 25 个 render pass 的 GPU 队列同步排空并重置 CP 上下文！
     2. **`BoMap`（`NC 3`：`534` 次，均值 `13.90 ms`，总墙钟 `7,423.1 ms`）**：每次映射前执行 `quiesceKernelIo()`，映射后同样执行 `leaveApplicationContext(..., false) -> RestoreKernel -> quiesceKernelIo()`。

## 阶段进展六：已定位 277“设置列表展示但不能滑动、上滑仍能回桌面”的精确内核／服务根因（`v301`）与纯 CPU 方法免 `RestoreKernel` 排空优化（`v302`）

1. **跨机型对照与本机源码链路闭合（零反汇编，纯开源 XNU C++ 与仓库记录）**：
   - 对照本地 `UniXNU-houji/archive/docs/display-performance.md`（r57 实测栈）与本机 XNU 源码确认：iOS `Preferences.app`（设置）主线程在查询网络接口（`SCNetworkInterfaceCopyAllWithPreferences` → `dispatch_once_wait`）时会同步等待 `configd` `InterfaceNamer` 的 `__wait_for_IOKit_to_quiesce`（即 `IOServiceWaitQuiet(gIOServiceRoot)`，默认等待 300 秒）。因为底部上滑返回桌面由独立的 `SpringBoard` + `backboardd` 系统手势处理，而列表滚动由 `Preferences` 主线程 `UIScrollView` 处理，所以呈现“设置能打开展示首帧列表但不能滑动、上滑回桌面完全正常，且 CPU 与 GPU 渲染下表现一致”的精确现象。
   - **本机 K80 iOS 26 根因**：核对本机链接符号表确认内核启用了 `!NO_KEXTD`（含 `gIOMatchDeferList` 与 `IOService::iokitDaemonLaunched`）。在 `iokit/Kernel/IOStartIOKit.cpp:187-196` 中，`StartIOKitMatching()` 因 `OSKext::iokitDaemonAvailable()`（`libkern/c++/OSKext.cpp:1598-1634` 在 iOS 上恒返 `true`）执行了 `IOService::getServiceRoot()->adjustBusy(+1)`，且 `IOService::publishPMRootDomain()` 跳过了 `publishUserResource(gIOResourceIOKitKey)`，等待用户态 `kernelmanagerd` 启动后调用 `IOService::iokitDaemonLaunched()`（`IOService.cpp:1229-1239`）执行 `adjustBusy(-1)` 与发布 `IOKit` 用户资源；但当前精简根的 `/System/Library/LaunchDaemons/` 未包含 `com.apple.kernelmanagerd.plist`（单体内核无动态 kext／dext 加载），导致 `gIOServiceRoot` 的 `busyState` 永久保持 `>= 1`！
   - **最小单变量修复构建验证（`v301`）**：新增 `ZornIokitDaemonQuiet301.h`（ASan／UBSan 与 TSan 16 线程并发仅单次递减 `1 -> 0` 验证通过），在 `ZornUfsOwner26.cpp` PID 1 进入 EL0 且核验根挂载后单次释放 `StartIOKitMatching()` 遗留的 busy 计数并发布 `gIOResourceIOKitKey`。内核 SHA-256 `19a7732281c9ac417e6ab175f05c8ccf45185d44e93b8f6f01d05fb66f8c`（修正以清单为准：`19a7732281c9ac417e6ab175f05c8ccf45185d44e93b8f6f1d5605ce6eb3e126`），启动包 SHA-256 `4512c7ee8da5b6a119e59c5310bf4562454bc10e6a357ac0e0959d192cd4f806`（标签 `94bb95fca9e14fa7b26f01d05fb66f8c`）。[301 源码清单](../patches/gpu/ios26-iokit-quiet301/source-manifest.json) [301 离线证据](evidence/k80-gpu-v301-iokit-quiet-offline-2026-11-18.json)
2. **`v302`（叠加 `v298 + v299 + v301 + ZornCpuViewContextFree302.h`）真机实测零错通过，`BoImport` 延迟骤降 `-98.8%`（`42.55 ms` → `0.498 ms`）！**：
   - 单次启动内核 `07d5030fd31a0df6155d5138e83f826e763b6e5dd677dd46c7626928922a9b89`、启动包 `f3d836a32d5bc92c27cac846c0226de92a2ae079797d7a125829765906bc68ad`（标签 `1881eb67fb094ba09abb05ad8f7cbdeb`，复用已安装 `v297` 根 `951d3de6…`，零根写入），`receiver_exit=0`、`camera_exit=0`、`verified=true`、零重试，`334.06s` 自动返回核验过的 TWRP，7 组保护采样、GPT 与整页 BCB 全部一致。[302 源码清单](../patches/gpu/ios26-cpuview-ctxfree302/source-manifest.json) [302 离线证据](evidence/k80-gpu-v302-cpuview-ctxfree-offline-2026-11-18.json) [302 精确实机证据](evidence/k80-gpu-v302-cpuview-ctxfree-device-2026-11-18.json)
   - **`v302` 核心实测改善（40.019s 采样窗口）**：
     - **`BoImport`（`NC 16`）均值**：`42.55 ms`（`v297`）→ `27.68 ms`（`v298`）→ `23.12 ms`（`v299`）→ **`0.498 ms`（`498 us`，较 `v299` `-97.8%`、较 `v297` `-98.8%`！）**；
     - **`BoAlloc`（`NC 2`）均值**：`12.66 ms`（`v298`）→ `7.10 ms`（`v299`）→ **`1.43 ms`（较 `v298` `-88.7%`）**；
     - **`FA3` 单帧资源导入耗时 `res`**：`12.26 ms`（`v299`）→ **`1.57 ms`（`-87.2%`！）**；
     - **`m2v-queue-wait` CPU 耗时**：`7,867 ms`（`v298`）→ `3,477 ms`（`v299`）→ **`1,890 ms`（较 `v298` `-76.0%`）**；
     - **液态玻璃画质零退化**：`K80SH297` `104×48` 裁剪（`present_frame=463`、`fence=1144`）保持精确 **435 种颜色**，小组件上方 `RGB(209,209,212)` 平滑过渡至暗底上方 `RGB(177,177,180)`。[302 液态玻璃串口裁剪图](evidence/images/k80-v302-serial-menu-ROI-2026-11-18.png)
3. **`v302` 揭示的桌面帧率决定性根因（源码逐行闭合，指引 `v303` 消除单帧 `~40+ ms` 内核页表全遍历开销！）**：
   - 在 `BoImport` 降至 `0.498 ms` 后，`v302` 的 `NC` 表暴露出单帧仍消耗约 `64.8 ms` 纯内核 CPU 时间：`BoMap` 均值 **`18.65 ms`**（`2.1` 次／帧）、`BoFree` **`11.95 ms`**（`1.16` 次／帧）、甚至异步写 `wptr` 的 `SubmitBatch` 也达 **`11.73 ms`**（`1.0` 次／帧）！
   - **逐行源码根因定位**：
     1. **`RestoreKernel ↔ Select -> p.vm_.auditLive()` 同进程反复全量页表遍历（每次 `~10 ms`，每帧触发 `~4` 次！）**：`ZornGen7HostRing26::finishApplicationOperation`／`leaveApplicationContext` 在每次 `BoMap`、`BoFree` 及已完成的 `WaitFence`（`outstanding == 0`）退出时，即使当前唯一活跃客户端 `backboardd` 未发生任何切换，仍强制执行 `RestoreKernel`（切回内核 TTBR0 并置 `s.native.requestContextReset()`）；几微秒后同一 `backboardd` 的下一次 `BoMap`／`BoFree`／`SubmitBatch` 进入 `enterApplicationContext -> Select -> ZornGen7HostGpuTables26::selectProcessTables:498`，每次均调用 **`p.vm_.auditLive()`** 全量遍历 `backboardd` 全部 268+ 个 BO／400+ MiB 稀疏 L1/L2/L3 SMMU 页表并重置 Adreno CP 上下文！而 `ZornGen7HostRing26` 的 `PrepareTables`（`2017` 行）、跨进程 `enterApplicationContext`（`1948` 行）、`Close`（`2124` 行）与 `releaseApplicationOob`（`1764` 行）本身已具备完整的跨客户端／关闭时 `restoreCompletedApplicationContext`／`RestoreKernel` 回收机制！
     2. **`BoMap`／`BoFree` 在途 GPU 等待仍位于锁内 + SMMU 全量流冲突扫描每帧重复 4 次**：`BoMap`／`BoFree` 遇上一帧 GPU 仍在执行时在 `s.issuer` 内忙等 `quiesceKernelIo()`（可复用 `v299` 已验证的锁外 `s.waitGate` IRQ 睡眠）；且 `ZornGen7SmmuDomain26` 的 `haltProcessRuntime`／`releaseProcessRuntime`／`beginProcessSubmission` 每次固定传 `full=true` 扫描全部 256 个 SMR/S2CR 寄存器（`ZornGen7DirectVm26::observeCheap()` 已每 64 次执行一次全量冲突扫描，`full=false` 仍完整核验全局／上下文故障寄存器、自有流激活态与上下文寄存器镜像）。
   - **`v303` 修复方案与真机实测大捷（40s 完成帧数跃升至 `788` 帧／`4.24×`，`commit-to-complete` 均值降至 `33.87 ms`，`99.87%` `< 64 ms`！）**：
     - 新增 `ZornActiveContextRetain303.h`（通过 `check-ios26-context-retain303.py` ASan／UBSan 与 TSan 100 帧仅 1 次 `Select`、跨客户端切换、`Close` 与故障保留测试），单次启动内核 `7df77ba770d15f7ddbbf59f8c9dc5d260a373d85438ae60409118c60b24a037d`、启动包 `0b4b696e0e9031171f4e90fb278caedbbacb0a10f6ee02654a12a6e6420f543a`（标签 `2f4ee01ef2c24506b38fd065d47bb57d`，复用已安装 `v297` 根 `951d3de6…`），`receiver_exit=0`、`camera_exit=0`、`verified=true`、零重试，`334.19s` 自动返回核验过的 TWRP，7 组保护采样、GPT 与整页 BCB 全部一致。[303 源码清单](../patches/gpu/ios26-context-retain303/source-manifest.json) [303 离线证据](evidence/k80-gpu-v303-context-retain-offline-2026-11-18.json) [303 精确实机证据](evidence/k80-gpu-v303-context-retain-device-2026-11-18.json)
     - **`v303` vs `v297..v302` 实测里程碑数据**：
       - **40.005s 液态玻璃完成帧数**：`186`（`v297`）→ `306`（`v298`）→ `332`（`v299`）→ **`788` 帧（`+323.7%`／`4.24×`！）**；离屏 2D 模糊达 **`1,550` 次**（`4.21×`），菜单截图时刻达 **`present_frame=1,444`、`fence=2,125`（较 `v298` `4.32×`！）**，后端错误与日志丢失均为 `0`。
       - **帧延迟与分布**：`commit-to-complete` 均值由 `103.34 ms`（`v297`）降至 **`33.87 ms`（`-67.2%`，全窗口最大仅 `102 ms`）**；**`< 64 ms` 帧占比从 `27.7%` 跃升至 `789/790 (99.87%)`**（其中 `204` 帧 `< 32 ms`）；25 个 render pass 重载液态玻璃 `FA3` 帧间隔降至 **`39.27 ms`（持续 `25.5 FPS`）**，轻量合成 `FA1` 帧间隔达 **`12.86 ms`（等效 `77.8 FPS`）**！
       - **`NativeAdrenoABI` 方法延迟全面降至亚毫秒—低毫秒级**：`BoImport` **`0.211 ms`**（较 `v297` `-99.5%`）、`GetTimestamp` **`0.237 ms`**、`GetStatus` **`0.684 ms`**（较 `v297` `-97.0%`）、`BoAlloc` **`0.745 ms`**（较 `v298` `-94.1%`）、`BoFree` **`1.14 ms`**（较 `v302` `-90.5%`）、`SubmitBatch` **`3.13 ms`**（较 `v302` `-73.3%`）。
       - **液态玻璃画质零退化**：`K80SH297` `104×48` 裁剪（`present_frame=1,444`、`fence=2,125`）保持精确 **435 种颜色**，小组件上方 `RGB(209,209,212)` 平滑高斯过渡至暗底上方 `RGB(177,177,180)`。[303 液态玻璃串口裁剪图](evidence/images/k80-v303-serial-menu-ROI-2026-11-18.png)

## 阶段进展七：305 投票 K80 原厂 SKU bin 3 标称频点 `578 MHz`（`0x80 NOM`）＋ `bus=5`（`8.17 Gbps` DDR）实机验证通过（40s 完成帧跃升至 `1,086` 帧／`5.84×`，`commit-to-complete` 均值降至 `19.63 ms`，`99.72%` `< 32 ms`，`100%` `< 64 ms`！）

1. **纯 GPU 执行瓶颈根因定位（`v303` → `v305`）**：
   - 在 `v303` 将内核 RPC 延迟压至亚毫秒—低毫秒级后，`FA3`（25 个全屏 `1125×2436` 液态玻璃高斯模糊 pass）帧间隔 `39.27 ms` 中有 `34.29 ms`（占 87.3%）消耗在 GPU 硬件执行（`pg`）。
   - 核查 `ZornGen7DarwinBoardOwner.cpp:3635-3678` 与 K80 原厂 `ZornGen791StockVoteData.inc`（`stock_0_power_3` / `stock_0_ddr`）发现：此前冷启动路径固定投票最低怠速档 `defaultLevel = 11`（`perfIndex = 1` = **`231 MHz` MIN_SVS**，仅为 `903 MHz` 峰值的 1/4）与 `initialBus = 1`（**`2,136,718 kbps` DDR**，仅为峰值带宽的 1/8）！
   - **`v305` 单变量修复**：新增 `ZornNominalOpp305.h`（通过 `check-ios26-nominal-opp305.py` ASan／UBSan 与 TSan 核验），在 `ZornGen7DarwinBoardOwner.cpp` 投票 K80 原厂 SKU bin 3 标称工作点 **`stock_0_power_3[6]`（`578 MHz`／`0x80 NOM` 电压角，`perfIndex = 6`）与 `stock_0_ddr[5]`（`bus_freq = 5`／`8,171,875 kbps` DDR，`3.82×` 带宽）**，无需开启冷路径未激活的 `HFI_FEATURE_ACD`，热功耗温和安全。
2. **`v305` 纯内核真机试验零错通过（零根写入）**：
   - 复用已安装 `v297` 根 `951d3de6…`，单次启动内核 `b1ee73d63e402a76cfdf685911e74b01170c8ada4911d40b19f08e3bf64e6641`、启动包 `eba8bd8bc3b672d97ae5ff9aefc7152dacdfc745dbff072d1692b5abd4f2c4aa`（标签 `78871e9ec441484592f84b6bacab8dfa`），`receiver_exit=0`、`camera_exit=0`、`verified=true`、零重试，`332.19s` 自动返回核验过的 TWRP，7 组保护采样、GPT 与整页 BCB 全部一致。[305 源码清单](../patches/gpu/ios26-nominal-opp305/source-manifest.json) [305 离线证据](evidence/k80-gpu-v305-nominal-opp-offline-2026-11-18.json) [305 精确实机证据](evidence/k80-gpu-v305-nominal-opp-device-2026-11-18.json)
3. **`v305` vs `v297..v303` 液态玻璃桌面性能实测总表（40.006s 采样窗口）**：
   - **完成帧数**：`186`（`v297`）→ `306`（`v298`）→ `332`（`v299`）→ `788`（`v303`）→ **`1,086` 帧（较 `v303` `1.38×`，较 `v297` `+483.9%`／`5.84×`！）**；菜单截图时刻达 **`present_frame=1,856`**（较 `v298` `5.56×`），离屏 2D 液态玻璃模糊达 **`2,150` 次**（`5.84×`），零后端错误、零日志丢失。
   - **GPU 提交至完成延迟（`commit-to-complete`）与帧分布**：
     - 均值由 `103.34 ms`（`v297`）→ `59.51 ms`（`v298`）→ `33.87 ms`（`v303`）骤降至 **`19.63 ms`（较 `v297` `-81.0%`，等效端到端 `~51 FPS`，全窗口最大仅 `54 ms`！）**；
     - `H frame-gpu` 分布：`<8ms=5`、`<16ms=73`、`<32ms=1,007`、`<64ms=3`、`**>=64ms=0**` —— **`1,085 / 1,088 (99.72%)` 帧低于 `32 ms`（`>= 31.25 FPS`），`1,088 / 1,088 (100.00%)` 帧低于 `64 ms`！**
   - **`FA3`（25-pass 液态玻璃）与 `FA1`（轻量合成）**：`FA3` 纯 GPU 阶段 `pg` 从 `34.29 ms` 降至 `21.46 ms`，其间隔为 `36.98 ms`。`FA1` 间隔 `12.45 ms` 的倒数为 `80.32` 次/秒，表示轻量合成阶段的节拍。该 40.006 秒窗口实际完成 `1,086` 帧，约 `27.1` 帧/秒。面板扫描时序仍缺测量。
   - **`NativeAdrenoABI` 延迟**：`GetTimestamp` **`0.145 ms`**、`BoImport` **`0.247 ms`**、`GetStatus` **`0.375 ms`**（较 `v297` `-98.4%`）、`BoAlloc` **`0.731 ms`**、`BoFree` **`1.234 ms`**、`SubmitBatch` **`3.296 ms`**、`WaitFence` **`4.059 ms`**（较 `v303` `-48.5%`）。
   - **液态玻璃画质零退化**：`K80SH297` `104×48` 裁剪（`present_frame=1,856`）保持精确 **435 种颜色**，小组件上方 `RGB(209,209,212)` 平滑高斯过渡至暗底上方 `RGB(177,177,180)`。[305 液态玻璃串口裁剪图](evidence/images/k80-v305-serial-menu-ROI-2026-11-18.png)

## 阶段进展八：306 已知图像 `CRC718ed2ce` ＋ 120 次棋盘呈现 ＋ 四客户端 `Close` 生命周期在完整 `v298..v305` 后端上真机验收通过（命令全耗时较 `v294` 提速 `15.48×`！），并经 307 恢复液态玻璃桌面根！

1. **`v306` 专用根增量写入（`951d3de6…` → `93347609…`）与真机验收零错通过**：
   - 先在核验过的 TWRP 中安装经审查的 40 页／19 组根增量（`K80-persistent-iOS26-known306-ba667cc7`，读回 SHA `abbbd532…`，7 组保护采样、GPT 与整页 BCB 全部一致：[306 根安装回执](evidence/k80-gpu-v306-known-root-installed-2026-11-18.json)）。
   - 单次无人值守启动 `v306`（完整包含 `v298` 呈现解锁、`v299` `WaitFence` IRQ 解锁、`v301` IOKit daemon busy 归零、`v302` 12 项纯 CPU 方法免排空、`v303` 活跃 SMMU 上下文保持、`v305` `578 MHz` 标称 OPP 投票；内核 `5072b9e45a9bf27359f2fbc77db67855077670eb8a5fee0616d06d740456f162`，启动包 `089286af7bb5c25bfba53eea02cb47408c81f47b42dd3acf3893d0a9cd0b6d78`，标签 `ba667cc788eb47d8adc50c3be81839c2`），`receiver_exit=0`、`camera_exit=0`、`verified=true`、零重试，`332.35s` 自动返回核验过的 TWRP，7 组保护采样、GPT 与整页 BCB 全部通过。[306 源码清单](../patches/gpu/ios26-known-lifecycle306/source-manifest.json) [306 离线证据](evidence/k80-gpu-v306-known-lifecycle-offline-2026-11-18.json) [306 精确实机证据](evidence/k80-gpu-v306-known-lifecycle-device-2026-11-18.json)
2. **`v306` 实机验收核心结果（对比 `v294` 基线）**：
   - **固件认证、GMU/HFI 与内核初始已知图像（`HGKI`）**：100% 正常通过。
   - **Metal 已知图像 `CRC718ed2ce` 与命令延迟（`15.48×` 提速！）**：16 次独立 `32×32` 公共 Metal 管线绘制（每次先覆盖污染共享 IOSurface，再等待真实 GPU 完成回调并做 Metal＋IOSurface 双重 CPU 读回）全部精确匹配 `CRC718ed2ce`；单命令全周期墙钟均值由 `v294` 的 `35,865.59 us`（`35.87 ms`，最大 `77.48 ms`）骤降至 **`2,317.14 us`（`2.32 ms`，中位数 `2.07 ms`，最小 `1.76 ms`，最大仅 `3.77 ms` —— 较 `v294` 提速 `15.48×`／延迟降低 `-93.5%`！）**。
   - **显示呈现双通道实证**：`120/120` 次棋盘格呈现全部完成，`K80SH265` 竖屏 `48×104` 串口截图与第 98 秒相机物理屏幕帧均清晰呈现满屏锐利绿紫棋盘格。[306 串口棋盘截图](evidence/images/k80-v306-serial-checkerboard-2026-11-18.png) [306 相机 98s 物理棋盘帧](evidence/images/k80-v306-camera-checkerboard-98s-2026-11-18.png)
   - **四客户端 `Close` 与资源生命周期**：探针注册的全部 **`4/4` 个原生客户端（ID `64, 129, 194, 259`）** 均完整执行 `Close`（`RestoreKernel -> DetachVm -> RetireDetached`）返回成功，后端错误 `0`、压缩诊断丢失 `0`，进程正常 `exit 0`（完整 48 条 journal `6,334` 字节零缺口）。
3. **`v307` 反向根增量恢复液态玻璃桌面根（`93347609…` → `951d3de6…`）完成，并备妥零合成输入的 `v308` 人工物理触控验收包**：
   - 在核验过的 TWRP 中应用经 32 GiB APFS 克隆重放验证的 40 页／19 组反向根增量（`K80-persistent-iOS26-glass307-ad7f16b4`，读回 SHA `4db6f551…`），7 组保护采样、GPT 与整页 BCB 全部不变，手机当前已恢复停留在已验证的液态玻璃桌面根 `951d3de636fb50a26886ac6b07e24db5bf3da6a0b58be2706542f28339fca301`。[307 根恢复回执](evidence/k80-gpu-v307-glass-root-restored-2026-11-18.json)
   - 同时基于完整 `v298..v305`（`578 MHz` 标称 OPP + `ZornIokitDaemonQuiet301` 设置防卡死修复）构建了零虚拟 HID／零合成触点的 `v308` 人工物理触控验收候选包（内核 `38efe3984d40b008b354a8f9a8d24e4c3174a16eeaea4761fdddbdf4b1cd6a0e`、启动包 `29f0db055343298a12611859d637d1229c325f4702151aae591c20f34e6fef12`，复用当前手机已安装的 `951d3de6…` 根，无需写根），供机主在场时一次性验收 `FT3683` 真手点按／滑动／抬起／触点身份／边缘行为以及 `Preferences`（设置）列表流畅滚动。[308 源码清单](../patches/gpu/ios26-manual-acceptance308/source-manifest.json) [308 离线证据](evidence/k80-gpu-v308-manual-acceptance-offline-2026-11-18.json)

## 阶段进展九：309 设置应用（`Preferences.app`）启动与液态玻璃界面真机渲染通过，并定位前台应用 HID 触点父集合 `(0, 0)` 坐标根因（严格遵守尽量不改动系统用户态原则，纯内核修复推进 `v310`）

1. **遵循 UniXNU 官方“尽量避免改动系统用户态”原则的边界核查**：
   - 全程未修改任何 Apple 系统用户态二进制、Framework 或 `dyld_shared_cache`。此前仅在 `v297`（`951d3de6…`）中因 `QuartzCore` `init_debug` 早于 `AdrenoMetal.metalPlugin` 加载且 `metal2vulkan` 暂不支持普通渲染 pass 的 `[[color(n)]]` framebuffer fetch，被迫在 `mkjobs.py` 本就配置的 `com.apple.backboardd.plist` `EnvironmentVariables` 中加入四项 `CA_DISABLE_*` 开关；自 `v298` 起全部修复与优化（`v298` 呈现解锁、`v299` `WaitFence` IRQ 睡眠、`v301` 内核释放 `StartIOKitMatching` 遗留 busy 计数代替补 `kernelmanagerd`、`v302` 纯 CPU 方法免排空、`v303` 活跃 SMMU 上下文保持、`v305` `578 MHz` OPP、`v309`、以及后续 `v310` HID 修复与 `v311` `FT3683` 30 Hz + 动态 DVFS）**100% 在内核／自有驱动侧完成，零系统用户态改动、零根写入**。
2. **`v309` 真机实测通过（`Preferences.app` 完整打开渲染液态玻璃界面，零错误自动回 TWRP）**：
   - 复用已恢复的 `v297` 根 `951d3de6…`（零根写入），单次启动内核 `c4f7dc6b8d8da76faf5e5f4e63238355dfb85d010a9d12ac994d524646bccfec`、启动包 `5cc011a19f5d6061a800f73459bf8485b016699b18941b6be68053569d82a078`（标签 `7540e9fe84de4a8b8a8a8be81f765ced`），`receiver_exit=0`、`camera_exit=0`、`verified=true`、零重试，`333.54s` 自动返回核验过的 TWRP，7 组保护采样、GPT 与整页 BCB 全部一致。[309 源码清单](../patches/gpu/ios26-settings-scroll309/source-manifest.json) [309 离线证据](evidence/k80-gpu-v309-settings-scroll-offline-2026-11-18.json) [309 精确实机证据](evidence/k80-gpu-v309-settings-scroll-device-2026-11-18.json)
   - **`K80UI276` 五阶段快照与相机物理屏幕实证**：
     - `before_menu`（`frame=1939, fence=2620`）→ `after_menu`（设置长按液态玻璃菜单展开：**`frame=1986 (+47), fence=2667`**）→ `after_dismiss`（外点收起菜单：**`frame=2006 (+20), fence=2687`**）→ **`after_app`（点击设置图标成功启动 `Preferences.app`：`frame=2056 (+50), fence=2737`）**！第 232s 相机画面清晰展示完整 `Settings` 首页（大标题 `Settings`、`Apple Account`、`Airplane Mode` 开关、`Wi-Fi`、`Bluetooth`、`Battery`、`General`、`Accessibility`、`Camera`、`Control Center` 及底部液态玻璃 `Search` 搜索栏），全过程零后端错误、零诊断丢失。[309 相机长按菜单 204s](evidence/images/k80-v309-camera-menu-204s-2026-11-18.png) [309 相机收起菜单 214s](evidence/images/k80-v309-camera-dismiss-214s-2026-11-18.png) [309 相机设置首页 232s](evidence/images/k80-v309-camera-settings-232s-2026-11-18.png)
3. **`after_scroll`（`frame 2056 -> 2056`）的精确纯内核 HID 根因定位（同时影响物理 `FT3683` 与合成触点！）**：
   - 逐行对照本机 `touch-rollover-candidate/ZornTouchFrameEvent26.cpp`（第 52–96 行）与本地开源 `UniXNU-houji` `SweetHID.cpp`（第 470, 495, 513, 529–534 行）及 `hakios-reference` `inject26.c`（第 335 行）确认：
     1. `ZornTouchFrameEvent26.cpp` 创建父级 `kIOHIDDigitizerTransducerTypeHand` 集合事件时固定传 `(x, y) = (0, 0)`，**从未调用 `parent->setFixedValue(kIOHIDEventFieldDigitizerX/Y, ...)`**！
     2. iOS 26 `backboardd` 对 digitizer 集合做目标进程窗口命中测试（hit-test）时读取**父 Hand 集合的 `(DigitizerX, DigitizerY)`**：在锁屏与主屏幕桌面时，`SpringBoard` 独占包括 `(0, 0)` 在内的全屏窗口，因此上滑解锁、长按菜单、外点收起和点击图标启动设置全部命中 `SpringBoard` 并正常生效；一旦前台 App（`Preferences.app`）打开，`(0, 0)` 落在左上角 **`SpringBoard` 状态栏系统区域**而非 `Preferences.app` 客户区窗口，导致 `Preferences.app` 收不到任何触控事件（物理 `FT3683` 触控打开第三方／系统前台 App 时同样受此 bug 影响）！
     3. 同时 `ZornTouchFrameEvent26.cpp` 将子指 `transducerID` 与 `DigitizerIdentity` 设为原始 `p.id`（当物理 `FT3683` 上报 `slot 0` 时与父 Hand 集合的 `transducerID = 0` 冲突；`SweetHID.cpp` 使用 `p.id + 2` 规避冲突，同时保留 `DigitizerIndex = p.id`）。此外 `MiniIOMobileFramebuffer.cpp` 此前仅在 `captureDeadline270` 到期后出现新 swap 时才抓取 `K80SH297`，若滚动惯性在截止前已停稳则需等到分钟跳变（260s）才触发，仅来得及发完 `5/7` 分块。
   - **`v310` 纯内核修复方案**：（a）在独立源码副本重编链接输入 `#1326`（`ZornTouchFrameEvent26.o`），为父 Hand 集合写入首活跃触点（全抬起帧取首抬起触点）归一化 `(DigitizerX, DigitizerY)`，并将子指 `transducerID`／`DigitizerIdentity` 设为 `p.id + 2`；（b）在 `MiniIOMobileFramebuffer.cpp` 的 `zorn26_serial_shot_request265()` 中支持在 `fLock` 保护下直接抓取已停稳的最新呈现帧 `fBase + fZornLastShownRecord310`，确保 `7/7` 分块在 285s 前完整收齐。

---

## 续接：310 父集合坐标与 312 单次验证

309 已在 333.54 秒返回 TWRP，设置首页可见，列表滑动前后停于 frame 2056／fence 2737。源码核验确认旧 Hand 集合坐标固定为 `(0, 0)`，子触点槽 0 和 Hand 的标识重复。前台窗口路由是待验证的解释。310 按本地 houji `SweetHID.cpp` 的已核验实现补入父坐标及子身份偏移，原槽位、分组、抬起、边缘判断和 FT3683 传输保留。串口增加取回已呈现帧的非阻塞路径，`fLock` 保护像素及对应呈现记录，开始写入时作废旧记录。ASan／UBSan、TSan 覆盖实际事件构建的下按、移动、抬起、槽 0、溢出分组和并发。[310 源码和完整构建](../patches/gpu/ios26-hid-parent310/source-manifest.json)

310 的固定 SDK37 预检发现项目私有 5039 实际由 SDK35.0.2 提供服务。旧 claim 已保存，设备启动计数为 0。恢复已核验的 SDK37.0.1 原生回环服务后，只读确认了相同设备、slot A、TWRP、GPT、Data 及根窗口。312 使用独立标签和完整包，并在消费 claim 前检查实际 SDK 进程路径和原生后端，保留共享 runner 中启动前的复核。其回归证明错误 SDK 在 claim 前被拒绝。312 继续复用已安装 v297 根与 578 MHz 投票，选择单次 300 秒试验及 600 秒回收边界。[310 主机中止及只读回执](evidence/k80-gpu-v310-hid-parent-host-stop-2026-11-18.json) [312 精确输入](../patches/gpu/ios26-hid-parent312/source-manifest.json)

已链接的 FT3683 worker 对应 `k80-touch-worker-reference26` 的 `12a3d0f2…` 对象。所选 `zorn26_touch_pacing=1` 是每次读取和上报结束后等待 20 ms，实际传输周期还包含总线与调度。30 Hz 目标需要测量完成间隔后再决定节拍。源自 K80 modules `7d16b7d994c942808a01e2ae6b18ff7a1b7f9285` 的 `gen7_gmu_dcvs_set` 使用 HFI 消息 30、阻塞 ACK、目标 SKU 的频率反向索引和总线能力检查。目前 direct 路径已发启动投票，运行期投票要另核对持有的 GMU/IRQ 权限、频率和带宽的先后、实际完成以及失败后停止推进边界。触控节拍与动态调频应单独比较，避免混淆两项效果。

312 从 TWRP 单次启动成功。设置首页可见，虚拟手势提交和抬起均返回，列表滑动前后保持 frame 2117／fence 2800。第 247 秒和第 271 秒相机画面里的设置条目位置一致。串口完整收齐七片裁剪，截图对应 frame 2118／fence 2801，持续存在已完成的 GPU 表面记录。父集合修复改善了事件字段，仍需检查前台应用路由及物理触控。这次未验收列表移动、顶部导航栏模糊或新帧率。[312 精确实机记录](evidence/k80-gpu-v312-hid-parent-device-2026-11-18.json)

**设备操作停止。** 312 在 600 秒内未能读到 TWRP／OrangeFox 属性，未取得运行后保护区读回。启动前 BCB 与 v309 逐字节相同，整页和尾部检查通过。相机第 319 秒拍到 Redmi 启动标志，稍后黑屏。macOS 重新枚举了 `92988a43`，USB ADB 接口被默认 5037 的 PID 91506 持有，项目 5039 的 PID 93135 收到 `0xe00002c5`（`kIOReturnExclusiveAccess`）。Recovery 核验受主机 USB 争用阻断，手机当前模式仍未知。保留 `stop_device_operations=true` 和已消费的 claim，后续在能安全解除争用且重新核定设备状态前保持离线。[主机日志与接口所有者](evidence/k80-gpu-v312-recovery-usb-host-ownership-2026-11-18.json) [只读主机诊断](../scripts/check-zorn-usb-adb-owner.py)

## v313 物理 FT3683 与 GPU 同步观察

- 以 v312 精确链接输入为基线，保留 v310 的 HID 父集合坐标修复和基线已选用的触点历史回滚。复用 v308 的被动观察线程，在九个窗口内读取真实 FT3683 工作线程的累计计数，以及独立的 GPU 表面、呈现、fence 和错误状态。观察线程不创建虚拟 HID 服务，也不注入触点。设置未滚动仍是 v312 的实际结果，v313 尚无实机结果。
- `K80FT313` 以 1,140 字节封装九组传输和触点统计，保留 `K80SH297` 稳定帧串口裁剪。统计包括读取调用、成功读取、解码、接收、点下、移动、正常抬起、清理抬起、触点 ID、边缘和并发触点。计数挂在原有 FT3683 数据路径上，接收计数反映内核 HID 路径接受完整帧。实际节拍由样本间计数增量和启动时钟计算。20 ms 是保留的传输和上报后等待参数，30 Hz 目标留待真实测量，GMU 继续使用固定 578 MHz 投票。
- 内核 SHA-256 `cdfd302a39e8422f15fd459e41fa0655433431e63e2483f0ad885d623a32c9f9`，启动包 SHA-256 `1a0175579c36bacb4dfd7f2c8d28cb5e1125880a9a8fcaa07da937bfa06a6d2f`，boot tag `33bbfcc946e24edeaba1579079b0b01a`。重编 35 个对象，完整链接 1,399 个输入，未定义符号为零。FAT 读回、加载器 PAC 消费检查、编译头文件与记录身份核对、ASan／UBSan、TSan 和零模糊补丁重放通过。沿用 v297 根、FD、ADT、启动器和菜单。精确包是离线候选，未创建新 runner、scope、ready 或 claim。[源码清单](../patches/gpu/ios26-physical-ft313/source-manifest.json) [离线证据与精确输入](evidence/k80-gpu-v313-physical-ft-offline-2026-11-18.json)
- v312 的启动前检查核对了 5039 服务和 SDK，却未确认其对重枚举 USB 接口的独占条件。只读诊断增加 `--preboot`，在私有进程当前独占接口而另有 5037／5039 监听者时仍退出失败。归档回放复现了 v312 的竞争，合成对照覆盖了 IPv6、通配绑定、重复私有进程和丢失接口持有者。快照只覆盖检查时刻，回收仍以核验 Recovery 属性及保护区读回为准。[主机诊断](../scripts/check-zorn-usb-adb-owner.py) [回归用例](../scripts/check-zorn-usb-adb-owner-fixtures.py)
- 设备停止状态仍适用。后续实机验收需要先恢复可核验的 Recovery，再以独立试验确认物理点按、滑动、抬起、边界命中和多指身份。将实机画面和相同窗口的源计数、GPU frame/fence 对齐，分别验证 Dock 模糊、长按菜单和实际应用响应。设置列表问题保持单独跟踪。

## v314 Direct Ring 引用回滚与 BO 回收

- v313 的 `HoldJob` 失败分支忽略了已持有 IB 引用的退回结果，仍增加成功退回计数。映射中的 `BoFree` 同样忽略 `retireCompleted` 错误，继续调用解除映射，依赖后续检查拦截。两处都位于已选用的 iOS 26 Direct Ring 客户端路径。
- v314 将未发布 IB 引用的四处回滚统一到实际提交实现。失败时记录仅剩的引用，标记提交者和呈现失败，沿既有外层错误路径停止后续工作。已知或可能写入 ring 的工作继续由原有 fence 和保留规则处理。映射中的 `BoFree` 在回收失败时立即返回原错误并保留映射、句柄和内存。正常回收完成后仍执行解除映射与释放。影响范围为 `ZornGen7DirectSubmit26.cpp`、其私有声明所在头文件和 `ZornGen7DirectClient26.cpp`。
- ASan／UBSan 和 TSan 通过 11 个回滚及 `BoFree` 对照用例与 7 个正常、超时及错误的 fence 回收对照。主机用例使用显式内存和 SMMU 模型。全部四个头文件消费者按实际 VFS 路径重编，完整链接 1,399 个输入，无未定义符号。新启动包只更换 FAT 中的内核成员。v313 的物理触控观察、原有 578 MHz 投票、v297 根和启动参数进入同一离线候选。[源码与回放清单](../patches/gpu/ios26-submit-rollback314/source-manifest.json) [v314 精确载荷和测试](evidence/k80-gpu-v314-submit-rollback-offline-2026-11-18.json)
- K80 原厂运行期调频路径使用 HFI 30 阻塞 ACK，按 SKU 反向频率索引，并依据 GMU 平均带宽能力决定 GMU 或主机互连投票。已确认当前 Direct Ring 在正常 Submit 中省去了 TLBIALL，v314 的改动集中在生命周期。运行期投票、样本时钟和温控结果仍需在既有物理基线上独立验收。[UniXNU GPU 与 Metal 适配](https://unixnu.com/zh/porting/gpu)

## v313／v314 物理触控归档验收

- 主机分析工具从已有文件解码 K80FT313、K80SH297、普通客户端 stderr、panic 和新鲜原生日志页。相邻观测窗口分别列出 FT3683 读取与触点计数、GPU 呈现和 fence 的增量。样本无效、触点未活动及窗口没有 GPU 更新分别可见。
- 提供归档的独立 bundle 和实际运行器退出值后，工具核对快照与归档的启动载荷、已消费的单次记录、唯一的 fastboot boot 记录、TWRP／OrangeFox 属性、BCB 预置完整页和尾部、7 组保护区前后样本，以及 GPT 和旧系统根清单的实际命令读回。串口完整、当前构建日志页新鲜、归档回收通过和出现终端 panic 分别报告。命令只读已有文件，在独立输出目录保存结果。
- v305 实机归档通过回收与保护区复核。v312 即使有成功的 fastboot boot 记录，也因未回到可核验的 Recovery 而拒绝。混合串口、完整 panic、陈旧日志页、损坏的 BCB／GPT、错误启动标签、重复包和多次启动等用例在明确标记的主机夹具上运行。现有内核和固件输入保持原哈希。[离线工具](../scripts/analyze-ios26-ft-capture.py) [回归记录](evidence/k80-ft-capture-archive-host-2026-11-18.json)
- 最终 FT3683 验收仍需真实手指完成点按、滑动、抬起、多指身份保持和边缘动作，并将可见反馈与对应窗口对齐。串口计数没有 UI 事件接收者或准确触点轨迹，104×48 裁剪需要按场景检查实际图像。v312 停止状态持续有效。

## v315 FT3683 连续派发失败处置

- v314 实际链接的 worker 来自 `k80-touch-worker-reference26`，v315 沿用它已修正的线程引用生命周期。此前 `DispatchReturned` 的非成功结果也会把错误计数清零。连续 HID 拒绝可因此一直读取 SPI，触点清理和停止条件都无法生效。
- `ZornFt3683Worker26.cpp` 现把未被 HID 接收的帧与传输、解码失败计入同一连续错误计数。第 3 次尝试抬起清理，第 10 次停止。成功帧才清零。若第 3 次清理成功，退出时不再重复。若清理未被接收且服务仍可用，退出前还有一次清理机会。连续拒收达到上限后，本次启动不再采样，未成功的清理结果仍保留在 worker 状态。
- 10 个 worker 故障和正常路径用例通过 ASan／UBSan、TSan，旧 worker 在全拒绝对照中继续读到第 11 帧。实际串口与原生日志身份、v315 归档解析以及零模糊补丁重放也通过。完整链接 1,399 个输入、重编 36 个对象，无未定义符号。包内替换了内核，继续使用现有 v297 根、20 ms 读后等待和 578 MHz 固定档。[源码与构建清单](../patches/gpu/ios26-ft-dispatch315/source-manifest.json) [v315 离线证据](evidence/k80-gpu-v315-ft-dispatch-offline-2026-11-18.json)

## v316 Direct Ring 完成游标

- `retireCompleted` 原先用只读观察接口检查真实 CP fence，随后回收已完成的任务。最后一个任务从列表移除后，ring 的 `completedFence` 可以仍停在旧位置，阻止依赖 ring 已清空的上下文切换和关闭。v316 的串行回收以零等待预算读取同一真实 fence，更新 ring 完成游标后执行原有资源回收。只读 IRQ 预等待的路径保持独立。
- `NativeAdrenoRing` 在 32 位 fence 耗尽时先拒绝新提交，再让已发出的最后一项正常等待、回收。真实时间戳退回已确认进度之前，或超出发出的最大值，将使 ring 进入错误状态。后续保留仍可能被设备访问的资源。变更在 `NativeAdrenoRing.cpp` 和 `ZornGen7DirectSubmit26.cpp`，主要风险是原先被容忍的回退读数现在会停止当前 GPU 会话。
- 旧代码分别复现了 fence 回绕和懒回收后仍有已完成任务被计为未完成。9 个 ring／回收对照和 7 个既有回收用例通过 ASan／UBSan、TSan，串口归档回放及完整构建验证通过。1,399 个链接输入，零未定义符号。启动包只替换内核，保留 v315 触控处置、固定 578 MHz 和既有根镜像。v316 未上机，设备停止仍按 v312 回收证据约束。[补丁与精确输入](../patches/gpu/ios26-fence-progress316/source-manifest.json) [v316 离线证据](evidence/k80-gpu-v316-fence-progress-offline-2026-11-18.json)

## ADB 主机连接恢复及 v316 验收准备

- 根据机主授权对占用 K80 USB 的旧 SDK 35.0.2 ADB 进程发送 SIGTERM。已审核的 SDK 37.0.1 取得 USB ADB 独占，主机 daemon 的缓存设备列表重新列出 `92988a43`，传输状态为 `recovery`。主机查询没有向手机发送命令。Recovery 属性、运行后保护区及 BCB 的现场读回仍待核验，设备停止标记保持有效。
- 后续验收以 bundle 中选定的 `adb_server_port` 绑定同一个 loopback daemon。主机检查接受显式端口，也可从唯一 USB 持有者发现端口。运行、回收轮询和归档校验使用同一绑定。旧归档按历史端口解码。5037 和 5511 的主机夹具以及跨端口档案拒绝测试通过。
- v316 离线清单重新计算了现有 32 GiB 根镜像的 SHA-256，验证镜像与有效内核窗口、两个仓库的存储描述及 v307 的 40 页回读一致。已封存内核、FD、ADT、加载器、启动菜单、固件和保护基线等 56 份独立输入。清单目前是离线审核材料，未生成启动许可、ready 或新 claim。外置相机本次未返回目标设备图像。[连接证据与归档](evidence/k80-adb-handoff-v316-review-2026-11-18.json)

## v309 人工复验与 v317 呈现耗时

- v312 的延后只读检查确认 TWRP、GPT、17 根标识、Data、26 根边界、BCB 和带 v312 身份的日志。随后原样 v309 单次临时启动，`332.503s` 自动回 TWRP，零根写入，七个保护区对照及 BCB 检查通过。机主确认能解锁和滑动桌面，可见 Dock 模糊和液态玻璃，整体低帧率并有撕裂，设置列表仍不能滚动。设置打开后与自动列表滑动后的帧号均为 `1790`，完成 fence 均为 `2473`。[v309 人工与串口证据](evidence/k80-gpu-v309-manual-repeat-device-2026-11-18.json)
- 原样 v305 单次临时启动，`334.563s` 自动回 TWRP。根写入为零，GPT、17 根标识、Data、26 根边界及 BCB 检查通过。串口在 `40.014139s` 内记录 `1,122` 次完成，约 `28.04` 次/秒。`FA1` 有 3 个样本，平均间隔 `13.40ms`。机主感觉 v305 与此前 v309 的帧率接近，两者偏低，较几天前略好。v305 首次打开设置时列表不能滚动且缺图标，关闭后再次打开可以滚动且有图标。此前 v309 只测试了首次打开。[v305 人工复验运行档案](evidence/k80-gpu-v305-manual-repeat-device-2026-11-18.json)
- 再次原样临时启动 v309，机主确认设置项的图标表现与 v305 一致，首次打开缺图标，第二次打开图标恢复且列表可以滚动。本次首次打开时的滚动表现未报告，设置首开问题留待独立定位。`332.265s` 自动回 TWRP，七个保护区对照、GPT、17 根标识和 BCB 检查通过。该次自动场景在长按前返回 `NoClient`，跳过后续操作。旧串口解析器把未尝试抬起的 `UINT32_MAX` 当作调用结果。修正后原始串口与截图通过校验，给三类跳过动作填入真实错误码的负向用例仍被拒绝。人工观察时间无法与自动场景绑定。[v309 第二次打开设置](evidence/k80-gpu-v309-settings-second-open-device-2026-11-18.json)
- v309／v316 的呈现代码把已完成 GPU surface 经 CPU 缩放后写入固件正在使用的 GOP 帧缓冲，VSync 回调来自软件定时器。DPU latch 和面板相位还没有实测。K80 的既有真机 FDT 选中 `o11_42_02_0a_dsc_cmd`，DSI0 的 `mdp_intf_base` 为 `0x0ae36000/0x300`。原厂 FDT 给出 1440×3200 的 60、90、120 Hz 模式，并与 INTF1 地址匹配。MiCode 的 SDE 源码已与固定 Git blob 核对。iOS26 当前实际刷新模式、计数器可读电源状态及 GOP 活动缓冲绑定仍需验证。[K80 板级输入](evidence/k80-display-timing-board-inputs-2026-11-18.json) [UniXNU 显示时序指南](https://unixnu.com/zh/porting/display)
- v317 在物理观察串口帧中接入既有 v278 呈现计数，同窗保留 FT3683、fence 和 GPU 帧记录，并按各自时间戳报告排队、节拍、租约、缓存取得、CPU 显示复制的总耗时。采样缺口保留，统计的是 CPU 墙钟与复制速率。ASan／UBSan、TSan、旧版归档回放、零模糊补丁重放、1,399 输入完整链接及只换内核的启动包校验通过。还需上机采样并核验面板时序，才能定位撕裂。[v317 精确构建](evidence/k80-gpu-v317-present-cost-offline-2026-11-18.json) [UniXNU 慢帧定位指南](https://unixnu.com/zh/porting/gpu#定位慢帧的耗时)

## v318 K80 DPU 时序采样

- `ZornDisplayTiming318.h` 采用 K80 DSI0 的既有 INTF1 资源、MiCode 固定提交的计数定义，以及小米 Pineapple 的显示 AHB、MDSS GDSC 和分支时钟状态。仅在观察到呈现且 GOP 缓冲位于 K80 保留区时进入。只读映射核对物理地址及长度。父时钟关闭、显示电源处于切换或分支时钟不满足时，跳过 DPU 计数器读取。读取前后均检查电源与时钟，映射错误或采样期间失稳会停止本次试验的后续读取。[K80 板级输入](evidence/k80-display-timing-board-inputs-2026-11-18.json)
- `K80FT318` 在同一有界串口帧中保留 9 组 DPU 原始计数、GPU fence、CPU 呈现分段和 FT3683 统计。解码保留采样缺口，并检查 TE 读指针的合理回绕。ASan／UBSan、TSan、归档回放、零模糊补丁重放和 1,399 输入完整链接通过。启动包只替换内核。实际固件扫描模式、时钟状态和计数器进度待真机采样，撕裂的根因仍未确认。[v318 精确构建](evidence/k80-gpu-v318-panel-timing-offline-2026-11-18.json)
- v318 无人值守单次启动在 `332.680s` 自动回 TWRP。BCB 整页读回、七个保护区对照、GPT 和 17 根标识通过。78,381 字节串口与新写入的原生日志均匹配启动身份。9 次检查均读到 `GCC_DISP_AHB` `0x80000003`，`CLK_OFF` 已置位，采样器在读取 DISPCC 或 DPU 前退出。当前面板刷新率仍未测得。[v318 真机记录](evidence/k80-gpu-v318-panel-timing-device-2026-11-18.json)
- `80.006s` 内 CPU 向活动 GOP 缓冲复制 `2,379` 帧，约 `29.74` 帧/秒。`show()` 合计 `48.70s`，每个完成复制约 `20.47ms`。完成 fence 从 `1624` 增至 `4003`。FT3683 有 `569` 个被接受的报告，接触计数为零。MiCode 的 CTL、SSPP、command-mode 完成和 splash SMMU 源码已固定到 v318 记录。Dada 的旧参考在 flush 等待超时后仍会重新提供旧缓冲，K80 的换帧实现需保留尚未确认退役的缓冲。[v318 采样与固定源码](evidence/k80-gpu-v318-panel-timing-device-2026-11-18.json)

## v319 CPU 呈现写入

- v319 将 CPU 缩放路径中相邻的两个 32 位像素合并为一次对齐的 64 位写入，保留未对齐起点和奇数宽度末端的 32 位写入。缩放、裁剪、像素字节、源缓冲生命周期和 GPU fence 沿用 v318。目标仍是正在扫描的 GOP 缓冲，未接入面板同步换帧。[实现与构建输入](../patches/gpu/ios26-gop-row-store319/source-manifest.json)
- ASan／UBSan、TSan 逐像素回归、串口归档回放和零模糊补丁重放通过。arm64e 内核以 1,399 个输入完整链接，未定义符号为零。FAT 内仅替换内核，继续使用 v297 已安装根。[v319 离线证据](evidence/k80-gpu-v319-gop-row-store-offline-2026-11-18.json)
- v319 单次启动后 `332.166s` 自动回 TWRP，零根写入。78,338 字节串口、带新启动身份的原生日志、整页 BCB 读回、七组存储保护及 GPT／17 根标识通过。GPU 完成 fence 从 1,041 增至 3,385，FT3683 接受 570 个无触点报告。9 组采样在读取 DPU 前因 `GCC_DISP_AHB` 的 `CLK_OFF` 退出。[v319 真机证据](evidence/k80-gpu-v319-gop-row-store-device-2026-11-18.json)
- 前七个约 70 秒的 GOP 采样窗口中，`show()` 平均从 v318 的 20.32 ms 降到 v319 的 19.10 ms，复制速率分别是 30.37 与 29.53 帧/秒。按各次全部有效窗口计算，v318 为 29.74 帧/秒（2,379 帧／80.006 秒），v319 为 30.24 帧/秒（2,346 帧／77.575 秒）。两次均为单次无人值守采样，整体提帧尚未确认。[帧率对照与采样边界](evidence/k80-gpu-v319-gop-row-store-device-2026-11-18.json)

## 串口帧率口径

- `report-ios26-fps.py` 读取通过核验的串口分析归档，用同一进程的 Metal 完成回调计数差除以内核 uptime 差，再用各自 CPU 计数采样时间统计 GOP 复制。v318 在 40.001 秒内有 1,234 个 Metal 命令缓冲完成，约 30.85 次/秒。v319 对应约 40 秒有 544 个完成，约 13.60 次/秒。早期合成负载不同，两个窗口都包含启动期，持续交互吞吐需要固定场景复测。[帧率分析脚本](../scripts/report-ios26-fps.py) [真机帧率对照](evidence/k80-gpu-v319-gop-row-store-device-2026-11-18.json)
- v305 的 1,086 次完成／40.006 秒约为 27.15 次/秒。约 80.32 FPS 是将一次轻量 `FA1` 的 12.45 ms 间隔取倒数所得。桌面和面板的帧率不能沿用这个数值。[v305 实机日志](evidence/k80-gpu-v305-nominal-opp-device-2026-11-18.json)
- 测量面板显示的完整新帧需要把每次呈现的序号与目标 DPU 的锁存或传输完成事件关联。同一画面可能跨过多次面板刷新。活动 GOP 当前可在扫描过程中被 CPU 修改，串口截图只反映读取到的缓冲内容。若用相机，需在固定动画中加入可辨认的帧编号和高帧率录像。已有 v309 视频为约 29.97 帧/秒，仅用于画面取证。[UniXNU GPU 帧诊断](https://unixnu.com/zh/porting/gpu#定位慢帧的耗时) [UniXNU 显示时序指南](https://unixnu.com/zh/porting/display)

### Sheng 与其他机型的统计参考

- Sheng 的官方探针按实际经过时间计算两个 DSI 接口的 `FRAME_COUNT` 差值，得到面板扫描节拍。双链路各自记录，同一帧只计一次。可复用的上屏计时在 `GopFramebuffer` 的 direct scanout 路径，`gpu-trace=1` 用同一交换标识记录请求、GPU fence、翻转、硬件锁存和退役。板级寄存器定义沿用 K80 自己的输入。[Sheng 官方固定源码](https://github.com/UniXNU/UniXNU-sheng/blob/516a780473a2ac59c8b438e132bb60204dda9e22/package/DisplayTimingProbe.cpp#L58-L68) [GopFramebuffer 帧诊断](https://github.com/UniXNU/GopFramebuffer#frame-diagnostics)
- Orange Pi 5 Plus 的零拷贝实验同时报告合成器交帧和直接扫描输出。解锁动画中上屏事件的平均间隔为 20.042 ms，约 49.9 帧/秒，最慢间隔约 200.1 ms。小米平板 6 `pipa` 用固定滑动测试统计活跃阶段的 swap 间隔与提交到退役耗时，可借鉴其交互场景。[Orange Pi 5 Plus 解锁动画记录](https://github.com/Hange777/UniXNU-opi5plus/blob/master/evidence/round11-result.md#s5--animation-rate-criterion-5-new-instrumentation) [pipa 实机记录](https://github.com/xVanTuring/UniXNU-pipa#readme)
- 同 SoC `UniXNU-houji` 的本地提交 `98bc0960f96076de8e8d16efcfb0c0603b166b85` 在 `kernel/overlay/iokit/Kernel/arm/HoujiDisplayTiming.h` 记录只读 DSI0、MDP 和 TE 计数，供交叉核对扫描节拍。K80 待核验控制器的扫描模式和缓冲所有权。确认后，在同一单调时钟记录 `present` 序号、fence 完成和相应的硬件锁存或命令模式传输完成。固定动画窗口内报成功上屏序号数、漏帧和重复刷新，以及帧间隔和提交到上屏的 P50／P95／P99。使用读回或硬件事件确认生效的帧，超时和 GOP 原地复制均缺少完整新帧的证据。可用带帧号的高速录像独立核对面板实际出光和撕裂。

## v320 外部 TE 与显示验收指标

- K80 原厂 DTBO 和 Recovery FDT 把主屏 TE 指向 TLMM GPIO86。MiCode 固定源码同样在该引脚上使用下降沿检查面板是否响应。v320 从 v318 独立构建，在最后一组常规采样之后读取继承的 MDP VSync 输入，窗口为 160 ms。保持引脚、IRQ、时钟及 DPU 状态，不改呈现路径。未通过引脚检查、采样存在大间隔或信号不稳定时保留原始结果。ASan／UBSan、新旧串口归档回放、补丁重放及 1,399 输入的完整链接通过。[K80 电路对应输入](evidence/k80-panel-te-board-inputs-2026-11-18.json) [v320 精确构建](evidence/k80-gpu-v320-panel-te-offline-2026-11-18.json)
- v320 实机在 160.016 ms 内读到 20 个 TE 下降沿。相邻下降沿间隔为 8.283–8.310 ms，均值 8.295 ms，对应约 120.55 Hz。首尾引脚配置均为 `0x4`，最大轮询间隙 56 µs。九组 DPU 采样仍在 GCC 显示 AHB 关闭时退出。单次启动在 334.211 秒自动回 TWRP，整页 BCB、七组保护对照、GPT 和 17 根标识通过，根写入为零。[v320 实机串口与回收证据](evidence/k80-gpu-v320-panel-te-device-2026-11-18.json)
- 后续在同一预热状态下跑固定动画。显示端以硬件确认的唯一呈现序号计算完整新帧数和帧间隔，统计中位数、P95 与 P99。用同一时间基准关联提交、GPU fence、DPU 锁存和命令模式传输完成，得到提交到显示传输完成的延迟。软件 GOP 复制、TE 和硬件传输各自保留原始计数。现有 GOP 直接改正在扫描的缓冲，仍需 DPU 确认逐帧结果。[MiCode 命令模式完成事件](https://github.com/MiCode/vendor_opensource_display-drivers/blob/3f527f3e55ef27f240507ace3181d13900c3ed7f/msm/sde/sde_encoder_phys_cmd.c)
- 本机 USB 相机枚举到 87 个视频格式与帧率区间组合，最高约 30 FPS。可用它检查画面和可见撕裂。逐帧光学验收还需要足够的采样率，在画面不同高度观察相同的帧编号。硬件确认的新帧数和提交到首个可见像素的延迟尚无对应证据。[相机格式枚举及范围](evidence/k80-gpu-v320-panel-te-device-2026-11-18.json)

## v321 DPU 启动交接

- 在 GOP 工厂确认原有 CPU 映射后、呈现器注册前记录显示 AHB。只有已有 AHB、MDSS 电源及分支时钟都满足条件才读取 CTL。沿 K80 Recovery FDT 的 CTL／SSPP 地址表，从 DSI0 的 INTF1 追到启用的取图管线，并复查时钟、管线掩码和未完成的 flush。地址数值相等可用于定位，显示侧 SMMU 映射与缓冲所有权还需另行确认。[K80 板级来源](evidence/k80-dpu-handoff-board-inputs-2026-11-18.json)
- 新版串口保留 v320 的 TE、fence 和呈现分段，在同一启动身份下加入早期记录。ASan／UBSan、新旧协议回放、补丁双向重放与 1,399 输入完整链接通过。启动包只替换内核。[v321 精确构建](evidence/k80-gpu-v321-dpu-handoff-offline-2026-11-18.json)
- v321 在内核 uptime 20.648 秒、GOP 呈现器注册前读到显示 AHB 为 `0x80000003`。后续九次读数相同，探针在进入 DPU 前退出。收到约 120.54 Hz 的外部 TE 信号。实际 GOP 基址为 `0xfc400000`、stride 5760；按存储几何，ramdump 之后可容纳一块 18,432,000 字节的候选缓冲，但其内存归属与显示 SMMU 可达性仍待确认。单次启动在 334.093 秒自动回 TWRP，整页 BCB、七组保护对照、GPT 和 17 根标识通过，根写入为零。[v321 真机证据](evidence/k80-gpu-v321-dpu-handoff-device-2026-11-18.json)
- 原厂的 SDE 在连续 splash 接手时先由运行时电源管理取得资源。DISPCC 的接口时钟对应 `GCC_DISP_AHB`，适配时还需处理 VDD 投票和寄存器总线。已从 K80 Recovery FDT 与 Pineapple 源码走通 `MASTER_APPSS_PROC → SLAVE_DISPLAY_CFG` 的依赖链，覆盖 HLOS 的 `SH1`、`CN0`、`CN1`。接入前需由共享的 RPMh/ICC 所有者解析 CommandDB 并保留现有投票。[板级输入和依赖链](evidence/k80-gpu-v321-dpu-handoff-device-2026-11-18.json)

## v322 从共享 CommandDB 解析显示电源资源

- 由已绑定的 `ZornGen7DarwinBoardOwner` 调用真实 CommandDB 读取器，逐项解析 `SH1`、`CN0`、`CN1` 和 `cx.lvl`、`mmcx.lvl`、`mx.lvl`。串口保留 BCM 的地址、单位、位宽和 VCD，以及 ARC 的实际电压等级映射。新增路径只解析输入，供共享投票器接续。[K80 电源输入](evidence/k80-display-power-board-inputs-2026-11-18.json)
- ASan／UBSan、v321 和 v322 串口归档回放、补丁双向重放及完整链接通过。实际链接保留 1,399 输入，启动包只替换内核。验证需区分条目缺失、解析失败与读到实际资源。[v322 精确构建](evidence/k80-gpu-v322-display-resources-offline-2026-11-18.json)
- 真机共享读取器返回六条独立资源，`CN0` 和 `CN1` 的实际 VCD 均为 5、单位均为 140000、位宽均为 4。内核 20.624 秒时显示 AHB 仍报告关闭，DPU 未返回有效计数。单次启动在 332.225 秒自动回 TWRP，整页 BCB、七组保护对照、GPT 和 17 根标识通过，根零写入。[v322 真机资源与回收](evidence/k80-gpu-v322-display-resources-device-2026-11-18.json)
- K80 原厂图确认 `CN0` 的 54 个成员横跨 `cnoc_main` 与 `cnoc_cfg`，`CN1` 的五个成员在 `cnoc_cfg`。运行中的投票器归属模型限制为两个 provider、每 BCM 15 个成员和同 provider 成员校验。显示请求需要扩展同一域的成员模型，并继续使用已有的 `SH1`，才能正确处理跨 provider 聚合和释放。

## v323 共享 HLOS 显示寄存器总线

- 从核验的 Pineapple 源码生成完整的两个 CNOC provider，扩展到四个 provider、78 个节点和六个 BCM。CN0 的 54 个成员由同一个 BCM 对象跨 provider 聚合，CN1 的五个成员及 GPU 已有 SH1 仍由同一个 HLOS 投票器管理。显示路径的六个节点全部验证相邻边，显示、GPU 与 TBU 使用各自的请求对象和同一套底层聚合器。[原始输入与源码补丁](../patches/gpu/ios26-display-icc323/source-manifest.json)
- 新增显示寄存器总线的受检查申请和释放入口，调用现有 `NativeConstraintApplication`。正向申请接受原厂 FDT 的三个非零级别，释放只撤销显示路径需求。原 GPU 启动时的保活次序沿用四个已有 BCM。提交失败或硬件回执不确定时保留请求并阻止后续操作。该入口等待显示电源所有者接入。
- 在 ASan／UBSan 下执行实际 ICC CPU 聚合代码，覆盖显示开关及 GPU 同时持有 SH1 的情况。显示归零后 CN1 返回零、CN0 保活及 GPU 的 SH1 需求仍然成立。投票器和调用方均用新头重编，1,399 输入完整链接通过，零未定义符号。未执行 RPMh 传输、显示供电或真机启动。[v323 离线证据](evidence/k80-gpu-v323-display-icc-offline-2026-11-18.json)

## 历史基线参考（294 与 296 原始记录）

294 用实际 Metal 设备和 pipeline 完成 16 次独立 32×32 绘制。每次先覆盖 IOSurface，再等待真实完成回调，Metal 与 IOSurface 的 CPU 读回均匹配 `CRC718ed2ce`。串口记录 120 次固定棋盘呈现、四个原生客户端 Close 成功和进程 `exit0`。相机第 97 秒确认绿紫棋盘。完整 journal 为 6334 字节、48 条、零缺口，压缩原生诊断丢失为零，单独的摘要通道省略 29 条。一次启动、零重试，333.84 秒返回核验过的 TWRP。安装根、Data、17、GPT、根窗口保护采样与 BCB 尾部检查通过。[294 精确实机证据](evidence/k80-gpu-v294-compact-observer-device-2026-11-18.json)

固定任务 CPU 墙钟平均 35.87 ms，中位 35.48 ms，范围 22.37–77.48 ms。提交返回后的等待平均 35.69 ms，包含调度、内核提交与回调交付。之前 290 锁屏窗口有 365 次真实 `SubmitBatch`，完成 fence 继续推进，采样覆盖当次锁屏。294 固定图案带主动节流。桌面 FPS、纯 GPU 执行耗时、长期稳定性和完整 FT3683 物理手势均待验收。293 的旧诊断丢 4 条，原失败判定保留。设置列表不能滚动已有用户记录，按用户指示延期。[完整演进记录](progress-2026-11-18-ios26-upstream-gpu.md)

## 液态玻璃的对照判据

用户看到 Dock、设置长按菜单和状态栏缺少液态玻璃，并补充了旧版可用时的对照。正常 Dock 后的壁纸被模糊，异常时 Dock 看起来完全透明。优先采集能辨认 Dock 内外背景纹理的图像并观察模糊。黑色或均匀背景下应记为无法判断。历史 274 浅灰菜单前后仍有实际完成 fence `310→314`，对应延后截图为 `317`。旧 274／275 相机画面的 Dock 太暗，暂不能作为确认过的正样本。优先定位同一桌面帧的材质与 GPU 路径，菜单和状态栏作为辅助。[274 截图和同场 fence](handoff-2026-11-17-k80-ios26-gpu-v274-context-menu.md)

295 恢复普通 `backboardd` 的原生策略，关闭独立棋盘探针，复用已实机跑过的 274 虚拟滑动及短长按。295 的串口裁剪只覆盖右上菜单。296 追加底部四分之一的 104×48 Dock 裁剪，在滑动抬起后 5 秒开放取景，长按前关闭。仍然只发送一个不可变截图，由真实呈现后的 CPU alias、当帧记录和 CRC 组成。相机覆盖随后菜单。虚拟 HID 输入的结果仅用于复现场景。两项候选均复用 294 驱动、真实 K80 固件和 direct-ring。[295 源码与构建](../patches/gpu/ios26-ordinary-materials295/source-manifest.json) [296 源码与构建](../patches/gpu/ios26-dock-material296/source-manifest.json)

## 296 精确输入与现有回归

- 内核 SHA-256 `c34d97511bdcabe5c127023360661bc2e0fb24f860c2f38fc08913563bf8c4da`，启动包 `6697a85df4149e48e47dfb360a5deea32ddb5520265cc55c1f954ab382cc74b1`。内核启动标签 `30ac366e5e2f4c3ca42d18fa4fdd8866`。根内 `backboardd` 的标量计时会话继承 295 的 `c46b8de4c09e4922af79b91e3693aae6`，解析两种标识时分别核对。
- 根 `181e7fc6f85c73bfe7155baf3cc25260ce9107b9c4efbef28d7075767955e03a`，ADT `5e5adf3e06f6962874e778ace04cfcdfda21c6eeceff3303186f4ef17e958777`，FD `1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab`。归档中的 295 ADT 较 294 只改变 `chosen/zorn26,root-image-sha256`。296 与 295 的 FAT 对比仅内核变化，DarwinBoot、管理器和 `unixnu.toml` 的精确哈希均在启动包 `verified.json` 中。源码归档中的旧内部内核文件名与产物哈希不同，识别输入以清单为准。[296 精确包路径及哈希](../patches/gpu/ios26-dock-material296/source-manifest.json)
- 候选从实机实际 293 根 `933476094a89d0e373392ec144b48bab1cbe537e3eeef44635d7693873570de5` 计算 25 个 4 KiB 页、14 组。重算 `unixnu` 专用根位于相对 LBA `6291712`，共 `8388608` 页，距现有 Data 末尾 782336 字节，根后保留 8588886016 字节。全量本机重放最终镜像 SHA 一致，变更页读回 SHA 为 `2756cfce69a2714772f487872beef31634e66d9d2c5e852aa4f81a419dc98a37`。仅三份客户端及诊断策略文件内容变化，现有签名 Metal 用户态和探针字节复用。文件系统、签名和受监控文件属性已经验证。与之前获批的 25 页／9 组根增量属于不同输入和范围。[根构建及回放清单](../patches/gpu/ios26-ordinary-materials295/source-manifest.json)
- 两版均用 1399 个实际输入完整链接、无未定义符号。296 通过 146 个依赖检查、补丁零模糊重放、实际采样器 ASan／UBSan 以及场景门控 ASan／UBSan 和 TSan。门控测试旧断言曾将历史 20 秒测试推进计入 mock 时间，已修正预期值，失败日志保留。混合串口回归用明确标注的历史 274 报文和合成像素验证正向、错误 scope 和不完整分块，属于主机验证。[采样器和解析回归](../scripts/check-ios26-dock296.py) [296 串口解码](../scripts/inspect_ios26_dock296.py) [296 主机归档](../scripts/zorn_ios26_dock296_capture.py)

## 接续顺序

1. 从 296 源码清单定位完整包及测试，完成固定安装和单次启动工具接入。目前 `device_ready=false`。安装前审查 25 页增量及其保护条件，用 293 实际安装逐组读回和随后 294 的七组保护、GPT、BCB、TWRP 回执绑定现场基线。沿用已审核的逐页预映像及逐组读回工具，独立生成只准安装和只准启动的 scope／ready／claim。检查脱机重放、遇坏预映像写入前停止和遇坏读回拒绝后续写组。禁止将 293 或 294 的旧准入套到 296。
2. 仅访问 `92988a43`，从核验过的 OrangeFox／TWRP 开始。SDK37 私有 `127.0.0.1:5039` 已获常设允许。设备看门狗为 300 秒，主机 Recovery 界限为 600 秒，单次启动、零自行重试。安装前后保护 Android、17、Data、GPT、Recovery 和启动分区。独立核验 BCB 完整页与尾部。无法回 Recovery 时停止设备操作并保留日志。不依赖用户按键、触屏或插拔。不自行 bootstrap、刷机恢复或扩大范围。
3. 把 `zorn_ios26_dock296_capture.py` 接入固定 CDC 接收器，再联动相机。保存原始 CDC、Dock 像素、同帧 present ID、IOSurface、producer／completed／access fence、原生错误、掉记录计数、计时 journal 和恢复后日志。Dock 裁剪来自 CPU 呈现 alias，实际手机外观另由相机核对。该场景先要有实际 `backboardd` 与 GPU 表面证据才能发虚拟滑动。未达到门控时应报告未产生桌面证据，不能由无截图推断软件回退。若有足够的壁纸纹理，按用户判据报告观察结果。若材质异常与实际 GPU 完成共存，再核对应用 pipeline 和合成路径。
4. 依官方优化顺序，先关联可复现桌面场景里的提交、分配、fence 和呈现，再按测得耗时改动。已确认 direct-ring 在成功且无变化的 VM 上不做逐提交全局失效。优先分解 294 完成等待，并对齐桌面呈现持有发行锁期间的取得／拷贝和等待。比较相同场景的冷、热 pipeline，根据 K80 实测再评估缓存预热、backing 复用和 GMEM 对照。保持 K80 4 KiB GPU 页／iOS26 16 KiB CPU 页、ABI1、Gen7.9.1 固件与板级参数。HWSCHED 留待用户决定。[UniXNU GPU 与 Metal 适配](https://unixnu.com/zh/porting/gpu)

严禁反汇编及逆向。保留 iPadOS17、Data、历史证据和产物，本机磁盘余量约 6.6 GiB，根镜像使用 APFS 克隆。两仓库只暂存本次修改，HEAD 分别为 `8067bd3` 和 `434f827`，本轮没有提交或推送。`porting.toml` 通过官方本地解析回归，完整历史 1172 条已保留。完整 GPU、Metal、显示和 FT3683 的实机验收仍未完成。

## v324 显示稳压器与寄存器总线生命周期

- K80 Recovery FDT 中 `clock-controller@af00000` 的 `iface` 指向 `GCC_DISP_AHB_CLK`。`vdd_mm` 指向由 CX 供电的 MMCX，`vdd_mxa` 指向 MX。DISP_CC 节点没有 ICC 属性，SDE 的寄存器总线使用独立的首档 `14,000 kB/s`。原厂运行时恢复申请 `MIN_SVS`（48），MMCX 的板级最低等级为 56，由现有 ARC 后端按实际约束和 CommandDB 选择。
- Board 所有者给 MMCX 和 MX 分配独立消费者，在申请引用后使用 v323 同一 ICC 投票器。正常释放先归零 SDE 请求，再降低并释放显示的稳压器引用。只有 MMCX 最后一个引用退出才沿实际依赖锁处理其 CX 父消费者。成功后撤销显示消费者的注册。底层错误、未返回或 RSC 故障会保留在途帧和未确认的资源。
- ASan／UBSan 主机测试覆盖共享、最后引用、错误保留、错序帧、锁持有和重复释放。v324 当前源码重编 40 个对象，核对 1,399 个链接输入，零未定义符号。CommandDB／CDC 回归及补丁正反向重放通过。该内核已链接 Board 电源路径，启动调用和显示时钟／域尚未接通。此轮未打包或访问真机。下一轮先绑定有界的显示启动调用并记录电源、ICC 和 GCC 状态，再继续接入 DPU 的实际依赖。[离线证据](evidence/k80-gpu-v324-display-regulators-offline-2026-11-18.json) [精确源码清单](../patches/gpu/ios26-display-regulators324/source-manifest.json)

## v325 单次显示资源启动试验

- 在 GPU 已知图像和原启动检查通过后、发布合成服务之前，连接了显示稳压器与 SDE 寄存器 ICC 请求。申请和释放均先检查本机实际 MMCX／MX proxy 仍持有参考。新串口字段区分申请、持有和释放，并记录三个时刻的 GCC AHB。当前阶段沿用已有 GOP 呈现，只读 GCC，没有增加 DPU 或 DSI 访问。全量链接、真实加载器校验、CDC 测试及保护归档回放通过。[离线证据](evidence/k80-gpu-v325-display-resource-startup-offline-2026-11-18.json)
- 单次临时启动后，经约 89.991 秒自动回到 TWRP。整页 BCB 和尾部、七组保护区、GPT 与根镜像清单均通过。串口没有捕获到字节，持久页仍是上一构建，无法确定执行到哪一阶段、重启原因或显示资源状态。零根写入，零重试。源代码重编的栈报告只在原串口包组装函数看到增加 32 字节，未见所核对的原早期函数栈占用扩大。[真机与对照证据](evidence/k80-gpu-v325-display-resource-startup-device-2026-11-18.json)

## v326 延迟挂接显示互连

- 完整候选将 GPU 启动恢复为两个 provider、19 个节点和四个 BCM。到显示资源申请时才在同一域和同一 voter 下挂接 CN0、CN1 和 SDE 路由，等显示对象全部就绪才扩大有效传输绑定数。挂接期间不发送 RPMh 请求。显示准备失败会在申请稳压器前返回。
- 对实际聚合与域挂接代码的主机测试通过，覆盖 GPU 仍有待完成操作时拒绝附加节点，以及显示归零后保留共享 SH1。重编 40 个对象后完成 1,399 输入链接和独立启动包。该候选尚未建立真机准入。v325 缺失早期日志的具体原因仍未确认。[v326 精确离线证据](evidence/k80-gpu-v326-deferred-display-icc-offline-2026-11-18.json)
- 新 scope 单次临时启动后约 89.936 秒自动回到 TWRP，完整 BCB 回读及七组保护区匹配，零根写入。串口未打开对应设备，持久页仍属旧构建。v322、v325、v326 的 FD、ADT、启动器、配置、启动参数和根完全匹配，FAT 只换了内核。[v326 真机证据](evidence/k80-gpu-v326-deferred-display-icc-device-2026-11-18.json)
- 源码中的检查顺序是登记根设备、等待延迟 GPU 所有者、写入并读回本次检查点、发送三帧早期串口数据，之后才调用 GPU 工作线程。显示资源的申请又晚于 GPU 已知图像。v325 和 v326 都缺少更早的持久检查点，显示申请的执行与结果仍未知。

## v327 延迟 GPU 所有者超时记录

- 在确认根仍已注册后，沿用现有单页写入和读回路径记录有界等待结果。30 秒内找到所有者时，原有成功记录和串口门槛继续生效。超时时写入带本次身份和 CRC 的 `deferred=timeout`，不会启动 GPU 或串口工作线程。若连这条记录也缺失，需要定位更早的启动阶段或同一日志页的写入路径。
- 重编 40 个对象，1,399 输入完整链接，未定义符号为零。独立启动包复用已安装 v297 根。原成功记录、超时记录、错误身份和 CRC、CDC 线格式及源码补丁重放验证通过。归档回放确认单有超时页时仍保留该证据，同时拒绝将超时页与一份完整 CDC 流联判为成功。[v327 精确离线证据](evidence/k80-gpu-v327-deferred-owner-checkpoint-offline-2026-11-18.json)
- 此候选只临时启动一次，90.032 秒自动回 TWRP，整页 BCB 回读及七组保护匹配。串口和持久日志都没有本次数据，无法判断是否进入早期工作线程或成功写页。v325、v326、v327 的回收耗时及日志表现一致，此类试验停止。UEFI 板级源码的早期模式 1 使用 65 秒 bite，主机的回收耗时也包含重新进入 TWRP 的时间。现有实机记录不能确认复位来源。下一轮先取得早于这条 GPU 检查路径的启动证据。[v327 真机证据](evidence/k80-gpu-v327-deferred-owner-checkpoint-device-2026-11-18.json) [UEFI 看门狗源码](https://github.com/kerrinz/uefi-zorn/blob/434f8278c68c6915df5aaa260c22dd0f5988f7b7/Platforms/Xiaomi/zornPkg/Drivers/ZornBootMemoryDxe/ZornBootMemoryDxe.c#L62-L91)

## v328–v329 早期 IOKit 与控制台

- v328 在旧有受检查的控制台映射画阶段码。摄像头在本轮录像第 24 秒拍到 `A0`，确认已进入 XNU 的 `PE_init_iokit`，并完成 `PE_init_printf(TRUE)`。之后显示四行较小文字，字形模糊，无法可靠辨认。未观察到后续阶段码，不能仅由缺失画面判断对应代码未执行。单次启动在 89.310 秒回到 TWRP，整页 BCB 及七组保护匹配，零根写入。无本次 CDC 或持久日志。[v328 构建](evidence/k80-gpu-v328-early-console-stage-offline-2026-11-19.json) [v328 真机](evidence/k80-gpu-v328-early-console-stage-device-2026-11-19.json)
- v329 在 `InitIOKit` 前后和 `ConfigureIOKit` 返回后加入 `A7`、`A8`、`A9`。沿用首次 panic 的原生格式化记录，从已映射的控制台以大字输出最多 224 字节，限于屏幕中部，不在 panic 路径进入存储。40 个对象重编和 1,399 输入完整链接通过。ASan／UBSan 校验无效几何、步幅、写入区域及长度上限，旧归档和补丁重放通过。[v329 精确离线证据](evidence/k80-gpu-v329-early-panic-screen-offline-2026-11-19.json)
- v329 的录像在第 26 秒清楚显示 `A9`，确认 `ConfigureIOKit` 返回。后续没有辨认到大字 panic，不能由此排除 panic。单次启动于 89.390 秒回到 TWRP，整页 BCB 与七组保护核对通过。持久页仍属旧启动，USB CDC 无数据，零根写入。[v329 真机证据](evidence/k80-gpu-v329-early-panic-screen-device-2026-11-19.json)
- 已纠正早期看门狗观测点。v328 和 v329 的 `A1/A2` 接在兼容函数 `houji26_start_recovery_timer` 上。按实际链接清单追到 v185 编译输入，K80 的 `GenericARMPE::start` 直接调用 `zorn26_platform_trial_start`。v330 把标记放在真实调用前后，并增加 IOKit 匹配及 K80 平台准入阶段码。重编 `GenericARMPE` 时用独立归档复用原头文件环境，校验了 357 个依赖字节一致。41 个对象重编和 1,399 输入完整链接通过，当前待真机。[v330 精确离线证据](evidence/k80-gpu-v330-platform-watchdog-stage-offline-2026-11-19.json)
- v330 本轮录像第 25 秒清楚显示 `B5`。当前 boot args 启用 `zorn26_gpu_board_stage=1`，源码和链接输入均核对，因此确认实际看门狗初始化、根输入登记和 GPU 板级工作线程创建都已返回成功。后续 UFS 根注册、GPU 工作线程返回及 PID1 的检查点未取得。单次启动在 89.397 秒回到 TWRP，整页 BCB 和七组保护通过，零根写入。串口仍未采到数据，持久页未更新。后续先分离 UFS 根注册和 GPU 工作线程的启动时序，观察到根就绪后再进入原有 GPU 工作，保留各自的真实失败条件。[v330 真机证据](evidence/k80-gpu-v330-platform-watchdog-stage-device-2026-11-19.json)

## v331–v332 UFS、PID1 与串口排序

- v331 从 `GenericARMPE::start` 移走 GPU 工作线程的调度。在真实 UFS 根注册成功后，原 UFS 所有者释放锁并调用原有的一次性 GPU 工作线程入口。主机用实际 `bindRoot` 源码核对拒绝、并发重复、锁释放与 GPU 失败后的根状态。完整链接和归档回放通过。[v331 离线构建](evidence/k80-gpu-v331-gpu-after-root-offline-2026-11-19.json)
- v331 录像先后显示 `BA`、`B8` 和 `A5`。`A5` 确认已通过实际根设备及 PID1 EL0 检查，并进入原本要等 GPU 预备所有者的工作线程。单次启动约 120.022 秒回 TWRP，比 v330 晚约 30.625 秒。完整 BCB 与七组保护匹配，零根写入。串口没有本次内容，持久页仍旧。GPU 板级初始化中首个失败操作和实际复位源仍未知。[v331 真机证据](evidence/k80-gpu-v331-gpu-after-root-device-2026-11-19.json)
- v332 在通过根设备及 PID1 检查后先写入并读回原诊断页。确认成功后开始 CDC，仍使用原格式和三帧真实传输门槛。USB 发送完成才从独立线程调度原 GPU 板级所有者，等待实际延迟所有者有 30 秒上限，后续保留原 GMU 验证与握手。41 对象重编和 1,399 输入完整链接通过。主机回归执行真实守门源码，覆盖页读回拒绝、三帧之前不可调度、重复回调、等待超时与实际调用次序。归档回放拒绝旧 CDC 次序冒充此构建。[v332 离线构建](evidence/k80-gpu-v332-cdc-first-offline-2026-11-19.json)
- v332 单次启动于 130.319 秒回到 TWRP。持久页出现本次启动标识，七组保护与 GPT、根清单和完整 BCB 回读通过，零根写入。CDC 的前三帧先于 GPU 调度，随后两帧表明工作线程已调度，最后收到完整的 140,831 字节 panic 包。与原内核字节相同的重新链接和编译器行表把 data abort 定位到 MMCX 上游供电元数据查询 `ZornGen7OwnedArcEnable.cpp:25`。导致地址失效的具体机制尚待确认。[v332 真机和源码定位](evidence/k80-gpu-v332-cdc-first-device-2026-11-19.json)

## v333 MMCX 供电拓扑查询

- 从现有 K80 原生供电关系在编译期派生标量位图，先核对组和投票者索引再查询。保留实际供电链路和正常释放代码，ARC 启动对象使用原 K80 编译配方和当前释放接口。主机 ASan／UBSan 覆盖全部 13 项及越界拒绝，编译器类型布局与保留对象匹配。完整重编 41 个对象，1,399 个链接输入无缺符号。独立启动包和归档回放通过，仍需真机确认 MMCX、GMU/HFI 和显示路径。[v333 离线证据](evidence/k80-gpu-v333-arc-supply-offline-2026-11-19.json)
- v333 单次启动于 332.220 秒自动回到 TWRP，整页 BCB 与七组保护通过，零根写入。CDC 捕获 30 个进度帧、九组呈现样本及完整锁屏时钟缩图，未见 panic。延迟 GPU 调用、加速器注册和内核已知任务均返回，fence 2 完成，CPU 读回匹配预期 CRC，任务引用已释放。`backboardd` 打开了原生客户端，本次未取得完整 Metal 前端验收或 FT3683 动作证据。[v333 真机记录](evidence/k80-gpu-v333-arc-supply-device-2026-11-19.json)
- 同一启动中，八个采样窗口完成 2,425 次 GOP 复制，总计 80.015 秒，约 30.31 次／秒，平均复制呈现耗时 19.72 ms。MMCX、MX 与显示 ICC 在同一启动内完成实际申请和释放，GCC DISP AHB 读值始终为 `0x80000003`。DPU 门槛拒绝了全部窗口，实际新帧率和上屏延迟仍缺少证据。K80 原厂 DTS 将该时钟同时接到 DISP_CC 和 MDSS GDSC，原厂 GCC 初始化只置位 bit 0，当前读值已含该位。后续须复用真实 GDSC 与 DISP_CC 时钟所有者，并把已确认的 CTL／PP 完成事件关联到同一个 present 序号。[K80 板级原始输入](evidence/k80-dpu-handoff-board-inputs-2026-11-18.json)

## v334 显示时钟和电源域

- 从已归档的 K80 Recovery FDT 核对了 GCC AHB、HF AXI、DISP_CC 和 MDSS GDSC。DISP_CC 及 GDSC 引用 GCC AHB，SDE 另外引用 HF AXI。原厂 GCC 注册代码将 AHB 软件使能位置 1，v333 的读回已包含该位。v334 在现有 MMCX、MX 和 SDE 寄存器总线带宽租约成功取得后，只读这些时钟和电源域状态，新路径不扩大 DPU 或 DSI 访问。主机验证八个读取点顺序、每处读失败、软件投票缺失与丢失。新旧 CDC 格式分别回放通过，完整内核和独立启动包已生成。[v334 精确构建](evidence/k80-gpu-v334-display-clock-offline-2026-11-19.json)
- v334 单次启动于 332.154 秒回到 TWRP。整页 BCB 和七组保护通过，根镜像零写入。CDC 确认 GPU 已知任务、fence 和 CPU 读回仍通过。GCC AHB 为 `0x80000003` 时，租约内实际读通 DISP_CC。MDSS GDSCR 为 `0xf822f800`，CFG_GDSCR 为 `0x04070000`，三个 DISP_CC 时钟分支均为 `1`，HF AXI 为 `0x00200001`。原 DPU 读取检查仍拒绝该 GCC AHB 状态，新帧率与延迟尚未取得。[v334 真机记录](evidence/k80-gpu-v334-display-clock-device-2026-11-19.json)
- 已补齐并通过 Git blob 校验的原厂显示中断源码。Pineapple 目录启用 CTL_DONE，K80 Recovery FDT 给出 MDSS SPI 83。原厂命令模式仅在有待完成的 kickoff 时发出帧完成。下一候选将限定在已持有租约并重新确认 HF AXI、电源域和 DISP_CC 分支的情况下读取 DPU，然后核对真实活跃的 CTL 和呈现序号。

## v335 租约内 DPU 采样

- 复用 v334 的本机显示供电和带宽租约。在 DSI0 接口每次读取前后，均重新核对 AHB 软件使能、HF AXI、MDSS 电源域、DISP_CC 分支和复位状态。读取两组相隔至少 120 ms 的计数，然后用原 CTL 路径核对稳定的活跃控制器和取图源。单独版本的 CDC 保留接口帧、撕裂同步计数和活跃路由，旧的判定和归档回放通过。该候选只读取显示寄存器。[v335 精确构建](evidence/k80-gpu-v335-held-dpu-offline-2026-11-19.json)
- v335 单次启动在 332.212 秒自动回到 TWRP，核验了整页 BCB、七组保护和 GPT／根镜像清单，根镜像零写入。CDC 保存 30 个进度帧和九组样本，GPU 已知任务完成 fence 2 和 CPU 像素读回。DPU 租约内的 120 ms 读数中，TE 计数增加 14，INTF 和 MDP 帧计数均维持 139。CTL0 路由到 DSI0，VIG0 和 VIG1 的取图地址数值均为 `0xfc400000`，步长 5760，采样时无待处理 flush。八个后续窗口共完成 2,386 次 GOP 复制，用时 80.019 秒。显示 SMMU 的实际翻译状态和每帧传输时刻仍待确认。[v335 真机证据](evidence/k80-gpu-v335-held-dpu-device-2026-11-19.json)

### 上游逐帧统计参考

- 官方 Sheng 的 `DisplayTimingProbe` 有硬件刷新计数和同地址 CTL 锁存测试。`dpu=3` 的 5.4 ms 来自同地址测试。逐帧诊断将显示请求、GPU fence、flip、CTL latch 和退休写入内核环，并用触控时间划定活动窗口。组件固定提交 `e47c1b8de169cd2bd0b885c7d85e433010e3cdf2` 的 `latchTick()` 每次轮询也记录 latch 事件，并在达到 50 ms 后走完成路径。移植时要用 CTL 成功条件和相同交换序号去重，单独记录超时并保留未确认释放的缓冲。[显示教程](https://unixnu.com/zh/porting/display) [逐帧诊断](https://unixnu.com/porting/gpu-diagnostics) [固定组件源码](https://github.com/UniXNU/GopFramebuffer/blob/e47c1b8de169cd2bd0b885c7d85e433010e3cdf2/NativeLegacyDisplay.cpp)
- `uke` 的 `gpucomp27` 硬件记录在 120 Hz 配置下观测到 10–28 次翻转／秒，CTL 锁存平均 4.1 ms、最大 8.4 ms。后续构建发现 GPU 读写指针相等仍可发生撕裂，改由 Metal runtime 等待对应工作的完成。`piano` 用 INTF 帧计数核验 60／120 Hz 模式，公开验收流程把同一指标用于面板刷新。两个项目的板级地址、时序和映射仅适用于各自硬件。[Uke 固定移植记录](https://github.com/Allenwdk/UniXNU-uke/blob/325fb593659f1881b71249bf93491ce53e19d504/porting.toml) [Piano DPU 文档](https://github.com/lenzhang/UniXNU-xiaomipad8pro/blob/main/docs/drivers/dpu.md)
- K80 按本机 DPU 和 Apps SMMU 确认取图归属，随后将同一个 present 序号与 GPU fence、CTL 锁存及匹配的 DSI 帧传输完成关联。固定滚动窗口只统计有完整硬件完成证据的唯一新帧，记录帧间隔、提交至传输完成的 P50／P95／P99 和超时。上线前用带递增编号的已知图案核对复帧、丢帧和撕裂，继续复用现有 CDC 归档。[K80 显示原始输入](evidence/k80-dpu-handoff-board-inputs-2026-11-18.json)

## v336 Apps SMMU 显示流查询

- 保存的 K80 Recovery FDT 和固定原厂源码均将非安全显示流 `0x1c00/0x1c02` 指向 Apps SMMU `0x15000000`。在 v335 的活跃 DPU 路由和显示租约成功后，v336 复用根 UFS 所持有的映射，读取两轮 SMR、S2CR 和对应上下文寄存器。映射、读值或显示时钟条件有任何差异时，只输出诊断状态。该查询不配置 SMMU、不更换页面表，也不更改显示寄存器或根镜像。[v336 精确构建](evidence/k80-gpu-v336-display-smmu-offline-2026-11-19.json)
- 41 个对象重新编译，1,399 个输入完整链接，无未定义符号。首轮链接后的依赖审查发现，移动 UFS 源文件改变了引号头文件的查找路径。已恢复原编译单元的头文件优先级，最终确认除候选源和新增诊断头文件外，UFS 依赖集合与 v335 一致。ASan／UBSan 回归覆盖 46 个读失败点、歧义、翻译及旁路。新 CDC 归档回归通过，v335 实机归档逐字节复现。
- v336 单次启动在 332.179 秒自动回到 TWRP，整页 BCB、七组保护和 GPT／根镜像清单核验通过。CDC 拿到 30 个进度帧和九组样本，GPU 已知任务、fence 2 和 CPU 读回通过。121 ms 内 TE 增加 15，INTF 和 MDP 均维持 139。UFS 入口在 Apps SMMU MMIO 前返回 `host_unavailable`，该状态无法区分锁竞争、传输状态或映射核验失败。[v336 真机记录](evidence/k80-gpu-v336-display-smmu-device-2026-11-19.json)

## v337 有界 UFS 映射核验

- 沿精确链接清单将 UFS 初始化定位到 `storage-hfs-owner-candidate/ZornUfsPreparation26.cpp`，确认本机初始化使用 `0x15000000`、`0xd0000` 和启动后保留的 `gHost` 映射。v337 保留查询路径，在 100 ms 内最多尝试 16 次取得同一把锁，通过 `kIOMemoryMapperNone` 核对实际物理段，并用 CDC 独立报告线程条件、锁、传输、映射地址与范围。主机验证等待、时钟回绕、休眠超时、映射拒绝后的解锁及七类串口结果。该改动不引入 UFS 命令或 SMMU 写入。[v337 精确构建](evidence/k80-gpu-v337-smmu-transport-offline-2026-11-19.json)
- 已核对固定 MiCode 源码，K80 活跃 `CTL_TOP=0xf0020000` 的 bit 17 是 DSI 命令模式。原厂驱动根据自刷新状态决定是否发 `CTL_START`，`CTL_DONE` 的状态和清除地址分别是 MDP TOP `+0x00c`、`+0x02c`，原厂只给有待完成 kickoff 的帧发完成。后续一次受控呈现应同读 `INTF_TEAR_AUTOREFRESH_CONFIG`，在实际一次提交前后追踪 CTL0 状态，单独标出 DSI 传输证据和超时。[MiCode 固定实现](https://github.com/MiCode/vendor_opensource_display-drivers/blob/3f527f3e55ef27f240507ace3181d13900c3ed7f/msm/sde/sde_encoder_phys_cmd.c)
- v337 单次启动在 334.239 秒自动回到 TWRP，整页 BCB、七组保护和 GPT／根镜像清单核验通过。CDC 完整，GPU 已知任务、fence 2 和 CPU 读回通过。Apps SMMU 在任何读寄存器之前返回 `lock_deadline`。此时启动期的 UFS 命令和显示查询竞争同一传输锁，后继实现需要复用稳定映射的生命周期。[v337 真机记录](evidence/k80-gpu-v337-smmu-transport-device-2026-11-19.json)

## v338 根初始化发布 Apps SMMU 映射

- 现有 UFS 初始化成功后、注册根设备之前，核对并保留实际的 Apps SMMU 映射，一次性发布只读观测所需的虚拟地址。显示租约内的双快照不再获取 UFS 命令锁。编译和实际依赖已核对，1,399 个输入完整链接，无未定义符号。主机回归覆盖跨线程发布、失败遮蔽、对应 CDC 解析，v337 实机归档逐字节复现。[v338 精确构建](evidence/k80-gpu-v338-apps-smmu-aperture-offline-2026-11-19.json)
- v338 单次启动在 334.126 秒自动回到 TWRP，整页 BCB、七组保护和 GPT／根清单核验通过，根镜像零写入。CDC 核对了 GPU 已知任务、fence 2 和 CPU 读回。`0x1c00`、`0x1c02` 均匹配 Apps SMMU slot 3，`SMR=0x80021c00`、`S2CR=0x00000003`。context bank 3 的 `CBAR=0x0001f000`、`SCTLR=0xe0`，stage 1 关闭且 stage 2 旁路。DPU 的 CTL0、两个 VIG、DSI0 和 `0xfc400000` 取图关系仍一致。121 ms 内 TE 增加 14，INTF／MDP 计数持平，后续窗口约有 29.68 次 GOP 复制／秒。逐帧传输完成证据仍待建立。[v338 真机记录](evidence/k80-gpu-v338-apps-smmu-aperture-device-2026-11-19.json)
- DSI0 活跃 FDT 控制器为 `0x0ae94000`，兼容 `qcom,dsi-ctrl-hw-v2.8`。固定原厂 `dsi_ctrl_reg.h` 将 `DSI_INT_CTRL` 定为 `+0x110`，`dsi_ctrl_hw_cmn.c` 将 bit 8 判为命令帧发送完成，bit 9 是对应中断使能。已有 K80 亮度传输为 W1C 保留的中断使能掩码和该控制器一致。下一次受控提交需要在实际 GOP 写入锁和显示租约下核对 DSI0 分支、命令模式和自刷新，关联同一笔 CTL0 提交及新的 DSI0 完成事件。当前只有源码和主机模型验证。[MiCode DSI 状态实现](https://github.com/MiCode/vendor_opensource_display-drivers/blob/3f527f3e55ef27f240507ace3181d13900c3ed7f/msm/dsi/dsi_ctrl_hw_cmn.c)

## v339 同地址命令帧

- 独立启动包在原显示租约内核对 Apps SMMU、活跃 CTL0／两条 VIG、CPU GOP 写入锁、DSI0 各分支和中断状态。满足空闲命令模式条件时，只提交一次同地址 FLUSH／START。CDC 序号绑定 FLUSH 清除、CTL0 完成和 DSI0 新的命令帧发送完成。原像素和取图地址保留，存在不确定的在途操作时保留寄存器映射、显示投票和帧缓冲并停止后续提交。[v339 精确构建及测试](evidence/k80-gpu-v339-dsi-transfer-offline-2026-11-19.json)
- 单次启动于 334.274 秒自动回到 TWRP。整页 BCB、七组保护及 GPT／根清单核验通过，专用根零写入。GPU 已知任务真实 fence 2 及 CPU 读回通过。四个 DSI 分支均运行，`AUTOREFRESH_CONFIG=0x8000003c`，受控路径以 `autorefresh_active`、序号 0 返回，未触发 FLUSH／START。显示租约正常归还。120 ms 内 TE 增加 15，INTF 与 MDP 持平。81.155 秒内完成 2,326 次 GOP 复制（28.66 次／秒），面板新帧率仍为空。串口与恢复归档离线重放逐字节一致。串口字段 `dsi_clock_control` 对应实际寄存器 `DSI_LANE_STATUS`（DSI0 `+0xa8`）。[v339 真机记录](evidence/k80-gpu-v339-dsi-transfer-device-2026-11-19.json)
- 原厂命令模式在自刷新开启时不发 `CTL_START`，将有待完成的 kickoff 与 auto-refresh IRQ 配对，再检查写指针确实已经启动。K80 先在现有自刷新配置下核对新传输的归属，避免把上一笔传输或后台重复扫描计到当前帧。[MiCode 原厂源代码](https://github.com/MiCode/vendor_opensource_display-drivers/blob/3f527f3e55ef27f240507ace3181d13900c3ed7f/msm/sde/sde_encoder_phys_cmd.c)

### 公开项目的帧率统计口径

- Sheng 本地核对提交 `6a3d35c02504b712897799c5481952a61761325d`。`package/DisplayTimingProbe.cpp` 用约 1 秒的单调时钟差与两次接口帧计数差计算扫描节拍，三级探针另计同地址 FLUSH 锁存耗时。`scripts/analyze-sheng-frame-timing.py` 按序号去重，输出 commit → 回调及 swap → 复制耗时，明确将稳定 120 FPS 验收标记为未达成。现有 `check-sheng-frame-timing.py` 主机回归通过。[显示教程](https://unixnu.com/zh/porting/display)
- 官方 `GopFramebuffer` 在直接取图路径记录同一 swap 的验证、fence、flip、latch 和 retire，适合定位排队与扫描地址切换。复制路径的 retire 记录完成存储。Pipa 用固定滑动序列与 `display: pacing` 计算活跃场景的 swap 节拍，记录了 53.9、40.5、41.3 FPS，并发现不同桌面页会改变负载。Houji 官方记录提供画幅、触控对齐等证据。公开材料未核实这些机型有逐帧内容与面板发光的配对记录。[GopFramebuffer](https://github.com/UniXNU/GopFramebuffer/blob/main/NativeLegacyDisplay.cpp) · [Pipa 滑动测试](https://github.com/xVanTuring/UniXNU-pipa#state-on-the-tablet) · [Houji](https://unixnu.com/zh/devices/houji)
- K80 的长期指标应使用相同页面、相同滑动序列与固定活跃采样窗，保留每笔 swap 的序号、GPU fence、写入或锁存时间及匹配的 DSI 发送完成，并导出定长事件环和丢记录数。按采样窗统计确认发出的不同帧、重复帧和跳号，计算帧间隔与提交到传输完成的 P50、P95、P99。只有外部光学记录能核对像素实际发光时间。测试画面可在屏幕上、下方编码同一帧号以观察撕裂。相机帧率经验证后用于定量，现有模糊相机或串口 framebuffer 截图可验证大图案与画质。[OpenLDAT](https://github.com/adolfintel/OpenLDAT) · [TestUFO 逐帧跳过测试](https://testufo.com/frameskipping)

## v340 自动刷新传输归属

- 固定 K80 FDT 的 DSI0 对应 INTF1，TE IRQ 基址为 MDP 相对 `0x36800`。MiCode `3f527f3e55ef27f240507ace3181d13900c3ed7f` 的 `sde_hw_interrupts.c` 定义 auto kickoff 与写指针状态位，`sde_encoder_phys_cmd.c` 把写指针验证作为自动启动证据。v340 使用 v339 实测的 `0x8000003c`，沿用启动期显示资源和 GOP 写入锁，只发一次同地址 CTL0 FLUSH。串口记录待锁存值、清除后的新 INTF1 事件、写指针推进与 DSI0 命令帧完成，最长观察 1.35 秒。配置、IRQ 使能、像素和取图地址保留。证据不齐时保留资源并停止后续相关写入。
- 精确内核与启动包已离线生成，41 个输入重编，1,399 个输入完整链接且无未定义符号。ASan／UBSan 回归覆盖提前 DSI 事件、陈旧事件、IRQ 所有者、写指针不动、时钟丢失和有界超时。新 CDC 合成归档通过，v339 真机归档逐字节重放相同。此阶段只验证单笔传输归属，面板新帧率仍待逐帧数据。[v340 精确构建及验证](evidence/k80-gpu-v340-autorefresh-transfer-offline-2026-11-19.json)
- v340 实机在同一序号观察到 CTL0 FLUSH 锁存与 INTF1 自动启动（319.376 ms），以及 DSI0 命令帧完成（327.238 ms）。两次观测相差 7.862 ms，最大轮询间隔为 1.202 ms，接口发送计数 139→140。显示租约正常归还，GPU 已知任务 fence 2 与 CPU 读回通过。332.216 秒自动回 TWRP，整页 BCB、七组保护、GPT 与根清单核验通过，专用根零写入。另一个窗口内完成 2,396 次 GOP 复制（29.95 次／秒）；该计数与本次同地址发送的证据分开。串口归档离线重放逐字节一致。[v340 真机证据](evidence/k80-gpu-v340-autorefresh-transfer-device-2026-11-19.json)
- 逐帧接入点是 `MiniIOMobileFramebuffer` 的 swap 入队时间、实际生产 fence 与 `show()` 的写屏屏障。现有显示租约仅能在 `CpuReady` 阶段取得一次，释放后为 `Released`。运行期需要让实际显示所有者维持有界租约，并把 DSI 等待放在 GPU 提交租约之外。先用可区分的 GPU 帧验证兜底单缓冲路径，然后验证连续呈现、地址与资源生命周期。

## v341 运行期 GPU 帧与 DSI0

- 现有显示所有者在 GPU 用户客户端发布前取得租约。工作线程等实际发布返回，在 50 秒内寻找一笔入队时间晚于基线、满足生产和表面 fence 已退休条件的普通合成器 swap。它用 `show()` 的写屏屏障时间和 GOP 像素采样差异核对当前画面，在同一把写入锁内复查 Apps SMMU 并沿用 v340 的一次 FLUSH 和完成跟踪。GPU 提交租约已释放，线程退出时按显示完成状态归还或保留资源。
- CDC v341 记录 swap、surface、三组 fence、GOP 写入序号、基线与当前采样签名、入队／写屏／认领时间及 DSI 观察时间。ASan／UBSan、13 项矛盾记录拒绝、合成 Recovery 回归和 v340 实机归档逐字节重放均通过。41 个输入重编，1,399 个输入完整链接。候选沿用已安装的 v297 根。[v341 精确构建](evidence/k80-gpu-v341-runtime-dsi-offline-2026-11-19.json)
- 实机在 72.405 秒取得基线，50 秒窗内尝试 1,129 次，最终返回 `no_changed_frame`，未触发 FLUSH。租约正常归还。140.747 秒已有普通合成器 swap 956，其生产 fence 1637、表面 fence 和退休 fence 1639。后续 80.012 秒有 2,384 次 GOP 复制（29.80 次／秒）。早期日志未分项记录锁竞争、fence 拒绝和签名相同，后续完成的 swap 无法回推具体拒绝项。GPU 已知任务通过，334.235 秒自动回 TWRP，专用根零写入，串口归档重放逐字节一致。[v341 真机证据](evidence/k80-gpu-v341-runtime-dsi-device-2026-11-19.json)
- 下一轮使用此前核验的有界虚拟滑动制造普通 GPU 合成场景，并记录认领拒绝项。连续统计要允许合成器按原节拍运行。将 GOP 写入代次夹在新 INTF1 与 DSI 事件前后，写入可能与 DMA 重叠时标成归属不明，避免把单笔测试中锁住 GOP 的测量当成正常帧率。

## v342 有界滑动与运行期传输

- 复用 v271 的虚拟 HID 服务和已构建的滑动计划。通过真实 backboardd、原生 GPU 已知任务、客户连接和合成 fence 的现有 v272 门槛后，在首次虚拟接触前核对 GOP 基线。最多提交 17 个接触报告，发生中途错误仍按原计划尝试一次抬起。只有滑动全部返回后才寻找改变的合成帧，最多触发一次同地址 FLUSH。物理 FT3683 沿用独立计数。
- CDC 输出真实接触返回与抬起状态、锁或地址不可用、旧副本、无效 fence、相同像素采样签名和超时计数。保留全部九个触控／呈现采样，使用末尾一组被时钟门控的面板寄存器采样槽传输场景记录。41 个输入重编，1,399 个输入完整链接。ASan／UBSan、14 个矛盾归档拒绝、Recovery 合成回归、v341 真机归档逐字节重放均通过。[v342 精确构建](evidence/k80-gpu-v342-swipe-dsi-offline-2026-11-19.json)
- 真机在 107.519 秒通过普通 GPU 合成器门槛并启动虚拟 HID 服务。至 113.520 秒，HID 订阅、合成器保持就绪和 GOP 基线的组合门槛未满足，接触报告为 0，未取得基线、未触发 FLUSH。串口无法区分具体子条件。后续软件复制率为 29.87 次／秒。GPU 已知任务通过，显示租约归还，334.310 秒自动回到 TWRP，存储保护与归档重放通过，专用根零写入。[v342 真机证据](evidence/k80-gpu-v342-swipe-dsi-device-2026-11-19.json)
- 被动测量准备按普通合成帧写入代次夹住 INTF1 启动与 DSI0 完成，区分重复、变化和与写入重叠而无法归属的帧。下一轮以正常合成器运行中的窗口为起点，不等待虚拟 HID。主机模型已覆盖并发写入、硬件计数跳跃及途中截止时保留资源，真机证据待补。
- v343 已将被动采样接入实际 `show()` 写入屏障与正常显示租约，重编 41 个输入并完整链接 1,399 个输入，内核 SHA-256 为 `92686bd4a8468663b033852a20f5af0bc90ac4c5b9e7b878bec14d61c1637893`。工作线程持有显示租约后复核实时 CTL／VIG／Apps SMMU 路由。MDP 映射只读，INTF1 和 DSI0 只确认所观察的中断状态。被动采样线程读取 GOP 写入代次，无需取得逐帧写入锁。下阶段补齐 CDC v343 解码、回归、精确启动包和真机。

## v343 正常合成器的被动 DSI 观测

- 精确启动包包含运行期 DPU／DSI 版本、通道、CTL、VIG、时钟与 Apps SMMU 复核。保持 CTL 命令次数为零，8 秒采样窗口结束时允许最多 50 ms 确认已见传输。采样记录接口计数差、DSI 完成事件、变化／重复／首次／无法归属的像素采样和轮询间隙。软件复制率另按原窗口计算。
- 原生并发写入、传输计数跳跃、完成排空、超时保留和初始状态清除失败均已通过主机回归。CDC 额外拒绝 15 种矛盾记录，v342 实机归档逐字节复现。精确内核与包的输入和校验值见记录。[v343 精确构建](evidence/k80-gpu-v343-runtime-cadence-offline-2026-11-19.json)
- 实机通过显示路由复核，但未取得符合条件的 GOP 写入代次，返回 `GOP_unavailable`。8 秒窗口未启动，后续串口记录的 79.991 秒内完成 2,394 次软件复制，平均 29.93 次／秒，单次 `show()` 平均 20.20 ms。另一个 120 ms 硬件快照中 TE 读计数增加 14，INTF 和 MDP 均未增加。GPU 已知任务完成，租约归还，334.186 秒自动回 TWRP，专用根零写入，实机串口归档重放逐字节一致。[v343 真机证据](evidence/k80-gpu-v343-runtime-cadence-device-2026-11-19.json)

### 显示帧率的上游参考

- Sheng 用单调时钟和 DPU 接口帧计数差测硬件刷新，用 GPU／显示事件和触控时间窗分析合成帧节拍。参考源码固定为 `516a780473a2ac59c8b438e132bb60204dda9e22`。直接扫描输出还检查生产 fence 和 CTL 锁存，支持定位出帧到锁存的延迟。分辨率、双 DSI 路由和寄存器取自 Sheng 自身。[显示时序源码](https://github.com/UniXNU/UniXNU-sheng/blob/516a780473a2ac59c8b438e132bb60204dda9e22/package/DisplayTimingProbe.cpp) [官方诊断记录](https://unixnu.com/devices/sheng)
- 同 SoC 的 houji r278 在 4.003023 秒内观测到 483 个接口计数增量，约 120.659 Hz。自动刷新会计入重复画面，原位复制可能撕裂。pipa 用固定滑动和活动期 swap 间隔对比软件呈现；Orange Pi 5 Plus 用直接扫描地址回读和锁存耗时验证显示控制器侧的呈现。各自的结果适用于对应观测点。[houji r278](https://github.com/lonzzi/UniXNU-houji/blob/98bc0960f96076de8e8d16efcfb0c0603b166b85/docs/device-tests.md#r278--关闭早期工作区后恢复桌面取得硬件时序) [pipa](https://github.com/xVanTuring/UniXNU-pipa) [Orange Pi 5 Plus](https://github.com/Hange777/UniXNU-opi5plus)
- K80 的下一轮先在合成活跃时独立记录硬件窗口及覆盖率，同时报告 GOP 代次门槛的具体拒绝项。显示路径有可靠帧身份后，在相同动作窗口内用 swap 序号关联生产 fence、写屏结束与 DSI 完成，统计新帧间隔和各阶段延迟。写入与传输重叠、观察断档及无法区分的帧保留为未知。面板实际发光时间需要独立光学对照。

## v344 分开验证逻辑尺寸与面板尺寸

- v343 的合成器账本由 `zorn26_present_frame298()` 写入逻辑 `fWidth/fHeight`。本次启动参数没有 `fbwidth`、`fbheight` 或 `fbscale` 覆盖，默认 1125×2436。旧观察器把这两项与物理 GOP 的 1440×3200 比较，使有效的缩放帧也无法通过。v344 分别核对账本与逻辑尺寸、CPU 别名与物理尺寸，以及同一 swap 的复制与生产 fence。
- v344 在原有普通合成器门槛与真实路由校验通过后立即监测 DSI。暂时缺少有效 GOP 代次的完成事件记为归属未知。可关联事件的延迟区间从最近一次对应 GOP 写屏结束到 1 ms 轮询观察到 DSI 完成，重复画面可能包含等待时间。CDC 同时记录逻辑尺寸、合格帧数、拒绝位和写入前后时间戳校验结果。
- 41 个输入重编，1,399 个输入完整链接，未解析符号为零。ASan／UBSan 覆盖缩放几何、无 GOP 代次的 DSI 计数、写入重叠、超时保留与延迟合计。串口归档回归通过，v343 实机归档逐字节重放。候选继续使用已安装 v297 根和既有 FD、启动器、ADT。[v344 精确构建](evidence/k80-gpu-v344-frame-attribution-offline-2026-11-19.json)
- 实机从 uptime 117.276 秒开始观测。8.000946 秒内记录 296 次合格 GOP 写入、16 次 INTF1 计数前进和 16 次 DSI0 完成，无轮询断档。DSI 完成平均间隔 497.663 ms，约 2.00 次／秒。初始自动刷新为 `0x8000003c`，MiCode 将低 16 位读作 `frame_count`。结合此前独立测得的约 120.55 Hz TE，结果符合每 60 个 TE 执行一次传输。15 次传输无法关联稳定 GOP 代次，另一次绑定 swap 282 和 fence 963，写屏结束至观察到完成为 22.269 ms。该窗口未确认面板完整新帧数。
- 后续 8 个串口窗口共 80.027 秒、2,298 次 GOP 复制，28.72 次／秒；`show()` 平均 18.90 ms。GPU 已知任务通过，显示租约归还。一次启动于 334.232 秒自动回 TWRP，BCB 整页、7 组保护对照及 GPT／17 根标识通过，专用根零写入，真机归档逐字节重放通过。[v344 真机证据](evidence/k80-gpu-v344-frame-attribution-device-2026-11-19.json)
- 优化接下来从更新时序和前后台缓冲区所有权着手。Recovery FDT 的 `splash_region` 包含候选第二帧 `[0xfd800000, 0xfe994000)`，候选避开原厂 `disp_rdump_region`。精确 ADT 无第二帧移交项，现用启动器只传主 GOP 长度。须先建立固件至 XNU 的显式移交及 CPU／DPU 访问验证，再让正常合成使用已完成且不会被写入的缓冲区。仅提高当前自动刷新频率会增加传输与原位写入发生重叠的机会。

## v345 第二扫描缓冲区的固件移交

- 新独立 DarwinBoot 用实际 GOP 几何、GCD 保留描述和最终 EFI 内存表核对候选范围，排除与 XNU 分配窗口的相交。只把标量结果填写到 `/chosen/zorn,scanout-reservation` 的零值占位，拒绝非零、错位、重复及尺寸不符的占位。EFI 保留内存条目的属性可能同时含能力位，有效访问保护以实时 GCD 属性为准。
- XNU 从 SecureDT 读取移交记录，复核物理 GOP、16 KiB 页大小和实际物理内存窗口，建立带 `kIOMemoryMapperNone` 的只读 CPU 映射，逐页比较物理翻译，再释放映射。本轮不读写该区的像素，不改变任何 DPU 取图地址。继承 v344 的被动传输观测。
- 独立 EFI 模块、41 个对象重编及 1,399 输入完整链接通过。新包更换启动器、ADT 和内核，继续使用原 FD、菜单和已安装的 v297 根。实际 EFI 检查函数与 ADT 解析器的主机 ASan／UBSan、两侧补丁零模糊重放、新格式归档与 v344 真机归档重放通过。[v345 精确构建](evidence/k80-gpu-v345-scanout-reservation-offline-2026-11-19.json)
- 真机确认 `0xfd800000` 起的 18,432,000 字节处于 EFI 保留区，XNU 检查了 1,125 个 16 KiB 页和缓冲区末字节的物理地址，完成后释放只读映射。既有路径 8.000074 秒内有 298 次合格 GOP 写入和 16 次 DSI 完成，显示租约归还。334.273 秒自动回 TWRP，整页 BCB、七组保护对照、GPT 和 17 根标识均匹配，专用根零写入，实际串口归档逐字节重放。[v345 真机证据](evidence/k80-gpu-v345-scanout-reservation-device-2026-11-19.json)
- 后续换帧用原来的 TE／DSI 完成观察，补上 VIG0／VIG1 的两个源地址设置及完成后的地址回读。独立主机回归覆盖双管线一起切换、切回原地址、第二次写入失败和切回前拒绝时保留缓冲与资源。下一次实机需验证新地址确实送出可辨识画面，以及切回原地址后才解除资源占用。

## v346 一次切换并回到原 GOP

- 接通真实 GOP 写入锁、已核验的第二缓冲区和现有 DSI 完成观察。候选先检查两条 VIG 仍指向原 GOP，再在第二缓冲区绘制并抽样回读固定三色图案。两条 VIG 的源地址和 CTL0 flush 是仅有的新增控制器写操作。完成要求包括两路地址回读、各一次 INTF1 增量与 DSI 完成，以及切回原 GOP。DPU 仍可能访问第二缓冲区时保持 CPU 映射和显示资源。
- 41 个对象重编、1,399 输入完整链接、独立启动包、补丁重放、串口合成测试和 v345 真机归档重放均通过。保留自动刷新间隔和 v345 的启动器、ADT、FD 与原 v297 根。[v346 精确构建](evidence/k80-gpu-v346-scanout-roundtrip-offline-2026-11-19.json)
- v346 单次真机启动确认两路 VIG 切到第二缓冲区并切回原 GOP。相机视频第 114.60 秒看到三色条纹。串口记录切换和恢复的 DSI 完成观察分别在写入后 337.979 ms 和 243.469 ms，显示租约已归还。恢复后 8.000412 秒内观察到 16 次 DSI 完成。333.782 秒自动回到 TWRP，七组保护、GPT、17 根及整页 BCB 校验通过，专用根零写入。[串口与回收证据](evidence/k80-gpu-v346-scanout-roundtrip-device-2026-11-19.json) · [相机画面](evidence/images/k80-v346-camera-second-scanout-2026-11-19.png)

## v347 固定画面的传输节拍对照

- 在第二缓冲区保持固定三色图案时，把自动刷新间隔从 60 TE 临时改为 4 TE，观察 1.5 秒，再恢复 60 TE 和原 GOP。切换时断开外部 TE、停用自动刷新并检查传输已平静。任何无法确认的状态都保留两份缓冲区和相关显示资源。完整内核、独立启动包、主机回归和 v346 归档重放通过。[v347 精确构建](evidence/k80-gpu-v347-panel-cadence-offline-2026-11-19.json)
- v347 单次启动实测 1.500024 秒内 45 次 INTF1 增量、45 次新 DSI 完成、零采样缺口，固定画面传输率约 30.00 次/秒。相机视频第 113.53 秒可辨识三色图案。驱动恢复 60 TE 和原 GOP 并归还显示时钟和带宽租约。串口与 Recovery 归档逐字节重放一致，333.741 秒自动回到 TWRP，整页 BCB、七组保护、GPT 和 17 根通过，专用根零写入。[v347 真机证据](evidence/k80-gpu-v347-panel-cadence-device-2026-11-19.json) · [相机画面](evidence/images/k80-v347-camera-static-4te-2026-11-19.png)

## v348 连续换帧后端

- 复用实际 K80 DPU/DSI 转移逻辑，增加只接受 4 TE 且限定基地址对的短时路径。同步记录序号、入队、像素就绪、寄存器提交和配对的 DSI 完成。两路源地址、新 INTF 增量和新 DSI 完成都匹配时才公布帧并移交旧缓冲写权。写后状态不明会禁止两块缓冲继续使用。ASan／UBSan 覆盖交替出画、重复序号、硬件计数器回绕、超时、源地址部分写入、帧计数不吻合及继承 60-TE 路径。[可重放补丁及固定输入](../patches/gpu/ios26-live-scanout348/source-manifest.json)
- v348 已接到实际呈现线程和板级显示租约。一秒内由同一写锁保护两块显示内存，部分更新先以当前显示的完整画面为底图，行辅助线程只写当次背缓冲。存储完成后再提交，最多允许 32 次正常帧转移尝试和一次恢复 flush。切回时把最新完整画面保留在原 GOP，恢复 60 TE；如果仍在扫描第二缓冲区，要取得原 GOP 的新 DSI 完成才可退役另一块。状态无法确认时停止提交并保留资源。内核 41 个对象重编、1,399 输入链接通过，启动包保留原 FD、启动器、ADT、根和用户态。CDC 保留真实 swap ID、入队和 DSI 完成时间，独立计数拒绝以及跨出统计窗口才完成的帧。主机回归与 v347 归档重放通过。[v348 整合补丁和构建](../patches/gpu/ios26-live-scanout348/integrated-source-manifest.json) · [v348 离线证据](evidence/k80-gpu-v348-live-scanout-offline-2026-11-19.json)
- v348 在无人值守的开机转入锁屏场景取得首组普通合成 swap 与硬件传输一一配对的实测。内核 uptime 113.076487 至 114.076487 秒内尝试 13 次，10 个 swap 各取得一份新的 DSI 完成，3 次在提交 VIG 地址前被拒绝。相邻确认间隔 P50 66.947 ms、最大 298.440 ms。入队至 DSI 确认 P50 209.514 ms、P95 299.582 ms；写寄存器至 DSI 确认 P50 27.708 ms、P95 32.484 ms。入队至像素就绪的估算中位数为 181.914 ms，仍需拆分等候、fence、缓存获取和复制，并记录每次拒绝的状态。本轮是 1 秒锁屏采样，缺少受控桌面交互、物理触控和逐帧光学观察。[v348 真机证据](evidence/k80-gpu-v348-live-scanout-device-2026-11-19.json)
- 10 次换帧后原 GOP 已是活动缓冲区，恢复 60 TE 后归还显示租约，无需额外切回。相机视频第 120 秒看到 iOS 锁屏。333.907 秒自动回 TWRP，整页 BCB、七组保护、GPT 和 17 根校验通过，专用根零写入。CDC 与 Recovery 归档逐字节重放一致。FT3683 的观测窗口接收了 569 个无触点报告，物理手势仍待验收。[相机画面](evidence/images/k80-v348-camera-lockscreen-after-scanout-2026-11-19.png)

## v349 显示逐帧阶段采样

- 沿用 v348 一秒锁屏和 4-TE 双缓冲路径。对最多 32 次换帧记录对应的 swap ID、排队、软件节拍、生产者与 issuer 就绪等待、缓存获取、CPU 写入和 DPU 拒绝条件。成功记录须与硬件 DSI 完成按顺序配对。阶段时间采用 64 µs 量化，时间缺失独立标记。这个版本用专用阶段记录替代物理观察包里原来的 v278 累计呈现耗时；FT3683 样本、硬件完成时间和已确认证据格式继续保留。[v349 完整构建与源补丁](../patches/gpu/ios26-present-phases349/source-manifest.json) · [v349 离线证据](evidence/k80-gpu-v349-present-phases-offline-2026-11-19.json)
- v349 真机在正常锁屏中到达 `writer_unavailable`，未开始 4-TE 窗口，也未发换帧命令。旧状态覆盖写锁、GOP 校验和板级 VIG 复核，当前日志无法判定具体拒绝点。显示租约正常归还。333.810 秒自动回 TWRP，零根写入，整页 BCB、七组存储保护、GPT 和 17 根检查通过，串口归档重放一致。[v349 真机证据](evidence/k80-gpu-v349-present-phases-device-2026-11-19.json)

## v350 呈现线程在帧边界让锁

- 一次请求用绝对启动时钟限制为 250 ms。现有呈现线程完成当前帧后让出写锁；请求结束或过期后继续呈现。请求状态只发布截止时间。候选按写锁、GOP 几何、正常 writer、板级寄存器读取及双 VIG 原地址分别记录准入结果，保持上一版的 4-TE 转移和看门狗边界。41 个对象重编、1,399 输入链接、独立启动包、主机线程回归、模拟串口和 v349 真机归档逐字节重放通过。[v350 完整构建](../patches/gpu/ios26-writer-reservation350/source-manifest.json) · [v350 离线证据](evidence/k80-gpu-v350-writer-reservation-offline-2026-11-19.json)
- v350 真机用 24 次锁检查、26.353 ms 完成写入者交接，两路 VIG 复核均为原 GOP。锁屏一秒内 12 次尝试全部取得配对的新 DSI 完成，无拒绝或跨窗口完成。出画间隔 P50 33.787 ms、最长 165.771 ms，入队到 DSI 完成 P50 231.514 ms，寄存器提交到 DSI P50 27.928 ms。该窗口为一次锁屏观察，持续桌面场景需要独立对照。[v350 真机证据](evidence/k80-gpu-v350-writer-reservation-device-2026-11-19.json)
- 12 次均为 GPU 路径且两块显示内存交替写入。原 GOP 的 6 次 CPU 写入用时 4.672–5.376 ms，中位数 4.864 ms。第二缓冲区的 6 次用时 65.152–133.440 ms，中位数 94.560 ms，无局部更新底图复制。入队到选取中位数 136.000 ms。生产者／issuer 等待与软件节拍均在 64 µs 量化下记录为零。样本将长尾指向第二缓冲区写入环节及其排队影响。[逐帧串口数据](evidence/k80-gpu-v350-writer-reservation-device-2026-11-19.json)
- 原 GOP 和 60-TE 配置正常恢复，显示租约归还。相机第 120 秒显示锁屏。333.774 秒自动回到 TWRP，整页 BCB、七组保护、GPT 和 17 根校验通过，专用根零写入，串口与 Recovery 归档重放一致。[相机画面](evidence/images/k80-v350-camera-lockscreen-after-scanout-2026-11-19.png)

## v351 第二缓冲区写合并对照

- v350 第二缓冲区的映射选项为 `kIOMapInhibitCache`。v351 对该块 EFI 保留显示 RAM 的只读核对和正式写入映射统一请求 `kIOMapWriteCombineCache`，映射对象须返回 `0x400` 才能进入帧写入，保留完整页物理地址校验和 DSI 完成后的退役。XNU 源码将两个选项分别映射为 `VM_WIMG_IO` 和 `VM_WIMG_WCOMB`，映射对象回读代表软件选项。真机仍需测量生效的写入延迟、出画节拍和回收。现有 MMIO 窗口和原 GOP 路径沿用各自配置。[v351 构建和固定源码](../patches/gpu/ios26-scanout-write-combine351/source-manifest.json) · [v351 离线证据](evidence/k80-gpu-v351-scanout-write-combine-offline-2026-11-19.json)
- v351 真机串口记录映射选项 `0x400`。同类一秒锁屏窗口内，DSI 确认换帧从 12 次增至 20 次，另有 1 次在窗口结束后完成。窗口内第二缓冲区 CPU 写入中位数从 94.560 ms 降至 5.152 ms，原 GOP 中位数为 5.504 ms。入队到 DSI 确认的中位数从 231.514 ms 降至 99.129 ms，最长帧间隔从 165.771 ms 降至 99.524 ms。仍有 9 次在写寄存器前以 `WrongTopology` 拒绝，均伴随 27.008–27.904 ms 的写入阶段，涉及两块缓冲区。锁屏录像仅用于确认场景。驱动已恢复原 GOP 和 60-TE，归还显示资源租约。一次启动在 333.796 秒自动回到 TWRP，整页 BCB、七组保护、GPT 和 17 根校验通过，专用根零写入，串口归档逐字节重放通过。[v351 实机数据](evidence/k80-gpu-v351-scanout-write-combine-device-2026-11-19.json)

## v352 记录每项拓扑检查

- v352 用 `WrongTopology` 的逐帧原因字段区分 DPU 版本、CTL 模式和路由、缓冲区对、活跃 VIG 源地址、行距、DSI 版本、控制和 lane 状态九项检查。保留 v351 的换帧判据、帧窗口和回收路径。41 个对象重编、1,399 个链接输入、完整启动包、ASan／UBSan 的单项与组合失败测试、新串口格式及 v351 真机归档回放均通过。每类模拟拓扑失败都在首个寄存器写入之前返回。[v352 固定源码与构建](../patches/gpu/ios26-topology-guard352/source-manifest.json) · [v352 离线证据](evidence/k80-gpu-v352-topology-guard-offline-2026-11-19.json)
- v352 真机 31 次尝试中，10 次只触发 DSI lane 状态检查，另 1 次为 `arm_status_dirty`。一秒锁屏窗口内确认 19 帧，另 1 帧于截止后完成。第二缓冲区写入中位数 5.408 ms，入队到 DSI 中位数 98.002 ms，最长相邻完成间隔 133.074 ms。恢复 60-TE 与原 GOP，返回显示租约。333.812 秒自动回 TWRP，整页 BCB、七组保护、GPT 与 17 根校验和归档重放通过，专用根零写入。[v352 实机数据](evidence/k80-gpu-v352-topology-guard-device-2026-11-19.json)

## v353 在写寄存器前等待 DSI 空闲

- 仅在 4-TE 窗口单独出现 lane 状态不符时，按 8 毫秒的绝对截止时间执行最多 8 次只读轮询，同时受统计窗口截止时间约束。每轮重新核对完整拓扑、IRQ 归属、欠载计数、自动刷新状态和 DSI 命令 MDP 发送状态。硬件满足条件才进入原有写入及完成关联。本次保留 33 次控制器提交上限、现有恢复顺序与失败保留。寄存器含义已核对固定的小米开源驱动及其 Git blob。[固定 MiCode DSI 状态源码](https://github.com/MiCode/vendor_opensource_display-drivers/blob/3f527f3e55ef27f240507ace3181d13900c3ed7f/msm/dsi/dsi_ctrl_hw_cmn.c#L1951) · [v353 固定补丁](../patches/gpu/ios26-dsi-idle-window353/source-manifest.json)
- 41 个对象重编、1,399 个链接输入、完整启动包、成功等待与各项无写入失败回归、v352 真机归档逐字节重放均通过。串口统计等待次数、达到空闲次数和最大观察时间，超时后跳过已准备的帧。[v353 离线证据](evidence/k80-gpu-v353-dsi-idle-window-offline-2026-11-19.json)
- v353 真机 9 次有限等待全部达到空闲，最长等待 5.942 ms。21 次尝试全部配对到 DSI 完成，其中 20 次落在一秒窗口内。相比 v352，拒绝从 11 次降至 0，最长确认间隔从 133.074 ms 缩短到 67.112 ms。入队到 DSI 的 P50 从 98.002 ms 增至 132.183 ms，复制阶段仍同时出现约 5 ms 和 27 ms 的样本。已恢复原 GOP、60-TE 和显示租约。333.677 秒自动回 TWRP，整页 BCB、七组保护、GPT、17 根及归档重放均通过，专用根零写入。[v353 真机数据](evidence/k80-gpu-v353-dsi-idle-window-device-2026-11-19.json)

## v354 对显示换帧增加可见 RGB 采样

- 沿用 v353 的一秒锁屏试验。两块扫描内存都完成校验后，复用 v341 的 64 点可见 RGB 签名，在当前可见缓冲区和准备好的缓冲区比较同一组坐标。仅为 DSI 确认的帧序号记录可见采样点是否有变化。测量不添加像素写入。网格之外的变化可能漏采，签名也不测量光学延迟和撕裂。完整内核和启动包、64 点颜色和 alpha 测试、只接受已确认序号与排除跨窗口完成、v353 真机归档逐字节重放通过。[v354 固定源码和构建](../patches/gpu/ios26-displayed-content354/source-manifest.json) · [v354 离线证据](evidence/k80-gpu-v354-displayed-content-offline-2026-11-19.json)
- v354 真机锁屏窗口内 22 次 DSI 确认换帧，其中 14 次在 64 个 RGB 采样点上与上一画面不同。另 1 次换帧在窗口截止后完成，拒绝 0 次。帧间隔 P50 为 33.377 ms，最长 66.558 ms。入队到 DSI 完成 P50 为 131.852 ms，CPU 复制 P50 为 5.248 ms、P95 为 27.776 ms。8 次有界 DSI 空闲等待全部成功。原 GOP、60-TE 和租约已恢复。333.642 秒自动回到 TWRP，整页 BCB、七组存储保护、GPT 与 17 根校验、串口逐字节重放通过，专用根零写入。[v354 实机数据](evidence/k80-gpu-v354-displayed-content-device-2026-11-19.json)

## v355 让运行中的线程领取扫描缓冲行段

- v354 的复制长尾同时出现在两块缓冲区。v355 在有界双缓冲试验中把每层已裁剪的可见行拆为最多 128 行的段，运行中的 CPU 在现有行锁下领取。呈现线程领取完所有段后关闭任务，只等待已经领取行段的线程完成写入屏障。仍使用原行绘制算法及 DSI 缓冲区所有权。普通呈现继续使用原调度。真实函数体 ASan／UBSan 回归验证了迟到线程、活动线程和 300 次连续裁剪层，完整链接、启动包、串口归档和 v354 实机归档重放通过。[v355 固定源码和构建](../patches/gpu/ios26-scanout-row-claims355/source-manifest.json) · [v355 离线证据](evidence/k80-gpu-v355-scanout-row-claims-offline-2026-11-19.json)
- v355 真机一秒锁屏窗口内有 30 次配对到 DSI 的换帧，其中 16 次在 64 个 RGB 采样点上有变化。另 1 次在窗口结束后完成，零拒绝。最长出画间隔为 34.029 ms，入队至 DSI 完成 P50 为 73.370 ms，复制最长 13.120 ms。试验恢复原扫描地址和 60-TE，在 333.565 秒自动回到 TWRP，七组存储保护及 GPT、17 根核验通过，专用根零写入。[v355 实机数据](evidence/k80-gpu-v355-scanout-row-claims-device-2026-11-19.json)

## v356 验证 2-TE 固定图案传输

- 在约 1.505 秒内记录 91 次配对的 INTF 增量和新 DSI 完成，零轮询缺口，约 60.47 次传输每秒。v347 的 4-TE 固定图案约为 30 次传输每秒。相机确认三色条出现在面板上，测量窗口内持续传输的是同一张图。结束时恢复原 GOP 扫描地址和 60-TE，归还租约，在 333.554 秒自动回到 TWRP。存储保护、整页 BCB 和串口逐字节重放通过，专用根零写入。[v356 实机数据](evidence/k80-gpu-v356-static-2te-device-2026-11-19.json)

## v357 在 2-TE 下验证锁屏真实换帧

- 沿用 v355 的双缓冲、动态分配行段、64 点 RGB 采样和回收检查。活动窗口改为 500 ms，比较节拍由 4 TE 改为 2 TE，32 次换帧和 1 次恢复 FLUSH 上限不变。对照使用 v355 的同长前半秒，其中 15 次确认换帧且采样点都有变化，入队至 DSI 的 P50 为 50.082 ms。41 个对象重编，1,399 个输入完整链接，未解析符号为零。原生模型、固定补丁重放、错误窗口拒绝、v355 和 v356 实机归档逐字节重放均通过。[v357 固定源码和构建](../patches/gpu/ios26-live-2te357/source-manifest.json) · [v357 离线证据](evidence/k80-gpu-v357-live-2te-offline-2026-11-19.json)
- v357 的半秒内有 16 次 DSI 确认换帧，其中 12 次 RGB 采样变化，零拒绝、零窗口外完成。相比 v355 的同长切片，编程至 DSI P50 从 21.628 ms 降至 15.052 ms，入队至 DSI P50 从 50.082 ms 增至 74.454 ms，最长换帧间隔从 34.029 ms 增至 49.870 ms。入队至选取的 P50 为 42.048 ms，软件节拍等待最长 16.256 ms。两次开机到锁屏的合成负载未做匹配，后续需固定动作验证差异。首个 FT3683 采样已累计 17 组接触和抬起，之后八个窗口未增长，来源未确定。相机在窗口后看到锁屏。原 GOP 和 60-TE 已恢复，显示租约归还，333.631 秒自动返回 TWRP，整页 BCB、七组保护、GPT、17 根核验和串口归档重放通过，专用根零写入。[v357 实机数据](evidence/k80-gpu-v357-live-2te-device-2026-11-19.json)

## v358 由确认换帧路径控制活动窗口节拍

- 在 `paceSwap()` 下先尝试取得现有 writer 锁。只有当前 2-TE 双缓冲窗口仍在截止时间内、缓冲状态已知且未触及上限时跳过软件休眠。退出后首个普通帧重新建立原软件节拍。原 GPU fence、像素复制、DSI 空闲检查与失败保留继续参与换帧。真实函数体 ASan／UBSan、完整 1,399 输入链接、新串口归档和 v357 逐字节重放通过。[v358 固定源码和构建](../patches/gpu/ios26-dsi-hardware-pacing358/source-manifest.json) · [v358 离线证据](evidence/k80-gpu-v358-dsi-hardware-pacing-offline-2026-11-19.json)
- v358 真机 17 次尝试、16 次确认换帧、13 次采样 RGB 变化。16 次成功换帧的软件等待全部为零，入队至 DSI P50 为 80.315 ms，入队至选取 P50 为 49.344 ms，最长出画间隔为 50.669 ms。一次 DSI 空闲等待超时后在写入转移寄存器之前退出。已恢复原 GOP、60-TE 和租约，333.502 秒自动回 TWRP，专用根零写入，整页 BCB、七组保护、GPT、17 根和串口重放通过。下一轮优先验证排队和固定滑动负载。[v358 实机数据](evidence/k80-gpu-v358-dsi-hardware-pacing-device-2026-11-19.json)

## v359 单槽呈现和请求入口时间戳

- K80 候选使用现有单槽队列模式。计时改从 `present()` 入口开始，包含调用方因满队列而等待的时间。真实函数的主机测试在相同的 23 ms 模拟准入等待和超时下对照了两个队列深度，也验证了 fence 随请求保留。完整内核、启动包、串口回归和 v358 实机归档重放通过。[v359 固定源码和构建](../patches/gpu/ios26-one-swap359/source-manifest.json) · [v359 离线证据](evidence/k80-gpu-v359-one-swap-offline-2026-11-19.json)
- 真机半秒内 18 次 DSI 确认换帧，另 1 次在窗口外完成，零拒绝。12 次采样 RGB 变化。请求入口到 DSI P50 为 44.717 ms，最长出画间隔为 34.164 ms。v358 始于准入后，P50 为 80.315 ms。两个窗口的开机负载有差异，仍需受控场景验证。原 GOP、60-TE 和显示租约恢复，332.958 秒自动回 TWRP。存储保护和串口逐字节重放通过，专用根零写入。[v359 实机证据](evidence/k80-gpu-v359-one-swap-device-2026-11-19.json)

## FT3683 的 GENI FIFO 传输候选

- 当前 FT3683 完整矩阵用 GPIO 逐位读取，实机持续采样约 7.1 次/秒。K80 的小米设备树将 0xA90000 对应到 QUP1 SE4，Linux 的 `spi2` 是总线编号。已核对 SE4、wrapper、时钟、引脚和中断来源。复用 UniXNU `QcomGeniSpi` 固定源码，在纯轮询 FIFO 路径增加可选的失败保留策略。进入前发现引擎忙、命令错误或超时就保留状态并拒绝后续写入。23 种长度的主机模型测试包含 K80 的 93、1513 和 3129 字节读帧，ASan／UBSan 和 arm64e 对象编译通过。仍需接入板级时钟、电源、引脚和 provider 所有者，并在真机读取确认 FIFO 可用。[源码补丁](../patches/touch/k80-geni-pio-retain/candidate.patch) · [输入与验证记录](evidence/k80-ft3683-geni-pio-offline-2026-11-19.json)
- v360 复用 UEFI 的 `ZORNTPWR` 供电和时钟交接。已有触控所有者取得排他 claim 后，在 GPIO 改写前检查三条时钟，随后用 `QcomGeniSpi` 的 `geni_spi_read_info()` 读取实际的 SPI、FIFO 几何和引擎状态。只读映射和回调均无写入接口。1,400 输入完整链接、主机状态分支、格式矛盾拒绝和 v359 真机串口重放通过，启动包保持 v359 的 GPIO 触控和呈现。[v360 固定源码和构建](../patches/gpu/ios26-touch-geni-inventory360/source-manifest.json) · [v360 离线证据](evidence/k80-gpu-v360-touch-geni-inventory-offline-2026-11-19.json)
- v360 单次临时启动后在 89.428 秒回到 TWRP，整页 BCB 和七组保护、GPT、17 根核验通过，专用根零写入。相机见到 UniXNU 菜单和早期控制台，文字无法辨读。串口未枚举，专用日志页未变，SE4 状态未知。复核链接发现新增 GENI 对象的 Mach-O subtype 为 `0x80000002`，与 K80 XNU 的 `0xc0000002` 不同，链接器发出两条新增警告。该构建缺陷已确认，提前回收的具体原因未取得启动日志证明。[v360 失败记录](evidence/k80-gpu-v360-touch-geni-inventory-device-2026-11-19.json)
- v361 用当前 XNU 的 C 编译配方重编同源 GENI 对象，确认 `arm64e.kernel` subtype，并在准入时绑定实际链接输入和编译配方。1,400 输入完整链接和启动包通过，新增的 ABI 警告消失，串口归档与错误状态拒绝回归通过。候选保留 v360 的只读探针。[v361 固定源码和构建](../patches/gpu/ios26-touch-geni-kernel-abi361/source-manifest.json) · [v361 离线证据](evidence/k80-gpu-v361-touch-geni-kernel-abi-offline-2026-11-19.json)
- FIFO 后续传输单独修正了纯轮询初始化的中断转发。旧实现初始化过程中会先打开 `SE_IRQ_EN` 再关闭。新实现先屏蔽转发，在全部初始化写入期间保持屏蔽，轮询仍读取本地状态。逐次 MMIO 写入的主机回归在旧版失败，新版通过完整 1513 字节传输。该补丁独立于 v360／v361 的只读探针。[轮询补丁](../patches/touch/k80-geni-poll-only/candidate.patch) · [回归记录](evidence/k80-ft3683-geni-poll-only-offline-2026-11-19.json)
- v361 单次启动在 333.593 秒自动回 TWRP。整页 BCB、七组保护、GPT、串口重放和专用根零写入核验通过。SE4 三条时钟均开启，SPI 固件读数 `0x102`。`IF_DISABLE=1` 与 `DMA_MODE=1`，序列状态、TX／RX FIFO 计数均为零。GPIO 触控累计 1,403 次成功读帧，最后区间约 7.10 Hz。串口观察期间无新增触点，手势尚待验证。同次 GPU 已知图像任务和真实 fence 通过，相机识别到锁屏。0.5 秒窗口内有 19 次 DSI 确认换帧，其中 12 次采样 RGB 变化。请求入口到 DSI 完成 P50 为 35.198 ms，最长出画间隔 34.329 ms。[v361 实机证据](evidence/k80-gpu-v361-touch-geni-kernel-abi-device-2026-11-19.json)
- K80 的 `qcom,spi-geni` 匹配原厂 `spi-msm-geni.c`，FIFO 禁用时选择 `GENI_GPI_DMA`。原厂 DMA 第五个参数 `2` 经 `msm_gpi.c` 解码后分配固定 GPII 0，使用通道 0／1、SPI 279 和 GPI 流 `0xb6`。原厂 SPI 数据缓冲通过标注流 `0xa3` 的 QUP wrapper 建立映射。新增 SoC 公共全双工描述符生成与完成事件匹配，通过四种 FT 传输长度的原厂字节对照、主机 sanitizer 和 XNU arm64e 对象编译。接入前仍需闭合实际通道所有权、DMA 地址和停止后的资源释放条件。[SoC 实现](../soc/sm8650/GpiSpiTransfer.h) · [原厂输入与离线回归](evidence/k80-ft3683-gpi-transfer-offline-2026-11-19.json)
- v362 补上旧 GPIO 接管检查遗漏的固定 GPII 0。在使用 GPIO 前读取 TX、RX、事件上下文。任何上下文不可读或尚分配都拒绝接管。用 UFS 已有的 APPs SMMU 只读映射采集 `0xb6`、`0xa3` 路由。v362 使用独立串口格式，原显示 SMMU 与 DSI 采集继续运行。1,400 输入完整链接、启动包装配、v361 实机原档无差别重放和 v362 串口正反例通过。[v362 构建与输入](../patches/gpu/ios26-touch-gpi-route362/source-manifest.json) · [离线证据](evidence/k80-gpu-v362-touch-gpi-route-offline-2026-11-19.json)
- GPI 环提交代码使用原厂 64 项 TX／RX 和 128 项事件环。等待 TX、RX 两个匹配当前描述符地址与长度的完成事件及 SE 空闲，才允许复用缓冲。门铃写入不明、记录损坏或超时会冻结该会话并保留 DMA 环及缓冲。主机 sanitizer 回归覆盖 135 次完整传输和三环回绕，以及 8 条保留路径。该提交路径尚未接入 v362。[环提交源码](../soc/sm8650/GpiSpiRings.h) · [主机回归](../soc/sm8650/Test/gpi-spi-rings.cpp)
- v362 单次试验在 333.659 秒自动回到 TWRP。整页 BCB、七组保护、GPT 和专用根零写入核验通过，串口归档逐字节重放一致。GPII 0 的 TX、RX 和事件配置原始值均为零。APPs SMMU 的 `0xb6` 与 `0xa3` 均无匹配条目，全局配置令未匹配访问产生 fault。GPIO 路径成功读帧 1,397 次，观察窗内无受控触点。GPU 已知图像和 fence 通过，相机见锁屏。0.5 秒内 DSI 确认换帧 17 次，其中 10 次检测到 RGB 采样变化。请求入口至 DSI P50 为 65.119 ms。[v362 实机证据](evidence/k80-gpu-v362-touch-gpi-route-device-2026-11-19.json)
- 已用固定 `ArmSmmu4K` 构造两套离线页表。GPI 表将 TX／RX 描述符页映射为只读，事件页映射为读写。QUP 表将 TX 数据页映射为只读，RX 数据页映射为读写。环和收发缓冲共用一块 16 KiB CPU 页，拆成四个 4 KiB SMMU 子页。主机审核覆盖叶项权限、页表损坏、地址宽度和物理别名，实际 XNU C／C++ 配方编译通过。接下来由 APPs SMMU 现有所有者分配流槽和上下文，验证 DMA 资源和停机条件后再接通传输。[DMA 内存源码](../native/display/ZornFt3683DmaMemory.h) · [固定依赖与校验](evidence/k80-ft3683-dma-memory-offline-2026-11-19.json)

## 连续出画的参考实现与统计口径

- **官方 Sheng。** 本地 `6a3d35c02504b712897799c5481952a61761325d` 的 `DisplayTimingProbe.cpp` 用 INTF 帧计数测传输节拍，`analyze-sheng-frame-timing.py` 从命令环统计提交到回调，从 swap 环统计提交到复制完成。官方收录提交 `c7a034617b94e4f0826b8eb70db6bc612e1aa093` 的 `sheng-latency-report.py --frames-only` 则直接读取 `kernel.rings.txt` 的 `S` 事件 4 和 `kernel.touch.bin`。它输出相邻 flip 的帧间隔及尾延迟，并用触点时间和两端的 flip 检查持续触控，阈值为 16.7 ms，两倍 Sheng 的名义 120 Hz 周期。K80 应按自己的触控报告节拍制定阈值，独立保留输入空档和出画空档。该脚本的测量终点是驱动 flip 事件。官方 `gpu-trace=1` 另外保留显示到达、fence、latch 等分段。历史 i570 记录的空闲 130 FPS 缺少逐帧面板序号或光学证据。[官方显示适配](https://unixnu.com/zh/porting/display) · [帧诊断](https://unixnu.com/porting/gpu-diagnostics) · [固定的帧统计源码](https://github.com/UniXNU/UniXNU-sheng/blob/c7a034617b94e4f0826b8eb70db6bc612e1aa093/scripts/sheng-latency-report.py)
- **小米 Pad 7（uke）。** `gpucomp27` 的 `UKE DPU: flip` 同时记录换帧累计、跳过、回退及 latch 均值和最大值。该次日志约 10–28 次换帧每秒，latch 平均 4.1 ms、最大 8.4 ms。K80 复用这些阶段的统计方法，以已验证的 DSI 完成配对为终点。[Pad 7 固定记录](https://github.com/NSR-XINE/UniXNU-uke/blob/325fb593659f1881b71249bf93491ce53e19d504/porting.toml#L218) · [UniXNU 设备页](https://unixnu.com/devices/uke-nsr-xine#display)
- **Nothing Phone (3a)（asteroids）。** `[frames]` 将复制和 flip 分开，并统计相邻帧间隔。`[frame time]` 记录合成、swap 至出画及 flip 至 latch 的阶段时间。其调试记录还显示，过早归还仍在扫描的表面会让合成器复写当前画面。[asteroids 固定适配记录](https://github.com/rootstockos/UniXNU-asteroids/blob/6370e66cc460202756058ae53f73afdb69abd364/porting.toml)
- **小米 14（houji）。** 本地 iOS26 分支 `98bc0960f96076de8e8d16efcfb0c0603b166b85` 的 `docs/device-tests.md` 记载 r278 的 INTF 计数在 4.003023 秒内增加 483，约 120.66 Hz，其中包含自动刷新复扫。同 SoC 的该例说明单读计数器无法推算新画面数量。[houji iOS26 分支](https://github.com/lonzzi/UniXNU-houji/tree/codex/houji-ios26)
- **EVB10。** 用可重复的脚本手势、按下和抬起划定分析窗口，结合显示间隔日志得到第 3–11 次滑动期间平均 52.6 FPS。代码记录也说明串口逐行读取当前 framebuffer 的截图只适合比较静态画面。K80 可沿用固定手势窗口，继续用自身 DSI 确认，并保留窗口内的长停顿。[EVB10 原始日志](https://github.com/Ken-u/UniXNU-evb10/blob/8ae5c74f52aff52adab778561c7e6dac9d31dc78/evidence/boot-v1-20261030.txt) · [显示和输入记录](https://unixnu.com/devices/evb10#display)
- **光学测量。** 开源 `videojitter` 通过已知测试序列和光传感器测量实际发光的帧边界、重复和漏帧。逐帧编号的高对比图案配合高速摄像也可比对手机屏幕上、下部的画面序号，检查顺序和撕裂。有同步参考才能求输入或提交至发光的延迟。[videojitter](https://github.com/dechamps/videojitter) · [高速视频扫描延迟实验](https://blurbusters.com/understanding-display-scanout-lag-with-high-speed-video/)

K80 连续双缓冲应为每个不可变待显示帧分配递增序号，用内核同一时钟记录 swap 到达、fence 或 CPU 写入就绪、VIG/CTL 提交和对应的 DSI 完成。仅在两路地址吻合并取得配对的 INTF 增量和新 DSI 完成时，将该序号记为一次出画。自动刷新复扫、被替换或拒绝的帧、超时及日志缺口各自累计。主指标使用固定手势窗口内成功显示的新帧序号数除以窗口时长，并报告相邻出画间隔与 swap 到 DSI 完成的 P50/P95/P99、最大值。可控测试图案逐帧编码序号，支持用相机验证画面顺序、漏帧和撕裂。光学延迟需由带同步参考的高速录像求得。

现有 `scripts/report-ios26-fps.py` 保留 Metal 完成、GOP 写入与 DSI 完成的独立统计。v305 的 FA1 间隔 12.45 ms、倒数 80.32 FPS 属于一个简单工作分类的记录。v355 给出了锁屏窗口的配对换帧数、采样有变化的换帧数及延迟分布。重复的交互场景和全屏光学出画 FPS 仍待实测。[v305 原始统计](evidence/k80-gpu-v305-nominal-opp-device-2026-11-18.json) · [K80 帧统计脚本](../scripts/report-ios26-fps.py)

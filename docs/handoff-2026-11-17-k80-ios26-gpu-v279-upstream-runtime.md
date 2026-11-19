# K80 iOS26：279 跟进上游 runtime／Metal

按机主“跟进上游”的方向，已取得官方UniXNU630b85a3实际选择的AdrenoMetal8c7f9502、Adreno7401c9029bc，并逐文件／Git树核验。279采用AdrenoMetal `8c7f9502de593c04a1003690f4a9441fe88551e8` 的公共frontend／Rust bridge，以及metal2vulkan development `46e7cc96a284150bdf19b4a6a7890b0a8bc0ef71` 加官方 `0063-main-optimizations-on-development-46e7cc96.patch`。完整用户态Metal bundle已在独立目录链接、签名并核验；**没有新根、内核或启动包，没有上机或FPS结果**。[精确源码](../patches/gpu/ios26-upstream-runtime279/source-manifest.json)、[实际构建与限制](evidence/k80-gpu-v279-upstream-userland-offline-2026-11-17.json)。

## 实际复用与适配

公共runtime复用上游的提交／调度、资源复用、缓存、linear／region-copy、staged-row和实际CM／FP计数实现，不重新实现后端。frontend、Rust bridge及K80服务发现适配层全部用当前iOS26目标重新编译，没有混入17对象。新iOS26 Metal接口保留原来正常service发现和真实Vulkan／GPU路径；没有用测试隧道或恒定成功回调代替它。

K80内核与实际Turnip仍为ABI-v1。新上游v2将method17由SubmitBatch改为SetPriority，flag2也由SubmitBatch改为OwnedCoherent，Submit结构由416变3104字节。不能直接更换协议头。279保留真实v1 Submit／128-IB批量扩展与WriteCombine策略，新增实际头文件编译门禁拒绝v2。原Turnip的priority setter明确返回不支持，frontend按真实拒绝处理；不冒充已实现优先级，也不改变当前direct-ring模式、固件、时钟、SMMU或K80板级参数。新Adreno740源码是参考，不是替换后的K80内核。

Rust no-copy入口接回既有有界VM身份walker：8192条记录／4096段上限，未知／失败观察走保守fresh-import；保留new runtime的真实资源与purgeable生命周期。共享模块仅调整测试路径，原有映射、COW／remap和失败记录语义保持。没有把失败保留扩大到所有对象永久不释放。

## iOS Mach 后端修复

实际交叉编译发现新runtime的`read_pages`仅在macOS编译，而iOS调用方也会使用它，产生缺符号；映射写权限查询在iOS落入固定false fallback，复制缓冲的GPU写回会被当作不可写。两处现在选择实际Mach实现。

iOS SDK的`mach/mach_vm.h`明确unsupported，不能把手写声明当SDK支持。iOS改用公开LP64接口`vm_read_overwrite`及`vm_region_64`，macOS保持原接口。实际本地XNU `osfmk/vm/vm_user.c` 显示前者调用`mach_vm_read_overwrite`、后者调用`mach_vm_region`；SDK原型、64位地址／长度、32位task port和9-word region布局经真实iOS26编译目标检查。实现仍读取当前task的正常资源数据，保护失败由内核返回false，不替换为恒定成功。

现有真实Mach函数体在主机上按iOS公开符号绑定执行：可读可写、只读、PROT_NONE、解除中间映射四种情况均通过；测试只操作测试进程自己的匿名内存，最终释放。它们不证明K80 GPU可见性或16KiB设备上的实测行为。另有实际暂存的有界VM walker测试与错误v2头拒绝通过。[测试工具](../scripts/check-ios26-mach-memory279.py)。

## 构建与精确输入

K80源候选tag `c06c80df1b754ba1aef8c3ec6b050ca9`，独立source／build目录，继承278真实平台源码，kernel身份仍明确标作parent278；未将279置为启动项。

沿用已经核验的houji26原生Rust arm64e/PAC target、nightly工具链与iOS26部署目标，SDK为现有iPhoneOS27.0。官方新配方的链接后指令重写路线没有执行；仅正常源编译、汇编公开作者`.ll` fixture、链接、文件头／版本元数据与undefined-only nm检查，无反汇编、逆向、地址符号化或Apple shader二进制分析。

完整translator归档含约1.9GB的验证观测数据；下载超时原件保留。实际Rust编译依赖从官方raw精确commit逐个Git blob验证，官方consumer patch所需源码／测试／文档也补齐，原样零fuzz应用；没有使用观测corpus或改变产品源码指纹算法。实际build_support自身按正常模块树核对产品源。新Cargo.lock为独立、离线、精确版本闭包；标准Cargo vendor补齐缺失源码，按registry校验和核验，不更改全局Cargo／Rust安装或旧vendor。

当前Rust archive SHA `83705f5f82273c927277227bc6c06105fd5eedac499f96e58ee1a20f1714c506`；新frontend和K80 OS wrapper各自重编、完整用户态链接通过，4KiB签名和bundle／嵌套driver核验通过。签名页4KiB与CPU16KiB／GPU4KiB分别记录。当前保留精确实际iOS26 Turnip `0ff53258845fa6eea197e0b94a05a856fc7dc39de589a50474eb64bf584404ba`；其底层Mesa revision85fda3b3与新版compiler输入一致，但最新公共Mesa patch stack仍需核对和集成，**不称整个图形栈都已升级或改善帧率**。原27／macOS板级参数、shader-cache Aqua代理、HWSCHED候选没有直接套入。

首次Cargo build缺Clang resource目录、随后真实iOS cfg编译失败均保留；补齐实际`clang -print-resource-dir`输入并修复真实Mach路径后重新构建。首个成功的private-Mach符号版本另存before-public-Mach-binding，当前archive和command哈希绑定公开接口版本。主机harness初始SDK头、模块可见性、全局rustdoc版本不一致等失败原件也保留，最终使用匹配rustc／rustdoc重新检查。

## 后续与验收边界

先跟进匹配的公共Turnip改动并保留K80真实v1传输／资源契约，再形成新root、完整K80内核和受保护启动包。279并未安装。278先前因私有ADB5039不可达在claim前退出，原失败归档不覆盖、不重跑；本轮没有手机命令，当前Recovery状态没有重新核验。后续仍需fresh Recovery／scope／ready／claim、300秒独立WDT、600秒有界Recovery返回，不能依赖人工操作。

低帧率瓶颈尚未测得；后续用对应精确构建测量presenter与新runtime分段计数，再用不依赖设置的固定工作负载检验。设置列表交互继续按机主指示独立待修。新renderer的已知图像、Metal设备／pipeline／真实fence／显示、客户端退出与资源生命周期、跨task及FT3683身份／边缘仍需精确新构建的实机证据，目标未完成。仅暂存，不新增commit／push。

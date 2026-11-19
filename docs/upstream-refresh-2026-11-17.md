# UniXNU 上游更新：2026-11-17

已将原 `UniXNU/origin/main` 从 `627c932a1573483dd44c29b48a113c3761dd8f55` 同步至官方main `630b85a307f19c8d8a4699d5bfc12f6796b874aa`（2026-11-17 08:12:28 UTC）。独立新版参考仓库位于本地 `UniXNU-upstream-630b85a307f1/`，main／origin/main均为这个精确提交，工作树干净。

原 `UniXNU/main` 仍保留627c932及K80本地改动；更新前后1357项文件指纹、porcelain状态和子模块状态一致。上游API报告新旧历史diverged，因此没有对带本地修改的构建树执行pull合并、reset、stash或子模块checkout。现有17／26源码、根、Data与已验收产物保持，K80候选尚未切换新core。[精确更新与检查证据](evidence/upstream-refresh-2026-11-17.json)。

## 下载和完整性

普通Git HTTPS入口明确连接超时，未停留在“已计划更新”。通过官方GitHub REST API取得当前commit、完整递归Git树和签名payload，通过官方codeload下载完整源码归档。逐一核对2287个文件的Git blob SHA1及所有tree SHA，根树为 `6357c2ab909b41c81d696e298d1370c27f891b75`；归档SHA256 `c10218edd56cbfc8a0ae0a2460f83c28b305e9a5dad8917c6e1f1a45c6ae228b`。只使用源码归档与Git元数据，没有分析程序指令或Apple shader二进制。

官方已有签名提交按Git格式无损导入，导入后的commit SHA必须与官方630b85a3完全一致；不是创建新提交。`git fsck --full`与工作树检查通过。独立参考仓库为shallow，未下载完整历史；已记录20项组件gitlink，组件源码尚未初始化。再从这个已核验本地镜像同步原仓库的origin/main，保留原本地main及其全部工作文件。来源响应、下载失败／部分归档、完整归档、导入脚本和新旧差异均在独立out归档保留。

官方compare响应仅返回250个commit和300个file，因此不把它当完整差异清单；完整文件核对以递归tree和源码归档为准。本文不把shallow快照称作完整Git历史。

## 回归检查

新版core的五组主机单元测试共42项：41通过，1项因缺少lzfse工具跳过。初次沙盒禁止本机127.0.0.1测试服务器bind导致的12项错误原样保留；在允许本机回环夹具的主机环境重跑通过，没有改测试或产品源码来掩盖失败。测试不读取真实IPSW、不访问手机。

使用新版官方porting-record检查当前zorn，13个区域通过；现有收录guard调用新版官方scanner，48KiB预算、1172条完整历史、截断EOF拒绝和当前入口接受回归通过。这些是源码／元数据检查，不是新K80构建或硬件验收。

## 对GPU低帧率工作的影响

新版官方文档描述了提交总耗时／lowering／recording／pipeline等待／锁等待／scheduler／submit的CM计数，以及命令池复用、批量提交、in-place／region-copy等FP计数。它们可补充278当前主要覆盖presenter的观察。缓存、tiling、region-copy和staged-row路径是后续需核对实际组件源码的候选，不能仅凭文档或commit标题断定适用于K80。

新main选择AdrenoMetal `8c7f9502de593c04a1003690f4a9441fe88551e8`、Adreno740 `1c9029bc3216a39d9e514ba41dee12e95e8f3598`；官方API已核对精确提交与说明，尚未替换本项目实际GPU后端、Turnip、转换器、Rust bridge或Metal插件。后续按CPU16KiB／GPU4KiB、iOS26 ABI、真实依赖、direct-ring和K80固件重新集成并重编，避免混链。

630b85a3最新修复的Shader Cache应用／Aqua登录注册属于macOS；不能直接套入当前iOS26，也不更换到iOS27／macOS配置。无需反汇编、逆向或shader二进制分析即可核对和复用合法开源实现。设置交互仍独立待修；278未启动，私有ADB5039缺失的启动前拒绝保留，不能把本次源码更新当实机耗时或FPS结果。

本次未操作手机，未安装／刷写，无新增本地commit或push。

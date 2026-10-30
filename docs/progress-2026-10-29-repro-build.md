# 上游更新后的构建与回归

日期：2026-10-29。按机主确认的顺序，先固化桌面基线、检查干净构建与重复启动，再完善触控、八核稳定性和其他外设。硬件 GPU 后置。

## 基线与隔离

已验收基线仍为 `42f3d518`：桌面、基本单指交互、八核、保留 8 GiB UFS Data 和低亮度。boot / kernel 哈希已重新核对，原归档及默认镜像均保留。主 UniXNU 更新到 `066c8d8`，参考设备 sheng 更新到 `08cde20`；上游更新本身不等于 K80 新特性已验证。

实验位于共同父目录 `out/zorn/repro-20261029/`。XNU 源码和对象目录与原树隔离；没有新建 GitHub 仓库、提交或推送。OS / SystemOS 只读，Data 不重置，不启动 Android，不 flash / erase / 改槽。

## 两次干净重放通过

从固定 Apple XNU `d8b80295118ef25ac3a784134bcf95cd8e88109f` 的新检出开始，两次独立重放均通过全部 **157 个补丁**；四个进入八核转换前的源文件与 `runtime-source-pins.json` 完全一致。

四处修正仅涉及上下文，新增和删除的非空代码行逐项核对不变：

- `vm-bands`：去除对手工空行的依赖，按真实前置源码生成精确上下文。
- `pmap-destroy-trace`：修正空行上下文。
- `user-console`：上下文中的旧采样上限 32 对齐前置补丁实际生成的 128，新增捕获逻辑不变。
- `ram-data-mount`：适配上游新增 GPU addon / staged apps 函数的邻接上下文，保留双方逻辑和顺序。

验证器不使用模糊应用、不跳过失败补丁、不复用旧 XNU 树。修正后的补丁均由标准 `git apply --check` / `git apply` 验证。可从共同父目录独立复测：

```sh
python3 UniXNU-zorn/scripts/check-zorn-patch-series.py \
  --workdir out/zorn/source-replay-new
```

需要本地固定 XNU 参考与 XnuPrelink。输出目录必须是新的，已有检出或结果会被拒绝，不会 reset / 清理它。此命令只验证源码，不编译或访问手机。

## 独立编译与统一打包通过

独立目录生成 **1011 个新 XNU 对象及编译记录**，最终完成原生链接和原版组件预链接。首次 bootstrap 的缺失板级符号由后续新构建的静态库满足，未沿用旧 XNU 对象。

恢复公开缺失头文件时曾遇到 TLS EOF；按固定 Apple tag API 元数据核对缓存头文件的 Git blob 后补齐，没有用旧对象代替源码。

**仍有显式的历史输入依赖：** ABI 配方会审计此前的预链接内核，本轮保留 `42f3d518` 和对应 plan 作为 ABI fixture。SDK、工具链及公开源码缓存也是既有输入。因此本结果不是“只有源码与 IPSW、完全不需此前 ABI 候选”的 bootstrap。

完整桌面参数的统一构建器已通过静态库、实际链接调用、原版 ABI、Data 种子、固件供电、负载及归档检查：

```text
boot    0b4eda46dee0e7e28b6ca82f7eefe6e87c2fbca4a3770816c4fbf94ae03cf150
kernel  7b2891d5c02ef5448b51a1d2b617943f3c75dcfe7ae496c66fd1b4f8e5acf1ac
```

127 项输入核对通过，归档已完整复制并逐文件比对到 `out/zorn/builds/0b4eda46/`。该候选保留 8 核、8 GiB RAM、保留的 8 GiB UFS Data、低亮度、原版 HID、Y 方向修正及快采样，使用 300 秒观察 / 600 秒主机回收预算。首次真机回归已自动回收，新日志确认 CPU1 预检 `SMP261`，`START1 step=4 rc=0 fail=0`，未进入用户态。Provider 曾完成 88 次只读请求，但未到 Data 初始化 / 用户态，不能据此认定 Data 损坏。构建通过不代替真机验收。

## 固定组件与可搬迁性

原 CLI 准备流程会自动更新子模块。新增显式 `--source-pins`，避免新主仓库顺带切换未验证组件：

- `source-pins.json` 固定 19 个实际组件 commit 和 363 个源码文件 SHA256。
- CLI overlay `0004-zorn-frozen-sources.patch` 核对组件集合、commit 和文件字节，不更新检出；错误 revision、错误文件哈希、缺少组件的三个反例均被拒绝。
- 构建前与打包前均核对，记录本身不得在构建期间变化；记录和检查代码纳入镜像输入清单。
- 固定当前实际组件不代表所有上游新组件已在 K80 验收。源码仍来自现有上游和工作区，不额外创建仓库。

```sh
python3 UniXNU-zorn/scripts/check-zorn-source-pins.py
```

完整构建命令追加 `--source-pins UniXNU-zorn/source-pins.json`；先安装本仓库 CLI overlay。

同时修复首次工作区的实际阻塞：contacts / frames 检查创建输出目录；八核资格检查用唯一相对后缀定位历史输入，原 manifest 不变、缺失或歧义仍拒绝；供电审计规范化真实 DXE 路径，搬迁后与旧 FD 能力记录完全一致；日志并发检查内置旧的两种非原子赋值反例，不再读取临时备份，实际八线程、每线程 2500 次及 footer / MAC / reset 检查保留。

## 实际硬件回归与源码快照

同一 recovery 起点的旧 `42f3d518` 对照，机主再次确认可进桌面、图标点击正常；八核掩码 `ff`、Data cookie `2dde8229` 和低亮度保留。`0b4eda46` 第二次通过八核并加载用户态，机主看到苹果标志；只有三次显示传帧，尚未达到桌面。真实等待栈已按对应内核符号化，一次等待采样不构成永久死锁证据。

旧公开基础补丁集 `16e592a` 的独立新对象对照 `1e926696` 也通过八核、保留 Data，但仅有三次显示传帧。它与实际成功工作树仍有 `kern_exec` / bindfs 等差异，不能称作完整基线复现。该轮额外源码一致性检查失败后，后续 shell 命令仍曾启动镜像；已记录流程错误，后续检查与启动改为显式检查退出码，失败不执行 USB 操作。镜像自身 ready、归档和设备边界检查并未跳过。

历史增量树并不等于按当前补丁目录重新应用得到的源码。新增 [`patches/compat`](../patches/compat/README.md) 过渡快照，独立重放后应用固定八核转换，97 个结果文件与保留工作树逐字节相同，没有复制旧 XNU 对象。旧归档只直接绑定四个 SMP 文件的源码指纹，其余来自保留工作树；不声称旧对象全部由这些字节新编译过。

该精确快照打包为 `2b4b143c`（221 项输入，kernel `dded911c1890961559353def07a2d66274bc7541d01361f883f9b4972607220f`）；两次真机均在 CPU1 `SMP261 / START1 step4 rc0` 自动回收，没有进入用户态，不能替换旧桌面基线。

对比两个工作区的 1024 个 Mach-O 对象，指令段全部一致；806 个对象全部非调试段相同，其余仅 217 个路径字符串段与一个版本时间常量段不同。217 个字符串差异在替换工作区前缀后全部消失。最终复位入口及其他原生符号整体移动 `0x4000`。这是布局敏感性的排查线索，尚不能证明 CPU1 的根因。下一对照仅规范化编译器嵌入的路径，保持 CPU、时限、Data、触控和服务配置不变。

## 路径规范化对照

`3a8ac966` 已从空对象目录独立编译，221 项输入与完整归档核对通过。仅增加 `-fmacro-prefix-map`，不改源码、CPU / 时限 / 触控 / Data / 服务策略。九个复位相关符号地址恢复为旧基线布局，最终链接的 1160 字节复位向量也与旧镜像相同。

1024 个对象指令段一致。Clang 对 56 个对象中的相同字符串作了重排；另有 `vm_tests` 的一个编译器诊断文件名仍保留新路径，已逐字节验证仅此前缀差异，没有把它算作完全相同。版本时间常量不同。这些限制均纳入对照检查。

机主已确认此轮进入桌面、图标点击正常；23:15 自动回收的新日志与 boot / kernel / 221 项输入匹配：八核各检查掩码 `ff`、Data cookie `2dde8229`、8 GiB UUID、亮度读回 64、三项系统修正均生效，2220 帧触控无坏帧、30 次 HID 提交无错误。轨迹最大间隔 148 ms、19 次显示传帧。第二轮也由机主确认桌面，23:23 自动回收，新日志及 221 项输入再次匹配。两轮均八核全检查通过、Data 保留和低亮度正常；这只是两次受控启动，不构成长期稳定性验收。此对照提示地址 / 布局敏感性，尚不等于 CPU1 根因已修复，也不是通用固定路径发布方案。默认 `out/zorn/boot.img` 仍保留 `42f3d518`。

## 分离双指记录

第二轮机主从锁屏进入桌面后，完成左右两个分离触点的按住 / 松开。新日志 27 条轨迹无覆盖、无坏样本：ID 0 与 ID 1 同时存在 5188 ms，跟踪期间 ID 保持，随后依次正常释放到零。2219 帧无坏帧，55 次 HID 提交无错误，最大采样间隔 148 ms。

证据范围为传感器解码后的双触点及提交结果，轨迹位于 HID 递送前；不能据此称系统捏合 / 缩放手势、十指、像素校准或防误触全部通过。两点位置不是精密坐标输入，本次不据它修改轴比例。详见 [双指与复测证据](evidence/qualified-source-repeat-two-contacts.json)。

手机已自动留在 recovery，无后台新轮次。原默认镜像和旧归档继续保留，没有提交或推送 Git。

## 独立工作区入口

以下只准备本机隔离目录，不编译、不访问手机；要求已有 SDK / 公开头文件缓存、只读系统镜像、Data 清单和资格归档：

```sh
python3 UniXNU-zorn/scripts/stage-zorn-build-workspace.py \
  --workspace out/zorn/isolated-build-new \
  --abi-reference out/zorn/builds/42f3d518 \
  --mu /path/to/Mu-Silicium \
  --source-snapshot UniXNU-zorn/patches/compat/qualified-42f3-source.json
```

输出目录必须不存在。19 个组件各有独立检出，只共享不可变 Git 对象；大型缓存按 APFS 写时复制准备，不复制 XNU 对象。省略 `--source-snapshot` 时测试当前基础加设备补丁；`--xnu-patch-base <完整commit>` 是另一个独立对照，二者不能混用。staged 状态不是 ready。

普通快照构建对应的是未规范化路径的 `2b4b143c` 对照，不应宣称会复现桌面。已通过一轮桌面的 `3a8ac966` 额外设置了以下环境（先进入新的隔离工作区，使 `$PWD` 是其共同父目录，再运行完整构建命令）：

```sh
zorn_warning_flags='-Wno-reserved-identifier -Wno-pre-c11-compat -Wno-missing-designated-field-initializers -Wno-suggest-override -Wno-unnecessary-virtual-specifier -Wno-suggest-destructor-override -Wno-ms-bitfield-padding'
export XNU_EXTRA_CFLAGS="$zorn_warning_flags -fmacro-prefix-map=$PWD=/Volumes/macData/projects/ios-zorn"
```

右侧绝对前缀来自旧基线实际编译记录，仅为复现其内核布局，不要求真实源码放在该路径，也不是通用发布约定。必须从空对象目录编译，核对实际编译记录、对象段及最终符号地址，不能仅改环境后复用旧对象或直接套用既有 ready 身份。找出布局依赖后仍须改为公开、独立的 canonical prefix 并重新验收。

进入新工作区后先运行 `python3 UniXNU-zorn/scripts/prepare-zorn-cpu-profile.py`，只读校验原版 SystemOS 三个固定修正位置并生成当前 profile 绑定；再使用 [完整构建参数](build-and-debug.md#基本桌面触控配置)，明确传入已验证 FD 与 IPSW。构建器核对源码重放清单、实际源码、八核转换和组件清单；归档全部通过才单独启动。仍依赖显式历史 ABI fixture，并非无历史输入 bootstrap。额外 `XNU_EXTRA_CFLAGS` 会记录在 ready 清单，正式启动前还须核对实际对象 / 编译记录。

## 后续验收

1. 已完成路径对照两轮桌面及分离双触点记录；后续分别验证连续双指移动与真实系统手势。
2. 定位 CPU1 启动 / 布局依赖，采用独立 canonical prefix 重测；两轮成功不等于根因修复，原桌面归档保留。
3. 消除历史 ABI fixture 依赖，单独安排触控采样、像素校准、多指及 CPU1 偶发早退的验证。

[构建证据](evidence/clean-source-replay-2026-10-29.json)区分源码、编译、ready 与真机结果；失败输出保留在独立目录。

# K80 iOS26 GPU 交接：v223 实测完成，v224 离线探针已签名，暂停

日期：2026-11-15（Asia/Shanghai）。本文件用于其他 Agent 续接。当前任务暂停；生成此文档不恢复测试。接手后在用户明确要求继续时恢复工作，不把历史 active 字样当作当前运行状态。全文没有宣称 GPU 已完整完成。

## 1. 先读与当前结论

- 仓库规则：[AGENTS.md](../AGENTS.md)、[README](../README.md)、[porting.toml](../porting.toml)。实施前按 AGENTS.md 读取官方记录、设备仓库、组件及所选 OS 配置。
- 历史逐轮记录：[v193 起累计交接](handoff-2026-11-15-k80-ios26-gpu-v193-active.md)、[GPU 进度](progress-2026-10-30-gpu.md)。里面 ready/active/live handle 均有后续 completed 记录，不要重复执行。
- 最近实测：[v222](evidence/k80-gpu-v222-metal-known-image-observed-2026-11-15.json)、[v223](evidence/k80-gpu-v223-without-map-waits-observed-2026-11-15.json)。本次离线核对：[暂停证据](evidence/k80-gpu-v224-paused-handoff-2026-11-15.json)。
- v222、v223 普通 Metal 客户端均完成真实设备发现、pipeline、提交、Completed 回调、32×32 全部 4096 RGBA 字节校验及正常 native close。CRC `718ed2ce`，first bad `ffffffff`，phase11/flags1023/status4/code0，97 次原生请求，close raw0。
- 两轮 `render_complete=true`、`native_teardown_complete=true`；辅助 stderr 截断 33，故严格 `application.complete=false`、`known_image_complete=false`、`full_GPU_qualification=false`。结构化报告本身无丢弃/copy 错误。**不放宽检查器、不把局部阳性升级为完整验收。**
- v222 有四点映射等待；v223 恢复原 IOUserClient，四点始终未选择，仍渲染成功。说明这次成功不依赖这四点等待，但其他历史诊断等待仍存在，不能称零等待。
- PAC 根因未确认修复，长期稳定性、真实 GPU 显示呈现、完整 FT3683 仍未验收。CPU 锁屏界面不证明 GPU 呈现。
- 对照[官方 GPU 教程](https://unixnu.com/zh/porting/gpu)：已有真实任务/完成/已知图像和普通 Metal 客户端阳性证据，正在进一步验证 IOSurface 共享图像，尚未完成实际 present/显示链路验收。不要把教程版本或其他 SoC 常量套入当前 iOS26。

## 2. 暂停时设备与授权

最后设备观测是 v223 在 333.1339709580061 秒回 TWRP；wrapper session11604 exit0、inner0。v222 session20074 也已结束（333.0683000830468 秒）。暂停时无 live job，不应轮询或重启已结束 handle。此交接没有重新连接手机确认实时状态。

v223 七组保护采样、完整 BCB 页及 tail 核对通过。手机仍装 root215；216–223 仅内核测试，没有新根写入。采样不等于全手机根镜像哈希。223 claim 已消耗。最后已核验的设备控制状态 active 字段为空、stop=false；续接须重新读取当前状态。

用户已授权后续真机测试，保持该授权，不重复索取每轮批准；但暂停指令有效，须用户要求继续后才恢复。仅允许既有固定流程：92988a43/zorn/slotA、private ADB5039、新 scope/bundle/owner/ready/admission/claim、完整 BCB/tail 与七组保护、300 秒独立看门狗、600 秒有界 Recovery、临时 fastboot boot。**只运行接收器先启动的 wrapper；inner entry 仅 check-only。** Recovery 返回失败立即停止设备操作。CC9 f85d4270 禁止。

## 3. 禁止事项与范围

严格禁止任何反汇编、逆向；不分析 panic 地址/寄存器/回溯，不符号化，不查看二进制指令或已定义符号。只用公开源码、头文件、编译器 AST 布局、普通构建元数据和哈希；如需检查未解析导入，仅 `llvm-nm -u`。

**绝不运行 `reference/houji/tools/build-ios26-bridge.py`，其中含禁用的指令检查。** 当前不需要重编 Rust。保留 Android/iOS17/Data、所有历史基线和两个 `_副本`；只维护 UniXNU-zorn、uefi-zorn 或隔离 out。无明确请求不 commit/push。运行时根只读，private var 为 RAMFS。不禁用 PAC、不伪造成功、不削减权限/生命周期/保护检查。

用户允许摄像头、看门狗+rec、串口；历史摄像头清单为空，此次未重新查看。用户 v217 照片单独确认 IA-key kernel PAC panic；没有 v221/222/223 新照片，不能从缺日志推断这些版本 panic 或位置。

## 4. 路径与保留输入

以下均是绝对路径；`/tmp/zorn-vNNN-path` 只是便利入口，可能被清理。

- B224：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v224-IOSurface-image-19a4a5e9872542ebab85c20db1e20129`
- S224：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v224-IOSurface-image-19a4a5e9872542ebab85c20db1e20129`
- B223：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v223-without-map-waits-b00b03c76099402f9446dd4e88b04cfc`
- B215：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v215-pipeline-without-extra-waits-e24d087ce9994306ac3c936887498d2e`
- B224 `candidate.json` 固定 tag/program `19a4a5e9872542ebab85c20db1e20129`，parent223，frontend215，Rust214。
- root215：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v215-pipeline-without-extra-waits-e24d087ce9994306ac3c936887498d2e/root-candidate/ios26-root-metal215.UNSELECTED.hfsx`；34359738368 字节，SHA256 `4a12265d312a0f07ea1348a2f2ea16734dd290ccc58fd2443c637b4f3687a523`。
- 保留 probe215 SHA `b94be7df06710c6e3fd0f3740fa618019588c1959def9e0e088261a9df2baccd`；CDHash `cc831b02a00755e8803bb1a6ee3bc25e6165f645`。
- frontend215 tag `e24d087ce9994306ac3c936887498d2e`；准确前端源码 SHA `b12b5552083f7cdf05ec95b756582b4cf8bbde32946a27839d8846675c83b691`，见 B215/frontend-source-review.json。
- Rust214 tag `7a16d3fe9b1a44cb859527a1ca87b961`；归档 SHA `79ab4b6b7adbe475fe7f6eea33b98d883a6c6d43c929f63e61f89d25de594349`。
- signed Turnip SHA `0ff53258845fa6eea197e0b94a05a856fc7dc39de589a50474eb64bf584404ba`。
- v223 kernel SHA `7158192eb8b8afcdfb61811b104f0b00ed474e8882b7185872d2a99e050a5092`；boot SHA `336a6418fcbff3d8a8cd90b99eea776a1045a3b1bfeeb072b70cdebdee4793e7`。均为已消耗历史输入，不重新执行旧 scope。

## 5. v224 已做、未做和已知记录问题

**仅完成离线用户探针编译/签名；没有新根镜像、根安装、内核构建、启动包、准入或上机。** candidate 的 root_payload_changed=true 表示计划更改载荷，不表示已改手机。kernel_built/hardware_trial_ready/system_booted 均 false。

S224 由223复制。`userland/ZornMetalProbe193.mm` 用公开 IOSurface API 创建32×32/32RGBA/row128 surface，校验实际几何与 CPU page；锁写并以0x5a初始化有效像素，创建真正 IOSurface-backed texture，检查实际 surface ID/plane。保留原 shader/pipeline/提交/Completed 判定。完成后分别读 Metal getBytes 与 IOSurfaceLockReadOnly 直接共享内存，使用不同初值的独立缓冲，比较两者并校验全部4096字节/CRC。正常释放 texture 与 surface；未知 GPU 完成状态继续保留到 watchdog，不提前释放。无 drawable/物理呈现结论。

新增 `userland/ZornSurfaceProbe224.h`：验证32×32、非多平面、页大小为2幂、base对齐且地址范围无溢出、row/总分配不溢出且覆盖实际32行；仅复制/初始化每行128字节，不碰padding。`ZornApplicationObservation26.inc` 只替换探针身份前缀；UFS启动身份尚未更新。

B224/build-user-probe-launch.py 已执行成功；arm64e-apple-ios26.0、现有 iPhoneOS27.0 SDK、ARC/O2/stack protector/C++17/Wall/Wextra/Werror，新增 IOSurface framework。签名允许 ZornGen7AppIoClient26 与 IOSurfaceRootUserClient，保留 no-container。编译、签名及 strict verification 已成功；没有运行探针。

探针：`/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v224-IOSurface-image-19a4a5e9872542ebab85c20db1e20129/user-probe-launch/zorn-metal-probe193`。
SHA256 `84840ffe87ae9ee4da143788d43dffb951082110b7e2f80cbf5fe9d6486838e5`；CDHash `6a3bcf65e26695a42ca617abd05c9b47c4c51529`。本次交接重新核对该二进制及 build-result 全部源码哈希一致，仅作数据完整性核对，不是新测试。

**必须先修复再准入：** B224/probe-source-stage.json 中 helper SHA 仍是 `6e62820f9241b22844d18575f8e8bbcb53c6f50af50e00e7b38be7fcb4eb5d8e`。暂存之后、编译之前增加了地址范围溢出拒绝，当前 helper SHA 为 `2ee2d2e08c20bcf7dd2d2d4f5561089126637b7db90a9fa0e489bf7559afef0c`，build-result 已记录新值。B224/stage224-probe.py 也未包含该后加 guard；不要直接重跑覆盖它。保留原暂存证据并补充修订记录/可重现脚本，不能悄悄把历史暂存当作最终构建输入。当前 probe-source.patch 是主 mm 差异，helper 独立。

尚未完成：几何/溢出/拒绝/padding/生命周期的 host 检查；imported cache 同步源码完整审查；新 root/probe trust 与 launch 绑定；v224 decoder/runner；新内核/package；任何硬件证据。

## 6. 已核对源码与研究

B223/selected-frontend-presentation-source-audit.json 是入口。精确215前端实现了 newTextureWithDescriptor:iosurface:plane: 和成功 Completed 后 presentDrawable；顶部“未实现 presentation”注释过时，不可据此认定缺失。surfaceBuffer 保留真实 surface，导入释放回调 CFRelease；holdImport 使用 buffer.importedSurface。禁止用假 drawable 回调代替物理呈现。

所选内核 `source/kernel/zorn26-platform-build-candidate/iokit/Kernel/houji-ufs-root/Adreno740/NativeAdrenoUserClient.cpp` 的 importBo 使用实际 callingTask；NativeAdrenoMemory.cpp importTask 要求完整 CPU 页、实际任务内存描述符 prepare/物理页枚举，失败保留/释放路径不省略。不要假定 CPU 页等于 GPU 4KiB页。MiniIOSurface.cpp 实际按 PAGE_SIZE 分配共享缓冲。暂停前只检索到 maintainImported/缓存函数，**完整缓存契约审查未做完**；不能认定缓存同步已证明。

已按用户要求查官方及其他机型，证据在 [v217 公开源码比较](evidence/k80-gpu-v217-public-source-PAC-comparison-2026-11-15.json) 和 B217/public-source-comparison：4仓库17文件，固定提交/Git blob/SHA256，无远程代码执行。

- UniXNU/Adreno740：54b41b8f59e90a167f6f75160739c5f825945fbc。
- UniXNU/UniXNU-sheng：5ae8b4876a378a5104330a5ae514ec9d6deae373。
- UniXNU/UniXNU-sm8550-common：2dc650ca76ae38715cd0712e60a44b14fe251745。
- superboyyy/hakios-arm64e-dada：f1ae906fcc43ba8f763663257724ba938fb820ab。

dada 的 Rust/C PAC flags 经验已与当前 Rust214 对齐，不是当前已证实缺项或可宣称修复。官方不同 memory view 的缓存属性各有契约，不能盲改。可继续查[官方 arm64e](https://unixnu.com/zh/porting/arm64e)、公开源码和 SDK 头文件，严格遵守禁止逆向。

## 7. 用户恢复后按此顺序继续

1. 读本交接、AGENTS.md、现有 porting 及证据；只读核对当前文件/构建身份和设备控制状态，避免覆盖他人改动。先解决上述 stage/helper 可重现性问题。
2. 补全实际导入页所有权/缓存同步/CPU lock/释放源码审查；对实际 helper 和拒绝/正常生命周期做必要 host 验证，保留真实错误，不写镜像实现的空测试。
3. 仅替换 probe 制作 root224，保留 frontend215、Turnip 和 Rust214 所有字节/签名。B215/compose-root.py、prepare-root-review.py、reconstruct-installed214.py 可参考，但它们是历史215配方，**不能直接复用旧根/旧哈希/旧新建计数**。
4. installed215 根差分证据入口 `/tmp/zorn-v215-delta-review`（V 下 k80-metal215-root-delta-review-e24d087c）。215实际写5627页/101组/23048192B，readback digest `7872522a2492598091851a77d0a7e22cbce4d99de5b6d026d122457b0cd1b5ad`；之前6964页/149组不是当前安装状态。必须按 prior readback + 215实际delta重建已安装215基线，再设计224delta/replay/保护审核。禁止把镜像本地哈希当手机全读回。
5. 完成新 probe/trust/launch/root 身份绑定、v224 producer/decoder/runner精确依赖、完整原生构建和输入/对象/link/ready 检查，再 fresh scope/admission。不得把223普通texture结果当224IOSurface结果。
6. 在用户恢复且既有授权范围内，接收器优先单次执行固定保护流程；新根安装若需要，先完成准确可审查delta及所有既有保护。遇 auto-review 真正拒绝则说明具体动作和理由；不要预设需重新申请每轮授权。不得以暂停期生成交接为启动授权。
7. 收集实际完整报告、原始CDC、Recovery及保护结果，再更新 porting.toml/进度/交接。先验收 IOSurface 图像，再独立推进真实显示呈现/长期稳定/触控；不直接切系统 GPU 桌面，不宣称全GPU完成。

## 8. 空间、记录与交接验证

暂停前磁盘约1.2GiB可用，续接先只读核实。此前已清理旧 iOS26 Cargo 中间缓存（B222 两份 cleanup JSON），6份最终 Rust .a 哈希保留；没有删除源码、根、内核、启动包、日志、测试证据或 iOS17。旧缓存可能需重建，但本轮不需重编 Rust。不要盲删 out。

当前已存证的实测截至223；v224仅本交接及其 evidence 描述离线状态，不改写历史GPU验收级别。文档生成过程没有设备操作、没有新代码修改、没有构建/安装/测试、没有提交。

## 9. 用户授权的本地空间清理（2026-11-15，后续更新）

已清理14份重复 local-replay 镜像、3份未完成的临时 composition 镜像，以及2份可从原始 IPSW 和本地 key 重建的 donor 解包缓存。实际可用空间由约1.0GiB增至15.4GiB，增加约14.3GiB；APFS共享块使逻辑删除量不能作为实际释放量。详见[逐文件清单与验证](evidence/local-space-cleanup-2026-11-15.json)。

所有正式 root 镜像、原始 IPSW、本地恢复材料、源码、构建产物、delta、日志和历史 manifest 保留。清理后完整本地 root215 SHA256 和 v224 binary/全部固定源码哈希重新核对通过，1025条 porting 本地证据引用存在。没有设备操作，GPU调试仍暂停。

历史回放报告中的 replay_image 路径现在可能不存在，这是清理后的预期状态；历史成功结果未改写。需要重新回放时，使用对应保留的 replay-and-check-layout.py、source_image、delta/patch 生成新临时输出；不要把缺失的回放副本当成主镜像丢失。

删除的 donor 缓存为 donor-decrypted/094-97238-092.dmg 和 094-95416-090.dmg。清理前已完整核对这两文件 SHA256，并逐字读取原始 IPSW 对应 .dmg.aea 成员以验证 ZIP CRC，同时记录成员 SHA256。恢复时：从项目根 iPhone18,1_26.6.2_23G90_Restore.ipsw 解出所需同名 .dmg.aea 到 donor-components，再使用 donor-decrypted/manifest.json 已保存的 /usr/bin/aea decrypt 参数和 donor-private 中现有同名 symmetric-key 生成输出，最后核对清单中的输出 SHA256。不要打印 key，也无需重新获取 key或运行 fcs-unwrap。恢复较大的 donor 时先留足加密输入和解密输出共约18GiB临时空间；完成验证后可清除新提取的加密中间件。此恢复配方未在清理时执行。v224继续使用root215，不需要恢复这些donor缓存。

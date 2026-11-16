# K80 iOS26 v258：已完成上下文的物理恢复

v258修复了源码中“旧任务已完成但仍占用选中上下文，其他客户端Close直接Busy”的路径。当前源码、sanitizer、完整原生内核和独立离线启动包验证通过。**未上机、未建立设备scope／ready／claim。** 最新实机仍为[v256](handoff-2026-11-16-k80-ios26-gpu-v256-operation-context.md)，完整GPU／显示／触控验收仍未完成，目标继续active。

## 根因与最小修复

修复前以257实际Root方法复现：另一个真实逻辑成员拥有选中上下文，任务已完成且无待处理资源，调用方Close仍在任何SMMU操作之前收到Busy。实际IOClient先设置closing，之后不会自动再次Close。这是源码复现，不能当作252实机Timeout根因。

当前使用独立Root物理恢复作用域。它在完整操作mutex下确认真实物理租约、Ring／maps／generation、旧逻辑成员、VM／task及不可变身份，通过新增的实际Board physicalContextCheck核对原有电源、时钟、SMMU、IRQ、认证等完整资源条件。该检查不借用旧任务的用户授权，不重复初始化或OOB请求。

DirectSubmit wait／waitAll新增明确的pendingFence输出，只有实际NativeRingFenceTimeout设置true。零预算执行原Ring的一次缓存获取和fence比较，不做idle等待重试；已完成fence后的VM／资源释放Timeout保持false。Root仍调用真实全任务／资源drain和原有界硬件idle，之后再次检查物理资源，仅允许原SMMU精确旧子上下文RestoreKernel及TLBSYNC／读回。旧VM、BO、映射和ASID保留，后续调用方走自己的原Select／Close后端。SMMU新增实参约束，物理作用域不能Select或访问其他子上下文。未知结果停止并保留，不复位、不猜测释放。

## 回归与构建

[真实fence源码检查](../scripts/check-ios26-context-fence.py)、[上下文检查](../scripts/check-ios26-context-handover.py)、[物理回调检查](../scripts/check-ios26-context-physical.py)及保留的[成员检查](../scripts/check-ios26-shared-members.py)均以当前实际方法编译，通过ASan／UBSan与TSan，显式关闭symbolization。覆盖完成后Close、未完成Busy不写MMU、后续Root关闭、错误task／成员／generation、迟到故障、两次物理检查拒绝、释放Timeout不能当pending，以及原最后成员clear。MMIO、缓存、SMMU执行、drain与资源等主机边界均明确为fixture，不能当作实机证据。

原Ring对象无法按原配方逐字节复现，保留结果且不解释机器码。当前改为冻结已有Ring源码及实际选用头文件，并用当前原生配方重新编译；源码与原件逐字节一致。修复过一次DirectSubmit头别名遗漏造成的链接缺符号，保留失败产物；最终32个实际消费者／对象重编，1398输入、0undefined、106有效头检查和CPU16KiB通过。GPU／磁盘4KiB独立。完整FAT成员读回、payload重组、原源码文件／section元数据consumer和11份零fuzz补丁重放通过。

- kernel：`ff82ebce97ab2bdc6848161031db65e8e23bcdbc38befd03d4732b2968db74f5`。
- boot：`c5e7e0070c27affe4e8235b1804b5f5c2c47e7264ceb6c04e54d5703ca8723e1`。
- 保留已安装252 root：`859c7ebae6355ef7e089896680b0b8ffd9a03af8a1f078918feec740b7a06b02`。
- ADT：`98f04ff54b9573ddaa2c4716da0e954fae8192d15b1f105426eba7f216805936`；FD：`1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab`。
- 启动ID：`719fc4d092574847b2a3fe9de893e76f`；禁用探针身份`f80eb1403d7e4f958b5eddacb49d98d0`保持。

[来源与补丁](../patches/gpu/ios26-context-handover258/source-manifest.json)、[离线证据](evidence/k80-gpu-v258-context-handover-offline-2026-11-16.json)。源码目录：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v258-context-handover-719fc4d092574847b2a3fe9de893e76f；构建目录：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v258-context-handover-719fc4d092574847b2a3fe9de893e76f。相对257启动包只替换kernel；root、FD、ADT、menu、插件、Metal wire、Turnip、Rust及backboardd政策保留，无新根镜像／增量／安装／手机操作。

## 风险与后续

本次只解决已经完成的旧上下文交接。仍在执行的真实fence返回健康Busy并保留；IOClient在该条件下的有界关闭续行尚未实现，不能宣称完整正常退出已通过。分段清理之间也可能出现其他成员的新提交，后续需要阶段明确的pending状态与续行，不能盲目重试已产生副作用的后端调用。并发逐客户端诊断、独立跨任务工作负载／政策及硬件隔离仍需完成。

下一步继续这些源码工作，再准备精确固定入口、receiver、新scope／ready／claim、300秒WDT与600秒Recovery回归。普通每帧GPU写入／fence／呈现、完整FT3683触点与手势尚未验收。Android／Recovery／iPadOS17／Data及历史产物保留；无反汇编、逆向、符号化或新增commit／push。

# K80 iOS26 v263：修复已证实的跨度元数据容量不足

v262实机在原4096跨度元数据表已用3524条时，请求847条，因只剩572条被真实VM预检拒绝。v263在K80实际Board创建方把prepareHostDirectRuntime参数调到8192；不是修改CPU页大小或绕过映射检查。已完成一次无人值守实机：约332.73秒自动回核验TWRP，38帧／66151字节串口和340秒录像成功。真实rc确认8192生效，但后期仍因剩余47条／请求842条而拒绝，此时已用8145条，共需8987条；首个失败序号822，扩大容量未彻底解决工作负载。相机210秒可见锁屏，330秒可见TWRP splash，未实施手动或合成输入。长按设置卡死原因及完整GPU／Metal／显示／FT3683验收仍未解决。

## 实现与风险

Board→InactiveOwner→BoardClocks→HostRing→Domain→HostGpuTables→实际VM attachSeeded的参数链已核对。后端支持上限262144；本次仅增加CPU ranges／alias_scratch元数据条数，原对象上限4096、CPU16KiB、GPU／磁盘4KiB、权限、固件、时钟、IRQ、映射拒绝条件和生命周期保持。额外分配会占用CPU内存；8192仍是有界容量，后续真实压力仍可能拒绝。不能将v262首个NoResources直接归为最终Settings卡死根因。

UFS串口在成功完成真实worker后读取现有Domain的zorn26_native_runtime_observation[11]，以rc字段报告实际容量；未完成时0。getter来自既有真实Domain，不是恒定成功回调。共享CF261记录类型与262节奏接口保留；普通38帧预留一帧终端、总529408字节、300秒独立WDT／600秒Recovery均不放宽。无串口截图或合成触摸路径被选用。

## 精确输入与验证

- kernel：`cf38fd643a729bd787adef86e9348be4dc494e917e6ca661bcfaec99cf808864`。
- boot：`24dbbd632df3a6bde2f345ceb8b398ec8daee139a310c68f5d8f2d6a8b0032e2`。
- root：`859c7ebae6355ef7e089896680b0b8ffd9a03af8a1f078918feec740b7a06b02`；复用实际安装252根，只读，无新增根镜像／布局写入。
- FD：`1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab`。
- ADT：`98f04ff54b9573ddaa2c4716da0e954fae8192d15b1f105426eba7f216805936`；启动ID：`5870a69eaaaa48439f94d86d2736dba7`。

[源码补丁与来源](../patches/gpu/ios26-span-room263/source-manifest.json)、[离线证据](evidence/k80-gpu-v263-span-room-offline-2026-11-17.json)、[父版本实机](evidence/k80-gpu-v262-mapping-capacity-observed-2026-11-17.json)。构建目录：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v263-span-room-5870a69eaaaa48439f94d86d2736dba7；源码目录：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v263-span-room-5870a69eaaaa48439f94d86d2736dba7。

32个实际对象、1398输入完整链接、0undefined、118有效头核对及CPU16KiB通过。实际编译器预处理确认仅选8192调用且旧4096调用不在当前创建方。真实VM预检提取控制复现3524+847在4096拒绝／8192接纳；8192满额仍拒绝，既有隔离／引用／边界检查保持。此为CPU夹具验证，不证明硬件映射成功。未改后端／共享头以逐字相同证明复用262八项ASan／UBSan／TSan结果，当前worker／frame／Domain getter边界夹具／终端／gate／串口解析另行验证。未使用反汇编、地址或回溯符号化。

[本次实机证据](evidence/k80-gpu-v263-span-room-observed-2026-11-17.json)：7组保护采样字节相同，完整BCB读回／尾部保护通过。最后surface834／fence834匹配、CPUcopy返回；仍无GPU写像素及物理scanout oracle。第二客户端8874调用，未采到关闭或进程退出。离线8192接纳旧4371条需求并不等于整机容量合适；下一步核对已固定houji后端的131072条设计、真实活跃跨度及正常unmap，避免逐次盲目翻倍。后续试验仍须独立固定入口／receiver-first／300秒WDT／600秒Recovery／新scope与零重试。当前Recovery身份、实际固件认证／GMU／HFI、真实有界任务和CPU可见结果、每帧GPU写入／scanout、完整Metal及FT3683触点／边缘均只能由对应硬件证据确认，不能预先视为通过。无人工输入依赖；Settings长按场景尚需后续有界自主观测方案。

新增262／263代码和记录暂存，未自动生成额外commit或push。两个已授权整理commit为UniXNU-zorn8067bd3、uefi-zorn434f827；网站收录修复仍待发布和官方重扫。

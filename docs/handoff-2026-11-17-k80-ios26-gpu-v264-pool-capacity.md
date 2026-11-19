# K80 iOS26 v264：碎片化内存池容量与真实VM回收计数

最近实机[v263](handoff-2026-11-17-k80-ios26-gpu-v263-span-room.md)确认8192跨度容量生效，但后期在已用8145条、再请求842条时仍被拒绝。相机210秒可见锁屏；38帧／66151字节、340秒录像与保护采样通过，约332.73秒自动回核验TWRP。单次零重试，无人工或合成输入，Settings长按场景未实施。扩大到8192只是推迟首个拒绝，不算容量问题已修复。

v264已完成一次无人值守实机：38帧／68910字节串口与340秒录像通过，约332.67秒自动回核验TWRP，零重试、7组保护采样相同、BCB完整读回／尾部保护通过。真实rc131072，采样窗口内未记录到跨度容量拒绝或被采样客户端后端错误。相机210秒可见锁屏、330秒可见TWRP splash。当前实际K80创建方选131072条CPU跨度元数据，仍在后端262144上限内；对象上限4096、CPU16KiB／GPU4KiB、原VM权限／预检／事务／引用／隔离／正常清理保持。

## 来源与实现

固定UniXNU-houji提交98bc0960f96076de8e8d16efcfb0c0603b166b85的archive/native/gpu/xnu/Adreno740/NativeAdrenoGpuContext.cpp已使用131072容量，其注释说明64MiB Metal池的物理碎片可能占用大量跨度。该文件是此提交的历史实现，不宣称它是当前houji已编译入口。另核对该提交实际NativeAdrenoVm.cpp容量边界与NativeAdrenoPublish.cpp动态跨度CPU视图。三个文件均与git固定提交逐字核对，精确SHA见[源码清单](../patches/gpu/ios26-pool-capacity264/source-manifest.json)所指引用回执。仅复用公共CPU元数据配置与内存池依据，没有移植houji板级地址／时钟／IRQ／表页配额。

实际K80 VM的正常unmap依次完成事务／release、erase跨度、retireAfterQuiescence、drop表面与清对象，源码未见“正常路径永不删除跨度”的现象；这不排除其他持有／泄漏，需要实机数据。v264把已有成功map／unmap计数和字节累计写改为原子操作，新增CPU getter与串口vm字段。getter不访问MMIO或对象指针，各字段独立采样，不是相同时刻的live-PTE清点，也不能单独判定泄漏、静止或允许释放。现有Domain rc继续报告真实容量。

## 精确构建与验证

- kernel：`a59c448b2ba3ff7256770697e76f1d31bc166aac24bbd382fe17f20758c4d0f0`。
- boot：`790944504ff17d602c0d18a89b803f46264d67363aabec62570705855a4c276d`。
- root：`859c7ebae6355ef7e089896680b0b8ffd9a03af8a1f078918feec740b7a06b02`，复用已安装252只读根，无新增根／布局写入。
- FD：`1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab`；ADT：`98f04ff54b9573ddaa2c4716da0e954fae8192d15b1f105426eba7f216805936`。
- 启动ID：`a1d69e45450e4415aa5b23c975a011bc`；禁用探针ID保持f80eb1403d7e4f958b5eddacb49d98d0。

[当前离线证据](evidence/k80-gpu-v264-pool-capacity-offline-2026-11-17.json)、[父版本实机证据](evidence/k80-gpu-v263-span-room-observed-2026-11-17.json)。构建：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v264-pool-capacity-a1d69e45450e4415aa5b23c975a011bc；源码：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v264-pool-capacity-a1d69e45450e4415aa5b23c975a011bc。

32实际对象／1398输入完整链接0undefined，118有效头核对，实际编译器仅选131072并拒绝旧身份。六补丁零fuzz重放。真实预检提取重现4096和8192两次实际需求的拒绝，131072接纳对应需求且满额仍拒绝；硬件边界用明确CPU夹具。当前计数器与getter的40000次CPU并发更新在ASan／UBSan和TSan下通过；原VM除原子计数和getter外逐字投影相同，既有生命周期测试仅按正文／共享头相同证明复用。当前worker／服务／frame／终端／gate／解码另行验证，最坏完整帧3071字节，journal198字节。最初主机frame夹具缺cstdint导致编译失败，原失败产物保留，仅修复夹具并重跑成功；原生构建已使用真实头独立通过。

[实机证据](evidence/k80-gpu-v264-pool-capacity-observed-2026-11-17.json)记录1039次成功map／700次成功unmap，累计字节9458040832／8912928768。各字段独立采样，只说明正常回收确有发生；不是一致live-PTE清点，不能据此排除其他泄漏或长期耗尽。最后surface645与fence648匹配，copy返回，仍无GPU写像素／scanout oracle。第二客户端7400调用，未采到退出／Close。Settings长按场景仍未实施，不能把本次成功回收当成原卡死已解决。后续试验仍需新scope／独立归档／receiver-first／300秒WDT／600秒Recovery／零重试；完整GPU写像素、Metal／显示与FT3683验收仍未完成。没有依赖用户操作的步骤。串口截图已核验sheng源代码参考，另有未集成的265公共SHOT／分片代码及ASan／UBSan／TSan控制，当前264未选用截屏功能。待接通实际K80 presenter完成点与原CDC owner后才生成完整265候选；不借用sheng地址或分区。

新增工作暂存，不自动生成额外commit或push。已授权整理commit仍是UniXNU-zorn8067bd3、uefi-zorn434f827；设备目录EOF本地修复仍待发布与官方重扫。

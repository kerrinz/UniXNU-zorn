# K80 iOS26 v260：原生平台记录与panic身份统一

准备259有界回归时，当前终端源码检查在访问手机之前发现身份不一致，已停止该准备路径、保存失败并生成独立260候选。**没有259设备访问、scope／ready／claim或启动。** 后续已用260进行一次有界回归并在333.19秒自动返回TWRP，提交／关闭错误保留，完整GPU／呈现／触控验收未完成，目标继续active。

## 根因与修复

259原生VFS覆盖层仍指向258构建目录中的ZornPlatformRecordIdentity26.h及ZornPlatformTrialIdentity26.h，虽然UFS／CDC／package已使用259启动ID。此前源／头检查覆盖的是列明的GPU接口，未覆盖这两份构建目录生成头；这次真实终端包解码拒绝了不匹配ID。它不是旧实机Timeout根因，不能修改历史运行身份。

260把两份头固定到候选源码record-identity目录，四个实际别名指向同一组当前头，不再隐含借用父构建目录。UFS／CDC使用同一新启动ID。32个实际对象重编后完整链接；[新检查](../scripts/check-ios26-native-identity.py)调用实际native编译配方预处理，验证五个实际消费者中的记录／panic数组与kernel／UFS／CDC／artifact身份相同。再将独立测试覆盖层换回实际258旧头，预处理结果必须被拒绝。没有查看或解释机器指令。

## 当前验证与精确构建

当前panic sender／transfer／epcmd检查已用编译器实际选中身份头通过，保留未知DMA状态；early launch、CPU原子发布、真实worker／service创建、后期门和close recorder当前源码检查通过。259共享上下文／有界关闭及联合退休链方法在260逐字节不变，保留的sanitizer结果只按精确源码相等复用，不把旧内核的硬件资格转移到新候选。SMMU、Ring、Submit、VM、Board、Metal／Turnip／Rust和触控实现均未改动。

完整1398输入0undefined，111有效头检查，CPU16KiB及独立GPU／磁盘4KiB通过。四份补丁零fuzz重放，完整FAT成员读回、payload重组和原源码文件section元数据consumer通过；只替换kernel成员。

- kernel：`0760266217b3d721f1799c859958310ced40b3f74c802266926b841f8b918f43`。
- boot：`a4f282c67941ce334df0df4ef220498418e271f52745f9c33e87d447db32ebef`。
- root：`859c7ebae6355ef7e089896680b0b8ffd9a03af8a1f078918feec740b7a06b02`，保留实际已安装252根、只读运行。
- ADT：`98f04ff54b9573ddaa2c4716da0e954fae8192d15b1f105426eba7f216805936`；FD：`1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab`。
- 启动ID：`81683386ba0d423d817a2b7d0e1c60f0`；禁用探针身份`f80eb1403d7e4f958b5eddacb49d98d0`保持。

[精确补丁与来源](../patches/gpu/ios26-platform-identity260/source-manifest.json)、[离线证据](evidence/k80-gpu-v260-platform-identity-offline-2026-11-16.json)。源码：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0；构建：/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0。FD／ADT／menu／根／插件／政策均保持，无新根或布局写入。

## 后续与限制

继续以新固定入口、receiver和camera、完整输入与保护归档、scope／ready／claim、300秒独立WDT与600秒自动Recovery准备普通backboardd回归，先确认实际日志身份、初始化和关闭生命周期。该阶段不要求完整桌面验收先完成，也不等于独立跨任务工作负载／政策或实际隔离通过。每帧GPU写入／fence／呈现、实际退出、FT3683完整触点／手势仍需对应精确构建的实机证据。Android／Recovery／iPadOS17／Data及历史产物保留；无反汇编、逆向、符号化或新commit／push。

## 260单次实机回归

此节追加到已保存的离线创建证据之后，不把创建时的“未执行”证明改写成运行结果。精确kernel／boot／FD／ADT／根与上节一致，scope／ready／claim全新；固定receiver先于启动，原核心工具不变，从核验TWRP开始一次临时启动，0重试，333.194828秒自动回到同版本TWRP。七组Data／metadata／根边界采样逐字节一致，BCB尾部保留且整页读回。只读根与原单4KiB日志／有界BCB路径保持，未新增根写入、bootstrap、刷机、布局或槽位操作。

39帧58152字节串口传输完整；原生记录和CDC均为当前260身份。CPU_done1、online8、CPU／USER／SYSTEM掩码均ff；worker state3／forward88、注册point6／ack6／failed0，publication为0x100000000。它们是源码定义的实际检查点，不是完整GPU验收。

backboardd unique／PID10第一段9调用、Close0；第二段3119调用后Close返回0xe00002ca（当前源码IOReturn.h定义为kIOReturnIOError）。最后native-return225样本为method17 SubmitBatch、run／external均0xe00002c2（kIOReturnBadArgument）。这是有界采样最后记录，尚不能认定它是第一个错误或关闭错误的根因。现有close内部里程碑只在panic导出，本次没有panic包；因此不能知道此次错误具体发生在quiesce、releaseAll、VM退休还是其他真实分支，下一步需记录精确客户端的首次失败原因与关闭阶段，不能猜测或改写为成功。

原始stderr journal9170字节／60记录、pending0／gap0、CRC4111814243、SHA6e50033d50dc7ead02e23ea656febcaea84229ee902dc7d6d8441b82c8850db6，捕获exited1／原始status15；没有正常退出或完整应用验收结论。旧compact窗口drop57，仍保留。末次surface记录为frame245／SID277、1125×2436、producer／tail／completed177、lease2、acquire／copy账本成立，但GPU access fence为0、GPU写入与物理scanout均未证明。

固定camera入口退出251，错误为Video device not found，未获得视频或物理图像证据。相机失败没有触发任何手机重试或改动Recovery流程。当前设备操作空闲、stop标志false；后续继续离线定位，下一次启动必须使用新候选／scope／ready／claim。

[实际回归证据](evidence/k80-gpu-v260-platform-identity-observed-2026-11-16.json)绑定完整归档。实时源码读取未使用反汇编、地址符号化或逆向。尚未验收并发逻辑成员／跨task隔离、待完成Close分支、实际正常资源退出、逐帧GPU写入／呈现和FT3683完整触点／手势。

## 相机复核

机主确认本机相机可用后进行了仅主机的复核：同一ffmpeg在受限执行环境中列举不到视频设备，在完整权限环境中能发现相同名称USB  Camera，并成功采集3秒无音频视频与静帧。因此260相机失败应归于当时执行环境不可见设备，不能说相机硬件不可用。未重启或操作手机，未改系统隐私设置，原260失败回执保持。当前帧可见手机及暗色反光屏幕，没有可读Recovery界面或GPU图像证据。后续固定相机入口在已验证执行环境启动，并先检查设备可见性。[相机复核证据](evidence/k80-camera-host-recheck-2026-11-16.json)。

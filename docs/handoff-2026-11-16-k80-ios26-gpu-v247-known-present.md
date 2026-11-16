# K80 iOS26 v247：已知Metal IOSurface的真实显示队列连接

247已完成独立根增量安装及一次有界实机试验，332.500秒自动回TWRP。首次取得与已校验Metal IOSurface对应的frame/SID、非零access fence和真实acquire/copy记录；摄像头只记录到稍后的锁屏，尚未确认物理棋盘图像。严格应用判定仍因raw诊断丢弃36而未通过。完整GPU/Metal/显示/FT3683验收没有完成，目标active。下方离线形成过程保留其范围；本次Git整理没有新增设备操作。

## 实现依据与实际路径

246表明Metal32×32 IOSurface像素与native close通过，但屏幕1125×2436 SID的关联fence为0；两者不是同一验收对象。实际现有MiniIOMobileFramebuffer的SwapWait直接返回成功，因此它不能作为呈现完成依据。本轮复用实际现有present()事务、所有surface bounds/hold、队列、GPU completion lease、acquire、drawLayer/show和退休处理，没有把SwapWait或新恒定成功回调当作后端。原present()函数与246逐字节一致；DirectClient/VM/Submit、MiniIOSurface及246关联后端原字节保持。

新增板级公开源码接口ZornKnownPresentSubmit247/Query247（0x5a470101/02），不声明为Apple私有接口。只有候选boot arg zorn26_software_accelerator=2才启用（1保持原行为，2保留相同软件兼容路径并增加已知帧接口），原IOKit open及客户端entitlement流程保持。Submit只接受真实32×32 packed RGBA surface SID，临时hold验证后使用实际显示尺寸构造原队列请求；实际present接管独立hold后才drop临时hold。排队失败原样返回，尚未完成的已知请求保持busy，不重试、伪造完成或释放原队列保留资源。只新增静态标量ticket，不改变user-client类布局/虚方法或IOSurface用户ABI。

只有原presenter完成真实show路径后，才按精确frame/SID发布原16word schema2结果。普通UI帧不覆盖这个专用已知帧记录。Query不等待硬件，只有匹配的已完成记录才成功；探针自身最多200次、每次间隔10ms查询，并同时要求GPU lease2、非零且已完成surface access fence、真实acquire、copy counter增量1及frame/SID匹配。IOServiceClose返回值也必须成功。未知或错误记录不能让验收通过。

探针继续使用原Metal设备、shader/pipeline、IOSurface分配、预填充和逐像素/CRC校验；在释放已校验的真实IOSurface及texture前只提交一次显示请求。新增的唯一entitlement为本项目既有IOMobileFramebufferUserClient，未改变全局IOKit授权检查。CPU copy到面板内存、GPU像素来源与物理scanout仍分别判断；原绿色/品红32×32棋盘未变，不新增任意颜色、alpha或完整桌面正确性结论。

另修正246记录语义：CPU lease不查询/带出历史surface GPU fence；GPU lease仍读取真实cache值。否则surface曾被GPU访问而当前使用CPU lease时，原parser可能合理拒绝不一致组合。该修正不改变CPU/GPU实际控制流程。

## 串口与回归

真实UFS producer追加kp=available/16word字段，持续导出最后已知帧记录；正常dp、39帧、3072字节每帧及529408总字节上限保持。新typed247 parser先校验kp再调用246 parser，保留原panic/身份/transport检查；它不自行声称GPU写入或物理呈现。新的程序run tag与内核stderr observer一致，原36次raw诊断丢弃问题未解决，未减弱strict application规则。

真实switch cases和实际probe查询函数分别在host提取测试：配置拒绝、尺寸/计数、排队原始失败、临时hold/drop、一个待完成ticket、错误帧/SID、publication丢弃时保留、完成早于Submit返回、精确取消及10万次并发snapshot；probe26种打开/提交/查询/关闭/错误fence/超时控制通过ASan/UBSan。真实presenter body验证unreadable保留、GPU acquire/show/ticket完成、CPU历史fence抑制；实际producer/worker/registration分支及容量检查通过。当前真实terminal sender重编，29项拒绝、397455字节packet、typed247完整/截断包组合检查通过。边界均有host stub，不能代替硬件。

[新header](../native/ios26-present247/ZornKnownPresent247.h)、[最小补丁及精确来源](../patches/diagnostics/ios26-known-present247/source-manifest.json)、[可重跑host检查](../scripts/check-ios26-known-present.py)、[离线证据](evidence/k80-gpu-v247-known-present-offline-2026-11-16.json)。host脚本需要prepared source-root和新out目录，不访问USB。五份补丁实际应用后逐字节恢复最终源，probe父源与仓库冻结native/ios26/userland源字节一致。

## 精确构建与存储

/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v247-known-present-c0bed9d9c79d4aeca33d0ad509f2984d

/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v247-known-present-c0bed9d9c79d4aeca33d0ad509f2984d

kernel：`bbe690d0446df7046feda16f604578a5638efaa95a180c3880c6e71169811653`，1398输入、29项重编、0undefined；最终70项相关头依赖与全输入SHA通过，仅核对源码、元数据、完整文件哈希和链接输入，不反汇编/逆向或解释panic地址/寄存器。

实际原生编译配方的预处理结果为ARM_PGSHIFT/PAGE_SHIFT=14，即CPU16KiB；与默认format2 arm64e profile的4KiB字段不是同一构建输入，不能混用。新代码未采用4KiB CPU假设；磁盘delta的4KiB块和GPU映射粒度另行处理。该结果及原配方SHA归档于native-platform-config.json。

新root：`dde0082d112afdaa07d46ef15e1b38ca9d6072ed4c0b1d71a578c8b6e3ce6f9e`，32GiB。只替换已签名探针，既有启动job/UID/GID/mode/inode、Metal bundle及其它受监控文件保持；独立克隆的HFSX签名及文件系统检查通过。与原193e5f01…完整根镜像相差63个4KiB页、10组；本地应用这些页后完整SHA一致，末组preimage错误及首组readback错误的停止控制通过。

新root窗口从受保护Data末端按显式1MiB对齐重新计算，再检查旧编译窗口兼容性，没有直接继承旧窗口结论。Data间隔782336字节，root后保留8588886016字节，未与原17系统、Data或单日志块重叠；布局未变。此为离线计算/本地重放，不是手机新GPT或preimage核验，不授权由该文件直接执行写入。247根已通过下方独立安装收据写入手机iOS26窗口；原193e5f01根镜像与Android、17/Data及全部旧产物保留。B247继承的旧installed-root-cohort只描述手机现有根，不能作为新root已安装的收据；部分编译产物/过期描述字段已单独归档，最终完整链接与新root绑定为准。

## 完整包、根安装与单次实测（更新）

初次打包检查拒绝了追加boot arg：原参数已占满1023字节。没有删除任何原启动步骤或截断参数；改为已有software_accelerator参数的模式2，保持原软件服务发布，只启用新板级API。所有实际包含变动共享头的原生消费者重编；用户探针也重新编译签名，与root中的原签名探针逐字节一致，因此root仍dde0082d…。初始f07e5fde…内核、未成功包及旧源码/测试保留在revision-before-profile-mode；不是硬件失败或重试。当前kernel为上方bbe690d0…，boot为`1af1d05edb9c19a341cb66eebbc5896584c7690088e8f56305f5c27313f6aeb2`，FD仍1bf94507…，新ADT为dd49b399…；FAT实际kernel/ADT/menu变化，其余成员保留。

候选包先离线生成，明确不把旧安装收据当作新root已安装。随后单独的Metal247 root-delta scope从真实TWRP开始，核验7200页既有写入证据、所有63页预映像、GPT/Data/17根manifest/边界和完整BCB；10组63页写入与读回通过，聚合SHA为28d7050ac49186ddff8f26cb23bdf900784d0989c44ac9bfd8ea62b38620b33d。七组保护样本（含完整BCB）前后字节一致。没有布局、Android/17/Data、GPT或启动分区写入，未自动启动/重试/恢复刷机；该步停留Recovery。不是全手机32GiB root读回。

独立boot scope随后通过104项错误输入拒绝检查，使用receiver-first、300秒独立WDT和600秒Recovery返回。仅一次临时启动，332.500360584秒回TWRP，outer/inner exit0，39帧46489字节，无解析错误或部分terminal包。boot七组定义的保护样本前后相同，BCB设置后整页读回及tail通过；没有导出terminal panic包，不能由缺包推断完整日志从未发生故障。

已知帧499、SID35、producer/tail/completed/access fence均4、GPU lease2，真实surface acquire通过，copy counter497→498，目标逻辑尺寸1125×2436。探针phase11/flags1023/status4/code0，CRC718ed2ce、badffffffff；按固定源码，phase11发生在原像素oracle及同一surface显示Submit/Query/Close均通过、原资源清理之后。两个native GPU session close均0。此为精确固定源码、程序报告及内核同帧记录的有界对应关系；parser对access标量单独保留GPU_surface_write_proven=false，未提高为通用GPU写入、完整桌面或物理scanout结论。最后普通UI帧SID3/access fence0，仍是软件兼容路径。

raw诊断丢弃仍36，application.complete=false，未削弱检查。约278秒摄像头为锁屏，未拍到此前单次棋盘帧；物理已知图像、完整桌面GPU、FT3683点按/滑动/抬起/身份/边缘及稳定性仍未验收。当前247 claim已消费，不可重用。

[完整包、模式修订与根安装证据](evidence/k80-gpu-v247-known-present-ready-2026-11-16.json)；[单次实测证据](evidence/k80-gpu-v247-known-present-observed-2026-11-16.json)。离线文件中的未安装/未执行状态属于其生成时刻，后续设备事实以这些独立收据为准，不能据新Git提交倒填旧硬件revision。

## 继续工作

继续解决raw stderr的有限缓冲丢弃，同时保留原损失计数，只有完整实际数据送达才可提高严格应用判定；核对真实进程退出与分段日志的生命周期。已知图像的物理观察应使用预先准备的有界摄像头采集和正常显示复用流程，不能用同帧计数代替。之后连接系统真实GPU客户端/Metal呈现路径，不把兼容模式锁屏当作GPU桌面。新的实现、构建和独立准入按其实际输入验证；仅92988a43/zorn/slotA，不bootstrap/重试/刷机，无法回Recovery立即停止设备操作。源码或配方缺口继续自行处理，不作为外部阻塞。

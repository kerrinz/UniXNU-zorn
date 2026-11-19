2026-11-17最新280：新Metal／runtime与公共Turnip完成整栈配套，独立根／完整K80内核／启动包及主机检查通过；保留真实ABI-v1，未安装或上机，GMEM／性能仍待实测。[280交接](handoff-2026-11-17-k80-ios26-gpu-v280-upstream-stack.md)。

2026-11-17最新279：配套上游8c7f9502／46e7cc96＋0063源码已构建为独立、完整链接签名的iOS26 Metal用户态bundle；实际Mach权限／安全读取和有界no-copy适配通过。原v1 Turnip保持，公共Mesa／新root／kernel／boot及硬件帧率仍待推进。[279交接](handoff-2026-11-17-k80-ios26-gpu-v279-upstream-runtime.md)。

2026-11-17上游更新：官方630b85a3已建立逐文件／Git树核验的独立参考仓库，并同步原origin/main；旧main、本地改动及所有K80基线保留。主机测试41通过／1缺工具跳过，新版官方记录检查通过。GPU组件仅核对新钉点，尚未集成或上机。[更新来源、回归和性能候选](upstream-refresh-2026-11-17.md)。

2026-11-17最新离线278：真实presenter的排队／pace／lease／acquire／show计时已接通并完成完整内核／启动包。固定入口因私有ADB5039不可达在claim前拒绝，未启动手机、无新耗时结果；不自行bootstrap或重试。设置交互独立待修，低帧率仍待测量。[278精确交接](handoff-2026-11-17-k80-ios26-gpu-v278-present-cost.md)。

Current hardware update: v256 kernel0f1840cb/boot79249c64 reuses installed252 root859c7eba and completed one protected ordinary-system trial. AutomaticTWRP333.724595s,first native close0/reopen,second last call3293/method13/raw0;surface151/SID183 accessfence154 matches producer/tail/completed/acquire/copy ledger.39frames58147B,intact9170B/60record observed stderr prefix,gaps0,actual8CPU samples and seven protection/fullBCB checks pass. Camera150/225s shows physical lockscreen4:02→4:03. No new root install or retries. Logical admission remains exclusive;independent per-switch MMIO/per-frame GPU-write,daemon exit/fullGPU desktop andFT3683 gestures remain unqualified. [256 handoff](handoff-2026-11-16-k80-ios26-gpu-v256-operation-context.md),[observed evidence](evidence/k80-gpu-v256-operation-context-observed-2026-11-16.json). The earlier offline creation summaries below keep their original chronology.

2026-11-17最新277手动验收：解锁、长按菜单出现／收起、Home手势有响应；设置列表无法滑动但可以回桌面，不是系统整体卡死。按机主指示设置单列待修，GPU主线优先定位低帧率。真实fence72..90／ROI93，无采样后端错误、compact丢失1；333.48秒回核验TWRP，完整验收未完成。[精确交接与机主更正](handoff-2026-11-17-k80-ios26-gpu-v277-manual-acceptance.md)。

2026-11-17 v261实机更新：一次启动约333.63秒自动回TWRP，串口／相机成功，用户确认iOS桌面及滑动／点按／长按／解锁响应，最终长按设置卡死。两条渲染路径均低帧率，不比较帧率高低；GPU稳定性未解决。首个记录后端错误BoMap NoResources，仍待内部容量／映射分支及更晚生命周期日志定位。[本次记录](handoff-2026-11-17-k80-ios26-gpu-v261-client-failure.md)。


2026-11-17：[v261客户端首错日志](handoff-2026-11-17-k80-ios26-gpu-v261-client-failure.md)已完成当前源码sanitizer／串口边界／32对象1398输入0undefined／完整离线启动包；尚无261设备访问或claim。260的Close IOError首个实际失败分支仍待对应内核日志确定，完整验收未完成。


260单次回归已在333.19秒自动回TWRP，原生记录与CDC当前身份、八核、39帧／58152字节及七组保护／完整BCB通过。第一段9调用Close0；第二段3119调用Close0xe00002ca，末次method17 SubmitBatch样本0xe00002c2。保留9170字节／60条无gap journal及exited1／status15，未认定正常退出。相机设备不存在，无视频证据；逐帧GPU／显示及完整触控仍未验收。继续精确客户端首次失败与Close阶段定位，不重试当前claim。


[v260原生平台身份](handoff-2026-11-16-k80-ios26-gpu-v260-platform-identity.md)：259准备终端检查发现VFS仍借用258两份生成身份头，未访问手机／建立claim；260冻结当前记录与panic头并重编32对象，实际native预处理五消费者／旧覆盖层拒绝、1398输入0undefined／111头检查及独立启动包通过。共享GPU／关闭后端逐字节保持259。继续准备固定有界回归；最新实机256，完整GPU／触控未验收。


[v259有界关闭续行](handoff-2026-11-16-k80-ios26-gpu-v259-bounded-close.md)已修复实际258 IOClient遇到健康清理前Busy后不继续的问题：精确Root pending状态经真实scope退出确认，三段分别有界等待，完成段不重做，未知失败保留。小米14固定源码关闭机制已核对，无板级参数导入。当前38／48／75／14控制及并发检查均通过两种sanitizer，32原生对象／1398输入0undefined／106头检查、独立启动包及五补丁重放通过；无259scope／手机操作，最新实机256。继续真实作业退休链、逐客户端诊断、实际退出及GPU／触控验收。


[v258已完成上下文恢复](handoff-2026-11-16-k80-ios26-gpu-v258-context-handover.md)已修复实际257源码的已完成foreign上下文Close拒绝：独立真实Board物理检查、实际fence pending输出、原有界drain／idle及精确RestoreKernel接通，保留旧VM／映射／ASID。当前sanitizer、32原生对象／1398输入0undefined／106头检查、独立启动包与11补丁重放通过；无258设备scope或操作，最新实机256。仍pending的IOClient关闭续行和分段清理间并发提交继续实现，不冒充完整退出已验收。


[v257真实共享成员](handoff-2026-11-16-k80-ios26-gpu-v257-shared-members.md)已接通服务／Board／Ring各自真实成员、短期当前操作身份、独立物理租约及最后成员clear／释放；修复grant后最后资源复核失败未标记Held记录的问题，保留原失败。实际提取成员／上下文／物理生命周期通过两种sanitizer，完整当前内核／离线启动包与九补丁重放通过。未上机、未建scope／ready／claim；其他成员待完成上下文Busy／退出及逐客户端诊断仍需继续，最新实机256。


# K80 iOS26 progress — 2026-11-16

[v256实际操作上下文](handoff-2026-11-16-k80-ios26-gpu-v256-operation-context.md)已接通完整操作mutex及原真实Select／fence-drain／idle／Restore／TLBSYNC读回，保留健康wait的未完成上下文。新候选晚到故障窗口经主机复现并在最终issuer处复核修复，不认定为252实机原因。当前30项上下文／48串行化请求及相关已有控制、31对象1398输入0undefined／90头／CPU16KiB和完整kernel0f1840cb／boot79249c64通过。未上机；逻辑准入仍独占，两个预置context fixture不代替实际多客户端。下一步准备本次重选／恢复的固定有界实机，再继续多成员准入；最新硬件252。


[v255独立物理授权](handoff-2026-11-16-k80-ios26-gpu-v255-physical-authority.md)已接通实际Board acquire／check／release、Ring资源／generation／线程绑定和不再retain首个AppExecution的DirectHfi。原物理谓词、实际OOB序列与逻辑准入保留，正常逻辑释放后才释放物理授权、退休租约；失败保留剩余真实资源。57项物理／29项Board／35项服务控制通过当前sanitizer，实际31消费者重编／1398输入0undefined／90头检查及完整kernelf92e5f03／boot1d7d4520通过。未上机，无新根／安装／scope；逻辑会话仍独占，跨任务上下文尚未接通，最新硬件252。


[v254物理OOB所有权](handoff-2026-11-16-k80-ios26-gpu-v254-physical-oob.md)已把实际DirectHfi请求／clear接到Ring拥有的精确租约，transport／maps独立引用、正常Board释放后的退休和失败保留已接通。当前45项源码控制／12竞争者的ASan／UBSan／TSan、8个实际共享头消费者重编、完整kerneld2396a99／boot336d1b28及元数据检查通过。未上机，无新根／安装／设备scope。物理会话仍独占，持续共享物理授权和多任务上下文尚未实现；最新实机仍为252。


[v253离线会话所有权](handoff-2026-11-16-k80-ios26-gpu-v253-board-sessions.md)已把实际Board acquire／check／release接到独立记录、generation、失败保留和精确正常退休，原完整物理/Ring权限谓词不变。完整kernel3700e98d／boot0af365fb及实际CPU16KiB/header/引用顺序检查通过，root859c7eba和配置沿用252，无新根／安装／手机操作。仍只有一个物理原生会话；共享物理OOB所有者、跨任务上下文及最后关闭释放是接下来的工程工作，不能称已支持并发。最新硬件证据仍为下述252。


最新[v252早期系统实机](handoff-2026-11-16-k80-ios26-gpu-v252-early-system.md)已接通普通backboardd真实原生会话；第一会话正常关闭0后第二会话持续使用，正常frame804／SID836的GPU access fence807完成、acquire／copy／账本匹配。摄像头150／225秒显示物理锁屏和时钟推进；一次启动332.649883秒自动回TWRP，8核实际采样、39帧58161字节、9170字节普通进程完整观测前缀与保护／BCB检查通过。精确kernel8a3e8c25／boot8c01452c／root859c7eba对应独立16页11组真实Recovery安装。它不是完整GPU桌面或生命周期／多原生会话／FT3683手势验收；第二个daemon会话仍在用、无进程退出，旧drop57和末WaitFence返回保持。[精确证据](evidence/k80-gpu-v252-early-system-observed-2026-11-16.json)。


Previous v251 device result:two actual admitted metadata opens,competingQuery returnedexclusive0xe00002c5,both closes0;then120/120 same-surface presentation queries,correctMetal pixels,native closes and actualexit0. Full5680B/56record journal and physical4×4 camera image pass;one boot automatically returnedTWRP332.501s,seven protection samples/fullBCB passed. Legacycompactdrop38 remains visible. Native sessions remain exclusive,ordinary systemGPU/FT3683 gestures remain incomplete. [251 handoff](handoff-2026-11-16-k80-ios26-gpu-v251-lazy-session.md),[observed evidence](evidence/k80-gpu-v251-lazy-session-observed-2026-11-16.json).

Current touch source attribution was traced through actual selected input manifests and independently rebuilt byte-equal forBoard/Source/Worker/Host. Kernel resource owners use16KiB pages;the shared parser is not used to infer page ownership. The actual source still reads capacitance matrices throughDetector,so complete controller contacts/physical gestures are not qualified. [Source-only touch evidence](evidence/k80-ft3683-selected-inputs-2026-11-16.json).

Previous v250 device result:120/120 exact same-surface presentation queries and close passed in14.976753385seconds,with correct Metal pixels,two native session closes and actual exit0. Complete5572B/55record journal,39frames59474B and camera-visible green/magenta4×4 image are bound to kernel52a7b61c/boot6ba14e9d/root40338c39. One boot returned automatically toTWRP in332.473304seconds;seven protection samples and fullBCB/tail passed. Legacy compact app.complete remainsfalse/drop37;the independent full-journal/application-with-Recovery predicates pass. This is bounded probe qualification,not ordinary system GPU desktop or fullFT3683 gestures. [250 handoff](handoff-2026-11-16-k80-ios26-gpu-v250-present-window.md),[observed evidence](evidence/k80-gpu-v250-present-window-observed-2026-11-16.json).

The independent250 root installation checked7300 actual retained pages and all58 new preimages,then wrote/read back58pages in7groups;aggregate matches the full local replay. Signature/fsck,actual16KiB CPU/header and1398input full link checks pass. Root was installed only through that separateRecovery scope;creation-time offline records retain their original uninstalled status. Android/17/Data boundaries and original firmware remain preserved.

v249 is retained as the preceding controlled failure:72submitted/71acknowledged in8.026576145s,exit10,with physical checker already observed. V250 extends only the between-call budget8→20s and preserves120-frame/record/close requirements. It does not inferGPU FPS from the loop duration. V248 remains the first complete5422B/exit0 journal baseline;v247 records the first sameSID/access-fence/acquire/copy correlation. Their original sources,artifacts and consumed claims remain archived.

Current252 selects onlybackboardd and disables automatic probe competition. Its early rootEL0 schedule suppresses the competing metadata placeholder while the actual native service retains normalMetal properties/task admission and source-owned initialization/CDC handshakes. Actual client/surface evidence is now present;the native backend still has one hardware session. Broader cross-task contexts,lifecycle and ordinary attachment-write/submit/fence/present attribution require further implementation;do not remove exclusivity or treat lockscreen alone as a GPU oracle. The previous251 probe-only policy/accessfence0 observations remain historical baselines,not current252 state. FT3683 physical gestures remain separate incomplete acceptance.

## Retained earlier clock-fix evidence

The v244 candidate fixes a reproduced diagnostic clock lifetime bug: DirectClient retained a stack clock/cookie in a global hook; later client cleanup could access it. DirectVM now supplies stateless XNU uptime and DirectSubmit calls it directly. Real fence deadlines,submission,releaseAll and failure retention remain unchanged. All three consumers were rebuilt together.

The exact kernel is `fac558258f3c8f0da78a88c5061dcc5ebdfab5c9644d9301659435bc74567af1`;boot image is `04af84279f32c798142d3f35cc24433c36a23caa2041fc08d909129b7973b05c`. Original ASan stack-use-after-return was reproduced;fixed source sections passed ASan/UBSan. Full link used1398 inputs,27 replacements and zero undefined symbols. Source/header and original-object byte proofs are retained in the evidence. These counts identify inputs;they are not completion criteria.

One protected real-device attempt on92988a43/zorn/slotA returned automatically toTWRP after331.983816seconds. CDC received39 valid frames/34867bytes. The Metal report reached phase11,flags1023,status4/code0,CRC718ed2ce and no bad pixel;both native sessions closed with return0. The strict application verdict remains incomplete because raw stderr diagnostic loss is36. A bound camera frame shows the iOS lockscreen. The seven defined storage protection samples and fullBCB/tail checks match;this is not a full Android userdata readback or Android boot qualification.

The actual framebuffer object was rebuilt byte-identically from its VFS-selected source and references the three Gen7 presentation hooks. It already uses a completion lease and surface acquisition before CPU copying. The lockscreen image alone does not correlate a particular GPU-produced surface,fence,copy and panel result. Complete GPU display presentation,FT3683 taps/swipes/releases/identity/edges and long-term stability remain unqualified. No new firmware build or root installation was performed for244. No disassembly or reverse engineering was used.

## Sources and evidence

- [Detailed244 handoff](handoff-2026-11-16-k80-ios26-gpu-v244-clock-fix.md)
- [Source and device-result evidence](evidence/k80-gpu-v244-clock-lifetime-2026-11-16.json)
- [Frozen source archive](../native/ios26/README.md)
- [Minimal clock patches](../patches/diagnostics/ios26-clock-lifetime244/source-manifest.json)
- [Authoritative porting record](../porting.toml)

Evidence summaries contain hashes and local archival paths. Local paths do not become downloadable logs when published,and this publication does not assign a new Git commit to historical tests. The record retains implemented/source classifications where an original matching published revision or public raw log is absent. Old iPadOS17,Data and successful baselines remain preserved.

## Build and repository scope

The official `scripts/package.sh` is copied byte-for-byte from UniXNU/templates/package.sh at core commit627c932a1573483dd44c29b48a113c3761dd8f55. Its source file SHA is f7b8e3ea043058b9c61d5b45c32b8e7669a85737c89d55d404957c3b43ec4aab. From the device directory,use `scripts/package.sh --os 17 --no-deps --check --out /path/to/new-output`. This validates configuration and patch planning without building or accessing a phone. The supported default configuration remains iPadOS17.7.11;the26 archive is not a generic release target. Complete clean-checkout native assembly and device execution through this entry are not qualified. Local IPSW,trust-cache,Mu firmware and device-specific seed inputs remain external.

See the [official building](https://unixnu.com/zh/building),[packaging](https://unixnu.com/zh/porting/packaging) and [record](https://unixnu.com/zh/porting/records) guides. `uefi-zorn` owns the firmware package and links this single device record rather than duplicating it. Synchronizing these repositories makes no new phone attempt.

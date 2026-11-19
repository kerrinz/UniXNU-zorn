# Redmi K80 iOS 26 · v366 显示与 FT3683 接续验证

设备为 92988a43／zorn／slot A。v366、v363 和 v367 使用各自独立的一次性范围和原 v297 只读根，各启动一次。三次均自动回到 TWRP，七组保护区、GPT、根清单及 BCB 整页和尾部校验通过，根和 Data 写入均为零。更早的行段调度及 v365 部分串口归档仍见[前期交接](handoff-2026-11-19-k80-ios26-v363-v366.md)。

## v366 串口与 GPU 呈现

启动 ID 为 `9e76160c81e643bba12267c2243484ce`，启动镜像 SHA-256 为 `e6d330727679f3af062e0465f0e311e3067253df4fe333aea6243cdff107a3b5`。333.720 秒自动回到 TWRP。串口截图、长观测包和归档逐字节重放通过。11 份提前发布的 DSI 摘要与完整观测包一致。已知 GPU 任务的原生 fence 2 和 CPU 可见 RGBA 读回通过。[实机证据](evidence/k80-gpu-v366-early-scanout-cdc-device-2026-11-19.json)

500 ms 锁屏窗口内发起 16 次呈现，15 次 DSI 完成在窗内，另一次在窗外完成，拒绝数为零。6 次出现 RGB 采样变化。8 次预传输等待均到达空闲，最长 8.370 ms，超过旧版 8 ms 上限。请求入口到 DSI 完成的 P50 为 60.785 ms，最长相邻完成间隔为 50.427 ms。窗口内 30 次确认完成／秒描述当次锁屏 DSI 活动。持续滑动的新帧率、撕裂及 v364 与 v366 的同负载性能差异仍需匹配窗口验证。

## v363 触控 SMMU 无 DMA 往返

启动 ID 为 `2c057a352f824c9990376d46a6a5962d`，启动镜像 SHA-256 为 `5a891df0190c15dc8cb111d606715990fbc834de12bc34ec707dfa497a3aa4b3`。333.784 秒自动回到 TWRP，完整串口和 Recovery 归档独立重放一致。GPII 0 保存未分配状态，GPI SID `0xb6` 与 QUP SID `0xa3` 复测均为未匹配即 fault。往返在 `attachQuiesced` 前拒绝，无 bank、故障来源和 attach／detach 返回码，无 DMA 提交。v363 的串口字段无法判定具体拒绝阶段。[实机证据](evidence/k80-ft3683-v363-apps-smmu-roundtrip-device-2026-11-19.json)

## v367 触控拒绝阶段

启动 ID 为 `563a3c360ee24e19a3f910d47c5f3640`，启动镜像 SHA-256 为 `ed78ed3ea0ffbd1a098268ab023d42d6e85a59f13f6abe1efb2830ff104cdd81`。新增 `K80FT367` 记录线程上下文、aperture 发布、UFS 锁、UFS 所有者、完整映射、几何和 UFS bank 检查。只有读取了 IDR1 才报告其值。原拒绝、回滚及故障保留路径沿用。实际 arm64e 配方重编 43 个对象，完整链接 1,400 个对象，零未定义符号，FAT 回读仅内核变化。主机覆盖全部记录阶段、矛盾包拒绝、归档与历史重放。[补丁](../patches/touch/ios26-apps-smmu-gate367/candidate.patch) · [源码清单](../patches/touch/ios26-apps-smmu-gate367/source-manifest.json) · [离线证据](evidence/k80-ft3683-v367-apps-smmu-gate-offline-2026-11-19.json)

v367 在 333.576 秒自动回到 TWRP。串口截图和归档逐字节重放通过。FT3683 走到 `aperture_unpublished` 后安全拒绝。后续只读采样已能看到 APPs SMMU，两个 SID 仍为未匹配即 fault。GPII 0 未分配，未调用 attach，未提交触控 DMA。GPU 已知图像和 fence 2 通过。原 8 ms 等待预算下，500 ms 锁屏窗有 16 次 DSI 完成、1 次拒绝，13 次确认完成伴随 RGB 采样变化。帧率报告现在兼容附加 FT3683 字段的 v363／v367，同时保留 v366 输出格式。[实机证据](evidence/k80-ft3683-v367-apps-smmu-gate-device-2026-11-19.json) · [帧率报告脚本](../scripts/report-ios26-fps.py)

## v368 按 UFS 就绪顺序启动触控

`GenericARMPE` 对原生根配置延后触控启动。UFS 完成 APPs SMMU 发布尝试并确认原根设备注册后，由现有入口创建 FT3683 线程。触控保留实际 aperture、GPII 空闲、UFS 锁、bank 和故障保留检查。补丁重放、43 个 arm64e 对象重编、1,400 个对象完整链接、FAT 内核替换及串口／Recovery 回归通过。启动 ID 为 `0b1d9fe655b34f3cbcf0aa993fe6430b`，启动镜像 SHA-256 为 `50a32030ab3b32ced3a272d360eadefbadefe9a3031c48a8e5dd56a7cf16f6aa`。根注册失败的原生根启动将跳过触控。实际申请和释放需用 v368 的独立实机范围验证。[补丁](../patches/touch/ios26-apps-smmu-after-root368/candidate.patch) · [离线证据](evidence/k80-ft3683-v368-after-root-offline-2026-11-19.json)

SM8650 GPI SPI 公共控制接续已有 ring 实现，按小米内核固定提交 `d9e81e6bcc4ac43c247dcbd382d1d8ff1e5f22d9` 的事件环、TX／RX、SE4 scratch 和命令 IRQ 顺序建立状态。ASan 和 UBSan 通过控制与 ring 测试，覆盖错误 IRQ、超时、失去时钟和无法确认停机时保留资源。iOS26 仍需接通真实 MMIO、IRQ 和 SMMU 所有者，再开始有界 SPI DMA。完整 Metal 呈现、客户端退出与资源回收，以及 FT3683 受控触点和边缘验收仍待完成。[GPI 控制](../soc/sm8650/GpiSpiControl.h) · [离线证据](evidence/k80-ft3683-gpi-control-offline-2026-11-19.json)

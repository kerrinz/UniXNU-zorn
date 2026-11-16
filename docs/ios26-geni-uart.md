# K80 iOS 26 GENI 调试串口

K80 原厂调试串口的设备树配置是 QUPv3 wrapper 2 的 S7，物理地址 `0x89c000`，GPIO30 为 TX，设备树给出 115200 8N1。XNU 候选沿用启动时已配置的 GENI UART，检查 GCC 时钟、TX 复用、协议、FIFO 格式和 GIC 中断。发送在普通内核线程中进行，最多 512 字节，FIFO 等待和命令完成共用一个有限轮询预算。该候选从已验证的 CPU 桌面镜像派生。

Mac 端先确认适配器对应的 `/dev/cu.*` 节点。实体接点和信号电平需按实际主板确认，采集只需接手机 TX、适配器 RX 和公共地。手机留在 TWRP。联动脚本会先打开接收端，随后执行已归档的单次临时启动。

```sh
python3 UniXNU-zorn/scripts/zorn_ios26_geni_capture.py /dev/cu.ADAPTER
```

联动候选的启动镜像 SHA-256 为 `13869784b10cb48bc9a443dffd7b2f29f9c7dcdba3b54a86e9c45c83c0af298d`。脚本在该候选的 `root-trial/trial` 中保留原始串口字节 `uart.raw` 和校验结果 `uart-capture.json`。回到 TWRP 后，用新 UFS 状态页中的记录逐字节核对串口日志正文，并核对镜像标记和完整行结束符。UART 状态为 0 时表示控制器报告发送完成，状态 2 表示发送前拒绝。当前串口调用点在 PID1 启动后的诊断线程，早期启动日志和 panic 输出需要独立的内核控制台接入。

[UniXNU 调试与日志](https://unixnu.com/zh/guide/debugging) · [UniXNU UEFI 集成](https://unixnu.com/porting/uefi-firmware)

## 真机结果

首次探测拒绝发送。随后读到主／从序列器空闲、TX FIFO 为空，唯一挡住发送的是继承的 `M_IRQ_EN=0x33c0007e`。该值与 MiCode 的通用 GENI 中断掩码一致。修正版核验对应 GIC 中断处于禁用状态后允许 FIFO 发送，控制器返回完成。约 333 秒自动回到 TWRP，七组存储保护样本一致。当前 Mac 只枚举到内置调试串口和蓝牙串口，线路接收尚待验证。

[首轮状态读回](evidence/k80-ios26-geni-state-observed-2026-11-13.json) · [发送完成记录](evidence/k80-ios26-geni-send-observed-2026-11-13.json)

## 分阶段日志候选

独立候选 `715f7756` 使用 `zorn26_geni_stages=1`，在 UFS 根设备准备前、注册成功后、PID 1 诊断线程开始时，以及原有 150 秒快照处输出带镜像标记的串口记录。各阶段最多尝试一次，共用一组映射。每次发送前重新检查时钟、TX 复用和中断所有权。一旦控制器拒绝、超时或报错，本次启动停止后续串口写入。

候选已完成完整链接、启动包回读和主机寄存器模拟，保留 300 秒独立看门狗。分阶段采集工具会在启动前打开串口，回到 Recovery 后验证四条记录的顺序、镜像标记、CRLF 和 UFS 快照正文。离线回放用历史实机 UFS 日志及合成串口字节测试了拒绝条件。独立运行清单已通过主机检查，尚未生成启动准入或启动该镜像。先用上文的单条日志候选验证实际线路接收。四个检查点覆盖根设备到诊断线程，早于根设备准备的日志仍待接入。

[分阶段候选的离线证据](evidence/k80-ios26-geni-stages-host-2026-11-13.json)

## 使用现有 USB 线的 CDC 预检

一加 Ace 5（giulia）已验证 SM8650 上的 USB CDC 日志。本地小米 14（houji）iOS 26 原型可复用其控制器和协议代码，但此前未能枚举，记录指向 USB 的 SMMU 路由。K80 预检 `4ef3b371` 从 CPU 桌面镜像派生，按 K80 小米设备树读取 GCC 电源和时钟、DWC3 的角色和停机状态，以及 apps SMMU 的 USB SID `0x40`。它在现有单页 UFS 日志中保存观察结果，随后由固定运行工具从 Recovery 取回。

预检只有寄存器读取，不分配 DMA 缓冲或修改时钟、PHY、控制器及 SMMU。沿用同一根镜像、ADT 和固件，保留 300 秒独立看门狗。即使预检读到有效的身份映射，CDC 枚举和日志接收仍需后续镜像验证。

单次真机预检读到 DWC3 ID `0x33313130`、设备模式和停机状态。USB SID `0x40` 唯一匹配到上下文 4，`CBAR=0x0001f000`、`SCTLR=0x000000e0`、`CBA2R=1`，符合该预检的身份路由条件。332.87 秒后自动回到 TWRP，七组保护样本一致。后续 CDC 候选需在接管控制器前重新核验该路由，并单独验证 DMA、枚举和主机日志接收。

[K80 CDC 真机预检证据](evidence/k80-ios26-usb-cdc-preflight-observed-2026-11-13.json)

CDC 发送候选复用了 houji 的端点和描述符。两份候选各临时启动一次，均在约 333 秒自动返回 TWRP。首份的编译配方屏蔽了返回类型诊断，错误码无法定位故障。修正版开启返回类型错误检查，真机日志确认 `DCTL.CSFTRST` 在 500 毫秒内未清除，启动在编程事件 DMA 前停止。USB 事件、控制请求和完成字节均为零，Mac 未接收到标记。

[首轮发送记录](evidence/k80-ios26-usb-cdc-tx-first-observed-2026-11-13.json) · [DWC3 复位超时记录](evidence/k80-ios26-usb-cdc-reset-timeout-2026-11-13.json)

候选 `2201ddb3` 在设备复位前清除两路 `SUSPHY`，并按原厂 `dwc3_gadget_dctl_write_safe` 保留 DCTL 其他字段。主机模拟覆盖寄存器写入顺序、复位成功、超时和回读拒绝。真机回读表明两路 `SUSPHY` 启动时已经清零，复位超时后 DCTL 为 `0x50f00000`。本轮在分配 CDC DMA 前停止，332.71 秒后自动回到 TWRP，七组保护样本一致。原厂恢复流程还启用 UTMI 和 sleep 时钟，并从 PHY 驱动恢复参考时钟与供电。K80 当前候选只确认了主时钟和两条 AXI 时钟，需先读取其余时钟及 eUSB2 状态，再确定初始化缺项。

[PHY 复位候选真机证据](evidence/k80-ios26-usb-cdc-phy-reset-observed-2026-11-13.json)

时钟候选 `a2c6015c` 在复位前核验 GCC sleep 和 mock UTMI 分支，两者原本已开启，原始和最终读数均为 `1`，本轮未取得新的分支时钟投票。两路 TCSR PHY 参考时钟的使能位均为零。USB2 BCR 为零，由于 USB2 参考时钟未确认开启，本轮跳过 eUSB2 本体读数。DCTL 仍为 `0x50f00000`，在 CDC DMA 分配前停止。332.73 秒后自动回到 TWRP，七组保护样本一致。下一步需核对 eUSB2 的 CXO 父时钟、供电和 repeater，再按原厂顺序准备参考时钟。

[CDC 时钟候选真机证据](evidence/k80-ios26-usb-cdc-clock-observed-2026-11-13.json)

候选 `93601ec9` 在原有 sleep 和 UTMI 分支上增加两路 TCSR PHY 参考时钟投票。eUSB2 读回符合已启用、退出 POR/SIDDQ 且 SLEEPM 置位的条件，随后 DWC3 的软复位完成。Mac 在 `/dev/cu.usbmodem21201` 收到与镜像标记完全一致的 49 字节，设备端也记录 49 字节完成、124 个 USB 事件和 22 个控制请求。手机 332.75 秒后自动回到 TWRP，七组保护样本一致。该结果覆盖有界 CDC 发送，GPU 运行日志与持续内核日志需在后续候选中接入验证。

[CDC 收包真机证据](evidence/k80-ios26-usb-cdc-ref-observed-2026-11-13.json)

[UniXNU 一加 Ace 5 适配页](https://unixnu.com/zh/devices/giulia) · [UniXNU USB 适配](https://unixnu.com/porting/usb)

## UniXNU 上游参考

官网的串口配置和抓取流程以板级 UART 已就绪为前提。UEFI 日志使用 `EFI_SERIAL_IO_PROTOCOL`，XNU 的 `serial=3` 还需要匹配的内核串口后端。官网 K80 设备页没有列出 GENI 引脚或内核控制台接入步骤。当前 GENI 发送候选仍需确认 Mac 能从实体线路收到日志。[UniXNU 串口配置](https://unixnu.com/zh/guide/debugging#串口) · [官网 K80 记录](https://unixnu.com/zh/devices/zorn)

同为 SM8650 的 giulia 提供 USB CDC 终端和主机采集代码。上游终端的交互命令依赖 giulia 协议 2。K80 当前使用自己的单向检查点格式，v105 已在 Mac 上收到 120 字节，并与同次启动的 TWRP UFS 回读逐字节核对。早期 XNU 日志、panic 输出和持续采集仍待接入验证。[giulia USB 终端实现](https://github.com/tycykp/UniXNU-OnePlus-Ace5/blob/main/docs/USB_TERMINAL.md) · [UniXNU 日志抓取与自动测试](https://unixnu.com/zh/porting/log-capture) · [K80 v105 实机证据](evidence/k80-gpu-v105-seed-cdc-observed-2026-11-14.json)

K80 v137 至 v140 的 GPU 检查点均由 Mac 的 `/dev/cu.usbmodem21201` 收到，并用镜像标记和同次启动的 UFS 正文核对。v139 另外记录了 CM3 初始化结果，v140 记录了 PDC/RSC 写入结果。该 USB CDC 口在临时启动期间枚举，回到 TWRP 后消失。Mac 当前未发现独立的实体 GENI 串口设备。[v139 串口证据](evidence/k80-gpu-v139-cm3-ui-cdc-observed-2026-11-14.json) · [v140 串口证据](evidence/k80-gpu-v140-pdc-rsc-cdc-observed-2026-11-14.json)

v142 的 CDC 日志增加了实际 HFI 查询应答，能读取请求头、返回值与固件状态。它仍是单次启动检查点。[v142 HFI 串口证据](evidence/k80-gpu-v142-hfi-query-cdc-observed-2026-11-14.json)

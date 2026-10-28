# FT3683 通信测试：启动与日志回传

本轮镜像 `bce3bdbe` 已编译/完整归档/校验，**尚未在手机上启动**。目的是验证 K80 FT3683 芯片 ID 和固件版本，不运行 iPadOS 锁屏，不提供 HID 或触摸响应。

正常路径：临时启动 → UEFI 原生 L14/L12 电源及串口时钟交接 → XNU 检查空闲/所有权 → GPIO SPI 读取 `A3/9F/A6`（CRC、最多3次重试）→ 恢复 GPIO → 单4KiB日志 → 自动 recovery。不会刷新触控固件，不写 OS/SystemOS 或重置 Data。

## 其他 Windows 电脑：不需要 Python

使用 `K80-touch-bce3bdbe-windows.zip`，整体解压并在该目录打开 PowerShell。现有 adb/fastboot 放在 PATH，或把完整 `platform-tools` 文件夹放到解压目录内。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\test-k80.ps1
```

回传新生成的 `logs\时间-bce3bdbe.zip`。`-CheckOnly` 仅离线核对镜像；`-CollectOnly` 仅在 recovery 读取现场日志并明确标为未绑定轮次。脚本检查固定镜像哈希和设备身份，处理 recovery BCB、临时启动与有界自动回收；无 Python 依赖。镜像只测芯片通信，不会进入锁屏，也不能验证触摸手势。Windows USB 端到端尚待机主测试。

开发机输出路径：`out/zorn/touch-return/K80-touch-bce3bdbe-windows.zip`。包内 `README-Windows.md` 含完整步骤和失败处理。

## 开发机：Python 一条命令启动并抓日志

手机连接这台电脑，保持 recovery 或 fastboot，**不要启动 Android**。在终端执行：

```sh
python3 /Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/test-zorn-touch.py
```

脚本锁定 `92988a43 / zorn / slot b`。它检查固定归档及内核 SHA，准备并读回 recovery BCB，然后只执行 `fastboot boot`。若起始状态是 fastboot，会先通过固定的已知 recovery bootstrap 回到 recovery；之后才启动新测试镜像。不会操作 CC9，不执行 flash/erase/set_active。

保持 USB 连接，等待它自动返回 recovery。此前同类短测约 50 秒完成，本轮上限为启动后360秒；时间不是触控成功判据。不需要轻触或滑动，本版尚无触摸上报。

结束时会打印 `Return this log bundle: ...zip`，日志包位于：

`/Volumes/macData/projects/ios-zorn/out/zorn/touch-return/`

**回传本轮新生成的 ZIP 即可**。其中包含固定候选身份、本轮 `run.json`、新旧日志块和解码文本。完整运行目录仍在 `out/zorn/debug/时间-bce3bdbe/`。日志必须是这轮的新记录，不能拿上轮 `TOUCHRO` 结果代替。

## 仅离线核对

```sh
python3 /Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/test-zorn-touch.py --check-only
```

此命令不访问 USB。

## 未能自动回 recovery 时

若脚本超时或失败，先回传它已保存的 ZIP，不要反复启动。如果必须手动复位，长按电源＋音量下回 fastboot，再用已有 recovery 入口回 recovery；不要进 Android、改槽或刷分区。回到 recovery 后还可以单独保存现场日志：

```sh
python3 /Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/read-zorn-log.py --save /Volumes/macData/projects/ios-zorn/out/zorn/touch-after-reset.bin --tail 100 > /Volumes/macData/projects/ios-zorn/out/zorn/touch-after-reset.txt
```

此时将 `.bin`、`.txt` 和之前 ZIP 一并回传，并说明手动复位过。单独读回的日志要比对运行前 SHA，不能仅凭文件存在判为新结果。

## 固定身份与已通过检查

- Boot SHA256：`bce3bdbe437455d7ed4049539b2881556fa8f4aeb89216b583620203838ba414`
- Kernel SHA256：`b3e264980b47c8b51ab3e2d68ccf7983bb65e4d333454dd7cb434f31a53497b1`
- 固定镜像：`out/zorn/builds/bce3bdbe/boot.img`；当前 `out/zorn/boot.img` 与它相同。建议运行上面脚本，它会先校验固定归档，不依赖以后被替换的默认路径。
- ASan/UBSan：全部256个命令值的白名单、CRC已知向量、错误状态/CRC/传输故障/全FF响应、有限重试、GPIO所有权/保持保留位、16种GPI状态、SPI mode0实际位序。
- 最终链接核对：实际 `native_legacy_display_late_probe` 调用芯片探针与受限日志/recovery路径；不是仅有源码或未使用的目标文件。
- 真机已验证的上一轮 `7ce0e293`：电源交接路径走通，SE时钟开启、SPI固件/空闲状态可读，自动回收。它尚未发送芯片通信命令。

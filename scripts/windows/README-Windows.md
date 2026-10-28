# K80 FT3683 命令行测试包（bce3bdbe）

仅用于这台已部署 SHNGROOT 的红米 K80：`92988a43 / zorn / slot b`。
本版仅读取触控芯片 ID/固件版本，尚无 HID/触摸响应，**不会进入系统锁屏**。
不要把它用于其他手机。不要启动 Android、刷分区、清除或切换槽位。

## 准备

1. 将整个 ZIP 解压到 Windows 的一个可写目录，例如 `C:\K80-touch`。不要只取出 boot.img。
2. 电脑需要 Windows PowerShell 5.1 或更新版本，以及能识别手机的 adb/fastboot 驱动。
3. 使用你现有的 Platform-Tools：将其目录加入当前 PowerShell 的 PATH，或把完整 `platform-tools` 文件夹放到解压目录内（保留 DLL）。不需要 Python，也不需要管理员权限。
4. 手机保持 recovery 或 fastboot，连接 USB，只启动一个测试脚本。脚本只定向操作序列号 92988a43；CC9 f85d4270 不会被操作。

## 运行

在解压目录打开 PowerShell，执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\test-k80.ps1
```

如果 adb/fastboot 不在 PATH，先执行这一行，将路径换成你实际的目录：

```powershell
$env:Path = "C:\platform-tools;" + $env:Path
```

`ExecutionPolicy Bypass` 仅作用于本次 PowerShell 子进程，不修改系统执行策略。
可先做完全离线的镜像校验（不会访问 USB）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\test-k80.ps1 -CheckOnly
```

脚本会先验证两份固定镜像的 SHA256。若从 fastboot 开始，先临时启动已知 recovery 引导镜像，最多等待360秒；随后准备并读回 recovery BCB，再临时启动触控测试镜像，最多等待360秒自动回 recovery。两段等待上限分别计算，保持线缆连接和电脑唤醒。

仅使用 `fastboot boot`，不 flash/erase/set_active。为保证测试结束进入 recovery，脚本会备份 misc 首4KiB，只修改前864字节的 recovery BCB，保留其余字节并完整读回核对。触控镜像只写既有 userdata 4KiB 日志块；不改 OS/SystemOS，不重置已有 Data，不刷触控固件。

## 回传

结束后会显示：

```text
Return this log bundle: ...\logs\时间-bce3bdbe.zip
```

**把该 ZIP 回传即可，成功或失败都回传。** 内含运行身份、镜像校验、启动输出、启动前后日志块、解码文本及 BCB 前后像。不要只回传屏幕上的最后一个词。

`recovered` 只表示回到 recovery，`kernel_log_changed=true` 只表示日志更新；芯片是否成功识别需进一步分析 `TOUCHID`、返回码与 CRC，不能据此认定触摸已完成。

如果超时，不要反复启动。先回传已有 ZIP。确需手动复位时，回到 recovery 后可只读抓取现场：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\test-k80.ps1 -CollectOnly
```

此命令不会重启手机、不会修改 BCB，只从 recovery 读取固定日志块。它把结果标为 `collected_unbound`：不能证明日志属于哪轮或是否新生成；连同前一个测试 ZIP 一起回传，并说明手动重启情况。二进制通过 adb pull 保存，不使用 Windows PowerShell 的 `>` 重定向。

## 验证范围

测试镜像的构建检查、主机端触控协议测试与实际链接调用核对已通过，但本版镜像尚未在手机上运行。此 Windows 包尚未做真实 Windows USB 端到端测试；离线脚本检查结果另见随包 `validation.json`。手机目前不在开发电脑旁，不会宣称远程测试已成功。

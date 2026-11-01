# K80 独立 unixnu64 存储（2026-11-01）

机主完整线刷 Android 后，明确要求为 iOS 预留64GiB并保留 Android 系统；实际在线缩容成功，没有格式化 Android 数据。当前系统仍为 iPadOS17.7.11 / Darwin23。此页仅记录存储迁移。

## 当前布局

- 目标：92988a43 / zorn / slot A，OrangeFox R12.0。保持槽位A，不操作CC9 f85d4270。
- Android userdata：sda34，4096字节LBA3112704..47271679，168.453125GiB。原起点、类型和uniqueGUID保留。
- iOS unixnu：sda35，LBA47271680..64048895，64GiB；uniqueGUID b279731f-ccad-4ef5-a8b7-e7440cd08de3。
- OS/SystemOS：原SHNGROOT镜像9382658048字节，完整读回SHA fd43ee7035ce185ce4215ac93fdc006fd784a54b3b7442e21457c226cbe03093；运行时只读。
- Data：unixnu相对16GiB（4194304块），初始8GiB逻辑APFS/COW，2097217块窗口、65块头/bitmap。UUID C7D77FF3-6437-4C4A-8E05-E8E239AC1641。
- 日志：unixnu相对2291712的单4KiB块；misc recovery BCB仍仅变更前864字节，尾部保留、整页读回。

64GiB是专用分区大小，当前Data实际容量仍8GiB，其余空间保留。历史userdata相对192GiB/cookie2dde8229以及slotB的启动资格均已失效，不可拿旧镜像在此布局启动。默认42、桌面3a及历史manifest/归档不覆盖。

## 根目录源码与打包

`UniXNU-zorn/storage/unixnu64.json`与`uefi-zorn/payload/storage/unixnu64.json`保存相同分区描述。UFS构建必须同时显式选择：

```sh
UNIXNU_ZORN_STORAGE_PROFILE=unixnu64
UNIXNU_ZORN_DATA_PROFILE=8g
```

实际编译加入`ZORN_UNIXNU64=1`，严格选择唯一unixnu名称/实际typeGUID/uniqueGUID/边界，拒绝回退Android userdata。原传输锁、GPT CRC、Data/CDB边界和单日志块限制保持。

低层负载打包新增成对参数（仍需完整既有参数，不单独构成可启动命令）：

```sh
--storage-profile uefi-zorn/payload/storage/unixnu64.json
--storage-build-proof out/zorn/dual-system-reinstall-20261101/storage-kernel-proof.json
```

打包器核对描述、8GiB Data配置和实际kernel SHA，并生成`.storage.json`旁证；它不把旧内核改成新分区，也不授予启动/设备I/O权限。实际新内核e32880346be9156d0c35f2b1f49ca0bf831fa12e1d4e18d43b795e0df1896acb已完成独立start.s/最终存储调用及iOS17原始ABI核对。构建原始系统镜像时，格式2根board的容量已改为64GiB；固定历史compat/legacy/board.toml的SHA保持不动。

**上游`unixnu build userdata`仍会打印`fastboot flash userdata`。那只是旧命令模板，此布局禁止执行。原始iOS镜像的目标只可能是已核验的unixnu。** 当前已经安装完成，正常调试不需要重刷系统、重建GPT或重新初始化Data。

## 已完成的新设备验证

首次初始化和保留Data/原触控两轮均从Recovery起步、freshBCB整页读回、临时fastboot boot，使用原独立watchdog和600秒回收上限。第二轮396.65秒自动回OrangeFox，新日志89c60012…；DKEEP从state1转state2且cookie2d931234相同，Data错误0、原八核门槛通过、亮度读回64。触控2243读取/0坏帧、2242解码、235个HID报告/最后返回0，机主确认解锁和点按正常。边缘观察器未安装（install_error3），没有把它记成触控优化成功。

第一轮没有完整覆盖300秒GUI窗口；第二轮快照319420ms，仍不构成长时间稳定性、性能或系统多指验收。Android系统和槽位A保留，但本次未实际启动Android验收双向切换。当前手机已回OrangeFox。

`read-zorn-log.py --storage-profile unixnu64`只读新分区日志；固定runner的显式`--unixnu64-install-trial`只接受新存储准入文件，不能把已经consumed的两份ready再次启动。此次安装/保留结果见[完整证据](evidence/dual-system-reinstall-2026-11-01.json)。本机完整原始材料在`out/zorn/dual-system-reinstall-20261101/`。

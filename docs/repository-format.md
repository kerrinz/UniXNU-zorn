# 记录格式与发布范围

本次整理日期：2026-10-29。按机主确认，仅更新两个 README 和结构化移植记录，保留可用构建入口，不迁移驱动或构建布局。

## 与官方格式 2 的关系

官方的[格式 2 设备仓库](https://unixnu.com/zh/porting/device-repository)包括构建配置分层、组件选择、板级 DTS、补丁顺序及发布记录。[sheng 设备页](https://unixnu.com/zh/devices/sheng)由结构化移植记录生成，README 只承担设备概况、构建入口与文档导航。

本次采用这种说明与记录组织方式：

- README 只保留当前结论、目录、依赖与使用入口，历史调查保留在按日期命名的文档内。
- 根目录 `porting.toml` 按官方 13 个区域列出输入、配置、过程、经验、完成条件、范围、下一步和证据。
- 记录文件的 `schema_version = 1` 是官方移植记录格式版本，与构建配置的 `schema_version = 2` 是两个独立概念，不能机械地同时改成 2。
- `board.toml` 仍按格式 1 解析，仅增加与现有 IPSW 一致的 `board.os_profile` 身份元数据，供记录检查器核对；不启用 profile 合并，不改变输出路径。
- 不新增空 `package/`，不将 `patches/zorn` 改成会替换基础补丁模块的 `patches/xnu`，不移动现有树或编译输入。

**本次不是完整格式 2 构建迁移。** 不应因此声明 DTS、SoC 配置层、干净补丁重放或新输出布局已经通过。将来迁移时，需另行验证所有层、路径、补丁和归档规则。

## 记录的验证等级

已有设备结果来自尚未提交的工作树，使用 boot、kernel、日志和输入清单的 SHA256 绑定。当前不能为这些结果填写一个声称对应全部新代码的已发布 Git revision。

因此有实现的区域暂用官方支持的 `implemented`，附 `kind = "source"` 的源码或已归档结果摘要引用；尚未接入的区域用 `planned`。这不是否认已有真机结果：结果及局限仍在各区正文和证据 JSON 中明确记录。`source` 引用不冒充一次新的主机或设备测试。

待机主提交对应源码后，可将新一轮匹配该提交的主机、设备测试记为 `host` / `device` 证据，补充真实 revision 与实际命令，再按完成条件提高等级。不要用当前 HEAD 冒充未提交的触控或八核代码版本。

## 只维护两个设备仓库

- `UniXNU-zorn` 保存设备配置、SM8650 / K80 的本地代码、补丁、脚本与整机记录。
- `uefi-zorn` 保存固件板级包、BootShim、菜单和打包工具；链接到设备仓库的整机记录。
- UniXNU、Mu-Silicium 与公共依赖继续使用现有上游检出，不要求创建任何额外 GitHub 仓库，也未新增子模块。

两仓库的 `origin` 已分别为 `kerrinz/UniXNU-zorn` 和 `kerrinz/uefi-zorn`。本次没有执行 Git 提交、推送、远程修改或仓库创建。

## 本地检查与发布

从主 UniXNU 检出执行：

```sh
python3 scripts/porting-record.py check --device ../UniXNU-zorn
```

设备仓库新增 `.github/workflows/porting-record.yml`，调用官方移植记录检查工作流。本地检查通过只说明当前记录满足检查器要求，不代表 GitHub Actions 已运行，也不代表完整格式 2 构建或官网已收录。

机主审阅后只需提交并推送现有两个仓库；无需运行官网示例中的 `gh repo create`。如希望参与官方目录扫描，可在设备仓库添加 `unixnu` topic，并确认已发布提交的 `Porting record` 检查；完整格式 2 发布要求仍需在后续构建迁移完成时逐项复核。官网收录与网页生成不能仅凭本次本地文档检查保证。

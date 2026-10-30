# 已验收工作树的过渡源码快照

`qualified-42f3-source.json` 和同名 `.patch` 记录本机保留的成功工作树相对固定 Apple XNU 的实际变化，用于隔离回归，不代表全部当前上游补丁已在 K80 验收。

- 基础为 `unixnu.lock` 中的 XNU `d8b80295118ef25ac3a784134bcf95cd8e88109f`。
- 包含 97 个改变的文件（含三个新增文件），四个 SMP 输入规范化到八核转换前固定指纹；构建器再应用并审计八核转换。
- 快照替代整组 XNU / XnuPrelink 补丁，不再叠加基础或设备补丁。
- JSON 绑定补丁 SHA256 和每个结果文件 SHA256；重放或编译期间不匹配即停止。
- 旧归档只直接绑定四个 SMP 源码指纹，其余来源是保留工作树，不能证明旧对象全部由这些字节重新编译过。新对象和真机结果另行验收。

这是生成的诊断输入，不应手改合并补丁来绕过审计。细粒度设备补丁仍在 `patches/zorn`，待回归定位后整理；代码原有许可和归属不变。此目录不含 Apple 系统二进制、私钥或生成内核。

在共同父目录验证源码（新输出目录、不编译、不访问手机）：

```sh
python3 UniXNU-zorn/scripts/check-zorn-patch-series.py \
  --snapshot UniXNU-zorn/patches/compat/qualified-42f3-source.json \
  --workdir out/zorn/qualified-source-check-new
```

独立工作区和实际回归结果见 [构建记录](../../docs/progress-2026-10-29-repro-build.md)。快照不是桌面、触控或 CPU 稳定性证明。

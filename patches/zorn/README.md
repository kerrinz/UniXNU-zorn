# zorn 内核补丁

这些补丁跟在 UniXNU 的 `patches/xnu` 后面应用。它们让内核在屏幕上打印阶段词，并在没有 UFS 根卷时继续用恢复内存盘启动。

本目录不叫 `xnu`。设备仓库里的 `patches/xnu` 会整份替换基础仓库的补丁模块，内核就编不过去。用 `scripts/install-zorn-patches.sh` 把这里的文件复制到 UniXNU 检出的 `patches/xnu/`，再运行 `./unixnu build kernel`。

屏幕上的词按补丁里的顺序出现。2026-10-25 的真机停在 `PARSE`，也就是 `load_machfile` 里、调用 `parse_machfile` 之前。

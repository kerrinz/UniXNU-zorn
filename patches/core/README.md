# Local UniXNU CLI overlay

The tested zorn images also depend on changes in the main UniXNU checkout.
They are preserved here so committing only the two device/firmware repositories
does not silently lose this dependency.

`0001-zorn-cli.patch` is the existing local diff against UniXNU revision
`16e592abee8a550dec8154ed1f38b5ebc4f16213`. It contains:

- Android boot header v3/v4 validation from the earlier bring-up. The tested
  zorn images currently use the separate uefi-zorn packager.
- Reuse of a hash-pinned local decompressed kernelcache.
- The existing post-prelink AMFI null-field shim at `0xfffffff004abbe54`,
  targeting the zorn patch's exported `_zorn_amfi_deref` function. This
  changes one original AMFI instruction; the PMGR and Image4 integrations
  must not be described as an entirely unchanged security executable chain.

`0002-zorn-verified-storage.patch` adds the concrete zorn verified UFS
provider (OS mdev and genuine SystemOS IOKit storage) as an alternative to Virtio for the existing owner-root build
dependency. The original owner audit/probe requirements remain. Actual
acceptance is supplied by signed block policies and APFS-reported readonly
mount UUIDs in `native/ufs-read/ZornVerifiedRoot.cpp`; the build flag itself
does not authorize a device or return a security decision.

`0003-zorn-gui-ipc-build.patch` connects the file-specific IPC observer compile
flag and invalidates the incremental ipc_kmsg object when that mode changes.
The device builder independently audits the actual linked calls before allowing
a GUI diagnostic boot; a defined observer function alone is insufficient.

Use a UniXNU checkout dedicated to this experimental port:

```sh
../UniXNU-zorn/scripts/install-zorn-patches.sh . --core
```

The installer detects an already applied overlay, otherwise requires a clean
`git apply --check` before applying it. A conflict stops installation.
Without `--core`, it retains the earlier behavior of copying only XNU patches.

The original overlay retained the historical XNU context conflicts. Later source-replay fixes and remaining build limits are recorded below; schema-2 migration remains separate.

## Frozen component inputs

`0004-zorn-frozen-sources.patch` adds explicit `UNIXNU_SUBMODULE_PINS` verification. The device builder's `--source-pins` passes the selected JSON to the CLI, which checks the module set, actual commits and source hashes instead of updating submodules. The default upstream behavior is unchanged when no pins are selected. The device builder repeats verification before packaging and archives the selected record and checker. The 2026-10-29 record pins the actual qualified component versions, independently of the newer main repository's gitlinks.

The four stale XNU patch contexts have since been repaired: 157 patches replay cleanly twice, and an isolated object build/prelink and complete candidate archive pass. The new candidate's first hardware boot stopped at CPU1 preflight261. This does not resolve the historical ABI-candidate bootstrap dependency or migrate the board to schema2; see the device's reproduction progress record.

实际成功工作树的合并诊断快照独立位于 [`../compat`](../compat/README.md)，只用于显式选择的源码回归，不由 CLI overlay 自动叠加。构建器记录额外 `XNU_EXTRA_CFLAGS`，包括布局对照所用的编译路径映射；它不是 CPU 修复开关。

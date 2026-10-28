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

This overlay does not resolve the old XNU patch-order/context conflicts or
migrate this schema-1 board to the current schema-2 device format. The current
successful builds reuse the existing patched XNU tree and previous prelink
candidate. See the main README and the progress record for those limits.

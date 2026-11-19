# K80 iOS26 Turnip280

Apply the 24 official patches in `source-manifest.json` to exact Mesa85fda3b3,then this directory’s `series`. Install the actual ABI-v1 header and existing279 compile guard at the manifest paths; select `-Dtu-darwin-abi-dir=../../../k80-abi280` from `src/freedreno/vulkan`. The local full-source manifest and recipes bind all input bytes. Do not use the upstream v2 header.

The patch reuses the actual K80 service/registry transport,ABI-v1 Submit/SubmitBatch and WriteCombine policy. Optional unsupported priority/note requests return false;they send no selector17 priority request. Common upstream process-wide IOVA allocation,BO cache/retirement,early sparse-slot clearing and command-buffer-boundary submission cuts remain. Faults lose this device;the new v2 restart/replay guarantee is not assumed. Transient/GMEM changes are included as unqualified source behavior,not a measured performance result.

Run `scripts/check-ios26-turnip280.py --source <selected-tu_knl_darwin.cc> --abi-dir <selected-ABI-dir> --out <new-host-output>` from the device repository. It compiles actual selected functions with explicit IOKit/reap/allocation fixtures and ASan/UBSan;it executes no GPU shader or phone code. Complete cross build,root and boot receipts are in [280 evidence](../../../docs/evidence/k80-gpu-v280-upstream-stack-offline-2026-11-17.json).

The Mesa backend and this patch use MIT;upstream source notices remain. No disassembly,instruction rewriting,address symbolization or Apple shader binary analysis is used. No installation,boot or Git commit is implied.

`platform-series` targets the separate frozen278 platform source,not Mesa. It binds the exact280 root and record identities;the actual affected native objects were rebuilt. `scripts/check-ios26-root280.py` validates the exact delta plan and unchanged Recovery adapter over local I/O fixtures. The fixed installer now checks its existing host listener before consuming a claim. No root installation/admission or phone operation occurred.

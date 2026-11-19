# iOS26 upstream279 adapters

The common runtime and Metal frontend come from the exact updated upstream selected in the [source manifest](../../patches/gpu/ios26-upstream-runtime279/source-manifest.json).

`NativeMetalPages.rs` retains the existing bounded VM-object identity tracker. Only its test include was relocated. The tests query mappings owned by the host process;they never execute GPU work. `ZornAdrenoAbiV1Selection279.h` rejects accidental ABI-v2 input:method17 and flag2 have incompatible meanings. It is a compile gate,not a driver or a protocol translator.

The runtime patch selects the real Mach backend on iOS and binds it to the SDK's public LP64 `vm_read_overwrite` and `vm_region_64`. XNU's source connects those to the corresponding Mach routines. The actual bodies pass readable/read-only/inaccessible/unmapped host-memory tests and the iOS26 SDK scalar/prototype checks. No constant-success callback is introduced.

See the [279 handoff](../../docs/handoff-2026-11-17-k80-ios26-gpu-v279-upstream-runtime.md) for the build and hardware limits.

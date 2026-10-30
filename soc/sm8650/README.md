# K80 SM8650 resource slice

This tracked, in-tree SoC input is selected by `feeds.toml`. Its revision is the enclosing device commit; it is not a separate repository or a generic SM8650 driver. Addresses and affinities preserve `scripts/make-zorn-adt.py` and `native/smp/ZornSmpPolicy.h`. The GIC and legacy UFS class-matching node are exported to the shared ADT here. UFS register constants, PHY, clocks, DMA and write policy remain in the existing board driver and are not inferred from this DTS. No GPU resources are enabled.

Format2 resolution, DTS compilation and tree assembly are checked separately from the retained legacy debug build and its historical device runs. See `../../docs/repository-format.md` and `../../porting.toml`.

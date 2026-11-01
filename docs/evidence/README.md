# Evidence scope

New machine-readable summaries in this directory use valid JSON. `porting.toml` in the sibling device repository is the authoritative status record; the firmware repository mirrors summaries rather than publishing a duplicate whole-device record.

Historical source summaries may contain workspace-relative raw-artifact locators such as `out/zorn/...`. Those large local archives, proprietary inputs and staged implementation capsules are not bundled here. A local path is provenance context, not a public download or a reproducibility claim. Host/device verification levels require actual source revisions, commands and accessible matching records; publication does not assign the latest commit to an older run.

Existing raw records `data-retained-repeat-result.json` and `touch-cooperative-result.json` in the firmware repository contain text output despite their legacy suffix. They are preserved byte-for-byte at their historical paths. They must not be treated as strict JSON by new tooling.

See [publication review](../publication-review-2026-11-01.md) and the [official record guide](https://unixnu.com/zh/porting/records).

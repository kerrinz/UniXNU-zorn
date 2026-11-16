# iOS 26 source archive

Frozen K80 v244 workspace sources, preserved byte-for-byte from the tested local candidate. See [source-index.json](source-index.json) and [actual-inputs.json](actual-inputs.json) for hashes, original source locations and actual selected object inputs. Files from earlier frontend/Rust candidates remain archival; their presence does not select them. Upstream copyright and license notices are retained.

The three direct-runtime clock changes are also available as minimal patches under `../../patches/diagnostics/ios26-clock-lifetime244/`. Public XNU sources and board adapters are included; generated firmware headers, Apple/vendor binaries, platform seeds, images and device logs are excluded. Includes referring to the original local workspace remain provenance, not portable build recipes. This archive is not connected to the default iOS17 profile and does not establish a clean-checkout iOS26 release build.

GPU completion, CPU framebuffer copying and physical presentation have separate acceptance boundaries. The v244 Metal pixel test and two native closes returned successfully; full display, FT3683 gestures and stability remain pending. See [the current progress summary](../../docs/progress-2026-11-16-ios26.md).

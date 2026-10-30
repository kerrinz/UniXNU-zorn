# Non-GPU progress — 2026-10-30

This snapshot is synchronized between UniXNU-zorn and uefi-zorn. It excludes GPU development updates. `UniXNU-zorn/porting.toml` is the authoritative structured record; dated investigations and original manifests remain historical evidence. Autonomous work is paused at the owner's request.

## Desktop, input and storage

The owner confirmed desktop, swipe unlock and icon taps on the retained42f3 baseline. The path-normalized3a8ac966 image entered desktop twice; its second run recorded two separate sensor IDs for5188ms with normal release. This does not qualify system pinch/zoom, pixel calibration, complex gestures or input rate. [Desktop touch](evidence/touch-desktop-fast-qualified.json), [two-ID trace](evidence/qualified-source-repeat-two-contacts.json).

The qualified XNU RAM window is8GiB on a nominal12GiB SKU. Data is an existing8GiB UFS-backed APFS volume at userdata-relative192GiB with a2097217-block boundary, UUID C7D77FF3-6437-4C4A-8E05-E8E239AC1641 and cookie2dde8229. OS/SystemOS remain read-only; no Data reset/enlargement is permitted. DCS panel brightness64 has readback, not calibrated nits or percentage. [Retained Data](evidence/data8-retained-touch-result.json), [brightness](evidence/brightness-dim-result.json).

## CPU1 publication and layouts

Same full75b9ca39 kernel controls were0-fail,1-pass,0-fail,1-pass with distinct logs. Publication0 had late MRS TTBR1=0; publication1 had TTBR1 equal to CPU0 pre-start/final root and passed all8 cores/9 mapping rounds. The narrow operation cleans the cache line containing cpu_ttep for8bytes; it does not write the root/page tables. Original2s gates remain. Two layouts16KiB apart passed without extra early assembly probes; the old5b claim is withdrawn due to stale start.o. Early source-slot word4 is not a valid MMU-off loaded-value observation. [Controlled evidence](evidence/cpu1-root-publication-controlled-2026-10-30.json).

Normal GUI runs on e700 twice and936 once showed lock screens, with matching new logs. The a889900-second run passed CPU/Data/dim64 but stayed on the Apple logo; its failure is retained. Its code/data/address layout matched successful e700, with78 metadata bytes differing, which does not establish a cause. A later same-full-kernel900-second run passed lock-screen observation, so the longer budget alone is not a sufficient cause. [Two layouts](evidence/cpu1-root-publication-gui-2026-10-30.json), [retained failure](evidence/cpu1-root-publication-stability-2026-10-30.json), [long-budget success](evidence/gui-budget-same-kernel-2026-10-30.json).

## Latest completed observation

The single final c50ca7ea trial ran17:53:39–18:00:14 and automatically recovered in395s. Its120-second USB single frame showed lock screen4:02. Boot c50ca7ea115b4b7619193dcbf8125264829c8079ad3263bfe3d17c9bd6e0c389, full kernel5310b1dd32cb1b06b83a4e37281496dd25d22fc7d1cac0acbd7e4795e40efa86 and new raw-log SHA55e643ec9a9021b5dd20435e61f7e11c22a794ba7567a86f4cafc1645ece56be were bound to255 inputs and77 archive files at completion. All8 gates, original Data UUID/cookie, zero RAM/Data errors and dim64 passed. This was a passive lock-screen observation, not desktop/touch/continuous-window/long-term acceptance. [Final trial](evidence/cpu-active-trial-2026-10-30.json).

Both active-accounting epochs were available with error0/status0/maskff. Every core's USER and SYSTEM cumulative counts increased. Accepted/transfer/retired were8/8/8, reject0/status0; earlier6aea runs were9/9/9 and8/8/8. Serial cumulative accounting can lag and cross the first boundary; zero delta is not idle, equal counts are not per-request pairing, and independent timestamps are not consistent event pairs. No FPS, MHz, idle percentage or display-copy/wait cost was established. The historical Apple-logo failure was not reproduced or narrowed. The one planned diagnostic is consumed; no repeat is pending. [Display repeat](evidence/display-progress-repeat-2026-10-30.json), [60Hz contract](evidence/display-notification-contract-2026-10-30.json).

## Build and publication scope

Two controlled incremental rebuilds actually linked the same complete kernel bytes in one prepared workspace; this is not clean-bootstrap or cross-machine reproducibility. c50 had independent start/object/final-link/FAT audits. Old6aea and954 manifests remain unchanged and historical after intentional source changes; old input-match claims are not current promises. [Tool-date experiment](evidence/tool-date-reproducibility-2026-10-30.json), [linked candidate](evidence/cpu-active-linked-2026-10-30.json).

Root board metadata now uses format2, with record schema1. This documentation/configuration migration does not qualify a new image. The existing diagnostic entry selects the pinned compatibility board and retains all ready, storage, target-device and bounded-recovery checks. Only a matching published source commit and new corresponding results can justify raising official host/device completion levels; no Git commit or push was performed here.

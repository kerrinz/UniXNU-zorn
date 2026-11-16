# K80 iOS26 progress — 2026-11-16

Latest v247 device checkpoint: one protected run returned toTWRP in332.500seconds. The GPU-verified IOSurface was submitted through the original display queue:known frame499/SID35/access fence4,real acquire and copy counter497→498 were captured,and the fixed probe reached phase11/code0 with correct pixels and two native closes. The later camera frame shows a lockscreen,not the checker. Raw diagnostic loss36 keeps strict application incomplete;full GPU desktop,physical known-image presentation and FT3683 gestures remain pending. [Exact247 handoff](handoff-2026-11-16-k80-ios26-gpu-v247-known-present.md),[observed evidence](evidence/k80-gpu-v247-known-present-observed-2026-11-16.json). Earlier offline and244/246 paragraphs below retain their original scope.


v247 offline update: the exact GPU-verified IOSurface can now be submitted through the existing framebuffer queue using a gated board API with real frame/SID completion query,without treating SwapWait as completion. A new signed root candidate and its full kernel are built and locally replayed;they are not installed or hardware qualified. See the [247 handoff](handoff-2026-11-16-k80-ios26-gpu-v247-known-present.md). The v246 results below remain the latest device observation.


Latest local working-tree checkpoint: v246 connects exact IOSurface backing to retained VM mappings and completed writable namespace access. One protected trial returned toTWRP in332.535seconds;Metal pixels and two native closes passed,the camera showed the lockscreen,and39 schema2 frames were captured. The displayed SID's access fence stayed zero;GPU-produced display attribution remains unproven. Raw stderr loss36 still prevents the strict application verdict. No commit or push was made. See the [246 handoff](handoff-2026-11-16-k80-ios26-gpu-v246-surface-backing.md) and [exact observed inputs/result](evidence/k80-gpu-v246-surface-backing-observed-2026-11-16.json). The244 sections below remain historical evidence for the clock fix.


The v244 candidate fixes a reproduced diagnostic clock lifetime bug: DirectClient retained a stack clock/cookie in a global hook; later client cleanup could access it. DirectVM now supplies stateless XNU uptime and DirectSubmit calls it directly. Real fence deadlines,submission,releaseAll and failure retention remain unchanged. All three consumers were rebuilt together.

The exact kernel is `fac558258f3c8f0da78a88c5061dcc5ebdfab5c9644d9301659435bc74567af1`;boot image is `04af84279f32c798142d3f35cc24433c36a23caa2041fc08d909129b7973b05c`. Original ASan stack-use-after-return was reproduced;fixed source sections passed ASan/UBSan. Full link used1398 inputs,27 replacements and zero undefined symbols. Source/header and original-object byte proofs are retained in the evidence. These counts identify inputs;they are not completion criteria.

One protected real-device attempt on92988a43/zorn/slotA returned automatically toTWRP after331.983816seconds. CDC received39 valid frames/34867bytes. The Metal report reached phase11,flags1023,status4/code0,CRC718ed2ce and no bad pixel;both native sessions closed with return0. The strict application verdict remains incomplete because raw stderr diagnostic loss is36. A bound camera frame shows the iOS lockscreen. The seven defined storage protection samples and fullBCB/tail checks match;this is not a full Android userdata readback or Android boot qualification.

The actual framebuffer object was rebuilt byte-identically from its VFS-selected source and references the three Gen7 presentation hooks. It already uses a completion lease and surface acquisition before CPU copying. The lockscreen image alone does not correlate a particular GPU-produced surface,fence,copy and panel result. Complete GPU display presentation,FT3683 taps/swipes/releases/identity/edges and long-term stability remain unqualified. No new firmware build or root installation was performed for244. No disassembly or reverse engineering was used.

## Sources and evidence

- [Detailed244 handoff](handoff-2026-11-16-k80-ios26-gpu-v244-clock-fix.md)
- [Source and device-result evidence](evidence/k80-gpu-v244-clock-lifetime-2026-11-16.json)
- [Frozen source archive](../native/ios26/README.md)
- [Minimal clock patches](../patches/diagnostics/ios26-clock-lifetime244/source-manifest.json)
- [Authoritative porting record](../porting.toml)

Evidence summaries contain hashes and local archival paths. Local paths do not become downloadable logs when published,and this publication does not assign a new Git commit to historical tests. The record retains implemented/source classifications where an original matching published revision or public raw log is absent. Old iPadOS17,Data and successful baselines remain preserved.

## Build and repository scope

The official `scripts/package.sh` is copied byte-for-byte from UniXNU/templates/package.sh at core commit627c932a1573483dd44c29b48a113c3761dd8f55. Its source file SHA is f7b8e3ea043058b9c61d5b45c32b8e7669a85737c89d55d404957c3b43ec4aab. From the device directory,use `scripts/package.sh --os 17 --no-deps --check --out /path/to/new-output`. This validates configuration and patch planning without building or accessing a phone. The supported default configuration remains iPadOS17.7.11;the26 archive is not a generic release target. Complete clean-checkout native assembly and device execution through this entry are not qualified. Local IPSW,trust-cache,Mu firmware and device-specific seed inputs remain external.

See the [official building](https://unixnu.com/zh/building),[packaging](https://unixnu.com/zh/porting/packaging) and [record](https://unixnu.com/zh/porting/records) guides. `uefi-zorn` owns the firmware package and links this single device record rather than duplicating it. Synchronizing these repositories makes no new phone attempt.

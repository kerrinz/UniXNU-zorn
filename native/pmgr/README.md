# zorn PMGR service integration

This adapter addresses the observed iPadOS 17.7.11 panic
`AMFI: No PMGR?` at `ConfigurationSettings.cpp:235`. The original AMFI
looks up an `ApplePMGRNub`, reads its provider's AON value, ORs bit 2 and
writes it back. This is a service/ABI integration for that boundary.
CPU power, clocks, idle, sleep and secondary cores remain unimplemented.

`ZornPlatformPower.cpp` is adapted from the MIT-licensed
`UniXNU-sheng/package/ShengPlatformPower.cpp`, revision
`0e1f6e52638137db15905db8d775ad73757f39fa`. The builder is adapted from
the corresponding sheng recipe and UniXNU's `audit-amfi-pmgr-contract.py`.
The original provider size is `0x4b8a8`, the original nub size is `0x740`,
and the provider vtable has 340 entries. Slots 320/321 inherit the original
ApplePMGR AON methods; unsupported power slots panic with their slot number.
No Apple MMIO resources are supplied. The pinned original AppleT8011PMGR
uses the same constant `0xffffffff` read and immediate-return write at these
two slots.

`scripts/build-zorn-pmgr.py` compiles against the actual kernel's generated
headers and IOPlatformExpert compile record. Before binding private symbols,
it checks the original kernelcache hash, PMGR executable hash, AMFI executable
hash and relevant instructions/imports. AMFI's hash is checked after undoing
only this port's existing, verified null-field BL shim in a temporary copy;
the script does not alter the candidate or original executable. It validates
the compiled subclass's full vtable and writes `build/zorn-pmgr/build-report.json`.
The recipe currently requires a previous candidate and the existing incremental
build tree; clean checkout reproduction is still pending for this port.

Initialization runs immediately after the zorn UFS probe in `bsd_init`, so
the persistent log and independent recovery watchdog cover adapter failures.
Late metaclass registration uses `preModLoad/postModLoad`; the ordinary static
initializer is removed from `__mod_init_func`, with its instructions checked
unchanged. No `CONFIG_XNU_SHENG_PMGR` hook is enabled on zorn.

Boot arguments:

- `zorn_pmgr=1`: create genuine original nub/provider objects, validate the
  provider binding and original method results, then release them. Success:
  `PMS00000004 PME00000000 PMRFFFFFFFF PMOK1`.
- `zorn_pmgr=2`: perform the same checks, attach/start/publish both services,
  verify actual service lookup and retain them. Success:
  `PMS00000005 PME00000000 PMRFFFFFFFF PMOK2`.
- `zorn_pmgr=3`: exercise the unsupported power-operation refusal. This is a
  deliberate panic control, not used for normal startup.
- Missing argument: adapter stays disabled.

Combine with `zorn_wdt=1 zorn_log_only=1 zorn_checkpoint_early=1`.
Use `zorn_checkpoint=PMOK1` or `PMOK2` for a bounded lifecycle/publication
trial. The host runner returns through recovery and stores the raw 4 KiB log.

Baseline device evidence is in the workspace artifact directory
`out/zorn/debug/20261026-232309-bbae32ea/`: seven EL0 SVC entries followed by
the missing-PMGR panic. The lifecycle trial passed on serial `92988a43`:
`out/zorn/debug/20261026-234239-c6788b61/` records
`PMS00000004 PME00000000 PMRFFFFFFFF PMOK1 WSTOP RSET TC00000003 HIT00000001 BCBK`
and automatic return to recovery. Image SHA256:
`c6788b61e72c99f984ba6c4da23374b49916bdef71cbd78466f9a9deb1136a3b`.
Publication also passed on the same device:
`out/zorn/debug/20261026-234426-10a4e895/` records
`PMATT PMPUB PMMATCH PMS00000005 PME00000000 PMRFFFFFFFF PMOK2`,
followed by checkpoint reset and automatic recovery. Image SHA256:
`10a4e8953fc036ecab85c8d19fe5fe2713caf4845f1d982f848b376fc34ceab3`.
These two trials use the identical kernel SHA256
`222011f493dfafbe346e742dbc8c21b283924dd9b1adc820220d817a692d9505`;
only the menu argument changes. AMFI consumption remains to be verified
by allowing user execution beyond the previous missing-service panic.

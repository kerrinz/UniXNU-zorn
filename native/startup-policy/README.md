# zorn temporary startup service policy

`--data-permissions` additionally restores numeric uid/gid/mode on 232 existing
paths of the volatile RAM Data copy before launchd. `DataPermissions.h` and
`data-permissions.json` record the readonly original template and the selected
desktop seed. The preparer checks the fixed seed hash; the kernel refuses
symlinks, unexpected types and paths on another device before calling real
fchown/fchmod and fstat readback. It creates no files and changes no contents.
Run 50081fc9 verified all 232 rows and Data root 0:0 on the K80; LaunchServices
still waited afterward, so this corrects metadata without proving a GUI fix.
The current v13 GUI footer retains its stage, errno, counts and root identity
in the same authorized 4 KiB diagnostic block.

Derived from UniXNU-sheng 0e1f6e52638137db15905db8d775ad73757f39fa,
`package/BootWatchdogPolicy.c`. See origin.json and the retained upstream
SPDX notice; UPSTREAM-LICENSE is the unchanged repository license.

The official guide documents `sheng-disable-jobs`:
https://unixnu.com/zh/guide/skip-setup

`build-zorn-debug.py --minimal-services` selects the qualified RAM Data GUI
profile and disables these launchd labels for that boot:

- com.apple.identityservicesd
- com.apple.locationd
- com.apple.CommCenter
- com.apple.bluetoothd
- com.apple.watchdogd (no matching userland watchdog backend on this port)

CoreLocation and other original framework files remain in the readonly OS.
SpringBoard, backboardd, render services and iconservices remain enabled.
The independent kernel Gunyah watchdog and recovery BCB remain active.
No Setup completion, activation, user account or key record is created.

Adding `--lite-services` selects the unchanged upstream `sheng-lite` job list
instead of the four explicit radio/location labels, plus watchdogd. The current
list has 22 labels; the host proof reconstructs and parses the expected
1083-byte plist and checks that critical UI jobs remain enabled. The b1137cba
hardware run recorded status 0, uid/gid 0, mode 0644 and 1083 bytes after full
readback. This proves the file operation; it does not inspect launchd's internal
disabled-job map or establish that this preset fixes system startup.

`--disable-jobs=<label>[,<label>...]` passes the existing upstream additional
override to the same temporary policy. It requires `--minimal-services`, uses
at most 32 labels and 199 ASCII label characters, and is recorded as `+custom` alongside the
exact combined job list. With `--lite-services`, the 22 upstream labels remain
unchanged and the requested labels are appended. This option alone does not
establish that launchd applied an override or that a service caused a wait.
An unbooted diagnostic candidate adds only `com.apple.liveactivitiesd`: the
9ead2e85 original user stack and exact selector show SpringBoard synchronously
reading `activitiesExceedingReducedPushBudget` through ActivityKit. This is a
bring-up isolation hypothesis, not a qualified fix; original service code and
OS plists remain intact.

The kernel hook runs after the writable Data mount and before original
launchd. The board guard requires the actual RAM Data probe stage 7, success,
no persistence backend and an armed diagnostic/recovery watchdog. The
policy writes only /private/var/db/com.apple.xpc.launchd/disabled.plist and
its disabled.migrated marker on volatile RAM Data. Symlinks are refused;
the normal syscalls set uid/gid 0 and mode 0644, fsync, stat and reopen/read
back every policy byte before continuing. Failures stop startup with their
real error. No OS/SystemOS image or new UFS region is written.

ZORNLOG8 preserves the status, file uid/gid/mode/size independently of the
text ring, in the same existing 4 KiB log block. Its footer version is 7,
2472 bytes at offset 1624; 134 text slots remain. Historical formats still
decode. Host ABI, negative configuration/old-kernel controls and metadata
roundtrip passed; hardware outcomes are recorded in docs/progress-2026-10-27-gui.md.

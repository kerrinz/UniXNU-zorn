# zorn UFS transport and unattended diagnostics

Current GUI profile (2026-10-28): `ZORNLOGB`, footer v14 (optional kernel
stack profile v15), 92 text slots,
2976-byte footer at offset 1120. The complete record remains one 4096-byte
block at the existing log LBA. Earlier formats below describe their historical
wire layouts; the reader retains them, including v11/v12/v13.

The footer retains bounded process registers, real user frame reads and errors,
display counters, temporary startup policy and numeric RAM Data permissions.
V14 adds the actual Data filesystem errno, supported attributes, block size,
total/available blocks and APFS UUID. A guarded readonly vnode lookup and
vfs_getattr run in the scheduled observer; no filesystem attributes or contents
are changed. Successful block I/O alone does not establish free APFS space.
Run 38dd08b2 recorded all four attributes, the expected Data UUID and
318418944 bytes available after 60 samples; Data capacity was not exhausted.

`--gui-kernel-stacks` adds an optional marked kernel stack record. It requires
an explicitly selected watcher/watchdog and refuses multiple initialized CPUs.
For a referenced blocked thread without a continuation, its retained wired
stack is read with ml_nofault_copy, within its actual allocation and at most
16 frames, while CPU0 preemption is briefly disabled. A continuation is already
present in the thread register record, so that case retains the original user
frame walk instead; runnable targets also use the original user sampler.
Terminating targets and actual kernel read failures retain an explicit error.
Recording occurs after preemption is restored; the target is never suspended.
The reader separates kernel/user sources and stale samples. Twenty controls
execute the actual helper with host stubs, including the separately gated
runnable-context option described below. Run 2c784bad recorded real
continuations, but did not enter the physical nofault stack-copy branch; that
branch remains unqualified on hardware. The mixed profile recovered in
9ead2e85 and later trials; those records used the continuation/user fallback.
`--gui-runnable-kernel-stacks` separately enables reads of a referenced,
non-current TH_RUN target on the sole initialized CPU. It requires the normal
kernel/user stack watchdog profile and defaults off. Preemption is disabled
only around bounded nofault reads; terminating/current targets and SMP are
refused, and continuations still select user frames. Original context-switch
code and target state are unchanged. Run 6f9950ba exposed a TH_RUN SpringBoard
with no display clients, but used the old user fallback. The new physical
runnable-stack read remains unqualified until a matching recovered trial.

`--gui-launchservices` selects lsd for the control-process stack and, from v13,
for its IPC and IOKit query slots. Without that option the control is launchd.
Old v11/v12 IPC and query slots continue to decode as launchd. The observer
never consumes an IOKit iterator or changes a message or original return value.

`--gui-hold-seconds` explicitly permits 30..1800 seconds. The observer samples
every 15 seconds through a 900-second profile and every 30 seconds for a longer
profile, at most 60 times. The 30-second profile also makes one initial bounded
pet before its first sleep. It pets the independent
watchdog only before the absolute logging-epoch deadline; a stalled observer
or an expired deadline cannot extend the hold indefinitely. The host recovery
timeout includes firmware and recovery boot time. Multiple 900-second trials
have recovered, including complete 60-sample runs. In 9ead2e85, SpringBoard
reached an ActivityKit synchronous request and lsd queried UserManagement;
the camera still showed the Apple logo. Earlier runs sometimes remained in
LaunchServices. The 1800-second fe55ffa5 trial recovered automatically with a
changed log, tick 60 / stage 12 at 1830267 ms and a persisted GUIEND marker.
SpringBoard still awaited the LaunchServices seeding group through a
ControlCenterServices query; Data retained 342114304 available bytes. The
camera showed the Apple logo at 21 minutes. The later camera frame was taken
after recovery and shows TWRP, not iPadOS. A longer window does not itself
establish completion of initialization.
Run dd3ef48e recovered with a changed log after its 1800-second window; its
last record was tick 59 / stage 10 at 1800081 ms. The selected lsd ordinal 2
waited in restoreInactiveInstalls on the database seeding group. The selected
backboardd ordinal 4 had a QuartzCore IOMFBServer thread_body / CFRunLoop user
stack. This does not establish a completed compositor or desktop: the camera
still showed the Apple logo, with six accepted/transferred frames. RAM Data
had 341368832 bytes available and no recorded I/O errors. The exact 163-tag
lookup ran in this trial, without establishing a controlled speedup.

Compact tracing retains the first LC/LD/LV/LW path lookup marker for each
suffix 0..9. An explicitly selected recovery checkpoint bypasses this filter.
LOGIO in the bounded text ring reports actual write attempts, successful writes,
suppressed repeats and the phase-2 subset. These counters do not establish a
filesystem error or attribute all suppression to the latest filter change.
After its final stage update, the observer attempts a bounded commit to the
same log block, at most three writes and two 10 ms scheduled waits, without
extending the watchdog hold. Run fe55ffa5 recorded stage 12 and GUIEND on
hardware. The later dd3ef48e log ended at tick 59 / stage 10 around the absolute
deadline and had no GUIEND; this is not evidence that its final commit ran.

`check-zorn-final-snapshot.py` executes the actual final-flush source helper
under ten disabled, busy, failing and successful host controls. Its report is
included in future GUI build archives. It checks the fixed buffer, write/wait
bounds and absence of a watchdog pet; it does not establish hardware success.
Run 5f3bedbf and later trials emitted `UFSIO` in the existing text ring: real
OS/SystemOS 4 KiB read attempts, transport failures and elapsed call time,
plus elapsed diagnostic write time. Timing starts only with GUI observation.
Read time includes the host mutex and preemption; write time may overlap it,
so these are not pure hardware latency or additive wall-time percentages.
Transport failures are distinct from authentication failures and RAM Data
errors. Readonly transfers, authentication and original results are unchanged.

This is the zorn adaptation of the local houji UFS transport. It uses the
pineapple UFS host at `0x01d84000` and the UFS SMMU stream `0x60`.
Both OS and SystemOS transfer callbacks reject writes. The command policy permits one
4096-byte FUA WRITE(10) only to the armed diagnostic log LBA, plus the
GPT-selected misc BCB page while the recovery writer is explicitly armed.

The log is inside userdata, 4 MiB after the 9382658048-byte SHNGROOT image:
partition-relative block `2291712` with 4096-byte blocks. The current
`ZORNLOG2` header is an 8-byte magic, little-endian 32-bit count, and a
little-endian 32-bit next-write index. It has 340 slots of 12 bytes, each
preserving up to 11 characters plus NUL. Once full, the next-write index also
identifies the oldest slot. Appending changes one slot rather than shifting
the entire buffer. The disk write remains a single 4096-byte FUA command.

The host reader also supports the old `ZORNLOG1` format (510 slots of 8 bytes,
7 printable characters). Old long addresses were truncated. V1 archived
logs and V2 partial/full/wrapped boundaries have been checked locally.

The panic hook stores its complete address tag, then `PANICBEGIN`, chunks
of a formatted reason (at most 255 characters), and `PANICEND`. Nonprintable
characters are normalized to spaces. The reason is assembled in RAM and
committed in one block write. The host reader reconstructs it as `panic: ...`.

`TIMxxxxxxxx` is the monotonic time in milliseconds since logging was armed,
encoded in hexadecimal. User SVC entries/returns, selected thread-creation
stages and AMFI worker/service lookups include this timestamp. `TCRxxxxxxxx`
is a native caller's low 32 address bits. Copy observations are limited to the
thread executing the observed Mach allocation's user-parameter copy;
they record its address, validation, access-enable, copy and abort boundaries.
Fault records include low PC, full fault address, ESR and recovery availability.
They preserve the original validation, PAN, copy and fault-handler semantics.
No logging calls are placed between `user_access_enable` and
`user_access_disable`; that window contains only the original byte copy.

The first 512 non-write EL0 SVC entries/returns are observed. A separate bounded
observer snapshots up to 4096 write SVC buffers, at most 256 bytes each,
using normal `copyin` before recording `UFD/USRBEGIN/USREND/UCON`. After the first 512 writes, at least 90% of a captured buffer must be printable
ASCII or whitespace; binary traffic is skipped. The observed libignition
output uses fd 3, so filtering only stdout/stderr loses it.
The original syscall arguments and results are preserved. Sysctl observations
record at most 12 MIB integers and the new-value length; dispatch observations
include the resolved kernel name, handler address and before/after MAC/handler
boundaries. These do not change policy or handler return values.

Original Image4 observations are collected in 64 fixed BSS records even before
UFS is ready, then flushed to the same log block. They record start boundaries,
service matching and actual wait/return calls, worker boundaries, and mutex-gate
try-close/wait/open calls. `I4EARLY/I4EVENT`, `I4K/I4P/I4H/I4L` and optional
`I4NBEGIN/I4NEND` describe the event, low caller PC, full value and name. At the
first ignition try-close, the early history is replayed once because ordinary
SVC tracing may already have wrapped the disk ring. The host reader decodes
these records. The observed indefinite wait for `IOAESAccelerator` on zorn was
resolved by selecting upstream SoftwareAES; original Image4 instructions and
gate semantics remain intact.

## SystemOS verified UFS and IOKit

OS contains an inner 512-byte-sector GPT; its APFS container starts at sector
34 (1024 bytes past a physical 4 KiB boundary). SystemOS is a raw APFS container
at SHNGROOT offset 6079643648, with 806400 blocks. It is not parsed as another
GPT disk. Both readonly devices share the transport lock and bounce buffer.
On 2026-10-27, SystemOS's real first block matched its pinned SHA256, the
callback rejected a write and an out-of-bounds read, and `md1` registration
reached the deliberate `SYSOK` checkpoint on the K80.

With `CONFIG_XNU_ZORN_VERIFIED_ROOT`, the new candidate opens the independent
owner-signed OS/SystemOS block policies using upstream VerifiedRoot/XNU crypto.
Every completed physical 4 KiB snapshot is verified before copying bytes out;
the OS's final 1536-byte policy tail is handled at its exact length. A failed
block poisons that policy and prevents later authorization. Policies/public
anchor live in the readonly kernel DATA_CONST segment. The owner-query adapter
uses the actual mdev device, readonly APFS mount and `VFSATTR_f_uuid`; it does
not manufacture IOMedia UUID properties. Unknown devices, mismatched UUIDs,
multiple mount matches and poisoned transports are refused.

The owner-signature opens and verified reads passed on hardware. A raw md1
user mount first failed with fsindex -1; a slice alias selected the real volume
but original APFS then rejected its absent IOKit node. Those diagnostic alias
and early-devfs patches are not part of the normal provider path.

ZornUfsBlock.cpp now provides a genuine readonly IOBlockStorageDevice backed
by zorn_systemos_transfer. Original IOStorageFamily/APFS publish IOMedia, UUID,
and BSD nodes; the port never sets these identity properties. UUID matching
requires a unique media object with this exact provider in its ancestry and
real BSD major/minor/name. Post-mount owner authorization independently checks
the actual dev_t, APFS UUID, readonly state and verified transport health.

build-zorn-storage.py uses the pinned public IOStorageFamily e45fbe30 source
for an annotation-only object. It checks 190 slots, 23 overrides, original base
lifecycle and private imports before and after prelink, with runtime parent
size guards (0x90/0x88). The reference object is never linked. The original
storage executable hash remains 852b7846a9039c58fde08478416080af38ffcd5b47c08c889b28497f5f5b4061.

Hardware run 20261027-094852-4997cc98 mounted /dev/disk1s1 with the expected
SystemOS UUID and reached ZCS6/ZCE0/ZCA1/OWNOK. It intentionally recovered at
that successful owner checkpoint. The later bounded progress run 20261027-100050-478cdb22 reached original
launchd's main loop and reported ptpd[48] spawned and rapportd[56] running.
That proves useful shared-cache/userland execution, not every cache page or
every daemon's function. Writable Data, XNU display and the desktop are not ready.
The current menu uses NOHIT natural runs.

The first rootless candidate retained a RAMDisk ADT placeholder and was
incompatible with DarwinBoot; the packager now removes only zero-valued
RAMDisk/PackedRAMDisk placeholders when omitting the file.

The optional early UEFI watchdog uses the same Gunyah ABI before kernel entry.
Its host path snapshots misc, replaces only the already-authorized 864-byte
BCB prefix, writes one 4 KiB page and requires exact read-back before boot.
This host writer passed both stubbed boundary/refusal tests and physical exact
readback on the K80. The UEFI stop-CPU test returned to recovery without changing
the kernel log; later mode-1 boots record WON at kernel takeover. Bootreason
is empty, so the precise reset source and timeout remain independently unproven.

ZP0..4 and ZT0..4 are buffered vnode lookup errno/type results for /dev, the
selected device, /private, /private/preboot and /private/var; ZDV is its dev_t.
APC/APBEGIN/APEND retain the last eight original printf messages during the
SystemOS mount. Capture only uses fixed BSS; persistent I/O waits for mount()
to return. These observations preserve all original return and policy values.

## Checkpoints

`zorn_checkpoint=NAME` selects a stage. The default is `IRET`. Normally the
reset is armed only after `parse_machfile` returns (`PDON`).
`zorn_checkpoint_early=1` arms it as soon as UFS logging is ready, for earlier
stages such as `CSMAD`. `zorn_checkpoint_skip=N` skips the first N matching
armed stages, recovering on match N+1. HIT records the number matched.

On a selected checkpoint, the logger persists the stage, writes the recovery
BCB, reads the page back, and invokes PSCI SYSTEM_RESET. Only the first 864
BCB bytes are replaced; the rest of the 4096-byte misc page is preserved.
The recovery command has no wipe argument. A reached checkpoint is an
intentional stop, not evidence that the kernel naturally stalled there.

`zorn_log_only=1` makes `zorn_say` call the persistent logger directly once
logging is armed. It skips framebuffer writes, cache maintenance, and the
display helper's DAIF manipulation. Before UFS is ready, early screen output
still operates. Later screen text can therefore be stale.

## Independent watchdog

The running K80 recovery device tree reports
`/hypervisor/qcom,gh-watchdog/compatible = qcom,gh-watchdog`.
The ABI is documented by the local factory kernel driver
`zorn-kernel/drivers/virt/gunyah/gh_virt_wdt.c`:

- `0x86000005`: control, 2 disables and 3 enables.
- `0x86000006`: status; return x0 must be zero, x1 bit 0 is enabled.
- `0x86000007`: pet/reset counter.
- `0x86000008`: set bark and bite, x1/x2 are 16-bit milliseconds.

`ZornWatchdog.h` implements these calls without physical watchdog MMIO.
Every failure records a status and uses the ordinary recovery reset path.
The recovery BCB is written and verified before enabling the watchdog.

- `zorn_wdt=0` or absent: no watchdog change.
- `zorn_wdt=1`: bark 45000 ms, bite 55000 ms. This is a fixed capture budget
  from UFS log readiness, not an inactivity timer. It is not petted by stages.
- `zorn_wdt=2`: bark 5000 ms, bite 7000 ms; record `WTEST`, mask interrupts,
  and deliberately stay in WFE. This mode is only for validating independent
  recovery, and does not attempt userspace startup.

Mode 2 was verified on 2026-10-26 with boot image SHA-256
`b96e8c48ba47b4f87f3e04f3238a2aea037d6f4feaae38506417f44ba12d39ae`.
The saved tail was `WARM WTEST`, with no `RSET` checkpoint path, and recovery
ADB reappeared. This verifies reset with the CPU stopped; it does not measure
the actual reset latency against the configured bite interval.

A normal checkpoint disables an armed watchdog before its PSCI reset.
`scripts/run-zorn-debug.py` automates one host round and leaves the phone in
recovery with raw log, decoded tail, image hash and boot output saved under
`out/zorn/debug/`. All targeted commands use serial `92988a43`; the runner
requires `product:zorn` and slot `b` before `fastboot boot`.


## Userspace evidence

`INITOK` is emitted only after `load_init_program` returns successfully.
The optional bounded SVC observer runs in `handle_svc`, which is called only
for a valid 64-bit EL0 SVC exception. It records the user PC as UHI/ULO and
the SVC number, followed by USVC. For the first 32 SVC entries it also records
returned x0 and CPSR when the handler returns, followed by URET. An SVC entry
proves EL0 instructions ran; an entry alone does not prove that syscall
completed or that launchd reached its main loop.

On 2026-10-26 image `3093f7b6…` reached user PC 0x0000000100bc2fb4 and SVC
0x4a, which this XNU's syscalls.master maps to mprotect. Both unchanged trust
modules were accepted (TC00000003). The current target is URET, to observe
that call completing before allowing longer userspace execution.


`zorn_trace_compact=1` omits the already-verified VM entry/lock/caller-address
trace words, retaining user SVC records, signing stages, and panic text. A
stage selected as the recovery target is never omitted. This reduces UFS
traffic and keeps the bounded ring useful after EL0 starts; use compact=0
when investigating those low-level VM paths again.

The first mprotect was observed returning x0=0, CPSR=0, followed by URET
and normal recovery, with image `067299cf…`. This is proof the first
user-initiated syscall handler returned successfully, not proof of a GUI.

In compact mode, repetitive successful MAC/vnode-read stages retain their first
occurrence, and bare eight-digit addresses retain only the first eight.
Tagged faults, results and the selected checkpoint are preserved. Disable
`zorn_trace_compact` for the full historical stage stream.

For large native-4K code-signature cache preparation, HFBEGIN/HFEND identify the
actual vnode basename, HG/HL record bytes fully checked against original signed
16K blocks and the code limit, and HRE records the original result. CSMAD is
a successful MAC return, not a wait inside MAC. With explicit
`zorn_hash_budget=120`, only successful authenticated chunks may pet at intervals
of at least 10 seconds, and never beyond 120 seconds since log startup. A stall
still triggers the existing 55-second hardware bite. Default host recovery wait
is 300 seconds including recovery boot; no parameter retains fixed-budget behavior.

Compact mode also retains the first successful namei/signature stages, skips
successful copy-scope steps while retaining aborts, and bounds ordinary thread
traces to 24 stages (256 in full mode). Selected checkpoints remain visible.

## Volatile Data and service observations

The independent upstream RamBlock component can carry a 512 MiB logical APFS
Data seed. The build checks its packed/logical hashes and links expected
UUID/size/hash constants. The XNU Data hook verifies actual mount identity and
uses normal VFS operations for a synchronized file write, reopen/readback,
comparison, unlink and ENOENT check. `DPT=7 / DPE=0 / DWR=1 / DER=0` passed on
serial 92988a43. These writes are RAM-only. ZornVolatileData.c explicitly
refuses the optional persistent store API; it performs no UFS Data writes.

With zorn_service_trace=1, printable write observations retain service-running
notices and selected compositor notices, reduce repeated persona warnings,
and keep errors. This diagnostic mode removes the old 4096-write observation
cutoff; the 4 KiB ring and independent watchdog are still bounded. The optional
exec observer records BEGIN and ACTIVATE_RETURN with PID, errno and copied
path. A zero activation return proves executable image activation, not full
service health or EL0 main execution. Arguments and results stay unchanged.

`zorn_ufs_log_ready` gates the board display probe until the transport, logger
and recovery watchdog initialization sequence has completed. The board call
is immediately after its PMGR hook, following bsd_autoconf.

## Bounded GUI observer

`--gui-watch` with display mode 3 adds `zorn_gui_watch=1`. The native XNU
observer selects launchd, SpringBoard and backboardd every 15 seconds, at most
12 times. It records registers for at most four user threads.
Registers are collected under the task lock; the current observer reads no
user VM or user stack. Samples may race running user code
and explicitly report truncation. Four original GUI process exit statuses
and reason namespace/code values are retained for later diagnostic snapshots.

The observer changes no syscall, authentication or exit decisions. It does
not pet the watchdog. Successful exec progress retains its existing separate
180-second budget. Hardware sampling and automatic log recovery are qualified by the later
rounds recorded in docs/progress-2026-10-27-gui.md.

WRGO is painted immediately before arming the UFS log. In log-only mode it
remains on screen even after the kernel advances; use the current round's
persistent log to establish the last executed state.

## Fixed GUI snapshots and bounded startup window

Earlier fixed GUI watchers use ZORNLOG3: the same 4096-byte authorized log
block, with a 16-byte header and 180 text slots of 12 bytes. The fixed snapshot
at offset 2176 survives text-ring wrap. Snapshot version 1 occupies 1344 bytes;
version 2 occupies 1920 bytes and adds four bounded exit details (saved
PC/LR/FAR/ESR/CPSR, shared-cache slide, executable header, fixup count, and up
to 91 bytes copied from a validated kernel reason buffer). The reader accepts
old ZORNLOG1/2 and both snapshot versions. C/C++ layout assertions and decoder
boundary checks cover this ABI. No extra log block or partition is written.

The latest observer samples registers only; it performs no user VM/frame reads.
The osfmk helper owns task-private access; BSD retains original exit decisions.
Normal --gui-watch never pets the watchdog. An explicit --gui-hold-seconds
30..180 is a separate startup observation mode requiring the watcher and
early watchdog mode 1. Its scheduled thread may pet only before the absolute
deadline; the existing exec/hash budgets also expire. It is not exec progress
evidence. This mode remains bounded if userland waits or the observer stalls.

Hardware dae66d26 reached an owner-confirmed Apple logo: 4 original display
client opens, 6 accepted surfaces and 5 transfer callbacks, with the last
transfer returning success for 18432000 bytes. SpringBoard also exited
repeatedly; a stable system UI is not yet qualified. Native readonly union
root trials remain separate from that known Apple-logo image.


The latest explicit GUI watcher uses ZORNLOG4 with 172 text slots and a
2016-byte version-3 footer at offset 2080, still exactly 4096 bytes total.
It retains the previous register/exit records and adds eight actual kernel
configuration values plus errno/vnode type results for four fixed library
and cache paths. The paths are queried once by the scheduled observer;
no lookup, signature or syscall result is changed. Old formats remain readable.
An identical repeat of the Apple-logo image also failed to produce frames;
CPU scanout is proven once, while repeatable GUI startup remains unresolved.


The next GUI observer also retains two scalar outgoing IPC attempts for each
of launchd, SpringBoard and backboardd. It uses only the copied-in kernel
message header and the original locked receiver-PID accessor. The IPC hook
changes no return value and never writes UFS; scheduled runtime snapshots
print its bounded RAM cache. A send attempt is not proof of delivery or reply.
The same observer prints a bounded process inventory; truncation is possible.


ZORNLOG5 keeps the same authorized block but uses 162 text slots and a
2136-byte version-4 footer at offset 1960. Six 20-byte IPC attempt records
(two for each selected process) survive text wrap. It preserves every prior
footer field; the reader supports all previous formats. The temporary IPC
text-only round was insufficient because service output overwrote it.


ZORNLOG6 uses 140 text slots and a 2400-byte version-5 footer at offset1696.
It adds bounded receiver process names and the last original IOKit matching
query for each selected process. The observer reads IOProviderClass and the
original result/iterator-presence only; it never consumes that iterator.
An iterator being present is not proof that it contains a matching service.
All previous log formats remain readable.

2026-10-28: ZORNLOG9 adds a version-8, 2904-byte footer at offset 1192,
with 98 text slots. The same authorized 4096-byte block is used. It retains
the v6 KeyStore and v7 temporary launch policy fields and adds three bounded
user-stack records (pid, sample tick, count, real VM-read error, 16 return PCs).
`--gui-user-stacks` is explicit and requires GUI watch plus early watchdog.
The scheduled observer releases task locks, references the target map, uses
original vm_map_read_user, and releases the map. Each process samples only
its first eligible thread, at most 16 aligned frame pairs within 1 MiB of SP.
These are best-effort samples of a running task, not atomic stackshots. Reads
may fault; an observer stall remains subject to independent timeout recovery.
The decoder keeps old samples separate and never attaches a stale stack to a
newer register snapshot. Layout/boundary controls and 95 historical log decodes
passed; real hardware stack-read results are recorded in the progress document.


The explicit `--gui-launchservices` profile uses ZORNLOG9/footer v9 with the
same layout and write address. Only the process/stack slot 0 changes from
launchd to lsd; launchd IPC records retain their original meaning. The reader
validates the selected process name. On 0959f393 the owner saw an Apple logo;
lsd's first thread was waiting in LSInstallProgressService journal recovery,
while SpringBoard still waited in LSCopyServerStore. Other lsd worker stacks
have not yet been captured.


75z is a narrowly scoped VM-map initialization experiment based on the matched
2ddf7cb4 retained kernel stack. It restores pinned XNU vm_map_lock_init rather
than clearing CAN_SLEEP after every map initialization. Other experimental
rwlock/pmap changes remain; no runtime success is implied by source equality.
The builder archives the original-macro/linked-call audit and header hash.

The first 75z trial f8533418 reached a camera-visible system lock screen and
recovered with a matched fresh log. This is one-run UI evidence, not proof of
all synchronization semantics; unlock, desktop and touch await owner checks.

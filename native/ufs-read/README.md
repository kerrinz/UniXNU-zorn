# zorn UFS transport and unattended diagnostics

This is the zorn adaptation of the local houji UFS transport. It uses the
pineapple UFS host at `0x01d84000` and the UFS SMMU stream `0x60`.
The OS transfer callback rejects writes. The command policy permits one
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

The first 128 valid EL0 SVC entries/returns are observed. A separate bounded
observer snapshots the first 64 write SVC buffers, at most 128 bytes each,
using normal `copyin` before recording `UFD/USRBEGIN/USREND/UCON`. The observed
libignition output uses fd 3, so filtering only stdout/stderr loses it.
The original syscall arguments and results are preserved. Sysctl observations
record at most 12 MIB integers and the new-value length; dispatch observations
include the resolved kernel name, handler address and before/after MAC/handler
boundaries. These do not change policy or handler return values.

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

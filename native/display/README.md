# zorn GopFramebuffer integration

Latest qualification (2026-10-28 09:31): f8533418 produced a visible system
lock-screen clock and home indicator in the run-bound late USB-camera frame.
Eight transfers completed with last status zero; recovery and a changed matched
log followed. Unlock/home-screen interaction, touch and repeatability remain
unqualified. The heartbeat is paused in verified recovery for owner confirmation.

Earlier K80 evidence (before this lock-screen observation): repeated owner/camera-confirmed Apple
logos and successful CPU transfer callbacks. Run 5f3bedbf recorded eight
accepted surfaces and eight successful transfers. Its SpringBoard main thread
had reached the UIKit event loop; the camera still showed the Apple logo.
No welcome page or desktop is qualified. The current 8 GiB/readonly union
profile and independent RAM Data are active; the 384/512 MiB notes below are
historical. Run fe55ffa5 qualified bounded 30-minute recovery, without a
desktop. Run dd3ef48e sampled backboardd ordinal 4 inside IOMFBServer thread_body
and CFRunLoop. Run a659853c recorded nine successful transfers and another
SpringBoard UIKit main-loop sample; its camera frame still showed the Apple
logo. These do not qualify all compositor workers or a stable system UI.

This experimental board adapter consumes the canonical GopFramebuffer
`NativeLegacyDisplay.cpp` CPU path. It does not copy houji's iOS 16 user-client
ABI or introduce a vendor panel, GPU, backlight, or touch implementation.

`scripts/build-zorn-display.py` derives the exact 358-slot Legacy interface
from the current prelink of the pinned iPad7,1 / 21H461 kernelcache. It checks
the original MobileGraphics and IOSurface executable hashes, the original
constructor chain, every inherited/owned dispatch slot, surface getters, and
selected swap/refresh call sites. Its generated header leaves private storage
opaque. The compiled canonical driver has 24 overrides, including seven
unsupported backend leaves that panic. No original code or vtable is patched.
The device probe records user clients without interposing their vtables.

The historical prelink plan's candidate digest predates this port's existing
AMFI postlink shim. The adapter hashes the actual selected original family
executables and records the actual current kernel digest. Historical QEMU
runtime metadata is not substituted for this device's observations. Runtime
registration requires the real `IOMobileFramebufferLegacy` metadata pointer
and 0x18a0 class extent.

The ordinary static initializer is staged late; its instruction bytes are
checked unchanged. The XNU hook runs after the zorn UFS logger, independent
recovery watchdog and PMGR service. The earlier generic bsd_autoconf hook
returns until the logger is ready. The build link-stub archive has no display
hook when the real display profile is selected.

Select `zorn_display_defconfig`. `build-zorn-debug.py --display-mode 1` prepares
an isolated derived menu for initialization/release only. Mode 2 publishes the
real GOP-backed service. Base menu files retain the UFS/volatile-Data baseline.
`--checkpoint DSPDONE` returns after either a failed probe or its completed
lifecycle so early results are retained in the 4 KiB log. `DSPINIT` identifies
successful initialize/release; `DSPOK` identifies successful publication.

The board probe requires the observed PE_current_console mode: physical
0xfc400000, 1440 x 3200, 5760 bytes per row, 32-bit, no rotation, primary display.
It supplies exactly this IODeviceMemory range to the original-family subclass.
It disables the ordinary console before CPU presentation and requires
zorn_log_only=1. Its DT node identifies the implemented GOP display subsystem;
no Apple/vendor compatible or guessed DPU/DSI registers are supplied.

`DSS/DSE/DSZ` record lifecycle stage, error and original base size;
`DSL` is the original-family load result. `DCP/DCE` record user-client PID and
open result, `DSA/DSR` swap validation, `DFR/DFE/DFB` actual transfer count/error/
bytes, and `DFDONE` an original swap-retirement callback. Counters are bounded
in the persistent diagnostic ring. GPU offers explicitly refuse, allowing
the canonical CPU path; no GPU completion is fabricated.

Host ABI/build success does not qualify registration, a visible system frame,
a stable desktop, panel timing or touch. Record these outcomes separately.

## Current runtime evidence and CPU GUI candidate

The live original 0x18a0 parent and initialize/release path passed. Candidate
323fe6ee passed stage 10 / error 0: exact entry-ID lookup confirmed actual
registration. Its DSPDONE summary acquired the writer for one bounded bulk
commit; transient observers can no longer discard that completion.

Mode 3 adds logical PM, real swap validation, CPU transfer/retirement, a
2x UI scale and a 60 Hz software notification timer. This is not measured
panel refresh. It includes only the first three exact display-startup fixups
from the pinned OS profile, verified read-only by prepare-zorn-cpu-profile.py.
The existing core patch applies them only after original page authentication
and original-byte matching. Original OS/SystemOS image files stay unchanged.

Use --memory-mib 512 to request a separate owned XNU window from the real
UEFI conventional-memory allocator. The default 384 MiB baseline had 711
free 4 KiB pages during service startup; the 512 MiB candidate reached WRGO.
That does not yet qualify full GUI or memory stability. The Data disk still
has its independent 512 MiB sparse logical capacity.

GPU work is deferred by the owner's explicit priority. Touch remains a
subsequent task after a verified system UI.


Official-workflow review: the CPU path copies an already produced surface; it
is not a software Metal/OpenGL renderer. The current selected profile's three
UI startup fixups target AttentionAwareness and PosterBoardServices, not an
accelerator fallback. The latest hardware query finds no iterator for
IOAcceleratorES; see docs/review-2026-10-27-official-porting.md before resuming
GUI trials. The hardware GPU work remains deferred by the owner.


## Volatile Data state service

`build-zorn-debug.py --keystore-state` explicitly enables upstream
`AppleKeyStoreState` for the independent RAM Data GUI trial. The board probe
requires `ephemeral-storage=1`, `offline-key-events=1`, `sheng-aks=1`, absence of
an existing AppleKeyStore class, and no original-keystore request. It stages
the upstream class initializer after IOKit is ready; its instructions are
checked unchanged. The exact 17.7.11 component/catalog revision is
42ff83e08b2265fe741d4adaf084bebe003452ba.

The interface describes unprotected temporary storage: no keybag, no passcode,
no key operations or SEP. Unsupported selectors retain the upstream errors.
This is neither persistent secure storage nor Android key-store access.
The existing component closed-boundary test and actual XNU ABI compilation
pass. Initial probe stages and the first bounded calls use the existing log
block; runtime/UI qualification is recorded separately in the progress log.

The sRGB ADT follows sheng's CPU display profile; an owner-confirmed Apple
logo and two transfer callbacks were captured in 2742649e. The last callback
succeeded. This still does not qualify a stable welcome screen or desktop.


`--hid-family` is a separate, explicit OS-service trial. It loads the original
IOHIDFamily and IOHIDEventDriver through their normal loader APIs and waits
at most five seconds for their real IOHIDResource. It creates no HID device,
button or touch reports. Physical touch remains unimplemented. Native ABI
compilation passed; runtime evidence belongs to the progress record.

`--quiet-gui` keeps fixed GUI/IPC/exit snapshots and bounded watchdog progress,
while omitting user-write buffer capture and verbose exec text. The optional
state service and OS-service loader stay default-off in baseline payloads.


## 2026-10-28: startup hardware brightness

Owner-confirmed lock screen is now the baseline; heartbeat is active.
`ZornDsiBrightness.h` is the bounded O11/DSI0 command path and
`ZornPanelBrightness.h` maps/logs it once before the CPU display publishes.
Modes 1/2/3 are register snapshot / panel read / fixed low limit with readback;
mode 0 remains off. UEFI menu brightness and OS sliders are not implemented.
See [current brightness evidence](../../docs/progress-2026-10-28-brightness.md).

# Offline fixed-work public Metal probe293

This is a separate,uninstalled probe candidate. `probe-frame293.patch` extends the exact267 public Metal source and changes its program identity. It reuses the original shader/metallib,pipeline,32×32 shared IOSurface helper,shared Query/Close test and120-present path. No private frontend entry is used.

After the original complete shader/pixel check,the probe performs16 fresh command buffers sequentially. Each iteration re-poisons the real shared IOSurface,encodes the same original draw,commits,waits up to3s for the actual completed handler,and compares Metal getBytes with the independent IOSurface CPU view and expectedCRC. Uncertain completion retains resources until the existing watchdog. Completed CPU-readback errors report failure and use normal process teardown.

Each report records CPU uptime before preparation,after encoding,after commit,after completion and after readback verification. The strict parser requires all16 ordered reports,one timebase,successful completion and expectedCRC before publishing statistics. These phases include CPU,driver,scheduling and cache work;they do not measure pure GPU duration or physical displayFPS. Positive parser fixtures are synthetic.

The source patch replays with zero fuzz;the iOS26 arm64e executable compiles with the existing SDK and is signed using unchanged267 entitlements. No293 root,kernel,installation or device result is implied. Exact source/build inputs are in `source-manifest.json`.

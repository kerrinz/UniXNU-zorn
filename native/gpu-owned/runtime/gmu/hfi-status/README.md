# Supplied Gen7 hwsched HFI status

This unselected CPU function classifies two supplied32-bit integers. Exact fixed
OEM453d8875 gen7_9_1 selects adreno_gen7_9_0_hwsched_gpudev and ultimately
gen7_hwsched_hfi_handler, not gen7_hfi_irq_handler. The reference is not Xiaomi
stock attestation. Neither the status nor software mask is observed here.

The exact handler suppresses only MSGQ bit0 when absent from its software mask.
MSGQ0/DBGQ2 select a worker branch; CM3 fault15 selects a fault branch, even
when DBGQ/CM3 are absent from a supplied mask. SIDEMSGQ1 has no direct branch.
The header OOB mask16..31 differs from the handler's ignored bits25..31:
oob_max=8 means its GENMASK expression retains bit24. Both raw inputs remain
available. unhandled_by_reference mirrors the later diagnostic test, and
without_direct_branch retains every input bit outside the three action bits,
including SIDEMSGQ and high ignored bits. This never asserts an unknown bit is
safe, serviced or retired. No auxiliary CM3 status is read by that handler;
AO fence auxiliary status is a separate domain and is never invented here.

Return OK validates only CPU output shape/classification. There is no register
offset/read/write/clear/mask operation, IRQ handler/source/controller lease,
callback, work scheduling, OOB completion, ACK/packet decode or fence retirement.
The AO and native RBBM/CP domains are separate; do not feed this scalar into
NativeAdrenoIrq. No hardware owner, route/stop/DMA eligibility or runtime caller
is added. Existing query/HFI/log wire formats and older profiles are unchanged.

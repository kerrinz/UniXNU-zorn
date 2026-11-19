# Initial native kernel task observation

`ZornKnownTask266.h` exports24 existing `ZornGen7HostRing26::recordKnownImage` fields through the actual UFS progress callback only after the worker release/acquire completion. It omits the IOVA and handle. No GPU command,shader,allocation,register read,root policy or backend lifecycle changes. The frozen record describes the existing initial kernel known-image task;it is not current global GPU quiescence or release authority.

Qualification requires the original task raw0/phase6,grant and real fence completion,source-defined ring idle masks,zero outstanding/device references,unmap and task OOB release,balanced table leases,and full backing verification with32x32 red RGBA CRCe843b26a. CPU output was poisoned with6d. The raw busy register is not a boolean:existing `hhr_idle` requires bit23 clear and status bits other than bit0 clear. The decoder preserves valid task failures and refuses malformed or mutated initial records. Host synthetic results are not hardware acceptance.

The existing265 SHOT/CRC protocol,264 VM totals,CPU16KiB/GPU4KiB granularity and131072span capacity remain. Complete native source/patches/build input hashes are linked from the266 handoff. No disassembly or reverse engineering.

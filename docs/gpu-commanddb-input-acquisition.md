# K80 CommandDB acquisition and offline import

This is a preparation document,not a boot admission. The decoder below is implemented and read-only. No device acquisition module or boot image is ready. The owner asked to continue porting;that instruction does not replace a fresh device scope/claim. The deleted recurring automation stays deleted.

## What can be obtained locally

The supplied `zorn-kernel/drivers/soc/qcom/cmd-db.c` defines a144-byte header,eight16-byte slave rows and24-byte resource records. Entry and auxiliary offsets are relative to the end of the144-byte header. Resource names are eight raw bytes,not necessarily terminated strings. The search stops at the first zero slave ID;later rows remain source bytes and are not searched.

The same driver's probe maps an `of_reserved_mem_lookup` region using `MEMREMAP_WB` and checks magic. Its readiness check does not bind the global version to an independently qualified expected version. The debugfs output prints resource fields and per-slave versions;it omits a complete byte-exact reservation image and is unsuitable as a replacement snapshot. Those source facts do not authorize Linux/Darwin mappings or memory reads on this phone.

All four retained stock DTBs describe `qcom,cmd-db` under `/reserved-memory`,with `no-map`,two address cells,two size cells and size0x20000 (131072 bytes). The raw cell bytes are source descriptions,not readable-memory ownership. No decoder or capture program uses their address cells as a pointer.

Stock AOP ELF containers,synthetic fixtures and historical resource lookup results cannot fill the raw snapshot input. Observing the first version word and passing it back to a consumer does not independently qualify it.

## Implemented offline receiver

`../scripts/decode-zorn-commanddb-file.py` reads an explicitly supplied file with a separately declared byte length and SHA256. It writes JSON to stdout only. It decodes all active rows and resource records,retaining raw IDs,priorities,address bytes,versions and AUX bytes. It records duplicate IDs and AUX/table overlaps without selecting a resource or claiming eligibility. Post-terminator row bytes remain in the output.

The file is bounded at4MiB and4096 entries for review resource consumption;these are offline tool budgets,not K80 runtime limits. Truncated/extra bytes,wrong hashes,ELF/DT containers,bad magic and record/AUX extents outside the file refuse. Successful decoding always leaves snapshot qualification,expected-version qualification,coherency and hardware qualification false. A caller can self-sign a file;the hash provides byte binding,not capture authenticity.

Example,only after an independently supplied raw file exists:

```sh
python3 -B UniXNU-zorn/scripts/decode-zorn-commanddb-file.py \
  --raw-reservation-file /absolute/path/commanddb.raw \
  --expected-bytes 131072 \
  --source-sha256 INDEPENDENTLY_RECORDED_SHA256
```

The size in this example matches the retained DT descriptions. It does not attest that a supplied file covers a current live reservation. Do not substitute an AOP image or debugfs text. Do not label synthetic test output as a device capture.

## Acquisition choices and concrete limits

An externally supplied byte-exact capture is the first viable input route. Preserve the original immutable file and a separate capture receipt identifying device/firmware/build,producer source/binary hash,capture epoch and the producer's actual extent/coherency/lifetime basis. Archive raw acquisition failures. Record any unproven field as unknown. Keep the global observed version separate from an independent version-policy receipt. The offline decoder can inspect bytes even when those receipts are incomplete,but startup admission must remain false.

The existing resource-observation runner is not an alternative full-snapshot route. Its a315 claim is consumed. It performed bounded protocol/resource-ID/GCD queries without physical dereference. Repeating those queries would neither produce the complete reservation bytes nor establish an independent global version policy. No historical ready/admission is reusable.

A new device exporter would require a separate design and scope change. It must first have an actual typed,owned,CPU-readable and coherent source capability;it must not cast DT address cells or reuse a historical GCD descriptor as that capability. If that capability cannot be obtained,the exporter stops without a read. No such source capability is implemented or qualified here.

The current terminal carrier permits one4096-byte block. A131072-byte reservation is32 such blocks before metadata,and cannot fit the permitted record. Replacing it with debugfs text,hash-only output,truncation or fragmentation would not satisfy the complete snapshot contract. Expanding that carrier,adding storage blocks or a USB export path is outside the existing scope. This document does not propose silently bypassing those limits. A new export channel needs concrete source,object and failure evidence before it can be presented for execution approval.

## Conditions before any future device proposal

A future executable proposal must specify the actual export channel and separately authorize its I/O extent. Preserve v18/v19/E20/v21 and the existing single-block terminal record unless an exact change is approved. No writes to Android/userdata,GPT,slots or Data content are allowed by this document.

Only92988a43/zorn/slotA and the fixed `build-zorn-debug.py` / `run-zorn-debug.py` entries are eligible. A future image needs an independently archived kernel/FD/current start/FAT/menu/ADT/input closure,new scope and nonce,new ready/admission,WDT1,fresh full-page BCB preserving its tail,and one exclusive claim before the first USB query. Start only from positively identified OrangeFox Recovery;no bootstrap,retry or Android boot. Recovery remains bounded at600 seconds. Stop all device actions and preserve evidence if recovery fails;no automatic flashing or restoration.

Neither that proposal nor a successful snapshot alone would establish power/rate/vote/reset/PAS/SMMU/IOVA/DMA/GPU rights. K80 policy and native ownership contracts remain separate inputs. No selected component,runtime caller,FD/kernel/device candidate or policy header is produced here.

## Next implementation decision

The implemented offline decoder can accept a real capture now without another parser rewrite. The next acquisition implementation cannot be honestly marked runnable until an owned snapshot source and an approved complete-data export channel exist. More synthetic decoder tests or a repeated resource boot will not resolve that. The practical choice is an independently supplied raw capture,or an explicitly scoped new exporter whose ownership and channel design can actually be demonstrated. Neither requires physical interaction to be requested during this preparation work.


## Freestanding C reuse

`native/gpu-owned/source-review/ZornCommandDbFile.c` now provides the same raw-layout operation as a caller-buffer C core,without generated Sheng policy dependencies.It validates all row/AUX extents before output writes and copies raw record bytes plus FILE offsets.The new isolated host sanitizer tests and iOS17 ARM64 object compilation pass.This source is unselected and has no native provider or startup caller;it does not resolve the acquisition/channel/independent-version requirements above.


## Raw receiver output budget

The Python receiver preflights all AUX extents and their cumulative materialized byte count before creating per-entry hex strings.Repeated/overlapping AUX slices each consume the budget;the limit is8MiB of raw AUX bytes,or16MiB of AUX hex characters plus bounded metadata.Over-budget files refuse with exit2;data are never truncated or silently omitted.This bounds offline export work and supplies no K80 runtime policy.The separate C file core only copies record bytes and reports AUX file offsets/lengths,so it does not materialize those repeated AUX strings.

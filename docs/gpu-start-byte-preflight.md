# Native GPU byte-count admission ordering

NativeAdrenoGpu::start checked callback/pointer presence,then latched started and invoked board reserve,bootGmu and programSmmu before Ring::attach rejected invalid ring/fence byte counts. The failure is visible in source ordering without constructing a powered board or invoking any operation.

The independent UNAPPLIED candidate checks exactly the existing Ring byte prerequisites before started/board publication:8192..1MiB power-of-two ring storage,and64..(16MiB-1) fence storage. These are the retained unselected Ring software API limits,not chosen K80 geometry or memory rights. It preserves all previously valid inputs and their call sequence. Other Ring/CP address/alignment validations remain in their original locations;this is not a claim every invalid configuration now fails before board activity.

Nine invalid scalar count pairs,four inclusive/mode-free controls,three source corruption controls,ASan/UBSan and one new iOS17 NativeGpu object pass. The source controls require the guard before started and all three board calls. No complete valid/invalid GPU config,board provider,address/lease,successful ring/fence or native object was modeled. start/board/ring/getter/callback/native operations remain unexecuted;object is unlinked/unexecuted.

The patch adds no power/reset/retry operation and selects no startup/component/runtime caller. Original catalog/pins,32 independent patches,eight profiles,class/header ABI,normal wire/log/carrier and hardware qualification remain unchanged. It is independent of prior Ring/CP candidates.

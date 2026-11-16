# Lower SMMU prepare error propagation

NativeAdrenoPrepareSmmuMemory returns IOReturn. Its actual source includes NoMemory for root allocation failure,IOError for audit/publisher failure,Busy for existing state,and NoResources/BadArgument for kit refusals. NativeAdrenoSmmuContext::prepare preserved only NoResources and converted every other failure to BadArgument,discarding failure cause before the GMU/GPU caller received it.

The independent UNAPPLIED candidate returns the unchanged lower IOReturn on failure. Argument/capacity refusals keep their existing codes;allocation,audit/publication and busy errors now retain theirs. No failure becomes success. Success config construction,prepared publication,retention and all callers remain unchanged. This supplies no retry,cleanup,root,address-space or hardware policy.

Five source return-site traces,three source corruption controls and one changed real-header iOS17 SmmuContext object pass. No enum result from a synthetic native peer was injected and no prepare/begin/allocator/kit/provider/getter/program/map/cache/native function was executed. Target object is unlinked/unexecuted. Caller source propagates failure before later program/attach/map and ready publication;no success path was run.

Existing table-page/VM lifetime and capacity records remain independent and were not rerun or composed. Catalog/pins,32patches,eight profiles,class/header ABI,wire/log/carrier and runtime selections are unchanged. A preserved source status is not an observed hardware error,ownership/OAS/route contract or GPU qualification.

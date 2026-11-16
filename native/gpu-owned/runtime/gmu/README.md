# Gen7 GMU reservation size validation

This CPU-only helper reuses ZGPlanMemAlloc and verifies the narrow ordinary
GMU RAM/GPU-global import extent. Include this directory and its parent runtime
directory when compiling. It is unselected and has no runtime caller.

The supplied backing byte count must cover the request and be page-sized.
Reserve ALIGN(backing_bytes, size_alignment), not ALIGN(requested_bytes, ...).
The resulting tail is not backed by the payload. A future genuine VMA owner
must keep it unavailable for other mappings; current NativeAdrenoVm tracks
mapped spans and is not that independent reservation ledger. VA alignment is
retained separately. Secure, fixed-resource and preallocated paths refuse.

Inputs are caller-supplied sizes, never native observations or authority.
No address is generated/exported; no allocation, native method, mapping,
callback, ACK, lease or provider success is modelled. The result describes
arithmetic only. It is not a GMU import adapter. Actual bank/context/routing,
VMA lifetime, permissions/cache attributes and stopped masters remain absent.
The old planner/profile and all wire protocols remain unchanged.

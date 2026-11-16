# Handle-index reserve cardinality width

The current UserClient/VM callers remain below the doubling-overflow region;this is not a demonstrated current K80 path. The public reserve(size_t keys) entry has a distinct input contract gap: keys*2 can wrap and incorrectly report enough capacity. Three pure cardinality witnesses pass the original loop decision without growth and now refuse through an independent UNAPPLIED guard. Seven ordinary/exact/over/wide-boundary decisions retain their results under ASan/UBSan. No key value or successful handle is modeled.

Only the reserve early guard/comparison changes. No fields,hashing,growth,allocator behavior,insert/find/erase or caller bodies change. The24-byte class layout remains unchanged. The actual changed inline method compiles with real iOS17 kernel headers in an internal,unlinked compile fixture taking an unbound pointer;the fixture is never instantiated or called. Native allocator imports are real compile dependencies and do not establish allocator execution or a linked kernel ABI. No component/runtime caller is selected.

The original exact catalog header,pins,32 patches and8 profiles remain unchanged. No prior VM/capacity/fullcore/role-API suite is rerun and no target object executes. This is input-preflight hardening,not GPU mapping,ownership,execution or rendering progress.

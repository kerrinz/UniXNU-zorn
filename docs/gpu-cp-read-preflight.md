# CP read-mode callback argument preflight

NativeAdrenoCpInit::run already rejects missing io/write32 as BadArgument. In its public already-programmed mode it also needs read32, but previously handled an absent read32 inside the read/compare failure expression by calling poison(). That path invokes no I/O yet permanently prevents subsequent use of the object. A missing function member is an invalid API argument, distinct from an actual callback failure or a returned readback mismatch.

The independent UNAPPLIED candidate validates this conditional read member after config validation and before either I/O branch, returning BadArgument without poisoning. Write mode retains its original requirements. Non-null callback failures and mismatched readback still poison, and all valid calls,packet values,ring submission and fence behavior remain byte-identical. No internal retry,reset or startup policy is added.

Three source corruption controls and one changed real-header iOS17 CP module pass. Checks trace the original short-circuit through poison versus the new argument refusal;run,poison,ring getters,read/write/barrier and any provider were never executed or modeled. No successful CP/fence/readback or synthetic hardware return is fabricated. The object remains unlinked/unexecuted. Retained Service and NativeGpu callers use mode0, so no existing K80 failure is claimed.

No CP_ME_INIT,firmware,pwrup or K80 parameters are generated or selected. Original catalog/pins,32 independent driver patches,eight profiles,class layout,ABI and normal wire/log fields remain unchanged. This preflight does not establish GPU ownership,readable MMIO,completion or startup qualification.

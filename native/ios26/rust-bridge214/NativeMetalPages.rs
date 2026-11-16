// SPDX-License-Identifier: MIT
//! Track the VM objects behind no-copy addresses, following AdrenoMetal fb2070d2.
//! A reused address does not identify the pages pinned by an older GPU import.

use std::collections::HashMap;
use std::hash::{Hash, Hasher};
use std::sync::atomic::{AtomicU64, Ordering::Relaxed};

const MAX_NOTES: usize = 8192;
const MAX_REGIONS: usize = 4096;
static QUERIES: [AtomicU64; 4] = [const { AtomicU64::new(0) }; 4];

/// Protected by the device's existing no-copy constructor gate. This holds only
/// identities, never a buffer, pointer dereference or ownership of client pages.
#[derive(Default)]
pub(crate) struct NoCopyPages {
    seen: HashMap<(u64, u64), u64>,
    forgot: bool,
}

impl NoCopyPages {
    pub(crate) fn needs_remap(&self, range: (u64, u64), now: Option<u64>) -> bool {
        match self.seen.get(&range) {
            Some(&previous) => now != Some(previous),
            None => self.forgot || now.is_none(),
        }
    }

    /// Record only after a successful constructor has pinned the pages. Pinning
    /// for writing can change the VM object through copy-on-write. A failed or
    /// unknown observation cannot prove there is no older live import.
    pub(crate) fn record(&mut self, range: (u64, u64), pinned: Option<u64>) {
        if let Some(identity) = pinned {
            if self.seen.len() >= MAX_NOTES && !self.seen.contains_key(&range) {
                self.seen.clear();
                self.forgot = true;
            }
            self.seen.insert(range, identity);
        } else {
            self.seen.remove(&range);
            self.forgot = true;
        }
    }
}

struct ObjectRegion {
    address: u64,
    size: u64,
    object: u32,
    offset: u64,
}

fn identity_over(start: u64, length: u64, mut query: impl FnMut(u64) -> Option<ObjectRegion>) -> Option<u64> {
    let end = start.checked_add(length)?;
    if length == 0 { return None; }
    let mut at = start;
    let mut hash = std::collections::hash_map::DefaultHasher::new();
    for _ in 0..MAX_REGIONS {
        let region = query(at)?;
        if region.address > at || region.object == 0 { return None; }
        let next = region.address.checked_add(region.size)?.min(end);
        if next <= at { return None; }
        let offset = region.offset.checked_add(at - region.address)?;
        (at, next, region.object, offset).hash(&mut hash);
        at = next;
        if at == end { return Some(hash.finish()); }
    }
    // A pathological fragmented map must not cause an unbounded render-thread
    // walk. Unknown identity takes the conservative fresh-import path instead.
    None
}

// XNU vm_region_submap_short_info_64 (mach/vm_region.h), twelve 32-bit words.
// The short form avoids asking the kernel to count resident pages.
#[cfg(target_vendor = "apple")]
#[repr(C, packed(4))]
#[derive(Default)]
struct Region {
    protection: i32,
    max_protection: i32,
    inheritance: u32,
    offset: u64,
    user_tag: u32,
    ref_count: u32,
    shadow_depth: u16,
    external_pager: u8,
    share_mode: u8,
    is_submap: i32,
    behavior: i32,
    object_id: u32,
    user_wired_count: u16,
}

#[cfg(target_vendor = "apple")]
fn query_region(at: u64) -> Option<ObjectRegion> {
    unsafe extern "C" {
        static mach_task_self_: u32;
        fn mach_vm_region_recurse(task: u32, address: *mut u64, size: *mut u64, depth: *mut u32,
                                  info: *mut i32, count: *mut u32) -> i32;
    }
    let (mut address, mut size, mut depth) = (at, 0, 64);
    let mut info = Region::default();
    let mut count = (std::mem::size_of::<Region>() / 4) as u32;
    // SAFETY: all out-parameters are local, with exactly count words of storage.
    // The syscall queries mappings; it never reads bytes at the supplied address.
    let status = unsafe {
        mach_vm_region_recurse(mach_task_self_, &mut address, &mut size, &mut depth,
                               (&raw mut info).cast(), &mut count)
    };
    if status != 0 || count != (std::mem::size_of::<Region>() / 4) as u32 || info.is_submap != 0 {
        return None;
    }
    Some(ObjectRegion { address, size, object: info.object_id, offset: info.offset })
}

#[cfg(not(target_vendor = "apple"))]
fn query_region(_: u64) -> Option<ObjectRegion> { None }

pub(crate) fn pages_identity(start: u64, length: u64) -> Option<u64> {
    let began = std::time::Instant::now();
    let result = identity_over(start, length, query_region);
    let micros = began.elapsed().as_micros().min(u64::MAX as u128) as u64;
    QUERIES[0].fetch_add(1, Relaxed);
    if result.is_none() { QUERIES[1].fetch_add(1, Relaxed); }
    QUERIES[2].fetch_add(micros, Relaxed);
    QUERIES[3].fetch_max(micros, Relaxed);
    result
}

pub(crate) fn query_stats() -> [u64; 4] { std::array::from_fn(|i| QUERIES[i].load(Relaxed)) }

#[cfg(test)]
#[path = "../../../../checks/metal-no-copy-pages.rs"]
mod tests;

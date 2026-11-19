// SPDX-License-Identifier: MIT
use super::*;

#[test]
fn identities_cover_every_mapping_and_offset() {
    let make = |object, offset| ObjectRegion { address: 0x1000, size: 0x4000, object, offset };
    let original = identity_over(0x1800, 0x2000, |_| Some(make(7, 0x10000))).unwrap();
    assert_eq!(Some(original), identity_over(0x1800, 0x2000, |_| Some(make(7, 0x10000))));
    assert_ne!(Some(original), identity_over(0x1800, 0x2000, |_| Some(make(8, 0x10000))));
    assert_ne!(Some(original), identity_over(0x1800, 0x2000, |_| Some(make(7, 0x20000))));
    let mut seen = Vec::new();
    let first = identity_over(0x1000, 0x3000, |at| {
        seen.push(at);
        Some(ObjectRegion { address: at, size: 0x1000, object: 7, offset: at })
    });
    assert!(first.is_some());
    assert_eq!(seen, [0x1000, 0x2000, 0x3000]);
    let last_changed = identity_over(0x1000, 0x3000, |at| Some(ObjectRegion {
        address: at, size: 0x1000, object: if at == 0x3000 {8} else {7}, offset: at,
    }));
    assert_ne!(first, last_changed);
}

#[test]
fn bad_or_unbounded_regions_are_unknown() {
    assert_eq!(identity_over(1, 0, |_| panic!("empty range queried")), None);
    assert_eq!(identity_over(u64::MAX, 2, |_| panic!("overflow queried")), None);
    for region in [
        ObjectRegion {address: 0x1001, size: 4096, object: 1, offset: 0},
        ObjectRegion {address: 0x1000, size: 0, object: 1, offset: 0},
        ObjectRegion {address: 0, size: 4096, object: 1, offset: 0},
        ObjectRegion {address: 0x1000, size: u64::MAX, object: 1, offset: 0},
        ObjectRegion {address: 0, size: 8192, object: 1, offset: u64::MAX},
        ObjectRegion {address: 0x1000, size: 4096, object: 0, offset: 0},
    ] {
        assert_eq!(identity_over(0x1000, 4096, |_| Some(ObjectRegion {..region})), None);
    }
    let mut calls=0;
    assert_eq!(identity_over(0, MAX_REGIONS as u64 + 1, |at| {
        calls+=1;
        Some(ObjectRegion {address: at, size: 1, object: 1, offset: at})
    }), None);
    assert_eq!(calls, MAX_REGIONS);
}

#[test]
fn pinned_identity_and_forgotten_ranges() {
    let mut notes=NoCopyPages::default();
    let range=(0x1000,4096);
    assert!(!notes.needs_remap(range,Some(1)));
    notes.record(range,Some(2)); // pinning COW changed the object
    assert!(!notes.needs_remap(range,Some(2)));
    assert!(notes.needs_remap(range,Some(1)));
    assert!(notes.needs_remap(range,None));
    notes.record(range,None); // failed pin/query cannot erase evidence of a live import
    assert!(notes.needs_remap(range,Some(2)));
    notes.record(range,Some(2));
    assert!(!notes.needs_remap(range,Some(2)));
    for i in 0..=MAX_NOTES {
        notes.record((0x10000 + i as u64 * 4096,4096),Some(i as u64));
        assert!(notes.seen.len()<=MAX_NOTES);
    }
    assert!(notes.forgot && notes.needs_remap(range,Some(2)));
}

#[cfg(target_vendor = "apple")]
#[test]
fn mach_abi_and_live_address_remap_with_old_pages_retained() {
    use std::{ffi::c_void, mem::{size_of,align_of,offset_of}};
    assert_eq!(size_of::<Region>(),48);
    assert_eq!(align_of::<Region>(),4);
    assert_eq!(offset_of!(Region,offset),12);
    assert_eq!(offset_of!(Region,object_id),40);
    assert_eq!(offset_of!(Region,user_wired_count),44);
    unsafe extern "C" {
        static mach_task_self_:u32;
        fn getpagesize()->i32;
        fn mmap(address:*mut c_void,length:usize,protection:i32,flags:i32,fd:i32,offset:i64)->*mut c_void;
        fn munmap(address:*mut c_void,length:usize)->i32;
        fn mach_vm_remap(target:u32,address:*mut u64,size:u64,mask:u64,flags:i32,source:u32,
                         source_address:u64,copy:i32,current:*mut i32,maximum:*mut i32,inheritance:u32)->i32;
    }
    struct Mapping(*mut c_void,usize);
    impl Drop for Mapping {fn drop(&mut self){assert_eq!(unsafe {munmap(self.0,self.1)},0);}}
    let size=unsafe {getpagesize()} as usize;
    let first=unsafe {mmap(std::ptr::null_mut(),size,3,0x1002,-1,0)};
    assert_ne!(first as isize,-1);
    let _first=Mapping(first,size);
    unsafe {first.cast::<u8>().write_volatile(0xa5)};
    let retain = || {
        let mut alias=0;let (mut current,mut maximum)=(0,0);
        let result=unsafe {mach_vm_remap(mach_task_self_,&mut alias,size as u64,0,1,mach_task_self_,first as u64,0,&mut current,&mut maximum,2)};
        assert_eq!(result,0);
        Mapping(alias as *mut c_void,size)
    };
    // Retain every generation, as live GPU imports would. Freed intermediate
    // VM objects are allowed to reuse identities, so keeping only the first
    // alias would not exercise the contract that this fix needs to preserve.
    let mut retained=vec![(retain(),0xa5u8)];
    let old=pages_identity(first as u64,size as u64).expect("old live VM identity");
    let mut notes=NoCopyPages::default();let range=(first as u64,size as u64);notes.record(range,Some(old));
    assert!(!notes.needs_remap(range,pages_identity(range.0,range.1)));
    for value in 1..=8u8 {
        let replaced=unsafe {mmap(first,size,3,0x1012,-1,0)};
        assert_eq!(replaced,first);
        unsafe {first.cast::<u8>().write_volatile(value)};
        let new=pages_identity(range.0,range.1).expect("replacement VM identity");
        assert_ne!(new,old);
        assert!(notes.needs_remap(range,Some(new)));
        notes.record(range,Some(new));
        assert!(!notes.needs_remap(range,Some(new)));
        for (mapping,expected) in &retained {
            assert_eq!(unsafe {mapping.0.cast::<u8>().read_volatile()},*expected);
        }
        assert_eq!(unsafe {first.cast::<u8>().read_volatile()},value);
        retained.push((retain(),value));
    }
    let counts=query_stats();assert!(counts[0]>=10 && counts[2]>=counts[3]);
}

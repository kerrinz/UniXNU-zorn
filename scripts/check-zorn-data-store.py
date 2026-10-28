#!/usr/bin/env python3
"""Exercise actual K80 store policy/provider and pinned overlay, without USB."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
NATIVE = ROOT / "UniXNU-zorn/native/ufs-read"
DATA = ROOT / "out/zorn/data-store"
plan = json.loads((DATA / "plan.json").read_text())
spec = importlib.util.spec_from_file_location("data_prepare", Path(__file__).with_name("prepare-zorn-data-store.py"))
prepare = importlib.util.module_from_spec(spec); spec.loader.exec_module(prepare)
assert prepare.window(plan["userdata_first"], plan["userdata_last"]) == (plan["absolute_first_lba"], plan["blocks"])
rejected = 0
for first, last in [(0, plan["userdata_last"]), (plan["userdata_first"], plan["userdata_first"] - 1),
                    (plan["userdata_first"], plan["userdata_last"] - 1), (0xffffffff, 0xffffffff + 60936442)]:
    try:
        prepare.window(first, last)
    except ValueError:
        rejected += 1
assert rejected == 4
header = (DATA / "primary-header.bin").read_bytes(); entries = (DATA / "primary-entries.bin").read_bytes()
assert prepare.gpt(header, entries, 1)["userdata_first"] == plan["userdata_first"]
for at in [0, 16, 56, 80]:
    bad = bytearray(header); bad[at] ^= 1
    try:
        prepare.gpt(bytes(bad), entries, 1)
    except ValueError:
        rejected += 1
assert rejected == 8

program = r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <array>
#include <map>
#include "ZornDataStorePolicy.h"
#include "HoujiGptCheck.h"
#include "PersistOverlay.h"
using IOReturn = int;
constexpr int kIOReturnSuccess=0, kIOReturnNotReady=1, kIOReturnNotPermitted=2;
constexpr unsigned kDataOffset=8192;
static unsigned depth, commands, writes, syncs;
static bool failRead, failCommand;
static uint8_t dma[8192+131072];
static struct {bool ready=true, poisoned=false; int *lock=nullptr; uint8_t *virt=dma;} gHost;
static unsigned gZornDataMode;
static bool gZornDataOpened;
static std::map<uint64_t,std::array<uint8_t,4096>> disk;
static void IOLockLock(int *) {assert(!depth);++depth;}
static void IOLockUnlock(int *) {assert(depth==1);--depth;}
static IOReturn hostRead4k(uint8_t lun,uint64_t at,uint32_t n,void *dst) {
    assert(!depth && !lun && n && n<=32);
    if(failRead)return kIOReturnNotReady;
    for(unsigned i=0;i<n;++i) {auto it=disk.find(at+i); if(it==disk.end())return kIOReturnNotReady;
        memcpy(static_cast<uint8_t *>(dst)+i*4096,it->second.data(),4096);}
    return 0;
}
static IOReturn hostScsiDir(uint8_t lun,const uint8_t *cdb,unsigned length,unsigned direction,uint32_t bytes,uint32_t timeout,uint32_t *scsi) {
    assert(depth==1 && !lun && length==10 && timeout==2000000 && !gHost.poisoned);
    uint8_t u[32]={};u[0]=1;u[1]=direction==1?0x20:0;
    for(unsigned i=0;i<4;++i)u[12+i]=uint8_t(bytes>>(24-8*i));memcpy(u+16,cdb,10);
    assert(zornDataCommandAllowed(u,32,direction,bytes,gZornDataMode,gZornDataOpened));
    ++commands;*scsi=failCommand?2:0;if(failCommand)return kIOReturnNotReady;
    if(cdb[0]==0x35){++syncs;return 0;}
    ++writes;uint64_t at=(uint32_t(cdb[2])<<24)|(uint32_t(cdb[3])<<16)|(uint32_t(cdb[4])<<8)|cdb[5];
    unsigned n=(unsigned(cdb[7])<<8)|cdb[8];
    for(unsigned i=0;i<n;++i)memcpy(disk[at+i].data(),dma+kDataOffset+i*4096,4096);
    return 0;
}
#define ZORN_RAM_DATA 1
@@FIXTURES@@
#include "ZornDataStore.h"
static void put(uint64_t at,const uint8_t *p,size_t bytes) {
    assert(bytes%4096==0);for(size_t i=0;i<bytes/4096;++i)memcpy(disk[at+i].data(),p+i*4096,4096);
}
static void setup(unsigned mode) {
    disk.clear();memset(dma,0,sizeof dma);depth=commands=writes=syncs=0;failRead=failCommand=false;
    gHost.ready=true;gHost.poisoned=false;gZornDataMode=mode;gZornDataOpened=false;
    gZornDataGeometryReady=true;gZornDataGptBusy=0;
    gZornDataHeaderCrc=houjiLe32(primary+16);gZornDataEntriesCrc=houjiLe32(primary+88);
    gZornDataEntryBytes=sizeof primary_entries;gZornDataBackupLba=houjiLe64(primary+32);
    memcpy(gZornDataDiskGuid,primary+56,16);
    put(1,primary,sizeof primary);put(2,primary_entries,sizeof primary_entries);
    put(gZornDataBackupLba,backup,sizeof backup);put(houjiLe64(backup+72),backup_entries,sizeof backup_entries);
    put(kZornDataFirst,metadata,sizeof metadata);
}
static void opened(unsigned mode) {setup(mode);uint64_t first=0;const char *why="";
    assert(zorn_data_store_open(kZornDataWindowBlocks,&first,&why) && first==kZornDataFirst && !commands);}
int main() {
    (void)&houjiGptError; // unrelated legacy helper in the shared endian/CRC header
    assert(zornDataGeometry(3112704,64049146,9382658048ULL,3112704+2291712));
    assert(!zornDataGeometry(3112705,64049147,9382658048ULL,3112705+2291712));
    assert(zornDataRange(0,32) && zornDataRange(kZornDataWindowBlocks-1,1));
    assert(!zornDataRange(kZornDataWindowBlocks,1) && !zornDataRange(0,33) && !zornDataRange(~0ULL,1));
    setup(0);uint64_t first=1;assert(!zorn_data_store_open(kZornDataWindowBlocks,&first,nullptr) && !first && !commands);
    opened(1);std::array<uint8_t,131072> data;data.fill(0x39);assert(!zorn_data_store_write(5,32,data.data()) && !commands);
    assert(!zorn_data_store_sync() && !commands);
    opened(2);assert(zorn_data_store_write(5,32,data.data()) && writes==1 && commands==1);
    std::array<uint8_t,131072> got;assert(zorn_data_store_read(5,32,got.data()) && got==data);
    assert(zorn_data_store_sync() && syncs==1 && !depth);
    assert(zorn_data_store_write(kZornDataWindowBlocks-1,1,data.data()));
    unsigned before=commands;assert(!zorn_data_store_write(kZornDataWindowBlocks-1,2,data.data()) && commands==before);
    assert(!zorn_data_store_write(~0ULL,1,data.data()) && commands==before);
    assert(!zorn_data_store_write(5,1,nullptr) && commands==before);
    failCommand=true;assert(!zorn_data_store_write(5,1,data.data()) && commands==before+1 && !depth);
    assert(!zorn_data_store_sync() && !depth);
    opened(2);gHost.poisoned=true;auto saved=dma[kDataOffset];assert(!zorn_data_store_write(5,1,data.data()) && !commands && dma[kDataOffset]==saved);
    for(unsigned offset: {0U,8U,12U,16U,24U,56U,60U}) {
        setup(2);disk[kZornDataFirst][offset]^=1;
        assert(!zorn_data_store_open(kZornDataWindowBlocks,&first,nullptr) && !commands && !gZornDataOpened);
    }
    setup(2);failRead=true;assert(!zorn_data_store_open(kZornDataWindowBlocks,&first,nullptr) && !commands);
    setup(2);disk[1][56]^=1;assert(!zorn_data_store_open(kZornDataWindowBlocks,&first,nullptr));
    setup(2);disk[gZornDataBackupLba][56]^=1;assert(!zorn_data_store_open(kZornDataWindowBlocks,&first,nullptr));
    setup(2);disk[2][0]^=1;assert(!zorn_data_store_open(kZornDataWindowBlocks,&first,nullptr));
    setup(2);gZornDataGptBusy=1;assert(zorn_data_store_gpt_check()==6 && gZornDataGptBusy==1);
    // The unchanged upstream overlay uses this actual provider: durable page first, then presence bit.
    opened(2);struct Ops {bool read(uint64_t b,uint32_t n,void*p){return zorn_data_store_read(b,n,p);}
        bool write(uint64_t b,uint32_t n,const void*p){return zorn_data_store_write(b,n,p);}
        bool sync(){return zorn_data_store_sync();}} ops;
    std::array<uint8_t,16384> bits{};persist::Overlay overlay;
    assert(overlay.open(ops,kZornDataPages,zorn_data_expected_seed,false,bits.data())==persist::Open::Resumed);
    assert(overlay.present==0 && overlay.writePage(ops,17,data.data()) && overlay.has(17));
    persist::Overlay resumed;std::array<uint8_t,16384> bits2{};
    assert(resumed.open(ops,kZornDataPages,zorn_data_expected_seed,false,bits2.data())==persist::Open::Resumed && resumed.has(17));
    assert(ops.read(persist::pageBlock(kZornDataPages,17),1,got.data()) && !memcmp(got.data(),data.data(),4096));
    puts("actual policy/provider/upstream-overlay controls passed; no USB");
}
'''


def array(name, data, external=False):
    prefix = 'extern "C" const uint8_t ' if external else 'static const uint8_t '
    return prefix + name + '[] = {' + ','.join(str(b) for b in data) + '};\n'


fixtures = ''.join(array(name, (DATA / file).read_bytes()) for name, file in [
    ("primary", "primary-header.bin"), ("primary_entries", "primary-entries.bin"),
    ("backup", "backup-header.bin"), ("backup_entries", "backup-entries.bin"),
    ("metadata", "empty-overlay-metadata.bin")])
fixtures += array("zorn_data_expected_seed", bytes.fromhex(plan["seed_sha256"]), True)
with tempfile.TemporaryDirectory(prefix="zorn-data-store-") as directory:
    p = Path(directory); source = p / "check.cpp"; exe = p / "check"
    source.write_text(program.replace("@@FIXTURES@@", fixtures))
    subprocess.run(["xcrun", "clang++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-I", str(NATIVE),
                    "-I", str(ROOT / "UniXNU/drivers/RamBlock"), str(source), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
report = {"python_geometry_crc_refusals": rejected, "actual_provider_and_policy_executed": True,
          "actual_upstream_overlay_resume_readback": True, "readonly_off_wrong_header_wrong_gpt_out_of_range_refused": True,
          "write_and_sync_failures_propagated": True, "poisoned_dma_not_mutated": True,
          "plan_sha256": hashlib.sha256((DATA / "plan.json").read_bytes()).hexdigest(),
          "source_sha256": {name: hashlib.sha256((NATIVE / name).read_bytes()).hexdigest()
                            for name in ["ZornDataStore.h", "ZornDataStorePolicy.h"]},
          "hardware_qualified": False, "phone_writes": False}
(ROOT / "out/zorn/data-store-host-checks.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))

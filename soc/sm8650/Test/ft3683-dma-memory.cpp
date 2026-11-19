// SPDX-License-Identifier: BSD-2-Clause-Patent
#include "../../../native/display/ZornFt3683DmaMemory.h"
#include "ArmSmmu4KAudit.h"
#include <cassert>

namespace Dma = ZornFt3683DmaMemory;

static void audit(const Dma::Page &pool, const ArmSmmu4KConfig &config,
                  const ArmSmmu4KResult &tables, const ArmSmmu4KRange (&ranges)[2])
{
    Dma::Page input = pool;
    const ArmSmmu4KTableIo read{&input, [](void *context, uint64_t physical, uint64_t *value) {
        const auto &page = *static_cast<const Dma::Page *>(context);
        if (physical < page.physical || physical - page.physical > Dma::CpuPageBytes - 8 ||
            (physical & 7)) return -1;
        *value = *reinterpret_cast<const uint64_t *>(page.cpu + (physical - page.physical));
        return 0;
    }};
    unsigned char visits[4]{};
    const ArmSmmu4KAuditRegion audit{ranges, 2, 4, 2048, visits, sizeof(visits)};
    ArmSmmu4KTableAuditResult result{};
    assert(tables.table_pages == 3 && tables.leaf_pages == 2);
    assert(ArmSmmu4KAuditTables(&read, &config, &tables, &audit,
                               tables.root_physical, &result) == ArmSmmu4KSuccess);
    assert(result.complete && result.leaf_pages == 2);
    auto *root = reinterpret_cast<uint64_t *>(pool.cpu);
    const unsigned index = unsigned(ranges[0].iova >> 30);
    const uint64_t entry = root[index];
    assert(entry);
    root[index] = 0;
    assert(ArmSmmu4KAuditTables(&read, &config, &tables, &audit,
                               tables.root_physical, &result) != ArmSmmu4KSuccess);
    root[index] = entry;
}

int main()
{
    alignas(Dma::CpuPageBytes) uint8_t dataCpu[Dma::CpuPageBytes]{};
    alignas(Dma::CpuPageBytes) uint64_t gpiCpu[Dma::CpuPageBytes / 8]{};
    alignas(Dma::CpuPageBytes) uint64_t qupCpu[Dma::CpuPageBytes / 8]{};
    const Dma::Page data{dataCpu, 0x500004000};
    const Dma::Page gpi{reinterpret_cast<uint8_t *>(gpiCpu), 0x500018000};
    const Dma::Page qup{reinterpret_cast<uint8_t *>(qupCpu), 0x50002c000};
    Dma::Mapping mapping{};
    assert(Dma::build(data, gpi, qup, 36, mapping) == ArmSmmu4KSuccess);
    assert(mapping.rings.tx.iova == 0x100000 && mapping.rings.rx.iova == 0x100400 &&
           mapping.rings.event.iova == 0x101000);
    assert(mapping.txBuffer == dataCpu + 8192 && mapping.rxBuffer == dataCpu + 12288);
    assert(mapping.txIova == 0x40000000 && mapping.rxIova == 0x40001000);
    const ArmSmmu4KRange expectedGpi[] = {
        {0x00100000, 0x500004000, 4096, ArmSmmu4KRead, 1, 3},
        {0x00101000, 0x500005000, 4096, ArmSmmu4KRead | ArmSmmu4KWrite, 1, 3},
    };
    const ArmSmmu4KRange expectedQup[] = {
        {0x40000000, 0x500006000, 4096, ArmSmmu4KRead, 1, 3},
        {0x40001000, 0x500007000, 4096, ArmSmmu4KRead | ArmSmmu4KWrite, 1, 3},
    };
    audit(gpi, mapping.gpi, mapping.gpiTables, expectedGpi);
    audit(qup, mapping.qup, mapping.qupTables, expectedQup);

    assert(Dma::build(data, gpi, qup, 32, mapping) == ArmSmmu4KBadRange);
    assert(!mapping.rings.tx.cpu && !mapping.gpiTables.root_physical);
    const Dma::Page alias{qup.cpu, gpi.physical};
    assert(Dma::build(data, gpi, alias, 36, mapping) == ArmSmmu4KArgument);
    const Dma::Page misaligned{data.cpu, data.physical + 4096};
    assert(Dma::build(misaligned, gpi, qup, 36, mapping) == ArmSmmu4KArgument);
}

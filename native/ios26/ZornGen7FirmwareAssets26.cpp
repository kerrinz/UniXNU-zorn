// SPDX-License-Identifier: BSD-2-Clause-Patent
#include "ZornGen7FirmwareAssets26.h"
#include "ZornGen7SmmuDomain26.h"
#include <IOKit/IOBufferMemoryDescriptor.h>
#include <kern/cpu_data.h>
extern unsigned long gPhysBase,gPhysSize;
#include "HoujiFullHostNativeMemory.h"
#include "GpuCodeMemory.h"
// Private headers are produced by the unmodified upstream generator, which
// verifies exact lengths and hashes against the pinned source requirements.
// Their bytes come from the retained K80 package, not a houji firmware dump.
#include "HoujiGmuFirmwareImage.h"
#include "HoujiCpFirmwareImages.h"

int ZornGen7PrepareFirmwareAssets26(FhgStorage &storage, uint32_t &code)
{
    return fhg_prepare(&storage, sizeof(storage),
        gHoujiGmuFirmwareImage, sizeof(gHoujiGmuFirmwareImage),
        gHoujiSqeFirmwareImage, sizeof(gHoujiSqeFirmwareImage),
        gHoujiAqeFirmwareImage, sizeof(gHoujiAqeFirmwareImage), &code);
}

IOReturn ZornGen7SeedFirmwareAssets26(ZornGen7SmmuDomain26 &domain,
    const HoujiFullHostNativeMemory &memory,OSObject &owner)
{
    // Actual registry caller proceeds to enableHostGmuColdClocks,
    // prepareHostHfi and startHostGmu:select its existing direct-ring seed.
    // HWSCHED backend/old candidates remain separate;no HFI17/scratch
    // resources are introduced into this host path.
    return domain.seedGmuFirmware(memory,owner,gHoujiGmuFirmwareImage,sizeof(gHoujiGmuFirmwareImage));
}

static bool validateCode26(const NativeAdrenoMemory &bo,bool configured)
{
    static_assert(sizeof(gHoujiSqeFirmwareImage)==HCC_SQE_BYTES && sizeof(gHoujiAqeFirmwareImage)==HCC_AQE_BYTES,"actual K80 code payload extent");
    if(!bo.backed() || bo.quarantined() || bo.imported() || !bo.writeCombined() || bo.readOnly() ||
       bo.deviceReferences()!=1 || !bo.mapping() || bo.bytes()!=HCC_BYTES || bo.ownedBytes()!=HCC_BYTES)return false;
    const auto *bytes=static_cast<const volatile uint8_t *>(bo.mapping());
    for(size_t i=0;i<HCC_BYTES;++i){if(configured && i>=HCC_RECORD_OFFSET)continue;uint8_t expected=0;
        if(i>=HCC_SQE_OFFSET && i<HCC_SQE_OFFSET+sizeof(gHoujiSqeFirmwareImage)-4)expected=gHoujiSqeFirmwareImage[i-HCC_SQE_OFFSET+4];
        else if(i>=HCC_AQE_OFFSET && i<HCC_AQE_OFFSET+sizeof(gHoujiAqeFirmwareImage)-4)expected=gHoujiAqeFirmwareImage[i-HCC_AQE_OFFSET+4];
        if(bytes[i]!=expected)return false;
    }
    return true;
}

bool ZornGen7ValidateOwnedGpuCode26(const NativeAdrenoMemory &bo){return validateCode26(bo,false);}
bool ZornGen7ValidateConfiguredGpuCode26(const NativeAdrenoMemory &bo){return validateCode26(bo,true);}

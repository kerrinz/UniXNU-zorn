// SPDX-License-Identifier: BSD-2-Clause-Patent
// Bind upstream VerifiedRoot to OS mdev and SystemOS IOKit on readonly UFS.
// The mount UUID comes from APFS itself, not from a synthetic IOMedia object.
#include "ZornVerifiedRoot.h"
#include "verified_root.h"
#include <libkern/libkern.h>
#include <libkern/crypto/sha2.h>
#include <sys/errno.h>
#include <sys/mount.h>
#include <sys/vnode.h>

extern "C" {
extern const struct vr_crypto vr_xnu_crypto;
extern const uint8_t verified_root_manifest[], verified_root_systemos_manifest[], verified_root_key[];
extern const uint64_t verified_root_manifest_bytes, zorn_systemos_manifest_bytes;
void zorn_say(const char *);
}

static struct vr_view gViews[2];
static bool gReady[2], gPoisoned[2];
static const char *const gUUIDs[2] = {
    "04769D26-2CA0-4825-B443-E2E5F88300F2", "8846FE78-2910-4297-AF97-D59BB6F8FC16"};
static const char *const gImageHashes[2] = {
    "e5634d04a8ac35f024845f583394e0a35deb26a04cb0c00286a8674e25a9a4f2",
    "b4908cde41d23e6bc05e6af51a2c9eeb00cf0f863a6a18b1600c96a3fd70414f"};

static bool uuidMatches(unsigned index, const uint8_t bytes[16])
{
    char text[37];
    static const char hex[] = "0123456789ABCDEF";
    unsigned pos = 0;
    for (unsigned i = 0; i < 16; ++i) {
        if (i == 4 || i == 6 || i == 8 || i == 10) text[pos++] = '-';
        text[pos++] = hex[bytes[i] >> 4];
        text[pos++] = hex[bytes[i] & 15];
    }
    text[pos] = 0;
    return index < 2 && !strcmp(text, gUUIDs[index]);
}

extern "C" int zorn_verified_open(unsigned index, uint64_t imageBytes)
{
    if (index >= 2 || gPoisoned[index]) return 0;
    const uint8_t *manifest = index ? verified_root_systemos_manifest : verified_root_manifest;
    uint64_t bytes = index ? zorn_systemos_manifest_bytes : verified_root_manifest_bytes;
    int status = vr_open(manifest, bytes, verified_root_key, 1, &vr_xnu_crypto, &gViews[index]);
    char hash[65];
    static const char hex[] = "0123456789abcdef";
    for (unsigned i = 0; i < 32; i++) {
        hash[i * 2] = hex[gViews[index].image_sha256[i] >> 4];
        hash[i * 2 + 1] = hex[gViews[index].image_sha256[i] & 15];
    }
    hash[64] = 0;
    if (status != VR_OK || gViews[index].image_bytes != imageBytes ||
        !uuidMatches(index, gViews[index].volume_uuid) || strcmp(hash, gImageHashes[index])) {
        gPoisoned[index] = true;
        zorn_say("VRBAD");
        return 0;
    }
    gReady[index] = true;
    zorn_say(index ? "VR1OK" : "VR0OK");
    return 1;
}

extern "C" int zorn_verified_block(unsigned index, uint64_t offset, const void *data, size_t bytes)
{
    if (index >= 2 || !gReady[index] || gPoisoned[index] || (offset & 4095)) return EAUTH;
    if (vr_verify_block(&gViews[index], offset / 4096, data, bytes, &vr_xnu_crypto) != VR_OK) {
        gPoisoned[index] = true;
        zorn_say(index ? "VR1BAD" : "VR0BAD");
        return EAUTH;
    }
    return 0;
}

static int deviceIndex(dev_t device)
{
    for (unsigned index = 0; index < 2; index++)
        if (device != NODEV && gReady[index] && !gPoisoned[index] &&
            zorn_ufs_window_healthy(index) && (zorn_ufs_window_device(index) == device ||
                (index == 1 && zorn_systemos_iokit_matches(device, gUUIDs[index]))))
            return static_cast<int>(index);
    return -1;
}

extern "C" int zorn_verified_window_ready(unsigned index)
{
    return index < 2 && gReady[index] && !gPoisoned[index] && zorn_ufs_window_healthy(index);
}

struct MountQuery {
    dev_t device;
    unsigned index, matches;
    bool authorized;
};

static int checkMount(struct mount *mp, void *argument)
{
    auto *query = static_cast<MountQuery *>(argument);
    vnode_t vnode = vfs_devvp(mp);
    dev_t actual = vnode ? vnode_specrdev(vnode) : NODEV;
    if (vnode) vnode_put(vnode);
    if (actual != query->device) return VFS_RETURNED;
    query->matches++;
    query->authorized = false;
    if (!(vfs_flags(mp) & MNT_RDONLY) || strcmp(vfs_statfs(mp)->f_fstypename, "apfs")) return VFS_RETURNED;
    struct vfs_attr attr;
    VFSATTR_INIT(&attr);
    VFSATTR_WANTED(&attr, f_uuid);
    if (vfs_getattr(mp, &attr, vfs_context_kernel()) || !VFSATTR_IS_SUPPORTED(&attr, f_uuid) ||
        !uuidMatches(query->index, attr.f_uuid)) return VFS_RETURNED;
    query->authorized = true;
    return VFS_RETURNED;
}

extern "C" int native_verified_block_root_authorized(dev_t device)
{
    int index = deviceIndex(device);
    if (index < 0) return 0;
    MountQuery query = {device, static_cast<unsigned>(index), 0, false};
    zorn_say("VRQUERY");
    if (vfs_iterate(0, checkMount, &query) || query.matches != 1 || !query.authorized ||
        deviceIndex(device) != index) {
        zorn_say("VRQNO");
        return 0;
    }
    zorn_say("VRQOK");
    return 1;
}

extern "C" int native_verified_block_volume_device(const char *uuid, dev_t *device, char *path, size_t size)
{
    if (!device || !path || size < 12) return 0;
    *device = NODEV;
    path[0] = 0;
    if (!uuid || strlen(uuid) != 36) return 0;
    if (!strcmp(uuid, gUUIDs[1])) {
        if (!zorn_verified_window_ready(1) ||
            !zorn_systemos_iokit_device(uuid, device, path, size)) return 0;
        return deviceIndex(*device) == 1;
    }
    for (unsigned index = 0; index < 2; index++) {
        dev_t selected = zorn_ufs_window_device(index);
        if (!strcmp(uuid, gUUIDs[index]) && deviceIndex(selected) == static_cast<int>(index)) {
            snprintf(path, size, "/dev/md%u", index);
            *device = selected;
            return 1;
        }
    }
    return 0;
}

extern "C" int native_verified_block_manifest_sha384(dev_t device, const char *uuid, uint8_t digest[48])
{
    if (!digest) return 0;
    bzero(digest, 48);
    int index = deviceIndex(device);
    if (index < 0 || !uuid || strcmp(uuid, gUUIDs[index]) ||
        !native_verified_block_root_authorized(device)) return 0;
    const uint8_t *manifest = index ? verified_root_systemos_manifest : verified_root_manifest;
    uint64_t bytes = index ? zorn_systemos_manifest_bytes : verified_root_manifest_bytes;
    SHA384_CTX context;
    SHA384_Init(&context);
    SHA384_Update(&context, manifest, bytes);
    SHA384_Final(digest, &context);
    return 1;
}

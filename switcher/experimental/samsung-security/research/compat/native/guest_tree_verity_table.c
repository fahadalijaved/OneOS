#include "guest_tree_verity_table.h"

#include <inttypes.h>
#include <linux/dm-ioctl.h>
#include <stdio.h>
#include <string.h>

/* Linux DM ioctl layout and alignment for the selected little-endian ABI. */
#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error Unsupported Linux DM response byte order
#endif
_Static_assert(sizeof(struct dm_ioctl) == 312 && offsetof(struct dm_ioctl, dev) == 40,
               "Unexpected Linux DM ioctl header layout");
_Static_assert(sizeof(struct dm_target_spec) == 40 &&
               offsetof(struct dm_target_spec, target_type) == 24,
               "Unexpected Linux DM target layout");

enum {
    DM_ALIGNMENT = 8, ABI_MAJOR = 4, ABI_MINOR_MIN = 45, ABI_MINOR_MAX = 48,
    BLOCK_BYTES = 4096, SECTOR_BYTES = 512, SECTORS_PER_BLOCK = BLOCK_BYTES / SECTOR_BYTES
};

static int valid_device(uint32_t major, uint32_t minor) {
    return major && major <= 0xfffU && minor <= 0xfffffU;
}

/* Linux huge_encode_dev is new_encode_dev in the low 32 bits. */
static uint64_t kernel_device(uint32_t major, uint32_t minor) {
    return (minor & 0xffU) | (major << 8) | ((minor & ~0xffU) << 12);
}

static int valid_profile(const struct guest_tree_verity_profile *profile,
                         uint32_t mapped_major, uint32_t mapped_minor, uint64_t mapped_bytes) {
    if (!profile || !valid_device(mapped_major, mapped_minor)
            || !valid_device(profile->data_major, profile->data_minor)
            || !valid_device(profile->hash_major, profile->hash_minor)
            || !profile->data_blocks || profile->data_blocks > UINT64_MAX / BLOCK_BYTES
            || profile->hash_start_block > UINT64_MAX / BLOCK_BYTES
            || mapped_bytes != profile->data_blocks * BLOCK_BYTES) return 0;
    uint64_t mapped = kernel_device(mapped_major, mapped_minor);
    uint64_t data = kernel_device(profile->data_major, profile->data_minor);
    uint64_t hash = kernel_device(profile->hash_major, profile->hash_minor);
    static const unsigned char zero[GUEST_TREE_VERITY_DIGEST_BYTES];
    return mapped != data && mapped != hash
            && (data != hash || profile->hash_start_block >= profile->data_blocks)
            && memcmp(profile->root_sha256, zero, sizeof(zero)) != 0;
}

static void hex_digest(const unsigned char bytes[GUEST_TREE_VERITY_DIGEST_BYTES],
                       char text[GUEST_TREE_VERITY_DIGEST_BYTES * 2 + 1]) {
    const char digits[] = "0123456789abcdef";
    for (size_t i = 0; i < GUEST_TREE_VERITY_DIGEST_BYTES; ++i) {
        text[2 * i] = digits[bytes[i] >> 4];
        text[2 * i + 1] = digits[bytes[i] & 0xf];
    }
    text[GUEST_TREE_VERITY_DIGEST_BYTES * 2] = '\0';
}

static int expected_table(const struct guest_tree_verity_profile *profile, char *text, size_t cap) {
    char root[GUEST_TREE_VERITY_DIGEST_BYTES * 2 + 1], salt[sizeof(root)];
    hex_digest(profile->root_sha256, root);
    hex_digest(profile->salt, salt);
    /* The selected table has no optional args. The Linux target then uses
     * the default EIO behavior for verification and underlying I/O failures. */
    return snprintf(text, cap, "1 %" PRIu32 ":%" PRIu32 " %" PRIu32 ":%" PRIu32
                    " 4096 4096 %" PRIu64 " %" PRIu64 " sha256 %s %s",
                    profile->data_major, profile->data_minor, profile->hash_major, profile->hash_minor,
                    profile->data_blocks, profile->hash_start_block, root, salt);
}

enum guest_tree_verity_sample guest_tree_verity_table_check(
        const void *buffer, size_t buffer_size, uint32_t mapped_major,
        uint32_t mapped_minor, uint64_t mapped_bytes,
        const struct guest_tree_verity_profile *profile) {
    const unsigned char *bytes = buffer;
    struct dm_ioctl header;
    struct dm_target_spec target;
    const unsigned flags = DM_READONLY_FLAG | DM_STATUS_TABLE_FLAG | DM_ACTIVE_PRESENT_FLAG;
    static const char verity[DM_MAX_TYPE_NAME] = "verity";
    char expected[256];

    if (!buffer || buffer_size < sizeof(header) + sizeof(target) + 1 ||
            buffer_size > GUEST_TREE_VERITY_MAX_BUFFER ||
            !valid_profile(profile, mapped_major, mapped_minor, mapped_bytes))
        return GUEST_TREE_VERITY_REFUSED;
    memcpy(&header, bytes, sizeof(header));
    if (header.version[0] != ABI_MAJOR || header.version[1] < ABI_MINOR_MIN ||
            header.version[1] > ABI_MINOR_MAX || header.data_start != sizeof(header) ||
            header.data_size > buffer_size || header.data_size < sizeof(header) + sizeof(target) + 1 ||
            header.flags != flags || header.target_count != 1 || header.open_count < 1 ||
            header.dev != kernel_device(mapped_major, mapped_minor))
        return GUEST_TREE_VERITY_REFUSED;

    memcpy(&target, bytes + header.data_start, sizeof(target));
    size_t used = header.data_size - header.data_start;
    size_t aligned = (used + DM_ALIGNMENT - 1) & ~(size_t)(DM_ALIGNMENT - 1);
    if (target.status || target.sector_start || target.length != profile->data_blocks * SECTORS_PER_BLOCK ||
            target.next != aligned || aligned > buffer_size - header.data_start ||
            memcmp(target.target_type, verity, sizeof(verity)) != 0)
        return GUEST_TREE_VERITY_REFUSED;

    int length = expected_table(profile, expected, sizeof(expected));
    if (length < 0 || (size_t)length >= sizeof(expected)) return GUEST_TREE_VERITY_REFUSED;
    size_t payload = used - sizeof(target);
    if (payload != (size_t)length + 1 ||
            memcmp(bytes + header.data_start + sizeof(target), expected, payload) != 0)
        return GUEST_TREE_VERITY_REFUSED;
    return GUEST_TREE_VERITY_TABLE_MATCHED;
}

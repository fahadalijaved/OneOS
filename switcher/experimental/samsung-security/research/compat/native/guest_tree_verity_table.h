#ifndef ONEOS_GUEST_TREE_VERITY_TABLE_H
#define ONEOS_GUEST_TREE_VERITY_TABLE_H

#include <stddef.h>
#include <stdint.h>

enum { GUEST_TREE_VERITY_MAX_BUFFER = 4096, GUEST_TREE_VERITY_DIGEST_BYTES = 32 };

struct guest_tree_verity_profile {
    uint64_t data_blocks, hash_start_block;
    uint32_t data_major, data_minor, hash_major, hash_minor;
    unsigned char root_sha256[GUEST_TREE_VERITY_DIGEST_BYTES];
    unsigned char salt[GUEST_TREE_VERITY_DIGEST_BYTES];
};

enum guest_tree_verity_sample {
    GUEST_TREE_VERITY_REFUSED = 0,
    GUEST_TREE_VERITY_TABLE_MATCHED
};

/*
 * Inert Linux little-endian DM_TABLE_STATUS response check. buffer_size is
 * the actual original buffer capacity, including space for target alignment,
 * and must not exceed GUEST_TREE_VERITY_MAX_BUFFER. The caller obtains it
 * from a successful active-table query selected by the real held block dev_t
 * and must independently observe that FD's mapped device number and capacity.
 * Profile values must come from a pinned, authenticated content generation.
 * Neither input may move during this call.
 *
 * Match identifies one sampled active read-only table with the exact expected
 * v1 SHA-256 profile. No ioctl, mount, device operation or authority transfer.
 * The real source owner must protect the matching table from reload, removal
 * and raw-writer uncertainty across the entire mounted generation lifetime.
 */
enum guest_tree_verity_sample guest_tree_verity_table_check(
        const void *buffer, size_t buffer_size, uint32_t mapped_major,
        uint32_t mapped_minor, uint64_t mapped_bytes,
        const struct guest_tree_verity_profile *profile);

#endif

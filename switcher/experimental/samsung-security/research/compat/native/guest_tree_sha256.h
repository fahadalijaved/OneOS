#ifndef ONEOS_GUEST_TREE_SHA256_H
#define ONEOS_GUEST_TREE_SHA256_H

#include <stddef.h>
#include <stdint.h>

struct guest_tree_sha256 {
    uint32_t words[8];
    uint64_t length;
    unsigned char pending[64];
};

/* Used for the bounded stage manifest and regular file payloads. Total
 * input must be below 2^61 bytes. final consumes the current hash state. */
void guest_tree_sha256_init(struct guest_tree_sha256 *hash);
void guest_tree_sha256_update(struct guest_tree_sha256 *hash, const void *data, size_t length);
void guest_tree_sha256_final(struct guest_tree_sha256 *hash, unsigned char digest[32]);

#endif

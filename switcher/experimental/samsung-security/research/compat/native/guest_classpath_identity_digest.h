#ifndef ONEOS_GUEST_CLASSPATH_IDENTITY_DIGEST_H
#define ONEOS_GUEST_CLASSPATH_IDENTITY_DIGEST_H

#include "guest_tree_sha256.h"
#include <sys/stat.h>

/* In-process snapshot, never a wire record. Include exactly the fields used
 * by guest_readback_same_node without hashing struct padding. */
static inline void guest_classpath_hash_node(struct guest_tree_sha256 *hash, const struct statx *node) {
    const uint64_t fields[] = {
        node->stx_mnt_id, node->stx_dev_major, node->stx_dev_minor, node->stx_ino,
        node->stx_mode, node->stx_uid, node->stx_gid, node->stx_nlink, node->stx_size,
        (uint64_t)node->stx_mtime.tv_sec, node->stx_mtime.tv_nsec,
        (uint64_t)node->stx_ctime.tv_sec, node->stx_ctime.tv_nsec,
    };
    guest_tree_sha256_update(hash, fields, sizeof(fields));
}

#endif

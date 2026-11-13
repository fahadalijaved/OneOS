#ifndef ONEOS_GUEST_TREE_MANIFEST_H
#define ONEOS_GUEST_TREE_MANIFEST_H

#include <stddef.h>
#include <stdint.h>

#define GTM_PATH_MAX 255U
#define GTM_DEPTH_MAX 16U
#define GTM_XATTR_MAX 8U
#define GTM_ATTR_NAME_MAX 255U
#define GTM_ATTR_VALUE_MAX 1024U

enum gtm_kind { GTM_DIRECTORY = 1, GTM_FILE, GTM_SYMLINK };

struct gtm_row {
    const unsigned char *path, *payload, *attrs;
    uint64_t size;
    uint32_t uid, gid, nlink, children, subdirs;
    uint16_t path_length, mode, link_length;
    uint8_t kind, attr_count;
};

struct gtm_manifest {
    struct gtm_row *rows;
    size_t count;
    uint64_t file_bytes;
};

struct gtm_attribute {
    const unsigned char *name, *value;
    uint16_t name_length, value_length;
};

/* The digest is a reviewed build input, never data from the staged tree.
 * Initialize result to zero. The bounded record index borrows bytes until
 * gtm_close. Success proves the exact manifest and grammar, not a live tree. */
int gtm_open(const unsigned char *bytes, size_t length, const unsigned char digest[32],
             struct gtm_manifest *result);
void gtm_close(struct gtm_manifest *manifest);
const struct gtm_row *gtm_find(const struct gtm_manifest *manifest, const void *path, size_t length);
/* Only for a row from a successful gtm_open, with the same retained bytes. */
void gtm_read_attributes(const struct gtm_row *row, struct gtm_attribute attributes[GTM_XATTR_MAX]);

#endif

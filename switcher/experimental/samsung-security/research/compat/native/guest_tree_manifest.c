#include "guest_tree_manifest.h"
#include "guest_tree_sha256.h"

#include <errno.h>
#include <stdlib.h>
#include <string.h>

#define GTM_BYTES_MAX (8U * 1024U * 1024U)
#define GTM_ROWS_MAX 65536U
#define GTM_HEADER_BYTES 64U
#define GTM_ROW_BYTES 28U

static uint16_t le16(const unsigned char *p) {
    return (uint16_t)(p[0] | (uint16_t)p[1] << 8);
}

static uint32_t le32(const unsigned char *p) {
    return (uint32_t)le16(p) | (uint32_t)le16(p + 2) << 16;
}

static uint64_t le64(const unsigned char *p) {
    return (uint64_t)le32(p) | (uint64_t)le32(p + 4) << 32;
}

static int order(const unsigned char *a, size_t a_length, const unsigned char *b, size_t b_length) {
    size_t common = a_length < b_length ? a_length : b_length;
    int prefix = common ? memcmp(a, b, common) : 0;
    if (prefix) return prefix;
    return (a_length > b_length) - (a_length < b_length);
}

static int valid_path(const unsigned char *path, size_t length) {
    if (length > GTM_PATH_MAX || memchr(path, 0, length)) return 0;
    if (!length) return 1;
    size_t start = 0, depth = 0;
    for (size_t i = 0; i <= length; ++i) {
        if (i != length && path[i] != '/') continue;
        size_t count = i - start;
        if (!count || ++depth > GTM_DEPTH_MAX ||
            (count == 1 && path[start] == '.') ||
            (count == 2 && path[start] == '.' && path[start + 1] == '.')) return 0;
        start = i + 1;
    }
    return 1;
}

static int parse_attrs(const unsigned char **cursor, const unsigned char *end, size_t count) {
    const unsigned char *previous = NULL;
    size_t previous_length = 0;
    for (size_t i = 0; i < count; ++i) {
        if ((size_t)(end - *cursor) < 4) return 0;
        size_t name = le16(*cursor), value = le16(*cursor + 2);
        *cursor += 4;
        if (!name || name > GTM_ATTR_NAME_MAX || value > GTM_ATTR_VALUE_MAX ||
            name + value > (size_t)(end - *cursor) || memchr(*cursor, 0, name) ||
            (previous && order(previous, previous_length, *cursor, name) >= 0)) return 0;
        previous = *cursor;
        previous_length = name;
        *cursor += name + value;
    }
    return 1;
}

const struct gtm_row *gtm_find(const struct gtm_manifest *manifest, const void *path, size_t length) {
    size_t start = 0, end = manifest->count;
    while (start < end) {
        size_t middle = start + (end - start) / 2;
        const struct gtm_row *row = &manifest->rows[middle];
        int relation = order(path, length, row->path, row->path_length);
        if (!relation) return row;
        if (relation < 0) end = middle;
        else start = middle + 1;
    }
    return NULL;
}

static int count_children(struct gtm_manifest *manifest) {
    for (size_t i = 1; i < manifest->count; ++i) {
        const struct gtm_row *row = &manifest->rows[i];
        size_t parent_length = row->path_length;
        while (parent_length && row->path[parent_length - 1] != '/') --parent_length;
        if (parent_length) --parent_length;
        const struct gtm_row *parent = gtm_find(manifest, row->path, parent_length);
        if (!parent || parent->kind != GTM_DIRECTORY) return 0;
        struct gtm_row *entry = &manifest->rows[parent - manifest->rows];
        ++entry->children;
        if (row->kind == GTM_DIRECTORY) ++entry->subdirs;
    }
    for (size_t i = 0; i < manifest->count; ++i) {
        const struct gtm_row *row = &manifest->rows[i];
        if (row->kind == GTM_DIRECTORY && row->nlink != row->subdirs + 2) return 0;
    }
    return 1;
}

int gtm_open(const unsigned char *bytes, size_t length, const unsigned char digest[32],
             struct gtm_manifest *result) {
    if (!bytes || !digest || !result || result->rows || result->count ||
        length < GTM_HEADER_BYTES || length > GTM_BYTES_MAX) { errno = EINVAL; return -1; }
    struct guest_tree_sha256 hash;
    unsigned char actual[32];
    guest_tree_sha256_init(&hash);
    guest_tree_sha256_update(&hash, bytes, length);
    guest_tree_sha256_final(&hash, actual);
    if (memcmp(actual, digest, sizeof(actual)) || memcmp(bytes, "OGTMF001", 8)) {
        errno = EPROTO;
        return -1;
    }
    size_t count = le32(bytes + 8);
    if (!count || count > GTM_ROWS_MAX || count > (length - GTM_HEADER_BYTES) / GTM_ROW_BYTES) {
        errno = EPROTO;
        return -1;
    }
    struct gtm_manifest next = {.rows = calloc(count, sizeof(*next.rows)), .count = count};
    if (!next.rows) return -1;
    uint32_t kinds[4] = {0};
    const unsigned char *cursor = bytes + GTM_HEADER_BYTES, *end = bytes + length;
    for (size_t i = 0; i < count; ++i) {
        if ((size_t)(end - cursor) < GTM_ROW_BYTES) goto invalid;
        struct gtm_row *row = &next.rows[i];
        row->path_length = le16(cursor);
        row->kind = cursor[2];
        row->attr_count = cursor[3];
        row->mode = le16(cursor + 4);
        row->link_length = le16(cursor + 6);
        row->uid = le32(cursor + 8);
        row->gid = le32(cursor + 12);
        row->nlink = le32(cursor + 16);
        row->size = le64(cursor + 20);
        cursor += GTM_ROW_BYTES;
        if (row->kind < GTM_DIRECTORY || row->kind > GTM_SYMLINK || row->attr_count > GTM_XATTR_MAX ||
            row->mode > 07777 || row->path_length > (size_t)(end - cursor) ||
            !valid_path(cursor, row->path_length)) goto invalid;
        row->path = cursor;
        cursor += row->path_length;
        if (i == 0) {
            if (row->path_length || row->kind != GTM_DIRECTORY) goto invalid;
        } else {
            const struct gtm_row *previous = row - 1;
            if (order(previous->path, previous->path_length, row->path, row->path_length) >= 0) goto invalid;
        }
        size_t payload = 0;
        if (row->kind == GTM_SYMLINK) {
            if (!row->link_length || row->link_length > GTM_PATH_MAX || row->size != row->link_length ||
                row->mode != 0777 || row->nlink != 1) goto invalid;
            payload = row->link_length;
        } else {
            if (row->link_length) goto invalid;
            if (row->kind == GTM_FILE) {
                if (row->nlink != 1 || row->size >= (UINT64_C(1) << 61) ||
                    UINT64_MAX - next.file_bytes < row->size) goto invalid;
                next.file_bytes += row->size;
                payload = 32;
            } else if (row->size) goto invalid;
        }
        if (payload > (size_t)(end - cursor) ||
            (row->kind == GTM_SYMLINK && memchr(cursor, 0, payload))) goto invalid;
        row->payload = cursor;
        cursor += payload;
        row->attrs = cursor;
        if (!parse_attrs(&cursor, end, row->attr_count)) goto invalid;
        ++kinds[row->kind];
    }
    if (cursor != end || kinds[GTM_FILE] != le32(bytes + 12) ||
        kinds[GTM_DIRECTORY] != le32(bytes + 16) || kinds[GTM_SYMLINK] != le32(bytes + 20) ||
        next.file_bytes != le64(bytes + 24) || !count_children(&next)) goto invalid;
    *result = next;
    return 0;
invalid:
    free(next.rows);
    errno = EPROTO;
    return -1;
}

void gtm_close(struct gtm_manifest *manifest) {
    free(manifest->rows);
    *manifest = (struct gtm_manifest){0};
}

void gtm_read_attributes(const struct gtm_row *row, struct gtm_attribute attributes[GTM_XATTR_MAX]) {
    const unsigned char *cursor = row->attrs;
    for (size_t i = 0; i < row->attr_count; ++i) {
        uint16_t name = le16(cursor), value = le16(cursor + 2);
        cursor += 4;
        attributes[i] = (struct gtm_attribute){cursor, cursor + name, name, value};
        cursor += name + value;
    }
}

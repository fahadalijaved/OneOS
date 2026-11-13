#ifndef ONEOS_GUEST_PRIVATE_VIEW_MOUNTINFO_H
#define ONEOS_GUEST_PRIVATE_VIEW_MOUNTINFO_H

#include <stddef.h>
#include <stdint.h>

/* Pure bounded grammar only. No syscall, allocator, ownership, namespace or
 * peer-group admission. The caller must acquire current kernel metadata. */
#define GPV_MOUNTINFO_MAX_BYTES (2U * 1024U * 1024U)
#define GPV_MOUNTINFO_MAX_ROWS 4096U
#define GPV_MOUNTINFO_MAX_LINE 8192U
#define GPV_FDINFO_MAX_BYTES 8192U
#define GPV_PATH_CAPACITY 1024U
#define GPV_OPTIONS_CAPACITY 513U
#define GPV_FSTYPE_CAPACITY 64U

enum gpv_parse_result { GPV_OK = 0, GPV_INVALID = -1, GPV_LIMIT = -2 };

struct gpv_mount_row {
    uint64_t id, parent, shared, master, propagate;
    uint32_t major, minor;
    unsigned unbindable;
    char root[GPV_PATH_CAPACITY];
    char point[GPV_PATH_CAPACITY];
    char source[GPV_PATH_CAPACITY];
    char type[GPV_FSTYPE_CAPACITY];
    char options[GPV_OPTIONS_CAPACITY];
    char super_options[GPV_OPTIONS_CAPACITY];
};

/* All buffer capacities/pointers must be valid; input and output storage must
 * not overlap (including rows/count and fdinfo/id). Input is immutable during
 * parsing; copied fields have no subsequent input-buffer lifetime dependency.
 * Input is exact bytes (no terminal NUL in length), LF-terminated.
 * count is zero on any refusal; output rows have no valid partial-table state.
 * Duplicate mount IDs/tags are refused. Equal paths with distinct mount IDs
 * are LEGAL: an overmount is not resolved by line order or pathname. */
int gpv_parse_mountinfo(const char *input, size_t length,
                        struct gpv_mount_row *rows, size_t capacity,
                        size_t *count);

/* Directory/O_PATH fdinfo profile: exactly one positive decimal mnt_id is
 * required; no general timerfd/fanotify field grammar is promised. The old held
 * FD can still name its old mount after a bind; read each actual fdinfo. */
int gpv_parse_fdinfo_mnt_id(const char *input, size_t length, uint64_t *id);

/* Only a successfully parsed, unmodified table may be passed to lookups.
 * Returned pointers borrow the caller's row storage and expire when that row
 * storage changes or ends; they confer no descriptor/resource ownership.
 * NULL means missing/invalid/duplicate, never permission to select by path. */
const struct gpv_mount_row *gpv_mount_by_id(const struct gpv_mount_row *rows,
                                          size_t count, uint64_t id);
/* Diagnostic multiplicity only; never returns a pathname-selected owner. */
int gpv_mount_path_count(const struct gpv_mount_row *rows, size_t count,
                         const char *decoded_path, size_t *matches);

#endif

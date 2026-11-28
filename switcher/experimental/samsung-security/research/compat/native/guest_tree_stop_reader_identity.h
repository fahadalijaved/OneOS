#ifndef ONEOS_GUEST_TREE_STOP_READER_IDENTITY_H
#define ONEOS_GUEST_TREE_STOP_READER_IDENTITY_H

#include "guest_tree_stop_proc.h"

enum { GUEST_TREE_STOP_READER_GROUP_CAPACITY = 128 };

struct guest_tree_stop_reader_identity {
    struct guest_tree_stop_proc_birth birth;
    char boot_id[37];
    uint64_t mount_ns_inode, time_ns_inode, proc_mount_id, proc_root_inode;
    uint32_t mount_ns_device_major, mount_ns_device_minor, time_ns_device_major, time_ns_device_minor;
    uint32_t proc_device_major, proc_device_minor;
    uint32_t uid, euid, fsuid, gid, egid, fsgid, group_count;
    uint32_t groups[GUEST_TREE_STOP_READER_GROUP_CAPACITY];
    char selinux_context[193];
};

/* Borrow the admitted physical /proc root on the observer's process leader.
 * The selected kernel must have CONFIG_PID_NS disabled. The caller keeps and
 * closes proc_fd and separately admits proc visibility. Return 0 on a stable
 * sample, otherwise -1 with errno and zero a nonnull out. */
int guest_tree_stop_reader_identity_read(int proc_fd, struct guest_tree_stop_reader_identity *out);

/* Compare two successful identity samples, including numeric credentials. */
int guest_tree_stop_reader_identity_equal(const struct guest_tree_stop_reader_identity *a,
        const struct guest_tree_stop_reader_identity *b);

#endif

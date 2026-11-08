#ifndef ONEOS_GUEST_ZYGOTE_ROOT_ENTRY_H
#define ONEOS_GUEST_ZYGOTE_ROOT_ENTRY_H

#include <stdint.h>

struct guest_zygote_root_view {
    int parent_namespace_fd, private_namespace_fd;
    int inherited_root_fd, guest_root_fd;
    uint64_t inherited_root_mount_id, guest_root_mount_id;
};

enum guest_zygote_root_state {
    GUEST_ZYGOTE_ROOT_NEW,
    GUEST_ZYGOTE_ROOT_ENTERING,
    GUEST_ZYGOTE_ROOT_READY,
    GUEST_ZYGOTE_ROOT_RETIRED,
};

struct guest_zygote_root_entry {
    enum guest_zygote_root_state state;
};

/* Borrow exact admitted view descriptors above reserved slots 0-4. Call
 * after the parent has accepted the inherited-root view, in its exclusive
 * single-threaded child with independent fs and FD state, trusted inherited
 * procfs and no concurrent mount or descriptor changes. Pass a zeroed entry.
 * After the first fchdir attempt, any failure retires the child occurrence.
 * This neither consumes descriptors nor retires external references.
 * The launch owner must dispose of all outside-root handles before exec. */
int guest_zygote_enter_root(const struct guest_zygote_root_view *view,
        struct guest_zygote_root_entry *entry);

#endif

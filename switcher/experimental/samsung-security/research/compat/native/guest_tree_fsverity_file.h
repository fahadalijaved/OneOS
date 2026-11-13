#ifndef ONEOS_GUEST_TREE_FSVERITY_FILE_H
#define ONEOS_GUEST_TREE_FSVERITY_FILE_H

#include <stdint.h>

struct guest_tree_fsverity_file;
struct guest_tree_stage_guard;

struct guest_tree_fsverity_inputs {
    int stage_fd, controller_namespace_fd;
    struct guest_tree_stage_guard *guard;
};

struct guest_tree_fsverity_expected {
    uint64_t bytes;
    unsigned char sha256[32]; /* Independently admitted fs-verity digest. */
};

struct guest_tree_fsverity_borrow {
    int image_fd, proc_root_fd;
};

/*
 * Dedicated GTSP controller main thread. Uses the actual retained pre-mount
 * stage and current controller namespace witnesses under the same guard.
 * Expected is copied and must originate
 * from the independent image admission, not from this file's ioctl reply.
 * Initialize *out to NULL. Keep a nonnull owner on refusal.
 */
int guest_tree_fsverity_open_file(const struct guest_tree_fsverity_inputs *stage,
        const struct guest_tree_fsverity_expected *expected, struct guest_tree_fsverity_file **out);

/*
 * Borrow the actual held readable image and authentic proc root after
 * current guard, identity and measurement checks. Initialize both output
 * cells to -1. There is no FD transfer. Retain the file owner and original
 * guard across the detached mount and its actual release.
 */
int guest_tree_fsverity_borrow_fds(struct guest_tree_fsverity_file *file,
                                  struct guest_tree_fsverity_borrow *out);

/*
 * Close local cells after refusal with no downstream use or after the
 * actual downstream owner has released its use. Does not finish the
 * guard or prove filesystem, mount, child, or kernel release.
 */
int guest_tree_fsverity_close_file(struct guest_tree_fsverity_file *file);

#endif

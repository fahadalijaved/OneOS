#ifndef ONEOS_GUEST_TREE_FILE_EROFS_ATTACH_H
#define ONEOS_GUEST_TREE_FILE_EROFS_ATTACH_H

#include "guest_tree_prepare_root.h"

struct guest_tree_file_erofs_attach_inputs {
    int stage_fd, initial_namespace_fd, current_namespace_fd, detached_mount_fd;
};

enum guest_tree_file_erofs_attach_state {
    GUEST_TREE_FILE_EROFS_ATTACH_EMPTY = 0,
    GUEST_TREE_FILE_EROFS_ATTACH_STARTED,
    GUEST_TREE_FILE_EROFS_MOVE_ATTEMPTED,
    GUEST_TREE_FILE_EROFS_MOVE_RETURNED,
    GUEST_TREE_FILE_EROFS_BACKING_HELD
};

struct guest_tree_file_erofs_attachment {
    enum guest_tree_file_erofs_attach_state state;
    pid_t source_pid;
    int stage_fd, covered_fd, mount_fd, detached_tree_fd, backing_fd, tree_fd;
    int close_error;
    struct guest_tree_mount_identity expected_mount;
    uint64_t expected_root_inode, expected_tree_inode, backing_mount_id;
};

#define GUEST_TREE_FILE_EROFS_ATTACHMENT_INITIALIZER { \
    .stage_fd = -1, .covered_fd = -1, .mount_fd = -1, .detached_tree_fd = -1, \
    .backing_fd = -1, .tree_fd = -1 \
}

/*
 * Fixed controller source only, in its own private mount namespace before GTC
 * child creation and /data shadowing. Borrow its held guarded stage, pre-unshare
 * and current namespace witnesses, and the exact gtfm detached mount.
 * The original creator retains file provenance, writer exclusion and its FDs.
 * The controller excludes other namespace and stage-directory writers. Mount
 * workspaces must be disjoint and follow the mount parser's bounds.
 *
 * This is one attempt per process. Retain every nonnegative owned FD and the
 * exact state even on failure. Zero establishes only the checked attachment.
 * The separate controller teardown owns all descriptor closure and unmount;
 * a MOVE_ATTEMPTED or later state never becomes a pre-effect refusal.
 */
int guest_tree_file_erofs_attach(struct guest_tree_file_erofs_attachment *owner,
        const struct guest_tree_file_erofs_attach_inputs *input,
        struct guest_tree_mount_scratch before, struct guest_tree_mount_scratch after);

#endif

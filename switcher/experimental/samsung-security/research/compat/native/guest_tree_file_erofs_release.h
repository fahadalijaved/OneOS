#ifndef ONEOS_GUEST_TREE_FILE_EROFS_RELEASE_H
#define ONEOS_GUEST_TREE_FILE_EROFS_RELEASE_H

struct gtfm_owner;
struct guest_tree_file_erofs_attachment;

enum guest_tree_file_erofs_release_phase {
    GUEST_TREE_FILE_EROFS_RELEASE_EMPTY = 0,
    GUEST_TREE_FILE_EROFS_RELEASE_CHECKING,
    GUEST_TREE_FILE_EROFS_RELEASE_CLOSING,
    GUEST_TREE_FILE_EROFS_RELEASE_UNMOUNT_ATTEMPTED,
    GUEST_TREE_FILE_EROFS_RELEASE_UNMOUNT_RETURNED,
    GUEST_TREE_FILE_EROFS_RELEASE_VERIFIED
};

struct guest_tree_file_erofs_release {
    enum guest_tree_file_erofs_release_phase phase;
    int error;
};

/* One call by the dedicated controller after all child/SCM/other mount users
 * have drained. The selected source must exclude namespace, pathname and FD
 * writers continuously through readback. No caller assertion proves this.
 * Use the actual creator and successfully verified attacher from the same
 * stage. The stage, covered-directory and namespace witnesses are borrowed.
 * The creator and the attacher's four same-mount FD cells are consumed only
 * after preflight. A close attempt consumes its cell even on error. Start
 * with a zeroed release record, and retain the phase and errno on failure.
 * Zero proves exact local attached-mount removal and exposure of the held
 * covered directory. The composer owns later witness and backing cleanup. */
int guest_tree_file_erofs_release(struct guest_tree_file_erofs_release *release,
        struct gtfm_owner *creator, struct guest_tree_file_erofs_attachment *attachment,
        int initial_namespace_fd, int current_namespace_fd);

#endif

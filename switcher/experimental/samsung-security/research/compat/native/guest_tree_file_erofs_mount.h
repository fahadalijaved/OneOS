#ifndef ONEOS_GUEST_TREE_FILE_EROFS_MOUNT_H
#define ONEOS_GUEST_TREE_FILE_EROFS_MOUNT_H

#include <stdint.h>

struct gtfm_owner;

struct gtfm_identity {
    uint64_t mount_id, root_inode;
    uint32_t device_major, device_minor;
};

/* One attempt on the dedicated controller process leader. The caller retains
 * the authenticated image and actual proc root FDs throughout creation.
 * Initialize *out to NULL and retain any nonnull owner, including on error. */
int gtfm_create(struct gtfm_owner **out, int verified_image_fd, int proc_fd);

/* Returns the original borrowed fsmount FD, or -1. The caller serializes its
 * use with close and retains any attachment separately. Refusal publishes no
 * new identity or reference. */
int gtfm_borrow_root(struct gtfm_owner *owner, struct gtfm_identity *out);

/* Consume owned descriptors once. Zero acknowledges local descriptor close.
 * The attachment owner independently settles any attached mount. Failed close
 * is sticky. */
int gtfm_close(struct gtfm_owner *owner);

#endif

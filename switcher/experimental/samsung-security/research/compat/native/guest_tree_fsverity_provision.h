#ifndef ONEOS_GUEST_TREE_FSVERITY_PROVISION_H
#define ONEOS_GUEST_TREE_FSVERITY_PROVISION_H

#include <stdint.h>

#define GUEST_TREE_FSVERITY_NEW_NAME ".guest.erofs.new"
#define GUEST_TREE_FSVERITY_FINAL_NAME "guest.erofs"

struct guest_tree_install_guard;
struct guest_tree_fsverity_provision;

struct guest_tree_fsverity_provision_inputs {
    int stage_fd, controller_namespace_fd, feed_fd;
    const struct guest_tree_install_guard *guard;
};

struct guest_tree_fsverity_provision_expected {
    uint64_t bytes;
    unsigned char raw_sha256[32], verity_sha256[32];
};

struct guest_tree_fsverity_provision_identity {
    uint64_t mount_id, inode, size;
    uint32_t dev_major, dev_minor;
    int64_t mtime_sec, ctime_sec;
    uint32_t mtime_nsec, ctime_nsec;
};

enum guest_tree_fsverity_provision_release {
    GTVP_HOLD = 1,
    GTVP_NO_EFFECT_LOCAL_CLOSED = 2,
    GTVP_PUBLISHED_LOCAL_CLOSED = 3
};

/*
 * Strong installer composition prerequisite, supplied by the actual
 * writer owner. Check its same retained exclusive lease and negative,
 * current controller and exact stage identities. It must already exclude
 * stage writers. Do not acquire a replacement lease or accept a receipt
 * or readiness flag. No default implementation exists.
 */
int guest_tree_fsverity_check_install_guard(const struct guest_tree_install_guard *guard,
        int stage_fd, int controller_namespace_fd);

/*
 * One attempt on the dedicated root installer main thread. The expected
 * profile is independently admitted. The borrowed feed is a read-only
 * regular file (read from offset zero), a sole-reader read-only nonblocking
 * pipe, or a connected nonblocking AF_UNIX SOCK_STREAM opened read/write.
 * All feeds require exact EOF. This owner exclusively creates the fixed new leaf,
 * writes only that inode, closes its writer, hashes the staged bytes, and
 * attempts ENABLE once before MEASURE. Initialize *out to NULL. Retain
 * any nonnull owner, even on failure. The real installer guard must stay
 * held. No adoption of an existing leaf or alteration of a published file.
 */
int guest_tree_fsverity_provision_new(const struct guest_tree_fsverity_provision_inputs *input,
        const struct guest_tree_fsverity_provision_expected *expected,
        struct guest_tree_fsverity_provision **out);

/*
 * One same-directory RENAME_NOREPLACE to the fixed final leaf under the
 * actual retained writer guard. Success requires the final named and
 * readable inode, kernel digest, absent temporary leaf, and a successful
 * fsync of the independently opened stage directory. On any failure
 * retain the same owner and guard. No fallback, replacement or rollback.
 */
int guest_tree_fsverity_provision_publish(struct guest_tree_fsverity_provision *owner);

/*
 * Consume local descriptors once. A partial creation, unpublished
 * candidate, unconfirmed effect, or close uncertainty stays in HOLD.
 * NO_EFFECT_LOCAL_CLOSED describes this leaf only. PUBLISHED_LOCAL_CLOSED
 * follows verified publication and successful local close, not guard
 * release. HOLD preserves the first errno. Repeat observes the outcome.
 */
enum guest_tree_fsverity_provision_release
guest_tree_fsverity_provision_close(struct guest_tree_fsverity_provision *owner);

/*
 * Copy the final close-time file observation after PUBLISHED_LOCAL_CLOSED.
 * Returns 0 on success or -1 with a zeroed nonnull output on refusal.
 * The saved identity does not assert current pathname identity or guard release.
 */
int guest_tree_fsverity_provision_published_identity(
        const struct guest_tree_fsverity_provision *owner,
        struct guest_tree_fsverity_provision_identity *out);

/*
 * Read the fixed isolated guest.erofs on the controller thread. Verify the
 * named and held inode, expected length and kernel verity digest, and absence
 * of the temporary leaf. Return identity only after all local descriptors
 * close successfully. Failure returns -1 with a zeroed nonnull output.
 * Uses expected bytes and verity_sha256 only. This point observation
 * acquires no writer guard and reads no payload bytes.
 */
int guest_tree_fsverity_provision_observe_current(
        const struct guest_tree_fsverity_provision_expected *expected,
        struct guest_tree_fsverity_provision_identity *out);

#endif

#ifndef ONEOS_GUEST_PRIVATE_VIEW_OWNER_H
#define ONEOS_GUEST_PRIVATE_VIEW_OWNER_H

#include <stdint.h>

/* Dedicated single-thread, one-shot authored supervisor only; not an Android
 * service/library embedding API. Provider/image authenticity remains external. */
struct gvo_plan {
    int image_witness_fd; /* internal fixed-stage provider, RO regular file */
    int private_data_witness_fd;
};
enum { GVO_HOLD=1, GVO_LOCAL_RELEASED_KERNEL_UNCONFIRMED=3 };

struct gvo_owner;
struct gvo_observation {
    uint64_t namespace_inode;
    uint64_t data_group;
    uint64_t mirror_group;
};

/* V3 begin duplicates witnesses and forks; receive privately adopts seven
 * descriptors: namespace, inherited root, guest root, data, mirror, newly owned
 * guest dev root and its socket directory. Dev/socket are distinct directory
 * objects on one private tmpfs; no device nodes or endpoints are supplied.
 * Copies observations only. Only receive_partial returning 0 means partial
 * filesystem/dev skeleton held, never image/authority/native/launch admission.
 * begin returning 0 means child starting; cancel returning 0 means request only.
 * Errors return -1 with errno.
 * No raw descriptor accessor, caller PID selector, exec or namespace entry API. */
/* A non-NULL *owner must be closed even when begin reports an after-fork error. */
int gvo_begin(const struct gvo_plan *, struct gvo_owner **);
int gvo_receive_partial(struct gvo_owner *, struct gvo_observation *);
int gvo_cancel(struct gvo_owner *);
/* 0: known no-own-configuration refusal closed/reaped only.
 * 3: confirmed AUTO configuration, child reaped and local capabilities closed;
 *    kernel release UNCONFIRMED, permanent metadata tombstone (never full0).
 * 1: HOLD; caller must keep the supervisor alive and may poll close again.
 * -1: cleanup uncertainty, errno set; no descriptor-number retry.
 * Owner is a process-lifetime tombstone; no free/re-begin or foreign waiters. */
int gvo_close(struct gvo_owner *);

#endif

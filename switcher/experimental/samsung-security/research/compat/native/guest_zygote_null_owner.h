#ifndef ONEOS_GUEST_ZYGOTE_NULL_OWNER_H
#define ONEOS_GUEST_ZYGOTE_NULL_OWNER_H

#include "guest_zygote_slot_owner.h"

#include <stdint.h>

enum guest_zygote_null_state {
    GUEST_ZYGOTE_NULL_NEW,
    GUEST_ZYGOTE_NULL_ACQUIRING,
    GUEST_ZYGOTE_NULL_READY,
    GUEST_ZYGOTE_NULL_RETIRED,
    GUEST_ZYGOTE_NULL_CLOSED,
};

struct guest_zygote_null_owner {
    enum guest_zygote_null_state state;
    int fd, close_error;
    int scratch[5];
};

/* Pass a zeroed owner and borrow the exact inherited-root FD and held slot
 * reservations in the exclusive child, before root entry. The caller owns
 * the admitted mount view and excludes concurrent FD and mount changes.
 * READY owns one CLOEXEC null FD above slots 0-4. After acquisition starts,
 * any failure retires the occurrence. Any acquired readable FD remains
 * owned until close, including on refusal. Scratch closes once on unwind. */
int guest_zygote_null_acquire(int inherited_root_fd, uint64_t mount_id,
        const struct guest_zygote_slot_owner *slots, struct guest_zygote_null_owner *owner);

/* Consume the owned descriptors once. A close failure stays sticky and
 * requires child retirement. This never closes the borrowed inputs. */
int guest_zygote_null_close(struct guest_zygote_null_owner *owner);

#endif

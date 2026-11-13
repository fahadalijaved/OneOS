#ifndef ONEOS_GUEST_ZYGOTE_SLOT_OWNER_H
#define ONEOS_GUEST_ZYGOTE_SLOT_OWNER_H

#include "guest_tree_release_owner.h"

struct guest_zygote_control_fds {
    int control;
    int witnesses[GTR_WITNESSES];
};

enum guest_zygote_slot_state {
    GUEST_ZYGOTE_SLOTS_NEW,
    GUEST_ZYGOTE_SLOTS_RESERVING,
    GUEST_ZYGOTE_SLOTS_HELD,
    GUEST_ZYGOTE_SLOTS_RELEASING,
    GUEST_ZYGOTE_SLOTS_RELEASED,
    GUEST_ZYGOTE_SLOTS_RETIRED,
};

struct guest_zygote_slot_owner {
    enum guest_zygote_slot_state state;
    int reserved[5], close_error;
    dev_t device;
    ino_t inode;
};

/* Pass a zeroed owner after the child FD sweep, before preparing the view.
 * The exclusive child owns the four live CLOEXEC cells throughout and uses
 * these same cells after relocation. A partial attempt retains relocated
 * and reserved FDs for child retirement. A failed close is recorded and
 * its consumed numeric slot is never retried. */
int guest_zygote_slots_reserve(struct guest_zygote_control_fds *owned,
        struct guest_zygote_slot_owner *owner);

/* Only after parent acceptance, with all reservations exclusively held.
 * Verify the complete pipe roster before consuming it. On failure retire
 * this child before another open, duplication or attempted release. */
int guest_zygote_slots_release(struct guest_zygote_slot_owner *owner);

#endif

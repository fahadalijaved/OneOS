#ifndef ONEOS_GUEST_ZYGOTE_CHILD_RETAINED_H
#define ONEOS_GUEST_ZYGOTE_CHILD_RETAINED_H

#include "guest_zygote_child_prepare.h"
#include "guest_zygote_slot_owner.h"

/* After the exact child entry is READY, retire its original inherited view
 * FDs and the three relocated witnesses. The caller owns these cells and
 * the exclusive child FD table. Keep control, guest root/dev/socket and
 * slots 0-4 intact. Preflight refusal changes no cell. On a close failure,
 * the failed cell is consumed and remaining cells stay owned through child
 * exit. Do not retry or publish a successful entry on refusal. */
int guest_zygote_retire_inherited_view(struct guest_zygote_control_fds *fds,
        struct gtc_child_view *view, const struct guest_zygote_child_owner *entry);

#endif

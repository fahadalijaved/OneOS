#ifndef ONEOS_GUEST_BINDER_MANAGER_LABEL_VERIFY_H
#define ONEOS_GUEST_BINDER_MANAGER_LABEL_VERIFY_H

#include "guest_binder_manager_handoff.h"

/* Read-only check in the same private pre-exec task as the exact handoff.
 * The source owner must exclude procfs, mount, descriptor, label and actor
 * writers through the whole call. Zero means the two current inode labels
 * and the caller's existing stock manager identity matched. A root launcher
 * or a future exec transition does not meet this check. No driver open,
 * execution permission check, policy transition, spawn or Binder claim. */
int guest_binder_manager_label_verify(struct guest_binder_manager_handoff_owner *handoff);

#endif

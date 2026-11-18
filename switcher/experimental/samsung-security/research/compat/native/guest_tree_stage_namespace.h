#ifndef ONEOS_GUEST_TREE_STAGE_NAMESPACE_H
#define ONEOS_GUEST_TREE_STAGE_NAMESPACE_H

struct gtsn_owner;

struct gtsn_witnesses {
    int initial_namespace_fd;
    int current_namespace_fd;
};

/*
 * One attempt in the dedicated UID 0 controller. The caller supplies a NULL
 * owner slot and retains any published owner even on failure. The controller
 * must remain single-threaded and own all mount changes throughout this use.
 */
int gtsn_enter(struct gtsn_owner **out);

/*
 * Sample the actual current namespace and private mount table again before
 * returning borrowed descriptors. Never close or replace either descriptor.
 * The pair expires at local close; any failed sample cuts off further borrows.
 */
int gtsn_borrow(struct gtsn_owner *owner, struct gtsn_witnesses *out);

/*
 * Use only after local attach/release users finish. Consume both descriptors
 * once. A sticky failure remains a failure after local close. This operation
 * never changes the current namespace or reports that mounts were released.
 */
int gtsn_close_local(struct gtsn_owner *owner);

#endif

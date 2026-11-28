#ifndef ONEOS_GUEST_TREE_FILE_STAGE_H
#define ONEOS_GUEST_TREE_FILE_STAGE_H

struct gtfs_owner;
struct guest_tree_stage_guard;

/* Retain the private controller namespace before opening stage descriptors. */
int gtfs_enter(struct gtfs_owner **out);

/* Create and attach the selected fs-verity-backed mount under this guard. */
int gtfs_mount(struct gtfs_owner *owner, int stage_fd, struct guest_tree_stage_guard *guard);

/* Join the live provider witnesses to the exact mount this owner created. */
int gtfs_check(struct gtfs_owner *owner, int stage_fd, int backing_fd, int tree_fd,
               int namespace_fd, struct guest_tree_stage_guard *guard);

/* Call after the provider has drained its child and closed its mount FDs.
 * Keep the guard until this owner's actual teardown is acknowledged. */
int gtfs_close(struct gtfs_owner *owner);

#endif

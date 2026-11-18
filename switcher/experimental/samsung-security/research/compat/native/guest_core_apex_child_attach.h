#ifndef ONEOS_GUEST_CORE_APEX_CHILD_ATTACH_H
#define ONEOS_GUEST_CORE_APEX_CHILD_ATTACH_H

#include "guest_core_apex_mount_roots.h"

struct guest_core_apex_child_sources;

/* In the dedicated controller before the single selected GTC fork. Consume
 * the genuine mount owner's one loan and retain exact CLOEXEC duplicates.
 * Initialize *out to NULL and retain a published owner even on failure. */
int guest_core_apex_child_sources_prepare(struct guest_core_apex_mount_roots *mounts,
        struct guest_core_apex_child_sources **out);

/* Exact inherited descriptor selector for the fixed child FD restriction.
 * In the one actual direct child, 1 keeps an exact descriptor, 0 grants no
 * keep and -1 refuses. The current selected GTC does not call this API. */
int guest_core_apex_child_sources_keep_in_child(struct guest_core_apex_child_sources *source, int fd);

/* In the original parent, compare a named child sibling to the still-owned
 * detached root after attachment. Zero attests that role and exact mount/inode
 * only. The caller owns the named FD and child lifetime. */
int guest_core_apex_child_sources_match_parent(struct guest_core_apex_child_sources *source,
        enum guest_core_apex_role role, int named_sibling_fd);

/* The actual sole GTC preparation child, with parent-death handling and a
 * fresh private namespace. Rejoin the original prepared tree and scaffold,
 * leave its /apex untouched, and stage the three roots in the same child's
 * private /mnt/gvi/apex-inputs. Failure retains every child-owned reference
 * and possible effect until the real GTC process/namespace drain. */
int guest_core_apex_child_attach(struct guest_core_apex_child_sources *source,
        const struct guest_tree_root_preparation *prepared, int parent_ns, int child_ns,
        struct guest_tree_mount_scratch scratch);

/* One loan, only after full named-FD and mountinfo readback in the original
 * child. All output FD cells must start at -1. Call before publishing or
 * staging final /apex aliases. Existing final APEX checks still apply. */
int guest_core_apex_child_borrow(struct guest_core_apex_child_sources *source,
        struct guest_tree_mount_scratch scratch, struct guest_core_apex_backing out[GCA_COUNT]);

/* Consume only the controller's copy of the nine FD cells once. The actual
 * caller first resolves fork and child drain, and retains the upstream mount,
 * loop, backing and stage owners through their separate release paths. */
int guest_core_apex_child_sources_close(struct guest_core_apex_child_sources *source);

#endif

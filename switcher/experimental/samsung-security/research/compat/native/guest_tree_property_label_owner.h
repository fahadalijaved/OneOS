#ifndef ONEOS_GUEST_TREE_PROPERTY_LABEL_OWNER_H
#define ONEOS_GUEST_TREE_PROPERTY_LABEL_OWNER_H

struct guest_tree_property_child;

/*
 * Pre-effect policy observation for the actual root-only seed in its
 * dedicated fork child. Borrow the live child owner and its same GTC dev
 * descriptor. No labels, modes, mounts or policy are modified.
 *
 * Success samples enforcing SELinux, a non-permissive current actor, and
 * exact relabelfrom/relabelto permissions for the six retained objects plus
 * setattr on the proposed directory label. It is not a permission token.
 * Actual inode mutation still needs transition validation, filesystem
 * association, writer exclusion and a post-transition custody state.
 * On refusal keep the child under its existing cutoff/drain owner.
 */
int guest_tree_property_label_preflight(struct guest_tree_property_child *owner, int dev_fd);

#endif

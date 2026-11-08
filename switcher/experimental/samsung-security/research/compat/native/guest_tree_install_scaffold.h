#ifndef ONEOS_GUEST_TREE_INSTALL_SCAFFOLD_H
#define ONEOS_GUEST_TREE_INSTALL_SCAFFOLD_H

struct guest_tree_install_guard;

/*
 * Read-only readiness check on the dedicated root installer thread, before
 * attaching the carrier. Borrow the actual selected stage and controller
 * namespace from the same live install guard. The caller supplies its
 * existing first-close-error cell. This check calls the install guard's
 * strong currentness gate, creates nothing, and returns no FDs.
 *
 * The selected stage and bin must be protected; backing must be empty;
 * private data has only data/ and user/0/ and both leaves are empty. Every
 * directory below /data belongs to the same writable F2FS mount. The guard
 * owner is responsible for the independent ancestry and writer-exclusion
 * contract. A matching directory profile cannot establish how it was created
 * or authorize adoption. Controller bytes and publication are separate.
 */
int guest_tree_install_scaffold_check(int stage_fd, int controller_namespace_fd,
        const struct guest_tree_install_guard *guard, int *close_error);

#endif

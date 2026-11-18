#ifndef ONEOS_GUEST_BINDER_MANAGER_ENTRY_H
#define ONEOS_GUEST_BINDER_MANAGER_ENTRY_H

#include <sys/stat.h>

#include "guest_binder_attach_owner.h"

enum guest_binder_manager_entry_state {
    GBME_EMPTY = 0, GBME_STARTED, GBME_INPUTS_HELD, GBME_REFUSED, GBME_RETIRED
};

enum guest_binder_manager_entry_node {
    GBME_ROOT = 0, GBME_DEV, GBME_CREATOR_NODE, GBME_BINDER,
    GBME_SYSTEM, GBME_BIN, GBME_BOOTSTRAP, GBME_EXECUTABLE, GBME_INTERPRETER, GBME_NODE_COUNT
};

struct guest_binder_manager_entry_owner {
    enum guest_binder_manager_entry_state state;
    pid_t source_pid, parent_pid;
    int parent_namespace_fd, namespace_fd, close_error;
    int nodes[GBME_NODE_COUNT];
    struct statx identities[GBME_NODE_COUNT];
    int noexec;
};

#define GUEST_BINDER_MANAGER_ENTRY_OWNER_INITIALIZER { \
    .parent_namespace_fd = -1, .namespace_fd = -1, \
    .nodes = {-1, -1, -1, -1, -1, -1, -1, -1, -1} \
}

/* Fixed private child only, before chroot, with its actual original admitted
 * inputs and the retained Binder creator and attachment. The source owner
 * excludes other namespace/descriptor writers. Inputs remain borrowed.
 * One attempt per process. Keep this owner on refusal as well as success.
 * A successful capture holds exact entry bytes and an O_PATH Binder witness.
 * It can describe a NOEXEC preparation root. It opens no Binder client. */
int guest_binder_manager_entry_prepare(struct guest_binder_manager_entry_owner *owner,
        const struct gtc_child_inputs *input, const struct gtc_child_view *view,
        const struct guest_binder_context_owner *created,
        const struct guest_binder_attach_owner *attached);

/* Recheck retained names and ownership at a future pre-spawn boundary.
 * Refuses NOEXEC and poisons the attempt on any check failure. Success is
 * file/namespace identity only. Caller still needs actual launch admission,
 * child/pidfd custody, runtime linkage, policy and positive Binder claim. */
int guest_binder_manager_entry_recheck(struct guest_binder_manager_entry_owner *owner);

/* Local descriptor close only. The creator and mount teardown remain with
 * their original owners. Consume each acquired descriptor once. */
int guest_binder_manager_entry_close(struct guest_binder_manager_entry_owner *owner);

#endif

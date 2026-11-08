#ifndef ONEOS_GUEST_TREE_INSTALL_HOST_PROFILE_H
#define ONEOS_GUEST_TREE_INSTALL_HOST_PROFILE_H

#include <stddef.h>

enum guest_tree_install_host_profile_result {
    GTHP_HOLD = 1,
    GTHP_NO_EFFECT_LOCAL_CLOSED = 2,
    GTHP_PUBLISHED_LOCAL_CLOSED = 3,
    GTHP_ALREADY_MATCHES_LOCAL_CLOSED = 4
};

/* One attempt per dedicated installer process. Input must be the selected
 * immutable 288-byte profile. The installer supplies the genuine host
 * filesystem view. Publication requires anonymous F2FS creation and linkat
 * from the held inode. Results describe local publication only. HOLD retains
 * an uncertain disposition. No retry, rollback or host activation is offered. */
enum guest_tree_install_host_profile_result
guest_tree_install_host_profile(const void *bytes, size_t length);

#endif

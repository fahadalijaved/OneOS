#ifndef ONEOS_GUEST_INSTALLD_ENVIRONMENT_H
#define ONEOS_GUEST_INSTALLD_ENVIRONMENT_H

#include <stddef.h>

/*
 * Fixed paths for the three selected Samsung installd globals, derived from
 * the captured ColorOS init exports and corroborated by the packaged OneOS
 * zygote launcher. A future C caller can initialize its local envp with this
 * list after admitting those paths in the child's actual filesystem view.
 * This list is not a full executable, interpreter or process profile.
 */
#define ONEOS_GUEST_INSTALLD_PATH_ENVIRONMENT { \
    "ANDROID_ROOT=/system", \
    "ANDROID_DATA=/data", \
    "ASEC_MOUNTPOINT=/mnt/asec", \
    NULL \
}

#endif

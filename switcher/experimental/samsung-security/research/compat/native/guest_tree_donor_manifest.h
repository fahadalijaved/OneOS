#ifndef ONEOS_GUEST_TREE_DONOR_MANIFEST_H
#define ONEOS_GUEST_TREE_DONOR_MANIFEST_H

#include "guest_tree_manifest.h"

/* The build embeds the exact reviewed donor manifest as read-only data. */
int guest_tree_open_donor_manifest(struct gtm_manifest *manifest);

#endif

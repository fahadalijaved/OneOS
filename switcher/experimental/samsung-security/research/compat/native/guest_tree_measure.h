#ifndef ONEOS_GUEST_TREE_MEASURE_H
#define ONEOS_GUEST_TREE_MEASURE_H

#include "guest_tree_manifest.h"

/* Full target-content readback of an already held tree. The caller must
 * first exclude writers and mount changes, supply a trusted manifest, and
 * retain those owners across this read and later use. Borrow root_fd.
 * A temporary close failure latches the caller's close_error cell. */
int guest_tree_measure(int root_fd, const struct gtm_manifest *manifest, int *close_error);

#endif

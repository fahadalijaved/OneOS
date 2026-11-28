#ifndef ONEOS_GUEST_TREE_CHILD_VIEW_H
#define ONEOS_GUEST_TREE_CHILD_VIEW_H

#include "guest_tree_control_owner.h"

/* Fixed prepare-only callback for gtc_begin. Pass NULL context. GTC calls it
 * in the exact fork child after limiting inherited descriptors and arming
 * parent-death handling. The provider retains the same source/lease and
 * excludes backing writers throughout. No guest entry or service startup.
 *
 * Witnesses are borrowed. The actual child retains the reported rights and
 * other acquired mount references until its process exits. GTC owns report
 * transport and STOP; the parent must independently admit all seven rights. */
int guest_tree_prepare_child_view(const struct gtc_child_inputs *input,
                                  struct gtc_child_view *view, void *context);

#endif

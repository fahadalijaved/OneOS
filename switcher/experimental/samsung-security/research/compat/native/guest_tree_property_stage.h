#ifndef ONEOS_GUEST_TREE_PROPERTY_STAGE_H
#define ONEOS_GUEST_TREE_PROPERTY_STAGE_H

#include "guest_tree_control_owner.h"

enum guest_tree_property_seed_role {
    GTP_SEED_INFO, GTP_SEED_BUILD, GTP_SEED_DEFAULT, GTP_SEED_VNDK, GTP_SEED_SERIAL,
    GTP_SEED_COUNT
};

/*
 * One attempt in the actual, dedicated GTC fork child after preparing its
 * empty private dev/socket skeleton and before reporting rights or exec.
 * Borrow its actual input/view and the five regular seed FDs in role order.
 * The function checks exact seed bytes and owns every destination writer.
 *
 * Initialize *property_dir to -1. On success it owns an O_PATH directory FD
 * for the fixed root-only __properties__ seed. A refusal after mkdir may
 * leave private files. Keep the child/namespace under its owner through
 * drain; never retry in the same child or delete by an external pathname.
 *
 * This stages bytes only. The current seven-role profile does not admit
 * the additional directory. A future caller must also establish the
 * actual labels/access, complete property values and writer lifecycle
 * before starting any original process.
 */
int guest_tree_stage_property_seed(const struct gtc_child_inputs *input,
        const struct gtc_child_view *view, const int seeds[GTP_SEED_COUNT], int *property_dir);

#endif

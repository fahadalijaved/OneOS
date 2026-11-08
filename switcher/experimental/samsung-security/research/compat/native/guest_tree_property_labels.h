#ifndef ONEOS_GUEST_TREE_PROPERTY_LABELS_H
#define ONEOS_GUEST_TREE_PROPERTY_LABELS_H

/*
 * Read-only check after the dedicated caller enters its actual guest root,
 * before any original binary starts. Borrow the genuine retained private dev
 * and its staged property directory, supplied by their live owner. That owner
 * must exclude namespace, pathname, label and byte writers for this check and
 * the later use. The caller must use the exact intended read credentials.
 *
 * Zero proves these five source-seeded files match labels, DAC, bytes, and
 * read/map access for this invocation. The launch owner still owes actual
 * exec credentials/domain, effective property population and writer service.
 * A refusal is terminal for this pre-exec child. Retain and drain the child
 * on failure, including uncertain mapping or descriptor cleanup.
 * This does not change labels, DAC, namespace, environment or policy.
 */
int guest_tree_verify_property_labels(int dev_fd, int property_dir_fd);

#endif

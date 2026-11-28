#ifndef ONEOS_GUEST_TREE_APEX_PHASE_WIRE_H
#define ONEOS_GUEST_TREE_APEX_PHASE_WIRE_H

#include <stddef.h>
#include <stdint.h>

#include "guest_tree_control_owner.h"

#define GTAW_MAGIC UINT32_C(0x47545035)
#define GTAW_VERSION UINT32_C(5)
#define GTAW_PACKET_BYTES 200

enum gtaw_kind {
    GTAW_PARTIAL = 1,
    GTAW_ERROR = 2,
    GTAW_CANCEL = 3,
    GTAW_ATTACH_CORE_APEX = 4,
    GTAW_CORE_APEX_PARTIAL = 5
};
enum { GTAW_REQUEST_STAGE = 0, GTAW_READBACK_STAGE = 11 };

struct gtaw_peer {
    int32_t pid;
    uint32_t uid, gid;
};

/* Same fixed GTC shape. Only the base tree view can appear in view. */
struct gtaw_packet {
    uint32_t magic, version, kind, stage;
    int32_t error, pid;
    uint32_t uid, gid;
    struct gtc_observation view;
    uint64_t image_dev, image_inode, loop_device;
    uint32_t loop_number, loop_flags;
    uint64_t reserved[2];
};

enum gtaw_state {
    GTAW_UNUSED = 0, GTAW_PARENT_PENDING, GTAW_CHILD_PENDING, GTAW_FINISHED, GTAW_REFUSED
};

/* A private, zero-initialized cell in each endpoint of the same GTC attempt.
 * Never copy or reset a claimed cell. Failure is sticky. */
struct gtaw_phase {
    enum gtaw_state state;
    struct gtc_observation base;
};

/* Original PARTIAL/ERROR/CANCEL envelope only. The caller owns the original
 * kind-specific fields and associated rights handling. */
int gtaw_init_packet(struct gtaw_packet *out, enum gtaw_kind kind, uint32_t stage,
                     struct gtaw_peer sender);

/* Envelope check after actual recvmsg/SCM_CREDENTIALS validation. The expected
 * tuple is from the same retained GTC occurrence, not the packet. The caller
 * owns truncation, ancillary validation, descriptor closure and deadlines. */
int gtaw_validate_header(const struct gtaw_packet *packet, size_t bytes, struct gtaw_peer expected);

/* Parent only, after full initial view verification and actual GTR adoption.
 * Claims the request before returning bytes to the caller's one send. A send
 * failure, timeout, or lost reply requires abort and the same owner cutoff. */
int gtaw_parent_prepare(struct gtaw_phase *phase, const struct gtc_observation *base,
                        struct gtaw_peer sender, struct gtaw_packet *out);
int gtaw_parent_accept(struct gtaw_phase *phase, const struct gtaw_packet *packet, size_t bytes,
                       size_t rights, struct gtaw_peer expected);

/* Child only, after initial PARTIAL on the same control endpoint. Accepts
 * one authenticated zero-rights request. Only successful real local action
 * permits a reply, with the exact previously retained base observation. */
int gtaw_child_accept(struct gtaw_phase *phase, const struct gtaw_packet *packet, size_t bytes,
                      size_t rights, struct gtaw_peer expected, const struct gtc_observation *base);
int gtaw_child_reply(struct gtaw_phase *phase, struct gtaw_peer sender, struct gtaw_packet *out);

void gtaw_abort(struct gtaw_phase *phase);

#endif

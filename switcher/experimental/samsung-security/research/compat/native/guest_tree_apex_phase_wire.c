#include "guest_tree_apex_phase_wire.h"

#include <errno.h>
#include <string.h>

_Static_assert(__BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__, "GTC v5 wire byte order");
_Static_assert(GTR_VIEW_RIGHTS == 7 && sizeof(struct gtc_observation) == 120,
               "GTC v5 base observation layout");
_Static_assert(sizeof(struct gtaw_packet) == GTAW_PACKET_BYTES
               && offsetof(struct gtaw_packet, stage) == 12
               && offsetof(struct gtaw_packet, error) == 16
               && offsetof(struct gtaw_packet, pid) == 20
               && offsetof(struct gtaw_packet, view) == 32
               && offsetof(struct gtaw_packet, image_dev) == 152
               && offsetof(struct gtaw_packet, loop_number) == 176
               && offsetof(struct gtaw_packet, reserved) == 184, "GTC v5 wire layout");

static int refuse(int error) {
    errno = error;
    return -1;
}

static void init_packet(struct gtaw_packet *out, enum gtaw_kind kind, uint32_t stage,
                        struct gtaw_peer sender) {
    memset(out, 0, sizeof(*out));
    out->magic = GTAW_MAGIC;
    out->version = GTAW_VERSION;
    out->kind = kind;
    out->stage = stage;
    out->pid = sender.pid;
    out->uid = sender.uid;
    out->gid = sender.gid;
}

int gtaw_init_packet(struct gtaw_packet *out, enum gtaw_kind kind, uint32_t stage,
                     struct gtaw_peer sender) {
    if (!out || sender.pid <= 0 || kind < GTAW_PARTIAL || kind > GTAW_CANCEL) return refuse(EINVAL);
    init_packet(out, kind, stage, sender);
    return 0;
}

int gtaw_validate_header(const struct gtaw_packet *packet, size_t bytes, struct gtaw_peer expected) {
    if (!packet || bytes != GTAW_PACKET_BYTES || expected.pid <= 0
            || packet->magic != GTAW_MAGIC || packet->version != GTAW_VERSION
            || packet->kind < GTAW_PARTIAL || packet->kind > GTAW_CORE_APEX_PARTIAL
            || packet->pid != expected.pid || packet->uid != expected.uid || packet->gid != expected.gid
            || packet->image_dev || packet->image_inode || packet->loop_device
            || packet->loop_number || packet->loop_flags || packet->reserved[0] || packet->reserved[1])
        return refuse(EPROTO);
    return 0;
}

static int valid_base(const struct gtc_observation *view) {
    if (!view || !view->namespace_inode || !view->namespace_dev || view->mounts[GTC_NAMESPACE]
            || !view->data_group || !view->mirror_group || view->data_group == view->mirror_group
            || !view->alias_native || !view->alias_guest || view->alias_native == view->alias_guest
            || !view->guest_data_mount || !view->guest_mirror_mount) return 0;
    for (size_t index = 1; index < GTR_VIEW_RIGHTS; ++index) if (!view->mounts[index]) return 0;
    return 1;
}

static int claim(struct gtaw_phase *phase, enum gtaw_state expected) {
    if (!phase) return refuse(EINVAL);
    enum gtaw_state previous = phase->state;
    phase->state = GTAW_REFUSED;
    return previous == expected ? 0 : refuse(EPROTO);
}

int gtaw_parent_prepare(struct gtaw_phase *phase, const struct gtc_observation *base,
                        struct gtaw_peer sender, struct gtaw_packet *out) {
    if (claim(phase, GTAW_UNUSED) < 0) return -1;
    if (!out || sender.pid <= 0 || !valid_base(base)) return refuse(EINVAL);
    phase->base = *base;
    init_packet(out, GTAW_ATTACH_CORE_APEX, GTAW_REQUEST_STAGE, sender);
    phase->state = GTAW_PARENT_PENDING;
    return 0;
}

int gtaw_parent_accept(struct gtaw_phase *phase, const struct gtaw_packet *packet, size_t bytes,
                       size_t rights, struct gtaw_peer expected) {
    if (claim(phase, GTAW_PARENT_PENDING) < 0) return -1;
    if (gtaw_validate_header(packet, bytes, expected) < 0) return -1;
    if (rights || packet->kind != GTAW_CORE_APEX_PARTIAL || packet->stage != GTAW_READBACK_STAGE
            || packet->error || memcmp(&packet->view, &phase->base, sizeof(phase->base)))
        return refuse(EPROTO);
    phase->state = GTAW_FINISHED;
    return 0;
}

int gtaw_child_accept(struct gtaw_phase *phase, const struct gtaw_packet *packet, size_t bytes,
                      size_t rights, struct gtaw_peer expected, const struct gtc_observation *base) {
    static const struct gtc_observation zero;
    if (claim(phase, GTAW_UNUSED) < 0) return -1;
    if (gtaw_validate_header(packet, bytes, expected) < 0) return -1;
    if (rights || packet->kind != GTAW_ATTACH_CORE_APEX || packet->stage != GTAW_REQUEST_STAGE
            || packet->error || memcmp(&packet->view, &zero, sizeof(zero))) return refuse(EPROTO);
    if (!valid_base(base)) return refuse(EINVAL);
    phase->base = *base;
    phase->state = GTAW_CHILD_PENDING;
    return 0;
}

int gtaw_child_reply(struct gtaw_phase *phase, struct gtaw_peer sender, struct gtaw_packet *out) {
    if (claim(phase, GTAW_CHILD_PENDING) < 0) return -1;
    if (!out || sender.pid <= 0) return refuse(EINVAL);
    init_packet(out, GTAW_CORE_APEX_PARTIAL, GTAW_READBACK_STAGE, sender);
    out->view = phase->base;
    phase->state = GTAW_FINISHED;
    return 0;
}

void gtaw_abort(struct gtaw_phase *phase) {
    if (phase) phase->state = GTAW_REFUSED;
}

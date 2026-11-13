"""Compose the unselected GTC slot-release phase from the reservation build."""

from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "out/guest-zygote-slot-control-build/r-34951002"
BASE_RECEIPT = "9987e3c0822aabc0915439704eee210e0e710b131da859d316bee14e15cd303a"
BASE_CONTROL = "951810c61c539b6cacc347531109dda5989fdc1943bf11a3d37c05a3e4c7ff84"

CHILD = """static int slot_phase_timeout(uint64_t deadline) {
    uint64_t now;
    if (now_ms(&now) < 0) return -1;
    if (now >= deadline) { errno = ETIMEDOUT; return -1; }
    uint64_t remaining = deadline - now;
    return (int)(remaining < 100 ? remaining : 100);
}

static int release_child_slots(int control, struct guest_zygote_slot_owner *slots,
                               const struct gtc_observation *base, struct gtc_wire *packet) {
    struct gtc_observation empty = {0};
    if (packet->kind != W_RELEASE_SLOTS || packet->stage || packet->error
            || memcmp(&packet->view, &empty, sizeof(empty)) || slots->state != GUEST_ZYGOTE_SLOTS_HELD) {
        errno = EPROTO;
        return -1;
    }
    if (getppid() != one.parent) { errno = ECHILD; return -1; }
    if (slot_phase_timeout(one.deadline) < 0) return -1;
    if (guest_zygote_slots_release(slots) < 0) {
        int error = errno;
        init_wire(packet, W_ERROR, S_SLOT_RELEASE);
        packet->error = error > 0 && error < 4096 ? error : EPROTO;
        if (getppid() == one.parent && slot_phase_timeout(one.deadline) > 0)
            (void)send_wire(control, packet, NULL);
        errno = error;
        return -1;
    }
    if (getppid() != one.parent) { errno = ECHILD; return -1; }
    if (slot_phase_timeout(one.deadline) < 0) return -1;
    init_wire(packet, W_SLOTS_RELEASED, S_READBACK);
    packet->view = *base;
    return send_wire(control, packet, NULL);
}

"""

PARENT = """static int slot_child_live(struct gtc_owner *owner) {
    int live = gtr_child_live(owner->release);
    if (live == 1) return 0;
    if (!live) errno = ECHILD;
    return -1;
}

static int confirm_slot_release(struct gtc_owner *owner) {
    struct gtc_wire reply;
    if (slot_child_live(owner) < 0 || slot_phase_timeout(owner->deadline) < 0) return -1;
    init_wire(&reply, W_RELEASE_SLOTS, 0);
    if (send_wire(owner->control, &reply, NULL) < 0) return -1;
    for (;;) {
        if (slot_child_live(owner) < 0) {
            if (errno == EINTR && slot_phase_timeout(owner->deadline) > 0) continue;
            return -1;
        }
        int timeout = slot_phase_timeout(owner->deadline);
        if (timeout < 0) return -1;
        struct pollfd p = {owner->control, POLLIN | POLLRDHUP, 0};
        int ready = poll(&p, 1, timeout);
        if (ready < 0 && errno == EINTR) continue;
        if (ready < 0) return -1;
        if (!ready) continue;
        if (!(p.revents & POLLIN) || p.revents & (POLLERR | POLLHUP | POLLNVAL | POLLRDHUP)) {
            errno = EPIPE;
            return -1;
        }
        if (slot_phase_timeout(owner->deadline) < 0) return -1;
        int rights[MAX_RIGHTS];
        size_t count;
        int received = receive_wire(owner->control, &reply, rights, &count, owner->child,
                                    owner->uid, owner->gid, &owner->close_error);
        int primary = errno;
        close_received(rights, count, &owner->close_error);
        if (count || owner->close_error) { errno = EPROTO; return -1; }
        if (received < 0) {
            if (primary == EAGAIN || primary == EINTR) continue;
            errno = primary;
            return -1;
        }
        if (slot_phase_timeout(owner->deadline) < 0) return -1;
        struct gtc_observation empty = {0};
        if (reply.kind == W_ERROR && reply.stage == S_SLOT_RELEASE && reply.error > 0
                && reply.error < 4096 && !memcmp(&reply.view, &empty, sizeof(empty))) {
            errno = reply.error;
            return -1;
        }
        if (reply.kind != W_SLOTS_RELEASED || reply.stage != S_READBACK || reply.error
                || memcmp(&reply.view, &owner->slot_base, sizeof(owner->slot_base))) {
            errno = EPROTO;
            return -1;
        }
        if (slot_child_live(owner) < 0 || slot_phase_timeout(owner->deadline) < 0) return -1;
        return 0;
    }
}

int gtc_release_startup_slots(struct gtc_owner *owner) {
    if (enter_owner(owner) < 0) return -1;
    if (!owner->held || owner->cutoff || owner->close_error || owner->slot_release_attempted) {
        leave();
        errno = EBUSY;
        return -1;
    }
    owner->slot_release_attempted = 1;
    int result = confirm_slot_release(owner);
    if (result < 0) {
        int primary = errno ? errno : EIO;
        (void)request_stop(owner);
        errno = primary;
    }
    leave();
    return result;
}

"""


def overlay(raw, pairs):
    newline = b"\r\n" if b"\r\n" in raw else b"\n"
    encoded = [(a.encode("ascii").replace(b"\n", newline), b.encode("ascii").replace(b"\n", newline))
               for a, b in pairs]
    changed = raw
    for before, after in encoded:
        if changed.count(before) != 1 or after in changed:
            raise ValueError(f"Unexpected slot-release overlay anchor {before!r}")
        changed = changed.replace(before, after, 1)
    restored = changed
    for before, after in reversed(encoded):
        if restored.count(after) != 1:
            raise ValueError(f"Unexpected slot-release inverse anchor {after!r}")
        restored = restored.replace(after, before, 1)
    if restored != raw:
        raise ValueError("Slot-release overlay inverse differs from the reservation source")
    return changed


def controller(raw):
    before_child = "static _Noreturn void run_child("
    before_parent = "int gtc_observed_child_birth("
    adoption = "        owner->held = 1;"
    old_cancel = """        if (result < 0 || count || close_error || packet.kind != W_CANCEL || packet.stage || packet.error
                || memcmp(&packet.view, &empty, sizeof(empty))) _exit(2);
        break;"""
    new_cancel = """        if (result < 0 || count || close_error) _exit(2);
        if (packet.kind == W_CANCEL) {
            if (packet.stage || packet.error || memcmp(&packet.view, &empty, sizeof(empty))) _exit(2);
            break;
        }
        if (release_child_slots(control, &launch_slots, &view.observation, &packet) < 0) _exit(2);"""
    return overlay(raw, [
        ("0x47564f33", "0x47545336"), ("packet->version = 3", "packet->version = 6"),
        ("packet->version != 3", "packet->version != 6"),
        ("Exact private GVO v3 shape", "Private GTS v6 slot-release shape"),
        ("GVO v3 wire layout", "GTS v6 wire layout"),
        ("W_CANCEL = 3 }", "W_CANCEL = 3, W_RELEASE_SLOTS = 4, W_SLOTS_RELEASED = 5 }"),
        ("S_IPC = 12,", "S_IPC = 12, S_SLOT_RELEASE = 13,"),
        ("    uint64_t deadline, kill_at;", """    int slot_release_attempted;
    struct gtc_observation slot_base;
    uint64_t deadline, kill_at;"""),
        (before_child, CHILD + before_child),
        ("        struct pollfd pollfd = {control, POLLIN, 0};\n        int ready = poll(&pollfd, 1, 250);",
         """        struct pollfd pollfd = {control, POLLIN | POLLRDHUP, 0};
        int timeout = launch_slots.state == GUEST_ZYGOTE_SLOTS_HELD
                ? slot_phase_timeout(one.deadline) : 250;
        if (timeout < 0) _exit(2);
        int ready = poll(&pollfd, 1, timeout);"""),
        ("        if (ready < 0 || !(pollfd.revents & POLLIN)) break;",
         """        if (ready < 0 || !(pollfd.revents & POLLIN)
                || pollfd.revents & (POLLERR | POLLHUP | POLLNVAL | POLLRDHUP)) break;"""),
        (old_cancel, new_cancel), (before_parent, PARENT + before_parent),
        (adoption, adoption + "\n        owner->slot_base = packet.view;"),
    ])


def provider(raw):
    publish = """    if (gtc_receive_partial(owner->control, &actual) < 0) goto done;
    if (admit_current(owner) < 0) {
        owner->source_error = errno ? errno : EIO;
        goto done;
    }
    *observed = actual;"""
    return overlay(raw, [(publish, publish.replace("    *observed = actual;", """    if (gtc_release_startup_slots(owner->control) < 0) goto done;
    if (admit_current(owner) < 0) {
        owner->source_error = errno ? errno : EIO;
        goto done;
    }
    *observed = actual;"""))])


def main():
    receipt = (BASE / "receipt.json").read_bytes()
    if sha256(receipt).hexdigest() != BASE_RECEIPT:
        raise ValueError("Pinned reservation overlay receipt changed")
    pins = json.loads(receipt.decode("utf-8-sig"))["sourcePins"]
    control_name = "guest_tree_control_owner.c"
    header_name = "guest_tree_control_owner.h"
    provider_name = "guest_tree_stage_provider.c"
    anchor = "int gtc_receive_partial(struct gtc_owner *owner, struct gtc_observation *observed);"
    inputs = {name: (BASE / "src" / name).read_bytes() for name in (control_name, header_name, provider_name)}
    expected = {**pins, control_name: BASE_CONTROL}
    if any(sha256(data).hexdigest() != expected[name] for name, data in inputs.items()):
        raise ValueError("Pinned reservation overlay source changed")
    outputs = {
        control_name: controller(inputs[control_name]),
        header_name: overlay(inputs[header_name], [(anchor, anchor + """

/* Research variant only. Call after the stage provider re-admits the
 * source for the adopted Partial. No retry after a send attempt. */
int gtc_release_startup_slots(struct gtc_owner *owner);""")]),
        provider_name: provider(inputs[provider_name]),
    }
    run = ROOT / "out/guest-zygote-slot-phase-source" / f"r-{uuid4().hex[:8]}"
    run.mkdir(parents=True)
    for name, data in outputs.items():
        (run / name).write_bytes(data)
    result = {
        "schema": 1, "status": "PASS_EXACT_SLOT_RELEASE_SOURCE_OVERLAY",
        "selected": False, "deviceEligible": False, "targetExecuted": False,
        "inverse": True, "baseReceipt": BASE_RECEIPT, "wireVersion": 6,
        "inputs": {name: expected[name] for name in inputs},
        "sources": {name: sha256(data).hexdigest() for name, data in outputs.items()},
    }
    (run / "receipt.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(run)


if __name__ == "__main__":
    main()

"""Bind the child's actual baseline FDs to the unselected parent readback."""

from hashlib import sha256
import json
from uuid import uuid4

from check_guest_tree_materialization_plan import read_small
from compose_guest_zygote_slot_release import ROOT, overlay


BASE = ROOT / "out/guest-zygote-linkerconfig-parent-build/r-c7dcc550"
BASE_RECEIPT = "82edfab1e37559308cb38376b9d4bd616e34679614796fe748e0677bf9378b4b"
ADMITTED_ARGS = "        const struct gtc_observation *admitted, int *close_error)"
BORROWED_ARGS = "        const struct gtc_observation *admitted, int directory_fd, int base_fd, int *close_error)"


def controller(raw):
    version = "packet->version"
    version_comment = "/* Private GTZ v7 child-preparation shape."
    send = """    if (rights) {
        memset(&control, 0, sizeof(control));
        message.msg_control = control.bytes;
        message.msg_controllen = sizeof(control.bytes);"""
    send_sizes = """        c->cmsg_len = CMSG_LEN(GTR_VIEW_RIGHTS * sizeof(int));
        memcpy(CMSG_DATA(c), rights, GTR_VIEW_RIGHTS * sizeof(int));"""
    child_end = """    init_wire(packet, W_CHILD_PREPARED, S_READBACK);
    packet->view = view->observation;
    return send_wire(control, packet, NULL);"""
    before_receive = "static int confirm_child_prepared(struct gtc_owner *owner) {"
    check_reply = """static int verify_prepared_reply(struct gtc_owner *owner, const struct gtc_wire *reply,
        const int *rights, size_t count) {
    if (owner->close_error) { errno = owner->close_error; return -1; }
    if (slot_phase_timeout(owner->deadline) < 0) return -1;
    struct gtc_observation empty = {0};
    if (reply->kind == W_ERROR && count == 0 && reply->stage == S_CHILD_PREPARE
            && reply->error > 0 && reply->error < 4096 && !memcmp(&reply->view, &empty, sizeof(empty))) {
        errno = reply->error;
        return -1;
    }
    if (reply->kind != W_CHILD_PREPARED || count != PREPARED_RIGHTS || reply->stage != S_READBACK
            || reply->error || memcmp(&reply->view, &owner->slot_base, sizeof(owner->slot_base))) {
        errno = EPROTO;
        return -1;
    }
    return gtr_verify_prepared_child(owner->release, &owner->slot_base,
            rights[PREPARED_DIRECTORY], rights[PREPARED_BASE], &owner->close_error);
}

"""
    old_receive = """        int primary = errno;
        close_received(rights, count, &owner->close_error);
        if (count || owner->close_error) { errno = EPROTO; return -1; }
        if (received < 0) {
            if (primary == EAGAIN || primary == EINTR) continue;
            errno = primary;
            return -1;
        }
        if (slot_phase_timeout(owner->deadline) < 0) return -1;
        struct gtc_observation empty = {0};
        if (reply.kind == W_ERROR && reply.stage == S_CHILD_PREPARE && reply.error > 0
                && reply.error < 4096 && !memcmp(&reply.view, &empty, sizeof(empty))) {
            errno = reply.error;
            return -1;
        }
        if (reply.kind != W_CHILD_PREPARED || reply.stage != S_READBACK || reply.error
                || memcmp(&reply.view, &owner->slot_base, sizeof(owner->slot_base))) {
            errno = EPROTO;
            return -1;
        }
        if (slot_child_live(owner) < 0 || slot_phase_timeout(owner->deadline) < 0) return -1;
        if (gtr_verify_prepared_child(owner->release, &owner->slot_base, &owner->close_error) < 0
                || slot_phase_timeout(owner->deadline) < 0) return -1;
        return 0;"""
    return overlay(raw, [
        ("#define GTC_MAGIC UINT32_C(0x47545a37)", "#define GTC_MAGIC UINT32_C(0x47545a38)"),
        (version + " = 7;", version + " = 8;"),
        (version + " != 7", version + " != 8"),
        (version_comment, version_comment.replace("v7", "v8")),
        ('"GTZ v7 wire layout"', '"GTZ v8 wire layout"'),
        ("enum { S_PRIVATE = 2,", "enum { PREPARED_DIRECTORY, PREPARED_BASE, PREPARED_RIGHTS };\n"
         "enum { S_PRIVATE = 2,"),
        (send, """    size_t count = 0;
    if (packet->kind == W_PARTIAL) count = GTR_VIEW_RIGHTS;
    else if (packet->kind == W_CHILD_PREPARED) count = PREPARED_RIGHTS;
    if ((rights != NULL) != (count != 0)) { errno = EINVAL; return -1; }
    if (count) {
        memset(&control, 0, sizeof(control));
        message.msg_control = control.bytes;
        message.msg_controllen = CMSG_SPACE(count * sizeof(int));"""),
        (send_sizes, """        c->cmsg_len = CMSG_LEN(count * sizeof(int));
        memcpy(CMSG_DATA(c), rights, count * sizeof(int));"""),
        ("if (bytes % sizeof(int)) bad = 1;", "if (!bytes || bytes % sizeof(int)) bad = 1;"),
        (child_end, """    int rights[PREPARED_RIGHTS] = {target->directory_fd, target->base_fd};
    if (target->root_fd != view->rights[GTC_GUEST_ROOT] || rights[PREPARED_DIRECTORY] == rights[PREPARED_BASE]) {
        errno = EPROTO;
        return -1;
    }
    for (size_t i = 0; i < PREPARED_RIGHTS; ++i) {
        if (rights[i] < 5 || rights[i] == control || rights[i] == view->rights[GTC_GUEST_ROOT]
                || rights[i] == view->rights[GTC_DEV] || rights[i] == view->rights[GTC_SOCKET]) {
            errno = EPROTO;
            return -1;
        }
        int flags = fcntl(rights[i], F_GETFD);
        if (flags < 0) return -1;
        if (!(flags & FD_CLOEXEC)) { errno = EPERM; return -1; }
    }
    init_wire(packet, W_CHILD_PREPARED, S_READBACK);
    packet->view = view->observation;
    return send_wire(control, packet, rights);"""),
        (before_receive, check_reply + before_receive),
        (old_receive, """        int result = received < 0 ? -1 : verify_prepared_reply(owner, &reply, rights, count);
        int primary = result < 0 ? (errno ? errno : EIO) : 0;
        close_received(rights, count, &owner->close_error);
        if (primary) {
            if (received < 0 && !count && !owner->close_error && (primary == EAGAIN || primary == EINTR)) continue;
            errno = primary;
            return -1;
        }
        if (owner->close_error) { errno = owner->close_error; return -1; }
        if (slot_child_live(owner) < 0 || slot_phase_timeout(owner->deadline) < 0) return -1;
        return 0;"""),
    ])


def release_owner(raw):
    call = "owner->rights[GTC_NAMESPACE], admitted, close_error) < 0"
    return overlay(raw, [
        (ADMITTED_ARGS, BORROWED_ARGS),
        (call, "owner->rights[GTC_NAMESPACE], admitted, directory_fd, base_fd, close_error) < 0"),
    ])


def parent_reader(raw):
    call = "guest_linkerconfig_parent_readback(fd[LIVE_ROOT], fd[TASK], &proc, close_error) < 0"
    return overlay(raw, [
        (ADMITTED_ARGS, BORROWED_ARGS),
        (call, "guest_linkerconfig_parent_readback(fd[LIVE_ROOT], fd[TASK], &proc,\n"
         "                directory_fd, base_fd, close_error) < 0"),
    ])


def role_header(raw):
    return overlay(raw, [(ADMITTED_ARGS, BORROWED_ARGS)])


def main():
    prior = json.loads(read_small(BASE / "receipt.json", 192 * 1024, BASE_RECEIPT))
    transforms = {
        "guest_tree_control_owner.c": controller,
        "guest_tree_release_owner.c": release_owner,
        "guest_tree_release_owner.h": role_header,
        "guest_zygote_parent_readback.c": parent_reader,
        "guest_zygote_parent_readback.h": role_header,
    }
    inputs = {name: prior["sourcePins"][name] for name in transforms}
    outputs = {
        name: transform(read_small(BASE / "src" / name, 64 * 1024, inputs[name]))
        for name, transform in transforms.items()
    }
    run = ROOT / "out/guest-zygote-linkerconfig-rights-source" / f"r-{uuid4().hex[:8]}"
    run.mkdir(parents=True)
    for name, data in outputs.items():
        (run / name).write_bytes(data)
    receipt = {
        "schema": 1, "status": "PASS_EXACT_CHILD_LINKERCONFIG_RIGHTS_OVERLAY",
        "baseReceiptSha256": BASE_RECEIPT, "inputs": inputs,
        "sources": {name: sha256(data).hexdigest() for name, data in outputs.items()},
        "inverse": True, "wireVersion": 8, "preparedRights": 2, "selected": False,
        "deviceEligible": False, "targetExecuted": False,
    }
    (run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(run)


if __name__ == "__main__":
    main()

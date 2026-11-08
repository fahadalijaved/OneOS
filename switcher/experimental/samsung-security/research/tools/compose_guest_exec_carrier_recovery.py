"""Carry verified early preparation cleanup through the research guard."""

from hashlib import sha256
import json
from uuid import uuid4

from check_guest_tree_materialization_plan import read_small
from compose_guest_zygote_slot_release import ROOT, overlay


BASE = ROOT / "out/guest-exec-carrier-bootstrap-loader-build/r-18273101"
BASE_RECEIPT = "4eaae9488fc14fd271f8cb3cba129ab1b314a0afd4a9ae4c16338a1c2c147278"
ENTRY = ROOT / "out/guest-exec-carrier-entry-source/r-454ce3b3"
ENTRY_RECEIPT = "11e6894062173301ff71d0eb3935e5f247319c20527b4b79edfde9ec436e4156"
MAIN = "retained_root_handoff.c"
POLL = "int guest_tree_stage_guard_poll_control(struct guest_tree_stage_guard *guard)"
TYPED_POLL = """int guest_tree_stage_guard_poll_control(struct guest_tree_stage_guard *guard,
        enum gtr_release *terminal)"""


def controller(raw):
    initial_receive = """        if (live != 1) {
            if (live < 0 && errno == EINTR) continue;
            if (live == 0) errno = ECHILD;
            break;
        }
        struct pollfd p = {owner->control, POLLIN, 0};
        uint64_t remaining = owner->deadline - now;
        int ready = poll(&p, 1, (int)(remaining < 100 ? remaining : 100));
        if (ready < 0 && errno == EINTR) continue;
        if (ready < 0) break;
        if (!ready) continue;
        if (!(p.revents & POLLIN)) { errno = EPIPE; break; }
        if (receive_wire(owner->control, &packet, rights, &count, owner->child,
                         owner->uid, owner->gid, &owner->close_error) < 0) {
            if (!count && (errno == EAGAIN || errno == EINTR)) continue;
            break;
        }"""
    verified = """        if (guest_tree_verify_remaining_view(owner->child, owner->witness, rights, &packet.view,
                                             &owner->close_error) != 0 || owner->close_error) break;"""
    return overlay(raw, [
        ("int cutoff, close_error, stop_error, held, receive_attempted, kill_due;",
         "int cutoff, close_error, stop_error, held, receive_attempted, kill_due;\n"
         "    int early_local_proved;"),
        ("pid_t pid, uid_t uid, gid_t gid, int *close_error) {",
         "pid_t pid, uid_t uid, gid_t gid, int *close_error, int *clean_eof) {"),
        ("    *count = 0;\n    ssize_t length = recvmsg",
         "    *count = 0;\n    if (clean_eof) *clean_eof = 0;\n    ssize_t length = recvmsg"),
        ("    if (length < 0) return -1;\n    int bad",
         """    if (length < 0) return -1;
    if (!length && !message.msg_controllen && !(message.msg_flags & (MSG_TRUNC | MSG_CTRUNC))) {
        if (clean_eof) *clean_eof = 1;
        errno = EPIPE;
        return -1;
    }
    int bad"""),
        ("one.parent, one.uid, one.gid, &close_error);",
         "one.parent, one.uid, one.gid, &close_error, NULL);"),
        (initial_receive, """        if (live < 0) {
            if (errno == EINTR) continue;
            break;
        }
        if (live > 0) {
            struct pollfd p = {owner->control, POLLIN | POLLRDHUP, 0};
            uint64_t remaining = owner->deadline - now;
            int ready = poll(&p, 1, (int)(remaining < 100 ? remaining : 100));
            if (ready < 0 && errno == EINTR) continue;
            if (ready < 0) break;
            if (!ready) continue;
            if (!(p.revents & (POLLIN | POLLHUP | POLLRDHUP)) || (p.revents & (POLLERR | POLLNVAL))) {
                errno = EPIPE;
                break;
            }
        }
        /* An exact reap can leave a packet and rights queued on our endpoint. */
        int clean_eof;
        if (receive_wire(owner->control, &packet, rights, &count, owner->child,
                         owner->uid, owner->gid, &owner->close_error, &clean_eof) < 0) {
            if (!count && !owner->close_error) {
                if (clean_eof) owner->early_local_proved = 1;
                else if (errno == EINTR || (live > 0 && errno == EAGAIN)) continue;
            }
            break;
        }"""),
        ("                && !memcmp(&packet.view, &empty, sizeof(empty))) { errno = packet.error; break; }",
         """                && !memcmp(&packet.view, &empty, sizeof(empty))) {
            /* Only the pre-Partial child path emits S_PRIVATE. */
            if (packet.stage == S_PRIVATE) owner->early_local_proved = 1;
            errno = packet.error;
            break;
        }
        if (live == 0) { errno = ECHILD; break; }"""),
        (verified, verified + "\n        owner->early_local_proved = 1;"),
        ("owner->uid, owner->gid, &owner->close_error);",
         "owner->uid, owner->gid, &owner->close_error, NULL);"),
        ("""    if (owner->close_error || owner->stop_error || (result == GTR_TREE_LOCAL_RELEASED && !owner->held)) {
        errno = owner->close_error ? owner->close_error : owner->stop_error ? owner->stop_error : EPROTO;
        result = GTR_HOLD;
    }""", """    if (owner->close_error || owner->stop_error || (result == GTR_TREE_LOCAL_RELEASED && !owner->held)) {
        errno = owner->close_error ? owner->close_error : owner->stop_error ? owner->stop_error : EPROTO;
        result = GTR_HOLD;
    } else if (result == GTR_CHILD_REAPED_LOCAL_CLOSED && owner->child > 0
            && !owner->held && !owner->entry_prepare_attempted && owner->early_local_proved) {
        result = GTR_EARLY_PREPARE_LOCAL_CLOSED;
    }"""),
    ])


def guard(raw):
    return overlay(raw, [
        ("int marker_attempted, verified, armed, begin_ok, control_closed, finished;",
         "int marker_attempted, verified, armed, begin_ok, finished;\n    enum gtr_release control_terminal;"),
        ("!guard->control_closed", "!guard->control_terminal"),
        (POLL, TYPED_POLL),
        ("    if (guard->control_closed) return 0;",
         """    if (guard->control_terminal) {
        if (terminal) *terminal = guard->control_terminal;
        return 0;
    }"""),
        ("    if (progress != expected) return hold(guard, EINPROGRESS);\n    guard->control_closed = 1;",
         """    if (progress != expected && !(guard->begin_ok && progress == GTR_EARLY_PREPARE_LOCAL_CLOSED))
        return hold(guard, EINPROGRESS);
    guard->control_terminal = progress;
    if (terminal) *terminal = progress;"""),
        ("guest_tree_stage_guard_poll_control(guard) < 0", "guest_tree_stage_guard_poll_control(guard, NULL) < 0"),
    ])


def provider(raw):
    return overlay(raw, [
        ("int available, armed, begin_ok, cutoff,", "int available, armed, cutoff,"),
        ("""    if (guest_tree_stage_guard_begin(owner->guard, &owner->control, owner->duplicates) < 0) goto done;
    owner->begin_ok = 1;
    struct gtc_observation actual;""",
         """    struct gtc_observation actual;
    if (guest_tree_stage_guard_begin(owner->guard, &owner->control, owner->duplicates) < 0) goto done;"""),
        ("    if (owner->armed && guest_tree_stage_guard_poll_control(owner->guard) < 0) goto done;",
         """    enum gtr_release control_terminal = owner->armed ? GTR_HOLD : GTR_NO_CHILD_LOCAL_CLOSED;
    if (owner->armed && guest_tree_stage_guard_poll_control(owner->guard, &control_terminal) < 0) goto done;
    enum gtsp_release terminal;
    if (control_terminal == GTR_EARLY_PREPARE_LOCAL_CLOSED)
        terminal = GTSP_EARLY_PREPARE_LOCAL_CLOSED;
    else if (control_terminal == GTR_TREE_LOCAL_RELEASED)
        terminal = GTSP_TREE_LOCAL_RELEASED;
    else if (control_terminal == GTR_NO_CHILD_LOCAL_CLOSED)
        terminal = GTSP_NEVER_BEGAN_LOCAL_CLOSED;
    else {
        owner->source_error = errno = EPROTO;
        goto done;
    }"""),
        ("    owner->terminal = owner->begin_ok ? GTSP_TREE_LOCAL_RELEASED : GTSP_NEVER_BEGAN_LOCAL_CLOSED;",
         "    owner->terminal = terminal;"),
    ])


def main():
    prior = json.loads(read_small(BASE / "receipt.json", 256 * 1024, BASE_RECEIPT))
    entry = json.loads(read_small(ENTRY / "receipt.json", 4096, ENTRY_RECEIPT))
    transforms = {
        "guest_tree_control_owner.c": controller,
        "guest_tree_release_owner.h": lambda raw: overlay(raw, [
            ("    GTR_TREE_LOCAL_RELEASED\n",
             "    GTR_TREE_LOCAL_RELEASED,\n"
             "    /* Only GTC adds this after verifying its early handoff. */\n"
             "    GTR_EARLY_PREPARE_LOCAL_CLOSED\n"),
        ]),
        "guest_tree_stage_guard.c": guard,
        "guest_tree_stage_guard.h": lambda raw: overlay(raw, [
            (POLL, TYPED_POLL),
            ("records its verified local terminal.", "records its verified local terminal in the optional output."),
            ("release after a successful begin, or proved no-child local closure after",
             "release or verified early local closure after a successful begin, or no-child closure after"),
        ]),
        "guest_tree_stage_provider.c": provider,
        "guest_tree_stage_provider.h": lambda raw: overlay(raw, [
            ("    GTSP_TREE_LOCAL_RELEASED = 4\n",
             "    GTSP_TREE_LOCAL_RELEASED = 4,\n    GTSP_EARLY_PREPARE_LOCAL_CLOSED = 5\n"),
            (" * Nonblocking child poll. After actual tree-local child release, confirm",
             " * Nonblocking child poll. After verified local child closure, confirm"),
            ("Armed no-rights, drift and uncertain close stay in HOLD.",
             "Unproved early closure, drift and uncertain close stay in HOLD."),
        ]),
        MAIN: lambda raw: overlay(raw, [
            ("return result==GTSP_NEVER_BEGAN_LOCAL_CLOSED || result==GTSP_TREE_LOCAL_RELEASED;",
             "return result==GTSP_NEVER_BEGAN_LOCAL_CLOSED || result==GTSP_TREE_LOCAL_RELEASED ||\n"
             "        result==GTSP_EARLY_PREPARE_LOCAL_CLOSED;"),
        ]),
    }
    inputs = {name: prior["sourcePins"][name] for name in transforms}
    inputs[MAIN] = entry["sources"][MAIN]
    outputs = {
        name: transform(read_small((ENTRY if name == MAIN else BASE / "src") / name, 64 * 1024, inputs[name]))
        for name, transform in transforms.items()
    }
    run = ROOT / "out/guest-exec-carrier-recovery-source" / f"r-{uuid4().hex[:8]}"
    run.mkdir(parents=True)
    for name, data in outputs.items():
        (run / name).write_bytes(data)
    receipt = {
        "schema": 1, "status": "PASS_EXACT_RESEARCH_EARLY_PREPARE_RECOVERY_SOURCE",
        "baseReceiptSha256": BASE_RECEIPT, "entryReceiptSha256": ENTRY_RECEIPT, "inputs": inputs,
        "sources": {name: sha256(data).hexdigest() for name, data in outputs.items()},
        "inverse": True, "wireChange": False, "selected": False,
        "deviceEligible": False, "targetExecuted": False,
    }
    (run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(run)


if __name__ == "__main__":
    main()

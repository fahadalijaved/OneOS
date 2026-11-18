"""Derive the unselected child-birth evidence overlay on the exact GTC owner."""

from prepare_retained_writer_app import apply
from run_guest_tree_install_transport import load_io, pinned


BASE = 'out/guest-tree-root-attach/r-95b38f3d/src/'
SOURCE = 'guest_tree_control_owner.c'
HEADER = 'guest_tree_control_owner.h'
PINS = {
    SOURCE: (18336, '5c3e7a7bb0bdef1417357abd3076918568e0303f42d3d69df792904a88f5e66d'),
    HEADER: (2651, 'e4755f74d65efc3008c8a942d444544bf214564e164269858dfda54ffb7e0d2a'),
}

RECEIVE = b'int gtc_receive_partial(struct gtc_owner *owner, struct gtc_observation *observed) {\n'
STOP = b'int gtc_request_stop(struct gtc_owner *owner) {\n'
TAKE_RIGHTS = b'''        if (gtr_take_view_rights(owner->release, rights) < 0) break;
        owner->held = 1;
        *observed = packet.view;
        result = 0;
'''

CAPTURE = b'''/* This observation never consumes child status or advances GTR ownership. */
static int child_live_for_birth(pid_t child) {
    siginfo_t status = {0};
    if (waitid(P_PID, (id_t)child, &status, WEXITED | WNOHANG | WNOWAIT) < 0) return -1;
    if (status.si_pid) { errno = ECHILD; return -1; }
    return 0;
}

static void capture_child_birth(struct gtc_owner *owner) {
    int saved = errno;
    uint64_t now, ticks = 0;
    if (now_ms(&now) == 0 && now < owner->deadline && owner->deadline - now >= GTC_BIRTH_MIN_REMAINING_MS
            && child_live_for_birth(owner->child) == 0
            && guest_tree_stop_role_birth(owner->child, &ticks) == 0 && ticks
            && child_live_for_birth(owner->child) == 0 && now_ms(&now) == 0 && now < owner->deadline) {
        owner->child_birth = (struct gtc_child_birth){.pid = owner->child, .start_ticks = ticks};
    }
    errno = saved;
}

'''

GETTER = b'''int gtc_observed_child_birth(struct gtc_owner *owner, struct gtc_child_birth *out) {
    if (!out) { errno = EINVAL; return -1; }
    *out = (struct gtc_child_birth){0};
    if (enter_owner(owner) < 0) return -1;
    int result = -1;
    if (owner->cutoff || !owner->held || !owner->release || owner->child <= 0) errno = EBUSY;
    else if (owner->child_birth.pid != owner->child || !owner->child_birth.start_ticks) errno = ENODATA;
    else if (child_live_for_birth(owner->child) == 0) {
        *out = owner->child_birth;
        result = 0;
    }
    leave();
    return result;
}

'''

EDITS = {
    SOURCE: (
        (b'#include "guest_tree_child_view.h"\n',
         b'#include "guest_tree_child_view.h"\n#include "guest_tree_stop_role_birth.h"\n', 1),
        (b'#include <sys/socket.h>\n', b'#include <sys/socket.h>\n#include <sys/wait.h>\n', 1),
        (b'#define GTC_GRACE_MS UINT64_C(2000)\n',
         b'#define GTC_GRACE_MS UINT64_C(2000)\n#define GTC_BIRTH_MIN_REMAINING_MS UINT64_C(100)\n', 1),
        (b'    uint64_t deadline, kill_at;\n',
         b'    uint64_t deadline, kill_at;\n    struct gtc_child_birth child_birth;\n', 1),
        (RECEIVE, CAPTURE + RECEIVE, 1),
        (TAKE_RIGHTS, TAKE_RIGHTS + b'        capture_child_birth(owner);\n', 1),
        (STOP, GETTER + STOP, 1),
    ),
    HEADER: (
        (b'/* One STOP request and actual control cutoff, with no reap promise. */\n',
         b'''/* Optional birth of the actual retained child, available before cutoff.
 * Returns zero and fills out only when the saved birth still has a live child.
 * On refusal, returns -1 and clears a nonnull out. No child wait is consumed. */
struct gtc_child_birth { pid_t pid; uint64_t start_ticks; };
int gtc_observed_child_birth(struct gtc_owner *owner, struct gtc_child_birth *out);

/* One STOP request and actual control cutoff, with no reap promise. */
''', 1),
    ),
}


def derive():
    """Read pinned inputs and return transformed bytes after an exact inverse check."""
    io = load_io()
    output = {}
    for name, (size, digest) in PINS.items():
        original = pinned(io, BASE + name, digest, size)
        if len(original) != size:
            raise ValueError(f'Unexpected GTC source length: {name}')
        edits = EDITS[name]
        staged = apply(original, edits)
        inverse = [(new, old, count) for old, new, count in reversed(edits)]
        if apply(staged, inverse, allow_existing=True) != original:
            raise ValueError(f'GTC child-birth source lacks an exact inverse: {name}')
        output[name] = staged
    return output

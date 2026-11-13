/* Inert stage/syscall model. The fixed content symbol exists only in this test. */
#include "guest_tree_stage_provider.h"
#include "guest_tree_stage_guard.h"
#include "guest_tree_source_mounts.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <unistd.h>

enum node { N_ROOT = 1, N_HOST_DATA, N_LOCAL, N_TMP, N_STAGE, N_BACKING, N_TREE, N_DATA, N_USER, N_ZERO, N_ALIAS,
            N_NS, N_MOUNTINFO };
enum fault { GOOD, STAGE_MISSING, GUARD_MISSING, CONTENT_REFUSED, POST_CHILD_DRIFT, ARMED_NO_RIGHTS, CLOSE_ERROR,
             SAME_DEVICE, WRITABLE_SUPER, READONLY_DATA, OVERMOUNT, ALIAS_MOUNT, POST_CHILD_BACKING_DRIFT,
             BEGIN_NO_CHILD, BEGIN_NO_CHILD_DRIFT, BEGIN_NO_CHILD_CLOSE_ERROR, BEGIN_MISSING_OWNER,
             UNEXPECTED_NO_CHILD };
enum { MAX_FDS = 512, PARENT = 23 };
struct guest_tree_stage_guard {
    struct gtc_owner *control;
    int begin_ok, control_closed, hold_error;
};
struct gtc_owner { int retained; };
static struct guest_tree_stage_guard guard;
static struct gtc_owner child;
static struct gtsp_owner *owner;
static int fds[MAX_FDS], next_fd = 3, child_fds[GTR_WITNESSES], checks;
static size_t offsets[MAX_FDS];
static int guard_checks, admissions, starts, receives, stops, finishes, polls, drift, at_release, original_tree;
static enum fault fault;

static void check(int condition, const char *why) {
    ++checks;
    if (!condition) { fprintf(stderr, "%s\n", why); exit(1); }
}

static int fd(int node) {
    check(next_fd < MAX_FDS, "bounded fixture descriptor table");
    fds[next_fd] = node;
    return next_fd++;
}

static int node(int handle) {
    check(handle >= 3 && handle < next_fd && fds[handle], "actual live descriptor");
    return fds[handle];
}

static int pre_fork_refusal(void) {
    return fault >= BEGIN_NO_CHILD && fault <= BEGIN_NO_CHILD_CLOSE_ERROR;
}

pid_t getpid(void) { return PARENT; }
pid_t gettid(void) { return PARENT; }
uid_t getuid(void) { return 0; }
uid_t geteuid(void) { return 0; }

int open(const char *path, int flags, ...) {
    check(owner != NULL, "retain source owner before actual open");
    if (!strcmp(path, "/")) {
        check(flags == (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC), "exact nofollow root open");
        return fd(N_ROOT);
    }
    if (!strcmp(path, "/proc/self/mountinfo")) {
        check(flags == (O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC), "bounded authentic proc open");
        return fd(N_MOUNTINFO);
    }
    check(!strcmp(path, "/proc/self/ns/mnt") && flags == (O_RDONLY | O_CLOEXEC), "exact original namespace open");
    return fd(N_NS);
}

int openat(int base, const char *name, int flags, ...) {
    check(flags == (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC), "nofollow every stage component");
    int parent = node(base);
    if (parent == N_ROOT && !strcmp(name, "data")) return fd(N_HOST_DATA);
    if (parent == N_HOST_DATA && !strcmp(name, "local")) return fd(N_LOCAL);
    if (parent == N_LOCAL && !strcmp(name, "tmp")) return fd(N_TMP);
    if (parent == N_TMP && !strcmp(name, "oneos-viewprep")) {
        if (fault == STAGE_MISSING) { errno = ENOENT; return -1; }
        return fd(N_STAGE);
    }
    if (parent == N_STAGE && !strcmp(name, "backing")) return fd(N_BACKING);
    if (parent == N_BACKING && !strcmp(name, "tree")) {
        int opened = fd(N_TREE);
        if (!original_tree) original_tree = opened;
        return opened;
    }
    if (parent == N_STAGE && !strcmp(name, "data")) return fd(N_DATA);
    if (parent == N_DATA && !strcmp(name, "user")) return fd(N_USER);
    if (parent == N_USER && !strcmp(name, "0")) return fd(N_ZERO);
    if (parent == N_DATA && !strcmp(name, "data")) return fd(N_ALIAS);
    abort();
}

int fcntl(int handle, int command, ...) {
    check(command == F_DUPFD_CLOEXEC, "actual CLOEXEC duplication");
    return fd(node(handle));
}
int close(int handle) {
    (void)node(handle);
    fds[handle] = 0;
    if (at_release && (fault == CLOSE_ERROR || fault == BEGIN_NO_CHILD_CLOSE_ERROR)
            && handle == original_tree) { errno = EIO; return -1; }
    return 0;
}
ssize_t read(int handle, void *bytes, size_t capacity) {
    check(node(handle) == N_MOUNTINFO, "mountinfo read owns exact proc file");
    char table[1024];
    int length = snprintf(table, sizeof(table), "1 99 8:1 / / ro - ext4 /dev/root ro\n"
        "2 1 8:2 / /data %s - f2fs /dev/data rw\n"
        "3 2 8:3 / " GUEST_TREE_BACKING_PATH " ro - erofs /dev/donor %s\n%s",
        fault == READONLY_DATA ? "ro" : "rw",
        fault == WRITABLE_SUPER || (fault == POST_CHILD_BACKING_DRIFT && receives) ? "rw" : "ro",
        fault == OVERMOUNT ? "4 2 8:4 / " GUEST_TREE_BACKING_PATH " ro - ext4 /dev/other ro\n"
        : fault == ALIAS_MOUNT ? "4 1 8:3 / /other ro - erofs /dev/donor ro\n" : "");
    check(length > 0 && (size_t)length < sizeof(table), "bounded fixture mount table");
    size_t remaining = (size_t)length - offsets[handle];
    if (capacity > remaining) capacity = remaining;
    memcpy(bytes, table + offsets[handle], capacity);
    offsets[handle] += capacity;
    return (ssize_t)capacity;
}
int statx(int handle, const char *path, int flags, unsigned mask, struct statx *out) {
    if (handle == AT_FDCWD) {
        check(!strcmp(path, "/proc") && flags == (AT_NO_AUTOMOUNT | AT_SYMLINK_NOFOLLOW)
            && mask == (STATX_TYPE | STATX_MNT_ID), "actual named proc mount identity");
        *out = (struct statx){.stx_mask = mask, .stx_mode = S_IFDIR | 0555, .stx_mnt_id = 7};
        return 0;
    }
    check(!*path && flags == (AT_EMPTY_PATH | AT_NO_AUTOMOUNT | AT_SYMLINK_NOFOLLOW)
          && (mask & STATX_MNT_ID), "statx actual held directory identity");
    int type = node(handle);
    if (type == N_MOUNTINFO) {
        *out = (struct statx){.stx_mask = mask, .stx_mode = S_IFREG | 0444, .stx_mnt_id = 7};
        return 0;
    }
    *out = (struct statx){.stx_mask = mask, .stx_mode = S_IFDIR | 0755, .stx_mnt_id = type == N_ROOT ? 1 : 2,
        .stx_dev_major = 8, .stx_dev_minor = type == N_ROOT ? 1 : 2,
        .stx_ino = (unsigned)type + 10, .stx_nlink = 2, .stx_size = 4096};
    if (type == N_BACKING || type == N_TREE) {
        out->stx_mnt_id = 3;
        if (fault != SAME_DEVICE) out->stx_dev_minor = 3;
    }
    if (type == N_DATA) { out->stx_uid = out->stx_gid = 1000; out->stx_mode = S_IFDIR | 0771; }
    if (type == N_TREE && drift) out->stx_ctime.tv_nsec = 1;
    return 0;
}
int fstat(int handle, struct stat *out) {
    check(node(handle) == N_NS, "actual namespace witness");
    *out = (struct stat){.st_dev = 3, .st_ino = 40};
    return 0;
}
int stat(const char *path, struct stat *out) {
    check(!strcmp(path, "/proc/self/ns/mnt"), "same named current namespace");
    *out = (struct stat){.st_dev = 3, .st_ino = 40};
    return 0;
}
int fstatfs(int handle, struct statfs *out) {
    int type = node(handle);
    check(type == N_NS || type == N_MOUNTINFO, "actual namespace or proc witness");
    out->f_type = type == N_NS ? NSFS_MAGIC : PROC_SUPER_MAGIC;
    return 0;
}
int ioctl(int handle, unsigned long request, ...) {
    check(node(handle) == N_NS && request == NS_GET_NSTYPE, "actual mount namespace type query");
    return CLONE_NEWNS;
}

int guest_tree_stage_guard_acquire(struct guest_tree_stage_guard **out) {
    check(owner && !*out, "retain actual source before guard work");
    *out = &guard;
    if (fault == GUARD_MISSING) { errno = ENOENT; return -1; }
    return 0;
}
int guest_tree_stage_guard_check(struct guest_tree_stage_guard *actual) {
    check(actual == &guard && !finishes, "same guard remains retained");
    ++guard_checks;
    return 0;
}
int guest_tree_admit_stage_contents(const struct gtsp_stage_witnesses *witnesses) {
    check(witnesses->guard == &guard && node(witnesses->stage_fd) == N_STAGE && node(witnesses->tree_fd) == N_TREE
          && node(witnesses->data_fd) == N_DATA && node(witnesses->parent_namespace_fd) == N_NS && guard_checks,
          "strong fixed gate receives exact held witnesses and guard");
    ++admissions;
    if (fault == CONTENT_REFUSED) { errno = ENOENT; return -1; }
    if (fault == POST_CHILD_DRIFT && receives) drift = 1;
    return 0;
}
int guest_tree_stage_guard_begin(struct guest_tree_stage_guard *actual, struct gtc_owner **out,
        int witnesses[GTR_WITNESSES]) {
    check(actual == &guard && !*out && admissions == 2 && node(witnesses[0]) == N_TREE
          && node(witnesses[1]) == N_DATA && node(witnesses[2]) == N_NS, "actual gated child witness transfer");
    ++starts;
    if (fault == BEGIN_MISSING_OWNER) { actual->hold_error = EACCES; errno = EACCES; return -1; }
    *out = actual->control = &child;
    /* A pre-fork socket setup failure retains GTC but has not taken the witness cells. */
    if (pre_fork_refusal()) { errno = EACCES; return -1; }
    for (int i = 0; i < GTR_WITNESSES; ++i) { child_fds[i] = witnesses[i]; witnesses[i] = -1; }
    actual->begin_ok = 1;
    return 0;
}
int gtc_receive_partial(struct gtc_owner *actual, struct gtc_observation *observation) {
    check(actual == &child && starts == 1, "receive exact retained control");
    ++receives;
    if (fault == ARMED_NO_RIGHTS) { errno = EPROTO; return -1; }
    *observation = (struct gtc_observation){.namespace_inode = 71};
    return 0;
}
int gtc_request_stop(struct gtc_owner *actual) {
    check(actual == &child && !stops, "one cutoff on actual child");
    ++stops;
    return 0;
}
enum gtr_release gtc_poll_close(struct gtc_owner *actual) {
    check(actual == &child && stops == 1, "same actual child drained after STOP");
    ++polls;
    if (polls == 1) return GTR_HOLD;
    if (pre_fork_refusal()) return GTR_NO_CHILD_LOCAL_CLOSED;
    if (polls == 2) {
        for (int i = 0; i < GTR_WITNESSES; ++i) { close(child_fds[i]); child_fds[i] = -1; }
    }
    if (fault == UNEXPECTED_NO_CHILD) return GTR_NO_CHILD_LOCAL_CLOSED;
    return fault == ARMED_NO_RIGHTS ? GTR_CHILD_REAPED_LOCAL_CLOSED : GTR_TREE_LOCAL_RELEASED;
}
int guest_tree_stage_guard_poll_control(struct guest_tree_stage_guard *actual) {
    check(actual == &guard && starts == 1 && !finishes, "poll the exact armed guard");
    if (actual->hold_error) { errno = actual->hold_error; return -1; }
    if (actual->control_closed) return 0;
    enum gtr_release progress = gtc_poll_close(actual->control);
    if (progress == GTR_HOLD) { errno = EAGAIN; return -1; }
    enum gtr_release expected = actual->begin_ok ? GTR_TREE_LOCAL_RELEASED : GTR_NO_CHILD_LOCAL_CLOSED;
    if (progress != expected) { errno = actual->hold_error = EINPROGRESS; return -1; }
    actual->control_closed = 1;
    return 0;
}
int guest_tree_stage_guard_finish(struct guest_tree_stage_guard *actual) {
    check(actual == &guard && !finishes, "exact guard finish once");
    for (int i = 3; i < next_fd; ++i) check(!fds[i], "all provider and child source refs closed before guard");
    ++finishes;
    return 0;
}

static void check_begin_refusal(int begun, const struct gtc_observation *observation) {
    check(begun < 0 && errno == EACCES && !observation->namespace_inode
          && starts == 1 && !receives && admissions == 2,
          "failed guard begin retains its primary error and publishes no view");
    int has_owner = fault != BEGIN_MISSING_OWNER;
    check(gtsp_poll_close(owner) == GTSP_HOLD && !finishes
          && polls == has_owner && stops == has_owner && node(original_tree) == N_TREE,
          "missing owner or unresolved lower close holds the source and guard");
    drift = fault == BEGIN_NO_CHILD_DRIFT;
    at_release = 1;
    enum gtsp_release expected = fault == BEGIN_NO_CHILD ? GTSP_NEVER_BEGAN_LOCAL_CLOSED : GTSP_HOLD;
    check(gtsp_poll_close(owner) == expected, "only proven no-child cleanup reaches never-began");
    if (fault == BEGIN_NO_CHILD) {
        check(admissions == 3 && finishes == 1 && polls == 2,
              "final source readback and exactly one guard finish");
        check(gtsp_poll_close(owner) == expected && finishes == 1 && polls == 2 && stops == 1,
              "never-began terminal stays sticky without polling or closing again");
    } else {
        int expected_admissions = fault == BEGIN_NO_CHILD_CLOSE_ERROR ? 3 : 2;
        check(!finishes && admissions == expected_admissions
              && gtsp_poll_close(owner) == GTSP_HOLD && !finishes && starts == 1,
              "missing owner, final source drift or uncertain close keeps the guard");
    }
}

static void run(void) {
    int opened = gtsp_open_existing(&owner);
    check(owner != NULL, "non-null source owner on post-claim refusal");
    if (fault == STAGE_MISSING || fault == GUARD_MISSING || fault == CONTENT_REFUSED
            || (fault >= SAME_DEVICE && fault <= ALIAS_MOUNT)) {
        int expected = fault == STAGE_MISSING ? ENOENT : fault == GUARD_MISSING ? EPERM
            : fault == CONTENT_REFUSED ? ESTALE : EXDEV;
        check(opened < 0 && errno == expected, "only actual sibling miss may request stage");
        check(admissions == (fault == CONTENT_REFUSED), "profile refusal precedes content admission");
        check(gtsp_poll_close(owner) == GTSP_NEVER_BEGAN_LOCAL_CLOSED && finishes == 1 && !starts,
              "unarmed refusal closes its own guard only");
        return;
    }
    check(opened == 0 && admissions == 1, "actual guarded content before source availability");
    struct gtc_observation observation = {0};
    int begun = gtsp_begin_view(owner, &observation);
    if (pre_fork_refusal() || fault == BEGIN_MISSING_OWNER) {
        check_begin_refusal(begun, &observation);
        return;
    }
    if (fault == GOOD || fault == CLOSE_ERROR || fault == UNEXPECTED_NO_CHILD) {
        check(begun == 0 && observation.namespace_inode == 71 && admissions == 3 && !stops,
              "publish actual retained partial only after post-read content");
        check(gtsp_begin_view(owner, &observation) < 0 && errno == EBUSY && !stops && starts == 1,
              "duplicate begin cannot cut off current child");
    } else {
        check(begun < 0 && !observation.namespace_inode && stops == 1, "failure cuts off child without publication");
    }
    check(gtsp_poll_close(owner) == GTSP_HOLD && !finishes && stops == 1 && polls == 1,
          "poll initiates exact STOP and retains source while child held");
    at_release = 1;
    enum gtsp_release expected = fault == GOOD ? GTSP_TREE_LOCAL_RELEASED : GTSP_HOLD;
    check(gtsp_poll_close(owner) == expected, "actual tree-local release or retained uncertainty");
    if (fault == GOOD) {
        check(admissions == 4 && finishes == 1 && gtsp_poll_close(owner) == expected && polls == 2,
              "actual final source readback, guard finish and sticky terminal");
    } else {
        check(!finishes && gtsp_poll_close(owner) == GTSP_HOLD && !finishes,
              "drift, no-rights or uncertain close stays negative");
        if (fault == UNEXPECTED_NO_CHILD)
            check(admissions == 3 && node(original_tree) == N_TREE,
                  "successful begin cannot downgrade to never-began or release its sources");
    }
}

int main(int argc, char **argv) {
    static const char *const names[] = {"good", "stage-missing", "guard-missing", "content-refused",
                                        "post-child-drift", "armed-no-rights", "close-error", "same-device",
                                        "writable-super", "readonly-data", "overmount", "alias-mount",
                                        "post-child-backing-drift", "begin-no-child", "begin-no-child-drift",
                                        "begin-no-child-close-error", "begin-missing-owner", "unexpected-no-child"};
    if (argc != 2) return 2;
    for (unsigned n = 0; n < sizeof(names) / sizeof(names[0]); ++n) {
        if (strcmp(argv[1], names[n])) continue;
        fault = (enum fault)n;
        run();
        printf("PASS %s %d\n", names[n], checks);
        return 0;
    }
    return 2;
}

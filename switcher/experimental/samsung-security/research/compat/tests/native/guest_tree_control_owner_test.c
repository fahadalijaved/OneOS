/* Inert socket/child syscalls and fixed-link verifier substitutions for tests. */
#include "guest_tree_control_owner.h"
#include "guest_tree_parent_view.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <time.h>

enum { PARENT = 23, CHILD = 41, CONTROL = 8, CHILD_CONTROL = 9, FIRST_RIGHT = 20 };
enum scenario {
    GOOD, WRONG_CREDENTIAL, TRUNCATED, ROOT_REFUSED, ROLES_REFUSED, DEADLINE,
    CHILD_ERROR, LOOP_FIELD, FORK_CLEANUP, SOCKET_SETUP, REENTRY, STOP_UNCERTAIN,
    SOCKET_SETUP_CLOSE_UNCERTAIN
};
struct fixture_directory { int index; };
struct packet {
    uint32_t magic, version, kind, stage;
    int32_t error, pid;
    uint32_t uid, gid;
    struct gtc_observation view;
    uint64_t image_dev, image_inode, loop_device;
    uint32_t loop_number, loop_flags;
    uint64_t reserved[2];
};
_Static_assert(sizeof(struct packet) == 200, "fixture uses exact v3 wire");

static enum scenario scenario;
static struct gtc_owner *owner;
static struct fixture_directory proc;
static int checks, opens, pairs, opts, forks, waits, receives, root_checks, role_checks, takes;
static int cancels, cutoffs, term_signals, kill_signals, close_counts[32];
static int final_reap;
static uint64_t time_ms = 1000;

static void check(int condition, const char *why) {
    ++checks;
    if (!condition) { fprintf(stderr, "%s\n", why); exit(1); }
}

pid_t getpid(void) { return PARENT; }
pid_t gettid(void) { return PARENT; }
pid_t getppid(void) { abort(); }
uid_t geteuid(void) { return 0; }
gid_t getegid(void) { return 0; }
int getresuid(uid_t *r, uid_t *e, uid_t *s) { *r = *e = *s = 0; return 0; }
int getresgid(gid_t *r, gid_t *e, gid_t *s) { *r = *e = *s = 0; return 0; }
int sigemptyset(sigset_t *set) { (void)set; abort(); }
int sigaction(int signal, const struct sigaction *action, struct sigaction *old) {
    (void)signal; (void)action; (void)old; abort();
}
int sigprocmask(int how, const sigset_t *set, sigset_t *old) { (void)how; (void)set; (void)old; abort(); }
int prctl(int option, ...) { (void)option; abort(); }
_Noreturn void _exit(int status) { (void)status; abort(); }

DIR *opendir(const char *path) {
    check(!strcmp(path, "/proc/self/task"), "parent only samples actual thread profile");
    ++opens;
    proc.index = 0;
    return &proc;
}
struct dirent *readdir(DIR *directory) {
    static struct dirent entry = {.d_name = "23"};
    check(directory == &proc, "exact proc directory");
    return directory->index++ ? NULL : &entry;
}
int dirfd(DIR *directory) { (void)directory; abort(); }
int closedir(DIR *directory) { check(directory == &proc, "close exact proc directory"); return 0; }

int clock_gettime(int clock, struct timespec *out) {
    check(clock == CLOCK_MONOTONIC, "only monotonic clock");
    out->tv_sec = (long long)(time_ms / 1000);
    out->tv_nsec = (long)(time_ms % 1000) * 1000000L;
    return 0;
}

int socketpair(int domain, int type, int protocol, int out[2]) {
    check(owner && domain == AF_UNIX && type == (SOCK_SEQPACKET | SOCK_CLOEXEC | SOCK_NONBLOCK)
          && protocol == 0, "retain owner before actual exact socketpair");
    ++pairs;
    out[0] = CONTROL;
    out[1] = CHILD_CONTROL;
    return 0;
}
int setsockopt(int fd, int level, int option, const void *value, socklen_t length) {
    check((fd == CONTROL || fd == CHILD_CONTROL) && level == SOL_SOCKET && option == SO_PASSCRED
          && length == sizeof(int) && *(const int *)value == 1, "authenticate actual credentials on both sockets");
    ++opts;
    if ((scenario == SOCKET_SETUP || scenario == SOCKET_SETUP_CLOSE_UNCERTAIN) && fd == CHILD_CONTROL) {
        errno = EACCES;
        return -1;
    }
    return 0;
}
int fcntl(int fd, int command, ...) {
    check(fd >= FIRST_RIGHT && fd < FIRST_RIGHT + GTR_VIEW_RIGHTS && command == F_GETFD,
          "validate actual received CLOEXEC cells");
    return FD_CLOEXEC;
}
int close(int fd) {
    check(fd >= 0 && fd < 32 && !close_counts[fd], "consume each exact close once");
    ++close_counts[fd];
    if (scenario == TRUNCATED && fd == FIRST_RIGHT + 2) { errno = EIO; return -1; }
    if (scenario == SOCKET_SETUP_CLOSE_UNCERTAIN && fd == CONTROL) { errno = EIO; return -1; }
    return 0;
}
int poll(struct pollfd *fds, unsigned long count, int timeout) {
    check(count == 1 && fds->fd == CONTROL && fds->events == POLLIN && timeout > 0 && timeout <= 100,
          "bounded actual control poll");
    fds->revents = POLLIN;
    return 1;
}

ssize_t recvmsg(int fd, struct msghdr *message, int flags) {
    check(fd == CONTROL && message->msg_iovlen == 1 && message->msg_iov[0].iov_len == 200
          && flags == (MSG_CMSG_CLOEXEC | MSG_DONTWAIT), "actual seqpacket receive and close-on-exec");
    ++receives;
    struct packet packet = {.magic = UINT32_C(0x47564f33), .version = 3, .kind = 1, .stage = 11, .pid = CHILD,
                            .view = {.namespace_inode = 2, .namespace_dev = 3, .mounts = {0, 51, 52, 53, 54, 55, 55},
                                     .data_group = 61, .mirror_group = 62, .alias_native = 71, .alias_guest = 72,
                                     .guest_data_mount = 73, .guest_mirror_mount = 74}};
    if (scenario == CHILD_ERROR) {
        packet.kind = 2; packet.stage = 2; packet.error = ENOENT;
        memset(&packet.view, 0, sizeof(packet.view));
    }
    if (scenario == LOOP_FIELD) packet.loop_flags = 1;
    memcpy(message->msg_iov[0].iov_base, &packet, sizeof(packet));
    size_t credential_space = CMSG_SPACE(sizeof(struct ucred));
    size_t rights_space = scenario == CHILD_ERROR ? 0 : CMSG_SPACE(GTR_VIEW_RIGHTS * sizeof(int));
    check(message->msg_controllen >= credential_space + rights_space, "actual ancillary buffer accommodates full packet");
    message->msg_controllen = credential_space + rights_space;
    struct cmsghdr *c = CMSG_FIRSTHDR(message);
    c->cmsg_level = SOL_SOCKET;
    c->cmsg_type = SCM_CREDENTIALS;
    c->cmsg_len = CMSG_LEN(sizeof(struct ucred));
    struct ucred credential = {.pid = scenario == WRONG_CREDENTIAL ? CHILD + 1 : CHILD};
    memcpy(CMSG_DATA(c), &credential, sizeof(credential));
    if (rights_space) {
        c = CMSG_NXTHDR(message, c);
        check(c != NULL, "SCM_RIGHTS follows credentials");
        c->cmsg_level = SOL_SOCKET;
        c->cmsg_type = SCM_RIGHTS;
        c->cmsg_len = CMSG_LEN(GTR_VIEW_RIGHTS * sizeof(int));
        int rights[GTR_VIEW_RIGHTS];
        for (int n = 0; n < GTR_VIEW_RIGHTS; ++n) rights[n] = FIRST_RIGHT + n;
        memcpy(CMSG_DATA(c), rights, sizeof(rights));
    }
    if (scenario == TRUNCATED) message->msg_flags = MSG_CTRUNC;
    return sizeof(packet);
}

ssize_t sendmsg(int fd, const struct msghdr *message, int flags) {
    struct packet packet;
    check(fd == CONTROL && message->msg_iov[0].iov_len == sizeof(packet)
          && flags == (MSG_NOSIGNAL | MSG_DONTWAIT) && !message->msg_control, "owned exact zero-rights cancel");
    memcpy(&packet, message->msg_iov[0].iov_base, sizeof(packet));
    check(packet.kind == 3 && packet.magic == UINT32_C(0x47564f33) && packet.version == 3
          && packet.pid == PARENT && !packet.stage && !packet.error && !packet.loop_flags
          && !packet.view.namespace_dev && !packet.view.mounts[GTC_GUEST_ROOT], "exact original CANCEL frame");
    ++cancels;
    return sizeof(packet);
}

struct gtr_owner { int used; };
static struct gtr_owner release;

pid_t gtr_fork(struct gtr_owner **out, int sockets[2], int witnesses[GTR_WITNESSES]) {
    check(owner && !*out && sockets[0] == CONTROL && sockets[1] == CHILD_CONTROL && opts == 2,
          "transfer actual pair to sole fork owner");
    check(witnesses[0] == 10 && witnesses[1] == 11 && witnesses[2] == 12, "exact witness transfer");
    ++forks;
    *out = &release;
    sockets[0] = sockets[1] = -1;
    for (int n = 0; n < GTR_WITNESSES; ++n) witnesses[n] = -1;
    if (scenario == FORK_CLEANUP) { errno = EIO; return -1; }
    return CHILD;
}
int gtr_child_live(struct gtr_owner *actual) {
    check(actual == &release, "poll exact fork owner only");
    ++waits;
    return 1;
}
int gtr_take_view_rights(struct gtr_owner *actual, int rights[GTR_VIEW_RIGHTS]) {
    check(actual == &release && root_checks == 1 && role_checks == 1 && !cutoffs, "all fixed proofs before custody transfer");
    ++takes;
    for (int n = 0; n < GTR_VIEW_RIGHTS; ++n) {
        check(rights[n] == FIRST_RIGHT + n && !close_counts[rights[n]], "exact live received right");
        rights[n] = -1;
    }
    return 0;
}
int gtr_request_stop(struct gtr_owner *actual) {
    check(actual == &release, "cut off exact child owner");
    ++cutoffs;
    if (scenario == STOP_UNCERTAIN || scenario == FORK_CLEANUP) { errno = EIO; return -1; }
    return 0;
}
int gtr_signal_child(struct gtr_owner *actual, int signal_number) {
    check(actual == &release && cutoffs == 1 && (signal_number == SIGTERM || signal_number == SIGKILL),
          "exact child signal only after real control cutoff");
    if (signal_number == SIGTERM) ++term_signals;
    else ++kill_signals;
    return 0;
}
enum gtr_release gtr_poll_close(struct gtr_owner *actual) {
    check(actual == &release && cutoffs == 1, "poll same retained child after cutoff");
    if (!final_reap) return GTR_HOLD;
    return takes ? GTR_TREE_LOCAL_RELEASED : GTR_CHILD_REAPED_LOCAL_CLOSED;
}

static int check_root(pid_t child, int source_fd, int parent_namespace_fd, int child_namespace_fd,
        int child_root_fd, uint64_t dev, uint64_t inode, uint64_t root_mount_id, int *close_error) {
    check(child == CHILD && source_fd == 10 && parent_namespace_fd == 12 && child_namespace_fd == FIRST_RIGHT
          && child_root_fd == FIRST_RIGHT + 2 && dev == 3 && inode == 2 && root_mount_id == 52 && !*close_error,
          "fixed root verifier sees same actual child, witnesses and rights");
    ++root_checks;
    if (scenario == ROOT_REFUSED) { *close_error = EIO; errno = EXDEV; return -1; }
    if (scenario == REENTRY) check(gtc_request_stop(owner) < 0 && errno == EBUSY && !cutoffs,
                                  "reentrant mutation denied during proof");
    return 0;
}
int guest_tree_verify_remaining_view(pid_t child, const int witnesses[GTR_WITNESSES],
        const int rights[GTR_VIEW_RIGHTS], const struct gtc_observation *view, int *close_error) {
    if (check_root(child, witnesses[GTC_TREE], witnesses[GTC_PARENT_NAMESPACE], rights[GTC_NAMESPACE],
                   rights[GTC_GUEST_ROOT], view->namespace_dev, view->namespace_inode,
                   view->mounts[GTC_GUEST_ROOT], close_error) != 0) return -1;
    check(child == CHILD && witnesses[1] == 11 && rights[GTC_DEV] == FIRST_RIGHT + 5
          && rights[GTC_SOCKET] == FIRST_RIGHT + 6 && view->mirror_group == 62 && !*close_error && root_checks == 1,
          "fixed other-role verification required");
    ++role_checks;
    if (scenario == ROLES_REFUSED) { errno = EXDEV; return 1; }
    if (scenario == DEADLINE) time_ms = 31000;
    return 0;
}
int guest_tree_prepare_child_view(const struct gtc_child_inputs *input, struct gtc_child_view *view, void *context) {
    (void)input; (void)view; (void)context;
    abort(); /* inert tests never execute the child constructor */
}

static void run_case(void) {
    int witnesses[GTR_WITNESSES] = {10, 11, 12};
    int begun = gtc_begin(&owner, witnesses);
    int begin_errno = errno;
    check(owner && opens == 1 && opts == 2, "actual attempt retained");
    if (scenario == SOCKET_SETUP) {
        check(begun < 0 && !forks && witnesses[0] == 10 && close_counts[CONTROL] == 1
              && close_counts[CHILD_CONTROL] == 1, "setup failure closes only actual owned sockets");
        check(gtc_poll_close(owner) == GTR_NO_CHILD_LOCAL_CLOSED && !cutoffs
              && !term_signals && !kill_signals, "no child terminal");
        return;
    }
    if (scenario == SOCKET_SETUP_CLOSE_UNCERTAIN) {
        check(begun < 0 && begin_errno == EACCES, "socket setup errno survives uncertain cleanup");
        check(witnesses[0] == 10 && witnesses[1] == 11 && witnesses[2] == 12
              && close_counts[CONTROL] == 1 && close_counts[CHILD_CONTROL] == 1,
              "uncertain first close still attempts the other socket and leaves witnesses with caller");
        errno = EBUSY;
        check(gtc_poll_close(owner) == GTR_HOLD && errno == EIO, "setup close error prevents no-child terminal");
        errno = ENOSPC;
        check(gtc_poll_close(owner) == GTR_HOLD && errno == EIO, "repeated poll retains setup close error");
        check(opens == 1 && pairs == 1 && opts == 2 && close_counts[CONTROL] == 1 && close_counts[CHILD_CONTROL] == 1
              && !forks && !waits && !receives && !cutoffs && !cancels && !term_signals && !kill_signals,
              "held setup does not retry sockets or touch any child");
        return;
    }
    if (scenario == FORK_CLEANUP) {
        check(begun < 0 && forks == 1 && witnesses[0] == -1, "failed fork result can retain actual child custody");
        final_reap = 1;
        check(gtc_poll_close(owner) == GTR_HOLD && cutoffs == 1 && !cancels, "uncertain birth cleanup holds");
        return;
    }
    check(begun == 0 && forks == 1 && witnesses[0] == -1, "one actual fork and transferred witnesses");
    struct gtc_observation observed;
    int ready = gtc_receive_partial(owner, &observed);
    int accepted = scenario == GOOD || scenario == REENTRY || scenario == STOP_UNCERTAIN;
    if (accepted) {
        check(ready == 0 && takes == 1 && receives == 1 && observed.namespace_inode == 2 && !cancels,
              "real partial after both fixed verifiers");
        int stop = gtc_request_stop(owner);
        check((stop < 0) == (scenario == STOP_UNCERTAIN), "actual stop disposition");
        check(cancels == 1 && cutoffs == 1 && term_signals == 1 && !kill_signals, "one cancel, control cutoff and TERM");
        check(gtc_poll_close(owner) == GTR_HOLD && !kill_signals, "live child retains grace");
        time_ms += 1999;
        check(gtc_poll_close(owner) == GTR_HOLD && !kill_signals, "not yet grace expiry");
        ++time_ms;
        check(gtc_poll_close(owner) == GTR_HOLD && kill_signals == 1, "exact two-second escalation");
        check(gtc_poll_close(owner) == GTR_HOLD && kill_signals == 1, "no repeated KILL");
        final_reap = 1;
        enum gtr_release expected = scenario == STOP_UNCERTAIN ? GTR_HOLD : GTR_TREE_LOCAL_RELEASED;
        check(gtc_poll_close(owner) == expected && gtc_poll_close(owner) == expected && cancels == 1, "actual drain only");
        return;
    }
    int primary = errno;
    check(ready < 0 && !takes && receives == 1 && !observed.namespace_inode && cutoffs == 1,
          "no partial publication after refusal");
    for (int n = 0; n < GTR_VIEW_RIGHTS; ++n) {
        check(close_counts[FIRST_RIGHT + n] == (scenario != CHILD_ERROR), "every rejected acquired right consumed");
    }
    check(root_checks == (scenario == ROOT_REFUSED || scenario == ROLES_REFUSED || scenario == DEADLINE)
          && role_checks == (scenario == ROLES_REFUSED || scenario == DEADLINE), "strict verification order");
    if (scenario == CHILD_ERROR) check(primary == ENOENT, "bounded real child error preserved");
    if (scenario == DEADLINE) check(primary == ETIMEDOUT, "post-proof deadline gate");
    final_reap = 1;
    enum gtr_release expected = (scenario == ROOT_REFUSED || scenario == TRUNCATED) ? GTR_HOLD : GTR_CHILD_REAPED_LOCAL_CLOSED;
    check(gtc_poll_close(owner) == expected && cancels == 1 && cutoffs == 1, "refusal cannot become tree release");
}

int main(int argc, char **argv) {
    static const char *const names[] = {"good", "wrong-credential", "truncated", "root-refused", "roles-refused",
        "deadline", "child-error", "loop-field", "fork-cleanup", "socket-setup", "reentry", "stop-uncertain",
        "socket-setup-close-uncertain"};
    if (argc != 2) return 2;
    for (unsigned n = 0; n < sizeof(names) / sizeof(names[0]); ++n) {
        if (strcmp(argv[1], names[n])) continue;
        scenario = (enum scenario)n;
        run_case();
        printf("PASS %s %d\n", names[n], checks);
        return 0;
    }
    return 2;
}

#define _GNU_SOURCE
#include "guest_tree_fsverity_provision.h"
#include "guest_tree_install_bootstrap.h"
#include "guest_tree_install_controller.h"
#include "guest_tree_install_guard.h"
#include "guest_tree_install_scaffold.h"
#include "guest_tree_install_stream.h"

#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <sys/sysmacros.h>
#include <unistd.h>

#define DIR_PATH (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define STAGE_WITNESS_FD 6
#define GUARD_WITNESS_FD 7

static const struct guest_tree_fsverity_provision_expected carrier = {
    .bytes = UINT64_C(13890850816),
    .raw_sha256 = {
        0x09, 0x4f, 0xf7, 0xe7, 0xac, 0x11, 0x48, 0xfa,
        0xb7, 0x32, 0x71, 0x9d, 0x2e, 0x04, 0xa9, 0x43,
        0xfb, 0xbc, 0xc0, 0xd7, 0xd0, 0xae, 0x67, 0xad,
        0x62, 0xd8, 0x98, 0xb5, 0x52, 0xeb, 0x36, 0x5d
    },
    .verity_sha256 = {
        0x9b, 0x2b, 0x66, 0x45, 0x82, 0x36, 0x0d, 0xec,
        0x66, 0x0e, 0x3e, 0x25, 0xc8, 0x40, 0x10, 0x4c,
        0x16, 0xb1, 0xe1, 0xa9, 0xcb, 0x4a, 0xad, 0xbf,
        0x8f, 0x46, 0x7e, 0x20, 0x0c, 0x52, 0x5b, 0xa9
    }
};

enum install_result { INSTALLED = 0, REFUSED = 2, HOLD = 3 };
enum install_action { CARRIER, CONTROLLER };

extern const unsigned char oneos_preparation_controller[746760];

static void close_cell(int *fd, int *error) {
    int original = *fd;
    *fd = -1;
    if (original >= 0 && close(original) < 0 && !*error) *error = errno ? errno : EIO;
}

static int open_stage(int *close_error) {
    static const char *const path[] = {"data", "local", "tmp", "oneos-viewprep"};
    int fd = open("/", DIR_PATH);
    for (size_t i = 0; fd >= 0 && i < sizeof(path) / sizeof(path[0]); ++i) {
        int next = openat(fd, path[i], DIR_PATH);
        int saved = errno;
        close_cell(&fd, close_error);
        fd = next;
        if (*close_error) {
            close_cell(&fd, close_error);
            return -1;
        }
        errno = saved;
    }
    return fd;
}

static int has_space(int stage) {
    struct statvfs status;
    if (fstatvfs(stage, &status) < 0 || !status.f_frsize) return 0;
    /* Carrier data, exact Merkle tree, and bounded allocation headroom. */
    const uint64_t required = carrier.bytes + UINT64_C(109383680) + UINT64_C(134217728);
    const uint64_t fragment = status.f_frsize;
    return status.f_bavail >= required / fragment + (required % fragment != 0);
}

static int prepare_feed(int fd) {
    struct stat value;
    if (fstat(fd, &value) < 0 || (!S_ISFIFO(value.st_mode) && !S_ISSOCK(value.st_mode))) return -1;
    int flags = fcntl(fd, F_GETFL);
    return flags < 0 ? -1 : fcntl(fd, F_SETFL, flags | O_NONBLOCK);
}

static int prepare_output(int fd) {
    struct stat value;
    int flags = fcntl(fd, F_GETFL);
    if (flags < 0 || (flags & O_PATH) || fstat(fd, &value) < 0) return -1;
    int access = flags & O_ACCMODE;
    if (S_ISFIFO(value.st_mode)) {
        if (access != O_WRONLY) return -1;
    } else if (!S_ISSOCK(value.st_mode) || access != O_RDWR || guest_tree_connected_unix_stream(fd) < 0) {
        return -1;
    }
    return fcntl(fd, F_SETFL, flags | O_NONBLOCK);
}

static enum install_result install(enum install_action action, int bound,
        struct guest_tree_fsverity_provision_identity *identity) {
    struct guest_tree_install_guard *guard = NULL;
    struct guest_tree_fsverity_provision *provision = NULL;
    enum install_result result = REFUSED;
    int close_error = 0, error = 0;
    int stage = -1, namespace_fd = -1, retained_stage = -1, retained_guard = -1;
    if (bound) {
        int inherited_stage = STAGE_WITNESS_FD, inherited_guard = GUARD_WITNESS_FD;
        /* Capture both inherited handles before any open can reuse a missing slot. */
        retained_stage = fcntl(inherited_stage, F_DUPFD_CLOEXEC, GUARD_WITNESS_FD + 1);
        if (retained_stage < 0) goto settle;
        retained_guard = fcntl(inherited_guard, F_DUPFD_CLOEXEC, GUARD_WITNESS_FD + 1);
        if (retained_guard < 0) goto settle;
        close_cell(&inherited_stage, &close_error);
        close_cell(&inherited_guard, &close_error);
        if (close_error) goto settle;
    }
    stage = open_stage(&close_error);
    if (stage < 0) goto settle;
    namespace_fd = open("/proc/self/ns/mnt", O_RDONLY | O_CLOEXEC);
    if (namespace_fd < 0) goto settle;
    int acquired = bound
        ? guest_tree_install_guard_acquire_bound(&guard, stage, namespace_fd, retained_stage, retained_guard)
        : guest_tree_install_guard_acquire(&guard, stage, namespace_fd);
    if (acquired < 0) goto settle;
    if (guest_tree_install_scaffold_check(stage, namespace_fd, guard, &close_error) < 0) goto settle;
    if (action == CONTROLLER) {
        enum guest_tree_install_controller_result release = guest_tree_install_controller(guard, stage,
                namespace_fd, oneos_preparation_controller, sizeof(oneos_preparation_controller));
        if (release == GTIC_PUBLISHED_LOCAL_CLOSED) result = INSTALLED;
        else if (release != GTIC_NO_EFFECT_LOCAL_CLOSED) error = errno ? errno : EIO;
    } else {
        if (!has_space(stage) || prepare_feed(STDIN_FILENO) < 0) goto settle;
        if (bound && guest_tree_verify_installed_controller(guard, stage, namespace_fd) < 0) goto settle;
        const struct guest_tree_fsverity_provision_inputs inputs = {stage, namespace_fd, STDIN_FILENO, guard};
        if (guest_tree_fsverity_provision_new(&inputs, &carrier, &provision) == 0)
            (void)guest_tree_fsverity_provision_publish(provision);
    }

settle:
    if (provision) {
        enum guest_tree_fsverity_provision_release release = guest_tree_fsverity_provision_close(provision);
        if (release == GTVP_PUBLISHED_LOCAL_CLOSED) {
            if (identity && guest_tree_fsverity_provision_published_identity(provision, identity) < 0)
                error = errno ? errno : EIO;
            else result = INSTALLED;
        } else if (release != GTVP_NO_EFFECT_LOCAL_CLOSED) error = errno ? errno : EIO;
    }
    if (action == CARRIER) {
        int input = STDIN_FILENO;
        close_cell(&input, &close_error);
    }
    close_cell(&namespace_fd, &close_error);
    close_cell(&stage, &close_error);
    if (!error) error = close_error;
    if (guard) {
        if (error) (void)guest_tree_install_guard_hold(guard, error);
        else if (guest_tree_install_guard_finish(guard) < 0) error = errno ? errno : EIO;
    }
    close_cell(&retained_guard, &close_error);
    close_cell(&retained_stage, &close_error);
    return error || close_error ? HOLD : result;
}

static enum install_result bootstrap(struct guest_tree_install_bootstrap_identity *identity) {
    struct guest_tree_install_bootstrap *owner = NULL;
    int result = guest_tree_install_bootstrap_begin(&owner);
    if (!owner) return result == 0 ? HOLD : REFUSED;
    enum guest_tree_install_bootstrap_release release = guest_tree_install_bootstrap_close(owner);
    if (result == 0 && release == GUEST_TREE_INSTALL_BOOTSTRAP_PUBLISHED_LOCAL_CLOSED) {
        if (identity && guest_tree_install_bootstrap_published_identity(owner, identity) < 0) return HOLD;
        return INSTALLED;
    }
    if (result < 0 && release == GUEST_TREE_INSTALL_BOOTSTRAP_NO_EFFECT_LOCAL_CLOSED) return REFUSED;
    return HOLD;
}

static int write_reply(enum install_result result, const char *frame, size_t capacity, int length) {
    if (length <= 0 || (size_t)length >= capacity) return HOLD;
    const char *message = frame;
    size_t left = (size_t)length;
    while (left) {
        struct pollfd output = {.fd = STDOUT_FILENO, .events = POLLOUT};
        if (poll(&output, 1, 1000) != 1 || output.revents != POLLOUT) return HOLD;
        ssize_t n = write(STDOUT_FILENO, message, left);
        if (n <= 0 || (size_t)n > left) return HOLD;
        message += n;
        left -= (size_t)n;
    }
    return result;
}

static int reply(enum install_result result, const char *prefix, const char *success,
        const struct guest_tree_fsverity_provision_identity *identity) {
    const char *state = result == INSTALLED ? success : result == REFUSED ? "REFUSED_LOCAL_CLOSED" : "HOLD";
    char frame[224];
    int length;
    if (result == INSTALLED && identity) {
        length = snprintf(frame, sizeof(frame), "%s %s %" PRIu64 " %" PRIu32 " %" PRIu32
                " %" PRIu64 " %" PRIu64 " %" PRId64 " %" PRIu32 " %" PRId64 " %" PRIu32 "\n",
                prefix, state, identity->mount_id, identity->dev_major, identity->dev_minor, identity->inode,
                identity->size, identity->mtime_sec, identity->mtime_nsec, identity->ctime_sec, identity->ctime_nsec);
    } else length = snprintf(frame, sizeof(frame), "%s %s\n", prefix, state);
    return write_reply(result, frame, sizeof(frame), length);
}

static int reply_bound_bootstrap(void) {
    struct guest_tree_install_bootstrap_identity identity = {0};
    enum install_result result = bootstrap(&identity);
    if (result != INSTALLED) return reply(result, "ONEOS_STAGE_V2", "PUBLISHED_CLOSED", NULL);
    uint64_t stage_dev = makedev(identity.stage_dev_major, identity.stage_dev_minor);
    uint64_t guard_dev = makedev(identity.guard_dev_major, identity.guard_dev_minor);
    char frame[160];
    int length = snprintf(frame, sizeof(frame), "ONEOS_STAGE_V2 PUBLISHED_CLOSED %" PRIu64
            " %" PRIu64 " %" PRIu64 " %" PRIu64 " %" PRIu64 " %" PRIu64 "\n",
            stage_dev, identity.stage_inode, identity.stage_mount,
            guard_dev, identity.guard_inode, identity.guard_mount);
    return write_reply(result, frame, sizeof(frame), length);
}

int main(int argc, char **argv) {
    if (argc != 2 || getuid() || geteuid() || getpid() != gettid()) return REFUSED;
    const char *verb = argv[1];
    int witness = !strcmp(verb, "--install-verified-carrier-with-witness");
    int bound_controller = !strcmp(verb, "--install-preparation-controller-with-bound-stage");
    int bound_bootstrap = !strcmp(verb, "--bootstrap-empty-stage-with-witness");
    int observe = !strcmp(verb, "--observe-published-carrier");
    if (strcmp(verb, "--bootstrap-empty-stage") && strcmp(verb, "--install-preparation-controller")
            && strcmp(verb, "--install-verified-carrier") && !witness && !bound_controller && !bound_bootstrap
            && !observe) return REFUSED;
    if (signal(SIGPIPE, SIG_IGN) == SIG_ERR || prepare_output(STDOUT_FILENO) < 0) return REFUSED;
    if (observe) {
        struct guest_tree_fsverity_provision_identity identity = {0};
        int result = guest_tree_fsverity_provision_observe_current(&carrier, &identity);
        return reply(result == 0 ? INSTALLED : HOLD, "ONEOS_CARRIER_READBACK_V1", "VERIFIED_CLOSED", &identity);
    }
    if (bound_bootstrap) return reply_bound_bootstrap();
    if (!strcmp(verb, "--bootstrap-empty-stage"))
        return reply(bootstrap(NULL), "ONEOS_STAGE_V1", "PUBLISHED_CLOSED", NULL);
    if (bound_controller || !strcmp(verb, "--install-preparation-controller"))
        return reply(install(CONTROLLER, bound_controller, NULL), "ONEOS_CONTROLLER_V1", "PUBLISHED_CLOSED", NULL);
    if (witness) {
        struct guest_tree_fsverity_provision_identity identity = {0};
        enum install_result result = install(CARRIER, 1, &identity);
        return reply(result, "ONEOS_CARRIER_V2", "PUBLISHED_CLOSED", &identity);
    }
    return reply(install(CARRIER, 0, NULL), "ONEOS_CARRIER_V1", "PUBLISHED_CLOSED", NULL);
}

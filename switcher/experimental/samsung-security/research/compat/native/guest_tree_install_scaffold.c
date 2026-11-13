#define _GNU_SOURCE
#include "guest_tree_install_scaffold.h"

#include "guest_tree_fsverity_provision.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <sched.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <unistd.h>

#define DIRECTORY (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define LOOKUP (AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT)
#define IDENTITY (STATX_TYPE | STATX_MODE | STATX_UID | STATX_GID | STATX_INO | STATX_NLINK \
                  | STATX_SIZE | STATX_MTIME | STATX_CTIME | STATX_MNT_ID)

enum { ROOT, HOST_DATA, LOCAL, TMP, STAGE, BIN, BACKING, PRIVATE_DATA, USER, USER_ZERO, ALIAS, COUNT };

static const struct {
    int parent;
    const char *name;
} names[COUNT] = {
    [ROOT] = {-1, "/"}, [HOST_DATA] = {ROOT, "data"}, [LOCAL] = {HOST_DATA, "local"},
    [TMP] = {LOCAL, "tmp"}, [STAGE] = {TMP, "oneos-viewprep"}, [BIN] = {STAGE, "bin"},
    [BACKING] = {STAGE, "backing"}, [PRIVATE_DATA] = {STAGE, "data"}, [USER] = {PRIVATE_DATA, "user"},
    [USER_ZERO] = {USER, "0"}, [ALIAS] = {PRIVATE_DATA, "data"},
};

static int refuse(int error) {
    errno = error;
    return -1;
}

static int current_guard(const struct guest_tree_install_guard *guard, int stage, int ns) {
    errno = 0;
    int status = guest_tree_fsverity_check_install_guard(guard, stage, ns);
    return status == 0 ? 0 : refuse(status > 0 ? EPERM : (errno ? errno : EIO));
}

static void record_close(int result, int *close_error) {
    if (result < 0 && !*close_error) *close_error = errno ? errno : EIO;
}

static int directory(int fd, const char *name, struct statx *out) {
    if (statx(fd, name, LOOKUP | (*name ? 0 : AT_EMPTY_PATH), IDENTITY, out) < 0) return -1;
    if ((out->stx_mask & IDENTITY) != IDENTITY || !out->stx_mnt_id || !out->stx_ino || !S_ISDIR(out->stx_mode))
        return refuse(EXDEV);
    return 0;
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major
            && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_directory(const struct statx *a, const struct statx *b, int full) {
    return same_mount(a, b) && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode
            && a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid
            && (!full || (a->stx_nlink == b->stx_nlink && a->stx_size == b->stx_size
                && a->stx_mtime.tv_sec == b->stx_mtime.tv_sec && a->stx_mtime.tv_nsec == b->stx_mtime.tv_nsec
                && a->stx_ctime.tv_sec == b->stx_ctime.tv_sec && a->stx_ctime.tv_nsec == b->stx_ctime.tv_nsec));
}

static int fresh_names(const int fds[COUNT], const struct statx held[COUNT], int stage_fd) {
    struct statx named, opened;
    for (int i = ROOT; i < COUNT; ++i) {
        int parent = i == ROOT ? AT_FDCWD : fds[names[i].parent];
        if (directory(parent, names[i].name, &named) < 0 || directory(fds[i], "", &opened) < 0) return -1;
        if (!same_directory(&held[i], &opened, i >= STAGE) || !same_directory(&opened, &named, i >= STAGE))
            return refuse(ESTALE);
    }
    if (directory(stage_fd, "", &opened) < 0) return -1;
    return same_directory(&held[STAGE], &opened, 1) ? 0 : refuse(ESTALE);
}

static int profile(const int fds[COUNT], const struct statx held[COUNT]) {
    struct statfs fs;
    struct statvfs flags;
    if (fstatfs(fds[HOST_DATA], &fs) < 0 || fstatvfs(fds[HOST_DATA], &flags) < 0) return -1;
    if ((unsigned long)fs.f_type != F2FS_SUPER_MAGIC || (flags.f_flag & ST_RDONLY)
            || same_mount(&held[ROOT], &held[HOST_DATA]) || held[ROOT].stx_uid || (held[ROOT].stx_mode & 0022))
        return refuse(EXDEV);
    for (int i = LOCAL; i < COUNT; ++i) {
        if (!same_mount(&held[i], &held[HOST_DATA])) return refuse(EXDEV);
        for (int j = HOST_DATA; j < i; ++j)
            if (held[i].stx_ino == held[j].stx_ino) return refuse(EXDEV);
    }
    const struct statx *data = &held[PRIVATE_DATA];
    if (held[STAGE].stx_uid || held[STAGE].stx_gid || (held[STAGE].stx_mode & 07777) != 0700
            || held[BIN].stx_uid || held[BIN].stx_gid || (held[BIN].stx_mode & 07777) != 0700
            || held[BACKING].stx_uid || (held[BACKING].stx_mode & 0022) || held[BACKING].stx_nlink != 2
            || data->stx_uid != 1000 || data->stx_gid != 1000 || (data->stx_mode & 07777) != 0771)
        return refuse(EPERM);
    return 0;
}

static int names_match(int fd, const struct statx *expected, const char *first, const char *second,
        int *close_error) {
    struct statx opened;
    int readable = openat(fd, ".", O_RDONLY | O_DIRECTORY | O_NOATIME | O_NOFOLLOW | O_CLOEXEC);
    if (readable < 0) return -1;
    int failure = 0;
    if (directory(readable, "", &opened) < 0) failure = errno;
    else if (!same_directory(&opened, expected, 1)) failure = ESTALE;
    DIR *stream = failure ? NULL : fdopendir(readable);
    if (!stream) {
        if (!failure) failure = errno;
        record_close(close(readable), close_error);
        return refuse(failure ? failure : EIO);
    }
    unsigned seen = 0;
    const unsigned mask = 3U | (first ? 4U : 0U) | (second ? 8U : 0U);
    for (;;) {
        errno = 0;
        const struct dirent *entry = readdir(stream);
        if (!entry) { failure = errno; break; }
        const char *name = entry->d_name;
        unsigned bit;
        if (!strcmp(name, ".")) bit = 1U;
        else if (!strcmp(name, "..")) bit = 2U;
        else if (first && !strcmp(name, first)) bit = 4U;
        else if (second && !strcmp(name, second)) bit = 8U;
        else { failure = ENOTEMPTY; break; }
        if (seen & bit) { failure = EPROTO; break; }
        seen |= bit;
    }
    record_close(closedir(stream), close_error);
    if (failure || *close_error) return refuse(failure ? failure : *close_error);
    return seen == mask ? 0 : refuse(EPROTO);
}

int guest_tree_install_scaffold_check(int stage_fd, int controller_namespace_fd,
        const struct guest_tree_install_guard *guard, int *close_error) {
    if (!guard || !close_error || stage_fd < 0 || controller_namespace_fd < 0) return refuse(EINVAL);
    if (*close_error) return refuse(*close_error);
    if (getpid() != gettid() || getuid() || geteuid() || getegid()) return refuse(EPERM);
    if (current_guard(guard, stage_fd, controller_namespace_fd) < 0) return -1;

    int fds[COUNT];
    struct statx held[COUNT];
    for (int i = ROOT; i < COUNT; ++i) fds[i] = -1;
    int result = -1;
    for (int i = ROOT; i < COUNT; ++i) {
        fds[i] = i == ROOT ? open(names[i].name, DIRECTORY)
                          : openat(fds[names[i].parent], names[i].name, DIRECTORY);
        if (fds[i] < 0 || directory(fds[i], "", &held[i]) < 0) goto done;
        if (i == STAGE) {
            struct statx borrowed;
            if (directory(stage_fd, "", &borrowed) < 0) goto done;
            if (!same_directory(&held[i], &borrowed, 1)) { errno = ESTALE; goto done; }
        }
    }
    if (profile(fds, held) < 0 || fresh_names(fds, held, stage_fd) < 0
            || names_match(fds[BACKING], &held[BACKING], NULL, NULL, close_error) < 0
            || names_match(fds[PRIVATE_DATA], &held[PRIVATE_DATA], "user", "data", close_error) < 0
            || names_match(fds[USER], &held[USER], "0", NULL, close_error) < 0
            || names_match(fds[USER_ZERO], &held[USER_ZERO], NULL, NULL, close_error) < 0
            || names_match(fds[ALIAS], &held[ALIAS], NULL, NULL, close_error) < 0
            || fresh_names(fds, held, stage_fd) < 0 || profile(fds, held) < 0
            || current_guard(guard, stage_fd, controller_namespace_fd) < 0) goto done;
    result = 0;
done:;
    int failure = errno;
    for (int i = COUNT - 1; i >= ROOT; --i)
        if (fds[i] >= 0) record_close(close(fds[i]), close_error);
    if (*close_error) return refuse(*close_error);
    return result == 0 ? 0 : refuse(failure ? failure : EIO);
}

#define _GNU_SOURCE
#include "guest_tree_control_owner.h"
#include "guest_tree_data_roles.h"
#include "guest_tree_dev_roles.h"
#include "guest_tree_parent_view.h"
#include "guest_tree_source_mounts.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <unistd.h>

struct inspection {
    const int *witnesses, *rights;
    const struct gtc_observation *observed;
};

static int refuse(int error) {
    errno = error;
    return -1;
}

static void close_temporary(int *cell, int *error, int *close_error) {
    int fd = *cell;
    *cell = -1;
    if (fd < 0 || close(fd) == 0) return;
    int failure = errno ? errno : EIO;
    if (!*close_error) *close_error = failure;
    if (!*error) *error = failure;
}

static int directory_stat(int base, const char *name, struct statx *stat) {
    const unsigned mask = STATX_TYPE | STATX_MODE | STATX_UID | STATX_GID |
                          STATX_INO | STATX_NLINK | STATX_MNT_ID;
    const int flags = AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT | (*name ? 0 : AT_EMPTY_PATH);
    if (statx(base, name, flags, mask, stat) < 0) return -1;
    if ((stat->stx_mask & mask) != mask || !S_ISDIR(stat->stx_mode) ||
        !stat->stx_ino || !stat->stx_mnt_id || !stat->stx_nlink) return refuse(EPROTO);
    return 0;
}

static int same_inode(const struct statx *a, const struct statx *b) {
    return a->stx_dev_major == b->stx_dev_major && a->stx_dev_minor == b->stx_dev_minor &&
           a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode &&
           a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid && a->stx_nlink == b->stx_nlink;
}

static int same_named_directory(int base, const char *name, const struct statx *held) {
    struct statx named;
    if (directory_stat(base, name, &named) < 0) return -1;
    if (held->stx_mnt_id != named.stx_mnt_id || !same_inode(held, &named)) return refuse(ESTALE);
    return 0;
}

static struct guest_tree_data_identity data_identity(const struct statx *value) {
    return (struct guest_tree_data_identity){
        .mount_id = value->stx_mnt_id, .inode = value->stx_ino,
        .major = value->stx_dev_major, .minor = value->stx_dev_minor,
        .uid = value->stx_uid, .gid = value->stx_gid, .mode = value->stx_mode,
    };
}

static int read_dev_identity(int fd, struct guest_tree_dev_identity *result) {
    struct statx stat;
    struct statfs fs;
    if (directory_stat(fd, "", &stat) < 0 || fstatfs(fd, &fs) < 0) return -1;
    *result = (struct guest_tree_dev_identity){
        .mount = {stat.stx_mnt_id, stat.stx_dev_major, stat.stx_dev_minor},
        .ino = stat.stx_ino, .nlink = stat.stx_nlink,
        .fs_type = (unsigned long)fs.f_type, .fs_flags = (unsigned long)fs.f_flags,
        .mode = stat.stx_mode, .uid = stat.stx_uid, .gid = stat.stx_gid,
    };
    return 0;
}

static int open_directory(int fd, const char *name) {
    return openat(fd, name, O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
}

static int directory_shape(int fd, int socket_expected, int *close_error) {
    int error = 0;
    unsigned seen = 0;
    struct statx held;
    DIR *directory = NULL;
    int readable = openat(fd, ".", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (readable < 0) return -1;
    if (directory_stat(fd, "", &held) < 0 || same_named_directory(readable, "", &held) < 0) {
        error = errno;
        goto done;
    }
    directory = fdopendir(readable);
    if (!directory) { error = errno; goto done; }
    readable = -1;
    for (;;) {
        errno = 0;
        const struct dirent *entry = readdir(directory);
        if (!entry) { error = errno; break; }
        unsigned bit;
        if (!strcmp(entry->d_name, ".")) bit = 1;
        else if (!strcmp(entry->d_name, "..")) bit = 2;
        else if (socket_expected && !strcmp(entry->d_name, "socket")) bit = 4;
        else { error = ENOTEMPTY; break; }
        if (seen & bit) { error = EPROTO; break; }
        seen |= bit;
    }
    if (!error && seen != (socket_expected ? 7U : 3U)) error = EPROTO;
done:
    if (directory && closedir(directory) < 0) {
        int failure = errno ? errno : EIO;
        if (!*close_error) *close_error = failure;
        if (!error) error = failure;
    }
    close_temporary(&readable, &error, close_error);
    return error ? refuse(error) : 0;
}

static int inspect_data(const struct guest_tree_parent_sample *sample, const struct inspection *in,
                        int *close_error) {
    const int *fds = in->rights;
    struct statx inherited, native, source, data, mirror, guest, item;
    struct guest_tree_data_roles roles;
    int guest_data = -1, user = -1, error = 0;
    if (directory_stat(fds[GTC_INHERITED_ROOT], "", &inherited) < 0 ||
        same_named_directory(sample->live_child_root, "", &inherited) < 0 ||
        directory_stat(AT_FDCWD, "/", &native) < 0 ||
        directory_stat(in->witnesses[GTC_PRIVATE_DATA], "", &source) < 0 ||
        same_named_directory(AT_FDCWD, GUEST_TREE_DATA_PATH, &source) < 0 ||
        directory_stat(fds[GTC_GUEST_ROOT], "", &guest) < 0 ||
        directory_stat(fds[GTC_DATA], "", &data) < 0 ||
        same_named_directory(sample->live_child_root, "data", &data) < 0 ||
        directory_stat(fds[GTC_MIRROR], "", &mirror) < 0 ||
        same_named_directory(sample->live_child_root, "data_mirror", &mirror) < 0) return -1;
    if (!same_inode(&inherited, &native) || inherited.stx_mnt_id == native.stx_mnt_id) return refuse(ESTALE);

    roles.inherited_root = data_identity(&inherited);
    roles.guest_root = data_identity(&guest);
    roles.private_data = data_identity(&source);
    roles.native_data = data_identity(&data);
    roles.native_mirror = data_identity(&mirror);
    guest_data = open_directory(fds[GTC_GUEST_ROOT], "data");
    if (guest_data < 0 || directory_stat(guest_data, "", &item) < 0) goto failed;
    roles.guest_data = data_identity(&item);
    if (directory_stat(fds[GTC_GUEST_ROOT], "data_mirror", &item) < 0) goto failed;
    roles.guest_mirror = data_identity(&item);
    user = open_directory(fds[GTC_DATA], "user");
    if (user < 0 || directory_stat(user, "", &item) < 0) goto failed;
    if (item.stx_mnt_id != data.stx_mnt_id) { errno = ESTALE; goto failed; }
    if (directory_stat(user, "0", &item) < 0) goto failed;
    roles.user_zero = data_identity(&item);
    if (directory_stat(fds[GTC_DATA], "data", &item) < 0) goto failed;
    roles.native_alias = data_identity(&item);
    if (directory_stat(guest_data, "data", &item) < 0) goto failed;
    roles.guest_alias = data_identity(&item);
    if (guest_tree_data_roles_check(sample->parent_rows, sample->parent_count,
            sample->child_rows, sample->child_count, &roles, in->observed) != 0) goto failed;
    goto done;
failed:
    error = errno ? errno : EIO;
done:
    close_temporary(&user, &error, close_error);
    close_temporary(&guest_data, &error, close_error);
    return error ? refuse(error) : 0;
}

static int inspect_dev(const struct guest_tree_parent_sample *sample, const struct inspection *in,
                       int *close_error) {
    const int *fds = in->rights;
    const uint64_t *mounts = in->observed->mounts;
    struct guest_tree_dev_sample dev;
    struct statx native_dev;
    int reopened_dev = -1, reopened_socket = -1, error = 0;
    if (read_dev_identity(fds[GTC_DEV], &dev.dev) < 0 ||
        read_dev_identity(fds[GTC_SOCKET], &dev.socket_dir) < 0 ||
        directory_stat(sample->live_child_root, "dev", &native_dev) < 0) return -1;
    if (dev.dev.mount.id != mounts[GTC_DEV] || dev.socket_dir.mount.id != mounts[GTC_SOCKET] ||
        (dev.dev.mount.major == native_dev.stx_dev_major && dev.dev.mount.minor == native_dev.stx_dev_minor))
        return refuse(ESTALE);
    reopened_dev = open_directory(fds[GTC_GUEST_ROOT], "dev");
    if (reopened_dev >= 0) reopened_socket = open_directory(fds[GTC_DEV], "socket");
    if (reopened_dev < 0 || reopened_socket < 0 || read_dev_identity(reopened_dev, &dev.reopened_dev) < 0 ||
        read_dev_identity(reopened_socket, &dev.reopened_socket) < 0 ||
        guest_tree_dev_roles_check(sample->child_rows, sample->child_count, mounts[GTC_GUEST_ROOT], &dev) != 0 ||
        directory_shape(fds[GTC_DEV], 1, close_error) < 0 ||
        directory_shape(fds[GTC_SOCKET], 0, close_error) < 0) error = errno ? errno : EIO;
    close_temporary(&reopened_socket, &error, close_error);
    close_temporary(&reopened_dev, &error, close_error);
    return error ? refuse(error) : 0;
}

static int inspect_remaining(const struct guest_tree_parent_sample *sample, void *context,
                             int *close_error) {
    const struct inspection *in = context;
    const struct gtc_observation *view = in->observed;
    const char prefix[] = GUEST_TREE_TARGET_PATH "/";
    for (size_t i = 0; i < sample->child_count; ++i) {
        const struct gpv_mount_row *row = &sample->child_rows[i];
        if (!strncmp(row->point, prefix, sizeof(prefix) - 1) &&
            row->id != view->guest_data_mount && row->id != view->guest_mirror_mount &&
            row->id != view->alias_guest && row->id != view->mounts[GTC_DEV]) return refuse(ESTALE);
    }
    if (inspect_data(sample, in, close_error) < 0) return -1;
    return inspect_dev(sample, in, close_error);
}

int guest_tree_verify_remaining_view(pid_t child, const int witnesses[GTR_WITNESSES],
                                     const int rights[GTR_VIEW_RIGHTS],
                                     const struct gtc_observation *observed, int *close_error) {
    if (!witnesses || !rights || !observed || !close_error) return refuse(EINVAL);
    struct inspection context = {.witnesses = witnesses, .rights = rights, .observed = observed};
    return guest_tree_parent_view_inspect(child, witnesses[GTC_TREE], witnesses[GTC_PARENT_NAMESPACE],
            rights[GTC_NAMESPACE], rights[GTC_GUEST_ROOT], observed->namespace_dev, observed->namespace_inode,
            observed->mounts[GTC_GUEST_ROOT], inspect_remaining, &context, close_error);
}

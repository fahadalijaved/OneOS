#define _GNU_SOURCE
#include "guest_linkerconfig_seed.h"
#include "guest_readback_identity.h"

#include <dirent.h>
#include <linux/magic.h>
#include <string.h>
#include <sys/statfs.h>
#include <unistd.h>

static const char base_name[] = "ld.config.txt";

static int directory_matches(int root_fd, int directory_fd, const struct statx *expected) {
    struct statx held, named;
    if (guest_readback_stat(directory_fd, "", &held) < 0
            || guest_readback_stat(root_fd, "linkerconfig", &named) < 0) return -1;
    if (!guest_readback_same_node(&held, &named)
            || !guest_readback_same_mount(expected, &held) || expected->stx_ino != held.stx_ino)
        return guest_readback_refuse(ESTALE);
    if (held.stx_mode != (S_IFDIR | 0755) || held.stx_uid || held.stx_gid)
        return guest_readback_refuse(EPERM);
    return 0;
}

static int check_names(int directory_fd, const struct statx *expected, int seeded) {
    int fd = openat(directory_fd, ".", O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) return -1;
    DIR *directory = fdopendir(fd);
    if (!directory) {
        int error = errno;
        (void)close(fd);
        return guest_readback_refuse(error);
    }
    struct statx held;
    int error = 0;
    if (guest_readback_stat(fd, "", &held) < 0) error = errno;
    else if (!guest_readback_same_mount(expected, &held) || expected->stx_ino != held.stx_ino) error = ESTALE;

    unsigned names = 0;
    while (!error) {
        errno = 0;
        struct dirent *entry = readdir(directory);
        if (!entry) {
            error = errno;
            break;
        }
        unsigned bit;
        if (!strcmp(entry->d_name, ".")) bit = 1;
        else if (!strcmp(entry->d_name, "..")) bit = 2;
        else if (seeded && !strcmp(entry->d_name, base_name)) bit = 4;
        else {
            error = EEXIST;
            break;
        }
        if (names & bit) {
            error = EPROTO;
            break;
        }
        names |= bit;
    }
    if (closedir(directory) < 0 && !error) error = errno;
    if (error) return guest_readback_refuse(error);
    return names == (seeded ? 7u : 3u) ? 0 : guest_readback_refuse(ESTALE);
}

static int created_file(int directory_fd, const struct statx *directory, int writer, struct statx *file) {
    struct statx named;
    if (guest_readback_stat(writer, "", file) < 0
            || guest_readback_stat(directory_fd, base_name, &named) < 0) return -1;
    if (!guest_readback_same_node(file, &named) || !guest_readback_same_mount(file, directory))
        return guest_readback_refuse(ESTALE);
    if (!S_ISREG(file->stx_mode) || file->stx_uid || file->stx_gid || file->stx_nlink != 1)
        return guest_readback_refuse(EPERM);
    return 0;
}

static int generation_matches(const struct guest_linkerconfig_generation_node *node, const struct statx *expected) {
    return node->inode == expected->stx_ino && node->mount_id == expected->stx_mnt_id
            && node->device_major == expected->stx_dev_major && node->device_minor == expected->stx_dev_minor
            && node->mode == expected->stx_mode && node->uid == expected->stx_uid && node->gid == expected->stx_gid;
}

int guest_linkerconfig_seed_target(int root_fd, int directory_fd,
        struct guest_linkerconfig_generation_start *out) {
    if (!out || root_fd < 0 || directory_fd < 0 || root_fd == directory_fd)
        return guest_readback_refuse(EINVAL);
    int root_flags = fcntl(root_fd, F_GETFD);
    if (root_flags < 0) return -1;
    int directory_flags = fcntl(directory_fd, F_GETFD);
    if (directory_flags < 0) return -1;
    if (!(root_flags & FD_CLOEXEC) || !(directory_flags & FD_CLOEXEC))
        return guest_readback_refuse(EPERM);

    struct statfs fs;
    struct statx root, directory, before, after, reopened;
    if (guest_readback_stat(root_fd, "", &root) < 0 || guest_readback_stat(directory_fd, "", &directory) < 0
            || fstatfs(directory_fd, &fs) < 0) return -1;
    if (fs.f_type != TMPFS_MAGIC || root.stx_mnt_id == directory.stx_mnt_id)
        return guest_readback_refuse(EXDEV);
    if (!S_ISDIR(root.stx_mode)) return guest_readback_refuse(ENOTDIR);
    if (directory_matches(root_fd, directory_fd, &directory) < 0 || check_names(directory_fd, &directory, 0) < 0
            || directory_matches(root_fd, directory_fd, &directory) < 0) return -1;

    int writer = openat(directory_fd, base_name, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0644);
    if (writer < 0) return -1;
    int base = -1;
    struct guest_linkerconfig_generation_start generation;
    if (created_file(directory_fd, &directory, writer, &before) < 0) goto failed;
    if (before.stx_size != 0) {
        errno = EPROTO;
        goto failed;
    }
    if (before.stx_mode != (S_IFREG | 0644) && fchmod(writer, 0644) < 0) goto failed;
    ssize_t written = write(writer, "#", 1);
    if (written != 1) {
        if (written >= 0) errno = EIO;
        goto failed;
    }
    if (created_file(directory_fd, &directory, writer, &after) < 0) goto failed;
    if (after.stx_ino != before.stx_ino || after.stx_mode != (S_IFREG | 0644) || after.stx_size != 1) {
        errno = ESTALE;
        goto failed;
    }
    base = openat(directory_fd, base_name, O_RDONLY | O_NOATIME | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);
    if (base < 0 || guest_readback_stat(base, "", &reopened) < 0) goto failed;
    if (!guest_readback_same_node(&after, &reopened)) {
        errno = ESTALE;
        goto failed;
    }
    int writer_result = close(writer);
    writer = -1;
    if (writer_result < 0 || check_names(directory_fd, &directory, 1) < 0
            || directory_matches(root_fd, directory_fd, &directory) < 0
            || guest_linkerconfig_generation_begin(root_fd, directory_fd, base, &generation) < 0)
        goto failed;
    if (!generation_matches(&generation.root, &root) || !generation_matches(&generation.directory, &directory)
            || !generation_matches(&generation.base, &reopened)) {
        errno = ESTALE;
        goto failed;
    }
    *out = generation;
    return 0;

failed: {
        int error = errno;
        if (base >= 0) (void)close(base);
        if (writer >= 0) (void)close(writer);
        return guest_readback_refuse(error);
    }
}

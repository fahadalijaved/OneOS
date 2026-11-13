#define _GNU_SOURCE
#include "guest_tree_property_stage.h"

#include "guest_tree_dev_roles.h"
#include "guest_tree_sha256.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/fs.h>
#include <linux/magic.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <unistd.h>

#define DIRECTORY (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define READING (O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC)
#define LOOKUP (AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT)
#define ID_MASK (STATX_TYPE | STATX_MNT_ID | STATX_INO)
#define PRIVATE_NAME ".oneos-property-seed"
#define PROPERTY_NAME "__properties__"
#define CHUNK 4096U

/* Full donor property_info and the exact four areas from donor-v1. */
struct seed {
    const char *name, *sha256;
    size_t bytes;
};

static const struct seed profile[GTP_SEED_COUNT] = {
    [GTP_SEED_INFO] = {"property_info", "a413051d6516719189ea964efaa7d74954f0d1052fedf066cef8c9a1c813d3e4", 171544},
    [GTP_SEED_BUILD] = {"u:object_r:build_prop:s0", "b8e9550fd09f0eb599c4fad63645ea4e1f9f9a41c0c4fbbbf93c70bb86591594", 262144},
    [GTP_SEED_DEFAULT] = {"u:object_r:default_prop:s0", "fe488c213c448d04ef155d14fc822625226da9df080c10b62b4495770d656bcb", 262144},
    [GTP_SEED_VNDK] = {"u:object_r:vndk_prop:s0", "4072c0f7a7e141a6e21b6a68c8ce216cf586293286192b467b5e141d316617ca", 262144},
    [GTP_SEED_SERIAL] = {"properties_serial", "f03e29e557ca4610dfa875a44cb091ed8f65df21de01250b28b3c21ce06c4f18", 262144},
};

struct staging {
    int error;
    unsigned char *bytes[GTP_SEED_COUNT];
    struct statx property, files[GTP_SEED_COUNT];
};

static int attempted;

static int refuse(int error) {
    errno = error;
    return -1;
}

static void close_fd(struct staging *owner, int *cell) {
    int fd = *cell, saved = errno;
    *cell = -1;
    if (fd >= 0 && close(fd) < 0 && !owner->error) owner->error = errno ? errno : EIO;
    errno = saved;
}

static int identify(int fd, struct statx *id) {
    if (statx(fd, "", LOOKUP | AT_EMPTY_PATH, ID_MASK, id) < 0) return -1;
    return (id->stx_mask & ID_MASK) == ID_MASK && id->stx_ino && id->stx_mnt_id ? 0 : refuse(EXDEV);
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major
            && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_object(const struct statx *a, const struct statx *b) {
    return same_mount(a, b) && a->stx_ino == b->stx_ino;
}

static int fstype(int fd, unsigned long wanted) {
    struct statfs fs;
    if (fstatfs(fd, &fs) < 0) return -1;
    return (unsigned long)fs.f_type == wanted ? 0 : refuse(EXDEV);
}

static int ns_identity(int fd, struct stat *st) {
    if (fstype(fd, NSFS_MAGIC) < 0 || fstat(fd, st) < 0) return -1;
    int type = ioctl(fd, NS_GET_NSTYPE);
    if (type < 0) return -1;
    return type == CLONE_NEWNS && st->st_ino ? 0 : refuse(EXDEV);
}

static int same_ns(const struct stat *a, const struct stat *b) {
    return a->st_dev == b->st_dev && a->st_ino == b->st_ino;
}

static int current_namespace(struct staging *owner, const struct gtc_child_inputs *input, int current) {
    struct stat initial, actual, named;
    struct statfs fs;
    struct statx proc, link;
    int fd = -1, result = -1;
    if (getpid() == input->parent || getppid() != input->parent) return refuse(EPERM);
    if (statfs("/proc", &fs) < 0 || statx(AT_FDCWD, "/proc", LOOKUP, ID_MASK, &proc) < 0
            || statx(AT_FDCWD, "/proc/self/ns/mnt", LOOKUP, ID_MASK, &link) < 0) return -1;
    if ((unsigned long)fs.f_type != PROC_SUPER_MAGIC || (proc.stx_mask & ID_MASK) != ID_MASK
            || (link.stx_mask & ID_MASK) != ID_MASK || !proc.stx_mnt_id || !same_mount(&proc, &link)
            || !S_ISDIR(proc.stx_mode) || !S_ISLNK(link.stx_mode)) return refuse(EXDEV);
    if (ns_identity(input->witnesses[GTC_PARENT_NAMESPACE], &initial) < 0
            || ns_identity(current, &actual) < 0) return -1;
    fd = open("/proc/self/ns/mnt", O_RDONLY | O_CLOEXEC);
    if (fd < 0 || ns_identity(fd, &named) < 0) goto done;
    result = !same_ns(&initial, &actual) && same_ns(&actual, &named) ? 0 : refuse(EXDEV);
done:
    close_fd(owner, &fd);
    return owner->error ? refuse(owner->error) : result;
}

static int dev_identity(int fd, struct guest_tree_dev_identity *value) {
    struct statx id;
    struct stat st;
    struct statfs fs;
    if (identify(fd, &id) < 0 || fstat(fd, &st) < 0 || fstatfs(fd, &fs) < 0) return -1;
    if (!S_ISDIR(id.stx_mode) || st.st_ino != id.stx_ino || !S_ISDIR(st.st_mode)) return refuse(EXDEV);
    *value = (struct guest_tree_dev_identity){
        .mount = {id.stx_mnt_id, id.stx_dev_major, id.stx_dev_minor},
        .ino = st.st_ino, .nlink = st.st_nlink, .fs_type = (unsigned long)fs.f_type,
        .fs_flags = fs.f_flags, .mode = st.st_mode, .uid = st.st_uid, .gid = st.st_gid,
    };
    return 0;
}

static int directory_shape(struct staging *owner, int source, const char *const *names, size_t count) {
    struct statx held, actual;
    unsigned seen = 0;
    int result = -1;
    int fd = openat(source, ".", READING | O_DIRECTORY);
    if (fd < 0) return -1;
    if (identify(source, &held) < 0 || identify(fd, &actual) < 0) goto done;
    if (!same_object(&held, &actual)) { errno = EXDEV; goto done; }
    DIR *entries = fdopendir(fd);
    if (!entries) goto done;
    fd = -1;
    for (;;) {
        errno = 0;
        struct dirent *entry = readdir(entries);
        if (!entry) {
            if (!errno) result = seen == ((1U << count) - 1U) ? 0 : refuse(EXDEV);
            break;
        }
        if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, "..")) continue;
        size_t i = 0;
        while (i < count && strcmp(entry->d_name, names[i])) ++i;
        if (i == count || (seen & (1U << i))) { errno = EXDEV; break; }
        seen |= 1U << i;
    }
    int saved = errno;
    if (closedir(entries) < 0 && !owner->error) owner->error = errno ? errno : EIO;
    errno = saved;
done:
    close_fd(owner, &fd);
    return owner->error ? refuse(owner->error) : result;
}

static int read_mounts(struct staging *owner, struct gpv_mount_row *rows, size_t *count) {
    struct statx proc, file;
    size_t used = 0;
    int result = -1;
    const size_t capacity = GPV_MOUNTINFO_MAX_BYTES + 1U;
    char *bytes = malloc(capacity);
    if (!bytes) return -1;
    int fd = open("/proc/self/mountinfo", READING);
    if (fd < 0 || fstype(fd, PROC_SUPER_MAGIC) < 0 || identify(fd, &file) < 0
            || statx(AT_FDCWD, "/proc", LOOKUP, ID_MASK, &proc) < 0) goto done;
    if ((proc.stx_mask & ID_MASK) != ID_MASK || !S_ISDIR(proc.stx_mode)
            || !S_ISREG(file.stx_mode) || !same_mount(&proc, &file)) {
        errno = EXDEV;
        goto done;
    }
    while (used < capacity) {
        ssize_t got = read(fd, bytes + used, capacity - used);
        if (got < 0) goto done;
        if (!got) break;
        used += (size_t)got;
    }
    result = gpv_parse_mountinfo(bytes, used, rows, GPV_MOUNTINFO_MAX_ROWS, count) == GPV_OK
        ? 0 : refuse(EPROTO);
done:
    close_fd(owner, &fd);
    free(bytes);
    return owner->error ? refuse(owner->error) : result;
}

static int fresh_dev(struct staging *owner, const int *rights, struct statx *dev_id) {
    static const char *const socket_only[] = {"socket"};
    struct statx root, inherited;
    struct guest_tree_dev_sample sample;
    int result = -1, reopened_socket = -1, host_dev = -1;
    int reopened_dev = openat(rights[GTC_GUEST_ROOT], "dev", DIRECTORY);
    struct gpv_mount_row *rows = NULL;
    if (reopened_dev < 0 || identify(rights[GTC_GUEST_ROOT], &root) < 0
            || identify(rights[GTC_DEV], dev_id) < 0) goto done;
    reopened_socket = openat(reopened_dev, "socket", DIRECTORY);
    host_dev = openat(rights[GTC_INHERITED_ROOT], "dev", DIRECTORY);
    if (reopened_socket < 0 || host_dev < 0 || identify(host_dev, &inherited) < 0) goto done;
    if (dev_id->stx_dev_major == inherited.stx_dev_major && dev_id->stx_dev_minor == inherited.stx_dev_minor) {
        errno = EXDEV;
        goto done;
    }
    if (dev_identity(rights[GTC_DEV], &sample.dev) < 0
            || dev_identity(rights[GTC_SOCKET], &sample.socket_dir) < 0
            || dev_identity(reopened_dev, &sample.reopened_dev) < 0
            || dev_identity(reopened_socket, &sample.reopened_socket) < 0) goto done;
    rows = malloc(GPV_MOUNTINFO_MAX_ROWS * sizeof(*rows));
    if (!rows) goto done;
    size_t count;
    if (read_mounts(owner, rows, &count) < 0) goto done;
    if (guest_tree_dev_roles_check(rows, count, root.stx_mnt_id, &sample) < 0) {
        errno = EXDEV;
        goto done;
    }
    if (directory_shape(owner, reopened_dev, socket_only, 1) < 0
            || directory_shape(owner, reopened_socket, NULL, 0) < 0) goto done;
    result = 0;
done:
    free(rows);
    close_fd(owner, &host_dev);
    close_fd(owner, &reopened_socket);
    close_fd(owner, &reopened_dev);
    return owner->error ? refuse(owner->error) : result;
}

static int exact_read(int fd, void *bytes, size_t count, size_t at) {
    unsigned char *out = bytes;
    while (count) {
        ssize_t got = pread(fd, out, count, (off_t)at);
        if (got < 0) return -1;
        if (!got) return refuse(EIO);
        out += (size_t)got;
        count -= (size_t)got;
        at += (size_t)got;
    }
    return 0;
}

static int hash_matches(const unsigned char *bytes, const struct seed *seed) {
    static const char hex[] = "0123456789abcdef";
    struct guest_tree_sha256 hash;
    unsigned char digest[32];
    guest_tree_sha256_init(&hash);
    guest_tree_sha256_update(&hash, bytes, seed->bytes);
    guest_tree_sha256_final(&hash, digest);
    for (size_t i = 0; i < sizeof(digest); ++i) {
        if (seed->sha256[2 * i] != hex[digest[i] >> 4] ||
                seed->sha256[2 * i + 1] != hex[digest[i] & 15]) return 0;
    }
    return 1;
}

static int capture_seeds(struct staging *owner, const int *fds) {
    for (size_t i = 0; i < GTP_SEED_COUNT; ++i) {
        const struct seed *seed = &profile[i];
        struct stat st;
        if (fstat(fds[i], &st) < 0) return -1;
        if (!S_ISREG(st.st_mode) || st.st_size != (off_t)seed->bytes) return refuse(EXDEV);
        owner->bytes[i] = malloc(seed->bytes);
        if (!owner->bytes[i] || exact_read(fds[i], owner->bytes[i], seed->bytes, 0) < 0) return -1;
        if (!hash_matches(owner->bytes[i], seed)) return refuse(EBADMSG);
    }
    return 0;
}

static int write_sparse(int fd, const unsigned char *bytes, size_t size) {
    static const unsigned char zeros[CHUNK];
    if (ftruncate(fd, (off_t)size) < 0) return -1;
    for (size_t at = 0; at < size; at += CHUNK) {
        size_t count = size - at < CHUNK ? size - at : CHUNK;
        if (!memcmp(bytes + at, zeros, count)) continue;
        size_t used = 0;
        while (used < count) {
            ssize_t got = pwrite(fd, bytes + at + used, count - used, (off_t)(at + used));
            if (got < 0) return -1;
            if (!got) return refuse(EIO);
            used += (size_t)got;
        }
    }
    return 0;
}

static int file_profile(int fd, size_t size) {
    struct stat st;
    if (fstat(fd, &st) < 0) return -1;
    return st.st_mode == (S_IFREG | 0444) && !st.st_uid && !st.st_gid && st.st_nlink == 1
        && st.st_size == (off_t)size ? 0 : refuse(EXDEV);
}

static int populate(struct staging *owner, int directory) {
    for (size_t i = 0; i < GTP_SEED_COUNT; ++i) {
        const struct seed *seed = &profile[i];
        int fd = openat(directory, seed->name, O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
        if (fd < 0) return -1;
        int error = 0;
        if (identify(fd, &owner->files[i]) < 0) error = errno;
        else if (!S_ISREG(owner->files[i].stx_mode) || !same_mount(&owner->property, &owner->files[i])) error = EXDEV;
        else if (write_sparse(fd, owner->bytes[i], seed->bytes) < 0 || fchown(fd, 0, 0) < 0
                || fchmod(fd, 0444) < 0 || file_profile(fd, seed->bytes) < 0) error = errno;
        close_fd(owner, &fd);
        if (owner->error || error) return refuse(owner->error ? owner->error : error);
    }
    return 0;
}

static int readback(struct staging *owner, int directory) {
    const char *names[GTP_SEED_COUNT];
    for (size_t i = 0; i < GTP_SEED_COUNT; ++i) {
        const struct seed *seed = &profile[i];
        struct statx id;
        unsigned char bytes[CHUNK];
        int fd = openat(directory, seed->name, READING);
        if (fd < 0) return -1;
        int error = 0;
        if (identify(fd, &id) < 0 || file_profile(fd, seed->bytes) < 0) error = errno;
        else if (!same_object(&id, &owner->files[i])) error = EXDEV;
        for (size_t at = 0; !error && at < seed->bytes; at += CHUNK) {
            size_t count = seed->bytes - at < CHUNK ? seed->bytes - at : CHUNK;
            if (exact_read(fd, bytes, count, at) < 0) error = errno;
            else if (memcmp(bytes, owner->bytes[i] + at, count)) error = EBADMSG;
        }
        close_fd(owner, &fd);
        if (owner->error || error) return refuse(owner->error ? owner->error : error);
        names[i] = seed->name;
    }
    return directory_shape(owner, directory, names, GTP_SEED_COUNT);
}

static int same_named_directory(struct staging *owner, int base, const char *name, const struct statx *expected) {
    struct statx actual;
    int fd = openat(base, name, DIRECTORY);
    if (fd < 0) return -1;
    int result = identify(fd, &actual);
    close_fd(owner, &fd);
    if (owner->error) return refuse(owner->error);
    if (result < 0) return -1;
    return same_object(&actual, expected) ? 0 : refuse(EXDEV);
}

static int private_directory_profile(int fd) {
    struct stat st;
    if (fstat(fd, &st) < 0) return -1;
    return st.st_mode == (S_IFDIR | 0500) && !st.st_uid && !st.st_gid && st.st_nlink == 2
        ? 0 : refuse(EXDEV);
}

int guest_tree_stage_property_seed(const struct gtc_child_inputs *input,
        const struct gtc_child_view *view, const int seeds[GTP_SEED_COUNT], int *property_dir) {
    static const char *const finished_dev[] = {"socket", PROPERTY_NAME};
    if (!input || !input->witnesses || !view || !seeds || !property_dir || *property_dir != -1) return refuse(EINVAL);
    if (getuid() || geteuid() || getpid() != gettid() || input->parent <= 1 || getppid() != input->parent)
        return refuse(EPERM);
    if (attempted) return refuse(EALREADY);
    attempted = 1;
    const int *rights = view->rights;
    int dev = rights[GTC_DEV], directory = -1, published = -1, result = -1;
    struct staging owner = {0};
    struct statx dev_id, final;
    if (capture_seeds(&owner, seeds) < 0 || current_namespace(&owner, input, rights[GTC_NAMESPACE]) < 0
            || fresh_dev(&owner, rights, &dev_id) < 0) goto done;

    if (mkdirat(dev, PRIVATE_NAME, 0700) < 0) goto done;
    directory = openat(dev, PRIVATE_NAME, READING | O_DIRECTORY);
    if (directory < 0 || identify(directory, &owner.property) < 0) goto done;
    if (!same_mount(&owner.property, &dev_id) || same_object(&owner.property, &dev_id)) {
        errno = EXDEV;
        goto done;
    }
    if (fchown(directory, 0, 0) < 0 || populate(&owner, directory) < 0
            || fchmod(directory, 0500) < 0
            || same_named_directory(&owner, dev, PRIVATE_NAME, &owner.property) < 0
            || same_named_directory(&owner, rights[GTC_GUEST_ROOT], "dev", &dev_id) < 0
            || current_namespace(&owner, input, rights[GTC_NAMESPACE]) < 0) goto done;
    if (renameat2(dev, PRIVATE_NAME, dev, PROPERTY_NAME, RENAME_NOREPLACE) < 0) goto done;

    published = openat(dev, PROPERTY_NAME, DIRECTORY);
    if (published < 0 || identify(published, &final) < 0) goto done;
    if (!same_object(&final, &owner.property)) { errno = EXDEV; goto done; }
    if (private_directory_profile(published) < 0 || readback(&owner, published) < 0
            || directory_shape(&owner, dev, finished_dev, 2) < 0
            || same_named_directory(&owner, dev, PROPERTY_NAME, &owner.property) < 0
            || same_named_directory(&owner, rights[GTC_GUEST_ROOT], "dev", &dev_id) < 0
            || current_namespace(&owner, input, rights[GTC_NAMESPACE]) < 0) goto done;
    result = 0;
done:
    close_fd(&owner, &directory);
    if (!result && !owner.error) {
        *property_dir = published;
        published = -1;
    }
    close_fd(&owner, &published);
    int error = owner.error ? owner.error : errno;
    for (size_t i = 0; i < GTP_SEED_COUNT; ++i) free(owner.bytes[i]);
    return owner.error || result < 0 ? refuse(error) : 0;
}

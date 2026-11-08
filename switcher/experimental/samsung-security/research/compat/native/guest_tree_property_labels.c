#define _GNU_SOURCE
#include "guest_tree_property_labels.h"

#include "guest_tree_sha256.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <sys/xattr.h>
#include <unistd.h>

#define PROPERTY_DIR "/dev/__properties__"
#define LABEL_NAME "security.selinux"
#define DIRECTORY (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define READING (O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC)
#define ID_MASK (STATX_TYPE | STATX_INO | STATX_MNT_ID)
#define READ_CHUNK 4096U

/* Same admitted seed bytes as guest_tree_property_stage. The two special
 * file labels come from property_info and serial creation, respectively. */
struct member {
    const char *name, *path, *label, *sha256;
    size_t size;
};

static const struct member selected[] = {
    {"property_info", PROPERTY_DIR "/property_info", "u:object_r:property_info:s0",
        "a413051d6516719189ea964efaa7d74954f0d1052fedf066cef8c9a1c813d3e4", 171544},
    {"u:object_r:build_prop:s0", PROPERTY_DIR "/u:object_r:build_prop:s0", "u:object_r:build_prop:s0",
        "b8e9550fd09f0eb599c4fad63645ea4e1f9f9a41c0c4fbbbf93c70bb86591594", 262144},
    {"u:object_r:default_prop:s0", PROPERTY_DIR "/u:object_r:default_prop:s0", "u:object_r:default_prop:s0",
        "fe488c213c448d04ef155d14fc822625226da9df080c10b62b4495770d656bcb", 262144},
    {"u:object_r:vndk_prop:s0", PROPERTY_DIR "/u:object_r:vndk_prop:s0", "u:object_r:vndk_prop:s0",
        "4072c0f7a7e141a6e21b6a68c8ce216cf586293286192b467b5e141d316617ca", 262144},
    {"properties_serial", PROPERTY_DIR "/properties_serial", "u:object_r:properties_serial:s0",
        "f03e29e557ca4610dfa875a44cb091ed8f65df21de01250b28b3c21ce06c4f18", 262144},
};

static int refuse(int error) {
    errno = error;
    return -1;
}

static void consume(int *cell, int *error) {
    int fd = *cell;
    *cell = -1;
    if (fd >= 0 && close(fd) < 0 && !*error) *error = errno ? errno : EIO;
}

static int label_matches(const char *actual, size_t length, const char *expected) {
    size_t size = strlen(expected) + 1;
    return length == size && !memcmp(actual, expected, size);
}

static int digest_matches(const unsigned char digest[32], const char *expected) {
    static const char hex[] = "0123456789abcdef";
    for (size_t i = 0; i < 32; ++i) {
        if (hex[digest[i] >> 4] != expected[2 * i] ||
                hex[digest[i] & 15] != expected[2 * i + 1]) return 0;
    }
    return 1;
}

static int identify(int fd, const char *name, struct statx *id) {
    int flags = AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT | (*name ? 0 : AT_EMPTY_PATH);
    if (statx(fd, name, flags, ID_MASK, id) < 0) return -1;
    return (id->stx_mask & ID_MASK) == ID_MASK && id->stx_mnt_id && id->stx_ino ? 0 : refuse(EXDEV);
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major
            && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_object(const struct statx *a, const struct statx *b) {
    return same_mount(a, b) && a->stx_ino == b->stx_ino;
}

static int same_name(int dir, const char *name, const struct statx *held, unsigned type) {
    struct statx id;
    if (identify(dir, name, &id) < 0) return -1;
    return same_object(&id, held) && (id.stx_mode & S_IFMT) == type ? 0 : refuse(EXDEV);
}

static int mode_profile(int fd, mode_t mode, nlink_t links, size_t bytes) {
    struct stat st;
    if (fstat(fd, &st) < 0) return -1;
    if (st.st_mode != mode || st.st_uid || st.st_gid || st.st_nlink != links
            || (S_ISREG(mode) && st.st_size != (off_t)bytes)) return refuse(EXDEV);
    return 0;
}

static int dev_profile(int fd) {
    struct statfs fs;
    const unsigned long flags = ST_NOSUID | ST_NODEV | ST_NOEXEC;
    if (fstatfs(fd, &fs) < 0) return -1;
    return (unsigned long)fs.f_type == TMPFS_MAGIC && ((unsigned long)fs.f_flags & flags) == flags
        ? 0 : refuse(EXDEV);
}

static int digest_file(int fd, const struct member *member) {
    struct guest_tree_sha256 hash;
    unsigned char bytes[READ_CHUNK], digest[32];
    guest_tree_sha256_init(&hash);
    size_t offset = 0;
    while (offset < member->size) {
        size_t wanted = member->size - offset < sizeof(bytes) ? member->size - offset : sizeof(bytes);
        ssize_t count = pread(fd, bytes, wanted, (off_t)offset);
        if (count < 0) return -1;
        if (!count) return refuse(EIO);
        guest_tree_sha256_update(&hash, bytes, (size_t)count);
        offset += (size_t)count;
    }
    guest_tree_sha256_final(&hash, digest);
    return digest_matches(digest, member->sha256) ? 0 : refuse(EBADMSG);
}

static int member_check(int dir, const struct statx *property, const struct member *member,
                        struct statx *file) {
    char label[64];
    if (access(member->path, R_OK) < 0) return -1;
    int fd = openat(dir, member->name, READING);
    if (fd < 0) return -1;
    int error = 0;
    if (identify(fd, "", file) < 0 || mode_profile(fd, S_IFREG | 0444, 1, member->size) < 0
            || same_name(AT_FDCWD, member->path, file, S_IFREG) < 0) error = errno;
    else if (!same_mount(property, file)) error = EXDEV;
    if (!error) {
        ssize_t length = fgetxattr(fd, LABEL_NAME, label, sizeof(label));
        if (length < 0) error = errno;
        else if (!label_matches(label, (size_t)length, member->label)) error = EACCES;
    }
    if (!error && digest_file(fd, member) < 0) error = errno;
    if (!error) {
        /* Test the donor client's actual map permissions. Digest via pread
         * above, keeping kernel mapping access separate from data validation. */
        void *map = mmap(NULL, member->size, PROT_READ, MAP_SHARED, fd, 0);
        if (map == MAP_FAILED || munmap(map, member->size) < 0) error = errno;
    }
    if (!error && mode_profile(fd, S_IFREG | 0444, 1, member->size) < 0) error = errno;
    consume(&fd, &error);
    return error ? refuse(error) : 0;
}

static int directory_label(void) {
    char label[64];
    ssize_t length = lgetxattr(PROPERTY_DIR, LABEL_NAME, label, sizeof(label));
    if (length < 0) return -1;
    return label_matches(label, (size_t)length, "u:object_r:properties_device:s0") ? 0 : refuse(EACCES);
}

int guest_tree_verify_property_labels(int dev_fd, int property_dir_fd) {
    struct statx dev, property, files[sizeof(selected) / sizeof(selected[0])];
    if (getenv("BIONIC_APPCOMPAT_OVERRIDE")) return refuse(EOPNOTSUPP);
    if (identify(dev_fd, "", &dev) < 0 || identify(property_dir_fd, "", &property) < 0
            || dev_profile(dev_fd) < 0
            || same_name(AT_FDCWD, "/dev", &dev, S_IFDIR) < 0
            || same_name(AT_FDCWD, PROPERTY_DIR, &property, S_IFDIR) < 0
            || same_name(dev_fd, "__properties__", &property, S_IFDIR) < 0
            || mode_profile(property_dir_fd, S_IFDIR | 0711, 2, 0) < 0) return -1;
    if (!same_mount(&dev, &property) || same_object(&dev, &property)) return refuse(EXDEV);
    if (directory_label() < 0) return -1;

    for (size_t i = 0; i < sizeof(selected) / sizeof(selected[0]); ++i) {
        if (member_check(property_dir_fd, &property, &selected[i], &files[i]) < 0) return -1;
    }
    if (same_name(AT_FDCWD, "/dev", &dev, S_IFDIR) < 0
            || same_name(AT_FDCWD, PROPERTY_DIR, &property, S_IFDIR) < 0
            || same_name(dev_fd, "__properties__", &property, S_IFDIR) < 0
            || mode_profile(property_dir_fd, S_IFDIR | 0711, 2, 0) < 0 || directory_label() < 0) return -1;
    for (size_t i = 0; i < sizeof(selected) / sizeof(selected[0]); ++i) {
        if (same_name(property_dir_fd, selected[i].name, &files[i], S_IFREG) < 0) return -1;
    }
    return 0;
}
